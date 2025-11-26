# Phase 8: Advanced Features

## Overview

This phase implements advanced features for power users including multi-user support, remote control capabilities, library management, and automation triggers.

**Features:**
- Multiple users support with per-user authentication
- Remote control features (messages, notifications, navigation)
- Library management services (played status, favorites, library scan)
- Automation triggers and conditions for playback events

## Dependencies

- Phase 1-7.5 complete
- Emby REST API endpoints for user management
- Home Assistant services framework
- Home Assistant device triggers platform

---

## Task 8.1: Multiple Users Support

Enable per-user authentication and user-specific libraries.

### 8.1.1 Add User Selection to Config Flow

**File:** `custom_components/embymedia/config_flow.py`

Add a user selection step after initial connection:

```python
async def async_step_user_select(
    self, user_input: dict[str, Any] | None = None
) -> ConfigFlowResult:
    """Handle user selection step."""
    if user_input is not None:
        self._user_id = user_input[CONF_USER_ID]
        return await self.async_step_finish()

    # Fetch users from server
    users = await self._client.async_get_users()

    return self.async_show_form(
        step_id="user_select",
        data_schema=vol.Schema({
            vol.Required(CONF_USER_ID): vol.In({
                user["Id"]: user["Name"] for user in users
            }),
        }),
    )
```

**Acceptance Criteria:**
- [ ] Config flow shows user selection after connection validation
- [ ] User ID stored in config entry data
- [ ] Optional "Use admin context" for API key auth (no user)

**Test Cases:**
- [ ] `test_config_flow_user_selection`
- [ ] `test_config_flow_user_selection_skipped`

### 8.1.2 Store User Context in Coordinator

**File:** `custom_components/embymedia/coordinator.py`

Add user ID tracking:

```python
class EmbyDataUpdateCoordinator:
    """Coordinator with user context."""

    def __init__(
        self,
        ...
        user_id: str | None = None,
    ) -> None:
        """Initialize with user context."""
        self._user_id = user_id

    @property
    def user_id(self) -> str | None:
        """Return configured user ID."""
        return self._user_id
```

**Acceptance Criteria:**
- [ ] User ID passed from config entry to coordinator
- [ ] API calls use user context when available
- [ ] Fallback to first user if not specified

**Test Cases:**
- [ ] `test_coordinator_with_user_id`
- [ ] `test_coordinator_without_user_id_fallback`

### 8.1.3 User-Specific Libraries

**File:** `custom_components/embymedia/media_player.py`

Use user context for library browsing:

```python
async def async_browse_media(
    self,
    media_content_type: MediaType | str | None = None,
    media_content_id: str | None = None,
) -> BrowseMedia:
    """Browse media with user context."""
    user_id = self._get_user_id()
    # Use user_id for all library API calls
```

**Acceptance Criteria:**
- [ ] Browse media uses configured user context
- [ ] User-specific favorites and restrictions respected
- [ ] Playback uses user's playback settings

**Test Cases:**
- [ ] `test_browse_media_with_user_context`
- [ ] `test_browse_media_respects_user_restrictions`

### 8.1.4 Options Flow for User Switching

**File:** `custom_components/embymedia/config_flow.py`

Add user switch to options flow:

```python
async def async_step_init(
    self, user_input: dict[str, Any] | None = None
) -> ConfigFlowResult:
    """Handle options flow."""
    # ... existing options ...

    # Add user selection option
    users = await self._get_users()
    schema = vol.Schema({
        # ... existing options ...
        vol.Optional(CONF_USER_ID, default=current_user): vol.In(users),
    })
```

**Acceptance Criteria:**
- [ ] Options flow allows user switching
- [ ] User change triggers integration reload
- [ ] User avatars shown in selection (optional)

**Test Cases:**
- [ ] `test_options_flow_user_switch`
- [ ] `test_options_flow_user_switch_reloads`

---

## Task 8.2: Remote Control Features

Send messages, notifications, and navigation commands to Emby clients.

### 8.2.1 Add Remote Control Services

