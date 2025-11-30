# Phase 16: Live TV & DVR Integration

## Overview

Comprehensive Live TV support including channel browsing, recording management, timer scheduling, EPG data exposure, and series timer support for DVR functionality.

This phase extends the Emby integration to expose Live TV capabilities through sensors and services, enabling users to monitor recordings, schedule new recordings, manage series timers, and access EPG (Electronic Program Guide) data for automations.

## Implementation Status: COMPLETE ✅

### Completed Tasks
- [x] Task 16.1: TypedDicts for Live TV API (EmbyLiveTvInfo, EmbyRecording, EmbyTimer, EmbySeriesTimer, EmbyTimerDefaults, EmbyProgram)
- [x] Task 16.2: Live TV API Methods (info, recordings, timers, series timers, EPG data)
- [x] Task 16.3: Live TV Binary Sensor (live_tv_enabled with tuner_count and active_recordings attributes)
- [x] Task 16.4: Recording Sensors (recording_count, active_recordings, scheduled_timer_count, series_timer_count)
- [x] Task 16.5: Recording Management Services (schedule_recording, cancel_recording, cancel_series_timer)
- [x] Task 16.6: Translations (strings.json and en.json updated)
- [x] Task 16.7: Testing (100% code coverage maintained)
- [x] Task 16.8: Documentation (README updated)

---

## Background Research

### Emby Live TV Architecture

Emby's Live TV system consists of several components:

1. **Live TV Info** - Server-level Live TV configuration and enabled users
2. **Channels** - Live TV channel listing (already supported in browsing)
3. **Recordings** - Completed recordings library
4. **Timers** - Scheduled one-time recordings
5. **Series Timers** - Recurring recording rules for entire series
6. **EPG Data** - Program guide information for all channels

### Key API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/LiveTv/Info` | GET | Get Live TV configuration and status |
| `/LiveTv/Channels` | GET | List all Live TV channels (existing) |
| `/LiveTv/Recordings` | GET | Get recorded programs |
| `/LiveTv/Timers` | GET | Get scheduled timers |
| `/LiveTv/Timers/Defaults` | GET | Get default timer settings for a program |
| `/LiveTv/Timers` | POST | Create a new timer |
| `/LiveTv/Timers/{Id}` | DELETE | Cancel a timer |
| `/LiveTv/SeriesTimers` | GET | Get series timers |
| `/LiveTv/SeriesTimers` | POST | Create a series timer |
| `/LiveTv/SeriesTimers/{Id}` | DELETE | Cancel a series timer |
| `/LiveTv/Programs` | GET | Get EPG program data |
| `/LiveTv/Programs/Recommended` | GET | Get recommended programs |

### Timer vs Series Timer

- **Timer**: Single recording of one program occurrence
- **Series Timer**: Recurring rule that creates timers automatically for all episodes

---

## Task Breakdown

### Task 16.1: TypedDicts for Live TV API

**Files:** `custom_components/embymedia/const.py`

Add TypedDicts for Live TV API responses.

#### 16.1.1 EmbyLiveTvInfo TypedDict
```python
class EmbyLiveTvInfo(TypedDict, total=False):
    """Response from /LiveTv/Info endpoint.

    Contains Live TV configuration and status information.
    """

    # Required fields
    IsEnabled: bool
    EnabledUsers: list[str]  # User IDs with Live TV access

    # Optional fields
    Services: list[EmbyLiveTvService]
    TunerCount: int  # Number of available tuners
    ActiveRecordingCount: int
    HomePageUrl: str
    Status: str  # "Ok", "LiveTvNotConfigured", etc.
    StatusMessage: str
```

#### 16.1.2 EmbyLiveTvService TypedDict
```python
class EmbyLiveTvService(TypedDict, total=False):
    """Live TV service/tuner information."""

    Name: str
    Id: str
    HomePageUrl: str
    Status: str
    StatusMessage: str
    Version: str
    HasUpdateAvailable: bool
    IsVisible: bool
```

#### 16.1.3 EmbyRecording TypedDict
```python
class EmbyRecording(TypedDict, total=False):
    """Recorded program information from /LiveTv/Recordings.

    Recordings are library items, so they inherit from EmbyBrowseItem
    with additional Live TV-specific fields.
    """

    # Standard item fields
    Id: str
    Name: str
    Type: str  # "Recording"

    # Recording-specific fields
    ChannelId: str
    ChannelName: str
    StartDate: str  # ISO 8601 datetime
    EndDate: str  # ISO 8601 datetime
    Status: str  # "Completed", "Recording", "Error", "Cancelled"
    IsRepeat: bool
    EpisodeTitle: str
    SeriesTimerId: str  # If part of series recording
    TimerId: str  # Original timer that created this recording
    RunTimeTicks: int

    # Program metadata
    Overview: str
    SeriesName: str
    SeasonNumber: int
    EpisodeNumber: int
    ProductionYear: int
    ImageTags: dict[str, str]
```

#### 16.1.4 EmbyTimer TypedDict
```python
class EmbyTimer(TypedDict, total=False):
    """Timer (scheduled recording) from /LiveTv/Timers."""

    # Required fields
    Id: str
    Type: str  # "Timer"
    ChannelId: str
    ChannelName: str
    ProgramId: str
    Name: str
    StartDate: str  # ISO 8601 datetime
    EndDate: str  # ISO 8601 datetime
    Status: str  # "New", "InProgress", "Completed", "Cancelled", "ConflictedNotOk"

    # Optional fields
    SeriesTimerId: str  # If created by series timer
    PrePaddingSeconds: int  # Recording starts early
    PostPaddingSeconds: int  # Recording ends late
    Priority: int  # Higher priority wins conflicts
    IsManual: bool  # User-created vs auto-created
    IsPrePaddingRequired: bool
    IsPostPaddingRequired: bool

    # Program metadata
    Overview: str
    EpisodeTitle: str
    SeriesName: str
    SeasonNumber: int
    EpisodeNumber: int
    RunTimeTicks: int
    ImageTags: dict[str, str]
```

