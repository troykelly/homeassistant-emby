# Phase 7: Real-Time Updates (WebSocket)

## Overview

This phase implements WebSocket-based real-time updates for the Emby integration, providing near-instant state updates and reducing server polling load.

**Features:**
- WebSocket connection to Emby server
- Real-time session state updates
- Automatic reconnection with exponential backoff
- Hybrid mode: WebSocket for events, polling fallback
- Connection state monitoring

## Dependencies

- Phase 1-6 complete
- aiohttp WebSocket support (already available)
- Emby WebSocket API endpoint

## Emby WebSocket API (Official Documentation)

### Connection URL

Convert HTTP URL to WebSocket:
- `http:` → `ws:`
- `https:` → `wss:`

**Format:**
```
wss://{host}/embywebsocket?api_key={token}&deviceId={deviceId}
```

**Parameters:**
| Parameter | Description |
|-----------|-------------|
| `api_key` | Authentication token (same as REST API) |
| `deviceId` | Unique device identifier for this client |

### Message Format

All messages use JSON with two properties:
```json
{
    "MessageType": "EventName",
    "Data": {}
}
```

### Subscription Messages (Client → Server)

#### SessionsStart
Subscribe to session updates:
```json
{
    "MessageType": "SessionsStart",
    "Data": "0,1500"
}
```

**Data format:** `"{initialPosition},{intervalMs}"`
- `initialPosition`: Always `0`
- `intervalMs`: Update interval in milliseconds (e.g., `1500` = 1.5 seconds)

#### SessionsStop
Unsubscribe from session updates:
```json
{
    "MessageType": "SessionsStop",
    "Data": ""
}
```

### Server → Client Message Types

#### Sessions
Periodic session state update (in response to SessionsStart):
```json
{
    "MessageType": "Sessions",
    "Data": [
        {
            "Id": "session-id",
            "DeviceId": "device-id",
            "DeviceName": "Device Name",
            "Client": "Client Name",
            "PlayState": {
                "CanSeek": true,
                "IsPaused": false,
                "IsMuted": false,
                "PositionTicks": 123456789,
                "VolumeLevel": 100,
                "RepeatMode": "RepeatNone"
            },
            "NowPlayingItem": {
                "Id": "item-id",
                "Name": "Item Name",
                "Type": "Movie",
                "RunTimeTicks": 72000000000
            },
            "SupportsRemoteControl": true,
            "SupportedCommands": ["PlayState", "Seek", ...]
        }
    ]
}
```

#### PlaybackStarted
Triggered when playback begins:
```json
{
    "MessageType": "PlaybackStarted",
    "Data": {
        "SessionId": "session-id",
        "ItemId": "item-id",
        ...
    }
}
```

#### PlaybackStopped
Triggered when playback ends:
```json
{
    "MessageType": "PlaybackStopped",
    "Data": {
        "SessionId": "session-id",
        ...
    }
}
```

#### SessionEnded
Triggered when a session disconnects:
```json
{
    "MessageType": "SessionEnded",
    "Data": {
        "SessionId": "session-id"
    }
}
```

#### UserDataChanged
User rating or playstate changes:
```json
{
    "MessageType": "UserDataChanged",
    "Data": {
        "UserId": "user-id",
        "UserDataList": [...]
    }
}
```

#### System Events
- `ServerRestarting` - Server is restarting
- `ServerShuttingDown` - Server is shutting down
- `RestartRequired` - Server needs restart

### Remote Control Commands (Server → Client)

These are commands sent TO clients (not from them):
- `Play` - Play items
- `Playstate` - Playback control (Pause, Stop, etc.)
- `GeneralCommand` - Navigation and UI commands

---

## Tasks

### Task 7.1: WebSocket Client Implementation

Create a new `EmbyWebSocket` class for WebSocket communication.

#### 7.1.1 Create websocket.py module

**File:** `custom_components/embymedia/websocket.py`

