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
