# Architecture Overview

This document describes the technical architecture of the Emby Media integration for Home Assistant.

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            Home Assistant                                 │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                         Config Entry                                 │ │
│  │  Stores: host, port, api_key, ssl, user_id, options                 │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                    │                                      │
│                                    ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                       Runtime Data                                   │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │ │
│  │  │ Session      │  │ Server       │  │ Library      │              │ │
│  │  │ Coordinator  │  │ Coordinator  │  │ Coordinator  │              │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │ │
│  │                                                                      │ │
│  │  ┌──────────────────────────────────────────────────────────────┐   │ │
│  │  │              Discovery Coordinators (per user)                │   │ │
│  │  └──────────────────────────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                    │                                      │
│                                    ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                          EmbyClient                                  │ │
│  │                                                                      │ │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │ │
│  │  │ HTTP Client   │  │ WebSocket     │  │ Metrics       │           │ │
│  │  │ (aiohttp)     │  │ Client        │  │ Collector     │           │ │
│  │  └───────────────┘  └───────────────┘  └───────────────┘           │ │
│  │                                                                      │ │
│  │  ┌───────────────┐  ┌───────────────┐                              │ │
│  │  │ Browse Cache  │  │ Request       │                              │ │
│  │  │ (TTL: 5m)     │  │ Coalescing    │                              │ │
│  │  └───────────────┘  └───────────────┘                              │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
├───────────────────────────────────────────────────────────────────────────┤
│  Entity Platforms                                                         │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐            │
│  │media_player│ │ remote     │ │ notify     │ │ button     │            │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘            │
│  ┌────────────┐ ┌────────────┐                                          │
│  │ sensor     │ │binary_sensor│                                          │
│  └────────────┘ └────────────┘                                          │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                            Emby Server                                    │
│  ┌────────────────────────┐    ┌────────────────────────┐               │
│  │ REST API               │    │ WebSocket Server       │               │
│  │ - /System/Info         │    │ - Sessions subscription│               │
│  │ - /Sessions            │    │ - LibraryChanged      │               │
│  │ - /Users/{id}/Items    │    │ - PlaybackStart/Stop  │               │
│  │ - /Items/{id}          │    │ - UserDataChanged     │               │
│  └────────────────────────┘    └────────────────────────┘               │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Components

### Config Entry

Stores connection configuration:

| Field | Description |
|-------|-------------|
| `host` | Emby server hostname/IP |
| `port` | Server port (default: 8096) |
| `api_key` | Authentication key |
| `ssl` | Use HTTPS |
| `verify_ssl` | Validate SSL certificates |
| `user_id` | Optional user context |

### Options

Runtime-adjustable settings:

| Field | Default | Description |
|-------|---------|-------------|
| `scan_interval` | 10s | Session polling interval |
| `enable_websocket` | true | Enable WebSocket |
| `websocket_interval` | 1500ms | WS subscription rate |
| `library_scan_interval` | 3600s | Library update interval |
| `server_scan_interval` | 300s | Server status interval |
| `ignored_devices` | [] | Hidden device names |
| `ignore_web_players` | false | Hide browser sessions |

---

## Coordinators

### Session Coordinator (`EmbyDataUpdateCoordinator`)

**Purpose:** Track active playback sessions

**Data Type:** `dict[str, EmbySession]`

**Update Source:**
- WebSocket (primary) - instant updates
- HTTP polling (fallback) - configurable interval

**Entities Created:**
- `media_player` - One per session
- `remote` - Navigation controls
- `notify` - On-screen messages

### Server Coordinator (`EmbyServerCoordinator`)

**Purpose:** Monitor server health and status

**Data Type:** `EmbyServerData`

**Update Interval:** 5 minutes (configurable)

**Entities Created:**
- `sensor.emby_version`
- `sensor.emby_active_sessions`
- `sensor.emby_running_tasks`
- `binary_sensor.emby_connected`
- `binary_sensor.emby_pending_restart`
- `binary_sensor.emby_update_available`

### Library Coordinator (`EmbyLibraryCoordinator`)

**Purpose:** Track library statistics

**Data Type:** `EmbyLibraryData`

**Update Interval:** 1 hour (configurable)

**Entities Created:**
- `sensor.emby_movies`
- `sensor.emby_series`
- `sensor.emby_episodes`
- `sensor.emby_songs`
- `sensor.emby_albums`
- `sensor.emby_artists`
- `binary_sensor.emby_library_scan_active`

### Discovery Coordinator (`EmbyDiscoveryCoordinator`)

**Purpose:** User-specific library discovery

**Data Type:** `EmbyDiscoveryData`

**Update Interval:** 30 minutes

**Per-User Data:**
- Latest media items
- Resume points
- Favorites count
- Played count
- Playlist count

---

## EmbyClient

The main API client for Emby server communication.

### HTTP Methods

| Method | Purpose |
|--------|---------|
| `_request` | GET requests |
| `_request_post` | POST without response |
| `_request_post_json` | POST with JSON response |
| `_request_delete` | DELETE requests |

All methods:
- Include timing instrumentation
- Handle authentication
- Manage SSL context
- Record metrics

### WebSocket Client

Manages real-time connection:

```python
class EmbyWebSocket:
    # Connection management
    async_connect()
    async_disconnect()

    # Subscriptions
    async_subscribe_sessions(interval_ms=1500)

    # Properties
    connected: bool
    reconnecting: bool
```

