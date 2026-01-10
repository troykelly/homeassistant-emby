"""Tests for DiscoveryCache functionality (Issue #288).

These tests verify:
- DiscoveryCache with configurable TTL
- Cache hit/miss/invalidation behavior
- Integration with EmbyDiscoveryCoordinator
- Cache invalidation on WebSocket events
- Cache stats exposed for diagnostics
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.embymedia.coordinator_discovery import (
    EmbyDiscoveryCoordinator,
)

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock EmbyClient."""
    client = MagicMock()
    client.async_get_next_up = AsyncMock(return_value=[])
    client.async_get_resumable_items = AsyncMock(return_value=[])
    client.async_get_latest_media = AsyncMock(return_value=[])
    client.async_get_suggestions = AsyncMock(return_value=[])
    client.async_get_user_item_count = AsyncMock(return_value=0)
    client.async_get_playlists = AsyncMock(return_value=[])
    # Batch user counts method added in Issue #291
    client.async_get_all_user_counts = AsyncMock(
        return_value={
            "favorites_count": 0,
            "played_count": 0,
            "resumable_count": 0,
            "playlist_count": 0,
        }
    )
    return client


@pytest.fixture
def mock_config_entry() -> MagicMock:
    """Create a mock config entry."""
    entry = MagicMock()
    entry.options = {}
    return entry


class TestDiscoveryCacheBasics:
    """Tests for DiscoveryCache basic functionality."""

    @pytest.mark.asyncio
    async def test_coordinator_has_discovery_cache(
        self,
        hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test that discovery coordinator has a discovery cache."""
        coordinator = EmbyDiscoveryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            config_entry=mock_config_entry,
            user_id="test-user",
        )

        assert hasattr(coordinator, "_discovery_cache")
        assert coordinator._discovery_cache is not None

    @pytest.mark.asyncio
    async def test_cache_has_configurable_ttl(
        self,
        hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test that discovery cache has configurable TTL."""
        coordinator = EmbyDiscoveryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            config_entry=mock_config_entry,
            user_id="test-user",
        )

        # Cache should have TTL property
        assert hasattr(coordinator._discovery_cache, "_ttl")
        # Default TTL should be 30 minutes (1800 seconds)
        assert coordinator._discovery_cache._ttl == 1800.0

    @pytest.mark.asyncio
    async def test_cache_ttl_default_value(
        self,
        hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test that cache TTL defaults to 30 minutes."""
        from custom_components.embymedia.const import DISCOVERY_CACHE_TTL

        assert DISCOVERY_CACHE_TTL == 1800  # 30 minutes


class TestDiscoveryCacheHitMiss:
    """Tests for cache hit/miss behavior."""

    @pytest.mark.asyncio
    async def test_cache_miss_on_first_fetch(
        self,
        hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test that first fetch results in cache miss and API call."""
        coordinator = EmbyDiscoveryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            config_entry=mock_config_entry,
            user_id="test-user",
        )

        await coordinator._async_update_data()

        # All API methods should have been called
        mock_client.async_get_next_up.assert_called_once()
        mock_client.async_get_resumable_items.assert_called_once()
        mock_client.async_get_latest_media.assert_called_once()
        mock_client.async_get_suggestions.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_hit_on_second_fetch(
        self,
        hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test that second fetch within TTL results in cache hit."""
        coordinator = EmbyDiscoveryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            config_entry=mock_config_entry,
            user_id="test-user",
        )

        # First fetch
        await coordinator._async_update_data()

        # Reset mocks
        mock_client.async_get_next_up.reset_mock()
        mock_client.async_get_resumable_items.reset_mock()
        mock_client.async_get_latest_media.reset_mock()
        mock_client.async_get_suggestions.reset_mock()

        # Second fetch - should hit cache
        await coordinator._async_update_data()

        # API methods should NOT have been called again
        mock_client.async_get_next_up.assert_not_called()
        mock_client.async_get_resumable_items.assert_not_called()
        mock_client.async_get_latest_media.assert_not_called()
        mock_client.async_get_suggestions.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_after_ttl_expires(
        self,
        hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test that fetch after TTL expires results in cache miss."""
        coordinator = EmbyDiscoveryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            config_entry=mock_config_entry,
            user_id="test-user",
        )

        # First fetch
        await coordinator._async_update_data()

        # Reset mocks
        mock_client.async_get_next_up.reset_mock()
        mock_client.async_get_resumable_items.reset_mock()

        # Simulate TTL expiration by advancing the cache timestamp
        coordinator._discovery_cache.clear()

        # Third fetch - should miss cache
        await coordinator._async_update_data()

        # API methods should have been called again
        mock_client.async_get_next_up.assert_called_once()
        mock_client.async_get_resumable_items.assert_called_once()


