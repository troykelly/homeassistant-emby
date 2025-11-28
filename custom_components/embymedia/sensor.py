"""Sensor platform for Emby integration."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EmbyDataUpdateCoordinator
from .coordinator_sensors import (
    EmbyLibraryCoordinator,
    EmbyServerCoordinator,
)
from .sensor_discovery import (
    EmbyContinueWatchingSensor,
    EmbyNextUpSensor,
    EmbyRecentlyAddedSensor,
    EmbySuggestionsSensor,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .const import EmbyConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EmbyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Emby sensors from a config entry.

    Args:
        hass: Home Assistant instance.
        config_entry: Config entry for the integration.
        async_add_entities: Callback to add entities.
    """
    runtime_data = config_entry.runtime_data
    server_coordinator: EmbyServerCoordinator = runtime_data.server_coordinator
    library_coordinator: EmbyLibraryCoordinator = runtime_data.library_coordinator
    session_coordinator: EmbyDataUpdateCoordinator = runtime_data.session_coordinator
    discovery_coordinators = runtime_data.discovery_coordinators
    server_name = server_coordinator.server_name

    entities: list[SensorEntity] = [
        # Server info sensors
        EmbyVersionSensor(server_coordinator),
        EmbyRunningTasksSensor(server_coordinator),
        # Session sensors
        EmbyActiveSessionsSensor(session_coordinator),
        # Library count sensors
        EmbyMovieCountSensor(library_coordinator, server_name),
        EmbySeriesCountSensor(library_coordinator, server_name),
        EmbyEpisodeCountSensor(library_coordinator, server_name),
        EmbySongCountSensor(library_coordinator, server_name),
        EmbyAlbumCountSensor(library_coordinator, server_name),
        EmbyArtistCountSensor(library_coordinator, server_name),
        # Playlist sensor (Phase 17)
        EmbyPlaylistCountSensor(library_coordinator, server_name),
        # Live TV sensors (Phase 16)
        EmbyRecordingCountSensor(server_coordinator),
        EmbyActiveRecordingsSensor(server_coordinator),
        EmbyScheduledTimerCountSensor(server_coordinator),
        EmbySeriesTimerCountSensor(server_coordinator),
    ]

    # Add discovery sensors for each user's coordinator
    # When admin context: creates sensors for ALL users (e.g., "troy Next Up", "matty Next Up")
    # When specific user: creates sensors for that user only
    for coordinator in discovery_coordinators.values():
        entities.extend(
            [
                EmbyNextUpSensor(coordinator, server_name),
                EmbyContinueWatchingSensor(coordinator, server_name),
                EmbyRecentlyAddedSensor(coordinator, server_name),
                EmbySuggestionsSensor(coordinator, server_name),
            ]
        )

    async_add_entities(entities)


# =============================================================================
# Server Sensors
# =============================================================================


class EmbyServerSensorBase(
    CoordinatorEntity[EmbyServerCoordinator],
    SensorEntity,
):
    """Base class for Emby server sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: EmbyServerCoordinator) -> None:
        """Initialize the sensor.

        Args:
            coordinator: The server data coordinator.
        """
        super().__init__(coordinator)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.server_id)},
            name=self.coordinator.server_name,
            manufacturer="Emby",
            model="Emby Server",
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None


class EmbyVersionSensor(EmbyServerSensorBase):
    """Sensor for Emby server version.

    Shows the current version of the Emby server software.
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:information"
    _attr_translation_key = "server_version"

    def __init__(self, coordinator: EmbyServerCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.server_id}_server_version"

    @property
    def native_value(self) -> str | None:
        """Return the server version."""
        if self.coordinator.data is None:
            return None
        return str(self.coordinator.data.get("server_version", "Unknown"))


class EmbyRunningTasksSensor(EmbyServerSensorBase):
    """Sensor for running scheduled tasks count.

    Shows the number of currently running scheduled tasks.
    """

    _attr_icon = "mdi:cog-sync"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "running_tasks"

    def __init__(self, coordinator: EmbyServerCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.server_id}_running_tasks"

    @property
    def native_value(self) -> int | None:
        """Return the number of running tasks."""
        if self.coordinator.data is None:
            return None
        return int(self.coordinator.data.get("running_tasks_count", 0))