#### 16.1.5 EmbySeriesTimer TypedDict
```python
class EmbySeriesTimer(TypedDict, total=False):
    """Series timer (recording rule) from /LiveTv/SeriesTimers."""

    # Required fields
    Id: str
    Type: str  # "SeriesTimer"
    Name: str
    ChannelId: str
    ChannelName: str
    ProgramId: str

    # Recording rules
    RecordAnyTime: bool  # Record regardless of time slot
    RecordAnyChannel: bool  # Record on any channel
    RecordNewOnly: bool  # Skip repeats
    SkipEpisodesInLibrary: bool  # Don't record episodes already in library

    # Timing
    Days: list[str]  # ["Monday", "Tuesday", ...]
    StartDate: str  # ISO 8601 datetime
    EndDate: str  # ISO 8601 datetime (when rule expires)
    PrePaddingSeconds: int
    PostPaddingSeconds: int
    Priority: int

    # Metadata
    SeriesId: str
    ImageTags: dict[str, str]
```

#### 16.1.6 EmbyTimerDefaults TypedDict
```python
class EmbyTimerDefaults(TypedDict, total=False):
    """Default timer settings from /LiveTv/Timers/Defaults.

    Used to pre-populate timer creation with server defaults.
    """

    ProgramId: str
    ChannelId: str
    StartDate: str
    EndDate: str
    PrePaddingSeconds: int
    PostPaddingSeconds: int
    Priority: int
    IsPrePaddingRequired: bool
    IsPostPaddingRequired: bool
```

#### 16.1.7 EmbyProgram TypedDict
```python
class EmbyProgram(TypedDict, total=False):
    """EPG program information from /LiveTv/Programs."""

    # Required fields
    Id: str
    Type: str  # "Program"
    Name: str
    ChannelId: str
    ChannelName: str
    StartDate: str  # ISO 8601 datetime
    EndDate: str  # ISO 8601 datetime

    # Optional fields
    Overview: str
    EpisodeTitle: str
    SeriesName: str
    SeasonNumber: int
    EpisodeNumber: int
    IsRepeat: bool
    IsMovie: bool
    IsSeries: bool
    IsSports: bool
    IsNews: bool
    IsKids: bool
    IsLive: bool
    IsPremiere: bool
    ImageTags: dict[str, str]
    RunTimeTicks: int
    TimerId: str  # If scheduled to record
    SeriesTimerId: str  # If part of series timer
```

**Tests:**
- [ ] Type annotation validation
- [ ] Optional field handling
- [ ] Nested TypedDict validation

**Pattern Reference:**
See `/workspaces/homeassistant-emby/custom_components/embymedia/const.py` lines 161-327 for existing TypedDict patterns.

---

### Task 16.2: Live TV API Methods

**Files:** `custom_components/embymedia/api.py`

Add API methods for Live TV functionality.

#### 16.2.1 Live TV Info Method
```python
async def async_get_live_tv_info(self) -> EmbyLiveTvInfo:
    """Get Live TV configuration and status.

    Returns:
        Live TV info including enabled status and tuner count.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    endpoint = "/LiveTv/Info"
    response = await self._request(HTTP_GET, endpoint)
    return response  # type: ignore[return-value]
```

**Pattern Reference:**
See `/workspaces/homeassistant-emby/custom_components/embymedia/api.py` lines 369-382 for `async_get_server_info()` pattern.

#### 16.2.2 Recordings Methods
```python
async def async_get_recordings(
    self,
    user_id: str,
    status: str | None = None,
    series_timer_id: str | None = None,
    is_in_progress: bool | None = None,
) -> list[EmbyRecording]:
    """Get recorded programs.

    Args:
        user_id: User ID to filter recordings.
        status: Filter by status ("Completed", "InProgress", etc.).
        series_timer_id: Filter by series timer ID.
        is_in_progress: Filter for currently recording programs.

    Returns:
        List of recording items.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    params: list[str] = [f"UserId={user_id}"]
    if status:
        params.append(f"Status={status}")
    if series_timer_id:
        params.append(f"SeriesTimerId={series_timer_id}")
    if is_in_progress is not None:
        params.append(f"IsInProgress={'true' if is_in_progress else 'false'}")

    query_string = "&".join(params)
    endpoint = f"/LiveTv/Recordings?{query_string}"
    response = await self._request(HTTP_GET, endpoint)
    items: list[EmbyRecording] = response.get("Items", [])  # type: ignore[assignment]
    return items
```

**Pattern Reference:**
See `/workspaces/homeassistant-emby/custom_components/embymedia/api.py` lines 887-950 for `async_get_items()` pattern with query parameters.

#### 16.2.3 Timer Methods
```python
async def async_get_timers(
    self,
    channel_id: str | None = None,
    series_timer_id: str | None = None,
) -> list[EmbyTimer]:
    """Get scheduled recording timers.

    Args:
        channel_id: Filter by channel ID.
        series_timer_id: Filter by series timer ID.

    Returns:
        List of timer objects.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    params: list[str] = []
    if channel_id:
        params.append(f"ChannelId={channel_id}")
    if series_timer_id:
        params.append(f"SeriesTimerId={series_timer_id}")

    query_string = "&".join(params) if params else ""
    endpoint = f"/LiveTv/Timers?{query_string}" if query_string else "/LiveTv/Timers"
    response = await self._request(HTTP_GET, endpoint)
    items: list[EmbyTimer] = response.get("Items", [])  # type: ignore[assignment]
    return items

async def async_get_timer_defaults(
    self,
    program_id: str,
) -> EmbyTimerDefaults:
    """Get default timer settings for a program.

    Args:
        program_id: Program ID to get defaults for.

    Returns:
        Timer defaults with pre-populated settings.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    endpoint = f"/LiveTv/Timers/Defaults?ProgramId={program_id}"
    response = await self._request(HTTP_GET, endpoint)
    return response  # type: ignore[return-value]

async def async_create_timer(
    self,
    timer_data: dict[str, object],
) -> None:
    """Create a new recording timer.

    Args:
        timer_data: Timer configuration (typically from get_timer_defaults).

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    endpoint = "/LiveTv/Timers"
    await self._request_post(endpoint, data=timer_data)

async def async_cancel_timer(
    self,
    timer_id: str,
) -> None:
    """Cancel a recording timer.

    Args:
        timer_id: Timer ID to cancel.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    endpoint = f"/LiveTv/Timers/{timer_id}"
    await self._request_delete(endpoint)
```

**Pattern Reference:**
See `/workspaces/homeassistant-emby/custom_components/embymedia/api.py`:
- Lines 753-787 for POST methods (`async_mark_played`)
- Lines 567-622 for DELETE methods (`_request_delete`)

