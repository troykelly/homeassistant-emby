"""Tests for Live TV services.

Phase 16: Live TV & DVR Integration
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

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


class TestScheduleRecordingService:
    """Tests for schedule_recording service."""

    @pytest.mark.asyncio
    async def test_schedule_recording_service_registered(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that schedule_recording service is registered."""
        from custom_components.embymedia.services import (
            SERVICE_SCHEDULE_RECORDING,
            async_setup_services,
        )

        await async_setup_services(hass)
        assert hass.services.has_service(DOMAIN, SERVICE_SCHEDULE_RECORDING)

    @pytest.mark.asyncio
    async def test_schedule_recording_success(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test schedule_recording service success."""
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
            client.async_get_timer_defaults = AsyncMock(
                return_value={
                    "ProgramId": "program-123",
                    "ChannelId": "channel-1",
                    "StartDate": "2025-11-28T20:00:00Z",
                    "EndDate": "2025-11-28T21:00:00Z",
                    "PrePaddingSeconds": 60,
                    "PostPaddingSeconds": 120,
                    "Priority": 0,
                }
            )
            client.async_create_timer = AsyncMock()
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
                "schedule_recording",
                {
                    ATTR_ENTITY_ID: [media_player_entity.entity_id],
                    "program_id": "program-123",
                },
                blocking=True,
            )

            client.async_get_timer_defaults.assert_called_once_with(program_id="program-123")
            client.async_create_timer.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_recording_with_padding(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test schedule_recording service with custom padding."""
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
            client.async_get_timer_defaults = AsyncMock(
                return_value={
                    "ProgramId": "program-123",
                    "ChannelId": "channel-1",
                    "StartDate": "2025-11-28T20:00:00Z",
                    "EndDate": "2025-11-28T21:00:00Z",
                    "PrePaddingSeconds": 60,
                    "PostPaddingSeconds": 120,
                    "Priority": 0,
                }
            )
            client.async_create_timer = AsyncMock()
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
                "schedule_recording",
                {
                    ATTR_ENTITY_ID: [media_player_entity.entity_id],
                    "program_id": "program-123",
                    "pre_padding_seconds": 300,
                    "post_padding_seconds": 600,
                },
                blocking=True,
            )

            # Verify the timer data was modified with custom padding
            call_args = client.async_create_timer.call_args
            timer_data = call_args.kwargs["timer_data"]
            assert timer_data["PrePaddingSeconds"] == 300
            assert timer_data["PostPaddingSeconds"] == 600

    @pytest.mark.asyncio
    async def test_schedule_recording_invalid_program_id(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test schedule_recording service with invalid program_id."""
        from custom_components.embymedia.services import async_setup_services

        await async_setup_services(hass)

        with pytest.raises(ServiceValidationError, match="Invalid program_id"):
            await hass.services.async_call(
                DOMAIN,
                "schedule_recording",
                {
                    "entity_id": ["media_player.test"],
                    "program_id": "invalid id with spaces",
                },
                blocking=True,
            )

    @pytest.mark.asyncio
    async def test_schedule_recording_emby_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test schedule_recording service handles Emby errors."""
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
                        "UserId": "user-1",
                    }
                ]
            )
            client.async_get_timer_defaults = AsyncMock(
                return_value={
                    "ProgramId": "program-123",
                    "ChannelId": "channel-1",
                }
            )
            client.async_create_timer = AsyncMock(side_effect=EmbyError("Server error"))
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

            with pytest.raises(HomeAssistantError, match="Server error"):
                await hass.services.async_call(
                    DOMAIN,
                    "schedule_recording",
                    {
                        ATTR_ENTITY_ID: [media_player_entity.entity_id],
                        "program_id": "program-123",
                    },
                    blocking=True,
                )

    @pytest.mark.asyncio
    async def test_schedule_recording_connection_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test schedule_recording service handles connection errors."""
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
                        "UserId": "user-1",
                    }
                ]
            )
            client.async_get_timer_defaults = AsyncMock(
                side_effect=EmbyConnectionError("Connection failed")
            )
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

            with pytest.raises(HomeAssistantError, match="Connection error"):
                await hass.services.async_call(
                    DOMAIN,
                    "schedule_recording",
                    {
                        ATTR_ENTITY_ID: [media_player_entity.entity_id],
                        "program_id": "program-123",
                    },
                    blocking=True,
                )


class TestCancelRecordingService:
    """Tests for cancel_recording service."""

    @pytest.mark.asyncio
    async def test_cancel_recording_service_registered(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that cancel_recording service is registered."""
        from custom_components.embymedia.services import (
            SERVICE_CANCEL_RECORDING,
            async_setup_services,
        )

        await async_setup_services(hass)
        assert hass.services.has_service(DOMAIN, SERVICE_CANCEL_RECORDING)

    @pytest.mark.asyncio
    async def test_cancel_recording_success(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test cancel_recording service success."""
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
            client.async_cancel_timer = AsyncMock()
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
                "cancel_recording",
                {
                    ATTR_ENTITY_ID: [media_player_entity.entity_id],
                    "timer_id": "timer-123",
                },
                blocking=True,
            )

            client.async_cancel_timer.assert_called_once_with(timer_id="timer-123")

    @pytest.mark.asyncio
    async def test_cancel_recording_invalid_timer_id(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test cancel_recording service with invalid timer_id."""
        from custom_components.embymedia.services import async_setup_services

        await async_setup_services(hass)

        with pytest.raises(ServiceValidationError, match="Invalid timer_id"):
            await hass.services.async_call(
                DOMAIN,
                "cancel_recording",
                {
                    "entity_id": ["media_player.test"],
                    "timer_id": "invalid id with spaces",
                },
                blocking=True,
            )

    @pytest.mark.asyncio
    async def test_cancel_recording_emby_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test cancel_recording service handles Emby errors."""
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
                        "UserId": "user-1",
                    }
                ]
            )
            client.async_cancel_timer = AsyncMock(side_effect=EmbyError("Server error"))
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

            with pytest.raises(HomeAssistantError, match="Server error"):
                await hass.services.async_call(
                    DOMAIN,
                    "cancel_recording",
                    {
                        ATTR_ENTITY_ID: [media_player_entity.entity_id],
                        "timer_id": "timer-123",
                    },
                    blocking=True,
                )

    @pytest.mark.asyncio
    async def test_cancel_recording_connection_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test cancel_recording service handles connection errors."""
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
                        "UserId": "user-1",
                    }
                ]
            )
            client.async_cancel_timer = AsyncMock(
                side_effect=EmbyConnectionError("Connection failed")
            )
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

            with pytest.raises(HomeAssistantError, match="Connection error"):
                await hass.services.async_call(
                    DOMAIN,
                    "cancel_recording",
                    {
                        ATTR_ENTITY_ID: [media_player_entity.entity_id],
                        "timer_id": "timer-123",
                    },
                    blocking=True,
                )