**File:** `custom_components/embymedia/services.py` (new file)

Define services schema:

```python
SERVICE_SEND_MESSAGE = "send_message"
SERVICE_SEND_NOTIFICATION = "send_notification"
SERVICE_SEND_COMMAND = "send_command"

ATTR_MESSAGE = "message"
ATTR_HEADER = "header"
ATTR_TIMEOUT_MS = "timeout_ms"
ATTR_COMMAND = "command"
ATTR_ARGUMENTS = "arguments"

SEND_MESSAGE_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Required(ATTR_MESSAGE): cv.string,
    vol.Optional(ATTR_HEADER, default=""): cv.string,
    vol.Optional(ATTR_TIMEOUT_MS, default=5000): vol.Coerce(int),
})

SEND_COMMAND_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Required(ATTR_COMMAND): cv.string,
    vol.Optional(ATTR_ARGUMENTS): vol.Schema({str: cv.string}),
})
```

**Acceptance Criteria:**
- [ ] Service schemas defined with validation
- [ ] Services registered on integration setup
- [ ] Services unregistered on unload

**Test Cases:**
- [ ] `test_service_schemas_valid`
- [ ] `test_services_registered_on_setup`

### 8.2.2 Implement Send Message API

**File:** `custom_components/embymedia/api.py`

Add message endpoint:

```python
async def async_send_message(
    self,
    session_id: str,
    text: str,
    header: str = "",
    timeout_ms: int = 5000,
) -> None:
    """Send a message to a session.

    Displays a message overlay on the Emby client.

    Args:
        session_id: Target session ID.
        text: Message body text.
        header: Optional message header.
        timeout_ms: Display duration in milliseconds.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    endpoint = f"/Sessions/{session_id}/Message"
    data = {
        "Text": text,
        "Header": header,
        "TimeoutMs": timeout_ms,
    }
    await self._request_post(endpoint, data=data)
```

**Emby Endpoint:** `POST /Sessions/{id}/Message`

**Acceptance Criteria:**
- [ ] Message sent to Emby client
- [ ] Header and timeout configurable
- [ ] Error handling for unreachable clients

**Test Cases:**
- [ ] `test_send_message_success`
- [ ] `test_send_message_with_header`
- [ ] `test_send_message_client_unavailable`

### 8.2.3 Implement Send Command API

**File:** `custom_components/embymedia/api.py`

Add general command endpoint:

```python
async def async_send_general_command_extended(
    self,
    session_id: str,
    command: str,
    arguments: dict[str, str] | None = None,
) -> None:
    """Send a general command to a session.

    Supported commands:
    - MoveUp, MoveDown, MoveLeft, MoveRight
    - Select, Back, Home
    - GoToSettings, GoToSearch
    - ToggleFullscreen
    - DisplayContent, DisplayMessage

    Args:
        session_id: Target session ID.
        command: Command name.
        arguments: Optional command arguments.
    """
    endpoint = f"/Sessions/{session_id}/Command"
    data: dict[str, str | dict[str, str]] = {"Name": command}
    if arguments:
        data["Arguments"] = arguments
    await self._request_post(endpoint, data=data)
```

**Emby Endpoint:** `POST /Sessions/{id}/Command`

**Supported Commands:**
| Command | Description |
|---------|-------------|
| `MoveUp` | Navigate up |
| `MoveDown` | Navigate down |
| `MoveLeft` | Navigate left |
| `MoveRight` | Navigate right |
| `Select` | Select current item |
| `Back` | Go back |
| `Home` | Go to home screen |
| `GoToSettings` | Open settings |
| `GoToSearch` | Open search |
| `ToggleFullscreen` | Toggle fullscreen mode |
| `DisplayContent` | Navigate to item (ItemId arg) |
| `DisplayMessage` | Show message (Text, Header args) |

**Acceptance Criteria:**
- [ ] Commands sent to Emby client
- [ ] Arguments passed correctly
- [ ] Invalid command handling

