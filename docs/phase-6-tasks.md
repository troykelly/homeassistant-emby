# Phase 6: Media Source Provider

## Overview

This phase implements the Media Source provider for the Emby integration, allowing Emby content to be played on ANY Home Assistant media player (Chromecast, Sonos, etc.), not just Emby clients.

**Features:**
- Register Emby as a Media Source in Home Assistant
- Browse Emby libraries from the Media Source UI
- Generate authenticated stream URLs for playback
- Support for transcoding parameters
- Audio/subtitle stream selection
- Play Emby content on any compatible HA media player

## Dependencies

- Phase 5 complete (media browsing)
- Home Assistant `MediaSource` class
- Emby streaming endpoints

## Home Assistant Media Source API

### MediaSource Base Class

```python
from homeassistant.components.media_source import (
    MediaSource,
    MediaSourceItem,
    PlayMedia,
    BrowseMediaSource,
    Unresolvable,
)

class EmbyMediaSource(MediaSource):
    """Emby Media Source implementation."""

    name: str = "Emby"

    async def async_resolve_media(
        self, item: MediaSourceItem
    ) -> PlayMedia:
        """Resolve a media item to a playable URL."""
        ...

    async def async_browse_media(
        self, item: MediaSourceItem
    ) -> BrowseMediaSource:
        """Browse media."""
        ...
```

### MediaSourceItem

```python
@dataclass
class MediaSourceItem:
    """Media source item."""

    domain: str  # "embymedia"
    identifier: str  # Our content ID
    target_media_player: str | None = None
```

### PlayMedia Response

```python
@dataclass
class PlayMedia:
    """Playable media."""

    url: str  # Stream URL
    mime_type: str  # e.g., "video/mp4"
```

### BrowseMediaSource

```python
class BrowseMediaSource(BrowseMedia):
    """Extended BrowseMedia with media source info."""

    domain: str
    identifier: str
```

---

## Emby Streaming Endpoints

### Video Streaming

```
GET /Videos/{itemId}/stream
GET /Videos/{itemId}/stream.{container}
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `Static` | bool | Direct play (no transcoding) |
| `Container` | string | Output container (mp4, mkv, webm) |
| `AudioCodec` | string | Audio codec (aac, mp3, opus) |
| `VideoCodec` | string | Video codec (h264, hevc, vp9) |
| `MaxVideoBitRate` | int | Max video bitrate |
| `MaxAudioBitRate` | int | Max audio bitrate |
| `MaxWidth` | int | Max video width |
| `MaxHeight` | int | Max video height |
| `AudioStreamIndex` | int | Audio track to use |
| `SubtitleStreamIndex` | int | Subtitle track |
| `SubtitleMethod` | string | Encode, Embed, External |

### Audio Streaming

```
GET /Audio/{itemId}/stream
GET /Audio/{itemId}/stream.{container}
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `Container` | string | Output format (mp3, flac, aac) |
| `AudioCodec` | string | Audio codec |
| `MaxAudioBitRate` | int | Max bitrate |
| `Static` | bool | Direct play |

### Universal Stream (Adaptive)

```
GET /Videos/{itemId}/master.m3u8
GET /Videos/{itemId}/main.m3u8
```

HLS adaptive streaming for compatible players.

### Direct Download

```
GET /Items/{itemId}/Download
```

Returns the original file without transcoding.

---

## Tasks

### Task 6.1: Media Source Registration

Register Emby as a media source provider.

#### 6.1.1 Create media_source.py

**File:** `custom_components/embymedia/media_source.py`

```python
"""Emby Media Source implementation."""

from __future__ import annotations

from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)
from homeassistant.components.media_player import MediaClass, MediaType
from homeassistant.core import HomeAssistant

from .const import DOMAIN

async def async_get_media_source(hass: HomeAssistant) -> EmbyMediaSource:
    """Set up Emby media source."""
    return EmbyMediaSource(hass)


class EmbyMediaSource(MediaSource):
    """Emby media source."""

    name: str = "Emby"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize Emby media source."""
        super().__init__(DOMAIN)
        self.hass = hass
```

