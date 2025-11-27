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

## Phase 14: Enhanced Playback & Queue Management

### Overview

Advanced playback features including Instant Mix (radio mode), similar items recommendations, queue visualization, and announcement support for TTS integration.

### 14.1 Instant Mix Support
- [ ] Add `async_get_instant_mix()` API method (`/Items/{Id}/InstantMix`)
- [ ] Add `async_get_artist_instant_mix()` API method (`/Artists/InstantMix`)
- [ ] Create `embymedia.play_instant_mix` service
- [ ] Support instant mix from currently playing item
- [ ] Support instant mix from specified item ID

### 14.2 Similar Items
- [ ] Add `async_get_similar_items()` API method (`/Items/{Id}/Similar`)
- [ ] Create `embymedia.play_similar` service
- [ ] Expose similar items as media player attribute

### 14.3 Queue Management
- [ ] Parse `NowPlayingQueue` from session data
- [ ] Add `queue_position` attribute to media player
- [ ] Add `queue_size` attribute to media player
- [ ] Add `CLEAR_PLAYLIST` feature support
- [ ] Create `embymedia.clear_queue` service

### 14.4 Announcement Support
- [ ] Implement `MEDIA_ANNOUNCE` feature flag
- [ ] Add `async_play_media()` announce parameter handling
- [ ] Pause current playback before announcement
- [ ] Resume playback after announcement completes
- [ ] Support TTS integration via announce

### 14.5 Testing & Documentation
- [ ] Unit tests for all new API methods
- [ ] Unit tests for queue management
- [ ] Unit tests for announcement flow
- [ ] Update README with new features
- [ ] Maintain 100% code coverage

**Deliverables:**
- Instant Mix/radio mode from any item or artist
- Similar items recommendations
- Queue visualization and management
- TTS announcement support with auto-resume

---

## Phase 15: Smart Discovery Sensors

### Overview

Sensors exposing personalized content recommendations including Next Up episodes, Continue Watching, Recently Added, and Suggestions.

### 15.1 Next Up Sensor
- [ ] Add `async_get_next_up()` API method (`/Shows/NextUp`)
- [ ] Create `sensor.{server}_next_up` entity
- [ ] Expose next episode title, series, thumbnail as attributes
- [ ] Support per-user next up (uses configured user)
- [ ] Add `Legacynextup=true` parameter option

### 15.2 Continue Watching Sensor
- [ ] Add `async_get_resumable_items()` API method (`Filters=IsResumable`)
- [ ] Create `sensor.{server}_continue_watching` entity
- [ ] Expose item count with list as attribute
- [ ] Include progress percentage per item
- [ ] Support multiple media types (movies, episodes)

### 15.3 Recently Added Sensors
- [ ] Add `async_get_latest_media()` API method (`/Users/{id}/Items/Latest`)
- [ ] Create `sensor.{server}_recently_added_movies` entity
- [ ] Create `sensor.{server}_recently_added_episodes` entity
- [ ] Create `sensor.{server}_recently_added_music` entity
- [ ] Expose item list with thumbnails as attributes

### 15.4 Suggestions Sensor
- [ ] Add `async_get_suggestions()` API method (`/Users/{id}/Suggestions`)
- [ ] Create `sensor.{server}_suggestions` entity
- [ ] Expose personalized recommendations as attributes

### 15.5 Discovery Coordinator
- [ ] Create `EmbyDiscoveryCoordinator` with configurable interval
- [ ] Default 15-minute polling interval
- [ ] Option to disable discovery sensors
- [ ] Efficient batched API calls

### 15.6 Testing & Documentation
- [ ] Unit tests for all new API methods
- [ ] Unit tests for discovery coordinator
- [ ] Unit tests for all sensor entities
- [ ] Update README with discovery sensors section
- [ ] Maintain 100% code coverage

**Deliverables:**
- Next Up sensor showing next episode to watch
- Continue Watching sensor with resumable items
- Recently Added sensors per media type
- Personalized Suggestions sensor
- Configurable polling and enable/disable options

---

## Phase 16: Live TV & DVR Integration

### Overview

Comprehensive Live TV support including channel sensors, recording management, timer scheduling, and EPG data exposure.

### 16.1 Live TV Information
- [ ] Add `async_get_live_tv_info()` API method (`/LiveTv/Info`)
- [ ] Create `binary_sensor.{server}_live_tv_enabled` entity
- [ ] Expose enabled users as attribute

