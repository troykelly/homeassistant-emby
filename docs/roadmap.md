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

### 4.2 Image Proxy
- [x] Proxy images through Home Assistant for auth (`EmbyImageProxyView`)
- [x] Cache headers for browser caching (1 year with tag, 5 min without)
- [x] Resize/quality parameters (maxWidth, maxHeight, quality)

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
- [x] **Music**: Library → Categories → A-Z → Artist/Album/Genre/Playlist → Track
- [x] **Playlists**: Library → Playlist → Items
- [x] **Collections**: Library → Collection → Items
- [x] **Live TV**: Library → Channels

### 5.3 Browse Media Response Building
- [x] `BrowseMedia` object construction
- [x] Thumbnail URLs for browse items
- [x] `can_play` / `can_expand` flags
- [x] Content type mapping to HA media types

### 5.4 Play from Browse
- [x] `async_play_media(media_type, media_id)`
- [x] Queue single items
- [x] Queue entire albums/seasons/playlists
- [x] Shuffle/repeat mode support
- [x] `POST /Sessions/{id}/Playing` with ItemIds

**Deliverables:**
- ✅ Full library browsing in HA media browser
- ✅ Play any content directly from browse UI
- ✅ Support for all content types (Movies, TV, Music, Playlists, Collections, Live TV)

---

## Phase 6: Media Source Provider ✅

### 6.1 Media Source Implementation (`media_source.py`)
- [x] Register `EmbyMediaSource` with Home Assistant
- [x] Implement `async_browse_media` for media source
- [x] Implement `async_resolve_media` for playback URLs

### 6.2 Media URL Resolution
- [x] Generate authenticated stream URLs
- [x] Support transcoding parameters
- [x] Direct play vs transcoded play options
- [x] Audio stream selection (API: `audio_stream_index` parameter)
- [x] Subtitle stream selection (API: `subtitle_stream_index` parameter)

### 6.3 Stream URL Endpoints
- [x] `GET /Videos/{id}/stream` - Video streaming
- [x] `GET /Audio/{id}/stream` - Audio streaming
- [x] HLS adaptive streaming (`master.m3u8`)
- [x] Container format selection (mp4, mkv, webm)
- [x] Bitrate/quality selection parameters

### 6.4 Cross-Player Playback
- [x] Expose Emby media to all HA media players
- [x] Stream URLs compatible with Chromecast
- [x] Stream URLs compatible with Sonos/other speakers
- [x] Integration with HA media dashboard

**Deliverables:**
- ✅ Emby content playable on ANY Home Assistant media player
- ✅ Authenticated stream URL generation
- ✅ Transcoding parameter support

---

## Phase 7: Real-Time Updates & Enhanced Features ✅

### 7.1 WebSocket Connection
- [x] Connect to Emby WebSocket API
- [x] Authentication via api_key query parameter
- [x] Automatic reconnection with exponential backoff
- [x] Connection state monitoring

### 7.2 Event Handling
- [x] `Sessions` - Periodic session updates
- [x] `SessionEnded` - Session disconnected
- [x] `PlaybackStarted` - Playback began
- [x] `PlaybackStopped` - Playback ended
- [x] `PlaybackProgress` - Position updates
- [x] `ServerRestarting` - Server restart event
- [x] `ServerShuttingDown` - Server shutdown event

### 7.3 Coordinator Integration
- [x] Push updates to coordinator via callbacks
- [x] Reduce polling interval when WebSocket connected (60s vs 10s)
- [x] Fallback to polling if WebSocket fails
- [x] Hybrid mode: WebSocket for events, polling as backup

### 7.4 WebSocket Exceptions
- [x] `EmbyWebSocketError` - Base WebSocket exception
- [x] `EmbyWebSocketConnectionError` - Connection failures
- [x] `EmbyWebSocketAuthError` - Authentication failures

### 7.5 Voice Assistant Search Support (Extended)
- [x] `async_search_media()` method for voice commands
- [x] `MediaPlayerEntityFeature.SEARCH_MEDIA` feature flag
- [x] `async_search_items()` API method
- [x] MediaType to Emby type mapping
- [x] Support for "Play X-Files Season 1 Episode 12" style commands

### 7.6 Enhanced Music Library Browsing (Extended)
- [x] Category-based navigation (Artists, Albums, Genres, Playlists)
- [x] A-Z letter filtering for large collections
- [x] `name_starts_with` API parameter
- [x] `async_get_music_genres()` API method
- [x] Playlist playability support

### 7.7 Live TV Browsing Fix (Extended)
- [x] Live TV library routes to channel listing
- [x] Channel playback support

**Deliverables:**
- ✅ Near-instant state updates via WebSocket
- ✅ Reduced server load (60s polling with WebSocket vs 10s without)
- ✅ Improved responsiveness
- ✅ Graceful fallback to polling
- ✅ Voice assistant search support
- ✅ Music library category navigation with A-Z filtering
- ✅ Live TV browsing works correctly

---

## Phase 7.5: Extended Media Features ✅

### 7.5.1 Image Proxy
- [x] `EmbyImageProxyView` for authenticated image access
- [x] URL pattern: `/api/embymedia/image/{server_id}/{item_id}/{image_type}`
- [x] Cache headers for browser caching

### 7.5.2 Browse Cache
- [x] In-memory LRU cache with TTL
- [x] Decorator-based caching for browse API responses
- [x] Configurable max size and TTL

### 7.5.3 Movie Library Categories
- [x] A-Z letter navigation
- [x] Year filtering
- [x] Decade filtering (1950s-2020s)
- [x] Genre browsing
- [x] Collections (BoxSets)

### 7.5.4 TV Library Categories
- [x] A-Z letter navigation
- [x] Year filtering
- [x] Decade filtering (1950s-2020s)
- [x] Genre browsing

### 7.5.5 Media Source Enhancement
- [x] All library categories available in media_source.py
- [x] Cross-player compatibility for all library types

**Deliverables:**
- ✅ Image proxy for secure media thumbnails
- ✅ Browse cache for improved performance
- ✅ Movie library category navigation
- ✅ TV library category navigation
- ✅ Consistent browsing across media_player and media_source

---

## Phase 8: Advanced Features ✅

### 8.1 Multiple Users Support ✅
- [x] Per-user authentication option (user selection in config flow)
- [x] User-specific libraries and restrictions (user_id context)
- [x] User context in coordinator
- [x] User avatar display (API: `get_user_image_url()` method)

