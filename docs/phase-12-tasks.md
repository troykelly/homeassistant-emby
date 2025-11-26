# Phase 12: Sensor Platform - Comprehensive Server & Library Statistics

## Overview

This phase adds a comprehensive sensor platform to expose Emby server health, library statistics, playback activity, and user data to Home Assistant. Sensors are organized under the Emby server device and leverage WebSocket subscriptions for real-time updates where possible.

## Data Sources

### WebSocket Subscriptions (Real-Time)

| Subscription | Response Type | Data Available |
|-------------|---------------|----------------|
| `SessionsStart` | `Sessions` | Active sessions, NowPlayingItem, PlayState, PlayMethod |
| `ScheduledTasksInfoStart` | `ScheduledTasksInfo` | Task name, State, CurrentProgressPercentage |
| `ActivityLogEntryStart` | `ActivityLogEntry` | New activity entries (push-based) |

### WebSocket Events (Push-Based)

These fire automatically when events occur:
- `LibraryChanged` - Trigger library count refresh
- `PlaybackStarted` / `PlaybackStopped` - Update stream counts
- `ServerRestarting` / `ServerShuttingDown` - Update server status
- `RestartRequired` - Update pending restart sensor
- `ScheduledTaskEnded` - Update task status

### REST API Endpoints (Polling)

| Endpoint | Data | Interval |
|----------|------|----------|
| `/System/Info` | Version, HasPendingRestart, HasUpdateAvailable | Startup + 5 min |
| `/Items/Counts` | MovieCount, SeriesCount, EpisodeCount, etc. | 1 hour |
| `/Library/VirtualFolders` | Per-library info, RefreshProgress | 1 hour |
| `/Users/{id}/Items?Filters=` | Favorites, Played, Resumable | 1 hour |
| `/Plugins` | Plugin count | Startup only |

---

## Sensor Specifications

### Server Sensors (Grouped under Emby Server Device)

#### Binary Sensors

| Entity ID | Name | Source | Description |
|-----------|------|--------|-------------|
| `binary_sensor.emby_{server}_connected` | Connected | Internal | Server reachable |
| `binary_sensor.emby_{server}_websocket` | WebSocket | Internal | WebSocket connected |
| `binary_sensor.emby_{server}_pending_restart` | Pending Restart | `/System/Info` | HasPendingRestart |
| `binary_sensor.emby_{server}_update_available` | Update Available | `/System/Info` | HasUpdateAvailable |
| `binary_sensor.emby_{server}_library_scan_active` | Library Scan Active | `ScheduledTasksInfo` WS | Any library scan running |

**Library Scan Active Sensor Attributes:**
- `progress_percent`: Current scan progress (0-100), null when not scanning
- `scanning_library`: Name of library being scanned, null when not scanning
- `task_name`: Full task name (e.g., "Scan media library")

#### Numeric Sensors

| Entity ID | Name | Source | Unit | State Class |
|-----------|------|--------|------|-------------|
| `sensor.emby_{server}_active_sessions` | Active Sessions | `Sessions` WS | sessions | measurement |
| `sensor.emby_{server}_active_streams` | Active Streams | `Sessions` WS | streams | measurement |
| `sensor.emby_{server}_transcoding_streams` | Transcoding Streams | `Sessions` WS | streams | measurement |
| `sensor.emby_{server}_direct_play_streams` | Direct Play Streams | `Sessions` WS | streams | measurement |
| `sensor.emby_{server}_direct_stream_streams` | Direct Stream Streams | `Sessions` WS | streams | measurement |

**Active Sessions Sensor Attributes:**
- `sessions`: List of session details (device, user, client, playing)
- `users`: List of unique connected usernames

**Active Streams Sensor Attributes:**
- `streams`: List of stream details (user, device, media_title, media_type, play_method, progress_percent)

#### Diagnostic Sensors

| Entity ID | Name | Source | Entity Category |
|-----------|------|--------|-----------------|
| `sensor.emby_{server}_version` | Server Version | `/System/Info` | diagnostic |
| `sensor.emby_{server}_running_tasks` | Running Tasks | `ScheduledTasksInfo` WS | diagnostic |

**Running Tasks Sensor Attributes:**
- `tasks`: List of running tasks with name, progress, category

---

### Library Count Sensors

#### Global Counts (from `/Items/Counts`)

| Entity ID | Name | Unit | State Class |
|-----------|------|------|-------------|
| `sensor.emby_{server}_movies` | Movies | movies | total |
| `sensor.emby_{server}_series` | Series | series | total |
| `sensor.emby_{server}_episodes` | Episodes | episodes | total |
| `sensor.emby_{server}_albums` | Albums | albums | total |
| `sensor.emby_{server}_songs` | Songs | songs | total |
| `sensor.emby_{server}_artists` | Artists | artists | total |

