"""Tests for Emby device conditions."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SSL,
    STATE_IDLE,
    STATE_PAUSED,
    STATE_PLAYING,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.embymedia.const import (
    CONF_API_KEY,
    CONF_PREFIX_MEDIA_PLAYER,
    CONF_VERIFY_SSL,
    DOMAIN,
)

from .conftest import add_coordinator_mocks


class TestGetConditions:
    """Test getting device conditions."""

    @pytest.mark.asyncio
    async def test_get_conditions_returns_all_types(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that all condition types are returned for a device."""
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
            add_coordinator_mocks(client)

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            # Get device ID
            device_registry = dr.async_get(hass)
            device = device_registry.async_get_device(identifiers={(DOMAIN, "device-123")})
            assert device is not None

            # Import and call async_get_conditions
            from custom_components.embymedia.device_condition import async_get_conditions

            conditions = await async_get_conditions(hass, device.id)

            # Should have all condition types for media_player entity
            expected_types = {
                "is_playing",
                "is_paused",
                "is_idle",
                "is_off",
                "has_media",
            }
            condition_types = {c["type"] for c in conditions}
            assert condition_types == expected_types

    @pytest.mark.asyncio
    async def test_get_conditions_empty_for_non_media_player_device(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that no conditions returned for non-media-player devices."""
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
            add_coordinator_mocks(client)

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            # Get the server device (not a media player device)
            device_registry = dr.async_get(hass)
            device = device_registry.async_get_device(identifiers={(DOMAIN, "test-server-id")})
            assert device is not None

            from custom_components.embymedia.device_condition import async_get_conditions

            conditions = await async_get_conditions(hass, device.id)

            # Server device has no media_player entities, so no conditions
            assert conditions == []


class TestConditionFromConfig:
    """Test evaluating conditions."""

    @pytest.mark.asyncio
    async def test_condition_is_playing(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test is_playing condition."""
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
                CONF_PREFIX_MEDIA_PLAYER: False,  # Phase 11: Disable prefix for test
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
                        "Id": "session-123",
                        "DeviceId": "device-123",
                        "DeviceName": "Test Player",
                        "Client": "Test Client",
                        "UserName": "TestUser",
                        "UserId": "user-123",
                        "PlayableMediaTypes": ["Audio", "Video"],
                        "SupportsRemoteControl": True,
                        "NowPlayingItem": {
                            "Id": "item-123",
                            "Name": "Test Movie",
                            "Type": "Movie",
                            "RunTimeTicks": 72000000000,
                        },
                        "PlayState": {
                            "PositionTicks": 36000000000,
                            "IsPaused": False,
                            "IsMuted": False,
                            "VolumeLevel": 100,
                        },
                    }
                ]
            )
            client.get_image_url.return_value = "http://emby.local/image.jpg"
            client.close = AsyncMock()
            add_coordinator_mocks(client)

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            # Verify entity state
            state = hass.states.get("media_player.test_player")
            assert state is not None
            assert state.state == STATE_PLAYING

            from custom_components.embymedia.device_condition import (
                async_condition_from_config,
            )

            condition_config = {
                "entity_id": "media_player.test_player",
                "type": "is_playing",
            }

            condition_fn = await async_condition_from_config(hass, condition_config)

            # Should return True when playing
            assert condition_fn(hass) is True

    @pytest.mark.asyncio
    async def test_condition_is_paused(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test is_paused condition."""
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
                CONF_PREFIX_MEDIA_PLAYER: False,  # Phase 11: Disable prefix for test
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
                        "Id": "session-123",
                        "DeviceId": "device-123",
                        "DeviceName": "Test Player",
                        "Client": "Test Client",
                        "UserName": "TestUser",
                        "UserId": "user-123",
                        "PlayableMediaTypes": ["Audio", "Video"],
                        "SupportsRemoteControl": True,
                        "NowPlayingItem": {
                            "Id": "item-123",
                            "Name": "Test Movie",
                            "Type": "Movie",
                            "RunTimeTicks": 72000000000,
                        },
                        "PlayState": {
                            "PositionTicks": 36000000000,
                            "IsPaused": True,  # Paused!
                            "IsMuted": False,
                            "VolumeLevel": 100,
                        },
                    }
                ]
            )
            client.get_image_url.return_value = "http://emby.local/image.jpg"
            client.close = AsyncMock()
            add_coordinator_mocks(client)

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            # Verify entity state
            state = hass.states.get("media_player.test_player")
            assert state is not None
            assert state.state == STATE_PAUSED

            from custom_components.embymedia.device_condition import (
                async_condition_from_config,
            )

            condition_config = {
                "entity_id": "media_player.test_player",
                "type": "is_paused",
            }

            condition_fn = await async_condition_from_config(hass, condition_config)

            # Should return True when paused
            assert condition_fn(hass) is True

    @pytest.mark.asyncio
    async def test_condition_is_idle(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test is_idle condition."""
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
                CONF_PREFIX_MEDIA_PLAYER: False,  # Phase 11: Disable prefix for test
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
            # No NowPlayingItem = idle
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
            add_coordinator_mocks(client)

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            # Verify entity state
            state = hass.states.get("media_player.test_player")
            assert state is not None
            assert state.state == STATE_IDLE

            from custom_components.embymedia.device_condition import (
                async_condition_from_config,
            )

            condition_config = {
                "entity_id": "media_player.test_player",
                "type": "is_idle",
            }

            condition_fn = await async_condition_from_config(hass, condition_config)

            # Should return True when idle
            assert condition_fn(hass) is True

    @pytest.mark.asyncio
    async def test_condition_has_media(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test has_media condition."""
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
                CONF_PREFIX_MEDIA_PLAYER: False,  # Phase 11: Disable prefix for test
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
                        "Id": "session-123",
                        "DeviceId": "device-123",
                        "DeviceName": "Test Player",
                        "Client": "Test Client",
                        "UserName": "TestUser",
                        "UserId": "user-123",
                        "PlayableMediaTypes": ["Audio", "Video"],
                        "SupportsRemoteControl": True,
                        "NowPlayingItem": {
                            "Id": "item-123",
                            "Name": "Test Movie",
                            "Type": "Movie",
                            "RunTimeTicks": 72000000000,
                        },
                        "PlayState": {
                            "PositionTicks": 36000000000,
                            "IsPaused": False,
                            "IsMuted": False,
                            "VolumeLevel": 100,
                        },
                    }
                ]
            )
            client.get_image_url.return_value = "http://emby.local/image.jpg"
            client.close = AsyncMock()
            add_coordinator_mocks(client)

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            from custom_components.embymedia.device_condition import (
                async_condition_from_config,
            )

            condition_config = {
                "entity_id": "media_player.test_player",
                "type": "has_media",
            }

            condition_fn = await async_condition_from_config(hass, condition_config)

            # Should return True when media is loaded
            assert condition_fn(hass) is True

    @pytest.mark.asyncio
    async def test_condition_false_when_state_not_matching(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test condition returns False when state doesn't match."""
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
            # Idle state
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
            add_coordinator_mocks(client)

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_entry.entry_id)
                await hass.async_block_till_done()

            from custom_components.embymedia.device_condition import (
                async_condition_from_config,
            )

            # Entity is idle, but we check for playing
            condition_config = {
                "entity_id": "media_player.emby_test_player",
                "type": "is_playing",
            }

            condition_fn = await async_condition_from_config(hass, condition_config)

            # Should return False when not playing (entity exists but state doesn't match)
            assert condition_fn(hass) is False

    @pytest.mark.asyncio
    async def test_condition_false_for_nonexistent_entity(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test condition returns False for non-existent entity."""
        from custom_components.embymedia.device_condition import (
            async_condition_from_config,
        )

        condition_config = {
            "entity_id": "media_player.nonexistent",
            "type": "is_playing",
        }

        condition_fn = await async_condition_from_config(hass, condition_config)

        # Should return False when entity doesn't exist (condition can't be met)
        assert condition_fn(hass) is False

    @pytest.mark.asyncio
    async def test_condition_is_off(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test is_off condition when entity is off."""
        from custom_components.embymedia.device_condition import (
            async_condition_from_config,
        )

        # Set up a state that's "off"
        hass.states.async_set("media_player.test_off_player", "off")

        condition_config = {
            "entity_id": "media_player.test_off_player",
            "type": "is_off",
        }

        condition_fn = await async_condition_from_config(hass, condition_config)

        # Should return True when state is off
        assert condition_fn(hass) is True

    @pytest.mark.asyncio
    async def test_condition_unknown_type_returns_false(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that unknown condition type returns False."""
        from custom_components.embymedia.device_condition import (
            async_condition_from_config,
        )

        # Set up a state
        hass.states.async_set("media_player.test_player", STATE_PLAYING)

        condition_config = {
            "entity_id": "media_player.test_player",
            "type": "unknown_type",
        }

        condition_fn = await async_condition_from_config(hass, condition_config)

        # Unknown condition type should return False
        assert condition_fn(hass) is False


class TestConditionCapabilities:
    """Test condition capabilities."""

    @pytest.mark.asyncio
    async def test_get_condition_capabilities(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test async_get_condition_capabilities returns empty dict."""
        from custom_components.embymedia.device_condition import (
            async_get_condition_capabilities,
        )

        result = await async_get_condition_capabilities(hass, {})

        assert result == {}