**Class structure:**
```python
class EmbyWebSocket:
    """WebSocket client for Emby server.

    Handles WebSocket connection, automatic reconnection,
    and message dispatching to the coordinator.

    Attributes:
        host: Emby server host.
        port: Emby server port.
        api_key: Authentication API key.
        ssl: Whether to use SSL.
        device_id: Unique device ID for this connection.
    """

    def __init__(
        self,
        host: str,
        port: int,
        api_key: str,
        ssl: bool,
        device_id: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize WebSocket client."""

    async def async_connect(self) -> None:
        """Establish WebSocket connection."""

    async def async_disconnect(self) -> None:
        """Close WebSocket connection."""

    async def async_subscribe_sessions(
        self,
        interval_ms: int = 1500,
    ) -> None:
        """Subscribe to session updates."""

    async def async_unsubscribe_sessions(self) -> None:
        """Unsubscribe from session updates."""

    def set_message_callback(
        self,
        callback: Callable[[str, Any], None],
    ) -> None:
        """Set callback for received messages."""

    @property
    def connected(self) -> bool:
        """Return True if WebSocket is connected."""
```

**Acceptance Criteria:**
- [ ] WebSocket connects to Emby server
- [ ] Authentication via api_key query parameter
- [ ] Handles SSL/TLS connections
- [ ] Exposes connection state

**Test Cases:**
- [ ] `test_websocket_connect_success`
- [ ] `test_websocket_connect_auth_failure`
- [ ] `test_websocket_ssl_connection`
- [ ] `test_websocket_connection_url_format`

#### 7.1.2 Add TypedDicts for WebSocket messages

**File:** `custom_components/embymedia/const.py`

```python
class EmbyWebSocketMessage(TypedDict):
    """WebSocket message structure."""
    MessageType: str
    Data: NotRequired[Any]

class EmbySessionsStartData(TypedDict):
    """Data for SessionsStart message (string format)."""
    # Represented as string "0,1500"
    pass  # Actually just a str

class EmbyPlaybackEventData(TypedDict):
    """Data from playback events."""
    SessionId: str
    ItemId: NotRequired[str]
    MediaSourceId: NotRequired[str]
    PositionTicks: NotRequired[int]
    IsPaused: NotRequired[bool]
```

**Acceptance Criteria:**
- [ ] All WebSocket message types defined
- [ ] No mypy errors

**Test Cases:**
- [ ] `test_websocket_message_types`

#### 7.1.3 Implement message sending

**Methods:**
```python
async def _async_send_message(
    self,
    message_type: str,
    data: str = "",
) -> None:
    """Send a message to the WebSocket.

    Args:
        message_type: The MessageType value.
        data: The Data value (string).
    """
```

**Acceptance Criteria:**
- [ ] Messages sent in correct JSON format
- [ ] Handles connection not ready state

**Test Cases:**
- [ ] `test_send_message_format`
- [ ] `test_send_message_not_connected`

#### 7.1.4 Implement message receiving

**Methods:**
```python
async def _async_receive_loop(self) -> None:
    """Receive and process WebSocket messages."""
```

**Acceptance Criteria:**
- [ ] Parses JSON messages correctly
- [ ] Handles text and close message types
- [ ] Dispatches to callback function
- [ ] Handles malformed messages gracefully

**Test Cases:**
- [ ] `test_receive_sessions_message`
- [ ] `test_receive_playback_started`
- [ ] `test_receive_malformed_json`
- [ ] `test_receive_connection_closed`

---

### Task 7.2: Automatic Reconnection

Implement reconnection with exponential backoff.

#### 7.2.1 Add reconnection logic

**File:** `custom_components/embymedia/websocket.py`

**Implementation:**
```python
class EmbyWebSocket:
    # ... existing code ...

    _reconnect_interval: float = 5.0  # Initial interval
    _max_reconnect_interval: float = 300.0  # Max 5 minutes
    _reconnect_task: asyncio.Task | None = None

    async def _async_reconnect_loop(self) -> None:
        """Reconnection loop with exponential backoff."""
        interval = self._reconnect_interval
        while True:
            try:
                await self.async_connect()
                await self.async_subscribe_sessions()
                interval = self._reconnect_interval  # Reset on success
                break
            except Exception:
                _LOGGER.warning(
                    "WebSocket reconnection failed, retrying in %s seconds",
                    interval,
                )
                await asyncio.sleep(interval)
                interval = min(interval * 2, self._max_reconnect_interval)
```

