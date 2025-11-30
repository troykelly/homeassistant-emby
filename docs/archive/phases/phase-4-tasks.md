# Phase 4: Media Images & Artwork

## Overview

This phase implements the `media_image_url` property for the `EmbyMediaPlayer` entity, enabling artwork display in the Home Assistant UI. This includes:

- Image URL generation with proper authentication
- Support for multiple image types (Primary, Backdrop, Thumb, Logo)
- Image tag caching to prevent unnecessary refreshes
- Fallback hierarchy (item -> parent -> series)

## Dependencies

- Phase 3 complete (media player entity with playback control)
- Emby API endpoints for images documented

## Emby Image API

### Image URL Pattern

```
GET /Items/{itemId}/Images/{imageType}
```

### Image Types

| Type | Description | Usage |
|------|-------------|-------|
| Primary | Main poster/cover art | Movies, Albums, Series |
| Backdrop | Background image | Movies, Episodes |
| Thumb | Thumbnail | Episodes, Chapters |
| Logo | Transparent logo | Series, Movies |
| Banner | Wide banner image | Series |
| Art | Clearart/fanart | Series, Movies |

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `maxWidth` | int | Maximum width in pixels |
| `maxHeight` | int | Maximum height in pixels |
| `quality` | int | JPEG quality (0-100) |
| `tag` | string | Image tag for cache busting |

### Image Tags

Emby provides image tags (hashes) that change when images are updated. Include these in URLs to:
1. Enable browser caching
2. Bust cache when images change

Example response containing tags:
```json
{
  "Id": "item123",
  "Name": "Movie Title",
  "ImageTags": {
    "Primary": "abc123def456",
    "Backdrop": "789xyz"
  },
  "BackdropImageTags": ["tag1", "tag2"],
  "ParentBackdropImageTags": ["parenttag1"]
}
```

---

## Tasks

### Task 4.1: Image URL Generation in API Client

Add a method to `EmbyClient` for generating authenticated image URLs.

#### 4.1.1 Add `get_image_url` method to EmbyClient

**File:** `custom_components/embymedia/api.py`

**Signature:**
```python
def get_image_url(
    self,
    item_id: str,
    image_type: str = "Primary",
    max_width: int | None = None,
    max_height: int | None = None,
    tag: str | None = None,
) -> str:
    """Generate URL for item image.

    Args:
        item_id: The item ID.
        image_type: Image type (Primary, Backdrop, Thumb, etc.).
        max_width: Optional maximum width.
        max_height: Optional maximum height.
        tag: Optional image tag for cache busting.

    Returns:
        Full URL to the image.
    """
```

**Acceptance Criteria:**
- [x] Returns URL with base_url + endpoint
- [x] Includes api_key query parameter for authentication
- [x] Includes optional maxWidth, maxHeight parameters
- [x] Includes tag parameter when provided
- [x] URL-encodes all parameters correctly

**Test Cases:**
- [x] `test_get_image_url_basic` - Basic URL generation
- [x] `test_get_image_url_with_dimensions` - URL with maxWidth/maxHeight
- [x] `test_get_image_url_with_tag` - URL with cache tag
- [x] `test_get_image_url_with_all_params` - URL with all parameters

---

### Task 4.2: Add Image Data to EmbyMediaItem Model

Ensure the `EmbyMediaItem` model has all necessary image-related data.

#### 4.2.1 Verify image_tags in EmbyMediaItem

**File:** `custom_components/embymedia/models.py`

The `EmbyMediaItem` already has `image_tags: tuple[tuple[str, str], ...]` which stores (tag_type, tag_value) pairs.

**Additional fields needed:**
- `series_id: str | None` - For episode artwork fallback to series
- `season_id: str | None` - For episode artwork fallback to season
- `album_id: str | None` - For audio artwork fallback to album
- `parent_backdrop_image_tags: tuple[str, ...] | None` - Backdrop tags from parent

**Acceptance Criteria:**
- [x] `series_id` field added
- [x] `season_id` field added
- [x] `album_id` field added
- [x] `parent_backdrop_image_tags` field added
- [x] `parse_media_item` updated to extract these fields

**Test Cases:**
- [x] `test_parse_media_item_with_series_id` - Parses SeriesId
- [x] `test_parse_media_item_with_album_id` - Parses AlbumId
- [x] `test_parse_media_item_with_parent_backdrop_tags` - Parses ParentBackdropImageTags

---

### Task 4.3: Implement `media_image_url` Property

