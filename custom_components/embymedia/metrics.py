"""API call metrics for Emby integration.

This module provides metrics collection for API calls, WebSocket connections,
and coordinator updates to help diagnose performance issues.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass
class ApiMetrics:
    """Metrics for a single API endpoint.

    Tracks call count, total response time, and error count for an endpoint.

    Attributes:
        endpoint: The API endpoint path.
        call_count: Total number of calls to this endpoint.
        total_time_ms: Total response time in milliseconds.
        error_count: Number of calls that resulted in errors.
        last_call: Timestamp of the last call.
    """

    endpoint: str
    call_count: int = 0
    total_time_ms: float = 0.0
    error_count: int = 0
    last_call: datetime | None = None

    @property
    def avg_response_time(self) -> float:
        """Calculate average response time in milliseconds.

        Returns:
            Average response time or 0 if no calls have been made.
        """
        if self.call_count == 0:
            return 0.0
        return self.total_time_ms / self.call_count


@dataclass
class WebSocketStats:
    """Statistics for WebSocket connection.

    Tracks messages received, connection uptime, and error counts.

    Attributes:
        messages_received: Total number of messages received.
        reconnection_count: Number of reconnection attempts.
        error_count: Number of WebSocket errors.
        connected_since: Timestamp when connection was established.
    """

    messages_received: int = 0
    reconnection_count: int = 0
    error_count: int = 0
    connected_since: float | None = None

    @property
    def uptime_hours(self) -> float:
        """Calculate connection uptime in hours.

        Returns:
            Uptime in hours or 0 if not connected.
        """
        if self.connected_since is None:
            return 0.0
        elapsed_seconds = datetime.now().timestamp() - self.connected_since
        return elapsed_seconds / 3600.0

    def to_dict(self) -> dict[str, int | float]:
        """Convert to dictionary for diagnostics.

        Returns:
            Dictionary with stats for diagnostics output.
        """
        return {
            "messages_received": self.messages_received,
            "reconnection_count": self.reconnection_count,
            "error_count": self.error_count,
            "uptime_hours": round(self.uptime_hours, 2),
        }


@dataclass
class CoordinatorStats:
    """Statistics for a DataUpdateCoordinator.

    Tracks update counts, failures, and timing for coordinators.

    Attributes:
        name: Name of the coordinator.
        update_count: Total number of update attempts.
        failure_count: Number of failed updates.
        total_duration_ms: Total time spent in updates.
    """

    name: str
    update_count: int = 0
    failure_count: int = 0
    total_duration_ms: float = 0.0

    @property
    def avg_duration_ms(self) -> float:
        """Calculate average update duration in milliseconds.

        Returns:
            Average duration or 0 if no updates have occurred.
        """
        if self.update_count == 0:
            return 0.0
        return self.total_duration_ms / self.update_count


@dataclass
class MetricsCollector:
    """Collects metrics for API calls, WebSocket, and coordinators.

    This collector is attached to the EmbyClient and provides a central
    place to track all efficiency-related metrics.

    Example:
        collector = MetricsCollector()
        collector.record_api_call("/Sessions", 150.0)
        collector.record_websocket_message("Sessions")
        diagnostics = collector.to_diagnostics()
    """

    _api_metrics: dict[str, ApiMetrics] = field(default_factory=dict)
    _websocket_stats: WebSocketStats = field(default_factory=WebSocketStats)
    _coordinator_stats: dict[str, CoordinatorStats] = field(default_factory=dict)

    def record_api_call(
        self,
        endpoint: str,
        duration_ms: float,
        error: bool = False,
    ) -> None:
        """Record an API call.

        Args:
            endpoint: The API endpoint that was called.
            duration_ms: Response time in milliseconds.
            error: Whether the call resulted in an error.
        """
        if endpoint not in self._api_metrics:
            self._api_metrics[endpoint] = ApiMetrics(endpoint=endpoint)

        metrics = self._api_metrics[endpoint]
        metrics.call_count += 1
        metrics.total_time_ms += duration_ms
        metrics.last_call = datetime.now()
        if error:
            metrics.error_count += 1

    def get_api_metrics(self, endpoint: str) -> ApiMetrics | None:
        """Get metrics for a specific endpoint.

        Args:
            endpoint: The API endpoint to get metrics for.

        Returns:
            ApiMetrics for the endpoint or None if not tracked.
        """
        return self._api_metrics.get(endpoint)

    def record_websocket_message(self, message_type: str) -> None:
        """Record a received WebSocket message.

        Args:
            message_type: The type of message received.
        """
        self._websocket_stats.messages_received += 1

    def record_websocket_connect(self) -> None:
        """Record WebSocket connection established."""
        self._websocket_stats.connected_since = datetime.now().timestamp()

    def record_websocket_disconnect(self) -> None:
        """Record WebSocket disconnection."""
        self._websocket_stats.connected_since = None

    def record_websocket_reconnect(self) -> None:
        """Record WebSocket reconnection attempt."""
        self._websocket_stats.reconnection_count += 1

    def record_websocket_error(self) -> None:
        """Record WebSocket error."""
        self._websocket_stats.error_count += 1

    def get_websocket_stats(self) -> WebSocketStats:
        """Get WebSocket statistics.

        Returns:
            Current WebSocket statistics.
        """
        return self._websocket_stats

    def record_coordinator_update(
        self,
        name: str,
        duration_ms: float,
        success: bool = True,
    ) -> None:
        """Record a coordinator update.

        Args:
            name: Name of the coordinator.
            duration_ms: Update duration in milliseconds.
            success: Whether the update succeeded.
        """
        if name not in self._coordinator_stats:
            self._coordinator_stats[name] = CoordinatorStats(name=name)

        stats = self._coordinator_stats[name]
        stats.update_count += 1
        stats.total_duration_ms += duration_ms
        if not success:
            stats.failure_count += 1

    def get_coordinator_stats(self, name: str) -> CoordinatorStats | None:
        """Get statistics for a specific coordinator.

        Args:
            name: Name of the coordinator.

        Returns:
            CoordinatorStats for the coordinator or None if not tracked.
        """
        return self._coordinator_stats.get(name)

    def reset_api_metrics(self) -> None:
        """Reset all API metrics."""
        self._api_metrics.clear()

    def to_diagnostics(self) -> dict[str, object]:
        """Convert all metrics to diagnostics format.

        Returns:
            Dictionary suitable for diagnostics output.
        """
        return {
            "api_calls": {
                endpoint: {
                    "count": metrics.call_count,
                    "avg_ms": round(metrics.avg_response_time, 2),
                    "errors": metrics.error_count,
                }
                for endpoint, metrics in self._api_metrics.items()
            },
            "websocket": self._websocket_stats.to_dict(),
            "coordinators": {
                name: {
                    "updates": stats.update_count,
                    "failures": stats.failure_count,
                    "avg_duration_ms": round(stats.avg_duration_ms, 2),
                }
                for name, stats in self._coordinator_stats.items()
            },
        }


__all__ = [
    "ApiMetrics",
    "CoordinatorStats",
    "MetricsCollector",
    "WebSocketStats",
]
