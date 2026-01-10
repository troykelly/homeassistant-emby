"""Data update coordinators for sensor platform."""

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

from .const import (
    CONF_LIBRARY_SCAN_INTERVAL,
    CONF_SERVER_SCAN_INTERVAL,
    DEFAULT_LIBRARY_SCAN_INTERVAL,
    DEFAULT_SERVER_SCAN_INTERVAL,
    DOMAIN,
    EmbyActivityLogEntry,
    EmbyBrowseItem,
    EmbyDeviceInfo,
    EmbyItemCounts,
    EmbyPlugin,
    EmbyScheduledTask,
    EmbyVirtualFolder,
)
from .exceptions import EmbyConnectionError, EmbyError

if TYPE_CHECKING:
    from .api import EmbyClient
    from .const import EmbyConfigEntry

_LOGGER = logging.getLogger(__name__)


class EmbyServerData(TypedDict, total=False):
    """Type definition for server coordinator data."""

    # Required fields
    server_version: str
    has_pending_restart: bool
    has_update_available: bool
    scheduled_tasks: list[EmbyScheduledTask]
    running_tasks_count: int
    library_scan_active: bool
    library_scan_progress: float | None

    # Live TV fields (Phase 16)
    live_tv_enabled: bool
    live_tv_tuner_count: int
    live_tv_active_recordings: int
    recording_count: int
    scheduled_timer_count: int
    series_timer_count: int

    # Activity log fields (Phase 18)
    recent_activities: list[EmbyActivityLogEntry]
    activity_count: int

    # Device fields (Phase 18)
    devices: list[EmbyDeviceInfo]
    device_count: int

    # Plugin fields (Phase 20)
    plugins: list[EmbyPlugin]
    plugin_count: int


class EmbyLibraryData(TypedDict, total=False):
    """Type definition for library coordinator data.

    Note: User-specific fields are optional (only present when user_id configured).
    """

    # Item counts
    movie_count: int
    series_count: int
    episode_count: int
    artist_count: int
    album_count: int
    song_count: int

    # Virtual folders
    virtual_folders: list[EmbyVirtualFolder]

    # User-specific counts (optional)
    user_favorites_count: int
    user_played_count: int
    user_resumable_count: int

    # Playlist count (Phase 17 - requires user_id)
    playlist_count: int

    # Collection count (Phase 19 - requires user_id)
    collection_count: int