#### 16.2.4 Series Timer Methods
```python
async def async_get_series_timers(self) -> list[EmbySeriesTimer]:
    """Get series recording timers.

    Returns:
        List of series timer objects.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    endpoint = "/LiveTv/SeriesTimers"
    response = await self._request(HTTP_GET, endpoint)
    items: list[EmbySeriesTimer] = response.get("Items", [])  # type: ignore[assignment]
    return items

async def async_create_series_timer(
    self,
    series_timer_data: dict[str, object],
) -> None:
    """Create a new series recording timer.

    Args:
        series_timer_data: Series timer configuration.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    endpoint = "/LiveTv/SeriesTimers"
    await self._request_post(endpoint, data=series_timer_data)

async def async_cancel_series_timer(
    self,
    series_timer_id: str,
) -> None:
    """Cancel a series recording timer.

    Args:
        series_timer_id: Series timer ID to cancel.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    endpoint = f"/LiveTv/SeriesTimers/{series_timer_id}"
    await self._request_delete(endpoint)
```

#### 16.2.5 EPG Data Methods (Optional)
```python
async def async_get_programs(
    self,
    user_id: str,
    channel_ids: list[str] | None = None,
    min_start_date: str | None = None,
    max_start_date: str | None = None,
    has_aired: bool | None = None,
    is_airing: bool | None = None,
) -> list[EmbyProgram]:
    """Get EPG program data.

    Args:
        user_id: User ID for personalization.
        channel_ids: Filter by channel IDs.
        min_start_date: Minimum start date (ISO 8601).
        max_start_date: Maximum start date (ISO 8601).
        has_aired: Filter for aired programs.
        is_airing: Filter for currently airing programs.

    Returns:
        List of program objects.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    params: list[str] = [f"UserId={user_id}"]
    if channel_ids:
        params.append(f"ChannelIds={','.join(channel_ids)}")
    if min_start_date:
        params.append(f"MinStartDate={min_start_date}")
    if max_start_date:
        params.append(f"MaxStartDate={max_start_date}")
    if has_aired is not None:
        params.append(f"HasAired={'true' if has_aired else 'false'}")
    if is_airing is not None:
        params.append(f"IsAiring={'true' if is_airing else 'false'}")

    query_string = "&".join(params)
    endpoint = f"/LiveTv/Programs?{query_string}"
    response = await self._request(HTTP_GET, endpoint)
    items: list[EmbyProgram] = response.get("Items", [])  # type: ignore[assignment]
    return items

async def async_get_recommended_programs(
    self,
    user_id: str,
    limit: int = 10,
) -> list[EmbyProgram]:
    """Get recommended programs for a user.

    Args:
        user_id: User ID for personalization.
        limit: Maximum number of programs to return.

    Returns:
        List of recommended program objects.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    endpoint = f"/LiveTv/Programs/Recommended?UserId={user_id}&Limit={limit}"
    response = await self._request(HTTP_GET, endpoint)
    items: list[EmbyProgram] = response.get("Items", [])  # type: ignore[assignment]
    return items
```

**Tests:**
- [ ] Test async_get_live_tv_info with mock response
- [ ] Test async_get_recordings with filters
- [ ] Test async_get_timers with filters
- [ ] Test async_get_timer_defaults
- [ ] Test async_create_timer with valid data
- [ ] Test async_cancel_timer
- [ ] Test async_get_series_timers
- [ ] Test async_create_series_timer
- [ ] Test async_cancel_series_timer
- [ ] Test async_get_programs with date filters
- [ ] Test async_get_recommended_programs
- [ ] Test error handling (item not found, auth failure)

**Pattern Reference:**
See `/workspaces/homeassistant-emby/tests/test_api.py` for existing API test patterns.

---

### Task 16.3: Live TV Binary Sensor

**Files:** `custom_components/embymedia/binary_sensor.py`

Add a binary sensor to indicate if Live TV is enabled on the server.

#### 16.3.1 Update EmbyServerCoordinator
First, update the server coordinator to fetch Live TV info.

**File:** `custom_components/embymedia/coordinator_sensors.py`

```python
async def _async_update_data(self) -> dict[str, object]:
    """Fetch server data."""
    try:
        server_info = await self.client.async_get_server_info()
        scheduled_tasks = await self.client.async_get_scheduled_tasks()
        live_tv_info = await self.client.async_get_live_tv_info()  # NEW

        # ... existing processing ...

        return {
            "server_version": server_info.get("Version"),
            "has_pending_restart": server_info.get("HasPendingRestart", False),
            # ... existing fields ...
            "live_tv_enabled": live_tv_info.get("IsEnabled", False),  # NEW
            "live_tv_tuner_count": live_tv_info.get("TunerCount", 0),  # NEW
            "live_tv_recording_count": live_tv_info.get("ActiveRecordingCount", 0),  # NEW
        }
    except EmbyError:
        # ... error handling ...
```

**Pattern Reference:**
See `/workspaces/homeassistant-emby/custom_components/embymedia/coordinator_sensors.py` lines 49-136 for `EmbyServerCoordinator` pattern.

#### 16.3.2 Create Live TV Enabled Binary Sensor
```python
class EmbyLiveTvEnabledBinarySensor(EmbyServerBinarySensorBase):
    """Binary sensor for Live TV enabled status.

    Shows whether Live TV is configured and enabled on the server.
    """

    _attr_device_class = None  # No specific device class
    _attr_translation_key = "live_tv_enabled"
    _attr_icon = "mdi:television-classic"

    def __init__(self, coordinator: EmbyServerCoordinator) -> None:
        """Initialize the sensor.

        Args:
            coordinator: The server data coordinator.
        """
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.server_id}_live_tv_enabled"

    @property
    def is_on(self) -> bool | None:
        """Return True if Live TV is enabled.

        Returns:
            True if Live TV is enabled, None if unknown.
        """
        if self.coordinator.data is None:
            return None
        return bool(self.coordinator.data.get("live_tv_enabled", False))

    @property
    def extra_state_attributes(self) -> dict[str, int] | None:
        """Return extra state attributes.

        Returns:
            Tuner count and active recording count.
        """
        if self.coordinator.data is None:
            return None

        return {
            "tuner_count": self.coordinator.data.get("live_tv_tuner_count", 0),
            "active_recordings": self.coordinator.data.get("live_tv_recording_count", 0),
        }
```

#### 16.3.3 Register Binary Sensor
Update `async_setup_entry` to add the new sensor.

```python
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EmbyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Emby binary sensors from a config entry."""
    runtime_data = config_entry.runtime_data
    server_coordinator: EmbyServerCoordinator = runtime_data.server_coordinator

    entities: list[BinarySensorEntity] = [
        EmbyServerConnectedBinarySensor(server_coordinator),
        EmbyPendingRestartBinarySensor(server_coordinator),
        EmbyUpdateAvailableBinarySensor(server_coordinator),
        EmbyLibraryScanActiveBinarySensor(server_coordinator),
        EmbyLiveTvEnabledBinarySensor(server_coordinator),  # NEW
    ]

    async_add_entities(entities)
```

