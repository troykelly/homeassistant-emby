# Emby Media for Home Assistant

[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/troykelly/homeassistant-emby)](https://github.com/troykelly/homeassistant-emby/releases)
[![License](https://img.shields.io/github/license/troykelly/homeassistant-emby)](LICENSE)
[![Tests](https://img.shields.io/github/actions/workflow/status/troykelly/homeassistant-emby/test.yml?label=tests)](https://github.com/troykelly/homeassistant-emby/actions)
[![Coverage](https://img.shields.io/codecov/c/github/troykelly/homeassistant-emby)](https://codecov.io/gh/troykelly/homeassistant-emby)

A modern Home Assistant integration for [Emby Media Server](https://emby.media/) with full playback control, media browsing, real-time updates, and voice assistant support.

<p align="center">
  <img src="https://emby.media/resources/logowhite_1881.png" alt="Emby Logo" width="200">
</p>

## ✨ Features

| Feature | Description |
|---------|-------------|
| **🎬 Media Players** | Automatic entities for all connected Emby clients |
| **⏯️ Playback Control** | Play, pause, stop, seek, volume, skip tracks |
| **📺 Remote Control** | Send navigation commands to Emby clients |
| **💬 Notifications** | Display messages on Emby client screens |
| **📚 Media Browsing** | Browse your entire library from Home Assistant |
| **🔊 Media Source** | Play Emby content on ANY Home Assistant media player |
| **⚡ Real-Time Updates** | WebSocket connection for instant state sync |
| **🎙️ Voice Control** | Search and play media with Google/Alexa |
| **🏠 Automations** | Device triggers for playback events |
| **📊 Server Sensors** | Monitor server status, library counts, and activity |
| **📡 Live TV & DVR** | Schedule recordings, manage timers, monitor DVR status |

## 📋 Requirements

- **Home Assistant** 2025.11.3 or later
- **Emby Server** 4.9.1.90 or later
- **Emby API Key** (see [Getting an API Key](#getting-an-api-key))

## 🚀 Installation

### Option 1: HACS (Recommended)

1. Open **HACS** in Home Assistant
2. Click the three dots menu (⋮) → **Custom repositories**
3. Add `https://github.com/troykelly/homeassistant-emby` as an **Integration**
4. Search for **"Emby Media"** and click **Download**
5. **Restart Home Assistant**
6. Continue to [Configuration](#-configuration)

### Option 2: Manual Installation

1. Download the [latest release](https://github.com/troykelly/homeassistant-emby/releases)
2. Extract and copy `custom_components/embymedia` to your `config/custom_components/` folder
3. **Restart Home Assistant**
4. Continue to [Configuration](#-configuration)

<details>
<summary>📁 Your folder structure should look like this</summary>

```
config/
├── configuration.yaml
├── custom_components/
│   └── embymedia/
│       ├── __init__.py
│       ├── manifest.json
│       ├── config_flow.py
│       └── ... (other files)
```

</details>

## ⚙️ Configuration

### Step 1: Get Your API Key

1. Open your **Emby Server Dashboard** (usually `http://your-server:8096`)
2. Go to **⚙️ Settings** → **Advanced** → **API Keys**
3. Click **+ New API Key**
4. Name it `Home Assistant` and click **OK**
5. **Copy the generated key** (you'll need it next)

<details>
<summary>📸 Screenshot: Where to find API Keys</summary>

Navigate to: Dashboard → Settings (gear icon) → Advanced → API Keys

</details>

### Step 2: Add the Integration

1. In Home Assistant, go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for **"Emby Media"**
4. Enter your connection details:

| Field | Description | Example |
|-------|-------------|---------|
| **Host** | Emby server hostname or IP | `192.168.1.100` or `emby.local` |
| **Port** | Server port | `8096` (HTTP) or `8920` (HTTPS) |
| **Use SSL** | Enable for HTTPS | ☐ for HTTP, ☑ for HTTPS |
| **API Key** | Key from Step 1 | `abc123...` |
| **Verify SSL** | Validate certificate | Disable for self-signed certs |

5. Click **Submit** - entities will appear automatically!

### Optional: YAML Configuration

You can also configure via `configuration.yaml`:

```yaml
embymedia:
  host: emby.local
  api_key: !secret emby_api_key
  port: 8096
  ssl: false
```

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for all options.

## 🎮 Usage

### Media Player Entities

Each Emby client automatically creates a media player entity with an "Emby" prefix:

- `media_player.emby_living_room_tv`
- `media_player.emby_bedroom_roku`
- `media_player.emby_samsung_tv`

> **Note**: Device names are prefixed with "Emby" by default. You can disable this per entity type in integration options.

**Lovelace Card Example:**
```yaml
type: media-control
entity: media_player.emby_living_room_tv
```

### Browsing Media

1. Click any Emby media player entity
2. Click **"Browse Media"**
3. Navigate: **Libraries** → **Categories** → **Content**

**Available categories:**
- 🎬 **Movies**: A-Z, Year, Decade, Genre, Studio, Collections
- 📺 **TV Shows**: A-Z, Year, Decade, Genre, Studio → Series → Season → Episode
- 🎵 **Music**: Artists A-Z, Albums A-Z, Genres, Playlists
- 📡 **Live TV**: Channel listing

### Voice Commands

Use with Google Home, Alexa, or other voice assistants:

- *"Hey Google, play The Office on Living Room TV"*
- *"Alexa, pause the TV"*
- *"Hey Google, play jazz music in the kitchen"*

### Remote Control

Send navigation commands to Emby clients:

```yaml
service: remote.send_command
target:
  entity_id: remote.emby_living_room_tv
data:
  command: Select  # or: MoveUp, MoveDown, Back, GoHome
```

### Notifications

Display messages on Emby client screens:

```yaml
service: notify.send_message
target:
  entity_id: notify.emby_living_room_tv
data:
  title: "Dinner Time!"
  message: "Food is ready 🍕"
```

## 🤖 Automation Examples

<details>
<summary><b>🌙 Dim lights when movie starts</b></summary>

```yaml
automation:
  - alias: "Dim lights for movies"
    trigger:
      - platform: state
        entity_id: media_player.emby_living_room_tv
        to: "playing"
    condition:
      - condition: template
        value_template: "{{ state_attr('media_player.emby_living_room_tv', 'media_content_type') == 'movie' }}"
    action:
      - service: light.turn_on
        target:
          entity_id: light.living_room
        data:
          brightness_pct: 10
          transition: 3
```
</details>

<details>
<summary><b>🔔 Pause media when doorbell rings</b></summary>

```yaml
automation:
  - alias: "Pause for doorbell"
    trigger:
      - platform: state
        entity_id: binary_sensor.doorbell
        to: "on"
    action:
      - service: media_player.media_pause
        target:
          entity_id: media_player.emby_living_room_tv
      - service: notify.send_message
        target:
          entity_id: notify.emby_living_room_tv
        data:
          title: "Doorbell"
          message: "Someone is at the door"
```
</details>

<details>
<summary><b>📺 Send TV notification when laundry is done</b></summary>

```yaml
automation:
  - alias: "Laundry notification"
    trigger:
      - platform: state
        entity_id: sensor.washer_status
        to: "complete"
    action:
      - service: notify.send_message
        target:
          entity_id: notify.emby_living_room_tv
        data:
          title: "Laundry"
          message: "Washing machine is done!"
```
</details>

<details>
<summary><b>⏰ Nightly library refresh</b></summary>

```yaml
automation:
  - alias: "Refresh Emby library at 3am"
    trigger:
      - platform: time
        at: "03:00:00"
    action:
      - service: button.press
        target:
          entity_id: button.emby_server_refresh_library
```
</details>

See [docs/AUTOMATIONS.md](docs/AUTOMATIONS.md) for more examples.

## 📊 Server & Library Sensors

The integration provides sensors to monitor your Emby server:

### Binary Sensors

| Sensor | Description |
|--------|-------------|
| `binary_sensor.{server}_connected` | Server connectivity status |
| `binary_sensor.{server}_pending_restart` | Server needs restart |
| `binary_sensor.{server}_update_available` | Server update available |
| `binary_sensor.{server}_library_scan_active` | Library scan in progress (with progress % attribute) |

### Numeric Sensors

| Sensor | Description |
|--------|-------------|
| `sensor.{server}_server_version` | Current server version |
| `sensor.{server}_running_tasks` | Number of running scheduled tasks |
| `sensor.{server}_active_sessions` | Number of connected clients |
| `sensor.{server}_movies` | Total movies in library |
| `sensor.{server}_tv_shows` | Total TV series in library |
| `sensor.{server}_episodes` | Total episodes in library |
| `sensor.{server}_songs` | Total songs in library |
| `sensor.{server}_albums` | Total albums in library |
| `sensor.{server}_artists` | Total artists in library |

<details>
<summary><b>📈 Sensor-based automation example</b></summary>

```yaml
automation:
  - alias: "Alert when library scan completes"
    trigger:
      - platform: state
        entity_id: binary_sensor.media_library_scan_active
        from: "on"
        to: "off"
    action:
      - service: notify.mobile_app
        data:
          title: "Emby"
          message: "Library scan completed!"
```
</details>

## 📺 Live TV & DVR

The integration provides comprehensive Live TV support for Emby servers with Live TV configured.

### Live TV Sensors

| Sensor | Description |
|--------|-------------|
| `binary_sensor.{server}_live_tv_enabled` | Live TV enabled status (attributes: `tuner_count`, `active_recordings`) |
| `sensor.{server}_recordings` | Total recordings count |
| `sensor.{server}_active_recordings` | Currently recording count |
| `sensor.{server}_scheduled_recordings` | Upcoming scheduled recordings |
| `sensor.{server}_series_recording_rules` | Active series timer count |

### Recording Management Services

#### Schedule a Recording

Schedule a one-time recording of a program:

```yaml
service: embymedia.schedule_recording
target:
  entity_id: media_player.emby_living_room_tv
data:
  program_id: "142098"
  pre_padding_seconds: 60   # Start 1 minute early (optional)
  post_padding_seconds: 120 # End 2 minutes late (optional)
```

#### Cancel a Recording

Cancel a scheduled recording timer:

```yaml
service: embymedia.cancel_recording
target:
  entity_id: media_player.emby_living_room_tv
data:
  timer_id: "abc123def456"
```

#### Cancel a Series Timer

Cancel a series recording rule (stops all future recordings):

```yaml
service: embymedia.cancel_series_timer
target:
  entity_id: media_player.emby_living_room_tv
data:
  series_timer_id: "series123"
```

<details>
<summary><b>📺 Live TV automation example</b></summary>

```yaml
automation:
  - alias: "Notify when recording starts"
    trigger:
      - platform: numeric_state
        entity_id: sensor.media_active_recordings
        above: 0
    action:
      - service: notify.mobile_app
        data:
          title: "Emby Recording"
          message: "A recording has started"
```
</details>

## 🎵 Playlist Management

Create and manage Emby playlists directly from Home Assistant.

### Create a Playlist

```yaml
service: embymedia.create_playlist
target:
  entity_id: media_player.emby_living_room_tv
data:
  name: "Road Trip Mix"
  media_type: "Audio"
  user_id: "your_user_id"
  item_ids:  # Optional - initial items
    - "abc123"
    - "def456"
```

### Add Items to Playlist

```yaml
service: embymedia.add_to_playlist
target:
  entity_id: media_player.emby_living_room_tv
data:
  playlist_id: "playlist123"
  item_ids:
    - "ghi789"
    - "jkl012"
  user_id: "your_user_id"
```

### Remove Items from Playlist

> **Important:** Use `playlist_item_ids` (NOT media item IDs). Get these from the playlist when browsing.

```yaml
service: embymedia.remove_from_playlist
target:
  entity_id: media_player.emby_living_room_tv
data:
  playlist_id: "playlist123"
  playlist_item_ids:
    - "1"
    - "2"
```

### Playlist Sensor

When a user is configured, a playlist count sensor is available:

- `sensor.{server}_playlists` - Total playlists count

**Notes:**
- Playlists can contain either Audio OR Video items, not mixed
- Playlists are user-specific - each user has their own playlists

## 🔧 Advanced Options

Configure in **Settings** → **Devices & Services** → **Emby Media** → **Configure**:

| Option | Default | Description |
|--------|---------|-------------|
| Scan Interval | 10s | Polling frequency (5-300 seconds) |
| Enable WebSocket | ✓ | Real-time updates (recommended) |
| Ignored Devices | — | Hide specific clients (comma-separated) |
| Ignore Web Players | ✗ | Hide browser-based players |
| Direct Play | ✓ | Try direct play before transcoding |
| Video Container | mp4 | Transcode format (mp4, mkv, webm) |

## 🐛 Troubleshooting

### Common Issues

<details>
<summary><b>❌ Connection Failed</b></summary>

1. **Verify Emby is running**: Open `http://your-server:8096` in a browser
2. **Check firewall**: Ensure port 8096 (or your port) is open
3. **Try IP instead of hostname**: Use `192.168.1.x` instead of `emby.local`
4. **For HTTPS**: Try disabling "Verify SSL" if using self-signed certificates

</details>

<details>
<summary><b>🔑 Invalid API Key</b></summary>

1. Generate a **new** API key in Emby Dashboard
2. Ensure no extra spaces when copying
3. Check the key hasn't been revoked

</details>

<details>
<summary><b>👻 No Entities Appearing</b></summary>

1. Ensure an Emby client is **actively connected** (open Emby on a device)
2. Check if the device supports **remote control** (not all clients do)
3. Verify the device isn't in the **Ignored Devices** list
4. Check Home Assistant logs for errors

</details>

<details>
<summary><b>⚡ WebSocket Keeps Disconnecting</b></summary>

1. Check network stability between HA and Emby
2. Try disabling WebSocket in options (uses polling instead)
3. Ensure no proxy is interfering with WebSocket connections

</details>

### Getting Diagnostics

1. Go to **Settings** → **Devices & Services**
2. Find **Emby Media** and click the three dots (⋮)
3. Click **Download Diagnostics**
4. Share the downloaded file when reporting issues (API keys are automatically redacted)

### Need Help?

- 📖 [Full Troubleshooting Guide](docs/TROUBLESHOOTING.md)
- 🐛 [Report a Bug](https://github.com/troykelly/homeassistant-emby/issues/new?template=bug_report.md)
- 💡 [Request a Feature](https://github.com/troykelly/homeassistant-emby/issues/new?template=feature_request.md)

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Installation Guide](docs/INSTALLATION.md) | Detailed setup instructions |
| [Configuration Reference](docs/CONFIGURATION.md) | All options explained |
| [Automation Examples](docs/AUTOMATIONS.md) | Ready-to-use automations |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common issues and solutions |
| [Services Reference](docs/SERVICES.md) | Available service calls |
| [Changelog](CHANGELOG.md) | Version history |

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.

## 🙏 Acknowledgments

- [Home Assistant](https://www.home-assistant.io/) - The amazing smart home platform
- [Emby](https://emby.media/) - Media server software
- [pyEmby](https://github.com/mezz64/pyEmby) - Reference implementation

---

<p align="center">
  Made with ❤️ for the Home Assistant community
</p>
