"""Device triggers for Emby media players."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_ENTITY_ID,
    CONF_PLATFORM,
    CONF_TYPE,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import CALLBACK_TYPE, HomeAssistant
    from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
    from homeassistant.helpers.typing import ConfigType

TRIGGER_TYPES = frozenset(
    {
        "playback_started",
        "playback_stopped",
        "playback_paused",
        "playback_resumed",
        "media_changed",
        "session_connected",
        "session_disconnected",
    }
)

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_ENTITY_ID): cv.entity_id,
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
    }
)


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, str]]:
    """List device triggers for Emby devices.

    Args:
        hass: Home Assistant instance.
        device_id: Device ID to get triggers for.

    Returns:
        List of trigger dictionaries.
    """
    triggers: list[dict[str, str]] = []

    entity_registry = er.async_get(hass)
    entries = er.async_entries_for_device(entity_registry, device_id)

    for entry in entries:
        if entry.domain == "media_player":
            triggers.extend(
                [
                    {
                        CONF_PLATFORM: "device",
                        CONF_DEVICE_ID: device_id,
                        CONF_DOMAIN: DOMAIN,
                        CONF_ENTITY_ID: entry.entity_id,
                        CONF_TYPE: trigger_type,
                    }
                    for trigger_type in TRIGGER_TYPES
                ]
            )

    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a trigger.

    Args:
        hass: Home Assistant instance.
        config: Trigger configuration.
        action: Action to call when triggered.
        trigger_info: Trigger info for context.

    Returns:
        Callback to unsubscribe from trigger.
    """
    entity_id: str = config[CONF_ENTITY_ID]
    trigger_type: str = config[CONF_TYPE]

    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: f"{DOMAIN}_event",
            event_trigger.CONF_EVENT_DATA: {
                CONF_ENTITY_ID: entity_id,
                CONF_TYPE: trigger_type,
            },
        }
    )
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )


async def async_get_trigger_capabilities(
    hass: HomeAssistant, config: ConfigType
) -> dict[str, vol.Schema]:
    """List trigger capabilities.

    Args:
        hass: Home Assistant instance.
        config: Trigger configuration.

    Returns:
        Empty dict as no extra capabilities needed.
    """
    return {}
