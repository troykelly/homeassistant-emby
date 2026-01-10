"""Tests for request coalescing functionality.

These tests verify that Issue #290 is correctly implemented:
- Concurrent identical requests are coalesced into single API call
- All callers receive the same result
- Errors are propagated to all waiting callers
- In-flight tracking is properly cleaned up
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

if TYPE_CHECKING:
    pass


class TestRequestCoalescerBasics:
    """Test basic request coalescer functionality."""

    def test_request_coalescer_exists(self) -> None:
        """Test that RequestCoalescer class exists."""
        from custom_components.embymedia.coalescer import RequestCoalescer

        coalescer = RequestCoalescer()
        assert coalescer is not None

    def test_request_coalescer_has_required_methods(self) -> None:
        """Test that RequestCoalescer has required methods."""
        from custom_components.embymedia.coalescer import RequestCoalescer

        coalescer = RequestCoalescer()
        assert hasattr(coalescer, "coalesce")
        assert callable(coalescer.coalesce)
        assert hasattr(coalescer, "get_stats")
        assert callable(coalescer.get_stats)

    def test_initial_stats(self) -> None:
        """Test that initial stats are zero."""
        from custom_components.embymedia.coalescer import RequestCoalescer

        coalescer = RequestCoalescer()
        stats = coalescer.get_stats()
        assert stats["total_requests"] == 0
        assert stats["coalesced_requests"] == 0
        assert stats["in_flight"] == 0


class TestSingleRequestBehavior:
    """Test single request behavior (no coalescing)."""

    @pytest.mark.asyncio
    async def test_single_request_executes_function(self) -> None:
        """Test that single request executes the provided function."""
        from custom_components.embymedia.coalescer import RequestCoalescer

        coalescer = RequestCoalescer()
        mock_func = AsyncMock(return_value={"data": "result"})

        result = await coalescer.coalesce("test-key", mock_func)

        assert result == {"data": "result"}
        mock_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_single_request_updates_stats(self) -> None:
        """Test that single request updates stats correctly."""
        from custom_components.embymedia.coalescer import RequestCoalescer

        coalescer = RequestCoalescer()
        mock_func = AsyncMock(return_value={})

        await coalescer.coalesce("test-key", mock_func)

        stats = coalescer.get_stats()
        assert stats["total_requests"] == 1
        assert stats["coalesced_requests"] == 0  # No coalescing happened


class TestConcurrentRequestCoalescing:
    """Test concurrent request coalescing."""

    @pytest.mark.asyncio
    async def test_concurrent_requests_coalesced(self) -> None:
        """Test that concurrent identical requests are coalesced."""
        from custom_components.embymedia.coalescer import RequestCoalescer

        coalescer = RequestCoalescer()

        # Create a slow function that we can control
        call_count = 0
        result_data = {"sessions": ["session1", "session2"]}

        async def slow_func() -> dict:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)  # Simulate network delay
            return result_data

        # Start 3 concurrent requests with the same key
        tasks = [
            asyncio.create_task(coalescer.coalesce("sessions", slow_func)),
            asyncio.create_task(coalescer.coalesce("sessions", slow_func)),
            asyncio.create_task(coalescer.coalesce("sessions", slow_func)),
        ]

        results = await asyncio.gather(*tasks)

        # All should get the same result
        assert all(r == result_data for r in results)
        # But the function should only be called once
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_concurrent_requests_update_stats(self) -> None:
        """Test that concurrent requests update stats correctly."""
        from custom_components.embymedia.coalescer import RequestCoalescer

        coalescer = RequestCoalescer()

        async def slow_func() -> dict:
            await asyncio.sleep(0.1)
            return {}

        tasks = [
            asyncio.create_task(coalescer.coalesce("key1", slow_func)),
            asyncio.create_task(coalescer.coalesce("key1", slow_func)),
            asyncio.create_task(coalescer.coalesce("key1", slow_func)),
        ]

        await asyncio.gather(*tasks)

        stats = coalescer.get_stats()
        assert stats["total_requests"] == 3
        assert stats["coalesced_requests"] == 2  # 2 requests were coalesced

    @pytest.mark.asyncio
    async def test_different_keys_not_coalesced(self) -> None:
        """Test that requests with different keys are not coalesced."""
        from custom_components.embymedia.coalescer import RequestCoalescer

        coalescer = RequestCoalescer()
        call_counts = {"key1": 0, "key2": 0}

        async def func_for_key1() -> dict:
            call_counts["key1"] += 1
            await asyncio.sleep(0.1)
            return {"key": "1"}

        async def func_for_key2() -> dict:
            call_counts["key2"] += 1
            await asyncio.sleep(0.1)
            return {"key": "2"}

        tasks = [
            asyncio.create_task(coalescer.coalesce("key1", func_for_key1)),
            asyncio.create_task(coalescer.coalesce("key2", func_for_key2)),
        ]

        results = await asyncio.gather(*tasks)

        # Different keys should result in different function calls
        assert call_counts["key1"] == 1
        assert call_counts["key2"] == 1
        assert results[0] == {"key": "1"}
        assert results[1] == {"key": "2"}


class TestErrorHandling:
    """Test error handling in request coalescing."""

    @pytest.mark.asyncio
    async def test_error_propagates_to_all_callers(self) -> None:
        """Test that errors propagate to all waiting callers."""
        from custom_components.embymedia.coalescer import RequestCoalescer

        coalescer = RequestCoalescer()

        async def failing_func() -> dict:
            await asyncio.sleep(0.05)
            raise ValueError("API error")

        tasks = [
            asyncio.create_task(coalescer.coalesce("fail-key", failing_func)),
            asyncio.create_task(coalescer.coalesce("fail-key", failing_func)),
        ]

        # Both tasks should raise the same error
        for task in tasks:
            with pytest.raises(ValueError, match="API error"):
                await task

    @pytest.mark.asyncio
    async def test_cleanup_after_error(self) -> None:
        """Test that in-flight tracking is cleaned up after error."""
        from custom_components.embymedia.coalescer import RequestCoalescer

        coalescer = RequestCoalescer()

        async def failing_func() -> dict:
            raise RuntimeError("Oops")

        with pytest.raises(RuntimeError):
            await coalescer.coalesce("error-key", failing_func)

        # Should be no in-flight requests after error
        stats = coalescer.get_stats()
        assert stats["in_flight"] == 0

    @pytest.mark.asyncio
    async def test_subsequent_request_after_error_works(self) -> None:
        """Test that new requests work after a previous error."""
        from custom_components.embymedia.coalescer import RequestCoalescer

        coalescer = RequestCoalescer()

        async def failing_func() -> dict:
            raise RuntimeError("First failure")

        async def success_func() -> dict:
            return {"success": True}

        # First request fails
        with pytest.raises(RuntimeError):
            await coalescer.coalesce("retry-key", failing_func)

        # Second request with same key should work
        result = await coalescer.coalesce("retry-key", success_func)
        assert result == {"success": True}


class TestInFlightTracking:
    """Test in-flight request tracking."""

    @pytest.mark.asyncio
    async def test_in_flight_count_during_request(self) -> None:
        """Test that in-flight count is accurate during request."""
        from custom_components.embymedia.coalescer import RequestCoalescer

        coalescer = RequestCoalescer()
        in_flight_during_request = None

        async def check_in_flight() -> dict:
            nonlocal in_flight_during_request
            in_flight_during_request = coalescer.get_stats()["in_flight"]
            await asyncio.sleep(0.05)
            return {}

        await coalescer.coalesce("inflight-key", check_in_flight)

        assert in_flight_during_request == 1
        # After completion, should be 0
        assert coalescer.get_stats()["in_flight"] == 0

    @pytest.mark.asyncio
    async def test_cleanup_after_success(self) -> None:
        """Test that in-flight tracking is cleaned up after success."""
        from custom_components.embymedia.coalescer import RequestCoalescer

        coalescer = RequestCoalescer()

        async def quick_func() -> dict:
            return {"done": True}

        await coalescer.coalesce("cleanup-key", quick_func)

        stats = coalescer.get_stats()
        assert stats["in_flight"] == 0


class TestSequentialRequests:
    """Test sequential request behavior."""

    @pytest.mark.asyncio
    async def test_sequential_requests_both_execute(self) -> None:
        """Test that sequential requests with same key both execute."""
        from custom_components.embymedia.coalescer import RequestCoalescer

        coalescer = RequestCoalescer()
        call_count = 0

        async def counting_func() -> dict:
            nonlocal call_count
            call_count += 1
            return {"count": call_count}

        # First request
        result1 = await coalescer.coalesce("seq-key", counting_func)
        # Second request (after first completes)
        result2 = await coalescer.coalesce("seq-key", counting_func)

        # Both should execute since they're sequential
        assert call_count == 2
        assert result1 == {"count": 1}
        assert result2 == {"count": 2}


class TestResetStats:
    """Test stats reset functionality."""

    @pytest.mark.asyncio
    async def test_reset_stats(self) -> None:
        """Test that reset_stats clears all counters."""
        from custom_components.embymedia.coalescer import RequestCoalescer

        coalescer = RequestCoalescer()
        mock_func = AsyncMock(return_value={})

        # Generate some stats
        await coalescer.coalesce("key", mock_func)

        stats_before = coalescer.get_stats()
        assert stats_before["total_requests"] > 0

        coalescer.reset_stats()

        stats_after = coalescer.get_stats()
        assert stats_after["total_requests"] == 0
        assert stats_after["coalesced_requests"] == 0


class TestEmbyClientIntegration:
    """Test EmbyClient integration with request coalescing."""

    def test_emby_client_has_coalescer(self) -> None:
        """Test that EmbyClient has a request coalescer."""
        from custom_components.embymedia.api import EmbyClient

        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-key",
        )

        assert hasattr(client, "_coalescer")
        assert hasattr(client, "get_coalescer_stats")
        assert hasattr(client, "reset_coalescer_stats")

    def test_emby_client_coalescer_stats_initial(self) -> None:
        """Test that EmbyClient coalescer stats are initially zero."""
        from custom_components.embymedia.api import EmbyClient

        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-key",
        )

        stats = client.get_coalescer_stats()
        assert stats["total_requests"] == 0
        assert stats["coalesced_requests"] == 0
        assert stats["in_flight"] == 0

    def test_emby_client_reset_coalescer_stats(self) -> None:
        """Test that EmbyClient can reset coalescer stats."""
        from custom_components.embymedia.api import EmbyClient

        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-key",
        )

        # Manually increment to verify reset
        client._coalescer._total_requests = 10
        client._coalescer._coalesced_requests = 5

        client.reset_coalescer_stats()

        stats = client.get_coalescer_stats()
        assert stats["total_requests"] == 0
        assert stats["coalesced_requests"] == 0
