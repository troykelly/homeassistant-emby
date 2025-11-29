"""Tests for EmbyDiscoveryCoordinator."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.embymedia.const import (
    DEFAULT_DISCOVERY_SCAN_INTERVAL,
    DOMAIN,
)
from custom_components.embymedia.coordinator_discovery import (
    EmbyDiscoveryCoordinator,
    EmbyDiscoveryData,
)
from custom_components.embymedia.exceptions import EmbyConnectionError, EmbyError

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock EmbyClient."""
    client = MagicMock()
    client.async_get_next_up = AsyncMock(return_value=[])
    client.async_get_resumable_items = AsyncMock(return_value=[])
    client.async_get_latest_media = AsyncMock(return_value=[])
    client.async_get_suggestions = AsyncMock(return_value=[])
    # User count methods
    client.async_get_user_item_count = AsyncMock(return_value=0)
    client.async_get_playlists = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_config_entry() -> MagicMock:
    """Create a mock config entry."""
    entry = MagicMock()
    entry.options = {}
    return entry


class TestEmbyDiscoveryCoordinatorInit:
    """Test EmbyDiscoveryCoordinator initialization."""

    async def test_coordinator_initialization(
        self,
        hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test coordinator initializes with correct parameters."""
        coordinator = EmbyDiscoveryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="server123",
            config_entry=mock_config_entry,
            user_id="user456",
        )

        assert coordinator.client == mock_client
        assert coordinator.server_id == "server123"
        assert coordinator.user_id == "user456"
        assert coordinator.user_name == "user456"  # Defaults to user_id when not provided
        assert coordinator.update_interval == timedelta(seconds=DEFAULT_DISCOVERY_SCAN_INTERVAL)
        assert coordinator.name == f"{DOMAIN}_server123_discovery_user456"

    async def test_coordinator_custom_scan_interval(
        self,
        hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test coordinator uses custom scan interval."""
        coordinator = EmbyDiscoveryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="server123",
            config_entry=mock_config_entry,
            user_id="user456",
            scan_interval=600,
        )

        assert coordinator.update_interval == timedelta(seconds=600)


class TestEmbyDiscoveryCoordinatorUpdate:
    """Test EmbyDiscoveryCoordinator data updates."""

    async def test_async_update_data_fetches_all_data(
        self,
        hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test async_update_data fetches all discovery data."""
        mock_client.async_get_next_up = AsyncMock(
            return_value=[
                {
                    "Id": "episode1",
                    "Name": "Next Episode",
                    "Type": "Episode",
                    "SeriesName": "Test Series",
                }
            ]
        )
        mock_client.async_get_resumable_items = AsyncMock(
            return_value=[
                {
                    "Id": "movie1",
                    "Name": "Paused Movie",
                    "Type": "Movie",
                    "UserData": {"PlayedPercentage": 50.0},
                }
            ]
        )
        mock_client.async_get_latest_media = AsyncMock(
            return_value=[
                {
                    "Id": "new1",
                    "Name": "New Movie",
                    "Type": "Movie",
                    "DateCreated": "2024-01-15T10:00:00Z",
                }
            ]
        )
        mock_client.async_get_suggestions = AsyncMock(
            return_value=[
                {
                    "Id": "suggest1",
                    "Name": "Suggested Movie",
                    "Type": "Movie",
                }
            ]
        )

        coordinator = EmbyDiscoveryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="server123",
            config_entry=mock_config_entry,
            user_id="user456",
        )

        data = await coordinator._async_update_data()

        # Verify all API calls were made with correct user_id
        mock_client.async_get_next_up.assert_called_once_with(user_id="user456")
        mock_client.async_get_resumable_items.assert_called_once_with(user_id="user456")
        mock_client.async_get_latest_media.assert_called_once_with(user_id="user456")
        mock_client.async_get_suggestions.assert_called_once_with(user_id="user456")

        # Verify data structure
        assert len(data["next_up"]) == 1
        assert data["next_up"][0]["Id"] == "episode1"
        assert len(data["continue_watching"]) == 1
        assert data["continue_watching"][0]["Id"] == "movie1"
        assert len(data["recently_added"]) == 1
        assert data["recently_added"][0]["Id"] == "new1"
        assert len(data["suggestions"]) == 1
        assert data["suggestions"][0]["Id"] == "suggest1"

    async def test_async_update_data_handles_empty_responses(
        self,
        hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test async_update_data handles empty responses."""
        mock_client.async_get_next_up = AsyncMock(return_value=[])
        mock_client.async_get_resumable_items = AsyncMock(return_value=[])
        mock_client.async_get_latest_media = AsyncMock(return_value=[])
        mock_client.async_get_suggestions = AsyncMock(return_value=[])

        coordinator = EmbyDiscoveryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="server123",
            config_entry=mock_config_entry,
            user_id="user456",
        )

        data = await coordinator._async_update_data()

        assert data["next_up"] == []
        assert data["continue_watching"] == []
        assert data["recently_added"] == []
        assert data["suggestions"] == []

    async def test_async_update_data_connection_error(
        self,
        hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test async_update_data raises UpdateFailed on connection error."""
        mock_client.async_get_next_up = AsyncMock(
            side_effect=EmbyConnectionError("Connection failed")
        )

        coordinator = EmbyDiscoveryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="server123",
            config_entry=mock_config_entry,
            user_id="user456",
        )

        with pytest.raises(UpdateFailed) as exc_info:
            await coordinator._async_update_data()

        assert "Failed to connect" in str(exc_info.value)

    async def test_async_update_data_generic_error(
        self,
        hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test async_update_data raises UpdateFailed on generic error."""
        mock_client.async_get_next_up = AsyncMock(side_effect=EmbyError("Something went wrong"))

        coordinator = EmbyDiscoveryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="server123",
            config_entry=mock_config_entry,
            user_id="user456",
        )

        with pytest.raises(UpdateFailed) as exc_info:
            await coordinator._async_update_data()

        assert "Error fetching discovery data" in str(exc_info.value)