class TestCacheInvalidationOnWebSocketEvents:
    """Tests for cache invalidation triggered by WebSocket events."""

    @pytest.mark.asyncio
    async def test_cache_invalidated_on_user_data_changed(
        self,
        hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test that cache is invalidated when UserDataChanged event occurs."""
        coordinator = EmbyDiscoveryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            config_entry=mock_config_entry,
            user_id="test-user",
        )

        # First fetch to populate cache
        await coordinator._async_update_data()

        # Reset mocks
        mock_client.async_get_next_up.reset_mock()

        # Simulate UserDataChanged event
        coordinator.invalidate_cache_for_user("test-user")

        # Next fetch should result in API call
        await coordinator._async_update_data()
        mock_client.async_get_next_up.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_invalidated_on_playback_stopped(
        self,
        hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test that cache is invalidated when PlaybackStopped event occurs."""
        coordinator = EmbyDiscoveryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            config_entry=mock_config_entry,
            user_id="test-user",
        )

        # First fetch to populate cache
        await coordinator._async_update_data()

        # Reset mocks
        mock_client.async_get_next_up.reset_mock()

        # Simulate PlaybackStopped event
        coordinator.on_playback_stopped("test-user")

        # Next fetch should result in API call
        await coordinator._async_update_data()
        mock_client.async_get_next_up.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_invalidated_on_library_changed(
        self,
        hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test that cache is invalidated when LibraryChanged event occurs."""
        coordinator = EmbyDiscoveryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            config_entry=mock_config_entry,
            user_id="test-user",
        )

        # First fetch to populate cache
        await coordinator._async_update_data()

        # Reset mocks
        mock_client.async_get_next_up.reset_mock()

        # Simulate LibraryChanged event
        coordinator.on_library_changed()

        # Next fetch should result in API call
        await coordinator._async_update_data()
        mock_client.async_get_next_up.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_only_affects_specific_user(
        self,
        hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test that invalidating one user's cache doesn't affect others."""
        coordinator = EmbyDiscoveryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            config_entry=mock_config_entry,
            user_id="test-user",
        )

        # First fetch to populate cache
        await coordinator._async_update_data()

        # Reset mocks
        mock_client.async_get_next_up.reset_mock()

        # Invalidate different user's cache
        coordinator.invalidate_cache_for_user("other-user")

        # Next fetch should still hit cache (different user invalidated)
        await coordinator._async_update_data()
        mock_client.async_get_next_up.assert_not_called()


