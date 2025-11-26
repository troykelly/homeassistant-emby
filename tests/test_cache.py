"""Tests for the browse cache module."""

from __future__ import annotations

import pytest


class TestBrowseCache:
    """Test browse cache functionality."""

    def test_cache_get_set(self) -> None:
        """Test setting and getting cache values."""
        from custom_components.embymedia.cache import BrowseCache

        cache = BrowseCache(ttl_seconds=60)
        cache.set("key1", {"data": "value1"})

        result = cache.get("key1")
        assert result == {"data": "value1"}

    def test_cache_miss_returns_none(self) -> None:
        """Test that cache miss returns None."""
        from custom_components.embymedia.cache import BrowseCache

        cache = BrowseCache(ttl_seconds=60)

        result = cache.get("nonexistent")
        assert result is None

    def test_cache_expiration(self) -> None:
        """Test that cached values expire after TTL."""
        from custom_components.embymedia.cache import BrowseCache

        # Use a very short TTL for testing
        cache = BrowseCache(ttl_seconds=0.01)
        cache.set("key1", {"data": "value1"})

        # Should be available immediately
        assert cache.get("key1") == {"data": "value1"}

        # Wait for expiration
        import time

        time.sleep(0.02)

        # Should be expired
        assert cache.get("key1") is None

    def test_cache_clear(self) -> None:
        """Test clearing the cache."""
        from custom_components.embymedia.cache import BrowseCache

        cache = BrowseCache(ttl_seconds=60)
        cache.set("key1", {"data": "value1"})
        cache.set("key2", {"data": "value2"})

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_delete(self) -> None:
        """Test deleting specific cache entry."""
        from custom_components.embymedia.cache import BrowseCache

        cache = BrowseCache(ttl_seconds=60)
        cache.set("key1", {"data": "value1"})
        cache.set("key2", {"data": "value2"})

        cache.delete("key1")

        assert cache.get("key1") is None
        assert cache.get("key2") == {"data": "value2"}

    def test_cache_generate_key(self) -> None:
        """Test generating cache keys from function arguments."""
        from custom_components.embymedia.cache import BrowseCache

        cache = BrowseCache(ttl_seconds=60)

        key1 = cache.generate_key("get_items", "user1", parent_id="lib1")
        key2 = cache.generate_key("get_items", "user1", parent_id="lib1")
        key3 = cache.generate_key("get_items", "user1", parent_id="lib2")

        # Same arguments should produce same key
        assert key1 == key2
        # Different arguments should produce different key
        assert key1 != key3

    def test_cache_invalidate_prefix(self) -> None:
        """Test invalidating cache entries by prefix."""
        from custom_components.embymedia.cache import BrowseCache

        cache = BrowseCache(ttl_seconds=60)
        cache.set("user1:genres", {"data": "genres"})
        cache.set("user1:years", {"data": "years"})
        cache.set("user2:genres", {"data": "other"})

        cache.invalidate_prefix("user1:")

        assert cache.get("user1:genres") is None
        assert cache.get("user1:years") is None
        assert cache.get("user2:genres") == {"data": "other"}

    def test_cache_size_limit(self) -> None:
        """Test that cache enforces max size."""
        from custom_components.embymedia.cache import BrowseCache

        cache = BrowseCache(ttl_seconds=60, max_entries=3)

        cache.set("key1", {"data": 1})
        cache.set("key2", {"data": 2})
        cache.set("key3", {"data": 3})
        cache.set("key4", {"data": 4})

        # Oldest entry should be evicted
        assert cache.get("key1") is None
        # Newer entries should remain
        assert cache.get("key2") == {"data": 2}
        assert cache.get("key3") == {"data": 3}
        assert cache.get("key4") == {"data": 4}

    def test_cache_stats(self) -> None:
        """Test cache statistics tracking."""
        from custom_components.embymedia.cache import BrowseCache

        cache = BrowseCache(ttl_seconds=60)
        cache.set("key1", {"data": "value1"})

        # Hit
        cache.get("key1")
        # Miss
        cache.get("nonexistent")
        # Another hit
        cache.get("key1")

        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["entries"] == 1


class TestCacheDecorator:
    """Test cache decorator for API methods."""

    @pytest.mark.asyncio
    async def test_cached_decorator_caches_result(self) -> None:
        """Test that @cached decorator caches function results."""
        from custom_components.embymedia.cache import BrowseCache, cached

        cache = BrowseCache(ttl_seconds=60)
        call_count = 0

        @cached(cache, "test_func")
        async def test_func(user_id: str, param: str) -> dict[str, str]:
            nonlocal call_count
            call_count += 1
            return {"result": f"{user_id}-{param}"}

        # First call should execute function
        result1 = await test_func("user1", "value1")
        assert result1 == {"result": "user1-value1"}
        assert call_count == 1

        # Second call with same args should use cache
        result2 = await test_func("user1", "value1")
        assert result2 == {"result": "user1-value1"}
        assert call_count == 1  # Should not increment

        # Different args should execute function
        result3 = await test_func("user1", "value2")
        assert result3 == {"result": "user1-value2"}
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_cached_decorator_with_kwargs(self) -> None:
        """Test that @cached decorator handles kwargs."""
        from custom_components.embymedia.cache import BrowseCache, cached

        cache = BrowseCache(ttl_seconds=60)
        call_count = 0

        @cached(cache, "test_func")
        async def test_func(user_id: str, parent_id: str | None = None) -> dict[str, str | None]:
            nonlocal call_count
            call_count += 1
            return {"user_id": user_id, "parent_id": parent_id}

        # Call with kwarg
        result1 = await test_func("user1", parent_id="lib1")
        assert result1 == {"user_id": "user1", "parent_id": "lib1"}
        assert call_count == 1

        # Same call should use cache
        result2 = await test_func("user1", parent_id="lib1")
        assert result2 == {"user_id": "user1", "parent_id": "lib1"}
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_cached_bypass_cache(self) -> None:
        """Test bypassing cache with bypass_cache=True."""
        from custom_components.embymedia.cache import BrowseCache, cached

        cache = BrowseCache(ttl_seconds=60)
        call_count = 0

        @cached(cache, "test_func")
        async def test_func(user_id: str) -> dict[str, int]:
            nonlocal call_count
            call_count += 1
            return {"call": call_count}

        # First call
        result1 = await test_func("user1")
        assert result1 == {"call": 1}

        # Bypassing cache
        result2 = await test_func("user1", bypass_cache=True)
        assert result2 == {"call": 2}

        # Normal call should still use cached result from first call
        result3 = await test_func("user1")
        assert result3 == {"call": 1}