# =============================================================================
# Session Sensors
# =============================================================================


class EmbySessionSensorBase(
    CoordinatorEntity[EmbyDataUpdateCoordinator],
    SensorEntity,
):
    """Base class for Emby session sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: EmbyDataUpdateCoordinator) -> None:
        """Initialize the sensor.

        Args:
            coordinator: The session data coordinator.
        """
        super().__init__(coordinator)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.server_id)},
            name=self.coordinator.server_name,
            manufacturer="Emby",
            model="Emby Server",
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return bool(self.coordinator.last_update_success)


class EmbyActiveSessionsSensor(EmbySessionSensorBase):
    """Sensor for active sessions count.

    Shows the number of currently connected clients.
    """

    _attr_icon = "mdi:account-multiple"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "active_sessions"

    def __init__(self, coordinator: EmbyDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.server_id}_active_sessions"

    @property
    def native_value(self) -> int:
        """Return the number of active sessions."""
        if self.coordinator.data is None:
            return 0
        return len(self.coordinator.data)


# =============================================================================
# Library Count Sensors
# =============================================================================


class EmbyLibrarySensorBase(
    CoordinatorEntity[EmbyLibraryCoordinator],
    SensorEntity,
):
    """Base class for Emby library sensors."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: EmbyLibraryCoordinator,
        server_name: str,
    ) -> None:
        """Initialize the sensor.

        Args:
            coordinator: The library data coordinator.
            server_name: The server name for device info.
        """
        super().__init__(coordinator)
        self._server_name = server_name

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.server_id)},
            name=self._server_name,
            manufacturer="Emby",
            model="Emby Server",
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None


class EmbyMovieCountSensor(EmbyLibrarySensorBase):
    """Sensor for movie count.

    Shows the total number of movies in the library.
    """

    _attr_icon = "mdi:movie"
    _attr_translation_key = "movie_count"

    def __init__(self, coordinator: EmbyLibraryCoordinator, server_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, server_name)
        self._attr_unique_id = f"{coordinator.server_id}_movie_count"

    @property
    def native_value(self) -> int | None:
        """Return the movie count."""
        if self.coordinator.data is None:
            return None
        return int(self.coordinator.data.get("movie_count", 0))


class EmbySeriesCountSensor(EmbyLibrarySensorBase):
    """Sensor for TV series count.

    Shows the total number of TV series in the library.
    """

    _attr_icon = "mdi:television"
    _attr_translation_key = "series_count"

    def __init__(self, coordinator: EmbyLibraryCoordinator, server_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, server_name)
        self._attr_unique_id = f"{coordinator.server_id}_series_count"

    @property
    def native_value(self) -> int | None:
        """Return the series count."""
        if self.coordinator.data is None:
            return None
        return int(self.coordinator.data.get("series_count", 0))


class EmbyEpisodeCountSensor(EmbyLibrarySensorBase):
    """Sensor for episode count.

    Shows the total number of TV episodes in the library.
    """

    _attr_icon = "mdi:television-play"
    _attr_translation_key = "episode_count"

    def __init__(self, coordinator: EmbyLibraryCoordinator, server_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, server_name)
        self._attr_unique_id = f"{coordinator.server_id}_episode_count"

    @property
    def native_value(self) -> int | None:
        """Return the episode count."""
        if self.coordinator.data is None:
            return None
        return int(self.coordinator.data.get("episode_count", 0))


class EmbySongCountSensor(EmbyLibrarySensorBase):
    """Sensor for song count.

    Shows the total number of songs in the library.
    """

    _attr_icon = "mdi:music"
    _attr_translation_key = "song_count"

    def __init__(self, coordinator: EmbyLibraryCoordinator, server_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, server_name)
        self._attr_unique_id = f"{coordinator.server_id}_song_count"

    @property
    def native_value(self) -> int | None:
        """Return the song count."""
        if self.coordinator.data is None:
            return None
        return int(self.coordinator.data.get("song_count", 0))


