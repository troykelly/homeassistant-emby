# Phase 13: Dynamic Transcoding for Universal Media Playback

## Overview

This phase implements intelligent transcoding support for the media source provider, enabling Emby content to be "cast" to any device (Chromecast, Roku, Apple TV, Sonos, etc.) with automatic format negotiation based on target device capabilities.

The implementation uses Emby's PlaybackInfo API to let the server decide the optimal playback method (Direct Play, Direct Stream, or HLS Transcoding) based on a DeviceProfile that describes the target device's capabilities.

## Implementation Status: COMPLETE ✅

---

## Background Research

### How Emby Transcoding Works

Emby supports three playback methods:

1. **Direct Play** - Client plays file directly from disk path (requires file system access)
2. **Direct Stream** - Server streams file as-is without re-encoding
3. **Transcode** - Server converts video/audio to compatible format in real-time

### Key API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/Items/{id}/PlaybackInfo` | POST | Get optimal playback URL with DeviceProfile |
| `/Videos/{id}/stream` | GET | Progressive video streaming |
| `/Videos/{id}/master.m3u8` | GET | HLS adaptive streaming |
| `/Audio/{id}/universal` | GET | Universal audio (server decides format) |
| `/Videos/ActiveEncodings` | DELETE | Stop transcoding session |

### Device Compatibility Matrix

| Device | Video Codecs | Audio Codecs | Container | Notes |
|--------|-------------|--------------|-----------|-------|
| Chromecast | H.264 (4.1), VP8, VP9 | AAC, MP3, Vorbis | MP4, WebM | HEVC on Ultra only |
| Roku | H.264, HEVC (4K) | AAC, AC3, MP3 | MP4, MKV, TS | Limited codec support |
| Apple TV | H.264, HEVC | AAC, AC3, E-AC3 | MP4, MOV | Wide format support |
| Sonos/Speakers | N/A | AAC, MP3, FLAC, OGG | - | Audio only |

---

## Task Breakdown

### Task 13.1: TypedDicts for PlaybackInfo API

**Files:** `custom_components/embymedia/const.py`

Add TypedDicts for the PlaybackInfo request and response structures.

#### 13.1.1 PlaybackInfoRequest TypedDict
```python
class PlaybackInfoRequest(TypedDict, total=False):
    """Request body for PlaybackInfo endpoint."""
    UserId: str
    MaxStreamingBitrate: int
    StartTimeTicks: int
    AudioStreamIndex: int
    SubtitleStreamIndex: int
    MaxAudioChannels: int
    MediaSourceId: str
    LiveStreamId: str
    DeviceProfile: DeviceProfile
    EnableDirectPlay: bool
    EnableDirectStream: bool
    EnableTranscoding: bool
    AllowVideoStreamCopy: bool
    AllowAudioStreamCopy: bool
    AutoOpenLiveStream: bool
```

#### 13.1.2 MediaSourceInfo TypedDict
```python
class MediaSourceInfo(TypedDict, total=False):
    """Media source information from PlaybackInfo response."""
    Id: str
    Name: str
    Path: str
    Protocol: str  # File, Http, Rtmp, etc.
    Container: str
    Size: int
    Bitrate: int
    RunTimeTicks: int
    SupportsTranscoding: bool
    SupportsDirectStream: bool
    SupportsDirectPlay: bool
    TranscodingUrl: str
    TranscodingSubProtocol: str
    TranscodingContainer: str
    DirectStreamUrl: str
    MediaStreams: list[MediaStreamInfo]
    DefaultAudioStreamIndex: int
    DefaultSubtitleStreamIndex: int
```

#### 13.1.3 MediaStreamInfo TypedDict
```python
class MediaStreamInfo(TypedDict, total=False):
    """Individual stream (video/audio/subtitle) information."""
    Index: int
    Type: str  # Video, Audio, Subtitle
    Codec: str
    Language: str
    Title: str
    IsDefault: bool
    IsForced: bool
    # Video-specific
    Width: int
    Height: int
    BitRate: int
    AspectRatio: str
    AverageFrameRate: float
    Profile: str
    Level: float
    # Audio-specific
    Channels: int
    SampleRate: int
    ChannelLayout: str
```

#### 13.1.4 PlaybackInfoResponse TypedDict
```python
class PlaybackInfoResponse(TypedDict):
    """Response from PlaybackInfo endpoint."""
    MediaSources: list[MediaSourceInfo]
    PlaySessionId: str
    ErrorCode: str | None
```

**Tests:**
- [x] Type annotation validation
- [x] Optional field handling

---

### Task 13.2: Device Profile TypedDicts

