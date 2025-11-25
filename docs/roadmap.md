# Home Assistant Emby Integration Roadmap

This document outlines the phased development plan for a complete, production-ready Home Assistant Emby Media Server integration.

## Overview

The integration provides:
- **Dynamic media player entities** - Automatically created/removed for Emby clients
- **Full media browsing** - Navigate Emby libraries within Home Assistant
- **Media source provider** - Expose Emby media for playback on any HA media player
- **Real-time synchronization** - WebSocket-based state updates

---

## Phase 1: Foundation & Core Infrastructure ✅

### 1.1 Project Scaffolding
- [x] Create `custom_components/embymedia/` directory structure
- [x] Configure `manifest.json` with dependencies and requirements
- [x] Set up `const.py` with domain constants and TypedDicts
- [x] Create `strings.json` and `translations/en.json`
- [x] Configure pytest, mypy, and ruff for CI/CD

### 1.2 Emby API Client (`api.py`)
- [x] Implement `EmbyClient` class with aiohttp session management
- [x] Authentication via API key (`X-Emby-Token` header)
- [x] Core endpoints:
  - `GET /System/Info` - Server identification
  - `GET /System/Info/Public` - Public server info (no auth)
  - `GET /Users` - List users
  - `GET /Sessions` - Active sessions/players
- [x] Error handling with custom exceptions (`EmbyConnectionError`, `EmbyAuthenticationError`)
- [x] Connection validation method for config flow
- [x] Tick-to-seconds conversion utilities (10,000,000 ticks = 1 second)

### 1.3 Config Flow (`config_flow.py`)
- [x] User step: Host, port, SSL toggle, API key input
- [x] Connection validation against live server
- [x] Unique ID assignment from server ID
- [x] Error handling: connection refused, auth failed, unknown
- [x] Options flow for configurable settings (scan interval, etc.)

### 1.4 Integration Setup (`__init__.py`)
- [x] `async_setup_entry` - Initialize integration from config entry
- [x] Platform forwarding to `media_player`
- [x] `async_unload_entry` - Clean shutdown
- [x] Store API client in `hass.data[DOMAIN]`

**Deliverables:**
- ✅ Working config flow that connects to Emby server
- ✅ API client with authentication and basic endpoints
- ✅ Integration loads successfully in Home Assistant

---

## Phase 2: Data Coordinator & Entity Management ✅

### 2.1 Data Update Coordinator (`coordinator.py`)
- [x] Implement `EmbyDataUpdateCoordinator` extending `DataUpdateCoordinator`
- [x] Fetch active sessions on configurable interval (default: 10 seconds)
- [x] Parse session data into typed dataclasses
- [x] Handle server unavailable gracefully
- [x] Track session additions and removals

### 2.2 Session & Player Models (`models.py`)
- [x] `EmbySession` dataclass - Session metadata
- [x] `EmbyPlaybackState` dataclass - Playback state information
- [x] `EmbyMediaItem` dataclass - Currently playing media details
- [x] `MediaType` enum - Media type classification
- [x] Type-safe parsing from API responses

### 2.3 Base Entity (`entity.py`)
- [x] `EmbyEntity` base class extending `CoordinatorEntity`
- [x] Device info from session/player data
- [x] Unique ID generation from device ID (stable across reconnections)
- [x] Availability based on coordinator state

### 2.4 Dynamic Entity Registry
- [x] Detect new sessions → Create media player entities
- [x] Entities become unavailable when sessions disappear (not removed)
- [x] Handle session ID changes (reconnecting clients use same entity)
- [x] Entity naming from device name

**Deliverables:**
- ✅ Media player entities automatically appear/disappear
- ✅ Entities update state via coordinator
- ✅ Clean entity lifecycle management

---

## Phase 3: Media Player Entity - Core Features ✅

