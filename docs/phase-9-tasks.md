# Phase 9: Polish & Production Readiness

## Overview

This phase focuses on production readiness including error handling, performance optimization, configuration options, diagnostics, and documentation.

**Features:**
- Graceful error handling and recovery
- Performance optimizations (connection pooling, caching)
- Extended configuration options
- Diagnostics platform for troubleshooting
- Comprehensive user documentation

## Dependencies

- Phase 1-8 complete
- Home Assistant diagnostics platform
- Home Assistant repairs platform (optional)

---

## Task 9.1: Error Handling & Resilience

Implement graceful degradation and detailed error handling.

### 9.1.1 Graceful Degradation on Partial Failures

**File:** `custom_components/embymedia/coordinator.py`

Handle partial failures without crashing:

```python
async def _async_update_data(self) -> dict[str, EmbySession]:
    """Fetch data with graceful degradation."""
    try:
        sessions = await self._client.async_get_sessions()
    except EmbyConnectionError as err:
        if self.data is not None:
            # Return cached data on connection failure
            _LOGGER.warning(
                "Failed to fetch sessions, using cached data: %s", err
            )
            return self.data
        raise UpdateFailed(f"Failed to connect: {err}") from err

    return self._parse_sessions(sessions)
```

**Acceptance Criteria:**
- [ ] Connection failures return cached data when available
- [ ] Partial session data doesn't crash coordinator
- [ ] Detailed logging of failures

**Test Cases:**
- [ ] `test_coordinator_uses_cached_data_on_failure`
- [ ] `test_coordinator_raises_on_first_failure`
- [ ] `test_coordinator_handles_partial_session_data`

### 9.1.2 User-Friendly Error Messages

**File:** `custom_components/embymedia/exceptions.py`

Add translation keys for errors:

```python
class EmbyError(Exception):
    """Base exception for Emby integration."""

    def __init__(
        self,
        message: str,
        translation_key: str | None = None,
        translation_placeholders: dict[str, str] | None = None,
    ) -> None:
        """Initialize with optional translation support."""
        super().__init__(message)
        self.translation_key = translation_key
        self.translation_placeholders = translation_placeholders or {}


class EmbyConnectionError(EmbyError):
    """Connection to Emby server failed."""

    def __init__(self, message: str, host: str = "", port: int = 0) -> None:
        """Initialize with connection details."""
        super().__init__(
            message,
            translation_key="connection_failed",
            translation_placeholders={"host": host, "port": str(port)},
        )
```

**File:** `custom_components/embymedia/strings.json`

Add error translations:

```json
{
  "exceptions": {
    "connection_failed": {
      "message": "Failed to connect to Emby server at {host}:{port}. Please check that the server is running and the host/port are correct."
    },
    "authentication_failed": {
      "message": "Authentication failed. Please check your API key."
    },
    "server_error": {
      "message": "The Emby server returned an error. Please check the server logs."
    }
  }
}
```

**Acceptance Criteria:**
- [ ] Errors have translation keys
- [ ] Error messages are user-friendly
- [ ] Placeholders filled correctly

**Test Cases:**
- [ ] `test_exception_translation_key`
- [ ] `test_exception_placeholders`

### 9.1.3 Automatic Recovery Mechanisms

**File:** `custom_components/embymedia/coordinator.py`

Add health monitoring and recovery:

```python
class EmbyDataUpdateCoordinator:
    """Coordinator with health monitoring."""

    _consecutive_failures: int = 0
    _max_consecutive_failures: int = 5
    _health_check_interval: int = 300  # 5 minutes

    async def _async_update_data(self) -> dict[str, EmbySession]:
        """Update with failure tracking."""
        try:
            result = await self._fetch_sessions()
            self._consecutive_failures = 0
            return result
        except EmbyConnectionError as err:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._max_consecutive_failures:
                await self._attempt_recovery()
            raise

    async def _attempt_recovery(self) -> None:
        """Attempt to recover from repeated failures."""
        _LOGGER.info("Attempting automatic recovery after %d failures", self._consecutive_failures)

        # Try to reconnect WebSocket
        if self._websocket:
            await self._websocket.async_reconnect()

        # Refresh server info
        try:
            await self._client.async_get_server_info()
            _LOGGER.info("Recovery successful, server is responding")
        except EmbyError:
            _LOGGER.warning("Recovery failed, server still unreachable")
```

