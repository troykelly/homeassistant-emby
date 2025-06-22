# Home Assistant Emby Integration

**Home Assistant Emby** is a custom integration that exposes your Emby media
server – movies, TV, music and more – to Home Assistant.  Once configured you
can browse your library, trigger playback on Emby clients, build automation
around play state changes and combine everything with the rich HA ecosystem.

Key features:

• 💿 **Browse Media** – visually navigate your Emby libraries from Home
  Assistant and start playback with a click.
• ▶️ **Play Media** – powerful resolver that supports titles, seasons, exact
  Emby IDs and more.
• 🔄 **Automations ready** – every browse item works seamlessly with
  `media_player.play_media`, making automations trivial.

This README focuses on the `media_player.play_media` functionality added in
version `0.6.0` (see CHANGELOG).  The latest release also introduces **native
media browsing** – letting you navigate your Emby libraries directly inside the
Home Assistant UI and start playback with a single click.  For full
installation & configuration details see the sections below.

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

## Browsing your Emby library in the UI  _(new in v0.6.0)_

From Home Assistant 2023.5 the **Browse Media** dialog became the preferred way
for users to explore their libraries and enqueue content.  The Emby
integration now implements `async_browse_media`, which means:

1. Click **Media → Browse media** (or the ✚ icon in Automations/Scenes).
2. Choose one of your connected Emby players.
3. Navigate through Libraries → Collections/Seasons → Items.
4. Tap a playable leaf item (movie, episode, track, playlist) to start
   playback instantly.

The navigation hierarchy matches what you see in the Emby web dashboard:

• **Libraries** – eg. *Movies*, *TV Shows*, *Music*\
• **Collections / Folders** – box-sets, TV seasons, artist albums\
• **Items** – individual movies, episodes, songs, channels…

Each tile is enriched with artwork and the correct media class so Home
Assistant can display appropriate icons and actions.  Pagination is handled
transparently – large libraries still load quickly and expose *Next / Previous*
folders for efficient navigation when required.

### Mixing local media & TTS

If you browse to **Media Source** paths such as `media-source://tts` the
integration automatically delegates to the built-in `media_source`
integration.  This keeps text-to-speech and local file playback working exactly
as before.

### Automations & scripts

The browse dialog is the fastest way to visually pick an item – but you can
also feed the resulting `media_content_id` straight back into the
`media_player.play_media` service (for example in a script).  Under the hood
the ID uses an `emby://` schema followed by the Emby ItemId so look-ups are
reliable and language-agnostic.

```yaml
service: media_player.play_media
target:
  entity_id: media_player.emby_lounge_tv
data:
  media_type: movie
  media_id: "emby://item/123456789abcdef"  # generated from the browse dialog
```

---

---

## Contributing & Support

Contributions are welcome!  Please open an issue or discussion before starting
large pieces of work so we can coordinate.  Bug fixes and documentation
improvements can be sent directly as pull-requests.

---

## License

This project is licensed under the MIT License – see the `LICENSE` file for
details.
