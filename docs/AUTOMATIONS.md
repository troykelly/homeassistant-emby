# Automation Examples

This guide provides ready-to-use automation examples for the Emby Media integration.

## Table of Contents

- [Lighting Automations](#lighting-automations)
- [Notification Automations](#notification-automations)
- [Playback Control Automations](#playback-control-automations)
- [Remote Control Automations](#remote-control-automations)
- [Library Management Automations](#library-management-automations)
- [Sensor-Based Automations](#sensor-based-automations)
- [Device Triggers](#device-triggers)
- [WebSocket Events](#websocket-events)
- [Advanced Examples](#advanced-examples)

---

## Lighting Automations

### Dim Lights When Movie Starts

```yaml
automation:
  - alias: "Emby - Dim lights for movies"
    description: "Dim living room lights when a movie starts playing"
    trigger:
      - platform: state
        entity_id: media_player.living_room_tv
        to: "playing"
    condition:
      - condition: template
        value_template: >
          {{ state_attr('media_player.living_room_tv', 'media_content_type') == 'movie' }}
    action:
      - service: light.turn_on
        target:
          entity_id: light.living_room
        data:
          brightness_pct: 10
          transition: 3
```

### Restore Lights When Playback Stops

```yaml
automation:
  - alias: "Emby - Restore lights when stopped"
    description: "Restore lights to full brightness when playback stops"
    trigger:
      - platform: state
        entity_id: media_player.living_room_tv
        from: "playing"
        to:
          - "idle"
          - "off"
    action:
      - service: light.turn_on
        target:
          entity_id: light.living_room
        data:
          brightness_pct: 100
          transition: 2
```

### Different Lighting for Different Content

```yaml
automation:
  - alias: "Emby - Content-based lighting"
    description: "Adjust lighting based on what's playing"
    trigger:
      - platform: state
        entity_id: media_player.living_room_tv
        to: "playing"
    action:
      - choose:
          # Movies - very dim
          - conditions:
              - condition: template
                value_template: >
                  {{ state_attr('media_player.living_room_tv', 'media_content_type') == 'movie' }}
            sequence:
              - service: light.turn_on
                target:
                  entity_id: light.living_room
                data:
                  brightness_pct: 5
                  color_temp: 500
          # TV Shows - moderately dim
          - conditions:
              - condition: template
                value_template: >
                  {{ state_attr('media_player.living_room_tv', 'media_content_type') == 'tvshow' }}
            sequence:
              - service: light.turn_on
                target:
                  entity_id: light.living_room
                data:
                  brightness_pct: 20
          # Music - colorful
          - conditions:
              - condition: template
                value_template: >
                  {{ state_attr('media_player.living_room_tv', 'media_content_type') == 'music' }}
            sequence:
              - service: light.turn_on
                target:
                  entity_id: light.living_room
                data:
                  brightness_pct: 50
                  rgb_color: [255, 100, 50]
```

### Pause Lighting During Paused Playback

```yaml
automation:
  - alias: "Emby - Raise lights when paused"
    trigger:
      - platform: state
        entity_id: media_player.living_room_tv
        to: "paused"
    action:
      - service: light.turn_on
        target:
          entity_id: light.living_room
        data:
          brightness_pct: 40
          transition: 1
```

---

## Notification Automations

### Pause for Doorbell

```yaml
automation:
  - alias: "Emby - Pause for doorbell"
    trigger:
      - platform: state
        entity_id: binary_sensor.doorbell
        to: "on"
    action:
      - service: media_player.media_pause
        target:
          entity_id: media_player.living_room_tv
      - service: notify.send_message
        target:
          entity_id: notify.living_room_tv_notification
        data:
          title: "Doorbell"
          message: "Someone is at the door"
```

### TV Notification for Laundry

```yaml
automation:
  - alias: "Emby - Laundry done notification"
    trigger:
      - platform: state
        entity_id: sensor.washer_status
        to: "complete"
    condition:
      - condition: state
        entity_id: media_player.living_room_tv
        state: "playing"
    action:
      - service: notify.send_message
        target:
          entity_id: notify.living_room_tv_notification
        data:
          title: "Laundry"
          message: "Washing machine is done!"
```

### Dinner Time Notification

```yaml
automation:
  - alias: "Emby - Dinner announcement"
    trigger:
      - platform: time
        at: "18:30:00"
    condition:
      - condition: state
        entity_id: media_player.living_room_tv
        state: "playing"
    action:
      - service: notify.send_message
        target:
          entity_id: notify.living_room_tv_notification
        data:
          title: "Dinner Time"
          message: "Food is ready! 🍕"
```

### Important Call Notification

```yaml
automation:
  - alias: "Emby - Phone call notification"
    trigger:
      - platform: state
        entity_id: sensor.phone_call_status
        to: "ringing"
    action:
      - service: media_player.media_pause
        target:
          entity_id:
            - media_player.living_room_tv
            - media_player.bedroom_tv
      - service: notify.send_message
        target:
          entity_id: notify.living_room_tv_notification
        data:
          title: "Incoming Call"
          message: "{{ state_attr('sensor.phone_call_status', 'caller_name') }}"
```

---

## Playback Control Automations

### Auto-Pause at Bedtime

```yaml
automation:
  - alias: "Emby - Bedtime pause"
    description: "Pause all Emby players at bedtime"
    trigger:
      - platform: time
        at: "23:00:00"
    condition:
      - condition: time
        weekday:
          - sun
          - mon
          - tue
          - wed
          - thu
    action:
      - service: media_player.media_pause
        target:
          entity_id:
            - media_player.living_room_tv
            - media_player.bedroom_tv
      - service: notify.send_message
        target:
          entity_id: notify.living_room_tv_notification
        data:
          title: "Bedtime"
          message: "It's getting late! 😴"
```

### Resume When Returning Home

```yaml
automation:
  - alias: "Emby - Resume when home"
    trigger:
      - platform: state
        entity_id: person.me
        to: "home"
    condition:
      - condition: state
        entity_id: media_player.living_room_tv
        state: "paused"
    action:
      - delay: "00:01:00"  # Wait 1 minute to settle in
      - service: media_player.media_play
        target:
          entity_id: media_player.living_room_tv
```

### Pause When Leaving Home

```yaml
automation:
  - alias: "Emby - Pause when leaving"
    trigger:
      - platform: state
        entity_id: group.family
        from: "home"
        to: "not_home"
    action:
      - service: media_player.media_stop
        target:
          entity_id:
            - media_player.living_room_tv
            - media_player.bedroom_tv
```

### Volume Adjustment for Time of Day

```yaml
automation:
  - alias: "Emby - Night volume"
    trigger:
      - platform: state
        entity_id: media_player.living_room_tv
        to: "playing"
    condition:
      - condition: time
        after: "22:00:00"
        before: "07:00:00"
    action:
      - service: media_player.volume_set
        target:
          entity_id: media_player.living_room_tv
        data:
          volume_level: 0.3
```

---

## Remote Control Automations

### Go Home After Idle

```yaml
automation:
  - alias: "Emby - Go home when idle"
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

### Physical Button to Navigate

```yaml
automation:
  - alias: "Emby - Button navigation"
    trigger:
      - platform: event
        event_type: zha_event
        event_data:
          device_id: "your_button_device_id"
    action:
      - choose:
          - conditions:
              - condition: template
                value_template: "{{ trigger.event.data.command == 'single' }}"
            sequence:
              - service: remote.send_command
                target:
                  entity_id: remote.living_room_tv_remote
                data:
                  command: Select
          - conditions:
              - condition: template
                value_template: "{{ trigger.event.data.command == 'double' }}"
            sequence:
              - service: remote.send_command
                target:
                  entity_id: remote.living_room_tv_remote
                data:
                  command: Back
          - conditions:
              - condition: template
                value_template: "{{ trigger.event.data.command == 'hold' }}"
            sequence:
              - service: remote.send_command
                target:
                  entity_id: remote.living_room_tv_remote
                data:
                  command: GoHome
```

---

## Library Management Automations

### Nightly Library Refresh

```yaml
automation:
  - alias: "Emby - Nightly library refresh"
    trigger:
      - platform: time
        at: "03:00:00"
    action:
      - service: button.press
        target:
          entity_id: button.emby_server_refresh_library
```

### Refresh After Download Completes

```yaml
automation:
  - alias: "Emby - Refresh after download"
    trigger:
      - platform: state
        entity_id: sensor.transmission_active_torrents
        to: "0"
    action:
      - delay: "00:05:00"  # Wait for files to be moved
      - service: button.press
        target:
          entity_id: button.emby_server_refresh_library
```

### Mark As Played After Finishing

```yaml
automation:
  - alias: "Emby - Mark as played"
    trigger:
      - platform: state
        entity_id: media_player.living_room_tv
        from: "playing"
        to: "idle"
    condition:
      - condition: template
        value_template: >
          {% set duration = state_attr('media_player.living_room_tv', 'media_duration') %}
          {% set position = state_attr('media_player.living_room_tv', 'media_position') %}
          {{ duration and position and (position / duration) > 0.9 }}
    action:
      - service: embymedia.mark_played
        target:
          entity_id: media_player.living_room_tv
        data:
          item_id: "{{ state_attr('media_player.living_room_tv', 'media_content_id') }}"
```

---

## Sensor-Based Automations

The Emby integration provides sensors for monitoring server status, library counts, and activity. These can be used to create powerful automations.

### Alert When Library Scan Completes

```yaml
automation:
  - alias: "Emby - Library scan complete notification"
    trigger:
      - platform: state
        entity_id: binary_sensor.media_library_scan_active
        from: "on"
        to: "off"
    action:
      - service: notify.mobile_app
        data:
          title: "Emby Library"
          message: "Library scan completed!"
```

### Notify When Server Needs Restart

```yaml
automation:
  - alias: "Emby - Server restart required"
    trigger:
      - platform: state
        entity_id: binary_sensor.media_pending_restart
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Emby Server"
          message: "Server restart is required"
```

### Alert When Update Available

```yaml
automation:
  - alias: "Emby - Update available"
    trigger:
      - platform: state
        entity_id: binary_sensor.media_update_available
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Emby Update"
          message: "A new Emby server update is available!"
```

### Monitor Active Sessions

```yaml
automation:
  - alias: "Emby - High session count alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.media_active_sessions
        above: 5
    action:
      - service: notify.mobile_app
        data:
          title: "Emby Server"
          message: "{{ states('sensor.media_active_sessions') }} users are connected"
```

### Weekly Library Statistics Report

```yaml
automation:
  - alias: "Emby - Weekly library report"
    trigger:
      - platform: time
        at: "09:00:00"
    condition:
      - condition: time
        weekday:
          - sun
    action:
      - service: notify.mobile_app
        data:
          title: "Emby Weekly Report"
          message: >
            Library Stats:
            🎬 Movies: {{ states('sensor.media_movies') }}
            📺 TV Shows: {{ states('sensor.media_tv_shows') }}
            🎵 Songs: {{ states('sensor.media_songs') }}
```

### Server Offline Alert

```yaml
automation:
  - alias: "Emby - Server offline alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.media_server_connected
        to: "off"
        for: "00:05:00"
    action:
      - service: notify.mobile_app
        data:
          title: "Emby Server"
          message: "Server has been offline for 5 minutes!"
          data:
            priority: high
```

### Dashboard Display with Library Counts

Use the sensors in a Lovelace dashboard:

```yaml
type: entities
title: Emby Library
entities:
  - entity: sensor.media_movies
    name: Movies
    icon: mdi:movie
  - entity: sensor.media_tv_shows
    name: TV Shows
    icon: mdi:television
  - entity: sensor.media_episodes
    name: Episodes
    icon: mdi:television-play
  - entity: sensor.media_songs
    name: Songs
    icon: mdi:music
  - entity: sensor.media_albums
    name: Albums
    icon: mdi:album
  - entity: sensor.media_artists
    name: Artists
    icon: mdi:account-music
```

### Server Status Card

```yaml
type: entities
title: Emby Server Status
entities:
  - entity: binary_sensor.media_server_connected
    name: Connected
  - entity: sensor.media_server_version
    name: Version
  - entity: sensor.media_active_sessions
    name: Active Sessions
  - entity: sensor.media_running_tasks
    name: Running Tasks
  - entity: binary_sensor.media_library_scan_active
    name: Library Scan
  - entity: binary_sensor.media_pending_restart
    name: Restart Required
  - entity: binary_sensor.media_update_available
    name: Update Available
```

---

## Device Triggers

The integration provides device triggers that can be used in automations. These are available in the automation UI under "Device" triggers.

### Available Trigger Types

| Trigger | Description |
|---------|-------------|
| `playback_started` | Media started playing |
| `playback_stopped` | Media stopped |
| `playback_paused` | Media was paused |
| `playback_resumed` | Media resumed from pause |
| `media_changed` | Different media started playing |
| `session_connected` | Client connected to Emby |
| `session_disconnected` | Client disconnected |

---

## WebSocket Events

The integration fires custom events when the Emby server sends real-time updates via WebSocket. These events can be used as triggers in automations.

### Library Updated Event

Fired when items are added, updated, or removed from the library.

**Event Type:** `embymedia_library_updated`

**Event Data:**
| Field | Type | Description |
|-------|------|-------------|
| `server_id` | string | Emby server ID |
| `server_name` | string | Emby server name |
| `items_added` | list | List of added item IDs |
| `items_updated` | list | List of updated item IDs |
| `items_removed` | list | List of removed item IDs |
| `folders_added_to` | list | Library folder IDs with new items |
| `folders_removed_from` | list | Library folder IDs with removed items |

**Example Automation:**

```yaml
automation:
  - alias: "Emby - Notify on new library content"
    trigger:
      - platform: event
        event_type: embymedia_library_updated
        event_data:
          server_name: "My Emby Server"
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.items_added | length > 0 }}"
    action:
      - service: notify.mobile_app
        data:
          title: "New Emby Content"
          message: "{{ trigger.event.data.items_added | length }} new items added to library!"
```

### User Data Changed Event

Fired when a user's item data changes (favorites, played status, ratings).

**Event Type:** `embymedia_user_data_changed`

**Event Data:**
| Field | Type | Description |
|-------|------|-------------|
| `server_id` | string | Emby server ID |
| `server_name` | string | Emby server name |
| `user_id` | string | Emby user ID |
| `item_id` | string | Item ID that changed |
| `is_favorite` | bool | Whether item is now a favorite |
| `played` | bool | Whether item is marked as played |
| `playback_position_ticks` | int | Resume position (optional) |
| `play_count` | int | Number of times played (optional) |
| `rating` | float | User rating 0.0-10.0 (optional) |
| `last_played_date` | string | ISO 8601 timestamp (optional) |

**Example Automation:**

```yaml
automation:
  - alias: "Emby - Track favorite changes"
    trigger:
      - platform: event
        event_type: embymedia_user_data_changed
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.is_favorite == true }}"
    action:
      - service: notify.mobile_app
        data:
          title: "Emby Favorite"
          message: "Item {{ trigger.event.data.item_id }} was added to favorites"
```

### Notification Event

Fired when the Emby server creates a notification.

**Event Type:** `embymedia_notification`

**Event Data:**
| Field | Type | Description |
|-------|------|-------------|
| `server_id` | string | Emby server ID |
| `server_name` | string | Emby server name |
| `name` | string | Notification title |
| `description` | string | Notification message (optional) |
| `level` | string | "Normal", "Warning", or "Error" |
| `notification_type` | string | Type like "Info", "Update", etc. |
| `url` | string | Related URL (optional) |
| `date` | string | ISO 8601 timestamp |

**Example Automation:**

```yaml
automation:
  - alias: "Emby - Forward server notifications"
    trigger:
      - platform: event
        event_type: embymedia_notification
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.level in ['Warning', 'Error'] }}"
    action:
      - service: notify.mobile_app
        data:
          title: "Emby {{ trigger.event.data.level }}"
          message: "{{ trigger.event.data.name }}: {{ trigger.event.data.description }}"
```

### User Changed Event

Fired when a user account is updated or deleted.

**Event Type:** `embymedia_user_changed`

**Event Data:**
| Field | Type | Description |
|-------|------|-------------|
| `server_id` | string | Emby server ID |
| `server_name` | string | Emby server name |
| `user_id` | string | Emby user ID |
| `user_name` | string | User display name (if available) |
| `change_type` | string | "updated" or "deleted" |

**Example Automation:**

```yaml
automation:
  - alias: "Emby - User account changes"
    trigger:
      - platform: event
        event_type: embymedia_user_changed
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.change_type == 'deleted' }}"
    action:
      - service: notify.mobile_app
        data:
          title: "Emby User Deleted"
          message: "User {{ trigger.event.data.user_name or trigger.event.data.user_id }} was removed"
```

### Using Device Triggers in YAML

```yaml
automation:
  - alias: "Emby - Device trigger example"
    trigger:
      - platform: device
        device_id: "your_device_id"
        domain: embymedia
        entity_id: media_player.living_room_tv
        type: playback_started
    action:
      - service: light.turn_off
        target:
          entity_id: light.living_room
```

---

## Advanced Examples

### Now Playing Dashboard Notification

```yaml
automation:
  - alias: "Emby - Now playing notification"
    trigger:
      - platform: state
        entity_id: media_player.living_room_tv
        to: "playing"
    action:
      - service: notify.mobile_app
        data:
          title: "Now Playing on Emby"
          message: >
            {{ state_attr('media_player.living_room_tv', 'media_title') }}
            {% if state_attr('media_player.living_room_tv', 'media_series_title') %}
              - {{ state_attr('media_player.living_room_tv', 'media_series_title') }}
              S{{ state_attr('media_player.living_room_tv', 'media_season') }}E{{ state_attr('media_player.living_room_tv', 'media_episode') }}
            {% endif %}
          data:
            image: "{{ state_attr('media_player.living_room_tv', 'entity_picture') }}"
```

### Multi-Room Audio Sync

```yaml
automation:
  - alias: "Emby - Multi-room music"
    trigger:
      - platform: state
        entity_id: input_boolean.party_mode
        to: "on"
    action:
      - service: media_player.play_media
        target:
          entity_id:
            - media_player.kitchen_speaker
            - media_player.living_room_speaker
            - media_player.patio_speaker
        data:
          media_content_type: "playlist"
          media_content_id: "emby://playlist/party-mix"
```

### Smart Pause for Motion

```yaml
automation:
  - alias: "Emby - Pause when no one watching"
    trigger:
      - platform: state
        entity_id: binary_sensor.living_room_motion
        to: "off"
        for: "00:10:00"
    condition:
      - condition: state
        entity_id: media_player.living_room_tv
        state: "playing"
      - condition: template
        value_template: >
          {{ state_attr('media_player.living_room_tv', 'media_content_type') in ['movie', 'tvshow'] }}
    action:
      - service: media_player.media_pause
        target:
          entity_id: media_player.living_room_tv
      - service: notify.send_message
        target:
          entity_id: notify.living_room_tv_notification
        data:
          message: "Paused - no one seems to be watching"
```

### Kids TV Time Limit

```yaml
automation:
  - alias: "Emby - Kids TV time limit"
    trigger:
      - platform: state
        entity_id: media_player.kids_room_tv
        to: "playing"
        for: "02:00:00"
    condition:
      - condition: time
        weekday:
          - mon
          - tue
          - wed
          - thu
          - fri
    action:
      - service: media_player.media_stop
        target:
          entity_id: media_player.kids_room_tv
      - service: notify.send_message
        target:
          entity_id: notify.kids_room_tv_notification
        data:
          title: "Screen Time"
          message: "Time to take a break! 📚"
```

---

## Tips

1. **Use entity groups** for controlling multiple players at once
2. **Add conditions** to prevent automations from running at inappropriate times
3. **Use delays** to prevent rapid-fire triggers
4. **Test with minimal actions** before adding complex sequences
5. **Check logs** if automations aren't working as expected

## Next Steps

- **[Services Reference](SERVICES.md)** - All available service calls
- **[Troubleshooting](TROUBLESHOOTING.md)** - Fix common issues
- **[Configuration](CONFIGURATION.md)** - Adjust integration settings