**Reconnection Strategy:**
- Initial delay: 5 seconds
- Maximum delay: 5 minutes
- Exponential backoff between attempts

### Caching

**Browse Cache:**
- LRU eviction policy
- 500 entry maximum
- 5-minute TTL
- Key generation via BLAKE2b hash

**Request Coalescing:**
- In-flight request deduplication
- asyncio.Lock for synchronization
- Immediate cleanup on completion

### Metrics Collector

Tracks API efficiency:

```python
@dataclass
class MetricsCollector:
    # API call tracking
    record_api_call(endpoint, duration_ms, error=False)

    # WebSocket tracking
    record_websocket_message(type)
    record_websocket_connect()
    record_websocket_disconnect()
    record_websocket_reconnect()

    # Coordinator tracking
    record_coordinator_update(name, duration_ms, success=True)

    # Export
    to_diagnostics() -> dict
```

---

## Entity Platforms

### Media Player (`media_player.py`)

**Features:**
- Play/pause/stop/seek
- Volume control
- Media browsing
- Queue management
- Shuffle/repeat
- Voice assistant search

**State Mapping:**

| Condition | State |
|-----------|-------|
| No session | OFF |
| Session, not playing | IDLE |
| Playing, paused | PAUSED |
| Playing | PLAYING |

### Remote (`remote.py`)

**Purpose:** Navigation commands for clients

**Commands:**
- `up`, `down`, `left`, `right`
- `select`, `back`, `home`
- `info`, `menu`
- `play`, `pause`

### Notify (`notify.py`)

**Purpose:** Send on-screen messages

**Target:** Session-specific notification

### Button (`button.py`)

**Purpose:** Server actions

**Buttons:**
- Refresh Library
- Restart Server (if available)

### Sensors (`sensor.py`)

**Types:**
- Library counts (movies, series, etc.)
- Server info (version, sessions)
- User statistics

### Binary Sensors (`binary_sensor.py`)

**Types:**
- Connection status
- Update availability
- Library scan status
- Pending restart

---

## Data Models

### EmbySession

```python
@dataclass
class EmbySession:
    session_id: str
    device_id: str
    device_name: str
    client_name: str
    app_version: str
    user_id: str | None
    user_name: str | None
    now_playing: EmbyNowPlaying | None
    play_state: EmbyPlayState | None
    supports_remote_control: bool
    supported_commands: list[str]
```

### EmbyNowPlaying

```python
@dataclass
class EmbyNowPlaying:
    item_id: str
    name: str
    series_name: str | None
    season_name: str | None
    episode_name: str | None
    media_type: EmbyMediaType
    duration_ticks: int | None
    position_ticks: int | None
    image_url: str | None
```

### EmbyPlayState

```python
@dataclass
class EmbyPlayState:
    is_paused: bool
    is_muted: bool
    volume_level: float | None
    position_ticks: int | None
    shuffle_mode: str | None
    repeat_mode: str | None
```

---

## Initialization Flow

```
async_setup_entry(hass, entry)
    │
    ├── Create EmbyClient
    │       └── Initialize caches, metrics
    │
    ├── Validate connection
    │       └── GET /System/Info
    │
    ├── Create Coordinators
    │       ├── SessionCoordinator
    │       ├── ServerCoordinator
    │       ├── LibraryCoordinator
    │       └── DiscoveryCoordinator(s)
    │
    ├── Store in runtime_data
    │
    ├── Start WebSocket (if enabled)
    │       └── Subscribe to sessions
    │
    ├── Initial coordinator refresh
    │       └── Parallel async_gather()
    │
    └── Forward to platforms
            ├── media_player
            ├── remote
            ├── notify
            ├── button
            ├── sensor
            └── binary_sensor
```

---

## WebSocket Message Handling

### Message Types

| Type | Handler | Action |
|------|---------|--------|
| `Sessions` | Session coordinator | Update session data |
| `LibraryChanged` | Library coordinator | Invalidate cache, refresh |
| `PlaybackStart` | Session coordinator | Update now playing |
| `PlaybackStop` | Session coordinator | Clear now playing |
| `UserDataChanged` | Discovery coordinator | Refresh user data |

### Connection Lifecycle

```
┌─────────────┐
│ Disconnected │
└──────┬──────┘
       │ connect()
       ▼
┌─────────────┐
│ Connecting  │
└──────┬──────┘
       │ success
       ▼
┌─────────────┐◄────────┐
│ Connected   │         │
└──────┬──────┘         │
       │ disconnect     │ reconnect
       ▼                │
┌─────────────┐         │
│ Reconnecting├─────────┘
└─────────────┘
```

---

## Error Handling

### Exception Hierarchy

```
EmbyError (base)
├── EmbyConnectionError
├── EmbyAuthenticationError
├── EmbyNotFoundError
├── EmbyServerError
├── EmbyTimeoutError
└── EmbySSLError
```

### Retry Strategy

| Error Type | Retry | Backoff |
|------------|-------|---------|
| Connection | Yes | Exponential |
| Authentication | No | N/A |
| Not Found | No | N/A |
| Server Error | Yes | Linear |
| Timeout | Yes | Exponential |
| SSL Error | No | N/A |

---

## See Also

- **[Efficiency](EFFICIENCY.md)** - Performance optimization details
- **[Configuration](CONFIGURATION.md)** - User configuration options
- **[Services](SERVICES.md)** - Available service calls
- **[CLAUDE.md](../CLAUDE.md)** - Development guidelines
