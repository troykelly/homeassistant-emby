"""The Emby integration.

Supports both YAML configuration and UI-based config flow.

YAML Configuration Example:
    embymedia:
      host: emby.local
      api_key: !secret emby_api_key
      port: 8096
      ssl: false
      verify_ssl: true
      scan_interval: 10
      enable_websocket: true
      ignored_devices: "Device1,Device2"
      direct_play: true
      video_container: mp4
      max_video_bitrate: 10000
      max_audio_bitrate: 320
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Final

import voluptuous as vol
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import EmbyClient
from .const import (
    CONF_API_KEY,
    CONF_DIRECT_PLAY,
    CONF_ENABLE_WEBSOCKET,
    CONF_IGNORE_WEB_PLAYERS,
    CONF_IGNORED_DEVICES,
    CONF_MAX_AUDIO_BITRATE,
    CONF_MAX_VIDEO_BITRATE,
    CONF_SCAN_INTERVAL,
    CONF_VERIFY_SSL,
    CONF_VIDEO_CONTAINER,
    DEFAULT_DIRECT_PLAY,
    DEFAULT_ENABLE_WEBSOCKET,
    DEFAULT_IGNORE_WEB_PLAYERS,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SSL,
    DEFAULT_VERIFY_SSL,
    DEFAULT_VIDEO_CONTAINER,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    PLATFORMS,
    VIDEO_CONTAINERS,
    EmbyConfigEntry,
)
from .coordinator import EmbyDataUpdateCoordinator
from .exceptions import EmbyAuthenticationError, EmbyConnectionError
from .image import async_setup_image_proxy
from .services import async_setup_services, async_unload_services

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# YAML Configuration Schema
CONFIG_SCHEMA: Final = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Required(CONF_API_KEY): cv.string,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
                vol.Optional(CONF_SSL, default=DEFAULT_SSL): cv.boolean,
                vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): cv.boolean,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): vol.All(
                    cv.positive_int,
                    vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                ),
                vol.Optional(
                    CONF_ENABLE_WEBSOCKET, default=DEFAULT_ENABLE_WEBSOCKET
                ): cv.boolean,
                vol.Optional(CONF_IGNORED_DEVICES, default=""): cv.string,
                vol.Optional(
                    CONF_IGNORE_WEB_PLAYERS, default=DEFAULT_IGNORE_WEB_PLAYERS
                ): cv.boolean,
                vol.Optional(CONF_DIRECT_PLAY, default=DEFAULT_DIRECT_PLAY): cv.boolean,
                vol.Optional(
                    CONF_VIDEO_CONTAINER, default=DEFAULT_VIDEO_CONTAINER
                ): vol.In(VIDEO_CONTAINERS),
                vol.Optional(CONF_MAX_VIDEO_BITRATE): cv.positive_int,
                vol.Optional(CONF_MAX_AUDIO_BITRATE): cv.positive_int,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Emby integration from YAML configuration.

    This function handles YAML-based configuration by triggering the
    config flow import process, which converts YAML config to a
    config entry.

    Args:
        hass: Home Assistant instance.
        config: Full configuration dictionary.

    Returns:
        True to indicate setup was successful.

    Example YAML:
        embymedia:
          host: emby.local
          api_key: !secret emby_api_key
          ssl: true
          port: 443
    """
    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]
    _LOGGER.info(
        "Importing Emby configuration from YAML for host: %s",
        conf.get(CONF_HOST),
    )

    # Trigger the config flow import step
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "import"},
            data=conf,
        )
    )

    return True


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
        config_entry=entry,
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
