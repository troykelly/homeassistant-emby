"""Tests for Phase 12 sensor configuration constants."""

from __future__ import annotations


def test_sensor_config_constants_exist() -> None:
    """Test that sensor configuration constants are defined."""
    from custom_components.embymedia.const import (
        CONF_ENABLE_LIBRARY_SENSORS,
        CONF_ENABLE_USER_SENSORS,
        CONF_LIBRARY_SCAN_INTERVAL,
    )

    assert CONF_ENABLE_LIBRARY_SENSORS == "enable_library_sensors"
    assert CONF_ENABLE_USER_SENSORS == "enable_user_sensors"
    assert CONF_LIBRARY_SCAN_INTERVAL == "library_scan_interval"


def test_sensor_config_defaults_exist() -> None:
    """Test that sensor configuration defaults are defined."""
    from custom_components.embymedia.const import (
        DEFAULT_ENABLE_LIBRARY_SENSORS,
        DEFAULT_ENABLE_USER_SENSORS,
        DEFAULT_LIBRARY_SCAN_INTERVAL,
    )

    # Library sensors enabled by default
    assert DEFAULT_ENABLE_LIBRARY_SENSORS is True
    # User sensors enabled by default
    assert DEFAULT_ENABLE_USER_SENSORS is True
    # Default scan interval is 1 hour (3600 seconds)
    assert DEFAULT_LIBRARY_SCAN_INTERVAL == 3600


def test_sensor_platforms_added() -> None:
    """Test that sensor and binary_sensor platforms are added to PLATFORMS."""
    from homeassistant.const import Platform

    from custom_components.embymedia.const import PLATFORMS

    assert Platform.SENSOR in PLATFORMS
    assert Platform.BINARY_SENSOR in PLATFORMS


def test_server_scan_interval_constant() -> None:
    """Test server coordinator scan interval constant."""
    from custom_components.embymedia.const import (
        DEFAULT_SERVER_SCAN_INTERVAL,
    )

    # Server info polled every 5 minutes (300 seconds)
    assert DEFAULT_SERVER_SCAN_INTERVAL == 300