class EmbyAlbumCountSensor(EmbyLibrarySensorBase):
    """Sensor for album count.

    Shows the total number of music albums in the library.
    """

    _attr_icon = "mdi:album"
    _attr_translation_key = "album_count"

    def __init__(self, coordinator: EmbyLibraryCoordinator, server_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, server_name)
        self._attr_unique_id = f"{coordinator.server_id}_album_count"

    @property
    def native_value(self) -> int | None:
        """Return the album count."""
        if self.coordinator.data is None:
            return None
        return int(self.coordinator.data.get("album_count", 0))


class EmbyArtistCountSensor(EmbyLibrarySensorBase):
    """Sensor for artist count.

    Shows the total number of music artists in the library.
    """

    _attr_icon = "mdi:account-music"
    _attr_translation_key = "artist_count"

    def __init__(self, coordinator: EmbyLibraryCoordinator, server_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, server_name)
        self._attr_unique_id = f"{coordinator.server_id}_artist_count"

    @property
    def native_value(self) -> int | None:
        """Return the artist count."""
        if self.coordinator.data is None:
            return None
        return int(self.coordinator.data.get("artist_count", 0))


class EmbyPlaylistCountSensor(EmbyLibrarySensorBase):
    """Sensor for playlist count (Phase 17).

    Shows the total number of playlists owned by the user.
    Note: This sensor only shows data when user_id is configured.
    """

    _attr_icon = "mdi:playlist-music"
    _attr_translation_key = "playlist_count"

    def __init__(self, coordinator: EmbyLibraryCoordinator, server_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, server_name)
        self._attr_unique_id = f"{coordinator.server_id}_playlist_count"

    @property
    def native_value(self) -> int | None:
        """Return the playlist count."""
        if self.coordinator.data is None:
            return None
        return int(self.coordinator.data.get("playlist_count", 0))


# =============================================================================
# Live TV Sensors (Phase 16)
# =============================================================================


class EmbyRecordingCountSensor(EmbyServerSensorBase):
    """Sensor for recording count.

    Shows the total number of recordings in the library.
    """

    _attr_icon = "mdi:record-rec"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "recording_count"

    def __init__(self, coordinator: EmbyServerCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.server_id}_recording_count"

    @property
    def native_value(self) -> int | None:
        """Return the recording count."""
        if self.coordinator.data is None:
            return None
        return int(self.coordinator.data.get("recording_count", 0))


class EmbyActiveRecordingsSensor(EmbyServerSensorBase):
    """Sensor for active recordings count.

    Shows the number of recordings currently in progress.
    """

    _attr_icon = "mdi:record"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "active_recordings"

    def __init__(self, coordinator: EmbyServerCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.server_id}_active_recordings"

    @property
    def native_value(self) -> int | None:
        """Return the active recordings count."""
        if self.coordinator.data is None:
            return None
        return int(self.coordinator.data.get("live_tv_active_recordings", 0))


class EmbyScheduledTimerCountSensor(EmbyServerSensorBase):
    """Sensor for scheduled timer count.

    Shows the total number of scheduled recording timers.
    """

    _attr_icon = "mdi:timer"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "scheduled_timer_count"

    def __init__(self, coordinator: EmbyServerCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.server_id}_scheduled_timer_count"

    @property
    def native_value(self) -> int | None:
        """Return the scheduled timer count."""
        if self.coordinator.data is None:
            return None
        return int(self.coordinator.data.get("scheduled_timer_count", 0))


class EmbySeriesTimerCountSensor(EmbyServerSensorBase):
    """Sensor for series timer count.

    Shows the total number of series recording timers.
    """

    _attr_icon = "mdi:timer-sync"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "series_timer_count"

    def __init__(self, coordinator: EmbyServerCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.server_id}_series_timer_count"

    @property
    def native_value(self) -> int | None:
        """Return the series timer count."""
        if self.coordinator.data is None:
            return None
        return int(self.coordinator.data.get("series_timer_count", 0))


