"""Compatibility shims for *pyemby* when running on async-timeout ≥ 4.

The upstream *pyemby* library (and therefore Home Assistant's built-in
`emby` integration) still uses the **old** synchronous context-manager form::

    with async_timeout.timeout(10):

That API was removed in *async-timeout* v4.  Python 3.13 ships the newer
version which results in::

    TypeError: 'Timeout' object does not support the context manager protocol

Until pyemby is updated upstream we monkey-patch the affected coroutines so
Home Assistant users running on Python 3.13 can continue to browse and
control their Emby library.

The patch is safe on older Python / async-timeout versions because replacing
the method with an ``async with`` variant works across all releases.
"""

from __future__ import annotations

# pyright: reportUnusedImport=false, reportGeneralTypeIssues=false

# Only *Any* is needed for typing hints below – import directly to avoid
# *unused import* diagnostics for the other helpers.

from typing import Any


def _patch_pyemby_timeout() -> None:
    """Replace *api_request* & *socket_connection* in :pymod:`pyemby.server`."""

    try:
        import async_timeout  # noqa: WPS433 – runtime import
        import asyncio
        import logging

        import aiohttp  # noqa: WPS433 – runtime import
        from pyemby import server as _srv  # type: ignore – 3rd-party lib

    except ModuleNotFoundError:
        # Either pyemby or one of its deps is missing – nothing to patch.
        return

    if getattr(_srv.EmbyServer, "_emby_timeout_patched", False):
        return  # already patched in this interpreter

    _LOGGER = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # api_request – used for all plain HTTP calls
    # ------------------------------------------------------------------

    async def _api_request_fixed(self, url: str, params: dict[str, Any]):  # type: ignore[override]
        try:
            async with async_timeout.timeout(_srv.DEFAULT_TIMEOUT):
                request = await self._api_session.get(url, params=params)

            if request.status != 200:
                _LOGGER.error("Error fetching Emby data: %s", request.status)
                return None

            data = await request.json()
            if "error" in data:
                err = data["error"]
                _LOGGER.error(
                    "Error converting Emby data to json: %s: %s",
                    err.get("code"),
                    err.get("message"),
                )
                return None

            return data
        except (aiohttp.ClientError, asyncio.TimeoutError, ConnectionRefusedError) as exc:
            _LOGGER.error("Error fetching Emby data: %s", exc)
            return None

    _srv.EmbyServer.api_request = _api_request_fixed  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # socket_connection – websocket for session updates
    # ------------------------------------------------------------------

    async def _socket_connection_fixed(self):  # type: ignore[override]
        if not self._registered:
            _LOGGER.error("Client not registered, cannot start socket.")
            return

        url = f"{self.construct_url(_srv.SOCKET_URL)}?DeviceID={self._api_id}&api_key={self._api_key}"

        fail_count = 0
        while True:
            _LOGGER.debug("Attempting Socket Connection.")
            try:
                async with async_timeout.timeout(_srv.DEFAULT_TIMEOUT):
                    self.wsck = await self._api_session.ws_connect(url, heartbeat=300)

                # Enable server session updates
                await self.wsck.send_str('{"MessageType":"SessionsStart", "Data": "0,1500"}')

                _LOGGER.debug("Socket Connected!")
                fail_count = 0

                while True:
                    msg = await self.wsck.receive()
                    if msg.type == aiohttp.WSMsgType.text:
                        self.process_msg(msg.data)
                    elif msg.type in (aiohttp.WSMsgType.closed, aiohttp.WSMsgType.error):
                        raise ValueError("Websocket closed or errored.")

            except (
                aiohttp.ClientError,
                asyncio.TimeoutError,
                aiohttp.WSServerHandshakeError,
                ConnectionRefusedError,
                OSError,
                KeyError,
                ValueError,
            ) as exc:
                if self._shutdown:
                    break

                fail_count += 1
                _LOGGER.debug(
                    "Websocket closed – reconnect %ss (%s)", (fail_count * 5) + 5, exc
                )
                await asyncio.sleep(15)

    _srv.EmbyServer.socket_connection = _socket_connection_fixed  # type: ignore[assignment]

    _srv.EmbyServer._emby_timeout_patched = True  # type: ignore[attr-defined]


# Run immediately on import
_patch_pyemby_timeout()
