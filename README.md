# Home Assistant Emby Integration

[![hacs-badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge&logo=home-assistant&logoColor=white)](https://hacs.xyz/)


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

### Via HACS  *(recommended)*

1.  Make sure the [Home Assistant Community Store – **HACS**](https://hacs.xyz/) is installed and set-up in your Home Assistant instance.
2.  Until this integration is accepted into the default HACS store you need to **add it as a custom repository**:
    • Navigate to **HACS → Integrations → ⋮ → Custom repositories**.  
    • Paste the GitHub URL `https://github.com/troykelly/homeassistant-emby` and choose **Integration** as the category.  
    • Click **Add** – the repository will now appear like any other integration.
3.  Search for **“Emby for Home Assistant”** in the HACS integrations list and click **Install**.
4.  Reboot Home Assistant when prompted.
5.  Go to **Settings → Devices & Services → + Add Integration** and search for **Emby** to configure the server connection.

Once the integration is included in the default HACS store (tracked in issue #55) step&nbsp;2 will no longer be required – you can simply search and install.

### Manual installation

If you would rather install manually (or are unable to use HACS):

1.  Copy/clone the `custom_components/embymedia` directory from this repository into `<config>/custom_components/` on your Home Assistant host.
2.  Reboot Home Assistant.
3.  Configure the integration via the UI or `configuration.yaml` as shown below.

### Upgrading

When installed via HACS you will be notified of new releases automatically – simply click **Upgrade** in the HACS UI and reboot when finished.  If you are using the manual method, repeat the copy/clone step with the latest release archive from GitHub and restart Home Assistant.


## Configuration

Example minimal YAML configuration:

```yaml
media_player:
  - platform: embymedia
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

### Development checks

Every pull-request is validated by two CI jobs:

1. **Tests & Coverage** – runs the full `pytest` suite and reports coverage.
2. **Pyright** – performs **strict static type checking**.  The codebase must
   pass with **zero** Pyright errors before a PR can be merged.  You can run
   the check locally by installing the dev dependency and executing `pyright`:

```bash
pip install pyright
pyright --stats
```

The configuration lives in `pyproject.toml` (`[tool.pyright]` section).  IDEs
such as **Visual Studio Code** (with the *Pylance* extension) will pick this up
automatically and surface type issues as you code.

---

## License

This project is licensed under the MIT License – see the `LICENSE` file for
details.
