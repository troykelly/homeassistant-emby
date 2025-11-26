# Phase 11: Entity Naming Customization

## Overview

Add a simple toggle to prefix device and entity names with "Emby". Also clean up redundant entity name suffixes.

### Problem Statement

1. **Redundant suffixes** - `notify.living_room_tv_notification` and `remote.living_room_tv_remote` have unnecessary suffixes
2. **No identification** - No way to distinguish Emby entities from other integrations

### Current Entity IDs

| Entity Type | Current Entity ID | Problem |
|-------------|-------------------|---------|
| Media Player | `media_player.living_room_tv` | No Emby identification |
| Notify | `notify.living_room_tv_notification` | Redundant `_notification` suffix |
| Remote | `remote.living_room_tv_remote` | Redundant `_remote` suffix |

---

## Design

### Part 1: Remove Redundant Suffixes (Breaking Change)

Remove `_attr_name` values from notify and remote entities:

| Entity Type | Before | After |
|-------------|--------|-------|
| Notify | `_attr_name = "Notification"` | `_attr_name = None` |
| Remote | `_attr_name = "Remote"` | `_attr_name = None` |

**Result:**
- `notify.living_room_tv` (was `_notification`)
- `remote.living_room_tv` (was `_remote`)

### Part 2: Add "Prefix with Emby" Toggles (Per Entity Type)

Add a toggle for each entity type to the Options Flow:

```python
# const.py
CONF_PREFIX_MEDIA_PLAYER: Final = "prefix_media_player"
CONF_PREFIX_NOTIFY: Final = "prefix_notify"
CONF_PREFIX_REMOTE: Final = "prefix_remote"
CONF_PREFIX_BUTTON: Final = "prefix_button"

DEFAULT_PREFIX_MEDIA_PLAYER: Final = True  # ON by default
DEFAULT_PREFIX_NOTIFY: Final = True        # ON by default
DEFAULT_PREFIX_REMOTE: Final = True        # ON by default
DEFAULT_PREFIX_BUTTON: Final = True        # ON by default
```

### Options Flow UI

```
Prefix device names with "Emby":
  [x] Media players     (checked by default)
  [x] Notifications     (checked by default)
  [x] Remote controls   (checked by default)
  [x] Server buttons    (checked by default)
```

### Behavior

Each entity type has its own device in Home Assistant. The toggle controls whether the device name is prefixed with "Emby".

**Client devices** (media_player, notify, remote):
- Device name from Emby: "Living Room TV"
- With prefix ON: "Emby Living Room TV"

**Server device** (button):
- Server name from Emby: "MyServer"
- With prefix ON: "Emby MyServer"

| Entity Type | Toggle | Device Name | Entity Name | Resulting Entity ID |
|-------------|--------|-------------|-------------|---------------------|
| Media Player | ON | "Emby Living Room TV" | None | `media_player.emby_living_room_tv` |
| Media Player | OFF | "Living Room TV" | None | `media_player.living_room_tv` |
| Notify | ON | "Emby Living Room TV" | None | `notify.emby_living_room_tv` |
| Notify | OFF | "Living Room TV" | None | `notify.living_room_tv` |
| Remote | ON | "Emby Living Room TV" | None | `remote.emby_living_room_tv` |
| Remote | OFF | "Living Room TV" | None | `remote.living_room_tv` |
| Button | ON | "Emby MyServer" | "Refresh Library" | `button.emby_myserver_refresh_library` |
| Button | OFF | "MyServer" | "Refresh Library" | `button.myserver_refresh_library` |

### Implementation

Each entity type overrides `device_info` to check its specific toggle:

**Base approach - add helper method to base entity:**

```python
# entity.py
def _get_device_name(self, prefix_conf_key: str, default_prefix: bool) -> str:
    """Get device name with optional Emby prefix."""
    session = self.session
    device_name = session.device_name if session else f"Client {self._device_id[:8]}"

    prefix_enabled = self.coordinator.config_entry.options.get(prefix_conf_key, default_prefix)
    if prefix_enabled:
        return f"Emby {device_name}"
    return device_name
```

**For media_player.py:**

```python
@property
def device_info(self) -> DeviceInfo:
    device_name = self._get_device_name(CONF_PREFIX_MEDIA_PLAYER, DEFAULT_PREFIX_MEDIA_PLAYER)
    return DeviceInfo(
        identifiers={(DOMAIN, self._device_id)},
        name=device_name,
        ...
    )
```

**For notify.py:**

```python
@property
def device_info(self) -> DeviceInfo:
    device_name = self._get_device_name(CONF_PREFIX_NOTIFY, DEFAULT_PREFIX_NOTIFY)
    return DeviceInfo(
        identifiers={(DOMAIN, self._device_id)},
        name=device_name,
        ...
    )
```

**For remote.py:**

```python
@property
def device_info(self) -> DeviceInfo:
    device_name = self._get_device_name(CONF_PREFIX_REMOTE, DEFAULT_PREFIX_REMOTE)
    return DeviceInfo(
        identifiers={(DOMAIN, self._device_id)},
        name=device_name,
        ...
    )
```

