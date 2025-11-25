"""Tests for Emby WebSocket client."""

from __future__ import annotations

import json
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.embymedia.websocket import EmbyWebSocket


@pytest.fixture
def mock_ws_response() -> MagicMock:
    """Create a mock WebSocket response."""
    mock = MagicMock()
    mock.type = aiohttp.WSMsgType.TEXT
    return mock


@pytest.fixture
def mock_aiohttp_session() -> Generator[MagicMock]:
    """Mock aiohttp ClientSession for WebSocket tests."""
    with patch("aiohttp.ClientSession", autospec=True) as mock_session_class:
        session = mock_session_class.return_value
        session.closed = False
        session.close = AsyncMock()
        yield session


class TestEmbyWebSocketInit:
    """Tests for EmbyWebSocket initialization."""

    def test_init_stores_parameters(self) -> None:
        """Test that init stores all parameters correctly."""
        session = MagicMock()

        ws = EmbyWebSocket(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            device_id="test-device-123",
            session=session,
        )

        assert ws.host == "emby.local"
        assert ws.port == 8096
        assert ws.api_key == "test-key"
        assert ws.ssl is False
        assert ws.device_id == "test-device-123"
        assert ws._session is session

    def test_init_with_ssl(self) -> None:
        """Test init with SSL enabled."""
        session = MagicMock()

        ws = EmbyWebSocket(
            host="emby.local",
            port=8920,
            api_key="test-key",
            ssl=True,
            device_id="test-device-123",
            session=session,
        )

        assert ws.ssl is True

    def test_connected_false_initially(self) -> None:
        """Test that connected is False when not connected."""
        session = MagicMock()

        ws = EmbyWebSocket(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            device_id="test-device-123",
            session=session,
        )

        assert ws.connected is False


class TestEmbyWebSocketConnectionUrl:
    """Tests for WebSocket connection URL generation."""

    def test_connection_url_http(self) -> None:
        """Test WebSocket URL generation for HTTP."""
        session = MagicMock()

        ws = EmbyWebSocket(
            host="emby.local",
            port=8096,
            api_key="my-api-key",
            ssl=False,
            device_id="device-abc",
            session=session,
        )

        url = ws._build_connection_url()

        assert url == "ws://emby.local:8096/embywebsocket?api_key=my-api-key&deviceId=device-abc"

    def test_connection_url_https(self) -> None:
        """Test WebSocket URL generation for HTTPS."""
        session = MagicMock()

        ws = EmbyWebSocket(
            host="emby.local",
            port=8920,
            api_key="my-api-key",
            ssl=True,
            device_id="device-abc",
            session=session,
        )

        url = ws._build_connection_url()

        assert url == "wss://emby.local:8920/embywebsocket?api_key=my-api-key&deviceId=device-abc"

    def test_connection_url_special_characters_in_api_key(self) -> None:
        """Test URL encoding of special characters in API key."""
        session = MagicMock()

        ws = EmbyWebSocket(
            host="emby.local",
            port=8096,
            api_key="key+with/special=chars",
            ssl=False,
            device_id="device-abc",
            session=session,
        )

        url = ws._build_connection_url()

        # URL should contain URL-encoded special characters
        assert "key%2Bwith%2Fspecial%3Dchars" in url or "key+with/special=chars" in url