### 8.2 Remote Control Features ✅
- [x] Send messages to clients (`embymedia.send_message` service)
- [x] Display notification on client
- [x] Navigate client UI (`embymedia.send_command` service)
- [x] General command support

### 8.3 Library Management Services ✅
- [x] Mark item as played/unplayed (`embymedia.mark_played`, `embymedia.mark_unplayed`)
- [x] Update favorite status (`embymedia.add_favorite`, `embymedia.remove_favorite`)
- [x] Trigger library scan (`embymedia.refresh_library`)
- [x] Refresh item metadata (API method exists)

### 8.4 Automation Triggers ✅
- [x] Device triggers for playback events (7 trigger types)
- [x] Custom events for automations (`embymedia_event`)
- [x] Event firing from coordinator

**Deliverables:**
- ✅ Multi-user support
- ✅ Remote control capabilities
- ✅ Library management from HA
- ✅ Automation integration

---

## Phase 9: Polish & Production Readiness ✅

### 9.1 Error Handling & Resilience ✅
- [x] Graceful degradation on partial failures (cached data fallback)
- [x] Detailed error logging
- [x] User-friendly error messages (translation support)
- [x] Automatic recovery mechanisms (consecutive failure tracking)
- [x] Fix `via_device` warning (register server device before entities) - FIXED in Phase 6

### 9.2 Performance Optimization ✅
- [x] Connection pooling (aiohttp ClientSession)
- [x] Response caching where appropriate (BrowseCache with LRU + TTL)
- [x] Lazy loading of heavy data
- [x] Memory usage optimization (dataclass slots)

### 9.3 Configuration Options ✅
- [x] Scan interval customization (5-300 seconds)
- [x] Feature toggles (WebSocket enable/disable)
- [x] Client/device filtering (ignored_devices option)
- [x] Transcoding options (direct_play, video_container, bitrate limits)

### 9.4 Diagnostics ✅
- [x] Implement diagnostics platform
- [x] Server information export
- [x] Connection status
- [x] Active session summary
- [x] Cache statistics
- [x] Per-device diagnostics

### 9.5 Documentation ✅
- [x] Installation guide (README.md)
- [x] Configuration reference
- [x] Troubleshooting guide
- [x] Example automations

**Deliverables:**
- ✅ Production-ready integration
- ✅ Comprehensive documentation
- ✅ Diagnostic capabilities

---

## Phase 10: Testing, CI/CD & HACS Compliance ✅

### 10.1 GitHub Actions CI Pipeline
- [x] Test workflow with Python 3.13 (HA 2025.x minimum)
- [x] Ruff linting and format checking
- [x] Mypy type checking
- [x] Pytest with 100% coverage requirement
- [x] Codecov integration
- [x] HACS validation workflow (`hacs/action@main`)
- [x] Hassfest validation workflow (`home-assistant/actions/hassfest@master`)
- [x] Release workflow with version bump and zip creation
- [x] Daily scheduled validation runs

### 10.2 HACS Default Repository Requirements
- [x] Public GitHub repository
- [x] Repository description
- [ ] At least one GitHub release published (post-merge)
- [x] HACS action passing (workflow created)
- [x] Hassfest action passing (workflow created)
- [ ] Submission to home-assistant/brands (post-merge)

### 10.3 Configuration Files
- [x] `hacs.json` with name, homeassistant minimum
- [x] `manifest.json` with all required fields
- [x] Update `iot_class` to `local_push` (WebSocket)
- [x] Update minimum `homeassistant` to 2024.4.0

### 10.4 Home Assistant Brands
- [ ] Create icon.png (256x256) - external asset
- [ ] Create icon@2x.png (512x512) - external asset
- [ ] Create logo.png (landscape, 128px min) - external asset
- [ ] Create logo@2x.png (landscape, 256px min) - external asset
- [ ] Submit PR to home-assistant/brands (post-merge)

### 10.5 Pre-commit Hooks
- [x] Create `.pre-commit-config.yaml`
- [x] Ruff linting and formatting hooks
- [x] Mypy type checking hook
- [x] Standard pre-commit hooks (trailing-whitespace, etc.)

### 10.6 Test Coverage (Complete ✅)
- [x] 815+ tests passing
- [x] 100% code coverage
- [x] All modules tested
- [x] Live server tests optional

### 10.7 Type Safety (Complete ✅)
- [x] Mypy strict compliance
- [x] No `Any` types (except required overrides)
- [x] Complete type annotations
- [x] TypedDict for all API responses

### 10.8 Documentation
- [x] README.md with installation guide
- [x] Configuration reference
- [x] Troubleshooting guide
- [x] CHANGELOG.md for releases
- [ ] Screenshots for HACS display (optional)

### 10.9 Progressive Code Review (Complete ✅)
- [x] Stage 1: Architecture Review
- [x] Stage 2: API & Data Layer Review
- [x] Stage 3: Entity Implementation Review
- [x] Stage 4: Config Flow & Options Review
- [x] Stage 5: Media Browsing Review
- [x] Stage 6: WebSocket & Real-time Review
- [x] Stage 7: Services & Automation Review
- [x] Stage 8: Error Handling & Edge Cases
- [x] Stage 9: Performance & Efficiency Review
- [x] Stage 10: Security Review
- [x] All critical/high-priority issues resolved or documented

**Deliverables:**
- All CI workflows passing
- HACS default repository ready
- Brands submission complete
- Pre-commit hooks configured
- Documentation complete
- Progressive code review completed

---

## Phase 11: Entity Naming Customization ✅

### Part A: Remove Redundant Suffixes (Breaking Change) ✅

### 11.1 Remove Entity Name Suffixes
- [x] Change `notify.py` `_attr_name` from `"Notification"` to `None`
- [x] Change `remote.py` `_attr_name` from `"Remote"` to `None`
- [x] Update all tests expecting old entity ID patterns
- [x] Document breaking change in CHANGELOG

**Entity ID Changes:**
- `notify.living_room_tv_notification` → `notify.living_room_tv`
- `remote.living_room_tv_remote` → `remote.living_room_tv`

### Part B: Add "Prefix with Emby" Toggles (Per Entity Type) ✅

