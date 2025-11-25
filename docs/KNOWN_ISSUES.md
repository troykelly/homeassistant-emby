# Known Issues

This document tracks known issues and planned fixes for the Home Assistant Emby integration.

---

## Active Issues

### 1. `via_device` Warning on Entity Registration

**Severity:** Warning (non-breaking)

**Introduced:** Phase 2

**Affected Versions:** All current versions

**Symptom:**
```
WARNING [homeassistant.helpers.frame] Detected that custom integration 'embymedia'
calls `device_registry.async_get_or_create` referencing a non existing `via_device`
('embymedia', '<server_id>'), with device info: {...}
```

**Root Cause:**
Media player entities reference the Emby server as their parent device via `via_device`, but the server device is not explicitly registered before the client entities are created. The entities attempt to link to a server device that doesn't exist yet.

**Location:**
- `custom_components/embymedia/entity.py:80` and `entity.py:89`

**Impact:**
- Warning message in logs
- Device hierarchy may not display correctly in HA UI
- Will stop working in Home Assistant 2025.12.0 (per warning)

**Planned Fix:**
Register the Emby server as a device during integration setup (`__init__.py`) before any media player entities are created. This should be addressed in Phase 9 (Polish & Production Readiness) or earlier if blocking.

**Workaround:**
None required - functionality works correctly, only cosmetic warning.

**Related Code:**
```python
# entity.py - current implementation
device_info = DeviceInfo(
    identifiers={(DOMAIN, self._device_id)},
    via_device=(DOMAIN, self.coordinator.server_id),  # Server device doesn't exist
    ...
)
```

**Proposed Fix:**
```python
# __init__.py - register server device first
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # ... existing setup ...

    # Register server as a device BEFORE forwarding to platforms
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, coordinator.server_id)},
        manufacturer="Emby",
        model="Emby Server",
        name=server_info["ServerName"],
        sw_version=server_info["Version"],
    )

    # Now forward to platforms - entities can reference via_device
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
```

---

## Resolved Issues

*No resolved issues yet.*

---

## Issue Template

When adding new issues, use this template:

```markdown
### N. Issue Title

**Severity:** Critical / Warning / Minor

**Introduced:** Phase N

**Affected Versions:**

**Symptom:**

**Root Cause:**

**Location:**

**Impact:**

**Planned Fix:**

**Workaround:**
```
