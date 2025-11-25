# Phase 3: Media Player Entity - Core Features - Detailed Tasks

> **Reference:** [Roadmap - Phase 3](./roadmap.md#phase-3-media-player-entity---core-features)
>
> **Goal:** Implement full media player functionality including playback control, volume management, and media metadata display.
>
> **Prerequisites:** Phase 1 (Foundation) and Phase 2 (Coordinator & Entity Management) complete
>
> **Deliverables:**
> - Full playback control of Emby clients
> - Volume management
> - Accurate state and metadata display

---

## Table of Contents

1. [Task 3.1: Media Player Properties](#task-31-media-player-properties)
2. [Task 3.2: Volume Control](#task-32-volume-control)
3. [Task 3.3: Playback Control](#task-33-playback-control)
4. [Task 3.4: API Client Extensions](#task-34-api-client-extensions)
5. [Acceptance Criteria](#acceptance-criteria)
6. [Dependencies](#dependencies)

---

## Task 3.1: Media Player Properties

### Overview

Implement all media player properties to display current playback information.

### Subtasks

#### 3.1.1 Implement MediaPlayerEntityFeature Flags

**File:** `custom_components/embymedia/media_player.py`

**Required Features:**
```python
from homeassistant.components.media_player import (
    MediaPlayerEntityFeature,
)

# Supported features for Emby players
SUPPORTED_FEATURES = (
    MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.PREVIOUS_TRACK
    | MediaPlayerEntityFeature.SEEK
    | MediaPlayerEntityFeature.PLAY_MEDIA
)
```

**Property Implementation:**
```python
@property
def supported_features(self) -> MediaPlayerEntityFeature:
    """Return the supported features."""
    session = self.session
    if session is None:
        return MediaPlayerEntityFeature(0)

    features = MediaPlayerEntityFeature(0)

    # Check session capabilities
    if session.supports_remote_control:
        features |= (
            MediaPlayerEntityFeature.PAUSE
            | MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.STOP
        )

        # Volume control if supported
        if "SetVolume" in session.supported_commands:
            features |= MediaPlayerEntityFeature.VOLUME_SET
        if "Mute" in session.supported_commands:
            features |= MediaPlayerEntityFeature.VOLUME_MUTE

        # Playback navigation
        if session.play_state and session.play_state.can_seek:
            features |= MediaPlayerEntityFeature.SEEK

        features |= (
            MediaPlayerEntityFeature.NEXT_TRACK
            | MediaPlayerEntityFeature.PREVIOUS_TRACK
            | MediaPlayerEntityFeature.PLAY_MEDIA
        )

    return features
```

**Acceptance Criteria:**
- [ ] `supported_features` property returns correct flags
- [ ] Features dynamically determined from session capabilities
- [ ] Returns 0 when session is None
- [ ] Volume features only enabled when commands supported
- [ ] Seek only enabled when `can_seek` is True

---

#### 3.1.2 Implement Media Content Properties

**File:** `custom_components/embymedia/media_player.py`

**Required Properties:**
```python
from homeassistant.components.media_player import MediaType

@property
def media_content_id(self) -> str | None:
    """Return the content ID of current playing media."""
    session = self.session
    if session is None or session.now_playing is None:
        return None
    return session.now_playing.item_id

@property
def media_content_type(self) -> MediaType | str | None:
    """Return the content type of current playing media."""
    session = self.session
    if session is None or session.now_playing is None:
        return None

    # Map Emby media types to HA media types
    media_type_map = {
        MediaType.MOVIE: MediaType.MOVIE,
        MediaType.EPISODE: MediaType.TVSHOW,
        MediaType.AUDIO: MediaType.MUSIC,
        MediaType.MUSIC_VIDEO: MediaType.VIDEO,
        MediaType.TRAILER: MediaType.VIDEO,
        MediaType.PHOTO: MediaType.IMAGE,
        MediaType.LIVE_TV: MediaType.CHANNEL,
    }

    return media_type_map.get(
        session.now_playing.media_type,
        MediaType.VIDEO
    )
```

**Acceptance Criteria:**
- [ ] `media_content_id` returns item ID when playing
- [ ] `media_content_id` returns None when not playing
- [ ] `media_content_type` maps Emby types to HA types correctly
- [ ] `media_content_type` returns None when not playing

---

#### 3.1.3 Implement Media Title Properties

**File:** `custom_components/embymedia/media_player.py`

**Required Properties:**
```python
@property
def media_title(self) -> str | None:
    """Return the title of current playing media."""
    session = self.session
    if session is None or session.now_playing is None:
        return None
    return session.now_playing.name

@property
def media_series_title(self) -> str | None:
    """Return the series title for TV episodes."""
    session = self.session
    if session is None or session.now_playing is None:
        return None
    return session.now_playing.series_name

@property
def media_season(self) -> str | None:
    """Return the season number."""
    session = self.session
    if session is None or session.now_playing is None:
        return None
    season = session.now_playing.season_number
    return str(season) if season is not None else None

@property
def media_episode(self) -> str | None:
    """Return the episode number."""
    session = self.session
    if session is None or session.now_playing is None:
        return None
    episode = session.now_playing.episode_number
    return str(episode) if episode is not None else None
```

**Acceptance Criteria:**
- [ ] `media_title` returns item name
- [ ] `media_series_title` returns series name for episodes
- [ ] `media_season` returns season number as string
- [ ] `media_episode` returns episode number as string
- [ ] All return None when not playing or not applicable

---

#### 3.1.4 Implement Music Metadata Properties

**File:** `custom_components/embymedia/media_player.py`

**Required Properties:**
```python
@property
def media_artist(self) -> str | None:
    """Return the artist of current playing media."""
    session = self.session
    if session is None or session.now_playing is None:
        return None

    artists = session.now_playing.artists
    if artists:
        return ", ".join(artists)
    return session.now_playing.album_artist

@property
def media_album_name(self) -> str | None:
    """Return the album of current playing media."""
    session = self.session
    if session is None or session.now_playing is None:
        return None
    return session.now_playing.album

@property
def media_album_artist(self) -> str | None:
    """Return the album artist of current playing media."""
    session = self.session
    if session is None or session.now_playing is None:
        return None
    return session.now_playing.album_artist
```

**Acceptance Criteria:**
- [ ] `media_artist` joins multiple artists with comma
- [ ] `media_artist` falls back to album_artist if no artists
- [ ] `media_album_name` returns album name
- [ ] `media_album_artist` returns album artist
- [ ] All return None when not playing music

---

#### 3.1.5 Implement Duration and Position Properties

**File:** `custom_components/embymedia/media_player.py`

**Required Properties:**
```python
from datetime import datetime
from homeassistant.util import dt as dt_util

@property
def media_duration(self) -> int | None:
    """Return the duration of current playing media in seconds."""
    session = self.session
    if session is None or session.now_playing is None:
        return None
    duration = session.now_playing.duration_seconds
    return int(duration) if duration is not None else None

@property
def media_position(self) -> int | None:
    """Return the current position in seconds."""
    session = self.session
    if session is None or session.play_state is None:
        return None
    return int(session.play_state.position_seconds)

@property
def media_position_updated_at(self) -> datetime | None:
    """Return when position was last updated."""
    session = self.session
    if session is None or session.play_state is None:
        return None
    # Use coordinator's last update time
    return dt_util.utcnow()
```

**Acceptance Criteria:**
- [ ] `media_duration` returns total duration in seconds as int
- [ ] `media_position` returns current position in seconds as int
- [ ] `media_position_updated_at` returns update timestamp
- [ ] All return None when not playing

---

## Task 3.2: Volume Control

### Overview

Implement volume level and mute properties and services.

### Subtasks

#### 3.2.1 Implement Volume Properties

**File:** `custom_components/embymedia/media_player.py`

**Required Properties:**
```python
@property
def volume_level(self) -> float | None:
    """Return the volume level (0.0 to 1.0)."""
    session = self.session
    if session is None or session.play_state is None:
        return None
    return session.play_state.volume_level

@property
def is_volume_muted(self) -> bool | None:
    """Return True if volume is muted."""
    session = self.session
    if session is None or session.play_state is None:
        return None
    return session.play_state.is_muted
```

**Acceptance Criteria:**
- [ ] `volume_level` returns 0.0-1.0 range
- [ ] `is_volume_muted` returns boolean
- [ ] Both return None when session/play_state is None

---

#### 3.2.2 Implement Volume Services

**File:** `custom_components/embymedia/media_player.py`

**Required Methods:**
```python
async def async_set_volume_level(self, volume: float) -> None:
    """Set volume level (0.0 to 1.0)."""
    session = self.session
    if session is None:
        return

    # Convert to 0-100 range for Emby
    volume_percent = int(volume * 100)
    await self.coordinator.client.async_send_command(
        session.session_id,
        "SetVolume",
        {"Volume": volume_percent},
    )

async def async_mute_volume(self, mute: bool) -> None:
    """Mute or unmute the volume."""
    session = self.session
    if session is None:
        return

    command = "Mute" if mute else "Unmute"
    await self.coordinator.client.async_send_command(
        session.session_id,
        command,
    )
```

**Acceptance Criteria:**
- [ ] `async_set_volume_level` converts to 0-100 range
- [ ] `async_set_volume_level` calls API correctly
- [ ] `async_mute_volume` sends Mute/Unmute command
- [ ] Methods handle missing session gracefully

---

## Task 3.3: Playback Control

### Overview

Implement playback control services for play, pause, stop, seek, and track navigation.

### Subtasks

#### 3.3.1 Implement Play/Pause/Stop Services

**File:** `custom_components/embymedia/media_player.py`

**Required Methods:**
```python
async def async_media_play(self) -> None:
    """Send play command."""
    session = self.session
    if session is None:
        return

    await self.coordinator.client.async_send_playback_command(
        session.session_id,
        "Unpause",
    )

async def async_media_pause(self) -> None:
    """Send pause command."""
    session = self.session
    if session is None:
        return

    await self.coordinator.client.async_send_playback_command(
        session.session_id,
        "Pause",
    )

async def async_media_stop(self) -> None:
    """Send stop command."""
    session = self.session
    if session is None:
        return

    await self.coordinator.client.async_send_playback_command(
        session.session_id,
        "Stop",
    )
```

**Acceptance Criteria:**
- [ ] `async_media_play` sends Unpause command
- [ ] `async_media_pause` sends Pause command
- [ ] `async_media_stop` sends Stop command
- [ ] All methods handle missing session gracefully

---

#### 3.3.2 Implement Track Navigation Services

**File:** `custom_components/embymedia/media_player.py`

**Required Methods:**
```python
async def async_media_next_track(self) -> None:
    """Send next track command."""
    session = self.session
    if session is None:
        return

    await self.coordinator.client.async_send_playback_command(
        session.session_id,
        "NextTrack",
    )

async def async_media_previous_track(self) -> None:
    """Send previous track command."""
    session = self.session
    if session is None:
        return

    await self.coordinator.client.async_send_playback_command(
        session.session_id,
        "PreviousTrack",
    )
```

**Acceptance Criteria:**
- [ ] `async_media_next_track` sends NextTrack command
- [ ] `async_media_previous_track` sends PreviousTrack command
- [ ] Both handle missing session gracefully

---

#### 3.3.3 Implement Seek Service

**File:** `custom_components/embymedia/media_player.py`

**Required Method:**
```python
from ..api import seconds_to_ticks

async def async_media_seek(self, position: float) -> None:
    """Seek to position in seconds."""
    session = self.session
    if session is None:
        return

    position_ticks = seconds_to_ticks(position)
    await self.coordinator.client.async_send_playback_command(
        session.session_id,
        "Seek",
        {"SeekPositionTicks": position_ticks},
    )
```

**Acceptance Criteria:**
- [ ] `async_media_seek` converts seconds to ticks
- [ ] Sends Seek command with SeekPositionTicks
- [ ] Handles missing session gracefully

---

## Task 3.4: API Client Extensions

### Overview

Add playback control methods to the EmbyClient.

### Subtasks

#### 3.4.1 Add Playback Command Methods

**File:** `custom_components/embymedia/api.py`

**Required Methods:**
```python
async def async_send_playback_command(
    self,
    session_id: str,
    command: str,
    args: dict[str, object] | None = None,
) -> None:
    """Send a playback command to a session.

    Args:
        session_id: The session ID to send command to.
        command: Playback command (Play, Pause, Stop, etc.).
        args: Optional command arguments.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    endpoint = f"/Sessions/{session_id}/Playing/{command}"
    await self._request_post(HTTP_POST, endpoint, data=args)

async def async_send_command(
    self,
    session_id: str,
    command: str,
    args: dict[str, object] | None = None,
) -> None:
    """Send a general command to a session.

    Args:
        session_id: The session ID to send command to.
        command: Command name (SetVolume, Mute, etc.).
        args: Optional command arguments.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    endpoint = f"/Sessions/{session_id}/Command/{command}"
    await self._request_post(HTTP_POST, endpoint, data=args)
```

**Acceptance Criteria:**
- [ ] `async_send_playback_command` sends to correct endpoint
- [ ] `async_send_command` sends to correct endpoint
- [ ] Both handle errors appropriately
- [ ] Arguments passed as POST body

---

#### 3.4.2 Add POST Request Support

**File:** `custom_components/embymedia/api.py`

**Required Method:**
```python
async def _request_post(
    self,
    method: str,
    endpoint: str,
    data: dict[str, object] | None = None,
) -> dict[str, object] | None:
    """Make a POST request to the Emby API.

    Args:
        method: HTTP method (POST).
        endpoint: API endpoint path.
        data: Optional JSON body.

    Returns:
        Parsed JSON response or None for empty responses.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: Authentication failed.
    """
    url = f"{self.base_url}{endpoint}"
    headers = self._get_headers()
    ssl_context = self._get_ssl_context()

    _LOGGER.debug(
        "Emby API POST request: %s (data=%s)",
        endpoint,
        data,
    )

    session = await self._get_session()

    try:
        async with session.post(
            url,
            headers=headers,
            json=data,
            ssl=ssl_context,
        ) as response:
            _LOGGER.debug(
                "Emby API response: %s %s for POST %s",
                response.status,
                response.reason,
                endpoint,
            )

            if response.status in (401, 403):
                raise EmbyAuthenticationError(
                    f"Authentication failed: {response.status}"
                )

            if response.status == 204:
                return None  # No content

            response.raise_for_status()

            # Some commands return no body
            content = await response.text()
            if not content:
                return None

            return await response.json()

    except aiohttp.ClientError as err:
        raise EmbyConnectionError(f"Request failed: {err}") from err
```

**Acceptance Criteria:**
- [ ] POST requests send JSON body
- [ ] Handles 204 No Content response
- [ ] Handles empty response body
- [ ] Proper error handling

---

## Acceptance Criteria

### Phase 3 Complete When:

1. **Media Properties**
   - [ ] `supported_features` dynamically determined
   - [ ] `media_content_id` returns item ID
   - [ ] `media_content_type` maps to HA types
   - [ ] `media_title` returns item name
   - [ ] `media_series_title` for TV episodes
   - [ ] `media_season` and `media_episode` for TV
   - [ ] `media_artist`, `media_album_name`, `media_album_artist` for music
   - [ ] `media_duration` and `media_position` in seconds
   - [ ] `media_position_updated_at` timestamp
   - [ ] 100% test coverage

2. **Volume Control**
   - [ ] `volume_level` returns 0.0-1.0
   - [ ] `is_volume_muted` returns boolean
   - [ ] `async_set_volume_level` works
   - [ ] `async_mute_volume` works
   - [ ] 100% test coverage

3. **Playback Control**
   - [ ] `async_media_play` works
   - [ ] `async_media_pause` works
   - [ ] `async_media_stop` works
   - [ ] `async_media_next_track` works
   - [ ] `async_media_previous_track` works
   - [ ] `async_media_seek` works
   - [ ] 100% test coverage

4. **API Extensions**
   - [ ] POST request support added
   - [ ] `async_send_playback_command` works
   - [ ] `async_send_command` works
   - [ ] 100% test coverage

5. **Code Quality**
   - [ ] mypy strict passes
   - [ ] ruff passes
   - [ ] No `Any` types (except required HA overrides)
   - [ ] All functions have type annotations
   - [ ] Google-style docstrings on all public functions

---

## Dependencies

### Phase 2 Components Required

| Component | Purpose |
|-----------|---------|
| `EmbyDataUpdateCoordinator` | Access to API client |
| `EmbySession` | Session data with playback state |
| `EmbyMediaItem` | Now playing media info |
| `EmbyPlaybackState` | Volume and position data |

### API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `POST /Sessions/{id}/Playing/{command}` | POST | Playback control |
| `POST /Sessions/{id}/Command/{command}` | POST | General commands |

### Emby Commands

| Command | Endpoint | Arguments |
|---------|----------|-----------|
| `Play` / `Unpause` | Playing | None |
| `Pause` | Playing | None |
| `Stop` | Playing | None |
| `NextTrack` | Playing | None |
| `PreviousTrack` | Playing | None |
| `Seek` | Playing | `{"SeekPositionTicks": int}` |
| `SetVolume` | Command | `{"Volume": 0-100}` |
| `Mute` | Command | None |
| `Unmute` | Command | None |

---

## Notes

### TDD Workflow Reminder

For every piece of code in this phase:

1. **RED** - Write a failing test first
2. **GREEN** - Write minimal code to pass
3. **REFACTOR** - Clean up while tests pass

No exceptions. See `ha-emby-tdd` skill for details.

### Media Type Mapping

| Emby Type | HA MediaType |
|-----------|--------------|
| `Movie` | `MediaType.MOVIE` |
| `Episode` | `MediaType.TVSHOW` |
| `Audio` | `MediaType.MUSIC` |
| `MusicVideo` | `MediaType.VIDEO` |
| `Trailer` | `MediaType.VIDEO` |
| `Photo` | `MediaType.IMAGE` |
| `TvChannel` | `MediaType.CHANNEL` |
| Unknown | `MediaType.VIDEO` |

### Time Conversion

Emby uses "ticks" where 10,000,000 ticks = 1 second.

- `ticks_to_seconds(ticks)` - Convert ticks to seconds
- `seconds_to_ticks(seconds)` - Convert seconds to ticks

Both functions are already in `api.py`.
