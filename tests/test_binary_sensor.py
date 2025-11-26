"""Tests for Phase 12 binary sensor platform."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.embymedia.const import (
    CONF_API_KEY,
    CONF_VERIFY_SSL,
    DOMAIN,
)

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test Emby Server",
        data={
            CONF_HOST: "emby.local",
            CONF_PORT: 8096,
            CONF_SSL: False,
            CONF_API_KEY: "test-api-key-12345",
            CONF_VERIFY_SSL: True,
        },
        unique_id="test-server-id-12345",
        version=1,
    )


@pytest.fixture
def mock_server_data() -> dict[str, object]:
    """Create mock server coordinator data."""
    return {
        "server_version": "4.9.2.0",
        "has_pending_restart": False,
        "has_update_available": False,
        "scheduled_tasks": [],
        "running_tasks_count": 0,
        "library_scan_active": False,
        "library_scan_progress": None,
    }


class TestEmbyServerConnectedBinarySensor:
    """Tests for server connected binary sensor."""

    async def test_sensor_creation(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_data: dict[str, object],
    ) -> None:
        """Test server connected binary sensor is created."""
        from custom_components.embymedia.binary_sensor import (
            EmbyServerConnectedBinarySensor,
        )
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator

        with patch("custom_components.embymedia.coordinator_sensors.EmbyServerCoordinator"):
            mock_coordinator = MagicMock(spec=EmbyServerCoordinator)
            mock_coordinator.data = mock_server_data
            mock_coordinator.last_update_success = True
            mock_coordinator.server_id = "test-server-id"
            mock_coordinator.server_name = "Test Server"
            mock_coordinator.config_entry = mock_config_entry

            sensor = EmbyServerConnectedBinarySensor(
                coordinator=mock_coordinator,
            )

            assert sensor.unique_id == "test-server-id_server_connected"
            assert sensor.device_class == BinarySensorDeviceClass.CONNECTIVITY
            assert sensor.is_on is True

    async def test_sensor_offline_when_update_fails(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_data: dict[str, object],
    ) -> None:
        """Test server connected shows off when update fails."""
        from custom_components.embymedia.binary_sensor import (
            EmbyServerConnectedBinarySensor,
        )
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator

        mock_coordinator = MagicMock(spec=EmbyServerCoordinator)
        mock_coordinator.data = mock_server_data
        mock_coordinator.last_update_success = False
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyServerConnectedBinarySensor(coordinator=mock_coordinator)

        assert sensor.is_on is False


class TestEmbyPendingRestartBinarySensor:
    """Tests for pending restart binary sensor."""

    async def test_sensor_no_restart_pending(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_data: dict[str, object],
    ) -> None:
        """Test pending restart is off when no restart pending."""
        from custom_components.embymedia.binary_sensor import (
            EmbyPendingRestartBinarySensor,
        )
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator

        mock_coordinator = MagicMock(spec=EmbyServerCoordinator)
        mock_coordinator.data = mock_server_data
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyPendingRestartBinarySensor(coordinator=mock_coordinator)

        assert sensor.unique_id == "test-server-id_pending_restart"
        assert sensor.device_class == BinarySensorDeviceClass.PROBLEM
        assert sensor.is_on is False

    async def test_sensor_restart_pending(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test pending restart is on when restart is pending."""
        from custom_components.embymedia.binary_sensor import (
            EmbyPendingRestartBinarySensor,
        )
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator

        server_data = {
            "server_version": "4.9.2.0",
            "has_pending_restart": True,
            "has_update_available": False,
            "scheduled_tasks": [],
            "running_tasks_count": 0,
            "library_scan_active": False,
            "library_scan_progress": None,
        }

        mock_coordinator = MagicMock(spec=EmbyServerCoordinator)
        mock_coordinator.data = server_data
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyPendingRestartBinarySensor(coordinator=mock_coordinator)

        assert sensor.is_on is True


