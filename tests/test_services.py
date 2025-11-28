"""Tests for Emby services."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.embymedia.const import (
    CONF_API_KEY,
    CONF_VERIFY_SSL,
    DOMAIN,
)


class TestSendMessageService:
    """Test send_message service."""

    @pytest.mark.asyncio
    async def test_send_message_success(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test sending message to Emby client."""
        # This test verifies the service can be called
        # Full implementation will use entity ID to find session
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

        # Verify service exists after setup
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
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            # Service should be registered
            assert hass.services.has_service(DOMAIN, "send_message")


class TestLibraryServices:
    """Test library management services."""

    @pytest.mark.asyncio
    async def test_mark_played_service_exists(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test mark_played service is registered."""
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
            client.async_get_sessions = AsyncMock(return_value=[])
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            # Library services should be registered
            assert hass.services.has_service(DOMAIN, "mark_played")
            assert hass.services.has_service(DOMAIN, "mark_unplayed")
            assert hass.services.has_service(DOMAIN, "add_favorite")
            assert hass.services.has_service(DOMAIN, "remove_favorite")
            assert hass.services.has_service(DOMAIN, "refresh_library")


class TestDeviceIdTargeting:
    """Test device_id targeting in services."""

    @pytest.mark.asyncio
    async def test_service_accepts_device_id(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test services accept device_id as target."""
        from homeassistant.const import ATTR_DEVICE_ID
        from homeassistant.helpers import device_registry as dr
        from homeassistant.helpers import entity_registry as er

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
            # Return a session so we have an entity
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
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            # Get device ID from device registry
            device_reg = dr.async_get(hass)
            entity_reg = er.async_get(hass)

            # Find the device that has a media_player entity (session device)
            devices = dr.async_entries_for_config_entry(device_reg, mock_entry.entry_id)
            assert len(devices) >= 1, "Expected at least one device"

            # Find device with a media_player entity (session devices, not server)
            target_device = None
            for device in devices:
                entries = er.async_entries_for_device(entity_reg, device.id)
                if any(e.platform == DOMAIN and e.domain == "media_player" for e in entries):
                    target_device = device
                    break

            assert target_device is not None, "No device with Emby media_player entity found"

            # Call service with device_id
            await hass.services.async_call(
                DOMAIN,
                "send_message",
                {
                    ATTR_DEVICE_ID: [target_device.id],
                    "message": "Test message",
                },
                blocking=True,
            )


class TestPlayInstantMixService:
    """Tests for play instant mix service."""

    @pytest.mark.asyncio
    async def test_play_instant_mix_service_registered(self, hass: HomeAssistant) -> None:
        """Test that play_instant_mix service is registered."""
        from custom_components.embymedia.services import (
            SERVICE_PLAY_INSTANT_MIX,
            async_setup_services,
        )

        await async_setup_services(hass)
        assert hass.services.has_service(DOMAIN, SERVICE_PLAY_INSTANT_MIX)

    @pytest.mark.asyncio
    async def test_play_instant_mix_success(self, hass: HomeAssistant) -> None:
        """Test play_instant_mix service success."""
        from homeassistant.const import ATTR_ENTITY_ID

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
                        "UserId": "user-1",
                    }
                ]
            )
            client.async_get_instant_mix = AsyncMock(
                return_value=[
                    {"Id": "item-1", "Name": "Track 1", "Type": "Audio"},
                    {"Id": "item-2", "Name": "Track 2", "Type": "Audio"},
                ]
            )
            client.async_play_items = AsyncMock()
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            # Find the media_player entity
            from homeassistant.helpers import entity_registry as er

            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_entry.entry_id)
            media_player_entity = next(
                (e for e in entities if e.domain == "media_player"),
                None,
            )
            assert media_player_entity is not None

            await hass.services.async_call(
                DOMAIN,
                "play_instant_mix",
                {
                    ATTR_ENTITY_ID: [media_player_entity.entity_id],
                    "item_id": "seed-item-123",
                },
                blocking=True,
            )

            client.async_get_instant_mix.assert_called_once()
            client.async_play_items.assert_called_once()

    @pytest.mark.asyncio
    async def test_play_instant_mix_no_items_found(self, hass: HomeAssistant) -> None:
        """Test play_instant_mix service when no items found."""
        from homeassistant.const import ATTR_ENTITY_ID
        from homeassistant.exceptions import HomeAssistantError

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
                        "UserId": "user-1",
                    }
                ]
            )
            # Return empty list - no items found
            client.async_get_instant_mix = AsyncMock(return_value=[])
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            from homeassistant.helpers import entity_registry as er

            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_entry.entry_id)
            media_player_entity = next(
                (e for e in entities if e.domain == "media_player"),
                None,
            )
            assert media_player_entity is not None

            with pytest.raises(HomeAssistantError, match="No instant mix items found"):
                await hass.services.async_call(
                    DOMAIN,
                    "play_instant_mix",
                    {
                        ATTR_ENTITY_ID: [media_player_entity.entity_id],
                        "item_id": "seed-item-123",
                    },
                    blocking=True,
                )


