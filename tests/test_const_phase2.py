"""Tests for Phase 2 TypedDicts in const.py."""

from __future__ import annotations


class TestEmbyNowPlayingItemTypedDict:
    """Test EmbyNowPlayingItem TypedDict definition."""

    def test_typeddict_exists(self) -> None:
        """Test EmbyNowPlayingItem TypedDict is defined."""
        from custom_components.embymedia.const import EmbyNowPlayingItem

        assert EmbyNowPlayingItem is not None

    def test_required_fields(self) -> None:
        """Test required fields are defined."""
        from custom_components.embymedia.const import EmbyNowPlayingItem

        # Create instance with required fields only
        item: EmbyNowPlayingItem = {
            "Id": "item-123",
            "Name": "Test Movie",
            "Type": "Movie",
        }
        assert item["Id"] == "item-123"
        assert item["Name"] == "Test Movie"
        assert item["Type"] == "Movie"

    def test_optional_fields(self) -> None:
        """Test optional fields can be included."""
        from custom_components.embymedia.const import EmbyNowPlayingItem

        item: EmbyNowPlayingItem = {
            "Id": "item-123",
            "Name": "Test Episode",
            "Type": "Episode",
            "RunTimeTicks": 36000000000,
            "SeriesName": "Test Series",
            "SeasonName": "Season 1",
            "IndexNumber": 5,
            "ParentIndexNumber": 1,
            "ProductionYear": 2024,
            "Album": "Test Album",
            "AlbumArtist": "Test Artist",
            "Artists": ["Artist 1", "Artist 2"],
            "ImageTags": {"Primary": "abc123"},
            "MediaType": "Video",
        }
        assert item["RunTimeTicks"] == 36000000000
        assert item["SeriesName"] == "Test Series"
        assert item["Artists"] == ["Artist 1", "Artist 2"]


class TestEmbyPlayStateTypedDict:
    """Test EmbyPlayState TypedDict definition."""

    def test_typeddict_exists(self) -> None:
        """Test EmbyPlayState TypedDict is defined."""
        from custom_components.embymedia.const import EmbyPlayState

        assert EmbyPlayState is not None

    def test_all_fields_optional(self) -> None:
        """Test all fields are optional (can create empty dict)."""
        from custom_components.embymedia.const import EmbyPlayState

        # Empty PlayState is valid (all fields NotRequired)
        state: EmbyPlayState = {}
        assert state == {}

    def test_full_play_state(self) -> None:
        """Test full PlayState with all fields."""
        from custom_components.embymedia.const import EmbyPlayState

        state: EmbyPlayState = {
            "PositionTicks": 5000000000,
            "CanSeek": True,
            "IsPaused": False,
            "IsMuted": False,
            "VolumeLevel": 80,
            "AudioStreamIndex": 1,
            "SubtitleStreamIndex": 0,
            "MediaSourceId": "source-123",
            "PlayMethod": "DirectPlay",
            "RepeatMode": "RepeatNone",
        }
        assert state["PositionTicks"] == 5000000000
        assert state["VolumeLevel"] == 80
        assert state["PlayMethod"] == "DirectPlay"


class TestEmbySessionResponseTypedDict:
    """Test EmbySessionResponse TypedDict definition."""

    def test_typeddict_exists(self) -> None:
        """Test EmbySessionResponse TypedDict is defined."""
        from custom_components.embymedia.const import EmbySessionResponse

        assert EmbySessionResponse is not None

    def test_required_fields(self) -> None:
        """Test required fields are defined."""
        from custom_components.embymedia.const import EmbySessionResponse

        session: EmbySessionResponse = {
            "Id": "session-123",
            "Client": "Emby Theater",
            "DeviceId": "device-abc",
            "DeviceName": "Living Room TV",
            "SupportsRemoteControl": True,
        }
        assert session["Id"] == "session-123"
        assert session["Client"] == "Emby Theater"
        assert session["DeviceId"] == "device-abc"
        assert session["DeviceName"] == "Living Room TV"
        assert session["SupportsRemoteControl"] is True

    def test_optional_fields(self) -> None:
        """Test optional fields can be included."""
        from custom_components.embymedia.const import (
            EmbyNowPlayingItem,
            EmbyPlayState,
            EmbySessionResponse,
        )

        now_playing: EmbyNowPlayingItem = {
            "Id": "movie-123",
            "Name": "Test Movie",
            "Type": "Movie",
        }
        play_state: EmbyPlayState = {
            "IsPaused": False,
            "CanSeek": True,
        }

        session: EmbySessionResponse = {
            "Id": "session-123",
            "Client": "Emby Theater",
            "DeviceId": "device-abc",
            "DeviceName": "Living Room TV",
            "SupportsRemoteControl": True,
            "UserId": "user-123",
            "UserName": "TestUser",
            "ApplicationVersion": "4.8.0",
            "IsActive": True,
            "NowPlayingItem": now_playing,
            "PlayState": play_state,
            "LastActivityDate": "2024-01-15T10:30:00.000Z",
            "PlayableMediaTypes": ["Video", "Audio"],
            "SupportedCommands": ["PlayPause", "Stop", "Seek"],
        }
        assert session["UserId"] == "user-123"
        assert session["NowPlayingItem"]["Name"] == "Test Movie"
        assert session["PlayState"]["IsPaused"] is False


class TestConfScanIntervalConstant:
    """Test CONF_SCAN_INTERVAL constant."""

    def test_constant_exists(self) -> None:
        """Test CONF_SCAN_INTERVAL is defined."""
        from custom_components.embymedia.const import CONF_SCAN_INTERVAL

        assert CONF_SCAN_INTERVAL == "scan_interval"
