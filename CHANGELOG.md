# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/troykelly/homeassistant-emby/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/troykelly/homeassistant-emby/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/troykelly/homeassistant-emby/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/troykelly/homeassistant-emby/releases/tag/v0.1.0
