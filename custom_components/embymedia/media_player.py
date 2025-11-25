"""Media player platform for Emby integration."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from homeassistant.components.media_player import (
    MediaClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.components.media_player.browse_media import BrowseMedia
from homeassistant.components.media_player.errors import BrowseError
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .browse import (
    can_expand_emby_type,
    can_play_emby_type,
    decode_content_id,
    emby_type_to_media_class,
    encode_content_id,
)
from .entity import EmbyEntity
from .models import MediaType as EmbyMediaType

if TYPE_CHECKING:
    from .const import EmbyBrowseItem, EmbyConfigEntry, EmbyLibraryItem

from .coordinator import EmbyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Map Emby media types to HA media types
_MEDIA_TYPE_MAP: dict[EmbyMediaType, MediaType] = {
    EmbyMediaType.MOVIE: MediaType.MOVIE,
    EmbyMediaType.EPISODE: MediaType.TVSHOW,
    EmbyMediaType.AUDIO: MediaType.MUSIC,
    EmbyMediaType.MUSIC_VIDEO: MediaType.VIDEO,
    EmbyMediaType.TRAILER: MediaType.VIDEO,
    EmbyMediaType.PHOTO: MediaType.IMAGE,
    EmbyMediaType.LIVE_TV: MediaType.CHANNEL,
}


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
    coordinator: EmbyDataUpdateCoordinator = entry.runtime_data
    _LOGGER.debug("Setting up Emby media player platform")

    # Track which entities we've created
    known_devices: set[str] = set()

    @callback  # type: ignore[misc]
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
    entry.async_on_unload(coordinator.async_add_listener(async_add_new_entities))


class EmbyMediaPlayer(EmbyEntity, MediaPlayerEntity):  # type: ignore[misc]
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

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Return the supported features.

        Features are dynamically determined based on session capabilities.

        Returns:
            Bitmask of supported features.
        """
        session = self.session
        if session is None:
            return MediaPlayerEntityFeature(0)

        if not session.supports_remote_control:
            return MediaPlayerEntityFeature(0)

        features = (
            MediaPlayerEntityFeature.PAUSE
            | MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.STOP
            | MediaPlayerEntityFeature.NEXT_TRACK
            | MediaPlayerEntityFeature.PREVIOUS_TRACK
            | MediaPlayerEntityFeature.PLAY_MEDIA
        )

        # Volume control if supported
        if "SetVolume" in session.supported_commands:
            features |= MediaPlayerEntityFeature.VOLUME_SET
        if "Mute" in session.supported_commands:
            features |= MediaPlayerEntityFeature.VOLUME_MUTE

        # Seek if playback supports it
        if session.play_state and session.play_state.can_seek:
            features |= MediaPlayerEntityFeature.SEEK

        return features

    @property
    def media_content_id(self) -> str | None:
        """Return the content ID of current playing media.

        Returns:
            Item ID or None if not playing.
        """
        session = self.session
        if session is None or session.now_playing is None:
            return None
        return session.now_playing.item_id

    @property
    def media_content_type(self) -> MediaType | str | None:
        """Return the content type of current playing media.

        Returns:
            HA MediaType or None if not playing.
        """
        session = self.session
        if session is None or session.now_playing is None:
            return None

        return _MEDIA_TYPE_MAP.get(session.now_playing.media_type, MediaType.VIDEO)

    @property
    def media_title(self) -> str | None:
        """Return the title of current playing media.

        Returns:
            Item name or None if not playing.
        """
        session = self.session
        if session is None or session.now_playing is None:
            return None
        return session.now_playing.name

    @property
    def media_series_title(self) -> str | None:
        """Return the series title for TV episodes.

        Returns:
            Series name or None if not an episode.
        """
        session = self.session
        if session is None or session.now_playing is None:
            return None
        return session.now_playing.series_name

    @property
    def media_season(self) -> str | None:
        """Return the season number.

        Returns:
            Season number as string or None.
        """
        session = self.session
        if session is None or session.now_playing is None:
            return None
        season = session.now_playing.season_number
        return str(season) if season is not None else None

    @property
    def media_episode(self) -> str | None:
        """Return the episode number.

        Returns:
            Episode number as string or None.
        """
        session = self.session
        if session is None or session.now_playing is None:
            return None
        episode = session.now_playing.episode_number
        return str(episode) if episode is not None else None

    @property
    def media_artist(self) -> str | None:
        """Return the artist of current playing media.

        Returns:
            Artist name(s) or None.
        """
        session = self.session
        if session is None or session.now_playing is None:
            return None

        artists = session.now_playing.artists
        if artists:
            return ", ".join(artists)
        return session.now_playing.album_artist

    @property
    def media_album_name(self) -> str | None:
        """Return the album of current playing media.

        Returns:
            Album name or None.
        """
        session = self.session
        if session is None or session.now_playing is None:
            return None
        return session.now_playing.album

    @property
    def media_album_artist(self) -> str | None:
        """Return the album artist of current playing media.

        Returns:
            Album artist or None.
        """
        session = self.session
        if session is None or session.now_playing is None:
            return None
        return session.now_playing.album_artist

    @property
    def media_image_url(self) -> str | None:
        """Return the image URL of current playing media.

        Implements fallback hierarchy:
        1. Item's Primary image (if available)
        2. Series Primary image (for episodes without images)
        3. Album Primary image (for audio without images)
        4. Item Primary image without tag (fallback)

        Returns:
            Full URL to the image or None if not playing.
        """
        session = self.session
        if session is None or session.now_playing is None:
            return None

        now_playing = session.now_playing
        image_tags_dict = dict(now_playing.image_tags)

        # Check if item has a Primary image tag
        primary_tag = image_tags_dict.get("Primary")

        # Get the client for image URL generation
        # Type cast needed due to CoordinatorEntity generic type erasure
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        if primary_tag:
            # Item has its own Primary image
            return client.get_image_url(
                now_playing.item_id,
                image_type="Primary",
                tag=primary_tag,
            )

        # Fallback: Episode -> Series
        if now_playing.series_id:
            return client.get_image_url(
                now_playing.series_id,
                image_type="Primary",
                tag=None,
            )

        # Fallback: Audio -> Album
        if now_playing.album_id:
            return client.get_image_url(
                now_playing.album_id,
                image_type="Primary",
                tag=None,
            )

        # Final fallback: Use item ID without tag
        return client.get_image_url(
            now_playing.item_id,
            image_type="Primary",
            tag=None,
        )

    @property
    def media_duration(self) -> int | None:
        """Return the duration of current playing media in seconds.

        Returns:
            Duration in seconds or None.
        """
        session = self.session
        if session is None or session.now_playing is None:
            return None
        duration = session.now_playing.duration_seconds
        return int(duration) if duration is not None else None

    @property
    def media_position(self) -> int | None:
        """Return the current position in seconds.

        Returns:
            Position in seconds or None.
        """
        session = self.session
        if session is None or session.play_state is None:
            return None
        return int(session.play_state.position_seconds)

    @property
    def media_position_updated_at(self) -> datetime | None:
        """Return when position was last updated.

        Returns:
            Timestamp or None.
        """
        session = self.session
        if session is None or session.play_state is None:
            return None
        now: datetime = dt_util.utcnow()
        return now

    @property
    def volume_level(self) -> float | None:
        """Return the volume level (0.0 to 1.0).

        Returns:
            Volume level or None.
        """
        session = self.session
        if session is None or session.play_state is None:
            return None
        return session.play_state.volume_level

    @property
    def is_volume_muted(self) -> bool | None:
        """Return True if volume is muted.

        Returns:
            True if muted, False if not, None if unknown.
        """
        session = self.session
        if session is None or session.play_state is None:
            return None
        return session.play_state.is_muted

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level (0.0 to 1.0).

        Args:
            volume: Volume level between 0.0 and 1.0.
        """
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
        """Mute or unmute the volume.

        Args:
            mute: True to mute, False to unmute.
        """
        session = self.session
        if session is None:
            return

        command = "Mute" if mute else "Unmute"
        await self.coordinator.client.async_send_command(
            session.session_id,
            command,
        )

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

    async def async_media_seek(self, position: float) -> None:
        """Seek to position in seconds.

        Args:
            position: Position in seconds to seek to.
        """
        session = self.session
        if session is None:
            return

        from .api import seconds_to_ticks

        position_ticks = seconds_to_ticks(position)
        await self.coordinator.client.async_send_playback_command(
            session.session_id,
            "Seek",
            {"SeekPositionTicks": position_ticks},
        )

    async def async_play_media(
        self,
        media_type: MediaType | str,
        media_id: str,
        **kwargs: object,
    ) -> None:
        """Play media on this player.

        Args:
            media_type: Type of media to play.
            media_id: Media ID, may be encoded as type:id from browse.
            **kwargs: Additional arguments (unused).
        """
        session = self.session
        if session is None:
            return

        # Extract item ID from encoded content ID format (e.g., "item:movie-123")
        # When media_id contains ":", it's in format "type:id" from browse UI
        if ":" in media_id:
            _, ids = decode_content_id(media_id)
            item_id = ids[0]
        else:
            item_id = media_id

        await self.coordinator.client.async_play_items(
            session.session_id,
            [item_id],
        )

    async def async_browse_media(
        self,
        media_content_type: MediaType | str | None = None,
        media_content_id: str | None = None,
    ) -> BrowseMedia:
        """Implement the media browsing interface.

        Args:
            media_content_type: Type of content to browse.
            media_content_id: ID of content to browse (encoded as type:id).

        Returns:
            BrowseMedia object with browsable content.

        Raises:
            BrowseError: If browsing fails (e.g., no session/user).
        """
        session = self.session
        if session is None or session.user_id is None:
            raise BrowseError("No active session to browse media")

        user_id = session.user_id

        # Root level - show libraries
        if media_content_id is None:
            return await self._async_browse_root(user_id)

        # Parse the content ID to determine what to browse
        content_type, ids = decode_content_id(media_content_id)

        if content_type == "library" and ids:
            return await self._async_browse_library(user_id, ids[0])

        if content_type == "series" and ids:
            return await self._async_browse_series(user_id, ids[0])

        if content_type == "season" and len(ids) >= 2:
            return await self._async_browse_season(user_id, ids[0], ids[1])

        # Default: try to browse as a library
        raise BrowseError(f"Unknown content type: {content_type}")

    async def _async_browse_root(self, user_id: str) -> BrowseMedia:
        """Browse root level - show user libraries.

        Args:
            user_id: The user ID for API calls.

        Returns:
            BrowseMedia with libraries as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        libraries = await client.async_get_user_views(user_id)

        children: list[BrowseMedia] = []
        for library in libraries:
            children.append(self._library_to_browse_media(library))

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id="",
            media_content_type=MediaType.VIDEO,
            title="Emby",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_library(
        self, user_id: str, library_id: str
    ) -> BrowseMedia:
        """Browse a library's contents.

        Args:
            user_id: The user ID for API calls.
            library_id: The library/folder ID.

        Returns:
            BrowseMedia with library items as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        result = await client.async_get_items(user_id, parent_id=library_id)
        items = result.get("Items", [])

        children: list[BrowseMedia] = []
        for item in items:
            children.append(self._item_to_browse_media(item))

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("library", library_id),
            media_content_type=MediaType.VIDEO,
            title="Library",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_series(self, user_id: str, series_id: str) -> BrowseMedia:
        """Browse a TV series - show seasons.

        Args:
            user_id: The user ID for API calls.
            series_id: The series ID.

        Returns:
            BrowseMedia with seasons as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        seasons = await client.async_get_seasons(user_id, series_id)

        children: list[BrowseMedia] = []
        for season in seasons:
            children.append(
                self._season_to_browse_media(season, series_id)
            )

        return BrowseMedia(
            media_class=MediaClass.TV_SHOW,
            media_content_id=encode_content_id("series", series_id),
            media_content_type=MediaType.TVSHOW,
            title="Series",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_season(
        self, user_id: str, series_id: str, season_id: str
    ) -> BrowseMedia:
        """Browse a TV season - show episodes.

        Args:
            user_id: The user ID for API calls.
            series_id: The series ID.
            season_id: The season ID.

        Returns:
            BrowseMedia with episodes as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        episodes = await client.async_get_episodes(user_id, series_id, season_id)

        children: list[BrowseMedia] = []
        for episode in episodes:
            children.append(self._item_to_browse_media(episode))

        return BrowseMedia(
            media_class=MediaClass.SEASON,
            media_content_id=encode_content_id("season", series_id, season_id),
            media_content_type=MediaType.TVSHOW,
            title="Season",
            can_play=False,
            can_expand=True,
            children=children,
        )

    def _library_to_browse_media(self, library: EmbyLibraryItem) -> BrowseMedia:
        """Convert a library item to BrowseMedia.

        Args:
            library: The library item from API.

        Returns:
            BrowseMedia representation of the library.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        # Get thumbnail if available
        thumbnail: str | None = None
        image_tags = library.get("ImageTags", {})
        if "Primary" in image_tags:
            thumbnail = client.get_image_url(
                library["Id"], image_type="Primary", tag=image_tags["Primary"]
            )

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("library", library["Id"]),
            media_content_type=MediaType.VIDEO,
            title=library["Name"],
            can_play=False,
            can_expand=True,
            thumbnail=thumbnail,
        )

    def _item_to_browse_media(self, item: EmbyBrowseItem) -> BrowseMedia:
        """Convert an Emby item to BrowseMedia.

        Args:
            item: The item from API.

        Returns:
            BrowseMedia representation of the item.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        item_type = item.get("Type", "Unknown")
        media_class = emby_type_to_media_class(item_type)
        can_play = can_play_emby_type(item_type)
        can_expand = can_expand_emby_type(item_type)

        # Determine content ID based on type
        if item_type == "Series":
            content_id = encode_content_id("series", item["Id"])
        elif item_type in ("Movie", "Episode", "Audio"):
            content_id = encode_content_id("item", item["Id"])
        else:
            content_id = encode_content_id("library", item["Id"])

        # Get thumbnail if available
        thumbnail: str | None = None
        image_tags = item.get("ImageTags", {})
        if "Primary" in image_tags:
            thumbnail = client.get_image_url(
                item["Id"], image_type="Primary", tag=image_tags["Primary"]
            )

        return BrowseMedia(
            media_class=media_class,
            media_content_id=content_id,
            media_content_type=MediaType.VIDEO,
            title=item["Name"],
            can_play=can_play,
            can_expand=can_expand,
            thumbnail=thumbnail,
        )

    def _season_to_browse_media(
        self, season: EmbyBrowseItem, series_id: str
    ) -> BrowseMedia:
        """Convert a season item to BrowseMedia.

        Args:
            season: The season item from API.
            series_id: The parent series ID.

        Returns:
            BrowseMedia representation of the season.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        # Get thumbnail if available
        thumbnail: str | None = None
        image_tags = season.get("ImageTags", {})
        if "Primary" in image_tags:
            thumbnail = client.get_image_url(
                season["Id"], image_type="Primary", tag=image_tags["Primary"]
            )

        return BrowseMedia(
            media_class=MediaClass.SEASON,
            media_content_id=encode_content_id("season", series_id, season["Id"]),
            media_content_type=MediaType.TVSHOW,
            title=season["Name"],
            can_play=False,
            can_expand=True,
            thumbnail=thumbnail,
        )


__all__ = ["EmbyMediaPlayer", "async_setup_entry"]