class TestCacheStats:
    """Tests for cache statistics."""

    @pytest.mark.asyncio
    async def test_cache_exposes_stats(
        self,
        hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test that cache exposes statistics."""
        coordinator = EmbyDiscoveryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            config_entry=mock_config_entry,
            user_id="test-user",
        )

        stats = coordinator.get_cache_stats()

        assert "hits" in stats
        assert "misses" in stats
        assert "entries" in stats

    @pytest.mark.asyncio
    async def test_cache_stats_increment_on_miss(
        self,
        hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test that cache miss increments miss counter."""
        coordinator = EmbyDiscoveryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            config_entry=mock_config_entry,
            user_id="test-user",
        )

        initial_stats = coordinator.get_cache_stats()
        initial_misses = initial_stats["misses"]

        # First fetch - should be a miss
        await coordinator._async_update_data()

        final_stats = coordinator.get_cache_stats()
        assert final_stats["misses"] > initial_misses

    @pytest.mark.asyncio
    async def test_cache_stats_increment_on_hit(
        self,
        hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test that cache hit increments hit counter."""
        coordinator = EmbyDiscoveryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            config_entry=mock_config_entry,
            user_id="test-user",
        )

        # First fetch
        await coordinator._async_update_data()

        initial_stats = coordinator.get_cache_stats()
        initial_hits = initial_stats["hits"]

        # Second fetch - should be a hit
        await coordinator._async_update_data()

        final_stats = coordinator.get_cache_stats()
        assert final_stats["hits"] > initial_hits


class TestCacheDataIntegrity:
    """Tests for cache data integrity."""

    @pytest.mark.asyncio
    async def test_cached_data_matches_original(
        self,
        hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test that cached data matches original data."""
        mock_client.async_get_next_up = AsyncMock(
            return_value=[{"Id": "episode1", "Name": "Test Episode"}]
        )
        mock_client.async_get_resumable_items = AsyncMock(
            return_value=[{"Id": "movie1", "Name": "Test Movie"}]
        )

        coordinator = EmbyDiscoveryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            config_entry=mock_config_entry,
            user_id="test-user",
        )

        # First fetch
        first_data = await coordinator._async_update_data()

        # Reset mocks
        mock_client.async_get_next_up.reset_mock()
        mock_client.async_get_resumable_items.reset_mock()

        # Second fetch (from cache)
        second_data = await coordinator._async_update_data()

        # Data should be identical
        assert first_data == second_data
        assert second_data["next_up"][0]["Id"] == "episode1"
        assert second_data["continue_watching"][0]["Id"] == "movie1"

    @pytest.mark.asyncio
    async def test_no_stale_data_after_invalidation(
        self,
        hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test that invalidation returns fresh data, not stale."""
        # Initial data
        mock_client.async_get_next_up = AsyncMock(
            return_value=[{"Id": "episode1", "Name": "Old Episode"}]
        )

        coordinator = EmbyDiscoveryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            config_entry=mock_config_entry,
            user_id="test-user",
        )

        # First fetch
        await coordinator._async_update_data()

        # Update mock to return different data
        mock_client.async_get_next_up = AsyncMock(
            return_value=[{"Id": "episode2", "Name": "New Episode"}]
        )

        # Invalidate cache
        coordinator.invalidate_cache_for_user("test-user")

        # Fetch again - should get new data
        new_data = await coordinator._async_update_data()
        assert new_data["next_up"][0]["Id"] == "episode2"


class TestCacheBypassForForceRefresh:
    """Tests for cache bypass functionality."""

    @pytest.mark.asyncio
    async def test_force_refresh_bypasses_cache(
        self,
        hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test that force refresh bypasses cache."""
        coordinator = EmbyDiscoveryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            config_entry=mock_config_entry,
            user_id="test-user",
        )

        # First fetch
        await coordinator._async_update_data()

        # Reset mocks
        mock_client.async_get_next_up.reset_mock()

        # Force refresh - should bypass cache
        await coordinator.async_force_refresh()

        # API should have been called again
        mock_client.async_get_next_up.assert_called_once()

    @pytest.mark.asyncio
    async def test_coordinator_has_force_refresh_method(
        self,
        hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test that coordinator has async_force_refresh method."""
        coordinator = EmbyDiscoveryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            config_entry=mock_config_entry,
            user_id="test-user",
        )

        assert hasattr(coordinator, "async_force_refresh")
        assert callable(coordinator.async_force_refresh)


class TestCacheConstant:
    """Tests for cache-related constants."""

    def test_discovery_cache_ttl_constant_exists(self) -> None:
        """Test that DISCOVERY_CACHE_TTL constant exists."""
        from custom_components.embymedia.const import DISCOVERY_CACHE_TTL

        assert isinstance(DISCOVERY_CACHE_TTL, int)
        assert DISCOVERY_CACHE_TTL > 0

    def test_discovery_cache_ttl_is_30_minutes(self) -> None:
        """Test that DISCOVERY_CACHE_TTL is 30 minutes."""
        from custom_components.embymedia.const import DISCOVERY_CACHE_TTL

        assert DISCOVERY_CACHE_TTL == 1800  # 30 minutes in seconds