**Files:** `custom_components/embymedia/const.py`

#### 13.2.1 DirectPlayProfile TypedDict
```python
class DirectPlayProfile(TypedDict, total=False):
    """Direct play capability declaration."""
    Container: str  # Comma-separated: "mp4,mkv,webm"
    VideoCodec: str  # Comma-separated: "h264,hevc"
    AudioCodec: str  # Comma-separated: "aac,mp3,ac3"
    Type: str  # "Video", "Audio", "Photo"
```

#### 13.2.2 TranscodingProfile TypedDict
```python
class TranscodingProfile(TypedDict, total=False):
    """Transcoding fallback configuration."""
    Container: str
    Type: str  # "Video", "Audio"
    VideoCodec: str
    AudioCodec: str
    Protocol: str  # "hls" or empty for progressive
    Context: str  # "Streaming" or "Static"
    MaxAudioChannels: str
    MinSegments: int
    SegmentLength: int
    BreakOnNonKeyFrames: bool
    TranscodeSeekInfo: str  # "Auto" or "Bytes"
    CopyTimestamps: bool
```

#### 13.2.3 SubtitleProfile TypedDict
```python
class SubtitleProfile(TypedDict, total=False):
    """Subtitle delivery options."""
    Format: str  # "srt", "vtt", "ass"
    Method: str  # "Encode", "Embed", "External", "Hls"
    Language: str
```

#### 13.2.4 DeviceProfile TypedDict
```python
class DeviceProfile(TypedDict, total=False):
    """Device capability profile for playback negotiation."""
    Name: str
    Id: str
    MaxStreamingBitrate: int
    MaxStaticBitrate: int
    MusicStreamingTranscodingBitrate: int
    DirectPlayProfiles: list[DirectPlayProfile]
    TranscodingProfiles: list[TranscodingProfile]
    SubtitleProfiles: list[SubtitleProfile]
```

**Tests:**
- [x] Type annotation validation

---

### Task 13.3: Predefined Device Profiles

**Files:** `custom_components/embymedia/profiles.py` (new file)

Create predefined device profiles for common cast targets.

#### 13.3.1 UNIVERSAL_PROFILE
Safe fallback profile that works on most devices:
```python
UNIVERSAL_PROFILE: DeviceProfile = {
    "Name": "Home Assistant Universal",
    "MaxStreamingBitrate": 40_000_000,  # 40 Mbps
    "DirectPlayProfiles": [
        {
            "Container": "mp4,m4v",
            "VideoCodec": "h264",
            "AudioCodec": "aac,mp3",
            "Type": "Video",
        },
        {
            "Container": "mp3,aac,m4a,flac",
            "AudioCodec": "mp3,aac,flac",
            "Type": "Audio",
        },
    ],
    "TranscodingProfiles": [
        {
            "Container": "ts",
            "Type": "Video",
            "VideoCodec": "h264",
            "AudioCodec": "aac",
            "Protocol": "hls",
            "Context": "Streaming",
            "MaxAudioChannels": "2",
            "SegmentLength": 6,
            "MinSegments": 1,
            "BreakOnNonKeyFrames": True,
        },
        {
            "Container": "mp3",
            "Type": "Audio",
            "AudioCodec": "mp3",
            "Context": "Streaming",
        },
    ],
    "SubtitleProfiles": [
        {"Format": "srt", "Method": "External"},
        {"Format": "vtt", "Method": "External"},
    ],
}
```

#### 13.3.2 CHROMECAST_PROFILE
Optimized for Chromecast devices:
```python
CHROMECAST_PROFILE: DeviceProfile = {
    "Name": "Chromecast",
    "MaxStreamingBitrate": 20_000_000,  # 20 Mbps
    "DirectPlayProfiles": [
        {
            "Container": "mp4,webm",
            "VideoCodec": "h264,vp8,vp9",
            "AudioCodec": "aac,mp3,vorbis,opus",
            "Type": "Video",
        },
    ],
    "TranscodingProfiles": [
        {
            "Container": "ts",
            "Type": "Video",
            "VideoCodec": "h264",
            "AudioCodec": "aac",
            "Protocol": "hls",
            "MaxAudioChannels": "2",
        },
    ],
    ...
}
```

#### 13.3.3 ROKU_PROFILE, APPLETV_PROFILE, AUDIO_ONLY_PROFILE

Similar structure tailored to each device's capabilities.

**Tests:**
- [x] Profile validation (required fields present)
- [x] Profile compatibility checks

---

### Task 13.4: PlaybackInfo API Method

**Files:** `custom_components/embymedia/api.py`

