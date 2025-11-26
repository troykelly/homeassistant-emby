# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/troykelly/homeassistant-emby/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/troykelly/homeassistant-emby/releases/tag/v0.1.0
