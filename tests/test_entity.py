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
    session.app_version = "4.8.0.0"
    return session


@pytest.fixture
def mock_coordinator(hass: HomeAssistant, mock_session: MagicMock) -> MagicMock:
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.server_id = "server-123"
    coordinator.server_name = "My Emby Server"
    coordinator.last_update_success = True
    coordinator.data = {"device-abc-123": mock_session}
    coordinator.get_session = MagicMock(return_value=mock_session)
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
    """Test EmbyEntity device info."""

    def test_device_info_with_session(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Test device info when session is available."""
        from custom_components.embymedia.entity import EmbyEntity

        mock_coordinator.get_session.return_value = mock_session

        entity = EmbyEntity(
            coordinator=mock_coordinator,
            device_id="device-abc-123",
        )

        device_info = entity.device_info

        assert device_info["identifiers"] == {(DOMAIN, "device-abc-123")}
        assert device_info["name"] == "Living Room TV"
        assert device_info["manufacturer"] == "Emby"
        assert device_info["model"] == "Emby Theater"
        assert device_info["sw_version"] == "4.8.0.0"
        assert device_info["via_device"] == (DOMAIN, "server-123")

    def test_device_info_without_session(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test device info fallback when session is not available."""
        from custom_components.embymedia.entity import EmbyEntity

        mock_coordinator.get_session.return_value = None

        entity = EmbyEntity(
            coordinator=mock_coordinator,
            device_id="device-abc-123",
        )

        device_info = entity.device_info

        assert device_info["identifiers"] == {(DOMAIN, "device-abc-123")}
        assert device_info["name"] == "Emby Client device-a"
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
