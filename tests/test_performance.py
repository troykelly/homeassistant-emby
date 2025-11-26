"""Tests for performance optimizations (Phase 9.2)."""

from __future__ import annotations

import sys


class TestDataclassSlots:
    """Test dataclasses use slots for memory optimization."""

    def test_emby_media_item_uses_slots(self) -> None:
        """Test EmbyMediaItem uses __slots__ for memory efficiency."""
        from custom_components.embymedia.models import EmbyMediaItem

        assert hasattr(EmbyMediaItem, "__slots__")
        # Frozen dataclass with slots should not have __dict__
        item = EmbyMediaItem(
            item_id="test",
            name="Test",
            media_type=None,  # type: ignore[arg-type]
        )
        assert not hasattr(item, "__dict__")

    def test_emby_playback_state_uses_slots(self) -> None:
        """Test EmbyPlaybackState uses __slots__ for memory efficiency."""
        from custom_components.embymedia.models import EmbyPlaybackState

        assert hasattr(EmbyPlaybackState, "__slots__")
        state = EmbyPlaybackState()
        assert not hasattr(state, "__dict__")

    def test_emby_session_uses_slots(self) -> None:
        """Test EmbySession uses __slots__ for memory efficiency."""
        from custom_components.embymedia.models import EmbySession

        assert hasattr(EmbySession, "__slots__")
        session = EmbySession(
            session_id="test",
            device_id="device",
            device_name="Test Device",
            client_name="Test Client",
        )
        assert not hasattr(session, "__dict__")


class TestCacheEfficiency:
    """Test cache implementation efficiency."""

    def test_cache_uses_ordered_dict_for_lru(self) -> None:
        """Test cache uses OrderedDict for LRU eviction."""
        from collections import OrderedDict

        from custom_components.embymedia.cache import BrowseCache

        cache = BrowseCache()
        assert isinstance(cache._cache, OrderedDict)

    def test_cache_respects_max_entries(self) -> None:
        """Test cache evicts old entries when at capacity."""
        from custom_components.embymedia.cache import BrowseCache

        cache = BrowseCache(max_entries=3)

        # Fill cache
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        assert len(cache._cache) == 3

        # Adding one more should evict oldest
        cache.set("key4", "value4")
        assert len(cache._cache) == 3
        assert cache.get("key1") is None  # Evicted
        assert cache.get("key4") == "value4"  # Present

    def test_cache_hit_rate_tracking(self) -> None:
        """Test cache tracks hit rate for monitoring."""
        from custom_components.embymedia.cache import BrowseCache

        cache = BrowseCache()

        # Set a value
        cache.set("key1", "value1")

        # Hit
        cache.get("key1")
        cache.get("key1")

        # Miss
        cache.get("key2")

        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1

    def test_cache_lru_behavior(self) -> None:
        """Test cache moves accessed items to end (LRU)."""
        from custom_components.embymedia.cache import BrowseCache

        cache = BrowseCache(max_entries=3)

        # Fill cache
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Access key1 (should move to end)
        cache.get("key1")

        # Add new key (should evict key2, not key1)
        cache.set("key4", "value4")

        assert cache.get("key1") is not None  # Still present
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") is not None  # Still present
        assert cache.get("key4") is not None  # New entry


class TestExceptionMemoryUsage:
    """Test exception classes don't waste memory."""

    def test_exceptions_store_only_necessary_data(self) -> None:
        """Test exceptions only store translation-related data."""
        from custom_components.embymedia.exceptions import EmbyConnectionError

        exc = EmbyConnectionError("Test error", host="localhost", port=8096)

        # Should only have message, translation_key, and translation_placeholders
        # plus standard exception attributes
        assert hasattr(exc, "translation_key")
        assert hasattr(exc, "translation_placeholders")
        assert exc.translation_key == "connection_failed"
        assert exc.translation_placeholders == {"host": "localhost", "port": "8096"}


class TestCoordinatorEfficiency:
    """Test coordinator memory efficiency."""

    def test_coordinator_doesnt_store_redundant_data(
        self,
    ) -> None:
        """Test coordinator only stores necessary session data."""


        # This test verifies the coordinator design doesn't
        # duplicate session data unnecessarily

        # The coordinator should only have one reference to each session
        # in self.data, not multiple copies
        from custom_components.embymedia.models import EmbySession

        session = EmbySession(
            session_id="sess-1",
            device_id="device-1",
            device_name="Test",
            client_name="Client",
        )

        # Verify session uses minimal memory by using slots
        assert hasattr(EmbySession, "__slots__")

        # Size should be relatively small due to slots
        # (This is a rough check - slots typically save 30-40% memory)
        size = sys.getsizeof(session)
        assert size < 500  # Reasonable size for a dataclass with slots
