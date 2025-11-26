"""Tests for Emby remote platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.remote import RemoteEntityFeature
from homeassistant.core import HomeAssistant

from custom_components.embymedia.models import EmbySession


class TestEmbyRemoteEntity:
    """Test EmbyRemoteEntity class directly."""

    def test_remote_entity_unique_id(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test remote entity unique_id format."""
        from custom_components.embymedia.remote import EmbyRemoteEntity

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {"device-1": MagicMock()}
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_coordinator.get_session = MagicMock(return_value=MagicMock())

        entity = EmbyRemoteEntity(mock_coordinator, "device-1")

        assert entity.unique_id == "server-123_device-1_remote"

    def test_remote_entity_name_is_none(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test remote entity name is None (uses device name only).

        Phase 11: Removed redundant 'Remote' suffix.
        Entity ID becomes remote.{device_name} instead of remote.{device_name}_remote.
        """
        from custom_components.embymedia.remote import EmbyRemoteEntity

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {"device-1": MagicMock()}
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_coordinator.get_session = MagicMock(return_value=MagicMock())

        entity = EmbyRemoteEntity(mock_coordinator, "device-1")

        # _attr_name = None means entity uses device name only (no suffix)
        assert entity.name is None

    def test_remote_entity_is_on_when_session_exists(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test remote entity is_on returns True when session exists."""
        from custom_components.embymedia.remote import EmbyRemoteEntity

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
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_coordinator.get_session = MagicMock(return_value=mock_session)

        entity = EmbyRemoteEntity(mock_coordinator, "device-1")

        assert entity.is_on is True

    def test_remote_entity_is_on_when_session_missing(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test remote entity is_on returns False when session is missing."""
        from custom_components.embymedia.remote import EmbyRemoteEntity

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {}
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_coordinator.get_session = MagicMock(return_value=None)

        entity = EmbyRemoteEntity(mock_coordinator, "device-1")

        assert entity.is_on is False

    def test_remote_entity_available_when_session_exists(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test remote entity is available when session exists."""
        from custom_components.embymedia.remote import EmbyRemoteEntity

        mock_session = MagicMock()
        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {"device-1": mock_session}
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_coordinator.get_session = MagicMock(return_value=mock_session)

        entity = EmbyRemoteEntity(mock_coordinator, "device-1")

        assert entity.available is True

    def test_remote_entity_unavailable_when_session_missing(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test remote entity is unavailable when session is missing."""
        from custom_components.embymedia.remote import EmbyRemoteEntity

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {}
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_coordinator.get_session = MagicMock(return_value=None)

        entity = EmbyRemoteEntity(mock_coordinator, "device-1")

        assert entity.available is False

    def test_remote_entity_supported_features(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test remote entity has no special features (basic command sending)."""
        from custom_components.embymedia.remote import EmbyRemoteEntity

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {"device-1": MagicMock()}
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_coordinator.get_session = MagicMock(return_value=MagicMock())

        entity = EmbyRemoteEntity(mock_coordinator, "device-1")

        # No special features - just basic command sending
        assert entity.supported_features == RemoteEntityFeature(0)


class TestRemoteSendCommand:
    """Test sending remote commands."""

    @pytest.mark.asyncio
    async def test_send_command_single(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test send_command sends single command to Emby API."""
        from custom_components.embymedia.remote import EmbyRemoteEntity

        mock_session = EmbySession(
            session_id="session-1",
            device_id="device-1",
            device_name="Living Room TV",
            client_name="Emby Theater",
            supports_remote_control=True,
        )

        mock_client = MagicMock()
        mock_client.async_send_command = AsyncMock()

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {"device-1": mock_session}
        mock_coordinator.client = mock_client
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_coordinator.get_session = MagicMock(return_value=mock_session)

        entity = EmbyRemoteEntity(mock_coordinator, "device-1")

        await entity.async_send_command(["GoHome"])

        mock_client.async_send_command.assert_called_once_with(
            session_id="session-1",
            command="GoHome",
            args=None,
        )

    @pytest.mark.asyncio
    async def test_send_command_multiple(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test send_command sends multiple commands sequentially."""
        from custom_components.embymedia.remote import EmbyRemoteEntity

        mock_session = EmbySession(
            session_id="session-1",
            device_id="device-1",
            device_name="Living Room TV",
            client_name="Emby Theater",
            supports_remote_control=True,
        )

        mock_client = MagicMock()
        mock_client.async_send_command = AsyncMock()

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {"device-1": mock_session}
        mock_coordinator.client = mock_client
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_coordinator.get_session = MagicMock(return_value=mock_session)

        entity = EmbyRemoteEntity(mock_coordinator, "device-1")

        await entity.async_send_command(["MoveDown", "MoveDown", "Select"])

        assert mock_client.async_send_command.call_count == 3

    @pytest.mark.asyncio
    async def test_send_command_with_num_repeats(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test send_command respects num_repeats parameter."""
        from custom_components.embymedia.remote import EmbyRemoteEntity

        mock_session = EmbySession(
            session_id="session-1",
            device_id="device-1",
            device_name="Living Room TV",
            client_name="Emby Theater",
            supports_remote_control=True,
        )

        mock_client = MagicMock()
        mock_client.async_send_command = AsyncMock()

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {"device-1": mock_session}
        mock_coordinator.client = mock_client
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_coordinator.get_session = MagicMock(return_value=mock_session)

        entity = EmbyRemoteEntity(mock_coordinator, "device-1")

        await entity.async_send_command(["VolumeUp"], num_repeats=3)

        # Should be called 3 times
        assert mock_client.async_send_command.call_count == 3

    @pytest.mark.asyncio
    async def test_send_command_session_not_found(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test send_command handles missing session gracefully."""
        from custom_components.embymedia.remote import EmbyRemoteEntity

        mock_client = MagicMock()
        mock_client.async_send_command = AsyncMock()

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {}
        mock_coordinator.client = mock_client
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_coordinator.get_session = MagicMock(return_value=None)

        entity = EmbyRemoteEntity(mock_coordinator, "device-1")

        # Should not raise but also not call API
        await entity.async_send_command(["GoHome"])

        mock_client.async_send_command.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_command_handles_api_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test send_command handles API errors gracefully."""
        from custom_components.embymedia.remote import EmbyRemoteEntity

        mock_session = EmbySession(
            session_id="session-1",
            device_id="device-1",
            device_name="Living Room TV",
            client_name="Emby Theater",
            supports_remote_control=True,
        )

        mock_client = MagicMock()
        mock_client.async_send_command = AsyncMock(side_effect=Exception("API Error"))

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {"device-1": mock_session}
        mock_coordinator.client = mock_client
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_coordinator.get_session = MagicMock(return_value=mock_session)

        entity = EmbyRemoteEntity(mock_coordinator, "device-1")

        # Should not raise, just log error
        await entity.async_send_command(["GoHome"])

        mock_client.async_send_command.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_command_with_delay(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test send_command respects delay_secs parameter."""
        from custom_components.embymedia.remote import EmbyRemoteEntity

        mock_session = EmbySession(
            session_id="session-1",
            device_id="device-1",
            device_name="Living Room TV",
            client_name="Emby Theater",
            supports_remote_control=True,
        )

        mock_client = MagicMock()
        mock_client.async_send_command = AsyncMock()

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {"device-1": mock_session}
        mock_coordinator.client = mock_client
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_coordinator.get_session = MagicMock(return_value=mock_session)

        entity = EmbyRemoteEntity(mock_coordinator, "device-1")

        # delay_secs is supported but we don't need to actually wait in tests
        await entity.async_send_command(["MoveDown", "Select"], delay_secs=0.1)

        assert mock_client.async_send_command.call_count == 2


class TestRemoteTurnOnOff:
    """Test remote turn on/off functionality."""

    @pytest.mark.asyncio
    async def test_turn_on_does_nothing(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test turn_on is a no-op (Emby clients don't have power control)."""
        from custom_components.embymedia.remote import EmbyRemoteEntity

        mock_session = EmbySession(
            session_id="session-1",
            device_id="device-1",
            device_name="Living Room TV",
            client_name="Emby Theater",
            supports_remote_control=True,
        )

        mock_client = MagicMock()
        mock_client.async_send_command = AsyncMock()

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {"device-1": mock_session}
        mock_coordinator.client = mock_client
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_coordinator.get_session = MagicMock(return_value=mock_session)

        entity = EmbyRemoteEntity(mock_coordinator, "device-1")

        # Should not raise - just a no-op
        await entity.async_turn_on()

        # No commands sent
        mock_client.async_send_command.assert_not_called()

    @pytest.mark.asyncio
    async def test_turn_off_does_nothing(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test turn_off is a no-op (Emby clients don't have power control)."""
        from custom_components.embymedia.remote import EmbyRemoteEntity

        mock_session = EmbySession(
            session_id="session-1",
            device_id="device-1",
            device_name="Living Room TV",
            client_name="Emby Theater",
            supports_remote_control=True,
        )

        mock_client = MagicMock()
        mock_client.async_send_command = AsyncMock()

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {"device-1": mock_session}
        mock_coordinator.client = mock_client
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())
        mock_coordinator.get_session = MagicMock(return_value=mock_session)

        entity = EmbyRemoteEntity(mock_coordinator, "device-1")

        # Should not raise - just a no-op
        await entity.async_turn_off()

        # No commands sent
        mock_client.async_send_command.assert_not_called()


class TestAsyncSetupEntry:
    """Test async_setup_entry function."""

    @pytest.mark.asyncio
    async def test_setup_entry_adds_entities_for_sessions(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test setup_entry adds entities for existing sessions."""
        from custom_components.embymedia.remote import async_setup_entry

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
        assert added_entities[0].unique_id == "server-123_device-1_remote"

    @pytest.mark.asyncio
    async def test_setup_entry_no_entities_when_no_sessions(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test setup_entry adds no entities when no sessions."""
        from custom_components.embymedia.remote import async_setup_entry

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = {}
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
        from custom_components.embymedia.remote import async_setup_entry

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.data = None  # Data is None
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
        from custom_components.embymedia.remote import async_setup_entry

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