**Acceptance Criteria:**
- [ ] Consecutive failures tracked
- [ ] Automatic recovery attempted after threshold
- [ ] Recovery logged clearly

**Test Cases:**
- [ ] `test_consecutive_failure_tracking`
- [ ] `test_automatic_recovery_triggered`
- [ ] `test_recovery_resets_failure_count`

### 9.1.4 Detailed Error Logging

**File:** `custom_components/embymedia/api.py`

Enhance logging for debugging:

```python
async def _request(
    self,
    method: str,
    endpoint: str,
    include_auth: bool = True,
) -> dict[str, object]:
    """Make request with detailed logging."""
    request_id = f"{method}:{endpoint}:{time.time():.3f}"
    _LOGGER.debug(
        "[%s] Starting request to %s",
        request_id,
        endpoint,
    )

    try:
        # ... existing request logic ...
        _LOGGER.debug(
            "[%s] Request completed successfully in %.3fs",
            request_id,
            time.time() - start_time,
        )
    except Exception as err:
        _LOGGER.debug(
            "[%s] Request failed after %.3fs: %s",
            request_id,
            time.time() - start_time,
            err,
        )
        raise
```

**Acceptance Criteria:**
- [ ] Requests have unique identifiers
- [ ] Timing information logged
- [ ] Failure details logged

**Test Cases:**
- [ ] `test_request_logging_success`
- [ ] `test_request_logging_failure`

---

## Task 9.2: Performance Optimization

Optimize for large installations and high request volumes.

### 9.2.1 Connection Pooling

**File:** `custom_components/embymedia/api.py`

Ensure proper session reuse:

```python
class EmbyClient:
    """Client with optimized connection handling."""

    def __init__(
        self,
        ...
        max_connections: int = 10,
        keepalive_timeout: int = 30,
    ) -> None:
        """Initialize with connection pool settings."""
        self._connector = aiohttp.TCPConnector(
            limit=max_connections,
            keepalive_timeout=keepalive_timeout,
            enable_cleanup_closed=True,
        )

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get session with connection pooling."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=self._timeout,
            )
            self._owns_session = True
        return self._session
```

**Acceptance Criteria:**
- [ ] Connections reused across requests
- [ ] Connection limit prevents exhaustion
- [ ] Cleanup of stale connections

**Test Cases:**
- [ ] `test_connection_pooling_reuses_connections`
- [ ] `test_connection_limit_respected`

### 9.2.2 Response Caching Improvements

**File:** `custom_components/embymedia/cache.py`

Add cache statistics and optimization:

```python
class BrowseCache:
    """Cache with statistics tracking."""

    def __init__(
        self,
        ttl_seconds: float = 300.0,
        max_entries: int = 500,
        enable_stats: bool = True,
    ) -> None:
        """Initialize with stats tracking."""
        self._stats = CacheStats() if enable_stats else None

    @property
    def stats(self) -> CacheStats | None:
        """Return cache statistics."""
        return self._stats

    def get(self, key: str) -> object | None:
        """Get with stats tracking."""
        result = self._cache.get(key)
        if self._stats:
            if result is not None:
                self._stats.hits += 1
            else:
                self._stats.misses += 1
        return result


@dataclass
class CacheStats:
    """Cache statistics for monitoring."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    current_size: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate hit rate percentage."""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0
```

**Acceptance Criteria:**
- [ ] Cache statistics tracked
- [ ] Hit rate calculable
- [ ] Stats available for diagnostics

**Test Cases:**
- [ ] `test_cache_stats_tracking`
- [ ] `test_cache_hit_rate_calculation`

### 9.2.3 Lazy Loading of Heavy Data

**File:** `custom_components/embymedia/media_player.py`

Defer loading of expensive data:

