"""Tests for Emby media player platform."""
from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.media_player import (
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.core import HomeAssistant

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_session_playing() -> MagicMock:
    """Create a mock session that is playing."""
    session = MagicMock()
    session.device_id = "device-abc-123"
    session.device_name = "Living Room TV"
    session.client_name = "Emby Theater"
    session.app_version = "4.8.0.0"
    session.is_playing = True
    session.play_state = MagicMock()
    session.play_state.is_paused = False
    return session


@pytest.fixture
def mock_session_paused() -> MagicMock:
    """Create a mock session that is paused."""
    session = MagicMock()
    session.device_id = "device-abc-123"
    session.device_name = "Living Room TV"
    session.client_name = "Emby Theater"
    session.app_version = "4.8.0.0"
    session.is_playing = True
    session.play_state = MagicMock()
    session.play_state.is_paused = True
    return session


@pytest.fixture
def mock_session_idle() -> MagicMock:
    """Create a mock session that is idle."""
    session = MagicMock()
    session.device_id = "device-abc-123"
    session.device_name = "Living Room TV"
    session.client_name = "Emby Theater"
    session.app_version = "4.8.0.0"
    session.is_playing = False
    session.play_state = None
    return session


@pytest.fixture
def mock_coordinator(hass: HomeAssistant) -> MagicMock:
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.server_id = "server-123"
    coordinator.server_name = "My Emby Server"
    coordinator.last_update_success = True
    coordinator.data = {}
    coordinator.get_session = MagicMock(return_value=None)
    coordinator.async_add_listener = MagicMock(return_value=MagicMock())
    return coordinator


class TestEmbyMediaPlayerState:
    """Test EmbyMediaPlayer state property."""

    def test_state_off_when_no_session(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test state is OFF when session is None."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator.get_session.return_value = None

        player = EmbyMediaPlayer(mock_coordinator, "device-xyz")

        assert player.state == MediaPlayerState.OFF

    def test_state_idle_when_not_playing(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
        mock_session_idle: MagicMock,
    ) -> None:
        """Test state is IDLE when session exists but nothing playing."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator.get_session.return_value = mock_session_idle

        player = EmbyMediaPlayer(mock_coordinator, "device-abc-123")

        assert player.state == MediaPlayerState.IDLE

    def test_state_paused_when_paused(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
        mock_session_paused: MagicMock,
    ) -> None:
        """Test state is PAUSED when playback is paused."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator.get_session.return_value = mock_session_paused

        player = EmbyMediaPlayer(mock_coordinator, "device-abc-123")

        assert player.state == MediaPlayerState.PAUSED

    def test_state_playing_when_playing(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
        mock_session_playing: MagicMock,
    ) -> None:
        """Test state is PLAYING when actively playing."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator.get_session.return_value = mock_session_playing

        player = EmbyMediaPlayer(mock_coordinator, "device-abc-123")

        assert player.state == MediaPlayerState.PLAYING


class TestEmbyMediaPlayerInit:
    """Test EmbyMediaPlayer initialization."""

    def test_media_player_inherits_from_emby_entity(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media player inherits EmbyEntity functionality."""
        from custom_components.embymedia.entity import EmbyEntity
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        player = EmbyMediaPlayer(mock_coordinator, "device-abc-123")

        assert isinstance(player, EmbyEntity)
        assert player._device_id == "device-abc-123"

    def test_media_player_name_is_none(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media player uses device name (name is None)."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        player = EmbyMediaPlayer(mock_coordinator, "device-abc-123")

        assert player._attr_name is None


class TestAsyncSetupEntry:
    """Test async_setup_entry function."""

    @pytest.mark.asyncio
    async def test_creates_entities_for_existing_sessions(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
        mock_session_idle: MagicMock,
    ) -> None:
        """Test entities are created for sessions that exist at setup time."""

        from custom_components.embymedia.media_player import async_setup_entry

        # Setup coordinator with existing session
        mock_coordinator.data = {"device-abc-123": mock_session_idle}

        # Create mock config entry
        mock_entry = MagicMock()
        mock_entry.runtime_data = mock_coordinator
        mock_entry.async_on_unload = MagicMock()

        # Track added entities
        added_entities: list = []

        def track_entities(entities: list) -> None:
            added_entities.extend(entities)

        await async_setup_entry(hass, mock_entry, track_entities)

        assert len(added_entities) == 1
        assert added_entities[0]._device_id == "device-abc-123"

    @pytest.mark.asyncio
    async def test_no_entities_when_no_sessions(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test no entities created when coordinator has no sessions."""
        from custom_components.embymedia.media_player import async_setup_entry

        mock_coordinator.data = {}

        mock_entry = MagicMock()
        mock_entry.runtime_data = mock_coordinator
        mock_entry.async_on_unload = MagicMock()

        added_entities: list = []

        def track_entities(entities: list) -> None:
            added_entities.extend(entities)

        await async_setup_entry(hass, mock_entry, track_entities)

        assert len(added_entities) == 0

    @pytest.mark.asyncio
    async def test_registers_coordinator_listener(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test coordinator listener is registered for new sessions."""
        from custom_components.embymedia.media_player import async_setup_entry

        mock_coordinator.data = {}

        mock_entry = MagicMock()
        mock_entry.runtime_data = mock_coordinator
        mock_entry.async_on_unload = MagicMock()

        await async_setup_entry(hass, mock_entry, MagicMock())

        mock_coordinator.async_add_listener.assert_called_once()
        mock_entry.async_on_unload.assert_called_once()

    @pytest.mark.asyncio
    async def test_adds_new_entities_on_coordinator_update(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
        mock_session_idle: MagicMock,
    ) -> None:
        """Test new entities are added when coordinator discovers new sessions."""
        from custom_components.embymedia.media_player import async_setup_entry

        # Start with no sessions
        mock_coordinator.data = {}

        mock_entry = MagicMock()
        mock_entry.runtime_data = mock_coordinator
        mock_entry.async_on_unload = MagicMock()

        added_entities: list = []

        def track_entities(entities: list) -> None:
            added_entities.extend(entities)

        # Capture the listener callback
        listener_callback = None

        def capture_listener(callback):
            nonlocal listener_callback
            listener_callback = callback
            return MagicMock()

        mock_coordinator.async_add_listener = capture_listener

        await async_setup_entry(hass, mock_entry, track_entities)

        # No entities initially
        assert len(added_entities) == 0

        # Simulate coordinator update with new session
        mock_coordinator.data = {"device-abc-123": mock_session_idle}
        listener_callback()

        # Entity should be added
        assert len(added_entities) == 1
        assert added_entities[0]._device_id == "device-abc-123"

    @pytest.mark.asyncio
    async def test_does_not_duplicate_entities(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
        mock_session_idle: MagicMock,
    ) -> None:
        """Test same device doesn't create duplicate entities."""
        from custom_components.embymedia.media_player import async_setup_entry

        mock_coordinator.data = {"device-abc-123": mock_session_idle}

        mock_entry = MagicMock()
        mock_entry.runtime_data = mock_coordinator
        mock_entry.async_on_unload = MagicMock()

        added_entities: list = []

        def track_entities(entities: list) -> None:
            added_entities.extend(entities)

        # Capture listener
        listener_callback = None

        def capture_listener(callback):
            nonlocal listener_callback
            listener_callback = callback
            return MagicMock()

        mock_coordinator.async_add_listener = capture_listener

        await async_setup_entry(hass, mock_entry, track_entities)

        # One entity initially
        assert len(added_entities) == 1

        # Simulate coordinator update with same session
        listener_callback()

        # Still only one entity
        assert len(added_entities) == 1

    @pytest.mark.asyncio
    async def test_handles_none_coordinator_data(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test handles case when coordinator.data is None."""
        from custom_components.embymedia.media_player import async_setup_entry

        mock_coordinator.data = None

        mock_entry = MagicMock()
        mock_entry.runtime_data = mock_coordinator
        mock_entry.async_on_unload = MagicMock()

        added_entities: list = []

        def track_entities(entities: list) -> None:
            added_entities.extend(entities)

        await async_setup_entry(hass, mock_entry, track_entities)

        # No crash, no entities
        assert len(added_entities) == 0


class TestEntityLifecycle:
    """Test dynamic entity lifecycle."""

    def test_entity_unavailable_when_session_disappears(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
        mock_session_idle: MagicMock,
    ) -> None:
        """Test entity becomes unavailable when session disappears."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        # Initially session exists
        mock_coordinator.get_session.return_value = mock_session_idle
        mock_coordinator.last_update_success = True

        player = EmbyMediaPlayer(mock_coordinator, "device-abc-123")
        assert player.available is True

        # Session disappears
        mock_coordinator.get_session.return_value = None
        assert player.available is False

    def test_entity_available_when_session_returns(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
        mock_session_idle: MagicMock,
    ) -> None:
        """Test entity becomes available when session returns."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        # Initially session is gone
        mock_coordinator.get_session.return_value = None
        mock_coordinator.last_update_success = True

        player = EmbyMediaPlayer(mock_coordinator, "device-abc-123")
        assert player.available is False

        # Session returns (same device_id)
        mock_coordinator.get_session.return_value = mock_session_idle
        assert player.available is True

    def test_reconnecting_client_uses_same_entity(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
        mock_session_idle: MagicMock,
    ) -> None:
        """Test reconnecting client (same device_id) uses the same entity."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        # First session
        mock_coordinator.get_session.return_value = mock_session_idle
        mock_coordinator.last_update_success = True

        player = EmbyMediaPlayer(mock_coordinator, "device-abc-123")
        original_unique_id = player.unique_id

        # Session disconnects
        mock_coordinator.get_session.return_value = None
        assert player.available is False

        # New session with same device_id (reconnection)
        new_session = MagicMock()
        new_session.device_id = "device-abc-123"  # Same device
        new_session.device_name = "Living Room TV"
        new_session.client_name = "Emby Theater"
        new_session.app_version = "4.8.0.0"
        new_session.is_playing = False
        new_session.play_state = None

        mock_coordinator.get_session.return_value = new_session

        # Same entity should be available again with same unique_id
        assert player.available is True
        assert player.unique_id == original_unique_id


class TestSupportedFeatures:
    """Test supported_features property."""

    def test_supported_features_zero_when_no_session(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test supported_features returns 0 when session is None."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator.get_session.return_value = None

        player = EmbyMediaPlayer(mock_coordinator, "device-xyz")

        assert player.supported_features == MediaPlayerEntityFeature(0)

    def test_supported_features_basic_when_remote_control(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test basic features when session supports remote control."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.supports_remote_control = True
        session.supported_commands = ()
        session.play_state = None

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        features = player.supported_features
        assert features & MediaPlayerEntityFeature.PAUSE
        assert features & MediaPlayerEntityFeature.PLAY
        assert features & MediaPlayerEntityFeature.STOP
        assert features & MediaPlayerEntityFeature.NEXT_TRACK
        assert features & MediaPlayerEntityFeature.PREVIOUS_TRACK
        assert features & MediaPlayerEntityFeature.PLAY_MEDIA
        assert features & MediaPlayerEntityFeature.BROWSE_MEDIA

    def test_supported_features_volume_when_supported(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test volume features enabled when commands supported."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.supports_remote_control = True
        session.supported_commands = ("SetVolume", "Mute", "Unmute")
        session.play_state = None

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        features = player.supported_features
        assert features & MediaPlayerEntityFeature.VOLUME_SET
        assert features & MediaPlayerEntityFeature.VOLUME_MUTE

    def test_supported_features_no_volume_when_not_supported(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test volume features disabled when commands not supported."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.supports_remote_control = True
        session.supported_commands = ()  # No volume commands
        session.play_state = None

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        features = player.supported_features
        assert not (features & MediaPlayerEntityFeature.VOLUME_SET)
        assert not (features & MediaPlayerEntityFeature.VOLUME_MUTE)

    def test_supported_features_seek_when_can_seek(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test seek feature enabled when can_seek is True."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.supports_remote_control = True
        session.supported_commands = ()
        session.play_state = MagicMock()
        session.play_state.can_seek = True

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        features = player.supported_features
        assert features & MediaPlayerEntityFeature.SEEK

    def test_supported_features_no_seek_when_cannot_seek(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test seek feature disabled when can_seek is False."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.supports_remote_control = True
        session.supported_commands = ()
        session.play_state = MagicMock()
        session.play_state.can_seek = False

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        features = player.supported_features
        assert not (features & MediaPlayerEntityFeature.SEEK)

    def test_supported_features_no_remote_control(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test no features when remote control not supported."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.supports_remote_control = False
        session.supported_commands = ("SetVolume", "Mute")
        session.play_state = MagicMock()
        session.play_state.can_seek = True

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.supported_features == MediaPlayerEntityFeature(0)


class TestMediaContentProperties:
    """Test media content properties."""

    def test_media_content_id_when_playing(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_content_id returns item ID when playing."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.now_playing = MagicMock()
        session.now_playing.item_id = "item-123-abc"

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.media_content_id == "item-123-abc"

    def test_media_content_id_when_not_playing(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_content_id returns None when not playing."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.now_playing = None

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.media_content_id is None

    def test_media_content_id_when_no_session(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_content_id returns None when session is None."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator.get_session.return_value = None

        player = EmbyMediaPlayer(mock_coordinator, "device-xyz")

        assert player.media_content_id is None

    def test_media_content_type_movie(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_content_type maps Movie correctly."""
        from homeassistant.components.media_player import MediaType

        from custom_components.embymedia.media_player import EmbyMediaPlayer
        from custom_components.embymedia.models import MediaType as EmbyMediaType

        session = MagicMock()
        session.now_playing = MagicMock()
        session.now_playing.media_type = EmbyMediaType.MOVIE

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.media_content_type == MediaType.MOVIE

    def test_media_content_type_episode(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_content_type maps Episode to TVSHOW."""
        from homeassistant.components.media_player import MediaType

        from custom_components.embymedia.media_player import EmbyMediaPlayer
        from custom_components.embymedia.models import MediaType as EmbyMediaType

        session = MagicMock()
        session.now_playing = MagicMock()
        session.now_playing.media_type = EmbyMediaType.EPISODE

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.media_content_type == MediaType.TVSHOW

    def test_media_content_type_audio(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_content_type maps Audio to MUSIC."""
        from homeassistant.components.media_player import MediaType

        from custom_components.embymedia.media_player import EmbyMediaPlayer
        from custom_components.embymedia.models import MediaType as EmbyMediaType

        session = MagicMock()
        session.now_playing = MagicMock()
        session.now_playing.media_type = EmbyMediaType.AUDIO

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.media_content_type == MediaType.MUSIC

    def test_media_content_type_when_not_playing(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_content_type returns None when not playing."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.now_playing = None

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.media_content_type is None


class TestMediaTitleProperties:
    """Test media title properties."""

    def test_media_title_when_playing(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_title returns item name when playing."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.now_playing = MagicMock()
        session.now_playing.name = "The Matrix"

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.media_title == "The Matrix"

    def test_media_title_when_not_playing(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_title returns None when not playing."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.now_playing = None

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.media_title is None

    def test_media_series_title_for_episode(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_series_title returns series name for episodes."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.now_playing = MagicMock()
        session.now_playing.series_name = "Breaking Bad"

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.media_series_title == "Breaking Bad"

    def test_media_series_title_when_not_episode(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_series_title returns None for non-episodes."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.now_playing = MagicMock()
        session.now_playing.series_name = None

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.media_series_title is None

    def test_media_season(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_season returns season number as string."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.now_playing = MagicMock()
        session.now_playing.season_number = 5

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.media_season == "5"

    def test_media_season_when_none(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_season returns None when season_number is None."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.now_playing = MagicMock()
        session.now_playing.season_number = None

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.media_season is None

    def test_media_episode(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_episode returns episode number as string."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.now_playing = MagicMock()
        session.now_playing.episode_number = 16

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.media_episode == "16"

    def test_media_episode_when_none(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_episode returns None when episode_number is None."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.now_playing = MagicMock()
        session.now_playing.episode_number = None

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.media_episode is None


class TestMusicMetadataProperties:
    """Test music metadata properties."""

    def test_media_artist_with_multiple_artists(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_artist joins multiple artists."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.now_playing = MagicMock()
        session.now_playing.artists = ("Artist A", "Artist B", "Artist C")
        session.now_playing.album_artist = "Album Artist"

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.media_artist == "Artist A, Artist B, Artist C"

    def test_media_artist_fallback_to_album_artist(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_artist falls back to album_artist when no artists."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.now_playing = MagicMock()
        session.now_playing.artists = ()
        session.now_playing.album_artist = "Album Artist"

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.media_artist == "Album Artist"

    def test_media_artist_when_none(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_artist returns None when no artists or album_artist."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.now_playing = MagicMock()
        session.now_playing.artists = ()
        session.now_playing.album_artist = None

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.media_artist is None

    def test_media_album_name(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_album_name returns album name."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.now_playing = MagicMock()
        session.now_playing.album = "Greatest Hits"

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.media_album_name == "Greatest Hits"

    def test_media_album_artist(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_album_artist returns album artist."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.now_playing = MagicMock()
        session.now_playing.album_artist = "The Artist"

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.media_album_artist == "The Artist"


class TestDurationPositionProperties:
    """Test duration and position properties."""

    def test_media_duration_when_playing(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_duration returns duration in seconds."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.now_playing = MagicMock()
        session.now_playing.duration_seconds = 7200.5  # 2 hours

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.media_duration == 7200

    def test_media_duration_when_none(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_duration returns None when duration_seconds is None."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.now_playing = MagicMock()
        session.now_playing.duration_seconds = None

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.media_duration is None

    def test_media_duration_when_not_playing(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_duration returns None when not playing."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.now_playing = None

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.media_duration is None

    def test_media_position_when_playing(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_position returns current position in seconds."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.play_state = MagicMock()
        session.play_state.position_seconds = 1234.7

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.media_position == 1234

    def test_media_position_when_no_play_state(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_position returns None when play_state is None."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.play_state = None

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.media_position is None

    def test_media_position_updated_at(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_position_updated_at returns timestamp."""
        from datetime import datetime

        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.play_state = MagicMock()

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        result = player.media_position_updated_at
        assert result is not None
        assert isinstance(result, datetime)

    def test_media_position_updated_at_when_no_play_state(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_position_updated_at returns None when play_state is None."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.play_state = None

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.media_position_updated_at is None


class TestVolumeProperties:
    """Test volume control properties."""

    def test_volume_level_when_available(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test volume_level returns level from play_state."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.play_state = MagicMock()
        session.play_state.volume_level = 0.75

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.volume_level == 0.75

    def test_volume_level_when_no_play_state(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test volume_level returns None when play_state is None."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.play_state = None

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.volume_level is None

    def test_volume_level_when_no_session(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test volume_level returns None when session is None."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator.get_session.return_value = None

        player = EmbyMediaPlayer(mock_coordinator, "device-xyz")

        assert player.volume_level is None

    def test_is_volume_muted_true(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test is_volume_muted returns True when muted."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.play_state = MagicMock()
        session.play_state.is_muted = True

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.is_volume_muted is True

    def test_is_volume_muted_false(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test is_volume_muted returns False when not muted."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.play_state = MagicMock()
        session.play_state.is_muted = False

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.is_volume_muted is False

    def test_is_volume_muted_when_no_play_state(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test is_volume_muted returns None when play_state is None."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.play_state = None

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.is_volume_muted is None


class TestVolumeServices:
    """Test volume control services."""

    @pytest.mark.asyncio
    async def test_async_set_volume_level(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test async_set_volume_level calls API correctly."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.session_id = "session-xyz"

        mock_coordinator.get_session.return_value = session
        mock_coordinator.client = MagicMock()
        mock_coordinator.client.async_send_command = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        await player.async_set_volume_level(0.75)

        mock_coordinator.client.async_send_command.assert_called_once_with(
            "session-xyz",
            "SetVolume",
            {"Volume": 75},
        )

    @pytest.mark.asyncio
    async def test_async_set_volume_level_rounds_correctly(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test async_set_volume_level rounds to integer correctly."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.session_id = "session-xyz"

        mock_coordinator.get_session.return_value = session
        mock_coordinator.client = MagicMock()
        mock_coordinator.client.async_send_command = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        await player.async_set_volume_level(0.333)

        mock_coordinator.client.async_send_command.assert_called_once_with(
            "session-xyz",
            "SetVolume",
            {"Volume": 33},
        )

    @pytest.mark.asyncio
    async def test_async_set_volume_level_no_session(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test async_set_volume_level does nothing when no session."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator.get_session.return_value = None
        mock_coordinator.client = MagicMock()
        mock_coordinator.client.async_send_command = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator, "device-xyz")

        await player.async_set_volume_level(0.5)

        mock_coordinator.client.async_send_command.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_mute_volume_mute(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test async_mute_volume sends Mute command."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.session_id = "session-xyz"

        mock_coordinator.get_session.return_value = session
        mock_coordinator.client = MagicMock()
        mock_coordinator.client.async_send_command = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        await player.async_mute_volume(mute=True)

        mock_coordinator.client.async_send_command.assert_called_once_with(
            "session-xyz",
            "Mute",
        )

    @pytest.mark.asyncio
    async def test_async_mute_volume_unmute(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test async_mute_volume sends Unmute command."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.session_id = "session-xyz"

        mock_coordinator.get_session.return_value = session
        mock_coordinator.client = MagicMock()
        mock_coordinator.client.async_send_command = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        await player.async_mute_volume(mute=False)

        mock_coordinator.client.async_send_command.assert_called_once_with(
            "session-xyz",
            "Unmute",
        )

    @pytest.mark.asyncio
    async def test_async_mute_volume_no_session(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test async_mute_volume does nothing when no session."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator.get_session.return_value = None
        mock_coordinator.client = MagicMock()
        mock_coordinator.client.async_send_command = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator, "device-xyz")

        await player.async_mute_volume(mute=True)

        mock_coordinator.client.async_send_command.assert_not_called()


class TestPlaybackControlServices:
    """Test playback control services."""

    @pytest.mark.asyncio
    async def test_async_media_play(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test async_media_play sends Unpause command."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.session_id = "session-xyz"

        mock_coordinator.get_session.return_value = session
        mock_coordinator.client = MagicMock()
        mock_coordinator.client.async_send_playback_command = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        await player.async_media_play()

        mock_coordinator.client.async_send_playback_command.assert_called_once_with(
            "session-xyz",
            "Unpause",
        )

    @pytest.mark.asyncio
    async def test_async_media_play_no_session(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test async_media_play does nothing when no session."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator.get_session.return_value = None
        mock_coordinator.client = MagicMock()
        mock_coordinator.client.async_send_playback_command = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator, "device-xyz")

        await player.async_media_play()

        mock_coordinator.client.async_send_playback_command.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_media_pause(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test async_media_pause sends Pause command."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.session_id = "session-xyz"

        mock_coordinator.get_session.return_value = session
        mock_coordinator.client = MagicMock()
        mock_coordinator.client.async_send_playback_command = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        await player.async_media_pause()

        mock_coordinator.client.async_send_playback_command.assert_called_once_with(
            "session-xyz",
            "Pause",
        )

    @pytest.mark.asyncio
    async def test_async_media_stop(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test async_media_stop sends Stop command."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.session_id = "session-xyz"

        mock_coordinator.get_session.return_value = session
        mock_coordinator.client = MagicMock()
        mock_coordinator.client.async_send_playback_command = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        await player.async_media_stop()

        mock_coordinator.client.async_send_playback_command.assert_called_once_with(
            "session-xyz",
            "Stop",
        )

    @pytest.mark.asyncio
    async def test_async_media_next_track(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test async_media_next_track sends NextTrack command."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.session_id = "session-xyz"

        mock_coordinator.get_session.return_value = session
        mock_coordinator.client = MagicMock()
        mock_coordinator.client.async_send_playback_command = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        await player.async_media_next_track()

        mock_coordinator.client.async_send_playback_command.assert_called_once_with(
            "session-xyz",
            "NextTrack",
        )

    @pytest.mark.asyncio
    async def test_async_media_previous_track(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test async_media_previous_track sends PreviousTrack command."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.session_id = "session-xyz"

        mock_coordinator.get_session.return_value = session
        mock_coordinator.client = MagicMock()
        mock_coordinator.client.async_send_playback_command = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        await player.async_media_previous_track()

        mock_coordinator.client.async_send_playback_command.assert_called_once_with(
            "session-xyz",
            "PreviousTrack",
        )

    @pytest.mark.asyncio
    async def test_async_media_seek(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test async_media_seek sends Seek command with ticks."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.session_id = "session-xyz"

        mock_coordinator.get_session.return_value = session
        mock_coordinator.client = MagicMock()
        mock_coordinator.client.async_send_playback_command = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        # Seek to 5 seconds = 50,000,000 ticks
        await player.async_media_seek(5.0)

        mock_coordinator.client.async_send_playback_command.assert_called_once_with(
            "session-xyz",
            "Seek",
            {"SeekPositionTicks": 50000000},
        )

    @pytest.mark.asyncio
    async def test_async_media_seek_fractional(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test async_media_seek handles fractional seconds."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.session_id = "session-xyz"

        mock_coordinator.get_session.return_value = session
        mock_coordinator.client = MagicMock()
        mock_coordinator.client.async_send_playback_command = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        # Seek to 1.5 seconds = 15,000,000 ticks
        await player.async_media_seek(1.5)

        mock_coordinator.client.async_send_playback_command.assert_called_once_with(
            "session-xyz",
            "Seek",
            {"SeekPositionTicks": 15000000},
        )

    @pytest.mark.asyncio
    async def test_async_media_seek_no_session(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test async_media_seek does nothing when no session."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator.get_session.return_value = None
        mock_coordinator.client = MagicMock()
        mock_coordinator.client.async_send_playback_command = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator, "device-xyz")

        await player.async_media_seek(5.0)

        mock_coordinator.client.async_send_playback_command.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_media_pause_no_session(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test async_media_pause does nothing when no session."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator.get_session.return_value = None
        mock_coordinator.client = MagicMock()
        mock_coordinator.client.async_send_playback_command = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator, "device-xyz")

        await player.async_media_pause()

        mock_coordinator.client.async_send_playback_command.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_media_stop_no_session(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test async_media_stop does nothing when no session."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator.get_session.return_value = None
        mock_coordinator.client = MagicMock()
        mock_coordinator.client.async_send_playback_command = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator, "device-xyz")

        await player.async_media_stop()

        mock_coordinator.client.async_send_playback_command.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_media_next_track_no_session(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test async_media_next_track does nothing when no session."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator.get_session.return_value = None
        mock_coordinator.client = MagicMock()
        mock_coordinator.client.async_send_playback_command = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator, "device-xyz")

        await player.async_media_next_track()

        mock_coordinator.client.async_send_playback_command.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_media_previous_track_no_session(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test async_media_previous_track does nothing when no session."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator.get_session.return_value = None
        mock_coordinator.client = MagicMock()
        mock_coordinator.client.async_send_playback_command = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator, "device-xyz")

        await player.async_media_previous_track()

        mock_coordinator.client.async_send_playback_command.assert_not_called()


class TestMediaImageUrl:
    """Test media_image_url property."""

    def test_media_image_url_when_playing_movie(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_image_url returns valid URL when playing a movie."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.now_playing = MagicMock()
        session.now_playing.item_id = "movie-123"
        session.now_playing.image_tags = (("Primary", "abc123"),)
        session.now_playing.series_id = None
        session.now_playing.album_id = None

        mock_coordinator.get_session.return_value = session
        mock_coordinator.client = MagicMock()
        mock_coordinator.client.get_image_url.return_value = (
            "http://emby:8096/Items/movie-123/Images/Primary?api_key=key&tag=abc123"
        )

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        url = player.media_image_url
        assert url is not None
        assert "movie-123" in url
        mock_coordinator.client.get_image_url.assert_called_once_with(
            "movie-123",
            image_type="Primary",
            tag="abc123",
        )

    def test_media_image_url_when_not_playing(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_image_url returns None when not playing."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.now_playing = None

        mock_coordinator.get_session.return_value = session

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        assert player.media_image_url is None

    def test_media_image_url_when_no_session(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_image_url returns None when session is None."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator.get_session.return_value = None

        player = EmbyMediaPlayer(mock_coordinator, "device-xyz")

        assert player.media_image_url is None

    def test_media_image_url_without_primary_tag(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_image_url works without Primary tag."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.now_playing = MagicMock()
        session.now_playing.item_id = "movie-123"
        session.now_playing.image_tags = ()  # No tags
        session.now_playing.series_id = None
        session.now_playing.album_id = None

        mock_coordinator.get_session.return_value = session
        mock_coordinator.client = MagicMock()
        mock_coordinator.client.get_image_url.return_value = (
            "http://emby:8096/Items/movie-123/Images/Primary?api_key=key"
        )

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        url = player.media_image_url
        assert url is not None
        # Called without tag when no Primary tag
        mock_coordinator.client.get_image_url.assert_called_once_with(
            "movie-123",
            image_type="Primary",
            tag=None,
        )

    def test_media_image_url_episode_fallback_to_series(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_image_url falls back to series for episodes without images."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.now_playing = MagicMock()
        session.now_playing.item_id = "episode-123"
        session.now_playing.image_tags = ()  # No episode image
        session.now_playing.series_id = "series-456"
        session.now_playing.album_id = None

        mock_coordinator.get_session.return_value = session
        mock_coordinator.client = MagicMock()
        mock_coordinator.client.get_image_url.return_value = (
            "http://emby:8096/Items/series-456/Images/Primary?api_key=key"
        )

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        url = player.media_image_url
        assert url is not None
        # Should use series_id since episode has no Primary image tag
        mock_coordinator.client.get_image_url.assert_called_once_with(
            "series-456",
            image_type="Primary",
            tag=None,
        )

    def test_media_image_url_audio_fallback_to_album(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_image_url falls back to album for audio without images."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        session = MagicMock()
        session.now_playing = MagicMock()
        session.now_playing.item_id = "track-123"
        session.now_playing.image_tags = ()  # No track image
        session.now_playing.series_id = None
        session.now_playing.album_id = "album-456"

        mock_coordinator.get_session.return_value = session
        mock_coordinator.client = MagicMock()
        mock_coordinator.client.get_image_url.return_value = (
            "http://emby:8096/Items/album-456/Images/Primary?api_key=key"
        )

        player = EmbyMediaPlayer(mock_coordinator, "device-abc")

        url = player.media_image_url
        assert url is not None
        # Should use album_id since track has no Primary image tag
        mock_coordinator.client.get_image_url.assert_called_once_with(
            "album-456",
            image_type="Primary",
            tag=None,
        )


class TestMediaPropertiesNoSession:
    """Test media properties when session is None (coverage for return None paths)."""

    def test_media_series_title_no_session(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_series_title returns None when session is None."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator.get_session.return_value = None

        player = EmbyMediaPlayer(mock_coordinator, "device-xyz")

        assert player.media_series_title is None

    def test_media_season_no_session(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_season returns None when session is None."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator.get_session.return_value = None

        player = EmbyMediaPlayer(mock_coordinator, "device-xyz")

        assert player.media_season is None

    def test_media_episode_no_session(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_episode returns None when session is None."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator.get_session.return_value = None

        player = EmbyMediaPlayer(mock_coordinator, "device-xyz")

        assert player.media_episode is None

    def test_media_artist_no_session(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_artist returns None when session is None."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator.get_session.return_value = None

        player = EmbyMediaPlayer(mock_coordinator, "device-xyz")

        assert player.media_artist is None

    def test_media_album_name_no_session(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_album_name returns None when session is None."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator.get_session.return_value = None

        player = EmbyMediaPlayer(mock_coordinator, "device-xyz")

        assert player.media_album_name is None

    def test_media_album_artist_no_session(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test media_album_artist returns None when session is None."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator.get_session.return_value = None

        player = EmbyMediaPlayer(mock_coordinator, "device-xyz")

        assert player.media_album_artist is None