### 16.2 Recording Sensors
- [ ] Add `async_get_recordings()` API method (`/LiveTv/Recordings`)
- [ ] Add `async_get_timers()` API method (`/LiveTv/Timers`)
- [ ] Create `sensor.{server}_recordings` entity (count with list attribute)
- [ ] Create `sensor.{server}_scheduled_recordings` entity (upcoming timers)

### 16.3 Timer Management Services
- [ ] Add `async_get_timer_defaults()` API method (`/LiveTv/Timers/Defaults`)
- [ ] Add `async_create_timer()` API method (`POST /LiveTv/Timers`)
- [ ] Add `async_cancel_timer()` API method (`DELETE /LiveTv/Timers/{Id}`)
- [ ] Create `embymedia.schedule_recording` service
- [ ] Create `embymedia.cancel_recording` service

### 16.4 Series Timer Support
- [ ] Add `async_get_series_timers()` API method (`/LiveTv/SeriesTimers`)
- [ ] Add `async_create_series_timer()` API method (`POST /LiveTv/SeriesTimers`)
- [ ] Create `embymedia.schedule_series` service
- [ ] Expose series timers as sensor attribute

### 16.5 EPG Data (Optional)
- [ ] Add `async_get_programs()` API method (`/LiveTv/Programs`)
- [ ] Add `async_get_recommended_programs()` API method
- [ ] Expose current/next program per channel as attributes

### 16.6 Testing & Documentation
- [ ] Unit tests for all Live TV API methods
- [ ] Unit tests for timer services
- [ ] Unit tests for recording sensors
- [ ] Update README with Live TV section
- [ ] Maintain 100% code coverage

**Deliverables:**
- Live TV enabled binary sensor
- Recording count and scheduled recordings sensors
- Services to schedule/cancel recordings
- Series timer support for recording entire shows
- Optional EPG data exposure

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

## Phase 19: Collection Management

### Overview

Collection (BoxSet) lifecycle management and enhanced library browsing by person, tag, and other metadata.

### 19.1 Collection Services
- [ ] Add `async_create_collection()` API method (`POST /Collections`)
- [ ] Add `async_add_to_collection()` API method
- [ ] Add `async_remove_from_collection()` API method
- [ ] Create `embymedia.create_collection` service
- [ ] Create `embymedia.add_to_collection` service

### 19.2 Collection Sensors
- [ ] Create `sensor.{server}_collections` entity (count)
- [ ] Expose collection list with item counts
- [ ] Track collection completeness percentage

### 19.3 Person Browsing
- [ ] Add `async_get_persons()` API method (`/Persons`)
- [ ] Add person browsing to media browser
- [ ] Support filtering by actor, director, writer
- [ ] Show person image and filmography

### 19.4 Tag Browsing
- [ ] Add `async_get_tags()` API method (`/Tags`)
- [ ] Add tag browsing to media browser
- [ ] Support user-defined tags
- [ ] Filter items by tag

### 19.5 Testing & Documentation
- [ ] Unit tests for collection API methods
- [ ] Unit tests for person/tag browsing
- [ ] Integration tests for collection workflows
- [ ] Update README with collection management section
- [ ] Maintain 100% code coverage

**Deliverables:**
- Services to create and manage collections
- Collection count sensor with list
- Person browsing in media browser
- Tag-based filtering and browsing

---

## Phase 20: Server Administration

### Overview

Server administration capabilities including scheduled task control, server restart/shutdown, plugin monitoring, and storage information.

### 20.1 Scheduled Task Control
- [ ] Add `async_run_scheduled_task()` API method (`POST /ScheduledTasks/{Id}/Trigger`)
- [ ] Add `async_stop_scheduled_task()` API method
- [ ] Create `embymedia.run_scheduled_task` service
- [ ] Create button entities for common tasks (library scan, etc.)
- [ ] Expose available tasks as service selector

### 20.2 Server Control
- [ ] Add `async_restart_server()` API method (`POST /System/Restart`)
- [ ] Add `async_shutdown_server()` API method (`POST /System/Shutdown`)
- [ ] Create `embymedia.restart_server` service
- [ ] Create `embymedia.shutdown_server` service
- [ ] Add confirmation requirement for destructive actions

### 20.3 Plugin Sensors
- [ ] Add `async_get_plugins()` API method (`/Plugins`)
- [ ] Create `sensor.{server}_plugins` entity (count)
- [ ] Expose plugin list with version info
- [ ] Detect plugins with available updates

### 20.4 Storage Information
- [ ] Parse virtual folder paths from existing API
- [ ] Create `sensor.{server}_storage` entity (optional)
- [ ] Expose library paths and sizes
- [ ] Monitor available disk space (if accessible)

