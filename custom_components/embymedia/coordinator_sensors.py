"""Data update coordinators for sensor platform."""

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
    DEFAULT_LIBRARY_SCAN_INTERVAL,
    DEFAULT_SERVER_SCAN_INTERVAL,
    DOMAIN,
    EmbyActivityLogEntry,
    EmbyDeviceInfo,
    EmbyScheduledTask,
    EmbyVirtualFolder,
)
from .exceptions import EmbyConnectionError, EmbyError

if TYPE_CHECKING:
    from .api import EmbyClient
    from .const import EmbyConfigEntry, EmbyServerInfo

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
        scan_interval: int = DEFAULT_SERVER_SCAN_INTERVAL,
    ) -> None:
        """Initialize the server coordinator.

        Args:
            hass: Home Assistant instance.
            client: Emby API client.
            server_id: Unique server identifier.
            server_name: Human-readable server name.
            config_entry: Config entry for reading options.
            scan_interval: Polling interval in seconds (default: 300).
        """
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{server_id}_server",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.server_id = server_id
        self.server_name = server_name
        self.config_entry = config_entry

    async def _async_update_data(self) -> EmbyServerData:
        """Fetch server data from Emby server.

        Returns:
            Server data including version, restart status, and scheduled tasks.

        Raises:
            UpdateFailed: If fetching data fails.
        """
        try:
            # Fetch server info
            server_info: EmbyServerInfo = await self.client.async_get_server_info()

            # Fetch scheduled tasks
            tasks: list[EmbyScheduledTask] = await self.client.async_get_scheduled_tasks()

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

            # Fetch Live TV info (Phase 16)
            live_tv_enabled = False
            live_tv_tuner_count = 0
            live_tv_active_recordings = 0
            recording_count = 0
            scheduled_timer_count = 0
            series_timer_count = 0
            try:
                live_tv_info = await self.client.async_get_live_tv_info()
                live_tv_enabled = bool(live_tv_info.get("IsEnabled", False))
                live_tv_tuner_count = live_tv_info.get("TunerCount", 0)
                live_tv_active_recordings = live_tv_info.get("ActiveRecordingCount", 0)

                # Fetch recording and timer counts if Live TV is enabled
                if live_tv_enabled:
                    timers = await self.client.async_get_timers()
                    scheduled_timer_count = len(timers)

                    series_timers = await self.client.async_get_series_timers()
                    series_timer_count = len(series_timers)

                    # Get recording count from recordings API
                    # Note: We use a user_id from enabled users if available
                    enabled_users = live_tv_info.get("EnabledUsers", [])
                    if enabled_users:
                        recordings = await self.client.async_get_recordings(
                            user_id=enabled_users[0]
                        )
                        recording_count = len(recordings)

            except (EmbyError, TypeError, AttributeError):
                # Live TV info is optional, don't fail the whole update
                # TypeError/AttributeError can occur if client doesn't have the method (e.g., in tests)
                _LOGGER.debug("Could not fetch Live TV info, Live TV may not be configured")

            # Fetch Activity Log (Phase 18) - graceful error handling
            recent_activities: list[EmbyActivityLogEntry] = []
            activity_count = 0
            try:
                activity_response = await self.client.async_get_activity_log(
                    start_index=0,
                    limit=20,  # Fetch last 20 entries
                )
                recent_activities = activity_response.get("Items", [])
                activity_count = activity_response.get("TotalRecordCount", 0)
            except (EmbyError, TypeError, AttributeError):
                _LOGGER.debug("Could not fetch activity log")

            # Fetch Devices (Phase 18) - graceful error handling
            devices: list[EmbyDeviceInfo] = []
            device_count = 0
            try:
                devices_response = await self.client.async_get_devices()
                devices = devices_response.get("Items", [])
                # Use actual item count (TotalRecordCount may be 0 due to API quirk)
                device_count = len(devices)
            except (EmbyError, TypeError, AttributeError):
                _LOGGER.debug("Could not fetch devices")

            return EmbyServerData(
                server_version=str(server_info.get("Version", "Unknown")),
                has_pending_restart=bool(server_info.get("HasPendingRestart", False)),
                has_update_available=bool(server_info.get("HasUpdateAvailable", False)),
                scheduled_tasks=tasks,
                running_tasks_count=running_tasks_count,
                library_scan_active=library_scan_active,
                library_scan_progress=library_scan_progress,
                live_tv_enabled=live_tv_enabled,
                live_tv_tuner_count=live_tv_tuner_count,
                live_tv_active_recordings=live_tv_active_recordings,
                recording_count=recording_count,
                scheduled_timer_count=scheduled_timer_count,
                series_timer_count=series_timer_count,
                recent_activities=recent_activities,
                activity_count=activity_count,
                devices=devices,
                device_count=device_count,
            )

        except EmbyConnectionError as err:
            raise UpdateFailed(f"Failed to connect to Emby server: {err}") from err
        except EmbyError as err:
            raise UpdateFailed(f"Error fetching server data: {err}") from err


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
        scan_interval: int = DEFAULT_LIBRARY_SCAN_INTERVAL,
        user_id: str | None = None,
    ) -> None:
        """Initialize the library coordinator.

        Args:
            hass: Home Assistant instance.
            client: Emby API client.
            server_id: Unique server identifier.
            config_entry: Config entry for reading options.
            scan_interval: Polling interval in seconds (default: 3600).
            user_id: Optional user ID for user-specific counts.
        """
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{server_id}_library",
            update_interval=timedelta(seconds=scan_interval),
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

        Returns:
            Library data including item counts and virtual folders.

        Raises:
            UpdateFailed: If fetching data fails.
        """
        try:
            # Fetch item counts
            counts = await self.client.async_get_item_counts()

            # Fetch virtual folders
            folders = await self.client.async_get_virtual_folders()

            data: EmbyLibraryData = {
                "movie_count": counts.get("MovieCount", 0),
                "series_count": counts.get("SeriesCount", 0),
                "episode_count": counts.get("EpisodeCount", 0),
                "artist_count": counts.get("ArtistCount", 0),
                "album_count": counts.get("AlbumCount", 0),
                "song_count": counts.get("SongCount", 0),
                "virtual_folders": folders,
            }

            # Fetch user-specific counts if user_id is configured
            if self._user_id:
                favorites_count = await self.client.async_get_user_item_count(
                    user_id=self._user_id,
                    filters="IsFavorite",
                )
                played_count = await self.client.async_get_user_item_count(
                    user_id=self._user_id,
                    filters="IsPlayed",
                )
                resumable_count = await self.client.async_get_user_item_count(
                    user_id=self._user_id,
                    filters="IsResumable",
                )

                data["user_favorites_count"] = favorites_count
                data["user_played_count"] = played_count
                data["user_resumable_count"] = resumable_count

                # Fetch playlist count (Phase 17)
                playlists = await self.client.async_get_playlists(user_id=self._user_id)
                data["playlist_count"] = len(playlists)

            return data

        except EmbyConnectionError as err:
            raise UpdateFailed(f"Failed to connect to Emby server: {err}") from err
        except EmbyError as err:
            raise UpdateFailed(f"Error fetching library data: {err}") from err


__all__ = [
    "EmbyLibraryCoordinator",
    "EmbyLibraryData",
    "EmbyServerCoordinator",
    "EmbyServerData",
]