**Test Cases:**
- [ ] `test_send_command_navigate`
- [ ] `test_send_command_with_arguments`
- [ ] `test_send_command_invalid`

### 8.2.4 Register Remote Control Services

**File:** `custom_components/embymedia/__init__.py`

Register services on setup:

```python
async def async_setup_entry(hass: HomeAssistant, entry: EmbyConfigEntry) -> bool:
    """Set up Emby with services."""
    # ... existing setup ...

    # Register services (only once)
    await async_setup_services(hass)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: EmbyConfigEntry) -> bool:
    """Unload entry and cleanup services."""
    # ... existing unload ...

    # Unregister services if last entry
    if not hass.config_entries.async_entries(DOMAIN):
        await async_unload_services(hass)

    return unload_ok
```

**Acceptance Criteria:**
- [ ] Services available in HA Developer Tools
- [ ] Services target correct entities
- [ ] Services cleaned up on unload

**Test Cases:**
- [ ] `test_services_available_after_setup`
- [ ] `test_services_removed_on_unload`

### 8.2.5 Service Handlers in Media Player

**File:** `custom_components/embymedia/media_player.py`

Add service handler methods:

```python
async def async_send_message(
    self,
    text: str,
    header: str = "",
    timeout_ms: int = 5000,
) -> None:
    """Send message to this media player."""
    if not self._session:
        raise HomeAssistantError("No active session")

    await self._client.async_send_message(
        session_id=self._session.session_id,
        text=text,
        header=header,
        timeout_ms=timeout_ms,
    )

async def async_send_command(
    self,
    command: str,
    arguments: dict[str, str] | None = None,
) -> None:
    """Send command to this media player."""
    if not self._session:
        raise HomeAssistantError("No active session")

    await self._client.async_send_general_command_extended(
        session_id=self._session.session_id,
        command=command,
        arguments=arguments,
    )
```

**Acceptance Criteria:**
- [ ] Entity methods callable from services
- [ ] Error when no active session
- [ ] Proper error propagation

**Test Cases:**
- [ ] `test_entity_send_message`
- [ ] `test_entity_send_command`
- [ ] `test_entity_no_session_error`

---

## Task 8.3: Library Management Services

Manage item states and trigger library operations.

### 8.3.1 Mark Item Played/Unplayed API

**File:** `custom_components/embymedia/api.py`

Add played status endpoints:

```python
async def async_mark_played(
    self,
    user_id: str,
    item_id: str,
) -> None:
    """Mark an item as played.

    Args:
        user_id: User ID.
        item_id: Item ID to mark.
    """
    endpoint = f"/Users/{user_id}/PlayedItems/{item_id}"
    await self._request_post(endpoint)

async def async_mark_unplayed(
    self,
    user_id: str,
    item_id: str,
) -> None:
    """Mark an item as unplayed.

    Args:
        user_id: User ID.
        item_id: Item ID to mark.
    """
    endpoint = f"/Users/{user_id}/PlayedItems/{item_id}"
    await self._request_delete(endpoint)
```

**Emby Endpoints:**
- `POST /Users/{userId}/PlayedItems/{itemId}` - Mark played
- `DELETE /Users/{userId}/PlayedItems/{itemId}` - Mark unplayed

**Acceptance Criteria:**
- [ ] Items marked as played
- [ ] Items marked as unplayed
- [ ] User context required

**Test Cases:**
- [ ] `test_mark_item_played`
- [ ] `test_mark_item_unplayed`

### 8.3.2 Update Favorite Status API

**File:** `custom_components/embymedia/api.py`

Add favorite endpoints:

```python
async def async_add_favorite(
    self,
    user_id: str,
    item_id: str,
) -> None:
    """Add an item to favorites.

    Args:
        user_id: User ID.
        item_id: Item ID to favorite.
    """
    endpoint = f"/Users/{user_id}/FavoriteItems/{item_id}"
    await self._request_post(endpoint)

async def async_remove_favorite(
    self,
    user_id: str,
    item_id: str,
) -> None:
    """Remove an item from favorites.

    Args:
        user_id: User ID.
        item_id: Item ID to unfavorite.
    """
    endpoint = f"/Users/{user_id}/FavoriteItems/{item_id}"
    await self._request_delete(endpoint)
```

