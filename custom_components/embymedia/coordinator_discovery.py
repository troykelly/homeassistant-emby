"""Data update coordinator for discovery sensors (Phase 15).

Includes caching to reduce redundant API calls (Issue #288).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import TYPE_CHECKING, TypedDict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .cache import BrowseCache
from .const import (
    DEFAULT_DISCOVERY_SCAN_INTERVAL,
    DISCOVERY_CACHE_TTL,
    DOMAIN,
    EmbyBrowseItem,
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


class EmbyUserCounts(TypedDict):
    """Type definition for user-specific item counts.

    Contains counts of items for a specific user:
    - favorites_count: Number of favorited items
    - played_count: Number of watched/played items
    - resumable_count: Number of in-progress items
    - playlist_count: Number of user's playlists
    """

    favorites_count: int
    played_count: int
    resumable_count: int
    playlist_count: int


class EmbyDiscoveryData(TypedDict):
    """Type definition for discovery coordinator data.

    Contains all discovery data fetched for a user:
    - next_up: Next episodes to watch
    - continue_watching: Partially watched items
    - recently_added: Recently added content
    - suggestions: Personalized recommendations
    - user_counts: User-specific item counts
    """

    next_up: list[NextUpItem]
    continue_watching: list[ResumableItem]
    recently_added: list[LatestMediaItem]
    suggestions: list[SuggestionItem]
    user_counts: EmbyUserCounts


class EmbyDiscoveryCoordinator(DataUpdateCoordinator[EmbyDiscoveryData]):
    """Coordinator for fetching discovery data (Next Up, Continue Watching, etc.).

    Polls discovery information every 15 minutes (configurable) including:
    - Next Up episodes for TV series in progress
    - Continue Watching (resumable items)
    - Recently Added content
    - Personalized suggestions

    Implements caching to reduce redundant API calls. Cache is invalidated on:
    - UserDataChanged WebSocket event (user watched/favorited something)
    - PlaybackStopped WebSocket event (user finished watching)
    - LibraryChanged WebSocket event (new content added)

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
    _discovery_cache: BrowseCache
    _bypass_cache: bool

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
            always_update=False,
        )
        self.client = client
        self.server_id = server_id
        self.config_entry = config_entry
        self._user_id = user_id
        self._user_name = user_name or user_id
        # Initialize discovery cache with configurable TTL (default 30 minutes)
        self._discovery_cache = BrowseCache(ttl_seconds=float(DISCOVERY_CACHE_TTL))
        self._bypass_cache = False

    @property
    def user_id(self) -> str:
        """Return the configured user ID."""
        return self._user_id

    @property
    def user_name(self) -> str:
        """Return the user name for display purposes."""
        return self._user_name

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics for diagnostics.

        Returns:
            Dictionary with hits, misses, and current entry count.
        """
        return self._discovery_cache.get_stats()

    def invalidate_cache_for_user(self, user_id: str) -> None:
        """Invalidate cache for a specific user.

        Called when UserDataChanged WebSocket event is received for this user.

        Args:
            user_id: The user ID whose cache should be invalidated.
        """
        if user_id == self._user_id:
            _LOGGER.debug(
                "Invalidating discovery cache for user %s (UserDataChanged)",
                user_id,
            )
            self._discovery_cache.clear()

    def on_playback_stopped(self, user_id: str) -> None:
        """Handle PlaybackStopped event for cache invalidation.

        Called when user stops playback - their discovery data may have changed.

        Args:
            user_id: The user ID who stopped playback.
        """
        if user_id == self._user_id:
            _LOGGER.debug(
                "Invalidating discovery cache for user %s (PlaybackStopped)",
                user_id,
            )
            self._discovery_cache.clear()

    def on_library_changed(self) -> None:
        """Handle LibraryChanged event for cache invalidation.

        Called when library content changes - discovery data may be stale.
        """
        _LOGGER.debug(
            "Invalidating discovery cache for user %s (LibraryChanged)",
            self._user_id,
        )
        self._discovery_cache.clear()

    async def async_force_refresh(self) -> EmbyDiscoveryData:
        """Force a refresh of discovery data, bypassing cache.

        Returns:
            Fresh discovery data from the API.
        """
        _LOGGER.debug("Force refreshing discovery data for user %s", self._user_id)
        self._bypass_cache = True
        try:
            return await self._async_update_data()
        finally:
            self._bypass_cache = False

    async def _async_update_data(self) -> EmbyDiscoveryData:
        """Fetch discovery data from Emby server.

        Uses caching to avoid redundant API calls. Cache is checked first,
        and only fetches from API on cache miss or when bypassing cache.

        Uses asyncio.gather() to fetch all data in parallel for improved performance.

        Returns:
            Discovery data including next up, continue watching,
            recently added, suggestions, and user-specific counts.

        Raises:
            UpdateFailed: If fetching data fails.
        """
        cache_key = f"discovery_{self._user_id}"

        # Check cache first (unless bypassing)
        if not self._bypass_cache:
            cached_data = self._discovery_cache.get(cache_key)
            if cached_data is not None:
                _LOGGER.debug(
                    "Discovery cache hit for user %s",
                    self._user_id,
                )
                return cached_data  # type: ignore[return-value]

        _LOGGER.debug(
            "Discovery cache miss for user %s - fetching from API",
            self._user_id,
        )

        try:
            # Fetch all discovery data in parallel using asyncio.gather()
            # Type annotation specifies expected return types for each coroutine
            results: tuple[
                list[NextUpItem],
                list[ResumableItem],
                list[LatestMediaItem],
                list[SuggestionItem],
                int,
                int,
                int,
                list[EmbyBrowseItem],
            ] = await asyncio.gather(
                self.client.async_get_next_up(user_id=self._user_id),
                self.client.async_get_resumable_items(user_id=self._user_id),
                self.client.async_get_latest_media(user_id=self._user_id),
                self.client.async_get_suggestions(user_id=self._user_id),
                self.client.async_get_user_item_count(
                    user_id=self._user_id,
                    filters="IsFavorite",
                ),
                self.client.async_get_user_item_count(
                    user_id=self._user_id,
                    filters="IsPlayed",
                ),
                self.client.async_get_user_item_count(
                    user_id=self._user_id,
                    filters="IsResumable",
                ),
                self.client.async_get_playlists(user_id=self._user_id),
            )  # type: ignore[assignment]

            next_up = results[0]
            continue_watching = results[1]
            recently_added = results[2]
            suggestions = results[3]
            favorites_count = results[4]
            played_count = results[5]
            resumable_count = results[6]
            playlists = results[7]

            playlist_count = len(playlists)

            user_counts = EmbyUserCounts(
                favorites_count=favorites_count,
                played_count=played_count,
                resumable_count=resumable_count,
                playlist_count=playlist_count,
            )

            data = EmbyDiscoveryData(
                next_up=next_up,
                continue_watching=continue_watching,
                recently_added=recently_added,
                suggestions=suggestions,
                user_counts=user_counts,
            )

            # Store in cache
            self._discovery_cache.set(cache_key, data)

            return data

        except EmbyConnectionError as err:
            raise UpdateFailed(f"Failed to connect to Emby server: {err}") from err
        except EmbyError as err:
            raise UpdateFailed(f"Error fetching discovery data: {err}") from err


__all__ = [
    "EmbyDiscoveryCoordinator",
    "EmbyDiscoveryData",
    "EmbyUserCounts",
]
