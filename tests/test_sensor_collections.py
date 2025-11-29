"""Tests for Collection sensors.

Phase 19: Collection Management
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.embymedia.const import DOMAIN

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry for testing."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "emby.local",
            "port": 8096,
            "api_key": "test-api-key",
        },
        unique_id="test-server-id",
    )


class TestEmbyCollectionCountSensor:
    """Tests for collection count sensor (Phase 19)."""

    async def test_sensor_exists(self) -> None:
        """Test that EmbyCollectionCountSensor class exists."""
        from custom_components.embymedia.sensor import EmbyCollectionCountSensor

        assert EmbyCollectionCountSensor is not None

    async def test_sensor_value(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test collection count sensor returns correct value."""
        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator
        from custom_components.embymedia.sensor import EmbyCollectionCountSensor

        mock_coordinator = MagicMock(spec=EmbyLibraryCoordinator)
        mock_coordinator.data = {"collection_count": 25}
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyCollectionCountSensor(coordinator=mock_coordinator, server_name="Test Server")

        assert sensor.unique_id == "test-server-id_collection_count"
        assert sensor.native_value == 25
        assert sensor.icon == "mdi:folder-multiple"

    async def test_sensor_returns_none_when_data_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test collection count sensor returns None when data is None."""
        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator
        from custom_components.embymedia.sensor import EmbyCollectionCountSensor

        mock_coordinator = MagicMock(spec=EmbyLibraryCoordinator)
        mock_coordinator.data = None
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyCollectionCountSensor(coordinator=mock_coordinator, server_name="Test Server")

        assert sensor.native_value is None

    async def test_sensor_returns_zero_when_no_collections(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test collection count sensor returns 0 when no collections exist."""
        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator
        from custom_components.embymedia.sensor import EmbyCollectionCountSensor

        mock_coordinator = MagicMock(spec=EmbyLibraryCoordinator)
        mock_coordinator.data = {"collection_count": 0}
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyCollectionCountSensor(coordinator=mock_coordinator, server_name="Test Server")

        assert sensor.native_value == 0

    async def test_sensor_translation_key(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test collection count sensor has correct translation key."""
        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator
        from custom_components.embymedia.sensor import EmbyCollectionCountSensor

        mock_coordinator = MagicMock(spec=EmbyLibraryCoordinator)
        mock_coordinator.data = {"collection_count": 10}
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyCollectionCountSensor(coordinator=mock_coordinator, server_name="Test Server")

        assert sensor.translation_key == "collection_count"