**Emby Endpoints:**
- `POST /Users/{userId}/FavoriteItems/{itemId}` - Add favorite
- `DELETE /Users/{userId}/FavoriteItems/{itemId}` - Remove favorite

**Acceptance Criteria:**
- [ ] Items added to favorites
- [ ] Items removed from favorites
- [ ] User context required

**Test Cases:**
- [ ] `test_add_favorite`
- [ ] `test_remove_favorite`

### 8.3.3 Trigger Library Scan API

**File:** `custom_components/embymedia/api.py`

Add library scan endpoint:

```python
async def async_refresh_library(
    self,
    library_id: str | None = None,
) -> None:
    """Trigger a library scan.

    Args:
        library_id: Optional specific library to refresh.
                   If None, refreshes all libraries.
    """
    endpoint = "/Library/Refresh"
    if library_id:
        endpoint = f"/Items/{library_id}/Refresh"
    await self._request_post(endpoint)

async def async_refresh_item(
    self,
    item_id: str,
    metadata_refresh: bool = True,
    image_refresh: bool = True,
) -> None:
    """Refresh metadata for a specific item.

    Args:
        item_id: Item ID to refresh.
        metadata_refresh: Whether to refresh metadata.
        image_refresh: Whether to refresh images.
    """
    params = []
    if metadata_refresh:
        params.append("MetadataRefreshMode=FullRefresh")
    if image_refresh:
        params.append("ImageRefreshMode=FullRefresh")

    query = "&".join(params) if params else ""
    endpoint = f"/Items/{item_id}/Refresh?{query}"
    await self._request_post(endpoint)
```

**Emby Endpoints:**
- `POST /Library/Refresh` - Refresh all libraries
- `POST /Items/{itemId}/Refresh` - Refresh specific item

**Acceptance Criteria:**
- [ ] Full library scan triggered
- [ ] Individual item refresh works
- [ ] Metadata/image refresh options

**Test Cases:**
- [ ] `test_refresh_all_libraries`
- [ ] `test_refresh_specific_library`
- [ ] `test_refresh_item_metadata`

### 8.3.4 Register Library Services

**File:** `custom_components/embymedia/services.py`

Add library service schemas:

```python
SERVICE_MARK_PLAYED = "mark_played"
SERVICE_MARK_UNPLAYED = "mark_unplayed"
SERVICE_ADD_FAVORITE = "add_favorite"
SERVICE_REMOVE_FAVORITE = "remove_favorite"
SERVICE_REFRESH_LIBRARY = "refresh_library"
SERVICE_REFRESH_ITEM = "refresh_item"

ATTR_ITEM_ID = "item_id"
ATTR_LIBRARY_ID = "library_id"

MARK_PLAYED_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Required(ATTR_ITEM_ID): cv.string,
})

REFRESH_LIBRARY_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Optional(ATTR_LIBRARY_ID): cv.string,
})
```

**Acceptance Criteria:**
- [ ] Library services registered
- [ ] Services callable from automations
- [ ] Error handling for invalid items

**Test Cases:**
- [ ] `test_mark_played_service`
- [ ] `test_refresh_library_service`

---

## Task 8.4: Automation Triggers

Device triggers for playback events and conditions for player state.

### 8.4.1 Create Device Trigger Platform

**File:** `custom_components/embymedia/device_trigger.py` (new file)

Implement device triggers:

