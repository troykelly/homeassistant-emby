"""Media player platform for Emby."""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import EmbyConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EmbyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Emby media player from a config entry.

    Args:
        hass: Home Assistant instance.
        entry: Config entry for this platform.
        async_add_entities: Callback to add entities.
    """
    # Phase 2: Will add media player entities here
    _LOGGER.debug("Emby media player platform setup (placeholder)")