**Acceptance Criteria:**
- [ ] Automatically reconnects on connection loss
- [ ] Uses exponential backoff
- [ ] Resets interval on successful connection
- [ ] Can be cancelled cleanly

**Test Cases:**
- [ ] `test_reconnect_on_disconnect`
- [ ] `test_reconnect_exponential_backoff`
- [ ] `test_reconnect_max_interval`
- [ ] `test_reconnect_cancel`

#### 7.2.2 Add connection state monitoring

**Methods:**
```python
@property
def connected(self) -> bool:
    """Return True if connected."""

@property
def reconnecting(self) -> bool:
    """Return True if attempting to reconnect."""

def set_connection_callback(
    self,
    callback: Callable[[bool], None],
) -> None:
    """Set callback for connection state changes."""
```

**Acceptance Criteria:**
- [ ] Connection state accurately reported
- [ ] Callback invoked on state changes

**Test Cases:**
- [ ] `test_connection_state_property`
- [ ] `test_connection_callback_on_connect`
- [ ] `test_connection_callback_on_disconnect`

---

### Task 7.3: Coordinator Integration

Integrate WebSocket with `EmbyDataUpdateCoordinator`.

#### 7.3.1 Add WebSocket to coordinator

**File:** `custom_components/embymedia/coordinator.py`

**Changes:**
```python
class EmbyDataUpdateCoordinator(DataUpdateCoordinator[dict[str, EmbySession]]):
    """Coordinator with WebSocket support."""

    websocket: EmbyWebSocket | None = None
    _websocket_enabled: bool = True

    async def async_setup_websocket(self) -> None:
        """Set up WebSocket connection."""

    async def async_shutdown_websocket(self) -> None:
        """Shut down WebSocket connection."""

    def _handle_websocket_message(
        self,
        message_type: str,
        data: Any,
    ) -> None:
        """Handle incoming WebSocket message."""
```

**Acceptance Criteria:**
- [ ] WebSocket created during coordinator setup
- [ ] Messages update coordinator data
- [ ] Clean shutdown on unload

**Test Cases:**
- [ ] `test_coordinator_websocket_setup`
- [ ] `test_coordinator_websocket_message_handling`
- [ ] `test_coordinator_websocket_shutdown`

#### 7.3.2 Handle Sessions message

**Implementation:**
```python
def _handle_sessions_message(
    self,
    sessions_data: list[EmbySessionResponse],
) -> None:
    """Process sessions update from WebSocket.

    Updates coordinator data and triggers entity updates.
    """
    sessions: dict[str, EmbySession] = {}
    for session_data in sessions_data:
        session = parse_session(session_data)
        if session.supports_remote_control:
            sessions[session.device_id] = session

    # Update data and notify listeners
    self.async_set_updated_data(sessions)
```

**Acceptance Criteria:**
- [ ] Sessions parsed correctly
- [ ] Coordinator data updated
- [ ] Entities receive updates

**Test Cases:**
- [ ] `test_handle_sessions_updates_data`
- [ ] `test_handle_sessions_filters_remote_control`
- [ ] `test_handle_sessions_notifies_entities`

#### 7.3.3 Handle playback events

**Implementation:**
```python
def _handle_playback_started(self, data: dict[str, Any]) -> None:
    """Handle PlaybackStarted event."""
    # Force immediate session refresh

def _handle_playback_stopped(self, data: dict[str, Any]) -> None:
    """Handle PlaybackStopped event."""
    # Force immediate session refresh

def _handle_session_ended(self, data: dict[str, Any]) -> None:
    """Handle SessionEnded event."""
    # Remove session from data
```

**Acceptance Criteria:**
- [ ] Playback events trigger updates
- [ ] Session removal handled correctly

**Test Cases:**
- [ ] `test_handle_playback_started`
- [ ] `test_handle_playback_stopped`
- [ ] `test_handle_session_ended`

---

### Task 7.4: Hybrid Polling Mode

Reduce polling frequency when WebSocket is connected.