**Tests:**
- [ ] Test binary sensor state reflects Live TV enabled status
- [ ] Test extra_state_attributes contains tuner and recording counts
- [ ] Test sensor unavailable when coordinator has no data
- [ ] Test sensor updates when Live TV configuration changes

**Pattern Reference:**
See `/workspages/homeassistant-emby/custom_components/embymedia/binary_sensor.py` lines 98-124 for `EmbyServerConnectedBinarySensor` pattern.

---

### Task 16.4: Recording Sensors

**Files:** `custom_components/embymedia/sensor.py`

Add sensors to track recording counts and scheduled recordings.

#### 16.4.1 Create Live TV Coordinator
Create a new coordinator for Live TV data (recordings, timers).

**File:** `custom_components/embymedia/coordinator_sensors.py`

```python
class EmbyLiveTvCoordinator(DataUpdateCoordinator[dict[str, object]]):
    """Coordinator for Live TV data (recordings, timers).

    Polls Live TV endpoints for recording and timer information.
    Updates every 5 minutes by default.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: EmbyClient,
        server_id: str,
        server_name: str,
        user_id: str,
        update_interval: int = 300,  # 5 minutes
    ) -> None:
        """Initialize the Live TV coordinator.

        Args:
            hass: Home Assistant instance.
            client: Emby API client.
            server_id: Server unique ID.
            server_name: Server name for device info.
            user_id: User ID for filtering recordings.
            update_interval: Update interval in seconds.
        """
        super().__init__(
            hass,
            _LOGGER,
            name=f"Emby Live TV ({server_name})",
            update_interval=timedelta(seconds=update_interval),
        )
        self.client = client
        self.server_id = server_id
        self.server_name = server_name
        self.user_id = user_id

    async def _async_update_data(self) -> dict[str, object]:
        """Fetch Live TV data.

        Returns:
            Dictionary with recordings, timers, and series timers.
        """
        try:
            recordings = await self.client.async_get_recordings(user_id=self.user_id)
            timers = await self.client.async_get_timers()
            series_timers = await self.client.async_get_series_timers()

            # Filter upcoming timers (not completed/cancelled)
            upcoming_timers = [
                timer for timer in timers
                if timer.get("Status") in ("New", "InProgress")
            ]

            return {
                "recording_count": len(recordings),
                "recordings": recordings[:10],  # Limit to 10 most recent
                "scheduled_count": len(upcoming_timers),
                "scheduled_timers": upcoming_timers[:10],  # Limit to 10 upcoming
                "series_timer_count": len(series_timers),
                "series_timers": series_timers,
            }
        except EmbyError as err:
            raise UpdateFailed(f"Failed to update Live TV data: {err}") from err
```

**Pattern Reference:**
See `/workspaces/homeassistant-emby/custom_components/embymedia/coordinator_sensors.py` lines 49-136 for coordinator pattern.

#### 16.4.2 Register Coordinator in Runtime Data
**File:** `custom_components/embymedia/const.py`

Update `EmbyRuntimeData` class:
```python
class EmbyRuntimeData:
    """Runtime data for Emby integration."""

    def __init__(
        self,
        session_coordinator: EmbyDataUpdateCoordinator,
        server_coordinator: EmbyServerCoordinator,
        library_coordinator: EmbyLibraryCoordinator,
        live_tv_coordinator: EmbyLiveTvCoordinator,  # NEW
    ) -> None:
        """Initialize runtime data."""
        self.session_coordinator = session_coordinator
        self.server_coordinator = server_coordinator
        self.library_coordinator = library_coordinator
        self.live_tv_coordinator = live_tv_coordinator  # NEW
```

**File:** `custom_components/embymedia/__init__.py`

Create coordinator in `async_setup_entry`:
```python
# Create Live TV coordinator
live_tv_coordinator = EmbyLiveTvCoordinator(
    hass,
    client,
    server_id,
    server_name,
    user_id=entry.data.get(CONF_USER_ID, ""),
    update_interval=DEFAULT_LIBRARY_SCAN_INTERVAL,  # 5 minutes
)

# Store runtime data
entry.runtime_data = EmbyRuntimeData(
    session_coordinator=coordinator,
    server_coordinator=server_coordinator,
    library_coordinator=library_coordinator,
    live_tv_coordinator=live_tv_coordinator,  # NEW
)
```

#### 16.4.3 Create Recording Count Sensor
```python
class EmbyRecordingCountSensor(
    CoordinatorEntity[EmbyLiveTvCoordinator],
    SensorEntity,
):
    """Sensor for recording count.

    Shows the total number of recordings in the library.
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:record-rec"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "recording_count"

    def __init__(
        self,
        coordinator: EmbyLiveTvCoordinator,
        server_name: str,
    ) -> None:
        """Initialize the sensor.

        Args:
            coordinator: The Live TV data coordinator.
            server_name: The server name for device info.
        """
        super().__init__(coordinator)
        self._server_name = server_name
        self._attr_unique_id = f"{coordinator.server_id}_recording_count"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.server_id)},
            name=self._server_name,
            manufacturer="Emby",
            model="Emby Server",
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def native_value(self) -> int | None:
        """Return the recording count."""
        if self.coordinator.data is None:
            return None
        return int(self.coordinator.data.get("recording_count", 0))

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return extra state attributes.

        Returns:
            List of recent recordings with metadata.
        """
        if self.coordinator.data is None:
            return None

        recordings = self.coordinator.data.get("recordings", [])
        if not recordings:
            return None

        # Format recordings for attributes
        recording_list = []
        for recording in recordings:
            recording_list.append({
                "name": recording.get("Name", "Unknown"),
                "channel": recording.get("ChannelName", "Unknown"),
                "start_date": recording.get("StartDate"),
                "status": recording.get("Status", "Unknown"),
                "series_name": recording.get("SeriesName"),
                "episode_title": recording.get("EpisodeTitle"),
            })

        return {"recordings": recording_list}
```

