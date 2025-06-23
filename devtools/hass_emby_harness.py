"""Mini Home Assistant harness to exercise the Emby *platform* outside a full HA install.

This launches an in-memory Home Assistant instance, loads **only** the
`emby` media_player platform we maintain in this repo and wires it up to the
real Emby server specified via environment variables (or CLI flags).

It is *not* a replacement for proper unit/integration tests but offers a quick
interactive way to validate end-to-end behaviour (device discovery, state
updates, play/pause remote control) without running an entire HA container.

Requirements
------------
The `homeassistant` Python package **must** be installed in your environment
(it already is in the Codespace).  No additional configuration files are
created – everything runs inside a temporary directory.

Usage::

    export EMBY_URL=https://my.emby.local
    export EMBY_API_KEY=abcd1234

    python -m devtools.hass_emby_harness

The script will listen for devices for ~15 seconds, print any entities that
appear and exit.  Feel free to tweak the timeout with `--duration`.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import pathlib
import sys
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Compatibility patch – pyemby *api_request* coroutine
# ---------------------------------------------------------------------------
#
# The upstream *pyemby* library (<https://github.com/nwithan8/pyemby>) still
# uses the **old** ``with async_timeout.timeout(...)`` context-manager pattern
# that was deprecated in *async-timeout* v4 and removed in v5.  Python 3.13
# therefore raises::
#
#     TypeError: 'Timeout' object does not support the context manager protocol
#
# The custom Home Assistant integration relies on *pyemby* only for device
# discovery and websocket updates.  Rather than forking the dependency we
# hot-patch the offending coroutine at runtime so development harnesses – and
# real HA installs running on modern Python – keep working.
# ---------------------------------------------------------------------------


def _patch_pyemby_timeout_issue() -> None:  # noqa: D401 – internal helper
    """Monkey-patch *pyemby* to support async-timeout ≥4.*."""

    try:
        import async_timeout  # pylint: disable=import-error
        from pyemby import server as _pyemby_server  # type: ignore
        import aiohttp  # pylint: disable=import-error
        import asyncio
        import logging

    except ModuleNotFoundError:
        # Dependency missing – nothing to patch.
        return

    # Guard against double-patching when the harness is reloaded within the
    # same interpreter session.
    if getattr(_pyemby_server.EmbyServer, "_timeout_patch_applied", False):
        return

    logger = logging.getLogger("pyemby.timeout_patch")

    async def _api_request_fixed(self, url, params):  # type: ignore[override]
        """Replacement for *EmbyServer.api_request* using *async with*."""

        try:
            async with async_timeout.timeout(_pyemby_server.DEFAULT_TIMEOUT):
                request = await self._api_session.get(url, params=params)

            if request.status != 200:
                logger.error("Error fetching Emby data: %s", request.status)
                return None

            request_json = await request.json()

            if "error" in request_json:
                logger.error(
                    "Error converting Emby data to json: %s: %s",
                    request_json["error"].get("code"),
                    request_json["error"].get("message"),
                )
                return None

            return request_json

        except (aiohttp.ClientError, asyncio.TimeoutError, ConnectionRefusedError) as err:
            logger.error("Error fetching Emby data: %s", err)
            return None

    # Patch in-place so all subsequent instances inherit the fix.
    _pyemby_server.EmbyServer.api_request = _api_request_fixed  # type: ignore[assignment]
    _pyemby_server.EmbyServer._timeout_patch_applied = True  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Patch the *socket_connection* coroutine (same timeout bug)
    # ------------------------------------------------------------------

    async def _socket_connection_fixed(self):  # type: ignore[override]
        """Replacement that uses modern async-timeout context-manager."""

        if not self._registered:
            logger.error("Client not registered, cannot start socket.")
            return

        url = f"{self.construct_url(_pyemby_server.SOCKET_URL)}?DeviceID={self._api_id}&api_key={self._api_key}"

        fail_count = 0
        while True:
            logger.debug("Attempting Socket Connection.")
            try:
                async with async_timeout.timeout(_pyemby_server.DEFAULT_TIMEOUT):
                    self.wsck = await self._api_session.ws_connect(url, heartbeat=300)

                # Enable server session updates
                try:
                    await self.wsck.send_str('{"MessageType":"SessionsStart", "Data": "0,1500"}')
                except Exception as err:  # noqa: BLE001 – upstream blanket
                    logger.error("Failure setting session updates: %s", err)
                    raise ValueError("Session updates error.")

                logger.debug("Socket Connected!")
                fail_count = 0

                while True:
                    msg = await self.wsck.receive()
                    if msg.type == aiohttp.WSMsgType.text:
                        self.process_msg(msg.data)
                    elif msg.type == aiohttp.WSMsgType.closed:
                        raise ValueError("Websocket was closed.")
                    elif msg.type == aiohttp.WSMsgType.error:
                        logger.debug("Websocket encountered an error: %s", msg)
                        raise ValueError("Websocket error.")

            except (
                aiohttp.ClientError,
                asyncio.TimeoutError,
                aiohttp.WSServerHandshakeError,
                ConnectionRefusedError,
                OSError,
                KeyError,
                ValueError,
            ) as err:
                if not self._shutdown:
                    fail_count += 1
                    logger.debug(
                        "Websocket unintentionally closed. Trying reconnect in %ss. Error: %s",
                        (fail_count * 5) + 5,
                        err,
                    )
                    await asyncio.sleep(15)
                    continue
                break

    _pyemby_server.EmbyServer.socket_connection = _socket_connection_fixed  # type: ignore[assignment]


# Apply patch right away – must run before Home Assistant spins up.
_patch_pyemby_timeout_issue()


# NOTE: The helper returns a **fully resolved** port so that the calling code
# can pass it through to the Home Assistant platform config unchanged – the
# integration does *not* apply its own defaults when a value is provided.
#
# 
# • When the URL explicitly specifies a port → use it as-is.
# • Otherwise fall back to common defaults:
#     - 443 for *https* (behind a reverse proxy / TLS termination)
#     - 8096 for *http*  (Emby's factory default)


def _parse_embro_url(url: str):
    parsed = urlparse(url)

    ssl = parsed.scheme == "https"
    if parsed.port is not None:
        port = parsed.port
    else:
        port = 443 if ssl else 8096

    return parsed.hostname or "localhost", port, ssl


async def _amain() -> None:  # noqa: ANN201 – script entrypoint
    try:
        from homeassistant.core import HomeAssistant, callback
        from homeassistant.const import (
            CONF_API_KEY,
            CONF_HOST,
            CONF_PORT,
            CONF_SSL,
            EVENT_HOMEASSISTANT_START,
        )
    except ImportError:
        print("homeassistant package not available – cannot run harness.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Home Assistant – Emby component harness")
    parser.add_argument("--url", default=os.getenv("EMBY_URL"), help="Base Emby URL")
    parser.add_argument("--api-key", default=os.getenv("EMBY_API_KEY"), help="Emby API key")
    parser.add_argument("--duration", type=int, default=15, help="Seconds to keep HA running")
    parser.add_argument(
        "--browse",
        action="store_true",
        help="After entities are discovered perform a root media browse and print the hierarchy.",
    )
    parser.add_argument(
        "--browse-id",
        default=None,
        metavar="MEDIA_CONTENT_ID",
        help=(
            "When --browse is active, perform an additional browse for the given "
            "Emby media_content_id (e.g. 'emby://<item_id>').  This is useful to "
            "quickly verify navigation into a specific library or item."
        ),
    )
    parser.add_argument(
        "--auto-demo",
        action="store_true",
        help=(
            "When browsing, automatically drill into the *Movies* library (if present) "
            "and show the first playable leaf item.  Useful for quick end-to-end smoke tests "
            "without having to manually pass --browse-id arguments."
        ),
    )
    args = parser.parse_args()

    if not args.url or not args.api_key:
        print("Both --url/EMBY_URL and --api-key/EMBY_API_KEY are required.")
        sys.exit(1)

    host, port, ssl = _parse_embro_url(args.url)

    # ------------------------------------------------------------------
    # Minimal Home Assistant bootstrap
    # ------------------------------------------------------------------

    config_dir = pathlib.Path("./.ha_tmp").absolute()
    config_dir.mkdir(exist_ok=True)

    hass = HomeAssistant(str(config_dir))

    # Inject our own platform config directly – we bypass configuration.yaml.
    platform_config = {
        CONF_HOST: host,
        CONF_API_KEY: args.api_key,
        CONF_SSL: ssl,
    }
    if port:
        platform_config[CONF_PORT] = port

    from custom_components.embymedia.media_player import async_setup_platform  # local import

    entities = []

    @callback
    def add_entities_callback(new_entities, update_before_add=False):  # noqa: D401, ANN001
        entities.extend(new_entities)
        print(f"[HA] New entities added: {new_entities}")

    # Set up the platform manually – we don't load via discovery flow.
    await async_setup_platform(hass, platform_config, add_entities_callback, None)

    # Fire the start event so the platform can connect.
    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)

    print("[HA] Home Assistant running – waiting for devices…")
    await asyncio.sleep(args.duration)

    print("[HA] Entities discovered:")
    for ent in entities:
        print(f" • {ent.name}  state={ent.state}  session={getattr(ent, 'get_current_session_id', lambda: None)()}")

    # ------------------------------------------------------------------
    # Optional media browsing demo
    # ------------------------------------------------------------------

    if args.browse and entities:
        # Use the first discovered entity for demo purposes – most installations
        # expose a single Emby *remote* at a time.  Users can refine the target
        # via Home Assistant UI if needed.
        # Select a *suitable* entity – some Home Assistant remotes expose
        # duplicated *pyemby* placeholder devices that are not associated
        # with a logged-in Emby user (``UserId`` == *None*).  Attempt to pick
        # the first entity for which *root* browsing succeeds to ensure the
        # subsequent demo steps do not abort with *Unable to determine Emby
        # user* errors.

        target = None
        for cand in entities:
            try:
                await cand.async_browse_media()
            except Exception:  # noqa: BLE001 – diagnostic selection
                continue
            target = cand
            break

        if target is None:
            print("[ERROR] Could not find a browsable Emby entity – aborting demo.")
            return

        print("\n[HA] Performing *root* media browse…")
        root = await target.async_browse_media()

        for child in root.children or []:
            print(f" • {child.title}  ({child.media_content_id})  can_expand={child.can_expand}")

        # Manual sub-browse when the caller supplied an explicit id.
        if args.browse_id:
            print(f"\n[HA] Browsing into '{args.browse_id}'…")
            try:
                sub = await target.async_browse_media(media_content_id=args.browse_id)
            except Exception as exc:  # noqa: BLE001 – diagnostic harness
                print(f"[ERROR] async_browse_media failed: {exc}")
            else:
                if sub.children is None:
                    print(" (no children – leaf item)")
                else:
                    for itr in sub.children:
                        print(f"   - {itr.title}  can_play={itr.can_play}  id={itr.media_content_id}")

        # ------------------------------------------------------------------
        # Auto-demo: drill into *Movies* and then first playable item
        # ------------------------------------------------------------------

        if args.auto_demo and not args.browse_id:
            movies_node = next(
                (
                    child
                    for child in (root.children or [])
                    if child.can_expand and child.title.lower() in ("movies", "movie")
                ),
                None,
            )

            if movies_node is None:
                print("[WARN] Could not locate a 'Movies' library – skipping auto-demo.")
                return

            print(f"\n[HA] Auto-demo: browsing into '{movies_node.title}'…")
            try:
                movies_slice = await target.async_browse_media(
                    media_content_id=movies_node.media_content_id
                )
            except Exception as exc:  # noqa: BLE001
                print(f"[ERROR] Failed to browse Movies: {exc}")
                return

            # Print first 10 items (or all when fewer) for brevity.
            for itm in (movies_slice.children or [])[:10]:
                print(
                    f"   - {itm.title}  can_play={itm.can_play}  can_expand={itm.can_expand}  id={itm.media_content_id}"
                )

            # Find first playable leaf and show its details.
            playable = next((c for c in movies_slice.children or [] if c.can_play), None)
            if playable:
                print(f"\n[HA] Fetching leaf item '{playable.title}'…")
                leaf = await target.async_browse_media(media_content_id=playable.media_content_id)
                print(
                    f"Leaf item → title='{leaf.title}', content_type='{leaf.media_content_type}', id='{leaf.media_content_id}'"
                )


def main() -> None:  # noqa: ANN001 – script entrypoint
    try:
        asyncio.run(_amain())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
