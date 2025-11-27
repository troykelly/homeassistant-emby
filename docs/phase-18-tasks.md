# Phase 18: User Activity & Statistics

## Overview

This phase implements comprehensive activity monitoring and statistics tracking for the Emby integration. Features include server activity logging, device management, user watch statistics, and real-time playback tracking via WebSocket events.

The implementation exposes activity data through sensor entities that provide insights into server usage, connected devices, and user behavior patterns.

## Implementation Status: NOT STARTED

---

## Background Research

### Emby Activity & Statistics APIs

#### Activity Log API
- **Endpoint:** `GET /System/ActivityLog/Entries`
- **Purpose:** Get server activity entries (user logins, library updates, etc.)
- **Parameters:**
  - `startIndex` - Pagination offset
  - `limit` - Max entries to return
  - `minDate` - Filter by date (ISO 8601 format)
  - `hasUserId` - Filter to entries with user association

#### Devices API
- **Endpoint:** `GET /Devices`
- **Purpose:** Get all registered devices
- **Parameters:**
  - `userId` - Filter by user
  - `supportsSync` - Filter by sync capability

#### WebSocket Events for Activity
- `PlaybackProgress` - Periodic playback position updates
- `ActivityLogEntry` - Real-time activity log additions
- `UserDataChanged` - User data modifications

### Activity Log Entry Types

Common activity types in Emby:
- `UserSignedIn` / `UserSignedOut`
- `AuthenticationSucceeded` / `AuthenticationFailed`
- `VideoPlayback` / `AudioPlayback`
- `VideoPlaybackStopped` / `AudioPlaybackStopped`
- `ItemAdded`
- `SubtitleDownload`
- `PluginInstalled` / `PluginUpdated`

---

## Task Breakdown

### Task 18.1: Activity Log TypedDicts

**File:** `custom_components/embymedia/const.py`

Add TypedDicts for Activity Log API responses.

#### 18.1.1 EmbyActivityLogEntry TypedDict
```python
class EmbyActivityLogEntry(TypedDict, total=False):
    """Response item from /System/ActivityLog/Entries endpoint.

    Represents a single activity log entry from the Emby server.
    """

    # Required fields
    Id: int  # Unique entry ID
    Name: str  # Activity description
    Type: str  # Activity type (UserSignedIn, VideoPlayback, etc.)
    Date: str  # ISO 8601 timestamp
    Severity: str  # "Info", "Warn", "Error"

    # Optional fields
    UserId: str  # Associated user ID
    ItemId: str  # Associated item ID
    ShortOverview: str  # Brief description
    Overview: str  # Full description
```

#### 18.1.2 EmbyActivityLogResponse TypedDict
```python
class EmbyActivityLogResponse(TypedDict):
    """Response from /System/ActivityLog/Entries endpoint."""

    Items: list[EmbyActivityLogEntry]
    TotalRecordCount: int
    StartIndex: int
```

**Pattern to follow (from const.py):**
```python
class EmbyItemCounts(TypedDict):
    """Response from /Items/Counts endpoint.

    Contains counts of various media types in the library.
    """

    MovieCount: int
    SeriesCount: int
    EpisodeCount: int
    # ... rest of fields
```

**Tests:**
- [ ] Type annotation validation (mypy strict)
- [ ] Optional field handling with NotRequired
- [ ] All fields properly typed (no Any)

**Acceptance Criteria:**
- TypedDicts added to const.py
- No `Any` types used
- Mypy strict passes
- Follows existing TypedDict patterns

---

### Task 18.2: Device TypedDicts

**File:** `custom_components/embymedia/const.py`

Add TypedDicts for Device API responses.

#### 18.2.1 EmbyDeviceInfo TypedDict
```python
class EmbyDeviceInfo(TypedDict, total=False):
    """Response item from /Devices endpoint.

    Represents a registered device on the Emby server.
    """

    # Required fields
    Id: str  # Device ID
    Name: str  # Device name
    LastUserId: str  # Last user that used this device
    LastUserName: str  # Last username
    DateLastActivity: str  # ISO 8601 timestamp

    # Optional fields
    AppName: str  # Application name (Emby for Android, etc.)
    AppVersion: str  # Application version
    CustomName: str  # User-customized device name
    Capabilities: dict[str, object]  # Device capabilities
```

