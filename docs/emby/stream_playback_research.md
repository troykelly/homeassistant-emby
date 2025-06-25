# Emby stream URL research (GitHub issue #218)

This document captures the findings of the exploratory work requested in
[*task: research Emby stream URL endpoints*](https://github.com/troykelly/homeassistant-emby/issues/218).
It focuses specifically on how to obtain a stable, **play-ready** HTTP(S) URL
for any Emby *ItemId* so that Home Assistant can play the content on devices
that are **not** running an Emby client application (Chromecast, Sonos, etc.).

The investigation uses the public Emby OpenAPI specification found under
`docs/emby/openapi.json` and has been verified against the test server set in
the CI environment (`$EMBY_URL`). All captured examples work unmodified when
the `$EMBY_API_KEY` environment variable is present.

---

## 1. Negotiating playback information – `POST /Items/{Id}/PlaybackInfo`

* **Spec reference:** `#/paths/Items/{Id}/PlaybackInfo/post`
* **Purpose:** Ask the server which *MediaSources* are available for the given
  item **for the requesting user** and under which conditions (direct play /
  transcoding / HLS / progressive download).

### Required request headers

```
X-Emby-Token: <API KEY>
Content-Type: application/json
```

### Minimal request body

```jsonc
{
  "UserId": "<user-guid>",            // optional – omit for anonymous
  "MaxStreamingBitrate": 80000000,     // optional upper cap (bits/s)
  "DeviceProfile": {
    "Name": "ha-direct-play",
    "DirectPlayProfile": [             // tell Emby what we can play natively
      { "Container": "mp4,mkv", "Type": "Video" },
      { "Container": "aac,mp3", "Type": "Audio" }
    ]
  }
}
```

> **Note** – Supplying a *DeviceProfile* is the officially supported way to
> influence whether Emby chooses direct play or transcoding.  Omitting it means
> the server will default to *transcode-first* which is not desirable for
> generic speakers/audio players.

### Successful response (excerpt)

```jsonc
{
  "MediaSources": [
    {
      "Id": "1a5fe7d492c7b3c27c5242b7b63b17e5",
      "Path": "/media/movies/DUNE.MP4",
      "Container": "mp4",
      "DirectStreamUrl": "https://emby.mctk.co/Videos/122/stream.mp4?Static=true&MediaSourceId=1a5fe...&api_key=<token>",
      "SupportsDirectStream": true,
      "SupportsDirectPlay": true,
      "TranscodingUrl": "Videos/122/master.m3u8?...",        // Only when transcoding needed
      "Subtitles": [ { "Index": 0, "Codec": "srt" } ],
      "MediaStreams": [
        { "Index": 0, "Codec": "h264", "Type": "Video" },
        { "Index": 1, "Codec": "aac",  "Type": "Audio" }
      ]
    }
  ]
}
```

The helper we will implement in issue #219 can simply iterate the
`MediaSources` array and pick the first entry where `SupportsDirectPlay` is
`true`.  When no such entry exists we fall back to the `TranscodingUrl`
variant.

---

## 2. Progressive / HLS stream endpoints

Once an appropriate *MediaSource* has been chosen we need the actual bytes. The
OpenAPI schema exposes two relevant URL patterns:

### 2.1 `/Videos/{Id}/stream` (progressive download)

* **Spec reference:** `#/paths/Videos/{Id}/stream`
* **Supports:** `Range` requests, ideal for quick-start clients (Chromecast,
  browsers).
* **Query parameters** (most common):
  * `Static=true` – instructs Emby to skip runtime transcoder probes and serve
    the file as-is.
  * `MediaSourceId` – the *Id* from the selected `MediaSource`.
  * `api_key` – repeat of `X-Emby-Token` for idempotent GET access.

### 2.2 `/Videos/{Id}/stream.{Container}` (container constrained)

* **Spec reference:** `#/paths/Videos/{Id}/stream.{Container}`
* Accepts an explicit container (e.g. `.mp4` / `.mkv`) which some DLNA devices
  insist on.

### 2.3 HLS master playlist – `/Videos/{Id}/master.m3u8`

* Generated automatically when Emby needs to transcode because direct play is
  not possible.
* URL is given directly in `PlaybackInfoResponse.TranscodingUrl` – **no extra
  authentication** parameters required when `X-Emby-Token` is present in the
  subsequent GET request.

---

## 3. Authentication mechanics

Emby supports two interchangeable auth methods:

1. `X-Emby-Token: <apikey>` header (recommended – see current integration)
2. `?api_key=<apikey>` query parameter for plain GETs.

For *stream* URLs we prefer the **query parameter** variant so that any
downstream player can fetch the media without having to set custom headers.
This is particularly important for Chromecast and browser based players where
header injection is not possible.

---

## 4. Examples against the test server

> `$EMBY_URL=https://emby.mctk.co`

### 4.1 Playback negotiation (item `122`, direct play preferred)

```bash
curl -X POST "$EMBY_URL/Items/122/PlaybackInfo" \
  -H "X-Emby-Token: $EMBY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"MaxStreamingBitrate":80000000,"DeviceProfile":{"Name":"ha","DirectPlayProfile":[{"Container":"mp4,mkv","Type":"Video"}]}}' | jq .MediaSources[0].DirectStreamUrl
```

### 4.2 Fetch the returned progressive stream URL

```bash
curl -O "https://emby.mctk.co/Videos/122/stream.mp4?Static=true&MediaSourceId=<id>&api_key=$EMBY_API_KEY"
```

---

## 5. Summary

* Use **`POST /Items/{Id}/PlaybackInfo`** to negotiate codecs, subtitles and to
  discover the best *MediaSource*.
* Prefer the `DirectStreamUrl` when `SupportsDirectPlay == true` otherwise fall
  back to `TranscodingUrl` (typically an HLS master playlist).
* Append the API key as a query parameter so that the resulting link is
  self-contained – no fragile header forwarding required.

These findings unblock the implementation work in issue #219 – a new helper
`EmbyAPI.get_stream_url(...)` can wrap the above logic and produce a
ready-to-use URL for Home Assistant's generic *play media* workflow.
