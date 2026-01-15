# Integration Comparison Matrix

## Home Assistant Media Server Integrations

This document provides a comprehensive comparison between this custom Emby Media integration (`embymedia`) and the official Home Assistant core integrations for Emby and Plex.

**Last Updated:** January 2026

**Sources:**

- [Official Emby Integration](https://www.home-assistant.io/integrations/emby/) (HA Core)
- [Official Plex Integration](https://www.home-assistant.io/integrations/plex/) (HA Core)
- This repository's source code

---

## Executive Summary

| Aspect               | embymedia (This)   | Official Emby | Official Plex |
| -------------------- | ------------------ | ------------- | ------------- |
| **Status**           | Active Development | Legacy        | Active        |
| **Entity Platforms** | 6                  | 1             | 4             |
| **Services**         | 20+                | 0             | 1             |
| **Config Flow**      | ✅ Full            | ❌ YAML Only  | ✅ Full       |
| **WebSocket**        | ✅ Real-time       | ❌ Polling    | ✅ Real-time  |
| **Voice Assist**     | ✅ search_media    | ❌            | ❌            |
| **Quality**          | Modern (2025)      | Legacy        | Modern        |

---

## Configuration & Setup

| Feature                    | embymedia        | Official Emby | Official Plex          |
| -------------------------- | ---------------- | ------------- | ---------------------- |
| **Config Flow (UI Setup)** | ✅ Full          | ❌ YAML only  | ✅ Full                |
| **Options Flow**           | ✅ Extensive     | ❌            | ✅ Limited             |
| **Reauth Flow**            | ✅               | ❌            | ✅                     |
| **SSDP Discovery**         | ❌               | ❌            | ❌                     |
| **Zeroconf Discovery**     | ❌               | ❌            | ✅                     |
| **GDM Discovery**          | N/A              | N/A           | ✅                     |
| **OAuth Authentication**   | ❌ (API Key)     | ❌ (API Key)  | ✅ (plex.tv)           |
| **Multi-Server Support**   | ✅               | ⚠️ Manual     | ✅                     |
| **Multi-User Support**     | ✅ Per-user data | ❌            | ✅ Per-user monitoring |
| **SSL/TLS Support**        | ✅ Configurable  | ✅ Basic      | ✅ Full                |
| **Verify SSL Option**      | ✅               | ❌            | ✅                     |

### Configuration Options Comparison

| Option                | embymedia       | Official Emby | Official Plex |
| --------------------- | --------------- | ------------- | ------------- |
| Host/Port/API Key     | ✅              | ✅            | ✅            |
| Polling Interval      | ✅ 5-300s       | ❌ Fixed      | ❌ Fixed      |
| Library Scan Interval | ✅ 1-24h        | ❌            | ❌            |
| WebSocket Toggle      | ✅              | N/A           | ❌ Always on  |
| Ignored Devices       | ✅              | ❌            | ❌            |
| Ignore Web Players    | ✅              | ❌            | ✅            |
| Entity Prefix Control | ✅ Per-platform | ❌            | ❌            |
| Transcoding Settings  | ✅ Full         | ❌            | ❌            |
| Monitored Users       | ✅              | ❌            | ✅            |
| Episode Artwork       | N/A             | N/A           | ✅            |

---

## Entity Platforms

| Platform          | embymedia        | Official Emby  | Official Plex   |
| ----------------- | ---------------- | -------------- | --------------- |
| **Media Player**  | ✅ Per-session   | ✅ Per-session | ✅ Per-client   |
| **Sensor**        | ✅ 15+ types     | ❌             | ✅ 2 types      |
| **Binary Sensor** | ✅ 5 types       | ❌             | ❌              |
| **Remote**        | ✅ Navigation    | ❌             | ❌              |
| **Button**        | ✅ Multiple      | ❌             | ✅ Scan clients |
| **Notify**        | ✅ On-screen     | ❌             | ❌              |
| **Image**         | ✅ Discovery art | ❌             | ❌              |
| **Update**        | ❌               | ❌             | ✅              |

### Sensor Types Detail

| Sensor Type       | embymedia | Official Emby | Official Plex         |
| ----------------- | --------- | ------------- | --------------------- |
| Active Sessions   | ✅        | ❌            | ✅ ("watching")       |
| Movie Count       | ✅        | ❌            | ✅                    |
| Series Count      | ✅        | ❌            | ✅ (as shows)         |
| Episode Count     | ✅        | ❌            | ✅                    |
| Song Count        | ✅        | ❌            | ❌                    |
| Album Count       | ✅        | ❌            | ✅                    |
| Artist Count      | ✅        | ❌            | ✅                    |
| Collection Count  | ✅        | ❌            | ❌                    |
| Playlist Count    | ✅        | ❌            | ❌                    |
| Server Version    | ✅        | ❌            | ❌ (in Update entity) |
| Running Tasks     | ✅        | ❌            | ❌                    |
| Recording Count   | ✅        | ❌            | ❌                    |
| Connected Devices | ✅        | ❌            | ❌                    |
| Plugin Count      | ✅        | ❌            | ❌                    |
| Watch Statistics  | ✅        | ❌            | ❌                    |
| Last Added Title  | ❌        | ❌            | ✅                    |

### Binary Sensor Types

| Binary Sensor       | embymedia | Official Emby | Official Plex    |
| ------------------- | --------- | ------------- | ---------------- |
| Server Connected    | ✅        | ❌            | ❌               |
| Pending Restart     | ✅        | ❌            | ❌               |
| Update Available    | ✅        | ❌            | ❌ (uses Update) |
| Library Scan Active | ✅        | ❌            | ❌               |
| Live TV Enabled     | ✅        | ❌            | N/A              |

---

## Media Player Capabilities

### Playback Control

| Feature        | embymedia | Official Emby | Official Plex |
| -------------- | --------- | ------------- | ------------- |
| Play           | ✅        | ✅            | ✅            |
| Pause          | ✅        | ✅            | ✅            |
| Stop           | ✅        | ✅            | ✅            |
| Next Track     | ✅        | ✅            | ✅            |
| Previous Track | ✅        | ✅            | ✅            |
| Seek           | ✅        | ✅            | ✅            |
| Volume Set     | ✅        | ❌            | ✅            |
| Volume Mute    | ✅        | ❌            | ⚠️ Simulated  |
| Shuffle Set    | ✅        | ❌            | ❌            |
| Repeat Set     | ✅        | ❌            | ❌            |

### Media Selection

| Feature        | embymedia       | Official Emby | Official Plex |
| -------------- | --------------- | ------------- | ------------- |
| Play Media     | ✅              | ❌            | ✅            |
| Browse Media   | ✅              | ❌            | ✅            |
| Search Media   | ✅ Voice Assist | ❌            | ❌            |
| Media Enqueue  | ✅              | ❌            | ❌            |
| Clear Playlist | ✅              | ❌            | ❌            |

### Media Information

| Property              | embymedia | Official Emby | Official Plex |
| --------------------- | --------- | ------------- | ------------- |
| Title                 | ✅        | ✅            | ✅            |
| Duration              | ✅        | ✅            | ✅            |
| Position              | ✅        | ✅            | ✅            |
| Artwork               | ✅        | ✅            | ✅            |
| Series/Season/Episode | ✅        | ✅            | ✅            |
| Album/Artist          | ✅        | ✅            | ✅            |
| Content ID            | ✅        | ✅            | ✅            |
| User/App Name         | ✅        | ✅            | ✅            |

### Supported Media Types

| Media Type   | embymedia | Official Emby | Official Plex |
| ------------ | --------- | ------------- | ------------- |
| Movies       | ✅        | ✅            | ✅            |
| TV Episodes  | ✅        | ✅            | ✅            |
| Music Tracks | ✅        | ✅            | ✅            |
| Music Videos | ✅        | ✅            | ❌            |
| Photos       | ✅        | ❌            | ✅            |
| Live TV      | ✅        | ✅            | N/A           |
| Trailers     | ✅        | ✅            | ✅ (clips)    |
| Playlists    | ✅        | ❌            | ✅            |

---

## Services

### Playback Services

| Service          | embymedia | Official Emby | Official Plex |
| ---------------- | --------- | ------------- | ------------- |
| Send Message     | ✅        | ❌            | ❌            |
| Send Command     | ✅        | ❌            | ❌            |
| Mark Played      | ✅        | ❌            | ❌            |
| Mark Unplayed    | ✅        | ❌            | ❌            |
| Add Favorite     | ✅        | ❌            | ❌            |
| Remove Favorite  | ✅        | ❌            | ❌            |
| Play Instant Mix | ✅        | ❌            | ❌            |
| Play Similar     | ✅        | ❌            | ❌            |
| Clear Queue      | ✅        | ❌            | ❌            |

### Library Services

| Service                | embymedia | Official Emby | Official Plex |
| ---------------------- | --------- | ------------- | ------------- |
| Refresh Library        | ✅        | ❌            | ✅            |
| Create Playlist        | ✅        | ❌            | ❌            |
| Add to Playlist        | ✅        | ❌            | ❌            |
| Remove from Playlist   | ✅        | ❌            | ❌            |
| Create Collection      | ✅        | ❌            | ❌            |
| Add to Collection      | ✅        | ❌            | ❌            |
| Remove from Collection | ✅        | ❌            | ❌            |

### Live TV Services

| Service             | embymedia | Official Emby | Official Plex |
| ------------------- | --------- | ------------- | ------------- |
| Schedule Recording  | ✅        | ❌            | N/A           |
| Cancel Recording    | ✅        | ❌            | N/A           |
| Cancel Series Timer | ✅        | ❌            | N/A           |

### Server Administration

| Service            | embymedia | Official Emby | Official Plex |
| ------------------ | --------- | ------------- | ------------- |
| Run Scheduled Task | ✅        | ❌            | ❌            |
| Restart Server     | ✅        | ❌            | ❌            |
| Shutdown Server    | ✅        | ❌            | ❌            |

---

## Real-Time Updates

| Feature               | embymedia              | Official Emby | Official Plex |
| --------------------- | ---------------------- | ------------- | ------------- |
| WebSocket Support     | ✅ Full                | ❌            | ✅ Limited    |
| Session Updates       | ✅ Real-time           | Polling       | ✅ Real-time  |
| Library Changes       | ✅ Real-time           | ❌            | ✅ Signals    |
| User Data Changes     | ✅ Real-time           | ❌            | ❌            |
| Auto-Reconnection     | ✅ Exponential backoff | N/A           | ✅            |
| Adaptive Polling      | ✅ WS-aware            | ❌            | ❌            |
| Configurable Interval | ✅ 500-10000ms         | ❌            | ❌            |

---

## Media Browsing

| Feature                 | embymedia | Official Emby | Official Plex |
| ----------------------- | --------- | ------------- | ------------- |
| Browse Media Support    | ✅        | ❌            | ✅            |
| Hierarchical Navigation | ✅        | ❌            | ✅            |
| Libraries               | ✅        | ❌            | ✅            |
| Genres                  | ✅        | ❌            | ❌            |
| Artists/Albums          | ✅        | ❌            | ✅            |
| Series/Seasons          | ✅        | ❌            | ✅            |
| Playlists               | ✅        | ❌            | ✅            |
| Collections/BoxSets     | ✅        | ❌            | ❌            |
| Recommendations         | ✅        | ❌            | ✅ (Hubs)     |

---

## Voice Assistant Integration

| Feature                 | embymedia | Official Emby | Official Plex |
| ----------------------- | --------- | ------------- | ------------- |
| HA Assist Support       | ✅        | ❌            | ❌            |
| search_media Method     | ✅        | ❌            | ❌            |
| Natural Language Search | ✅        | ❌            | ❌            |
| Play by Voice           | ✅        | ❌            | ❌            |

---

## Device Automation

| Feature                | embymedia  | Official Emby | Official Plex |
| ---------------------- | ---------- | ------------- | ------------- |
| **Device Triggers**    | ✅ 7 types | ❌            | ❌            |
| - playback_started     | ✅         | ❌            | ❌            |
| - playback_stopped     | ✅         | ❌            | ❌            |
| - playback_paused      | ✅         | ❌            | ❌            |
| - playback_resumed     | ✅         | ❌            | ❌            |
| - media_changed        | ✅         | ❌            | ❌            |
| - session_connected    | ✅         | ❌            | ❌            |
| - session_disconnected | ✅         | ❌            | ❌            |
| **Device Conditions**  | ✅ 5 types | ❌            | ❌            |
| - is_playing           | ✅         | ❌            | ❌            |
| - is_paused            | ✅         | ❌            | ❌            |
| - is_idle              | ✅         | ❌            | ❌            |
| - is_off               | ✅         | ❌            | ❌            |
| - has_media            | ✅         | ❌            | ❌            |

---

## Remote Entity (Navigation)

| Command                         | embymedia | Official Emby | Official Plex |
| ------------------------------- | --------- | ------------- | ------------- |
| Navigation (Up/Down/Left/Right) | ✅        | ❌            | ❌            |
| Page Up/Down                    | ✅        | ❌            | ❌            |
| Select/Back                     | ✅        | ❌            | ❌            |
| Home/Settings                   | ✅        | ❌            | ❌            |
| Context Menu                    | ✅        | ❌            | ❌            |
| OSD Menu                        | ✅        | ❌            | ❌            |
| Volume Keys                     | ✅        | ❌            | ❌            |
| Audio/Subtitle Index            | ✅        | ❌            | ❌            |
| Send String                     | ✅        | ❌            | ❌            |
| Screenshot                      | ✅        | ❌            | ❌            |

---

## Discovery & Recommendations

| Feature            | embymedia         | Official Emby | Official Plex  |
| ------------------ | ----------------- | ------------- | -------------- |
| Next Up Episodes   | ✅ Sensor + Image | ❌            | ❌             |
| Continue Watching  | ✅ Sensor + Image | ❌            | ❌             |
| Recently Added     | ✅ Sensor + Image | ❌            | ✅ (attribute) |
| Suggestions        | ✅ Sensor + Image | ❌            | ❌             |
| Per-User Discovery | ✅                | ❌            | ❌             |

---

## Transcoding & Streaming

| Feature                  | embymedia        | Official Emby | Official Plex |
| ------------------------ | ---------------- | ------------- | ------------- |
| Direct Play Preference   | ✅ Configurable  | N/A           | N/A           |
| Transcode Profiles       | ✅ 5 presets     | ❌            | ❌            |
| - Universal              | ✅               | ❌            | ❌            |
| - Chromecast             | ✅               | ❌            | ❌            |
| - Roku                   | ✅               | ❌            | ❌            |
| - Apple TV               | ✅               | ❌            | ❌            |
| - Audio Only             | ✅               | ❌            | ❌            |
| Max Bitrate Config       | ✅ Video + Audio | ❌            | ❌            |
| Container Selection      | ✅ mp4/mkv/webm  | ❌            | ❌            |
| HLS Streaming            | ✅               | ❌            | ❌            |
| PlaybackInfo Negotiation | ✅               | ❌            | ❌            |

---

## Live TV & DVR

| Feature                  | embymedia | Official Emby | Official Plex |
| ------------------------ | --------- | ------------- | ------------- |
| Live TV Channel Browse   | ✅        | ⚠️ Basic      | N/A           |
| Recording Management     | ✅        | ❌            | N/A           |
| Series Timers            | ✅        | ❌            | N/A           |
| Active Recordings Sensor | ✅        | ❌            | N/A           |
| Scheduled Timers Sensor  | ✅        | ❌            | N/A           |

---

## Architecture & Quality

| Aspect                | embymedia          | Official Emby    | Official Plex |
| --------------------- | ------------------ | ---------------- | ------------- |
| Quality Scale         | Modern             | Legacy           | Modern        |
| IoT Class             | local_push         | local_push       | local_push    |
| Integration Type      | Hub                | Platform         | Service       |
| Coordinators          | ✅ Multi (4 types) | ❌               | ⚠️ Limited    |
| Request Coalescing    | ✅                 | ❌               | ❌            |
| Browse Caching        | ✅                 | ❌               | ❌            |
| Diagnostics Export    | ✅                 | ❌               | ❌            |
| Device ID Persistence | ✅                 | ⚠️ Session-based | ✅            |

### Coordinator Types (embymedia)

| Coordinator | Purpose                       | Default Interval |
| ----------- | ----------------------------- | ---------------- |
| Session     | Active sessions/players       | 10 seconds       |
| Server      | Server status, tasks, plugins | 5 minutes        |
| Library     | Item counts, virtual folders  | 1 hour           |
| Discovery   | Next Up, Continue Watching    | 15 minutes       |

---

## Third-Party Integration

| Feature       | embymedia       | Official Emby | Official Plex |
| ------------- | --------------- | ------------- | ------------- |
| Sonos Support | ❌              | ❌            | ✅ Direct     |
| Cast Support  | ⚠️ Via profiles | ❌            | ✅            |
| Media Source  | ✅              | ❌            | ✅            |

---

## Error Handling & Resilience

| Feature               | embymedia          | Official Emby | Official Plex  |
| --------------------- | ------------------ | ------------- | -------------- |
| Connection Recovery   | ✅ Auto-reconnect  | Basic         | ✅             |
| Auth Error Handling   | ✅ Reauth flow     | ❌            | ✅ Reauth flow |
| SSL Error Handling    | ✅ Configurable    | Basic         | ✅             |
| Timeout Configuration | ✅                 | ❌            | ❌             |
| Health Checks         | ✅ 5-min intervals | ❌            | ❌             |
| Stale Session Cleanup | ✅                 | ❌            | ❌             |

---

## Summary

### embymedia (This Integration)

**Strengths:**

- Most comprehensive Emby integration available
- Full config flow with extensive options
- Real-time WebSocket updates with adaptive polling
- 6 entity platforms providing complete control
- 20+ services for playback, library, and server management
- Voice assistant (Assist) integration via search_media
- Device triggers and conditions for automations
- Remote entity for navigation control
- Discovery sensors with artwork (Next Up, Continue Watching)
- Transcoding profile support
- Live TV and DVR capabilities
- Modern architecture with multiple specialized coordinators

**Use When:**

- You want the most complete Emby experience in Home Assistant
- You need voice control via Home Assistant Assist
- You want device triggers for playback automations
- You need remote control navigation
- You want real-time notifications of library changes
- You use Live TV features

### Official Emby (HA Core)

**Strengths:**

- Part of Home Assistant Core (no custom component needed)
- Simple, lightweight implementation
- Basic playback control

**Limitations:**

- Legacy status, minimal maintenance
- YAML configuration only
- No config flow or options
- Single platform (media_player only)
- No volume, shuffle, repeat, browse, or search
- No services
- No sensors or binary sensors
- No WebSocket/real-time updates

**Use When:**

- You only need basic play/pause/stop functionality
- You prefer not to install custom components
- You have very simple automation needs

### Official Plex (HA Core)

**Strengths:**

- Part of Home Assistant Core
- Full config flow with OAuth
- Zeroconf auto-discovery
- WebSocket real-time updates
- Media browsing support
- Library sensors
- Update entity for server updates
- Sonos integration
- Good media information display

**Limitations:**

- No shuffle or repeat control
- No voice assistant integration
- No device triggers or conditions
- No remote entity for navigation
- No playlist/queue management
- Limited services (refresh_library only)
- Volume mute is simulated

**Use When:**

- You use Plex Media Server
- You want official HA Core support
- You need Sonos integration
- You want auto-discovery

---

## Feature Count Summary

| Category              | embymedia | Official Emby | Official Plex |
| --------------------- | --------- | ------------- | ------------- |
| Entity Platforms      | 6         | 1             | 4             |
| Media Player Features | 15        | 6             | 10            |
| Services              | 20+       | 0             | 1             |
| Sensor Types          | 15+       | 0             | 2             |
| Binary Sensors        | 5         | 0             | 0             |
| Device Triggers       | 7         | 0             | 0             |
| Device Conditions     | 5         | 0             | 0             |
| Remote Commands       | 15+       | 0             | 0             |
| Config Options        | 20+       | 4             | 5             |
| Coordinators          | 4         | 0             | 1             |

---

_This comparison was generated by analyzing the source code of all three integrations as of January 2026._
