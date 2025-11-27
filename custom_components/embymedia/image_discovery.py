"""Discovery image entities for Emby integration (Phase 15).

Provides ImageEntity instances for discovery sensors, showing cover art
for the first/featured item in each discovery category.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.image import ImageEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator_discovery import EmbyDiscoveryCoordinator

if TYPE_CHECKING:
    from typing import Any

    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


# =============================================================================
# Base Class for Discovery Images
# =============================================================================


class EmbyDiscoveryImageBase(
    CoordinatorEntity[EmbyDiscoveryCoordinator],
    ImageEntity,
):
    """Base class for Emby discovery image entities.

    Shows the cover art for the first item in a discovery category.
    Uses the HA image proxy to serve images without exposing API keys.
    """

    _attr_has_entity_name = True
    _discovery_key: str = ""  # Override in subclasses

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: EmbyDiscoveryCoordinator,
        server_name: str,
    ) -> None:
        """Initialize the discovery image entity.

        Args:
            hass: Home Assistant instance.
            coordinator: The discovery data coordinator.
            server_name: The server name for device info.
        """
        CoordinatorEntity.__init__(self, coordinator)
        ImageEntity.__init__(self, hass)
        self._server_name = server_name
        self._attr_image_url = self._get_image_url()
        if self._attr_image_url:
            self._attr_image_last_updated = dt_util.utcnow()
        else:
            self._attr_image_last_updated = None

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
        return bool(self.coordinator.last_update_success)

    def _get_items(self) -> list[dict[str, Any]]:
        """Get the items list for this discovery type.

        Override in subclasses to return the appropriate list.
        """
        if self.coordinator.data is None:
            return []
        items: list[dict[str, Any]] = self.coordinator.data.get(self._discovery_key, [])
        return items

    def _get_image_url(self) -> str | None:
        """Generate the proxy image URL for the first item.

        Returns:
            Proxy URL string or None if no items.
        """
        items = self._get_items()
        if not items:
            return None

        item = items[0]
        item_id = str(item.get("Id", ""))
        if not item_id:
            return None

        item_type = str(item.get("Type", ""))
        series_id = item.get("SeriesId")
        image_tags: dict[str, str] = item.get("ImageTags", {})
        series_primary_tag = item.get("SeriesPrimaryImageTag")

        # For episodes, prefer series image
        if item_type == "Episode" and series_id:
            target_id = str(series_id)
            tag = series_primary_tag
        else:
            target_id = item_id
            tag = image_tags.get("Primary")

        # Build proxy URL
        url = f"/api/embymedia/image/{self.coordinator.server_id}/{target_id}/Primary"
        params: list[str] = ["maxWidth=300", "maxHeight=450"]
        if tag:
            params.append(f"tag={tag}")

        return f"{url}?{'&'.join(params)}"

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        new_url = self._get_image_url()

        if new_url != self._attr_image_url:
            self._attr_image_url = new_url
            self._cached_image = None
            self._attr_image_last_updated = dt_util.utcnow()

        super()._handle_coordinator_update()


# =============================================================================
# Next Up Image
# =============================================================================


class EmbyNextUpImage(EmbyDiscoveryImageBase):
    """Image entity showing cover art for next up episode."""

    _attr_translation_key = "next_up_image"
    _discovery_key = "next_up"

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: EmbyDiscoveryCoordinator,
        server_name: str,
    ) -> None:
        """Initialize the next up image entity."""
        self._attr_unique_id = f"{coordinator.server_id}_{coordinator.user_id}_next_up_image"
        self._attr_name = f"{coordinator.user_name} Next Up"
        super().__init__(hass, coordinator, server_name)


# =============================================================================
# Continue Watching Image
# =============================================================================


class EmbyContinueWatchingImage(EmbyDiscoveryImageBase):
    """Image entity showing cover art for continue watching item."""

    _attr_translation_key = "continue_watching_image"
    _discovery_key = "continue_watching"

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: EmbyDiscoveryCoordinator,
        server_name: str,
    ) -> None:
        """Initialize the continue watching image entity."""
        self._attr_unique_id = (
            f"{coordinator.server_id}_{coordinator.user_id}_continue_watching_image"
        )
        self._attr_name = f"{coordinator.user_name} Continue Watching"
        super().__init__(hass, coordinator, server_name)


# =============================================================================
# Recently Added Image
# =============================================================================


class EmbyRecentlyAddedImage(EmbyDiscoveryImageBase):
    """Image entity showing cover art for recently added item."""

    _attr_translation_key = "recently_added_image"
    _discovery_key = "recently_added"

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: EmbyDiscoveryCoordinator,
        server_name: str,
    ) -> None:
        """Initialize the recently added image entity."""
        self._attr_unique_id = f"{coordinator.server_id}_{coordinator.user_id}_recently_added_image"
        self._attr_name = f"{coordinator.user_name} Recently Added"
        super().__init__(hass, coordinator, server_name)


# =============================================================================
# Suggestions Image
# =============================================================================


class EmbySuggestionsImage(EmbyDiscoveryImageBase):
    """Image entity showing cover art for suggested item."""

    _attr_translation_key = "suggestions_image"
    _discovery_key = "suggestions"

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: EmbyDiscoveryCoordinator,
        server_name: str,
    ) -> None:
        """Initialize the suggestions image entity."""
        self._attr_unique_id = f"{coordinator.server_id}_{coordinator.user_id}_suggestions_image"
        self._attr_name = f"{coordinator.user_name} Suggestions"
        super().__init__(hass, coordinator, server_name)


__all__ = [
    "EmbyContinueWatchingImage",
    "EmbyDiscoveryImageBase",
    "EmbyNextUpImage",
    "EmbyRecentlyAddedImage",
    "EmbySuggestionsImage",
]
