"""Browse cache for Emby media browsing."""

from __future__ import annotations

import functools
import hashlib
import json
import logging
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, ParamSpec, TypeVar

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)

# Type variables for the cached decorator
P = ParamSpec("P")
R = TypeVar("R")


class BrowseCache:
    """In-memory cache with TTL for browse API responses.

    Provides caching for expensive API calls like getting genres, years,
    and library items to improve browse responsiveness.
    """

    def __init__(
        self,
        ttl_seconds: float = 300.0,
        max_entries: int = 1000,
    ) -> None:
        """Initialize the browse cache.

        Args:
            ttl_seconds: Time to live for cache entries in seconds.
            max_entries: Maximum number of entries to store.
        """
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._cache: OrderedDict[str, tuple[float, object]] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> object | None:
        """Get a value from the cache.

        Args:
            key: The cache key.

        Returns:
            The cached value or None if not found or expired.
        """
        if key not in self._cache:
            self._misses += 1
            return None

        timestamp, value = self._cache[key]
        if time.time() - timestamp > self._ttl:
            # Expired
            del self._cache[key]
            self._misses += 1
            return None

        # Move to end (most recently accessed)
        self._cache.move_to_end(key)
        self._hits += 1
        return value

    def set(self, key: str, value: object) -> None:
        """Set a value in the cache.

        Args:
            key: The cache key.
            value: The value to cache.
        """
        # Remove oldest entries if at max capacity
        while len(self._cache) >= self._max_entries:
            self._cache.popitem(last=False)

        self._cache[key] = (time.time(), value)
        # Move to end (most recently added)
        self._cache.move_to_end(key)

    def delete(self, key: str) -> None:
        """Delete a specific cache entry.

        Args:
            key: The cache key to delete.
        """
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def invalidate_prefix(self, prefix: str) -> None:
        """Invalidate all cache entries with keys starting with prefix.

        Args:
            prefix: The key prefix to invalidate.
        """
        keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
        for key in keys_to_remove:
            del self._cache[key]

    def generate_key(self, func_name: str, *args: object, **kwargs: object) -> str:
        """Generate a cache key from function name and arguments.

        Args:
            func_name: The function name.
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            A unique cache key string.
        """
        # Sort kwargs for consistent ordering
        sorted_kwargs = sorted(kwargs.items())
        key_data = json.dumps(
            {"func": func_name, "args": args, "kwargs": sorted_kwargs},
            sort_keys=True,
            default=str,
        )
        # Use MD5 for short, deterministic key
        return hashlib.md5(key_data.encode()).hexdigest()

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with hits, misses, and current entry count.
        """
        return {
            "hits": self._hits,
            "misses": self._misses,
            "entries": len(self._cache),
        }


def cached(
    cache: BrowseCache, func_name: str
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Decorator for caching async function results.

    Args:
        cache: The BrowseCache instance to use.
        func_name: Name to use for cache key generation.

    Returns:
        Decorator function.
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Check for bypass_cache parameter
            bypass = kwargs.pop("bypass_cache", False)

            if not bypass:
                # Generate cache key
                key = cache.generate_key(func_name, *args, **kwargs)

                # Try to get from cache
                cached_result = cache.get(key)
                if cached_result is not None:
                    return cached_result  # type: ignore[return-value]

            # Call the function
            result = await func(*args, **kwargs)

            if not bypass:
                # Store in cache
                cache.set(key, result)

            return result

        return wrapper

    return decorator


__all__ = ["BrowseCache", "cached"]