#### 18.2.2 EmbyDevicesResponse TypedDict
```python
class EmbyDevicesResponse(TypedDict):
    """Response from /Devices endpoint."""

    Items: list[EmbyDeviceInfo]
    TotalRecordCount: int
```

**Pattern to follow:**
```python
class EmbySessionResponse(TypedDict):
    """Type definition for /Sessions endpoint response item."""

    Id: str
    UserId: NotRequired[str]
    UserName: NotRequired[str]
    # ... rest of fields
```

**Tests:**
- [ ] Type annotation validation
- [ ] Device info parsing from mock response
- [ ] Handle missing optional fields gracefully

**Acceptance Criteria:**
- TypedDicts added to const.py
- Follows existing session response patterns
- All tests pass with 100% coverage

---

### Task 18.3: Activity Log API Methods

**File:** `custom_components/embymedia/api.py`

Add API methods for fetching activity log entries.

#### 18.3.1 async_get_activity_log method
```python
async def async_get_activity_log(
    self,
    start_index: int = 0,
    limit: int = 50,
    min_date: str | None = None,
    has_user_id: bool | None = None,
) -> EmbyActivityLogResponse:
    """Get server activity log entries.

    Args:
        start_index: Pagination offset. Defaults to 0.
        limit: Maximum entries to return. Defaults to 50.
        min_date: ISO 8601 date string to filter entries after.
        has_user_id: Filter to entries associated with a user.

    Returns:
        Activity log response with entries and total count.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    params: list[str] = [
        f"StartIndex={start_index}",
        f"Limit={limit}",
    ]
    if min_date:
        params.append(f"MinDate={min_date}")
    if has_user_id is not None:
        params.append(f"HasUserId={'true' if has_user_id else 'false'}")

    query_string = "&".join(params)
    endpoint = f"/System/ActivityLog/Entries?{query_string}"
    response = await self._request(HTTP_GET, endpoint)
    return response  # type: ignore[return-value]
```

**Pattern to follow (from api.py):**
```python
async def async_get_scheduled_tasks(
    self,
    include_hidden: bool = False,
) -> list[EmbyScheduledTask]:
    """Get scheduled tasks status.

    Args:
        include_hidden: Whether to include hidden tasks.

    Returns:
        List of scheduled tasks with their current state.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    endpoint = "/ScheduledTasks"
    if include_hidden:
        endpoint = f"{endpoint}?IsHidden=true"
    response = await self._request(HTTP_GET, endpoint)
    return response  # type: ignore[return-value]
```

**Tests:**
- [ ] Test successful activity log fetch
- [ ] Test with pagination parameters
- [ ] Test with date filtering
- [ ] Test with has_user_id filter
- [ ] Test error handling (404, 500, timeout)

**Acceptance Criteria:**
- Method added to EmbyClient class
- Follows existing API method patterns
- Proper error handling
- Tests achieve 100% coverage

---

### Task 18.4: Device Management API Methods

**File:** `custom_components/embymedia/api.py`

Add API methods for device information.

#### 18.4.1 async_get_devices method
```python
async def async_get_devices(
    self,
    user_id: str | None = None,
) -> EmbyDevicesResponse:
    """Get registered devices.

    Args:
        user_id: Optional user ID to filter devices.

    Returns:
        Devices response with device list and total count.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    endpoint = "/Devices"
    if user_id:
        endpoint = f"{endpoint}?UserId={user_id}"
    response = await self._request(HTTP_GET, endpoint)
    return response  # type: ignore[return-value]
```

**Pattern to follow:**
```python
async def async_get_users(self) -> list[EmbyUser]:
    """Get list of users.

    Returns:
        List of user objects.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    response = await self._request(HTTP_GET, ENDPOINT_USERS)
    return response  # type: ignore[return-value]
```