#### 13.4.1 Add async_get_playback_info method
```python
async def async_get_playback_info(
    self,
    item_id: str,
    user_id: str,
    device_profile: DeviceProfile | None = None,
    max_streaming_bitrate: int = 40_000_000,
    start_position_ticks: int = 0,
    audio_stream_index: int | None = None,
    subtitle_stream_index: int | None = None,
    enable_direct_play: bool = True,
    enable_direct_stream: bool = True,
    enable_transcoding: bool = True,
) -> PlaybackInfoResponse:
    """Get playback information for an item.

    Uses the PlaybackInfo endpoint to determine the optimal playback
    method (direct play, direct stream, or transcoding) based on the
    provided device profile.

    Args:
        item_id: The media item ID.
        user_id: The user ID.
        device_profile: Device capability profile. Uses UNIVERSAL_PROFILE if None.
        max_streaming_bitrate: Maximum bitrate in bits per second.
        start_position_ticks: Starting position in ticks.
        audio_stream_index: Audio track to select.
        subtitle_stream_index: Subtitle track to select.
        enable_direct_play: Allow direct play.
        enable_direct_stream: Allow direct streaming.
        enable_transcoding: Allow transcoding.

    Returns:
        PlaybackInfoResponse with MediaSources and PlaySessionId.
    """
    ...
```

#### 13.4.2 Add async_stop_transcoding method
```python
async def async_stop_transcoding(
    self,
    device_id: str,
    play_session_id: str | None = None,
) -> None:
    """Stop active transcoding for a device.

    Should be called when playback ends to release server resources.

    Args:
        device_id: The device ID that was transcoding.
        play_session_id: Optional specific session to stop.
    """
    endpoint = f"/Videos/ActiveEncodings?DeviceId={device_id}"
    if play_session_id:
        endpoint += f"&PlaySessionId={play_session_id}"
    await self._request_delete(endpoint)
```

#### 13.4.3 Add get_universal_audio_url method
```python
def get_universal_audio_url(
    self,
    item_id: str,
    user_id: str,
    device_id: str,
    max_streaming_bitrate: int = 320_000,
    container: str = "opus,mp3,aac,m4a,flac,wav,ogg",
    transcoding_container: str = "mp3",
    transcoding_protocol: str = "",  # Empty for progressive, "hls" for HLS
    audio_codec: str = "mp3",
    max_sample_rate: int = 48000,
    play_session_id: str | None = None,
) -> str:
    """Generate universal audio streaming URL.

    The server decides between direct play and transcoding based on
    the provided container formats and device capabilities.
    """
    ...
```

**Tests:**
- [x] Test async_get_playback_info with mock responses
- [x] Test direct play scenario
- [x] Test direct stream scenario
- [x] Test transcoding scenario
- [x] Test async_stop_transcoding
- [x] Test get_universal_audio_url generation
- [x] Test error handling (item not found, auth failure)

---

### Task 13.5: Enhanced Media Source Resolution

**Files:** `custom_components/embymedia/media_source.py`

#### 13.5.1 Update async_resolve_media to use PlaybackInfo
```python
async def async_resolve_media(
    self,
    item: MediaSourceItem,
) -> PlayMedia:
    """Resolve media item to a playable URL with transcoding support.

    Uses the PlaybackInfo API to determine the optimal playback method:
    1. Direct Stream if format is compatible
    2. HLS Transcoding if format conversion needed

    Returns appropriate URL and MIME type for the stream.
    """
    ...

    # Get playback info with device profile
    playback_info = await coordinator.client.async_get_playback_info(
        item_id=item_id,
        user_id=user_id,
        device_profile=self._get_device_profile(coordinator),
    )

    # Select best media source
    media_source = self._select_media_source(playback_info["MediaSources"])

    # Determine URL and MIME type
    if media_source["SupportsDirectStream"]:
        url = self._build_direct_stream_url(coordinator, media_source)
        mime_type = self._get_mime_type_for_container(media_source["Container"])
    else:
        # Use transcoding URL from response
        url = self._build_transcoding_url(coordinator, media_source)
        mime_type = "application/x-mpegURL"  # HLS

    return PlayMedia(url=url, mime_type=mime_type)
```