### 3.1 Media Player Implementation (`media_player.py`)
- [x] Extend `MediaPlayerEntity` with `EmbyEntity`
- [x] Implement `MediaPlayerEntityFeature` flags
- [x] Property implementations:
  - [x] `state` - OFF/IDLE/PLAYING/PAUSED mapping
  - [x] `media_content_id` - Current item ID
  - [x] `media_content_type` - Movie/Episode/Music/etc.
  - [x] `media_title` - Item name
  - [x] `media_artist` / `media_album_name` / `media_album_artist` - Music metadata
  - [x] `media_series_title` / `media_season` / `media_episode` - TV metadata
  - [x] `media_duration` - Total length in seconds
  - [x] `media_position` - Current position in seconds
  - [x] `media_position_updated_at` - Timestamp for position tracking

### 3.2 Volume Control
- [x] `volume_level` property (0.0-1.0)
- [x] `is_volume_muted` property
- [x] `async_set_volume_level(volume)` service
- [x] `async_mute_volume(mute)` service

### 3.3 Playback Control
- [x] `async_media_play()` - Resume playback
- [x] `async_media_pause()` - Pause playback
- [x] `async_media_stop()` - Stop playback
- [x] `async_media_next_track()` - Next item
- [x] `async_media_previous_track()` - Previous item
- [x] `async_media_seek(position)` - Seek to position

### 3.4 Playback Command Implementation
- [x] `POST /Sessions/{id}/Playing/Unpause` - Resume
- [x] `POST /Sessions/{id}/Playing/Pause` - Pause
- [x] `POST /Sessions/{id}/Playing/Stop` - Stop
- [x] `POST /Sessions/{id}/Playing/NextTrack` - Next track
- [x] `POST /Sessions/{id}/Playing/PreviousTrack` - Previous track
- [x] `POST /Sessions/{id}/Playing/Seek` with `SeekPositionTicks`
- [x] `POST /Sessions/{id}/Command/SetVolume` for volume control
- [x] `POST /Sessions/{id}/Command/Mute` and `Unmute` for mute control

**Deliverables:**
- ✅ Full playback control of Emby clients
- ✅ Volume management
- ✅ Accurate state and metadata display

---

## Phase 4: Media Images & Artwork ✅

### 4.1 Image URL Generation
- [x] `media_image_url` property implementation
- [x] Support multiple image types:
  - Primary (poster/cover)
  - Backdrop
  - Thumb
  - Logo
- [x] Image tag caching to prevent unnecessary refreshes
- [x] Fallback hierarchy (item → parent → series)

### 4.2 Image Proxy (Optional)
- [ ] Proxy images through Home Assistant for auth
- [ ] Cache headers for browser caching
- [ ] Resize/quality parameters

**Deliverables:**
- ✅ Media artwork displays in Home Assistant UI
- ✅ Efficient image loading with caching

---

## Phase 5: Media Browsing ✅

### 5.1 Browse Media Implementation
- [x] Implement `async_browse_media(media_content_type, media_content_id)`
- [x] Root level: Libraries (Movies, TV Shows, Music, etc.)
- [x] Library browsing endpoints:
  - `GET /Users/{id}/Items` with ParentId
  - `GET /Users/{id}/Views` for user libraries
- [x] Pagination support for large libraries

### 5.2 Content Type Hierarchy
- [x] **Movies**: Library → Movie
- [x] **TV Shows**: Library → Series → Season → Episode
- [ ] **Music**: Library → Artist → Album → Track (partial - Albums work)
- [ ] **Playlists**: Library → Playlist → Items
- [ ] **Collections**: Library → Collection → Items
- [ ] **Live TV**: Channels → Programs (if enabled)

### 5.3 Browse Media Response Building
- [x] `BrowseMedia` object construction
- [x] Thumbnail URLs for browse items
- [x] `can_play` / `can_expand` flags
- [x] Content type mapping to HA media types

### 5.4 Play from Browse
- [x] `async_play_media(media_type, media_id)`
- [x] Queue single items
- [ ] Queue entire albums/seasons
- [ ] Shuffle/repeat options
- [x] `POST /Sessions/{id}/Playing` with ItemIds

