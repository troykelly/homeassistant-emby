"""Tests to cover remaining gaps in test coverage."""

from __future__ import annotations

import asyncio
import contextlib
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.embymedia.const import CONF_API_KEY, CONF_VERIFY_SSL, DOMAIN
from custom_components.embymedia.exceptions import EmbyConnectionError, EmbyServerError


class TestCoordinatorWebSocketErrors:
    """Tests for coordinator WebSocket error handling."""

    @pytest.fixture
    def mock_config_entry(self) -> MockConfigEntry:
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

    @pytest.mark.asyncio
    async def test_websocket_subscribe_failure(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test WebSocket subscription failure is handled gracefully."""
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
                "custom_components.embymedia.coordinator.EmbyWebSocket"
            ) as mock_ws_class:
                mock_ws = MagicMock()
                mock_ws.async_connect = AsyncMock()
                # Simulate subscription failure
                mock_ws.async_subscribe_sessions = AsyncMock(
                    side_effect=RuntimeError("Subscription failed")
                )
                mock_ws.async_close = AsyncMock()
                mock_ws_class.return_value = mock_ws

                await hass.config_entries.async_setup(mock_config_entry.entry_id)
                await hass.async_block_till_done()

                # Should have called subscribe which failed
                mock_ws.async_subscribe_sessions.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_client_error_in_receive_loop(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test ClientError in WebSocket receive loop is handled."""
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

            # Track calls to the receive loop
            receive_called = asyncio.Event()

            with patch(
                "custom_components.embymedia.coordinator.EmbyWebSocket"
            ) as mock_ws_class:
                mock_ws = MagicMock()
                mock_ws.async_connect = AsyncMock()
                mock_ws.async_subscribe_sessions = AsyncMock()
                mock_ws.async_close = AsyncMock()

                # Make async_run_receive_loop raise ClientError after being called
                async def mock_receive_loop():
                    receive_called.set()
                    raise aiohttp.ClientError("Connection reset")

                mock_ws.async_run_receive_loop = mock_receive_loop
                mock_ws_class.return_value = mock_ws

                await hass.config_entries.async_setup(mock_config_entry.entry_id)
                await hass.async_block_till_done()

                # Wait briefly for receive loop to be called
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(receive_called.wait(), timeout=1.0)

    @pytest.mark.asyncio
    async def test_websocket_connection_failure(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test WebSocket connection failure is handled gracefully."""
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
                "custom_components.embymedia.coordinator.EmbyWebSocket"
            ) as mock_ws_class:
                mock_ws = MagicMock()
                # Simulate connection failure
                mock_ws.async_connect = AsyncMock(
                    side_effect=aiohttp.ClientError("Connection refused")
                )
                mock_ws.async_close = AsyncMock()
                mock_ws_class.return_value = mock_ws

                await hass.config_entries.async_setup(mock_config_entry.entry_id)
                await hass.async_block_till_done()

                # Should have tried to connect
                mock_ws.async_connect.assert_called_once()


class TestWebSocketJsonDecodeErrors:
    """Tests for WebSocket JSON decode error handling."""

    @pytest.mark.asyncio
    async def test_too_many_json_decode_errors(self) -> None:
        """Test WebSocket disconnects after too many JSON decode errors."""
        from custom_components.embymedia.websocket import EmbyWebSocket

        # Create a mock session
        mock_session = MagicMock(spec=aiohttp.ClientSession)

        # Create a WebSocket instance
        ws = EmbyWebSocket(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            device_id="test-device-id",
            session=mock_session,
        )

        # Create a mock WebSocket message with invalid JSON
        mock_msg = MagicMock()
        mock_msg.type = aiohttp.WSMsgType.TEXT
        mock_msg.data = "not valid json {"

        # Simulate processing many JSON decode errors
        ws._ws = MagicMock()  # Set _ws to simulate connected state
        for _i in range(9):
            result = ws._process_message(mock_msg)
            assert result is True  # Should still return True, not disconnected yet

        # The 10th error should trigger disconnect
        result = ws._process_message(mock_msg)
        assert result is False  # Should return False to signal disconnect

    @pytest.mark.asyncio
    async def test_reconnect_lock_skips_concurrent_attempts(self) -> None:
        """Test that reconnection is skipped when already in progress."""
        from custom_components.embymedia.websocket import EmbyWebSocket

        # Create a mock session
        mock_session = MagicMock(spec=aiohttp.ClientSession)

        ws = EmbyWebSocket(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            device_id="test-device-id",
            session=mock_session,
        )

        # Simulate an ongoing reconnection by acquiring the lock
        async with ws._reconnect_lock:
            # Now try to start a reconnect, which should be skipped
            await ws.async_start_reconnect_loop()
            # If we get here, the method returned early due to lock being held


class TestNotifyConnectionError:
    """Tests for notify entity connection error handling."""

    @pytest.fixture
    def mock_config_entry(self) -> MockConfigEntry:
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

    @pytest.mark.asyncio
    async def test_notify_send_connection_error(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test notification handles connection errors gracefully."""
        from custom_components.embymedia.notify import EmbyNotifyEntity

        mock_config_entry.add_to_hass(hass)

        # Create a mock coordinator
        mock_coordinator = MagicMock()
        mock_coordinator.client = MagicMock()
        mock_coordinator.client.async_send_message = AsyncMock(
            side_effect=EmbyConnectionError("Connection lost")
        )

        # Create a mock session
        mock_session = MagicMock()
        mock_session.session_id = "session-123"
        mock_session.device_name = "Test Device"
        mock_session.device_id = "device-123"

        # Create the notify entity directly and call send_message
        entity = EmbyNotifyEntity(mock_coordinator, mock_session)

        # This should catch the EmbyConnectionError and log it, not raise
        await entity.async_send_message("Test message", title="Test")

        # Verify the send was attempted
        mock_coordinator.client.async_send_message.assert_called_once()


class TestApiInvalidJsonResponse:
    """Tests for API invalid JSON response handling."""

    @pytest.mark.asyncio
    async def test_api_returns_invalid_json(self) -> None:
        """Test API client handles invalid JSON responses."""
        from custom_components.embymedia.api import EmbyClient

        # Create a mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.reason = "OK"
        mock_response.raise_for_status = MagicMock()
        # Make json() raise ValueError (invalid JSON)
        mock_response.json = AsyncMock(side_effect=ValueError("No JSON"))

        @asynccontextmanager
        async def mock_request(*args, **kwargs):
            yield mock_response

        # Create mock session
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.request = mock_request
        mock_session.closed = False

        # Patch _get_session to return our mock
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            verify_ssl=True,
        )

        with (
            patch.object(client, "_get_session", AsyncMock(return_value=mock_session)),
            pytest.raises(EmbyServerError) as exc_info,
        ):
            await client._request("GET", "/System/Info")

        assert "invalid JSON" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_api_returns_content_type_error(self) -> None:
        """Test API client handles ContentTypeError responses."""
        from custom_components.embymedia.api import EmbyClient

        # Create a mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.reason = "OK"
        mock_response.raise_for_status = MagicMock()
        # Make json() raise ContentTypeError
        mock_response.json = AsyncMock(
            side_effect=aiohttp.ContentTypeError(
                request_info=MagicMock(),
                history=(),
                message="Expected JSON",
            )
        )

        @asynccontextmanager
        async def mock_request(*args, **kwargs):
            yield mock_response

        # Create mock session
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.request = mock_request
        mock_session.closed = False

        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            verify_ssl=True,
        )

        with (
            patch.object(client, "_get_session", AsyncMock(return_value=mock_session)),
            pytest.raises(EmbyServerError) as exc_info,
        ):
            await client._request("GET", "/System/Info")

        assert "invalid JSON" in str(exc_info.value)
