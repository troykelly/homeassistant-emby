"""Request coalescing for concurrent identical API requests.

This module implements request coalescing to reduce redundant API calls
when multiple callers request the same data simultaneously. Instead of
making N identical requests, only one request is made and all callers
receive the same result.

Example usage:
    coalescer = RequestCoalescer()

    # Multiple concurrent calls with same key will only trigger one fetch
    result1 = await coalescer.coalesce("sessions", fetch_sessions)
    result2 = await coalescer.coalesce("sessions", fetch_sessions)  # shares result1's request
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


class RequestCoalescer:
    """Coalesces concurrent identical requests into a single API call.

    When multiple callers request the same data (identified by a key)
    concurrently, only the first request actually executes. Subsequent
    requests wait for and receive the same result.

    This is particularly useful for:
    - Multiple entities refreshing simultaneously
    - Parallel coordinator updates requesting same endpoint
    - User actions triggering overlapping fetches

    Attributes:
        _in_flight: Dictionary mapping keys to in-flight request futures.
        _total_requests: Total number of requests received.
        _coalesced_requests: Number of requests that were coalesced.
    """

    def __init__(self) -> None:
        """Initialize the request coalescer."""
        self._in_flight: dict[str, asyncio.Future[object]] = {}
        self._total_requests: int = 0
        self._coalesced_requests: int = 0

    async def coalesce(
        self,
        key: str,
        fetch_func: Callable[[], Awaitable[T]],
    ) -> T:
        """Execute a request with coalescing.

        If an identical request (same key) is already in flight, wait for
        its result instead of making a new request. Otherwise, execute the
        request and share the result with any concurrent callers.

        Args:
            key: Unique identifier for this request (e.g., endpoint + params).
            fetch_func: Async function to execute if no request is in flight.

        Returns:
            The result from fetch_func (may be from a coalesced request).

        Raises:
            Exception: Any exception raised by fetch_func is propagated to
                       all callers waiting on this request.
        """
        self._total_requests += 1

        # Check if there's already an in-flight request for this key
        if key in self._in_flight:
            self._coalesced_requests += 1
            _LOGGER.debug(
                "Coalescing request for key '%s' (waiting for in-flight request)",
                key,
            )
            # Wait for the existing request to complete
            return await self._in_flight[key]  # type: ignore[return-value]

        # Create a new future to track this request
        loop = asyncio.get_running_loop()
        future: asyncio.Future[object] = loop.create_future()
        self._in_flight[key] = future

        try:
            _LOGGER.debug("Executing request for key '%s'", key)
            result = await fetch_func()
            future.set_result(result)
            return result
        except Exception as exc:
            # Propagate error to all waiting callers
            future.set_exception(exc)
            raise
        finally:
            # Clean up in-flight tracking
            del self._in_flight[key]

    def get_stats(self) -> dict[str, int]:
        """Get coalescing statistics.

        Returns:
            Dictionary with:
            - total_requests: Total number of coalesce() calls
            - coalesced_requests: Number of requests that waited on existing
            - in_flight: Current number of in-flight requests
        """
        return {
            "total_requests": self._total_requests,
            "coalesced_requests": self._coalesced_requests,
            "in_flight": len(self._in_flight),
        }

    def reset_stats(self) -> None:
        """Reset statistics counters.

        Clears total_requests and coalesced_requests. Does not affect
        in-flight requests.
        """
        self._total_requests = 0
        self._coalesced_requests = 0


__all__ = ["RequestCoalescer"]