**Deliverables:**
- ✅ Full library browsing in HA media browser
- ✅ Play any content directly from browse UI
- ✅ Support for Movies and TV Shows content types

---

## Phase 6: Media Source Provider

### 6.1 Media Source Implementation (`media_source.py`)
- [ ] Register `EmbyMediaSource` with Home Assistant
- [ ] Implement `async_browse_media` for media source
- [ ] Implement `async_resolve_media` for playback URLs

### 6.2 Media URL Resolution
- [ ] Generate authenticated stream URLs
- [ ] Support transcoding parameters
- [ ] Direct play vs transcoded play options
- [ ] Audio stream selection
- [ ] Subtitle stream selection (external/embedded)

### 6.3 Stream URL Endpoints
- [ ] `GET /Videos/{id}/stream` - Video streaming
- [ ] `GET /Audio/{id}/stream` - Audio streaming
- [ ] `GET /Items/{id}/Download` - Direct download
- [ ] Container format selection (mp4, mkv, webm)
- [ ] Bitrate/quality selection

### 6.4 Cross-Player Playback
- [ ] Expose Emby media to all HA media players
- [ ] Cast Emby content to Chromecast
- [ ] Play Emby content on Sonos/other speakers
- [ ] Integration with HA media dashboard

**Deliverables:**
- Emby content playable on ANY Home Assistant media player
- Authenticated stream URL generation
- Transcoding support for compatibility

---

## Phase 7: Real-Time Updates (WebSocket)

### 7.1 WebSocket Connection
- [ ] Connect to Emby WebSocket API
- [ ] Authentication handshake
- [ ] Automatic reconnection with backoff
- [ ] Connection state monitoring

### 7.2 Event Handling
- [ ] `SessionsStart` - New session connected
- [ ] `SessionsEnd` - Session disconnected
- [ ] `PlaybackStart` - Playback began
- [ ] `PlaybackStopped` - Playback ended
- [ ] `PlaybackProgress` - Position updates
- [ ] `UserDataChanged` - Item state changes

### 7.3 Coordinator Integration
- [ ] Push updates to coordinator
- [ ] Reduce polling frequency with WebSocket active
- [ ] Fallback to polling if WebSocket fails
- [ ] Hybrid mode: WebSocket for events, polling for full sync

**Deliverables:**
- Near-instant state updates
- Reduced server load
- Improved responsiveness

---

## Phase 8: Advanced Features

### 8.1 Multiple Users Support
- [ ] Per-user authentication option
- [ ] User-specific libraries and restrictions
- [ ] Switch user context in options flow
- [ ] User avatar display

### 8.2 Remote Control Features
- [ ] Send messages to clients (`POST /Sessions/{id}/Message`)
- [ ] Display notification on client
- [ ] Navigate client UI (`POST /Sessions/{id}/Command`)
- [ ] General command support

### 8.3 Library Management Services
- [ ] Mark item as played/unplayed
- [ ] Update favorite status
- [ ] Trigger library scan
- [ ] Refresh item metadata

### 8.4 Automation Triggers
- [ ] Device triggers for playback events
- [ ] Conditions for player state
- [ ] Custom events for automations

**Deliverables:**
- Multi-user support
- Remote control capabilities
- Library management from HA
- Automation integration

---

## Phase 9: Polish & Production Readiness

### 9.1 Error Handling & Resilience
- [ ] Graceful degradation on partial failures
- [ ] Detailed error logging
- [ ] User-friendly error messages
- [ ] Automatic recovery mechanisms
- [ ] Fix `via_device` warning (register server device before entities) - see [KNOWN_ISSUES.md](./KNOWN_ISSUES.md)

### 9.2 Performance Optimization
- [ ] Connection pooling
- [ ] Response caching where appropriate
- [ ] Lazy loading of heavy data
- [ ] Memory usage optimization

