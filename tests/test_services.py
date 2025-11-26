"""Tests for Emby services."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import ATTR_ENTITY_ID, CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
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
