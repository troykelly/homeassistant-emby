# Home Assistant Emby Integration

A custom Home Assistant integration for Emby Media Server providing full media player control, library browsing, and real-time updates via WebSocket.

## Features

- **Dynamic Media Players** - Automatic entity creation for all Emby clients
- **Full Playback Control** - Play, pause, stop, seek, volume, next/previous
- **Remote Control** - Send navigation commands (GoHome, Back, Select, arrows, etc.)
- **Notifications** - Send messages to Emby clients via standard notify platform
- **Server Actions** - Button entities for server operations (library refresh)
- **Media Browsing** - Navigate your entire Emby library from Home Assistant
- **Media Source Provider** - Play Emby content on any Home Assistant media player
- **Real-Time Updates** - WebSocket connection for instant state synchronization
- **Voice Assistant Support** - Search and play media with voice commands
- **Category Navigation** - Browse by A-Z, Year, Decade, Genre for Movies/TV/Music

## Requirements

- Home Assistant 2025.1 or later
- Emby Server 4.7.0 or later
- Emby API key (generated from Emby Dashboard)

## Installation

### HACS (Recommended)

1. Add this repository to HACS as a custom repository
2. Search for "Emby Media" in HACS
3. Install the integration
4. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/embymedia` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

This integration supports both UI-based configuration and YAML file configuration.

### UI Configuration (Recommended)

1. Go to **Settings** > **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Emby Media"
4. Enter your Emby server details:
   - **Host**: Emby server hostname or IP (e.g., `192.168.1.100` or `emby.local`)
   - **Port**: Emby server port (default: `8096`, or `8920` for HTTPS)
   - **Use SSL**: Enable for HTTPS connections
   - **API Key**: Generate from Emby Dashboard > Advanced > API Keys
   - **Verify SSL**: Disable only for self-signed certificates

### YAML Configuration

Add the following to your `configuration.yaml`:

```yaml
embymedia:
  host: emby.local
  api_key: !secret emby_api_key
  port: 8096              # Optional, default: 8096
  ssl: false              # Optional, default: false
  verify_ssl: true        # Optional, default: true
  scan_interval: 10       # Optional, default: 10 (seconds, 5-300)
  enable_websocket: true  # Optional, default: true
  ignored_devices: ""     # Optional, comma-separated device names
  ignore_web_players: false  # Optional, default: false - hide web browser sessions
  direct_play: true       # Optional, default: true
  video_container: mp4    # Optional, default: mp4 (mp4, mkv, webm)
  max_video_bitrate: 10000  # Optional, in kbps
  max_audio_bitrate: 320    # Optional, in kbps
```

**Required fields:** `host`, `api_key`

When configured via YAML, settings will automatically import into a config entry, so you can still modify options through the UI after initial setup.

### Getting an API Key

1. Open your Emby server dashboard
2. Navigate to **Advanced** > **API Keys**
3. Click **New API Key**
4. Enter a name (e.g., "Home Assistant")
5. Copy the generated key

## Options

After setup, configure optional settings via **Configure** on the integration:

| Option | Default | Description |
|--------|---------|-------------|
| Scan Interval | 10 seconds | How often to poll for updates (5-300 seconds) |
| Enable WebSocket | Yes | Use WebSocket for real-time updates |
| Ignored Devices | (empty) | Comma-separated device names to ignore |
| Ignore Web Players | No | Hide media players from web browser sessions |
| Direct Play | Yes | Try direct play before transcoding |
| Video Container | mp4 | Preferred format for transcoding (mp4, mkv, webm) |
| Max Video Bitrate | (unlimited) | Maximum video bitrate in kbps |
| Max Audio Bitrate | (unlimited) | Maximum audio bitrate in kbps |

## Usage

### Media Players

Each Emby client creates a media player entity named after the device (e.g., `media_player.living_room_tv`).

**Supported Features:**
- Play/Pause/Stop
- Seek
- Volume control
- Mute
- Next/Previous track

### Remote Control

Each Emby client also creates a remote entity (e.g., `remote.living_room_tv_remote`) for sending navigation commands.

**Supported Commands:**
- **Navigation**: `MoveUp`, `MoveDown`, `MoveLeft`, `MoveRight`, `PageUp`, `PageDown`
- **Selection**: `Select`, `Back`, `GoHome`, `GoToSettings`
- **Menus**: `ToggleContextMenu`, `ToggleOsdMenu`
- **Volume**: `VolumeUp`, `VolumeDown`, `Mute`, `Unmute`, `ToggleMute`

**Example:**
```yaml
service: remote.send_command
target:
  entity_id: remote.living_room_tv_remote
data:
  command:
    - MoveDown
    - MoveDown
    - Select
```

### Notifications

Each Emby client creates a notify entity (e.g., `notify.living_room_tv_notification`) for sending on-screen messages.

**Example:**
```yaml
service: notify.send_message
target:
  entity_id: notify.living_room_tv_notification
data:
  message: "Dinner is ready!"
  title: "Kitchen Alert"
