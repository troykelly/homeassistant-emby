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
    EmbyScheduledTask,
    EmbyVirtualFolder,
)
from .exceptions import EmbyConnectionError, EmbyError

if TYPE_CHECKING:
    from .api import EmbyClient
    from .const import EmbyConfigEntry, EmbyServerInfo

_LOGGER = logging.getLogger(__name__)


class EmbyServerData(TypedDict):
    """Type definition for server coordinator data."""

    server_version: str
    has_pending_restart: bool
    has_update_available: bool
    scheduled_tasks: list[EmbyScheduledTask]
    running_tasks_count: int
    library_scan_active: bool
    library_scan_progress: float | None


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

            return EmbyServerData(
                server_version=str(server_info.get("Version", "Unknown")),
                has_pending_restart=bool(server_info.get("HasPendingRestart", False)),
                has_update_available=bool(server_info.get("HasUpdateAvailable", False)),
                scheduled_tasks=tasks,
                running_tasks_count=running_tasks_count,
                library_scan_active=library_scan_active,
                library_scan_progress=library_scan_progress,
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
