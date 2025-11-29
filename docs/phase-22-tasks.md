# Phase 22: Code Quality & Performance Optimization

## Overview

This phase implements comprehensive code quality improvements identified through an exhaustive code review. The focus is on performance optimization, memory management, code maintainability, and reducing load on both Home Assistant and Emby servers.

Key improvements:
- **Concurrent API Calls** - Use `asyncio.gather()` in coordinators for parallel API requests
- **Memory Management** - Clean up playback session tracking, stream image responses
- **Bug Fixes** - Fix genre browsing filter that currently returns all items
- **Code Quality** - Replace deprecated MD5, fix encapsulation violations, refine exception handling
- **Configuration** - Make WebSocket session interval configurable

## Implementation Status: NOT STARTED

---

## Background Research

### Performance Issues Identified

1. **Sequential API Calls in Coordinators**
   - `EmbyDiscoveryCoordinator._async_update_data()` makes 8 sequential API calls
   - `EmbyServerCoordinator._async_update_data()` makes multiple sequential calls
   - `EmbyLibraryCoordinator._async_update_data()` makes 5+ sequential user-specific calls
   - Each sequential call blocks the event loop, increasing update latency

2. **Memory Leaks**
   - `coordinator.py:135` - `_playback_sessions` dictionary grows unboundedly
   - Sessions are added on `PlaybackProgress` but never removed on `PlaybackStopped`/`SessionEnded`

3. **Inefficient Image Handling**
   - `image_proxy.py:100-102` loads full image into memory before responding
   - For large artwork files, this consumes significant memory

### Bug: Genre Browsing Doesn't Filter

In `media_player.py:1239-1262`, the `_async_browse_genre_items()` method has this comment:
```python
# Note: Emby's genre filtering is complex - for now return all albums
```

This means when a user clicks a genre, they see ALL albums instead of albums in that genre.

**Fix:** Use the `GenreIds` parameter in the API call.

### Hash Function Deprecation

`cache.py:129-130` uses MD5:
```python
return hashlib.md5(key_data.encode()).hexdigest()
```

