"""Tests for coordinator resilience and error handling (Phase 9.1)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.embymedia.const import CONF_API_KEY, DOMAIN
from custom_components.embymedia.exceptions import EmbyConnectionError

if TYPE_CHECKING:
    from custom_components.embymedia.const import EmbyConfigEntry


@pytest.fixture
def mock_emby_client() -> MagicMock:
    """Create a mock Emby API client."""
    client = MagicMock()
    client.async_get_sessions = AsyncMock(return_value=[])
    client.async_get_server_info = AsyncMock(return_value={"Id": "server-123"})
    return client


@pytest.fixture
def mock_config_entry(hass: HomeAssistant) -> EmbyConfigEntry:
    """Create a mock config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "emby.local",
            "port": 8096,
            CONF_API_KEY: "test-api-key",
        },
        options={},
        unique_id="server-123",
    )
    entry.add_to_hass(hass)
    return entry  # type: ignore[return-value]


@pytest.fixture
def mock_session_data() -> list[dict[str, object]]:
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
    ]


class TestGracefulDegradation:
    """Test graceful degradation on partial failures."""

    @pytest.mark.asyncio
    async def test_coordinator_uses_cached_data_on_failure(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: EmbyConfigEntry,
        mock_session_data: list[dict[str, object]],
    ) -> None:
        """Test coordinator returns cached data on connection failure."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        # First call succeeds with data
        mock_emby_client.async_get_sessions = AsyncMock(return_value=mock_session_data)

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Fetch initial data successfully
        await coordinator.async_refresh()
        assert coordinator.data is not None
        assert len(coordinator.data) == 1

        # Now simulate connection failure
        mock_emby_client.async_get_sessions = AsyncMock(
            side_effect=EmbyConnectionError("Connection refused")
        )

        # Should return cached data instead of raising UpdateFailed
        data = await coordinator._async_update_data()
        assert data is not None
        assert len(data) == 1
        assert "device-abc" in data

    @pytest.mark.asyncio
    async def test_coordinator_raises_on_first_failure(
        self, hass: HomeAssistant, mock_emby_client: MagicMock, mock_config_entry: EmbyConfigEntry
    ) -> None:
        """Test coordinator raises UpdateFailed on first connection failure (no cached data)."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_emby_client.async_get_sessions = AsyncMock(
            side_effect=EmbyConnectionError("Connection refused")
        )

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # No cached data, should raise UpdateFailed
        with pytest.raises(UpdateFailed) as exc_info:
            await coordinator._async_update_data()
        assert "Failed to connect" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_coordinator_handles_partial_session_data(
        self, hass: HomeAssistant, mock_emby_client: MagicMock, mock_config_entry: EmbyConfigEntry
    ) -> None:
        """Test coordinator continues processing when some sessions fail to parse."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        # Mix of valid and invalid sessions
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
                    # Invalid session - missing DeviceId
                    "Id": "session-bad",
                    "Client": "Bad Client",
                    "DeviceName": "Bad Device",
                    "SupportsRemoteControl": True,
                },
                {
                    "Id": "session-2",
                    "Client": "Emby Mobile",
                    "DeviceId": "device-def",
                    "DeviceName": "Phone",
                    "SupportsRemoteControl": True,
                },
            ]
        )

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Should succeed and have 2 valid sessions
        data = await coordinator._async_update_data()
        assert len(data) == 2
        assert "device-abc" in data
        assert "device-def" in data

    @pytest.mark.asyncio
    async def test_cached_data_warning_logged(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: EmbyConfigEntry,
        mock_session_data: list[dict[str, object]],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test warning is logged when using cached data."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_emby_client.async_get_sessions = AsyncMock(return_value=mock_session_data)

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Get initial data
        await coordinator.async_refresh()

        # Simulate failure
        mock_emby_client.async_get_sessions = AsyncMock(
            side_effect=EmbyConnectionError("Connection refused")
        )

        with caplog.at_level("WARNING"):
            await coordinator._async_update_data()

        assert "Failed to fetch sessions, using cached data" in caplog.text


class TestAutomaticRecovery:
    """Test automatic recovery mechanisms."""

    @pytest.mark.asyncio
    async def test_consecutive_failure_tracking(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: EmbyConfigEntry,
        mock_session_data: list[dict[str, object]],
    ) -> None:
        """Test consecutive failures are tracked."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        # First success to get cached data
        mock_emby_client.async_get_sessions = AsyncMock(return_value=mock_session_data)

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        await coordinator.async_refresh()
        assert coordinator._consecutive_failures == 0

        # Now fail multiple times
        mock_emby_client.async_get_sessions = AsyncMock(
            side_effect=EmbyConnectionError("Connection refused")
        )

        # Each call should increment failure count
        await coordinator._async_update_data()
        assert coordinator._consecutive_failures == 1

        await coordinator._async_update_data()
        assert coordinator._consecutive_failures == 2

    @pytest.mark.asyncio
    async def test_automatic_recovery_triggered(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: EmbyConfigEntry,
        mock_session_data: list[dict[str, object]],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test automatic recovery is triggered after threshold failures."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        # First success
        mock_emby_client.async_get_sessions = AsyncMock(return_value=mock_session_data)

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        await coordinator.async_refresh()

        # Set threshold low for testing
        coordinator._max_consecutive_failures = 3

        # Simulate failures
        mock_emby_client.async_get_sessions = AsyncMock(
            side_effect=EmbyConnectionError("Connection refused")
        )

        # Fail 3 times (threshold)
        with caplog.at_level("INFO"):
            for _ in range(3):
                await coordinator._async_update_data()

        assert "Attempting automatic recovery" in caplog.text

    @pytest.mark.asyncio
    async def test_recovery_resets_failure_count(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: EmbyConfigEntry,
        mock_session_data: list[dict[str, object]],
    ) -> None:
        """Test successful fetch resets failure count."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        # First success
        mock_emby_client.async_get_sessions = AsyncMock(return_value=mock_session_data)

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        await coordinator.async_refresh()

        # Simulate failures
        mock_emby_client.async_get_sessions = AsyncMock(
            side_effect=EmbyConnectionError("Connection refused")
        )
        await coordinator._async_update_data()
        await coordinator._async_update_data()
        assert coordinator._consecutive_failures == 2

        # Recover
        mock_emby_client.async_get_sessions = AsyncMock(return_value=mock_session_data)
        await coordinator._async_update_data()
        assert coordinator._consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_recovery_attempts_websocket_reconnect(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: EmbyConfigEntry,
        mock_session_data: list[dict[str, object]],
    ) -> None:
        """Test recovery attempts to reconnect WebSocket."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_emby_client.async_get_sessions = AsyncMock(return_value=mock_session_data)

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        await coordinator.async_refresh()

        # Mock websocket
        mock_ws = MagicMock()
        mock_ws.async_start_reconnect_loop = AsyncMock()
        coordinator._websocket = mock_ws
        coordinator._max_consecutive_failures = 1

        # Simulate failure to trigger recovery
        mock_emby_client.async_get_sessions = AsyncMock(
            side_effect=EmbyConnectionError("Connection refused")
        )

        await coordinator._async_update_data()

        # Should have attempted to reconnect websocket
        mock_ws.async_start_reconnect_loop.assert_called_once()

    @pytest.mark.asyncio
    async def test_recovery_success_logged(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: EmbyConfigEntry,
        mock_session_data: list[dict[str, object]],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test successful recovery is logged."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_emby_client.async_get_sessions = AsyncMock(return_value=mock_session_data)

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        await coordinator.async_refresh()
        coordinator._max_consecutive_failures = 1

        # First call will fail
        mock_emby_client.async_get_sessions = AsyncMock(
            side_effect=EmbyConnectionError("Connection refused")
        )

        with caplog.at_level("INFO"):
            await coordinator._async_update_data()

        assert "Recovery successful" in caplog.text

    @pytest.mark.asyncio
    async def test_recovery_failure_logged(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: EmbyConfigEntry,
        mock_session_data: list[dict[str, object]],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test failed recovery is logged."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_emby_client.async_get_sessions = AsyncMock(return_value=mock_session_data)

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        await coordinator.async_refresh()
        coordinator._max_consecutive_failures = 1

        # Both session fetch and server info will fail
        mock_emby_client.async_get_sessions = AsyncMock(
            side_effect=EmbyConnectionError("Connection refused")
        )
        mock_emby_client.async_get_server_info = AsyncMock(
            side_effect=EmbyConnectionError("Still failing")
        )

        with caplog.at_level("WARNING"):
            await coordinator._async_update_data()

        assert "Recovery failed" in caplog.text


class TestExceptionTranslation:
    """Test exception translation support."""

    def test_exception_translation_key(self) -> None:
        """Test exception has translation key."""
        from custom_components.embymedia.exceptions import EmbyConnectionError

        exc = EmbyConnectionError(
            "Connection failed",
            host="emby.local",
            port=8096,
        )
        assert exc.translation_key == "connection_failed"

    def test_exception_placeholders(self) -> None:
        """Test exception placeholders are filled."""
        from custom_components.embymedia.exceptions import EmbyConnectionError

        exc = EmbyConnectionError(
            "Connection failed",
            host="emby.local",
            port=8096,
        )
        assert exc.translation_placeholders["host"] == "emby.local"
        assert exc.translation_placeholders["port"] == "8096"

    def test_authentication_error_translation(self) -> None:
        """Test authentication error has translation."""
        from custom_components.embymedia.exceptions import EmbyAuthenticationError

        exc = EmbyAuthenticationError("Invalid API key")
        assert exc.translation_key == "authentication_failed"

    def test_server_error_translation(self) -> None:
        """Test server error has translation."""
        from custom_components.embymedia.exceptions import EmbyServerError

        exc = EmbyServerError("Server returned 500")
        assert exc.translation_key == "server_error"

    def test_base_exception_no_translation(self) -> None:
        """Test base exception without translation works."""
        from custom_components.embymedia.exceptions import EmbyError

        exc = EmbyError("Generic error")
        assert exc.translation_key is None
        assert exc.translation_placeholders == {}
