# Phase 2: Data Coordinator & Entity Management - Detailed Tasks

> **Reference:** [Roadmap - Phase 2](./roadmap.md#phase-2-data-coordinator--entity-management)
>
> **Goal:** Implement the data update coordinator for polling Emby sessions, create typed data models for session/player data, build the base entity class, and establish dynamic entity lifecycle management.
>
> **Prerequisites:** Phase 1 complete (API client, config flow, integration setup)
>
> **Deliverables:**
> - Media player entities automatically appear/disappear based on active sessions
> - Entities update state via coordinator polling
> - Clean entity lifecycle management with proper cleanup

---

## Table of Contents

1. [Task 2.1: Session & Player TypedDicts](#task-21-session--player-typeddicts)
2. [Task 2.2: Session & Player Models](#task-22-session--player-models)
3. [Task 2.3: API Client Sessions Endpoint](#task-23-api-client-sessions-endpoint)
4. [Task 2.4: Data Update Coordinator](#task-24-data-update-coordinator)
5. [Task 2.5: Base Entity](#task-25-base-entity)
6. [Task 2.6: Media Player Entity Shell](#task-26-media-player-entity-shell)
7. [Task 2.7: Dynamic Entity Registry](#task-27-dynamic-entity-registry)
8. [Task 2.8: Integration Setup Updates](#task-28-integration-setup-updates)
9. [Acceptance Criteria](#acceptance-criteria)
10. [Dependencies](#dependencies)

---

## Task 2.1: Session & Player TypedDicts

### Overview

Define TypedDicts in `const.py` for the raw API responses from the `/Sessions` endpoint. These represent the external data structure from Emby.

### Subtasks

#### 2.1.1 Add EmbySessionResponse TypedDict

**File:** `custom_components/emby/const.py`

```python
class EmbyNowPlayingItem(TypedDict):
    """Type definition for NowPlayingItem in session response."""

    Id: str
    Name: str
    Type: str  # "Movie", "Episode", "Audio", etc.
    RunTimeTicks: NotRequired[int]
    Overview: NotRequired[str]
    SeriesName: NotRequired[str]
    SeasonName: NotRequired[str]
    SeriesId: NotRequired[str]
    SeasonId: NotRequired[str]
    IndexNumber: NotRequired[int]  # Episode number
    ParentIndexNumber: NotRequired[int]  # Season number
    ProductionYear: NotRequired[int]
    Album: NotRequired[str]
    AlbumId: NotRequired[str]
    AlbumArtist: NotRequired[str]
    Artists: NotRequired[list[str]]
    ImageTags: NotRequired[dict[str, str]]
    BackdropImageTags: NotRequired[list[str]]
    ParentBackdropImageTags: NotRequired[list[str]]
    MediaType: NotRequired[str]  # "Video", "Audio"


class EmbyPlayState(TypedDict):
    """Type definition for PlayState in session response."""

    PositionTicks: NotRequired[int]
    CanSeek: NotRequired[bool]
    IsPaused: NotRequired[bool]
    IsMuted: NotRequired[bool]
    VolumeLevel: NotRequired[int]  # 0-100
    AudioStreamIndex: NotRequired[int]
    SubtitleStreamIndex: NotRequired[int]
    MediaSourceId: NotRequired[str]
    PlayMethod: NotRequired[str]  # "DirectPlay", "Transcode", etc.
    RepeatMode: NotRequired[str]


class EmbyDeviceInfo(TypedDict):
    """Type definition for device info in session response."""

    Id: str
    Name: str
    AppName: NotRequired[str]
    AppVersion: NotRequired[str]
    DeviceName: NotRequired[str]


class EmbySessionResponse(TypedDict):
    """Type definition for /Sessions endpoint response item."""

    Id: str
    UserId: NotRequired[str]
    UserName: NotRequired[str]
    Client: str  # Client app name
    DeviceId: str
    DeviceName: str
    DeviceType: NotRequired[str]
    ApplicationVersion: NotRequired[str]
    IsActive: NotRequired[bool]
    SupportsRemoteControl: bool
    NowPlayingItem: NotRequired[EmbyNowPlayingItem]
    PlayState: NotRequired[EmbyPlayState]
    LastActivityDate: NotRequired[str]
    PlayableMediaTypes: NotRequired[list[str]]
    SupportedCommands: NotRequired[list[str]]
```

**Acceptance Criteria:**
- [ ] All TypedDicts use `NotRequired` for optional fields
- [ ] Field names match Emby API exactly (PascalCase)
- [ ] No `Any` types used
- [ ] Docstrings explain purpose of each TypedDict

---

## Task 2.2: Session & Player Models

### Overview

Create dataclasses in `models.py` for internal representation of session/player data. These transform the raw API responses into clean internal models.

### Subtasks

#### 2.2.1 Create EmbyMediaItem Dataclass

**File:** `custom_components/emby/models.py`

```python
from dataclasses import dataclass, field
from enum import StrEnum


class MediaType(StrEnum):
    """Media type enumeration."""

    MOVIE = "Movie"
    EPISODE = "Episode"
    AUDIO = "Audio"
    MUSIC_VIDEO = "MusicVideo"
    TRAILER = "Trailer"
    PHOTO = "Photo"
    LIVE_TV = "TvChannel"
    UNKNOWN = "Unknown"


@dataclass(frozen=True, slots=True)
class EmbyMediaItem:
    """Currently playing media item.

    Attributes:
        item_id: Unique identifier for the media item.
        name: Display name of the item.
        media_type: Type of media (Movie, Episode, Audio, etc.).
        duration_seconds: Total duration in seconds, or None if unknown.
        series_name: Name of the series for episodes.
        season_name: Name of the season for episodes.
        episode_number: Episode number within season.
        season_number: Season number.
        album: Album name for audio.
        album_artist: Album artist for audio.
        artists: List of artists for audio.
        year: Production year.
        overview: Description/overview text.
        image_tags: Dictionary of image type to tag for cache busting.
    """

    item_id: str
    name: str
    media_type: MediaType
    duration_seconds: float | None = None
    series_name: str | None = None
    season_name: str | None = None
    episode_number: int | None = None
    season_number: int | None = None
    album: str | None = None
    album_artist: str | None = None
    artists: tuple[str, ...] = field(default_factory=tuple)
    year: int | None = None
    overview: str | None = None
    # Note: Using tuple of tuples instead of dict for frozen dataclass compatibility
    image_tags: tuple[tuple[str, str], ...] = field(default_factory=tuple)
```

**Test Requirements:**
- Test creation with all fields
- Test creation with minimal fields
- Test frozen immutability
- Test default values

#### 2.2.2 Create EmbyPlayState Dataclass

```python
@dataclass(frozen=True, slots=True)
class EmbyPlaybackState:
    """Current playback state.

    Attributes:
        position_seconds: Current position in seconds.
        can_seek: Whether seeking is supported.
        is_paused: Whether playback is paused.
        is_muted: Whether audio is muted.
        volume_level: Volume level 0.0-1.0, or None if unknown.
        play_method: How content is being played (DirectPlay, Transcode).
    """

    position_seconds: float = 0.0
    can_seek: bool = False
    is_paused: bool = False
    is_muted: bool = False
    volume_level: float | None = None
    play_method: str | None = None
```

#### 2.2.3 Create EmbySession Dataclass

```python
from datetime import datetime


@dataclass(frozen=True, slots=True)
class EmbySession:
    """Emby session representing a connected client.

    Attributes:
        session_id: Unique session identifier.
        device_id: Unique device identifier (stable across reconnections).
        device_name: Human-readable device name.
        client_name: Client application name (e.g., "Emby Theater").
        user_id: ID of the logged-in user, or None if no user.
        user_name: Name of the logged-in user.
        supports_remote_control: Whether the client accepts remote commands.
        now_playing: Currently playing media, or None if idle.
        play_state: Current playback state, or None if not playing.
        last_activity: Timestamp of last activity.
        app_version: Client application version.
        playable_media_types: List of media types this client can play.
        supported_commands: List of commands this client supports.
    """

    session_id: str
    device_id: str
    device_name: str
    client_name: str
    user_id: str | None = None
    user_name: str | None = None
    supports_remote_control: bool = False
    now_playing: EmbyMediaItem | None = None
    play_state: EmbyPlaybackState | None = None
    last_activity: datetime | None = None
    app_version: str | None = None
    playable_media_types: tuple[str, ...] = field(default_factory=tuple)
    supported_commands: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_active(self) -> bool:
        """Return True if session has recent activity."""
        if self.last_activity is None:
            return False
        # Consider active if activity within last 5 minutes
        # Use UTC for comparison to handle timezone-aware datetimes
        from datetime import timezone
        now = datetime.now(timezone.utc)
        last = self.last_activity.replace(tzinfo=timezone.utc) if self.last_activity.tzinfo is None else self.last_activity
        age = now - last
        return age.total_seconds() < 300

    @property
    def is_playing(self) -> bool:
        """Return True if something is currently playing."""
        return self.now_playing is not None

    @property
    def unique_id(self) -> str:
        """Return unique identifier for entity creation.

        Uses device_id which is stable across reconnections,
        not session_id which changes each connection.
        """
        return self.device_id
```

#### 2.2.4 Create Parser Functions

```python
from .const import (
    EmbyNowPlayingItem,
    EmbyPlayState,
    EmbySessionResponse,
)
from .api import ticks_to_seconds


def parse_media_item(data: EmbyNowPlayingItem) -> EmbyMediaItem:
    """Parse API response into EmbyMediaItem.

    Args:
        data: Raw NowPlayingItem from API response.

    Returns:
        Parsed EmbyMediaItem instance.
    """
    runtime_ticks = data.get("RunTimeTicks")
    duration = ticks_to_seconds(runtime_ticks) if runtime_ticks else None

    media_type_str = data.get("Type", "Unknown")
    try:
        media_type = MediaType(media_type_str)
    except ValueError:
        media_type = MediaType.UNKNOWN

    return EmbyMediaItem(
        item_id=data["Id"],
        name=data["Name"],
        media_type=media_type,
        duration_seconds=duration,
        series_name=data.get("SeriesName"),
        season_name=data.get("SeasonName"),
        episode_number=data.get("IndexNumber"),
        season_number=data.get("ParentIndexNumber"),
        album=data.get("Album"),
        album_artist=data.get("AlbumArtist"),
        artists=tuple(data.get("Artists", [])),
        year=data.get("ProductionYear"),
        overview=data.get("Overview"),
        image_tags=tuple(data.get("ImageTags", {}).items()),
    )


def parse_play_state(data: EmbyPlayState) -> EmbyPlaybackState:
    """Parse API response into EmbyPlaybackState.

    Args:
        data: Raw PlayState from API response.

    Returns:
        Parsed EmbyPlaybackState instance.
    """
    position_ticks = data.get("PositionTicks", 0)
    volume = data.get("VolumeLevel")

    return EmbyPlaybackState(
        position_seconds=ticks_to_seconds(position_ticks),
        can_seek=data.get("CanSeek", False),
        is_paused=data.get("IsPaused", False),
        is_muted=data.get("IsMuted", False),
        volume_level=volume / 100.0 if volume is not None else None,
        play_method=data.get("PlayMethod"),
    )


def parse_session(data: EmbySessionResponse) -> EmbySession:
    """Parse API response into EmbySession.

    Args:
        data: Raw session from API response.

    Returns:
        Parsed EmbySession instance.
    """
    now_playing_data = data.get("NowPlayingItem")
    play_state_data = data.get("PlayState")

    now_playing = parse_media_item(now_playing_data) if now_playing_data else None
    play_state = parse_play_state(play_state_data) if play_state_data else None

    last_activity_str = data.get("LastActivityDate")
    last_activity = None
    if last_activity_str:
        # Parse ISO format datetime
        last_activity = datetime.fromisoformat(
            last_activity_str.replace("Z", "+00:00")
        )

    return EmbySession(
        session_id=data["Id"],
        device_id=data["DeviceId"],
        device_name=data["DeviceName"],
        client_name=data["Client"],
        user_id=data.get("UserId"),
        user_name=data.get("UserName"),
        supports_remote_control=data.get("SupportsRemoteControl", False),
        now_playing=now_playing,
        play_state=play_state,
        last_activity=last_activity,
        app_version=data.get("ApplicationVersion"),
        playable_media_types=tuple(data.get("PlayableMediaTypes", [])),
        supported_commands=tuple(data.get("SupportedCommands", [])),
    )
```

**Test Requirements:**
- Test parsing complete session data
- Test parsing session with no now_playing
- Test parsing session with minimal data
- Test media type enum fallback to UNKNOWN
- Test datetime parsing with various formats
- Test volume conversion (0-100 to 0.0-1.0)
- Test ticks to seconds conversion

---

## Task 2.3: API Client Sessions Endpoint

### Overview

Add the `/Sessions` endpoint to the API client for fetching active sessions.

### Subtasks

#### 2.3.1 Add async_get_sessions Method

**File:** `custom_components/emby/api.py`

Add to `EmbyClient` class:

```python
async def async_get_sessions(self) -> list[EmbySessionResponse]:
    """Get list of active sessions.

    Returns:
        List of session objects representing connected clients.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    response = await self._request(HTTP_GET, ENDPOINT_SESSIONS)
    return response  # type: ignore[return-value]
```

**File:** `custom_components/emby/const.py`

Constants needed (some may already exist):
```python
ENDPOINT_SESSIONS: Final = "/Sessions"
CONF_SCAN_INTERVAL: Final = "scan_interval"
```

**Test Requirements:**
- Test successful response with multiple sessions
- Test empty sessions list
- Test authentication error
- Test connection error

---

## Task 2.4: Data Update Coordinator

### Overview

Implement `EmbyDataUpdateCoordinator` extending Home Assistant's `DataUpdateCoordinator` to poll for session data on a configurable interval.

### Subtasks

#### 2.4.1 Implement EmbyDataUpdateCoordinator

**File:** `custom_components/emby/coordinator.py`

```python
"""Data update coordinator for Emby integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .exceptions import EmbyConnectionError, EmbyError
from .models import EmbySession, parse_session

if TYPE_CHECKING:
    from .api import EmbyClient
    from .const import EmbySessionResponse

_LOGGER = logging.getLogger(__name__)


class EmbyDataUpdateCoordinator(DataUpdateCoordinator[dict[str, EmbySession]]):
    """Coordinator for fetching Emby session data.

    This coordinator polls the Emby server for active sessions and
    maintains a dictionary mapping device_id to EmbySession.

    Using device_id (not session_id) as the key ensures entities
    persist across client reconnections.

    Attributes:
        client: The Emby API client instance.
        server_id: The Emby server ID.
        server_name: The Emby server name.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: EmbyClient,
        server_id: str,
        server_name: str,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance.
            client: Emby API client.
            server_id: Unique server identifier.
            server_name: Human-readable server name.
            scan_interval: Polling interval in seconds.
        """
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{server_id}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.server_id = server_id
        self.server_name = server_name
        self._previous_sessions: set[str] = set()

    async def _async_update_data(self) -> dict[str, EmbySession]:
        """Fetch session data from Emby server.

        Returns:
            Dictionary mapping device_id to EmbySession.

        Raises:
            UpdateFailed: If fetching data fails.
        """
        try:
            sessions_data: list[EmbySessionResponse] = (
                await self.client.async_get_sessions()
            )
        except EmbyConnectionError as err:
            raise UpdateFailed(f"Failed to connect to Emby server: {err}") from err
        except EmbyError as err:
            raise UpdateFailed(f"Error fetching sessions: {err}") from err

        # Parse sessions and index by device_id
        sessions: dict[str, EmbySession] = {}
        for session_data in sessions_data:
            try:
                session = parse_session(session_data)
                # Filter to only sessions that support remote control
                # These are the ones we can create media players for
                if session.supports_remote_control:
                    sessions[session.device_id] = session
            except (KeyError, ValueError) as err:
                _LOGGER.warning(
                    "Failed to parse session data: %s - %s",
                    err,
                    session_data.get("DeviceName", "Unknown"),
                )
                continue

        # Log session changes
        current_devices = set(sessions.keys())
        added = current_devices - self._previous_sessions
        removed = self._previous_sessions - current_devices

        for device_id in added:
            session = sessions[device_id]
            _LOGGER.debug(
                "New session detected: %s (%s)",
                session.device_name,
                session.client_name,
            )

        for device_id in removed:
            _LOGGER.debug("Session removed: %s", device_id)

        self._previous_sessions = current_devices

        return sessions

    def get_session(self, device_id: str) -> EmbySession | None:
        """Get a specific session by device ID.

        Args:
            device_id: The device ID to look up.

        Returns:
            The session if found, None otherwise.
        """
        if self.data is None:
            return None
        return self.data.get(device_id)
```

**Test Requirements:**
- Test successful data fetch and parsing
- Test connection error raises UpdateFailed
- Test session filtering (only supports_remote_control)
- Test session addition/removal logging
- Test get_session helper
- Test scan interval configuration

---

## Task 2.5: Base Entity

### Overview

Create `EmbyEntity` base class that extends `CoordinatorEntity` and provides common functionality for all Emby entities.

### Subtasks

#### 2.5.1 Create EmbyEntity Base Class

**File:** `custom_components/emby/entity.py`

```python
"""Base entity for Emby integration."""
from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

if TYPE_CHECKING:
    from .coordinator import EmbyDataUpdateCoordinator
    from .models import EmbySession


class EmbyEntity(CoordinatorEntity["EmbyDataUpdateCoordinator"]):
    """Base class for Emby entities.

    Provides common functionality including:
    - Device info generation
    - Unique ID management
    - Availability based on session presence
    - Session data access

    Attributes:
        _device_id: The stable device identifier.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the entity.

        Args:
            coordinator: The data update coordinator.
            device_id: The stable device identifier for this entity.
        """
        super().__init__(coordinator)
        self._device_id = device_id

    @property
    def session(self) -> EmbySession | None:
        """Return the current session data.

        Returns:
            The session if available, None otherwise.
        """
        return self.coordinator.get_session(self._device_id)

    @property
    def available(self) -> bool:
        """Return True if entity is available.

        Entity is available when:
        - Coordinator has data
        - Session exists in coordinator data
        """
        return (
            self.coordinator.last_update_success
            and self.session is not None
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information.

        Returns:
            DeviceInfo for device registry.
        """
        session = self.session
        if session is None:
            # Fallback device info when session not available
            return DeviceInfo(
                identifiers={(DOMAIN, self._device_id)},
                name=f"Emby Client {self._device_id[:8]}",
                manufacturer="Emby",
                via_device=(DOMAIN, self.coordinator.server_id),
            )

        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=session.device_name,
            manufacturer="Emby",
            model=session.client_name,
            sw_version=session.app_version,
            via_device=(DOMAIN, self.coordinator.server_id),
        )

    @property
    def unique_id(self) -> str:
        """Return unique ID for the entity.

        Uses device_id which persists across session reconnections.
        """
        return f"{self.coordinator.server_id}_{self._device_id}"
```

**Test Requirements:**
- Test device_info with active session
- Test device_info without session (fallback)
- Test availability when session present
- Test availability when session missing
- Test availability when coordinator failed
- Test unique_id generation

---

## Task 2.6: Media Player Entity Shell

### Overview

Create the basic `EmbyMediaPlayer` class structure. Full implementation happens in Phase 3, but we need the shell for entity lifecycle in Phase 2.

### Subtasks

#### 2.6.1 Create EmbyMediaPlayer Shell

**File:** `custom_components/emby/media_player.py`

```python
"""Media player platform for Emby integration."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerState,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import EmbyEntity

if TYPE_CHECKING:
    from .const import EmbyConfigEntry
    from .coordinator import EmbyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EmbyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Emby media player from config entry.

    Args:
        hass: Home Assistant instance.
        entry: Config entry being set up.
        async_add_entities: Callback to add entities.
    """
    coordinator = entry.runtime_data
    _LOGGER.debug("Setting up Emby media player platform")

    # Track which entities we've created
    known_devices: set[str] = set()

    @callback
    def async_add_new_entities() -> None:
        """Add entities for new sessions."""
        if coordinator.data is None:
            return

        new_entities: list[EmbyMediaPlayer] = []
        for device_id in coordinator.data:
            if device_id not in known_devices:
                _LOGGER.debug("Adding media player for device: %s", device_id)
                known_devices.add(device_id)
                new_entities.append(EmbyMediaPlayer(coordinator, device_id))

        if new_entities:
            async_add_entities(new_entities)

    # Add entities for existing sessions
    async_add_new_entities()

    # Listen for coordinator updates to add new entities
    entry.async_on_unload(
        coordinator.async_add_listener(async_add_new_entities)
    )


class EmbyMediaPlayer(EmbyEntity, MediaPlayerEntity):
    """Representation of an Emby media player.

    This entity represents a single Emby client session that can
    play media. Full playback control is implemented in Phase 3.
    """

    _attr_name = None  # Use device name

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the media player.

        Args:
            coordinator: The data update coordinator.
            device_id: The stable device identifier.
        """
        super().__init__(coordinator, device_id)

    @property
    def state(self) -> MediaPlayerState:
        """Return the state of the player.

        Returns:
            Current player state.
        """
        session = self.session
        if session is None:
            return MediaPlayerState.OFF

        if not session.is_playing:
            return MediaPlayerState.IDLE

        if session.play_state and session.play_state.is_paused:
            return MediaPlayerState.PAUSED

        return MediaPlayerState.PLAYING
```

**Test Requirements:**
- Test state mapping (OFF, IDLE, PAUSED, PLAYING)
- Test entity creation from coordinator
- Test entity addition on coordinator update
- Test entity uses device name

---

## Task 2.7: Dynamic Entity Registry

### Overview

Implement the mechanism for detecting session changes and managing entity lifecycle. Entities should be added when new sessions appear and marked unavailable when sessions disappear.

### Design Decision

**Approach:** Entities become unavailable (not removed) when sessions disappear. This prevents constant entity ID churn and allows automations to reference entities that might temporarily disconnect.

**Entity removal:** Only happens on integration unload or explicit user action.

### Subtasks

#### 2.7.1 Entity Lifecycle is Already Implemented

The entity lifecycle is handled in `media_player.py`:

1. **Initial load:** `async_setup_entry` creates entities for existing sessions
2. **New sessions:** Coordinator listener adds new entities
3. **Removed sessions:** Entity `available` property returns False
4. **Reconnecting clients:** Same device_id = same entity (no churn)

**Test Requirements:**
- Test entities created on setup for existing sessions
- Test new entity added when session appears
- Test entity becomes unavailable when session disappears
- Test entity becomes available again when session returns
- Test reconnecting client uses same entity

---

## Task 2.8: Integration Setup Updates

### Overview

Update `__init__.py` to create the coordinator and pass it to the config entry runtime data.

### Subtasks

#### 2.8.1 Update async_setup_entry

**File:** `custom_components/emby/__init__.py`

Update to create coordinator:

```python
async def async_setup_entry(hass: HomeAssistant, entry: EmbyConfigEntry) -> bool:
    """Set up Emby from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    ssl = entry.data.get(CONF_SSL, DEFAULT_SSL)
    api_key = entry.data[CONF_API_KEY]
    verify_ssl = entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    session = async_get_clientsession(hass, verify_ssl=verify_ssl)
    client = EmbyClient(
        host=host,
        port=port,
        api_key=api_key,
        ssl=ssl,
        verify_ssl=verify_ssl,
        session=session,
    )

    # Validate connection and get server info
    try:
        server_info = await client.async_get_server_info()
    except EmbyError as err:
        raise ConfigEntryNotReady(f"Failed to connect to Emby server: {err}") from err

    server_id = server_info["Id"]
    server_name = server_info["ServerName"]

    # Create coordinator
    coordinator = EmbyDataUpdateCoordinator(
        hass=hass,
        client=client,
        server_id=server_id,
        server_name=server_name,
        scan_interval=scan_interval,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator in runtime data
    entry.runtime_data = coordinator

    # Forward to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener
    entry.async_on_unload(entry.add_update_listener(async_options_updated))

    _LOGGER.info(
        "Connected to Emby server: %s (version %s)",
        server_name,
        server_info["Version"],
    )

    return True
```

**Test Requirements:**
- Test coordinator created with correct parameters
- Test initial data fetch happens
- Test ConfigEntryNotReady on connection failure
- Test scan_interval from options

---

## Acceptance Criteria

### Phase 2 Complete When:

- [ ] All TypedDicts defined for session API responses
- [ ] All dataclasses implemented with parser functions
- [ ] API client has async_get_sessions method
- [ ] Coordinator fetches and parses sessions
- [ ] Base entity provides device info and availability
- [ ] Media player entities created for active sessions
- [ ] Entities become unavailable when sessions disappear
- [ ] Entities reuse same ID when clients reconnect
- [ ] 100% test coverage maintained
- [ ] All mypy and ruff checks pass
- [ ] Integration loads and creates entities successfully

### Manual Testing Checklist:

1. [ ] Install integration via config flow
2. [ ] Open Emby client (TV, phone, etc.)
3. [ ] Verify media player entity appears in HA
4. [ ] Start playing media
5. [ ] Verify entity state changes to PLAYING
6. [ ] Pause media
7. [ ] Verify entity state changes to PAUSED
8. [ ] Close Emby client
9. [ ] Verify entity state changes to OFF (unavailable)
10. [ ] Reopen same Emby client
11. [ ] Verify same entity becomes available again

---

## Dependencies

### From Phase 1:
- `api.py` - EmbyClient class
- `const.py` - Constants and TypedDicts
- `exceptions.py` - Custom exceptions
- `config_flow.py` - Configuration flow
- `__init__.py` - Integration setup

### External:
- `homeassistant.helpers.update_coordinator`
- `homeassistant.helpers.device_registry`
- `homeassistant.components.media_player`

### Phase 3 Dependencies:
- Phase 3 will extend `EmbyMediaPlayer` with:
  - Playback controls
  - Volume control
  - Media metadata properties
  - Supported features flags