class TestCancelSeriesTimerService:
    """Tests for cancel_series_timer service."""

    @pytest.mark.asyncio
    async def test_cancel_series_timer_service_registered(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that cancel_series_timer service is registered."""
        from custom_components.embymedia.services import (
            SERVICE_CANCEL_SERIES_TIMER,
            async_setup_services,
        )

        await async_setup_services(hass)
        assert hass.services.has_service(DOMAIN, SERVICE_CANCEL_SERIES_TIMER)

    @pytest.mark.asyncio
    async def test_cancel_series_timer_success(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test cancel_series_timer service success."""
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
            client.async_cancel_series_timer = AsyncMock()
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
                "cancel_series_timer",
                {
                    ATTR_ENTITY_ID: [media_player_entity.entity_id],
                    "series_timer_id": "series-timer-123",
                },
                blocking=True,
            )

            client.async_cancel_series_timer.assert_called_once_with(
                series_timer_id="series-timer-123"
            )

    @pytest.mark.asyncio
    async def test_cancel_series_timer_invalid_id(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test cancel_series_timer service with invalid series_timer_id."""
        from custom_components.embymedia.services import async_setup_services

        await async_setup_services(hass)

        with pytest.raises(ServiceValidationError, match="Invalid series_timer_id"):
            await hass.services.async_call(
                DOMAIN,
                "cancel_series_timer",
                {
                    "entity_id": ["media_player.test"],
                    "series_timer_id": "invalid id with spaces",
                },
                blocking=True,
            )

    @pytest.mark.asyncio
    async def test_cancel_series_timer_emby_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test cancel_series_timer service handles Emby errors."""
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
                        "UserId": "user-1",
                    }
                ]
            )
            client.async_cancel_series_timer = AsyncMock(side_effect=EmbyError("Server error"))
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

            with pytest.raises(HomeAssistantError, match="Server error"):
                await hass.services.async_call(
                    DOMAIN,
                    "cancel_series_timer",
                    {
                        ATTR_ENTITY_ID: [media_player_entity.entity_id],
                        "series_timer_id": "series-timer-123",
                    },
                    blocking=True,
                )

    @pytest.mark.asyncio
    async def test_cancel_series_timer_connection_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test cancel_series_timer service handles connection errors."""
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
                        "UserId": "user-1",
                    }
                ]
            )
            client.async_cancel_series_timer = AsyncMock(
                side_effect=EmbyConnectionError("Connection failed")
            )
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

            with pytest.raises(HomeAssistantError, match="Connection error"):
                await hass.services.async_call(
                    DOMAIN,
                    "cancel_series_timer",
                    {
                        ATTR_ENTITY_ID: [media_player_entity.entity_id],
                        "series_timer_id": "series-timer-123",
                    },
                    blocking=True,
                )
