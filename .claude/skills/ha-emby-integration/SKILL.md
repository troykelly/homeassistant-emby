---
name: ha-emby-integration
description: Use when implementing Home Assistant integration code - covers Nov 2025 best practices for config flows, coordinators, entities, async patterns, manifest, translations, and project structure. Required reading before writing any HA code.
---

# Home Assistant Emby Integration Best Practices

## Overview

**Follow Home Assistant 2025 integration patterns exactly.**

This covers config flows, data coordinators, entity patterns, and project structure per current Home Assistant core standards.

## Project Structure

```
custom_components/embymedia/
├── __init__.py           # Integration setup
├── manifest.json         # Integration metadata
├── config_flow.py        # UI configuration flow
├── const.py              # Constants and types
├── coordinator.py        # Data update coordinator
├── media_player.py       # Media player entity
├── entity.py             # Base entity class
├── api.py                # Emby API client wrapper
├── strings.json          # English translations
├── translations/         # Other languages
│   └── en.json
└── services.yaml         # Service definitions (if any)

tests/
├── conftest.py           # Test fixtures
├── test_init.py          # Setup tests
├── test_config_flow.py   # Config flow tests
├── test_media_player.py  # Entity tests
└── test_coordinator.py   # Coordinator tests
```

## manifest.json (2025 Format)

```json
{
  "domain": "emby",
  "name": "Emby",
  "codeowners": ["@username"],
  "config_flow": true,
  "documentation": "https://github.com/username/ha-emby",
  "iot_class": "local_push",
  "issue_tracker": "https://github.com/username/ha-emby/issues",
  "requirements": ["embypy>=0.8.0"],
  "version": "1.0.0",
  "integration_type": "hub"
}
```

**Key fields:**
- `config_flow: true` - Required for UI setup
- `iot_class: local_push` - Emby uses websockets for updates
- `integration_type: hub` - Manages multiple devices

## __init__.py Pattern

```python
"""The Emby integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import EmbyDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER]

type EmbyConfigEntry = ConfigEntry[EmbyDataUpdateCoordinator]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EmbyConfigEntry,
) -> bool:
    """Set up Emby from a config entry."""
    coordinator = EmbyDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: EmbyConfigEntry,
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

## Config Flow Pattern

```python
"""Config flow for Emby integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_PORT

from .api import EmbyApiClient, EmbyApiError, EmbyAuthError
from .const import DOMAIN, DEFAULT_PORT

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_API_KEY): str,
    }
)


class EmbyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Emby."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            client = EmbyApiClient(
                host=user_input[CONF_HOST],
                port=user_input[CONF_PORT],
                api_key=user_input[CONF_API_KEY],
            )

            try:
                server_info = await client.async_get_server_info()
            except EmbyAuthError:
                errors["base"] = "invalid_auth"
            except EmbyApiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(server_info.server_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=server_info.server_name,
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
```

## Data Update Coordinator

```python
"""Data update coordinator for Emby."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import EmbyApiClient, EmbyApiError
from .const import DOMAIN
from .models import EmbyData

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=30)


class EmbyDataUpdateCoordinator(DataUpdateCoordinator[EmbyData]):
    """Class to manage fetching Emby data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = EmbyApiClient(
            host=entry.data[CONF_HOST],
            port=entry.data[CONF_PORT],
            api_key=entry.data[CONF_API_KEY],
        )

    async def _async_update_data(self) -> EmbyData:
        """Fetch data from Emby."""
        try:
            sessions = await self.client.async_get_sessions()
            return EmbyData(sessions=sessions)
        except EmbyApiError as err:
            raise UpdateFailed(f"Error communicating with Emby: {err}") from err
```

## Entity Base Class

```python
"""Base entity for Emby."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EmbyDataUpdateCoordinator


class EmbyEntity(CoordinatorEntity[EmbyDataUpdateCoordinator]):
    """Base entity for Emby."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{coordinator.config_entry.unique_id}_{device_id}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            manufacturer="Emby",
            name=self._get_device_name(),
            via_device=(DOMAIN, self.coordinator.config_entry.unique_id),
        )

    def _get_device_name(self) -> str:
        """Get the device name from coordinator data."""
        # Implement based on your data structure
        ...
```

## strings.json

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Connect to Emby Server",
        "description": "Enter your Emby server details",
        "data": {
          "host": "Host",
          "port": "Port",
          "api_key": "API Key"
        }
      }
    },
    "error": {
      "cannot_connect": "Failed to connect",
      "invalid_auth": "Invalid API key"
    },
    "abort": {
      "already_configured": "Server is already configured"
    }
  },
  "entity": {
    "media_player": {
      "emby_player": {
        "name": "Player"
      }
    }
  }
}
```

## Async Best Practices

### Never Block the Event Loop

```python
# WRONG - Blocking I/O
def get_data(self) -> dict:
    response = requests.get(url)  # Blocks!
    return response.json()

# CORRECT - Async I/O
async def async_get_data(self) -> dict[str, str]:
    async with self._session.get(url) as response:
        return await response.json()
```

### Properties Never Do I/O

```python
# WRONG - Property makes network call
@property
def media_title(self) -> str | None:
    return self._client.get_now_playing().title  # Bad!

# CORRECT - Property returns cached data
@property
def media_title(self) -> str | None:
    if self._now_playing is None:
        return None
    return self._now_playing.title
```

### Use Coordinator for Data Updates

```python
# Data comes from coordinator, not direct API calls
@property
def state(self) -> MediaPlayerState | None:
    """Return the state of the player."""
    session = self.coordinator.data.get_session(self._device_id)
    if session is None:
        return MediaPlayerState.OFF
    if session.is_paused:
        return MediaPlayerState.PAUSED
    if session.is_playing:
        return MediaPlayerState.PLAYING
    return MediaPlayerState.IDLE
```

## Error Handling

### ConfigEntryAuthFailed for Auth Errors

```python
from homeassistant.exceptions import ConfigEntryAuthFailed

async def _async_update_data(self) -> EmbyData:
    try:
        return await self.client.async_get_data()
    except EmbyAuthError as err:
        raise ConfigEntryAuthFailed(err) from err
    except EmbyApiError as err:
        raise UpdateFailed(err) from err
```

### Reauth Flow

```python
async def async_step_reauth(
    self,
    entry_data: Mapping[str, Any],
) -> ConfigFlowResult:
    """Handle reauthorization."""
    return await self.async_step_reauth_confirm()

async def async_step_reauth_confirm(
    self,
    user_input: dict[str, Any] | None = None,
) -> ConfigFlowResult:
    """Confirm reauthorization."""
    errors: dict[str, str] = {}

    if user_input is not None:
        # Validate new credentials
        ...
        return self.async_update_reload_and_abort(
            self._get_reauth_entry(),
            data_updates=user_input,
        )

    return self.async_show_form(
        step_id="reauth_confirm",
        data_schema=REAUTH_SCHEMA,
        errors=errors,
    )
```

## Testing Requirements

**100% coverage for:**
- `config_flow.py` - All steps, errors, abort cases
- `__init__.py` - Setup, unload, migration
- Entity state transitions
- Coordinator update failures

See **ha-emby-tdd** skill for testing patterns.

## The Bottom Line

**Follow current HA patterns exactly. Don't invent new patterns.**

- Config flow for setup
- Coordinator for data
- CoordinatorEntity base class
- Typed ConfigEntry with runtime_data
- Async everything, properties never do I/O