#### 7.4.1 Adjust polling interval

**File:** `custom_components/embymedia/coordinator.py`

**Implementation:**
```python
WEBSOCKET_POLL_INTERVAL = 60  # Reduced polling when WebSocket connected
FALLBACK_POLL_INTERVAL = 10   # Normal polling without WebSocket

def _update_poll_interval(self) -> None:
    """Update polling interval based on WebSocket state."""
    if self.websocket and self.websocket.connected:
        interval = WEBSOCKET_POLL_INTERVAL
    else:
        interval = self._configured_interval

    self.update_interval = timedelta(seconds=interval)
```

**Acceptance Criteria:**
- [ ] Reduced polling when WebSocket connected
- [ ] Normal polling as fallback
- [ ] Interval updates on WebSocket state change

**Test Cases:**
- [ ] `test_poll_interval_with_websocket`
- [ ] `test_poll_interval_without_websocket`
- [ ] `test_poll_interval_on_websocket_disconnect`

#### 7.4.2 Fallback to polling on WebSocket failure

**Implementation:**
```python
def _handle_websocket_connection_change(self, connected: bool) -> None:
    """Handle WebSocket connection state change."""
    if connected:
        _LOGGER.info("WebSocket connected, reducing poll interval")
    else:
        _LOGGER.warning("WebSocket disconnected, using polling fallback")

    self._update_poll_interval()
```

**Acceptance Criteria:**
- [ ] Graceful fallback to polling
- [ ] Logging for connection changes
- [ ] No data gaps during transition

**Test Cases:**
- [ ] `test_fallback_to_polling`
- [ ] `test_no_data_gap_on_reconnect`

---

### Task 7.5: Integration Setup

Wire up WebSocket in integration lifecycle.

#### 7.5.1 Start WebSocket on setup

**File:** `custom_components/embymedia/__init__.py`

**Changes to `async_setup_entry`:**
```python
async def async_setup_entry(hass: HomeAssistant, entry: EmbyConfigEntry) -> bool:
    # ... existing setup ...

    # Start WebSocket after coordinator setup
    await coordinator.async_setup_websocket()

    # Store unload callback
    entry.async_on_unload(coordinator.async_shutdown_websocket)

    return True
```

**Acceptance Criteria:**
- [ ] WebSocket started during setup
- [ ] WebSocket stopped on unload
- [ ] Integration still works if WebSocket fails

**Test Cases:**
- [ ] `test_setup_starts_websocket`
- [ ] `test_unload_stops_websocket`
- [ ] `test_setup_succeeds_if_websocket_fails`

#### 7.5.2 Add WebSocket toggle option

**File:** `custom_components/embymedia/config_flow.py`

Add option to disable WebSocket:
```python
CONF_ENABLE_WEBSOCKET = "enable_websocket"
DEFAULT_ENABLE_WEBSOCKET = True
```

**Acceptance Criteria:**
- [ ] Option available in options flow
- [ ] WebSocket respects option setting
- [ ] Option persisted correctly

**Test Cases:**
- [ ] `test_options_websocket_toggle`
- [ ] `test_websocket_disabled_by_option`

---

### Task 7.6: Error Handling

Robust error handling for WebSocket operations.

#### 7.6.1 Add WebSocket exceptions

**File:** `custom_components/embymedia/exceptions.py`

```python
class EmbyWebSocketError(EmbyError):
    """Error from WebSocket operations."""

class EmbyWebSocketConnectionError(EmbyWebSocketError):
    """Failed to connect to WebSocket."""

class EmbyWebSocketAuthError(EmbyWebSocketError):
    """WebSocket authentication failed."""
```

**Test Cases:**
- [ ] `test_websocket_exception_hierarchy`

#### 7.6.2 Handle server events

**Implementation:**
```python
def _handle_server_event(self, message_type: str) -> None:
    """Handle server status events."""
    if message_type == "ServerRestarting":
        _LOGGER.info("Emby server is restarting")
        # Expect disconnection, prepare for reconnect
    elif message_type == "ServerShuttingDown":
        _LOGGER.warning("Emby server is shutting down")
        # Stop reconnection attempts
```