#### Per-Library Counts

For each library in `/Library/VirtualFolders`:

| Entity ID Pattern | Name | Description |
|-------------------|------|-------------|
| `sensor.emby_{server}_{library_slug}_items` | {Library Name} Items | Total items in library |

**Per-Library Sensor Attributes:**
- `library_id`: Emby library ID
- `library_type`: Collection type (movies, tvshows, music, etc.)
- `locations`: List of file paths

**Examples from live server:**
- `sensor.emby_media_movies_items` → 1,209 movies
- `sensor.emby_media_tv_shows_items` → 5,797 items (374 series, 679 seasons, 4,620 episodes)
- `sensor.emby_media_music_items` → 14,341 items

---

### User Sensors (Per Configured User)

If a user is selected during config flow, create user-specific sensors:

| Entity ID | Name | Source | Unit |
|-----------|------|--------|------|
| `sensor.emby_{server}_{user}_favorites` | {User} Favorites | `?Filters=IsFavorite` | items |
| `sensor.emby_{server}_{user}_watched` | {User} Watched | `?Filters=IsPlayed` | items |
| `sensor.emby_{server}_{user}_in_progress` | {User} In Progress | `?Filters=IsResumable` | items |

**User Sensor Attributes:**
- `user_id`: Emby user ID
- `user_name`: Display name

---

## Implementation Architecture

### New Files

```
custom_components/embymedia/
├── sensor.py              # SensorEntity implementations
├── binary_sensor.py       # BinarySensorEntity implementations
└── coordinator_sensors.py # Separate coordinator for library stats (slow poll)
```

### Coordinator Strategy

1. **Existing `EmbyDataUpdateCoordinator`** (10s/60s poll)
   - Already has session data
   - Add: Subscribe to `ScheduledTasksInfoStart` via WebSocket
   - Provides data for: Active sessions, streams, transcoding, tasks

2. **New `EmbyLibraryCoordinator`** (1 hour poll)
   - Fetches `/Items/Counts`
   - Fetches `/Library/VirtualFolders` with item counts
   - Fetches user-specific counts
   - Triggers early refresh on `LibraryChanged` WebSocket event

3. **New `EmbyServerCoordinator`** (5 min poll)
   - Fetches `/System/Info`
   - Can be refreshed on `RestartRequired` event

### WebSocket Enhancements

Extend `EmbyWebSocket` to:
1. Subscribe to `ScheduledTasksInfoStart` for task monitoring
2. Handle `LibraryChanged` event to trigger library coordinator refresh
3. Handle `RestartRequired` event to update server info

### Entity Base Classes

```python
class EmbyServerSensorEntity(CoordinatorEntity, SensorEntity):
    """Base class for server-level sensors."""

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info - grouped under server device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.server_id)},
            name=f"Emby {self.coordinator.server_name}",
            manufacturer="Emby",
            model="Media Server",
            sw_version=self.coordinator.server_version,
        )
```

---

## Task Breakdown

### 12.1 Infrastructure Setup
- [ ] Create `sensor.py` with platform setup
- [ ] Create `binary_sensor.py` with platform setup
- [ ] Create `EmbyLibraryCoordinator` for slow-polling library data
- [ ] Create `EmbyServerCoordinator` for server info polling
- [ ] Add `Platform.SENSOR` and `Platform.BINARY_SENSOR` to `PLATFORMS`
- [ ] Add new TypedDicts for API responses (`EmbyItemCounts`, `EmbyScheduledTask`)

### 12.2 WebSocket Enhancements
- [ ] Add `async_subscribe_scheduled_tasks()` method to `EmbyWebSocket`
- [ ] Handle `ScheduledTasksInfo` messages in coordinator
- [ ] Handle `LibraryChanged` event to trigger library refresh
- [ ] Handle `RestartRequired` event to trigger server info refresh
- [ ] Store task data in coordinator for sensor access

### 12.3 Server Binary Sensors
- [ ] `EmbyConnectedBinarySensor` - server reachable
- [ ] `EmbyWebSocketBinarySensor` - WebSocket connected
- [ ] `EmbyPendingRestartBinarySensor` - from `/System/Info`
- [ ] `EmbyUpdateAvailableBinarySensor` - from `/System/Info`
- [ ] `EmbyLibraryScanActiveBinarySensor` - from `ScheduledTasksInfo` with progress attribute

### 12.4 Server Numeric Sensors
- [ ] `EmbyActiveSessionsSensor` - count from Sessions
- [ ] `EmbyActiveStreamsSensor` - count where NowPlayingItem
- [ ] `EmbyTranscodingStreamsSensor` - count where PlayMethod=Transcode
- [ ] `EmbyDirectPlayStreamsSensor` - count where PlayMethod=DirectPlay
- [ ] `EmbyDirectStreamStreamsSensor` - count where PlayMethod=DirectStream