```python
class EmbyMediaPlayerEntity(EmbyEntity, MediaPlayerEntity):
    """Media player with lazy loading."""

    _user_id: str | None = None
    _user_loaded: bool = False

    async def _ensure_user_loaded(self) -> None:
        """Lazily load user ID when needed."""
        if self._user_loaded:
            return

        if self._session and self._session.user_id:
            self._user_id = self._session.user_id
        else:
            # Fallback: fetch first user
            users = await self.coordinator.client.async_get_users()
            if users:
                self._user_id = users[0]["Id"]

        self._user_loaded = True

    async def async_browse_media(
        self,
        media_content_type: MediaType | str | None = None,
        media_content_id: str | None = None,
    ) -> BrowseMedia:
        """Browse with lazy user loading."""
        await self._ensure_user_loaded()
        # ... rest of browse logic
```

**Acceptance Criteria:**
- [ ] User data loaded only when needed
- [ ] No blocking during entity creation
- [ ] Cached after first load

**Test Cases:**
- [ ] `test_lazy_user_loading`
- [ ] `test_user_cached_after_load`

### 9.2.4 Memory Usage Optimization

**File:** `custom_components/embymedia/models.py`

Use slots for dataclasses:

```python
@dataclass(slots=True)
class EmbySession:
    """Emby session with optimized memory."""

    device_id: str
    device_name: str
    # ... other fields


@dataclass(slots=True)
class EmbyMediaItem:
    """Media item with optimized memory."""

    item_id: str
    name: str
    # ... other fields
```

**Acceptance Criteria:**
- [ ] Dataclasses use slots
- [ ] Reduced memory footprint
- [ ] No functionality regression

**Test Cases:**
- [ ] `test_dataclass_slots`
- [ ] `test_dataclass_functionality`

---

## Task 9.3: Configuration Options

Extended options for customization.

### 9.3.1 Scan Interval Customization

**File:** `custom_components/embymedia/config_flow.py`

Already implemented in options flow. Verify:

```python
OPTIONS_SCHEMA = vol.Schema({
    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
        vol.Coerce(int),
        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
    ),
})
```

**Acceptance Criteria:**
- [x] Scan interval configurable (already done)
- [ ] Validation of min/max values
- [ ] Real-time update on change

**Test Cases:**
- [ ] `test_options_scan_interval_validation`
- [ ] `test_options_scan_interval_update`

### 9.3.2 Entity Naming Templates

**File:** `custom_components/embymedia/config_flow.py`

Add entity naming options:

```python
CONF_ENTITY_NAME_TEMPLATE = "entity_name_template"
DEFAULT_ENTITY_NAME_TEMPLATE = "{device_name}"

# Templates:
# {device_name} - Device name from Emby
# {client} - Client application name
# {user} - Current user name
# {server} - Server name

OPTIONS_SCHEMA = OPTIONS_SCHEMA.extend({
    vol.Optional(
        CONF_ENTITY_NAME_TEMPLATE,
        default=DEFAULT_ENTITY_NAME_TEMPLATE
    ): cv.string,
})
```

**File:** `custom_components/embymedia/entity.py`

Apply template:

```python
class EmbyEntity(CoordinatorEntity):
    """Entity with configurable naming."""

    @property
    def name(self) -> str:
        """Return entity name from template."""
        template = self.coordinator.entity_name_template
        return template.format(
            device_name=self._device_name,
            client=self._session.client if self._session else "",
            user=self._session.user_name if self._session else "",
            server=self.coordinator.server_name,
        )
```

**Acceptance Criteria:**
- [ ] Name template configurable
- [ ] Template variables substituted
- [ ] Invalid template handled gracefully

**Test Cases:**
- [ ] `test_entity_name_template_substitution`
- [ ] `test_entity_name_template_invalid`

### 9.3.3 Feature Toggles

**File:** `custom_components/embymedia/config_flow.py`

Add feature toggle options:

```python
CONF_ENABLE_WEBSOCKET = "enable_websocket"
CONF_ENABLE_MEDIA_SOURCE = "enable_media_source"
CONF_ENABLE_BROWSE = "enable_browse"

DEFAULT_ENABLE_WEBSOCKET = True
DEFAULT_ENABLE_MEDIA_SOURCE = True
DEFAULT_ENABLE_BROWSE = True

OPTIONS_SCHEMA = OPTIONS_SCHEMA.extend({
    vol.Optional(CONF_ENABLE_WEBSOCKET, default=DEFAULT_ENABLE_WEBSOCKET): bool,
    vol.Optional(CONF_ENABLE_MEDIA_SOURCE, default=DEFAULT_ENABLE_MEDIA_SOURCE): bool,
    vol.Optional(CONF_ENABLE_BROWSE, default=DEFAULT_ENABLE_BROWSE): bool,
})
```

