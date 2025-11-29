"""Media player platform for Emby integration."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from homeassistant.components.media_player import (
    MediaClass,
    MediaPlayerEnqueue,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    RepeatMode,
)
from homeassistant.components.media_player.browse_media import (
    BrowseMedia,
    SearchMedia,
    SearchMediaQuery,
)
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
from .exceptions import EmbyError
from .models import MediaType as EmbyMediaType

if TYPE_CHECKING:
    from .const import EmbyBrowseItem, EmbyConfigEntry, EmbyLibraryItem, EmbyPerson

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
    coordinator: EmbyDataUpdateCoordinator = entry.runtime_data.session_coordinator
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
    entry.async_on_unload(coordinator.async_add_listener(async_add_new_entities))


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
        # Cache for similar items to avoid repeated API calls
        self._similar_items_cache: list[dict[str, str]] | None = None
        self._similar_items_item_id: str | None = None

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
            | MediaPlayerEntityFeature.BROWSE_MEDIA
            | MediaPlayerEntityFeature.MEDIA_ENQUEUE
            | MediaPlayerEntityFeature.SHUFFLE_SET
            | MediaPlayerEntityFeature.REPEAT_SET
            | MediaPlayerEntityFeature.SEARCH_MEDIA
        )

        # Volume control if supported
        if "SetVolume" in session.supported_commands:
            features |= MediaPlayerEntityFeature.VOLUME_SET
        if "Mute" in session.supported_commands:
            features |= MediaPlayerEntityFeature.VOLUME_MUTE

        # Seek if playback supports it
        if session.play_state and session.play_state.can_seek:
            features |= MediaPlayerEntityFeature.SEEK

        # Clear playlist if there's a queue
        if session.queue_item_ids:
            features |= MediaPlayerEntityFeature.CLEAR_PLAYLIST

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

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return entity specific state attributes.

        Returns:
            Dictionary of extra attributes including queue and similar items.
        """
        session = self.session
        if session is None:
            return {}

        attrs: dict[str, object] = {}

        # Queue information
        if session.queue_item_ids:
            attrs["queue_size"] = len(session.queue_item_ids)
            attrs["queue_position"] = session.queue_position + 1  # 1-based for display

        # Similar items (if cached and for current item)
        if (
            self._similar_items_cache is not None
            and session.now_playing is not None
            and self._similar_items_item_id == session.now_playing.item_id
        ):
            attrs["similar_items"] = self._similar_items_cache

        return attrs

    async def async_update_similar_items(self) -> None:
        """Fetch and cache similar items for the currently playing media.

        This method should be called when the now playing item changes
        to refresh the similar items cache.
        """
        session = self.session
        if session is None or session.now_playing is None:
            self._similar_items_cache = None
            self._similar_items_item_id = None
            return

        current_item_id = session.now_playing.item_id

        # Skip if already cached for this item
        if self._similar_items_item_id == current_item_id:
            return

        # Fetch similar items from API
        user_id = session.user_id
        if user_id is None:
            self._similar_items_cache = None
            self._similar_items_item_id = None
            return

        try:
            similar_items = await self.coordinator.client.async_get_similar_items(
                user_id=user_id,
                item_id=current_item_id,
                limit=10,  # Limit to 10 similar items for the attribute
            )
            # Transform to simpler format for attribute
            self._similar_items_cache = [
                {
                    "id": item.get("Id", ""),
                    "name": item.get("Name", ""),
                    "type": item.get("Type", ""),
                }
                for item in similar_items
            ]
            self._similar_items_item_id = current_item_id
        except EmbyError:
            _LOGGER.debug("Failed to fetch similar items for %s", current_item_id)
            self._similar_items_cache = None
            self._similar_items_item_id = None

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

    async def async_clear_playlist(self) -> None:
        """Clear the playback queue.

        Stops playback to clear the current queue since Emby
        doesn't have a direct "clear queue" command.
        """
        session = self.session
        if session is None:
            return

        await self.coordinator.client.async_stop_playback(session.session_id)

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

    async def async_set_shuffle(self, shuffle: bool) -> None:
        """Set shuffle mode.

        Args:
            shuffle: Whether to enable shuffle mode.
        """
        session = self.session
        if session is None:
            return

        mode = "Shuffle" if shuffle else "Sorted"
        await self.coordinator.client.async_send_general_command(
            session.session_id,
            "SetShuffleQueue",
            {"ShuffleMode": mode},
        )

    async def async_set_repeat(self, repeat: RepeatMode) -> None:
        """Set repeat mode.

        Args:
            repeat: The repeat mode to set.
        """
        session = self.session
        if session is None:
            return

        # Map Home Assistant repeat modes to Emby repeat modes
        emby_modes: dict[RepeatMode, str] = {
            RepeatMode.OFF: "RepeatNone",
            RepeatMode.ONE: "RepeatOne",
            RepeatMode.ALL: "RepeatAll",
        }
        mode = emby_modes.get(repeat, "RepeatNone")
        await self.coordinator.client.async_send_general_command(
            session.session_id,
            "SetRepeatMode",
            {"RepeatMode": mode},
        )

    async def async_play_media(
        self,
        media_type: MediaType | str,
        media_id: str,
        enqueue: MediaPlayerEnqueue | None = None,
        **kwargs: object,
    ) -> None:
        """Play media on this player.

        Args:
            media_type: Type of media to play.
            media_id: Media ID, may be encoded as type:id from browse.
            enqueue: Enqueue behavior (play, add, next, replace).
            **kwargs: Additional arguments (unused).
        """
        session = self.session
        if session is None:
            return

        # Determine the play command based on enqueue option
        play_command = "PlayNow"
        if enqueue == MediaPlayerEnqueue.ADD:
            play_command = "PlayLast"
        elif enqueue == MediaPlayerEnqueue.NEXT:
            play_command = "PlayNext"
        # PLAY and REPLACE both use PlayNow

        # Parse the content ID format
        if ":" in media_id:
            content_type, ids = decode_content_id(media_id)
        else:
            content_type = "item"
            ids = [media_id]

        # Handle container types (albums, seasons, playlists)
        item_ids = await self._resolve_play_media_ids(content_type, ids)

        await self.coordinator.client.async_play_items(
            session.session_id,
            item_ids,
            start_position_ticks=0,
            play_command=play_command,
        )

    async def _resolve_play_media_ids(self, content_type: str, ids: list[str]) -> list[str]:
        """Resolve content type and IDs to playable item IDs.

        Handles containers like albums, seasons, and playlists by fetching
        all child items and returning their IDs for queue playback.

        Args:
            content_type: The content type (item, album, season, playlist).
            ids: List of IDs from the decoded content ID.

        Returns:
            List of playable item IDs.
        """
        session = self.session
        if session is None or session.user_id is None:
            return ids

        user_id = session.user_id
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        if content_type == "album" and ids:
            # Get all tracks from the album
            album_id = ids[0]
            tracks = await client.async_get_album_tracks(user_id, album_id)
            return [track["Id"] for track in tracks]

        if content_type == "season" and len(ids) >= 2:
            # Get all episodes from the season
            series_id = ids[0]
            season_id = ids[1]
            episodes = await client.async_get_episodes(user_id, series_id, season_id)
            return [episode["Id"] for episode in episodes]

        if content_type == "playlist" and ids:
            # Get all items from the playlist
            playlist_id = ids[0]
            items = await client.async_get_playlist_items(user_id, playlist_id)
            return [item["Id"] for item in items]

        # Default: return the first ID as a single item
        if ids:
            return [ids[0]]
        return []

    async def async_search_media(
        self,
        query: SearchMediaQuery,
    ) -> SearchMedia:
        """Search for media in Emby library.

        Supports voice assistant commands like "Play X-Files Season 1 Episode 12".

        Args:
            query: Search query containing search string and optional filters.

        Returns:
            SearchMedia with list of matching BrowseMedia results.
        """
        session = self.session
        if session is None or session.user_id is None:
            return SearchMedia(result=[])

        user_id = session.user_id
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        # Map HA MediaType to Emby item types
        include_item_types: str | None = None
        if query.media_content_type:
            type_mapping: dict[MediaType | str, str] = {
                MediaType.MOVIE: "Movie",
                MediaType.TVSHOW: "Episode,Series",
                MediaType.MUSIC: "Audio,MusicAlbum,MusicArtist",
                MediaType.VIDEO: "Movie,Episode,MusicVideo",
                MediaType.CHANNEL: "TvChannel",
            }
            include_item_types = type_mapping.get(query.media_content_type)

        # Perform search
        items = await client.async_search_items(
            user_id=user_id,
            search_term=query.search_query,
            include_item_types=include_item_types,
        )

        # Convert results to BrowseMedia
        results: list[BrowseMedia] = []
        for item in items:
            results.append(self._item_to_browse_media(item))

        return SearchMedia(result=results)

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

        if content_type == "musiclibrary" and ids:
            return await self._async_browse_music_library(user_id, ids[0])

        if content_type == "musicartists" and ids:
            return await self._async_browse_music_artists(user_id, ids[0])

        if content_type == "musicartistletter" and len(ids) >= 2:
            return await self._async_browse_artists_by_letter(user_id, ids[0], ids[1])

        if content_type == "musicalbums" and ids:
            return await self._async_browse_music_albums(user_id, ids[0])

        if content_type == "musicalbumletter" and len(ids) >= 2:
            return await self._async_browse_albums_by_letter(user_id, ids[0], ids[1])

        if content_type == "musicgenres" and ids:
            return await self._async_browse_music_genres(user_id, ids[0])

        if content_type == "musicgenre" and len(ids) >= 2:
            return await self._async_browse_genre_items(user_id, ids[0], ids[1])

        if content_type == "musicplaylists" and ids:
            return await self._async_browse_music_playlists(user_id, ids[0])

        if content_type == "series" and ids:
            return await self._async_browse_series(user_id, ids[0])

        if content_type == "season" and len(ids) >= 2:
            return await self._async_browse_season(user_id, ids[0], ids[1])

        if content_type == "artist" and ids:
            return await self._async_browse_artist(user_id, ids[0])

        if content_type == "album" and ids:
            return await self._async_browse_album(user_id, ids[0])

        if content_type == "playlist" and ids:
            return await self._async_browse_playlist(user_id, ids[0])

        if content_type == "collection" and ids:
            return await self._async_browse_collection(user_id, ids[0])

        if content_type == "livetv":
            return await self._async_browse_livetv(user_id)

        # Movie library routing
        if content_type == "movielibrary" and ids:
            return await self._async_browse_movie_library(user_id, ids[0])
        if content_type == "movieaz" and ids:
            return await self._async_browse_movie_az(user_id, ids[0])
        if content_type == "movieazletter" and len(ids) >= 2:
            return await self._async_browse_movies_by_letter(user_id, ids[0], ids[1])
        if content_type == "movieyear" and ids:
            return await self._async_browse_movie_years(user_id, ids[0])
        if content_type == "movieyearitems" and len(ids) >= 2:
            return await self._async_browse_movies_by_year(user_id, ids[0], ids[1])
        if content_type == "moviedecade" and ids:
            return await self._async_browse_movie_decades(user_id, ids[0])
        if content_type == "moviedecadeitems" and len(ids) >= 2:
            return await self._async_browse_movies_by_decade(user_id, ids[0], ids[1])
        if content_type == "moviegenre" and ids:
            return await self._async_browse_movie_genres(user_id, ids[0])
        if content_type == "moviegenreitems" and len(ids) >= 2:
            return await self._async_browse_movies_by_genre(user_id, ids[0], ids[1])
        if content_type == "moviecollection" and ids:
            return await self._async_browse_movie_collections(user_id, ids[0])
        if content_type == "moviestudio" and ids:
            return await self._async_browse_movie_studios(user_id, ids[0])
        if content_type == "moviestudioitems" and len(ids) >= 2:
            return await self._async_browse_movies_by_studio(user_id, ids[0], ids[1])
        if content_type == "moviepeople" and ids:
            return await self._async_browse_movie_people(user_id, ids[0])
        if content_type == "person" and len(ids) >= 2:
            return await self._async_browse_person(user_id, ids[1], ids[0])
        if content_type == "movietags" and ids:
            return await self._async_browse_movie_tags(user_id, ids[0])
        if content_type == "movietag" and len(ids) >= 2:
            return await self._async_browse_movies_by_tag(user_id, ids[0], ids[1])

        # TV library routing
        if content_type == "tvlibrary" and ids:
            return await self._async_browse_tv_library(user_id, ids[0])
        if content_type == "tvaz" and ids:
            return await self._async_browse_tv_az(user_id, ids[0])
        if content_type == "tvazletter" and len(ids) >= 2:
            return await self._async_browse_tv_by_letter(user_id, ids[0], ids[1])
        if content_type == "tvyear" and ids:
            return await self._async_browse_tv_years(user_id, ids[0])
        if content_type == "tvyearitems" and len(ids) >= 2:
            return await self._async_browse_tv_by_year(user_id, ids[0], ids[1])
        if content_type == "tvdecade" and ids:
            return await self._async_browse_tv_decades(user_id, ids[0])
        if content_type == "tvdecadeitems" and len(ids) >= 2:
            return await self._async_browse_tv_by_decade(user_id, ids[0], ids[1])
        if content_type == "tvgenre" and ids:
            return await self._async_browse_tv_genres(user_id, ids[0])
        if content_type == "tvgenreitems" and len(ids) >= 2:
            return await self._async_browse_tv_by_genre(user_id, ids[0], ids[1])
        if content_type == "tvstudio" and ids:
            return await self._async_browse_tv_studios(user_id, ids[0])
        if content_type == "tvstudioitems" and len(ids) >= 2:
            return await self._async_browse_tv_by_studio(user_id, ids[0], ids[1])

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

    async def _async_browse_library(self, user_id: str, library_id: str) -> BrowseMedia:
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

    async def _async_browse_music_library(self, user_id: str, library_id: str) -> BrowseMedia:
        """Browse a music library - show category menu.

        Music libraries show categories (Artists, Albums, Genres, Playlists)
        to organize large collections effectively.

        Args:
            user_id: The user ID for API calls.
            library_id: The music library ID.

        Returns:
            BrowseMedia with categories as children.
        """
        categories = [
            ("Artists", "musicartists", MediaClass.DIRECTORY),
            ("Albums", "musicalbums", MediaClass.DIRECTORY),
            ("Genres", "musicgenres", MediaClass.DIRECTORY),
            ("Playlists", "musicplaylists", MediaClass.PLAYLIST),
        ]

        children: list[BrowseMedia] = []
        for title, content_type, media_class in categories:
            children.append(
                BrowseMedia(
                    media_class=media_class,
                    media_content_id=encode_content_id(content_type, library_id),
                    media_content_type=MediaType.MUSIC,
                    title=title,
                    can_play=False,
                    can_expand=True,
                    thumbnail=None,
                )
            )

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("musiclibrary", library_id),
            media_content_type=MediaType.MUSIC,
            title="Music Library",
            can_play=False,
            can_expand=True,
            children=children,
        )

    def _build_letter_menu(
        self,
        content_type: str,
        library_id: str,
        media_content_type: MediaType = MediaType.MUSIC,
    ) -> list[BrowseMedia]:
        """Build A-Z letter menu for large library navigation.

        Args:
            content_type: The content type prefix (e.g., 'musicartistletter').
            library_id: The library ID.
            media_content_type: The media content type (MUSIC, VIDEO, TVSHOW).

        Returns:
            List of BrowseMedia items for # and A-Z letters.
        """
        letters = ["#"] + [chr(i) for i in range(ord("A"), ord("Z") + 1)]
        children: list[BrowseMedia] = []

        for letter in letters:
            children.append(
                BrowseMedia(
                    media_class=MediaClass.DIRECTORY,
                    media_content_id=encode_content_id(content_type, library_id, letter),
                    media_content_type=media_content_type,
                    title=letter,
                    can_play=False,
                    can_expand=True,
                    thumbnail=None,
                )
            )

        return children

    def _build_decade_menu(
        self,
        content_type: str,
        library_id: str,
        media_content_type: MediaType = MediaType.VIDEO,
    ) -> list[BrowseMedia]:
        """Build decade menu for library navigation.

        Args:
            content_type: The content type prefix (e.g., 'moviedecadeitems').
            library_id: The library ID.
            media_content_type: The media content type (VIDEO, TVSHOW).

        Returns:
            List of BrowseMedia items for decades from 2020s to 1920s.
        """
        # Decades from 2020s down to 1920s
        decades = list(range(2020, 1910, -10))
        children: list[BrowseMedia] = []

        for decade in decades:
            children.append(
                BrowseMedia(
                    media_class=MediaClass.DIRECTORY,
                    media_content_id=encode_content_id(content_type, library_id, str(decade)),
                    media_content_type=media_content_type,
                    title=f"{decade}s",
                    can_play=False,
                    can_expand=True,
                    thumbnail=None,
                )
            )

        return children

    async def _async_browse_music_artists(self, user_id: str, library_id: str) -> BrowseMedia:
        """Browse music artists category - show A-Z letter menu.

        Args:
            user_id: The user ID for API calls.
            library_id: The music library ID.

        Returns:
            BrowseMedia with A-Z letters as children.
        """
        children = self._build_letter_menu("musicartistletter", library_id)

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("musicartists", library_id),
            media_content_type=MediaType.MUSIC,
            title="Artists",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_artists_by_letter(
        self, user_id: str, library_id: str, letter: str
    ) -> BrowseMedia:
        """Browse artists starting with a specific letter.

        Args:
            user_id: The user ID for API calls.
            library_id: The music library ID.
            letter: The letter to filter by (# for numbers/symbols).

        Returns:
            BrowseMedia with filtered artists as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        # For "#", we need special handling - Emby uses empty string for non-alpha
        name_filter = "" if letter == "#" else letter

        result = await client.async_get_items(
            user_id,
            parent_id=library_id,
            include_item_types="MusicArtist",
            recursive=True,
            name_starts_with=name_filter if name_filter else None,
        )
        items = result.get("Items", [])

        # For "#", filter to non-alpha items manually
        if letter == "#":
            items = [i for i in items if not i.get("Name", "")[0:1].isalpha()]

        children: list[BrowseMedia] = []
        for item in items:
            children.append(self._item_to_browse_media(item))

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("musicartistletter", library_id, letter),
            media_content_type=MediaType.MUSIC,
            title=f"Artists - {letter}",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_music_albums(self, user_id: str, library_id: str) -> BrowseMedia:
        """Browse music albums category - show A-Z letter menu.

        Args:
            user_id: The user ID for API calls.
            library_id: The music library ID.

        Returns:
            BrowseMedia with A-Z letters as children.
        """
        children = self._build_letter_menu("musicalbumletter", library_id)

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("musicalbums", library_id),
            media_content_type=MediaType.MUSIC,
            title="Albums",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_albums_by_letter(
        self, user_id: str, library_id: str, letter: str
    ) -> BrowseMedia:
        """Browse albums starting with a specific letter.

        Args:
            user_id: The user ID for API calls.
            library_id: The music library ID.
            letter: The letter to filter by.

        Returns:
            BrowseMedia with filtered albums as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        name_filter = "" if letter == "#" else letter

        result = await client.async_get_items(
            user_id,
            parent_id=library_id,
            include_item_types="MusicAlbum",
            recursive=True,
            name_starts_with=name_filter if name_filter else None,
        )
        items = result.get("Items", [])

        # For "#", filter to non-alpha items manually
        if letter == "#":
            items = [i for i in items if not i.get("Name", "")[0:1].isalpha()]

        children: list[BrowseMedia] = []
        for item in items:
            children.append(self._album_to_browse_media(item))

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("musicalbumletter", library_id, letter),
            media_content_type=MediaType.MUSIC,
            title=f"Albums - {letter}",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_music_genres(self, user_id: str, library_id: str) -> BrowseMedia:
        """Browse music genres.

        Args:
            user_id: The user ID for API calls.
            library_id: The music library ID.

        Returns:
            BrowseMedia with genres as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        genres = await client.async_get_music_genres(user_id, library_id)

        children: list[BrowseMedia] = []
        for genre in genres:
            children.append(
                BrowseMedia(
                    media_class=MediaClass.GENRE,
                    media_content_id=encode_content_id("musicgenre", library_id, genre["Id"]),
                    media_content_type=MediaType.MUSIC,
                    title=genre["Name"],
                    can_play=False,
                    can_expand=True,
                    thumbnail=None,
                )
            )

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("musicgenres", library_id),
            media_content_type=MediaType.MUSIC,
            title="Genres",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_genre_items(
        self, user_id: str, library_id: str, genre_id: str
    ) -> BrowseMedia:
        """Browse items in a genre.

        Args:
            user_id: The user ID for API calls.
            library_id: The music library ID.
            genre_id: The genre ID.

        Returns:
            BrowseMedia with albums in the genre as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        # Fetch albums in this genre using genre_ids filter
        result = await client.async_get_items(
            user_id,
            parent_id=library_id,
            include_item_types="MusicAlbum",
            recursive=True,
            genre_ids=genre_id,
        )
        items = result.get("Items", [])

        children: list[BrowseMedia] = []
        for item in items:
            children.append(self._album_to_browse_media(item))

        return BrowseMedia(
            media_class=MediaClass.GENRE,
            media_content_id=encode_content_id("musicgenre", library_id, genre_id),
            media_content_type=MediaType.MUSIC,
            title="Genre",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_music_playlists(self, user_id: str, library_id: str) -> BrowseMedia:
        """Browse music playlists.

        Args:
            user_id: The user ID for API calls.
            library_id: The music library ID.

        Returns:
            BrowseMedia with playlists as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        result = await client.async_get_items(
            user_id,
            include_item_types="Playlist",
            recursive=True,
        )
        items = result.get("Items", [])

        children: list[BrowseMedia] = []
        for item in items:
            children.append(self._item_to_browse_media(item))

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("musicplaylists", library_id),
            media_content_type=MediaType.PLAYLIST,
            title="Playlists",
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
            children.append(self._season_to_browse_media(season, series_id))

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

    async def _async_browse_artist(self, user_id: str, artist_id: str) -> BrowseMedia:
        """Browse a music artist - show albums.

        Args:
            user_id: The user ID for API calls.
            artist_id: The artist ID.

        Returns:
            BrowseMedia with albums as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        albums = await client.async_get_artist_albums(user_id, artist_id)

        children: list[BrowseMedia] = []
        for album in albums:
            children.append(self._album_to_browse_media(album))

        return BrowseMedia(
            media_class=MediaClass.ARTIST,
            media_content_id=encode_content_id("artist", artist_id),
            media_content_type=MediaType.MUSIC,
            title="Artist",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_album(self, user_id: str, album_id: str) -> BrowseMedia:
        """Browse a music album - show tracks.

        Args:
            user_id: The user ID for API calls.
            album_id: The album ID.

        Returns:
            BrowseMedia with tracks as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        tracks = await client.async_get_album_tracks(user_id, album_id)

        children: list[BrowseMedia] = []
        for track in tracks:
            children.append(self._track_to_browse_media(track))

        return BrowseMedia(
            media_class=MediaClass.ALBUM,
            media_content_id=encode_content_id("album", album_id),
            media_content_type=MediaType.MUSIC,
            title="Album",
            can_play=True,  # Albums can be played (queues all tracks)
            can_expand=True,
            children=children,
        )

    async def _async_browse_playlist(self, user_id: str, playlist_id: str) -> BrowseMedia:
        """Browse a playlist - show items.

        Args:
            user_id: The user ID for API calls.
            playlist_id: The playlist ID.

        Returns:
            BrowseMedia with playlist items as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        items = await client.async_get_playlist_items(user_id, playlist_id)

        children: list[BrowseMedia] = []
        for item in items:
            children.append(self._item_to_browse_media(item))

        return BrowseMedia(
            media_class=MediaClass.PLAYLIST,
            media_content_id=encode_content_id("playlist", playlist_id),
            media_content_type=MediaType.PLAYLIST,
            title="Playlist",
            can_play=True,  # Playlists can be played (queues all items)
            can_expand=True,
            children=children,
        )

    async def _async_browse_collection(self, user_id: str, collection_id: str) -> BrowseMedia:
        """Browse a collection (BoxSet) - show items.

        Args:
            user_id: The user ID for API calls.
            collection_id: The collection ID.

        Returns:
            BrowseMedia with collection items as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        items = await client.async_get_collection_items(user_id, collection_id)

        children: list[BrowseMedia] = []
        for item in items:
            children.append(self._item_to_browse_media(item))

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("collection", collection_id),
            media_content_type=MediaType.VIDEO,
            title="Collection",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_livetv(self, user_id: str) -> BrowseMedia:
        """Browse Live TV - show channels.

        Args:
            user_id: The user ID for API calls.

        Returns:
            BrowseMedia with Live TV channels as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        channels = await client.async_get_live_tv_channels(user_id)

        children: list[BrowseMedia] = []
        for channel in channels:
            children.append(self._item_to_browse_media(channel))

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("livetv"),
            media_content_type=MediaType.CHANNEL,
            title="Live TV",
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

        # Use special content types for each library type
        collection_type = library.get("CollectionType", "")
        if collection_type == "music":
            content_id = encode_content_id("musiclibrary", library["Id"])
            media_content_type = MediaType.MUSIC
        elif collection_type == "livetv":
            content_id = encode_content_id("livetv")
            media_content_type = MediaType.CHANNEL
        elif collection_type == "movies":
            content_id = encode_content_id("movielibrary", library["Id"])
            media_content_type = MediaType.VIDEO
        elif collection_type == "tvshows":
            content_id = encode_content_id("tvlibrary", library["Id"])
            media_content_type = MediaType.VIDEO
        else:
            content_id = encode_content_id("library", library["Id"])
            media_content_type = MediaType.VIDEO

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=content_id,
            media_content_type=media_content_type,
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
        elif item_type == "MusicArtist":
            content_id = encode_content_id("artist", item["Id"])
        elif item_type == "MusicAlbum":
            content_id = encode_content_id("album", item["Id"])
        elif item_type == "Playlist":
            content_id = encode_content_id("playlist", item["Id"])
        elif item_type == "BoxSet":
            content_id = encode_content_id("collection", item["Id"])
        elif item_type in ("Movie", "Episode", "Audio", "TvChannel"):
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

    def _season_to_browse_media(self, season: EmbyBrowseItem, series_id: str) -> BrowseMedia:
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

    def _album_to_browse_media(self, album: EmbyBrowseItem) -> BrowseMedia:
        """Convert a music album item to BrowseMedia.

        Args:
            album: The album item from API.

        Returns:
            BrowseMedia representation of the album.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        # Get thumbnail if available
        thumbnail: str | None = None
        image_tags = album.get("ImageTags", {})
        if "Primary" in image_tags:
            thumbnail = client.get_image_url(
                album["Id"], image_type="Primary", tag=image_tags["Primary"]
            )

        return BrowseMedia(
            media_class=MediaClass.ALBUM,
            media_content_id=encode_content_id("album", album["Id"]),
            media_content_type=MediaType.MUSIC,
            title=album["Name"],
            can_play=True,  # Albums can be played (queues all tracks)
            can_expand=True,
            thumbnail=thumbnail,
        )

    def _track_to_browse_media(self, track: EmbyBrowseItem) -> BrowseMedia:
        """Convert a music track item to BrowseMedia.

        Args:
            track: The track item from API.

        Returns:
            BrowseMedia representation of the track.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        # Get thumbnail if available
        thumbnail: str | None = None
        image_tags = track.get("ImageTags", {})
        if "Primary" in image_tags:
            thumbnail = client.get_image_url(
                track["Id"], image_type="Primary", tag=image_tags["Primary"]
            )

        return BrowseMedia(
            media_class=MediaClass.TRACK,
            media_content_id=encode_content_id("item", track["Id"]),
            media_content_type=MediaType.MUSIC,
            title=track["Name"],
            can_play=True,
            can_expand=False,
            thumbnail=thumbnail,
        )

    # -------------------------------------------------------------------------
    # Movie Library Browsing Methods
    # -------------------------------------------------------------------------

    async def _async_browse_movie_library(self, user_id: str, library_id: str) -> BrowseMedia:
        """Browse a movies library - show category menu.

        Movies libraries show categories (A-Z, Year, Decade, Genre, Collections)
        to organize large collections effectively.

        Args:
            user_id: The user ID for API calls.
            library_id: The movies library ID.

        Returns:
            BrowseMedia with categories as children.
        """
        categories = [
            ("A-Z", "movieaz", MediaClass.DIRECTORY),
            ("Year", "movieyear", MediaClass.DIRECTORY),
            ("Decade", "moviedecade", MediaClass.DIRECTORY),
            ("Genre", "moviegenre", MediaClass.DIRECTORY),
            ("Studio", "moviestudio", MediaClass.DIRECTORY),
            ("People", "moviepeople", MediaClass.DIRECTORY),
            ("Tags", "movietags", MediaClass.DIRECTORY),
            ("Collections", "moviecollection", MediaClass.DIRECTORY),
        ]

        children: list[BrowseMedia] = []
        for title, content_type, media_class in categories:
            children.append(
                BrowseMedia(
                    media_class=media_class,
                    media_content_id=encode_content_id(content_type, library_id),
                    media_content_type=MediaType.VIDEO,
                    title=title,
                    can_play=False,
                    can_expand=True,
                    thumbnail=None,
                )
            )

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("movielibrary", library_id),
            media_content_type=MediaType.VIDEO,
            title="Movies Library",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_movie_az(self, user_id: str, library_id: str) -> BrowseMedia:
        """Browse movies A-Z - show letter menu.

        Args:
            user_id: The user ID for API calls.
            library_id: The movies library ID.

        Returns:
            BrowseMedia with A-Z letters as children.
        """
        children = self._build_letter_menu("movieazletter", library_id, MediaType.VIDEO)

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("movieaz", library_id),
            media_content_type=MediaType.VIDEO,
            title="A-Z",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_movies_by_letter(
        self, user_id: str, library_id: str, letter: str
    ) -> BrowseMedia:
        """Browse movies starting with a specific letter.

        Args:
            user_id: The user ID for API calls.
            library_id: The movies library ID.
            letter: The letter to filter by (# for numbers/symbols).

        Returns:
            BrowseMedia with filtered movies as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        # For "#", we need special handling - Emby uses empty string for non-alpha
        name_filter = "" if letter == "#" else letter

        result = await client.async_get_items(
            user_id,
            parent_id=library_id,
            include_item_types="Movie",
            recursive=True,
            name_starts_with=name_filter if name_filter else None,
        )
        items = result.get("Items", [])

        # For "#", filter to non-alpha items manually
        if letter == "#":
            items = [i for i in items if not i.get("Name", "")[0:1].isalpha()]

        children: list[BrowseMedia] = []
        for item in items:
            children.append(self._item_to_browse_media(item))

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("movieazletter", library_id, letter),
            media_content_type=MediaType.VIDEO,
            title=f"Movies - {letter}",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_movie_years(self, user_id: str, library_id: str) -> BrowseMedia:
        """Browse movie years - show year list.

        Args:
            user_id: The user ID for API calls.
            library_id: The movies library ID.

        Returns:
            BrowseMedia with years as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        children: list[BrowseMedia] = []
        try:
            years = await client.async_get_years(
                user_id,
                parent_id=library_id,
                include_item_types="Movie",
            )
        except EmbyError as err:
            _LOGGER.debug("Failed to get movie years: %s", err)
            years = []

        for year in years:
            children.append(
                BrowseMedia(
                    media_class=MediaClass.DIRECTORY,
                    media_content_id=encode_content_id("movieyearitems", library_id, year["Name"]),
                    media_content_type=MediaType.VIDEO,
                    title=year["Name"],
                    can_play=False,
                    can_expand=True,
                    thumbnail=None,
                )
            )

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("movieyear", library_id),
            media_content_type=MediaType.VIDEO,
            title="Year",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_movies_by_year(
        self, user_id: str, library_id: str, year: str
    ) -> BrowseMedia:
        """Browse movies from a specific year.

        Args:
            user_id: The user ID for API calls.
            library_id: The movies library ID.
            year: The year to filter by.

        Returns:
            BrowseMedia with movies from that year as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        children: list[BrowseMedia] = []
        try:
            result = await client.async_get_items(
                user_id,
                parent_id=library_id,
                include_item_types="Movie",
                recursive=True,
                years=year,
            )
            items = result.get("Items", [])
        except EmbyError as err:
            _LOGGER.debug("Failed to get movies by year %s: %s", year, err)
            items = []

        for item in items:
            children.append(self._item_to_browse_media(item))

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("movieyearitems", library_id, year),
            media_content_type=MediaType.VIDEO,
            title=f"Movies - {year}",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_movie_decades(self, user_id: str, library_id: str) -> BrowseMedia:
        """Browse movie decades - show decade menu.

        Args:
            user_id: The user ID for API calls.
            library_id: The movies library ID.

        Returns:
            BrowseMedia with decades as children.
        """
        children = self._build_decade_menu("moviedecadeitems", library_id, MediaType.VIDEO)

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("moviedecade", library_id),
            media_content_type=MediaType.VIDEO,
            title="Decade",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_movies_by_decade(
        self, user_id: str, library_id: str, decade: str
    ) -> BrowseMedia:
        """Browse movies from a specific decade.

        Args:
            user_id: The user ID for API calls.
            library_id: The movies library ID.
            decade: The decade start year (e.g., "1990" for 1990s).

        Returns:
            BrowseMedia with movies from that decade as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        # Build year range for decade (e.g., 1990-1999)
        decade_start = int(decade)
        year_list = ",".join(str(y) for y in range(decade_start, decade_start + 10))

        result = await client.async_get_items(
            user_id,
            parent_id=library_id,
            include_item_types="Movie",
            recursive=True,
            years=year_list,
        )
        items = result.get("Items", [])

        children: list[BrowseMedia] = []
        for item in items:
            children.append(self._item_to_browse_media(item))

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("moviedecadeitems", library_id, decade),
            media_content_type=MediaType.VIDEO,
            title=f"Movies - {decade}s",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_movie_genres(self, user_id: str, library_id: str) -> BrowseMedia:
        """Browse movie genres - show genre list.

        Args:
            user_id: The user ID for API calls.
            library_id: The movies library ID.

        Returns:
            BrowseMedia with genres as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        genres = await client.async_get_genres(
            user_id,
            parent_id=library_id,
            include_item_types="Movie",
        )

        children: list[BrowseMedia] = []
        for genre in genres:
            children.append(
                BrowseMedia(
                    media_class=MediaClass.GENRE,
                    media_content_id=encode_content_id("moviegenreitems", library_id, genre["Id"]),
                    media_content_type=MediaType.VIDEO,
                    title=genre["Name"],
                    can_play=False,
                    can_expand=True,
                    thumbnail=None,
                )
            )

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("moviegenre", library_id),
            media_content_type=MediaType.VIDEO,
            title="Genre",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_movies_by_genre(
        self, user_id: str, library_id: str, genre_id: str
    ) -> BrowseMedia:
        """Browse movies in a specific genre.

        Args:
            user_id: The user ID for API calls.
            library_id: The movies library ID.
            genre_id: The genre ID to filter by.

        Returns:
            BrowseMedia with movies in that genre as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        result = await client.async_get_items(
            user_id,
            parent_id=library_id,
            include_item_types="Movie",
            recursive=True,
            genre_ids=genre_id,
        )
        items = result.get("Items", [])

        children: list[BrowseMedia] = []
        for item in items:
            children.append(self._item_to_browse_media(item))

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("moviegenreitems", library_id, genre_id),
            media_content_type=MediaType.VIDEO,
            title="Movies by Genre",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_movie_collections(self, user_id: str, library_id: str) -> BrowseMedia:
        """Browse movie collections (BoxSets) in the library.

        Args:
            user_id: The user ID for API calls.
            library_id: The movies library ID.

        Returns:
            BrowseMedia with collections as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        result = await client.async_get_items(
            user_id,
            parent_id=library_id,
            include_item_types="BoxSet",
            recursive=True,
        )
        items = result.get("Items", [])

        children: list[BrowseMedia] = []
        for item in items:
            children.append(self._item_to_browse_media(item))

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("moviecollection", library_id),
            media_content_type=MediaType.VIDEO,
            title="Collections",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_movie_studios(self, user_id: str, library_id: str) -> BrowseMedia:
        """Browse movie studios - show studio list.

        Args:
            user_id: The user ID for API calls.
            library_id: The movies library ID.

        Returns:
            BrowseMedia with studios as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        studios = await client.async_get_studios(
            user_id,
            parent_id=library_id,
            include_item_types="Movie",
        )

        children: list[BrowseMedia] = []
        for studio in studios:
            children.append(
                BrowseMedia(
                    media_class=MediaClass.DIRECTORY,
                    media_content_id=encode_content_id(
                        "moviestudioitems", library_id, studio["Id"]
                    ),
                    media_content_type=MediaType.VIDEO,
                    title=studio["Name"],
                    can_play=False,
                    can_expand=True,
                    thumbnail=None,
                )
            )

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("moviestudio", library_id),
            media_content_type=MediaType.VIDEO,
            title="Studio",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_movies_by_studio(
        self, user_id: str, library_id: str, studio_id: str
    ) -> BrowseMedia:
        """Browse movies from a specific studio.

        Args:
            user_id: The user ID for API calls.
            library_id: The movies library ID.
            studio_id: The studio ID to filter by.

        Returns:
            BrowseMedia with movies from that studio as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        result = await client.async_get_items(
            user_id,
            parent_id=library_id,
            include_item_types="Movie",
            recursive=True,
            studio_ids=studio_id,
        )
        items = result.get("Items", [])

        children: list[BrowseMedia] = []
        for item in items:
            children.append(self._item_to_browse_media(item))

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("moviestudioitems", library_id, studio_id),
            media_content_type=MediaType.VIDEO,
            title="Movies by Studio",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_movie_people(self, user_id: str, library_id: str) -> BrowseMedia:
        """Browse people (actors, directors, writers) in movie library.

        Args:
            user_id: The user ID for API calls.
            library_id: The movies library ID.

        Returns:
            BrowseMedia with person list as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        # Fetch persons from movie library
        persons_response = await client.async_get_persons(
            user_id,
            parent_id=library_id,
            limit=200,
        )
        persons = persons_response.get("Items", [])

        children: list[BrowseMedia] = []
        for person in persons:
            children.append(self._person_to_browse_media(person, library_id))

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("moviepeople", library_id),
            media_content_type=MediaType.VIDEO,
            title="People",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_person(
        self, user_id: str, person_id: str, library_id: str
    ) -> BrowseMedia:
        """Browse a person's filmography.

        Args:
            user_id: The user ID for API calls.
            person_id: The person ID.
            library_id: The library ID for filtering.

        Returns:
            BrowseMedia with person's works as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        # Fetch items featuring this person
        items = await client.async_get_person_items(
            user_id,
            person_id,
            include_item_types="Movie,Series",
            limit=200,
        )

        children: list[BrowseMedia] = []
        for item in items:
            children.append(self._item_to_browse_media(item))

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("person", library_id, person_id),
            media_content_type=MediaType.VIDEO,
            title="Filmography",
            can_play=False,
            can_expand=True,
            children=children,
        )

    def _person_to_browse_media(self, person: EmbyPerson, library_id: str) -> BrowseMedia:
        """Convert a person item to BrowseMedia.

        Args:
            person: The person from API.
            library_id: The library ID for content_id.

        Returns:
            BrowseMedia representation of the person.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        # Get thumbnail if available
        thumbnail: str | None = None
        image_tags = person.get("ImageTags", {})
        if isinstance(image_tags, dict) and "Primary" in image_tags:
            person_id = str(person.get("Id", ""))
            thumbnail = client.get_image_url(
                person_id, image_type="Primary", tag=str(image_tags["Primary"])
            )

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("person", library_id, str(person.get("Id", ""))),
            media_content_type=MediaType.VIDEO,
            title=str(person.get("Name", "Unknown")),
            can_play=False,
            can_expand=True,
            thumbnail=thumbnail,
        )

    async def _async_browse_movie_tags(self, user_id: str, library_id: str) -> BrowseMedia:
        """Browse tags in movie library.

        Args:
            user_id: The user ID for API calls.
            library_id: The movies library ID.

        Returns:
            BrowseMedia with tags as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        # Fetch tags from movie library
        tags = await client.async_get_tags(
            user_id,
            parent_id=library_id,
            include_item_types="Movie",
        )

        children: list[BrowseMedia] = []
        for tag in tags:
            children.append(
                BrowseMedia(
                    media_class=MediaClass.DIRECTORY,
                    media_content_id=encode_content_id("movietag", library_id, tag["Id"]),
                    media_content_type=MediaType.VIDEO,
                    title=tag["Name"],
                    can_play=False,
                    can_expand=True,
                    thumbnail=None,
                )
            )

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("movietags", library_id),
            media_content_type=MediaType.VIDEO,
            title="Tags",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_movies_by_tag(
        self, user_id: str, library_id: str, tag_id: str
    ) -> BrowseMedia:
        """Browse movies with a specific tag.

        Args:
            user_id: The user ID for API calls.
            library_id: The movies library ID.
            tag_id: The tag ID to filter by.

        Returns:
            BrowseMedia with movies having that tag as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        items = await client.async_get_items_by_tag(
            user_id,
            tag_id,
            parent_id=library_id,
            include_item_types="Movie",
        )

        children: list[BrowseMedia] = []
        for item in items:
            children.append(self._item_to_browse_media(item))

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("movietag", library_id, tag_id),
            media_content_type=MediaType.VIDEO,
            title="Movies by Tag",
            can_play=False,
            can_expand=True,
            children=children,
        )

    # -------------------------------------------------------------------------
    # TV Show Library Browsing Methods
    # -------------------------------------------------------------------------

    async def _async_browse_tv_library(self, user_id: str, library_id: str) -> BrowseMedia:
        """Browse a TV shows library - show category menu.

        TV libraries show categories (A-Z, Year, Decade, Genre)
        to organize large collections effectively.

        Args:
            user_id: The user ID for API calls.
            library_id: The TV shows library ID.

        Returns:
            BrowseMedia with categories as children.
        """
        categories = [
            ("A-Z", "tvaz", MediaClass.DIRECTORY),
            ("Year", "tvyear", MediaClass.DIRECTORY),
            ("Decade", "tvdecade", MediaClass.DIRECTORY),
            ("Genre", "tvgenre", MediaClass.DIRECTORY),
            ("Studio", "tvstudio", MediaClass.DIRECTORY),
        ]

        children: list[BrowseMedia] = []
        for title, content_type, media_class in categories:
            children.append(
                BrowseMedia(
                    media_class=media_class,
                    media_content_id=encode_content_id(content_type, library_id),
                    media_content_type=MediaType.TVSHOW,
                    title=title,
                    can_play=False,
                    can_expand=True,
                    thumbnail=None,
                )
            )

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("tvlibrary", library_id),
            media_content_type=MediaType.TVSHOW,
            title="TV Shows Library",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_tv_az(self, user_id: str, library_id: str) -> BrowseMedia:
        """Browse TV shows A-Z - show letter menu.

        Args:
            user_id: The user ID for API calls.
            library_id: The TV shows library ID.

        Returns:
            BrowseMedia with A-Z letters as children.
        """
        children = self._build_letter_menu("tvazletter", library_id, MediaType.TVSHOW)

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("tvaz", library_id),
            media_content_type=MediaType.TVSHOW,
            title="A-Z",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_tv_by_letter(
        self, user_id: str, library_id: str, letter: str
    ) -> BrowseMedia:
        """Browse TV shows starting with a specific letter.

        Args:
            user_id: The user ID for API calls.
            library_id: The TV shows library ID.
            letter: The letter to filter by (# for numbers/symbols).

        Returns:
            BrowseMedia with filtered TV shows as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        # For "#", we need special handling - Emby uses empty string for non-alpha
        name_filter = "" if letter == "#" else letter

        result = await client.async_get_items(
            user_id,
            parent_id=library_id,
            include_item_types="Series",
            recursive=True,
            name_starts_with=name_filter if name_filter else None,
        )
        items = result.get("Items", [])

        # For "#", filter to non-alpha items manually
        if letter == "#":
            items = [i for i in items if not i.get("Name", "")[0:1].isalpha()]

        children: list[BrowseMedia] = []
        for item in items:
            children.append(self._item_to_browse_media(item))

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("tvazletter", library_id, letter),
            media_content_type=MediaType.TVSHOW,
            title=f"TV Shows - {letter}",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_tv_years(self, user_id: str, library_id: str) -> BrowseMedia:
        """Browse TV show years - show year list.

        Args:
            user_id: The user ID for API calls.
            library_id: The TV shows library ID.

        Returns:
            BrowseMedia with years as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        children: list[BrowseMedia] = []
        try:
            years = await client.async_get_years(
                user_id,
                parent_id=library_id,
                include_item_types="Series",
            )
        except EmbyError as err:
            _LOGGER.debug("Failed to get TV years: %s", err)
            years = []

        for year in years:
            children.append(
                BrowseMedia(
                    media_class=MediaClass.DIRECTORY,
                    media_content_id=encode_content_id("tvyearitems", library_id, year["Name"]),
                    media_content_type=MediaType.TVSHOW,
                    title=year["Name"],
                    can_play=False,
                    can_expand=True,
                    thumbnail=None,
                )
            )

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("tvyear", library_id),
            media_content_type=MediaType.TVSHOW,
            title="Year",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_tv_by_year(
        self, user_id: str, library_id: str, year: str
    ) -> BrowseMedia:
        """Browse TV shows from a specific year.

        Args:
            user_id: The user ID for API calls.
            library_id: The TV shows library ID.
            year: The year to filter by.

        Returns:
            BrowseMedia with TV shows from that year as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        children: list[BrowseMedia] = []
        try:
            result = await client.async_get_items(
                user_id,
                parent_id=library_id,
                include_item_types="Series",
                recursive=True,
                years=year,
            )
            items = result.get("Items", [])
        except EmbyError as err:
            _LOGGER.debug("Failed to get TV shows by year %s: %s", year, err)
            items = []

        for item in items:
            children.append(self._item_to_browse_media(item))

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("tvyearitems", library_id, year),
            media_content_type=MediaType.TVSHOW,
            title=f"TV Shows - {year}",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_tv_decades(self, user_id: str, library_id: str) -> BrowseMedia:
        """Browse TV show decades - show decade menu.

        Args:
            user_id: The user ID for API calls.
            library_id: The TV shows library ID.

        Returns:
            BrowseMedia with decades as children.
        """
        children = self._build_decade_menu("tvdecadeitems", library_id, MediaType.TVSHOW)

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("tvdecade", library_id),
            media_content_type=MediaType.TVSHOW,
            title="Decade",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_tv_by_decade(
        self, user_id: str, library_id: str, decade: str
    ) -> BrowseMedia:
        """Browse TV shows from a specific decade.

        Args:
            user_id: The user ID for API calls.
            library_id: The TV shows library ID.
            decade: The decade start year (e.g., "1990" for 1990s).

        Returns:
            BrowseMedia with TV shows from that decade as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        # Build year range for decade (e.g., 1990-1999)
        decade_start = int(decade)
        year_list = ",".join(str(y) for y in range(decade_start, decade_start + 10))

        result = await client.async_get_items(
            user_id,
            parent_id=library_id,
            include_item_types="Series",
            recursive=True,
            years=year_list,
        )
        items = result.get("Items", [])

        children: list[BrowseMedia] = []
        for item in items:
            children.append(self._item_to_browse_media(item))

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("tvdecadeitems", library_id, decade),
            media_content_type=MediaType.TVSHOW,
            title=f"TV Shows - {decade}s",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_tv_genres(self, user_id: str, library_id: str) -> BrowseMedia:
        """Browse TV show genres - show genre list.

        Args:
            user_id: The user ID for API calls.
            library_id: The TV shows library ID.

        Returns:
            BrowseMedia with genres as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        genres = await client.async_get_genres(
            user_id,
            parent_id=library_id,
            include_item_types="Series",
        )

        children: list[BrowseMedia] = []
        for genre in genres:
            children.append(
                BrowseMedia(
                    media_class=MediaClass.GENRE,
                    media_content_id=encode_content_id("tvgenreitems", library_id, genre["Id"]),
                    media_content_type=MediaType.TVSHOW,
                    title=genre["Name"],
                    can_play=False,
                    can_expand=True,
                    thumbnail=None,
                )
            )

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("tvgenre", library_id),
            media_content_type=MediaType.TVSHOW,
            title="Genre",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_tv_by_genre(
        self, user_id: str, library_id: str, genre_id: str
    ) -> BrowseMedia:
        """Browse TV shows in a specific genre.

        Args:
            user_id: The user ID for API calls.
            library_id: The TV shows library ID.
            genre_id: The genre ID to filter by.

        Returns:
            BrowseMedia with TV shows in that genre as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        result = await client.async_get_items(
            user_id,
            parent_id=library_id,
            include_item_types="Series",
            recursive=True,
            genre_ids=genre_id,
        )
        items = result.get("Items", [])

        children: list[BrowseMedia] = []
        for item in items:
            children.append(self._item_to_browse_media(item))

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("tvgenreitems", library_id, genre_id),
            media_content_type=MediaType.TVSHOW,
            title="TV Shows by Genre",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_tv_studios(self, user_id: str, library_id: str) -> BrowseMedia:
        """Browse TV studios/networks - show studio list.

        Args:
            user_id: The user ID for API calls.
            library_id: The TV shows library ID.

        Returns:
            BrowseMedia with studios/networks as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        studios = await client.async_get_studios(
            user_id,
            parent_id=library_id,
            include_item_types="Series",
        )

        children: list[BrowseMedia] = []
        for studio in studios:
            children.append(
                BrowseMedia(
                    media_class=MediaClass.DIRECTORY,
                    media_content_id=encode_content_id("tvstudioitems", library_id, studio["Id"]),
                    media_content_type=MediaType.TVSHOW,
                    title=studio["Name"],
                    can_play=False,
                    can_expand=True,
                    thumbnail=None,
                )
            )

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("tvstudio", library_id),
            media_content_type=MediaType.TVSHOW,
            title="Studio",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_tv_by_studio(
        self, user_id: str, library_id: str, studio_id: str
    ) -> BrowseMedia:
        """Browse TV shows from a specific studio/network.

        Args:
            user_id: The user ID for API calls.
            library_id: The TV shows library ID.
            studio_id: The studio/network ID to filter by.

        Returns:
            BrowseMedia with TV shows from that studio as children.
        """
        coordinator: EmbyDataUpdateCoordinator = self.coordinator
        client = coordinator.client

        result = await client.async_get_items(
            user_id,
            parent_id=library_id,
            include_item_types="Series",
            recursive=True,
            studio_ids=studio_id,
        )
        items = result.get("Items", [])

        children: list[BrowseMedia] = []
        for item in items:
            children.append(self._item_to_browse_media(item))

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=encode_content_id("tvstudioitems", library_id, studio_id),
            media_content_type=MediaType.TVSHOW,
            title="TV Shows by Studio",
            can_play=False,
            can_expand=True,
            children=children,
        )


__all__ = ["EmbyMediaPlayer", "async_setup_entry"]
