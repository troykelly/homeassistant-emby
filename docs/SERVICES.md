# Services Reference

This document describes all services provided by the Emby Media integration.

## Table of Contents

- [Standard Media Player Services](#standard-media-player-services)
- [Remote Entity Services](#remote-entity-services)
- [Notify Entity Services](#notify-entity-services)
- [Button Entity Services](#button-entity-services)
- [Custom Emby Services](#custom-emby-services)
- [Service Targeting](#service-targeting)

---

## Standard Media Player Services

These are Home Assistant standard services that work with Emby media player entities.

### media_player.media_play

Resume playback on a paused player.

```yaml
service: media_player.media_play
target:
  entity_id: media_player.living_room_tv
```

### media_player.media_pause

Pause current playback.

```yaml
service: media_player.media_pause
target:
  entity_id: media_player.living_room_tv
```

### media_player.media_stop

Stop playback completely.

```yaml
service: media_player.media_stop
target:
  entity_id: media_player.living_room_tv
```

### media_player.media_play_pause

Toggle between play and pause.

```yaml
service: media_player.media_play_pause
target:
  entity_id: media_player.living_room_tv
```

### media_player.media_next_track

Skip to the next item in queue.

```yaml
service: media_player.media_next_track
target:
  entity_id: media_player.living_room_tv
```

### media_player.media_previous_track

Go back to the previous item.

```yaml
service: media_player.media_previous_track
target:
  entity_id: media_player.living_room_tv
```

### media_player.media_seek

Seek to a specific position.

```yaml
service: media_player.media_seek
target:
  entity_id: media_player.living_room_tv
data:
  seek_position: 300  # Seconds from start
```

### media_player.volume_set

Set volume level (0.0 to 1.0).

```yaml
service: media_player.volume_set
target:
  entity_id: media_player.living_room_tv
data:
  volume_level: 0.5  # 50%
```

### media_player.volume_up / volume_down

Adjust volume incrementally.

```yaml
service: media_player.volume_up
target:
  entity_id: media_player.living_room_tv
```

### media_player.volume_mute

Mute or unmute audio.

```yaml
service: media_player.volume_mute
target:
  entity_id: media_player.living_room_tv
data:
  is_volume_muted: true
```

### media_player.play_media

Play specific media content.

```yaml
service: media_player.play_media
target:
  entity_id: media_player.living_room_tv
data:
  media_content_type: movie
  media_content_id: "item_id_from_emby"
```

**Content Types:**
- `movie` - Play a movie
- `tvshow` - Play a TV episode
- `music` - Play a music track
- `video` - Generic video
- `audio` - Generic audio
- `playlist` - Play a playlist
- `channel` - Play a Live TV channel

---

## Remote Entity Services

Each Emby client creates a remote entity for navigation commands.

### remote.send_command

Send navigation commands to Emby clients.

```yaml
service: remote.send_command
target:
  entity_id: remote.living_room_tv_remote
data:
  command: Select
```

**Available Commands:**

| Command | Description |
|---------|-------------|
| `MoveUp` | Navigate up |
| `MoveDown` | Navigate down |
| `MoveLeft` | Navigate left |
| `MoveRight` | Navigate right |
| `PageUp` | Page up in lists |
| `PageDown` | Page down in lists |
| `Select` | Select/confirm current item |
| `Back` | Go back |
| `GoHome` | Go to home screen |
| `GoToSettings` | Open settings |
| `ToggleContextMenu` | Open context menu |
| `ToggleOsdMenu` | Toggle on-screen display |
| `VolumeUp` | Increase volume |
| `VolumeDown` | Decrease volume |
| `Mute` | Mute audio |
| `Unmute` | Unmute audio |
| `ToggleMute` | Toggle mute state |

**Send Multiple Commands:**

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

### remote.turn_on / turn_off

These are not supported - Emby remotes are virtual entities.

---

## Notify Entity Services

Each Emby client creates a notify entity for on-screen messages.

### notify.send_message

Display a message on the Emby client screen.

```yaml
service: notify.send_message
target:
  entity_id: notify.living_room_tv_notification
data:
  message: "Dinner is ready!"
  title: "Kitchen"  # Optional
```

**Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `message` | Yes | Message text to display |
| `title` | No | Message header/title |

The message will display for approximately 5 seconds on the Emby client.

---

## Button Entity Services

### button.press

Press a button entity to trigger server actions.

```yaml
service: button.press
target:
  entity_id: button.emby_server_refresh_library
```

**Available Buttons:**

| Button | Description |
|--------|-------------|
| `button.emby_server_refresh_library` | Trigger a full library scan |

---

## Custom Emby Services

These are custom services specific to the Emby integration.

### embymedia.send_message

Send a message to one or more Emby clients with more options than the notify entity.

```yaml
service: embymedia.send_message
target:
  entity_id: media_player.living_room_tv
data:
  message: "Important notification!"
  header: "Alert"        # Optional, message header
  timeout_ms: 10000      # Optional, display time in milliseconds (default: 5000)
```

**Parameters:**

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `message` | Yes | — | Message text |
| `header` | No | "" | Message header |
| `timeout_ms` | No | 5000 | Display duration (1000-60000 ms) |

### embymedia.send_command

Send a general command to Emby clients.

```yaml
service: embymedia.send_command
target:
  entity_id: media_player.living_room_tv
data:
  command: GoHome
```

**Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `command` | Yes | Command name (see remote commands above) |

### embymedia.mark_played

Mark an item as played/watched.

```yaml
service: embymedia.mark_played
target:
  entity_id: media_player.living_room_tv
data:
  item_id: "abc123"      # Emby item ID
  user_id: "xyz789"      # Optional, uses session user if not specified
```

**Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `item_id` | Yes | Emby item ID to mark as played |
| `user_id` | No | User ID (defaults to session user) |

### embymedia.mark_unplayed

Mark an item as unplayed/unwatched.

```yaml
service: embymedia.mark_unplayed
target:
  entity_id: media_player.living_room_tv
data:
  item_id: "abc123"
```

**Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `item_id` | Yes | Emby item ID to mark as unplayed |
| `user_id` | No | User ID (defaults to session user) |

### embymedia.add_favorite

Add an item to user's favorites.

```yaml
service: embymedia.add_favorite
target:
  entity_id: media_player.living_room_tv
data:
  item_id: "abc123"
```

**Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `item_id` | Yes | Emby item ID to add to favorites |
| `user_id` | No | User ID (defaults to session user) |

### embymedia.remove_favorite

Remove an item from user's favorites.

```yaml
service: embymedia.remove_favorite
target:
  entity_id: media_player.living_room_tv
data:
  item_id: "abc123"
```

**Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `item_id` | Yes | Emby item ID to remove from favorites |
| `user_id` | No | User ID (defaults to session user) |

### embymedia.refresh_library

Trigger a library scan on the Emby server.

```yaml
service: embymedia.refresh_library
target:
  entity_id: media_player.living_room_tv
data:
  library_id: "abc123"   # Optional, refreshes all if not specified
```

**Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `library_id` | No | Specific library to refresh (all if omitted) |

---

## Service Targeting

### By Entity ID

Target one or more entities directly:

```yaml
service: embymedia.send_message
target:
  entity_id:
    - media_player.living_room_tv
    - media_player.bedroom_tv
data:
  message: "Hello!"
```

### By Device ID

Target by device ID (from Developer Tools):

```yaml
service: embymedia.send_message
target:
  device_id: "abc123def456"
data:
  message: "Hello!"
```

### By Area

Target all Emby entities in an area:

```yaml
service: media_player.media_pause
target:
  area_id: living_room
```

### Multiple Targets

Combine multiple targeting methods:

```yaml
service: embymedia.send_message
target:
  entity_id: media_player.kitchen_tv
  area_id: bedroom
  device_id: "abc123"
data:
  message: "Movie night!"
```

---

## Finding Item IDs

To use services like `mark_played` or `add_favorite`, you need the Emby item ID.

### From Entity Attributes

When something is playing, check the entity attributes:

1. Go to **Developer Tools** → **States**
2. Find your media player entity
3. Look for `media_content_id` attribute

### From Emby URL

When viewing an item in Emby's web interface:
- URL format: `http://emby:8096/web/index.html#!/item?id=abc123`
- The item ID is the `id` parameter: `abc123`

### From Media Browser

The media browser content IDs are in the format required by services.

---

## Examples

### Complete Movie Night Automation

```yaml
automation:
  - alias: "Movie Night Setup"
    trigger:
      - platform: state
        entity_id: input_boolean.movie_night
        to: "on"
    action:
      # Dim the lights
      - service: light.turn_on
        target:
          entity_id: light.living_room
        data:
          brightness_pct: 5
      # Send notification to all TVs
      - service: embymedia.send_message
        target:
          entity_id:
            - media_player.living_room_tv
            - media_player.bedroom_tv
        data:
          message: "Movie night is starting!"
          header: "🎬 Movie Night"
          timeout_ms: 8000
      # Start playing from queue
      - service: media_player.media_play
        target:
          entity_id: media_player.living_room_tv
```

### Mark Series as Watched

```yaml
script:
  mark_series_watched:
    alias: "Mark Series as Watched"
    sequence:
      - service: embymedia.mark_played
        target:
          entity_id: media_player.living_room_tv
        data:
          item_id: "{{ series_id }}"
```

---

## Next Steps

- **[Automations](AUTOMATIONS.md)** - Ready-to-use automation examples
- **[Configuration](CONFIGURATION.md)** - Integration settings
- **[Troubleshooting](TROUBLESHOOTING.md)** - Fix common issues
