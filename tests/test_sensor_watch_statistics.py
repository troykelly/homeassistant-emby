"""Tests for EmbyWatchStatisticsSensor.

Phase 18: User Activity & Statistics - Task 18.9
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from homeassistant.components.sensor import SensorStateClass

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_session_coordinator() -> MagicMock:
    """Create a mock session coordinator with watch statistics data.

    Note: EmbyWatchStatisticsSensor uses session coordinator (EmbyDataUpdateCoordinator)
    since playback tracking happens via WebSocket messages.
    """
    coordinator = MagicMock()
    coordinator.server_id = "test-server-id"
    coordinator.server_name = "Test Server"
    coordinator.last_update_success = True
    coordinator.daily_watch_time = 3600  # 60 minutes in seconds
    coordinator.playback_sessions = {
        "session-1": {
            "item_id": "item-123",
            "item_name": "Test Movie",
            "position_ticks": 300 * 10_000_000,  # 5 minutes
        },
        "session-2": {
            "item_id": "item-456",
            "item_name": "Test Episode",
            "position_ticks": 600 * 10_000_000,  # 10 minutes
        },
    }
    # Session coordinator returns list of sessions, not server data dict
    coordinator.data = []
    return coordinator


class TestEmbyWatchStatisticsSensorExists:
    """Tests for EmbyWatchStatisticsSensor class existence."""

    def test_sensor_class_exists(self) -> None:
        """Test EmbyWatchStatisticsSensor class exists."""
        from custom_components.embymedia.sensor import EmbyWatchStatisticsSensor

        assert EmbyWatchStatisticsSensor is not None

    def test_sensor_inherits_from_base(
        self,
        mock_session_coordinator: MagicMock,
    ) -> None:
        """Test sensor inherits from EmbySessionSensorBase."""
        from custom_components.embymedia.sensor import (
            EmbySessionSensorBase,
            EmbyWatchStatisticsSensor,
        )

        sensor = EmbyWatchStatisticsSensor(mock_session_coordinator)
        assert isinstance(sensor, EmbySessionSensorBase)


class TestEmbyWatchStatisticsSensorIdentity:
    """Tests for sensor identity attributes."""

    def test_sensor_unique_id(
        self,
        mock_session_coordinator: MagicMock,
    ) -> None:
        """Test sensor has correct unique_id."""
        from custom_components.embymedia.sensor import EmbyWatchStatisticsSensor

        sensor = EmbyWatchStatisticsSensor(mock_session_coordinator)
        assert sensor.unique_id == "test-server-id_watch_statistics"

    def test_sensor_translation_key(
        self,
        mock_session_coordinator: MagicMock,
    ) -> None:
        """Test sensor has correct translation_key."""
        from custom_components.embymedia.sensor import EmbyWatchStatisticsSensor

        sensor = EmbyWatchStatisticsSensor(mock_session_coordinator)
        assert sensor.translation_key == "watch_statistics"


class TestEmbyWatchStatisticsSensorStateClass:
    """Tests for sensor state class configuration."""

    def test_sensor_state_class_is_total_increasing(
        self,
        mock_session_coordinator: MagicMock,
    ) -> None:
        """Test sensor has TOTAL_INCREASING state class for HA statistics."""
        from custom_components.embymedia.sensor import EmbyWatchStatisticsSensor

        sensor = EmbyWatchStatisticsSensor(mock_session_coordinator)
        assert sensor.state_class == SensorStateClass.TOTAL_INCREASING


class TestEmbyWatchStatisticsSensorNativeValue:
    """Tests for sensor native_value (daily watch time in minutes)."""

    def test_native_value_returns_minutes(
        self,
        mock_session_coordinator: MagicMock,
    ) -> None:
        """Test native_value returns daily watch time in minutes."""
        from custom_components.embymedia.sensor import EmbyWatchStatisticsSensor

        sensor = EmbyWatchStatisticsSensor(mock_session_coordinator)
        # 3600 seconds = 60 minutes
        assert sensor.native_value == 60

    def test_native_value_rounds_down(
        self,
        mock_session_coordinator: MagicMock,
    ) -> None:
        """Test native_value rounds down to whole minutes."""
        from custom_components.embymedia.sensor import EmbyWatchStatisticsSensor

        mock_session_coordinator.daily_watch_time = 3650  # 60.83 minutes
        sensor = EmbyWatchStatisticsSensor(mock_session_coordinator)
        assert sensor.native_value == 60  # Rounds down to 60

    def test_native_value_zero_when_no_watch_time(
        self,
        mock_session_coordinator: MagicMock,
    ) -> None:
        """Test native_value returns 0 when no watch time."""
        from custom_components.embymedia.sensor import EmbyWatchStatisticsSensor

        mock_session_coordinator.daily_watch_time = 0
        sensor = EmbyWatchStatisticsSensor(mock_session_coordinator)
        assert sensor.native_value == 0


class TestEmbyWatchStatisticsSensorUnit:
    """Tests for sensor unit of measurement."""

    def test_native_unit_of_measurement(
        self,
        mock_session_coordinator: MagicMock,
    ) -> None:
        """Test sensor has minutes as unit of measurement."""
        from custom_components.embymedia.sensor import EmbyWatchStatisticsSensor

        sensor = EmbyWatchStatisticsSensor(mock_session_coordinator)
        assert sensor.native_unit_of_measurement == "min"


class TestEmbyWatchStatisticsSensorAttributes:
    """Tests for sensor extra_state_attributes."""

    def test_has_extra_state_attributes(
        self,
        mock_session_coordinator: MagicMock,
    ) -> None:
        """Test sensor has extra_state_attributes."""
        from custom_components.embymedia.sensor import EmbyWatchStatisticsSensor

        sensor = EmbyWatchStatisticsSensor(mock_session_coordinator)
        attrs = sensor.extra_state_attributes
        assert attrs is not None

    def test_extra_state_attributes_has_active_sessions_count(
        self,
        mock_session_coordinator: MagicMock,
    ) -> None:
        """Test extra_state_attributes has active_sessions_count."""
        from custom_components.embymedia.sensor import EmbyWatchStatisticsSensor

        sensor = EmbyWatchStatisticsSensor(mock_session_coordinator)
        attrs = sensor.extra_state_attributes
        assert "active_sessions_count" in attrs
        assert attrs["active_sessions_count"] == 2

    def test_extra_state_attributes_has_active_sessions_list(
        self,
        mock_session_coordinator: MagicMock,
    ) -> None:
        """Test extra_state_attributes has active_sessions list."""
        from custom_components.embymedia.sensor import EmbyWatchStatisticsSensor

        sensor = EmbyWatchStatisticsSensor(mock_session_coordinator)
        attrs = sensor.extra_state_attributes
        assert "active_sessions" in attrs
        assert isinstance(attrs["active_sessions"], list)
        assert len(attrs["active_sessions"]) == 2

    def test_extra_state_attributes_session_details(
        self,
        mock_session_coordinator: MagicMock,
    ) -> None:
        """Test active_sessions contains correct details."""
        from custom_components.embymedia.sensor import EmbyWatchStatisticsSensor

        sensor = EmbyWatchStatisticsSensor(mock_session_coordinator)
        attrs = sensor.extra_state_attributes
        sessions = attrs["active_sessions"]

        # Check session details include item name
        item_names = [s.get("item_name") for s in sessions]
        assert "Test Movie" in item_names
        assert "Test Episode" in item_names

    def test_extra_state_attributes_has_daily_watch_time_seconds(
        self,
        mock_session_coordinator: MagicMock,
    ) -> None:
        """Test extra_state_attributes has daily_watch_time_seconds."""
        from custom_components.embymedia.sensor import EmbyWatchStatisticsSensor

        sensor = EmbyWatchStatisticsSensor(mock_session_coordinator)
        attrs = sensor.extra_state_attributes
        assert "daily_watch_time_seconds" in attrs
        assert attrs["daily_watch_time_seconds"] == 3600

    def test_extra_state_attributes_empty_when_no_sessions(
        self,
        mock_session_coordinator: MagicMock,
    ) -> None:
        """Test extra_state_attributes handles empty sessions."""
        from custom_components.embymedia.sensor import EmbyWatchStatisticsSensor

        mock_session_coordinator.playback_sessions = {}
        sensor = EmbyWatchStatisticsSensor(mock_session_coordinator)
        attrs = sensor.extra_state_attributes
        assert attrs["active_sessions_count"] == 0
        assert attrs["active_sessions"] == []


class TestEmbyWatchStatisticsSensorIcon:
    """Tests for sensor icon."""

    def test_sensor_icon(
        self,
        mock_session_coordinator: MagicMock,
    ) -> None:
        """Test sensor has appropriate icon."""
        from custom_components.embymedia.sensor import EmbyWatchStatisticsSensor

        sensor = EmbyWatchStatisticsSensor(mock_session_coordinator)
        assert sensor.icon == "mdi:chart-timeline-variant"


# =============================================================================
# Per-User Watch Statistics Sensor Tests
# =============================================================================


@pytest.fixture
def mock_session_coordinator_with_users() -> MagicMock:
    """Create a mock session coordinator with per-user watch statistics data."""
    coordinator = MagicMock()
    coordinator.server_id = "test-server-id"
    coordinator.server_name = "Test Server"
    coordinator.last_update_success = True
    # Per-user watch times
    coordinator.user_watch_times = {
        "user-abc": 1800,  # 30 minutes
        "user-xyz": 3600,  # 60 minutes
    }
    coordinator.get_user_watch_time = MagicMock(
        side_effect=lambda user_id: coordinator.user_watch_times.get(user_id, 0)
    )
    coordinator.playback_sessions = {
        "user-abc:session-1": {
            "item_id": "item-123",
            "item_name": "Test Movie",
            "user_id": "user-abc",
            "user_name": "Alice",
        },
    }
    coordinator.data = []
    return coordinator


class TestEmbyUserWatchStatisticsSensorExists:
    """Tests for EmbyUserWatchStatisticsSensor class existence."""

    def test_sensor_class_exists(self) -> None:
        """Test EmbyUserWatchStatisticsSensor class exists."""
        from custom_components.embymedia.sensor import EmbyUserWatchStatisticsSensor

        assert EmbyUserWatchStatisticsSensor is not None

    def test_sensor_inherits_from_base(
        self,
        mock_session_coordinator_with_users: MagicMock,
    ) -> None:
        """Test sensor inherits from EmbySessionSensorBase."""
        from custom_components.embymedia.sensor import (
            EmbySessionSensorBase,
            EmbyUserWatchStatisticsSensor,
        )

        sensor = EmbyUserWatchStatisticsSensor(
            mock_session_coordinator_with_users,
            user_id="user-abc",
            user_name="Alice",
        )
        assert isinstance(sensor, EmbySessionSensorBase)


class TestEmbyUserWatchStatisticsSensorIdentity:
    """Tests for per-user sensor identity attributes."""

    def test_sensor_unique_id_includes_user(
        self,
        mock_session_coordinator_with_users: MagicMock,
    ) -> None:
        """Test sensor has user-specific unique_id."""
        from custom_components.embymedia.sensor import EmbyUserWatchStatisticsSensor

        sensor = EmbyUserWatchStatisticsSensor(
            mock_session_coordinator_with_users,
            user_id="user-abc",
            user_name="Alice",
        )
        assert sensor.unique_id == "test-server-id_user-abc_watch_statistics"

    def test_sensor_name_includes_user_name(
        self,
        mock_session_coordinator_with_users: MagicMock,
    ) -> None:
        """Test sensor has user-specific name."""
        from custom_components.embymedia.sensor import EmbyUserWatchStatisticsSensor

        sensor = EmbyUserWatchStatisticsSensor(
            mock_session_coordinator_with_users,
            user_id="user-abc",
            user_name="Alice",
        )
        assert sensor.name == "Alice Watch Time"

    def test_sensor_translation_key(
        self,
        mock_session_coordinator_with_users: MagicMock,
    ) -> None:
        """Test sensor has correct translation_key."""
        from custom_components.embymedia.sensor import EmbyUserWatchStatisticsSensor

        sensor = EmbyUserWatchStatisticsSensor(
            mock_session_coordinator_with_users,
            user_id="user-abc",
            user_name="Alice",
        )
        assert sensor.translation_key == "user_watch_statistics"


class TestEmbyUserWatchStatisticsSensorNativeValue:
    """Tests for per-user sensor native_value."""

    def test_native_value_returns_user_watch_time_in_minutes(
        self,
        mock_session_coordinator_with_users: MagicMock,
    ) -> None:
        """Test native_value returns user's watch time in minutes."""
        from custom_components.embymedia.sensor import EmbyUserWatchStatisticsSensor

        sensor = EmbyUserWatchStatisticsSensor(
            mock_session_coordinator_with_users,
            user_id="user-abc",
            user_name="Alice",
        )
        # 1800 seconds = 30 minutes
        assert sensor.native_value == 30

    def test_native_value_different_user(
        self,
        mock_session_coordinator_with_users: MagicMock,
    ) -> None:
        """Test native_value returns correct value for different user."""
        from custom_components.embymedia.sensor import EmbyUserWatchStatisticsSensor

        sensor = EmbyUserWatchStatisticsSensor(
            mock_session_coordinator_with_users,
            user_id="user-xyz",
            user_name="Bob",
        )
        # 3600 seconds = 60 minutes
        assert sensor.native_value == 60

    def test_native_value_zero_for_unknown_user(
        self,
        mock_session_coordinator_with_users: MagicMock,
    ) -> None:
        """Test native_value returns 0 for unknown user."""
        from custom_components.embymedia.sensor import EmbyUserWatchStatisticsSensor

        sensor = EmbyUserWatchStatisticsSensor(
            mock_session_coordinator_with_users,
            user_id="unknown-user",
            user_name="Unknown",
        )
        assert sensor.native_value == 0


