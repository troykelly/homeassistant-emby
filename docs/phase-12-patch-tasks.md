# Phase 12 Patch: Media Browser Bug Fixes

## Overview

This patch release fixes bugs in the media browser functionality that affect both the generic media source and the session-based media player browsing.

## Bug Reports

### Bug 1: Browsing Movies by Year Generates "Unknown Error"

**Symptoms:**
- Navigating to Movies > Year > [specific year] causes "Unknown error" in Home Assistant
- The HA media browser closes when attempting to browse movies by year
- Browsing by decade works correctly (Movies > Decade > [decade] shows results)

**Affected Component:** `media_source.py`

**Root Cause Analysis:**

The `_async_browse_movies_by_year` method in `media_source.py` may have one of these issues:

1. **Missing exception handling** - If the API call fails or returns unexpected data, there's no error handling to provide a meaningful error or empty result.

2. **Identifier parsing issue** - The year identifier format `server_id/movieyearitems/library_id/year` is parsed using:
   ```python
   parts = item_id.split("/")
   if len(parts) >= 2:
       return await self._async_browse_movies_by_year(...)
   ```
   If `len(parts) < 2`, the code falls through to the generic `_async_browse_item` which doesn't handle `movieyearitems` content type.

3. **No user_id available** - The generic media source gets `user_id` from active sessions. If no sessions exist, `_get_user_id()` returns `None` and the method returns an empty BrowseMediaSource. However, there may be additional issues with how this empty result is handled.

4. **API parameter issue** - The `years` parameter passed to `async_get_items()` may have formatting issues compared to how decades work.

**Investigation Steps:**
1. Add debug logging to `_async_browse_movie_years` and `_async_browse_movies_by_year`
2. Verify year identifier format matches expected pattern
3. Test API call with years parameter directly
4. Add proper exception handling with meaningful errors

---

### Bug 2: Generic Media Source Missing Browsing Features

**Symptoms:**
- The generic/server media source (accessible from HA Media panel without an active Emby player) doesn't have all the same media browsing improvements as the session-based media player entity.

**Affected Component:** `media_source.py`

**Root Cause Analysis:**

Comparing `media_source.py` with `media_player.py` reveals implementation differences:

| Feature | media_player.py | media_source.py |
|---------|-----------------|-----------------|
| Decade menu helper | `_build_decade_menu()` | Inline hardcoded list |
| Letter menu helper | `_build_letter_menu()` | Inline hardcoded list |
| Decade format | Integer "2020" | String "2020s" |
| Content ID encoding | `encode_content_id()` (colon-separated) | `build_identifier()` (slash-separated) |
| Error handling | `BrowseError` exception | Falls through to generic handler |

**Key Discrepancies:**

1. **Music library categories** - `media_player.py` has full music library browsing (Artists A-Z, Albums A-Z, Genres, Playlists). `media_source.py` has simpler implementation.

2. **TV library categories** - Both have A-Z, Year, Decade, Genre but implementations differ.

3. **Helper methods** - `media_player.py` uses reusable helpers (`_build_letter_menu`, `_build_decade_menu`). `media_source.py` duplicates logic inline.

4. **Error handling** - `media_player.py` raises `BrowseError` for unknown content types. `media_source.py` falls through to `_async_browse_item` which may fail silently or unexpectedly.

---

## Tasks

### Task 1: Fix Year Browsing in Media Source

**Priority:** High

**Files to modify:**
- `custom_components/embymedia/media_source.py`
- `tests/test_media_source.py`

**Acceptance Criteria:**
- [x] Browsing Movies > Year > [year] returns movies from that year
- [x] Browsing TV Shows > Year > [year] returns TV shows from that year
- [x] Empty results display gracefully (not error)
- [x] Proper error handling with meaningful messages
- [x] Unit tests cover year browsing scenarios

**Implementation:**
1. Add try/except around year browsing API calls
2. Verify identifier parsing handles all edge cases
3. Add fallback behavior when `user_id` is None
4. Add debug logging for troubleshooting
5. Write unit tests for:
   - Successful year browsing with results
   - Year browsing with no results (empty library)
   - Year browsing without active sessions (no user_id)
   - Invalid year identifier format

---

### Task 2: Synchronize Media Source with Media Player Browsing