class EmbyServerCoordinator(DataUpdateCoordinator[EmbyServerData]):
    """Coordinator for fetching server info and scheduled tasks.

    Polls server information every 5 minutes (configurable) including:
    - Server version
    - Pending restart status
    - Update availability
    - Scheduled task status

    Attributes:
        client: The Emby API client instance.
        server_id: The Emby server ID.
        server_name: The Emby server name.
        config_entry: Config entry for reading options.
    """

    client: EmbyClient
    server_id: str
    server_name: str
    config_entry: EmbyConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: EmbyClient,
        server_id: str,
        server_name: str,
        config_entry: EmbyConfigEntry,
        scan_interval: int | None = None,
    ) -> None:
        """Initialize the server coordinator.

        Args:
            hass: Home Assistant instance.
            client: Emby API client.
            server_id: Unique server identifier.
            server_name: Human-readable server name.
            config_entry: Config entry for reading options.
            scan_interval: Polling interval in seconds. If None, reads from
                config_entry.options or uses DEFAULT_SERVER_SCAN_INTERVAL.
        """
        # Read interval from options if not explicitly provided (#292)
        if scan_interval is None:
            scan_interval = config_entry.options.get(
                CONF_SERVER_SCAN_INTERVAL, DEFAULT_SERVER_SCAN_INTERVAL
            )
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{server_id}_server",
            update_interval=timedelta(seconds=scan_interval),
            always_update=False,
        )
        self.client = client
        self.server_id = server_id
        self.server_name = server_name
        self.config_entry = config_entry

    async def _async_update_data(self) -> EmbyServerData:
        """Fetch server data from Emby server.

        Uses asyncio.gather() to fetch independent data in parallel for improved performance.

        Returns:
            Server data including version, restart status, and scheduled tasks.

        Raises:
            UpdateFailed: If fetching data fails.
        """
        try:
            # Fetch all data in parallel using asyncio.gather()
            # Server info is fetched with others but processed first for error handling
            (
                server_info,
                tasks,
                live_tv_data,
                activity_data,
                devices_data,
                plugins,
            ) = await asyncio.gather(
                self.client.async_get_server_info(),
                self._fetch_scheduled_tasks_safe(),
                self._fetch_live_tv_info_safe(),
                self._fetch_activity_log_safe(),
                self._fetch_devices_safe(),
                self._fetch_plugins_safe(),
            )

            # Calculate running tasks and library scan status
            running_tasks = [t for t in tasks if t.get("State") == "Running"]
            running_tasks_count = len(running_tasks)

            # Check for library scan task
            library_scan_active = False
            library_scan_progress: float | None = None
            for task in running_tasks:
                task_key = task.get("Key", "")
                task_name = task.get("Name", "").lower()
                if "library" in task_key.lower() or "scan" in task_name or "refresh" in task_name:
                    library_scan_active = True
                    library_scan_progress = task.get("CurrentProgressPercentage")
                    break

            # Extract Live TV data
            live_tv_enabled = live_tv_data.get("live_tv_enabled", False)
            live_tv_tuner_count = live_tv_data.get("live_tv_tuner_count", 0)
            live_tv_active_recordings = live_tv_data.get("live_tv_active_recordings", 0)
            recording_count = live_tv_data.get("recording_count", 0)
            scheduled_timer_count = live_tv_data.get("scheduled_timer_count", 0)
            series_timer_count = live_tv_data.get("series_timer_count", 0)

            # Extract activity data
            activity_items = activity_data.get("Items", [])
            activity_total = activity_data.get("TotalRecordCount", 0)
            recent_activities: list[EmbyActivityLogEntry] = (
                activity_items if isinstance(activity_items, list) else []
            )
            activity_count: int = activity_total if isinstance(activity_total, int) else 0

            # Extract devices data
            devices: list[EmbyDeviceInfo] = devices_data.get("Items", [])
            device_count = len(devices)

            # Extract plugins data
            plugin_count = len(plugins)

            return EmbyServerData(
                server_version=str(server_info.get("Version", "Unknown")),
                has_pending_restart=bool(server_info.get("HasPendingRestart", False)),
                has_update_available=bool(server_info.get("HasUpdateAvailable", False)),
                scheduled_tasks=tasks,
                running_tasks_count=running_tasks_count,
                library_scan_active=library_scan_active,
                library_scan_progress=library_scan_progress,
                live_tv_enabled=bool(live_tv_enabled),
                live_tv_tuner_count=live_tv_tuner_count,
                live_tv_active_recordings=live_tv_active_recordings,
                recording_count=recording_count,
                scheduled_timer_count=scheduled_timer_count,
                series_timer_count=series_timer_count,
                recent_activities=recent_activities,
                activity_count=activity_count,
                devices=devices,
                device_count=device_count,
                plugins=plugins,
                plugin_count=plugin_count,
            )

        except EmbyConnectionError as err:
            raise UpdateFailed(f"Failed to connect to Emby server: {err}") from err
        except EmbyError as err:
            raise UpdateFailed(f"Error fetching server data: {err}") from err

    async def _fetch_scheduled_tasks_safe(self) -> list[EmbyScheduledTask]:
        """Fetch scheduled tasks with graceful error handling.

        Returns:
            List of scheduled tasks, or empty list on failure.
        """
        try:
            return await self.client.async_get_scheduled_tasks()
        except (EmbyError, TypeError, AttributeError):
            _LOGGER.debug("Could not fetch scheduled tasks")
            return []

    async def _fetch_live_tv_info_safe(self) -> dict[str, bool | int]:
        """Fetch Live TV info with graceful error handling.

        Returns:
            Dictionary with Live TV data, or defaults on failure.
        """
        try:
            live_tv_info = await self.client.async_get_live_tv_info()
            live_tv_enabled = bool(live_tv_info.get("IsEnabled", False))
            live_tv_tuner_count: int = live_tv_info.get("TunerCount", 0)
            live_tv_active_recordings: int = live_tv_info.get("ActiveRecordingCount", 0)

            recording_count = 0
            scheduled_timer_count = 0
            series_timer_count = 0

            # Fetch recording and timer counts if Live TV is enabled
            if live_tv_enabled:
                # Fetch timers in parallel
                try:
                    timers, series_timers = await asyncio.gather(
                        self.client.async_get_timers(),
                        self.client.async_get_series_timers(),
                    )
                    scheduled_timer_count = len(timers)
                    series_timer_count = len(series_timers)
                except (EmbyError, TypeError, AttributeError):
                    pass

                # Get recording count from recordings API
                enabled_users: list[str] = live_tv_info.get("EnabledUsers", [])
                if enabled_users:
                    try:
                        recordings = await self.client.async_get_recordings(
                            user_id=enabled_users[0]
                        )
                        recording_count = len(recordings)
                    except (EmbyError, TypeError, AttributeError):
                        pass

            return {
                "live_tv_enabled": live_tv_enabled,
                "live_tv_tuner_count": live_tv_tuner_count,
                "live_tv_active_recordings": live_tv_active_recordings,
                "recording_count": recording_count,
                "scheduled_timer_count": scheduled_timer_count,
                "series_timer_count": series_timer_count,
            }
        except (EmbyError, TypeError, AttributeError):
            _LOGGER.debug("Could not fetch Live TV info, Live TV may not be configured")
            return {
                "live_tv_enabled": False,
                "live_tv_tuner_count": 0,
                "live_tv_active_recordings": 0,
                "recording_count": 0,
                "scheduled_timer_count": 0,
                "series_timer_count": 0,
            }

    async def _fetch_activity_log_safe(self) -> dict[str, list[EmbyActivityLogEntry] | int]:
        """Fetch activity log with graceful error handling.

        Returns:
            Dictionary with activity log data, or empty defaults on failure.
        """
        try:
            response = await self.client.async_get_activity_log(
                start_index=0,
                limit=20,
            )
            return {
                "Items": response.get("Items", []),
                "TotalRecordCount": response.get("TotalRecordCount", 0),
            }
        except (EmbyError, TypeError, AttributeError):
            _LOGGER.debug("Could not fetch activity log")
            return {"Items": [], "TotalRecordCount": 0}

    async def _fetch_devices_safe(self) -> dict[str, list[EmbyDeviceInfo]]:
        """Fetch devices with graceful error handling.

        Returns:
            Dictionary with devices data, or empty defaults on failure.
        """
        try:
            response = await self.client.async_get_devices()
            return {"Items": response.get("Items", [])}
        except (EmbyError, TypeError, AttributeError):
            _LOGGER.debug("Could not fetch devices")
            return {"Items": []}

    async def _fetch_plugins_safe(self) -> list[EmbyPlugin]:
        """Fetch plugins with graceful error handling.

        Returns:
            List of plugins, or empty list on failure.
        """
        try:
            return await self.client.async_get_plugins()
        except (EmbyError, TypeError, AttributeError):
            _LOGGER.debug("Could not fetch plugins")
            return []


