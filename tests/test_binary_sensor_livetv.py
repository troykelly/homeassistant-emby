"""Tests for Live TV binary sensors.

Phase 16: Live TV & DVR Integration
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from custom_components.embymedia.binary_sensor import EmbyLiveTvEnabledBinarySensor
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
    }
    return coordinator


class TestEmbyLiveTvEnabledBinarySensor:
    """Tests for Live TV enabled binary sensor."""

    def test_unique_id(self, mock_server_coordinator: MagicMock) -> None:
        """Test unique ID is set correctly."""
        sensor = EmbyLiveTvEnabledBinarySensor(mock_server_coordinator)

        assert sensor.unique_id == "test-server-123_live_tv_enabled"

    def test_device_info(self, mock_server_coordinator: MagicMock) -> None:
        """Test device info is correct."""
        sensor = EmbyLiveTvEnabledBinarySensor(mock_server_coordinator)

        device_info: DeviceInfo = sensor.device_info
        assert device_info["identifiers"] == {(DOMAIN, "test-server-123")}
        assert device_info["name"] == "Test Emby Server"
        assert device_info["manufacturer"] == "Emby"
        assert device_info["model"] == "Emby Server"

    def test_is_on_when_enabled(self, mock_server_coordinator: MagicMock) -> None:
        """Test is_on returns True when Live TV is enabled."""
        mock_server_coordinator.data["live_tv_enabled"] = True
        sensor = EmbyLiveTvEnabledBinarySensor(mock_server_coordinator)

        assert sensor.is_on is True

    def test_is_on_when_disabled(self, mock_server_coordinator: MagicMock) -> None:
        """Test is_on returns False when Live TV is disabled."""
        mock_server_coordinator.data["live_tv_enabled"] = False
        sensor = EmbyLiveTvEnabledBinarySensor(mock_server_coordinator)

        assert sensor.is_on is False

    def test_is_on_when_no_data(self, mock_server_coordinator: MagicMock) -> None:
        """Test is_on returns None when no data available."""
        mock_server_coordinator.data = None
        sensor = EmbyLiveTvEnabledBinarySensor(mock_server_coordinator)

        assert sensor.is_on is None

    def test_extra_state_attributes(self, mock_server_coordinator: MagicMock) -> None:
        """Test extra state attributes contain tuner and recording info."""
        mock_server_coordinator.data["live_tv_tuner_count"] = 2
        mock_server_coordinator.data["live_tv_active_recordings"] = 1
        sensor = EmbyLiveTvEnabledBinarySensor(mock_server_coordinator)

        attrs = sensor.extra_state_attributes
        assert attrs is not None
        assert attrs["tuner_count"] == 2
        assert attrs["active_recordings"] == 1

    def test_extra_state_attributes_no_data(self, mock_server_coordinator: MagicMock) -> None:
        """Test extra state attributes return None when no data."""
        mock_server_coordinator.data = None
        sensor = EmbyLiveTvEnabledBinarySensor(mock_server_coordinator)

        assert sensor.extra_state_attributes is None

    def test_translation_key(self, mock_server_coordinator: MagicMock) -> None:
        """Test translation key is set correctly."""
        sensor = EmbyLiveTvEnabledBinarySensor(mock_server_coordinator)

        assert sensor.translation_key == "live_tv_enabled"

    def test_icon(self, mock_server_coordinator: MagicMock) -> None:
        """Test icon is set correctly."""
        sensor = EmbyLiveTvEnabledBinarySensor(mock_server_coordinator)

        assert sensor.icon == "mdi:television-classic"

    def test_available_when_coordinator_success(self, mock_server_coordinator: MagicMock) -> None:
        """Test available returns True when coordinator has data."""
        mock_server_coordinator.last_update_success = True
        mock_server_coordinator.data = {"live_tv_enabled": True}
        sensor = EmbyLiveTvEnabledBinarySensor(mock_server_coordinator)

        assert sensor.available is True

    def test_available_when_no_data(self, mock_server_coordinator: MagicMock) -> None:
        """Test available returns False when coordinator has no data."""
        mock_server_coordinator.last_update_success = True
        mock_server_coordinator.data = None
        sensor = EmbyLiveTvEnabledBinarySensor(mock_server_coordinator)

        assert sensor.available is False

    def test_available_when_update_failed(self, mock_server_coordinator: MagicMock) -> None:
        """Test available returns False when coordinator update failed."""
        mock_server_coordinator.last_update_success = False
        mock_server_coordinator.data = {"live_tv_enabled": True}
        sensor = EmbyLiveTvEnabledBinarySensor(mock_server_coordinator)

        assert sensor.available is False