class TestEmbyDiscoveryDataTypedDict:
    """Test EmbyDiscoveryData TypedDict structure."""

    def test_discovery_data_structure(self) -> None:
        """Test EmbyDiscoveryData has correct structure."""
        data: EmbyDiscoveryData = {
            "next_up": [],
            "continue_watching": [],
            "recently_added": [],
            "suggestions": [],
            "user_counts": {
                "favorites_count": 0,
                "played_count": 0,
                "resumable_count": 0,
                "playlist_count": 0,
            },
        }
        assert "next_up" in data
        assert "continue_watching" in data
        assert "recently_added" in data
        assert "suggestions" in data
        assert "user_counts" in data


class TestEmbyDiscoveryCoordinatorParallelExecution:
    """Test that coordinator uses asyncio.gather for parallel API calls."""

    async def test_parallel_api_calls_faster_than_sequential(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test that API calls run in parallel, not sequentially.

        If 8 calls with 50ms delay each ran sequentially, it would take 400ms.
        In parallel, they should complete in ~50ms (plus overhead).
        We assert completion in under 200ms to prove parallelism.
        """
        import asyncio
        import time

        delay_seconds = 0.05  # 50ms per call

        async def slow_api_call(*args: object, **kwargs: object) -> list[object]:
            """Simulate a slow API call."""
            await asyncio.sleep(delay_seconds)
            return []

        async def slow_count_call(*args: object, **kwargs: object) -> int:
            """Simulate a slow count API call."""
            await asyncio.sleep(delay_seconds)
            return 0

        mock_client = MagicMock()
        mock_client.async_get_next_up = AsyncMock(side_effect=slow_api_call)
        mock_client.async_get_resumable_items = AsyncMock(side_effect=slow_api_call)
        mock_client.async_get_latest_media = AsyncMock(side_effect=slow_api_call)
        mock_client.async_get_suggestions = AsyncMock(side_effect=slow_api_call)
        mock_client.async_get_user_item_count = AsyncMock(side_effect=slow_count_call)
        mock_client.async_get_playlists = AsyncMock(side_effect=slow_api_call)

        coordinator = EmbyDiscoveryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="server123",
            config_entry=mock_config_entry,
            user_id="user456",
        )

        # Measure execution time
        start = time.time()
        await coordinator._async_update_data()
        elapsed = time.time() - start

        # 8 calls at 50ms each:
        # Sequential: 400ms minimum (8 * 50ms)
        # Parallel: ~50ms (plus overhead)
        # We allow up to 200ms to account for overhead but prove parallelism
        assert elapsed < 0.2, (
            f"API calls took {elapsed:.3f}s - "
            f"should be < 0.2s if running in parallel (8 calls * 50ms sequential = 400ms)"
        )

    async def test_all_api_methods_called(
        self,
        hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test that all 8 API calls are made during update."""
        coordinator = EmbyDiscoveryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="server123",
            config_entry=mock_config_entry,
            user_id="user456",
        )

        await coordinator._async_update_data()

        # Verify all 8 API calls were made
        mock_client.async_get_next_up.assert_called_once_with(user_id="user456")
        mock_client.async_get_resumable_items.assert_called_once_with(user_id="user456")
        mock_client.async_get_latest_media.assert_called_once_with(user_id="user456")
        mock_client.async_get_suggestions.assert_called_once_with(user_id="user456")
        # User item count called 3 times (favorites, played, resumable)
        assert mock_client.async_get_user_item_count.call_count == 3
        mock_client.async_get_playlists.assert_called_once_with(user_id="user456")