**Acceptance Criteria:**
- [ ] Server restart handled gracefully
- [ ] Server shutdown stops reconnection

**Test Cases:**
- [ ] `test_handle_server_restarting`
- [ ] `test_handle_server_shutting_down`

---

## Integration Tests

### Task 7.7: Full WebSocket Integration Test

Test complete WebSocket workflow:
1. Connection established
2. Sessions subscription active
3. Receive session updates
4. Handle playback events
5. Reconnect on disconnect
6. Clean shutdown

**Test Cases:**
- [ ] `test_websocket_full_lifecycle`
- [ ] `test_websocket_reconnect_flow`
- [ ] `test_websocket_with_coordinator`

---

## Acceptance Criteria Summary

### Required for Phase 7 Complete

- [x] WebSocket client implementation
- [x] Connection URL format: `wss://{host}/embywebsocket?api_key={key}&deviceId={id}`
- [x] SessionsStart/SessionsStop subscription
- [x] Handle Sessions message updates
- [x] Handle playback events (PlaybackStarted, PlaybackStopped)
- [x] Handle session end events
- [x] Automatic reconnection with backoff
- [x] Coordinator integration
- [x] Hybrid polling mode
- [x] Clean shutdown
- [x] All tests passing (445 tests)
- [x] 100% code coverage maintained
- [x] No mypy errors
- [x] No ruff errors

### Definition of Done

1. ✅ WebSocket connects to Emby server
2. ✅ Real-time session updates received
3. ✅ Automatic reconnection on disconnect
4. ✅ Reduced polling with WebSocket active (60s vs 10s)
5. ✅ Graceful fallback to polling
6. ✅ Integration continues to work if WebSocket unavailable

### Phase 7 Complete

All acceptance criteria have been met. WebSocket real-time updates are now fully implemented.

### Bug Fix: WebSocket Receive Loop (2025-11-25)

**Issue:** After initial implementation, WebSocket connected but never received messages. The UI showed stale data.

**Root Cause:** The `async_setup_websocket` method in `coordinator.py` was missing two critical steps:
1. Never called `async_subscribe_sessions()` to tell Emby to send session updates
2. Never started the receive loop (`_async_receive_loop()`) to process incoming messages

**Fix:** Added to `coordinator.py`:
```python
# After connect:
await self._websocket.async_subscribe_sessions()
self.hass.async_create_task(self._async_websocket_receive_loop())

# New method:
async def _async_websocket_receive_loop(self) -> None:
    """Run the WebSocket receive loop."""
    if self._websocket is None:
        return
    try:
        await self._websocket._async_receive_loop()
    except Exception as err:
        _LOGGER.warning("WebSocket receive loop error: %s", err)
    finally:
        if self._websocket_enabled:
            self._handle_websocket_connection(False)
```

**Verification:** After fix, logs show:
- `Subscribed to session updates (interval: 1500ms)`
- `Received WebSocket message: Sessions` every ~1.5 seconds
- `Manually updated embymedia data` confirming real-time updates

---

## Message Type Reference

| MessageType | Direction | Description |
|-------------|-----------|-------------|
| SessionsStart | Client → Server | Subscribe to session updates |
| SessionsStop | Client → Server | Unsubscribe from sessions |
| Sessions | Server → Client | Session state update |
| PlaybackStarted | Server → Client | Playback began |
| PlaybackStopped | Server → Client | Playback ended |
| SessionEnded | Server → Client | Session disconnected |
| UserDataChanged | Server → Client | User data changed |
| ServerRestarting | Server → Client | Server restarting |
| ServerShuttingDown | Server → Client | Server shutting down |
| Play | Server → Client | Remote control command |
| Playstate | Server → Client | Remote playback command |
| GeneralCommand | Server → Client | General remote command |

---

## Notes

- WebSocket URL path is `/embywebsocket` (not just `/`)
- Device ID should be unique per integration instance
- SessionsStart interval is in milliseconds
- Sessions message returns full session array (same as REST API)
- No dedicated pause/unpause events - infer from PlayState.IsPaused
- Server auto-increments playback position, so frequent polling unnecessary