### 12.5 Server Diagnostic Sensors
- [ ] `EmbyServerVersionSensor` - from `/System/Info`
- [ ] `EmbyRunningTasksSensor` - count from `ScheduledTasksInfo`

### 12.6 Library Count Sensors
- [ ] `EmbyMovieCountSensor` - from `/Items/Counts`
- [ ] `EmbySeriesCountSensor` - from `/Items/Counts`
- [ ] `EmbyEpisodeCountSensor` - from `/Items/Counts`
- [ ] `EmbyAlbumCountSensor` - from `/Items/Counts`
- [ ] `EmbySongCountSensor` - from `/Items/Counts`
- [ ] `EmbyArtistCountSensor` - from `/Items/Counts`

### 12.7 Per-Library Sensors
- [ ] Dynamic sensor creation for each library from `/Library/VirtualFolders`
- [ ] Query item count per library via `/Users/{id}/Items?ParentId={lib}&Limit=0`
- [ ] Include library_type and locations as attributes

### 12.8 User Sensors
- [ ] `EmbyUserFavoritesSensor` - from `?Filters=IsFavorite`
- [ ] `EmbyUserWatchedSensor` - from `?Filters=IsPlayed`
- [ ] `EmbyUserInProgressSensor` - from `?Filters=IsResumable`
- [ ] Only create if user_id is configured

### 12.9 Configuration Options
- [ ] Add `CONF_ENABLE_LIBRARY_SENSORS` option (default: True)
- [ ] Add `CONF_ENABLE_USER_SENSORS` option (default: True)
- [ ] Add `CONF_LIBRARY_SCAN_INTERVAL` option (default: 3600 seconds)
- [ ] Update options flow with sensor toggles

### 12.10 API Client Extensions
- [ ] Add `async_get_item_counts()` method
- [ ] Add `async_get_scheduled_tasks()` method
- [ ] Add `async_get_user_item_count()` method with filters
- [ ] Add TypedDicts for all new response types

### 12.11 Translations
- [ ] Add sensor name translations to `strings.json`
- [ ] Add sensor name translations to `en.json`
- [ ] Add options flow translations for sensor toggles

### 12.12 Testing
- [ ] Unit tests for all sensor entities
- [ ] Unit tests for new coordinators
- [ ] Unit tests for WebSocket task subscription
- [ ] Unit tests for API client extensions
- [ ] Integration tests for sensor platform setup
- [ ] 100% code coverage

### 12.13 Documentation
- [ ] Update README with sensor documentation
- [ ] Add sensor examples to documentation
- [ ] Document WebSocket subscription behavior

---

## API Response TypedDicts

```python
class EmbyItemCounts(TypedDict):
    """Response from /Items/Counts endpoint."""
    MovieCount: int
    SeriesCount: int
    EpisodeCount: int
    GameCount: int
    ArtistCount: int
    ProgramCount: int
    GameSystemCount: int
    TrailerCount: int
    SongCount: int
    AlbumCount: int
    MusicVideoCount: int
    BoxSetCount: int
    BookCount: int
    ItemCount: int


class EmbyTaskResult(TypedDict):
    """Last execution result for a scheduled task."""
    StartTimeUtc: str
    EndTimeUtc: str
    Status: str  # "Completed", "Failed", "Cancelled"
    Name: str
    Key: str
    Id: str


class EmbyScheduledTask(TypedDict):
    """Response item from /ScheduledTasks endpoint."""
    Name: str
    State: str  # "Idle", "Running", "Cancelling"
    Id: str
    LastExecutionResult: NotRequired[EmbyTaskResult]
    Triggers: list[dict[str, object]]
    Description: str
    Category: str
    IsHidden: bool
    Key: str
    CurrentProgressPercentage: NotRequired[float]  # Only when running
```

---

## Success Criteria

- [ ] All server sensors grouped under Emby server device
- [ ] Real-time session/stream sensors update via WebSocket
- [ ] Library scan sensor shows progress percentage when active
- [ ] Library counts refresh on `LibraryChanged` event
- [ ] Per-library sensors created dynamically
- [ ] User sensors created when user is configured
- [ ] All sensors have appropriate state_class for statistics
- [ ] 100% test coverage
- [ ] No `Any` types (strict typing)
- [ ] All translations complete

---

## Dependencies

- Phase 7 (WebSocket) - Required for real-time subscriptions
- Phase 2 (Coordinator) - Base coordinator patterns

## Breaking Changes

None - new platform addition only.