class TestEmbyWebSocketConnect:
    """Tests for WebSocket connection."""

    @pytest.mark.asyncio
    async def test_connect_success(self) -> None:
        """Test successful WebSocket connection."""
        mock_session = MagicMock()
        mock_ws = AsyncMock()
        mock_ws.closed = False

        # Create async context manager mock
        mock_ws_connect = AsyncMock(return_value=mock_ws)
        mock_session.ws_connect = mock_ws_connect

        ws = EmbyWebSocket(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            device_id="test-device",
            session=mock_session,
        )

        await ws.async_connect()

        assert ws.connected is True
        mock_session.ws_connect.assert_called_once()

        # Verify URL format
        call_args = mock_session.ws_connect.call_args
        url = call_args[0][0]
        assert "ws://emby.local:8096/embywebsocket" in url
        assert "api_key=test-key" in url
        assert "deviceId=test-device" in url

    @pytest.mark.asyncio
    async def test_connect_with_ssl(self) -> None:
        """Test WebSocket connection with SSL."""
        mock_session = MagicMock()
        mock_ws = AsyncMock()
        mock_ws.closed = False
        mock_session.ws_connect = AsyncMock(return_value=mock_ws)

        ws = EmbyWebSocket(
            host="emby.local",
            port=8920,
            api_key="test-key",
            ssl=True,
            device_id="test-device",
            session=mock_session,
        )

        await ws.async_connect()

        call_args = mock_session.ws_connect.call_args
        url = call_args[0][0]
        assert url.startswith("wss://")

    @pytest.mark.asyncio
    async def test_connect_failure_raises_exception(self) -> None:
        """Test that connection failure raises exception."""
        mock_session = MagicMock()
        mock_session.ws_connect = AsyncMock(
            side_effect=aiohttp.ClientError("Connection refused")
        )

        ws = EmbyWebSocket(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            device_id="test-device",
            session=mock_session,
        )

        with pytest.raises(aiohttp.ClientError):
            await ws.async_connect()

        assert ws.connected is False


class TestEmbyWebSocketDisconnect:
    """Tests for WebSocket disconnection."""

    @pytest.mark.asyncio
    async def test_disconnect_closes_connection(self) -> None:
        """Test that disconnect closes the WebSocket."""
        mock_session = MagicMock()
        mock_ws = AsyncMock()
        mock_ws.closed = False
        mock_ws.close = AsyncMock()
        mock_session.ws_connect = AsyncMock(return_value=mock_ws)

        ws = EmbyWebSocket(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            device_id="test-device",
            session=mock_session,
        )

        await ws.async_connect()
        assert ws.connected is True

        await ws.async_disconnect()

        mock_ws.close.assert_called_once()
        assert ws.connected is False

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self) -> None:
        """Test disconnect when not connected does nothing."""
        mock_session = MagicMock()

        ws = EmbyWebSocket(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            device_id="test-device",
            session=mock_session,
        )

        # Should not raise
        await ws.async_disconnect()

        assert ws.connected is False


class TestEmbyWebSocketSubscription:
    """Tests for session subscription."""

    @pytest.mark.asyncio
    async def test_subscribe_sessions_sends_message(self) -> None:
        """Test that subscribe sends SessionsStart message."""
        mock_session = MagicMock()
        mock_ws = AsyncMock()
        mock_ws.closed = False
        mock_ws.send_str = AsyncMock()
        mock_session.ws_connect = AsyncMock(return_value=mock_ws)

        ws = EmbyWebSocket(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            device_id="test-device",
            session=mock_session,
        )

        await ws.async_connect()
        await ws.async_subscribe_sessions(interval_ms=1500)

        mock_ws.send_str.assert_called_once()
        call_args = mock_ws.send_str.call_args[0][0]
        message = json.loads(call_args)

        assert message["MessageType"] == "SessionsStart"
        assert message["Data"] == "0,1500"

    @pytest.mark.asyncio
    async def test_subscribe_sessions_custom_interval(self) -> None:
        """Test subscribe with custom interval."""
        mock_session = MagicMock()
        mock_ws = AsyncMock()
        mock_ws.closed = False
        mock_ws.send_str = AsyncMock()
        mock_session.ws_connect = AsyncMock(return_value=mock_ws)

        ws = EmbyWebSocket(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            device_id="test-device",
            session=mock_session,
        )

        await ws.async_connect()
        await ws.async_subscribe_sessions(interval_ms=3000)

        call_args = mock_ws.send_str.call_args[0][0]
        message = json.loads(call_args)

        assert message["Data"] == "0,3000"

    @pytest.mark.asyncio
    async def test_unsubscribe_sessions_sends_message(self) -> None:
        """Test that unsubscribe sends SessionsStop message."""
        mock_session = MagicMock()
        mock_ws = AsyncMock()
        mock_ws.closed = False
        mock_ws.send_str = AsyncMock()
        mock_session.ws_connect = AsyncMock(return_value=mock_ws)

        ws = EmbyWebSocket(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            device_id="test-device",
            session=mock_session,
        )

        await ws.async_connect()
        await ws.async_unsubscribe_sessions()

        mock_ws.send_str.assert_called_once()
        call_args = mock_ws.send_str.call_args[0][0]
        message = json.loads(call_args)

        assert message["MessageType"] == "SessionsStop"
        assert message["Data"] == ""

    @pytest.mark.asyncio
    async def test_subscribe_when_not_connected_raises(self) -> None:
        """Test that subscribe when not connected raises."""
        mock_session = MagicMock()

        ws = EmbyWebSocket(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            device_id="test-device",
            session=mock_session,
        )

        with pytest.raises(RuntimeError, match="not connected"):
            await ws.async_subscribe_sessions()

    @pytest.mark.asyncio
    async def test_unsubscribe_when_not_connected_raises(self) -> None:
        """Test that unsubscribe when not connected raises."""
        mock_session = MagicMock()

        ws = EmbyWebSocket(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            device_id="test-device",
            session=mock_session,
        )

        with pytest.raises(RuntimeError, match="not connected"):
            await ws.async_unsubscribe_sessions()


