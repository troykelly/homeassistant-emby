"""Tests for Live TV sensors.

Phase 16: Live TV & DVR Integration
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from custom_components.embymedia.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.helpers.device_registry import DeviceInfo


@pytest.fixture
def mock_server_coordinator() -> MagicMock:
    """Create a mock server coordinator with Live TV data."""
    coordinator = MagicMock()
    coordinator.server_id = "test-server-123"
    coordinator.server_name = "Test Emby Server"
    coordinator.last_update_success = True
    coordinator.data = {
        "server_version": "4.9.1.90",
        "has_pending_restart": False,
        "has_update_available": False,
        "scheduled_tasks": [],
        "running_tasks_count": 0,
        "library_scan_active": False,
        "library_scan_progress": None,
        "live_tv_enabled": True,
        "live_tv_tuner_count": 2,
        "live_tv_active_recordings": 1,
        # Live TV sensor data
        "recording_count": 845,
        "scheduled_timer_count": 70,
        "series_timer_count": 9,
    }
    return coordinator


class TestEmbyRecordingCountSensor:
    """Tests for recording count sensor."""

    def test_unique_id(self, mock_server_coordinator: MagicMock) -> None:
        """Test unique ID is set correctly."""
        from custom_components.embymedia.sensor import EmbyRecordingCountSensor

        sensor = EmbyRecordingCountSensor(mock_server_coordinator)

        assert sensor.unique_id == "test-server-123_recording_count"

    def test_device_info(self, mock_server_coordinator: MagicMock) -> None:
        """Test device info is correct."""
        from custom_components.embymedia.sensor import EmbyRecordingCountSensor

        sensor = EmbyRecordingCountSensor(mock_server_coordinator)

        device_info: DeviceInfo = sensor.device_info
        assert device_info["identifiers"] == {(DOMAIN, "test-server-123")}
        assert device_info["name"] == "Test Emby Server"

    def test_native_value(self, mock_server_coordinator: MagicMock) -> None:
        """Test native value returns recording count."""
        from custom_components.embymedia.sensor import EmbyRecordingCountSensor

        mock_server_coordinator.data["recording_count"] = 845
        sensor = EmbyRecordingCountSensor(mock_server_coordinator)

        assert sensor.native_value == 845

    def test_native_value_zero(self, mock_server_coordinator: MagicMock) -> None:
        """Test native value returns zero when no recordings."""
        from custom_components.embymedia.sensor import EmbyRecordingCountSensor

        mock_server_coordinator.data["recording_count"] = 0
        sensor = EmbyRecordingCountSensor(mock_server_coordinator)

        assert sensor.native_value == 0

    def test_native_value_when_no_data(self, mock_server_coordinator: MagicMock) -> None:
        """Test native value returns None when no data."""
        from custom_components.embymedia.sensor import EmbyRecordingCountSensor

        mock_server_coordinator.data = None
        sensor = EmbyRecordingCountSensor(mock_server_coordinator)

        assert sensor.native_value is None

    def test_translation_key(self, mock_server_coordinator: MagicMock) -> None:
        """Test translation key is set correctly."""
        from custom_components.embymedia.sensor import EmbyRecordingCountSensor

        sensor = EmbyRecordingCountSensor(mock_server_coordinator)

        assert sensor.translation_key == "recording_count"

    def test_icon(self, mock_server_coordinator: MagicMock) -> None:
        """Test icon is set correctly."""
        from custom_components.embymedia.sensor import EmbyRecordingCountSensor

        sensor = EmbyRecordingCountSensor(mock_server_coordinator)

        assert sensor.icon == "mdi:record-rec"


class TestEmbyActiveRecordingsSensor:
    """Tests for active recordings sensor."""

    def test_unique_id(self, mock_server_coordinator: MagicMock) -> None:
        """Test unique ID is set correctly."""
        from custom_components.embymedia.sensor import EmbyActiveRecordingsSensor

        sensor = EmbyActiveRecordingsSensor(mock_server_coordinator)

        assert sensor.unique_id == "test-server-123_active_recordings"

    def test_native_value(self, mock_server_coordinator: MagicMock) -> None:
        """Test native value returns active recordings count."""
        from custom_components.embymedia.sensor import EmbyActiveRecordingsSensor

        mock_server_coordinator.data["live_tv_active_recordings"] = 3
        sensor = EmbyActiveRecordingsSensor(mock_server_coordinator)

        assert sensor.native_value == 3

    def test_native_value_zero(self, mock_server_coordinator: MagicMock) -> None:
        """Test native value returns zero when no active recordings."""
        from custom_components.embymedia.sensor import EmbyActiveRecordingsSensor

        mock_server_coordinator.data["live_tv_active_recordings"] = 0
        sensor = EmbyActiveRecordingsSensor(mock_server_coordinator)

        assert sensor.native_value == 0

    def test_native_value_when_no_data(self, mock_server_coordinator: MagicMock) -> None:
        """Test native value returns None when no data."""
        from custom_components.embymedia.sensor import EmbyActiveRecordingsSensor

        mock_server_coordinator.data = None
        sensor = EmbyActiveRecordingsSensor(mock_server_coordinator)

        assert sensor.native_value is None

    def test_translation_key(self, mock_server_coordinator: MagicMock) -> None:
        """Test translation key is set correctly."""
        from custom_components.embymedia.sensor import EmbyActiveRecordingsSensor

        sensor = EmbyActiveRecordingsSensor(mock_server_coordinator)

        assert sensor.translation_key == "active_recordings"

    def test_icon(self, mock_server_coordinator: MagicMock) -> None:
        """Test icon is set correctly."""
        from custom_components.embymedia.sensor import EmbyActiveRecordingsSensor

        sensor = EmbyActiveRecordingsSensor(mock_server_coordinator)

        assert sensor.icon == "mdi:record"


class TestEmbyScheduledTimerCountSensor:
    """Tests for scheduled timer count sensor."""

    def test_unique_id(self, mock_server_coordinator: MagicMock) -> None:
        """Test unique ID is set correctly."""
        from custom_components.embymedia.sensor import EmbyScheduledTimerCountSensor

        sensor = EmbyScheduledTimerCountSensor(mock_server_coordinator)

        assert sensor.unique_id == "test-server-123_scheduled_timer_count"

    def test_native_value(self, mock_server_coordinator: MagicMock) -> None:
        """Test native value returns scheduled timer count."""
        from custom_components.embymedia.sensor import EmbyScheduledTimerCountSensor

        mock_server_coordinator.data["scheduled_timer_count"] = 70
        sensor = EmbyScheduledTimerCountSensor(mock_server_coordinator)

        assert sensor.native_value == 70

    def test_native_value_zero(self, mock_server_coordinator: MagicMock) -> None:
        """Test native value returns zero when no timers."""
        from custom_components.embymedia.sensor import EmbyScheduledTimerCountSensor

        mock_server_coordinator.data["scheduled_timer_count"] = 0
        sensor = EmbyScheduledTimerCountSensor(mock_server_coordinator)

        assert sensor.native_value == 0

    def test_native_value_when_no_data(self, mock_server_coordinator: MagicMock) -> None:
        """Test native value returns None when no data."""
        from custom_components.embymedia.sensor import EmbyScheduledTimerCountSensor

        mock_server_coordinator.data = None
        sensor = EmbyScheduledTimerCountSensor(mock_server_coordinator)

        assert sensor.native_value is None

    def test_translation_key(self, mock_server_coordinator: MagicMock) -> None:
        """Test translation key is set correctly."""
        from custom_components.embymedia.sensor import EmbyScheduledTimerCountSensor

        sensor = EmbyScheduledTimerCountSensor(mock_server_coordinator)

        assert sensor.translation_key == "scheduled_timer_count"

    def test_icon(self, mock_server_coordinator: MagicMock) -> None:
        """Test icon is set correctly."""
        from custom_components.embymedia.sensor import EmbyScheduledTimerCountSensor

        sensor = EmbyScheduledTimerCountSensor(mock_server_coordinator)

        assert sensor.icon == "mdi:timer"


class TestEmbySeriesTimerCountSensor:
    """Tests for series timer count sensor."""

    def test_unique_id(self, mock_server_coordinator: MagicMock) -> None:
        """Test unique ID is set correctly."""
        from custom_components.embymedia.sensor import EmbySeriesTimerCountSensor

        sensor = EmbySeriesTimerCountSensor(mock_server_coordinator)

        assert sensor.unique_id == "test-server-123_series_timer_count"

    def test_native_value(self, mock_server_coordinator: MagicMock) -> None:
        """Test native value returns series timer count."""
        from custom_components.embymedia.sensor import EmbySeriesTimerCountSensor

        mock_server_coordinator.data["series_timer_count"] = 9
        sensor = EmbySeriesTimerCountSensor(mock_server_coordinator)

        assert sensor.native_value == 9

    def test_native_value_zero(self, mock_server_coordinator: MagicMock) -> None:
        """Test native value returns zero when no series timers."""
        from custom_components.embymedia.sensor import EmbySeriesTimerCountSensor

        mock_server_coordinator.data["series_timer_count"] = 0
        sensor = EmbySeriesTimerCountSensor(mock_server_coordinator)

        assert sensor.native_value == 0

    def test_native_value_when_no_data(self, mock_server_coordinator: MagicMock) -> None:
        """Test native value returns None when no data."""
        from custom_components.embymedia.sensor import EmbySeriesTimerCountSensor

        mock_server_coordinator.data = None
        sensor = EmbySeriesTimerCountSensor(mock_server_coordinator)

        assert sensor.native_value is None

    def test_translation_key(self, mock_server_coordinator: MagicMock) -> None:
        """Test translation key is set correctly."""
        from custom_components.embymedia.sensor import EmbySeriesTimerCountSensor

        sensor = EmbySeriesTimerCountSensor(mock_server_coordinator)

        assert sensor.translation_key == "series_timer_count"

    def test_icon(self, mock_server_coordinator: MagicMock) -> None:
        """Test icon is set correctly."""
        from custom_components.embymedia.sensor import EmbySeriesTimerCountSensor

        sensor = EmbySeriesTimerCountSensor(mock_server_coordinator)

        assert sensor.icon == "mdi:timer-sync"