```

### Server Buttons

The integration creates button entities for server-level actions:

| Button | Description |
|--------|-------------|
| `button.emby_server_refresh_library` | Triggers a full library scan |

**Example:**
```yaml
# Trigger library refresh after adding new media
service: button.press
target:
  entity_id: button.emby_server_refresh_library
```

### Media Browser

Access the Emby media browser from any media player card:

1. Click the media player entity
2. Click "Browse Media"
3. Navigate: Libraries > Categories > Content

**Content Types:**
- **Movies**: A-Z, Year, Decade, Genre, Collections
- **TV Shows**: A-Z, Year, Decade, Genre, then Series > Season > Episode
- **Music**: Artists, Albums, Genres, Playlists, A-Z navigation
- **Live TV**: Channel listing with direct playback

### Media Source

Use Emby as a media source for any Home Assistant media player:

1. Go to **Media** in the sidebar
2. Select "Emby Media" from sources
3. Browse and play on any compatible player

### Voice Commands

Search and play media with voice assistants:

```
"Hey Google, play The Office on Emby"
"Alexa, play jazz music on Living Room TV"
```

## Automation Examples

### Dim Lights When Playing

```yaml
automation:
  - alias: "Dim lights when Emby plays"
    trigger:
      - platform: state
        entity_id: media_player.living_room_tv
        to: "playing"
    action:
      - service: light.turn_on
        target:
          entity_id: light.living_room
        data:
          brightness_pct: 20
```

### Pause When Doorbell Rings

```yaml
automation:
  - alias: "Pause Emby on doorbell"
    trigger:
      - platform: state
        entity_id: binary_sensor.doorbell
        to: "on"
    action:
      - service: media_player.media_pause
        target:
          entity_id: media_player.living_room_tv
```

### Send Notification to TV

```yaml
automation:
  - alias: "Notify TV when laundry done"
    trigger:
      - platform: state
        entity_id: sensor.washer
        to: "complete"
    action:
      - service: notify.send_message
        target:
          entity_id: notify.living_room_tv_notification
        data:
          message: "Laundry is done!"
          title: "Washer"
```

### Navigate with Remote

```yaml
automation:
  - alias: "Go home on idle"
    trigger:
      - platform: state
        entity_id: media_player.living_room_tv
        to: "idle"
        for: "00:05:00"
    action:
      - service: remote.send_command
        target:
          entity_id: remote.living_room_tv_remote
        data:
          command: GoHome
```

### Nightly Library Refresh

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

### Play Music at Sunrise

```yaml
automation:
  - alias: "Morning music"
    trigger:
      - platform: sun
        event: sunrise
    action:
      - service: media_player.play_media
        target:
          entity_id: media_player.kitchen_speaker
        data:
          media_content_type: "music"
          media_content_id: "emby://playlist/morning-mix"
```

### Send Notification on New Movie

```yaml
automation:
  - alias: "New movie notification"
    trigger:
      - platform: state
        entity_id: media_player.server
        attribute: media_title
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.attributes.media_content_type == 'movie' }}"
    action:
      - service: notify.mobile_app
        data:
          title: "Now Playing"
          message: "{{ trigger.to_state.attributes.media_title }}"
```

## Troubleshooting

### Connection Failed

1. Verify the Emby server is running and accessible
2. Check the host and port are correct
3. Ensure no firewall is blocking the connection
4. Try disabling SSL verification for self-signed certificates

### Invalid API Key

1. Generate a new API key from Emby Dashboard
2. Ensure the key has not been revoked
3. Check for extra spaces when copying the key

### Entities Not Appearing

1. Ensure there are active Emby clients
2. Check the client supports remote control
3. Verify the device is not in the ignored list
4. Check Home Assistant logs for errors

### WebSocket Disconnects

The integration automatically reconnects with exponential backoff. If WebSocket is unstable:

1. Try disabling WebSocket in options (uses polling instead)
2. Check network stability between HA and Emby
3. Verify no proxy is interfering with WebSocket

### Media Browser Empty

1. Ensure the API key has access to the libraries
2. Check that libraries are configured for the API user
3. Verify the server has indexed media content

## Diagnostics

Download diagnostic information from **Settings** > **Devices & Services** > **Emby Media** > **3 dots** > **Download Diagnostics**.

Includes:
- Server information
- Connection status
- Active sessions
- Cache statistics

(API keys are automatically redacted)

## Development

See [CLAUDE.md](CLAUDE.md) for development instructions and project structure.

### Running Tests

```bash
pytest tests/ -v
pytest tests/ --cov=custom_components.embymedia --cov-report=term-missing
```

### Type Checking

```bash
mypy custom_components/embymedia/
```

### Linting

```bash
ruff check custom_components/embymedia/
ruff format custom_components/embymedia/
```

## License

This project is licensed under the MIT License.

## Acknowledgments

- [Home Assistant](https://www.home-assistant.io/) - Smart home platform
- [Emby](https://emby.media/) - Media server
- [pyEmby](https://github.com/mezz64/pyEmby) - Reference implementation