While not a security issue (it's just for hashing), MD5 is deprecated. Python 3.13+ warns about MD5 usage, and it may be removed in future versions.

---

## Task Breakdown

### Task 22.1: Concurrent API Calls in Discovery Coordinator

**Priority:** Critical
**Files:** `custom_components/embymedia/coordinator_discovery.py`

Refactor `_async_update_data()` to use `asyncio.gather()` for parallel API calls.

#### Current Implementation (Sequential)

```python
next_up = await self.client.async_get_next_up(user_id=self._user_id)
continue_watching = await self.client.async_get_resumable_items(user_id=self._user_id)
recently_added = await self.client.async_get_latest_media(user_id=self._user_id)
suggestions = await self.client.async_get_suggestions(user_id=self._user_id)
favorites_count = await self.client.async_get_user_item_count(user_id=self._user_id, filters="IsFavorite")
played_count = await self.client.async_get_user_item_count(user_id=self._user_id, filters="IsPlayed")
resumable_count = await self.client.async_get_user_item_count(user_id=self._user_id, filters="IsResumable")
playlists = await self.client.async_get_playlists(user_id=self._user_id)
```

#### Target Implementation (Parallel)

```python
import asyncio

# Fetch all data in parallel
(
    next_up,
    continue_watching,
    recently_added,
    suggestions,
    favorites_count,
    played_count,
    resumable_count,
    playlists,
) = await asyncio.gather(
    self.client.async_get_next_up(user_id=self._user_id),
    self.client.async_get_resumable_items(user_id=self._user_id),
    self.client.async_get_latest_media(user_id=self._user_id),
    self.client.async_get_suggestions(user_id=self._user_id),
    self.client.async_get_user_item_count(user_id=self._user_id, filters="IsFavorite"),
    self.client.async_get_user_item_count(user_id=self._user_id, filters="IsPlayed"),
    self.client.async_get_user_item_count(user_id=self._user_id, filters="IsResumable"),
    self.client.async_get_playlists(user_id=self._user_id),
)
```

#### Acceptance Criteria

- [ ] All 8 API calls run in parallel using `asyncio.gather()`
- [ ] Error handling preserved (first exception propagates)
- [ ] All existing tests pass
- [ ] New test added to verify parallel execution
- [ ] Performance improvement documented (measure before/after)

#### TDD Steps

1. **RED**: Write test that mocks API calls and verifies they complete faster than sequential
2. **GREEN**: Refactor to use `asyncio.gather()`
3. **REFACTOR**: Clean up variable unpacking and error handling

---

### Task 22.2: Concurrent API Calls in Server Coordinator

**Priority:** Critical
**Files:** `custom_components/embymedia/coordinator_sensors.py`

Refactor `EmbyServerCoordinator._async_update_data()` to parallelize independent API calls.

#### Current Flow (Sequential)

1. `async_get_server_info()` - Required first (provides base data)
2. `async_get_scheduled_tasks()` - Independent
3. `async_get_live_tv_info()` - Independent
4. `async_get_timers()` - Depends on Live TV being enabled
5. `async_get_series_timers()` - Depends on Live TV being enabled
6. `async_get_recordings()` - Depends on Live TV being enabled
7. `async_get_activity_log()` - Independent
8. `async_get_devices()` - Independent
9. `async_get_plugins()` - Independent

#### Target Implementation

Group independent calls:
```python
# Phase 1: Get server info first (needed for other decisions)
server_info = await self.client.async_get_server_info()

# Phase 2: Independent calls in parallel
(tasks, activity_response, devices_response, plugins) = await asyncio.gather(
    self.client.async_get_scheduled_tasks(),
    self.client.async_get_activity_log(start_index=0, limit=20),
    self.client.async_get_devices(),
    self.client.async_get_plugins(),
    return_exceptions=True,  # Don't fail if one call fails
)

# Phase 3: Live TV calls (only if enabled, can be parallel)
if live_tv_enabled:
    (timers, series_timers, recordings) = await asyncio.gather(
        self.client.async_get_timers(),
        self.client.async_get_series_timers(),
        self._get_recordings_safe(),
        return_exceptions=True,
    )
```

#### Acceptance Criteria

- [ ] Independent API calls grouped with `asyncio.gather()`
- [ ] Live TV calls parallelized when Live TV is enabled
- [ ] `return_exceptions=True` used to prevent one failure from blocking all
- [ ] Results validated (check for Exception instances before using)
- [ ] All existing tests pass
- [ ] Performance improvement documented

#### TDD Steps

1. **RED**: Write test verifying parallel execution timing
2. **GREEN**: Implement parallel fetching with proper exception handling
3. **REFACTOR**: Extract exception checking logic

---

### Task 22.3: Concurrent API Calls in Library Coordinator

**Priority:** Critical
**Files:** `custom_components/embymedia/coordinator_sensors.py`

Refactor `EmbyLibraryCoordinator._async_update_data()` to parallelize user-specific count fetches.

#### Current Flow

```python
# Independent calls - can be parallel
counts = await self.client.async_get_item_counts()
folders = await self.client.async_get_virtual_folders()

# User-specific calls - can be parallel with each other
if self._user_id:
    favorites_count = await self.client.async_get_user_item_count(...)
    played_count = await self.client.async_get_user_item_count(...)
    resumable_count = await self.client.async_get_user_item_count(...)
    playlists = await self.client.async_get_playlists(...)
    collections = await self.client.async_get_collections(...)
```

#### Target Implementation

```python
# Parallel base calls
(counts, folders) = await asyncio.gather(
    self.client.async_get_item_counts(),
    self.client.async_get_virtual_folders(),
)

# Parallel user-specific calls
if self._user_id:
    (favorites_count, played_count, resumable_count, playlists, collections) = await asyncio.gather(
        self.client.async_get_user_item_count(user_id=self._user_id, filters="IsFavorite"),
        self.client.async_get_user_item_count(user_id=self._user_id, filters="IsPlayed"),
        self.client.async_get_user_item_count(user_id=self._user_id, filters="IsResumable"),
        self.client.async_get_playlists(user_id=self._user_id),
        self.client.async_get_collections(user_id=self._user_id),
    )
```

#### Acceptance Criteria

- [ ] Base calls parallelized
- [ ] User-specific calls parallelized
- [ ] All existing tests pass
- [ ] Performance improvement documented

---

### Task 22.4: Fix Genre Browsing Filter

**Priority:** Critical
**Files:** `custom_components/embymedia/media_player.py`

Fix `_async_browse_genre_items()` to actually filter by genre.

#### Current Implementation (Broken)

```python
async def _async_browse_genre_items(self, user_id: str, library_id: str, genre: str) -> BrowseMedia:
    # Note: Emby's genre filtering is complex - for now return all albums
    result = await client.async_get_items(
        user_id,
        parent_id=library_id,
        include_item_types="MusicAlbum",
        recursive=True,
    )
```

#### Target Implementation

```python
async def _async_browse_genre_items(self, user_id: str, library_id: str, genre: str) -> BrowseMedia:
    result = await client.async_get_items(
        user_id,
        parent_id=library_id,
        include_item_types="MusicAlbum",
        recursive=True,
        genres=genre,  # Filter by genre name
    )
```

#### Research Required

Verify the correct Emby API parameter for genre filtering:
- `Genres` - Comma-separated genre names
- `GenreIds` - Comma-separated genre IDs (if we have IDs)

Test against live Emby server to confirm which works.

#### Acceptance Criteria

- [ ] Genre parameter passed to API call
- [ ] Only albums matching the genre are returned
- [ ] Test added for genre filtering
- [ ] Remove the "Note:" comment explaining the workaround

---

### Task 22.5: Playback Session Memory Cleanup

**Priority:** High
**Files:** `custom_components/embymedia/coordinator.py`

Clean up `_playback_sessions` dictionary when sessions end.

#### Current Issue

```python
# Line 135
self._playback_sessions: dict[str, dict[str, int | str]] = {}
```

This dictionary grows unboundedly as sessions are tracked but never cleaned up.

#### Target Implementation

Add cleanup in `_handle_websocket_message()`:

```python
def _handle_websocket_message(self, message_type: str, data: Any) -> None:
    # ... existing code ...

    elif message_type == "PlaybackStopped":
        self._cleanup_playback_session(data)
        self._trigger_debounced_refresh()
    elif message_type == "SessionEnded":
        self._cleanup_session_tracking(data)
        self._trigger_debounced_refresh()

def _cleanup_playback_session(self, data: dict[str, object]) -> None:
    """Remove playback session tracking when playback stops."""
    user_id = data.get("UserId", "")
    device_id = data.get("DeviceId", "")
    play_session_id = data.get("PlaySessionId", device_id)
    tracking_key = f"{user_id}:{play_session_id}"
    self._playback_sessions.pop(tracking_key, None)

def _cleanup_session_tracking(self, data: dict[str, object]) -> None:
    """Remove all tracking for a session that ended."""
    device_id = str(data.get("DeviceId", ""))
    # Remove any entries containing this device_id
    keys_to_remove = [k for k in self._playback_sessions if device_id in k]
    for key in keys_to_remove:
        self._playback_sessions.pop(key, None)
```

#### Additional Enhancement: Maximum Age Eviction

Add periodic cleanup of stale entries:

```python
import time

# In _track_playback_progress(), add timestamp:
self._playback_sessions[tracking_key] = {
    "watch_time": new_watch_time,
    "position_ticks": new_position,
    "last_updated": time.time(),  # Add timestamp
}

# In _async_update_data(), clean stale entries:
def _cleanup_stale_sessions(self, max_age_seconds: int = 3600) -> None:
    """Remove playback sessions older than max_age_seconds."""
    now = time.time()
    keys_to_remove = [
        k for k, v in self._playback_sessions.items()
        if now - v.get("last_updated", 0) > max_age_seconds
    ]
    for key in keys_to_remove:
        self._playback_sessions.pop(key, None)
```

#### Acceptance Criteria

- [ ] Sessions removed on `PlaybackStopped` event
- [ ] Sessions removed on `SessionEnded` event
- [ ] Stale sessions (>1 hour old) automatically cleaned
- [ ] Tests verify cleanup behavior
- [ ] No memory growth over extended runtime

---

### Task 22.6: Streaming Image Proxy

**Priority:** High
**Files:** `custom_components/embymedia/image_proxy.py`

Refactor `EmbyImageProxyView.get()` to stream responses.

#### Current Implementation (Memory-Heavy)

```python
async with session.get(emby_url) as response:
    body = await response.read()  # Loads entire image into memory
    return web.Response(
        status=response.status,
        body=body,
        headers=response_headers,
    )
```

#### Target Implementation (Streaming)

```python
async with session.get(emby_url) as response:
    if response.status != 200:
        return web.Response(status=response.status)

    # Create streaming response
    stream_response = web.StreamResponse(
        status=response.status,
        headers=response_headers,
    )
    await stream_response.prepare(request)

    # Stream chunks
    async for chunk in response.content.iter_chunked(8192):
        await stream_response.write(chunk)

    await stream_response.write_eof()
    return stream_response
```

#### Acceptance Criteria

- [ ] Response streamed in 8KB chunks
- [ ] Memory usage constant regardless of image size
- [ ] Headers properly forwarded
- [ ] Error responses handled correctly
- [ ] Tests verify streaming behavior

---

### Task 22.7: Parallel Service Execution

**Priority:** High
**Files:** `custom_components/embymedia/services.py`

Refactor service handlers to use `asyncio.gather()` for multi-entity operations.

#### Current Implementation

```python
for entity_id in entity_ids:
    coordinator = _get_coordinator_for_entity(hass, entity_id)
    if coordinator:
        await coordinator.client.async_send_message(...)
```

#### Target Implementation

```python
async def _execute_for_entities(
    hass: HomeAssistant,
    entity_ids: list[str],
    operation: Callable[[EmbyClient, str], Coroutine[None, None, None]],
) -> None:
    """Execute an operation for multiple entities in parallel."""
    tasks = []
    for entity_id in entity_ids:
        coordinator = _get_coordinator_for_entity(hass, entity_id)
        if coordinator:
            tasks.append(operation(coordinator.client, entity_id))

    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Log any failures
        for entity_id, result in zip(entity_ids, results):
            if isinstance(result, Exception):
                _LOGGER.error("Service failed for %s: %s", entity_id, result)
```

#### Acceptance Criteria

- [ ] Multi-entity operations run in parallel
- [ ] Individual failures don't block other entities
- [ ] Errors logged per-entity
- [ ] All existing tests pass
- [ ] New tests verify parallel execution

---

### Task 22.8: Replace MD5 with Modern Hash

**Priority:** High
**Files:** `custom_components/embymedia/cache.py`

Replace MD5 with SHA-256 or BLAKE2b.

#### Current Implementation

```python
return hashlib.md5(key_data.encode()).hexdigest()
```

#### Target Implementation

```python
# Option 1: SHA-256 (widely available, slightly slower)
return hashlib.sha256(key_data.encode()).hexdigest()

# Option 2: BLAKE2b (faster, modern)
return hashlib.blake2b(key_data.encode(), digest_size=16).hexdigest()
```

**Recommendation:** Use BLAKE2b with 16-byte digest - faster than MD5 and SHA-256.

#### Acceptance Criteria

- [ ] MD5 replaced with BLAKE2b
- [ ] Cache keys still unique and deterministic
- [ ] All cache tests pass
- [ ] No change in cache behavior

---

### Task 22.9: Add Public API Key Property

**Priority:** Medium
**Files:** `custom_components/embymedia/api.py`, `custom_components/embymedia/image_proxy.py`

Add public property for API key access.

#### Current Issue

```python
# image_proxy.py:93-94
coordinator.client._api_key  # Accessing private attribute
```

#### Target Implementation

```python
# api.py
@property
def api_key(self) -> str:
    """Return the API key for authentication."""
    return self._api_key

# image_proxy.py
coordinator.client.api_key  # Use public property
```

#### Acceptance Criteria

- [ ] Public `api_key` property added to `EmbyClient`
- [ ] `image_proxy.py` updated to use public property
- [ ] Tests verify property access

---

### Task 22.10: Fix Diagnostics Private Attribute Access

**Priority:** Medium
**Files:** `custom_components/embymedia/diagnostics.py`

Use public property instead of private attribute.

#### Current Issue

```python
# diagnostics.py:67
"websocket_enabled": coordinator._websocket_enabled,
```

#### Verification Required

Check if `websocket_enabled` property already exists:
```python
# coordinator.py - verify this property exists
@property
def websocket_enabled(self) -> bool:
    """Return whether WebSocket is enabled."""
    return self._websocket_enabled
```

#### Target Implementation

```python
# diagnostics.py
"websocket_enabled": coordinator.websocket_enabled,  # Use public property
```

#### Acceptance Criteria

- [ ] Verify `websocket_enabled` property exists (add if not)
- [ ] Update diagnostics to use public property
- [ ] All diagnostics tests pass

---

### Task 22.11: Add Image Fetch Timeout

**Priority:** Medium
**Files:** `custom_components/embymedia/image_discovery.py`

Add explicit timeout to image fetches.

#### Current Implementation

```python
async with session.get(image_url) as response:
    # No timeout - can hang indefinitely
```

#### Target Implementation

```python
timeout = aiohttp.ClientTimeout(total=10)
async with session.get(image_url, timeout=timeout) as response:
    # Times out after 10 seconds
```

#### Acceptance Criteria

- [ ] 10-second timeout added to all image fetches
- [ ] Timeout exception handled gracefully
- [ ] Tests verify timeout behavior

---

### Task 22.12: Refine Exception Handling

**Priority:** Medium
**Files:** Multiple

Replace broad `except Exception:` with specific exceptions.

#### Locations to Fix

1. **`__init__.py:269`**
   ```python
   # Current
   except Exception:
   # Target
   except EmbyError as err:
       _LOGGER.warning("Failed to create discovery coordinator: %s", err)
   ```

2. **`__init__.py:319`**
   ```python
   # Current
   except Exception:
   # Target
   except (aiohttp.ClientError, OSError) as err:
       _LOGGER.error("Failed to fetch image: %s", err)
   ```

3. **`remote.py:267`**
   ```python
   # Current
   except Exception as err:
   # Target
   except (EmbyError, aiohttp.ClientError) as err:
       raise HomeAssistantError(f"Failed to send command: {err}") from err
   ```

4. **`image_discovery.py:163`**
   ```python
   # Current
   except Exception as err:
   # Target
   except (aiohttp.ClientError, OSError, TimeoutError) as err:
       _LOGGER.debug("Image discovery failed: %s", err)
   ```

#### Acceptance Criteria

- [ ] All 4 locations updated with specific exceptions
- [ ] Logging preserved for debugging
- [ ] Tests verify exception handling

---

### Task 22.13: Extract Letter Browsing Helper

**Priority:** Low
**Files:** `custom_components/embymedia/media_player.py`

Extract common logic from `_async_browse_*_by_letter` methods.

#### Current Duplication

- `_async_browse_artists_by_letter()`
- `_async_browse_albums_by_letter()`
- `_async_browse_movies_by_letter()`
- `_async_browse_series_by_letter()`

All have similar logic:
```python
name_filter = "" if letter == "#" else letter
result = await client.async_get_items(user_id, parent_id=library_id, ...)
if letter == "#":
    items = [i for i in items if not i.get("Name", "")[0:1].isalpha()]
```

#### Target Implementation

```python
async def _async_browse_items_by_letter(
    self,
    user_id: str,
    library_id: str,
    letter: str,
    item_type: str,
    title_prefix: str,
    content_type: str,
    media_class: MediaClass,
) -> BrowseMedia:
    """Browse items starting with a specific letter.

    Generic helper for letter-based browsing across different item types.
    """
    coordinator: EmbyDataUpdateCoordinator = self.coordinator
    client = coordinator.client

    name_filter = "" if letter == "#" else letter

    result = await client.async_get_items(
        user_id,
        parent_id=library_id,
        include_item_types=item_type,
        recursive=True,
        name_starts_with=name_filter if name_filter else None,
    )
    items = result.get("Items", [])

    # For "#", filter to non-alpha items manually
    if letter == "#":
        items = [i for i in items if not i.get("Name", "")[0:1].isalpha()]

    children = [self._item_to_browse_media(item) for item in items]

    return BrowseMedia(
        media_class=MediaClass.DIRECTORY,
        media_content_id=encode_content_id(content_type, library_id, letter),
        media_content_type=media_class,
        title=f"{title_prefix} - {letter}",
        can_play=False,
        can_expand=True,
        children=children,
    )
```

#### Acceptance Criteria

- [ ] Generic helper method created
- [ ] All 4 existing methods refactored to use helper
- [ ] All existing tests pass
- [ ] Code deduplication verified

---

### Task 22.14: Web Player Detection Optimization

**Priority:** Low
**Files:** `custom_components/embymedia/coordinator.py`

Optimize web player client name detection.

#### Current Implementation

```python
# Line 214
return any(web_client.lower() in client_name for web_client in WEB_PLAYER_CLIENTS)
```

This converts strings to lowercase and does substring search for each check.

#### Target Implementation

```python
# const.py - precompute lowercase set
WEB_PLAYER_CLIENTS_LOWER = frozenset(c.lower() for c in WEB_PLAYER_CLIENTS)

# coordinator.py - O(1) lookup
def _is_web_player(self, session: EmbySession) -> bool:
    client_name = session.client_name.lower()
    return client_name in WEB_PLAYER_CLIENTS_LOWER
```

**Note:** This changes from substring matching to exact matching. Verify this is acceptable with real client names.

#### Acceptance Criteria

- [ ] Pre-computed lowercase set in const.py
- [ ] O(1) lookup instead of O(n) substring search
- [ ] Verify behavior with actual web player client names
- [ ] Tests updated for new matching behavior

---

### Task 22.15: Configurable WebSocket Session Interval

**Priority:** Low
**Files:** `custom_components/embymedia/const.py`, `custom_components/embymedia/config_flow.py`, `custom_components/embymedia/websocket.py`

Make WebSocket session subscription interval configurable.

#### Current Implementation

```python
# websocket.py:137
async def async_subscribe_sessions(self, interval_ms: int = 1500) -> None:
```

Hardcoded 1500ms may be too frequent for stable sessions.

#### Target Implementation

1. Add constant and config option:
   ```python
   # const.py
   CONF_WEBSOCKET_INTERVAL = "websocket_interval"
   DEFAULT_WEBSOCKET_INTERVAL = 1500  # ms
   ```

2. Add to options flow:
   ```python
   # config_flow.py options step
   vol.Optional(
       CONF_WEBSOCKET_INTERVAL,
       default=DEFAULT_WEBSOCKET_INTERVAL,
   ): vol.All(vol.Coerce(int), vol.Range(min=500, max=10000)),
   ```

3. Use in coordinator:
   ```python
   interval = config_entry.options.get(CONF_WEBSOCKET_INTERVAL, DEFAULT_WEBSOCKET_INTERVAL)
   await self._websocket.async_subscribe_sessions(interval_ms=interval)
   ```

#### Acceptance Criteria

- [ ] Config option added to options flow
- [ ] Interval range: 500ms - 10000ms
- [ ] Default remains 1500ms
- [ ] Coordinator uses configured value
- [ ] Tests verify configuration

---

### Task 22.16: Add Cache Statistics Reset

**Priority:** Low
**Files:** `custom_components/embymedia/cache.py`

Add method to reset cache statistics.

#### Target Implementation

```python
def reset_stats(self) -> None:
    """Reset cache hit/miss statistics."""
    self._hits = 0
    self._misses = 0
```

#### Acceptance Criteria

- [ ] `reset_stats()` method added
- [ ] Stats reset to zero
- [ ] Test verifies reset behavior

---

## Testing Requirements

### Performance Benchmarks

Add benchmarks to measure coordinator update times:

```python
@pytest.fixture
def benchmark_coordinator(hass: HomeAssistant, mock_client: MagicMock) -> EmbyDiscoveryCoordinator:
    """Create coordinator for benchmarking."""
    # Add artificial delay to mock API calls
    async def slow_api_call(*args, **kwargs):
        await asyncio.sleep(0.1)  # 100ms per call
        return []

    mock_client.async_get_next_up.side_effect = slow_api_call
    # ... other mocks
    return coordinator

async def test_parallel_execution_performance(benchmark_coordinator):
    """Verify parallel execution is faster than sequential."""
    import time

    start = time.time()
    await benchmark_coordinator.async_refresh()
    elapsed = time.time() - start

    # 8 calls at 100ms each:
    # Sequential: 800ms minimum
    # Parallel: ~100ms (plus overhead)
    assert elapsed < 0.3  # Should complete in under 300ms
```

### Coverage Requirements

- All new code must have 100% test coverage
- Existing tests must continue to pass
- Add integration tests for critical paths

---

## Documentation Updates

### CHANGELOG Entry

```markdown
## [0.11.0] - TBD

### Changed
- **Performance**: Coordinator API calls now execute in parallel using `asyncio.gather()`
- **Performance**: Image proxy now streams responses instead of loading full images to memory
- **Performance**: Service calls for multiple entities now execute in parallel

### Fixed
- Genre browsing now correctly filters by selected genre (was returning all items)
- Memory leak in playback session tracking cleaned up
- Replaced deprecated MD5 hash with BLAKE2b in cache

### Improved
- Added public `api_key` property to EmbyClient for better encapsulation
- Refined exception handling with specific exception types
- Added configurable WebSocket session interval option
```

### README Updates

Add performance section documenting:
- Parallel coordinator updates
- Memory-efficient image proxying
- Configurable polling intervals

---

## Verification Checklist

Before marking phase complete:

- [ ] All tasks implemented with TDD
- [ ] All tests pass (pytest)
- [ ] 100% code coverage maintained
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Performance improvements measured and documented
- [ ] CHANGELOG updated
- [ ] README updated if needed