---

## Phase 7 Extension: Enhanced Media Features (2025-11-25)

After completing WebSocket support, Phase 7 was extended to include voice assistant integration and enhanced media browsing for large libraries.

### Task 7.8: Voice Assistant Search Support

Implement `async_search_media()` for voice assistant commands like "Play The X-Files Season 1 Episode 12 on Living Room TV".

#### 7.8.1 Search API Implementation

**File:** `custom_components/embymedia/api.py`

Added `async_search_items()` method:
```python
async def async_search_items(
    self,
    user_id: str,
    search_term: str,
    include_item_types: str | None = None,
    limit: int = 50,
) -> list[EmbyBrowseItem]:
    """Search for items in the Emby library.

    Args:
        user_id: The user ID for API calls.
        search_term: The search query string.
        include_item_types: Optional comma-separated item types to filter.
        limit: Maximum number of results to return.

    Returns:
        List of matching items.
    """
```

**Emby API Endpoint:** `GET /Users/{userId}/Items?SearchTerm={query}&Recursive=true`

**Acceptance Criteria:**
- [x] Search uses Emby's `SearchTerm` parameter
- [x] Results sorted by relevance (SortName)
- [x] Optional type filtering (Movie, Episode, Audio, etc.)
- [x] Configurable result limit

**Test Cases:**
- [x] `test_search_items_success`
- [x] `test_search_items_with_type_filter`

#### 7.8.2 Media Player Search Implementation

**File:** `custom_components/embymedia/media_player.py`

Added `MediaPlayerEntityFeature.SEARCH_MEDIA` to supported features and implemented:
```python
async def async_search_media(
    self,
    query: SearchMediaQuery,
) -> SearchMedia:
    """Search for media in Emby library.

    Supports voice assistant commands like "Play X-Files Season 1 Episode 12".

    Args:
        query: Search query containing search string and optional filters.

    Returns:
        SearchMedia with list of matching BrowseMedia results.
    """
```

**SearchMediaQuery Properties:**
| Property | Type | Description |
|----------|------|-------------|
| `search_query` | `str` | The search string |
| `media_content_type` | `MediaType \| str \| None` | Optional type filter |
| `media_content_id` | `str \| None` | Optional content ID scope |
| `media_filter_classes` | `list[MediaClass] \| None` | Optional class filters |

**MediaType to Emby Type Mapping:**
| HA MediaType | Emby Types |
|--------------|------------|
| `MOVIE` | `Movie` |
| `TVSHOW` | `Episode,Series` |
| `MUSIC` | `Audio,MusicAlbum,MusicArtist` |
| `VIDEO` | `Movie,Episode,MusicVideo` |
| `CHANNEL` | `TvChannel` |

**Acceptance Criteria:**
- [x] `SEARCH_MEDIA` feature flag in `supported_features`
- [x] Maps HA MediaType to Emby item types
- [x] Returns `SearchMedia` with `BrowseMedia` results
- [x] Handles no session gracefully (returns empty results)
- [x] Handles no user gracefully (returns empty results)

**Test Cases:**
- [x] `test_search_media_feature_in_supported_features`
- [x] `test_search_media_returns_results`
- [x] `test_search_media_with_type_filter`
- [x] `test_search_media_no_session_returns_empty`
- [x] `test_search_media_no_user_returns_empty`

---

### Task 7.9: Enhanced Music Library Browsing

Implement category-based navigation for music libraries to handle large collections (10,000+ items).

#### 7.9.1 Music Library Categories

**File:** `custom_components/embymedia/media_player.py`

Music libraries now show a category menu instead of listing all artists:

```
Music Library
├── Artists (A-Z navigation)
├── Albums (A-Z navigation)
├── Genres
└── Playlists
```

**Category Structure:**
| Category | Content Type | Navigation |
|----------|--------------|------------|
| Artists | `musicartists` | A-Z letter menu |
| Albums | `musicalbums` | A-Z letter menu |
| Genres | `musicgenres` | Genre list → Albums |
| Playlists | `musicplaylists` | Playlist list |

