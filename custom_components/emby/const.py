"""Constants for the Emby integration."""
from __future__ import annotations

from typing import TYPE_CHECKING, Final, NotRequired, TypedDict

from homeassistant.const import Platform

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .coordinator import EmbyDataUpdateCoordinator

# Integration domain
DOMAIN: Final = "emby"

# Type alias for config entry with runtime data
type EmbyConfigEntry = ConfigEntry[EmbyDataUpdateCoordinator]

# Configuration keys (use HA constants where available)
CONF_API_KEY: Final = "api_key"
CONF_USER_ID: Final = "user_id"
CONF_VERIFY_SSL: Final = "verify_ssl"
CONF_SCAN_INTERVAL: Final = "scan_interval"

# Default values
DEFAULT_PORT: Final = 8096
DEFAULT_SSL: Final = False
DEFAULT_VERIFY_SSL: Final = True
DEFAULT_SCAN_INTERVAL: Final = 10  # seconds
DEFAULT_TIMEOUT: Final = 10  # seconds

# Scan interval limits
MIN_SCAN_INTERVAL: Final = 5
MAX_SCAN_INTERVAL: Final = 300

# API constants
EMBY_TICKS_PER_SECOND: Final = 10_000_000
EMBY_MIN_VERSION: Final = "4.7.0"

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
PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER]


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
