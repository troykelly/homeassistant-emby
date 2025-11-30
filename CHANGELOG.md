# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.1] - 2025-11-30

### Added
- **Playing Sessions Sensor** (#276)
  - New sensor: `sensor.{server}_playing_sessions` - Count of currently playing sessions
  - Proper translations for sensor name and state attributes

### Fixed
- **Artist Count Accuracy** (#277)
  - Artist count sensor now uses dedicated `async_get_artist_count` API for accurate counts
  - Added workaround for BoxSet (collections) count always returning zero from Emby API

### Changed
- Migrated to GitHub Issues/Projects workflow for project management (#278)
- Added GitHub issue templates with AI-powered triage support (#275)

## [0.4.0] - 2025-11-29

### Added
- **Enhanced WebSocket Events** (Phase 21)
  - New event: `embymedia_library_updated` - Fires when items are added/updated/removed from libraries
  - New event: `embymedia_user_data_changed` - Fires when favorites, played status, or ratings change
  - New event: `embymedia_notification` - Forwards Emby server notifications to Home Assistant
  - New event: `embymedia_user_changed` - Fires when user accounts are updated or deleted
  - TypedDicts: `EmbyLibraryChangedData`, `EmbyUserDataChangedData`, `EmbyNotificationData`, `EmbyUserChangedData`
  - Automatic browse cache invalidation on library changes
  - Debounced library coordinator refresh (5-second delay) on library changes
  - Documentation with example automations in docs/AUTOMATIONS.md

- **Server Administration** (Phase 20)
  - New service: `embymedia.run_scheduled_task` - Trigger any scheduled task on demand
  - New service: `embymedia.restart_server` - Restart the Emby server (requires admin)
  - New service: `embymedia.shutdown_server` - Shutdown the Emby server (requires admin)
  - New sensor: `sensor.{server}_plugins` - Plugin count with full plugin list in attributes
  - New button: `button.{server}_run_library_scan` - Quick trigger library scan
  - API methods: `async_run_scheduled_task`, `async_restart_server`, `async_shutdown_server`, `async_get_plugins`

- **Collection Management** (Phase 19)
  - New service: `embymedia.create_collection` - Create new collections (BoxSets)
  - New service: `embymedia.add_to_collection` - Add items to existing collections
  - New service: `embymedia.remove_from_collection` - Remove items from collections
  - New sensor: `sensor.{server}_collections` - Shows collection count (requires user_id configuration)
  - API methods: `async_create_collection`, `async_add_to_collection`, `async_remove_from_collection`, `async_get_collections`
  - TypedDicts for collection API type safety

- **Person Browsing** (Phase 19)
  - Browse actors, directors, writers in movie libraries
  - View person filmography - see all movies/shows featuring a person
  - Person images displayed when available
  - API methods: `async_get_persons`, `async_get_person_items`

- **Tag Browsing** (Phase 19)
  - Browse user-defined tags in movie libraries
  - Filter movies by tag to view tagged content
  - API methods: `async_get_tags`, `async_get_items_by_tag`
  - Cached tag lists for improved performance

- **Enhanced Movie Library Categories**
  - "People" category added to movie library browser
  - "Tags" category added to movie library browser

- **User Activity & Statistics** (Phase 18)
  - New sensor: `sensor.{server}_last_activity` - Most recent server activity with details
  - New sensor: `sensor.{server}_connected_devices` - Count of registered devices with device list
  - Activity log API: `async_get_activity_log` - Fetch server activity entries
  - Device management API: `async_get_devices` - List all registered devices
  - TypedDicts for activity and device API type safety

- **Playlist Management** (Phase 17)
  - New service: `embymedia.create_playlist` - Create new Audio or Video playlists
  - New service: `embymedia.add_to_playlist` - Add items to existing playlists
  - New service: `embymedia.remove_from_playlist` - Remove items from playlists using PlaylistItemId
  - New sensor: `sensor.{server}_playlists` - Shows playlist count (requires user_id configuration)
  - TypedDicts for playlist API type safety

- **Code Quality & Performance Optimization** (Phase 22)
  - Parallel API calls for coordinator data fetching (discovery, server, library)
  - Streaming image proxy for efficient memory usage
  - Playback session memory cleanup to prevent memory leaks
  - BLAKE2b hash algorithm replacing MD5 for cache keys
  - Parallel service execution for non-dependent operations
  - Optimized web player detection with O(1) lookup
  - Configurable WebSocket session interval option
  - Enhanced error handling with specific exception types

- **Enhanced Playback** (Phase 14)
  - New service: `embymedia.clear_queue` - Clear playback queue
  - New attribute: `similar_items` - List of similar content on media players
  - Queue attributes: `queue_items`, `queue_position`, `queue_total`

### Changed
- Replaced MD5 with BLAKE2b for cache key hashing (improved security)
- Replaced broad exception handling with specific exception types
- Extracted letter browsing helper for code reuse
- Image proxy now uses streaming for better memory efficiency

### Technical
- 1649 tests with 100% code coverage
- Internationalization: 9 language translations added

## [0.3.0] - 2025-11-27

### Added
- **Dynamic Transcoding for Universal Media Playback** (Phase 13)
  - Universal audio endpoint for maximum device compatibility
  - Predefined device profiles for different playback scenarios
  - Transcoding session management with proper lifecycle handling
  - PlaybackInfo API methods for querying playback capabilities and stream URLs
  - Device ID generation functions for transcoding sessions

### Fixed
- **Audio-only Device Compatibility**: Media browsing now uses MIME type prefixes (`audio/`, `video/`) instead of MediaType constants, allowing audio-only Cast devices (Sonos, etc.) to see and play music content
- **Audio Playback**: Fixed empty UserId in universal audio endpoint causing playback failures

### Technical
- Added `homeassistant-stubs` to test dependencies for consistent mypy behavior between local development and CI
- 1102 tests with 100% code coverage

## [0.2.2] - 2025-11-27

### Fixed
- **Artist Browsing**: Clicking on an artist in the media browser now correctly shows their albums instead of attempting playback
  - Added `musicartist` and `musicalbum` to expandable types
  - Added artist content type handler to fetch albums via `async_get_artist_albums` API

## [0.2.1] - 2025-11-27

### Added
- **Studio/Network Browsing** - Browse movies and TV shows by studio or network
  - Movies > Studio shows list of production studios
  - TV Shows > Studio shows list of networks/studios
- **Enhanced Music Library Browsing** - Full category navigation for music libraries
  - Artists A-Z letter navigation
  - Albums A-Z letter navigation
  - Genre browsing with albums
  - Playlist browsing

### Fixed
- Fixed "Unknown error" when browsing movies by year in media source
- Fixed "Unknown error" when browsing TV shows by year in media source
- Fixed year browsing when Emby `/Years` endpoint fails (automatic fallback to extracting years from items)
- Improved error handling in media source browsing with descriptive messages
- Synchronized media source browsing features with media player entity browsing

## [0.2.0] - 2025-11-26

### Added
- **Sensor Platform** (Phase 12)
  - Binary sensors for server status:
    - `binary_sensor.{server}_connected` - Server connectivity
    - `binary_sensor.{server}_pending_restart` - Restart required indicator
    - `binary_sensor.{server}_update_available` - Update availability
    - `binary_sensor.{server}_library_scan_active` - Library scan status with progress attribute
  - Numeric sensors for server statistics:
    - `sensor.{server}_server_version` - Server version (diagnostic)
    - `sensor.{server}_running_tasks` - Active scheduled tasks count
    - `sensor.{server}_active_sessions` - Connected client count
  - Library count sensors (1-hour polling):
    - `sensor.{server}_movies` - Total movie count
    - `sensor.{server}_tv_shows` - Total TV series count
    - `sensor.{server}_episodes` - Total episode count
    - `sensor.{server}_songs` - Total song count
    - `sensor.{server}_albums` - Total album count
    - `sensor.{server}_artists` - Total artist count
  - New coordinators for sensor data:
    - `EmbyServerCoordinator` - Server info polling (5-minute interval)
    - `EmbyLibraryCoordinator` - Library counts polling (1-hour interval)
  - `EmbyRuntimeData` class to manage multiple coordinators

### Technical
- 941 tests with 100% code coverage
- TypedDict definitions for sensor API responses
- Backward-compatible runtime_data structure

### Fixed
- Release workflow permissions for uploading zip artifacts

## [0.1.0] - 2025-11-26

### Added
- Initial release of Home Assistant Emby Media integration
- Media player entities for Emby clients with full playback control
- Real-time state updates via WebSocket connection
- Media browsing support for all Emby library types:
  - Movies (A-Z, year, decade, genre, collections)
  - TV Shows (A-Z, year, decade, genre, seasons, episodes)
  - Music (artists, albums, genres, playlists)
  - Live TV channels
  - Playlists and collections
- Media source provider for cross-player playback
- Voice assistant search support (`async_search_media`)
- Image proxy for authenticated media artwork
- Config flow with connection validation
- Options flow for customizable settings:
  - Scan interval (5-300 seconds)
  - WebSocket enable/disable
  - Device filtering
  - Transcoding options (direct play, container, bitrate)
  - Entity name prefix toggles ("Emby" prefix per entity type)
- Multiple users support with per-user libraries
- Custom services:
  - `embymedia.send_message` - Display notifications on clients
  - `embymedia.send_command` - Send navigation commands
  - `embymedia.mark_played` / `embymedia.mark_unplayed` - Manage watch status
  - `embymedia.add_favorite` / `embymedia.remove_favorite` - Manage favorites
  - `embymedia.refresh_library` - Trigger library scan
- Device triggers for automation:
  - Playback started/stopped/paused/resumed
  - Session connected/disconnected
  - Media changed
- Diagnostics download for troubleshooting
- Remote entity for navigation commands
- Notify entity for on-screen messages
- Button entity for server actions

### Technical
- Python 3.13+ support (Home Assistant 2025.x)
- 100% test coverage with 815+ tests
- Strict type checking with mypy
- TypedDict definitions for all API responses
- WebSocket with exponential backoff reconnection
- Browse cache with LRU + TTL for performance
- Graceful degradation on partial failures

[Unreleased]: https://github.com/troykelly/homeassistant-emby/compare/v0.4.1...HEAD
[0.4.1]: https://github.com/troykelly/homeassistant-emby/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/troykelly/homeassistant-emby/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/troykelly/homeassistant-emby/compare/v0.2.2...v0.3.0
[0.2.2]: https://github.com/troykelly/homeassistant-emby/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/troykelly/homeassistant-emby/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/troykelly/homeassistant-emby/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/troykelly/homeassistant-emby/releases/tag/v0.1.0
