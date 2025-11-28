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

    def test_coordinator_has_daily_watch_time_attribute(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test coordinator has _daily_watch_time counter."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        assert hasattr(coordinator, "_daily_watch_time")
        assert coordinator._daily_watch_time == 0

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
            "PositionTicks": 300 * EMBY_TICKS_PER_SECOND,  # 5 minutes
            "ItemId": "item-456",
            "ItemName": "Test Movie",
        }

        coordinator._track_playback_progress(data)

        assert "session-123" in coordinator._playback_sessions
        session = coordinator._playback_sessions["session-123"]
        assert session["position_ticks"] == 300 * EMBY_TICKS_PER_SECOND
        assert session["item_id"] == "item-456"
        assert session["item_name"] == "Test Movie"

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
            "PositionTicks": 0,
            "ItemId": "item-456",
        }
        coordinator._track_playback_progress(data1)
        assert coordinator._daily_watch_time == 0

        # Second update - 30 seconds later
        data2 = {
            "PlaySessionId": "session-123",
            "PositionTicks": 30 * EMBY_TICKS_PER_SECOND,
            "ItemId": "item-456",
        }
        coordinator._track_playback_progress(data2)

        # Should have added 30 seconds
        assert coordinator._daily_watch_time == 30

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
                "PositionTicks": 300 * EMBY_TICKS_PER_SECOND,
            }
        )

        # Seek backward to 1 minute
        coordinator._track_playback_progress(
            {
                "PlaySessionId": "session-123",
                "PositionTicks": 60 * EMBY_TICKS_PER_SECOND,
            }
        )

        # Watch time should still be 0 (no forward progress counted)
        assert coordinator._daily_watch_time == 0

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
                "PositionTicks": 0,
            }
        )

        # Jump forward 5 minutes (likely a seek, not real playback)
        coordinator._track_playback_progress(
            {
                "PlaySessionId": "session-123",
                "PositionTicks": 300 * EMBY_TICKS_PER_SECOND,
            }
        )

        # Should not count large jumps (>60s between updates is suspicious)
        assert coordinator._daily_watch_time == 0

    def test_track_playback_progress_handles_missing_session_id(
        self,
        mock_hass: MagicMock,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test graceful handling of missing PlaySessionId."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # No PlaySessionId
        coordinator._track_playback_progress(
            {
                "PositionTicks": 100 * EMBY_TICKS_PER_SECOND,
            }
        )

        # Should not crash, and no sessions tracked
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

        # Simulate some watch time
        coordinator._daily_watch_time = 3600  # 1 hour
        coordinator._last_reset_date = date.today() - timedelta(days=1)  # Yesterday

        # Process a playback event (should trigger reset)
        coordinator._track_playback_progress(
            {
                "PlaySessionId": "session-123",
                "PositionTicks": 0,
            }
        )

        # Watch time should be reset to 0
        assert coordinator._daily_watch_time == 0
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
        coordinator._daily_watch_time = 1800  # 30 minutes
        coordinator._last_reset_date = date.today()

        # Process a playback event
        coordinator._track_playback_progress(
            {
                "PlaySessionId": "session-123",
                "PositionTicks": 0,
            }
        )

        # Watch time should NOT be reset
        assert coordinator._daily_watch_time == 1800


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
        """Test daily_watch_time property is accessible."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        coordinator._daily_watch_time = 3600

        assert hasattr(coordinator, "daily_watch_time")
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

        coordinator._playback_sessions = {"session-1": {"position_ticks": 100}}

        assert hasattr(coordinator, "playback_sessions")
        assert coordinator.playback_sessions == {"session-1": {"position_ticks": 100}}
