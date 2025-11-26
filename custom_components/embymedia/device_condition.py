"""Device conditions for Emby media players."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.const import (
    CONF_CONDITION,
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_ENTITY_ID,
    CONF_TYPE,
    STATE_IDLE,
    STATE_PAUSED,
    STATE_PLAYING,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.config_validation import DEVICE_CONDITION_BASE_SCHEMA

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.condition import ConditionCheckerType
    from homeassistant.helpers.typing import ConfigType

# Media content attribute - using string directly to avoid importing media_player
ATTR_MEDIA_CONTENT_ID = "media_content_id"

CONDITION_TYPES = frozenset(
    {
        "is_playing",
        "is_paused",
        "is_idle",
        "is_off",
        "has_media",
    }
)

CONDITION_SCHEMA = DEVICE_CONDITION_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_ENTITY_ID): cv.entity_id,
        vol.Required(CONF_TYPE): vol.In(CONDITION_TYPES),
    }
)


async def async_get_conditions(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, str]]:
    """List device conditions for Emby devices.

    Args:
        hass: Home Assistant instance.
        device_id: Device ID to get conditions for.

    Returns:
        List of condition dictionaries.
    """
    conditions: list[dict[str, str]] = []

    entity_registry = er.async_get(hass)
    entries = er.async_entries_for_device(entity_registry, device_id)

    for entry in entries:
        if entry.domain == "media_player":
            conditions.extend(
                [
                    {
                        CONF_CONDITION: "device",
                        CONF_DEVICE_ID: device_id,
                        CONF_DOMAIN: DOMAIN,
                        CONF_ENTITY_ID: entry.entity_id,
                        CONF_TYPE: condition_type,
                    }
                    for condition_type in CONDITION_TYPES
                ]
            )

    return conditions


async def async_condition_from_config(
    hass: HomeAssistant, config: ConfigType
) -> ConditionCheckerType:
    """Create a condition from config.

    Args:
        hass: Home Assistant instance.
        config: Condition configuration.

    Returns:
        Condition checker function.
    """
    entity_id: str = config[CONF_ENTITY_ID]
    condition_type: str = config[CONF_TYPE]

    def test_condition(hass: HomeAssistant) -> bool:
        """Test the condition.

        Args:
            hass: Home Assistant instance.

        Returns:
            True if condition is met, False otherwise.
        """
        state = hass.states.get(entity_id)
        if state is None:
            return False

        current_state = state.state
        if condition_type == "is_playing":
            return bool(current_state == STATE_PLAYING)
        if condition_type == "is_paused":
            return bool(current_state == STATE_PAUSED)
        if condition_type == "is_idle":
            return bool(current_state == STATE_IDLE)
        if condition_type == "is_off":
            return bool(current_state == "off")
        if condition_type == "has_media":
            return state.attributes.get(ATTR_MEDIA_CONTENT_ID) is not None

        return False

    return test_condition


async def async_get_condition_capabilities(
    hass: HomeAssistant, config: ConfigType
) -> dict[str, vol.Schema]:
    """List condition capabilities.

    Args:
        hass: Home Assistant instance.
        config: Condition configuration.

    Returns:
        Empty dict as no extra capabilities needed.
    """
    return {}
