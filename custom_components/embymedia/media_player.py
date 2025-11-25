"""Media player platform for Emby integration."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import TYPE_CHECKING

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .entity import EmbyEntity
from .models import MediaType as EmbyMediaType

if TYPE_CHECKING:
    from .const import EmbyConfigEntry
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
        return dt_util.utcnow()


__all__ = ["EmbyMediaPlayer", "async_setup_entry"]