### 20.5 Testing & Documentation
- [ ] Unit tests for task control API
- [ ] Unit tests for server control (mocked)
- [ ] Unit tests for plugin detection
- [ ] Update README with administration section
- [ ] Maintain 100% code coverage

**Deliverables:**
- Service to trigger scheduled tasks on demand
- Server restart/shutdown services (with confirmation)
- Plugin count sensor with update detection
- Optional storage monitoring

---

## Phase 21: Enhanced WebSocket Events

### Overview

Extended WebSocket event handling to fire Home Assistant events for library changes, user data updates, and server notifications.

### 21.1 Library Change Events
- [ ] Subscribe to `LibraryChanged` WebSocket message
- [ ] Fire `embymedia_library_updated` HA event
- [ ] Include added/updated/removed item IDs
- [ ] Clear browse cache on library changes
- [ ] Trigger coordinator refresh for affected data

### 21.2 User Data Events
- [ ] Subscribe to `UserDataChanged` WebSocket message
- [ ] Fire `embymedia_user_data_changed` HA event
- [ ] Include item ID, user ID, and change type
- [ ] Support favorite/rating/played status changes
- [ ] Update relevant sensors on changes

### 21.3 Notification Events
- [ ] Subscribe to `NotificationAdded` WebSocket message
- [ ] Fire `embymedia_notification` HA event
- [ ] Include notification text, level, and category
- [ ] Option to create persistent notifications in HA

### 21.4 User Account Events
- [ ] Subscribe to `UserUpdated`, `UserDeleted` WebSocket messages
- [ ] Fire `embymedia_user_changed` HA event
- [ ] Reload integration on significant user changes

### 21.5 Event Documentation
- [ ] Document all fired events with payload schemas
- [ ] Provide example automations for each event type
- [ ] Add event descriptions to developer docs

### 21.6 Testing & Documentation
- [ ] Unit tests for WebSocket message parsing
- [ ] Unit tests for event firing
- [ ] Integration tests for event-driven updates
- [ ] Update README with events section
- [ ] Maintain 100% code coverage

**Deliverables:**
- Library change events for automation triggers
- User data change events (favorites, ratings, played)
- Server notification forwarding to HA
- Comprehensive event documentation with examples

---

## Future Phases (Backlog)

### Phase 22: Multi-Instance & Advanced Config
- Better handling of multiple Emby servers
- Per-user config entries for isolated data
- Device grouping for synchronized playback

### Phase 23: Media Player Enhancements
- `TURN_ON`/`TURN_OFF` with Wake-on-LAN
- `SELECT_SOURCE` for audio/subtitle track selection
- Backdrop image support in addition to poster
- `media_position_percentage` attribute

### Phase 24: Voice Assistant Deep Integration
- Enhanced natural language search
- Context-aware playback ("play the next episode")
- Multi-room audio commands
- Integration with Assist pipelines

---

## Updated Implementation Order

```
Completed Phases (1-13) ────────────────────────────────────────────►

Phase 14 (Queue/Mix) ─┬─► Phase 17 (Playlists)
                      │
Phase 15 (Discovery)  ├─► Phase 18 (Activity)
                      │
Phase 16 (Live TV)    └─► Phase 19 (Collections)

Phase 20 (Admin) ─────────► Phase 21 (WebSocket Events)

Future: Phase 22 ─► Phase 23 ─► Phase 24
```

**Recommended Priority:**
1. Phase 15 (Discovery Sensors) - High user value
2. Phase 14 (Queue/Instant Mix) - Enhanced playback
3. Phase 20 (Admin) - Server control automation
4. Phase 18 (Activity) - Usage monitoring
5. Phase 16 (Live TV) - For Live TV users
6. Phase 17 (Playlists) - Library management
7. Phase 21 (WebSocket) - Reactive automations
8. Phase 19 (Collections) - Power user features

---

## Version History

| Version | Date | Milestone |
|---------|------|-----------|
| 0.1.0 | 2025-11-26 | MVP - Full media player with browsing, WebSocket, services |
| 0.2.0 | 2025-11-26 | Sensor platform (Phase 12) |
| 0.3.0 | 2025-11-27 | Dynamic transcoding (Phase 13) |
| 0.4.0 | TBD | Discovery sensors (Phase 15) |
| 0.5.0 | TBD | Queue management & Instant Mix (Phase 14) |
| 1.0.0 | TBD | Production release |
