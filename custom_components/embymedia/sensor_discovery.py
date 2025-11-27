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
    - Image URL generation for cover art
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

    def _get_image_url(
        self,
        item_id: str,
        image_tags: dict[str, str] | None = None,
        image_type: str = "Primary",
        max_width: int = 300,
        max_height: int = 450,
    ) -> str | None:
        """Generate image URL for an item.

        Args:
            item_id: The item ID.
            image_tags: Dict of image type to tag (for cache busting).
            image_type: Type of image (Primary, Backdrop, Thumb).
            max_width: Maximum image width.
            max_height: Maximum image height.

        Returns:
            Image URL string or None if no image available.
        """
        if not item_id:
            return None

        tag = None
        if image_tags and image_type in image_tags:
            tag = image_tags[image_type]

        url: str | None = self.coordinator.client.get_image_url(
            item_id=item_id,
            image_type=image_type,
            max_width=max_width,
            max_height=max_height,
            tag=tag,
        )
        return url

    def _get_series_image_url(
        self,
        series_id: str | None,
        series_primary_tag: str | None = None,
        max_width: int = 300,
        max_height: int = 450,
    ) -> str | None:
        """Generate image URL for a series (for episodes).

        Args:
            series_id: The series ID.
            series_primary_tag: Series primary image tag.
            max_width: Maximum image width.
            max_height: Maximum image height.

        Returns:
            Image URL string or None if no series ID.
        """
        if not series_id:
            return None

        url: str | None = self.coordinator.client.get_image_url(
            item_id=series_id,
            image_type="Primary",
            max_width=max_width,
            max_height=max_height,
            tag=series_primary_tag,
        )
        return url


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
        # Include user_id in unique_id to support multi-user mode
        self._attr_unique_id = f"{coordinator.server_id}_{coordinator.user_id}_next_up"
        # Set custom name with user name (e.g., "troy Next Up")
        self._attr_name = f"{coordinator.user_name} Next Up"

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
            item_id = item.get("Id", "")
            series_id = item.get("SeriesId")
            image_tags = item.get("ImageTags", {})
            series_primary_tag = item.get("SeriesPrimaryImageTag")

            # For episodes, prefer series image; fall back to episode image
            image_url = self._get_series_image_url(series_id, series_primary_tag)
            if not image_url:
                image_url = self._get_image_url(item_id, image_tags)

            items.append(
                {
                    "id": item_id,
                    "name": item.get("Name"),
                    "type": item.get("Type"),
                    "series_name": item.get("SeriesName"),
                    "series_id": series_id,
                    "season_name": item.get("SeasonName"),
                    "episode_number": item.get("IndexNumber"),
                    "season_number": item.get("ParentIndexNumber"),
                    "image_url": image_url,
                    "backdrop_url": self._get_image_url(item_id, image_tags, "Backdrop", 1280, 720),
                }
            )

        return {"items": items, "user_id": self.coordinator.user_id}


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
        # Include user_id in unique_id to support multi-user mode
        self._attr_unique_id = f"{coordinator.server_id}_{coordinator.user_id}_continue_watching"
        # Set custom name with user name (e.g., "troy Continue Watching")
        self._attr_name = f"{coordinator.user_name} Continue Watching"

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
            item_id = item.get("Id", "")
            series_id = item.get("SeriesId")
            image_tags = item.get("ImageTags", {})
            series_primary_tag = item.get("SeriesPrimaryImageTag")
            user_data = item.get("UserData", {})
            item_type = item.get("Type", "")

            # For episodes, prefer series image; for movies, use item image
            if item_type == "Episode" and series_id:
                image_url = self._get_series_image_url(series_id, series_primary_tag)
            else:
                image_url = self._get_image_url(item_id, image_tags)

            items.append(
                {
                    "id": item_id,
                    "name": item.get("Name"),
                    "type": item_type,
                    "series_name": item.get("SeriesName"),
                    "series_id": series_id,
                    "progress_percent": user_data.get("PlayedPercentage", 0),
                    "image_url": image_url,
                    "backdrop_url": self._get_image_url(item_id, image_tags, "Backdrop", 1280, 720),
                }
            )

        return {"items": items, "user_id": self.coordinator.user_id}


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
        # Include user_id in unique_id to support multi-user mode
        self._attr_unique_id = f"{coordinator.server_id}_{coordinator.user_id}_recently_added"
        # Set custom name with user name (e.g., "troy Recently Added")
        self._attr_name = f"{coordinator.user_name} Recently Added"

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
            item_id = item.get("Id", "")
            series_id = item.get("SeriesId")
            image_tags = item.get("ImageTags", {})
            series_primary_tag = item.get("SeriesPrimaryImageTag")
            item_type = item.get("Type", "")

            # For episodes, prefer series image; for movies/music, use item image
            if item_type == "Episode" and series_id:
                image_url = self._get_series_image_url(series_id, series_primary_tag)
            else:
                image_url = self._get_image_url(item_id, image_tags)

            items.append(
                {
                    "id": item_id,
                    "name": item.get("Name"),
                    "type": item_type,
                    "series_name": item.get("SeriesName"),
                    "series_id": series_id,
                    "year": item.get("ProductionYear"),
                    "image_url": image_url,
                    "backdrop_url": self._get_image_url(item_id, image_tags, "Backdrop", 1280, 720),
                }
            )

        return {"items": items, "user_id": self.coordinator.user_id}


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
        # Include user_id in unique_id to support multi-user mode
        self._attr_unique_id = f"{coordinator.server_id}_{coordinator.user_id}_suggestions"
        # Set custom name with user name (e.g., "troy Suggestions")
        self._attr_name = f"{coordinator.user_name} Suggestions"

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
            item_id = item.get("Id", "")
            series_id = item.get("SeriesId")
            image_tags = item.get("ImageTags", {})
            series_primary_tag = item.get("SeriesPrimaryImageTag")
            item_type = item.get("Type", "")

            # For episodes/series content, prefer series image
            if item_type in ("Episode", "Series") and series_id:
                image_url = self._get_series_image_url(series_id, series_primary_tag)
            elif item_type == "Series":
                image_url = self._get_image_url(item_id, image_tags)
            else:
                image_url = self._get_image_url(item_id, image_tags)

            items.append(
                {
                    "id": item_id,
                    "name": item.get("Name"),
                    "type": item_type,
                    "series_name": item.get("SeriesName"),
                    "series_id": series_id,
                    "rating": item.get("CommunityRating"),
                    "year": item.get("ProductionYear"),
                    "image_url": image_url,
                    "backdrop_url": self._get_image_url(item_id, image_tags, "Backdrop", 1280, 720),
                }
            )

        return {"items": items, "user_id": self.coordinator.user_id}


__all__ = [
    "EmbyContinueWatchingSensor",
    "EmbyDiscoverySensorBase",
    "EmbyNextUpSensor",
    "EmbyRecentlyAddedSensor",
    "EmbySuggestionsSensor",
]
