"""Tests for Collection services.

Phase 19: Collection Management
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import ATTR_ENTITY_ID, CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.embymedia.const import (
    CONF_API_KEY,
    CONF_VERIFY_SSL,
    DOMAIN,
)


class TestCreateCollectionService:
    """Tests for create_collection service."""

    @pytest.mark.asyncio
    async def test_create_collection_service_registered(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that create_collection service is registered."""
        from custom_components.embymedia.services import (
            SERVICE_CREATE_COLLECTION,
            async_setup_services,
        )

        await async_setup_services(hass)
        assert hass.services.has_service(DOMAIN, SERVICE_CREATE_COLLECTION)

    @pytest.mark.asyncio
    async def test_create_collection_success(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test create_collection service success."""
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
            client.async_create_collection = AsyncMock(
                return_value={"Id": "collection-123", "Name": "Test Collection"}
            )
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

                # Call service
                await hass.services.async_call(
                    DOMAIN,
                    "create_collection",
                    {
                        ATTR_ENTITY_ID: "media_player.emby_test_device",
                        "collection_name": "Test Collection",
                    },
                    blocking=True,
                )

                # Verify API was called
                client.async_create_collection.assert_called_once_with(
                    name="Test Collection",
                    item_ids=None,
                )

    @pytest.mark.asyncio
    async def test_create_collection_with_item_ids(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test create_collection service with initial item IDs."""
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
            client.async_create_collection = AsyncMock(
                return_value={"Id": "collection-123", "Name": "Movie Collection"}
            )
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

                # Call service with item_ids
                await hass.services.async_call(
                    DOMAIN,
                    "create_collection",
                    {
                        ATTR_ENTITY_ID: "media_player.emby_test_device",
                        "collection_name": "Movie Collection",
                        "item_ids": ["movie-1", "movie-2", "movie-3"],
                    },
                    blocking=True,
                )

                # Verify API was called with item_ids
                client.async_create_collection.assert_called_once_with(
                    name="Movie Collection",
                    item_ids=["movie-1", "movie-2", "movie-3"],
                )


class TestAddToCollectionService:
    """Tests for add_to_collection service."""

    @pytest.mark.asyncio
    async def test_add_to_collection_service_registered(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that add_to_collection service is registered."""
        from custom_components.embymedia.services import (
            SERVICE_ADD_TO_COLLECTION,
            async_setup_services,
        )

        await async_setup_services(hass)
        assert hass.services.has_service(DOMAIN, SERVICE_ADD_TO_COLLECTION)

    @pytest.mark.asyncio
    async def test_add_to_collection_success(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test add_to_collection service success."""
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
            client.async_add_to_collection = AsyncMock()
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

                # Call service
                await hass.services.async_call(
                    DOMAIN,
                    "add_to_collection",
                    {
                        ATTR_ENTITY_ID: "media_player.emby_test_device",
                        "collection_id": "collection-123",
                        "item_ids": ["item-1", "item-2"],
                    },
                    blocking=True,
                )

                # Verify API was called
                client.async_add_to_collection.assert_called_once_with(
                    collection_id="collection-123",
                    item_ids=["item-1", "item-2"],
                )

    @pytest.mark.asyncio
    async def test_add_to_collection_invalid_collection_id(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test add_to_collection service with invalid collection ID."""
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
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

                # Call service with invalid collection_id
                with pytest.raises(ServiceValidationError):
                    await hass.services.async_call(
                        DOMAIN,
                        "add_to_collection",
                        {
                            ATTR_ENTITY_ID: "media_player.emby_test_device",
                            "collection_id": "",  # Invalid - empty
                            "item_ids": ["item-1"],
                        },
                        blocking=True,
                    )


class TestRemoveFromCollectionService:
    """Tests for remove_from_collection service."""

    @pytest.mark.asyncio
    async def test_remove_from_collection_service_registered(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that remove_from_collection service is registered."""
        from custom_components.embymedia.services import (
            SERVICE_REMOVE_FROM_COLLECTION,
            async_setup_services,
        )

        await async_setup_services(hass)
        assert hass.services.has_service(DOMAIN, SERVICE_REMOVE_FROM_COLLECTION)

    @pytest.mark.asyncio
    async def test_remove_from_collection_success(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test remove_from_collection service success."""
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
            client.async_remove_from_collection = AsyncMock()
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

                # Call service
                await hass.services.async_call(
                    DOMAIN,
                    "remove_from_collection",
                    {
                        ATTR_ENTITY_ID: "media_player.emby_test_device",
                        "collection_id": "collection-123",
                        "item_ids": ["item-1", "item-2"],
                    },
                    blocking=True,
                )

                # Verify API was called
                client.async_remove_from_collection.assert_called_once_with(
                    collection_id="collection-123",
                    item_ids=["item-1", "item-2"],
                )
