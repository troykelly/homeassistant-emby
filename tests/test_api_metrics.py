"""Tests for API call metrics (Issue #293).

These tests verify that:
- API metrics are tracked per endpoint
- Response times are recorded
- Error counts are tracked
- Metrics are exposed via diagnostics
- WebSocket metrics are tracked
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestApiMetricsDataclass:
    """Test ApiMetrics dataclass structure."""

    def test_api_metrics_exists(self) -> None:
        """Test that ApiMetrics dataclass is defined."""
        from custom_components.embymedia.metrics import ApiMetrics

        assert ApiMetrics is not None

    def test_api_metrics_fields(self) -> None:
        """Test ApiMetrics has required fields."""
        from custom_components.embymedia.metrics import ApiMetrics

        metrics = ApiMetrics(endpoint="/Sessions")

        assert metrics.endpoint == "/Sessions"
        assert metrics.call_count == 0
        assert metrics.total_time_ms == 0.0
        assert metrics.error_count == 0
        assert metrics.last_call is None

    def test_api_metrics_avg_response_time_zero(self) -> None:
        """Test avg_response_time returns 0 when no calls."""
        from custom_components.embymedia.metrics import ApiMetrics

        metrics = ApiMetrics(endpoint="/Sessions")

        assert metrics.avg_response_time == 0.0

    def test_api_metrics_avg_response_time_calculation(self) -> None:
        """Test avg_response_time is calculated correctly."""
        from custom_components.embymedia.metrics import ApiMetrics

        metrics = ApiMetrics(
            endpoint="/Sessions",
            call_count=10,
            total_time_ms=1500.0,
        )

        assert metrics.avg_response_time == 150.0


class TestWebSocketStatsDataclass:
    """Test WebSocketStats dataclass structure."""

    def test_websocket_stats_exists(self) -> None:
        """Test that WebSocketStats dataclass is defined."""
        from custom_components.embymedia.metrics import WebSocketStats

        assert WebSocketStats is not None

    def test_websocket_stats_fields(self) -> None:
        """Test WebSocketStats has required fields."""
        from custom_components.embymedia.metrics import WebSocketStats

        stats = WebSocketStats()

        assert stats.messages_received == 0
        assert stats.reconnection_count == 0
        assert stats.error_count == 0
        assert stats.connected_since is None

    def test_websocket_stats_uptime_hours_when_not_connected(self) -> None:
        """Test uptime_hours returns 0 when not connected."""
        from custom_components.embymedia.metrics import WebSocketStats

        stats = WebSocketStats()

        assert stats.uptime_hours == 0.0

    def test_websocket_stats_uptime_hours_calculation(self) -> None:
        """Test uptime_hours is calculated correctly."""
        from custom_components.embymedia.metrics import WebSocketStats

        # Set connected_since to 2 hours ago
        connected_time = datetime.now().timestamp() - 7200  # 2 hours ago
        stats = WebSocketStats(connected_since=connected_time)

        # Allow some tolerance for test execution time
        assert 1.9 <= stats.uptime_hours <= 2.1

    def test_websocket_stats_to_dict(self) -> None:
        """Test WebSocketStats.to_dict() method."""
        from custom_components.embymedia.metrics import WebSocketStats

        stats = WebSocketStats(
            messages_received=100,
            reconnection_count=3,
            error_count=1,
        )

        result = stats.to_dict()

        assert result["messages_received"] == 100
        assert result["reconnection_count"] == 3
        assert result["error_count"] == 1
        assert "uptime_hours" in result


class TestCoordinatorStatsDataclass:
    """Test CoordinatorStats dataclass structure."""

    def test_coordinator_stats_exists(self) -> None:
        """Test that CoordinatorStats dataclass is defined."""
        from custom_components.embymedia.metrics import CoordinatorStats

        assert CoordinatorStats is not None

    def test_coordinator_stats_fields(self) -> None:
        """Test CoordinatorStats has required fields."""
        from custom_components.embymedia.metrics import CoordinatorStats

        stats = CoordinatorStats(name="session")

        assert stats.name == "session"
        assert stats.update_count == 0
        assert stats.failure_count == 0
        assert stats.total_duration_ms == 0.0

    def test_coordinator_stats_avg_duration_zero(self) -> None:
        """Test avg_duration_ms returns 0 when no updates."""
        from custom_components.embymedia.metrics import CoordinatorStats

        stats = CoordinatorStats(name="session")

        assert stats.avg_duration_ms == 0.0

    def test_coordinator_stats_avg_duration_calculation(self) -> None:
        """Test avg_duration_ms is calculated correctly."""
        from custom_components.embymedia.metrics import CoordinatorStats

        stats = CoordinatorStats(
            name="session",
            update_count=5,
            total_duration_ms=500.0,
        )

        assert stats.avg_duration_ms == 100.0


class TestMetricsCollector:
    """Test MetricsCollector class."""

    def test_metrics_collector_exists(self) -> None:
        """Test that MetricsCollector class is defined."""
        from custom_components.embymedia.metrics import MetricsCollector

        assert MetricsCollector is not None

    def test_record_api_call_new_endpoint(self) -> None:
        """Test recording API call for new endpoint."""
        from custom_components.embymedia.metrics import MetricsCollector

        collector = MetricsCollector()
        collector.record_api_call("/Sessions", 150.0)

        metrics = collector.get_api_metrics("/Sessions")
        assert metrics is not None
        assert metrics.call_count == 1
        assert metrics.total_time_ms == 150.0
        assert metrics.error_count == 0
        assert metrics.last_call is not None

    def test_record_api_call_existing_endpoint(self) -> None:
        """Test recording multiple API calls for same endpoint."""
        from custom_components.embymedia.metrics import MetricsCollector

        collector = MetricsCollector()
        collector.record_api_call("/Sessions", 100.0)
        collector.record_api_call("/Sessions", 200.0)

        metrics = collector.get_api_metrics("/Sessions")
        assert metrics is not None
        assert metrics.call_count == 2
        assert metrics.total_time_ms == 300.0
        assert metrics.avg_response_time == 150.0

    def test_record_api_call_with_error(self) -> None:
        """Test recording API call that resulted in error."""
        from custom_components.embymedia.metrics import MetricsCollector

        collector = MetricsCollector()
        collector.record_api_call("/Sessions", 50.0, error=True)

        metrics = collector.get_api_metrics("/Sessions")
        assert metrics is not None
        assert metrics.call_count == 1
        assert metrics.error_count == 1

    def test_record_websocket_message(self) -> None:
        """Test recording WebSocket message."""
        from custom_components.embymedia.metrics import MetricsCollector

        collector = MetricsCollector()
        collector.record_websocket_message("Sessions")
        collector.record_websocket_message("Sessions")
        collector.record_websocket_message("LibraryChanged")

        stats = collector.get_websocket_stats()
        assert stats.messages_received == 3

    def test_record_websocket_connect(self) -> None:
        """Test recording WebSocket connection."""
        from custom_components.embymedia.metrics import MetricsCollector

        collector = MetricsCollector()
        collector.record_websocket_connect()

        stats = collector.get_websocket_stats()
        assert stats.connected_since is not None
        assert stats.uptime_hours >= 0

    def test_record_websocket_disconnect(self) -> None:
        """Test recording WebSocket disconnection."""
        from custom_components.embymedia.metrics import MetricsCollector

        collector = MetricsCollector()
        collector.record_websocket_connect()
        collector.record_websocket_disconnect()

        stats = collector.get_websocket_stats()
        assert stats.connected_since is None

    def test_record_websocket_reconnect(self) -> None:
        """Test recording WebSocket reconnection increments count."""
        from custom_components.embymedia.metrics import MetricsCollector

        collector = MetricsCollector()
        collector.record_websocket_reconnect()
        collector.record_websocket_reconnect()

        stats = collector.get_websocket_stats()
        assert stats.reconnection_count == 2

    def test_record_websocket_error(self) -> None:
        """Test recording WebSocket error increments count."""
        from custom_components.embymedia.metrics import MetricsCollector

        collector = MetricsCollector()
        collector.record_websocket_error()

        stats = collector.get_websocket_stats()
        assert stats.error_count == 1

    def test_record_coordinator_update(self) -> None:
        """Test recording coordinator update."""
        from custom_components.embymedia.metrics import MetricsCollector

        collector = MetricsCollector()
        collector.record_coordinator_update("session", 180.0)

        stats = collector.get_coordinator_stats("session")
        assert stats is not None
        assert stats.update_count == 1
        assert stats.total_duration_ms == 180.0
        assert stats.failure_count == 0

    def test_record_coordinator_failure(self) -> None:
        """Test recording coordinator update failure."""
        from custom_components.embymedia.metrics import MetricsCollector

        collector = MetricsCollector()
        collector.record_coordinator_update("session", 180.0, success=False)

        stats = collector.get_coordinator_stats("session")
        assert stats is not None
        assert stats.update_count == 1
        assert stats.failure_count == 1

    def test_to_diagnostics(self) -> None:
        """Test converting metrics to diagnostics format."""
        from custom_components.embymedia.metrics import MetricsCollector

        collector = MetricsCollector()
        collector.record_api_call("/Sessions", 100.0)
        collector.record_api_call("/System/Info", 50.0)
        collector.record_websocket_message("Sessions")
        collector.record_coordinator_update("session", 180.0)

        result = collector.to_diagnostics()

        assert "api_calls" in result
        assert "/Sessions" in result["api_calls"]
        assert "/System/Info" in result["api_calls"]

        assert "websocket" in result
        assert result["websocket"]["messages_received"] == 1

        assert "coordinators" in result
        assert "session" in result["coordinators"]

    def test_reset_api_metrics(self) -> None:
        """Test resetting API metrics."""
        from custom_components.embymedia.metrics import MetricsCollector

        collector = MetricsCollector()
        collector.record_api_call("/Sessions", 100.0)
        collector.reset_api_metrics()

        metrics = collector.get_api_metrics("/Sessions")
        assert metrics is None


class TestDiagnosticsIncludesMetrics:
    """Test that diagnostics includes efficiency metrics."""

    @pytest.mark.asyncio
    async def test_diagnostics_includes_efficiency_metrics(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that diagnostics output includes efficiency_metrics section."""

        from custom_components.embymedia.diagnostics import (
            async_get_config_entry_diagnostics,
        )
        from custom_components.embymedia.metrics import MetricsCollector

        # Create mock coordinator with metrics
        mock_coordinator = MagicMock()
        mock_coordinator.data = {}
        mock_coordinator.server_id = "test-server"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.websocket_enabled = True
        mock_coordinator.last_update_success = True
        mock_coordinator.update_interval = 30

        # Create mock client with browse cache and metrics
        mock_client = MagicMock()
        mock_client.browse_cache.get_stats.return_value = {"hits": 10, "misses": 2, "entries": 5}

        # Add metrics collector to client
        metrics_collector = MetricsCollector()
        metrics_collector.record_api_call("/Sessions", 100.0)
        mock_client.metrics = metrics_collector

        mock_coordinator.client = mock_client

        # Create mock entry
        mock_entry = MagicMock()
        mock_entry.entry_id = "test-entry-id"
        mock_entry.data = {"host": "emby.local", "port": 8096}
        mock_entry.options = {}
        mock_entry.runtime_data = MagicMock()
        mock_entry.runtime_data.session_coordinator = mock_coordinator

        result = await async_get_config_entry_diagnostics(hass, mock_entry)

        assert "efficiency_metrics" in result
        assert "api_calls" in result["efficiency_metrics"]
        assert "websocket" in result["efficiency_metrics"]
        assert "coordinators" in result["efficiency_metrics"]


