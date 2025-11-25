"""Tests for Emby data update coordinator."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.embymedia.const import DEFAULT_SCAN_INTERVAL, DOMAIN
from custom_components.embymedia.exceptions import (
    EmbyAuthenticationError,
    EmbyConnectionError,
)

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_emby_client() -> MagicMock:
    """Create a mock Emby API client."""
    client = MagicMock()
    client.async_get_sessions = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_session_data() -> list[dict]:
    """Create mock session data from API."""
    return [
        {
            "Id": "session-1",
            "Client": "Emby Theater",
            "DeviceId": "device-abc",
            "DeviceName": "Living Room TV",
            "SupportsRemoteControl": True,
            "UserId": "user-123",
            "UserName": "TestUser",
        },
        {
            "Id": "session-2",
            "Client": "Emby Mobile",
            "DeviceId": "device-def",
            "DeviceName": "Phone",
            "SupportsRemoteControl": True,
        },
        {
            "Id": "session-3",
            "Client": "Emby Server",
            "DeviceId": "device-ghi",
            "DeviceName": "Server",
            "SupportsRemoteControl": False,  # Should be filtered out
        },
    ]


class TestCoordinatorInitialization:
    """Test coordinator initialization."""

    def test_coordinator_init(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test coordinator initializes with correct parameters."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            scan_interval=30,
        )

        assert coordinator.client is mock_emby_client
        assert coordinator.server_id == "server-123"
        assert coordinator.server_name == "Test Server"
        assert coordinator.update_interval == timedelta(seconds=30)
        assert coordinator.name == f"{DOMAIN}_server-123"

    def test_coordinator_default_scan_interval(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test coordinator uses default scan interval."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        assert coordinator.update_interval == timedelta(seconds=DEFAULT_SCAN_INTERVAL)


class TestCoordinatorDataFetch:
    """Test coordinator data fetching."""

    @pytest.mark.asyncio
    async def test_fetch_sessions_success(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_session_data: list[dict],
    ) -> None:
        """Test successful session data fetch."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_emby_client.async_get_sessions = AsyncMock(return_value=mock_session_data)

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        data = await coordinator._async_update_data()

        # Should have 2 sessions (the one without remote control filtered out)
        assert len(data) == 2
        assert "device-abc" in data
        assert "device-def" in data
        assert "device-ghi" not in data  # Filtered out

        # Verify parsed data
        session = data["device-abc"]
        assert session.device_name == "Living Room TV"
        assert session.client_name == "Emby Theater"

    @pytest.mark.asyncio
    async def test_fetch_sessions_empty(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test handling empty sessions list."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_emby_client.async_get_sessions = AsyncMock(return_value=[])

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        data = await coordinator._async_update_data()
        assert data == {}

    @pytest.mark.asyncio
    async def test_fetch_sessions_connection_error(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test connection error raises UpdateFailed."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_emby_client.async_get_sessions = AsyncMock(
            side_effect=EmbyConnectionError("Connection refused")
        )

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        with pytest.raises(UpdateFailed) as exc_info:
            await coordinator._async_update_data()
        assert "Failed to connect" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_sessions_auth_error(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test authentication error raises UpdateFailed."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_emby_client.async_get_sessions = AsyncMock(
            side_effect=EmbyAuthenticationError("Invalid API key")
        )

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        with pytest.raises(UpdateFailed) as exc_info:
            await coordinator._async_update_data()
        assert "Error fetching sessions" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_sessions_parsing_error_skipped(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test sessions with parsing errors are skipped."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        # One valid session, one with missing required fields
        mock_emby_client.async_get_sessions = AsyncMock(
            return_value=[
                {
                    "Id": "session-1",
                    "Client": "Emby Theater",
                    "DeviceId": "device-abc",
                    "DeviceName": "Living Room TV",
                    "SupportsRemoteControl": True,
                },
                {
                    # Missing required fields like DeviceId
                    "Id": "session-bad",
                    "Client": "Bad Client",
                    "SupportsRemoteControl": True,
                },
            ]
        )

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        data = await coordinator._async_update_data()

        # Should have only the valid session
        assert len(data) == 1
        assert "device-abc" in data


class TestCoordinatorGetSession:
    """Test coordinator get_session helper."""

    @pytest.mark.asyncio
    async def test_get_session_exists(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_session_data: list[dict],
    ) -> None:
        """Test getting existing session."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_emby_client.async_get_sessions = AsyncMock(return_value=mock_session_data)

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        # Fetch data using async_refresh which properly sets self.data
        await coordinator.async_refresh()

        session = coordinator.get_session("device-abc")
        assert session is not None
        assert session.device_name == "Living Room TV"

    @pytest.mark.asyncio
    async def test_get_session_not_exists(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_session_data: list[dict],
    ) -> None:
        """Test getting non-existent session."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_emby_client.async_get_sessions = AsyncMock(return_value=mock_session_data)

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        # Fetch data first
        await coordinator._async_update_data()

        session = coordinator.get_session("device-xyz")
        assert session is None

    def test_get_session_no_data(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test getting session when no data fetched yet."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        # No data fetched yet
        session = coordinator.get_session("device-abc")
        assert session is None


class TestCoordinatorSessionTracking:
    """Test coordinator session addition/removal tracking."""

    @pytest.mark.asyncio
    async def test_new_session_logged(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test new sessions are logged."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_emby_client.async_get_sessions = AsyncMock(
            return_value=[
                {
                    "Id": "session-1",
                    "Client": "Emby Theater",
                    "DeviceId": "device-abc",
                    "DeviceName": "Living Room TV",
                    "SupportsRemoteControl": True,
                },
            ]
        )

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        with caplog.at_level("DEBUG"):
            await coordinator._async_update_data()

        assert "New session detected: Living Room TV" in caplog.text

    @pytest.mark.asyncio
    async def test_removed_session_logged(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test removed sessions are logged."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        # First fetch with a session
        mock_emby_client.async_get_sessions = AsyncMock(
            return_value=[
                {
                    "Id": "session-1",
                    "Client": "Emby Theater",
                    "DeviceId": "device-abc",
                    "DeviceName": "Living Room TV",
                    "SupportsRemoteControl": True,
                },
            ]
        )
        await coordinator._async_update_data()

        # Second fetch without the session
        mock_emby_client.async_get_sessions = AsyncMock(return_value=[])

        with caplog.at_level("DEBUG"):
            await coordinator._async_update_data()

        assert "Session removed: device-abc" in caplog.text


class TestCoordinatorWebSocket:
    """Test coordinator WebSocket integration."""

    @pytest.fixture
    def mock_aiohttp_session(self) -> MagicMock:
        """Create a mock aiohttp session."""
        session = MagicMock()
        session.ws_connect = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_setup_websocket(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test WebSocket setup creates connection."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_emby_client.host = "emby.local"
        mock_emby_client.port = 8096
        mock_emby_client.api_key = "test-key"
        mock_emby_client.ssl = False

        # Mock WebSocket that succeeds and stays connected
        mock_ws = AsyncMock()
        mock_ws.closed = False
        mock_ws.close = AsyncMock()
        mock_ws.send_str = AsyncMock()

        # Make it an async iterator that never yields (stays connected)
        async def infinite_wait() -> None:
            import asyncio

            await asyncio.sleep(1000)

        mock_ws.__aiter__ = lambda self: self
        mock_ws.__anext__ = lambda self: infinite_wait()
        mock_aiohttp_session.ws_connect = AsyncMock(return_value=mock_ws)

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        # Setup WebSocket
        await coordinator.async_setup_websocket(mock_aiohttp_session)

        assert coordinator.websocket is not None
        assert coordinator.websocket_enabled is True

    @pytest.mark.asyncio
    async def test_shutdown_websocket(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test WebSocket shutdown closes connection."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_emby_client.host = "emby.local"
        mock_emby_client.port = 8096
        mock_emby_client.api_key = "test-key"
        mock_emby_client.ssl = False

        # Mock WebSocket that succeeds and stays connected
        mock_ws = AsyncMock()
        mock_ws.closed = False
        mock_ws.close = AsyncMock()
        mock_ws.send_str = AsyncMock()

        # Make it an async iterator that never yields (stays connected)
        async def infinite_wait() -> None:
            import asyncio

            await asyncio.sleep(1000)

        mock_ws.__aiter__ = lambda self: self
        mock_ws.__anext__ = lambda self: infinite_wait()
        mock_aiohttp_session.ws_connect = AsyncMock(return_value=mock_ws)

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        await coordinator.async_setup_websocket(mock_aiohttp_session)
        await coordinator.async_shutdown_websocket()

        assert coordinator.websocket is None

    @pytest.mark.asyncio
    async def test_handle_sessions_message(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test handling Sessions message updates coordinator data."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_emby_client.async_get_sessions = AsyncMock(return_value=[])

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        # Initialize data first
        await coordinator.async_refresh()

        # Simulate receiving Sessions message via WebSocket
        sessions_data = [
            {
                "Id": "session-1",
                "Client": "Emby Theater",
                "DeviceId": "device-abc",
                "DeviceName": "Living Room TV",
                "SupportsRemoteControl": True,
            },
        ]

        coordinator._handle_websocket_message("Sessions", sessions_data)

        # Data should be updated
        assert coordinator.data is not None
        assert "device-abc" in coordinator.data

    @pytest.mark.asyncio
    async def test_handle_playback_started_message(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test handling PlaybackStarted triggers refresh."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_emby_client.async_get_sessions = AsyncMock(return_value=[])

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        await coordinator.async_refresh()
        mock_emby_client.async_get_sessions.reset_mock()

        # Simulate PlaybackStarted event
        coordinator._handle_websocket_message("PlaybackStarted", {"SessionId": "123"})

        # Should trigger a refresh
        mock_emby_client.async_get_sessions.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_playback_stopped_message(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test handling PlaybackStopped triggers refresh."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_emby_client.async_get_sessions = AsyncMock(return_value=[])

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        await coordinator.async_refresh()
        mock_emby_client.async_get_sessions.reset_mock()

        # Simulate PlaybackStopped event
        coordinator._handle_websocket_message("PlaybackStopped", {"SessionId": "123"})

        # Should trigger a refresh
        mock_emby_client.async_get_sessions.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_connection_callback(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_aiohttp_session: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test WebSocket connection state changes are logged."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_emby_client.host = "emby.local"
        mock_emby_client.port = 8096
        mock_emby_client.api_key = "test-key"
        mock_emby_client.ssl = False

        # Mock WebSocket that succeeds and stays connected
        mock_ws = AsyncMock()
        mock_ws.closed = False
        mock_ws.close = AsyncMock()
        mock_ws.send_str = AsyncMock()

        # Make it an async iterator that never yields (stays connected)
        async def infinite_wait() -> None:
            import asyncio

            await asyncio.sleep(1000)

        mock_ws.__aiter__ = lambda self: self
        mock_ws.__anext__ = lambda self: infinite_wait()

        mock_aiohttp_session.ws_connect = AsyncMock(return_value=mock_ws)

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        with caplog.at_level("INFO"):
            await coordinator.async_setup_websocket(mock_aiohttp_session)

        assert "WebSocket connected" in caplog.text
        assert coordinator.websocket_enabled is True

    @pytest.mark.asyncio
    async def test_setup_websocket_connection_failure(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_aiohttp_session: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test WebSocket setup handles connection failure."""
        import aiohttp

        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_emby_client.host = "emby.local"
        mock_emby_client.port = 8096
        mock_emby_client.api_key = "test-key"
        mock_emby_client.ssl = False

        # Mock WebSocket that fails
        mock_aiohttp_session.ws_connect = AsyncMock(
            side_effect=aiohttp.ClientError("Connection refused")
        )

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        with caplog.at_level("WARNING"):
            await coordinator.async_setup_websocket(mock_aiohttp_session)

        assert coordinator.websocket_enabled is False
        assert "Failed to connect WebSocket" in caplog.text

    @pytest.mark.asyncio
    async def test_handle_unknown_message_type(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test handling unknown WebSocket message type logs debug."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        with caplog.at_level("DEBUG"):
            coordinator._handle_websocket_message("UnknownType", {"data": "test"})

        assert "Unhandled WebSocket message type: UnknownType" in caplog.text

    @pytest.mark.asyncio
    async def test_handle_sessions_message_with_parsing_error(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test handling Sessions message with invalid session data."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_emby_client.async_get_sessions = AsyncMock(return_value=[])

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        # Initialize data first
        await coordinator.async_refresh()

        # Simulate receiving Sessions message with invalid data
        sessions_data = [
            {
                # Missing required fields
                "Id": "session-1",
                "Client": "Emby Theater",
                "DeviceName": "Bad Device",
                # Missing DeviceId which is required
            },
        ]

        with caplog.at_level("WARNING"):
            coordinator._handle_websocket_message("Sessions", sessions_data)

        assert "Failed to parse session data from WebSocket" in caplog.text

    @pytest.mark.asyncio
    async def test_handle_sessions_message_removes_session(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test handling Sessions message logs removed sessions."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_emby_client.async_get_sessions = AsyncMock(return_value=[])

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        # Initialize data first
        await coordinator.async_refresh()

        # Add a session via WebSocket
        sessions_data = [
            {
                "Id": "session-1",
                "Client": "Emby Theater",
                "DeviceId": "device-abc",
                "DeviceName": "Living Room TV",
                "SupportsRemoteControl": True,
            },
        ]
        coordinator._handle_websocket_message("Sessions", sessions_data)

        # Now remove the session by sending empty list
        with caplog.at_level("DEBUG"):
            coordinator._handle_websocket_message("Sessions", [])

        assert "Session removed: device-abc" in caplog.text

    @pytest.mark.asyncio
    async def test_websocket_disconnect_callback(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test WebSocket disconnect callback logs warning."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        with caplog.at_level("WARNING"):
            coordinator._handle_websocket_connection(False)

        assert "WebSocket disconnected from Emby server" in caplog.text

    @pytest.mark.asyncio
    async def test_websocket_receive_loop_no_websocket(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test receive loop returns early when websocket is None."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        # Websocket is None by default
        assert coordinator._websocket is None

        # Should return early without error
        await coordinator._async_websocket_receive_loop()

    @pytest.mark.asyncio
    async def test_websocket_receive_loop_exception(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test receive loop handles exceptions from websocket."""
        from unittest.mock import MagicMock as SyncMagicMock

        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        # Create a mock websocket that raises an exception
        mock_ws = SyncMagicMock()
        mock_ws._async_receive_loop = AsyncMock(
            side_effect=RuntimeError("Connection lost")
        )

        coordinator._websocket = mock_ws
        coordinator._websocket_enabled = True

        with caplog.at_level("WARNING"):
            await coordinator._async_websocket_receive_loop()

        assert "WebSocket receive loop error" in caplog.text
        assert "Connection lost" in caplog.text


class TestCoordinatorHybridPolling:
    """Test coordinator hybrid polling mode."""

    @pytest.fixture
    def mock_aiohttp_session(self) -> MagicMock:
        """Create a mock aiohttp session."""
        session = MagicMock()
        session.ws_connect = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_poll_interval_with_websocket(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test reduced polling interval when WebSocket is connected."""
        from datetime import timedelta

        from custom_components.embymedia.const import WEBSOCKET_POLL_INTERVAL
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_emby_client.host = "emby.local"
        mock_emby_client.port = 8096
        mock_emby_client.api_key = "test-key"
        mock_emby_client.ssl = False

        # Mock WebSocket that succeeds and stays connected
        mock_ws = AsyncMock()
        mock_ws.closed = False
        mock_ws.close = AsyncMock()
        mock_ws.send_str = AsyncMock()

        # Make it an async iterator that never yields (stays connected)
        async def infinite_wait() -> None:
            import asyncio

            await asyncio.sleep(1000)

        mock_ws.__aiter__ = lambda self: self
        mock_ws.__anext__ = lambda self: infinite_wait()

        mock_aiohttp_session.ws_connect = AsyncMock(return_value=mock_ws)

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        await coordinator.async_setup_websocket(mock_aiohttp_session)

        # Should use reduced polling interval
        assert coordinator.update_interval == timedelta(seconds=WEBSOCKET_POLL_INTERVAL)

    @pytest.mark.asyncio
    async def test_poll_interval_without_websocket(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test normal polling interval without WebSocket."""
        from datetime import timedelta

        from custom_components.embymedia.const import DEFAULT_SCAN_INTERVAL
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        # No WebSocket setup, should use default interval
        assert coordinator.update_interval == timedelta(seconds=DEFAULT_SCAN_INTERVAL)

    @pytest.mark.asyncio
    async def test_poll_interval_on_websocket_disconnect(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_aiohttp_session: MagicMock,
    ) -> None:
        """Test polling interval increases on WebSocket disconnect."""
        from datetime import timedelta

        from custom_components.embymedia.const import (
            DEFAULT_SCAN_INTERVAL,
            WEBSOCKET_POLL_INTERVAL,
        )
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_emby_client.host = "emby.local"
        mock_emby_client.port = 8096
        mock_emby_client.api_key = "test-key"
        mock_emby_client.ssl = False

        # Mock WebSocket that succeeds and stays connected
        mock_ws = AsyncMock()
        mock_ws.closed = False
        mock_ws.close = AsyncMock()
        mock_ws.send_str = AsyncMock()

        # Make it an async iterator that never yields (stays connected)
        async def infinite_wait() -> None:
            import asyncio

            await asyncio.sleep(1000)

        mock_ws.__aiter__ = lambda self: self
        mock_ws.__anext__ = lambda self: infinite_wait()
        mock_aiohttp_session.ws_connect = AsyncMock(return_value=mock_ws)

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        await coordinator.async_setup_websocket(mock_aiohttp_session)

        # Initially should have reduced interval
        assert coordinator.update_interval == timedelta(seconds=WEBSOCKET_POLL_INTERVAL)

        # Simulate WebSocket disconnect callback
        coordinator._handle_websocket_connection(False)

        # Should revert to default interval
        assert coordinator.update_interval == timedelta(seconds=DEFAULT_SCAN_INTERVAL)

    @pytest.mark.asyncio
    async def test_poll_interval_restores_on_reconnect(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test polling interval reduces on WebSocket reconnect."""
        from datetime import timedelta

        from custom_components.embymedia.const import WEBSOCKET_POLL_INTERVAL
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        # Simulate WebSocket reconnect
        coordinator._handle_websocket_connection(True)

        # Should use reduced interval
        assert coordinator.update_interval == timedelta(seconds=WEBSOCKET_POLL_INTERVAL)

    @pytest.mark.asyncio
    async def test_fallback_to_polling_logged(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_aiohttp_session: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test fallback to polling is logged."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_emby_client.host = "emby.local"
        mock_emby_client.port = 8096
        mock_emby_client.api_key = "test-key"
        mock_emby_client.ssl = False

        # Mock WebSocket that succeeds
        mock_ws = AsyncMock()
        mock_ws.closed = False
        mock_ws.close = AsyncMock()
        mock_aiohttp_session.ws_connect = AsyncMock(return_value=mock_ws)

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        await coordinator.async_setup_websocket(mock_aiohttp_session)

        with caplog.at_level("WARNING"):
            coordinator._handle_websocket_connection(False)

        assert "Using polling fallback" in caplog.text

    @pytest.mark.asyncio
    async def test_reduced_polling_logged(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test reduced polling is logged on connect."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        with caplog.at_level("INFO"):
            coordinator._handle_websocket_connection(True)

        assert "reducing poll interval" in caplog.text


class TestCoordinatorServerEvents:
    """Test coordinator handling of server events."""

    @pytest.mark.asyncio
    async def test_handle_server_restarting(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test handling ServerRestarting event."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        with caplog.at_level("INFO"):
            coordinator._handle_websocket_message("ServerRestarting", None)

        assert "Server is restarting" in caplog.text

    @pytest.mark.asyncio
    async def test_handle_server_shutting_down(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test handling ServerShuttingDown event."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        with caplog.at_level("WARNING"):
            coordinator._handle_websocket_message("ServerShuttingDown", None)

        assert "Server is shutting down" in caplog.text

    @pytest.mark.asyncio
    async def test_handle_session_ended(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test handling SessionEnded event triggers refresh."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_emby_client.async_get_sessions = AsyncMock(return_value=[])

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
        )

        await coordinator.async_refresh()
        mock_emby_client.async_get_sessions.reset_mock()

        # Simulate SessionEnded event
        coordinator._handle_websocket_message("SessionEnded", {"SessionId": "123"})

        # Should trigger a refresh
        mock_emby_client.async_get_sessions.assert_called_once()