**Acceptance Criteria:**
- [ ] WebSocket can be disabled
- [ ] Media source can be disabled
- [ ] Browse can be disabled
- [ ] Changes take effect after reload

**Test Cases:**
- [ ] `test_options_websocket_toggle`
- [ ] `test_options_media_source_toggle`

### 9.3.4 Client/Device Filtering

**File:** `custom_components/embymedia/config_flow.py`

Add device filter options:

```python
CONF_INCLUDE_CLIENTS = "include_clients"
CONF_EXCLUDE_CLIENTS = "exclude_clients"
CONF_INCLUDE_DEVICES = "include_devices"
CONF_EXCLUDE_DEVICES = "exclude_devices"

OPTIONS_SCHEMA = OPTIONS_SCHEMA.extend({
    vol.Optional(CONF_INCLUDE_CLIENTS): cv.ensure_list,
    vol.Optional(CONF_EXCLUDE_CLIENTS): cv.ensure_list,
    vol.Optional(CONF_INCLUDE_DEVICES): cv.ensure_list,
    vol.Optional(CONF_EXCLUDE_DEVICES): cv.ensure_list,
})
```

**File:** `custom_components/embymedia/coordinator.py`

Apply filters:

```python
def _should_include_session(self, session: EmbySession) -> bool:
    """Check if session passes filters."""
    include_clients = self._options.get(CONF_INCLUDE_CLIENTS)
    exclude_clients = self._options.get(CONF_EXCLUDE_CLIENTS)

    if include_clients and session.client not in include_clients:
        return False
    if exclude_clients and session.client in exclude_clients:
        return False

    # Similar for devices...
    return True
```

**Acceptance Criteria:**
- [ ] Include filter works (whitelist)
- [ ] Exclude filter works (blacklist)
- [ ] Filters apply to both clients and devices

**Test Cases:**
- [ ] `test_filter_include_clients`
- [ ] `test_filter_exclude_clients`
- [ ] `test_filter_include_devices`

---

## Task 9.4: Diagnostics Platform

Implement diagnostics for troubleshooting.

### 9.4.1 Create Diagnostics Platform

**File:** `custom_components/embymedia/diagnostics.py` (new file)

```python
"""Diagnostics support for Emby integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.diagnostics import async_redact_data

from .const import CONF_API_KEY, DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .const import EmbyConfigEntry

TO_REDACT = {CONF_API_KEY, "api_key", "token", "password"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: EmbyConfigEntry
) -> dict[str, object]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data

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
            "websocket_connected": coordinator.websocket_connected,
            "last_update": coordinator.last_update_success_time,
            "update_interval": str(coordinator.update_interval),
        },
        "sessions": {
            "active_count": len(coordinator.data) if coordinator.data else 0,
            "sessions": [
                {
                    "device_id": session.device_id,
                    "device_name": session.device_name,
                    "client": session.client,
                    "is_playing": session.now_playing_item is not None,
                }
                for session in (coordinator.data or {}).values()
            ],
        },
        "cache_stats": coordinator.client.browse_cache.stats.__dict__
        if coordinator.client.browse_cache.stats
        else None,
    }
```

**Acceptance Criteria:**
- [ ] API keys redacted
- [ ] Server info included
- [ ] Connection status shown
- [ ] Session summary provided
- [ ] Cache stats included

**Test Cases:**
- [ ] `test_diagnostics_redacts_api_key`
- [ ] `test_diagnostics_includes_server_info`
- [ ] `test_diagnostics_includes_sessions`

### 9.4.2 Add Device Diagnostics

**File:** `custom_components/embymedia/diagnostics.py`

Add per-device diagnostics:

```python
async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: EmbyConfigEntry, device: DeviceEntry
) -> dict[str, object]:
    """Return diagnostics for a device."""
    coordinator = entry.runtime_data

    # Find session for this device
    device_id = None
    for identifier in device.identifiers:
        if identifier[0] == DOMAIN:
            device_id = identifier[1]
            break

    if device_id is None:
        return {"error": "Device not found"}

    session = (coordinator.data or {}).get(device_id)
    if session is None:
        return {"device_id": device_id, "status": "offline"}

    return {
        "device_id": device_id,
        "status": "online",
        "device_name": session.device_name,
        "client": session.client,
        "application_version": session.application_version,
        "supports_remote_control": session.supports_remote_control,
        "supported_commands": session.supported_commands,
        "playback_state": {
            "is_playing": session.now_playing_item is not None,
            "is_paused": session.is_paused,
            "volume_level": session.volume_level,
            "is_muted": session.is_muted,
        },
        "now_playing": {
            "item_id": session.now_playing_item.item_id,
            "name": session.now_playing_item.name,
            "type": session.now_playing_item.media_type,
        }
        if session.now_playing_item
        else None,
    }
```

**Acceptance Criteria:**
- [ ] Device-specific diagnostics
- [ ] Session details included
- [ ] Playback state shown

**Test Cases:**
- [ ] `test_device_diagnostics_online`
- [ ] `test_device_diagnostics_offline`

### 9.4.3 Register Diagnostics Platform

**File:** `custom_components/embymedia/manifest.json`

Ensure diagnostics dependency:

```json
{
  "dependencies": ["diagnostics"]
}
```

**Acceptance Criteria:**
- [ ] Diagnostics downloadable from UI
- [ ] No errors during download

**Test Cases:**
- [ ] `test_diagnostics_platform_registered`

---

## Task 9.5: Documentation

Create comprehensive user documentation.

### 9.5.1 Installation Guide

**File:** `docs/installation.md` (new file)

```markdown
# Installation Guide

## Prerequisites

- Home Assistant 2024.1.0 or later
- Emby Server 4.7.0 or later
- An Emby API key (Admin Dashboard → API Keys)

## Installation Methods

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click "+ Explore & Add Repositories"
3. Search for "Emby"
4. Click "Download"
5. Restart Home Assistant

### Manual Installation

1. Download the latest release
2. Copy `custom_components/embymedia` to your `custom_components` folder
3. Restart Home Assistant

## Configuration

1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "Emby"
4. Enter your server details:
   - Host: Your Emby server hostname or IP
   - Port: Default is 8096
   - API Key: From Emby Admin Dashboard
   - SSL: Enable if using HTTPS

## First Run

After adding the integration:
- Media player entities will be created for active Emby clients
- Use the Media Browser to browse your libraries
- Enjoy real-time updates via WebSocket connection
```

**Acceptance Criteria:**
- [ ] Clear installation steps
- [ ] Prerequisites listed
- [ ] Screenshots if possible

### 9.5.2 Configuration Reference

**File:** `docs/configuration.md` (new file)

```markdown
# Configuration Reference

## Initial Setup Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| Host | Yes | - | Emby server hostname/IP |
| Port | Yes | 8096 | Emby server port |
| API Key | Yes | - | API key from Emby admin |
| SSL | No | false | Use HTTPS connection |
| Verify SSL | No | true | Verify SSL certificate |

## Options (After Setup)

| Option | Default | Description |
|--------|---------|-------------|
| Scan Interval | 10 | Polling interval in seconds |
| Enable WebSocket | true | Real-time updates |
| Enable Media Source | true | Expose media to other players |
| Enable Browse | true | Media browser support |

## Services

### embymedia.send_message

Send a message to an Emby client.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| entity_id | string | Yes | Media player entity |
| message | string | Yes | Message text |
| header | string | No | Message header |
| timeout_ms | int | No | Display duration (default: 5000) |

Example:
```yaml
service: embymedia.send_message
target:
  entity_id: media_player.emby_living_room
data:
  message: "Dinner is ready!"
  header: "Kitchen"
  timeout_ms: 10000
```

[... more services ...]
```

**Acceptance Criteria:**
- [ ] All options documented
- [ ] Services documented with examples
- [ ] YAML examples included

### 9.5.3 Troubleshooting Guide

**File:** `docs/troubleshooting.md` (new file)