#### 16.4.4 Create Scheduled Recordings Sensor
```python
class EmbyScheduledRecordingsSensor(
    CoordinatorEntity[EmbyLiveTvCoordinator],
    SensorEntity,
):
    """Sensor for scheduled recordings count.

    Shows the number of upcoming scheduled recordings.
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-clock"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "scheduled_recordings"

    def __init__(
        self,
        coordinator: EmbyLiveTvCoordinator,
        server_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._server_name = server_name
        self._attr_unique_id = f"{coordinator.server_id}_scheduled_recordings"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.server_id)},
            name=self._server_name,
            manufacturer="Emby",
            model="Emby Server",
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def native_value(self) -> int | None:
        """Return the scheduled recordings count."""
        if self.coordinator.data is None:
            return None
        return int(self.coordinator.data.get("scheduled_count", 0))

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return extra state attributes.

        Returns:
            List of upcoming timers with metadata.
        """
        if self.coordinator.data is None:
            return None

        timers = self.coordinator.data.get("scheduled_timers", [])
        if not timers:
            return None

        # Format timers for attributes
        timer_list = []
        for timer in timers:
            timer_list.append({
                "name": timer.get("Name", "Unknown"),
                "channel": timer.get("ChannelName", "Unknown"),
                "start_date": timer.get("StartDate"),
                "status": timer.get("Status", "Unknown"),
                "series_name": timer.get("SeriesName"),
                "episode_title": timer.get("EpisodeTitle"),
            })

        return {"scheduled_timers": timer_list}
```

#### 16.4.5 Create Series Timers Sensor
```python
class EmbySeriesTimersSensor(
    CoordinatorEntity[EmbyLiveTvCoordinator],
    SensorEntity,
):
    """Sensor for series timers count.

    Shows the number of active series recording rules.
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:television-guide"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "series_timers"

    def __init__(
        self,
        coordinator: EmbyLiveTvCoordinator,
        server_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._server_name = server_name
        self._attr_unique_id = f"{coordinator.server_id}_series_timers"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.server_id)},
            name=self._server_name,
            manufacturer="Emby",
            model="Emby Server",
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def native_value(self) -> int | None:
        """Return the series timers count."""
        if self.coordinator.data is None:
            return None
        return int(self.coordinator.data.get("series_timer_count", 0))

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return extra state attributes.

        Returns:
            List of series timers with metadata.
        """
        if self.coordinator.data is None:
            return None

        series_timers = self.coordinator.data.get("series_timers", [])
        if not series_timers:
            return None

        # Format series timers for attributes
        timer_list = []
        for timer in series_timers:
            timer_list.append({
                "name": timer.get("Name", "Unknown"),
                "channel": timer.get("ChannelName", "Unknown"),
                "record_new_only": timer.get("RecordNewOnly", False),
                "skip_in_library": timer.get("SkipEpisodesInLibrary", False),
                "days": timer.get("Days", []),
            })

        return {"series_timers": timer_list}
```

#### 16.4.6 Register Sensors
Update `async_setup_entry` to add the new sensors.

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
    live_tv_coordinator: EmbyLiveTvCoordinator = runtime_data.live_tv_coordinator  # NEW
    server_name = server_coordinator.server_name

    entities: list[SensorEntity] = [
        # ... existing sensors ...

        # Live TV sensors (NEW)
        EmbyRecordingCountSensor(live_tv_coordinator, server_name),
        EmbyScheduledRecordingsSensor(live_tv_coordinator, server_name),
        EmbySeriesTimersSensor(live_tv_coordinator, server_name),
    ]

    async_add_entities(entities)
```

**Tests:**
- [ ] Test recording count sensor state
- [ ] Test recording count sensor attributes with recording list
- [ ] Test scheduled recordings sensor state
- [ ] Test scheduled recordings sensor attributes with timer list
- [ ] Test series timers sensor state
- [ ] Test series timers sensor attributes with timer list
- [ ] Test coordinator updates with Live TV data
- [ ] Test sensor unavailable when coordinator has no data

**Pattern Reference:**
See `/workspaces/homeassistant-emby/custom_components/embymedia/sensor.py` lines 255-274 for `EmbyMovieCountSensor` pattern.

---

### Task 16.5: Recording Management Services

**Files:** `custom_components/embymedia/services.py`

Add services for scheduling and canceling recordings.

#### 16.5.1 Service Constants
Add to file header:
```python
# Service names (existing + new)
SERVICE_SCHEDULE_RECORDING = "schedule_recording"
SERVICE_CANCEL_RECORDING = "cancel_recording"
SERVICE_SCHEDULE_SERIES = "schedule_series"

# Service attributes (existing + new)
ATTR_PROGRAM_ID = "program_id"
ATTR_TIMER_ID = "timer_id"
ATTR_SERIES_TIMER_ID = "series_timer_id"
ATTR_PRE_PADDING_SECONDS = "pre_padding_seconds"
ATTR_POST_PADDING_SECONDS = "post_padding_seconds"
ATTR_RECORD_NEW_ONLY = "record_new_only"
ATTR_SKIP_IN_LIBRARY = "skip_in_library"
```

#### 16.5.2 Service Schemas
```python
SCHEDULE_RECORDING_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(ATTR_PROGRAM_ID): cv.string,
        vol.Optional(ATTR_PRE_PADDING_SECONDS): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=3600)
        ),
        vol.Optional(ATTR_POST_PADDING_SECONDS): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=3600)
        ),
    }
)

CANCEL_RECORDING_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(ATTR_TIMER_ID): cv.string,
    }
)

SCHEDULE_SERIES_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(ATTR_PROGRAM_ID): cv.string,
        vol.Optional(ATTR_RECORD_NEW_ONLY, default=True): cv.boolean,
        vol.Optional(ATTR_SKIP_IN_LIBRARY, default=True): cv.boolean,
        vol.Optional(ATTR_PRE_PADDING_SECONDS): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=3600)
        ),
        vol.Optional(ATTR_POST_PADDING_SECONDS): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=3600)
        ),
    }
)
```

#### 16.5.3 Schedule Recording Service
```python
async def async_schedule_recording(call: ServiceCall) -> None:
    """Schedule a one-time recording."""
    entity_ids = _get_entity_ids_from_call(hass, call)
    program_id: str = call.data[ATTR_PROGRAM_ID]
    pre_padding: int | None = call.data.get(ATTR_PRE_PADDING_SECONDS)
    post_padding: int | None = call.data.get(ATTR_POST_PADDING_SECONDS)

    # Validate program ID
    _validate_emby_id(program_id, "program_id")

    for entity_id in entity_ids:
        coordinator = _get_coordinator_for_entity(hass, entity_id)

        try:
            # Get default timer settings from server
            timer_defaults = await coordinator.client.async_get_timer_defaults(
                program_id=program_id
            )

            # Override with user-provided values
            if pre_padding is not None:
                timer_defaults["PrePaddingSeconds"] = pre_padding
            if post_padding is not None:
                timer_defaults["PostPaddingSeconds"] = post_padding

            # Create the timer
            await coordinator.client.async_create_timer(timer_data=timer_defaults)

        except EmbyConnectionError as err:
            raise HomeAssistantError(
                f"Failed to schedule recording for {entity_id}: Connection error"
            ) from err
        except EmbyError as err:
            raise HomeAssistantError(
                f"Failed to schedule recording for {entity_id}: {err}"
            ) from err