class TestPlaySimilarService:
    """Tests for play similar items service."""

    @pytest.mark.asyncio
    async def test_play_similar_service_registered(self, hass: HomeAssistant) -> None:
        """Test that play_similar service is registered."""
        from custom_components.embymedia.services import (
            SERVICE_PLAY_SIMILAR,
            async_setup_services,
        )

        await async_setup_services(hass)
        assert hass.services.has_service(DOMAIN, SERVICE_PLAY_SIMILAR)

    @pytest.mark.asyncio
    async def test_play_similar_success(self, hass: HomeAssistant) -> None:
        """Test play_similar service success."""
        from homeassistant.const import ATTR_ENTITY_ID

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
                        "UserId": "user-1",
                    }
                ]
            )
            client.async_get_similar_items = AsyncMock(
                return_value=[
                    {"Id": "movie-1", "Name": "Similar Movie 1", "Type": "Movie"},
                    {"Id": "movie-2", "Name": "Similar Movie 2", "Type": "Movie"},
                ]
            )
            client.async_play_items = AsyncMock()
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            from homeassistant.helpers import entity_registry as er

            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_entry.entry_id)
            media_player_entity = next(
                (e for e in entities if e.domain == "media_player"),
                None,
            )
            assert media_player_entity is not None

            await hass.services.async_call(
                DOMAIN,
                "play_similar",
                {
                    ATTR_ENTITY_ID: [media_player_entity.entity_id],
                    "item_id": "seed-movie-123",
                },
                blocking=True,
            )

            client.async_get_similar_items.assert_called_once()
            client.async_play_items.assert_called_once()

    @pytest.mark.asyncio
    async def test_play_similar_no_items_found(self, hass: HomeAssistant) -> None:
        """Test play_similar service when no similar items found."""
        from homeassistant.const import ATTR_ENTITY_ID
        from homeassistant.exceptions import HomeAssistantError

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
                        "UserId": "user-1",
                    }
                ]
            )
            # Return empty list - no similar items found
            client.async_get_similar_items = AsyncMock(return_value=[])
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            from homeassistant.helpers import entity_registry as er

            entity_reg = er.async_get(hass)
            entities = er.async_entries_for_config_entry(entity_reg, mock_entry.entry_id)
            media_player_entity = next(
                (e for e in entities if e.domain == "media_player"),
                None,
            )
            assert media_player_entity is not None

            with pytest.raises(HomeAssistantError, match="No similar items found"):
                await hass.services.async_call(
                    DOMAIN,
                    "play_similar",
                    {
                        ATTR_ENTITY_ID: [media_player_entity.entity_id],
                        "item_id": "seed-movie-123",
                    },
                    blocking=True,
                )