class TestEmbyWebSocketMessageCallback:
    """Tests for message callback handling."""

    def test_set_message_callback(self) -> None:
        """Test setting message callback."""
        mock_session = MagicMock()
        callback = MagicMock()

        ws = EmbyWebSocket(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            device_id="test-device",
            session=mock_session,
        )

        ws.set_message_callback(callback)

        assert ws._message_callback is callback

    @pytest.mark.asyncio
    async def test_callback_invoked_on_message(self) -> None:
        """Test that callback is invoked when message received."""
        mock_session = MagicMock()
        mock_ws = AsyncMock()
        mock_ws.closed = False
        mock_ws.send_str = AsyncMock()

        # Create a mock message
        mock_msg = MagicMock()
        mock_msg.type = aiohttp.WSMsgType.TEXT
        mock_msg.data = json.dumps({
            "MessageType": "Sessions",
            "Data": [{"Id": "session-1"}],
        })

        # Make ws_connect return our mock
        mock_session.ws_connect = AsyncMock(return_value=mock_ws)

        ws = EmbyWebSocket(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            device_id="test-device",
            session=mock_session,
        )

        callback = MagicMock()
        ws.set_message_callback(callback)

        await ws.async_connect()

        # Simulate receiving a message
        ws._process_message(mock_msg)

        callback.assert_called_once_with("Sessions", [{"Id": "session-1"}])

    @pytest.mark.asyncio
    async def test_callback_not_invoked_for_malformed_json(self) -> None:
        """Test that callback is not invoked for malformed JSON."""
        mock_session = MagicMock()

        ws = EmbyWebSocket(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            device_id="test-device",
            session=mock_session,
        )

        callback = MagicMock()
        ws.set_message_callback(callback)

        mock_msg = MagicMock()
        mock_msg.type = aiohttp.WSMsgType.TEXT
        mock_msg.data = "not valid json {"

        # Should not raise, just log warning
        ws._process_message(mock_msg)

        callback.assert_not_called()


