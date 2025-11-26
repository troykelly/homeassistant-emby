"""Comprehensive tests for Emby services to achieve full coverage."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import ATTR_DEVICE_ID, ATTR_ENTITY_ID, CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.embymedia.const import (
    CONF_API_KEY,
    CONF_VERIFY_SSL,
    DOMAIN,
)
from custom_components.embymedia.services import (
    _get_coordinator_for_entity,
    _get_entity_ids_from_call,
    _get_session_id_for_entity,
    _get_user_id_for_entity,
    _validate_emby_id,
)


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "emby.local",
            CONF_PORT: 8096,
            CONF_SSL: False,
            CONF_API_KEY: "test-api-key",
            CONF_VERIFY_SSL: True,
        },
        unique_id="test-server-id",
    )


class TestGetEntityIdsFromCall:
    """Tests for _get_entity_ids_from_call helper."""

    @pytest.mark.asyncio
    async def test_entity_id_as_list(self, hass: HomeAssistant) -> None:
        """Test getting entity IDs from list."""
        call = MagicMock(spec=ServiceCall)
        call.data = {ATTR_ENTITY_ID: ["media_player.test1", "media_player.test2"]}

        result = _get_entity_ids_from_call(hass, call)
        assert result == ["media_player.test1", "media_player.test2"]

    @pytest.mark.asyncio
    async def test_entity_id_as_string(self, hass: HomeAssistant) -> None:
        """Test getting entity ID from single string."""
        call = MagicMock(spec=ServiceCall)
        call.data = {ATTR_ENTITY_ID: "media_player.single"}

        result = _get_entity_ids_from_call(hass, call)
        assert result == ["media_player.single"]

    @pytest.mark.asyncio
    async def test_device_id_as_string(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test getting entity IDs from device_id as string."""
        mock_config_entry.add_to_hass(hass)

        device_reg = dr.async_get(hass)
        entity_reg = er.async_get(hass)

        # Create a device
        device = device_reg.async_get_or_create(
            config_entry_id=mock_config_entry.entry_id,
            identifiers={(DOMAIN, "test-device")},
            name="Test Device",
        )

        # Create an entity for the device
        entity_reg.async_get_or_create(
            "media_player",
            DOMAIN,
            "test-device-entity",
            config_entry=mock_config_entry,
            device_id=device.id,
        )

        call = MagicMock(spec=ServiceCall)
        call.data = {ATTR_DEVICE_ID: device.id}  # String, not list

        result = _get_entity_ids_from_call(hass, call)
        assert len(result) == 1
        assert "test_device_entity" in result[0]

    @pytest.mark.asyncio
    async def test_device_id_not_found(self, hass: HomeAssistant) -> None:
        """Test error when device_id not found."""
        call = MagicMock(spec=ServiceCall)
        call.data = {ATTR_DEVICE_ID: ["nonexistent-device"]}

        with pytest.raises(ServiceValidationError) as exc_info:
            _get_entity_ids_from_call(hass, call)

        assert "Device nonexistent-device not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_no_targets_provided(self, hass: HomeAssistant) -> None:
        """Test error when no targets provided."""
        call = MagicMock(spec=ServiceCall)
        call.data = {}

        with pytest.raises(ServiceValidationError) as exc_info:
            _get_entity_ids_from_call(hass, call)

        assert "No valid targets provided" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_device_without_emby_entities(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test device that exists but has no Emby entities."""
        mock_config_entry.add_to_hass(hass)

        device_reg = dr.async_get(hass)
        entity_reg = er.async_get(hass)

        # Create a device
        device = device_reg.async_get_or_create(
            config_entry_id=mock_config_entry.entry_id,
            identifiers={(DOMAIN, "device-no-entities")},
            name="Device Without Entities",
        )

        # Create an entity for a DIFFERENT domain
        entity_reg.async_get_or_create(
            "light",
            "some_other_domain",
            "other-entity",
            config_entry=mock_config_entry,
            device_id=device.id,
        )

        call = MagicMock(spec=ServiceCall)
        call.data = {ATTR_DEVICE_ID: [device.id]}

        with pytest.raises(ServiceValidationError):
            _get_entity_ids_from_call(hass, call)


class TestGetCoordinatorForEntity:
    """Tests for _get_coordinator_for_entity helper."""

    @pytest.mark.asyncio
    async def test_entity_not_found(self, hass: HomeAssistant) -> None:
        """Test error when entity not found."""
        with pytest.raises(HomeAssistantError) as exc_info:
            _get_coordinator_for_entity(hass, "media_player.nonexistent")

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_entity_wrong_platform(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test error when entity is not an Emby entity."""
        mock_config_entry.add_to_hass(hass)
        entity_reg = er.async_get(hass)

        # Create an entity for a different platform
        entry = entity_reg.async_get_or_create(
            "media_player",
            "other_platform",
            "other-entity",
        )

        with pytest.raises(HomeAssistantError) as exc_info:
            _get_coordinator_for_entity(hass, entry.entity_id)

        assert "not an Emby entity" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_entity_no_config_entry(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test error when entity has no config entry."""
        entity_reg = er.async_get(hass)

        # Create an entity without a config entry
        entry = entity_reg.async_get_or_create(
            "media_player",
            DOMAIN,
            "orphan-entity",
        )

        with pytest.raises(HomeAssistantError) as exc_info:
            _get_coordinator_for_entity(hass, entry.entity_id)

        assert "has no config entry" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_config_entry_not_found(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test error when config entry not found."""
        mock_config_entry.add_to_hass(hass)
        entity_reg = er.async_get(hass)

        # Create an entity with a valid config entry
        entry = entity_reg.async_get_or_create(
            "media_player",
            DOMAIN,
            "orphan-entity-for-config-test",
            config_entry=mock_config_entry,
        )

        # Mock async_get_entry to return None (simulating stale config entry reference)
        with (
            patch.object(hass.config_entries, "async_get_entry", return_value=None),
            pytest.raises(HomeAssistantError) as exc_info,
        ):
            _get_coordinator_for_entity(hass, entry.entity_id)

        assert "Config entry" in str(exc_info.value) and "not found" in str(exc_info.value)


class TestGetSessionIdForEntity:
    """Tests for _get_session_id_for_entity helper."""

    @pytest.mark.asyncio
    async def test_entity_not_found(self, hass: HomeAssistant) -> None:
        """Test returns None when entity not found."""
        mock_coordinator = MagicMock()

        result = _get_session_id_for_entity(hass, "media_player.nonexistent", mock_coordinator)
        assert result is None

    @pytest.mark.asyncio
    async def test_no_unique_id(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test returns None when entity has no unique_id."""
        mock_config_entry.add_to_hass(hass)
        entity_reg = er.async_get(hass)

        # Create an entity without unique_id
        entry = entity_reg.async_get_or_create(
            "media_player",
            DOMAIN,
            "no-unique-id",
            config_entry=mock_config_entry,
        )
        # Clear the unique_id
        entity_reg.async_update_entity(entry.entity_id, new_unique_id=None)

        mock_coordinator = MagicMock()
        mock_coordinator.data = {}

        result = _get_session_id_for_entity(hass, entry.entity_id, mock_coordinator)
        assert result is None

    @pytest.mark.asyncio
    async def test_coordinator_data_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test returns None when coordinator data is None."""
        mock_config_entry.add_to_hass(hass)
        entity_reg = er.async_get(hass)

        # Unique ID format is: {server_id}_{device_id}
        entry = entity_reg.async_get_or_create(
            "media_player",
            DOMAIN,
            "server_device-id",
            config_entry=mock_config_entry,
        )

        mock_coordinator = MagicMock()
        mock_coordinator.data = None

        result = _get_session_id_for_entity(hass, entry.entity_id, mock_coordinator)
        assert result is None

    @pytest.mark.asyncio
    async def test_session_not_in_coordinator(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test returns None when session not in coordinator data."""
        mock_config_entry.add_to_hass(hass)
        entity_reg = er.async_get(hass)

        entry = entity_reg.async_get_or_create(
            "media_player",
            DOMAIN,
            "test-entity",
            config_entry=mock_config_entry,
        )

        mock_coordinator = MagicMock()
        mock_coordinator.data = {}  # Empty, no session for this entity

        result = _get_session_id_for_entity(hass, entry.entity_id, mock_coordinator)
        assert result is None

    @pytest.mark.asyncio
    async def test_session_found(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test returns session_id when found."""
        mock_config_entry.add_to_hass(hass)
        entity_reg = er.async_get(hass)

        # Unique ID format is: {server_id}_{device_id}
        entry = entity_reg.async_get_or_create(
            "media_player",
            DOMAIN,
            "test-server-id_device-123",
            config_entry=mock_config_entry,
        )

        mock_session = MagicMock()
        mock_session.session_id = "session-123"

        mock_coordinator = MagicMock()
        # Coordinator data is keyed by device_id (extracted from unique_id)
        mock_coordinator.data = {"device-123": mock_session}

        result = _get_session_id_for_entity(hass, entry.entity_id, mock_coordinator)
        assert result == "session-123"


class TestGetUserIdForEntity:
    """Tests for _get_user_id_for_entity helper."""

    @pytest.mark.asyncio
    async def test_entity_not_found(self, hass: HomeAssistant) -> None:
        """Test returns None when entity not found."""
        mock_coordinator = MagicMock()

        result = _get_user_id_for_entity(hass, "media_player.nonexistent", mock_coordinator)
        assert result is None

    @pytest.mark.asyncio
    async def test_no_unique_id(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test returns None when entity has no unique_id."""
        mock_config_entry.add_to_hass(hass)
        entity_reg = er.async_get(hass)

        entry = entity_reg.async_get_or_create(
            "media_player",
            DOMAIN,
            "no-unique-id",
            config_entry=mock_config_entry,
        )
        entity_reg.async_update_entity(entry.entity_id, new_unique_id=None)

        mock_coordinator = MagicMock()
        mock_coordinator.data = {}

        result = _get_user_id_for_entity(hass, entry.entity_id, mock_coordinator)
        assert result is None

    @pytest.mark.asyncio
    async def test_unique_id_no_underscore(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test returns None when unique_id has no underscore."""
        mock_config_entry.add_to_hass(hass)
        entity_reg = er.async_get(hass)

        # Unique ID without underscore - can't extract device_id
        entry = entity_reg.async_get_or_create(
            "media_player",
            DOMAIN,
            "nounderscore",
            config_entry=mock_config_entry,
        )

        mock_coordinator = MagicMock()
        mock_coordinator.data = {}

        result = _get_user_id_for_entity(hass, entry.entity_id, mock_coordinator)
        assert result is None

    @pytest.mark.asyncio
    async def test_coordinator_data_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test returns None when coordinator data is None."""
        mock_config_entry.add_to_hass(hass)
        entity_reg = er.async_get(hass)

        # Unique ID format is: {server_id}_{device_id}
        entry = entity_reg.async_get_or_create(
            "media_player",
            DOMAIN,
            "server_device-id",
            config_entry=mock_config_entry,
        )

        mock_coordinator = MagicMock()
        mock_coordinator.data = None

        result = _get_user_id_for_entity(hass, entry.entity_id, mock_coordinator)
        assert result is None

    @pytest.mark.asyncio
    async def test_user_id_from_session(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test returns user_id from session."""
        mock_config_entry.add_to_hass(hass)
        entity_reg = er.async_get(hass)

        # Unique ID format is: {server_id}_{device_id}
        entry = entity_reg.async_get_or_create(
            "media_player",
            DOMAIN,
            "test-server-id_device-123",
            config_entry=mock_config_entry,
        )

        mock_session = MagicMock()
        mock_session.user_id = "user-from-session"

        mock_coordinator = MagicMock()
        # Coordinator data is keyed by device_id (extracted from unique_id)
        mock_coordinator.data = {"device-123": mock_session}

        result = _get_user_id_for_entity(hass, entry.entity_id, mock_coordinator)
        assert result == "user-from-session"

    @pytest.mark.asyncio
    async def test_user_id_from_config_entry(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test returns user_id from config entry when session has none."""
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
                "user_id": "user-from-config",
            },
            unique_id="test-server-id",
        )
        config_entry.add_to_hass(hass)
        entity_reg = er.async_get(hass)

        # Unique ID format is: {server_id}_{device_id}
        entry = entity_reg.async_get_or_create(
            "media_player",
            DOMAIN,
            "test-server-id_device-123",
            config_entry=config_entry,
        )

        mock_session = MagicMock()
        mock_session.user_id = None

        mock_coordinator = MagicMock()
        # Coordinator data is keyed by device_id (extracted from unique_id)
        mock_coordinator.data = {"device-123": mock_session}

        result = _get_user_id_for_entity(hass, entry.entity_id, mock_coordinator)
        assert result == "user-from-config"


class TestServicesSetup:
    """Tests for services setup and teardown."""

    @pytest.mark.asyncio
    async def test_services_are_registered(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test all services are registered on setup."""
        mock_config_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(return_value=[])
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_config_entry.entry_id)
                await hass.async_block_till_done()

            # All services should be registered
            assert hass.services.has_service(DOMAIN, "send_message")
            assert hass.services.has_service(DOMAIN, "send_command")
            assert hass.services.has_service(DOMAIN, "mark_played")
            assert hass.services.has_service(DOMAIN, "mark_unplayed")
            assert hass.services.has_service(DOMAIN, "add_favorite")
            assert hass.services.has_service(DOMAIN, "remove_favorite")
            assert hass.services.has_service(DOMAIN, "refresh_library")

    @pytest.mark.asyncio
    async def test_services_unregistered_on_unload(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test services are unregistered on unload."""
        mock_config_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(return_value=[])
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_config_entry.entry_id)
                await hass.async_block_till_done()

            # Services exist before unload
            assert hass.services.has_service(DOMAIN, "send_message")

            # Unload the entry
            await hass.config_entries.async_unload(mock_config_entry.entry_id)
            await hass.async_block_till_done()

            # Services should be unregistered
            assert not hass.services.has_service(DOMAIN, "send_message")


class TestServiceHandlers:
    """Tests for individual service handlers to achieve full coverage."""

    @pytest.mark.asyncio
    async def test_send_message_service_handler(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test send_message service handler executes correctly."""
        mock_config_entry.add_to_hass(hass)

        sessions = [
            {
                "Id": "session-1",
                "DeviceId": "device-1",
                "DeviceName": "Test Device",
                "Client": "Emby Web",
                "SupportsRemoteControl": True,
                "UserId": "user-123",
                "UserName": "TestUser",
            }
        ]

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ),
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(return_value=sessions)
            client.async_send_message = AsyncMock()
            client.close = AsyncMock()

            await hass.config_entries.async_setup(mock_config_entry.entry_id)
            await hass.async_block_till_done()

            # Find the entity ID
            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_config_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            await hass.services.async_call(
                DOMAIN,
                "send_message",
                {
                    ATTR_ENTITY_ID: entity_id,
                    "message": "Hello World",
                    "header": "Test Header",
                    "timeout_ms": 10000,
                },
                blocking=True,
            )

            # Verify the client method was called
            client.async_send_message.assert_called_once()
            call_kwargs = client.async_send_message.call_args[1]
            assert call_kwargs["text"] == "Hello World"
            assert call_kwargs["header"] == "Test Header"
            assert call_kwargs["timeout_ms"] == 10000

    @pytest.mark.asyncio
    async def test_send_command_service_handler(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test send_command service handler executes correctly."""
        mock_config_entry.add_to_hass(hass)

        sessions = [
            {
                "Id": "session-1",
                "DeviceId": "device-1",
                "DeviceName": "Test Device",
                "Client": "Emby Web",
                "SupportsRemoteControl": True,
            }
        ]

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ),
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(return_value=sessions)
            client.async_send_general_command = AsyncMock()
            client.close = AsyncMock()

            await hass.config_entries.async_setup(mock_config_entry.entry_id)
            await hass.async_block_till_done()

            # Find the entity ID
            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_config_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            await hass.services.async_call(
                DOMAIN,
                "send_command",
                {
                    ATTR_ENTITY_ID: entity_id,
                    "command": "ToggleMute",
                },
                blocking=True,
            )

            client.async_send_general_command.assert_called_once()
            call_kwargs = client.async_send_general_command.call_args[1]
            assert call_kwargs["command"] == "ToggleMute"

    @pytest.mark.asyncio
    async def test_mark_played_service_handler(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test mark_played service handler executes correctly."""
        mock_config_entry.add_to_hass(hass)

        sessions = [
            {
                "Id": "session-1",
                "DeviceId": "device-1",
                "DeviceName": "Test Device",
                "Client": "Emby Web",
                "SupportsRemoteControl": True,
                "UserId": "user-123",
                "UserName": "TestUser",
            }
        ]

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(return_value=sessions)
            client.async_mark_played = AsyncMock()
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_config_entry.entry_id)
                await hass.async_block_till_done()

            # Find the entity ID
            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_config_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            await hass.services.async_call(
                DOMAIN,
                "mark_played",
                {
                    ATTR_ENTITY_ID: entity_id,
                    "item_id": "item-123",
                },
                blocking=True,
            )

            client.async_mark_played.assert_called_once()
            call_kwargs = client.async_mark_played.call_args[1]
            assert call_kwargs["item_id"] == "item-123"
            assert call_kwargs["user_id"] == "user-123"

    @pytest.mark.asyncio
    async def test_mark_played_with_explicit_user_id(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test mark_played with explicitly provided user_id."""
        mock_config_entry.add_to_hass(hass)

        sessions = [
            {
                "Id": "session-1",
                "DeviceId": "device-1",
                "DeviceName": "Test Device",
                "Client": "Emby Web",
                "SupportsRemoteControl": True,
                "UserId": "user-123",
            }
        ]

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(return_value=sessions)
            client.async_mark_played = AsyncMock()
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_config_entry.entry_id)
                await hass.async_block_till_done()

            # Find the entity ID
            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_config_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            await hass.services.async_call(
                DOMAIN,
                "mark_played",
                {
                    ATTR_ENTITY_ID: entity_id,
                    "item_id": "item-123",
                    "user_id": "explicit-user-456",
                },
                blocking=True,
            )

            client.async_mark_played.assert_called_once()
            call_kwargs = client.async_mark_played.call_args[1]
            assert call_kwargs["user_id"] == "explicit-user-456"

    @pytest.mark.asyncio
    async def test_mark_unplayed_service_handler(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test mark_unplayed service handler executes correctly."""
        mock_config_entry.add_to_hass(hass)

        sessions = [
            {
                "Id": "session-1",
                "DeviceId": "device-1",
                "DeviceName": "Test Device",
                "Client": "Emby Web",
                "SupportsRemoteControl": True,
                "UserId": "user-123",
            }
        ]

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(return_value=sessions)
            client.async_mark_unplayed = AsyncMock()
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_config_entry.entry_id)
                await hass.async_block_till_done()

            # Find the entity ID
            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_config_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            await hass.services.async_call(
                DOMAIN,
                "mark_unplayed",
                {
                    ATTR_ENTITY_ID: entity_id,
                    "item_id": "item-123",
                },
                blocking=True,
            )

            client.async_mark_unplayed.assert_called_once()
            call_kwargs = client.async_mark_unplayed.call_args[1]
            assert call_kwargs["item_id"] == "item-123"

    @pytest.mark.asyncio
    async def test_add_favorite_service_handler(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test add_favorite service handler executes correctly."""
        mock_config_entry.add_to_hass(hass)

        sessions = [
            {
                "Id": "session-1",
                "DeviceId": "device-1",
                "DeviceName": "Test Device",
                "Client": "Emby Web",
                "SupportsRemoteControl": True,
                "UserId": "user-123",
            }
        ]

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(return_value=sessions)
            client.async_add_favorite = AsyncMock()
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_config_entry.entry_id)
                await hass.async_block_till_done()

            # Find the entity ID
            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_config_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            await hass.services.async_call(
                DOMAIN,
                "add_favorite",
                {
                    ATTR_ENTITY_ID: entity_id,
                    "item_id": "item-123",
                },
                blocking=True,
            )

            client.async_add_favorite.assert_called_once()
            call_kwargs = client.async_add_favorite.call_args[1]
            assert call_kwargs["item_id"] == "item-123"

    @pytest.mark.asyncio
    async def test_remove_favorite_service_handler(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test remove_favorite service handler executes correctly."""
        mock_config_entry.add_to_hass(hass)

        sessions = [
            {
                "Id": "session-1",
                "DeviceId": "device-1",
                "DeviceName": "Test Device",
                "Client": "Emby Web",
                "SupportsRemoteControl": True,
                "UserId": "user-123",
            }
        ]

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(return_value=sessions)
            client.async_remove_favorite = AsyncMock()
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_config_entry.entry_id)
                await hass.async_block_till_done()

            # Find the entity ID
            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_config_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            await hass.services.async_call(
                DOMAIN,
                "remove_favorite",
                {
                    ATTR_ENTITY_ID: entity_id,
                    "item_id": "item-123",
                },
                blocking=True,
            )

            client.async_remove_favorite.assert_called_once()
            call_kwargs = client.async_remove_favorite.call_args[1]
            assert call_kwargs["item_id"] == "item-123"

    @pytest.mark.asyncio
    async def test_refresh_library_service_handler(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test refresh_library service handler executes correctly."""
        mock_config_entry.add_to_hass(hass)

        sessions = [
            {
                "Id": "session-1",
                "DeviceId": "device-1",
                "DeviceName": "Test Device",
                "Client": "Emby Web",
                "SupportsRemoteControl": True,
            }
        ]

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(return_value=sessions)
            client.async_refresh_library = AsyncMock()
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_config_entry.entry_id)
                await hass.async_block_till_done()

            # Find the entity ID
            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_config_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            await hass.services.async_call(
                DOMAIN,
                "refresh_library",
                {
                    ATTR_ENTITY_ID: entity_id,
                },
                blocking=True,
            )

            client.async_refresh_library.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_library_with_library_id(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test refresh_library with specific library_id."""
        mock_config_entry.add_to_hass(hass)

        sessions = [
            {
                "Id": "session-1",
                "DeviceId": "device-1",
                "DeviceName": "Test Device",
                "Client": "Emby Web",
                "SupportsRemoteControl": True,
            }
        ]

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(return_value=sessions)
            client.async_refresh_library = AsyncMock()
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_config_entry.entry_id)
                await hass.async_block_till_done()

            # Find the entity ID
            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_config_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            await hass.services.async_call(
                DOMAIN,
                "refresh_library",
                {
                    ATTR_ENTITY_ID: entity_id,
                    "library_id": "lib-123",
                },
                blocking=True,
            )

            client.async_refresh_library.assert_called_once()
            call_kwargs = client.async_refresh_library.call_args[1]
            assert call_kwargs["library_id"] == "lib-123"


class TestServiceEdgeCases:
    """Tests for edge cases in service handling."""

    @pytest.mark.asyncio
    async def test_services_already_registered_skips_registration(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test that services aren't re-registered if already present."""
        from custom_components.embymedia.services import async_setup_services

        mock_config_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(return_value=[])
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_config_entry.entry_id)
                await hass.async_block_till_done()

            # Services are registered
            assert hass.services.has_service(DOMAIN, "send_message")

            # Try to register again - should be a no-op
            await async_setup_services(hass)

            # Still has services
            assert hass.services.has_service(DOMAIN, "send_message")

    @pytest.mark.asyncio
    async def test_unload_services_when_not_registered(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test unload services gracefully handles case when not registered."""
        from custom_components.embymedia.services import async_unload_services

        # Services not registered
        assert not hass.services.has_service(DOMAIN, "send_message")

        # Should not raise
        await async_unload_services(hass)

    @pytest.mark.asyncio
    async def test_mark_played_no_user_id_raises_error(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test mark_played raises error when no user_id available."""
        mock_config_entry.add_to_hass(hass)

        # Session without user_id
        sessions = [
            {
                "Id": "session-1",
                "DeviceId": "device-1",
                "DeviceName": "Test Device",
                "Client": "Emby Web",
                "SupportsRemoteControl": True,
                # No UserId
            }
        ]

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(return_value=sessions)
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_config_entry.entry_id)
                await hass.async_block_till_done()

            # Find the entity ID
            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_config_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            with pytest.raises(ServiceValidationError) as exc_info:
                await hass.services.async_call(
                    DOMAIN,
                    "mark_played",
                    {
                        ATTR_ENTITY_ID: entity_id,
                        "item_id": "item-123",
                    },
                    blocking=True,
                )

            assert "No user_id available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_message_no_session_raises_error(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test send_message raises error when no session found."""
        mock_config_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            # Session initially
            client.async_get_sessions = AsyncMock(
                return_value=[
                    {
                        "Id": "session-1",
                        "DeviceId": "device-1",
                        "DeviceName": "Test Device",
                        "Client": "Emby Web",
                        "SupportsRemoteControl": True,
                    }
                ]
            )
            client.async_send_message = AsyncMock()
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_config_entry.entry_id)
                await hass.async_block_till_done()

            # Now simulate no sessions - manually clear the coordinator data
            coordinator = mock_config_entry.runtime_data.session_coordinator
            coordinator.data = {}

            # Find the entity ID
            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_config_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            # Should raise HomeAssistantError when session not found
            with pytest.raises(HomeAssistantError) as exc_info:
                await hass.services.async_call(
                    DOMAIN,
                    "send_message",
                    {
                        ATTR_ENTITY_ID: entity_id,
                        "message": "Hello",
                    },
                    blocking=True,
                )

            assert "Session not found" in str(exc_info.value)
            assert "offline" in str(exc_info.value)

            # Client method was NOT called since no session
            client.async_send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_user_id_fallback_to_config_entry_no_session(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test user_id fallback when session not in coordinator data."""
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
                "user_id": "config-user-id",
            },
            unique_id="test-server-id",
        )
        config_entry.add_to_hass(hass)
        entity_reg = er.async_get(hass)

        # Unique ID format is: {server_id}_{device_id}
        entry = entity_reg.async_get_or_create(
            "media_player",
            DOMAIN,
            "test-server-id_device-123",
            config_entry=config_entry,
        )

        mock_coordinator = MagicMock()
        mock_coordinator.data = {}  # Empty - no session for this entity

        result = _get_user_id_for_entity(hass, entry.entity_id, mock_coordinator)
        assert result == "config-user-id"

    @pytest.mark.asyncio
    async def test_mark_unplayed_no_user_id_raises_error(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test mark_unplayed raises error when no user_id available."""
        mock_config_entry.add_to_hass(hass)

        # Session without user_id
        sessions = [
            {
                "Id": "session-1",
                "DeviceId": "device-1",
                "DeviceName": "Test Device",
                "Client": "Emby Web",
                "SupportsRemoteControl": True,
                # No UserId
            }
        ]

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ),
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(return_value=sessions)
            client.close = AsyncMock()

            await hass.config_entries.async_setup(mock_config_entry.entry_id)
            await hass.async_block_till_done()

            # Find the entity ID
            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_config_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            with pytest.raises(ServiceValidationError) as exc_info:
                await hass.services.async_call(
                    DOMAIN,
                    "mark_unplayed",
                    {
                        ATTR_ENTITY_ID: entity_id,
                        "item_id": "item-123",
                    },
                    blocking=True,
                )

            assert "No user_id available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_add_favorite_no_user_id_raises_error(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test add_favorite raises error when no user_id available."""
        mock_config_entry.add_to_hass(hass)

        # Session without user_id
        sessions = [
            {
                "Id": "session-1",
                "DeviceId": "device-1",
                "DeviceName": "Test Device",
                "Client": "Emby Web",
                "SupportsRemoteControl": True,
                # No UserId
            }
        ]

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ),
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(return_value=sessions)
            client.close = AsyncMock()

            await hass.config_entries.async_setup(mock_config_entry.entry_id)
            await hass.async_block_till_done()

            # Find the entity ID
            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_config_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            with pytest.raises(ServiceValidationError) as exc_info:
                await hass.services.async_call(
                    DOMAIN,
                    "add_favorite",
                    {
                        ATTR_ENTITY_ID: entity_id,
                        "item_id": "item-123",
                    },
                    blocking=True,
                )

            assert "No user_id available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_remove_favorite_no_user_id_raises_error(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test remove_favorite raises error when no user_id available."""
        mock_config_entry.add_to_hass(hass)

        # Session without user_id
        sessions = [
            {
                "Id": "session-1",
                "DeviceId": "device-1",
                "DeviceName": "Test Device",
                "Client": "Emby Web",
                "SupportsRemoteControl": True,
                # No UserId
            }
        ]

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ),
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(return_value=sessions)
            client.close = AsyncMock()

            await hass.config_entries.async_setup(mock_config_entry.entry_id)
            await hass.async_block_till_done()

            # Find the entity ID
            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_config_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            with pytest.raises(ServiceValidationError) as exc_info:
                await hass.services.async_call(
                    DOMAIN,
                    "remove_favorite",
                    {
                        ATTR_ENTITY_ID: entity_id,
                        "item_id": "item-123",
                    },
                    blocking=True,
                )

            assert "No user_id available" in str(exc_info.value)


class TestValidateEmbyId:
    """Tests for _validate_emby_id helper."""

    def test_valid_id(self) -> None:
        """Test valid Emby IDs pass validation."""
        # Should not raise
        _validate_emby_id("abc123", "item_id")
        _validate_emby_id("ABC-123_xyz", "item_id")
        _validate_emby_id("a", "item_id")

    def test_empty_id(self) -> None:
        """Test empty ID raises error."""
        with pytest.raises(ServiceValidationError) as exc_info:
            _validate_emby_id("", "item_id")
        assert "cannot be empty" in str(exc_info.value)

    def test_whitespace_only_id(self) -> None:
        """Test whitespace-only ID raises error."""
        with pytest.raises(ServiceValidationError) as exc_info:
            _validate_emby_id("   ", "item_id")
        assert "cannot be empty" in str(exc_info.value)

    def test_too_long_id(self) -> None:
        """Test ID exceeding max length raises error."""
        long_id = "a" * 201  # MAX_SEARCH_TERM_LENGTH is 200
        with pytest.raises(ServiceValidationError) as exc_info:
            _validate_emby_id(long_id, "item_id")
        assert "exceeds maximum length" in str(exc_info.value)

    def test_invalid_characters(self) -> None:
        """Test ID with invalid characters raises error."""
        with pytest.raises(ServiceValidationError) as exc_info:
            _validate_emby_id("abc<script>", "item_id")
        assert "invalid characters" in str(exc_info.value)

    def test_special_characters_rejected(self) -> None:
        """Test various special characters are rejected."""
        invalid_ids = ["abc/def", "abc\\def", "abc;def", "abc'def", 'abc"def']
        for invalid_id in invalid_ids:
            with pytest.raises(ServiceValidationError) as exc_info:
                _validate_emby_id(invalid_id, "item_id")
            assert "invalid characters" in str(exc_info.value)


class TestServiceApiErrorHandling:
    """Tests for API error handling in service handlers."""

    @pytest.mark.asyncio
    async def test_send_message_connection_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test send_message handles connection errors."""
        from custom_components.embymedia.exceptions import EmbyConnectionError

        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="test-server-id",
        )
        mock_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(
                return_value=[
                    {
                        "Id": "session-1",
                        "DeviceId": "device-1",
                        "DeviceName": "Test Device",
                        "Client": "Emby Web",
                        "SupportsRemoteControl": True,
                    }
                ]
            )
            client.async_send_message = AsyncMock(
                side_effect=EmbyConnectionError("Connection refused")
            )
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            with pytest.raises(HomeAssistantError) as exc_info:
                await hass.services.async_call(
                    DOMAIN,
                    "send_message",
                    {
                        ATTR_ENTITY_ID: entity_id,
                        "message": "Test",
                    },
                    blocking=True,
                )

            assert "Connection error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_command_no_session(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test send_command raises error when session not found."""
        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="test-server-id",
        )
        mock_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            # Return session initially, but make coordinator.data empty later
            client.async_get_sessions = AsyncMock(
                return_value=[
                    {
                        "Id": "session-1",
                        "DeviceId": "device-1",
                        "DeviceName": "Test Device",
                        "Client": "Emby Web",
                        "SupportsRemoteControl": True,
                    }
                ]
            )
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            # Clear coordinator data to simulate offline session
            coordinator = mock_entry.runtime_data.session_coordinator
            coordinator.data = {}

            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            with pytest.raises(HomeAssistantError) as exc_info:
                await hass.services.async_call(
                    DOMAIN,
                    "send_command",
                    {
                        ATTR_ENTITY_ID: entity_id,
                        "command": "GoHome",
                    },
                    blocking=True,
                )

            assert "Session not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_mark_played_connection_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test mark_played handles connection errors."""
        from custom_components.embymedia.exceptions import EmbyConnectionError

        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="test-server-id",
        )
        mock_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(
                return_value=[
                    {
                        "Id": "session-1",
                        "DeviceId": "device-1",
                        "DeviceName": "Test Device",
                        "Client": "Emby Web",
                        "SupportsRemoteControl": True,
                        "UserId": "user-123",
                    }
                ]
            )
            client.async_mark_played = AsyncMock(side_effect=EmbyConnectionError("Connection lost"))
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            with pytest.raises(HomeAssistantError) as exc_info:
                await hass.services.async_call(
                    DOMAIN,
                    "mark_played",
                    {
                        ATTR_ENTITY_ID: entity_id,
                        "item_id": "item-123",
                    },
                    blocking=True,
                )

            assert "Connection error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_message_emby_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test send_message handles generic Emby errors."""
        from custom_components.embymedia.exceptions import EmbyError

        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="test-server-id",
        )
        mock_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(
                return_value=[
                    {
                        "Id": "session-1",
                        "DeviceId": "device-1",
                        "DeviceName": "Test Device",
                        "Client": "Emby Web",
                        "SupportsRemoteControl": True,
                    }
                ]
            )
            client.async_send_message = AsyncMock(side_effect=EmbyError("Session not controllable"))
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            with pytest.raises(HomeAssistantError) as exc_info:
                await hass.services.async_call(
                    DOMAIN,
                    "send_message",
                    {
                        ATTR_ENTITY_ID: entity_id,
                        "message": "Test",
                    },
                    blocking=True,
                )

            assert "Session not controllable" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_command_connection_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test send_command handles connection errors."""
        from custom_components.embymedia.exceptions import EmbyConnectionError

        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="test-server-id",
        )
        mock_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(
                return_value=[
                    {
                        "Id": "session-1",
                        "DeviceId": "device-1",
                        "DeviceName": "Test Device",
                        "Client": "Emby Web",
                        "SupportsRemoteControl": True,
                    }
                ]
            )
            client.async_send_general_command = AsyncMock(
                side_effect=EmbyConnectionError("Connection reset")
            )
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            with pytest.raises(HomeAssistantError) as exc_info:
                await hass.services.async_call(
                    DOMAIN,
                    "send_command",
                    {
                        ATTR_ENTITY_ID: entity_id,
                        "command": "GoHome",
                    },
                    blocking=True,
                )

            assert "Connection error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_command_emby_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test send_command handles generic Emby errors."""
        from custom_components.embymedia.exceptions import EmbyError

        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="test-server-id",
        )
        mock_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(
                return_value=[
                    {
                        "Id": "session-1",
                        "DeviceId": "device-1",
                        "DeviceName": "Test Device",
                        "Client": "Emby Web",
                        "SupportsRemoteControl": True,
                    }
                ]
            )
            client.async_send_general_command = AsyncMock(
                side_effect=EmbyError("Command not supported")
            )
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            with pytest.raises(HomeAssistantError) as exc_info:
                await hass.services.async_call(
                    DOMAIN,
                    "send_command",
                    {
                        ATTR_ENTITY_ID: entity_id,
                        "command": "GoHome",
                    },
                    blocking=True,
                )

            assert "Command not supported" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_mark_played_emby_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test mark_played handles generic Emby errors."""
        from custom_components.embymedia.exceptions import EmbyError

        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="test-server-id",
        )
        mock_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(
                return_value=[
                    {
                        "Id": "session-1",
                        "DeviceId": "device-1",
                        "DeviceName": "Test Device",
                        "Client": "Emby Web",
                        "SupportsRemoteControl": True,
                        "UserId": "user-123",
                    }
                ]
            )
            client.async_mark_played = AsyncMock(side_effect=EmbyError("Item not found"))
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            with pytest.raises(HomeAssistantError) as exc_info:
                await hass.services.async_call(
                    DOMAIN,
                    "mark_played",
                    {
                        ATTR_ENTITY_ID: entity_id,
                        "item_id": "nonexistent-item",
                    },
                    blocking=True,
                )

            assert "Item not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_mark_unplayed_connection_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test mark_unplayed handles connection errors."""
        from custom_components.embymedia.exceptions import EmbyConnectionError

        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="test-server-id",
        )
        mock_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(
                return_value=[
                    {
                        "Id": "session-1",
                        "DeviceId": "device-1",
                        "DeviceName": "Test Device",
                        "Client": "Emby Web",
                        "SupportsRemoteControl": True,
                        "UserId": "user-123",
                    }
                ]
            )
            client.async_mark_unplayed = AsyncMock(side_effect=EmbyConnectionError("Timeout"))
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            with pytest.raises(HomeAssistantError) as exc_info:
                await hass.services.async_call(
                    DOMAIN,
                    "mark_unplayed",
                    {
                        ATTR_ENTITY_ID: entity_id,
                        "item_id": "item-123",
                    },
                    blocking=True,
                )

            assert "Connection error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_mark_unplayed_emby_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test mark_unplayed handles generic Emby errors."""
        from custom_components.embymedia.exceptions import EmbyError

        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="test-server-id",
        )
        mock_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(
                return_value=[
                    {
                        "Id": "session-1",
                        "DeviceId": "device-1",
                        "DeviceName": "Test Device",
                        "Client": "Emby Web",
                        "SupportsRemoteControl": True,
                        "UserId": "user-123",
                    }
                ]
            )
            client.async_mark_unplayed = AsyncMock(side_effect=EmbyError("Permission denied"))
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            with pytest.raises(HomeAssistantError) as exc_info:
                await hass.services.async_call(
                    DOMAIN,
                    "mark_unplayed",
                    {
                        ATTR_ENTITY_ID: entity_id,
                        "item_id": "item-123",
                    },
                    blocking=True,
                )

            assert "Permission denied" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_mark_unplayed_with_user_id_validates(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test mark_unplayed validates user_id when provided."""
        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="test-server-id",
        )
        mock_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(
                return_value=[
                    {
                        "Id": "session-1",
                        "DeviceId": "device-1",
                        "DeviceName": "Test Device",
                        "Client": "Emby Web",
                        "SupportsRemoteControl": True,
                        "UserId": "user-123",
                    }
                ]
            )
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            # Invalid user_id should raise
            with pytest.raises(ServiceValidationError) as exc_info:
                await hass.services.async_call(
                    DOMAIN,
                    "mark_unplayed",
                    {
                        ATTR_ENTITY_ID: entity_id,
                        "item_id": "item-123",
                        "user_id": "invalid<chars>",
                    },
                    blocking=True,
                )

            assert "invalid characters" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_add_favorite_connection_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test add_favorite handles connection errors."""
        from custom_components.embymedia.exceptions import EmbyConnectionError

        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="test-server-id",
        )
        mock_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(
                return_value=[
                    {
                        "Id": "session-1",
                        "DeviceId": "device-1",
                        "DeviceName": "Test Device",
                        "Client": "Emby Web",
                        "SupportsRemoteControl": True,
                        "UserId": "user-123",
                    }
                ]
            )
            client.async_add_favorite = AsyncMock(
                side_effect=EmbyConnectionError("Server unreachable")
            )
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            with pytest.raises(HomeAssistantError) as exc_info:
                await hass.services.async_call(
                    DOMAIN,
                    "add_favorite",
                    {
                        ATTR_ENTITY_ID: entity_id,
                        "item_id": "item-123",
                    },
                    blocking=True,
                )

            assert "Connection error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_add_favorite_emby_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test add_favorite handles generic Emby errors."""
        from custom_components.embymedia.exceptions import EmbyError

        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="test-server-id",
        )
        mock_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(
                return_value=[
                    {
                        "Id": "session-1",
                        "DeviceId": "device-1",
                        "DeviceName": "Test Device",
                        "Client": "Emby Web",
                        "SupportsRemoteControl": True,
                        "UserId": "user-123",
                    }
                ]
            )
            client.async_add_favorite = AsyncMock(side_effect=EmbyError("Already a favorite"))
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            with pytest.raises(HomeAssistantError) as exc_info:
                await hass.services.async_call(
                    DOMAIN,
                    "add_favorite",
                    {
                        ATTR_ENTITY_ID: entity_id,
                        "item_id": "item-123",
                    },
                    blocking=True,
                )

            assert "Already a favorite" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_add_favorite_with_user_id_validates(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test add_favorite validates user_id when provided."""
        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="test-server-id",
        )
        mock_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(
                return_value=[
                    {
                        "Id": "session-1",
                        "DeviceId": "device-1",
                        "DeviceName": "Test Device",
                        "Client": "Emby Web",
                        "SupportsRemoteControl": True,
                        "UserId": "user-123",
                    }
                ]
            )
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            # Invalid user_id should raise
            with pytest.raises(ServiceValidationError) as exc_info:
                await hass.services.async_call(
                    DOMAIN,
                    "add_favorite",
                    {
                        ATTR_ENTITY_ID: entity_id,
                        "item_id": "item-123",
                        "user_id": "bad/user",
                    },
                    blocking=True,
                )

            assert "invalid characters" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_remove_favorite_connection_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test remove_favorite handles connection errors."""
        from custom_components.embymedia.exceptions import EmbyConnectionError

        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="test-server-id",
        )
        mock_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(
                return_value=[
                    {
                        "Id": "session-1",
                        "DeviceId": "device-1",
                        "DeviceName": "Test Device",
                        "Client": "Emby Web",
                        "SupportsRemoteControl": True,
                        "UserId": "user-123",
                    }
                ]
            )
            client.async_remove_favorite = AsyncMock(
                side_effect=EmbyConnectionError("Network timeout")
            )
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            with pytest.raises(HomeAssistantError) as exc_info:
                await hass.services.async_call(
                    DOMAIN,
                    "remove_favorite",
                    {
                        ATTR_ENTITY_ID: entity_id,
                        "item_id": "item-123",
                    },
                    blocking=True,
                )

            assert "Connection error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_remove_favorite_emby_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test remove_favorite handles generic Emby errors."""
        from custom_components.embymedia.exceptions import EmbyError

        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="test-server-id",
        )
        mock_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(
                return_value=[
                    {
                        "Id": "session-1",
                        "DeviceId": "device-1",
                        "DeviceName": "Test Device",
                        "Client": "Emby Web",
                        "SupportsRemoteControl": True,
                        "UserId": "user-123",
                    }
                ]
            )
            client.async_remove_favorite = AsyncMock(side_effect=EmbyError("Not a favorite"))
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            with pytest.raises(HomeAssistantError) as exc_info:
                await hass.services.async_call(
                    DOMAIN,
                    "remove_favorite",
                    {
                        ATTR_ENTITY_ID: entity_id,
                        "item_id": "item-123",
                    },
                    blocking=True,
                )

            assert "Not a favorite" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_remove_favorite_with_user_id_validates(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test remove_favorite validates user_id when provided."""
        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="test-server-id",
        )
        mock_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(
                return_value=[
                    {
                        "Id": "session-1",
                        "DeviceId": "device-1",
                        "DeviceName": "Test Device",
                        "Client": "Emby Web",
                        "SupportsRemoteControl": True,
                        "UserId": "user-123",
                    }
                ]
            )
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            # Invalid user_id should raise
            with pytest.raises(ServiceValidationError) as exc_info:
                await hass.services.async_call(
                    DOMAIN,
                    "remove_favorite",
                    {
                        ATTR_ENTITY_ID: entity_id,
                        "item_id": "item-123",
                        "user_id": "user;injection",
                    },
                    blocking=True,
                )

            assert "invalid characters" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_refresh_library_connection_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test refresh_library handles connection errors."""
        from custom_components.embymedia.exceptions import EmbyConnectionError

        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="test-server-id",
        )
        mock_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(
                return_value=[
                    {
                        "Id": "session-1",
                        "DeviceId": "device-1",
                        "DeviceName": "Test Device",
                        "Client": "Emby Web",
                        "SupportsRemoteControl": True,
                    }
                ]
            )
            client.async_refresh_library = AsyncMock(
                side_effect=EmbyConnectionError("Connection closed")
            )
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            with pytest.raises(HomeAssistantError) as exc_info:
                await hass.services.async_call(
                    DOMAIN,
                    "refresh_library",
                    {
                        ATTR_ENTITY_ID: entity_id,
                    },
                    blocking=True,
                )

            assert "Connection error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_refresh_library_emby_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test refresh_library handles generic Emby errors."""
        from custom_components.embymedia.exceptions import EmbyError

        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="test-server-id",
        )
        mock_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(
                return_value=[
                    {
                        "Id": "session-1",
                        "DeviceId": "device-1",
                        "DeviceName": "Test Device",
                        "Client": "Emby Web",
                        "SupportsRemoteControl": True,
                    }
                ]
            )
            client.async_refresh_library = AsyncMock(
                side_effect=EmbyError("Library scan in progress")
            )
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_entry.entry_id)
            entity_id = None
            for ent in entities:
                if ent.domain == "media_player":
                    entity_id = ent.entity_id
                    break

            assert entity_id is not None

            with pytest.raises(HomeAssistantError) as exc_info:
                await hass.services.async_call(
                    DOMAIN,
                    "refresh_library",
                    {
                        ATTR_ENTITY_ID: entity_id,
                    },
                    blocking=True,
                )

            assert "Library scan in progress" in str(exc_info.value)