**Priority:** High

**Files to modify:**
- `custom_components/embymedia/media_source.py`
- `tests/test_media_source.py`

**Acceptance Criteria:**
- [x] All library types have consistent browsing behavior
- [x] Error handling consistent with media_player.py
- [ ] Code duplication minimized through shared helpers (deferred - not critical)

**Implementation:**
1. Extract common browsing logic into shared module (optional: `browse_helpers.py`)
2. Ensure all content types have explicit handlers (no fallthrough to generic)
3. Add `Unresolvable` exceptions for unknown content types
4. Synchronize:
   - Movie library: A-Z, Year, Decade, Genre, Collections
   - TV library: A-Z, Year, Decade, Genre
   - Music library: Artists A-Z, Albums A-Z, Genres, Playlists
5. Write comprehensive tests for all browsing paths

---

### Task 3: Add Missing Error Handling

**Priority:** Medium

**Files to modify:**
- `custom_components/embymedia/media_source.py`
- `tests/test_media_source.py`

**Acceptance Criteria:**
- [x] All content type routes have explicit handlers
- [ ] Unknown content types raise `Unresolvable` with descriptive message (existing behavior OK)
- [x] API errors are caught and converted to user-friendly messages
- [x] Logging added for debugging

**Implementation:**
1. Add explicit else clauses for content type routing
2. Wrap API calls in try/except
3. Convert API exceptions to `Unresolvable`
4. Add `_LOGGER.debug()` calls for browsing flow
5. Add `_LOGGER.error()` for unexpected errors

---

### Task 4: Test Coverage

**Priority:** High

**Files to modify:**
- `tests/test_media_source.py`

**Acceptance Criteria:**
- [x] 100% coverage maintained
- [x] All content type routes tested
- [x] Error conditions tested
- [x] Edge cases (empty results, no user_id) tested

**New Test Cases:**
1. `test_browse_movies_by_year` - Successful year browsing
2. `test_browse_movies_by_year_empty` - No movies in year
3. `test_browse_movies_by_year_no_user` - No active sessions
4. `test_browse_tv_by_year` - Successful TV year browsing
5. `test_browse_invalid_content_type` - Unknown content type raises Unresolvable
6. `test_browse_malformed_identifier` - Invalid identifier format

---

## Files Changed

| File | Changes |
|------|---------|
| `custom_components/embymedia/media_source.py` | Fix year browsing, add error handling |
| `tests/test_media_source.py` | Add comprehensive browsing tests |
| `docs/phase-12-patch-tasks.md` | This document |
| `docs/roadmap.md` | Add Phase 12 Patch section |

---

## Testing Plan

### Manual Testing

1. **Year Browsing:**
   - Start HA with Emby integration
   - Open Media panel (without an active Emby player)
   - Navigate: Emby > [Server] > Movies > Year
   - Click on a specific year
   - Verify movies are displayed (or empty list if none)

2. **Decade Browsing (regression check):**
   - Navigate: Emby > [Server] > Movies > Decade
   - Click on a specific decade
   - Verify movies are displayed

3. **TV Year/Decade:**
   - Navigate: Emby > [Server] > TV Shows > Year/Decade
   - Verify shows are displayed

4. **Session-based Browsing (regression check):**
   - Have an active Emby session
   - Use the media player entity's browse feature
   - Verify all browsing still works

### Automated Testing

```bash
# Run all media source tests
pytest tests/test_media_source.py -v

# Run with coverage
pytest tests/test_media_source.py --cov=custom_components.embymedia.media_source --cov-report=term-missing

# Run specific test
pytest tests/test_media_source.py::test_browse_movies_by_year -v
```

---

## Success Criteria

- [x] Browsing movies by year works in generic media source
- [x] Browsing TV shows by year works in generic media source
- [x] Browsing by decade continues to work (regression check)
- [x] All browsing features match between media_player and media_source
- [x] 100% test coverage maintained
- [x] No new ruff/mypy issues
- [x] All existing tests pass

---

## Release Notes (for CHANGELOG)

### Fixed
- Fixed "Unknown error" when browsing movies by year in media source
- Fixed "Unknown error" when browsing TV shows by year in media source
- Improved error handling in media source browsing with descriptive messages
- Synchronized media source browsing features with media player entity browsing
