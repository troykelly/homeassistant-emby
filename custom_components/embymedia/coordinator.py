"""Data update coordinator for Emby integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .exceptions import EmbyConnectionError, EmbyError
from .models import EmbySession, parse_session

if TYPE_CHECKING:
    from .api import EmbyClient
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

    async def _async_update_data(self) -> dict[str, EmbySession]:
        """Fetch session data from Emby server.

        Returns:
            Dictionary mapping device_id to EmbySession.

        Raises:
            UpdateFailed: If fetching data fails.
        """
        try:
            sessions_data: list[EmbySessionResponse] = await self.client.async_get_sessions()
        except EmbyConnectionError as err:
            raise UpdateFailed(f"Failed to connect to Emby server: {err}") from err
        except EmbyError as err:
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


__all__ = ["EmbyDataUpdateCoordinator"]
