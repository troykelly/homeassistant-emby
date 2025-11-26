"""Constants for the Emby integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, NotRequired, TypedDict

from homeassistant.const import Platform

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .coordinator import EmbyDataUpdateCoordinator

# Integration domain
DOMAIN: Final = "embymedia"

# Type alias for config entry with runtime data
type EmbyConfigEntry = ConfigEntry[EmbyDataUpdateCoordinator]

# Configuration keys (use HA constants where available)
CONF_API_KEY: Final = "api_key"
CONF_USER_ID: Final = "user_id"
CONF_VERIFY_SSL: Final = "verify_ssl"
CONF_SCAN_INTERVAL: Final = "scan_interval"

# Streaming/transcoding option keys
CONF_DIRECT_PLAY: Final = "direct_play"
CONF_VIDEO_CONTAINER: Final = "video_container"
CONF_MAX_VIDEO_BITRATE: Final = "max_video_bitrate"
CONF_MAX_AUDIO_BITRATE: Final = "max_audio_bitrate"

# Feature toggle option keys
CONF_ENABLE_WEBSOCKET: Final = "enable_websocket"
CONF_IGNORED_DEVICES: Final = "ignored_devices"
CONF_IGNORE_WEB_PLAYERS: Final = "ignore_web_players"

# Entity name prefix option keys (Phase 11)
CONF_PREFIX_MEDIA_PLAYER: Final = "prefix_media_player"
CONF_PREFIX_NOTIFY: Final = "prefix_notify"
CONF_PREFIX_REMOTE: Final = "prefix_remote"
CONF_PREFIX_BUTTON: Final = "prefix_button"

# Default values
DEFAULT_PORT: Final = 8096
DEFAULT_SSL: Final = False
DEFAULT_VERIFY_SSL: Final = True
DEFAULT_SCAN_INTERVAL: Final = 10  # seconds
DEFAULT_TIMEOUT: Final = 10  # seconds
DEFAULT_DIRECT_PLAY: Final = True
DEFAULT_VIDEO_CONTAINER: Final = "mp4"
DEFAULT_ENABLE_WEBSOCKET: Final = True
DEFAULT_IGNORED_DEVICES: Final[list[str]] = []
DEFAULT_IGNORE_WEB_PLAYERS: Final = False

# Default prefix values (Phase 11) - all enabled by default
DEFAULT_PREFIX_MEDIA_PLAYER: Final = True
DEFAULT_PREFIX_NOTIFY: Final = True
DEFAULT_PREFIX_REMOTE: Final = True
DEFAULT_PREFIX_BUTTON: Final = True

# Video container options
VIDEO_CONTAINERS: Final[list[str]] = ["mp4", "mkv", "webm"]

# Scan interval limits
MIN_SCAN_INTERVAL: Final = 5
MAX_SCAN_INTERVAL: Final = 300

# WebSocket polling intervals
WEBSOCKET_POLL_INTERVAL: Final = 60  # Reduced polling when WebSocket connected
FALLBACK_POLL_INTERVAL: Final = 10  # Normal polling when WebSocket disconnected

# Notification defaults
DEFAULT_NOTIFICATION_TIMEOUT_MS: Final = 5000  # 5 seconds

# Search validation
MAX_SEARCH_TERM_LENGTH: Final = 200

# API constants
EMBY_TICKS_PER_SECOND: Final = 10_000_000
EMBY_MIN_VERSION: Final = "4.9.1.90"

# HTTP constants
HEADER_AUTHORIZATION: Final = "X-Emby-Token"
USER_AGENT_TEMPLATE: Final = "HomeAssistant/Emby/{version}"

# HTTP methods
HTTP_GET: Final = "GET"
HTTP_POST: Final = "POST"
HTTP_PUT: Final = "PUT"
HTTP_DELETE: Final = "DELETE"

# API Endpoints
ENDPOINT_SYSTEM_INFO: Final = "/System/Info"
ENDPOINT_SYSTEM_INFO_PUBLIC: Final = "/System/Info/Public"
ENDPOINT_USERS: Final = "/Users"
ENDPOINT_SESSIONS: Final = "/Sessions"

# Platforms
PLATFORMS: list[Platform] = [
    Platform.BUTTON,
    Platform.MEDIA_PLAYER,
    Platform.NOTIFY,
    Platform.REMOTE,
]


# =============================================================================
# TypedDicts for API Responses
# =============================================================================
# Note: TypedDicts are for API responses (external data)
# Dataclasses are for internal models (see models.py in Phase 2)
# =============================================================================


class EmbyServerInfo(TypedDict):
    """Type definition for /System/Info response."""

    Id: str
    ServerName: str
    Version: str
    OperatingSystem: str
    HasPendingRestart: bool
    IsShuttingDown: bool
    LocalAddress: str
    WanAddress: NotRequired[str]


class EmbyPublicInfo(TypedDict):
    """Type definition for /System/Info/Public response."""

    Id: str
    ServerName: str
    Version: str
    LocalAddress: str


class EmbyUser(TypedDict):
    """Type definition for user object."""

    Id: str
    Name: str
    ServerId: str
    HasPassword: bool
    HasConfiguredPassword: bool
    PrimaryImageTag: NotRequired[str]
    HasPrimaryImage: NotRequired[bool]


class EmbyErrorResponse(TypedDict):
    """Type definition for error responses from Emby API."""

    ErrorCode: NotRequired[str]
    Message: NotRequired[str]


class EmbyConfigFlowUserInput(TypedDict):
    """Type definition for config flow user input."""

    host: str
    port: int
    ssl: bool
    api_key: str
    verify_ssl: NotRequired[bool]


# =============================================================================
# TypedDicts for Library Browsing API (Phase 5)
# =============================================================================


class EmbyLibraryItem(TypedDict):
    """Type definition for library item from user views.

    Returned by /Users/{userId}/Views endpoint.
    """

    Id: str
    Name: str
    CollectionType: NotRequired[str]  # "movies", "tvshows", "music", etc.
    ImageTags: NotRequired[dict[str, str]]


class EmbyBrowseItem(TypedDict):
    """Type definition for item from browse response.

    Returned by /Users/{userId}/Items endpoint.
    """

    Id: str
    Name: str
    Type: str  # "Movie", "Series", "Episode", "Audio", etc.
    ImageTags: NotRequired[dict[str, str]]
    ProductionYear: NotRequired[int]
    SeriesName: NotRequired[str]
    SeasonName: NotRequired[str]
    IndexNumber: NotRequired[int]  # Episode/track number
    ParentIndexNumber: NotRequired[int]  # Season number


class EmbyItemsResponse(TypedDict):
    """Type definition for response from /Users/{id}/Items endpoint."""

    Items: list[EmbyBrowseItem]
    TotalRecordCount: int
    StartIndex: int


# =============================================================================
# TypedDicts for /Sessions API Response (Phase 2)
# =============================================================================


class EmbyNowPlayingItem(TypedDict):
    """Type definition for NowPlayingItem in session response.

    Represents the currently playing media item in an Emby session.
    """

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
    """Type definition for PlayState in session response.

    Represents the current playback state of an Emby session.
    All fields are optional as they may not be present when nothing is playing.
    """

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


class EmbySessionResponse(TypedDict):
    """Type definition for /Sessions endpoint response item.

    Represents a single session from the Emby server's session list.
    """

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


# =============================================================================
# TypedDicts for Media Source Streaming (Phase 6)
# =============================================================================


class VideoStreamParams(TypedDict, total=False):
    """Type definition for video streaming parameters.

    All fields are optional to allow partial configuration.
    """

    container: str  # Output container format (mp4, mkv, webm)
    static: bool  # Direct play without transcoding
    audio_codec: str  # Audio codec for transcoding (aac, mp3, opus)
    video_codec: str  # Video codec for transcoding (h264, hevc, vp9)
    max_width: int  # Maximum video width
    max_height: int  # Maximum video height
    max_video_bitrate: int  # Maximum video bitrate in bps
    max_audio_bitrate: int  # Maximum audio bitrate in bps
    audio_stream_index: int  # Audio track index to use
    subtitle_stream_index: int  # Subtitle track index
    subtitle_method: str  # Encode, Embed, or External


class AudioStreamParams(TypedDict, total=False):
    """Type definition for audio streaming parameters.

    All fields are optional to allow partial configuration.
    """

    container: str  # Output format (mp3, flac, aac)
    static: bool  # Direct play without transcoding
    audio_codec: str  # Audio codec for transcoding
    max_bitrate: int  # Maximum bitrate in bps


class MediaSourceIdentifier(TypedDict):
    """Type definition for media source content identifier.

    Used to identify content in the media source browser.
    """

    server_id: str  # Emby server ID
    content_type: str  # Content type (movie, episode, track, etc.)
    item_id: str  # Emby item ID


# MIME type mapping for media content
MIME_TYPES: Final[dict[str, str]] = {
    "movie": "video/mp4",
    "episode": "video/mp4",
    "video": "video/mp4",
    "track": "audio/mpeg",
    "audio": "audio/mpeg",
}


# =============================================================================
# Utility Functions
# =============================================================================


def sanitize_api_key(api_key: str) -> str:
    """Sanitize API key for safe logging.

    Args:
        api_key: The full API key

    Returns:
        Truncated key safe for logging (first 4 + last 2 chars)
    """
    if len(api_key) <= 6:
        return "***"
    return f"{api_key[:4]}...{api_key[-2:]}"


def normalize_host(host: str) -> str:
    """Normalize host input from user.

    Removes protocol prefix and trailing slashes.

    Args:
        host: Raw host input from user

    Returns:
        Cleaned hostname or IP address
    """
    host = host.strip()
    # Remove protocol if present
    for prefix in ("https://", "http://"):
        if host.lower().startswith(prefix):
            host = host[len(prefix) :]
    return host.rstrip("/")
