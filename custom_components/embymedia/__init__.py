"""The Emby integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EmbyClient
from .const import (
    CONF_API_KEY,
    CONF_SCAN_INTERVAL,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SSL,
    DEFAULT_VERIFY_SSL,
    PLATFORMS,
    EmbyConfigEntry,
)
from .coordinator import EmbyDataUpdateCoordinator
from .exceptions import EmbyAuthenticationError, EmbyConnectionError

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

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register options update listener
    entry.async_on_unload(entry.add_update_listener(async_options_updated))

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