**Acceptance Criteria:**
- [ ] `media_source.py` file created
- [ ] `EmbyMediaSource` class extends `MediaSource`
- [ ] `async_get_media_source` function defined
- [ ] Registered in `manifest.json`

**Test Cases:**
- [ ] `test_media_source_creation`
- [ ] `test_media_source_name`

#### 6.1.2 Update manifest.json

Add media_source dependency.

```json
{
  "dependencies": ["media_source"]
}
```

**Test Cases:**
- [ ] `test_manifest_has_media_source_dependency`

---

### Task 6.2: Browse Media Implementation (Media Source)

Implement `async_browse_media` for the media source.

#### 6.2.1 Root Level Browsing

```python
async def async_browse_media(
    self, item: MediaSourceItem
) -> BrowseMediaSource:
    """Browse Emby media."""
    if item.identifier is None:
        return await self._async_browse_root()

    return await self._async_browse_item(item.identifier)
```

**Acceptance Criteria:**
- [ ] Returns list of configured Emby servers at root
- [ ] Each server shows its libraries
- [ ] Libraries show content
- [ ] Full hierarchy navigation works

**Test Cases:**
- [ ] `test_browse_media_source_root`
- [ ] `test_browse_media_source_server`
- [ ] `test_browse_media_source_library`

#### 6.2.2 Content ID Format for Media Source

```
# Format: server_id/content_type/item_id
"abc123"                           # Server abc123 root
"abc123/library/lib456"           # Library lib456 on server abc123
"abc123/movie/mov789"             # Movie mov789
"abc123/series/ser123"            # Series
"abc123/season/ser123/sea456"     # Season
"abc123/episode/ep789"            # Episode
"abc123/album/alb123"             # Album
"abc123/track/trk456"             # Track
```

**Test Cases:**
- [ ] `test_media_source_content_id_encoding`
- [ ] `test_media_source_content_id_decoding`

---

### Task 6.3: Media URL Resolution

Implement `async_resolve_media` to generate playable URLs.

#### 6.3.1 Basic URL Resolution

```python
async def async_resolve_media(
    self, item: MediaSourceItem
) -> PlayMedia:
    """Resolve media to a playable URL."""
    server_id, content_type, item_id = self._parse_identifier(item.identifier)

    # Get client for server
    client = self._get_client(server_id)
    if not client:
        raise Unresolvable(f"Server {server_id} not found")

    # Generate stream URL
    url = client.get_stream_url(item_id, content_type)
    mime_type = self._get_mime_type(content_type)

    return PlayMedia(url=url, mime_type=mime_type)
```

**Acceptance Criteria:**
- [ ] Resolves video items to stream URLs
- [ ] Resolves audio items to stream URLs
- [ ] Includes authentication in URL
- [ ] Returns correct MIME type

**Test Cases:**
- [ ] `test_resolve_media_video`
- [ ] `test_resolve_media_audio`
- [ ] `test_resolve_media_invalid`
- [ ] `test_resolve_media_server_not_found`

#### 6.3.2 Add Stream URL Methods to API Client

**File:** `custom_components/embymedia/api.py`

```python
def get_video_stream_url(
    self,
    item_id: str,
    container: str = "mp4",
    static: bool = True,
    audio_codec: str | None = None,
    video_codec: str | None = None,
    max_width: int | None = None,
    max_height: int | None = None,
    audio_stream_index: int | None = None,
    subtitle_stream_index: int | None = None,
) -> str:
    """Generate URL for video streaming.

    Args:
        item_id: Video item ID.
        container: Output container format.
        static: Direct play without transcoding.
        audio_codec: Audio codec for transcoding.
        video_codec: Video codec for transcoding.
        max_width: Maximum video width.
        max_height: Maximum video height.
        audio_stream_index: Audio track index.
        subtitle_stream_index: Subtitle track index.

    Returns:
        Full streaming URL with authentication.
    """

def get_audio_stream_url(
    self,
    item_id: str,
    container: str = "mp3",
    static: bool = True,
    audio_codec: str | None = None,
    max_bitrate: int | None = None,
) -> str:
    """Generate URL for audio streaming."""

def get_hls_url(
    self,
    item_id: str,
) -> str:
    """Generate HLS adaptive streaming URL."""
```

