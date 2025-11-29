"""Tests for Plugin Count sensor (Phase 20)."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.components.sensor import SensorStateClass
from homeassistant.core import HomeAssistant


class TestEmbyPluginCountSensor:
    """Test EmbyPluginCountSensor class."""

    def test_sensor_unique_id(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test sensor unique_id format."""
        from custom_components.embymedia.sensor import EmbyPluginCountSensor

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        sensor = EmbyPluginCountSensor(mock_coordinator)

        assert sensor.unique_id == "server-123_plugins"

    def test_sensor_name(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test sensor name is 'Plugins'."""
        from custom_components.embymedia.sensor import EmbyPluginCountSensor

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        sensor = EmbyPluginCountSensor(mock_coordinator)

        assert sensor.name == "Plugins"

    def test_sensor_state_class(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test sensor has MEASUREMENT state class."""
        from custom_components.embymedia.sensor import EmbyPluginCountSensor

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        sensor = EmbyPluginCountSensor(mock_coordinator)

        assert sensor.state_class == SensorStateClass.MEASUREMENT

    def test_sensor_native_value_with_plugins(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test sensor native value returns plugin count."""
        from custom_components.embymedia.sensor import EmbyPluginCountSensor

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {
            "plugin_count": 5,
            "plugins": [
                {"Name": "Plugin 1", "Version": "1.0", "Id": "id1"},
                {"Name": "Plugin 2", "Version": "2.0", "Id": "id2"},
                {"Name": "Plugin 3", "Version": "3.0", "Id": "id3"},
                {"Name": "Plugin 4", "Version": "4.0", "Id": "id4"},
                {"Name": "Plugin 5", "Version": "5.0", "Id": "id5"},
            ],
        }
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        sensor = EmbyPluginCountSensor(mock_coordinator)

        assert sensor.native_value == 5

    def test_sensor_native_value_no_plugins(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test sensor native value returns 0 when no plugins."""
        from custom_components.embymedia.sensor import EmbyPluginCountSensor

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {
            "plugin_count": 0,
            "plugins": [],
        }
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        sensor = EmbyPluginCountSensor(mock_coordinator)

        assert sensor.native_value == 0

    def test_sensor_native_value_no_data(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test sensor native value returns 0 when no data."""
        from custom_components.embymedia.sensor import EmbyPluginCountSensor

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = None
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        sensor = EmbyPluginCountSensor(mock_coordinator)

        assert sensor.native_value == 0

    def test_sensor_extra_state_attributes(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test sensor extra_state_attributes returns plugin list."""
        from custom_components.embymedia.sensor import EmbyPluginCountSensor

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {
            "plugins": [
                {"Name": "Backup & Restore", "Version": "1.8.2.0", "Id": "plugin-1"},
                {"Name": "DLNA", "Version": "1.5.4.0", "Id": "plugin-2"},
            ],
        }
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        sensor = EmbyPluginCountSensor(mock_coordinator)
        attrs = sensor.extra_state_attributes

        assert "plugins" in attrs
        assert len(attrs["plugins"]) == 2
        assert attrs["plugins"][0]["name"] == "Backup & Restore"
        assert attrs["plugins"][0]["version"] == "1.8.2.0"
        assert attrs["plugins"][1]["name"] == "DLNA"
        assert attrs["plugins"][1]["version"] == "1.5.4.0"

    def test_sensor_extra_state_attributes_no_data(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test sensor extra_state_attributes returns empty list when no data."""
        from custom_components.embymedia.sensor import EmbyPluginCountSensor

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = None
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        sensor = EmbyPluginCountSensor(mock_coordinator)
        attrs = sensor.extra_state_attributes

        assert attrs == {"plugins": []}

    def test_sensor_icon(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test sensor has puzzle icon."""
        from custom_components.embymedia.sensor import EmbyPluginCountSensor

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        sensor = EmbyPluginCountSensor(mock_coordinator)

        assert sensor.icon == "mdi:puzzle"

    def test_sensor_device_info(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test sensor device info."""
        from custom_components.embymedia.const import CONF_PREFIX_SENSOR, DOMAIN
        from custom_components.embymedia.sensor import EmbyPluginCountSensor

        mock_config_entry = MagicMock()
        mock_config_entry.options = {CONF_PREFIX_SENSOR: True}

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.config_entry = mock_config_entry
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        sensor = EmbyPluginCountSensor(mock_coordinator)
        device_info = sensor.device_info

        assert device_info is not None
        assert (DOMAIN, "server-123") in device_info["identifiers"]