### 11.2 Configuration Options
- [x] Add `CONF_PREFIX_MEDIA_PLAYER`, `CONF_PREFIX_NOTIFY`, `CONF_PREFIX_REMOTE`, `CONF_PREFIX_BUTTON`
- [x] Add corresponding defaults (all `True`)

### 11.3 Options Flow Enhancement
- [x] Add four boolean toggles to options flow
- [x] All toggles default ON

### 11.4 Entity Updates
- [x] Add `_get_device_name()` helper to `entity.py`
- [x] Override `device_info` in each entity type to use its toggle

### 11.5 Translations
- [x] Add strings.json entries for all four toggles

### 11.6 Testing & Documentation
- [x] 100% test coverage for new code
- [x] Update README with entity naming section
- [x] Document entity ID patterns and breaking changes

**Deliverables:**
- ✅ Clean entity IDs without redundant suffixes
- ✅ Per-entity-type toggles to prefix device names with "Emby"
- ✅ All toggles ON by default → `notify.emby_living_room_tv`
- ✅ Individual toggles can be turned OFF
- ✅ Clear documentation for users

---

## Phase 12: Sensor Platform - Server & Library Statistics ✅

### Overview

Comprehensive sensor platform exposing Emby server health, library statistics, and playback activity.

### 12.1 New Coordinators ✅
- [x] `EmbyServerCoordinator` - 5 min polling for server info
- [x] `EmbyLibraryCoordinator` - 1 hour polling for library counts
- [x] `EmbyRuntimeData` class to manage multiple coordinators

### 12.2 Server Binary Sensors ✅
- [x] `binary_sensor.{server}_connected` - Server reachable
- [x] `binary_sensor.{server}_pending_restart` - From `/System/Info`
- [x] `binary_sensor.{server}_update_available` - From `/System/Info`
- [x] `binary_sensor.{server}_library_scan_active` - With progress % attribute

### 12.3 Server Diagnostic Sensors ✅
- [x] `sensor.{server}_version` - Server version
- [x] `sensor.{server}_running_tasks` - Running task count

### 12.4 Session Sensors ✅
- [x] `sensor.{server}_active_sessions` - Session count

### 12.5 Library Count Sensors (1 Hour Polling) ✅
- [x] `sensor.{server}_movies` - From `/Items/Counts`
- [x] `sensor.{server}_series` - From `/Items/Counts`
- [x] `sensor.{server}_episodes` - From `/Items/Counts`
- [x] `sensor.{server}_albums` - From `/Items/Counts`
- [x] `sensor.{server}_songs` - From `/Items/Counts`
- [x] `sensor.{server}_artists` - From `/Items/Counts`

### 12.6 API Methods ✅
- [x] `async_get_item_counts()` - Library item counts
- [x] `async_get_scheduled_tasks()` - Scheduled task status
- [x] `async_get_virtual_folders()` - Library folder info
- [x] `async_get_user_item_count()` - User-specific counts

### 12.7 Testing & Documentation ✅
- [x] 941 tests with 100% code coverage
- [x] Unit tests for new coordinators
- [x] Update README with sensor documentation

**Deliverables:**
- ✅ All sensors grouped under Emby server device
- ✅ Library scan sensor with progress percentage attribute
- ✅ Library count sensors (movies, series, episodes, songs, albums, artists)
- ✅ Server status binary sensors
- ✅ Session count sensor

---

## Phase 12 Patch: Media Browser Bug Fixes ✅

### Overview

Bug fix release addressing media browser issues in the generic media source.

### 12P.1 Year Browsing Fix ✅
- [x] Fix "Unknown error" when browsing movies by year in media source
- [x] Fix "Unknown error" when browsing TV shows by year in media source
- [x] Add proper error handling for edge cases
- [x] Add debug logging for troubleshooting

### 12P.2 Media Source Feature Parity ✅
- [x] Synchronize browsing features between `media_source.py` and `media_player.py`
- [x] Ensure all content types have explicit handlers
- [x] Add `Unresolvable` exceptions for unknown content types
- [x] Consistent error messages

### 12P.3 Test Coverage ✅
- [x] Add unit tests for year browsing scenarios
- [x] Add tests for error conditions
- [x] Maintain 100% code coverage

**Deliverables:**
- ✅ Year browsing works in generic media source
- ✅ Feature parity between media_source and media_player browsing
- ✅ Improved error handling and logging

---

## Phase 13: Dynamic Transcoding for Universal Media Playback ✅

### Overview

This phase implements intelligent transcoding support for the media source provider, enabling Emby content to be "cast" to any device (Chromecast, Roku, Apple TV, Sonos, etc.) with automatic format negotiation based on target device capabilities.

### 13.1 PlaybackInfo API Integration ✅
- [x] Add `async_get_playback_info()` API method
- [x] Implement `PlaybackInfoRequest` TypedDict
- [x] Implement `PlaybackInfoResponse` TypedDict
- [x] Implement `MediaSourceInfo` TypedDict for response parsing
- [x] Handle `TranscodingUrl` and `DirectStreamUrl` from response
- [x] Generate unique `PlaySessionId` for each stream request

### 13.2 Device Profile System ✅
- [x] Create `DeviceProfile` TypedDict structure
- [x] Implement `DirectPlayProfile` TypedDict
- [x] Implement `TranscodingProfile` TypedDict
- [x] Implement `SubtitleProfile` TypedDict
- [x] Create predefined profiles:
  - `UNIVERSAL_PROFILE` - Safe fallback (H.264/AAC)
  - `CHROMECAST_PROFILE` - Chromecast-optimized
  - `ROKU_PROFILE` - Roku-optimized
  - `APPLETV_PROFILE` - Apple TV-optimized
  - `AUDIO_ONLY_PROFILE` - For speakers (Sonos, Google Home)

### 13.3 Enhanced Media Source Resolution ✅
- [x] Update `async_resolve_media()` to use PlaybackInfo
- [x] Implement format negotiation logic:
  - Direct Play if source is compatible
  - Direct Stream if container needs remuxing only
  - HLS Transcoding if full transcode required
- [x] Return appropriate MIME type based on stream type
- [x] Support `application/x-mpegURL` for HLS streams

### 13.4 HLS Streaming Support ✅
- [x] Generate HLS master playlist URLs with transcoding parameters
- [x] Add `DeviceId` and `MediaSourceId` parameters
- [x] Configure video codec (h264), audio codec (aac), channels
- [x] Support adaptive bitrate parameters

