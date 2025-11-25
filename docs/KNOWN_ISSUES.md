# Known Issues

This document tracks known issues and planned fixes for the Home Assistant Emby integration.

---

## Active Issues

*No active issues.*

---

## Resolved Issues

### 1. `via_device` Warning on Entity Registration (FIXED)

**Severity:** Warning (non-breaking)

**Introduced:** Phase 2

**Fixed In:** Phase 6

**Original Symptom:**
```
WARNING [homeassistant.helpers.frame] Detected that custom integration 'embymedia'
calls `device_registry.async_get_or_create` referencing a non existing `via_device`
('embymedia', '<server_id>'), with device info: {...}
```

**Root Cause:**
Media player entities reference the Emby server as their parent device via `via_device`, but the server device was not explicitly registered before the client entities were created.

**Resolution:**
Server device is now registered in `__init__.py:async_setup_entry()` before forwarding to platforms. The fix registers the Emby server as a device with manufacturer, model, name, and version before any entities are created.

**Location of Fix:**
- `custom_components/embymedia/__init__.py` - lines 89-100

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