```python
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

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import CALLBACK_TYPE, HomeAssistant
    from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
    from homeassistant.helpers.typing import ConfigType

TRIGGER_TYPES = {
    "playback_started",
    "playback_stopped",
    "playback_paused",
    "playback_resumed",
    "media_changed",
    "session_connected",
    "session_disconnected",
}

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend({
    vol.Required(CONF_ENTITY_ID): cv.entity_id,
    vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
})


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, str]]:
    """List device triggers for Emby devices."""
    triggers = []

    # Get entity registry entries for this device
    entity_registry = er.async_get(hass)
    entries = er.async_entries_for_device(entity_registry, device_id)

    for entry in entries:
        if entry.domain == "media_player":
            triggers.extend([
                {
                    CONF_PLATFORM: "device",
                    CONF_DEVICE_ID: device_id,
                    CONF_DOMAIN: DOMAIN,
                    CONF_ENTITY_ID: entry.entity_id,
                    CONF_TYPE: trigger_type,
                }
                for trigger_type in TRIGGER_TYPES
            ])

    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a trigger."""
    event_config = event_trigger.TRIGGER_SCHEMA({
        event_trigger.CONF_PLATFORM: "event",
        event_trigger.CONF_EVENT_TYPE: f"{DOMAIN}_event",
        event_trigger.CONF_EVENT_DATA: {
            CONF_ENTITY_ID: config[CONF_ENTITY_ID],
            CONF_TYPE: config[CONF_TYPE],
        },
    })
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )
```

**Trigger Types:**
| Type | Description |
|------|-------------|
| `playback_started` | Media playback began |
| `playback_stopped` | Media playback stopped |
| `playback_paused` | Playback paused |
| `playback_resumed` | Playback resumed from pause |
| `media_changed` | Playing media changed |
| `session_connected` | Client session connected |
| `session_disconnected` | Client session disconnected |

**Acceptance Criteria:**
- [ ] Triggers appear in automation UI
- [ ] Events fired on state changes
- [ ] Multiple entities per device supported

**Test Cases:**
- [ ] `test_get_triggers_returns_all_types`
- [ ] `test_attach_trigger_playback_started`
- [ ] `test_attach_trigger_session_connected`

### 8.4.2 Fire Events from Coordinator

**File:** `custom_components/embymedia/coordinator.py`

Fire events on state changes:

```python
def _handle_sessions_message(
    self,
    sessions_data: list[EmbySessionResponse],
) -> None:
    """Handle sessions update with event firing."""
    old_sessions = self.data or {}
    new_sessions = self._parse_sessions(sessions_data)

    # Detect changes and fire events
    for device_id, session in new_sessions.items():
        old_session = old_sessions.get(device_id)

        if old_session is None:
            # New session connected
            self._fire_event(device_id, "session_connected")
        elif old_session.now_playing_item is None and session.now_playing_item:
            # Playback started
            self._fire_event(device_id, "playback_started", {
                "media_content_id": session.now_playing_item.item_id,
                "media_content_type": session.now_playing_item.media_type,
            })
        elif old_session.now_playing_item and session.now_playing_item is None:
            # Playback stopped
            self._fire_event(device_id, "playback_stopped")
        elif old_session.is_paused != session.is_paused:
            # Pause state changed
            event_type = "playback_paused" if session.is_paused else "playback_resumed"
            self._fire_event(device_id, event_type)

    # Check for disconnected sessions
    for device_id in old_sessions:
        if device_id not in new_sessions:
            self._fire_event(device_id, "session_disconnected")

    self.async_set_updated_data(new_sessions)

def _fire_event(
    self,
    device_id: str,
    event_type: str,
    extra_data: dict[str, str] | None = None,
) -> None:
    """Fire an Emby event."""
    entity_id = self._get_entity_id_for_device(device_id)
    if entity_id:
        data = {
            CONF_ENTITY_ID: entity_id,
            CONF_TYPE: event_type,
            **(extra_data or {}),
        }
        self.hass.bus.async_fire(f"{DOMAIN}_event", data)
```

**Acceptance Criteria:**
- [ ] Events fired on playback changes
- [ ] Events fired on session connect/disconnect
- [ ] Extra data included in events

**Test Cases:**
- [ ] `test_fire_event_playback_started`
- [ ] `test_fire_event_session_connected`
- [ ] `test_fire_event_includes_media_info`

### 8.4.3 Create Condition Platform