**For button.py (server-level):**

```python
@property
def device_info(self) -> DeviceInfo:
    server_name = self.coordinator.server_name
    prefix_enabled = self.coordinator.config_entry.options.get(
        CONF_PREFIX_BUTTON, DEFAULT_PREFIX_BUTTON
    )
    if prefix_enabled:
        server_name = f"Emby {server_name}"

    return DeviceInfo(
        identifiers={(DOMAIN, self.coordinator.server_id)},
        name=server_name,
        ...
    )
```

### Resulting Entity IDs (All Toggles ON - Default)

- `media_player.emby_living_room_tv`
- `notify.emby_living_room_tv`
- `remote.emby_living_room_tv`
- `button.emby_myserver_refresh_library`

### Resulting Entity IDs (All Toggles OFF)

- `media_player.living_room_tv`
- `notify.living_room_tv`
- `remote.living_room_tv`
- `button.myserver_refresh_library`

---

## Implementation Tasks

### Part A: Remove Redundant Suffixes

#### Task 11.1: Remove Notification Suffix

**File:** `notify.py`

**Change:**
```python
# Before
_attr_name = "Notification"

# After
_attr_name = None
```

**Tests:** `tests/test_notify.py`
- [ ] Test entity ID is `notify.{device_name}` (no `_notification` suffix)
- [ ] Test entity still functions correctly
- [ ] Test unique_id unchanged (still has `_notify` suffix for internal tracking)

---

#### Task 11.2: Remove Remote Suffix

**File:** `remote.py`

**Change:**
```python
# Before
_attr_name = "Remote"

# After
_attr_name = None
```

**Tests:** `tests/test_remote.py`
- [ ] Test entity ID is `remote.{device_name}` (no `_remote` suffix)
- [ ] Test entity still functions correctly
- [ ] Test unique_id unchanged (still has `_remote` suffix for internal tracking)

---

#### Task 11.3: Update Existing Tests

**Files:** Various test files

- [ ] Update all tests expecting `_notification` suffix in entity IDs
- [ ] Update all tests expecting `_remote` suffix in entity IDs
- [ ] Ensure 100% test coverage maintained

---

### Part B: Add "Prefix with Emby" Toggles (Per Entity Type)

#### Task 11.4: Add Constants

**File:** `const.py`

- [ ] Add `CONF_PREFIX_MEDIA_PLAYER: Final = "prefix_media_player"`
- [ ] Add `CONF_PREFIX_NOTIFY: Final = "prefix_notify"`
- [ ] Add `CONF_PREFIX_REMOTE: Final = "prefix_remote"`
- [ ] Add `CONF_PREFIX_BUTTON: Final = "prefix_button"`
- [ ] Add `DEFAULT_PREFIX_MEDIA_PLAYER: Final = True`
- [ ] Add `DEFAULT_PREFIX_NOTIFY: Final = True`
- [ ] Add `DEFAULT_PREFIX_REMOTE: Final = True`
- [ ] Add `DEFAULT_PREFIX_BUTTON: Final = True`

**Tests:** `tests/test_const.py`
- [ ] Test constants exist and have correct values

---

#### Task 11.5: Update Options Flow

**File:** `config_flow.py`

- [ ] Import new constants
- [ ] Add four boolean toggles to options schema

```python
vol.Optional(
    CONF_PREFIX_MEDIA_PLAYER,
    default=self.config_entry.options.get(CONF_PREFIX_MEDIA_PLAYER, DEFAULT_PREFIX_MEDIA_PLAYER),
): bool,
vol.Optional(
    CONF_PREFIX_NOTIFY,
    default=self.config_entry.options.get(CONF_PREFIX_NOTIFY, DEFAULT_PREFIX_NOTIFY),
): bool,
vol.Optional(
    CONF_PREFIX_REMOTE,
    default=self.config_entry.options.get(CONF_PREFIX_REMOTE, DEFAULT_PREFIX_REMOTE),
): bool,
vol.Optional(
    CONF_PREFIX_BUTTON,
    default=self.config_entry.options.get(CONF_PREFIX_BUTTON, DEFAULT_PREFIX_BUTTON),
): bool,
```

**Tests:** `tests/test_config_flow.py`
- [ ] Test options flow shows all four toggles
- [ ] Test default values are all True
- [ ] Test toggles can be turned off independently
- [ ] Test options are saved correctly

---

#### Task 11.6: Update Translations

**File:** `strings.json`

- [ ] Add `prefix_media_player` label and description
- [ ] Add `prefix_notify` label and description
- [ ] Add `prefix_remote` label and description
- [ ] Add `prefix_button` label and description

**File:** `translations/en.json`
- [ ] Mirror all changes from strings.json

---

#### Task 11.7: Update Base Entity Class

**File:** `entity.py`

- [ ] Add `_get_device_name()` helper method

