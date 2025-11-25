# Phase 5: Media Browsing

## Overview

This phase implements media browsing capabilities for the Emby integration, allowing users to browse and play content directly from the Home Assistant Media Browser UI.

**Features:**
- Browse Emby libraries (Movies, TV Shows, Music, etc.)
- Navigate hierarchical content (Series → Seasons → Episodes)
- Play content directly from browse UI
- Thumbnail support for browse items
- Search and filter capabilities

## Dependencies

- Phase 4 complete (image URL generation for thumbnails)
- Home Assistant `BrowseMedia` class
- Emby API library browsing endpoints

## Home Assistant Browse Media API

### BrowseMedia Class (HA 2025)

```python
from homeassistant.components.media_player.browse_media import BrowseMedia

BrowseMedia(
    *,  # All arguments are keyword-only
    media_class: MediaClass | str,          # Classification (directory, movie, etc.)
    media_content_id: str,                  # Unique ID for navigation
    media_content_type: MediaType | str,    # Type (video, music, etc.)
    title: str,                             # Display name
    can_play: bool,                         # Is playable
    can_expand: bool,                       # Has children
    children: Sequence[BrowseMedia] | None = None,  # Child items
    children_media_class: MediaClass | str | None = None,  # Class for all children
    thumbnail: str | None = None,           # Preview image URL
    not_shown: int = 0,                     # Count of hidden items
    can_search: bool = False,               # Supports search (new in 2025)
)
```

**Note:** HA 2025 added `can_search` and `SEARCH_MEDIA` feature flag for media search.

### MediaClass Values

| MediaClass | Usage |
|------------|-------|
| DIRECTORY | Container/folder |
| MOVIE | Movie item |
| TV_SHOW | TV Series |
| SEASON | TV Season |
| EPISODE | TV Episode |
| MUSIC | Music container |
| ARTIST | Music artist |
| ALBUM | Music album |
| TRACK | Music track |
| PLAYLIST | Playlist |
| CHANNEL | Live TV channel |

### Feature Flags (HA 2025)

```python
from homeassistant.components.media_player import MediaPlayerEntityFeature

# Relevant feature flags for browse/play
MediaPlayerEntityFeature.BROWSE_MEDIA      # 131072 - Enable media browsing
MediaPlayerEntityFeature.PLAY_MEDIA        # 512 - Enable play_media service
MediaPlayerEntityFeature.MEDIA_ENQUEUE     # 2097152 - Support enqueue options
MediaPlayerEntityFeature.SEARCH_MEDIA      # 4194304 - Support search (new in 2025)
```

---

## Emby API Endpoints

### Get User Views (Libraries)

```
GET /Users/{userId}/Views
```

Returns available libraries for the user.

**Response:**
```json
{
  "Items": [
    {
      "Id": "library-movies",
      "Name": "Movies",
      "CollectionType": "movies",
      "ImageTags": {"Primary": "abc123"}
    },
    {
      "Id": "library-tvshows",
      "Name": "TV Shows",
      "CollectionType": "tvshows"
    }
  ]
}
```

### Browse Library Contents

```
GET /Users/{userId}/Items
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `ParentId` | string | Library or folder ID |
| `IncludeItemTypes` | string | Filter by type (Movie, Series, etc.) |
| `SortBy` | string | Sort field (SortName, DateCreated, etc.) |
| `SortOrder` | string | Ascending or Descending |
| `Limit` | int | Max items per page |
| `StartIndex` | int | Pagination offset |
| `Recursive` | bool | Include nested items |
| `Fields` | string | Additional fields to include |

**Response:**
```json
{
  "Items": [
    {
      "Id": "movie-123",
      "Name": "Movie Title",
      "Type": "Movie",
      "ImageTags": {"Primary": "def456"},
      "ProductionYear": 2024,
      "RunTimeTicks": 72000000000
    }
  ],
  "TotalRecordCount": 150,
  "StartIndex": 0
}
```

### Get Seasons

```
GET /Shows/{seriesId}/Seasons
```

### Get Episodes

```
GET /Shows/{seriesId}/Episodes?SeasonId={seasonId}
```

### Play Media

```
POST /Sessions/{sessionId}/Playing
```

**Body:**
```json
{
  "ItemIds": ["item-id-1", "item-id-2"],
  "StartPositionTicks": 0,
  "PlayCommand": "PlayNow"
}
```

---

## Tasks

### Task 5.1: API Methods for Browsing

Add methods to `EmbyClient` for library browsing.

#### 5.1.1 Add async_get_user_views method

**File:** `custom_components/embymedia/api.py`

**Signature:**
```python
async def async_get_user_views(self, user_id: str) -> list[EmbyLibraryResponse]:
    """Get available libraries for a user.

    Args:
        user_id: The user ID.

    Returns:
        List of library items.
    """
