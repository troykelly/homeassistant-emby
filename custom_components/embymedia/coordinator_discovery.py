"""Data update coordinator for discovery sensors (Phase 15)."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, TypedDict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DEFAULT_DISCOVERY_SCAN_INTERVAL,
    DOMAIN,
    LatestMediaItem,
    NextUpItem,
    ResumableItem,
    SuggestionItem,
)
from .exceptions import EmbyConnectionError, EmbyError

if TYPE_CHECKING:
    from .api import EmbyClient
    from .const import EmbyConfigEntry

_LOGGER = logging.getLogger(__name__)


class EmbyDiscoveryData(TypedDict):
    """Type definition for discovery coordinator data.

    Contains all discovery data fetched for a user:
    - next_up: Next episodes to watch
    - continue_watching: Partially watched items
    - recently_added: Recently added content
    - suggestions: Personalized recommendations
    """

    next_up: list[NextUpItem]
    continue_watching: list[ResumableItem]
    recently_added: list[LatestMediaItem]
    suggestions: list[SuggestionItem]


class EmbyDiscoveryCoordinator(DataUpdateCoordinator[EmbyDiscoveryData]):
    """Coordinator for fetching discovery data (Next Up, Continue Watching, etc.).

    Polls discovery information every 15 minutes (configurable) including:
    - Next Up episodes for TV series in progress
    - Continue Watching (resumable items)
    - Recently Added content
    - Personalized suggestions

    This coordinator requires a user_id to fetch user-specific content.

    Attributes:
        client: The Emby API client instance.
        server_id: The Emby server ID.
        config_entry: Config entry for reading options.
        user_id: The user ID for user-specific discovery data.
        user_name: The user name for display purposes.
    """

    client: EmbyClient
    server_id: str
    config_entry: EmbyConfigEntry
    _user_id: str
    _user_name: str

    def __init__(
        self,
        hass: HomeAssistant,
        client: EmbyClient,
        server_id: str,
        config_entry: EmbyConfigEntry,
        user_id: str,
        scan_interval: int = DEFAULT_DISCOVERY_SCAN_INTERVAL,
        user_name: str | None = None,
    ) -> None:
        """Initialize the discovery coordinator.

        Args:
            hass: Home Assistant instance.
            client: Emby API client.
            server_id: Unique server identifier.
            config_entry: Config entry for reading options.
            user_id: User ID for user-specific discovery data.
            scan_interval: Polling interval in seconds (default: 900 = 15 min).
            user_name: Optional user name for display purposes.
        """
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{server_id}_discovery_{user_id}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.server_id = server_id
        self.config_entry = config_entry
        self._user_id = user_id
        self._user_name = user_name or user_id

    @property
    def user_id(self) -> str:
        """Return the configured user ID."""
        return self._user_id

    @property
    def user_name(self) -> str:
        """Return the user name for display purposes."""
        return self._user_name

    async def _async_update_data(self) -> EmbyDiscoveryData:
        """Fetch discovery data from Emby server.

        Returns:
            Discovery data including next up, continue watching,
            recently added, and suggestions.

        Raises:
            UpdateFailed: If fetching data fails.
        """
        try:
            # Fetch all discovery data for the user
            next_up = await self.client.async_get_next_up(user_id=self._user_id)
            continue_watching = await self.client.async_get_resumable_items(user_id=self._user_id)
            recently_added = await self.client.async_get_latest_media(user_id=self._user_id)
            suggestions = await self.client.async_get_suggestions(user_id=self._user_id)

            return EmbyDiscoveryData(
                next_up=next_up,
                continue_watching=continue_watching,
                recently_added=recently_added,
                suggestions=suggestions,
            )

        except EmbyConnectionError as err:
            raise UpdateFailed(f"Failed to connect to Emby server: {err}") from err
        except EmbyError as err:
            raise UpdateFailed(f"Error fetching discovery data: {err}") from err


__all__ = [
    "EmbyDiscoveryCoordinator",
    "EmbyDiscoveryData",
]