class TestEmbyUpdateAvailableBinarySensor:
    """Tests for update available binary sensor."""

    async def test_sensor_no_update_available(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_data: dict[str, object],
    ) -> None:
        """Test update available is off when no update."""
        from custom_components.embymedia.binary_sensor import (
            EmbyUpdateAvailableBinarySensor,
        )
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator

        mock_coordinator = MagicMock(spec=EmbyServerCoordinator)
        mock_coordinator.data = mock_server_data
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyUpdateAvailableBinarySensor(coordinator=mock_coordinator)

        assert sensor.unique_id == "test-server-id_update_available"
        assert sensor.device_class == BinarySensorDeviceClass.UPDATE
        assert sensor.is_on is False

    async def test_sensor_update_available(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test update available is on when update exists."""
        from custom_components.embymedia.binary_sensor import (
            EmbyUpdateAvailableBinarySensor,
        )
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator

        server_data = {
            "server_version": "4.9.2.0",
            "has_pending_restart": False,
            "has_update_available": True,
            "scheduled_tasks": [],
            "running_tasks_count": 0,
            "library_scan_active": False,
            "library_scan_progress": None,
        }

        mock_coordinator = MagicMock(spec=EmbyServerCoordinator)
        mock_coordinator.data = server_data
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyUpdateAvailableBinarySensor(coordinator=mock_coordinator)

        assert sensor.is_on is True


class TestEmbyLibraryScanActiveBinarySensor:
    """Tests for library scan active binary sensor."""

    async def test_sensor_scan_not_active(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_data: dict[str, object],
    ) -> None:
        """Test library scan is off when not scanning."""
        from custom_components.embymedia.binary_sensor import (
            EmbyLibraryScanActiveBinarySensor,
        )
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator

        mock_coordinator = MagicMock(spec=EmbyServerCoordinator)
        mock_coordinator.data = mock_server_data
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyLibraryScanActiveBinarySensor(coordinator=mock_coordinator)

        assert sensor.unique_id == "test-server-id_library_scan_active"
        assert sensor.device_class == BinarySensorDeviceClass.RUNNING
        assert sensor.is_on is False

    async def test_sensor_scan_active_with_progress(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test library scan is on when scanning with progress."""
        from custom_components.embymedia.binary_sensor import (
            EmbyLibraryScanActiveBinarySensor,
        )
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator

        server_data = {
            "server_version": "4.9.2.0",
            "has_pending_restart": False,
            "has_update_available": False,
            "scheduled_tasks": [],
            "running_tasks_count": 1,
            "library_scan_active": True,
            "library_scan_progress": 45.5,
        }

        mock_coordinator = MagicMock(spec=EmbyServerCoordinator)
        mock_coordinator.data = server_data
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyLibraryScanActiveBinarySensor(coordinator=mock_coordinator)

        assert sensor.is_on is True
        assert sensor.extra_state_attributes == {"progress_percent": 45.5}


class TestAsyncSetupEntry:
    """Tests for async_setup_entry function."""

    async def test_setup_entry_creates_binary_sensors(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test that setup creates all binary sensors."""
        from custom_components.embymedia.binary_sensor import async_setup_entry
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator

        mock_server_data = {
            "server_version": "4.9.2.0",
            "has_pending_restart": False,
            "has_update_available": False,
            "scheduled_tasks": [],
            "running_tasks_count": 0,
            "library_scan_active": False,
            "library_scan_progress": None,
        }

        mock_coordinator = MagicMock(spec=EmbyServerCoordinator)
        mock_coordinator.data = mock_server_data
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.config_entry = mock_config_entry

        # Create a simple class to hold the coordinator
        class RuntimeData:
            server_coordinator = mock_coordinator

        # Store coordinator in runtime_data
        mock_config_entry.runtime_data = RuntimeData()

        entities_added: list[object] = []

        def mock_add_entities(entities: list[object], update: bool = False) -> None:
            entities_added.extend(entities)

        await async_setup_entry(hass, mock_config_entry, mock_add_entities)

        assert len(entities_added) == 4  # 4 binary sensors


class TestBinarySensorDataNone:
    """Tests for binary sensors when coordinator data is None."""

    async def test_pending_restart_returns_none_when_data_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test pending restart returns None when coordinator data is None."""
        from custom_components.embymedia.binary_sensor import (
            EmbyPendingRestartBinarySensor,
        )
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator

        mock_coordinator = MagicMock(spec=EmbyServerCoordinator)
        mock_coordinator.data = None
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyPendingRestartBinarySensor(coordinator=mock_coordinator)

        assert sensor.is_on is None

    async def test_update_available_returns_none_when_data_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test update available returns None when coordinator data is None."""
        from custom_components.embymedia.binary_sensor import (
            EmbyUpdateAvailableBinarySensor,
        )
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator

        mock_coordinator = MagicMock(spec=EmbyServerCoordinator)
        mock_coordinator.data = None
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyUpdateAvailableBinarySensor(coordinator=mock_coordinator)

        assert sensor.is_on is None

    async def test_library_scan_active_returns_none_when_data_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test library scan active returns None when coordinator data is None."""
        from custom_components.embymedia.binary_sensor import (
            EmbyLibraryScanActiveBinarySensor,
        )
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator

        mock_coordinator = MagicMock(spec=EmbyServerCoordinator)
        mock_coordinator.data = None
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyLibraryScanActiveBinarySensor(coordinator=mock_coordinator)

        assert sensor.is_on is None

    async def test_library_scan_extra_state_attributes_none_when_data_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test library scan extra_state_attributes returns None when data is None."""
        from custom_components.embymedia.binary_sensor import (
            EmbyLibraryScanActiveBinarySensor,
        )
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator

        mock_coordinator = MagicMock(spec=EmbyServerCoordinator)
        mock_coordinator.data = None
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyLibraryScanActiveBinarySensor(coordinator=mock_coordinator)

        assert sensor.extra_state_attributes is None
