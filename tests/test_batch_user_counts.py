"""Tests for batch user counts functionality.

These tests verify that Issue #291 is correctly implemented:
- Consolidated API for fetching all user counts in one call
- Returns all count types (favorites, played, resumable, playlists)
- Efficient parallel fetching when batch method is used
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    pass


class TestBatchUserCountsMethod:
    """Test batch user counts API method."""

    def test_async_get_all_user_counts_exists(self) -> None:
        """Test that async_get_all_user_counts method exists on EmbyClient."""
        from custom_components.embymedia.api import EmbyClient

        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-key",
        )

        assert hasattr(client, "async_get_all_user_counts")
        assert callable(client.async_get_all_user_counts)

    @pytest.mark.asyncio
    async def test_batch_user_counts_returns_all_counts(self) -> None:
        """Test that batch method returns all count types."""
        from custom_components.embymedia.api import EmbyClient

        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-key",
        )

        # Mock the individual count methods
        with (
            patch.object(client, "async_get_user_item_count", new_callable=AsyncMock) as mock_count,
            patch.object(client, "async_get_playlists", new_callable=AsyncMock) as mock_playlists,
        ):
            # Set up mock return values
            mock_count.side_effect = [100, 500, 25]  # favorites, played, resumable
            mock_playlists.return_value = [{"Id": "1"}, {"Id": "2"}]  # 2 playlists

            result = await client.async_get_all_user_counts(user_id="user-123")

            # Verify structure
            assert "favorites_count" in result
            assert "played_count" in result
            assert "resumable_count" in result
            assert "playlist_count" in result

            # Verify values
            assert result["favorites_count"] == 100
            assert result["played_count"] == 500
            assert result["resumable_count"] == 25
            assert result["playlist_count"] == 2

    @pytest.mark.asyncio
    async def test_batch_user_counts_calls_in_parallel(self) -> None:
        """Test that batch method fetches counts in parallel."""
        from custom_components.embymedia.api import EmbyClient

        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-key",
        )

        call_order: list[str] = []
        call_times: list[float] = []

        async def mock_count(user_id: str, filters: str) -> int:
            import time

            call_times.append(time.time())
            call_order.append(filters)
            await asyncio.sleep(0.05)  # Simulate network delay
            return 10

        async def mock_playlists(user_id: str) -> list:
            import time

            call_times.append(time.time())
            call_order.append("playlists")
            await asyncio.sleep(0.05)
            return []

        with (
            patch.object(client, "async_get_user_item_count", side_effect=mock_count),
            patch.object(client, "async_get_playlists", side_effect=mock_playlists),
        ):
            await client.async_get_all_user_counts(user_id="user-123")

            # All 4 calls should have started at approximately the same time
            # If sequential, time difference would be >= 0.05 between each
            # If parallel, all should start within a small window
            assert len(call_times) == 4
            time_span = max(call_times) - min(call_times)
            assert time_span < 0.03  # All started within 30ms = parallel


class TestDiscoveryCoordinatorUsessBatchCounts:
    """Test that discovery coordinator uses batch counts method."""

    @pytest.mark.asyncio
    async def test_discovery_coordinator_uses_batch_counts(self, hass) -> None:
        """Test that EmbyDiscoveryCoordinator uses async_get_all_user_counts."""
        from custom_components.embymedia.coordinator_discovery import (
            EmbyDiscoveryCoordinator,
        )

        mock_client = MagicMock()
        mock_client.async_get_next_up = AsyncMock(return_value=[])
        mock_client.async_get_resumable_items = AsyncMock(return_value=[])
        mock_client.async_get_latest_media = AsyncMock(return_value=[])
        mock_client.async_get_suggestions = AsyncMock(return_value=[])
        mock_client.async_get_all_user_counts = AsyncMock(
            return_value={
                "favorites_count": 10,
                "played_count": 50,
                "resumable_count": 5,
                "playlist_count": 3,
            }
        )

        mock_config_entry = MagicMock()
        mock_config_entry.options = {}

        coordinator = EmbyDiscoveryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            config_entry=mock_config_entry,
            user_id="user-123",
        )

        result = await coordinator._async_update_data()

        # Verify batch method was called
        mock_client.async_get_all_user_counts.assert_called_once_with(user_id="user-123")

        # Verify result contains correct counts
        assert result["user_counts"]["favorites_count"] == 10
        assert result["user_counts"]["played_count"] == 50
        assert result["user_counts"]["resumable_count"] == 5
        assert result["user_counts"]["playlist_count"] == 3


class TestBatchUserCountsReturnType:
    """Test return type of batch user counts."""

    @pytest.mark.asyncio
    async def test_return_type_is_typed_dict(self) -> None:
        """Test that async_get_all_user_counts returns UserCountsResult TypedDict."""
        from custom_components.embymedia.api import EmbyClient

        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-key",
        )

        with (
            patch.object(client, "async_get_user_item_count", new_callable=AsyncMock) as mock_count,
            patch.object(client, "async_get_playlists", new_callable=AsyncMock) as mock_playlists,
        ):
            mock_count.side_effect = [10, 20, 30]
            mock_playlists.return_value = []

            result = await client.async_get_all_user_counts(user_id="user-123")

            # Verify it's a dict with expected keys
            assert isinstance(result, dict)
            assert set(result.keys()) == {
                "favorites_count",
                "played_count",
                "resumable_count",
                "playlist_count",
            }
