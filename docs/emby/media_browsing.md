# Media Browsing

Home Assistant exposes a generic **Browse Media** dialog which integrations can
hook into to provide a rich navigation tree.  As of version `0.6.0` the Emby
integration fully implements this capability through the
`media_player.async_browse_media` API.

---

## Quick start

1. Open the left-hand **Media** panel in Home Assistant.
2. Click **Browse media** then pick any Emby player entity.
3. Choose a library (Movies, TV Shows, Music, …).
4. Drill down into collections / folders until you reach a playable item.
5. Hit the artwork tile to start playback instantly on the selected client.

![Browse Emby root](../images/browse_root.png)
![Browse Emby movies](../images/browse_movies.png)

_Screenshots are illustrative – your artwork and library names will differ._

---

## Hierarchy mapping

| Emby Object            | HA `media_class`            | `can_play` | `can_expand` |
|------------------------|-----------------------------|------------|--------------|
| Library (View)         | `directory`                 | ❌         | ✅           |
| Collection / Folder    | `directory`                 | ❌         | ✅           |
| TV Season              | `season`                    | ❌         | ✅           |
| Movie                  | `movie`                     | ✅         | ❌           |
| Episode                | `episode`                   | ✅         | ❌           |
| Music Album            | `album`                     | ✅         | ✅ (tracks)  |
| Song / Track           | `music`                     | ✅         | ❌           |
| Playlist               | `playlist`                  | ✅         | ❌           |

The integration translates Emby item types into the closest matching Home
Assistant `media_class` so the frontend can decorate each tile appropriately.

---

## Deep linking & automations

Every tile in the browse tree exposes a stable `media_content_id` that starts
with the custom schema `emby://`.  Example:

```
emby://item/9d2c6723d5c175afcd9f5e9d1f4b5678
```

You can copy this ID (e.g. via automation UI) and feed it directly into
`media_player.play_media` – either manually or programmatically – to trigger
playback without going through the browse dialog.

```yaml
service: media_player.play_media
target:
  entity_id: media_player.emby_projector
data:
  media_type: movie
  media_id: "emby://item/9d2c6723d5c175afcd9f5e9d1f4b5678"
```

---

## Mixing in other sources

When the requested ID starts with `media-source://` the Emby integration
delegates the call back to the built-in `media_source` integration so local
files, TTS and cloud providers keep working as expected.  This means you can
seamlessly blend local jingles or announcements into your Emby driven
automations.

---

## Troubleshooting

• *Item not found* – The associated Emby item has been deleted or is no longer
  accessible to the user configured in the integration.  Re-scan libraries or
  regenerate the link via the browse dialog.
• *Empty library* – Ensure the user account used by Home Assistant has
  permission to view the libraries in Emby server settings.

For further assistance please open an issue on GitHub with debug logs
(`logger: components.emby: debug`).

---

_Document generated automatically by Codex 🤖_