**File:** `custom_components/embymedia/device_condition.py` (new file)

Implement device conditions:

```python
"""Device conditions for Emby media players."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.components.device_automation import DEVICE_CONDITION_BASE_SCHEMA
from homeassistant.const import (
    CONF_CONDITION,
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_ENTITY_ID,
    CONF_TYPE,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_IDLE,
)
from homeassistant.helpers import condition

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType

CONDITION_TYPES = {
    "is_playing",
    "is_paused",
    "is_idle",
    "is_off",
    "has_media",
}

CONDITION_SCHEMA = DEVICE_CONDITION_BASE_SCHEMA.extend({
    vol.Required(CONF_ENTITY_ID): cv.entity_id,
    vol.Required(CONF_TYPE): vol.In(CONDITION_TYPES),
})


async def async_get_conditions(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, str]]:
    """List device conditions for Emby devices."""
    conditions = []

    entity_registry = er.async_get(hass)
    entries = er.async_entries_for_device(entity_registry, device_id)

    for entry in entries:
        if entry.domain == "media_player":
            conditions.extend([
                {
                    CONF_CONDITION: "device",
                    CONF_DEVICE_ID: device_id,
                    CONF_DOMAIN: DOMAIN,
                    CONF_ENTITY_ID: entry.entity_id,
                    CONF_TYPE: condition_type,
                }
                for condition_type in CONDITION_TYPES
            ])

    return conditions


async def async_condition_from_config(
    hass: HomeAssistant, config: ConfigType
) -> condition.ConditionCheckerType:
    """Create a condition from config."""
    entity_id = config[CONF_ENTITY_ID]
    condition_type = config[CONF_TYPE]

    def test_condition(hass: HomeAssistant) -> bool:
        """Test the condition."""
        state = hass.states.get(entity_id)
        if state is None:
            return False

        if condition_type == "is_playing":
            return state.state == STATE_PLAYING
        if condition_type == "is_paused":
            return state.state == STATE_PAUSED
        if condition_type == "is_idle":
            return state.state == STATE_IDLE
        if condition_type == "is_off":
            return state.state == "off"
        if condition_type == "has_media":
            return state.attributes.get("media_content_id") is not None

        return False

    return test_condition
```

**Condition Types:**
| Type | Description |
|------|-------------|
| `is_playing` | Media is currently playing |
| `is_paused` | Playback is paused |
| `is_idle` | Player is idle (connected, no playback) |
| `is_off` | Player is off (disconnected) |
| `has_media` | Any media is loaded |

**Acceptance Criteria:**
- [ ] Conditions appear in automation UI
- [ ] Conditions evaluate correctly
- [ ] Support for all player states

**Test Cases:**
- [ ] `test_get_conditions_returns_all_types`
- [ ] `test_condition_is_playing`
- [ ] `test_condition_has_media`

### 8.4.4 Register Platforms in manifest.json

**File:** `custom_components/embymedia/manifest.json`

Update to include automation platforms:

```json
{
  "domain": "embymedia",
  "name": "Emby",
  ...
  "dependencies": ["device_automation"]
}
```

**Acceptance Criteria:**
- [ ] Device automation dependency added
- [ ] Triggers/conditions discoverable

**Test Cases:**
- [ ] `test_manifest_includes_device_automation`

---

## Acceptance Criteria Summary

### Required for Phase 8 Complete

- [x] User selection in config flow
- [x] User context stored and used
- [x] Send message service working
- [x] Send command service working
- [x] Mark played/unplayed working
- [x] Favorite management working
- [x] Library refresh working
- [x] Device triggers implemented
- [x] Device conditions implemented
- [x] Notify platform implemented (entity-based)
- [x] All tests passing
- [x] 100% code coverage maintained
- [x] No mypy errors
- [x] No ruff errors

### Definition of Done

1. ✅ Multi-user support functional
2. ✅ Remote control services available
3. ✅ Library management services working
4. ✅ Automation triggers firing
5. ✅ Automation conditions evaluating
6. ✅ Notify platform working with `notify.send_message` action
7. ✅ All tests passing (815+ tests)
8. ✅ 100% code coverage maintained