#### 13.5.2 Add helper methods
```python
def _get_device_profile(
    self,
    coordinator: EmbyDataUpdateCoordinator,
) -> DeviceProfile:
    """Get device profile from config or use default."""
    ...

def _select_media_source(
    self,
    media_sources: list[MediaSourceInfo],
) -> MediaSourceInfo:
    """Select the best media source from available options."""
    # Prefer direct stream capable sources
    # Fall back to transcoding-capable sources
    ...

def _build_direct_stream_url(
    self,
    coordinator: EmbyDataUpdateCoordinator,
    media_source: MediaSourceInfo,
) -> str:
    """Build authenticated direct stream URL."""
    ...

def _build_transcoding_url(
    self,
    coordinator: EmbyDataUpdateCoordinator,
    media_source: MediaSourceInfo,
) -> str:
    """Build authenticated transcoding URL from TranscodingUrl."""
    ...

def _get_mime_type_for_container(
    self,
    container: str,
) -> str:
    """Get MIME type for container format."""
    ...
```

**Tests:**
- [x] Test async_resolve_media with direct stream response
- [x] Test async_resolve_media with transcoding response
- [x] Test media source selection logic
- [x] Test URL building with authentication
- [x] Test MIME type mapping
- [x] Test audio resolution
- [x] Test error cases

---

### Task 13.6: Configuration Options

**Files:**
- `custom_components/embymedia/const.py`
- `custom_components/embymedia/config_flow.py`
- `custom_components/embymedia/strings.json`
- `custom_components/embymedia/translations/en.json`

#### 13.6.1 Add constants
```python
# Transcoding configuration keys
CONF_TRANSCODING_PROFILE = "transcoding_profile"
CONF_MAX_STREAMING_BITRATE = "max_streaming_bitrate"
CONF_PREFER_DIRECT_PLAY = "prefer_direct_play"
CONF_MAX_VIDEO_WIDTH = "max_video_width"
CONF_MAX_VIDEO_HEIGHT = "max_video_height"

# Defaults
DEFAULT_TRANSCODING_PROFILE = "universal"
DEFAULT_MAX_STREAMING_BITRATE = 40_000_000  # 40 Mbps
DEFAULT_PREFER_DIRECT_PLAY = True
DEFAULT_MAX_VIDEO_WIDTH = 1920
DEFAULT_MAX_VIDEO_HEIGHT = 1080

# Profile choices
TRANSCODING_PROFILES = ["universal", "chromecast", "roku", "appletv", "audio_only"]
```

#### 13.6.2 Update Options Flow
Add transcoding options to the options flow step.

#### 13.6.3 Add translations
```json
{
  "options": {
    "step": {
      "init": {
        "data": {
          "transcoding_profile": "Transcoding Profile",
          "max_streaming_bitrate": "Maximum Streaming Bitrate (Mbps)",
          "prefer_direct_play": "Prefer Direct Play",
          "max_video_width": "Maximum Video Width",
          "max_video_height": "Maximum Video Height"
        },
        "data_description": {
          "transcoding_profile": "Target device profile for format negotiation",
          "max_streaming_bitrate": "Maximum bitrate for streaming (40 Mbps default)",
          "prefer_direct_play": "Prefer direct playback when format is compatible"
        }
      }
    }
  }
}
```

**Tests:**
- [x] Test options flow with new options
- [x] Test default values
- [x] Test configuration loading

---

### Task 13.7: Transcoding Session Management

**Files:**
- `custom_components/embymedia/media_source.py`
- `custom_components/embymedia/__init__.py`

#### 13.7.1 Track active sessions
```python
class EmbyMediaSource(MediaSource):
    """Emby media source with transcoding session tracking."""

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(DOMAIN)
        self.hass = hass
        self._active_sessions: dict[str, str] = {}  # play_session_id -> device_id
```

#### 13.7.2 Session cleanup on unload
```python
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Stop any active transcoding sessions
    coordinator = entry.runtime_data.session_coordinator
    media_source = hass.data.get(DATA_MEDIA_SOURCE)
    if media_source:
        await media_source.async_cleanup_sessions(coordinator)
    ...
```

**Tests:**
- [x] Test session tracking
- [x] Test cleanup on unload

---

### Task 13.8: Device ID Generation

**Files:** `custom_components/embymedia/const.py`, `custom_components/embymedia/media_source.py`

Generate a unique, stable device ID for the Home Assistant instance to identify transcoding sessions.

```python
def get_ha_device_id(hass: HomeAssistant) -> str:
    """Get stable device ID for Home Assistant instance."""
    # Use HA installation UUID for stability
    return f"homeassistant-{hass.data.get('core.uuid', 'unknown')}"
```

**Tests:**
- [x] Test device ID generation
- [x] Test stability across restarts

---

### Task 13.9: Audio Universal Endpoint Support

**Files:** `custom_components/embymedia/media_source.py`

