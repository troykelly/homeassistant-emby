"""Constants for the Emby integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, NotRequired, TypedDict

from homeassistant.const import Platform

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .coordinator import EmbyDataUpdateCoordinator
    from .coordinator_discovery import EmbyDiscoveryCoordinator
    from .coordinator_sensors import EmbyLibraryCoordinator, EmbyServerCoordinator

# Integration domain
DOMAIN: Final = "embymedia"


# Runtime data class to hold all coordinators
class EmbyRuntimeData:
    """Runtime data for Emby integration.

    Holds all coordinators for the config entry.
    """

    def __init__(
        self,
        session_coordinator: EmbyDataUpdateCoordinator,
        server_coordinator: EmbyServerCoordinator,
        library_coordinator: EmbyLibraryCoordinator,
        discovery_coordinators: dict[str, EmbyDiscoveryCoordinator] | None = None,
    ) -> None:
        """Initialize runtime data.

        Args:
            session_coordinator: Coordinator for session/media player data.
            server_coordinator: Coordinator for server status data.
            library_coordinator: Coordinator for library counts data.
            discovery_coordinators: Optional dict of user_id -> coordinator for discovery data.
        """
        self.session_coordinator = session_coordinator
        self.server_coordinator = server_coordinator
        self.library_coordinator = library_coordinator
        self.discovery_coordinators = discovery_coordinators or {}

    # Provide backward compatibility as the old coordinator
    @property
    def coordinator(self) -> EmbyDataUpdateCoordinator:
        """Return the session coordinator (for backward compatibility)."""
        return self.session_coordinator

    # Backward compatibility for single discovery coordinator
    @property
    def discovery_coordinator(self) -> EmbyDiscoveryCoordinator | None:
        """Return the first discovery coordinator (for backward compatibility)."""
        if self.discovery_coordinators:
            return next(iter(self.discovery_coordinators.values()))
        return None


# Type alias for config entry with runtime data
type EmbyConfigEntry = ConfigEntry[EmbyRuntimeData]

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

# Sensor platform option keys (Phase 12)
CONF_ENABLE_LIBRARY_SENSORS: Final = "enable_library_sensors"
CONF_ENABLE_USER_SENSORS: Final = "enable_user_sensors"
CONF_LIBRARY_SCAN_INTERVAL: Final = "library_scan_interval"

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

# Default sensor values (Phase 12)
DEFAULT_ENABLE_LIBRARY_SENSORS: Final = True
DEFAULT_ENABLE_USER_SENSORS: Final = True
DEFAULT_LIBRARY_SCAN_INTERVAL: Final = 3600  # 1 hour in seconds
DEFAULT_SERVER_SCAN_INTERVAL: Final = 300  # 5 minutes in seconds

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
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.IMAGE,
    Platform.MEDIA_PLAYER,
    Platform.NOTIFY,
    Platform.REMOTE,
    Platform.SENSOR,
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


class EmbyQueueItem(TypedDict):
    """Type definition for a queue item in NowPlayingQueue.

    Represents a single item in the playback queue.
    """

    Id: str
    PlaylistItemId: NotRequired[str]


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
    NowPlayingQueue: NotRequired[list[EmbyQueueItem]]


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


# =============================================================================
# TypedDicts for Sensor Platform (Phase 12)
# =============================================================================


class EmbyItemCounts(TypedDict):
    """Response from /Items/Counts endpoint.

    Contains counts of various media types in the library.
    """

    MovieCount: int
    SeriesCount: int
    EpisodeCount: int
    ArtistCount: int
    AlbumCount: int
    SongCount: int
    GameCount: int
    GameSystemCount: int
    TrailerCount: int
    MusicVideoCount: int
    BoxSetCount: int
    BookCount: int
    ItemCount: int


class EmbyScheduledTaskResult(TypedDict):
    """Last execution result for a scheduled task."""

    StartTimeUtc: str
    EndTimeUtc: str
    Status: str  # "Completed", "Failed", "Cancelled", "Aborted"
    Name: str
    Key: str
    Id: str


class EmbyScheduledTask(TypedDict, total=False):
    """Response item from /ScheduledTasks endpoint.

    Note: total=False means all fields are optional by default.
    We make specific fields required by not using NotRequired.
    """

    # Required fields (always present)
    Name: str
    State: str  # "Idle", "Running", "Cancelling"
    Id: str
    Description: str
    Category: str
    IsHidden: bool
    Key: str
    Triggers: list[dict[str, object]]

    # Optional fields (only present in certain conditions)
    CurrentProgressPercentage: float  # Only when running
    LastExecutionResult: EmbyScheduledTaskResult  # May not be present


class EmbyVirtualFolderLocation(TypedDict):
    """Location path within a virtual folder."""

    Path: str


class EmbyVirtualFolder(TypedDict, total=False):
    """Response item from /Library/VirtualFolders endpoint.

    Represents a library/virtual folder configuration.
    """

    # Required fields
    Name: str
    ItemId: str
    CollectionType: str  # "movies", "tvshows", "music", etc.
    Locations: list[str]

    # Optional fields (only present during refresh)
    RefreshProgress: float  # Progress percentage when refreshing
    RefreshStatus: str  # "Active", "Idle"


# MIME type mapping for media content
MIME_TYPES: Final[dict[str, str]] = {
    "movie": "video/mp4",
    "episode": "video/mp4",
    "video": "video/mp4",
    "track": "audio/mpeg",
    "audio": "audio/mpeg",
}

# HLS MIME type
MIME_TYPE_HLS: Final = "application/x-mpegURL"


# =============================================================================
# TypedDicts for Transcoding / PlaybackInfo API (Phase 13)
# =============================================================================


class MediaStreamInfo(TypedDict, total=False):
    """Individual stream (video/audio/subtitle) information.

    Represents a single stream within a media source, containing codec
    and format details needed for playback decisions.
    """

    # Common fields
    Index: int
    Type: str  # "Video", "Audio", "Subtitle"
    Codec: str
    Language: str
    Title: str
    IsDefault: bool
    IsForced: bool

    # Video-specific fields
    Width: int
    Height: int
    BitRate: int
    AspectRatio: str
    AverageFrameRate: float
    Profile: str
    Level: float

    # Audio-specific fields
    Channels: int
    SampleRate: int
    ChannelLayout: str


class MediaSourceInfo(TypedDict, total=False):
    """Media source information from PlaybackInfo response.

    Contains all information about a media source including its
    capabilities for direct play, direct stream, and transcoding.
    """

    Id: str
    Name: str
    Path: str
    Protocol: str  # "File", "Http", "Rtmp", etc.
    Container: str
    Size: int
    Bitrate: int
    RunTimeTicks: int

    # Playback capability flags
    SupportsTranscoding: bool
    SupportsDirectStream: bool
    SupportsDirectPlay: bool

    # URLs for different playback methods
    TranscodingUrl: str
    TranscodingSubProtocol: str  # "hls" or empty
    TranscodingContainer: str
    DirectStreamUrl: str

    # Stream information
    MediaStreams: list[MediaStreamInfo]
    DefaultAudioStreamIndex: int
    DefaultSubtitleStreamIndex: int


class PlaybackInfoResponse(TypedDict, total=False):
    """Response from PlaybackInfo endpoint.

    Contains the available media sources and session information
    for playing the requested item.
    """

    MediaSources: list[MediaSourceInfo]
    PlaySessionId: str
    ErrorCode: str  # Present when there's an error


class DirectPlayProfile(TypedDict, total=False):
    """Direct play capability declaration.

    Defines what container/codec combinations the device
    can play directly without transcoding.
    """

    Container: str  # Comma-separated: "mp4,mkv,webm"
    VideoCodec: str  # Comma-separated: "h264,hevc"
    AudioCodec: str  # Comma-separated: "aac,mp3,ac3"
    Type: str  # "Video", "Audio", "Photo"


class TranscodingProfile(TypedDict, total=False):
    """Transcoding fallback configuration.

    Defines how media should be transcoded when direct play
    is not supported.
    """

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


class SubtitleProfile(TypedDict, total=False):
    """Subtitle delivery options.

    Defines how subtitles should be delivered to the device.
    """

    Format: str  # "srt", "vtt", "ass"
    Method: str  # "Encode", "Embed", "External", "Hls"
    Language: str


class DeviceProfile(TypedDict, total=False):
    """Device capability profile for playback negotiation.

    Describes what the target device can play directly and
    how content should be transcoded when necessary.
    """

    Name: str
    Id: str
    MaxStreamingBitrate: int
    MaxStaticBitrate: int
    MusicStreamingTranscodingBitrate: int
    DirectPlayProfiles: list[DirectPlayProfile]
    TranscodingProfiles: list[TranscodingProfile]
    SubtitleProfiles: list[SubtitleProfile]


class PlaybackInfoRequest(TypedDict, total=False):
    """Request body for PlaybackInfo endpoint.

    Sent to the server to get playback information including
    the optimal streaming URL based on device capabilities.
    """

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


# =============================================================================
# Transcoding Configuration Constants (Phase 13)
# =============================================================================

# Transcoding configuration keys
CONF_TRANSCODING_PROFILE: Final = "transcoding_profile"
CONF_MAX_STREAMING_BITRATE: Final = "max_streaming_bitrate"
CONF_PREFER_DIRECT_PLAY: Final = "prefer_direct_play"
CONF_MAX_VIDEO_WIDTH: Final = "max_video_width"
CONF_MAX_VIDEO_HEIGHT: Final = "max_video_height"

# Default values for transcoding
DEFAULT_TRANSCODING_PROFILE: Final = "universal"
DEFAULT_MAX_STREAMING_BITRATE: Final = 40_000_000  # 40 Mbps
DEFAULT_PREFER_DIRECT_PLAY: Final = True
DEFAULT_MAX_VIDEO_WIDTH: Final = 1920
DEFAULT_MAX_VIDEO_HEIGHT: Final = 1080

# Available transcoding profile choices
TRANSCODING_PROFILES: Final[list[str]] = [
    "universal",
    "chromecast",
    "roku",
    "appletv",
    "audio_only",
]


# =============================================================================
# TypedDicts for Discovery API (Phase 15)
# =============================================================================


class EmbyUserData(TypedDict, total=False):
    """User data embedded in item responses.

    Contains playback state, favorites, and play history for an item.
    """

    PlaybackPositionTicks: int
    PlayedPercentage: float
    PlayCount: int
    IsFavorite: bool
    Played: bool
    LastPlayedDate: str


class NextUpItem(TypedDict, total=False):
    """Next up episode item from /Shows/NextUp.

    Represents the next episode to watch in a TV series.
    """

    # Standard item fields
    Id: str
    Name: str
    Type: str  # "Episode"
    ServerId: str

    # Series context
    SeriesName: str
    SeasonName: str
    IndexNumber: int  # Episode number
    ParentIndexNumber: int  # Season number
    SeriesId: str
    SeasonId: str

    # Metadata
    Overview: str
    RunTimeTicks: int
    ProductionYear: int
    PremiereDate: str

    # Images
    ImageTags: dict[str, str]
    BackdropImageTags: list[str]
    SeriesPrimaryImageTag: str
    ParentBackdropItemId: str
    ParentBackdropImageTags: list[str]
    ParentLogoItemId: str
    ParentLogoImageTag: str
    ParentThumbItemId: str
    ParentThumbImageTag: str

    # User data
    UserData: EmbyUserData

    # Media info
    MediaType: str  # "Video"


class ResumableItem(TypedDict, total=False):
    """Resumable item from Continue Watching.

    Represents a partially watched movie or episode.
    """

    # Standard item fields
    Id: str
    Name: str
    Type: str  # "Movie" or "Episode"
    ServerId: str
    IsFolder: bool

    # TV-specific (only for episodes)
    SeriesName: str
    SeasonName: str
    IndexNumber: int
    ParentIndexNumber: int
    SeriesId: str
    SeasonId: str
    SeriesPrimaryImageTag: str

    # Metadata
    Overview: str
    RunTimeTicks: int
    ProductionYear: int

    # Images
    ImageTags: dict[str, str]
    BackdropImageTags: list[str]
    ParentBackdropItemId: str
    ParentBackdropImageTags: list[str]
    ParentLogoItemId: str
    ParentLogoImageTag: str
    ParentThumbItemId: str
    ParentThumbImageTag: str

    # User data with progress
    UserData: EmbyUserData

    # Media info
    MediaType: str  # "Video"


class LatestMediaItem(TypedDict, total=False):
    """Latest media item from /Users/{id}/Items/Latest.

    Represents recently added content (movie, episode, album, etc.).
    """

    # Standard item fields
    Id: str
    Name: str
    Type: str  # "Movie", "Episode", "Audio", etc.
    ServerId: str
    IsFolder: bool

    # TV-specific
    SeriesName: str
    SeasonName: str
    IndexNumber: int
    ParentIndexNumber: int

    # Music-specific
    Album: str
    AlbumId: str
    AlbumArtist: str
    Artists: list[str]

    # Metadata
    Overview: str
    RunTimeTicks: int
    ProductionYear: int
    DateCreated: str

    # Images
    ImageTags: dict[str, str]
    BackdropImageTags: list[str]

    # User data
    UserData: EmbyUserData

    # Media info
    MediaType: str


class SuggestionItem(TypedDict, total=False):
    """Suggestion item from /Users/{id}/Suggestions.

    Represents a personalized recommendation.
    """

    # Standard item fields
    Id: str
    Name: str
    Type: str  # "Movie", "Series", "Audio", "Folder", etc.
    ServerId: str
    IsFolder: bool

    # Metadata
    Overview: str
    RunTimeTicks: int
    ProductionYear: int
    CommunityRating: float
    CriticRating: int

    # Music-specific
    Album: str
    AlbumId: str
    AlbumArtist: str
    Artists: list[str]

    # Images
    ImageTags: dict[str, str]
    BackdropImageTags: list[str]
    ParentBackdropItemId: str
    ParentBackdropImageTags: list[str]

    # User data
    UserData: EmbyUserData

    # Media info
    MediaType: str


# =============================================================================
# TypedDicts for Live TV API (Phase 16)
# =============================================================================


class EmbyLiveTvInfo(TypedDict, total=False):
    """Response from /LiveTv/Info endpoint.

    Contains Live TV configuration and status information.
    """

    # Required fields (use NotRequired for optional)
    IsEnabled: bool
    EnabledUsers: list[str]  # User IDs with Live TV access

    # Optional fields
    Services: list[dict[str, object]]
    TunerCount: int  # Number of available tuners
    ActiveRecordingCount: int
    HomePageUrl: str
    Status: str  # "Ok", "LiveTvNotConfigured", etc.
    StatusMessage: str


class EmbyRecording(TypedDict, total=False):
    """Recorded program information from /LiveTv/Recordings.

    Recordings are library items with additional Live TV-specific fields.
    """

    # Standard item fields
    Id: str
    Name: str
    Type: str  # "Episode", "Movie", "Recording"
    ServerId: str
    IsFolder: bool

    # Recording-specific fields
    ChannelId: str
    ChannelName: str
    StartDate: str  # ISO 8601 datetime
    EndDate: str  # ISO 8601 datetime
    Status: str  # "Completed", "Recording", "Error", "Cancelled"
    IsRepeat: bool
    EpisodeTitle: str
    SeriesTimerId: str  # If part of series recording
    TimerId: str  # Original timer that created this recording
    RunTimeTicks: int

    # Program metadata
    Overview: str
    SeriesName: str
    SeasonNumber: int
    EpisodeNumber: int
    ProductionYear: int
    ImageTags: dict[str, str]
    BackdropImageTags: list[str]
    MediaType: str


class EmbyTimer(TypedDict, total=False):
    """Timer (scheduled recording) from /LiveTv/Timers."""

    # Required fields
    Id: str
    Type: str  # "Timer"
    ChannelId: str
    ChannelName: str
    ProgramId: str
    Name: str
    StartDate: str  # ISO 8601 datetime
    EndDate: str  # ISO 8601 datetime
    Status: str  # "New", "InProgress", "Completed", "Cancelled", "ConflictedNotOk"

    # Optional fields
    SeriesTimerId: str  # If created by series timer
    PrePaddingSeconds: int  # Recording starts early
    PostPaddingSeconds: int  # Recording ends late
    Priority: int  # Higher priority wins conflicts
    IsManual: bool  # User-created vs auto-created
    IsPrePaddingRequired: bool
    IsPostPaddingRequired: bool
    KeepUntil: str  # "UntilDeleted", "UntilSpaceNeeded", etc.

    # Program metadata
    Overview: str
    EpisodeTitle: str
    SeriesName: str
    SeasonNumber: int
    EpisodeNumber: int
    RunTimeTicks: int
    ImageTags: dict[str, str]
    ChannelNumber: str
    ChannelPrimaryImageTag: str
    ProgramInfo: dict[str, object]  # Full program info nested object


class EmbySeriesTimer(TypedDict, total=False):
    """Series timer (recording rule) from /LiveTv/SeriesTimers."""

    # Required fields
    Id: str
    Type: str  # "SeriesTimer"
    Name: str
    ChannelId: str
    ChannelName: str
    ProgramId: str

    # Recording rules
    RecordAnyTime: bool  # Record regardless of time slot
    RecordAnyChannel: bool  # Record on any channel
    RecordNewOnly: bool  # Skip repeats
    SkipEpisodesInLibrary: bool  # Don't record episodes already in library
    MatchExistingItemsWithAnyLibrary: bool

    # Keep settings
    KeepUpTo: int  # Number of recordings to keep
    KeepUntil: str  # "UntilDeleted", "UntilSpaceNeeded"
    MaxRecordingSeconds: int

    # Timing
    Days: list[str]  # ["Monday", "Tuesday", ...]
    ChannelIds: list[str]  # For RecordAnyChannel
    StartDate: str  # ISO 8601 datetime
    EndDate: str  # ISO 8601 datetime (when rule expires)
    PrePaddingSeconds: int
    PostPaddingSeconds: int
    Priority: int
    IsPrePaddingRequired: bool
    IsPostPaddingRequired: bool

    # Metadata
    SeriesId: str
    Overview: str
    ChannelNumber: str
    ImageTags: dict[str, str]
    Keywords: list[str]
    TimerType: str
    ServerId: str
    ParentPrimaryImageItemId: str
    ParentPrimaryImageTag: str


class EmbyTimerDefaults(TypedDict, total=False):
    """Default timer settings from /LiveTv/Timers/Defaults.

    Used to pre-populate timer creation with server defaults.
    """

    ProgramId: str
    ChannelId: str
    StartDate: str
    EndDate: str
    PrePaddingSeconds: int
    PostPaddingSeconds: int
    Priority: int
    IsPrePaddingRequired: bool
    IsPostPaddingRequired: bool


class EmbyProgram(TypedDict, total=False):
    """EPG program information from /LiveTv/Programs."""

    # Required fields
    Id: str
    Type: str  # "Program"
    Name: str
    ChannelId: str
    ChannelName: str
    StartDate: str  # ISO 8601 datetime
    EndDate: str  # ISO 8601 datetime

    # Optional fields
    ServerId: str
    Overview: str
    EpisodeTitle: str
    SeriesName: str
    SeasonName: str
    SeasonNumber: int
    EpisodeNumber: int
    IndexNumber: int
    ParentIndexNumber: int
    IsRepeat: bool
    IsMovie: bool
    IsSeries: bool
    IsSports: bool
    IsNews: bool
    IsKids: bool
    IsLive: bool
    IsPremiere: bool
    ImageTags: dict[str, str]
    BackdropImageTags: list[str]
    RunTimeTicks: int
    TimerId: str  # If scheduled to record
    SeriesTimerId: str  # If part of series timer
    UserData: dict[str, object]  # Playback state
    MediaType: str


# Live TV configuration constants
CONF_ENABLE_LIVE_TV_SENSORS: Final = "enable_live_tv_sensors"
DEFAULT_ENABLE_LIVE_TV_SENSORS: Final = True
DEFAULT_LIVE_TV_SCAN_INTERVAL: Final = 300  # 5 minutes in seconds


# =============================================================================
# TypedDicts for Playlist API (Phase 17)
# =============================================================================


class EmbyPlaylistCreateResponse(TypedDict):
    """Response from POST /Playlists endpoint.

    Returns the newly created playlist information.
    """

    Id: str  # The created playlist ID
    Name: str  # The playlist name
    ItemAddedCount: int  # Number of items added (0 if none provided)


class EmbyPlaylistItem(TypedDict, total=False):
    """Playlist item with PlaylistItemId.

    Returned by GET /Playlists/{Id}/Items endpoint.
    IMPORTANT: PlaylistItemId is needed for removal, not the media item Id.
    """

    # Required fields (always present)
    Id: str  # Media item ID
    PlaylistItemId: str  # Unique ID for this item in the playlist
    Name: str
    Type: str  # "Audio", "Episode", "Movie", etc.

    # Optional fields from EmbyBrowseItem
    ImageTags: dict[str, str]
    ProductionYear: int
    SeriesName: str
    SeasonName: str
    IndexNumber: int  # Track/episode number
    ParentIndexNumber: int  # Season number


# =============================================================================
# Discovery Sensor Configuration Constants (Phase 15)
# =============================================================================

# Discovery sensor option keys
CONF_ENABLE_DISCOVERY_SENSORS: Final = "enable_discovery_sensors"
CONF_DISCOVERY_SCAN_INTERVAL: Final = "discovery_scan_interval"

# Default discovery values
DEFAULT_ENABLE_DISCOVERY_SENSORS: Final = True
DEFAULT_DISCOVERY_SCAN_INTERVAL: Final = 900  # 15 minutes in seconds


# =============================================================================
# TypedDicts for Activity Log API (Phase 18)
# =============================================================================


class EmbyActivityLogEntry(TypedDict, total=False):
    """Response item from /System/ActivityLog/Entries endpoint.

    Represents a single activity log entry from the Emby server.
    Note: Id is an int in Emby's activity log (unlike other IDs which are strings).

    Activity types include:
    - UserSignedIn / UserSignedOut
    - AuthenticationSucceeded / AuthenticationFailed
    - playback.start / playback.stop
    - ItemAdded
    - livetv.recordingerror
    - SubtitleDownload
    - PluginInstalled / PluginUpdated
    """

    # Required fields (present in all entries)
    Id: int  # Unique entry ID (note: int, not str)
    Name: str  # Activity description
    Type: str  # Activity type (e.g., "playback.start", "livetv.recordingerror")
    Date: str  # ISO 8601 timestamp
    Severity: str  # "Info", "Warn", "Error"

    # Optional fields (may not be present in all entries)
    UserId: str  # Associated user ID
    ItemId: str  # Associated media item ID
    UserPrimaryImageTag: str  # User avatar image tag
    ShortOverview: str  # Brief description
    Overview: str  # Full description


class EmbyActivityLogResponse(TypedDict):
    """Response from /System/ActivityLog/Entries endpoint.

    Contains a paginated list of activity entries and the total count.
    """

    Items: list[EmbyActivityLogEntry]
    TotalRecordCount: int


# =============================================================================
# TypedDicts for Devices API (Phase 18)
# =============================================================================


class EmbyDeviceInfo(TypedDict, total=False):
    """Response item from /Devices endpoint.

    Represents a registered device on the Emby server.
    """

    # Required fields (present in all device entries)
    Id: str  # Device ID
    Name: str  # Device name
    LastUserName: str  # Last username that used this device
    LastUserId: str  # Last user ID
    DateLastActivity: str  # ISO 8601 timestamp of last activity
    AppName: str  # Application name (e.g., "Emby for Samsung")
    AppVersion: str  # Application version

    # Optional fields (may not be present in all entries)
    ReportedDeviceId: str  # Device-reported unique ID
    IconUrl: str  # URL to device icon image
    IpAddress: str  # IP address (IPv4 or IPv6)


class EmbyDevicesResponse(TypedDict):
    """Response from /Devices endpoint.

    Contains a list of registered devices.
    Note: TotalRecordCount may be 0 even with items (Emby API quirk).
    """

    Items: list[EmbyDeviceInfo]
    TotalRecordCount: int


# =============================================================================
# TypedDicts for Collection Management API (Phase 19)
# =============================================================================


class EmbyCollectionCreateResponse(TypedDict):
    """Response from POST /Collections endpoint.

    Returns the newly created collection (BoxSet) information.
    """

    Id: str  # The created collection ID
    Name: str  # The collection name


# =============================================================================
# Person Types (Phase 19)
# =============================================================================


class EmbyPerson(TypedDict, total=False):
    """Type definition for person from /Persons endpoint.

    Represents an actor, director, writer, or other person in the library.
    """

    Id: str
    Name: str
    Type: str  # "Person"
    PrimaryImageTag: str
    ImageTags: dict[str, str]
    Role: str  # "Actor", "Director", "Writer", etc.


class EmbyPersonsResponse(TypedDict):
    """Response from /Persons endpoint."""

    Items: list[EmbyPerson]
    TotalRecordCount: int
    StartIndex: int


# =============================================================================
# Tag Types (Phase 19)
# =============================================================================


class EmbyTag(TypedDict, total=False):
    """Type definition for tag from /Tags endpoint.

    Represents a user-defined tag.
    """

    Id: str
    Name: str
    Type: str  # "Tag"


class EmbyTagsResponse(TypedDict):
    """Response from /Tags endpoint."""

    Items: list[EmbyTag]
    TotalRecordCount: int


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


def get_ha_device_id(hass: object) -> str:
    """Get a stable device ID for the Home Assistant instance.

    This ID is used to identify transcoding sessions with the Emby server.
    It uses the Home Assistant installation UUID for stability across restarts.

    Args:
        hass: Home Assistant instance (uses .data dict)

    Returns:
        Device ID string in format "homeassistant-{uuid}"
    """
    # hass.data is a dict-like object, we access it generically
    data = getattr(hass, "data", {})
    uuid = data.get("core.uuid", "unknown") if isinstance(data, dict) else "unknown"
    return f"homeassistant-{uuid}"


def generate_play_session_id() -> str:
    """Generate a unique play session ID for transcoding.

    Returns:
        32-character hex string (UUID without dashes)
    """
    import uuid

    return uuid.uuid4().hex
