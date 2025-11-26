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
        with patch(
            "custom_components.embymedia.EmbyClient", autospec=True
        ) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.8.0.0",
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

        with patch(
            "custom_components.embymedia.EmbyClient", autospec=True
        ) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.8.0.0",
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

        with patch(
            "custom_components.embymedia.EmbyClient", autospec=True
        ) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.8.0.0",
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
            devices = dr.async_entries_for_config_entry(
                device_reg, mock_entry.entry_id
            )
            assert len(devices) >= 1, "Expected at least one device"

            # Find device with an entity attached
            target_device = None
            for device in devices:
                entries = er.async_entries_for_device(entity_reg, device.id)
                if any(e.platform == DOMAIN for e in entries):
                    target_device = device
                    break

            assert target_device is not None, "No device with Emby entity found"

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