**A-Z Letter Navigation:**
- Letters A-Z plus `#` for numbers/symbols
- Each letter fetches items starting with that letter
- Uses Emby's `NameStartsWith` parameter for efficient filtering

**API Enhancement - `name_starts_with` parameter:**
```python
async def async_get_items(
    self,
    user_id: str,
    parent_id: str | None = None,
    include_item_types: str | None = None,
    name_starts_with: str | None = None,  # NEW
    ...
) -> EmbyItemsResponse:
```

**New Genre API:**
```python
async def async_get_music_genres(
    self,
    user_id: str,
    parent_id: str | None = None,
) -> list[EmbyBrowseItem]:
    """Get music genres from the Emby library."""
```

**Acceptance Criteria:**
- [x] Music library shows category menu
- [x] A-Z navigation for Artists and Albums
- [x] `#` symbol filters non-alphabetic names
- [x] Genre browsing returns albums in genre
- [x] Playlist browsing shows all playlists
- [x] Playlists marked as playable

**Test Cases:**
- [x] `test_browse_music_library_shows_categories`
- [x] `test_browse_music_artists_shows_letters`
- [x] `test_browse_artists_by_letter`
- [x] `test_browse_artists_hash_symbol`
- [x] `test_browse_music_albums_shows_letters`
- [x] `test_browse_albums_by_letter`
- [x] `test_browse_music_genres`
- [x] `test_browse_genre_items`
- [x] `test_browse_music_playlists`

#### 7.9.2 Playlist Playability

**File:** `custom_components/embymedia/browse.py`

Added `Playlist` to playable types:
```python
_PLAYABLE_TYPES: frozenset[str] = frozenset(
    {
        "Movie", "Episode", "Audio", "TvChannel",
        "MusicVideo", "Trailer", "Playlist",  # Playlist added
    }
)
```

---

### Task 7.10: Live TV Browsing Fix

Fixed Live TV library browsing to properly route to channel listing.

**Issue:** Live TV library was treated as a generic library, failing to show channels.

**Fix:** Added special handling in `_library_to_browse_media()`:
```python
collection_type = library.get("CollectionType", "")
if collection_type == "livetv":
    content_id = encode_content_id("livetv")
    media_content_type = MediaType.CHANNEL
```

**Acceptance Criteria:**
- [x] Live TV library shows channel list
- [x] Channels are marked as playable
- [x] Channel playback works

---

## Phase 7 Extended Summary

### New Features Added

| Feature | Description | Tests |
|---------|-------------|-------|
| Voice Search | `async_search_media()` for voice assistants | 5 tests |
| Search API | `async_search_items()` in EmbyClient | 2 tests |
| Music Categories | Artists, Albums, Genres, Playlists | 9 tests |
| A-Z Navigation | Letter filtering for large collections | Part of music tests |
| Genre API | `async_get_music_genres()` | Part of music tests |
| Live TV Fix | Proper routing to channel list | Existing tests |
| Playlist Playback | Playlists now playable | Part of music tests |

### Test Count

- Phase 7 original (WebSocket): ~75 tests
- Phase 7 extension (Voice + Music): +16 tests
- Total test count: 527 tests
- Coverage: 100%

### Remaining Work (Future Phases)

The following items are deferred to Phase 8:

1. **Movies Library Categories**
   - A-Z, Year, Decade, Genre, Collections

2. **TV Shows Library Categories**
   - A-Z, Year, Decade, Genre

3. **Browse Cache**
   - In-memory cache with TTL for browse API requests

4. **Media Source Enhancement**
   - Apply same category pattern to `media_source.py`

---

## Definition of Done (Phase 7 Extended)

1. ✅ WebSocket connects to Emby server
2. ✅ Real-time session updates received
3. ✅ Automatic reconnection on disconnect
4. ✅ Reduced polling with WebSocket active (60s vs 10s)
5. ✅ Graceful fallback to polling
6. ✅ Voice assistant search support (`async_search_media`)
7. ✅ Music library category navigation
8. ✅ A-Z filtering for large collections
9. ✅ Live TV browsing works
10. ✅ All tests passing (527 tests)
11. ✅ 100% code coverage maintained