```

#### 16.5.4 Cancel Recording Service
```python
async def async_cancel_recording(call: ServiceCall) -> None:
    """Cancel a scheduled recording."""
    entity_ids = _get_entity_ids_from_call(hass, call)
    timer_id: str = call.data[ATTR_TIMER_ID]

    # Validate timer ID
    _validate_emby_id(timer_id, "timer_id")

    for entity_id in entity_ids:
        coordinator = _get_coordinator_for_entity(hass, entity_id)

        try:
            await coordinator.client.async_cancel_timer(timer_id=timer_id)
        except EmbyConnectionError as err:
            raise HomeAssistantError(
                f"Failed to cancel recording for {entity_id}: Connection error"
            ) from err
        except EmbyError as err:
            raise HomeAssistantError(
                f"Failed to cancel recording for {entity_id}: {err}"
            ) from err
```

#### 16.5.5 Schedule Series Service
```python
async def async_schedule_series(call: ServiceCall) -> None:
    """Schedule a series recording."""
    entity_ids = _get_entity_ids_from_call(hass, call)
    program_id: str = call.data[ATTR_PROGRAM_ID]
    record_new_only: bool = call.data.get(ATTR_RECORD_NEW_ONLY, True)
    skip_in_library: bool = call.data.get(ATTR_SKIP_IN_LIBRARY, True)
    pre_padding: int | None = call.data.get(ATTR_PRE_PADDING_SECONDS)
    post_padding: int | None = call.data.get(ATTR_POST_PADDING_SECONDS)

    # Validate program ID
    _validate_emby_id(program_id, "program_id")

    for entity_id in entity_ids:
        coordinator = _get_coordinator_for_entity(hass, entity_id)

        try:
            # Get default timer settings as base
            timer_defaults = await coordinator.client.async_get_timer_defaults(
                program_id=program_id
            )

            # Build series timer data from defaults
            series_timer_data: dict[str, object] = {
                "ProgramId": program_id,
                "ChannelId": timer_defaults.get("ChannelId"),
                "RecordNewOnly": record_new_only,
                "SkipEpisodesInLibrary": skip_in_library,
                "PrePaddingSeconds": pre_padding or timer_defaults.get("PrePaddingSeconds", 0),
                "PostPaddingSeconds": post_padding or timer_defaults.get("PostPaddingSeconds", 0),
                "Priority": timer_defaults.get("Priority", 0),
            }

            # Create the series timer
            await coordinator.client.async_create_series_timer(
                series_timer_data=series_timer_data
            )

        except EmbyConnectionError as err:
            raise HomeAssistantError(
                f"Failed to schedule series for {entity_id}: Connection error"
            ) from err
        except EmbyError as err:
            raise HomeAssistantError(
                f"Failed to schedule series for {entity_id}: {err}"
            ) from err
```

#### 16.5.6 Register Services
Update `async_setup_services`:
```python
async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up Emby services."""
    if hass.services.has_service(DOMAIN, SERVICE_SEND_MESSAGE):
        # Services already registered
        return

    # ... existing service registrations ...

    # Live TV services (NEW)
    hass.services.async_register(
        DOMAIN,
        SERVICE_SCHEDULE_RECORDING,
        async_schedule_recording,
        schema=SCHEDULE_RECORDING_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CANCEL_RECORDING,
        async_cancel_recording,
        schema=CANCEL_RECORDING_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SCHEDULE_SERIES,
        async_schedule_series,
        schema=SCHEDULE_SERIES_SCHEMA,
    )

    _LOGGER.debug("Emby services registered")
```

Update `async_unload_services`:
```python
async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload Emby services."""
    if not hass.services.has_service(DOMAIN, SERVICE_SEND_MESSAGE):
        return

    # ... existing service removals ...

    # Live TV services (NEW)
    hass.services.async_remove(DOMAIN, SERVICE_SCHEDULE_RECORDING)
    hass.services.async_remove(DOMAIN, SERVICE_CANCEL_RECORDING)
    hass.services.async_remove(DOMAIN, SERVICE_SCHEDULE_SERIES)

    _LOGGER.debug("Emby services unregistered")