```python
def _get_device_name(self, prefix_conf_key: str, default_prefix: bool) -> str:
    """Get device name with optional Emby prefix."""
    session = self.session
    device_name = session.device_name if session else f"Client {self._device_id[:8]}"

    prefix_enabled = self.coordinator.config_entry.options.get(prefix_conf_key, default_prefix)
    if prefix_enabled:
        return f"Emby {device_name}"
    return device_name
```

**Tests:** `tests/test_entity.py`
- [ ] Test `_get_device_name()` with prefix enabled
- [ ] Test `_get_device_name()` with prefix disabled
- [ ] Test fallback device name when session is None

---

#### Task 11.8: Update Media Player Entity

**File:** `media_player.py`

- [ ] Override `device_info` property to use `CONF_PREFIX_MEDIA_PLAYER`

**Tests:** `tests/test_media_player.py`
- [ ] Test device name with prefix (default)
- [ ] Test device name without prefix when toggle off
- [ ] Test entity ID reflects prefix

---

#### Task 11.9: Update Notify Entity

**File:** `notify.py`

- [ ] Override `device_info` property to use `CONF_PREFIX_NOTIFY`

**Tests:** `tests/test_notify.py`
- [ ] Test device name with prefix (default)
- [ ] Test device name without prefix when toggle off
- [ ] Test entity ID reflects prefix

---

#### Task 11.10: Update Remote Entity

**File:** `remote.py`

- [ ] Override `device_info` property to use `CONF_PREFIX_REMOTE`

**Tests:** `tests/test_remote.py`
- [ ] Test device name with prefix (default)
- [ ] Test device name without prefix when toggle off
- [ ] Test entity ID reflects prefix

---

#### Task 11.11: Update Button Entity

**File:** `button.py`

- [ ] Override `device_info` property to use `CONF_PREFIX_BUTTON`
- [ ] Prefix server name instead of device name

**Tests:** `tests/test_button.py`
- [ ] Test server device name with prefix (default)
- [ ] Test server device name without prefix when toggle off
- [ ] Test entity ID reflects prefix

---

#### Task 11.12: Integration Tests

**File:** `tests/test_init.py`

- [ ] Test entity IDs with all prefixes ON (default)
- [ ] Test entity IDs with all prefixes OFF
- [ ] Test mixed prefix settings (some ON, some OFF)
- [ ] Test each entity type independently

---

#### Task 11.13: Update Documentation

**File:** `README.md`

- [ ] Document per-entity-type prefix options
- [ ] Add examples of entity ID patterns
- [ ] Explain breaking change from suffix removal

**File:** `docs/roadmap.md`

- [ ] Update Phase 11 section with completion status

---

## Acceptance Criteria

### Part A: Suffix Removal
1. **Notify entities**: Entity ID is `notify.{device_name}` (no `_notification` suffix)
2. **Remote entities**: Entity ID is `remote.{device_name}` (no `_remote` suffix)
3. **Unique IDs**: Internal unique IDs unchanged (preserve `_notify`, `_remote` suffixes)
4. **Tests**: All existing tests updated, 100% coverage maintained

### Part B: "Prefix with Emby" Toggles (Per Entity Type)
1. **Options Flow**: Four toggles for media_player, notify, remote, button
2. **Default**: All toggles ON by default
3. **Device Name**: When enabled, device names become "Emby {Device Name}"
4. **Per-Type Control**: Each entity type can be toggled independently
5. **Entity IDs**: Entity IDs correctly reflect prefix (e.g., `notify.emby_living_room_tv`)
6. **Tests**: 100% test coverage for new code
7. **Types**: No `Any` types used (strict mypy compliance)
8. **Documentation**: User-facing documentation updated

---

## Dependencies

- Phase 10 (Testing & CI/CD) - Must be complete
- No external dependencies required

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Suffix removal breaks existing automations | **High** | Document in CHANGELOG; this is pre-1.0 so acceptable |
| Prefix changes not applied immediately | Medium | Trigger entity reload on options change |
| Complex naming logic | Low | Centralize in `naming.py` helper module |

---

## Breaking Changes

### Entity ID Changes (Part A)

| Entity Type | Before | After |
|-------------|--------|-------|
| Notify | `notify.living_room_tv_notification` | `notify.living_room_tv` |
| Remote | `remote.living_room_tv_remote` | `remote.living_room_tv` |

**Migration:** Users must update any automations referencing old entity IDs.

---

## Out of Scope

- Per-device prefix customization (too complex)
- Localized prefixes (use English only)
- Automatic migration of automations (not possible)

---

## Version Notes

### Part A (Breaking)
- Removes redundant `_notification` and `_remote` suffixes from entity IDs
- This is a breaking change but the integration is pre-1.0
- Document clearly in CHANGELOG

### Part B (Additive)
- Prefix feature is additive and backward-compatible
- Default behavior: no prefix (empty string)
- Notify entities default to "prefix enabled" when a prefix is set
- No config entry migration required (options default to current behavior)
