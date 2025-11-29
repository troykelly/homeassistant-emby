"""Tests for parallel service execution (Phase 22).

These tests verify that services execute operations in parallel
when targeting multiple entities, using asyncio.gather().
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import ATTR_ENTITY_ID, CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.embymedia.const import (
    CONF_API_KEY,
    CONF_PREFIX_MEDIA_PLAYER,
    CONF_VERIFY_SSL,
    DOMAIN,
)
from custom_components.embymedia.services import (
    ATTR_ITEM_ID,
    ATTR_MESSAGE,
    SERVICE_MARK_PLAYED,
    SERVICE_SEND_MESSAGE,
)

from .conftest import add_coordinator_mocks


def create_session_data(session_id: str, device_id: str, device_name: str) -> dict[str, Any]:
    """Create mock session data."""
    return {
        "Id": session_id,
        "DeviceId": device_id,
        "DeviceName": device_name,
        "Client": "Test Client",
        "UserName": "TestUser",
        "UserId": "user-123",
        "PlayableMediaTypes": ["Audio", "Video"],
        "SupportsRemoteControl": True,
    }


class TestParallelServiceExecution:
    """Test that services execute in parallel for multiple entities."""

    @pytest.mark.asyncio
    async def test_send_message_executes_in_parallel(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that send_message executes in parallel for multiple entities."""
        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
            options={
                CONF_PREFIX_MEDIA_PLAYER: False,
            },
            unique_id="test-server-id",
        )
        mock_entry.add_to_hass(hass)

        # Track call order and timing
        call_order: list[str] = []
        call_start_times: dict[str, float] = {}

        async def mock_send_message(
            session_id: str, text: str, header: str, timeout_ms: int
        ) -> None:
            """Mock that tracks call timing."""
            loop = asyncio.get_event_loop()
            call_start_times[session_id] = loop.time()
            call_order.append(f"start_{session_id}")
            # Simulate some async work
            await asyncio.sleep(0.05)
            call_order.append(f"end_{session_id}")

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
            # Return two sessions
            client.async_get_sessions = AsyncMock(
                return_value=[
                    create_session_data("session-1", "device-1", "Player One"),
                    create_session_data("session-2", "device-2", "Player Two"),
                ]
            )
            client.async_send_message = AsyncMock(side_effect=mock_send_message)
            client.close = AsyncMock()
            add_coordinator_mocks(client)

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            # Verify both entities exist
            entity_registry = er.async_get(hass)
            entity1 = entity_registry.async_get("media_player.player_one")
            entity2 = entity_registry.async_get("media_player.player_two")
            assert entity1 is not None
            assert entity2 is not None

            # Call service targeting both entities
            await hass.services.async_call(
                DOMAIN,
                SERVICE_SEND_MESSAGE,
                {
                    ATTR_ENTITY_ID: [
                        "media_player.player_one",
                        "media_player.player_two",
                    ],
                    ATTR_MESSAGE: "Test message",
                },
                blocking=True,
            )

            # Verify both were called
            assert client.async_send_message.call_count == 2

            # Verify parallel execution: both should start before either ends
            # In parallel execution: start_1, start_2, end_1, end_2
            # In sequential execution: start_1, end_1, start_2, end_2
            start_indices = [i for i, x in enumerate(call_order) if x.startswith("start_")]
            end_indices = [i for i, x in enumerate(call_order) if x.startswith("end_")]

            # For parallel execution, all starts should come before all ends
            assert max(start_indices) < min(end_indices), (
                f"Expected parallel execution, got order: {call_order}"
            )

    @pytest.mark.asyncio
    async def test_mark_played_executes_in_parallel(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that mark_played executes in parallel for multiple entities."""
        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
            options={
                CONF_PREFIX_MEDIA_PLAYER: False,
            },
            unique_id="test-server-id",
        )
        mock_entry.add_to_hass(hass)

        # Track call order
        call_order: list[str] = []

        async def mock_mark_played(user_id: str, item_id: str) -> None:
            """Mock that tracks call timing."""
            call_order.append(f"start_{user_id}")
            await asyncio.sleep(0.05)
            call_order.append(f"end_{user_id}")

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
                    create_session_data("session-1", "device-1", "Player One"),
                    create_session_data("session-2", "device-2", "Player Two"),
                ]
            )
            client.async_mark_played = AsyncMock(side_effect=mock_mark_played)
            client.close = AsyncMock()
            add_coordinator_mocks(client)

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            # Call service targeting both entities
            await hass.services.async_call(
                DOMAIN,
                SERVICE_MARK_PLAYED,
                {
                    ATTR_ENTITY_ID: [
                        "media_player.player_one",
                        "media_player.player_two",
                    ],
                    ATTR_ITEM_ID: "item-123",
                },
                blocking=True,
            )

            # Verify both were called
            assert client.async_mark_played.call_count == 2

            # Verify parallel execution
            start_indices = [i for i, x in enumerate(call_order) if x.startswith("start_")]
            end_indices = [i for i, x in enumerate(call_order) if x.startswith("end_")]
            assert max(start_indices) < min(end_indices), (
                f"Expected parallel execution, got order: {call_order}"
            )

    @pytest.mark.asyncio
    async def test_parallel_execution_propagates_first_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that errors are properly propagated in parallel execution."""
        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
            options={
                CONF_PREFIX_MEDIA_PLAYER: False,
            },
            unique_id="test-server-id",
        )
        mock_entry.add_to_hass(hass)

        call_count = 0

        async def mock_send_message_with_error(
            session_id: str, text: str, header: str, timeout_ms: int
        ) -> None:
            """Mock that fails for the second call."""
            nonlocal call_count
            call_count += 1
            if session_id == "session-2":
                from custom_components.embymedia.exceptions import EmbyError

                raise EmbyError("Simulated error")

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
                    create_session_data("session-1", "device-1", "Player One"),
                    create_session_data("session-2", "device-2", "Player Two"),
                ]
            )
            client.async_send_message = AsyncMock(side_effect=mock_send_message_with_error)
            client.close = AsyncMock()
            add_coordinator_mocks(client)

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            # Call service targeting both entities - should raise error
            with pytest.raises(HomeAssistantError) as exc_info:
                await hass.services.async_call(
                    DOMAIN,
                    SERVICE_SEND_MESSAGE,
                    {
                        ATTR_ENTITY_ID: [
                            "media_player.player_one",
                            "media_player.player_two",
                        ],
                        ATTR_MESSAGE: "Test message",
                    },
                    blocking=True,
                )

            # Error should be propagated
            assert "Simulated error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_single_entity_still_works(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that services still work correctly with a single entity."""
        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
            options={
                CONF_PREFIX_MEDIA_PLAYER: False,
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
                    create_session_data("session-1", "device-1", "Player One"),
                ]
            )
            client.async_send_message = AsyncMock()
            client.close = AsyncMock()
            add_coordinator_mocks(client)

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            # Call service with single entity
            await hass.services.async_call(
                DOMAIN,
                SERVICE_SEND_MESSAGE,
                {
                    ATTR_ENTITY_ID: "media_player.player_one",
                    ATTR_MESSAGE: "Test message",
                },
                blocking=True,
            )

            # Verify it was called
            assert client.async_send_message.call_count == 1