```

**Tests:**
- [ ] Test schedule_recording service with valid program ID
- [ ] Test schedule_recording with padding parameters
- [ ] Test schedule_recording with invalid program ID
- [ ] Test cancel_recording service with valid timer ID
- [ ] Test cancel_recording with invalid timer ID
- [ ] Test schedule_series service with valid program ID
- [ ] Test schedule_series with record_new_only option
- [ ] Test schedule_series with skip_in_library option
- [ ] Test service error handling (connection error, auth failure)
- [ ] Test service with entity_id targeting
- [ ] Test service with device_id targeting

**Pattern Reference:**
See `/workspaces/homeassistant-emby/custom_components/embymedia/services.py` lines 225-257 for `async_mark_played` service pattern.

---

### Task 16.6: Translations

**Files:**
- `custom_components/embymedia/strings.json`
- `custom_components/embymedia/translations/en.json`

#### 16.6.1 Binary Sensor Translations
```json
{
  "entity": {
    "binary_sensor": {
      "live_tv_enabled": {
        "name": "Live TV enabled"
      }
    }
  }
}
```

#### 16.6.2 Sensor Translations
```json
{
  "entity": {
    "sensor": {
      "recording_count": {
        "name": "Recordings"
      },
      "scheduled_recordings": {
        "name": "Scheduled recordings"
      },
      "series_timers": {
        "name": "Series timers"
      }
    }
  }
}
```

#### 16.6.3 Service Translations
```json
{
  "services": {
    "schedule_recording": {
      "name": "Schedule recording",
      "description": "Schedule a one-time recording of a program.",
      "fields": {
        "program_id": {
          "name": "Program ID",
          "description": "The ID of the program to record."
        },
        "pre_padding_seconds": {
          "name": "Pre-padding (seconds)",
          "description": "Start recording this many seconds early."
        },
        "post_padding_seconds": {
          "name": "Post-padding (seconds)",
          "description": "End recording this many seconds late."
        }
      }
    },
    "cancel_recording": {
      "name": "Cancel recording",
      "description": "Cancel a scheduled recording.",
      "fields": {
        "timer_id": {
          "name": "Timer ID",
          "description": "The ID of the timer to cancel."
        }
      }
    },
    "schedule_series": {
      "name": "Schedule series",
      "description": "Schedule a series recording for all episodes.",
      "fields": {
        "program_id": {
          "name": "Program ID",
          "description": "The ID of the program to create a series timer for."
        },
        "record_new_only": {
          "name": "Record new only",
          "description": "Skip episodes marked as repeats."
        },
        "skip_in_library": {
          "name": "Skip in library",
          "description": "Don't record episodes already in the library."
        },
        "pre_padding_seconds": {
          "name": "Pre-padding (seconds)",
          "description": "Start recording this many seconds early."
        },
        "post_padding_seconds": {
          "name": "Post-padding (seconds)",
          "description": "End recording this many seconds late."
        }
      }
    }
  }
}
```

**Tests:**
- [ ] Verify translation keys match entity translation_key attributes
- [ ] Verify service translations include all fields
- [ ] Test translations load correctly

**Pattern Reference:**
See `/workspaces/homeassistant-emby/custom_components/embymedia/strings.json` for existing translation patterns.

---

### Task 16.7: Testing

**Files:**
- `tests/test_api_livetv.py` (new file)
- `tests/test_binary_sensor_livetv.py` (new file)
- `tests/test_sensor_livetv.py` (new file)
- `tests/test_services_livetv.py` (new file)
- `tests/test_coordinator_livetv.py` (new file)

#### Test Categories

1. **API Tests** (`test_api_livetv.py`)
   - [ ] Test async_get_live_tv_info with mock response
   - [ ] Test async_get_recordings with filters
   - [ ] Test async_get_timers with filters
   - [ ] Test async_get_timer_defaults
   - [ ] Test async_create_timer
   - [ ] Test async_cancel_timer
   - [ ] Test async_get_series_timers
   - [ ] Test async_create_series_timer
   - [ ] Test async_cancel_series_timer
   - [ ] Test async_get_programs
   - [ ] Test async_get_recommended_programs
   - [ ] Test error handling

2. **Binary Sensor Tests** (`test_binary_sensor_livetv.py`)
   - [ ] Test Live TV enabled binary sensor state
   - [ ] Test extra_state_attributes with tuner/recording counts
   - [ ] Test sensor unavailable when coordinator has no data
   - [ ] Test sensor updates on Live TV config change

3. **Sensor Tests** (`test_sensor_livetv.py`)
   - [ ] Test recording count sensor
   - [ ] Test recording count attributes with recording list
   - [ ] Test scheduled recordings sensor
   - [ ] Test scheduled recordings attributes with timer list
   - [ ] Test series timers sensor
   - [ ] Test series timers attributes with timer list

4. **Coordinator Tests** (`test_coordinator_livetv.py`)
   - [ ] Test EmbyLiveTvCoordinator initialization
   - [ ] Test coordinator data update with Live TV data
   - [ ] Test coordinator error handling
   - [ ] Test filtering of upcoming timers

5. **Service Tests** (`test_services_livetv.py`)
   - [ ] Test schedule_recording service
   - [ ] Test schedule_recording with padding
   - [ ] Test cancel_recording service
   - [ ] Test schedule_series service
   - [ ] Test schedule_series with options
   - [ ] Test service error handling
   - [ ] Test service validation

**Coverage:** Maintain 100% code coverage

**Pattern Reference:**
See `/workspaces/homeassistant-emby/tests/test_api.py`, `/workspaces/homeassistant-emby/tests/test_binary_sensor.py`, `/workspaces/homeassistant-emby/tests/test_sensor.py`, and `/workspaces/homeassistant-emby/tests/test_services.py` for existing test patterns.

---

### Task 16.8: Documentation

**Files:** `README.md`

#### 16.8.1 Update README - Live TV Section

Add a new section after the Sensor Platform section:

```markdown
### Live TV & DVR

The integration provides comprehensive Live TV support for Emby servers with Live TV configured.

#### Binary Sensors

- `binary_sensor.{server}_live_tv_enabled` - Live TV enabled status
  - Attributes: `tuner_count`, `active_recordings`

#### Sensors

- `sensor.{server}_recordings` - Total recordings count
  - Attributes: List of recent recordings
- `sensor.{server}_scheduled_recordings` - Upcoming recordings count
  - Attributes: List of scheduled timers
- `sensor.{server}_series_timers` - Active series timer count
  - Attributes: List of series recording rules

#### Services

##### `embymedia.schedule_recording`

Schedule a one-time recording of a program.

```yaml
service: embymedia.schedule_recording
target:
  entity_id: media_player.emby_living_room_tv
data:
  program_id: "abc123"
  pre_padding_seconds: 60  # Start 1 minute early
  post_padding_seconds: 120  # End 2 minutes late
```

##### `embymedia.cancel_recording`

Cancel a scheduled recording.

```yaml
service: embymedia.cancel_recording
target:
  entity_id: media_player.emby_living_room_tv
data:
  timer_id: "timer-123"
```

##### `embymedia.schedule_series`

Schedule a series recording for all episodes.

```yaml
service: embymedia.schedule_series
target:
  entity_id: media_player.emby_living_room_tv
data:
  program_id: "series-abc123"
  record_new_only: true  # Skip repeats
  skip_in_library: true  # Don't re-record existing episodes
  pre_padding_seconds: 60
  post_padding_seconds: 120
```

#### Example Automation: Auto-Record Favorites

