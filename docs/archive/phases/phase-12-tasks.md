# Phase 12: Sensor Platform - Server & Library Statistics ✅

## Overview

This phase adds a comprehensive sensor platform to expose Emby server health, library statistics, and playback activity to Home Assistant. Sensors are organized under the Emby server device.

## Implementation Status: COMPLETE

### Completed Features

#### Coordinators ✅
- [x] `EmbyServerCoordinator` - 5-minute polling for server info and scheduled tasks
- [x] `EmbyLibraryCoordinator` - 1-hour polling for library counts
- [x] `EmbyRuntimeData` class to manage all three coordinators

#### Binary Sensors ✅
| Entity ID | Name | Source | Status |
|-----------|------|--------|--------|
| `binary_sensor.{server}_connected` | Connected | Coordinator state | ✅ |
| `binary_sensor.{server}_pending_restart` | Pending Restart | `/System/Info` | ✅ |
| `binary_sensor.{server}_update_available` | Update Available | `/System/Info` | ✅ |
| `binary_sensor.{server}_library_scan_active` | Library Scan Active | `/ScheduledTasks` | ✅ |

**Library Scan Active Sensor Attributes:**
- `progress_percent`: Current scan progress (0-100), null when not scanning

#### Numeric Sensors ✅
| Entity ID | Name | Source | Status |
|-----------|------|--------|--------|
| `sensor.{server}_server_version` | Server Version | `/System/Info` | ✅ |
| `sensor.{server}_running_tasks` | Running Tasks | `/ScheduledTasks` | ✅ |
| `sensor.{server}_active_sessions` | Active Sessions | Session coordinator | ✅ |

#### Library Count Sensors ✅
| Entity ID | Name | Source | Status |
|-----------|------|--------|--------|
| `sensor.{server}_movies` | Movies | `/Items/Counts` | ✅ |
| `sensor.{server}_tv_shows` | TV Shows | `/Items/Counts` | ✅ |
| `sensor.{server}_episodes` | Episodes | `/Items/Counts` | ✅ |
| `sensor.{server}_songs` | Songs | `/Items/Counts` | ✅ |
| `sensor.{server}_albums` | Albums | `/Items/Counts` | ✅ |
| `sensor.{server}_artists` | Artists | `/Items/Counts` | ✅ |

#### API Methods ✅
- [x] `async_get_item_counts()` - Library item counts from `/Items/Counts`
- [x] `async_get_scheduled_tasks()` - Task status from `/ScheduledTasks`
- [x] `async_get_virtual_folders()` - Library info from `/Library/VirtualFolders`
- [x] `async_get_user_item_count()` - User-specific counts with filters

#### TypedDicts ✅
- [x] `EmbyItemCounts` - Response from `/Items/Counts`
- [x] `EmbyScheduledTask` - Task item from `/ScheduledTasks`
- [x] `EmbyVirtualFolder` - Library from `/Library/VirtualFolders`

#### Translations ✅
- [x] Binary sensor translations in `strings.json` and `en.json`
- [x] Sensor translations in `strings.json` and `en.json`

#### Testing ✅
- [x] 941 tests with 100% code coverage
- [x] Unit tests for all sensor entities
- [x] Unit tests for coordinators
- [x] Unit tests for API methods
- [x] Tests for None data edge cases

---

## Files Created/Modified

### New Files
- `custom_components/embymedia/sensor.py` - Sensor entity implementations
- `custom_components/embymedia/binary_sensor.py` - Binary sensor implementations
- `custom_components/embymedia/coordinator_sensors.py` - Server and library coordinators
- `tests/test_sensor.py` - Sensor platform tests
- `tests/test_binary_sensor.py` - Binary sensor tests
- `tests/test_coordinator_sensors.py` - Coordinator tests
- `tests/test_api_sensor_methods.py` - API method tests
- `tests/test_sensor_config.py` - Sensor configuration tests
- `tests/test_sensor_types.py` - Sensor type tests

### Modified Files
- `custom_components/embymedia/__init__.py` - Added runtime_data structure
- `custom_components/embymedia/api.py` - Added sensor API methods
- `custom_components/embymedia/const.py` - Added TypedDicts and constants
- `custom_components/embymedia/strings.json` - Added sensor translations
- `custom_components/embymedia/translations/en.json` - Added sensor translations
- All platform files - Updated to use `runtime_data.session_coordinator`
- All test files - Updated for new runtime_data structure

---

## Architecture

### Coordinator Strategy

```
EmbyRuntimeData
├── session_coordinator (EmbyDataUpdateCoordinator) - 10s/60s polling
│   └── Session data for media players, remotes, notify, buttons
├── server_coordinator (EmbyServerCoordinator) - 5 min polling
│   └── Server info, scheduled tasks, restart status
└── library_coordinator (EmbyLibraryCoordinator) - 1 hour polling
    └── Library counts, virtual folders
```

### Entity Hierarchy

All sensors are grouped under the Emby server device:

```
Device: Emby {Server Name}
├── binary_sensor.{server}_connected
├── binary_sensor.{server}_pending_restart
├── binary_sensor.{server}_update_available
├── binary_sensor.{server}_library_scan_active
├── sensor.{server}_server_version
├── sensor.{server}_running_tasks
├── sensor.{server}_active_sessions
├── sensor.{server}_movies
├── sensor.{server}_tv_shows
├── sensor.{server}_episodes
├── sensor.{server}_songs
├── sensor.{server}_albums
└── sensor.{server}_artists
```

---

## Success Criteria - All Met ✅

- [x] All server sensors grouped under Emby server device
- [x] Library scan sensor shows progress percentage when active
- [x] Library counts available (movies, series, episodes, songs, albums, artists)
- [x] All sensors have appropriate state_class for statistics
- [x] 941 tests with 100% code coverage
- [x] No `Any` types (strict typing)
- [x] All translations complete

---

## Future Enhancements (Not Implemented)

The following features from the original spec were deferred:

- WebSocket subscription to `ScheduledTasksInfoStart` for real-time task updates
- Per-library item count sensors (dynamic from `/Library/VirtualFolders`)
- User-specific sensors (favorites, watched, in-progress)
- Configuration options for sensor toggles
- Active streams breakdown (transcoding vs direct play)

These can be added in a future phase if needed.
