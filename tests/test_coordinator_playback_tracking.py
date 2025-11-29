"""Tests for playback progress tracking in coordinator.

Phase 18: User Activity & Statistics - Task 18.8
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

if TYPE_CHECKING:
    pass


# Emby uses ticks (100 nanoseconds) for time
EMBY_TICKS_PER_SECOND = 10_000_000


@pytest.fixture
def mock_hass() -> MagicMock:
    """Create a mock HomeAssistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.async_create_task = MagicMock(return_value=MagicMock())
    return hass


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock EmbyClient for testing."""
    client = MagicMock()
    client.async_get_sessions = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_config_entry() -> MagicMock:
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {}
    entry.options = {}
    return entry


class TestPlaybackTrackingInitialization:
    """Tests for playback tracking attributes initialization."""

    def test_coordinator_has_playback_sessions_attribute(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test coordinator has _playback_sessions dict."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        assert hasattr(coordinator, "_playback_sessions")
        assert isinstance(coordinator._playback_sessions, dict)
        assert len(coordinator._playback_sessions) == 0

    def test_coordinator_has_user_watch_times_attribute(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test coordinator has _user_watch_times for per-user tracking."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        assert hasattr(coordinator, "_user_watch_times")
        assert isinstance(coordinator._user_watch_times, dict)
        assert len(coordinator._user_watch_times) == 0
        # daily_watch_time property returns sum of user watch times
        assert coordinator.daily_watch_time == 0

    def test_coordinator_has_last_reset_date_attribute(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test coordinator has _last_reset_date for daily reset."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        assert hasattr(coordinator, "_last_reset_date")
        # Should be today's date
        assert coordinator._last_reset_date == date.today()


class TestPlaybackProgressTracking:
    """Tests for _track_playback_progress method."""

    def test_track_playback_progress_method_exists(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test _track_playback_progress method exists."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        assert hasattr(coordinator, "_track_playback_progress")
        assert callable(coordinator._track_playback_progress)

    def test_track_playback_progress_updates_session(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test _track_playback_progress creates/updates session tracking."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        data = {
            "PlaySessionId": "session-123",
            "UserId": "user-abc",
            "UserName": "TestUser",
            "PositionTicks": 300 * EMBY_TICKS_PER_SECOND,  # 5 minutes
            "ItemId": "item-456",
            "ItemName": "Test Movie",
        }

        coordinator._track_playback_progress(data)

        # Key is now "user_id:session_id"
        assert "user-abc:session-123" in coordinator._playback_sessions
        session = coordinator._playback_sessions["user-abc:session-123"]
        assert session["position_ticks"] == 300 * EMBY_TICKS_PER_SECOND
        assert session["item_id"] == "item-456"
        assert session["item_name"] == "Test Movie"
        assert session["user_id"] == "user-abc"

    def test_track_playback_progress_calculates_watch_time(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test watch time is calculated from position delta."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # First update - establishes baseline
        data1 = {
            "PlaySessionId": "session-123",
            "UserId": "user-abc",
            "PositionTicks": 0,
            "ItemId": "item-456",
        }
        coordinator._track_playback_progress(data1)
        assert coordinator.daily_watch_time == 0

        # Second update - 30 seconds later
        data2 = {
            "PlaySessionId": "session-123",
            "UserId": "user-abc",
            "PositionTicks": 30 * EMBY_TICKS_PER_SECOND,
            "ItemId": "item-456",
        }
        coordinator._track_playback_progress(data2)

        # Should have added 30 seconds to user's watch time
        assert coordinator.daily_watch_time == 30
        assert coordinator.get_user_watch_time("user-abc") == 30

    def test_track_playback_progress_ignores_backward_seeks(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test backward seeks don't count as watch time."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # First update at 5 minutes
        coordinator._track_playback_progress(
            {
                "PlaySessionId": "session-123",
                "UserId": "user-abc",
                "PositionTicks": 300 * EMBY_TICKS_PER_SECOND,
            }
        )

        # Seek backward to 1 minute
        coordinator._track_playback_progress(
            {
                "PlaySessionId": "session-123",
                "UserId": "user-abc",
                "PositionTicks": 60 * EMBY_TICKS_PER_SECOND,
            }
        )

        # Watch time should still be 0 (no forward progress counted)
        assert coordinator.daily_watch_time == 0

    def test_track_playback_progress_ignores_large_jumps(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test large forward jumps (seeks) don't count as watch time."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # First update at 0
        coordinator._track_playback_progress(
            {
                "PlaySessionId": "session-123",
                "UserId": "user-abc",
                "PositionTicks": 0,
            }
        )

        # Jump forward 5 minutes (likely a seek, not real playback)
        coordinator._track_playback_progress(
            {
                "PlaySessionId": "session-123",
                "UserId": "user-abc",
                "PositionTicks": 300 * EMBY_TICKS_PER_SECOND,
            }
        )

        # Should not count large jumps (>60s between updates is suspicious)
        assert coordinator.daily_watch_time == 0

    def test_track_playback_progress_handles_missing_user_id(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test graceful handling of missing UserId."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # No UserId - should not track
        coordinator._track_playback_progress(
            {
                "PlaySessionId": "session-123",
                "PositionTicks": 100 * EMBY_TICKS_PER_SECOND,
            }
        )

        # Should not crash, and no sessions tracked (UserId required)
        assert len(coordinator._playback_sessions) == 0


class TestDailyWatchTimeReset:
    """Tests for daily watch time reset at midnight."""

    def test_daily_reset_on_new_day(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test watch time resets when date changes."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Simulate some watch time for a user
        coordinator._user_watch_times["user-abc"] = 3600  # 1 hour
        coordinator._last_reset_date = date.today() - timedelta(days=1)  # Yesterday

        # Process a playback event (should trigger reset)
        coordinator._track_playback_progress(
            {
                "PlaySessionId": "session-123",
                "UserId": "user-abc",
                "PositionTicks": 0,
            }
        )

        # Watch time should be reset to 0
        assert coordinator.daily_watch_time == 0
        assert coordinator._last_reset_date == date.today()

    def test_no_reset_on_same_day(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test watch time is not reset on same day."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Set some watch time for today
        coordinator._user_watch_times["user-abc"] = 1800  # 30 minutes
        coordinator._last_reset_date = date.today()

        # Process a playback event
        coordinator._track_playback_progress(
            {
                "PlaySessionId": "session-123",
                "UserId": "user-abc",
                "PositionTicks": 0,
            }
        )

        # Watch time should NOT be reset
        assert coordinator.daily_watch_time == 1800


class TestWebSocketIntegration:
    """Tests for WebSocket message handling of PlaybackProgress."""

    def test_playback_progress_message_triggers_tracking(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test PlaybackProgress WebSocket message triggers tracking."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Mock the tracking method
        with patch.object(coordinator, "_track_playback_progress") as mock_track:
            data = {
                "PlaySessionId": "session-123",
                "PositionTicks": 100 * EMBY_TICKS_PER_SECOND,
            }

            coordinator._handle_websocket_message("PlaybackProgress", data)

            mock_track.assert_called_once_with(data)


class TestPublicAccessors:
    """Tests for public accessor properties for sensor usage."""

    def test_daily_watch_time_property(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test daily_watch_time property returns sum of all user watch times."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Set per-user watch times
        coordinator._user_watch_times["user-abc"] = 1800  # 30 min
        coordinator._user_watch_times["user-xyz"] = 1800  # 30 min

        assert hasattr(coordinator, "daily_watch_time")
        # Total should be sum of all users
        assert coordinator.daily_watch_time == 3600

    def test_playback_sessions_property(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test playback_sessions property is accessible."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Key format is now "user_id:session_id"
        coordinator._playback_sessions = {"user-abc:session-1": {"position_ticks": 100}}

        assert hasattr(coordinator, "playback_sessions")
        assert coordinator.playback_sessions == {"user-abc:session-1": {"position_ticks": 100}}

    def test_user_watch_times_property(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test user_watch_times property returns per-user watch times."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        coordinator._user_watch_times["user-abc"] = 1800
        coordinator._user_watch_times["user-xyz"] = 3600

        assert hasattr(coordinator, "user_watch_times")
        assert coordinator.user_watch_times == {"user-abc": 1800, "user-xyz": 3600}

    def test_get_user_watch_time_method(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test get_user_watch_time returns time for specific user."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        coordinator._user_watch_times["user-abc"] = 1800
        coordinator._user_watch_times["user-xyz"] = 3600

        assert coordinator.get_user_watch_time("user-abc") == 1800
        assert coordinator.get_user_watch_time("user-xyz") == 3600
        # Unknown user returns 0
        assert coordinator.get_user_watch_time("unknown-user") == 0


class TestPlaybackTrackingEdgeCases:
    """Tests for edge cases in playback tracking."""

    def test_track_playback_handles_missing_session_id(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test graceful handling of missing session ID."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # No session IDs (PlaySessionId, DeviceId, Id) - should return early
        coordinator._track_playback_progress(
            {
                "UserId": "user-abc",
                "PositionTicks": 100 * EMBY_TICKS_PER_SECOND,
            }
        )

        # Should not crash, and no sessions tracked
        assert len(coordinator._playback_sessions) == 0

    def test_track_playback_gets_position_from_play_state(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test getting PositionTicks from nested PlayState."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # PositionTicks in nested PlayState
        data = {
            "PlaySessionId": "session-123",
            "UserId": "user-abc",
            "PlayState": {
                "PositionTicks": 30 * EMBY_TICKS_PER_SECOND,
            },
            "ItemId": "item-456",
        }
        coordinator._track_playback_progress(data)

        # Should track the session with position from PlayState
        assert "user-abc:session-123" in coordinator._playback_sessions
        assert (
            coordinator._playback_sessions["user-abc:session-123"]["position_ticks"]
            == 30 * EMBY_TICKS_PER_SECOND
        )

    def test_track_playback_handles_invalid_position_ticks(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test handling of non-integer PositionTicks."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # PositionTicks as string (invalid)
        data = {
            "PlaySessionId": "session-123",
            "UserId": "user-abc",
            "PositionTicks": "invalid",
            "ItemId": "item-456",
        }
        coordinator._track_playback_progress(data)

        # Should default to 0
        assert "user-abc:session-123" in coordinator._playback_sessions
        assert coordinator._playback_sessions["user-abc:session-123"]["position_ticks"] == 0

    def test_track_playback_handles_invalid_now_playing(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test handling of non-dict NowPlayingItem."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # NowPlayingItem as string (invalid)
        data = {
            "PlaySessionId": "session-123",
            "UserId": "user-abc",
            "PositionTicks": 100 * EMBY_TICKS_PER_SECOND,
            "NowPlayingItem": "invalid",
        }
        coordinator._track_playback_progress(data)

        # Should still track the session
        assert "user-abc:session-123" in coordinator._playback_sessions

    def test_track_playback_paused_updates_position_only(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test paused state updates position but doesn't count watch time."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # First update - establish session
        data1 = {
            "PlaySessionId": "session-123",
            "UserId": "user-abc",
            "PositionTicks": 0,
            "ItemId": "item-456",
            "ItemName": "Test Movie",
            "UserName": "Test User",
        }
        coordinator._track_playback_progress(data1)

        # Second update - 30 seconds later but paused
        data2 = {
            "PlaySessionId": "session-123",
            "UserId": "user-abc",
            "PositionTicks": 30 * EMBY_TICKS_PER_SECOND,
            "ItemId": "item-456",
            "ItemName": "Test Movie",
            "UserName": "Test User",
            "PlayState": {
                "IsPaused": True,
            },
        }
        coordinator._track_playback_progress(data2)

        # Position should be updated
        assert (
            coordinator._playback_sessions["user-abc:session-123"]["position_ticks"]
            == 30 * EMBY_TICKS_PER_SECOND
        )
        # But watch time should NOT be counted (paused)
        assert coordinator.daily_watch_time == 0


class TestPlaybackSessionCleanup:
    """Tests for playback session memory cleanup (Phase 22)."""

    def test_playback_stopped_cleans_up_session(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test PlaybackStopped event removes session from tracking."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Add some tracked sessions
        coordinator._playback_sessions["user-abc:session-123"] = {
            "position_ticks": 100 * EMBY_TICKS_PER_SECOND,
            "item_id": "item-456",
            "user_id": "user-abc",
        }
        coordinator._playback_sessions["user-xyz:session-456"] = {
            "position_ticks": 200 * EMBY_TICKS_PER_SECOND,
            "item_id": "item-789",
            "user_id": "user-xyz",
        }

        # Handle PlaybackStopped event
        data = {
            "UserId": "user-abc",
            "PlaySessionId": "session-123",
        }
        coordinator._handle_websocket_message("PlaybackStopped", data)

        # Session should be removed
        assert "user-abc:session-123" not in coordinator._playback_sessions
        # Other session should remain
        assert "user-xyz:session-456" in coordinator._playback_sessions

    def test_session_ended_cleans_up_by_device_id(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test SessionEnded event removes all tracking for that device."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Add tracked sessions - some with device IDs in the key
        coordinator._playback_sessions["user-abc:device-123"] = {
            "position_ticks": 100 * EMBY_TICKS_PER_SECOND,
            "item_id": "item-456",
            "user_id": "user-abc",
        }
        coordinator._playback_sessions["user-xyz:device-456"] = {
            "position_ticks": 200 * EMBY_TICKS_PER_SECOND,
            "item_id": "item-789",
            "user_id": "user-xyz",
        }

        # Handle SessionEnded event
        data = {
            "DeviceId": "device-123",
        }
        coordinator._handle_websocket_message("SessionEnded", data)

        # Sessions containing device-123 should be removed
        assert "user-abc:device-123" not in coordinator._playback_sessions
        # Other session should remain
        assert "user-xyz:device-456" in coordinator._playback_sessions

    def test_cleanup_stale_sessions(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test stale sessions are cleaned up after timeout."""
        from datetime import datetime, timedelta

        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Add a stale session (2 hours old)
        stale_time = (datetime.now() - timedelta(hours=2)).isoformat()
        coordinator._playback_sessions["user-abc:session-stale"] = {
            "position_ticks": 100 * EMBY_TICKS_PER_SECOND,
            "item_id": "item-456",
            "user_id": "user-abc",
            "last_update": stale_time,
        }

        # Add a recent session
        recent_time = datetime.now().isoformat()
        coordinator._playback_sessions["user-xyz:session-recent"] = {
            "position_ticks": 200 * EMBY_TICKS_PER_SECOND,
            "item_id": "item-789",
            "user_id": "user-xyz",
            "last_update": recent_time,
        }

        # Clean up stale sessions (default: 1 hour max age)
        coordinator._cleanup_stale_sessions()

        # Stale session should be removed
        assert "user-abc:session-stale" not in coordinator._playback_sessions
        # Recent session should remain
        assert "user-xyz:session-recent" in coordinator._playback_sessions

    def test_cleanup_stale_sessions_custom_max_age(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test stale sessions cleanup with custom max age."""
        from datetime import datetime, timedelta

        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Add a session that's 10 minutes old
        old_time = (datetime.now() - timedelta(minutes=10)).isoformat()
        coordinator._playback_sessions["user-abc:session-123"] = {
            "position_ticks": 100 * EMBY_TICKS_PER_SECOND,
            "last_update": old_time,
        }

        # With 15 minute max age, session should NOT be removed
        coordinator._cleanup_stale_sessions(max_age_seconds=900)  # 15 min
        assert "user-abc:session-123" in coordinator._playback_sessions

        # With 5 minute max age, session SHOULD be removed
        coordinator._cleanup_stale_sessions(max_age_seconds=300)  # 5 min
        assert "user-abc:session-123" not in coordinator._playback_sessions

    def test_cleanup_stale_sessions_handles_missing_timestamp(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test cleanup handles sessions without last_update timestamp."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Add session without last_update (legacy or malformed)
        coordinator._playback_sessions["user-abc:session-no-timestamp"] = {
            "position_ticks": 100 * EMBY_TICKS_PER_SECOND,
            # No last_update field
        }

        # Cleanup should remove sessions without timestamps (treated as stale)
        coordinator._cleanup_stale_sessions()

        assert "user-abc:session-no-timestamp" not in coordinator._playback_sessions