---

## API Reference

### New Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/Sessions/{id}/Message` | POST | Send message to client |
| `/Sessions/{id}/Command` | POST | Send general command |
| `/Users/{userId}/PlayedItems/{itemId}` | POST | Mark item played |
| `/Users/{userId}/PlayedItems/{itemId}` | DELETE | Mark item unplayed |
| `/Users/{userId}/FavoriteItems/{itemId}` | POST | Add favorite |
| `/Users/{userId}/FavoriteItems/{itemId}` | DELETE | Remove favorite |
| `/Library/Refresh` | POST | Refresh all libraries |
| `/Items/{itemId}/Refresh` | POST | Refresh specific item |

### New Services

| Service | Description |
|---------|-------------|
| `embymedia.send_message` | Send message to Emby client |
| `embymedia.send_command` | Send navigation command |
| `embymedia.mark_played` | Mark item as played |
| `embymedia.mark_unplayed` | Mark item as unplayed |
| `embymedia.add_favorite` | Add item to favorites |
| `embymedia.remove_favorite` | Remove from favorites |
| `embymedia.refresh_library` | Trigger library scan |
| `embymedia.refresh_item` | Refresh item metadata |

---

## Task 8.5: Notify Platform

The integration includes a notify platform that creates `NotifyEntity` entities for each Emby client that supports remote control.

### 8.5.1 Entity Structure

**File:** `custom_components/embymedia/notify.py`

Each Emby client with `SupportsRemoteControl: true` gets a notify entity:
- **Entity ID:** `notify.{device_name}_notification`
- **Name:** `{Device Name} Notification`

### 8.5.2 Usage

**IMPORTANT:** The notify platform uses the modern `NotifyEntity` approach (entity-based), NOT the legacy notify service with targets in data.

#### Correct Usage (Entity-Based)

```yaml
action: notify.send_message
target:
  entity_id: notify.living_room_tv_notification
data:
  message: "Hello from Home Assistant!"
  title: "Notification Title"
```

Or in an automation:

```yaml
automation:
  - alias: "Notify Emby Client on Event"
    trigger:
      - platform: state
        entity_id: binary_sensor.motion
        to: "on"
    action:
      - action: notify.send_message
        target:
          entity_id: notify.living_room_tv_notification
        data:
          title: "Motion Detected"
          message: "Motion was detected in the living room"
```

#### WRONG Usage (Will Not Work)

The following legacy format does NOT work with the modern NotifyEntity platform:

```yaml
# ❌ WRONG - This will fail with "Unknown error"
action: notify.notify
data:
  target: notify.living_room_tv_notification
  title: "Title"
  message: "Message"
```

### 8.5.3 API Implementation

The notify entity calls the Emby `/Sessions/{id}/Message` endpoint:

```python
async def async_send_message(
    self,
    message: str,
    title: str | None = None,
) -> None:
    """Send a message to the Emby client."""
    await self._client.async_send_message(
        session_id=self._session.session_id,
        text=message,
        header=title or "",
        timeout_ms=5000,
    )
```

### 8.5.4 Acceptance Criteria

- [x] Notify entity created for each controllable session
- [x] Entity ID follows pattern `notify.{device}_notification`
- [x] `notify.send_message` action works with entity target
- [x] Title and message displayed on Emby client
- [x] Error handling for unavailable clients

### 8.5.5 Test Cases

- [x] `test_notify_entity_created`
- [x] `test_notify_send_message`
- [x] `test_notify_send_message_with_title`
- [x] `test_notify_unavailable_session`

---

## Notes

- User selection is optional; admin API key works without user context
- Remote control requires `SupportsRemoteControl: true` in session
- Library management requires appropriate user permissions
- Triggers use Home Assistant's event system for reliability
- Conditions check entity state, not direct API calls
- **Notify platform uses entity-based `notify.send_message` action, NOT legacy `notify.notify` with target in data**