### 13.5 Transcoding Session Management ✅
- [x] Track active transcoding sessions via `PlaySessionId`
- [x] Implement `async_stop_transcoding()` API method
- [x] Call `DELETE /Videos/ActiveEncodings?DeviceId=xxx` on cleanup
- [x] Handle session cleanup on integration unload

### 13.6 Configuration Options ✅
- [x] Add `CONF_TRANSCODING_PROFILE` option (universal/chromecast/roku/appletv)
- [x] Add `CONF_MAX_STREAMING_BITRATE` option (default: 40 Mbps)
- [x] Add `CONF_PREFER_DIRECT_PLAY` option (default: true)
- [x] Add `CONF_MAX_VIDEO_WIDTH` option (default: 1920)
- [x] Add `CONF_MAX_VIDEO_HEIGHT` option (default: 1080)
- [x] Add options to Options Flow

### 13.7 Audio Streaming Enhancement ✅
- [x] Use Universal Audio endpoint `/Audio/{id}/universal`
- [x] Support HLS audio transcoding (`TranscodingProtocol=hls`)
- [x] Support progressive audio fallback
- [x] Configure `MaxStreamingBitrate`, `MaxSampleRate`

### 13.8 TypedDicts & Constants ✅
- [x] `PlaybackInfoRequest` - POST body structure
- [x] `PlaybackInfoResponse` - Response with MediaSources
- [x] `MediaSourceInfo` - Individual media source details
- [x] `MediaStreamInfo` - Audio/video/subtitle stream details
- [x] `DeviceProfile` - Device capability declaration
- [x] `DirectPlayProfile` - Direct play supported formats
- [x] `TranscodingProfile` - Transcoding fallback configuration
- [x] `SubtitleProfile` - Subtitle delivery options
- [x] Constants for common codecs, containers, protocols

### 13.9 Testing ✅
- [x] Unit tests for `async_get_playback_info()`
- [x] Unit tests for device profile generation
- [x] Unit tests for format negotiation logic
- [x] Unit tests for HLS URL generation
- [x] Unit tests for transcoding session cleanup
- [x] Integration tests with mocked PlaybackInfo responses
- [x] 100% code coverage (1102 tests)

### 13.10 Documentation ✅
- [x] Update README with transcoding section
- [x] Document device profiles and their capabilities
- [x] Document configuration options
- [x] Add troubleshooting guide for transcoding issues

**Deliverables:**
- ✅ PlaybackInfo API integration for smart format selection
- ✅ Predefined device profiles for common cast targets
- ✅ Dynamic transcoding with HLS support
- ✅ Direct Play/Direct Stream when compatible
- ✅ Configuration options for transcoding preferences
- ✅ Automatic transcoding session cleanup
- ✅ Full test coverage

---

## Implementation Order

```
Phase 1 ─┬─► Phase 2 ─┬─► Phase 3 ─► Phase 4
         │            │
         │            └─► Phase 5 ─► Phase 6 ─► Phase 13 (Transcoding)
         │
         └─────────────────────────► Phase 7 ─┬─► Phase 8
                                              │
                                              └─► Phase 12 (Sensors) ─► Phase 12P (Bug Fixes)
Phase 8 ─► Phase 9 ─► Phase 10 ─► Phase 11
```

**Critical Path:** Phases 1-3 are sequential and blocking.

**Parallel Work:**
- Phase 4 (Images) can start after Phase 3
- Phase 5 (Browsing) can start after Phase 2
- Phase 7 (WebSocket) can start after Phase 1
- Phase 12 (Sensors) can start after Phase 7 (requires WebSocket)
- Phase 13 (Transcoding) can start after Phase 6 (extends media_source)

---

## Success Criteria

### Minimum Viable Product (Phases 1-4)
- [x] Config flow connects to Emby server
- [x] Media player entities created for active sessions
- [x] Full playback control working
- [x] Media artwork displayed

### Feature Complete (Phases 1-7)
- [x] Media browsing functional
- [x] Media source provider working
- [x] Real-time updates via WebSocket

### Production Ready (Phases 1-12)
- [x] 100% test coverage (941 tests)
- [x] Full documentation
- [x] HACS validation workflows configured
- [x] Hassfest validation workflow configured
- [ ] home-assistant/brands submission (post-merge)
- [x] Pre-commit hooks configured
- [ ] At least one GitHub release (post-merge)
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
| `/Items/Counts` | GET | Library item counts (Phase 12) |
| `/ScheduledTasks` | GET | Scheduled task status (Phase 12) |
| `/Library/VirtualFolders` | GET | Library folders info (Phase 12) |
| `/System/ActivityLog/Entries` | GET | Activity log entries (Phase 12) |
| `/Plugins` | GET | Installed plugins (Phase 12) |
| `/Items/{id}/PlaybackInfo` | POST | Get playback info with DeviceProfile (Phase 13) |
| `/Videos/{id}/master.m3u8` | GET | HLS adaptive streaming (Phase 13) |
| `/Audio/{id}/universal` | GET | Universal audio streaming (Phase 13) |
| `/Videos/ActiveEncodings` | DELETE | Stop transcoding session (Phase 13) |

### WebSocket Subscriptions

| Subscription | Response Type | Purpose |
|-------------|---------------|---------|
| `SessionsStart` | `Sessions` | Periodic session updates |
| `ScheduledTasksInfoStart` | `ScheduledTasksInfo` | Task status updates (Phase 12) |
| `ActivityLogEntryStart` | `ActivityLogEntry` | New activity entries (Phase 12) |

### WebSocket Events (Push-Based)

| Event | Purpose |
|-------|---------|
| `PlaybackStarted` | Playback started |
| `PlaybackStopped` | Playback stopped |
| `PlaybackProgress` | Position update |
| `SessionEnded` | Client disconnected |
| `LibraryChanged` | Library items changed |
| `ServerRestarting` | Server restart initiated |
| `ServerShuttingDown` | Server shutdown initiated |
| `RestartRequired` | Server needs restart |
| `ScheduledTaskEnded` | Task completed |

---

## Phase 14: Enhanced Playback & Queue Management ✅

### Overview

Advanced playback features including Instant Mix (radio mode), similar items recommendations, queue visualization, and announcement support research for TTS integration.

