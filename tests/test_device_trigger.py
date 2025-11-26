"""Tests for Emby device triggers."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.device_automation import DeviceAutomationType
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.embymedia.const import (
    CONF_API_KEY,
    CONF_VERIFY_SSL,
    DOMAIN,
)


class TestGetTriggers:
    """Test getting device triggers."""

    @pytest.mark.asyncio
    async def test_get_triggers_returns_all_types(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that all trigger types are returned for a device."""
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
            client.async_get_sessions = AsyncMock(
                return_value=[
                    {
                        "Id": "session-123",
                        "DeviceId": "device-123",
                        "DeviceName": "Test Player",
                        "Client": "Test Client",
                        "UserName": "TestUser",
                        "UserId": "user-123",
                        "PlayableMediaTypes": ["Audio", "Video"],
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

            # Get device ID
            device_registry = dr.async_get(hass)
            device = device_registry.async_get_device(
                identifiers={(DOMAIN, "device-123")}
            )
            assert device is not None

            # Import and call async_get_triggers
            from custom_components.embymedia.device_trigger import async_get_triggers

            triggers = await async_get_triggers(hass, device.id)

            # Should have all trigger types for media_player entity
            expected_types = {
                "playback_started",
                "playback_stopped",
                "playback_paused",
                "playback_resumed",
                "media_changed",
                "session_connected",
                "session_disconnected",
            }
            trigger_types = {t["type"] for t in triggers}
            assert trigger_types == expected_types

    @pytest.mark.asyncio
    async def test_get_triggers_empty_for_non_media_player_device(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that no triggers returned for non-media-player devices."""
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

            # Get the server device (not a media player device)
            device_registry = dr.async_get(hass)
            device = device_registry.async_get_device(
                identifiers={(DOMAIN, "test-server-id")}
            )
            assert device is not None

            from custom_components.embymedia.device_trigger import async_get_triggers

            triggers = await async_get_triggers(hass, device.id)

            # Server device has no media_player entities, so no triggers
            assert triggers == []


class TestAttachTrigger:
    """Test attaching device triggers."""

    @pytest.mark.asyncio
    async def test_attach_trigger_playback_started(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test attaching playback_started trigger."""
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
            client.async_get_sessions = AsyncMock(
                return_value=[
                    {
                        "Id": "session-123",
                        "DeviceId": "device-123",
                        "DeviceName": "Test Player",
                        "Client": "Test Client",
                        "UserName": "TestUser",
                        "UserId": "user-123",
                        "PlayableMediaTypes": ["Audio", "Video"],
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

            # Get device and entity IDs
            device_registry = dr.async_get(hass)
            device = device_registry.async_get_device(
                identifiers={(DOMAIN, "device-123")}
            )
            assert device is not None

            entity_registry = er.async_get(hass)
            entity_entry = entity_registry.async_get("media_player.test_player")
            assert entity_entry is not None

            # Setup automation component
            await async_setup_component(hass, "automation", {})
            await hass.async_block_till_done()

            from custom_components.embymedia.device_trigger import async_attach_trigger

            triggered = []

            async def trigger_action(
                run_variables: dict[str, Any], context: Any = None
            ) -> None:
                """Handle trigger."""
                triggered.append(run_variables)

            trigger_config = {
                "platform": "device",
                "domain": DOMAIN,
                "device_id": device.id,
                "entity_id": "media_player.test_player",
                "type": "playback_started",
            }

            # TriggerInfo requires trigger_data and variables
            trigger_info = {
                "trigger_data": {},
                "variables": {},
            }

            unsub = await async_attach_trigger(
                hass,
                trigger_config,
                trigger_action,
                trigger_info,
            )

            # Fire the event
            hass.bus.async_fire(
                f"{DOMAIN}_event",
                {
                    "entity_id": "media_player.test_player",
                    "type": "playback_started",
                    "media_content_id": "item-123",
                },
            )
            await hass.async_block_till_done()

            # Verify trigger was called
            assert len(triggered) == 1

            # Cleanup
            unsub()
