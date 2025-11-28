"""Data models for Emby integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from .api import ticks_to_seconds

if TYPE_CHECKING:
    from .const import EmbyNowPlayingItem, EmbyPlayState, EmbySessionResponse


class MediaType(StrEnum):
    """Media type enumeration.

    Maps to Emby's Type field in media items.
    """

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

    Represents a media item from an Emby session's NowPlayingItem.
    Uses frozen=True for immutability and slots=True for memory efficiency.

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
        artists: Tuple of artists for audio.
        year: Production year.
        overview: Description/overview text.
        image_tags: Tuple of (tag_type, tag_value) pairs for image cache busting.
        series_id: ID of the parent series (for episodes) for image fallback.
        season_id: ID of the parent season (for episodes) for image fallback.
        album_id: ID of the parent album (for audio) for image fallback.
        parent_backdrop_image_tags: Tuple of backdrop image tags from parent.
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
    image_tags: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    series_id: str | None = None
    season_id: str | None = None
    album_id: str | None = None
    parent_backdrop_image_tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class EmbyPlaybackState:
    """Current playback state.

    Represents the PlayState from an Emby session.

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


@dataclass(frozen=True, slots=True)
class EmbySession:
    """Emby session representing a connected client.

    Represents a session from the /Sessions endpoint.

    Attributes:
        session_id: Unique session identifier (changes on reconnection).
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
        playable_media_types: Tuple of media types this client can play.
        supported_commands: Tuple of commands this client supports.
        queue_item_ids: Tuple of item IDs in the playback queue.
        queue_position: Current position in the queue (0-based).
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
    queue_item_ids: tuple[str, ...] = field(default_factory=tuple)
    queue_position: int = 0

    @property
    def is_active(self) -> bool:
        """Return True if session has recent activity.

        Sessions are considered active if their last activity
        was within the last 5 minutes.

        Returns:
            True if activity within last 5 minutes, False otherwise.
        """
        if self.last_activity is None:
            return False
        # Use UTC for comparison
        now = datetime.now(UTC)
        # Handle naive datetimes by assuming UTC
        last = (
            self.last_activity
            if self.last_activity.tzinfo is not None
            else self.last_activity.replace(tzinfo=UTC)
        )
        age = now - last
        return age.total_seconds() < 300  # 5 minutes

    @property
    def is_playing(self) -> bool:
        """Return True if something is currently playing.

        Returns:
            True if now_playing is set, False otherwise.
        """
        return self.now_playing is not None

    @property
    def unique_id(self) -> str:
        """Return unique identifier for entity creation.

        Uses device_id which is stable across reconnections,
        not session_id which changes each connection.

        Returns:
            The device_id for stable entity identification.
        """
        return self.device_id


# =============================================================================
# Parser Functions
# =============================================================================


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

    parent_backdrop_tags = data.get("ParentBackdropImageTags", [])

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
        series_id=data.get("SeriesId"),
        season_id=data.get("SeasonId"),
        album_id=data.get("AlbumId"),
        parent_backdrop_image_tags=tuple(parent_backdrop_tags),
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
        # Parse ISO format datetime, handle Z suffix
        last_activity = datetime.fromisoformat(last_activity_str.replace("Z", "+00:00"))

    # Parse queue data
    queue_data = data.get("NowPlayingQueue", [])
    queue_item_ids: tuple[str, ...] = tuple(item["Id"] for item in queue_data if "Id" in item)

    # Find current position in queue
    queue_position = 0
    if now_playing and queue_item_ids:
        current_item_id = now_playing.item_id
        if current_item_id in queue_item_ids:
            queue_position = queue_item_ids.index(current_item_id)

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
        queue_item_ids=queue_item_ids,
        queue_position=queue_position,
    )


__all__ = [
    "EmbyMediaItem",
    "EmbyPlaybackState",
    "EmbySession",
    "MediaType",
    "parse_media_item",
    "parse_play_state",
    "parse_session",
]