```yaml
automation:
  - alias: "Record recommended programs"
    trigger:
      - platform: time
        at: "06:00:00"
    action:
      - service: embymedia.schedule_recording
        target:
          entity_id: media_player.emby_living_room_tv
        data:
          program_id: "{{ state_attr('sensor.emby_server_recommended_programs', 'programs')[0].id }}"
```
```

**Tests:**
- [ ] Verify README is accurate and complete
- [ ] Verify example automations are syntactically correct
- [ ] Verify all service parameters documented

---

## Files Summary

### New Files
| File | Purpose |
|------|---------|
| `tests/test_api_livetv.py` | Live TV API method tests |
| `tests/test_binary_sensor_livetv.py` | Live TV binary sensor tests |
| `tests/test_sensor_livetv.py` | Live TV sensor tests |
| `tests/test_services_livetv.py` | Live TV service tests |
| `tests/test_coordinator_livetv.py` | Live TV coordinator tests |

### Modified Files
| File | Changes |
|------|---------|
| `const.py` | TypedDicts for Live TV API responses |
| `api.py` | Live TV API methods (info, recordings, timers, series timers, EPG) |
| `coordinator_sensors.py` | EmbyLiveTvCoordinator, update server coordinator for Live TV info |
| `binary_sensor.py` | Live TV enabled binary sensor |
| `sensor.py` | Recording, scheduled recordings, and series timers sensors |
| `services.py` | Schedule/cancel recording and series timer services |
| `__init__.py` | Register Live TV coordinator |
| `strings.json` | Translations for entities and services |
| `translations/en.json` | English translations |
| `README.md` | Live TV documentation |

---

## Success Criteria

- [ ] Live TV info API working
- [ ] Recording and timer APIs working
- [ ] Series timer APIs working
- [ ] EPG data APIs working (optional)
- [ ] Live TV enabled binary sensor showing status
- [ ] Recording count sensor with list attributes
- [ ] Scheduled recordings sensor with list attributes
- [ ] Series timers sensor with list attributes
- [ ] Schedule recording service working
- [ ] Cancel recording service working
- [ ] Schedule series service working
- [ ] Services validate inputs correctly
- [ ] 100% test coverage maintained
- [ ] Documentation complete with examples

---

## API Reference

### GET /LiveTv/Info

**Response:**
```json
{
  "IsEnabled": true,
  "EnabledUsers": ["user-uuid"],
  "Services": [
    {
      "Name": "HD HomeRun",
      "Id": "service-id",
      "Status": "Ok",
      "Version": "1.0.0"
    }
  ],
  "TunerCount": 2,
  "ActiveRecordingCount": 1
}
```

### GET /LiveTv/Recordings

**Query Parameters:**
- `UserId` (required): User ID
- `Status` (optional): Filter by status
- `SeriesTimerId` (optional): Filter by series timer
- `IsInProgress` (optional): Filter for currently recording

**Response:**
```json
{
  "Items": [
    {
      "Id": "recording-id",
      "Name": "Program Name",
      "Type": "Recording",
      "ChannelId": "channel-id",
      "ChannelName": "NBC",
      "StartDate": "2025-11-27T20:00:00Z",
      "EndDate": "2025-11-27T21:00:00Z",
      "Status": "Completed",
      "SeriesName": "Show Name",
      "EpisodeTitle": "Episode Title"
    }
  ],
  "TotalRecordCount": 42
}
```

### GET /LiveTv/Timers

**Query Parameters:**
- `ChannelId` (optional): Filter by channel
- `SeriesTimerId` (optional): Filter by series timer

**Response:**
```json
{
  "Items": [
    {
      "Id": "timer-id",
      "Type": "Timer",
      "ProgramId": "program-id",
      "ChannelId": "channel-id",
      "ChannelName": "NBC",
      "Name": "Program Name",
      "StartDate": "2025-11-28T20:00:00Z",
      "EndDate": "2025-11-28T21:00:00Z",
      "Status": "New",
      "PrePaddingSeconds": 60,
      "PostPaddingSeconds": 120
    }
  ]
}
```

### GET /LiveTv/Timers/Defaults

**Query Parameters:**
- `ProgramId` (required): Program ID

**Response:**
```json
{
  "ProgramId": "program-id",
  "ChannelId": "channel-id",
  "StartDate": "2025-11-28T20:00:00Z",
  "EndDate": "2025-11-28T21:00:00Z",
  "PrePaddingSeconds": 60,
  "PostPaddingSeconds": 120,
  "Priority": 0
}
```

### POST /LiveTv/Timers

**Request Body:**
```json
{
  "ProgramId": "program-id",
  "ChannelId": "channel-id",
  "StartDate": "2025-11-28T20:00:00Z",
  "EndDate": "2025-11-28T21:00:00Z",
  "PrePaddingSeconds": 60,
  "PostPaddingSeconds": 120
}
```

### POST /LiveTv/SeriesTimers

**Request Body:**
```json
{
  "ProgramId": "program-id",
  "ChannelId": "channel-id",
  "RecordNewOnly": true,
  "SkipEpisodesInLibrary": true,
  "PrePaddingSeconds": 60,
  "PostPaddingSeconds": 120,
  "Priority": 0
}
```

### GET /LiveTv/Programs

**Query Parameters:**
- `UserId` (required): User ID
- `ChannelIds` (optional): Comma-separated channel IDs
- `MinStartDate` (optional): ISO 8601 datetime
- `MaxStartDate` (optional): ISO 8601 datetime
- `HasAired` (optional): true/false
- `IsAiring` (optional): true/false

**Response:**
```json
{
  "Items": [
    {
      "Id": "program-id",
      "Type": "Program",
      "Name": "Program Name",
      "ChannelId": "channel-id",
      "ChannelName": "NBC",
      "StartDate": "2025-11-28T20:00:00Z",
      "EndDate": "2025-11-28T21:00:00Z",
      "IsLive": false,
      "IsRepeat": false,
      "SeriesName": "Show Name",
      "EpisodeTitle": "Episode Title"
    }
  ],
  "TotalRecordCount": 100
}
```

---

## References

- [Emby Live TV API](https://dev.emby.media/doc/restapi/Live-Tv.html)
- [Emby Recording API](https://dev.emby.media/doc/restapi/Recordings.html)
- [Emby Timer API](https://dev.emby.media/reference/RestAPI/LiveTvService/)
- [Home Assistant Sensor Platform](https://developers.home-assistant.io/docs/core/entity/sensor/)
- [Home Assistant Binary Sensor Platform](https://developers.home-assistant.io/docs/core/entity/binary-sensor/)
- [Home Assistant Services](https://developers.home-assistant.io/docs/dev_101_services/)

---

## Notes

- The `async_get_live_tv_channels()` method already exists in `api.py` (line 1386), so we only need to add the DVR-specific methods
- Live TV coordinator should poll every 5 minutes to avoid excessive API calls
- Series timers are powerful but complex - provide sensible defaults (record_new_only=True, skip_in_library=True)
- EPG data methods (async_get_programs) are optional and can be implemented in a future phase if needed
- Timer IDs and Series Timer IDs must be validated for security (no path traversal)
- Consider adding a configuration option to disable Live TV features if not used