**Tests:**
- [ ] Test successful device fetch
- [ ] Test with user_id filter
- [ ] Test empty device list
- [ ] Test error handling

**Acceptance Criteria:**
- Method added to EmbyClient class
- Returns properly typed response
- All edge cases tested
- 100% test coverage

---

### Task 18.5: Activity Sensor Implementation

**File:** `custom_components/embymedia/sensor.py`

Add sensor entity for displaying recent server activity.

#### 18.5.1 EmbyLastActivitySensor Class
```python
class EmbyLastActivitySensor(EmbyServerSensorBase):
    """Sensor for last server activity.

    Shows the most recent activity log entry with additional
    recent entries exposed as attributes.
    """

    _attr_icon = "mdi:history"
    _attr_translation_key = "last_activity"

    def __init__(self, coordinator: EmbyServerCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.server_id}_last_activity"

    @property
    def native_value(self) -> str | None:
        """Return the last activity description."""
        if self.coordinator.data is None:
            return None

        activities: list[EmbyActivityLogEntry] = self.coordinator.data.get(
            "recent_activities", []
        )
        if not activities:
            return None

        # Most recent activity
        return str(activities[0].get("Name", "Unknown"))

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return additional attributes."""
        if self.coordinator.data is None:
            return {}

        activities: list[EmbyActivityLogEntry] = self.coordinator.data.get(
            "recent_activities", []
        )

        return {
            "recent_entries": [
                {
                    "name": entry.get("Name"),
                    "type": entry.get("Type"),
                    "date": entry.get("Date"),
                    "severity": entry.get("Severity"),
                    "user": entry.get("UserId"),
                }
                for entry in activities[:10]  # Last 10 entries
            ],
            "entry_count": len(activities),
        }
```

**Pattern to follow (from sensor.py):**
```python
class EmbyRunningTasksSensor(EmbyServerSensorBase):
    """Sensor for running scheduled tasks count.

    Shows the number of currently running scheduled tasks.
    """

    _attr_icon = "mdi:cog-sync"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "running_tasks"

    def __init__(self, coordinator: EmbyServerCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.server_id}_running_tasks"

    @property
    def native_value(self) -> int | None:
        """Return the number of running tasks."""
        if self.coordinator.data is None:
            return None
        return int(self.coordinator.data.get("running_tasks_count", 0))
```

**Tests:**
- [ ] Test sensor state with activity data
- [ ] Test sensor with no activities
- [ ] Test extra_state_attributes
- [ ] Test availability
- [ ] Test device_info grouping

**Acceptance Criteria:**
- Sensor added to sensor.py
- Grouped under Emby server device
- Shows most recent activity as state
- Exposes last 10 entries as attributes
- All tests pass with 100% coverage

---

### Task 18.6: Connected Devices Sensor

**File:** `custom_components/embymedia/sensor.py`

Add sensor entity for tracking connected devices.

#### 18.6.1 EmbyConnectedDevicesSensor Class
```python
class EmbyConnectedDevicesSensor(EmbyServerSensorBase):
    """Sensor for connected devices count.

    Shows the total number of registered devices with
    device details as attributes.
    """

    _attr_icon = "mdi:devices"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "connected_devices"

    def __init__(self, coordinator: EmbyServerCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.server_id}_connected_devices"

    @property
    def native_value(self) -> int | None:
        """Return the number of connected devices."""
        if self.coordinator.data is None:
            return None

        devices: list[EmbyDeviceInfo] = self.coordinator.data.get("devices", [])
        return len(devices)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return device list as attributes."""
        if self.coordinator.data is None:
            return {}

        devices: list[EmbyDeviceInfo] = self.coordinator.data.get("devices", [])

        return {
            "devices": [
                {
                    "id": device.get("Id"),
                    "name": device.get("Name"),
                    "app": device.get("AppName"),
                    "version": device.get("AppVersion"),
                    "last_user": device.get("LastUserName"),
                    "last_activity": device.get("DateLastActivity"),
                }
                for device in devices
            ],
        }
```