```

**Acceptance Criteria:**
- [ ] Makes GET request to /Users/{userId}/Views
- [ ] Returns list of library items
- [ ] Handles authentication errors

**Test Cases:**
- [ ] `test_get_user_views_success`
- [ ] `test_get_user_views_empty`
- [ ] `test_get_user_views_auth_error`

#### 5.1.2 Add async_get_items method

**Signature:**
```python
async def async_get_items(
    self,
    user_id: str,
    parent_id: str | None = None,
    include_item_types: str | None = None,
    sort_by: str = "SortName",
    sort_order: str = "Ascending",
    limit: int = 100,
    start_index: int = 0,
    recursive: bool = False,
) -> EmbyItemsResponse:
    """Get items from a library or folder.

    Args:
        user_id: The user ID.
        parent_id: Parent library/folder ID.
        include_item_types: Filter by item type.
        sort_by: Sort field.
        sort_order: Sort direction.
        limit: Max items to return.
        start_index: Pagination offset.
        recursive: Include nested items.

    Returns:
        Items response with items and total count.
    """
```

**Acceptance Criteria:**
- [ ] Makes GET request to /Users/{userId}/Items
- [ ] Includes query parameters
- [ ] Returns items with total count
- [ ] Supports pagination

**Test Cases:**
- [ ] `test_get_items_from_library`
- [ ] `test_get_items_with_type_filter`
- [ ] `test_get_items_pagination`
- [ ] `test_get_items_recursive`

#### 5.1.3 Add async_get_seasons method

**Signature:**
```python
async def async_get_seasons(
    self,
    user_id: str,
    series_id: str,
) -> list[EmbySeasonResponse]:
    """Get seasons for a TV series."""
```

**Test Cases:**
- [ ] `test_get_seasons_success`
- [ ] `test_get_seasons_empty`

#### 5.1.4 Add async_get_episodes method

**Signature:**
```python
async def async_get_episodes(
    self,
    user_id: str,
    series_id: str,
    season_id: str | None = None,
) -> list[EmbyEpisodeResponse]:
    """Get episodes for a series or season."""
```

**Test Cases:**
- [ ] `test_get_episodes_by_series`
- [ ] `test_get_episodes_by_season`

#### 5.1.5 Add async_play_items method

**Signature:**
```python
async def async_play_items(
    self,
    session_id: str,
    item_ids: list[str],
    start_position_ticks: int = 0,
    play_command: str = "PlayNow",
) -> None:
    """Play items on a session.

    Args:
        session_id: Target session ID.
        item_ids: List of item IDs to play.
        start_position_ticks: Starting position.
        play_command: PlayNow, PlayNext, or PlayLast.
    """
```

**Test Cases:**
- [ ] `test_play_items_single`
- [ ] `test_play_items_multiple`
- [ ] `test_play_items_with_position`

---

### Task 5.2: TypedDicts for Browse Responses

Add TypedDicts for API responses.

**File:** `custom_components/embymedia/const.py`

```python
class EmbyLibraryItem(TypedDict):
    """Library item from user views."""
    Id: str
    Name: str
    CollectionType: NotRequired[str]
    ImageTags: NotRequired[dict[str, str]]

class EmbyBrowseItem(TypedDict):
    """Item from browse response."""
    Id: str
    Name: str
    Type: str
    ImageTags: NotRequired[dict[str, str]]
    ProductionYear: NotRequired[int]
    SeriesName: NotRequired[str]
    SeasonName: NotRequired[str]
    IndexNumber: NotRequired[int]
    ParentIndexNumber: NotRequired[int]

class EmbyItemsResponse(TypedDict):
    """Response from /Users/{id}/Items."""
    Items: list[EmbyBrowseItem]
    TotalRecordCount: int
    StartIndex: int
```

**Acceptance Criteria:**
- [ ] All browse response types defined
- [ ] No mypy errors

---

### Task 5.3: Implement async_browse_media

Add media browsing to `EmbyMediaPlayer`.

#### 5.3.1 Root Level Browsing

When called with no arguments, return library list.

**File:** `custom_components/embymedia/media_player.py`

**Implementation:**
```python
async def async_browse_media(
    self,
    media_content_type: str | None = None,
    media_content_id: str | None = None,
) -> BrowseMedia:
    """Implement media browsing."""
    if media_content_id is None:
        # Return root level with libraries
        return await self._async_browse_root()

    # Parse content_id and browse accordingly
    return await self._async_browse_item(media_content_type, media_content_id)
```

**Acceptance Criteria:**
- [ ] Returns libraries at root level
- [ ] Libraries have correct media_class (DIRECTORY)
- [ ] Libraries have thumbnail URLs
- [ ] can_expand=True for all libraries

**Test Cases:**
- [ ] `test_browse_media_root`
- [ ] `test_browse_media_root_with_thumbnails`

#### 5.3.2 Library Browsing

Browse contents of a library.

**Acceptance Criteria:**
- [ ] Returns items in library
- [ ] Items have correct media_class per type
- [ ] Movies: can_play=True, can_expand=False
- [ ] Series: can_play=False, can_expand=True

**Test Cases:**
- [ ] `test_browse_media_movies_library`
- [ ] `test_browse_media_tvshows_library`
- [ ] `test_browse_media_music_library`

#### 5.3.3 Hierarchical Browsing

Navigate TV Show → Season → Episode hierarchy.

**Acceptance Criteria:**
- [ ] Series shows seasons as children
- [ ] Season shows episodes as children
- [ ] Episodes are playable

**Test Cases:**
- [ ] `test_browse_media_series`
- [ ] `test_browse_media_season`
- [ ] `test_browse_media_episode`

---

### Task 5.4: Content ID Encoding

Design content ID format for navigation.

**Format:** `type:id` or `type:parent_id:child_id`

```python
# Examples:
"library:abc123"           # Browse library abc123
"series:xyz789"            # Browse series xyz789 (show seasons)
"season:xyz789:season1"    # Browse season (show episodes)
"movie:movie123"           # Playable movie
"episode:xyz789:ep1"       # Playable episode
```

**Helper functions:**
```python
def encode_content_id(content_type: str, *ids: str) -> str:
    """Encode content type and IDs into content_id."""
    return f"{content_type}:{':'.join(ids)}"

