"""Image platform for Emby integration.

Provides ImageEntity instances for discovery sensors, showing cover art
for the first/featured item in each discovery category.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.image import ImageEntity

from .image_discovery import (
    EmbyContinueWatchingImage,
    EmbyNextUpImage,
    EmbyRecentlyAddedImage,
    EmbySuggestionsImage,
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
    """Set up Emby image entities from a config entry.

    Args:
        hass: Home Assistant instance.
        config_entry: Config entry for the integration.
        async_add_entities: Callback to add entities.
    """
    runtime_data = config_entry.runtime_data
    discovery_coordinators = runtime_data.discovery_coordinators
    server_name = runtime_data.server_coordinator.server_name

    entities: list[ImageEntity] = []

    # Add discovery image entities for each user's coordinator
    for coordinator in discovery_coordinators.values():
        entities.extend(
            [
                EmbyNextUpImage(hass, coordinator, server_name),
                EmbyContinueWatchingImage(hass, coordinator, server_name),
                EmbyRecentlyAddedImage(hass, coordinator, server_name),
                EmbySuggestionsImage(hass, coordinator, server_name),
            ]
        )

    if entities:
        _LOGGER.debug("Adding %d discovery image entities", len(entities))
        async_add_entities(entities)


__all__ = [
    "async_setup_entry",
]
