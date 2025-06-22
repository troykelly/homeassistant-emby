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


def _parse_embro_url(url: str):
    parsed = urlparse(url)
    return parsed.hostname or "localhost", parsed.port, parsed.scheme == "https"


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

    from components.emby.media_player import async_setup_platform  # local import

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


def main() -> None:  # noqa: ANN001 – script entrypoint
    try:
        asyncio.run(_amain())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