**Test Cases:**
- [ ] `test_get_video_stream_url_direct`
- [ ] `test_get_video_stream_url_transcode`
- [ ] `test_get_audio_stream_url`
- [ ] `test_get_hls_url`

---

### Task 6.4: MIME Type Mapping

Map Emby content types to MIME types.

```python
MIME_TYPES: dict[str, str] = {
    "movie": "video/mp4",
    "episode": "video/mp4",
    "video": "video/mp4",
    "audio": "audio/mpeg",
    "track": "audio/mpeg",
}

def _get_mime_type(self, content_type: str, container: str = "mp4") -> str:
    """Get MIME type for content."""
    if content_type in ("movie", "episode", "video"):
        return f"video/{container}"
    if content_type in ("audio", "track"):
        if container == "flac":
            return "audio/flac"
        if container == "aac":
            return "audio/aac"
        return "audio/mpeg"
    return "application/octet-stream"
```

**Test Cases:**
- [ ] `test_get_mime_type_video`
- [ ] `test_get_mime_type_audio`
- [ ] `test_get_mime_type_unknown`

---

### Task 6.5: Multi-Server Support

Handle multiple Emby servers.

#### 6.5.1 Server Discovery

```python
def _get_configured_servers(self) -> dict[str, EmbyCoordinator]:
    """Get all configured Emby servers."""
    servers: dict[str, EmbyCoordinator] = {}
    for entry_id, data in self.hass.data.get(DOMAIN, {}).items():
        coordinator = data.get("coordinator")
        if coordinator:
            servers[coordinator.server_id] = coordinator
    return servers
```

**Acceptance Criteria:**
- [ ] Discovers all configured Emby servers
- [ ] Shows all servers at media source root
- [ ] Each server's content is browsable
- [ ] Handles server disconnection gracefully

**Test Cases:**
- [ ] `test_multi_server_discovery`
- [ ] `test_multi_server_browsing`
- [ ] `test_server_unavailable`

---

### Task 6.6: TypedDicts for Streaming

Add type definitions for streaming parameters.

**File:** `custom_components/embymedia/const.py`

```python
class VideoStreamParams(TypedDict, total=False):
    """Video streaming parameters."""

    container: str
    static: bool
    audio_codec: str
    video_codec: str
    max_width: int
    max_height: int
    max_video_bitrate: int
    max_audio_bitrate: int
    audio_stream_index: int
    subtitle_stream_index: int
    subtitle_method: str


class AudioStreamParams(TypedDict, total=False):
    """Audio streaming parameters."""

    container: str
    static: bool
    audio_codec: str
    max_bitrate: int
```

**Test Cases:**
- [ ] `test_video_stream_params_typing`
- [ ] `test_audio_stream_params_typing`

---

### Task 6.7: Integration with Home Assistant

#### 6.7.1 Platform Registration

Ensure media_source platform is loaded.

**File:** `custom_components/embymedia/__init__.py`

```python
PLATFORMS = [Platform.MEDIA_PLAYER]  # media_source loaded via manifest
```

**Note:** Media Source is registered automatically via `async_get_media_source` function.

**Test Cases:**
- [ ] `test_media_source_platform_loads`
- [ ] `test_media_source_available_after_setup`

---

### Task 6.8: Error Handling

Handle various error conditions gracefully.

```python
async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
    """Resolve media with error handling."""
    try:
        server_id, content_type, item_id = self._parse_identifier(item.identifier)
    except ValueError as err:
        raise Unresolvable(f"Invalid identifier: {item.identifier}") from err

    client = self._get_client(server_id)
    if not client:
        raise Unresolvable(f"Server {server_id} not configured")

    if not client.available:
        raise Unresolvable(f"Server {server_id} is unavailable")

    # Generate URL
    ...
```

**Error Conditions:**
- [ ] Invalid identifier format
- [ ] Server not found
- [ ] Server unavailable
- [ ] Item not found
- [ ] Permission denied