def decode_content_id(content_id: str) -> tuple[str, list[str]]:
    """Decode content_id into type and ID parts."""
    parts = content_id.split(":")
    return parts[0], parts[1:]
```

**Acceptance Criteria:**
- [ ] Content IDs encode/decode correctly
- [ ] Can navigate full hierarchy
- [ ] Supports all content types

**Test Cases:**
- [ ] `test_encode_content_id`
- [ ] `test_decode_content_id`
- [ ] `test_content_id_roundtrip`

---

### Task 5.5: Implement async_play_media

Add media playback from browse.

**File:** `custom_components/embymedia/media_player.py`

**Signature:**
```python
async def async_play_media(
    self,
    media_type: MediaType | str,
    media_id: str,
    enqueue: MediaPlayerEnqueue | None = None,
    announce: bool | None = None,
    **kwargs: Any,
) -> None:
    """Play media on the Emby client."""
```

**Implementation:**
1. Decode `media_id` to get Emby item ID
2. Call `async_play_items` on API client
3. Handle enqueue options

**Acceptance Criteria:**
- [ ] Plays single items
- [ ] Supports enqueue options (add, next, replace)
- [ ] Works with movies, episodes, tracks
- [ ] Handles invalid media_id gracefully

**Test Cases:**
- [ ] `test_play_media_movie`
- [ ] `test_play_media_episode`
- [ ] `test_play_media_track`
- [ ] `test_play_media_enqueue_next`
- [ ] `test_play_media_invalid_id`

---

### Task 5.6: Add BROWSE_MEDIA Feature Flag

Update supported features.

**File:** `custom_components/embymedia/media_player.py`

```python
_attr_supported_features = (
    MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.PREVIOUS_TRACK
    | MediaPlayerEntityFeature.SEEK
    | MediaPlayerEntityFeature.BROWSE_MEDIA  # NEW
    | MediaPlayerEntityFeature.PLAY_MEDIA    # NEW
)
```

**Acceptance Criteria:**
- [ ] BROWSE_MEDIA feature flag added
- [ ] PLAY_MEDIA feature flag added
- [ ] Browse UI appears in HA

---

### Task 5.7: User ID Management

Track user ID for API calls.

The browse API requires a user_id. Options:
1. Store admin user ID during config flow
2. Get first user from session
3. Add user selection to options flow

**Recommended:** Store user_id in coordinator from first session.

**Acceptance Criteria:**
- [ ] User ID available for browse calls
- [ ] Works with multi-user setups

---

## Integration Tests

### Task 5.8: Full Browse Integration Test

Test complete browse flow:
1. Browse root → libraries
2. Browse movies library → movies
3. Browse TV library → series
4. Browse series → seasons
5. Browse season → episodes
6. Play movie
7. Play episode

**Test Cases:**
- [ ] `test_browse_media_full_hierarchy`
- [ ] `test_play_from_browse`

---

## Acceptance Criteria Summary

### Required for Phase 5 Complete

- [ ] API methods for library browsing
- [ ] `async_browse_media` implementation
- [ ] Hierarchical navigation (library → content → sub-content)
- [ ] `async_play_media` implementation
- [ ] Content ID encoding/decoding
- [ ] BROWSE_MEDIA feature flag
- [ ] Thumbnail URLs for browse items
- [ ] All tests passing
- [ ] 100% code coverage maintained
- [ ] No mypy errors
- [ ] No ruff errors

### Definition of Done

1. Media browser shows Emby libraries
2. Can navigate through all content types
3. Can play content from browse UI
4. Thumbnails display for items
5. Works with multiple Emby users

---

## Content Type Mapping

| Emby Type | MediaClass | can_play | can_expand |
|-----------|------------|----------|------------|
| CollectionFolder | DIRECTORY | False | True |
| Movie | MOVIE | True | False |
| Series | TV_SHOW | False | True |
| Season | SEASON | False | True |
| Episode | EPISODE | True | False |
| MusicArtist | ARTIST | False | True |
| MusicAlbum | ALBUM | False | True |
| Audio | TRACK | True | False |
| Playlist | PLAYLIST | False | True |
| TvChannel | CHANNEL | True | False |

---

## Notes

- Emby item IDs are stable and can be used directly
- Libraries may have mixed content types
- Some items may not have thumbnails
- Pagination may be needed for large libraries
- Consider caching library structure for performance
