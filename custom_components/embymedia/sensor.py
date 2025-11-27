"""Sensor platform for Emby integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
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
    ]

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


__all__ = [
    "EmbyActiveSessionsSensor",
    "EmbyAlbumCountSensor",
    "EmbyArtistCountSensor",
    "EmbyEpisodeCountSensor",
    "EmbyMovieCountSensor",
    "EmbyRunningTasksSensor",
    "EmbySeriesCountSensor",
    "EmbySongCountSensor",
    "EmbyVersionSensor",
    "async_setup_entry",
]