# =============================================================================
# Activity & Device Sensors (Phase 18)
# =============================================================================


class EmbyLastActivitySensor(EmbyServerSensorBase):
    """Sensor for last activity timestamp.

    Shows when the most recent activity occurred on the server.
    The state is a timestamp, with extra attributes showing activity details.
    """

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:history"
    _attr_translation_key = "last_activity"

    def __init__(self, coordinator: EmbyServerCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.server_id}_last_activity"

    @property
    def native_value(self) -> datetime | None:
        """Return the timestamp of the most recent activity."""
        if self.coordinator.data is None:
            return None

        activities = self.coordinator.data.get("recent_activities", [])
        if not activities:
            return None

        # Parse the ISO 8601 timestamp from the most recent activity
        date_str = activities[0].get("Date")
        if not date_str:
            return None

        try:
            # Handle Emby's timestamp format with 7-digit microseconds
            # Remove trailing zeros beyond 6 digits for standard parsing
            if "." in date_str:
                main_part, frac_and_tz = date_str.split(".", 1)
                # Find where the fractional part ends (Z or +/-)
                for i, char in enumerate(frac_and_tz):
                    if char in "Z+-":
                        frac = frac_and_tz[:i][:6]  # Keep max 6 digits
                        tz = frac_and_tz[i:]
                        date_str = f"{main_part}.{frac}{tz}"
                        break
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, str | int] | None:
        """Return extra state attributes."""
        if self.coordinator.data is None:
            return None

        activities = self.coordinator.data.get("recent_activities", [])
        activity_count = self.coordinator.data.get("activity_count", 0)

        if not activities:
            return {"total_activities": activity_count}

        latest = activities[0]
        return {
            "activity_name": latest.get("Name", "Unknown"),
            "activity_type": latest.get("Type", "Unknown"),
            "severity": latest.get("Severity", "Info"),
            "total_activities": activity_count,
        }


class EmbyConnectedDevicesSensor(EmbyServerSensorBase):
    """Sensor for connected devices count.

    Shows the number of registered devices connected to the server.
    Extra attributes contain a list of all devices with details.
    """

    _attr_icon = "mdi:devices"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "connected_devices"

    def __init__(self, coordinator: EmbyServerCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.server_id}_connected_devices"

    @property
    def native_value(self) -> int | None:
        """Return the number of connected devices."""
        if self.coordinator.data is None:
            return None
        return int(self.coordinator.data.get("device_count", 0))

    @property
    def extra_state_attributes(self) -> dict[str, list[dict[str, str]]] | None:
        """Return extra state attributes with device list."""
        if self.coordinator.data is None:
            return None

        devices = self.coordinator.data.get("devices", [])

        # Transform device data for attributes
        device_list = [
            {
                "name": device.get("Name", "Unknown"),
                "app_name": device.get("AppName", "Unknown"),
                "app_version": device.get("AppVersion", "Unknown"),
                "last_user": device.get("LastUserName", "Unknown"),
                "last_activity": device.get("DateLastActivity", ""),
            }
            for device in devices
        ]

        return {"devices": device_list}


__all__ = [
    "EmbyActiveRecordingsSensor",
    "EmbyActiveSessionsSensor",
    "EmbyAlbumCountSensor",
    "EmbyArtistCountSensor",
    "EmbyConnectedDevicesSensor",
    "EmbyEpisodeCountSensor",
    "EmbyLastActivitySensor",
    "EmbyMovieCountSensor",
    "EmbyPlaylistCountSensor",
    "EmbyRecordingCountSensor",
    "EmbyRunningTasksSensor",
    "EmbyScheduledTimerCountSensor",
    "EmbySeriesCountSensor",
    "EmbySeriesTimerCountSensor",
    "EmbySongCountSensor",
    "EmbyVersionSensor",
    "async_setup_entry",
]
