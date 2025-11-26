"""Tests for Emby base entity."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.embymedia.const import DOMAIN

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock EmbySession."""
    session = MagicMock(spec_set=["device_id", "device_name", "client_name", "app_version"])
    session.device_id = "device-abc-123"
    session.device_name = "Living Room TV"
    session.client_name = "Emby Theater"
    session.app_version = "4.9.2.0"
    return session


@pytest.fixture
def mock_coordinator(hass: HomeAssistant, mock_session: MagicMock) -> MagicMock:
    """Create a mock coordinator."""
    from custom_components.embymedia.const import CONF_PREFIX_MEDIA_PLAYER

    coordinator = MagicMock()
    coordinator.server_id = "server-123"
    coordinator.server_name = "My Emby Server"
    coordinator.last_update_success = True
    coordinator.data = {"device-abc-123": mock_session}
    coordinator.get_session = MagicMock(return_value=mock_session)
    # Phase 11: Add config_entry with default prefix settings (enabled by default)
    mock_config_entry = MagicMock()
    mock_config_entry.options = {CONF_PREFIX_MEDIA_PLAYER: True}
    coordinator.config_entry = mock_config_entry
    return coordinator


class TestEmbyEntityInit:
    """Test EmbyEntity initialization."""

    def test_entity_init(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test entity initializes with correct attributes."""
        from custom_components.embymedia.entity import EmbyEntity

        entity = EmbyEntity(
            coordinator=mock_coordinator,
            device_id="device-abc-123",
        )

        assert entity._device_id == "device-abc-123"
        assert entity.coordinator is mock_coordinator

    def test_entity_has_entity_name_attribute(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test entity has _attr_has_entity_name = True."""
        from custom_components.embymedia.entity import EmbyEntity

        entity = EmbyEntity(
            coordinator=mock_coordinator,
            device_id="device-abc-123",
        )

        assert entity._attr_has_entity_name is True


class TestEmbyEntitySession:
    """Test EmbyEntity session property."""

    def test_session_returns_session_from_coordinator(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Test session property returns session from coordinator."""
        from custom_components.embymedia.entity import EmbyEntity

        entity = EmbyEntity(
            coordinator=mock_coordinator,
            device_id="device-abc-123",
        )

        assert entity.session is mock_session
        mock_coordinator.get_session.assert_called_once_with("device-abc-123")


class TestEmbyEntityAvailability:
    """Test EmbyEntity availability."""

    def test_available_when_session_exists_and_update_success(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Test entity is available when session exists and coordinator succeeded."""
        from custom_components.embymedia.entity import EmbyEntity

        mock_coordinator.last_update_success = True
        mock_coordinator.get_session.return_value = mock_session

        entity = EmbyEntity(
            coordinator=mock_coordinator,
            device_id="device-abc-123",
        )

        assert entity.available is True

    def test_unavailable_when_session_missing(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test entity is unavailable when session doesn't exist."""
        from custom_components.embymedia.entity import EmbyEntity

        mock_coordinator.last_update_success = True
        mock_coordinator.get_session.return_value = None

        entity = EmbyEntity(
            coordinator=mock_coordinator,
            device_id="device-xyz-999",
        )

        assert entity.available is False

    def test_unavailable_when_coordinator_failed(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Test entity is unavailable when coordinator failed."""
        from custom_components.embymedia.entity import EmbyEntity

        mock_coordinator.last_update_success = False
        mock_coordinator.get_session.return_value = mock_session

        entity = EmbyEntity(
            coordinator=mock_coordinator,
            device_id="device-abc-123",
        )

        assert entity.available is False


class TestEmbyEntityDeviceInfo:
    """Test EmbyEntity device info (Phase 11 - with prefix support)."""

    def test_device_info_with_session_and_prefix_enabled(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Test device info with 'Emby' prefix when session is available and prefix enabled."""
        from custom_components.embymedia.const import CONF_PREFIX_MEDIA_PLAYER
        from custom_components.embymedia.entity import EmbyEntity

        # Ensure prefix is enabled (default)
        mock_coordinator.config_entry.options = {CONF_PREFIX_MEDIA_PLAYER: True}
        mock_coordinator.get_session.return_value = mock_session

        entity = EmbyEntity(
            coordinator=mock_coordinator,
            device_id="device-abc-123",
        )

        device_info = entity.device_info

        assert device_info["identifiers"] == {(DOMAIN, "device-abc-123")}
        assert device_info["name"] == "Emby Living Room TV"  # Phase 11: Prefixed
        assert device_info["manufacturer"] == "Emby"
        assert device_info["model"] == "Emby Theater"
        assert device_info["sw_version"] == "4.9.2.0"
        assert device_info["via_device"] == (DOMAIN, "server-123")

    def test_device_info_with_session_and_prefix_disabled(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Test device info without prefix when prefix disabled."""
        from custom_components.embymedia.const import CONF_PREFIX_MEDIA_PLAYER
        from custom_components.embymedia.entity import EmbyEntity

        # Disable prefix
        mock_coordinator.config_entry.options = {CONF_PREFIX_MEDIA_PLAYER: False}
        mock_coordinator.get_session.return_value = mock_session

        entity = EmbyEntity(
            coordinator=mock_coordinator,
            device_id="device-abc-123",
        )

        device_info = entity.device_info

        assert device_info["identifiers"] == {(DOMAIN, "device-abc-123")}
        assert device_info["name"] == "Living Room TV"  # No prefix
        assert device_info["manufacturer"] == "Emby"
        assert device_info["model"] == "Emby Theater"
        assert device_info["sw_version"] == "4.9.2.0"
        assert device_info["via_device"] == (DOMAIN, "server-123")

    def test_device_info_without_session(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test device info fallback when session is not available."""
        from custom_components.embymedia.const import CONF_PREFIX_MEDIA_PLAYER
        from custom_components.embymedia.entity import EmbyEntity

        mock_coordinator.config_entry.options = {CONF_PREFIX_MEDIA_PLAYER: True}
        mock_coordinator.get_session.return_value = None

        entity = EmbyEntity(
            coordinator=mock_coordinator,
            device_id="device-abc-123",
        )

        device_info = entity.device_info

        assert device_info["identifiers"] == {(DOMAIN, "device-abc-123")}
        assert device_info["name"] == "Emby Client device-a"  # Fallback with prefix
        assert device_info["manufacturer"] == "Emby"
        assert "model" not in device_info
        assert "sw_version" not in device_info
        assert device_info["via_device"] == (DOMAIN, "server-123")


class TestEmbyEntityUniqueId:
    """Test EmbyEntity unique_id."""

    def test_unique_id_format(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test unique_id combines server_id and device_id."""
        from custom_components.embymedia.entity import EmbyEntity

        entity = EmbyEntity(
            coordinator=mock_coordinator,
            device_id="device-abc-123",
        )

        assert entity.unique_id == "server-123_device-abc-123"


class TestEmbyEntityDeviceNameHelper:
    """Test _get_device_name helper for entity prefix support (Phase 11)."""

    def test_get_device_name_with_prefix_enabled(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Test device name prefixed with 'Emby' when toggle is ON."""
        from custom_components.embymedia.const import (
            CONF_PREFIX_MEDIA_PLAYER,
            DEFAULT_PREFIX_MEDIA_PLAYER,
        )
        from custom_components.embymedia.entity import EmbyEntity

        # Setup mock config entry with prefix enabled
        mock_config_entry = MagicMock()
        mock_config_entry.options = {CONF_PREFIX_MEDIA_PLAYER: True}
        mock_coordinator.config_entry = mock_config_entry
        mock_coordinator.get_session.return_value = mock_session

        entity = EmbyEntity(
            coordinator=mock_coordinator,
            device_id="device-abc-123",
        )

        result = entity._get_device_name(CONF_PREFIX_MEDIA_PLAYER, DEFAULT_PREFIX_MEDIA_PLAYER)

        assert result == "Emby Living Room TV"

    def test_get_device_name_with_prefix_disabled(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Test device name without prefix when toggle is OFF."""
        from custom_components.embymedia.const import (
            CONF_PREFIX_MEDIA_PLAYER,
            DEFAULT_PREFIX_MEDIA_PLAYER,
        )
        from custom_components.embymedia.entity import EmbyEntity

        # Setup mock config entry with prefix disabled
        mock_config_entry = MagicMock()
        mock_config_entry.options = {CONF_PREFIX_MEDIA_PLAYER: False}
        mock_coordinator.config_entry = mock_config_entry
        mock_coordinator.get_session.return_value = mock_session

        entity = EmbyEntity(
            coordinator=mock_coordinator,
            device_id="device-abc-123",
        )

        result = entity._get_device_name(CONF_PREFIX_MEDIA_PLAYER, DEFAULT_PREFIX_MEDIA_PLAYER)

        assert result == "Living Room TV"

    def test_get_device_name_uses_default_when_option_missing(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Test device name uses default when option not set."""
        from custom_components.embymedia.const import (
            CONF_PREFIX_MEDIA_PLAYER,
            DEFAULT_PREFIX_MEDIA_PLAYER,
        )
        from custom_components.embymedia.entity import EmbyEntity

        # Setup mock config entry with no prefix option (uses default=True)
        mock_config_entry = MagicMock()
        mock_config_entry.options = {}  # No options set
        mock_coordinator.config_entry = mock_config_entry
        mock_coordinator.get_session.return_value = mock_session

        entity = EmbyEntity(
            coordinator=mock_coordinator,
            device_id="device-abc-123",
        )

        result = entity._get_device_name(CONF_PREFIX_MEDIA_PLAYER, DEFAULT_PREFIX_MEDIA_PLAYER)

        # Default is True, so should be prefixed
        assert result == "Emby Living Room TV"

    def test_get_device_name_fallback_when_session_none(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test fallback device name when session is None."""
        from custom_components.embymedia.const import (
            CONF_PREFIX_MEDIA_PLAYER,
            DEFAULT_PREFIX_MEDIA_PLAYER,
        )
        from custom_components.embymedia.entity import EmbyEntity

        # Setup mock config entry with prefix enabled
        mock_config_entry = MagicMock()
        mock_config_entry.options = {CONF_PREFIX_MEDIA_PLAYER: True}
        mock_coordinator.config_entry = mock_config_entry
        mock_coordinator.get_session.return_value = None

        entity = EmbyEntity(
            coordinator=mock_coordinator,
            device_id="device-abc-123",
        )

        result = entity._get_device_name(CONF_PREFIX_MEDIA_PLAYER, DEFAULT_PREFIX_MEDIA_PLAYER)

        # Should use fallback name (first 8 chars of device ID)
        assert result == "Emby Client device-a"

    def test_get_device_name_fallback_without_prefix(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test fallback device name without prefix when toggle is OFF."""
        from custom_components.embymedia.const import (
            CONF_PREFIX_MEDIA_PLAYER,
            DEFAULT_PREFIX_MEDIA_PLAYER,
        )
        from custom_components.embymedia.entity import EmbyEntity

        # Setup mock config entry with prefix disabled
        mock_config_entry = MagicMock()
        mock_config_entry.options = {CONF_PREFIX_MEDIA_PLAYER: False}
        mock_coordinator.config_entry = mock_config_entry
        mock_coordinator.get_session.return_value = None

        entity = EmbyEntity(
            coordinator=mock_coordinator,
            device_id="device-abc-123",
        )

        result = entity._get_device_name(CONF_PREFIX_MEDIA_PLAYER, DEFAULT_PREFIX_MEDIA_PLAYER)

        # Should use fallback name without prefix
        assert result == "Client device-a"