### 14.1 Instant Mix Support ✅
- [x] Add `async_get_instant_mix()` API method (`/Items/{Id}/InstantMix`)
- [x] Add `async_get_artist_instant_mix()` API method (`/Artists/InstantMix`)
- [x] Create `embymedia.play_instant_mix` service
- [x] Support instant mix from currently playing item
- [x] Support instant mix from specified item ID

### 14.2 Similar Items ✅
- [x] Add `async_get_similar_items()` API method (`/Items/{Id}/Similar`)
- [x] Create `embymedia.play_similar` service
- [x] Expose similar items as media player attribute (`similar_items`)

### 14.3 Queue Management ✅
- [x] Parse `NowPlayingQueue` from session data
- [x] Add `queue_position` attribute to media player
- [x] Add `queue_size` attribute to media player
- [x] Add `CLEAR_PLAYLIST` feature support
- [x] Create `embymedia.clear_queue` service

### 14.4 Announcement Support ❌ (Researched - Not Feasible)
- [x] Research Emby API announcement capabilities
- [ ] ~~Implement `MEDIA_ANNOUNCE` feature flag~~ (not possible)
- [ ] ~~Add `async_play_media()` announce parameter handling~~ (not possible)
- [ ] ~~Pause current playback before announcement~~ (not possible)
- [ ] ~~Resume playback after announcement completes~~ (not possible)
- [ ] ~~Support TTS integration via announce~~ (not possible)