```markdown
# Troubleshooting

## Common Issues

### No Entities Appearing

**Symptoms:** Integration configured but no media player entities.

**Causes:**
1. No active Emby clients
2. Clients don't support remote control

**Solutions:**
1. Open an Emby client (app, web, etc.)
2. Check Emby Dashboard → Sessions
3. Verify "Supports Remote Control" is shown

### Connection Failed

**Symptoms:** "Failed to connect" error during setup.

**Causes:**
1. Wrong host/port
2. Firewall blocking connection
3. SSL certificate issues

**Solutions:**
1. Verify host is correct (no http:// prefix)
2. Test connection: `curl http://host:port/emby/System/Info/Public`
3. For SSL issues, try disabling "Verify SSL"

### Authentication Failed

**Symptoms:** "Invalid API key" error.

**Solutions:**
1. Generate new API key in Emby → Dashboard → API Keys
2. Ensure key has no extra spaces
3. Verify key permissions

### WebSocket Not Connecting

**Symptoms:** Integration works but updates are slow.

**Causes:**
1. WebSocket blocked by proxy/firewall
2. SSL certificate issues for WSS

**Solutions:**
1. Check firewall allows WebSocket connections
2. Verify proxy passes WebSocket upgrades
3. Try disabling WebSocket in options

## Debug Logging

Enable debug logging:

```yaml
logger:
  logs:
    custom_components.embymedia: debug
```

## Getting Help

1. Check existing issues on GitHub
2. Download diagnostics (Settings → Integrations → Emby → 3 dots → Download diagnostics)
3. Open new issue with diagnostics attached
```

**Acceptance Criteria:**
- [ ] Common issues covered
- [ ] Clear solutions provided
- [ ] Debug logging explained

### 9.5.4 Example Automations

**File:** `docs/examples.md` (new file)

```markdown
# Example Automations

## Dim Lights When Playing

```yaml
automation:
  - alias: "Dim lights when Emby plays"
    trigger:
      - platform: state
        entity_id: media_player.emby_living_room
        to: "playing"
    action:
      - service: light.turn_on
        target:
          entity_id: light.living_room
        data:
          brightness_pct: 20
```

## Pause on Phone Call

```yaml
automation:
  - alias: "Pause Emby on phone call"
    trigger:
      - platform: state
        entity_id: sensor.phone_state
        to: "ringing"
    condition:
      - condition: state
        entity_id: media_player.emby_living_room
        state: "playing"
    action:
      - service: media_player.media_pause
        target:
          entity_id: media_player.emby_living_room
```

## Send Message on Motion

```yaml
automation:
  - alias: "Alert Emby user on motion"
    trigger:
      - platform: state
        entity_id: binary_sensor.front_door_motion
        to: "on"
    action:
      - service: embymedia.send_message
        target:
          entity_id: media_player.emby_living_room
        data:
          message: "Motion detected at front door"
          header: "Security"
```

## Mark Played After Completion

```yaml
automation:
  - alias: "Mark as played when stopped"
    trigger:
      - platform: state
        entity_id: media_player.emby_living_room
        from: "playing"
        to: "idle"
    action:
      - service: embymedia.mark_played
        target:
          entity_id: media_player.emby_living_room
        data:
          item_id: "{{ trigger.from_state.attributes.media_content_id }}"
```
```

**Acceptance Criteria:**
- [ ] Real-world examples
- [ ] Copy-paste ready YAML
- [ ] Various use cases covered

---

## Acceptance Criteria Summary

### Required for Phase 9 Complete

- [ ] Graceful degradation implemented
- [ ] User-friendly error messages
- [ ] Automatic recovery working
- [ ] Connection pooling optimized
- [ ] Cache statistics available
- [ ] Extended options implemented
- [ ] Device filtering working
- [ ] Diagnostics platform complete
- [ ] Documentation written
- [ ] All tests passing
- [ ] 100% code coverage maintained
- [ ] No mypy errors
- [ ] No ruff errors

### Definition of Done

1. ✅ Error handling graceful and informative
2. ✅ Performance optimized for large installations
3. ✅ All configuration options working
4. ✅ Diagnostics downloadable and useful
5. ✅ Documentation comprehensive
6. ✅ All tests passing (target: 700+ tests)
7. ✅ 100% code coverage maintained

---

## Notes

- Diagnostics should never expose sensitive data
- Documentation should be accessible to non-technical users
- Error messages should guide users to solutions
- Performance optimizations should not change behavior
- All changes should be backwards compatible