Add the `media_image_url` property to `EmbyMediaPlayer`.

#### 4.3.1 Basic media_image_url implementation

**File:** `custom_components/embymedia/media_player.py`

**Logic:**
1. If no session or no now_playing, return None
2. Get Primary image tag from now_playing.image_tags
3. Generate URL using coordinator.client.get_image_url()
4. Return URL

**Acceptance Criteria:**
- [x] Returns None when no session
- [x] Returns None when not playing
- [x] Returns URL with Primary image when available
- [x] Includes image tag for cache busting

**Test Cases:**
- [x] `test_media_image_url_when_playing` - Returns valid URL
- [x] `test_media_image_url_when_not_playing` - Returns None
- [x] `test_media_image_url_when_no_session` - Returns None
- [x] `test_media_image_url_includes_tag` - URL contains image tag

---

### Task 4.4: Image Fallback Hierarchy

Implement fallback logic for images when primary image is not available.

#### 4.4.1 Fallback for Episodes

For episodes without artwork, fall back to:
1. Episode Primary image
2. Season Primary image (using season_id)
3. Series Primary image (using series_id)

#### 4.4.2 Fallback for Audio

For audio without artwork, fall back to:
1. Track Primary image
2. Album Primary image (using album_id)

**Acceptance Criteria:**
- [x] Episode falls back to series when no episode image
- [x] Audio falls back to album when no track image
- [x] Returns None only when all fallbacks exhausted

**Test Cases:**
- [x] `test_media_image_url_episode_fallback_to_series`
- [x] `test_media_image_url_audio_fallback_to_album`
- [x] `test_media_image_url_no_fallback_available`

---

### Task 4.5: Update TypedDict for NowPlayingItem

Ensure the TypedDict includes all image-related fields.

**File:** `custom_components/embymedia/const.py`

**Fields to verify/add:**
- `SeriesId: NotRequired[str]`
- `SeasonId: NotRequired[str]`
- `AlbumId: NotRequired[str]`
- `PrimaryImageTag: NotRequired[str]`
- `ParentBackdropImageTags: NotRequired[list[str]]`

**Acceptance Criteria:**
- [x] All image-related fields present in TypedDict
- [x] No mypy errors

---

### Task 4.6: Integration Tests

#### 4.6.1 End-to-end image URL test

Test that the complete flow works:
1. Session with now_playing item
2. Item has image tags
3. media_image_url returns valid URL
4. URL contains all expected parameters

**Test Cases:**
- [x] `test_media_image_url_full_integration`

---

## Optional: Image Proxy

> Note: This is optional for Phase 4. Can be deferred to Phase 9.

### Task 4.7: Image Proxy Implementation (Optional)

Create an image proxy to handle authenticated image requests through Home Assistant.

**Files:**
- `custom_components/embymedia/image.py` - Image proxy view

This would allow:
- Proxy images through HA for clients that can't use API key
- Cache images locally
- Add cache headers

**Deferred:** This adds complexity and may not be necessary for basic functionality.

---

## Acceptance Criteria Summary

### Required for Phase 4 Complete

- [x] `get_image_url` method in EmbyClient
- [x] `media_image_url` property in EmbyMediaPlayer
- [x] Image tags used for cache busting
- [x] Fallback hierarchy for episodes/audio
- [x] All tests passing
- [x] 100% code coverage maintained
- [x] No mypy errors
- [x] No ruff errors

### Definition of Done

1. Media artwork displays in Home Assistant UI when playing media
2. Artwork updates when media changes
3. No unnecessary image refreshes (tag-based caching)
4. Graceful fallback when item has no artwork

---

## API Examples

### Movie with Primary Image

```python
# Item has Primary image tag
image_tags = (("Primary", "abc123"),)
url = client.get_image_url(
    item_id="movie123",
    image_type="Primary",
    tag="abc123",
    max_width=300,
)
# Result: http://emby:8096/Items/movie123/Images/Primary?api_key=xxx&tag=abc123&maxWidth=300
```

### Episode Fallback to Series

```python
# Episode has no Primary tag, fall back to series
item = EmbyMediaItem(
    item_id="episode456",
    series_id="series789",
    image_tags=(),  # No episode image
)
# Use series_id for image:
url = client.get_image_url(item_id="series789", image_type="Primary")
```

---

## Notes

- Emby images are served without authentication in some configurations, but we always include the API key for compatibility
- The `tag` parameter is important for cache busting - always include it when available
- Default image dimensions should balance quality with load time (300-500px width is typical for media cards)