**Research Conclusion:** Cannot be implemented due to Emby API limitation - the API requires all playable content to have an Item ID in the library. External URLs (like TTS audio) cannot be played on Emby clients. See [phase-14-tasks.md Task 7](phase-14-tasks.md#task-7-announcement-support-media_announce) for full research.

### 14.5 Testing & Documentation ✅
- [x] Unit tests for all new API methods
- [x] Unit tests for queue management
- [x] Unit tests for similar_items attribute edge cases
- [x] Unit tests for clear_queue service
- [x] Document announcement research findings
- [x] Update README with new features
- [x] Maintain 100% code coverage

**Deliverables:**
- ✅ Instant Mix/radio mode from any item or artist
- ✅ Similar items recommendations (API + service + media player attribute)
- ✅ Queue visualization (position, size) + clear_queue service
- ✅ Announcement research documented (not feasible due to API limitation)

---

## Phase 15: Smart Discovery Sensors ✅

### Overview

Sensors exposing personalized content recommendations including Next Up episodes, Continue Watching, Recently Added, and Suggestions. **Now includes ImageEntity instances for cover art display.**

### 15.1 Next Up Sensor ✅
- [x] Add `async_get_next_up()` API method (`/Shows/NextUp`)
- [x] Create `sensor.{user}_next_up` entity (per-user)
- [x] Expose next episode title, series, thumbnail as attributes
- [x] Support per-user next up
- [x] Add ImageEntity for cover art display

### 15.2 Continue Watching Sensor ✅
- [x] Add `async_get_resumable_items()` API method (`Filters=IsResumable`)
- [x] Create `sensor.{user}_continue_watching` entity (per-user)
- [x] Expose item count with list as attribute
- [x] Include progress percentage per item
- [x] Support multiple media types (movies, episodes)
- [x] Add ImageEntity for cover art display

### 15.3 Recently Added Sensor ✅
- [x] Add `async_get_latest_media()` API method (`/Users/{id}/Items/Latest`)
- [x] Create unified `sensor.{user}_recently_added` entity
- [x] Expose item list with thumbnails as attributes
- [x] Add ImageEntity for cover art display

### 15.4 Suggestions Sensor ✅
- [x] Add `async_get_suggestions()` API method (`/Users/{id}/Suggestions`)
- [x] Create `sensor.{user}_suggestions` entity (per-user)
- [x] Expose personalized recommendations as attributes
- [x] Add ImageEntity for cover art display

### 15.5 Discovery Coordinator ✅
- [x] Create `EmbyDiscoveryCoordinator` with configurable interval
- [x] Default 15-minute polling interval
- [x] Option to disable discovery sensors (`enable_discovery_sensors`)
- [x] Multi-user support (coordinator per user)
- [x] Efficient batched API calls with `asyncio.gather()`

### 15.6 ImageEntity Support ✅
- [x] Create `EmbyDiscoveryImageBase` base class
- [x] 4 ImageEntity classes per user (next_up, continue_watching, recently_added, suggestions)
- [x] Images fetched directly from Emby server via `async_image()`
- [x] Images served via HA's authenticated image proxy
- [x] Series artwork used for episodes (better visual presentation)

### 15.7 Testing & Documentation ✅
- [x] Unit tests for all new API methods
- [x] Unit tests for discovery coordinator
- [x] Unit tests for all sensor entities
- [x] Unit tests for all image entities
- [x] 100% code coverage (1463 tests)
- [x] Translations complete for all entities

### 15.8 Per-User Count Sensors (Enhancement) ✅
- [x] `EmbyUserFavoritesCountSensor` - Per-user favorites count
- [x] `EmbyUserPlayedCountSensor` - Per-user watched items count
- [x] `EmbyUserInProgressCountSensor` - Per-user resumable items count
- [x] `EmbyUserPlaylistCountSensor` - Per-user playlists count
- [x] Updated `EmbyDiscoveryCoordinator` to fetch user-specific counts
- [x] All translations updated (11 files)

**Deliverables:**
- ✅ Next Up sensor showing next episode to watch
- ✅ Continue Watching sensor with resumable items
- ✅ Recently Added sensor with latest content
- ✅ Personalized Suggestions sensor
- ✅ ImageEntity instances for cover art display in dashboards
- ✅ Configurable polling and enable/disable options
- ✅ Multi-user support (sensors and images per user)
- ✅ Per-user count sensors (favorites, watched, in-progress, playlists)

---

## Phase 16: Live TV & DVR Integration ✅

### Overview

Comprehensive Live TV support including channel sensors, recording management, timer scheduling, and EPG data exposure.

### 16.1 Live TV Information
- [x] Add `async_get_live_tv_info()` API method (`/LiveTv/Info`)
- [x] Create `binary_sensor.{server}_live_tv_enabled` entity
- [x] Expose tuner count and active recordings as attributes

### 16.2 Recording Sensors
- [x] Add `async_get_recordings()` API method (`/LiveTv/Recordings`)
- [x] Add `async_get_timers()` API method (`/LiveTv/Timers`)
- [x] Create `sensor.{server}_recordings` entity (count)
- [x] Create `sensor.{server}_active_recordings` entity (currently recording)
- [x] Create `sensor.{server}_scheduled_recordings` entity (upcoming timers)

### 16.3 Timer Management Services
- [x] Add `async_get_timer_defaults()` API method (`/LiveTv/Timers/Defaults`)
- [x] Add `async_create_timer()` API method (`POST /LiveTv/Timers`)
- [x] Add `async_cancel_timer()` API method (`DELETE /LiveTv/Timers/{Id}`)
- [x] Create `embymedia.schedule_recording` service
- [x] Create `embymedia.cancel_recording` service

### 16.4 Series Timer Support
- [x] Add `async_get_series_timers()` API method (`/LiveTv/SeriesTimers`)
- [x] Add `async_create_series_timer()` API method (`POST /LiveTv/SeriesTimers`)
- [x] Add `async_cancel_series_timer()` API method (`DELETE /LiveTv/SeriesTimers/{Id}`)
- [x] Create `embymedia.cancel_series_timer` service
- [x] Create `sensor.{server}_series_recording_rules` entity

### 16.5 EPG Data (Optional)
- [x] Add `async_get_programs()` API method (`/LiveTv/Programs`)
- [x] Add `async_get_recommended_programs()` API method

### 16.6 Testing & Documentation
- [x] Unit tests for all Live TV API methods
- [x] Unit tests for timer services
- [x] Unit tests for recording sensors
- [x] Update README with Live TV section
- [x] Maintain 100% code coverage

**Deliverables:**
- ✅ Live TV enabled binary sensor
- ✅ Recording count, active recordings, and scheduled recordings sensors
- ✅ Series recording rules sensor
- ✅ Services to schedule/cancel recordings
- ✅ Service to cancel series timers
- ✅ EPG data API methods (optional, implemented)

---

## Phase 17: Playlist Management

### Overview

Full playlist lifecycle management including creation, modification, and deletion of playlists from Home Assistant.

### 17.1 Playlist Creation
- [ ] Add `async_create_playlist()` API method (`POST /Playlists`)
- [ ] Create `embymedia.create_playlist` service
- [ ] Support Audio and Video playlist types
- [ ] Support initial item list on creation

### 17.2 Playlist Modification
- [ ] Add `async_add_to_playlist()` API method (`POST /Playlists/{Id}/Items`)
- [ ] Add `async_remove_from_playlist()` API method (`DELETE /Playlists/{Id}/Items`)
- [ ] Create `embymedia.add_to_playlist` service
- [ ] Create `embymedia.remove_from_playlist` service
- [ ] Support adding currently playing item

### 17.3 Playlist Sensors
- [ ] Add `async_get_playlists()` API method
- [ ] Create `sensor.{server}_playlists` entity (count)
- [ ] Expose playlist list with item counts as attribute

### 17.4 Playlist Browsing Enhancement
- [ ] Add playlist management options to media browser
- [ ] Support "Add to playlist" context action
- [ ] Show playlist contents with reorder capability

### 17.5 Testing & Documentation
- [ ] Unit tests for all playlist API methods
- [ ] Unit tests for playlist services
- [ ] Integration tests for playlist workflows
- [ ] Update README with playlist management section
- [ ] Maintain 100% code coverage

**Deliverables:**
- Service to create new playlists
- Services to add/remove items from playlists
- Playlist count sensor with list attribute
- Enhanced media browser playlist integration

---

## Phase 18: User Activity & Statistics

### Overview

Comprehensive activity monitoring including server activity log, user watch statistics, connected devices, and playback history.

### 18.1 Activity Log Sensor
- [ ] Add `async_get_activity_log()` API method (`/System/ActivityLog/Entries`)
- [ ] Create `sensor.{server}_last_activity` entity
- [ ] Expose recent activity list as attribute
- [ ] Filter by severity and type options
- [ ] Support date range filtering

### 18.2 Device Management
- [ ] Add `async_get_devices()` API method (`/Devices`)
- [ ] Create `sensor.{server}_connected_devices` entity
- [ ] Expose device list with last seen timestamps
- [ ] Add device info attributes (name, app, version)

### 18.3 User Watch Statistics
- [ ] Add `async_get_user_watch_history()` API method
- [ ] Create `sensor.{server}_{user}_recently_played` entity
- [ ] Track items played today/this week
- [ ] Calculate estimated watch time

### 18.4 Playback Reporting Integration
- [ ] Subscribe to `PlaybackProgress` WebSocket events
- [ ] Track playback duration per session
- [ ] Aggregate daily/weekly statistics
- [ ] Expose statistics as sensor attributes

### 18.5 Testing & Documentation
- [ ] Unit tests for activity log API
- [ ] Unit tests for device management
- [ ] Unit tests for statistics calculations
- [ ] Update README with activity monitoring section
- [ ] Maintain 100% code coverage

**Deliverables:**
- Activity log sensor with recent events
- Connected devices sensor with device list
- User watch history and statistics
- Real-time playback tracking via WebSocket

---

## Phase 19: Collection Management ✅

### Overview

Collection (BoxSet) lifecycle management and enhanced library browsing by person, tag, and other metadata.

### 19.1 Collection Services ✅
- [x] Add `async_create_collection()` API method (`POST /Collections`)
- [x] Add `async_add_to_collection()` API method
- [x] Add `async_remove_from_collection()` API method
- [x] Create `embymedia.create_collection` service
- [x] Create `embymedia.add_to_collection` service

### 19.2 Collection Sensors ✅
- [x] Create `sensor.{server}_collections` entity (count)
- [x] Expose collection count via library coordinator

### 19.3 Person Browsing ✅
- [x] Add `async_get_persons()` API method (`/Persons`)
- [x] Add `async_get_person_items()` API method
- [x] Add person browsing to media browser ("People" category)
- [x] Support filtering by actor, director, writer
- [x] Show person image and filmography

### 19.4 Tag Browsing ✅
- [x] Add `async_get_tags()` API method (`/Tags`)
- [x] Add `async_get_items_by_tag()` API method
- [x] Add tag browsing to media browser ("Tags" category)
- [x] Support user-defined tags
- [x] Filter items by tag
- [x] Cached tag lists for performance

### 19.5 Testing & Documentation ✅
- [x] Unit tests for collection API methods
- [x] Unit tests for person/tag browsing
- [x] Integration tests for collection workflows (12 tests)
- [x] Update README with collection management section
- [x] Update CHANGELOG with Phase 19 features
- [x] 1567 tests with 100% code coverage

**Deliverables:**
- ✅ Services to create and manage collections
- ✅ Collection count sensor
- ✅ Person browsing in media browser
- ✅ Tag-based filtering and browsing
- ✅ Enhanced movie library categories (People, Tags)

---

## Phase 20: Server Administration ✅

### Overview

Server administration capabilities including scheduled task control, server restart/shutdown, plugin monitoring, and storage information.

### 20.1 Scheduled Task Control ✅
- [x] Add `async_run_scheduled_task()` API method (`POST /ScheduledTasks/Running/{Id}`)
- [x] Create `embymedia.run_scheduled_task` service
- [x] Create button entity for library scan (`button.{server}_run_library_scan`)
- [x] Task ID provided in service call

### 20.2 Server Control ✅
- [x] Add `async_restart_server()` API method (`POST /System/Restart`)
- [x] Add `async_shutdown_server()` API method (`POST /System/Shutdown`)
- [x] Create `embymedia.restart_server` service
- [x] Create `embymedia.shutdown_server` service

### 20.3 Plugin Sensors ✅
- [x] Add `async_get_plugins()` API method (`/Plugins`)
- [x] Create `EmbyPlugin` TypedDict for type-safe plugin data
- [x] Create `sensor.{server}_plugins` entity (count)
- [x] Expose plugin list with version info in extra_state_attributes

### 20.4 Storage Information ❌
- Not available: Emby API does not expose disk space or storage information
- The `/Environment/Drives` endpoint only returns directory paths without size data
- The `/System/Info` endpoint has no storage-related fields
- Third-party plugins like Emby.DashboardExtras exist specifically because this data isn't exposed
- **Resolution:** Cannot implement - Emby API limitation, not a deferral

### 20.5 Testing & Documentation ✅
- [x] Unit tests for task control API (14 tests in test_api_admin.py)
- [x] Unit tests for server control services (13 tests in test_services_admin.py)
- [x] Unit tests for plugin sensor (10 tests in test_sensor_plugins.py)
- [x] Unit tests for Run Library Scan button (8 tests in test_button.py)
- [x] Update services.yaml with new services
- [x] Update strings.json with translations
- [x] 1618 tests with 100% code coverage

**Deliverables:**
- ✅ Service to trigger scheduled tasks on demand
- ✅ Server restart/shutdown services
- ✅ Plugin count sensor with plugin list
- ✅ Run Library Scan button entity

---

## Phase 21: Enhanced WebSocket Events ✅

### Overview

Extended WebSocket event handling to fire Home Assistant events for library changes, user data updates, and server notifications.

### 21.1 Library Change Events ✅
- [x] Subscribe to `LibraryChanged` WebSocket message
- [x] Fire `embymedia_library_updated` HA event
- [x] Include added/updated/removed item IDs
- [x] Clear browse cache on library changes
- [x] Trigger coordinator refresh for affected data (5-second debounce)

### 21.2 User Data Events ✅
- [x] Subscribe to `UserDataChanged` WebSocket message
- [x] Fire `embymedia_user_data_changed` HA event
- [x] Include item ID, user ID, and change type
- [x] Support favorite/rating/played status changes
- [x] Update relevant sensors on changes

### 21.3 Notification Events ✅
- [x] Subscribe to `NotificationAdded` WebSocket message
- [x] Fire `embymedia_notification` HA event
- [x] Include notification text, level, and category
- [x] Option to create persistent notifications in HA

### 21.4 User Account Events ✅
- [x] Subscribe to `UserUpdated`, `UserDeleted` WebSocket messages
- [x] Fire `embymedia_user_changed` HA event
- [x] Reload integration on significant user changes

### 21.5 Event Documentation ✅
- [x] Document all fired events with payload schemas (docs/AUTOMATIONS.md)
- [x] Provide example automations for each event type
- [x] Add event descriptions to developer docs

### 21.6 Testing & Documentation ✅
- [x] Unit tests for WebSocket message parsing
- [x] Unit tests for event firing
- [x] Integration tests for event-driven updates
- [x] Update README with events section
- [x] Maintain 100% code coverage (1649 tests)

**Deliverables:**
- ✅ Library change events for automation triggers
- ✅ User data change events (favorites, ratings, played)
- ✅ Server notification forwarding to HA
- ✅ Comprehensive event documentation with examples

---

## Phase 22: Code Quality & Performance Optimization ✅

### Overview

Comprehensive code quality improvements identified through exhaustive code review. Focus on performance optimization, memory management, code maintainability, and reducing load on both Home Assistant and Emby servers.

### 22.1 Critical: Concurrent API Calls in Coordinators
- [ ] Refactor `EmbyDiscoveryCoordinator._async_update_data()` to use `asyncio.gather()` for 8 parallel API calls
- [ ] Refactor `EmbyServerCoordinator._async_update_data()` to use `asyncio.gather()` for parallel fetches
- [ ] Refactor `EmbyLibraryCoordinator._async_update_data()` to parallelize user-specific count fetches
- [ ] Measure and document performance improvement

### 22.2 Critical: Fix Genre Browsing Filter
- [ ] Fix `_async_browse_genre_items()` to actually filter by genre using `GenreIds` parameter
- [ ] Currently returns ALL albums instead of albums in selected genre
- [ ] Add unit tests for genre filtering

### 22.3 High Priority: Memory Management
- [ ] Clean up `_playback_sessions` dictionary when sessions end (handle `PlaybackStopped`, `SessionEnded`)
- [ ] Add session cleanup in `_handle_websocket_message()` for relevant event types
- [ ] Add maximum age eviction for stale playback session entries
- [ ] Add unit tests for session cleanup

### 22.4 High Priority: Image Proxy Streaming
- [ ] Refactor `EmbyImageProxyView.get()` to stream responses instead of loading full image to memory
- [ ] Use `web.StreamResponse` with chunked transfer
- [ ] Add memory-efficient image proxying for large artwork files

### 22.5 High Priority: Service Call Parallelization
- [ ] Refactor service handlers in `services.py` to use `asyncio.gather()` for multi-entity operations
- [ ] Apply to: `async_send_message`, `async_send_command`, `async_mark_played`, etc.
- [ ] Maintain error handling per-entity while running in parallel

### 22.6 High Priority: Replace MD5 with Modern Hash
- [ ] Replace `hashlib.md5()` in `cache.py` with `hashlib.sha256()` or `hashlib.blake2b()`
- [ ] MD5 is deprecated and may be removed from Python's hashlib in future versions
- [ ] Update cache key generation to use secure hash function

### 22.7 Medium Priority: Encapsulation Fixes
- [ ] Add public `api_key` property to `EmbyClient` (currently accessed via `client._api_key` in image_proxy.py:93-94)
- [ ] Fix `diagnostics.py:67` to use public `websocket_enabled` property instead of `_websocket_enabled`
- [ ] Review all private attribute access and add public interfaces where needed

### 22.8 Medium Priority: Image Fetch Timeout
- [ ] Add explicit timeout to image fetches in `image_discovery.py:150-156`
- [ ] Use `aiohttp.ClientTimeout(total=10)` for image requests
- [ ] Prevent indefinite hangs on slow Emby server responses

### 22.9 Medium Priority: Exception Handling Refinement
- [ ] Replace broad `except Exception:` with specific exceptions in:
  - `__init__.py:269` - Replace with `EmbyError`
  - `__init__.py:319` - Replace with `aiohttp.ClientError, OSError`
  - `remote.py:267` - Replace with `EmbyError, aiohttp.ClientError`
  - `image_discovery.py:163` - Replace with `aiohttp.ClientError, OSError, TimeoutError`
- [ ] Add logging for unexpected exceptions before catching broadly

### 22.10 Low Priority: Code Deduplication
- [ ] Extract common `#` letter handling logic from `_async_browse_*_by_letter` methods into helper
- [ ] Create `_async_browse_items_by_letter()` generic method
- [ ] Apply to: artists, albums, movies, TV shows browsing

### 22.11 Low Priority: Multi-User Coordinator Optimization
- [ ] Consider single discovery coordinator fetching data for all users in admin mode
- [ ] Current design creates N coordinators for N users, each polling independently
- [ ] Evaluate trade-offs: simplicity vs. API call reduction

### 22.12 Low Priority: Web Player Detection Optimization
- [ ] Pre-compute lowercase set for web player client names
- [ ] Change from O(n) substring search to O(1) set lookup
- [ ] Minor optimization for session filtering

### 22.13 Low Priority: WebSocket Session Interval Configuration
- [ ] Make WebSocket session subscription interval configurable via options flow
- [ ] Current hardcoded 1500ms may be too frequent for stable sessions
- [ ] Add `CONF_WEBSOCKET_INTERVAL` option with sensible defaults

### 22.14 Low Priority: Cache Statistics Reset
- [ ] Add `reset_stats()` method to `BrowseCache` for diagnostic purposes
- [ ] Allow users to reset hit/miss counters via diagnostics or service

### 22.15 Testing & Documentation
- [ ] Add unit tests for all refactored code
- [ ] Add performance benchmarks for coordinator updates
- [ ] Document performance improvements in CHANGELOG
- [ ] Maintain 100% code coverage

**Deliverables:**
- Concurrent API calls in all coordinators (significant performance improvement)
- Fixed genre browsing filter
- Memory leak prevention for playback sessions
- Streaming image proxy
- Parallel service execution
- Modern hash function for cache
- Proper encapsulation throughout
- Refined exception handling
- Code deduplication
- Configurable WebSocket intervals

---

## Future Phases (Backlog)

### Phase 23: Multi-Instance & Advanced Config
- Better handling of multiple Emby servers
- Per-user config entries for isolated data
- Device grouping for synchronized playback

### Phase 24: Media Player Enhancements
- `TURN_ON`/`TURN_OFF` with Wake-on-LAN
- `SELECT_SOURCE` for audio/subtitle track selection
- Backdrop image support in addition to poster
- `media_position_percentage` attribute

### Phase 25: Voice Assistant Deep Integration
- Enhanced natural language search
- Context-aware playback ("play the next episode")
- Multi-room audio commands
- Integration with Assist pipelines

---

## Updated Implementation Order

```
Completed Phases (1-21, 14) ────────────────────────────────────────►

Phase 22 (Code Quality) ─► Future Phases

Future: Phase 23 ─► Phase 24 ─► Phase 25
```

**Recommended Priority:**
1. ~~Phase 15 (Discovery Sensors)~~ ✅ Complete
2. ~~Phase 16 (Live TV)~~ ✅ Complete
3. ~~Phase 17 (Playlists)~~ ✅ Complete
4. ~~Phase 18 (Activity)~~ ✅ Complete
5. ~~Phase 19 (Collections)~~ ✅ Complete
6. ~~Phase 20 (Admin)~~ ✅ Complete
7. ~~Phase 21 (WebSocket)~~ ✅ Complete
8. ~~Phase 14 (Enhanced Playback)~~ ✅ Complete
9. Phase 22 (Code Quality & Performance) - Next

---

## Version History

| Version | Date | Milestone |
|---------|------|-----------|
| 0.1.0 | 2025-11-26 | MVP - Full media player with browsing, WebSocket, services |
| 0.2.0 | 2025-11-26 | Sensor platform (Phase 12) |
| 0.3.0 | 2025-11-27 | Dynamic transcoding (Phase 13) |
| 0.4.0 | 2025-11-28 | Discovery sensors with ImageEntity (Phase 15) |
| 0.5.0 | 2025-11-28 | Live TV & DVR Integration (Phase 16) |
| 0.6.0 | 2025-11-28 | Playlist Management (Phase 17) |
| 0.7.0 | 2025-11-29 | User Activity & Statistics (Phase 18) |
| 0.8.0 | 2025-11-29 | Collection Management (Phase 19) |
| 0.9.0 | 2025-11-29 | Server Administration (Phase 20) |
| 0.10.0 | 2025-11-29 | Enhanced WebSocket Events (Phase 21) |
| 0.10.1 | 2025-11-29 | Enhanced Playback Complete (Phase 14) |
| 0.11.0 | TBD | Code Quality & Performance Optimization (Phase 22) |
| 1.0.0 | TBD | Production release |
