"""Tests for Emby integration data models."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest


class TestMediaTypeEnum:
    """Test MediaType enumeration."""

    def test_enum_exists(self) -> None:
        """Test MediaType enum is defined."""
        from custom_components.embymedia.models import MediaType

        assert MediaType is not None

    def test_enum_values(self) -> None:
        """Test MediaType has expected values."""
        from custom_components.embymedia.models import MediaType

        assert MediaType.MOVIE == "Movie"
        assert MediaType.EPISODE == "Episode"
        assert MediaType.AUDIO == "Audio"
        assert MediaType.MUSIC_VIDEO == "MusicVideo"
        assert MediaType.TRAILER == "Trailer"
        assert MediaType.PHOTO == "Photo"
        assert MediaType.LIVE_TV == "TvChannel"
        assert MediaType.UNKNOWN == "Unknown"

    def test_enum_from_string(self) -> None:
        """Test MediaType can be created from string."""
        from custom_components.embymedia.models import MediaType

        assert MediaType("Movie") == MediaType.MOVIE
        assert MediaType("Episode") == MediaType.EPISODE


class TestEmbyMediaItem:
    """Test EmbyMediaItem dataclass."""

    def test_creation_minimal(self) -> None:
        """Test creating EmbyMediaItem with minimal fields."""
        from custom_components.embymedia.models import EmbyMediaItem, MediaType

        item = EmbyMediaItem(
            item_id="item-123",
            name="Test Movie",
            media_type=MediaType.MOVIE,
        )
        assert item.item_id == "item-123"
        assert item.name == "Test Movie"
        assert item.media_type == MediaType.MOVIE
        assert item.duration_seconds is None
        assert item.series_name is None
        assert item.artists == ()
        assert item.image_tags == ()

    def test_creation_full(self) -> None:
        """Test creating EmbyMediaItem with all fields."""
        from custom_components.embymedia.models import EmbyMediaItem, MediaType

        item = EmbyMediaItem(
            item_id="item-123",
            name="Test Episode",
            media_type=MediaType.EPISODE,
            duration_seconds=3600.5,
            series_name="Test Series",
            season_name="Season 1",
            episode_number=5,
            season_number=1,
            album="Test Album",
            album_artist="Test Artist",
            artists=("Artist 1", "Artist 2"),
            year=2024,
            overview="Test overview",
            image_tags=(("Primary", "abc123"),),
        )
        assert item.duration_seconds == 3600.5
        assert item.series_name == "Test Series"
        assert item.episode_number == 5
        assert item.artists == ("Artist 1", "Artist 2")
        assert item.image_tags == (("Primary", "abc123"),)

    def test_frozen(self) -> None:
        """Test EmbyMediaItem is immutable."""
        from custom_components.embymedia.models import EmbyMediaItem, MediaType

        item = EmbyMediaItem(
            item_id="item-123",
            name="Test Movie",
            media_type=MediaType.MOVIE,
        )
        with pytest.raises(AttributeError):
            item.name = "New Name"  # type: ignore[misc]


class TestEmbyPlaybackState:
    """Test EmbyPlaybackState dataclass."""

    def test_creation_default(self) -> None:
        """Test creating EmbyPlaybackState with defaults."""
        from custom_components.embymedia.models import EmbyPlaybackState

        state = EmbyPlaybackState()
        assert state.position_seconds == 0.0
        assert state.can_seek is False
        assert state.is_paused is False
        assert state.is_muted is False
        assert state.volume_level is None
        assert state.play_method is None

    def test_creation_full(self) -> None:
        """Test creating EmbyPlaybackState with all fields."""
        from custom_components.embymedia.models import EmbyPlaybackState

        state = EmbyPlaybackState(
            position_seconds=1234.5,
            can_seek=True,
            is_paused=True,
            is_muted=False,
            volume_level=0.8,
            play_method="DirectPlay",
        )
        assert state.position_seconds == 1234.5
        assert state.can_seek is True
        assert state.is_paused is True
        assert state.volume_level == 0.8
        assert state.play_method == "DirectPlay"

    def test_frozen(self) -> None:
        """Test EmbyPlaybackState is immutable."""
        from custom_components.embymedia.models import EmbyPlaybackState

        state = EmbyPlaybackState()
        with pytest.raises(AttributeError):
            state.is_paused = True  # type: ignore[misc]


class TestEmbySession:
    """Test EmbySession dataclass."""

    def test_creation_minimal(self) -> None:
        """Test creating EmbySession with minimal fields."""
        from custom_components.embymedia.models import EmbySession

        session = EmbySession(
            session_id="session-123",
            device_id="device-abc",
            device_name="Living Room TV",
            client_name="Emby Theater",
        )
        assert session.session_id == "session-123"
        assert session.device_id == "device-abc"
        assert session.device_name == "Living Room TV"
        assert session.client_name == "Emby Theater"
        assert session.user_id is None
        assert session.supports_remote_control is False
        assert session.now_playing is None
        assert session.play_state is None

    def test_creation_full(self) -> None:
        """Test creating EmbySession with all fields."""
        from custom_components.embymedia.models import (
            EmbyMediaItem,
            EmbyPlaybackState,
            EmbySession,
            MediaType,
        )

        now_playing = EmbyMediaItem(
            item_id="movie-123",
            name="Test Movie",
            media_type=MediaType.MOVIE,
        )
        play_state = EmbyPlaybackState(is_paused=False, can_seek=True)
        last_activity = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        session = EmbySession(
            session_id="session-123",
            device_id="device-abc",
            device_name="Living Room TV",
            client_name="Emby Theater",
            user_id="user-123",
            user_name="TestUser",
            supports_remote_control=True,
            now_playing=now_playing,
            play_state=play_state,
            last_activity=last_activity,
            app_version="4.8.0",
            playable_media_types=("Video", "Audio"),
            supported_commands=("PlayPause", "Stop"),
        )
        assert session.user_id == "user-123"
        assert session.supports_remote_control is True
        assert session.now_playing is not None
        assert session.now_playing.name == "Test Movie"
        assert session.app_version == "4.8.0"

    def test_is_playing_true(self) -> None:
        """Test is_playing returns True when media is playing."""
        from custom_components.embymedia.models import (
            EmbyMediaItem,
            EmbySession,
            MediaType,
        )

        now_playing = EmbyMediaItem(
            item_id="movie-123",
            name="Test Movie",
            media_type=MediaType.MOVIE,
        )
        session = EmbySession(
            session_id="session-123",
            device_id="device-abc",
            device_name="TV",
            client_name="Emby",
            now_playing=now_playing,
        )
        assert session.is_playing is True

    def test_is_playing_false(self) -> None:
        """Test is_playing returns False when nothing playing."""
        from custom_components.embymedia.models import EmbySession

        session = EmbySession(
            session_id="session-123",
            device_id="device-abc",
            device_name="TV",
            client_name="Emby",
        )
        assert session.is_playing is False

    def test_unique_id_returns_device_id(self) -> None:
        """Test unique_id returns device_id for entity stability."""
        from custom_components.embymedia.models import EmbySession

        session = EmbySession(
            session_id="session-123",
            device_id="device-abc",
            device_name="TV",
            client_name="Emby",
        )
        assert session.unique_id == "device-abc"

    def test_is_active_with_recent_activity(self) -> None:
        """Test is_active returns True for recent activity."""
        from custom_components.embymedia.models import EmbySession

        # Activity 1 minute ago
        recent = datetime.now(UTC)
        session = EmbySession(
            session_id="session-123",
            device_id="device-abc",
            device_name="TV",
            client_name="Emby",
            last_activity=recent,
        )
        assert session.is_active is True

    def test_is_active_with_old_activity(self) -> None:
        """Test is_active returns False for old activity."""
        from datetime import timedelta

        from custom_components.embymedia.models import EmbySession

        # Activity 10 minutes ago (beyond 5 minute threshold)
        old = datetime.now(UTC) - timedelta(minutes=10)
        session = EmbySession(
            session_id="session-123",
            device_id="device-abc",
            device_name="TV",
            client_name="Emby",
            last_activity=old,
        )
        assert session.is_active is False

    def test_is_active_with_no_activity(self) -> None:
        """Test is_active returns False when no activity recorded."""
        from custom_components.embymedia.models import EmbySession

        session = EmbySession(
            session_id="session-123",
            device_id="device-abc",
            device_name="TV",
            client_name="Emby",
            last_activity=None,
        )
        assert session.is_active is False


class TestParseMediaItem:
    """Test parse_media_item function."""

    def test_parse_minimal(self) -> None:
        """Test parsing minimal NowPlayingItem data."""
        from custom_components.embymedia.const import EmbyNowPlayingItem
        from custom_components.embymedia.models import MediaType, parse_media_item

        data: EmbyNowPlayingItem = {
            "Id": "item-123",
            "Name": "Test Movie",
            "Type": "Movie",
        }
        item = parse_media_item(data)
        assert item.item_id == "item-123"
        assert item.name == "Test Movie"
        assert item.media_type == MediaType.MOVIE
        assert item.duration_seconds is None

    def test_parse_with_duration(self) -> None:
        """Test parsing item with duration in ticks."""
        from custom_components.embymedia.const import EmbyNowPlayingItem
        from custom_components.embymedia.models import parse_media_item

        data: EmbyNowPlayingItem = {
            "Id": "item-123",
            "Name": "Test Movie",
            "Type": "Movie",
            "RunTimeTicks": 36000000000,  # 1 hour in ticks
        }
        item = parse_media_item(data)
        assert item.duration_seconds == 3600.0

    def test_parse_episode(self) -> None:
        """Test parsing episode data."""
        from custom_components.embymedia.const import EmbyNowPlayingItem
        from custom_components.embymedia.models import MediaType, parse_media_item

        data: EmbyNowPlayingItem = {
            "Id": "episode-123",
            "Name": "Pilot",
            "Type": "Episode",
            "SeriesName": "Test Series",
            "SeasonName": "Season 1",
            "IndexNumber": 1,
            "ParentIndexNumber": 1,
            "ProductionYear": 2024,
        }
        item = parse_media_item(data)
        assert item.media_type == MediaType.EPISODE
        assert item.series_name == "Test Series"
        assert item.season_name == "Season 1"
        assert item.episode_number == 1
        assert item.season_number == 1
        assert item.year == 2024

    def test_parse_audio(self) -> None:
        """Test parsing audio track data."""
        from custom_components.embymedia.const import EmbyNowPlayingItem
        from custom_components.embymedia.models import MediaType, parse_media_item

        data: EmbyNowPlayingItem = {
            "Id": "track-123",
            "Name": "Test Song",
            "Type": "Audio",
            "Album": "Test Album",
            "AlbumArtist": "Test Artist",
            "Artists": ["Artist 1", "Artist 2"],
        }
        item = parse_media_item(data)
        assert item.media_type == MediaType.AUDIO
        assert item.album == "Test Album"
        assert item.album_artist == "Test Artist"
        assert item.artists == ("Artist 1", "Artist 2")

    def test_parse_unknown_type(self) -> None:
        """Test parsing unknown media type falls back to UNKNOWN."""
        from custom_components.embymedia.const import EmbyNowPlayingItem
        from custom_components.embymedia.models import MediaType, parse_media_item

        data: EmbyNowPlayingItem = {
            "Id": "item-123",
            "Name": "Test Item",
            "Type": "SomeNewType",
        }
        item = parse_media_item(data)
        assert item.media_type == MediaType.UNKNOWN

    def test_parse_with_image_tags(self) -> None:
        """Test parsing item with image tags."""
        from custom_components.embymedia.const import EmbyNowPlayingItem
        from custom_components.embymedia.models import parse_media_item

        data: EmbyNowPlayingItem = {
            "Id": "item-123",
            "Name": "Test Movie",
            "Type": "Movie",
            "ImageTags": {"Primary": "abc123", "Backdrop": "def456"},
        }
        item = parse_media_item(data)
        assert ("Primary", "abc123") in item.image_tags
        assert ("Backdrop", "def456") in item.image_tags


class TestParsePlayState:
    """Test parse_play_state function."""

    def test_parse_empty(self) -> None:
        """Test parsing empty PlayState."""
        from custom_components.embymedia.const import EmbyPlayState
        from custom_components.embymedia.models import parse_play_state

        data: EmbyPlayState = {}
        state = parse_play_state(data)
        assert state.position_seconds == 0.0
        assert state.can_seek is False
        assert state.is_paused is False
        assert state.volume_level is None

    def test_parse_full(self) -> None:
        """Test parsing full PlayState."""
        from custom_components.embymedia.const import EmbyPlayState
        from custom_components.embymedia.models import parse_play_state

        data: EmbyPlayState = {
            "PositionTicks": 50000000000,  # 5000 seconds
            "CanSeek": True,
            "IsPaused": True,
            "IsMuted": False,
            "VolumeLevel": 80,
            "PlayMethod": "Transcode",
        }
        state = parse_play_state(data)
        assert state.position_seconds == 5000.0
        assert state.can_seek is True
        assert state.is_paused is True
        assert state.is_muted is False
        assert state.volume_level == 0.8  # Converted from 0-100 to 0.0-1.0
        assert state.play_method == "Transcode"


class TestParseSession:
    """Test parse_session function."""

    def test_parse_minimal(self) -> None:
        """Test parsing minimal session data."""
        from custom_components.embymedia.const import EmbySessionResponse
        from custom_components.embymedia.models import parse_session

        data: EmbySessionResponse = {
            "Id": "session-123",
            "Client": "Emby Theater",
            "DeviceId": "device-abc",
            "DeviceName": "Living Room TV",
            "SupportsRemoteControl": True,
        }
        session = parse_session(data)
        assert session.session_id == "session-123"
        assert session.client_name == "Emby Theater"
        assert session.device_id == "device-abc"
        assert session.device_name == "Living Room TV"
        assert session.supports_remote_control is True
        assert session.now_playing is None
        assert session.play_state is None

    def test_parse_with_now_playing(self) -> None:
        """Test parsing session with now playing item."""
        from custom_components.embymedia.const import EmbySessionResponse
        from custom_components.embymedia.models import parse_session

        data: EmbySessionResponse = {
            "Id": "session-123",
            "Client": "Emby Theater",
            "DeviceId": "device-abc",
            "DeviceName": "Living Room TV",
            "SupportsRemoteControl": True,
            "NowPlayingItem": {
                "Id": "movie-123",
                "Name": "Test Movie",
                "Type": "Movie",
            },
            "PlayState": {
                "IsPaused": False,
                "CanSeek": True,
                "PositionTicks": 10000000000,
            },
        }
        session = parse_session(data)
        assert session.now_playing is not None
        assert session.now_playing.name == "Test Movie"
        assert session.play_state is not None
        assert session.play_state.is_paused is False
        assert session.play_state.position_seconds == 1000.0

    def test_parse_with_last_activity(self) -> None:
        """Test parsing session with last activity date."""
        from custom_components.embymedia.const import EmbySessionResponse
        from custom_components.embymedia.models import parse_session

        data: EmbySessionResponse = {
            "Id": "session-123",
            "Client": "Emby Theater",
            "DeviceId": "device-abc",
            "DeviceName": "Living Room TV",
            "SupportsRemoteControl": True,
            "LastActivityDate": "2024-01-15T10:30:00.000Z",
        }
        session = parse_session(data)
        assert session.last_activity is not None
        assert session.last_activity.year == 2024
        assert session.last_activity.month == 1
        assert session.last_activity.day == 15

    def test_parse_full(self) -> None:
        """Test parsing full session data."""
        from custom_components.embymedia.const import EmbySessionResponse
        from custom_components.embymedia.models import parse_session

        data: EmbySessionResponse = {
            "Id": "session-123",
            "Client": "Emby Theater",
            "DeviceId": "device-abc",
            "DeviceName": "Living Room TV",
            "SupportsRemoteControl": True,
            "UserId": "user-123",
            "UserName": "TestUser",
            "ApplicationVersion": "4.8.0",
            "PlayableMediaTypes": ["Video", "Audio"],
            "SupportedCommands": ["PlayPause", "Stop", "Seek"],
        }
        session = parse_session(data)
        assert session.user_id == "user-123"
        assert session.user_name == "TestUser"
        assert session.app_version == "4.8.0"
        assert session.playable_media_types == ("Video", "Audio")
        assert session.supported_commands == ("PlayPause", "Stop", "Seek")