**Pattern to follow:**
```python
class EmbyActiveSessionsSensor(EmbySessionSensorBase):
    """Sensor for active sessions count.

    Shows the number of currently connected clients.
    """

    _attr_icon = "mdi:account-multiple"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "active_sessions"

    def __init__(self, coordinator: EmbyDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.server_id}_active_sessions"

    @property
    def native_value(self) -> int:
        """Return the number of active sessions."""
        if self.coordinator.data is None:
            return 0
        return len(self.coordinator.data)
```

**Tests:**
- [ ] Test device count calculation
- [ ] Test with empty device list
- [ ] Test device attributes
- [ ] Test availability

**Acceptance Criteria:**
- Sensor shows device count as state
- Device details in extra_state_attributes
- Grouped under server device
- 100% test coverage

---

### Task 18.7: Server Coordinator Enhancement

**File:** `custom_components/embymedia/coordinator_sensors.py`

Update EmbyServerCoordinator to fetch activity log and device data.

#### 18.7.1 Update _async_update_data method
```python
async def _async_update_data(self) -> dict[str, object]:
    """Fetch server data from Emby server.

    Returns:
        Dictionary with server info, tasks, activities, and devices.

    Raises:
        UpdateFailed: If fetching data fails.
    """
    try:
        # Existing server info and tasks fetch
        server_info = await self.client.async_get_server_info()
        scheduled_tasks = await self.client.async_get_scheduled_tasks()

        # NEW: Fetch activity log (last 20 entries)
        activity_log = await self.client.async_get_activity_log(
            start_index=0,
            limit=20,
        )

        # NEW: Fetch connected devices
        devices_response = await self.client.async_get_devices()

        # Count running tasks
        running_tasks_count = sum(
            1 for task in scheduled_tasks if task.get("State") == "Running"
        )

        return {
            "server_version": server_info.get("Version", "Unknown"),
            "server_name": server_info.get("ServerName", "Emby"),
            "operating_system": server_info.get("OperatingSystem", "Unknown"),
            "has_pending_restart": server_info.get("HasPendingRestart", False),
            "is_shutting_down": server_info.get("IsShuttingDown", False),
            "running_tasks_count": running_tasks_count,
            "scheduled_tasks": scheduled_tasks,
            # NEW fields
            "recent_activities": activity_log.get("Items", []),
            "activity_count": activity_log.get("TotalRecordCount", 0),
            "devices": devices_response.get("Items", []),
            "device_count": devices_response.get("TotalRecordCount", 0),
        }

    except EmbyError as err:
        raise UpdateFailed(f"Error fetching server data: {err}") from err
```

**Pattern to follow (from coordinator_sensors.py):**
```python
async def _async_update_data(self) -> dict[str, object]:
    """Fetch library data from Emby server.

    Returns:
        Dictionary with library counts.

    Raises:
        UpdateFailed: If fetching data fails.
    """
    try:
        item_counts = await self.client.async_get_item_counts()

        return {
            "movie_count": item_counts.get("MovieCount", 0),
            "series_count": item_counts.get("SeriesCount", 0),
            # ... rest of counts
        }
    except EmbyError as err:
        raise UpdateFailed(f"Error fetching library data: {err}") from err
```

**Tests:**
- [ ] Test successful data fetch with activities and devices
- [ ] Test error handling for activity log failures
- [ ] Test error handling for device fetch failures
- [ ] Test graceful degradation if activity/device APIs unavailable
- [ ] Test data structure returned

