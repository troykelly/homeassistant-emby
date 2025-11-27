"""Discovery sensor entities for Emby integration (Phase 15)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator_discovery import EmbyDiscoveryCoordinator

if TYPE_CHECKING:
    from typing import Any


_LOGGER = logging.getLogger(__name__)


# =============================================================================
# Base Class for Discovery Sensors
# =============================================================================


class EmbyDiscoverySensorBase(
    CoordinatorEntity[EmbyDiscoveryCoordinator],
    SensorEntity,
):
    """Base class for Emby discovery sensors.

    Provides common functionality for all discovery sensor types:
    - Device info linking to server device
    - Availability based on coordinator state
    - Common entity attributes
    """

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: EmbyDiscoveryCoordinator,
        server_name: str,
    ) -> None:
        """Initialize the discovery sensor.

        Args:
            coordinator: The discovery data coordinator.
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


# =============================================================================
# Next Up Sensor
# =============================================================================


class EmbyNextUpSensor(EmbyDiscoverySensorBase):
    """Sensor showing next up episodes to watch.

    Shows the count of next episodes for TV series the user is watching.
    Extra state attributes contain the list of items with details.
    """

    _attr_icon = "mdi:television-play"
    _attr_translation_key = "next_up"

    def __init__(
        self,
        coordinator: EmbyDiscoveryCoordinator,
        server_name: str,
    ) -> None:
        """Initialize the next up sensor."""
        super().__init__(coordinator, server_name)
        self._attr_unique_id = f"{coordinator.server_id}_next_up"

    @property
    def native_value(self) -> int | None:
        """Return the count of next up items."""
        if self.coordinator.data is None:
            return None
        return len(self.coordinator.data.get("next_up", []))

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes with item details."""
        if self.coordinator.data is None:
            return None

        items = []
        for item in self.coordinator.data.get("next_up", []):
            items.append(
                {
                    "id": item.get("Id"),
                    "name": item.get("Name"),
                    "type": item.get("Type"),
                    "series_name": item.get("SeriesName"),
                    "season_name": item.get("SeasonName"),
                    "episode_number": item.get("IndexNumber"),
                    "season_number": item.get("ParentIndexNumber"),
                }
            )

        return {"items": items}


# =============================================================================
# Continue Watching Sensor
# =============================================================================


class EmbyContinueWatchingSensor(EmbyDiscoverySensorBase):
    """Sensor showing items to continue watching.

    Shows the count of partially watched movies and episodes.
    Extra state attributes contain the list of items with progress.
    """

    _attr_icon = "mdi:play-pause"
    _attr_translation_key = "continue_watching"

    def __init__(
        self,
        coordinator: EmbyDiscoveryCoordinator,
        server_name: str,
    ) -> None:
        """Initialize the continue watching sensor."""
        super().__init__(coordinator, server_name)
        self._attr_unique_id = f"{coordinator.server_id}_continue_watching"

    @property
    def native_value(self) -> int | None:
        """Return the count of continue watching items."""
        if self.coordinator.data is None:
            return None
        return len(self.coordinator.data.get("continue_watching", []))

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes with item details and progress."""
        if self.coordinator.data is None:
            return None

        items = []
        for item in self.coordinator.data.get("continue_watching", []):
            user_data = item.get("UserData", {})
            items.append(
                {
                    "id": item.get("Id"),
                    "name": item.get("Name"),
                    "type": item.get("Type"),
                    "series_name": item.get("SeriesName"),
                    "progress_percent": user_data.get("PlayedPercentage", 0),
                }
            )

        return {"items": items}


# =============================================================================
# Recently Added Sensor
# =============================================================================


class EmbyRecentlyAddedSensor(EmbyDiscoverySensorBase):
    """Sensor showing recently added content.

    Shows the count of recently added items (movies, episodes, music, etc.).
    Extra state attributes contain the list of items.
    """

    _attr_icon = "mdi:new-box"
    _attr_translation_key = "recently_added"

    def __init__(
        self,
        coordinator: EmbyDiscoveryCoordinator,
        server_name: str,
    ) -> None:
        """Initialize the recently added sensor."""
        super().__init__(coordinator, server_name)
        self._attr_unique_id = f"{coordinator.server_id}_recently_added"

    @property
    def native_value(self) -> int | None:
        """Return the count of recently added items."""
        if self.coordinator.data is None:
            return None
        return len(self.coordinator.data.get("recently_added", []))

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes with item details."""
        if self.coordinator.data is None:
            return None

        items = []
        for item in self.coordinator.data.get("recently_added", []):
            items.append(
                {
                    "id": item.get("Id"),
                    "name": item.get("Name"),
                    "type": item.get("Type"),
                    "series_name": item.get("SeriesName"),
                    "year": item.get("ProductionYear"),
                }
            )

        return {"items": items}


# =============================================================================
# Suggestions Sensor
# =============================================================================


class EmbySuggestionsSensor(EmbyDiscoverySensorBase):
    """Sensor showing personalized suggestions.

    Shows the count of suggested items based on watch history.
    Extra state attributes contain the list of items with ratings.
    """

    _attr_icon = "mdi:lightbulb"
    _attr_translation_key = "suggestions"

    def __init__(
        self,
        coordinator: EmbyDiscoveryCoordinator,
        server_name: str,
    ) -> None:
        """Initialize the suggestions sensor."""
        super().__init__(coordinator, server_name)
        self._attr_unique_id = f"{coordinator.server_id}_suggestions"

    @property
    def native_value(self) -> int | None:
        """Return the count of suggestions."""
        if self.coordinator.data is None:
            return None
        return len(self.coordinator.data.get("suggestions", []))

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes with item details and ratings."""
        if self.coordinator.data is None:
            return None

        items = []
        for item in self.coordinator.data.get("suggestions", []):
            items.append(
                {
                    "id": item.get("Id"),
                    "name": item.get("Name"),
                    "type": item.get("Type"),
                    "rating": item.get("CommunityRating"),
                    "year": item.get("ProductionYear"),
                }
            )

        return {"items": items}


__all__ = [
    "EmbyContinueWatchingSensor",
    "EmbyDiscoverySensorBase",
    "EmbyNextUpSensor",
    "EmbyRecentlyAddedSensor",
    "EmbySuggestionsSensor",
]