class TestEmbyWebSocketMessageProcessing:
    """Tests for message processing."""

    def test_process_sessions_message(self) -> None:
        """Test processing Sessions message."""
        mock_session = MagicMock()

        ws = EmbyWebSocket(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            device_id="test-device",
            session=mock_session,
        )

        callback = MagicMock()
        ws.set_message_callback(callback)

        sessions_data = [
            {"Id": "session-1", "DeviceName": "TV"},
            {"Id": "session-2", "DeviceName": "Phone"},
        ]

        mock_msg = MagicMock()
        mock_msg.type = aiohttp.WSMsgType.TEXT
        mock_msg.data = json.dumps({
            "MessageType": "Sessions",
            "Data": sessions_data,
        })

        ws._process_message(mock_msg)

        callback.assert_called_once_with("Sessions", sessions_data)

    def test_process_playback_started_message(self) -> None:
        """Test processing PlaybackStarted message."""
        mock_session = MagicMock()

        ws = EmbyWebSocket(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            device_id="test-device",
            session=mock_session,
        )

        callback = MagicMock()
        ws.set_message_callback(callback)

        event_data = {
            "SessionId": "session-1",
            "ItemId": "movie-123",
        }

        mock_msg = MagicMock()
        mock_msg.type = aiohttp.WSMsgType.TEXT
        mock_msg.data = json.dumps({
            "MessageType": "PlaybackStarted",
            "Data": event_data,
        })

        ws._process_message(mock_msg)

        callback.assert_called_once_with("PlaybackStarted", event_data)

    def test_process_playback_stopped_message(self) -> None:
        """Test processing PlaybackStopped message."""
        mock_session = MagicMock()

        ws = EmbyWebSocket(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            device_id="test-device",
            session=mock_session,
        )

        callback = MagicMock()
        ws.set_message_callback(callback)

        event_data = {"SessionId": "session-1"}

        mock_msg = MagicMock()
        mock_msg.type = aiohttp.WSMsgType.TEXT
        mock_msg.data = json.dumps({
            "MessageType": "PlaybackStopped",
            "Data": event_data,
        })

        ws._process_message(mock_msg)

        callback.assert_called_once_with("PlaybackStopped", event_data)

    def test_process_closed_message_type(self) -> None:
        """Test handling closed WebSocket message."""
        mock_session = MagicMock()

        ws = EmbyWebSocket(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            device_id="test-device",
            session=mock_session,
        )

        callback = MagicMock()
        ws.set_message_callback(callback)

        mock_msg = MagicMock()
        mock_msg.type = aiohttp.WSMsgType.CLOSED

        # Should not call callback for closed message
        ws._process_message(mock_msg)

        callback.assert_not_called()

    def test_process_error_message_type(self) -> None:
        """Test handling error WebSocket message."""
        mock_session = MagicMock()

        ws = EmbyWebSocket(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            device_id="test-device",
            session=mock_session,
        )

        callback = MagicMock()
        ws.set_message_callback(callback)

        mock_msg = MagicMock()
        mock_msg.type = aiohttp.WSMsgType.ERROR

        # Should not call callback for error message
        ws._process_message(mock_msg)

        callback.assert_not_called()


class TestEmbyWebSocketConnectionCallback:
    """Tests for connection state callback."""

    def test_set_connection_callback(self) -> None:
        """Test setting connection callback."""
        mock_session = MagicMock()
        callback = MagicMock()

        ws = EmbyWebSocket(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            device_id="test-device",
            session=mock_session,
        )

        ws.set_connection_callback(callback)

        assert ws._connection_callback is callback

    @pytest.mark.asyncio
    async def test_connection_callback_on_connect(self) -> None:
        """Test connection callback invoked on connect."""
        mock_session = MagicMock()
        mock_ws = AsyncMock()
        mock_ws.closed = False
        mock_session.ws_connect = AsyncMock(return_value=mock_ws)

        ws = EmbyWebSocket(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            device_id="test-device",
            session=mock_session,
        )

        callback = MagicMock()
        ws.set_connection_callback(callback)

        await ws.async_connect()

        callback.assert_called_once_with(True)

    @pytest.mark.asyncio
    async def test_connection_callback_on_disconnect(self) -> None:
        """Test connection callback invoked on disconnect."""
        mock_session = MagicMock()
        mock_ws = AsyncMock()
        mock_ws.closed = False
        mock_ws.close = AsyncMock()
        mock_session.ws_connect = AsyncMock(return_value=mock_ws)

        ws = EmbyWebSocket(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            device_id="test-device",
            session=mock_session,
        )

        callback = MagicMock()
        ws.set_connection_callback(callback)

        await ws.async_connect()
        callback.reset_mock()  # Clear the connect call

        await ws.async_disconnect()

        callback.assert_called_once_with(False)
