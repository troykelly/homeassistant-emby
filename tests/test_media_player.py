"""Tests for Emby media player platform."""
from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

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
