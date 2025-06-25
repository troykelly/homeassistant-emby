# Direct playback on non-Emby devices

The Emby integration is no longer limited to controlling **Emby clients**.  It
can now *stream* library items to **any** media player entity that understands
regular HTTP(S)/HLS URLs – Chromecast, Sonos, AirPlay speakers, browser audio
elements, you name it.

Behind the scenes a brand-new *media source* provider turns an internal
identifier of the form

```
media-source://emby/<ItemId>
```

into a fully authenticated stream URL by negotiating the best playback option
with your Emby server (`/Items/{Id}/PlaybackInfo`).  The resulting link is
self-contained – it carries the API key as a query parameter – so the target
device can fetch the bytes without any custom headers.

---

## Quick start

1. Open Home Assistant’s **Media** panel.
2. Pick *any* target that is **not** an Emby player (e.g. a Chromecast).
3. Browse your Emby library – note how the Play button is available even
   though the device runs no Emby app.
4. Hit **Play** – that’s it.  HA will resolve the `media-source://` URI and
   forward the direct stream to the device.

---

## Service call example

Play *“Dune”* (ItemId `122`) on a living-room Chromecast:

```yaml
service: media_player.play_media
target:
  entity_id: media_player.living_room_cast
data:
  media_content_id: "media-source://emby/122"
  media_content_type: movie
```

You can supply any valid `media_content_type` supported by the player –
`movie`, `music`, `episode` and so on.

---

## Advanced tips

* **Resume position** – When a movie or episode has a `PlayedPercentage` the
  integration automatically passes the offset to compatible players so
  playback resumes without manual seeking.
* **Subtitles** – Emby automatically selects the *default* subtitle track when
  transcoding is required.  Future versions will expose explicit subtitle &
  audio stream selectors in the service schema (tracked in issue #230).

---

## Troubleshooting

* *Error: unsupported media format* – The target might not be able to play
  the chosen container/codec.  Ensure your Emby server can transcode on the
  fly (HLS) or limit the *MaxStreamingBitrate* under **Settings → Playback**.
* *Stuttering on Wi-Fi* – Reduce the bitrate cap in the integration options
  or wire your Chromecast via Ethernet.

If problems persist, enable debug logging (`logger: components.emby: debug`) and
open an issue on GitHub – please include the full Home Assistant logs.

---

_Document generated automatically by Codex 🤖_
