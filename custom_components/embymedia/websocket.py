"""WebSocket client for Emby server."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any
from urllib.parse import quote

import aiohttp

_LOGGER = logging.getLogger(__name__)

# Default reconnection settings
DEFAULT_RECONNECT_INTERVAL = 5.0  # seconds
DEFAULT_MAX_RECONNECT_INTERVAL = 300.0  # 5 minutes


class EmbyWebSocket:
    """WebSocket client for Emby server.

    Handles WebSocket connection, automatic reconnection,
    and message dispatching to the coordinator.

    Attributes:
        host: Emby server host.
        port: Emby server port.
        api_key: Authentication API key.
        ssl: Whether to use SSL.
        device_id: Unique device ID for this connection.
    """

    def __init__(
        self,
        host: str,
        port: int,
        api_key: str,
        ssl: bool,
        device_id: str,
        session: aiohttp.ClientSession,
        reconnect_interval: float = DEFAULT_RECONNECT_INTERVAL,
        max_reconnect_interval: float = DEFAULT_MAX_RECONNECT_INTERVAL,
    ) -> None:
        """Initialize WebSocket client.

        Args:
            host: Emby server hostname.
            port: Emby server port.
            api_key: API key for authentication.
            ssl: Whether to use SSL/TLS.
            device_id: Unique device identifier for this client.
            session: aiohttp ClientSession for connections.
            reconnect_interval: Initial reconnection interval in seconds.
            max_reconnect_interval: Maximum reconnection interval in seconds.
        """
        self.host = host
        self.port = port
        self.api_key = api_key
        self.ssl = ssl
        self.device_id = device_id
        self._session = session
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._message_callback: Callable[[str, Any], None] | None = None
        self._connection_callback: Callable[[bool], None] | None = None
        self._reconnect_interval = reconnect_interval
        self._max_reconnect_interval = max_reconnect_interval
        self._reconnecting = False
        self._stop_reconnect = False

    @property
    def connected(self) -> bool:
        """Return True if WebSocket is connected."""
        return self._ws is not None and not self._ws.closed

    @property
    def reconnecting(self) -> bool:
        """Return True if attempting to reconnect."""
        return self._reconnecting

    def _build_connection_url(self) -> str:
        """Build the WebSocket connection URL.

        Returns:
            The WebSocket URL with authentication parameters.
        """
        protocol = "wss" if self.ssl else "ws"
        # URL encode the API key in case it contains special characters
        encoded_api_key = quote(self.api_key, safe="")
        encoded_device_id = quote(self.device_id, safe="")

        return (
            f"{protocol}://{self.host}:{self.port}/embywebsocket"
            f"?api_key={encoded_api_key}&deviceId={encoded_device_id}"
        )

    async def async_connect(self) -> None:
        """Establish WebSocket connection.

        Raises:
            aiohttp.ClientError: If connection fails.
        """
        url = self._build_connection_url()
        _LOGGER.debug("Connecting to WebSocket: %s", url.replace(self.api_key, "***"))

        try:
            self._ws = await self._session.ws_connect(
                url,
                heartbeat=30,
            )
            _LOGGER.info("WebSocket connected to Emby server")

            if self._connection_callback:
                self._connection_callback(True)

        except aiohttp.ClientError:
            self._ws = None
            _LOGGER.error("Failed to connect to Emby WebSocket")
            raise

    async def async_disconnect(self) -> None:
        """Close WebSocket connection."""
        if self._ws is not None and not self._ws.closed:
            await self._ws.close()
            _LOGGER.info("WebSocket disconnected")

        self._ws = None

        if self._connection_callback:
            self._connection_callback(False)

    async def async_subscribe_sessions(self, interval_ms: int = 1500) -> None:
        """Subscribe to session updates.

        Args:
            interval_ms: Update interval in milliseconds.

        Raises:
            RuntimeError: If not connected.
        """
        if not self.connected:
            raise RuntimeError("WebSocket is not connected")

        message = json.dumps({
            "MessageType": "SessionsStart",
            "Data": f"0,{interval_ms}",
        })

        await self._ws.send_str(message)  # type: ignore[union-attr]
        _LOGGER.debug("Subscribed to session updates (interval: %dms)", interval_ms)

    async def async_unsubscribe_sessions(self) -> None:
        """Unsubscribe from session updates.

        Raises:
            RuntimeError: If not connected.
        """
        if not self.connected:
            raise RuntimeError("WebSocket is not connected")

        message = json.dumps({
            "MessageType": "SessionsStop",
            "Data": "",
        })

        await self._ws.send_str(message)  # type: ignore[union-attr]
        _LOGGER.debug("Unsubscribed from session updates")

    def set_message_callback(
        self,
        callback: Callable[[str, Any], None],
    ) -> None:
        """Set callback for received messages.

        Args:
            callback: Function to call with (message_type, data).
        """
        self._message_callback = callback

    def set_connection_callback(
        self,
        callback: Callable[[bool], None],
    ) -> None:
        """Set callback for connection state changes.

        Args:
            callback: Function to call with connection state (True=connected).
        """
        self._connection_callback = callback

    def _process_message(self, msg: aiohttp.WSMessage) -> None:
        """Process a received WebSocket message.

        Args:
            msg: The WebSocket message to process.
        """
        if msg.type == aiohttp.WSMsgType.TEXT:
            try:
                data = json.loads(msg.data)
                message_type = data.get("MessageType", "Unknown")
                message_data = data.get("Data")

                _LOGGER.debug("Received WebSocket message: %s", message_type)

                if self._message_callback:
                    self._message_callback(message_type, message_data)

            except json.JSONDecodeError:
                _LOGGER.warning("Received malformed JSON from WebSocket: %s", msg.data[:100])

        elif msg.type == aiohttp.WSMsgType.CLOSED:
            _LOGGER.info("WebSocket connection closed by server")

        elif msg.type == aiohttp.WSMsgType.ERROR:
            _LOGGER.error("WebSocket error received")

    async def _async_receive_loop(self) -> None:
        """Receive and process WebSocket messages.

        Loops until the connection is closed or an error occurs.
        """
        if self._ws is None:
            return

        async for msg in self._ws:
            self._process_message(msg)

            if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                break

    async def async_start_reconnect_loop(self) -> None:
        """Start the reconnection loop.

        Connects to the WebSocket and automatically reconnects on failure
        with exponential backoff.
        """
        self._stop_reconnect = False
        interval = self._reconnect_interval

        while not self._stop_reconnect:
            try:
                self._reconnecting = not self.connected
                await self.async_connect()
                self._reconnecting = False
                interval = self._reconnect_interval  # Reset on success
                break

            except aiohttp.ClientError:
                self._reconnecting = True
                _LOGGER.warning(
                    "WebSocket connection failed, retrying in %.1f seconds",
                    interval,
                )

                if self._stop_reconnect:
                    break

                await asyncio.sleep(interval)
                interval = min(interval * 2, self._max_reconnect_interval)

        self._reconnecting = False

    async def async_stop_reconnect_loop(self) -> None:
        """Stop the reconnection loop and disconnect."""
        self._stop_reconnect = True
        self._reconnecting = False
        await self.async_disconnect()


__all__ = ["EmbyWebSocket"]
