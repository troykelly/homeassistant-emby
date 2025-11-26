"""Data update coordinator for Emby integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import EmbyClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, WEBSOCKET_POLL_INTERVAL
from .exceptions import EmbyConnectionError, EmbyError
from .models import EmbySession, parse_session
from .websocket import EmbyWebSocket

if TYPE_CHECKING:
    from .const import EmbySessionResponse

_LOGGER = logging.getLogger(__name__)


class EmbyDataUpdateCoordinator(DataUpdateCoordinator[dict[str, EmbySession]]):  # type: ignore[misc]
    """Coordinator for fetching Emby session data.

    This coordinator polls the Emby server for active sessions and
    maintains a dictionary mapping device_id to EmbySession.

    Using device_id (not session_id) as the key ensures entities
    persist across client reconnections.

    Attributes:
        client: The Emby API client instance.
        server_id: The Emby server ID.
        server_name: The Emby server name.
    """

    client: EmbyClient
    server_id: str
    server_name: str

    def __init__(
        self,
        hass: HomeAssistant,
        client: EmbyClient,
        server_id: str,
        server_name: str,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance.
            client: Emby API client.
            server_id: Unique server identifier.
            server_name: Human-readable server name.
            scan_interval: Polling interval in seconds.
        """
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{server_id}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.server_id = server_id
        self.server_name = server_name
        self._previous_sessions: set[str] = set()
        self._websocket: EmbyWebSocket | None = None
        self._websocket_enabled: bool = False
        self._configured_scan_interval = scan_interval
        # Resilience tracking
        self._consecutive_failures: int = 0
        self._max_consecutive_failures: int = 5

    @property
    def websocket(self) -> EmbyWebSocket | None:
        """Return the WebSocket client instance."""
        return self._websocket

    @property
    def websocket_enabled(self) -> bool:
        """Return True if WebSocket is enabled."""
        return self._websocket_enabled

    async def _async_update_data(self) -> dict[str, EmbySession]:
        """Fetch session data from Emby server with graceful degradation.

        Returns:
            Dictionary mapping device_id to EmbySession.

        Raises:
            UpdateFailed: If fetching data fails and no cached data available.
        """
        try:
            sessions_data: list[EmbySessionResponse] = await self.client.async_get_sessions()
            # Success - reset failure counter
            self._consecutive_failures = 0
        except EmbyConnectionError as err:
            self._consecutive_failures += 1
            # Check if recovery is needed
            if self._consecutive_failures >= self._max_consecutive_failures:
                await self._attempt_recovery()
            # Return cached data if available
            if self.data is not None:
                _LOGGER.warning(
                    "Failed to fetch sessions, using cached data: %s",
                    err,
                )
                cached: dict[str, EmbySession] = self.data
                return cached
            raise UpdateFailed(f"Failed to connect to Emby server: {err}") from err
        except EmbyError as err:
            self._consecutive_failures += 1
            raise UpdateFailed(f"Error fetching sessions: {err}") from err

        # Parse sessions and index by device_id
        sessions: dict[str, EmbySession] = {}
        for session_data in sessions_data:
            try:
                session = parse_session(session_data)
                # Filter to only sessions that support remote control
                # These are the ones we can create media players for
                if session.supports_remote_control:
                    sessions[session.device_id] = session
            except (KeyError, ValueError) as err:
                _LOGGER.warning(
                    "Failed to parse session data: %s - %s",
                    err,
                    session_data.get("DeviceName", "Unknown"),
                )
                continue

        # Log session changes
        current_devices = set(sessions.keys())
        added = current_devices - self._previous_sessions
        removed = self._previous_sessions - current_devices

        for device_id in added:
            session = sessions[device_id]
            _LOGGER.debug(
                "New session detected: %s (%s)",
                session.device_name,
                session.client_name,
            )

        for device_id in removed:
            _LOGGER.debug("Session removed: %s", device_id)

        self._previous_sessions = current_devices

        return sessions

    async def _attempt_recovery(self) -> None:
        """Attempt to recover from repeated failures.

        Tries to reconnect WebSocket and verify server is responding.
        """
        _LOGGER.info(
            "Attempting automatic recovery after %d failures",
            self._consecutive_failures,
        )

        # Try to reconnect WebSocket by starting reconnect loop
        if self._websocket is not None:
            await self._websocket.async_start_reconnect_loop()

        # Refresh server info to verify connectivity
        try:
            await self.client.async_get_server_info()
            _LOGGER.info("Recovery successful, server is responding")
        except EmbyError:
            _LOGGER.warning("Recovery failed, server still unreachable")

    def get_session(self, device_id: str) -> EmbySession | None:
        """Get a specific session by device ID.

        Args:
            device_id: The device ID to look up.

        Returns:
            The session if found, None otherwise.
        """
        if self.data is None:
            return None
        result: EmbySession | None = self.data.get(device_id)
        return result

    async def async_setup_websocket(
        self,
        session: aiohttp.ClientSession,
    ) -> None:
        """Set up WebSocket connection for real-time updates.

        Args:
            session: aiohttp ClientSession for WebSocket connection.
        """
        self._websocket = EmbyWebSocket(
            host=self.client.host,
            port=self.client.port,
            api_key=self.client.api_key,
            ssl=self.client.ssl,
            device_id=f"ha-emby-{self.server_id}",
            session=session,
        )

        # Set up callbacks
        self._websocket.set_message_callback(self._handle_websocket_message)
        self._websocket.set_connection_callback(self._handle_websocket_connection)

        # Connect to WebSocket
        try:
            await self._websocket.async_connect()
            # Subscribe to session updates
            await self._websocket.async_subscribe_sessions()
            self._websocket_enabled = True
            # Reduce polling interval since we have real-time updates
            self.update_interval = timedelta(seconds=WEBSOCKET_POLL_INTERVAL)
            _LOGGER.info("WebSocket connected to Emby server %s", self.server_name)
            # Start receive loop in background
            self.hass.async_create_task(self._async_websocket_receive_loop())
        except aiohttp.ClientError as err:
            _LOGGER.warning(
                "Failed to connect WebSocket to %s: %s",
                self.server_name,
                err,
            )
            self._websocket_enabled = False

    async def _async_websocket_receive_loop(self) -> None:
        """Run the WebSocket receive loop."""
        if self._websocket is None:
            return
        try:
            await self._websocket._async_receive_loop()
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOGGER.warning("WebSocket receive loop error: %s", err)
        finally:
            # Connection lost, trigger reconnect or fallback
            if self._websocket_enabled:
                self._handle_websocket_connection(False)

    async def async_shutdown_websocket(self) -> None:
        """Shut down WebSocket connection."""
        if self._websocket is not None:
            await self._websocket.async_stop_reconnect_loop()
            self._websocket = None
            self._websocket_enabled = False
            _LOGGER.info("WebSocket disconnected from Emby server %s", self.server_name)

    def _handle_websocket_message(
        self,
        message_type: str,
        data: Any,
    ) -> None:
        """Handle incoming WebSocket messages.

        Args:
            message_type: The type of message received.
            data: The message payload.
        """
        if message_type == "Sessions":
            # Direct session update from WebSocket
            self._process_sessions_data(data)
        elif message_type in (
            "PlaybackStarted",
            "PlaybackStopped",
            "PlaybackProgress",
            "SessionEnded",
        ):
            # Trigger a refresh to get latest session state
            self.hass.async_create_task(self.async_refresh())
        elif message_type == "ServerRestarting":
            _LOGGER.info("Emby server %s is restarting", self.server_name)
        elif message_type == "ServerShuttingDown":
            _LOGGER.warning("Emby server %s is shutting down", self.server_name)
        else:
            _LOGGER.debug("Unhandled WebSocket message type: %s", message_type)

    def _handle_websocket_connection(self, connected: bool) -> None:
        """Handle WebSocket connection state changes.

        Args:
            connected: True if connected, False if disconnected.
        """
        if connected:
            _LOGGER.info(
                "WebSocket connected, reducing poll interval to %d seconds",
                WEBSOCKET_POLL_INTERVAL,
            )
            self.update_interval = timedelta(seconds=WEBSOCKET_POLL_INTERVAL)
        else:
            _LOGGER.warning("WebSocket disconnected from Emby server. Using polling fallback")
            self.update_interval = timedelta(seconds=self._configured_scan_interval)

    def _process_sessions_data(
        self,
        sessions_data: list[EmbySessionResponse],
    ) -> None:
        """Process sessions data from WebSocket and update coordinator.

        Args:
            sessions_data: List of session data dictionaries from the API.
        """
        sessions: dict[str, EmbySession] = {}

        for session_data in sessions_data:
            try:
                session = parse_session(session_data)
                if session.supports_remote_control:
                    sessions[session.device_id] = session
            except (KeyError, ValueError) as err:
                _LOGGER.warning(
                    "Failed to parse session data from WebSocket: %s - %s",
                    err,
                    session_data.get("DeviceName", "Unknown"),
                )
                continue

        # Log session changes
        current_devices = set(sessions.keys())
        added = current_devices - self._previous_sessions
        removed = self._previous_sessions - current_devices

        for device_id in added:
            session = sessions[device_id]
            _LOGGER.debug(
                "New session detected: %s (%s)",
                session.device_name,
                session.client_name,
            )

        for device_id in removed:
            _LOGGER.debug("Session removed: %s", device_id)

        self._previous_sessions = current_devices

        # Update coordinator data and notify listeners
        self.async_set_updated_data(sessions)


__all__ = ["EmbyDataUpdateCoordinator"]
