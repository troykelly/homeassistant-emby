"""Tests for WebSocket-based polling optimization (Issue #287).

These tests verify that polling is disabled when WebSocket is stable,
and re-enabled as a fallback when WebSocket fails.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.embymedia.const import (
    DEFAULT_SCAN_INTERVAL,
)
from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock Emby client."""
    client = MagicMock()
    client.host = "emby.local"
    client.port = 8096
    client.api_key = "test-api-key"
    client.ssl = False
    client.async_get_sessions = AsyncMock(return_value=[])
    client.async_get_server_info = AsyncMock(return_value={"ServerName": "Test"})
    client.async_ping = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_config_entry() -> MagicMock:
    """Create a mock config entry."""
    entry = MagicMock()
    entry.options = {}
    return entry


class TestWebSocketStabilityTracking:
    """Tests for WebSocket stability tracking."""

    @pytest.mark.asyncio
    async def test_coordinator_has_stability_tracking_attributes(
        self, hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test that coordinator has WebSocket stability tracking attributes."""
        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Should have stability tracking attributes
        assert hasattr(coordinator, "_ws_consecutive_success")
        assert hasattr(coordinator, "WEBSOCKET_STABLE_THRESHOLD")
        assert hasattr(coordinator, "_polling_disabled")

    @pytest.mark.asyncio
    async def test_websocket_stable_threshold_default(
        self, hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test that WebSocket stable threshold has sensible default."""
        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Threshold should be at least 3 to avoid false positives
        assert coordinator.WEBSOCKET_STABLE_THRESHOLD >= 3

    @pytest.mark.asyncio
    async def test_initial_state_has_polling_enabled(
        self, hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test that polling is enabled initially."""
        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        assert coordinator._polling_disabled is False
        assert coordinator._ws_consecutive_success == 0


class TestPollingDisabledWhenStable:
    """Tests for disabling polling when WebSocket is stable."""

    @pytest.mark.asyncio
    async def test_polling_disabled_after_stable_threshold(
        self, hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test that polling is disabled after reaching stability threshold."""
        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Simulate enough successful WebSocket messages
        for _ in range(coordinator.WEBSOCKET_STABLE_THRESHOLD):
            coordinator._on_websocket_message_success()

        assert coordinator._polling_disabled is True
        # When polling is disabled, update_interval should be None
        assert coordinator.update_interval is None

    @pytest.mark.asyncio
    async def test_consecutive_success_increments(
        self, hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test that consecutive success counter increments on each message."""
        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        assert coordinator._ws_consecutive_success == 0
        coordinator._on_websocket_message_success()
        assert coordinator._ws_consecutive_success == 1
        coordinator._on_websocket_message_success()
        assert coordinator._ws_consecutive_success == 2

    @pytest.mark.asyncio
    async def test_polling_not_disabled_before_threshold(
        self, hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test that polling stays enabled before reaching threshold."""
        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Simulate one less than threshold
        for _ in range(coordinator.WEBSOCKET_STABLE_THRESHOLD - 1):
            coordinator._on_websocket_message_success()

        assert coordinator._polling_disabled is False
        assert coordinator.update_interval is not None


class TestPollingReenabledOnFailure:
    """Tests for re-enabling polling when WebSocket fails."""

    @pytest.mark.asyncio
    async def test_polling_reenabled_on_websocket_error(
        self, hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test that polling is re-enabled when WebSocket encounters error."""
        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # First, get to stable state
        for _ in range(coordinator.WEBSOCKET_STABLE_THRESHOLD):
            coordinator._on_websocket_message_success()

        assert coordinator._polling_disabled is True

        # Simulate WebSocket error
        coordinator._on_websocket_error()

        assert coordinator._polling_disabled is False
        assert coordinator._ws_consecutive_success == 0
        assert coordinator.update_interval is not None

    @pytest.mark.asyncio
    async def test_success_counter_resets_on_error(
        self, hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test that consecutive success counter resets on error."""
        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        coordinator._on_websocket_message_success()
        coordinator._on_websocket_message_success()
        assert coordinator._ws_consecutive_success == 2

        coordinator._on_websocket_error()
        assert coordinator._ws_consecutive_success == 0

    @pytest.mark.asyncio
    async def test_polling_reenabled_on_disconnect(
        self, hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test that polling is re-enabled when WebSocket disconnects."""
        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # First, get to stable state
        for _ in range(coordinator.WEBSOCKET_STABLE_THRESHOLD):
            coordinator._on_websocket_message_success()

        assert coordinator._polling_disabled is True

        # Simulate WebSocket disconnect
        coordinator._handle_websocket_connection(False)

        assert coordinator._polling_disabled is False
        assert coordinator.update_interval == timedelta(seconds=DEFAULT_SCAN_INTERVAL)


class TestHealthCheckReplacesPoll:
    """Tests for health check functionality."""

    @pytest.mark.asyncio
    async def test_coordinator_has_health_check_method(
        self, hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test that coordinator has health check method."""
        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        assert hasattr(coordinator, "async_health_check")
        assert callable(coordinator.async_health_check)

    @pytest.mark.asyncio
    async def test_health_check_uses_lightweight_endpoint(
        self, hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test that health check uses a lightweight API endpoint."""
        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        await coordinator.async_health_check()

        # Should call a lightweight endpoint like ping or server info
        # not the full sessions endpoint
        mock_client.async_get_sessions.assert_not_called()
        # Should have called a health check endpoint
        mock_client.async_ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_failure_triggers_polling_reenable(
        self, hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test that health check failure re-enables polling."""
        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Get to stable state
        for _ in range(coordinator.WEBSOCKET_STABLE_THRESHOLD):
            coordinator._on_websocket_message_success()

        assert coordinator._polling_disabled is True

        # Make health check fail
        from custom_components.embymedia.exceptions import EmbyConnectionError

        mock_client.async_ping.side_effect = EmbyConnectionError("Connection failed")

        await coordinator.async_health_check()

        assert coordinator._polling_disabled is False


class TestMessageCallbackIntegration:
    """Tests for integration with WebSocket message handling."""

    @pytest.mark.asyncio
    async def test_sessions_message_increments_success_counter(
        self, hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test that receiving Sessions message increments success counter."""
        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        initial_count = coordinator._ws_consecutive_success

        # Simulate receiving a Sessions message via the handler
        coordinator._handle_websocket_message("Sessions", [])

        assert coordinator._ws_consecutive_success == initial_count + 1

    @pytest.mark.asyncio
    async def test_playback_messages_increment_success_counter(
        self, hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test that playback messages increment success counter."""
        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Test various playback message types
        message_types = ["PlaybackProgress", "PlaybackStarted", "PlaybackStopped"]

        for msg_type in message_types:
            initial_count = coordinator._ws_consecutive_success
            coordinator._handle_websocket_message(msg_type, {})
            assert coordinator._ws_consecutive_success == initial_count + 1


class TestPollingIntervalProperty:
    """Tests for polling interval property behavior."""

    @pytest.mark.asyncio
    async def test_polling_disabled_property_reflects_state(
        self, hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test that polling_disabled property correctly reflects state."""
        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        assert coordinator.polling_disabled is False

        # Reach stable state
        for _ in range(coordinator.WEBSOCKET_STABLE_THRESHOLD):
            coordinator._on_websocket_message_success()

        assert coordinator.polling_disabled is True

        # Error resets
        coordinator._on_websocket_error()
        assert coordinator.polling_disabled is False
