"""Discovery image entities for Emby integration (Phase 15).

Provides ImageEntity instances for discovery sensors, showing cover art
for the first/featured item in each discovery category.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.image import ImageEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
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
    Fetches images directly from Emby server using the coordinator's client.
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
        self._current_image_id: str | None = None
        self._update_image_id()
        if self._current_image_id:
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

    def _get_image_info(self) -> tuple[str | None, str | None]:
        """Get the item ID and image tag for the first item.

        Returns:
            Tuple of (item_id, tag) or (None, None) if no items.
        """
        items = self._get_items()
        if not items:
            return None, None

        item = items[0]
        item_id = str(item.get("Id", ""))
        if not item_id:
            return None, None

        item_type = str(item.get("Type", ""))
        series_id = item.get("SeriesId")
        image_tags: dict[str, str] = item.get("ImageTags", {})
        series_primary_tag = item.get("SeriesPrimaryImageTag")

        # For episodes, prefer series image
        if item_type == "Episode" and series_id:
            target_id = str(series_id)
            tag = str(series_primary_tag) if series_primary_tag else None
        else:
            target_id = item_id
            tag = image_tags.get("Primary")

        return target_id, tag

    def _update_image_id(self) -> None:
        """Update the current image ID from coordinator data."""
        target_id, _ = self._get_image_info()
        self._current_image_id = target_id

    async def async_image(self) -> bytes | None:
        """Return bytes of image by fetching from Emby server.

        This fetches the image directly from Emby using the client's
        credentials, avoiding the need for external URL access.
        """
        target_id, tag = self._get_image_info()
        if not target_id:
            return None

        # Build the Emby image URL
        image_url = self.coordinator.client.get_image_url(
            item_id=target_id,
            image_type="Primary",
            max_width=300,
            max_height=450,
            tag=tag,
        )

        # Fetch the image
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(image_url) as response:
                if response.status == 200:
                    content_type = response.headers.get("Content-Type", "image/jpeg")
                    self._attr_content_type = content_type
                    return await response.read()
                _LOGGER.debug(
                    "Failed to fetch image for %s: HTTP %s",
                    self.entity_id,
                    response.status,
                )
                return None
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOGGER.debug("Error fetching image for %s: %s", self.entity_id, err)
            return None

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        old_image_id = self._current_image_id
        self._update_image_id()

        if self._current_image_id != old_image_id:
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
