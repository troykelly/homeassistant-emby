# Home Assistant Emby Integration

**Home Assistant Emby** is a custom integration that exposes your Emby media
server – movies, TV, music and more – to Home Assistant.  Once configured you
can browse your library, trigger playback on Emby clients, build automation
around play state changes and combine everything with the rich HA ecosystem.

This README focuses on the `media_player.play_media` functionality added in
version `0.5.0` (see CHANGELOG).  For full installation & configuration details
see the sections below.

---

## Installation

1. Copy/clone the `components/emby` directory into your Home Assistant
   `custom_components` folder.
2. Restart Home Assistant.
3. Configure the platform via `configuration.yaml` (see below) **or** use the
   UI “Add integration” flow if published on HACS/Blueprints.

## Configuration

Example minimal YAML configuration:

```yaml
media_player:
  - platform: emby
    host: 192.168.1.50        # IP / hostname of your Emby server
    api_key: ABCDEF123456789  # Create under Emby → Settings → API keys
    # Optional
    port: 8096               # Defaults to 8096 (HTTP) / 8920 (HTTPS)
    ssl: false               # Set `true` when Emby is served over HTTPS
```

After a reload you should see one `media_player` entity per active Emby client
session – their names match what you see inside the Emby dashboard.

---

## Using `media_player.play_media`

Home Assistant exposes a generic `media_player.play_media` service which the
Emby integration now implements.  It accepts the following payload:

| key        | required | type    | description                                                  |
|------------|----------|---------|--------------------------------------------------------------|
| media_type | yes      | string  | `movie`, `episode`, `music`, `playlist`, `channel`, `trailer` |
| media_id   | yes      | string  | Title, Emby ItemId or path understood by the search resolver |
| enqueue    | no       | bool    | `true` → queue after current item, `false` (default) → play now |
| position   | no       | int     | Start position in **seconds** (converted internally)         |

### Simple example – play a movie immediately

```yaml
service: media_player.play_media
target:
  entity_id: media_player.emby_living_room_tv
data:
  media_type: movie
  media_id: "Back to the Future (1985)"
```

### Queue the next episode of a show

```yaml
service: media_player.play_media
target:
  entity_id: media_player.emby_living_room_tv
data:
  media_type: episode
  media_id: "S02E05"      # Title fragments also work (\"Lost S02E05\")
  enqueue: true
```

### Start music 30 seconds in

```yaml
service: media_player.play_media
target:
  entity_id: media_player.emby_audio_zone
data:
  media_type: music
  media_id: "Bohemian Rhapsody"
  position: 30
```

### Automation snippet

```yaml
alias: Play a welcome song when I arrive home
trigger:
  platform: state
  entity_id: person.matt
  to: home
action:
  - service: media_player.play_media
    target:
      entity_id: media_player.emby_kitchen_display
    data:
      media_type: music
      media_id: "Here Comes the Sun"
```

The internal resolver is quite smart – it will try exact Emby Item IDs first,
then fall back to title search across libraries, seasons/episodes, artists &
tracks.  Ambiguous searches raise a clear error so your automations never hang
silently.

---

## Contributing & Support

Contributions are welcome!  Please open an issue or discussion before starting
large pieces of work so we can coordinate.  Bug fixes and documentation
improvements can be sent directly as pull-requests.

---

## License

This project is licensed under the MIT License – see the `LICENSE` file for
details.
