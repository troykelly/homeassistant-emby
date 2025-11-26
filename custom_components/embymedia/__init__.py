"""The Emby integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EmbyClient
from .const import (
    CONF_API_KEY,
    CONF_SCAN_INTERVAL,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SSL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    PLATFORMS,
    EmbyConfigEntry,
)
from .coordinator import EmbyDataUpdateCoordinator
from .exceptions import EmbyAuthenticationError, EmbyConnectionError
from .image import async_setup_image_proxy
from .services import async_setup_services, async_unload_services

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: EmbyConfigEntry) -> bool:
    """Set up Emby from a config entry.

    Args:
        hass: Home Assistant instance.
        entry: Config entry to set up.

    Returns:
        True if setup was successful.

    Raises:
        ConfigEntryAuthFailed: If authentication fails.
        ConfigEntryNotReady: If server is temporarily unavailable.
    """
    session = async_get_clientsession(hass)

    client = EmbyClient(
        host=str(entry.data[CONF_HOST]),
        port=int(entry.data[CONF_PORT]),
        api_key=str(entry.data[CONF_API_KEY]),
        ssl=bool(entry.data.get(CONF_SSL, DEFAULT_SSL)),
        verify_ssl=bool(entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)),
        session=session,
    )

    try:
        await client.async_validate_connection()
        server_info = await client.async_get_server_info()
    except EmbyAuthenticationError as err:
        raise ConfigEntryAuthFailed(
            f"Invalid API key for Emby server at {entry.data[CONF_HOST]}"
        ) from err
    except EmbyConnectionError as err:
        raise ConfigEntryNotReady(
            f"Unable to connect to Emby server at {entry.data[CONF_HOST]}: {err}"
        ) from err

    server_id = str(server_info.get("Id", ""))
    server_name = str(server_info.get("ServerName", "Unknown"))
    scan_interval = int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))

    # Create coordinator
    coordinator = EmbyDataUpdateCoordinator(
        hass=hass,
        client=client,
        server_id=server_id,
        server_name=server_name,
        scan_interval=scan_interval,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator in runtime_data
    entry.runtime_data = coordinator

    # Register server device BEFORE forwarding to platforms
    # This prevents the via_device warning where entities reference
    # a server device that doesn't exist yet
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, server_id)},
        manufacturer="Emby",
        model="Emby Server",
        name=server_name,
        sw_version=str(server_info.get("Version", "Unknown")),
    )

    # Register image proxy view (only once, for first config entry)
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    if "image_proxy_registered" not in hass.data[DOMAIN]:
        await async_setup_image_proxy(hass)
        hass.data[DOMAIN]["image_proxy_registered"] = True

    # Set up services (only once, for first config entry)
    await async_setup_services(hass)

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Start WebSocket for real-time updates
    try:
        await coordinator.async_setup_websocket(session)
    except Exception:  # pylint: disable=broad-exception-caught
        _LOGGER.warning(
            "Failed to set up WebSocket connection to Emby server %s. "
            "Falling back to polling only.",
            server_name,
        )

    # Register cleanup callbacks
    entry.async_on_unload(entry.add_update_listener(async_options_updated))
    entry.async_on_unload(coordinator.async_shutdown_websocket)

    _LOGGER.info(
        "Connected to Emby server: %s (version %s)",
        server_name,
        server_info.get("Version", "Unknown"),
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: EmbyConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass: Home Assistant instance.
        entry: Config entry to unload.

    Returns:
        True if unload was successful.
    """
    unload_ok: bool = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Unload services if this is the last config entry
        loaded_entries = [
            e for e in hass.config_entries.async_entries(DOMAIN) if e.entry_id != entry.entry_id
        ]
        if not loaded_entries:
            await async_unload_services(hass)
        _LOGGER.info("Unloaded Emby integration for entry %s", entry.entry_id)

    return unload_ok


async def async_options_updated(hass: HomeAssistant, entry: EmbyConfigEntry) -> None:
    """Handle options update.

    Args:
        hass: Home Assistant instance.
        entry: Config entry with updated options.
    """
    _LOGGER.debug("Emby options updated, reloading integration")
    await hass.config_entries.async_reload(entry.entry_id)