class TestEmbyUserWatchStatisticsSensorAttributes:
    """Tests for per-user sensor state class and unit."""

    def test_sensor_state_class_is_total_increasing(
        self,
        mock_session_coordinator_with_users: MagicMock,
    ) -> None:
        """Test sensor has TOTAL_INCREASING state class."""
        from custom_components.embymedia.sensor import EmbyUserWatchStatisticsSensor

        sensor = EmbyUserWatchStatisticsSensor(
            mock_session_coordinator_with_users,
            user_id="user-abc",
            user_name="Alice",
        )
        assert sensor.state_class == SensorStateClass.TOTAL_INCREASING

    def test_native_unit_of_measurement(
        self,
        mock_session_coordinator_with_users: MagicMock,
    ) -> None:
        """Test sensor has minutes as unit of measurement."""
        from custom_components.embymedia.sensor import EmbyUserWatchStatisticsSensor

        sensor = EmbyUserWatchStatisticsSensor(
            mock_session_coordinator_with_users,
            user_id="user-abc",
            user_name="Alice",
        )
        assert sensor.native_unit_of_measurement == "min"

    def test_sensor_icon(
        self,
        mock_session_coordinator_with_users: MagicMock,
    ) -> None:
        """Test sensor has appropriate icon."""
        from custom_components.embymedia.sensor import EmbyUserWatchStatisticsSensor

        sensor = EmbyUserWatchStatisticsSensor(
            mock_session_coordinator_with_users,
            user_id="user-abc",
            user_name="Alice",
        )
        assert sensor.icon == "mdi:account-clock"


