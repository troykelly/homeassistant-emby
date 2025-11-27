"""Diagnostics support for Emby integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_API_KEY

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceEntry

    from .const import EmbyRuntimeData
    from .coordinator import EmbyDataUpdateCoordinator

# Keys to redact from diagnostics output
TO_REDACT = {CONF_API_KEY, "api_key", "token", "password"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry[EmbyRuntimeData],
) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    Args:
        hass: Home Assistant instance.
        entry: Config entry to get diagnostics for.

    Returns:
        Dictionary containing diagnostic information.
    """
    coordinator: EmbyDataUpdateCoordinator = entry.runtime_data.session_coordinator

    # Build session list
    sessions_list: list[dict[str, str | bool]] = []
    if coordinator.data:
        for session in coordinator.data.values():
            sessions_list.append(
                {
                    "device_id": session.device_id,
                    "device_name": session.device_name,
                    "client": session.client_name,
                    "is_playing": session.now_playing is not None,
                }
            )

    # Get cache stats
    cache_stats: dict[str, int] = coordinator.client.browse_cache.get_stats()

    return {
        "config_entry": {
            "entry_id": entry.entry_id,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "server_info": {
            "server_id": coordinator.server_id,
            "server_name": coordinator.server_name,
        },
        "connection_status": {
            "websocket_enabled": coordinator._websocket_enabled,
            "last_update_success": coordinator.last_update_success,
            "update_interval": str(coordinator.update_interval),
        },
        "sessions": {
            "active_count": len(coordinator.data) if coordinator.data else 0,
            "sessions": sessions_list,
        },
        "cache_stats": cache_stats,
    }


async def async_get_device_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry[EmbyRuntimeData],
    device: DeviceEntry,
) -> dict[str, Any]:
    """Return diagnostics for a device.

    Args:
        hass: Home Assistant instance.
        entry: Config entry the device belongs to.
        device: Device to get diagnostics for.

    Returns:
        Dictionary containing device diagnostic information.
    """
    coordinator: EmbyDataUpdateCoordinator = entry.runtime_data.session_coordinator

    # Find device_id from device identifiers
    device_id: str | None = None
    for identifier in device.identifiers:
        if identifier[0] == DOMAIN:
            device_id = identifier[1]
            break

    if device_id is None:
        return {"error": "Device not found"}

    # Get session for this device
    session = (coordinator.data or {}).get(device_id)

    if session is None:
        return {"device_id": device_id, "status": "offline"}

    # Get play state info
    play_state_info: dict[str, bool | float | None] = {}
    if session.play_state:
        play_state_info = {
            "is_paused": session.play_state.is_paused,
            "volume_level": session.play_state.volume_level,
            "is_muted": session.play_state.is_muted,
        }

    # Get now playing info
    now_playing_info: dict[str, str | None] | None = None
    if session.now_playing:
        media_type_value: str | None = None
        if session.now_playing.media_type is not None:
            media_type_value = session.now_playing.media_type.value
        now_playing_info = {
            "item_id": session.now_playing.item_id,
            "name": session.now_playing.name,
            "type": media_type_value,
        }

    return {
        "device_id": device_id,
        "status": "online",
        "device_name": session.device_name,
        "client": session.client_name,
        "application_version": session.app_version,
        "supports_remote_control": session.supports_remote_control,
        "supported_commands": session.supported_commands,
        "playback_state": play_state_info,
        "now_playing": now_playing_info,
    }