class EmbyLibraryCoordinator(DataUpdateCoordinator[EmbyLibraryData]):
    """Coordinator for fetching library counts and statistics.

    Polls library information every hour (configurable) including:
    - Global media counts (movies, series, episodes, etc.)
    - Virtual folder information
    - User-specific counts (favorites, watched, in-progress)

    Attributes:
        client: The Emby API client instance.
        server_id: The Emby server ID.
        config_entry: Config entry for reading options.
        user_id: Optional user ID for user-specific counts.
    """

    client: EmbyClient
    server_id: str
    config_entry: EmbyConfigEntry
    _user_id: str | None

    def __init__(
        self,
        hass: HomeAssistant,
        client: EmbyClient,
        server_id: str,
        config_entry: EmbyConfigEntry,
        scan_interval: int | None = None,
        user_id: str | None = None,
    ) -> None:
        """Initialize the library coordinator.

        Args:
            hass: Home Assistant instance.
            client: Emby API client.
            server_id: Unique server identifier.
            config_entry: Config entry for reading options.
            scan_interval: Polling interval in seconds. If None, reads from
                config_entry.options or uses DEFAULT_LIBRARY_SCAN_INTERVAL.
            user_id: Optional user ID for user-specific counts.
        """
        # Read interval from options if not explicitly provided (#292)
        if scan_interval is None:
            scan_interval = config_entry.options.get(
                CONF_LIBRARY_SCAN_INTERVAL, DEFAULT_LIBRARY_SCAN_INTERVAL
            )
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{server_id}_library",
            update_interval=timedelta(seconds=scan_interval),
            always_update=False,
        )
        self.client = client
        self.server_id = server_id
        self.config_entry = config_entry
        self._user_id = user_id

    @property
    def user_id(self) -> str | None:
        """Return the configured user ID."""
        return self._user_id

    async def _async_update_data(self) -> EmbyLibraryData:
        """Fetch library data from Emby server.

        Uses asyncio.gather() to fetch independent data in parallel for improved performance.

        Returns:
            Library data including item counts and virtual folders.

        Raises:
            UpdateFailed: If fetching data fails.
        """
        try:
            if self._user_id:
                # Fetch all data in parallel (9 calls) when user_id is configured
                # Split into two gather calls for type safety (mypy limitation with 6+ args)
                (
                    (counts, folders, artist_count, boxset_count),
                    (
                        favorites_count,
                        played_count,
                        resumable_count,
                        playlists,
                        collections,
                    ),
                ) = await asyncio.gather(
                    self._fetch_base_data(),
                    self._fetch_user_data(self._user_id),
                )

                # Use boxset_count from API, but if user has collections use that count
                # (user collections may differ from global count)
                final_collection_count = len(collections) if collections else boxset_count

                return EmbyLibraryData(
                    movie_count=counts.get("MovieCount", 0),
                    series_count=counts.get("SeriesCount", 0),
                    episode_count=counts.get("EpisodeCount", 0),
                    artist_count=artist_count,
                    album_count=counts.get("AlbumCount", 0),
                    song_count=counts.get("SongCount", 0),
                    virtual_folders=folders,
                    user_favorites_count=favorites_count,
                    user_played_count=played_count,
                    user_resumable_count=resumable_count,
                    playlist_count=len(playlists),
                    collection_count=final_collection_count,
                )
            else:
                # Fetch only basic data in parallel (4 calls) when no user_id
                counts, folders, artist_count, boxset_count = await self._fetch_base_data()

                return EmbyLibraryData(
                    movie_count=counts.get("MovieCount", 0),
                    series_count=counts.get("SeriesCount", 0),
                    episode_count=counts.get("EpisodeCount", 0),
                    artist_count=artist_count,
                    album_count=counts.get("AlbumCount", 0),
                    song_count=counts.get("SongCount", 0),
                    virtual_folders=folders,
                    collection_count=boxset_count,
                )

        except EmbyConnectionError as err:
            raise UpdateFailed(f"Failed to connect to Emby server: {err}") from err
        except EmbyError as err:
            raise UpdateFailed(f"Error fetching library data: {err}") from err

    async def _fetch_base_data(
        self,
    ) -> tuple[EmbyItemCounts, list[EmbyVirtualFolder], int, int]:
        """Fetch base library data in parallel.

        Note: Artist count and BoxSet count are fetched separately because the
        /Items/Counts endpoint has known Emby bugs where ArtistCount and
        BoxSetCount always return 0.

        See: https://emby.media/community/index.php?/topic/98298-boxset-count-now-broken-in-http-api/

        Returns:
            Tuple of (item counts, virtual folders, artist count, boxset count).
        """
        return await asyncio.gather(
            self.client.async_get_item_counts(),
            self.client.async_get_virtual_folders(),
            self.client.async_get_artist_count(),
            self.client.async_get_boxset_count(),
        )

    async def _fetch_user_data(
        self,
        user_id: str,
    ) -> tuple[int, int, int, list[EmbyBrowseItem], list[EmbyBrowseItem]]:
        """Fetch user-specific library data in parallel.

        Args:
            user_id: The user ID to fetch data for.

        Returns:
            Tuple of (favorites_count, played_count, resumable_count, playlists, collections).
        """
        return await asyncio.gather(
            self.client.async_get_user_item_count(
                user_id=user_id,
                filters="IsFavorite",
            ),
            self.client.async_get_user_item_count(
                user_id=user_id,
                filters="IsPlayed",
            ),
            self.client.async_get_user_item_count(
                user_id=user_id,
                filters="IsResumable",
            ),
            self.client.async_get_playlists(user_id=user_id),
            self.client.async_get_collections(user_id=user_id),
        )


__all__ = [
    "EmbyLibraryCoordinator",
    "EmbyLibraryData",
    "EmbyServerCoordinator",
    "EmbyServerData",
]