class TestEmbyUserWatchStatisticsSensorExtraAttributes:
    """Tests for per-user sensor extra_state_attributes."""

    def test_has_extra_state_attributes(
        self,
        mock_session_coordinator_with_users: MagicMock,
    ) -> None:
        """Test sensor has extra_state_attributes."""
        from custom_components.embymedia.sensor import EmbyUserWatchStatisticsSensor

        sensor = EmbyUserWatchStatisticsSensor(
            mock_session_coordinator_with_users,
            user_id="user-abc",
            user_name="Alice",
        )
        attrs = sensor.extra_state_attributes
        assert attrs is not None

    def test_extra_state_attributes_has_user_id(
        self,
        mock_session_coordinator_with_users: MagicMock,
    ) -> None:
        """Test extra_state_attributes has user_id."""
        from custom_components.embymedia.sensor import EmbyUserWatchStatisticsSensor

        sensor = EmbyUserWatchStatisticsSensor(
            mock_session_coordinator_with_users,
            user_id="user-abc",
            user_name="Alice",
        )
        attrs = sensor.extra_state_attributes
        assert attrs is not None
        assert "user_id" in attrs
        assert attrs["user_id"] == "user-abc"

    def test_extra_state_attributes_has_watch_time_seconds(
        self,
        mock_session_coordinator_with_users: MagicMock,
    ) -> None:
        """Test extra_state_attributes has daily_watch_time_seconds."""
        from custom_components.embymedia.sensor import EmbyUserWatchStatisticsSensor

        sensor = EmbyUserWatchStatisticsSensor(
            mock_session_coordinator_with_users,
            user_id="user-abc",
            user_name="Alice",
        )
        attrs = sensor.extra_state_attributes
        assert attrs is not None
        assert "daily_watch_time_seconds" in attrs
        assert attrs["daily_watch_time_seconds"] == 1800