class TestApiClientInstrumentsMetrics:
    """Test that EmbyClient instruments API calls with metrics."""

    @pytest.mark.asyncio
    async def test_client_has_metrics_collector(self) -> None:
        """Test that EmbyClient has a metrics collector."""
        from custom_components.embymedia.api import EmbyClient

        client = EmbyClient(
            host="test.local",
            port=8096,
            api_key="test-key",
        )

        assert hasattr(client, "metrics")
        assert client.metrics is not None

    @pytest.mark.asyncio
    async def test_api_request_records_metrics(self) -> None:
        """Test that API requests are instrumented with metrics."""
        import aiohttp
        from aiohttp import ClientResponse

        from custom_components.embymedia.api import EmbyClient

        client = EmbyClient(
            host="test.local",
            port=8096,
            api_key="test-key",
        )

        # Mock the session and response
        mock_response = MagicMock(spec=ClientResponse)
        mock_response.status = 200
        mock_response.reason = "OK"
        mock_response.json = AsyncMock(return_value={})

        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.closed = False

        # Create a proper async context manager for the request
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = MagicMock(return_value=mock_context_manager)

        client._session = mock_session
        client._owns_session = False

        # Make a request
        await client._request("GET", "/System/Info")

        # Check metrics were recorded
        metrics = client.metrics.get_api_metrics("/System/Info")
        assert metrics is not None
        assert metrics.call_count == 1
        assert metrics.total_time_ms > 0

        await client.close()

    @pytest.mark.asyncio
    async def test_api_request_records_error_metrics(self) -> None:
        """Test that API errors are recorded in metrics."""
        import aiohttp
        from aiohttp import ClientResponse

        from custom_components.embymedia.api import EmbyClient
        from custom_components.embymedia.exceptions import EmbyServerError

        client = EmbyClient(
            host="test.local",
            port=8096,
            api_key="test-key",
        )

        # Mock the session and response
        mock_response = MagicMock(spec=ClientResponse)
        mock_response.status = 500
        mock_response.reason = "Internal Server Error"

        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.closed = False

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.request = MagicMock(return_value=mock_context_manager)

        client._session = mock_session
        client._owns_session = False

        # Make a request that fails
        with pytest.raises(EmbyServerError):
            await client._request("GET", "/Sessions")

        # Check error was recorded
        metrics = client.metrics.get_api_metrics("/Sessions")
        assert metrics is not None
        assert metrics.call_count == 1
        assert metrics.error_count == 1

        await client.close()