### 9.3 Configuration Options
- [ ] Scan interval customization
- [ ] Entity naming templates
- [ ] Feature toggles (WebSocket, media source)
- [ ] Client/device filtering

### 9.4 Diagnostics
- [ ] Implement diagnostics platform
- [ ] Server information export
- [ ] Connection status
- [ ] Active session summary

### 9.5 Documentation
- [ ] Installation guide
- [ ] Configuration reference
- [ ] Troubleshooting guide
- [ ] Example automations

**Deliverables:**
- Production-ready integration
- Comprehensive documentation
- Diagnostic capabilities

---

## Phase 10: Testing & Quality Assurance

### 10.1 Unit Tests
- [ ] 100% coverage for all modules
- [ ] API client tests with mocked responses
- [ ] Config flow tests (all paths)
- [ ] Coordinator tests
- [ ] Entity tests

### 10.2 Integration Tests
- [ ] Full setup/unload cycle
- [ ] Entity lifecycle tests
- [ ] Service call tests
- [ ] Error scenario tests

### 10.3 Live Server Tests
- [ ] Optional tests against real Emby server
- [ ] Connection validation
- [ ] Playback control verification
- [ ] Media browsing validation

### 10.4 Type Safety
- [ ] mypy strict compliance
- [ ] No `Any` types (except required overrides)
- [ ] Complete type annotations
- [ ] TypedDict for all API responses

**Deliverables:**
- 100% test coverage
- CI/CD pipeline passing
- Type-safe codebase

---

## Implementation Order

```
Phase 1 ─┬─► Phase 2 ─┬─► Phase 3 ─► Phase 4
         │            │
         │            └─► Phase 5 ─► Phase 6
         │
         └─────────────────────────► Phase 7
                                        │
Phase 8 ◄───────────────────────────────┘
   │
   └─► Phase 9 ─► Phase 10
```

**Critical Path:** Phases 1-3 are sequential and blocking.

**Parallel Work:**
- Phase 4 (Images) can start after Phase 3
- Phase 5 (Browsing) can start after Phase 2
- Phase 7 (WebSocket) can start after Phase 1

---

## Success Criteria

### Minimum Viable Product (Phases 1-4)
- [x] Config flow connects to Emby server
- [x] Media player entities created for active sessions
- [x] Full playback control working
- [x] Media artwork displayed

### Feature Complete (Phases 1-7)
- [x] Media browsing functional
- [ ] Media source provider working
- [ ] Real-time updates via WebSocket

### Production Ready (Phases 1-10)
- [ ] 100% test coverage
- [ ] Full documentation
- [ ] HACS compatible
- [ ] Community tested

---

## API Reference Summary

### Core Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/System/Info` | GET | Server identification |
| `/System/Info/Public` | GET | Public info (no auth) |
| `/Sessions` | GET | Active sessions list |
| `/Users` | GET | User list |
| `/Users/{id}/Views` | GET | User libraries |
| `/Users/{id}/Items` | GET | Browse items |
| `/Items/{id}` | GET | Item details |
| `/Items/{id}/Images/{type}` | GET | Item artwork |
| `/Videos/{id}/stream` | GET | Video stream URL |
| `/Audio/{id}/stream` | GET | Audio stream URL |
| `/Sessions/{id}/Playing/{cmd}` | POST | Playback control |
| `/Sessions/{id}/Command` | POST | General commands |

### WebSocket Events

| Event | Purpose |
|-------|---------|
| `SessionsStart` | Client connected |
| `SessionsEnd` | Client disconnected |
| `PlaybackStart` | Playback started |
| `PlaybackStopped` | Playback stopped |
| `PlaybackProgress` | Position update |

---

## Version History

| Version | Date | Milestone |
|---------|------|-----------|
| 0.1.0 | TBD | MVP - Basic media player |
| 0.2.0 | TBD | Media browsing |
| 0.3.0 | TBD | Media source provider |
| 0.4.0 | TBD | WebSocket support |
| 1.0.0 | TBD | Production release |
