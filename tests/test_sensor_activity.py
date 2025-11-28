"""Tests for Activity and Device sensors.

Phase 18: User Activity & Statistics
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_server_coordinator() -> MagicMock:
    """Create a mock server coordinator with activity/device data."""
    coordinator = MagicMock()
    coordinator.server_id = "test-server-id"
    coordinator.server_name = "Test Server"
    coordinator.last_update_success = True
    coordinator.data = {
        "server_version": "4.9.1.90",
        "has_pending_restart": False,
        "has_update_available": False,
        "scheduled_tasks": [],
        "running_tasks_count": 0,
        "library_scan_active": False,
        "library_scan_progress": None,
        "live_tv_enabled": False,
        "live_tv_tuner_count": 0,
        "live_tv_active_recordings": 0,
        "recording_count": 0,
        "scheduled_timer_count": 0,
        "series_timer_count": 0,
        # Phase 18 activity data
        "recent_activities": [
            {
                "Id": 6612,
                "Name": "Recording of BBC News has failed",
                "Type": "livetv.recordingerror",
                "Date": "2025-11-28T10:00:37.8370000Z",
                "Severity": "Error",
            },
            {
                "Id": 6611,
                "Name": "admin is playing Elsbeth",
                "Type": "playback.start",
                "Date": "2025-11-28T09:56:09.8260000Z",
                "Severity": "Info",
            },
        ],
        "activity_count": 6612,
        # Phase 18 device data
        "devices": [
            {
                "Name": "Samsung Smart TV",
                "Id": "5",
                "LastUserName": "admin",
                "AppName": "Emby for Samsung",
                "AppVersion": "2.2.5",
                "LastUserId": "user1",
                "DateLastActivity": "2025-11-28T10:00:16.0000000Z",
            },
            {
                "Name": "macOS",
                "Id": "6",
                "LastUserName": "troy",
                "AppName": "Emby for macOS",
                "AppVersion": "2.2.39",
                "LastUserId": "user2",
                "DateLastActivity": "2025-11-28T09:56:51.0000000Z",
            },
        ],
        "device_count": 2,
    }
    return coordinator


class TestEmbyLastActivitySensor:
    """Tests for EmbyLastActivitySensor."""

    def test_sensor_exists(self) -> None:
        """Test EmbyLastActivitySensor class exists."""
        from custom_components.embymedia.sensor import EmbyLastActivitySensor

        assert EmbyLastActivitySensor is not None

    def test_sensor_inherits_from_base(
        self,
        mock_server_coordinator: MagicMock,
    ) -> None:
        """Test sensor inherits from EmbyServerSensorBase."""
        from custom_components.embymedia.sensor import (
            EmbyLastActivitySensor,
            EmbyServerSensorBase,
        )

        sensor = EmbyLastActivitySensor(mock_server_coordinator)
        assert isinstance(sensor, EmbyServerSensorBase)

    def test_sensor_unique_id(
        self,
        mock_server_coordinator: MagicMock,
    ) -> None:
        """Test sensor has correct unique_id."""
        from custom_components.embymedia.sensor import EmbyLastActivitySensor

        sensor = EmbyLastActivitySensor(mock_server_coordinator)
        assert sensor.unique_id == "test-server-id_last_activity"

    def test_sensor_translation_key(
        self,
        mock_server_coordinator: MagicMock,
    ) -> None:
        """Test sensor has correct translation_key."""
        from custom_components.embymedia.sensor import EmbyLastActivitySensor

        sensor = EmbyLastActivitySensor(mock_server_coordinator)
        assert sensor.translation_key == "last_activity"

    def test_sensor_device_class_is_timestamp(
        self,
        mock_server_coordinator: MagicMock,
    ) -> None:
        """Test sensor has timestamp device class."""
        from custom_components.embymedia.sensor import EmbyLastActivitySensor

        sensor = EmbyLastActivitySensor(mock_server_coordinator)
        assert sensor.device_class == SensorDeviceClass.TIMESTAMP

    def test_sensor_native_value_is_datetime(
        self,
        mock_server_coordinator: MagicMock,
    ) -> None:
        """Test native_value returns datetime from most recent activity."""
        from custom_components.embymedia.sensor import EmbyLastActivitySensor

        sensor = EmbyLastActivitySensor(mock_server_coordinator)
        value = sensor.native_value

        # Should be a datetime object
        assert isinstance(value, datetime)

    def test_sensor_native_value_none_when_no_data(
        self,
        mock_server_coordinator: MagicMock,
    ) -> None:
        """Test native_value returns None when no coordinator data."""
        from custom_components.embymedia.sensor import EmbyLastActivitySensor

        mock_server_coordinator.data = None
        sensor = EmbyLastActivitySensor(mock_server_coordinator)
        assert sensor.native_value is None

    def test_sensor_native_value_none_when_no_activities(
        self,
        mock_server_coordinator: MagicMock,
    ) -> None:
        """Test native_value returns None when no activities."""
        from custom_components.embymedia.sensor import EmbyLastActivitySensor

        mock_server_coordinator.data["recent_activities"] = []
        sensor = EmbyLastActivitySensor(mock_server_coordinator)
        assert sensor.native_value is None

    def test_sensor_native_value_none_when_no_date(
        self,
        mock_server_coordinator: MagicMock,
    ) -> None:
        """Test native_value returns None when activity has no Date field."""
        from custom_components.embymedia.sensor import EmbyLastActivitySensor

        mock_server_coordinator.data["recent_activities"] = [
            {
                "Id": 6612,
                "Name": "Activity without date",
                "Type": "test.type",
                "Severity": "Info",
                # No "Date" field
            }
        ]
        sensor = EmbyLastActivitySensor(mock_server_coordinator)
        assert sensor.native_value is None

    def test_sensor_native_value_none_on_invalid_date(
        self,
        mock_server_coordinator: MagicMock,
    ) -> None:
        """Test native_value returns None when date is invalid."""
        from custom_components.embymedia.sensor import EmbyLastActivitySensor

        mock_server_coordinator.data["recent_activities"] = [
            {
                "Id": 6612,
                "Name": "Activity with invalid date",
                "Type": "test.type",
                "Severity": "Info",
                "Date": "not-a-valid-date",
            }
        ]
        sensor = EmbyLastActivitySensor(mock_server_coordinator)
        assert sensor.native_value is None

    def test_sensor_extra_state_attributes_none_when_no_data(
        self,
        mock_server_coordinator: MagicMock,
    ) -> None:
        """Test extra_state_attributes returns None when no coordinator data."""
        from custom_components.embymedia.sensor import EmbyLastActivitySensor

        mock_server_coordinator.data = None
        sensor = EmbyLastActivitySensor(mock_server_coordinator)
        assert sensor.extra_state_attributes is None

    def test_sensor_has_extra_state_attributes(
        self,
        mock_server_coordinator: MagicMock,
    ) -> None:
        """Test sensor has extra_state_attributes with activity info."""
        from custom_components.embymedia.sensor import EmbyLastActivitySensor

        sensor = EmbyLastActivitySensor(mock_server_coordinator)
        attrs = sensor.extra_state_attributes

        assert attrs is not None
        assert "activity_name" in attrs
        assert "activity_type" in attrs
        assert "severity" in attrs
        assert "total_activities" in attrs

    def test_sensor_extra_state_attributes_values(
        self,
        mock_server_coordinator: MagicMock,
    ) -> None:
        """Test extra_state_attributes contains correct values."""
        from custom_components.embymedia.sensor import EmbyLastActivitySensor

        sensor = EmbyLastActivitySensor(mock_server_coordinator)
        attrs = sensor.extra_state_attributes

        assert attrs["activity_name"] == "Recording of BBC News has failed"
        assert attrs["activity_type"] == "livetv.recordingerror"
        assert attrs["severity"] == "Error"
        assert attrs["total_activities"] == 6612

    def test_sensor_icon(
        self,
        mock_server_coordinator: MagicMock,
    ) -> None:
        """Test sensor has appropriate icon."""
        from custom_components.embymedia.sensor import EmbyLastActivitySensor

        sensor = EmbyLastActivitySensor(mock_server_coordinator)
        assert sensor.icon == "mdi:history"


class TestEmbyConnectedDevicesSensor:
    """Tests for EmbyConnectedDevicesSensor."""

    def test_sensor_exists(self) -> None:
        """Test EmbyConnectedDevicesSensor class exists."""
        from custom_components.embymedia.sensor import EmbyConnectedDevicesSensor

        assert EmbyConnectedDevicesSensor is not None

    def test_sensor_inherits_from_base(
        self,
        mock_server_coordinator: MagicMock,
    ) -> None:
        """Test sensor inherits from EmbyServerSensorBase."""
        from custom_components.embymedia.sensor import (
            EmbyConnectedDevicesSensor,
            EmbyServerSensorBase,
        )

        sensor = EmbyConnectedDevicesSensor(mock_server_coordinator)
        assert isinstance(sensor, EmbyServerSensorBase)

    def test_sensor_unique_id(
        self,
        mock_server_coordinator: MagicMock,
    ) -> None:
        """Test sensor has correct unique_id."""
        from custom_components.embymedia.sensor import EmbyConnectedDevicesSensor

        sensor = EmbyConnectedDevicesSensor(mock_server_coordinator)
        assert sensor.unique_id == "test-server-id_connected_devices"

    def test_sensor_translation_key(
        self,
        mock_server_coordinator: MagicMock,
    ) -> None:
        """Test sensor has correct translation_key."""
        from custom_components.embymedia.sensor import EmbyConnectedDevicesSensor

        sensor = EmbyConnectedDevicesSensor(mock_server_coordinator)
        assert sensor.translation_key == "connected_devices"

    def test_sensor_state_class_is_measurement(
        self,
        mock_server_coordinator: MagicMock,
    ) -> None:
        """Test sensor has measurement state class."""
        from custom_components.embymedia.sensor import EmbyConnectedDevicesSensor

        sensor = EmbyConnectedDevicesSensor(mock_server_coordinator)
        assert sensor.state_class == SensorStateClass.MEASUREMENT

    def test_sensor_native_value_is_device_count(
        self,
        mock_server_coordinator: MagicMock,
    ) -> None:
        """Test native_value returns device count."""
        from custom_components.embymedia.sensor import EmbyConnectedDevicesSensor

        sensor = EmbyConnectedDevicesSensor(mock_server_coordinator)
        assert sensor.native_value == 2

    def test_sensor_native_value_none_when_no_data(
        self,
        mock_server_coordinator: MagicMock,
    ) -> None:
        """Test native_value returns None when no coordinator data."""
        from custom_components.embymedia.sensor import EmbyConnectedDevicesSensor

        mock_server_coordinator.data = None
        sensor = EmbyConnectedDevicesSensor(mock_server_coordinator)
        assert sensor.native_value is None

    def test_sensor_extra_state_attributes_none_when_no_data(
        self,
        mock_server_coordinator: MagicMock,
    ) -> None:
        """Test extra_state_attributes returns None when no coordinator data."""
        from custom_components.embymedia.sensor import EmbyConnectedDevicesSensor

        mock_server_coordinator.data = None
        sensor = EmbyConnectedDevicesSensor(mock_server_coordinator)
        assert sensor.extra_state_attributes is None

    def test_sensor_has_extra_state_attributes(
        self,
        mock_server_coordinator: MagicMock,
    ) -> None:
        """Test sensor has extra_state_attributes with device list."""
        from custom_components.embymedia.sensor import EmbyConnectedDevicesSensor

        sensor = EmbyConnectedDevicesSensor(mock_server_coordinator)
        attrs = sensor.extra_state_attributes

        assert attrs is not None
        assert "devices" in attrs

    def test_sensor_extra_state_attributes_devices_list(
        self,
        mock_server_coordinator: MagicMock,
    ) -> None:
        """Test extra_state_attributes devices list contains device info."""
        from custom_components.embymedia.sensor import EmbyConnectedDevicesSensor

        sensor = EmbyConnectedDevicesSensor(mock_server_coordinator)
        attrs = sensor.extra_state_attributes
        devices = attrs["devices"]

        assert len(devices) == 2
        assert devices[0]["name"] == "Samsung Smart TV"
        assert devices[0]["app_name"] == "Emby for Samsung"
        assert devices[0]["last_user"] == "admin"
        assert devices[1]["name"] == "macOS"
        assert devices[1]["app_name"] == "Emby for macOS"

    def test_sensor_icon(
        self,
        mock_server_coordinator: MagicMock,
    ) -> None:
        """Test sensor has appropriate icon."""
        from custom_components.embymedia.sensor import EmbyConnectedDevicesSensor

        sensor = EmbyConnectedDevicesSensor(mock_server_coordinator)
        assert sensor.icon == "mdi:devices"
