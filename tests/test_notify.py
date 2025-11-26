"""Tests for Emby notify platform."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.notify import NotifyEntityFeature
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.embymedia.const import DOMAIN
from custom_components.embymedia.exceptions import EmbyError
from custom_components.embymedia.models import EmbySession

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "emby.local",
            "port": 8096,
            "api_key": "test-key",
        },
        unique_id="server-123",
    )


@pytest.fixture
def mock_server_info() -> dict:
    """Create mock server info."""
    return {
        "Id": "server-123",
        "ServerName": "Test Server",
        "Version": "4.9.2.0",
    }


@pytest.fixture
def mock_session_data() -> EmbySession:
    """Create mock session."""
    return EmbySession(
        session_id="session-1",
        device_id="device-1",
        device_name="Living Room TV",
        client_name="Emby Theater",
        supports_remote_control=True,
    )


class TestNotifyPlatformSetup:
    """Test notify platform setup via async_setup_entry function."""

    # Note: Full integration tests (with mocked coordinator and client setup)
    # are complex due to Home Assistant's entity platform registration.
    # The async_setup_entry tests in TestAsyncSetupEntry class below
    # provide comprehensive coverage of the platform setup logic.
    pass


class TestEmbyNotifyEntity:
    """Test EmbyNotifyEntity class directly."""

    def test_notify_entity_supported_features(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test notify entity supports title feature."""
        from custom_components.embymedia.notify import EmbyNotifyEntity

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {"device-1": MagicMock()}
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        entity = EmbyNotifyEntity(mock_coordinator, "device-1")

        assert entity.supported_features & NotifyEntityFeature.TITLE

    def test_notify_entity_unique_id(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test notify entity unique_id format."""
        from custom_components.embymedia.notify import EmbyNotifyEntity

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {"device-1": MagicMock()}
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        entity = EmbyNotifyEntity(mock_coordinator, "device-1")

        assert entity.unique_id == "server-123_device-1_notify"

    def test_notify_entity_available_when_session_exists(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test notify entity is available when session exists."""
        from custom_components.embymedia.notify import EmbyNotifyEntity

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {"device-1": MagicMock()}
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        entity = EmbyNotifyEntity(mock_coordinator, "device-1")

        assert entity.available is True

    def test_notify_entity_unavailable_when_session_missing(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test notify entity is unavailable when session is missing."""
        from custom_components.embymedia.notify import EmbyNotifyEntity

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {}  # No sessions
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_coordinator.get_session = MagicMock(return_value=None)

        entity = EmbyNotifyEntity(mock_coordinator, "device-1")

        assert entity.available is False

    def test_notify_entity_unavailable_when_data_none(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test notify entity is unavailable when coordinator data is None."""
        from custom_components.embymedia.notify import EmbyNotifyEntity

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = None
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_coordinator.get_session = MagicMock(return_value=None)

        entity = EmbyNotifyEntity(mock_coordinator, "device-1")

        assert entity.available is False


class TestNotifySendMessage:
    """Test sending notifications."""

    @pytest.mark.asyncio
    async def test_send_message_calls_emby_api(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test send_message calls Emby API correctly."""
        from custom_components.embymedia.notify import EmbyNotifyEntity

        mock_session = EmbySession(
            session_id="session-1",
            device_id="device-1",
            device_name="Living Room TV",
            client_name="Emby Theater",
            supports_remote_control=True,
        )

        mock_client = MagicMock()
        mock_client.async_send_message = AsyncMock()

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {"device-1": mock_session}
        mock_coordinator.client = mock_client
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_coordinator.get_session = MagicMock(return_value=mock_session)

        entity = EmbyNotifyEntity(mock_coordinator, "device-1")

        await entity.async_send_message(
            message="Test notification",
            title="Test Title",
        )

        mock_client.async_send_message.assert_called_once_with(
            session_id="session-1",
            text="Test notification",
            header="Test Title",
            timeout_ms=5000,
        )

    @pytest.mark.asyncio
    async def test_send_message_without_title(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test send_message works without title."""
        from custom_components.embymedia.notify import EmbyNotifyEntity

        mock_session = EmbySession(
            session_id="session-1",
            device_id="device-1",
            device_name="Living Room TV",
            client_name="Emby Theater",
            supports_remote_control=True,
        )

        mock_client = MagicMock()
        mock_client.async_send_message = AsyncMock()

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {"device-1": mock_session}
        mock_coordinator.client = mock_client
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_coordinator.get_session = MagicMock(return_value=mock_session)

        entity = EmbyNotifyEntity(mock_coordinator, "device-1")

        await entity.async_send_message(message="Test notification")

        mock_client.async_send_message.assert_called_once_with(
            session_id="session-1",
            text="Test notification",
            header="",
            timeout_ms=5000,
        )

    @pytest.mark.asyncio
    async def test_send_message_session_not_found(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test send_message handles missing session gracefully."""
        from custom_components.embymedia.notify import EmbyNotifyEntity

        mock_client = MagicMock()
        mock_client.async_send_message = AsyncMock()

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {}  # Session gone
        mock_coordinator.client = mock_client
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_coordinator.get_session = MagicMock(return_value=None)

        entity = EmbyNotifyEntity(mock_coordinator, "device-1")

        # Should not raise but also not call API
        await entity.async_send_message(message="Test notification")

        mock_client.async_send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_message_data_none(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test send_message handles coordinator data being None."""
        from custom_components.embymedia.notify import EmbyNotifyEntity

        mock_client = MagicMock()
        mock_client.async_send_message = AsyncMock()

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = None  # Data is None
        mock_coordinator.client = mock_client
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_coordinator.get_session = MagicMock(return_value=None)

        entity = EmbyNotifyEntity(mock_coordinator, "device-1")

        # Should not raise but also not call API
        await entity.async_send_message(message="Test notification")

        mock_client.async_send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_message_handles_api_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test send_message handles API errors gracefully."""
        from custom_components.embymedia.notify import EmbyNotifyEntity

        mock_session = EmbySession(
            session_id="session-1",
            device_id="device-1",
            device_name="Living Room TV",
            client_name="Emby Theater",
            supports_remote_control=True,
        )

        mock_client = MagicMock()
        mock_client.async_send_message = AsyncMock(side_effect=EmbyError("API Error"))

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {"device-1": mock_session}
        mock_coordinator.client = mock_client
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_coordinator.get_session = MagicMock(return_value=mock_session)

        entity = EmbyNotifyEntity(mock_coordinator, "device-1")

        # Should not raise, just log error
        await entity.async_send_message(message="Test notification")

        # API was called (and failed)
        mock_client.async_send_message.assert_called_once()


class TestNotifyEntityName:
    """Test notify entity naming."""

    def test_notify_entity_name_is_none(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test notify entity name is None (uses device name only).

        Phase 11: Removed redundant 'Notification' suffix.
        Entity ID becomes notify.{device_name} instead of notify.{device_name}_notification.
        """
        from custom_components.embymedia.notify import EmbyNotifyEntity

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {"device-1": MagicMock()}
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        entity = EmbyNotifyEntity(mock_coordinator, "device-1")

        # _attr_name = None means entity uses device name only (no suffix)
        assert entity.name is None


class TestAsyncSetupEntry:
    """Test async_setup_entry function."""

    @pytest.mark.asyncio
    async def test_setup_entry_adds_entities_for_sessions(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test setup_entry adds entities for existing sessions."""
        from custom_components.embymedia.notify import async_setup_entry

        mock_session = EmbySession(
            session_id="session-1",
            device_id="device-1",
            device_name="Living Room TV",
            client_name="Emby Theater",
            supports_remote_control=True,
        )

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {"device-1": mock_session}
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        mock_entry = MagicMock()
        mock_entry.runtime_data = mock_coordinator
        mock_entry.async_on_unload = MagicMock()

        added_entities: list = []

        def capture_entities(entities: list) -> None:
            added_entities.extend(entities)

        await async_setup_entry(hass, mock_entry, capture_entities)

        assert len(added_entities) == 1
        assert added_entities[0].unique_id == "server-123_device-1_notify"

    @pytest.mark.asyncio
    async def test_setup_entry_no_entities_when_no_sessions(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test setup_entry adds no entities when no sessions."""
        from custom_components.embymedia.notify import async_setup_entry

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {}  # No sessions
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        mock_entry = MagicMock()
        mock_entry.runtime_data = mock_coordinator
        mock_entry.async_on_unload = MagicMock()

        added_entities: list = []

        def capture_entities(entities: list) -> None:
            added_entities.extend(entities)

        await async_setup_entry(hass, mock_entry, capture_entities)

        assert len(added_entities) == 0

    @pytest.mark.asyncio
    async def test_setup_entry_no_entities_when_data_none(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test setup_entry adds no entities when data is None."""
        from custom_components.embymedia.notify import async_setup_entry

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = None
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        mock_entry = MagicMock()
        mock_entry.runtime_data = mock_coordinator
        mock_entry.async_on_unload = MagicMock()

        added_entities: list = []

        def capture_entities(entities: list) -> None:
            added_entities.extend(entities)

        await async_setup_entry(hass, mock_entry, capture_entities)

        assert len(added_entities) == 0

    @pytest.mark.asyncio
    async def test_setup_entry_registers_listener(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test setup_entry registers coordinator listener."""
        from custom_components.embymedia.notify import async_setup_entry

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {}
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        mock_entry = MagicMock()
        mock_entry.runtime_data = mock_coordinator
        mock_entry.async_on_unload = MagicMock()

        await async_setup_entry(hass, mock_entry, MagicMock())

        mock_coordinator.async_add_listener.assert_called_once()
        mock_entry.async_on_unload.assert_called_once()