#### 13.9.1 Update audio resolution to use universal endpoint
```python
async def _async_resolve_audio(
    self,
    coordinator: EmbyDataUpdateCoordinator,
    item_id: str,
    user_id: str,
) -> PlayMedia:
    """Resolve audio item using universal audio endpoint."""
    device_id = get_ha_device_id(self.hass)
    play_session_id = self._generate_play_session_id()

    url = coordinator.client.get_universal_audio_url(
        item_id=item_id,
        user_id=user_id,
        device_id=device_id,
        container="mp3,aac,m4a,flac,ogg",
        transcoding_container="mp3",
        audio_codec="mp3",
        play_session_id=play_session_id,
    )

    return PlayMedia(url=url, mime_type="audio/mpeg")
```

**Tests:**
- [x] Test audio resolution with universal endpoint
- [x] Test container negotiation

---

### Task 13.10: Testing

**Files:** `tests/test_media_source_transcoding.py` (new file)

#### Test Categories

1. **PlaybackInfo API Tests**
   - [x] Test request body construction
   - [x] Test response parsing
   - [x] Test error handling

2. **Device Profile Tests**
   - [x] Test UNIVERSAL_PROFILE structure
   - [x] Test CHROMECAST_PROFILE structure
   - [x] Test profile selection from config

3. **Media Resolution Tests**
   - [x] Test direct stream path
   - [x] Test HLS transcoding path
   - [x] Test audio universal endpoint
   - [x] Test MIME type selection

4. **Session Management Tests**
   - [x] Test session tracking
   - [x] Test session cleanup
   - [x] Test cleanup on integration unload

5. **Configuration Tests**
   - [x] Test options flow
   - [x] Test profile selection
   - [x] Test bitrate configuration

**Coverage:** 100% ✅ (1102 tests passing)

---

### Task 13.11: Documentation

**Files:** `README.md`, `docs/transcoding.md` (new file)

#### 13.11.1 Update README
- Add transcoding section
- Document supported devices
- Configuration options

#### 13.11.2 Create transcoding guide
- Explain how transcoding works
- Device profile descriptions
- Troubleshooting guide

---

## Files Summary

### New Files
| File | Purpose |
|------|---------|
| `custom_components/embymedia/profiles.py` | Predefined device profiles |
| `tests/test_media_source_transcoding.py` | Transcoding-specific tests |
| `docs/transcoding.md` | Transcoding documentation |

### Modified Files
| File | Changes |
|------|---------|
| `const.py` | TypedDicts, constants |
| `api.py` | PlaybackInfo, stop transcoding, universal audio |
| `media_source.py` | Enhanced resolution with PlaybackInfo |
| `config_flow.py` | Transcoding options |
| `__init__.py` | Session cleanup on unload |
| `strings.json` | Translations |
| `translations/en.json` | English translations |
| `README.md` | Documentation |

---

## Success Criteria

- [x] PlaybackInfo API integration working
- [x] Device profiles correctly sent to server
- [x] Direct stream used when compatible
- [x] HLS transcoding used when needed
- [x] Audio universal endpoint working
- [x] Transcoding sessions cleaned up properly
- [x] Configuration options in UI
- [x] 100% test coverage (1102 tests)
- [x] Documentation complete

---

## API Reference

### POST /Items/{id}/PlaybackInfo

**Request Body:**
```json
{
  "UserId": "user-uuid",
  "MaxStreamingBitrate": 40000000,
  "DeviceProfile": {
    "Name": "Home Assistant Universal",
    "DirectPlayProfiles": [...],
    "TranscodingProfiles": [...]
  },
  "EnableDirectPlay": true,
  "EnableDirectStream": true,
  "EnableTranscoding": true
}
```

**Response:**
```json
{
  "MediaSources": [
    {
      "Id": "source-id",
      "SupportsDirectStream": false,
      "SupportsTranscoding": true,
      "TranscodingUrl": "/Videos/{id}/master.m3u8?...",
      "TranscodingSubProtocol": "hls",
      "Container": "mkv",
      "MediaStreams": [...]
    }
  ],
  "PlaySessionId": "abc123"
}
```

### DELETE /Videos/ActiveEncodings

**Query Parameters:**
- `DeviceId` (required): Device identifier
- `PlaySessionId` (optional): Specific session to stop

---

## References

- [Emby Video Streaming API](https://dev.emby.media/doc/restapi/Video-Streaming.html)
- [Emby Audio Streaming API](https://dev.emby.media/doc/restapi/Audio-Streaming.html)
- [Emby PlaybackInfo API](https://dev.emby.media/reference/RestAPI/MediaInfoService/postItemsByIdPlaybackinfo.html)
- [Emby HTTP Live Streaming](https://dev.emby.media/doc/restapi/Http-Live-Streaming.html)