**Acceptance Criteria:**
- Coordinator fetches activity log and devices
- Graceful error handling (don't fail entire update if one API fails)
- Data available to sensor entities
- 100% test coverage

---

### Task 18.8: User Statistics Tracking (Playback Progress)

**File:** `custom_components/embymedia/coordinator.py`

Enhance WebSocket message handling to track playback statistics.

#### 18.8.1 Add playback tracking to EmbyDataUpdateCoordinator
```python
def __init__(
    self,
    hass: HomeAssistant,
    client: EmbyClient,
    server_id: str,
    server_name: str,
    config_entry: EmbyConfigEntry,
    scan_interval: int = DEFAULT_SCAN_INTERVAL,
    user_id: str | None = None,
) -> None:
    """Initialize the coordinator."""
    super().__init__(...)
    # ... existing init code ...

    # NEW: Track playback statistics
    self._playback_sessions: dict[str, dict[str, object]] = {}
    self._daily_watch_time: int = 0  # Total seconds watched today
    self._last_reset_date: str = datetime.now().date().isoformat()
```

#### 18.8.2 Update _handle_websocket_message
```python
def _handle_websocket_message(
    self,
    message_type: str,
    data: Any,
) -> None:
    """Handle incoming WebSocket messages."""
    # Existing message handling...

    if message_type == "PlaybackProgress":
        # NEW: Track playback progress for statistics
        self._track_playback_progress(data)
    # ... rest of handlers
```

#### 18.8.3 Add _track_playback_progress method
```python
def _track_playback_progress(self, data: dict[str, object]) -> None:
    """Track playback progress for statistics.

    Args:
        data: PlaybackProgress WebSocket event data.
    """
    from datetime import datetime

    # Reset daily counter if it's a new day
    today = datetime.now().date().isoformat()
    if today != self._last_reset_date:
        self._daily_watch_time = 0
        self._last_reset_date = today

    # Extract session data
    session_id = str(data.get("PlaySessionId", ""))
    if not session_id:
        return

    position_ticks = data.get("PositionTicks", 0)

    # Calculate watch time since last update
    if session_id in self._playback_sessions:
        last_position = self._playback_sessions[session_id].get("position_ticks", 0)
        # Only count forward progress (not seeks backward)
        if isinstance(position_ticks, int) and isinstance(last_position, int):
            if position_ticks > last_position:
                ticks_delta = position_ticks - last_position
                seconds_delta = ticks_delta // EMBY_TICKS_PER_SECOND
                # Sanity check: don't count huge jumps (likely seeks)
                if seconds_delta < 60:  # Max 60s between updates
                    self._daily_watch_time += seconds_delta

    # Update session tracking
    self._playback_sessions[session_id] = {
        "position_ticks": position_ticks,
        "last_update": datetime.now().isoformat(),
        "item_id": data.get("ItemId"),
        "item_name": data.get("ItemName"),
    }
```

**Pattern to follow (from coordinator.py):**
```python
def _handle_websocket_message(
    self,
    message_type: str,
    data: Any,
) -> None:
    """Handle incoming WebSocket messages.

    Args:
        message_type: The type of message received.
        data: The message payload.
    """
    if message_type == "Sessions":
        # Direct session update from WebSocket
        self._process_sessions_data(data)
    elif message_type in (
        "PlaybackStarted",
        "PlaybackStopped",
        "PlaybackProgress",
        "SessionEnded",
    ):
        # Trigger a refresh to get latest session state (with debouncing)
        self._trigger_debounced_refresh()
    # ... rest of handlers
```

**Tests:**
- [ ] Test playback progress tracking
- [ ] Test daily watch time calculation
- [ ] Test daily reset at midnight
- [ ] Test session tracking updates
- [ ] Test skip backwards detection
- [ ] Test large seek detection (don't count as watch time)

**Acceptance Criteria:**
- Playback progress tracked in real-time
- Daily watch time calculated accurately
- Resets at midnight
- Handles edge cases (seeks, pauses)
- 100% test coverage

---

### Task 18.9: Watch Statistics Sensor

**File:** `custom_components/embymedia/sensor.py`

Add sensor to expose user watch statistics.

#### 18.9.1 EmbyWatchStatisticsSensor Class
```python
class EmbyWatchStatisticsSensor(EmbySessionSensorBase):
    """Sensor for watch time statistics.

    Shows total watch time today with additional statistics
    as attributes.
    """

    _attr_icon = "mdi:clock-outline"
    _attr_translation_key = "watch_statistics"
    _attr_native_unit_of_measurement = "min"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator: EmbyDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.server_id}_watch_statistics"

    @property
    def native_value(self) -> int:
        """Return today's watch time in minutes."""
        # Access coordinator's _daily_watch_time
        watch_seconds = getattr(self.coordinator, "_daily_watch_time", 0)
        return watch_seconds // 60

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return playback session details."""
        playback_sessions = getattr(self.coordinator, "_playback_sessions", {})

        return {
            "active_sessions": len(playback_sessions),
            "sessions": [
                {
                    "item_id": session.get("item_id"),
                    "item_name": session.get("item_name"),
                    "last_update": session.get("last_update"),
                }
                for session in playback_sessions.values()
            ],
        }
```

**Pattern to follow:**
```python
class EmbyActiveSessionsSensor(EmbySessionSensorBase):
    """Sensor for active sessions count."""

    _attr_icon = "mdi:account-multiple"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "active_sessions"

    def __init__(self, coordinator: EmbyDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.server_id}_active_sessions"

    @property
    def native_value(self) -> int:
        """Return the number of active sessions."""
        if self.coordinator.data is None:
            return 0
        return len(self.coordinator.data)
```

**Tests:**
- [ ] Test watch time calculation
- [ ] Test minutes conversion
- [ ] Test with no watch time
- [ ] Test session attributes
- [ ] Test state_class for statistics

**Acceptance Criteria:**
- Sensor shows daily watch time in minutes
- Active sessions exposed as attributes
- Grouped under server device
- Compatible with HA statistics (TOTAL_INCREASING)
- 100% test coverage

---

### Task 18.10: Translations

**Files:**
- `custom_components/embymedia/strings.json`
- `custom_components/embymedia/translations/en.json`

Add translations for new sensor entities.

#### 18.10.1 Sensor translations
```json
{
  "entity": {
    "sensor": {
      "last_activity": {
        "name": "Last Activity"
      },
      "connected_devices": {
        "name": "Connected Devices"
      },
      "watch_statistics": {
        "name": "Watch Time Today"
      }
    }
  }
}
```

**Pattern to follow (from strings.json):**
```json
{
  "entity": {
    "sensor": {
      "active_sessions": {
        "name": "Active Sessions"
      },
      "movie_count": {
        "name": "Movies"
      }
    }
  }
}
```

**Tests:**
- [ ] Translation keys exist in strings.json
- [ ] Translation keys exist in en.json
- [ ] Keys match translation_key in sensor classes

**Acceptance Criteria:**
- All sensor translation keys added
- Matches existing translation patterns
- No missing translations

---

### Task 18.11: Platform Registration

**File:** `custom_components/embymedia/sensor.py`

Register new sensors in async_setup_entry.

#### 18.11.1 Update async_setup_entry
```python
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EmbyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Emby sensors from a config entry."""
    runtime_data = config_entry.runtime_data
    server_coordinator: EmbyServerCoordinator = runtime_data.server_coordinator
    library_coordinator: EmbyLibraryCoordinator = runtime_data.library_coordinator
    session_coordinator: EmbyDataUpdateCoordinator = runtime_data.session_coordinator
    server_name = server_coordinator.server_name

    entities: list[SensorEntity] = [
        # Server info sensors
        EmbyVersionSensor(server_coordinator),
        EmbyRunningTasksSensor(server_coordinator),
        # NEW: Activity sensors
        EmbyLastActivitySensor(server_coordinator),
        EmbyConnectedDevicesSensor(server_coordinator),
        # Session sensors
        EmbyActiveSessionsSensor(session_coordinator),
        # NEW: Watch statistics
        EmbyWatchStatisticsSensor(session_coordinator),
        # Library count sensors
        EmbyMovieCountSensor(library_coordinator, server_name),
        EmbySeriesCountSensor(library_coordinator, server_name),
        EmbyEpisodeCountSensor(library_coordinator, server_name),
        EmbySongCountSensor(library_coordinator, server_name),
        EmbyAlbumCountSensor(library_coordinator, server_name),
        EmbyArtistCountSensor(library_coordinator, server_name),
    ]

    async_add_entities(entities)
```

**Pattern to follow:**
```python
entities: list[SensorEntity] = [
    # Server info sensors
    EmbyVersionSensor(server_coordinator),
    EmbyRunningTasksSensor(server_coordinator),
    # Session sensors
    EmbyActiveSessionsSensor(session_coordinator),
    # Library count sensors
    EmbyMovieCountSensor(library_coordinator, server_name),
    # ... rest
]
```

**Tests:**
- [ ] Test all sensors created in setup
- [ ] Test proper coordinator assignment
- [ ] Test unique_id uniqueness

**Acceptance Criteria:**
- All new sensors registered
- Proper coordinator dependencies
- All setup tests pass

---

### Task 18.12: Testing & Documentation

#### 18.12.1 Test Files
Create comprehensive tests:

**File:** `tests/test_api_activity.py`
- Test `async_get_activity_log()` method
- Test pagination parameters
- Test date filtering
- Test error handling

**File:** `tests/test_api_devices.py`
- Test `async_get_devices()` method
- Test user_id filtering
- Test empty responses
- Test error handling

**File:** `tests/test_sensor_activity.py`
- Test EmbyLastActivitySensor state and attributes
- Test EmbyConnectedDevicesSensor state and attributes
- Test EmbyWatchStatisticsSensor calculations
- Test sensor availability
- Test device_info grouping

**File:** `tests/test_coordinator_activity.py`
- Test server coordinator with activity/device data
- Test playback progress tracking
- Test daily watch time calculation
- Test daily reset logic

**Pattern to follow (from tests/test_sensor.py):**
```python
async def test_running_tasks_sensor(
    hass: HomeAssistant,
    mock_server_coordinator: EmbyServerCoordinator,
) -> None:
    """Test running tasks sensor."""
    sensor = EmbyRunningTasksSensor(mock_server_coordinator)

    # Test with data
    mock_server_coordinator.async_set_updated_data({
        "running_tasks_count": 3,
    })
    assert sensor.native_value == 3

    # Test with None data
    mock_server_coordinator.async_set_updated_data(None)
    assert sensor.native_value is None
```

#### 18.12.2 Documentation Updates

**File:** `README.md`

Add section documenting activity sensors:

```markdown
### Activity & Statistics Sensors

Track server activity and user watch statistics:

- **Last Activity** - Most recent server activity with recent entries as attributes
- **Connected Devices** - Count of registered devices with device details
- **Watch Time Today** - Total watch time today in minutes (resets at midnight)
- **Active Sessions** - Current active playback sessions

#### Example Automation: Track Daily Watch Time

```yaml
automation:
  - alias: "Log Daily Watch Time"
    trigger:
      - platform: time
        at: "23:59:00"
    action:
      - service: notify.persistent_notification
        data:
          title: "Emby Watch Time"
          message: >
            Today's watch time: {{ states('sensor.emby_watch_time_today') }} minutes
```
```

**Tests:**
- [ ] All new tests passing
- [ ] 100% code coverage maintained
- [ ] No regressions in existing tests
- [ ] README updated with examples

**Acceptance Criteria:**
- Test coverage at 100%
- All tests pass
- README documentation complete
- No type errors (mypy strict)

---

## Files Modified

### New Files
- `tests/test_api_activity.py` - Activity log API tests
- `tests/test_api_devices.py` - Device API tests
- `tests/test_sensor_activity.py` - Activity sensor tests
- `tests/test_coordinator_activity.py` - Activity coordinator tests

### Modified Files
- `custom_components/embymedia/const.py` - Add TypedDicts
- `custom_components/embymedia/api.py` - Add API methods
- `custom_components/embymedia/sensor.py` - Add sensor entities
- `custom_components/embymedia/coordinator.py` - Add playback tracking
- `custom_components/embymedia/coordinator_sensors.py` - Update server coordinator
- `custom_components/embymedia/strings.json` - Add translations
- `custom_components/embymedia/translations/en.json` - Add translations
- `README.md` - Add activity sensors documentation

---

## Architecture

### Coordinator Strategy

```
EmbyRuntimeData
├── session_coordinator (EmbyDataUpdateCoordinator) - 10s/60s polling
│   ├── Session data for media players
│   └── NEW: Playback tracking (_playback_sessions, _daily_watch_time)
│
├── server_coordinator (EmbyServerCoordinator) - 5 min polling
│   ├── Server info, scheduled tasks
│   └── NEW: Activity log, connected devices
│
└── library_coordinator (EmbyLibraryCoordinator) - 1 hour polling
    └── Library counts, virtual folders
```

### Entity Hierarchy

All activity sensors grouped under Emby server device:

```
Device: Emby {Server Name}
├── sensor.{server}_last_activity
├── sensor.{server}_connected_devices
├── sensor.{server}_watch_time_today
├── sensor.{server}_active_sessions
└── ... (existing sensors)
```

### WebSocket Event Flow

```
PlaybackProgress Event
    ↓
_handle_websocket_message()
    ↓
_track_playback_progress()
    ↓
Update _daily_watch_time
Update _playback_sessions
    ↓
EmbyWatchStatisticsSensor.native_value
```

---

## Success Criteria

- [ ] Activity log sensor shows recent server activity
- [ ] Connected devices sensor shows all registered devices
- [ ] Watch time sensor tracks daily playback accurately
- [ ] Watch time resets at midnight
- [ ] All sensors grouped under server device
- [ ] 100% test coverage maintained
- [ ] No `Any` types (strict typing)
- [ ] All translations complete
- [ ] WebSocket playback tracking works reliably
- [ ] No performance impact on existing features

---

## Future Enhancements (Not Implemented)

The following features could be added in future phases:

- **Weekly/Monthly Statistics** - Aggregate watch time over longer periods
- **Per-User Statistics** - Track watch time per user
- **Top Content** - Most-watched movies/shows
- **Activity Filtering** - Filter by activity type or severity
- **Device Analytics** - Track device usage patterns
- **WebSocket Subscription** - Subscribe to `ActivityLogEntry` events for real-time updates
- **Persistent Statistics** - Store watch time in HA recorder for long-term tracking

---

## API Reference

### New Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/System/ActivityLog/Entries` | GET | Get server activity entries |
| `/Devices` | GET | Get registered devices |

### New WebSocket Events Tracked

| Event | Purpose |
|-------|---------|
| `PlaybackProgress` | Track playback time for statistics |

---

## TypedDict Reference

### EmbyActivityLogEntry
```python
class EmbyActivityLogEntry(TypedDict, total=False):
    Id: int
    Name: str
    Type: str
    Date: str
    Severity: str
    UserId: str
    ItemId: str
    ShortOverview: str
    Overview: str
```

### EmbyDeviceInfo
```python
class EmbyDeviceInfo(TypedDict, total=False):
    Id: str
    Name: str
    LastUserId: str
    LastUserName: str
    DateLastActivity: str
    AppName: str
    AppVersion: str
    CustomName: str
    Capabilities: dict[str, object]
```

---

## Development Workflow

This phase follows the TDD approach enforced by `ha-emby-tdd` skill:

1. **RED** - Write failing tests for TypedDicts, API methods, sensors
2. **GREEN** - Implement minimum code to pass tests
3. **REFACTOR** - Optimize while keeping tests green

Use `ha-emby-phase-executor` skill to execute this phase:

```
Execute phase 18
```

The skill will:
- Create branch `phase-18-implementation`
- Execute tasks in TDD cycles
- Run code review after each task
- Create PR when complete

---

## Notes

- Activity log polling every 5 minutes is sufficient (not real-time critical)
- Device list changes infrequently, 5-minute polling is appropriate
- Watch time tracking uses WebSocket for accuracy
- Daily reset uses local server time (not UTC)
- Playback progress sanity checks prevent inflated watch time from seeks
- Statistics are volatile (lost on restart) - future phase could add persistence