**Test Cases:**
- [ ] `test_resolve_invalid_identifier`
- [ ] `test_resolve_server_not_found`
- [ ] `test_resolve_server_unavailable`
- [ ] `test_resolve_item_not_found`

---

## Optional Tasks

### Task 6.9: Image Proxy (Phase 4 Optional)

Proxy images through Home Assistant for authentication.

**File:** `custom_components/embymedia/image.py`

```python
"""Emby image proxy."""

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

class EmbyImageProxyView(HomeAssistantView):
    """Proxy for Emby images."""

    url = "/api/embymedia/image/{server_id}/{item_id}/{image_type}"
    name = "api:embymedia:image"
    requires_auth = False  # Images are public

    async def get(
        self,
        request: web.Request,
        server_id: str,
        item_id: str,
        image_type: str,
    ) -> web.Response:
        """Proxy image request to Emby server."""
```

**Acceptance Criteria:**
- [ ] Images accessible without exposing API key
- [ ] Cache headers for browser caching
- [ ] Resize parameters support

**Test Cases:**
- [ ] `test_image_proxy_get`
- [ ] `test_image_proxy_caching`
- [ ] `test_image_proxy_resize`

---

### Task 6.10: Transcoding Options

Add options flow for default transcoding settings.

**File:** `custom_components/embymedia/config_flow.py` (Options Flow)

```python
async def async_step_streaming(
    self, user_input: dict[str, Any] | None = None
) -> ConfigFlowResult:
    """Configure streaming options."""
    if user_input is not None:
        return self.async_create_entry(data=user_input)

    return self.async_show_form(
        step_id="streaming",
        data_schema=vol.Schema({
            vol.Optional(CONF_VIDEO_CONTAINER, default="mp4"): vol.In(["mp4", "mkv", "webm"]),
            vol.Optional(CONF_MAX_VIDEO_BITRATE): cv.positive_int,
            vol.Optional(CONF_MAX_AUDIO_BITRATE): cv.positive_int,
            vol.Optional(CONF_DIRECT_PLAY, default=True): cv.boolean,
        }),
    )
```

**Test Cases:**
- [ ] `test_options_flow_streaming`
- [ ] `test_streaming_options_applied`

---

## Integration Tests

### Task 6.11: End-to-End Media Source Test

Test complete media source flow:

1. Browse media source root → servers
2. Browse server → libraries
3. Browse library → content
4. Resolve video → stream URL
5. Resolve audio → stream URL

**Test Cases:**
- [ ] `test_media_source_full_flow`
- [ ] `test_media_source_playback_on_cast`

---

## Acceptance Criteria Summary

### Required for Phase 6 Complete

- [ ] `EmbyMediaSource` class implemented
- [ ] Media source registered in manifest
- [ ] `async_browse_media` for media source
- [ ] `async_resolve_media` returns stream URLs
- [ ] Stream URL generation methods in API client
- [ ] MIME type mapping
- [ ] Multi-server support
- [ ] Error handling
- [ ] All tests passing
- [ ] 100% code coverage maintained
- [ ] No mypy errors
- [ ] No ruff errors

### Definition of Done

1. [ ] Emby appears in Media Source browser
2. [ ] Can browse all Emby content from Media Source
3. [ ] Can play Emby video on Chromecast
4. [ ] Can play Emby audio on Sonos (or similar)
5. [ ] Works with multiple Emby servers

---

## MIME Type Reference

| Content Type | Default Container | MIME Type |
|--------------|-------------------|-----------|
| Movie | mp4 | video/mp4 |
| Episode | mp4 | video/mp4 |
| Video | mp4 | video/mp4 |
| Track | mp3 | audio/mpeg |
| Audio | mp3 | audio/mpeg |
| MKV Video | mkv | video/x-matroska |
| WebM Video | webm | video/webm |
| FLAC Audio | flac | audio/flac |
| AAC Audio | aac | audio/aac |

---

## Notes

- Media Source is distinct from MediaPlayerEntity browsing
- Stream URLs must include authentication
- Consider transcoding for compatibility with various players
- HLS provides better adaptive streaming for variable bandwidth
- Some players may not support all codecs/containers
