# Phase 17: Playlist Management

## Overview

This phase implements full playlist lifecycle management including creation, modification, and deletion of playlists from Home Assistant. Users will be able to create new playlists, add/remove items from existing playlists, and view playlist statistics through sensors.

The implementation follows the established patterns from Phase 8 (Library Management Services) and Phase 12 (Sensor Platform), providing services for playlist operations and sensors for monitoring.

## Implementation Status: NOT STARTED

---

## Background Research

### Emby Playlist API

Emby provides comprehensive REST endpoints for playlist management:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `POST /Playlists` | POST | Create new playlist |
| `POST /Playlists/{Id}/Items` | POST | Add items to playlist |
| `DELETE /Playlists/{Id}/Items` | DELETE | Remove items from playlist |
| `GET /Users/{userId}/Items?IncludeItemTypes=Playlist` | GET | Get user's playlists |
| `GET /Playlists/{Id}/Items` | GET | Get playlist items (already implemented) |

### Key Concepts

1. **Playlist Types**: Playlists can contain either Audio or Video items, not mixed
2. **Item Addition**: Items are added by ID, can add multiple items in one request
3. **Item Removal**: Items are removed using `PlaylistItemId` (not the media item ID)
4. **User Context**: Playlists are user-specific and require user_id for operations

### Emby API Quirks

- **PlaylistItemId vs ItemId**: When removing items from a playlist, you must use the `PlaylistItemId` returned when getting playlist items, NOT the original media item ID
- **Playlist Type**: The `MediaType` field in the create request determines if it's an Audio or Video playlist
- **Item IDs Format**: Multiple items can be added using comma-separated IDs in the query string

---

## Task Breakdown

### Task 17.1: TypedDicts for Playlist API

**Files:** `custom_components/embymedia/const.py`

Add TypedDicts for playlist API requests and responses.

#### 17.1.1 EmbyPlaylistCreateRequest TypedDict

```python
class EmbyPlaylistCreateRequest(TypedDict, total=False):
    """Request body for creating a playlist.

    POST /Playlists
    """
    Name: str  # Required
    MediaType: str  # "Audio" or "Video" - Required
    Ids: str  # Comma-separated item IDs to add initially (optional)
    UserId: str  # User ID (optional, uses API key user if not specified)
```

#### 17.1.2 EmbyPlaylistCreateResponse TypedDict

```python
class EmbyPlaylistCreateResponse(TypedDict):
    """Response from playlist creation.

    Returns the newly created playlist ID.
    """
    Id: str
```

#### 17.1.3 EmbyPlaylistItem TypedDict

```python
class EmbyPlaylistItem(TypedDict):
    """Playlist item with PlaylistItemId.

    Extends EmbyBrowseItem with the PlaylistItemId needed for removal.
    """
    Id: str  # Media item ID
    PlaylistItemId: str  # Unique ID for this item in the playlist
    Name: str
    Type: str
    ImageTags: NotRequired[dict[str, str]]
    # ... other EmbyBrowseItem fields
```

**Acceptance Criteria:**
- [ ] TypedDicts added to `const.py`
- [ ] All fields properly typed with `NotRequired` where appropriate
- [ ] Docstrings explain the purpose and API endpoint
- [ ] mypy strict compliance

**Tests:**
- [ ] Type annotation validation passes mypy

---

### Task 17.2: Playlist API Methods

**Files:** `custom_components/embymedia/api.py`

Add methods to the `EmbyClient` class for playlist operations.

#### 17.2.1 async_create_playlist() Method

```python
async def async_create_playlist(
    self,
    name: str,
    media_type: str,
    user_id: str,
    item_ids: list[str] | None = None,
) -> str:
    """Create a new playlist.

    Args:
        name: Playlist name.
        media_type: "Audio" or "Video".
        user_id: User ID who owns the playlist.
        item_ids: Optional list of item IDs to add initially.

    Returns:
        The newly created playlist ID.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
        ValueError: Invalid media_type.

    Example:
        >>> playlist_id = await client.async_create_playlist(
        ...     name="My Favorites",
        ...     media_type="Audio",
        ...     user_id="user123",
        ...     item_ids=["item1", "item2"]
        ... )
    """
    if media_type not in ("Audio", "Video"):
        raise ValueError(f"Invalid media_type: {media_type}. Must be 'Audio' or 'Video'")

    # Build query parameters
    params: list[str] = [
        f"Name={quote(name)}",
        f"MediaType={media_type}",
        f"UserId={user_id}",
    ]
    if item_ids:
        params.append(f"Ids={','.join(item_ids)}")

    query_string = "&".join(params)
    endpoint = f"/Playlists?{query_string}"

    response = await self._request_post_json(endpoint)
    playlist_id: str = response["Id"]
    return playlist_id
```

**Pattern Reference:** Similar to `async_mark_played()` in `api.py` (lines 753-769)

#### 17.2.2 async_add_to_playlist() Method

```python
async def async_add_to_playlist(
    self,
    playlist_id: str,
    item_ids: list[str],
    user_id: str,
) -> None:
    """Add items to a playlist.

    Args:
        playlist_id: The playlist ID.
        item_ids: List of item IDs to add.
        user_id: User ID (required for permissions).

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
        EmbyNotFoundError: Playlist not found.

    Example:
        >>> await client.async_add_to_playlist(
        ...     playlist_id="playlist123",
        ...     item_ids=["item1", "item2"],
        ...     user_id="user123"
        ... )
    """
    # Items are added via query string parameters
    params: list[str] = [
        f"Ids={','.join(item_ids)}",
        f"UserId={user_id}",
    ]
    query_string = "&".join(params)
    endpoint = f"/Playlists/{playlist_id}/Items?{query_string}"
    await self._request_post(endpoint)
```

**Pattern Reference:** Similar to `async_add_favorite()` in `api.py` (lines 789-806)

#### 17.2.3 async_remove_from_playlist() Method

```python
async def async_remove_from_playlist(
    self,
    playlist_id: str,
    playlist_item_ids: list[str],
) -> None:
    """Remove items from a playlist.

    IMPORTANT: Use PlaylistItemId from playlist items, NOT the media item ID.

    Args:
        playlist_id: The playlist ID.
        playlist_item_ids: List of PlaylistItemId values (from GET /Playlists/{Id}/Items).

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
        EmbyNotFoundError: Playlist not found.

    Example:
        >>> # First get playlist items to obtain PlaylistItemIds
        >>> items = await client.async_get_playlist_items("user123", "playlist123")
        >>> playlist_item_ids = [item["PlaylistItemId"] for item in items]
        >>>
        >>> # Then remove by PlaylistItemId
        >>> await client.async_remove_from_playlist(
        ...     playlist_id="playlist123",
        ...     playlist_item_ids=playlist_item_ids[:2]  # Remove first 2 items
        ... )
    """
    # Items are removed via query string with PlaylistItemIds
    entry_ids = ",".join(playlist_item_ids)
    endpoint = f"/Playlists/{playlist_id}/Items?EntryIds={entry_ids}"
    await self._request_delete(endpoint)
```

**Pattern Reference:** Similar to `async_remove_favorite()` in `api.py` (lines 807-823), but uses DELETE with query params

#### 17.2.4 async_get_playlists() Method

```python
async def async_get_playlists(
    self,
    user_id: str,
) -> list[EmbyBrowseItem]:
    """Get user's playlists.

    Args:
        user_id: The user ID.

    Returns:
        List of playlist items.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.

    Example:
        >>> playlists = await client.async_get_playlists("user123")
        >>> for playlist in playlists:
        ...     print(f"{playlist['Name']}: {playlist['Id']}")
    """
    endpoint = (
        f"/Users/{user_id}/Items?"
        f"IncludeItemTypes=Playlist&"
        f"SortBy=SortName&SortOrder=Ascending&"
        f"Recursive=true"
    )
    response = await self._request(HTTP_GET, endpoint)
    items: list[EmbyBrowseItem] = response.get("Items", [])  # type: ignore[assignment]
    return items
```

**Pattern Reference:** Similar to `async_get_artist_albums()` in `api.py` (lines 1002-1028)

**Acceptance Criteria:**
- [ ] All four methods added to `EmbyClient` class in `api.py`
- [ ] Methods use existing `_request_post`, `_request_post_json`, `_request_delete` helpers
- [ ] Proper error handling with custom exceptions
- [ ] URL encoding for playlist names using `urllib.parse.quote`
- [ ] Return types properly annotated
- [ ] Docstrings with Args, Returns, Raises, and Example sections

**Tests:**
- [ ] `test_async_create_playlist()` - successful creation
- [ ] `test_async_create_playlist_with_items()` - creation with initial items
- [ ] `test_async_create_playlist_invalid_type()` - ValueError for invalid media_type
- [ ] `test_async_add_to_playlist()` - successful addition
- [ ] `test_async_add_to_playlist_not_found()` - EmbyNotFoundError
- [ ] `test_async_remove_from_playlist()` - successful removal
- [ ] `test_async_remove_from_playlist_not_found()` - EmbyNotFoundError
- [ ] `test_async_get_playlists()` - returns playlist list
- [ ] All tests in `tests/test_api.py`

---

### Task 17.3: Playlist Services

**Files:** `custom_components/embymedia/services.py`, `custom_components/embymedia/services.yaml`

Add three new services for playlist management.

#### 17.3.1 Service Constants and Schemas

Add to `services.py`:

```python
# Service names (add after existing SERVICE_* constants around line 31)
SERVICE_CREATE_PLAYLIST = "create_playlist"
SERVICE_ADD_TO_PLAYLIST = "add_to_playlist"
SERVICE_REMOVE_FROM_PLAYLIST = "remove_from_playlist"

# Service attributes (add after existing ATTR_* constants around line 40)
ATTR_PLAYLIST_NAME = "playlist_name"
ATTR_PLAYLIST_ID = "playlist_id"
ATTR_MEDIA_TYPE = "media_type"
ATTR_ITEM_IDS = "item_ids"
ATTR_PLAYLIST_ITEM_IDS = "playlist_item_ids"

# Service schemas
CREATE_PLAYLIST_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(ATTR_PLAYLIST_NAME): cv.string,
        vol.Required(ATTR_MEDIA_TYPE): vol.In(["Audio", "Video"]),
        vol.Optional(ATTR_ITEM_IDS): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(ATTR_USER_ID): cv.string,
    }
)

ADD_TO_PLAYLIST_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(ATTR_PLAYLIST_ID): cv.string,
        vol.Required(ATTR_ITEM_IDS): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(ATTR_USER_ID): cv.string,
    }
)

REMOVE_FROM_PLAYLIST_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(ATTR_PLAYLIST_ID): cv.string,
        vol.Required(ATTR_PLAYLIST_ITEM_IDS): vol.All(cv.ensure_list, [cv.string]),
    }
)
```

**Pattern Reference:** See existing schemas in `services.py` (lines 43-78)

#### 17.3.2 Service Handlers

Add to `async_setup_services()` in `services.py`:

```python
async def async_create_playlist(call: ServiceCall) -> None:
    """Create a new playlist."""
    entity_ids = _get_entity_ids_from_call(hass, call)
    playlist_name: str = call.data[ATTR_PLAYLIST_NAME]
    media_type: str = call.data[ATTR_MEDIA_TYPE]
    item_ids: list[str] | None = call.data.get(ATTR_ITEM_IDS)
    user_id: str | None = call.data.get(ATTR_USER_ID)

    # Validate playlist name
    if not playlist_name.strip():
        raise ServiceValidationError("Playlist name cannot be empty")

    # Validate item IDs if provided
    if item_ids:
        for item_id in item_ids:
            _validate_emby_id(item_id, "item_id")

    for entity_id in entity_ids:
        coordinator = _get_coordinator_for_entity(hass, entity_id)
        effective_user_id = user_id or _get_user_id_for_entity(hass, entity_id, coordinator)

        if not effective_user_id:
            raise ServiceValidationError(
                f"No user_id available for {entity_id}. Please provide user_id parameter."
            )

        try:
            playlist_id = await coordinator.client.async_create_playlist(
                name=playlist_name,
                media_type=media_type,
                user_id=effective_user_id,
                item_ids=item_ids,
            )
            _LOGGER.info(
                "Created %s playlist '%s' (ID: %s) for user %s",
                media_type,
                playlist_name,
                playlist_id,
                effective_user_id,
            )
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        except EmbyConnectionError as err:
            raise HomeAssistantError(
                f"Failed to create playlist for {entity_id}: Connection error"
            ) from err
        except EmbyError as err:
            raise HomeAssistantError(
                f"Failed to create playlist for {entity_id}: {err}"
            ) from err


async def async_add_to_playlist(call: ServiceCall) -> None:
    """Add items to a playlist."""
    entity_ids = _get_entity_ids_from_call(hass, call)
    playlist_id: str = call.data[ATTR_PLAYLIST_ID]
    item_ids: list[str] = call.data[ATTR_ITEM_IDS]
    user_id: str | None = call.data.get(ATTR_USER_ID)

    # Validate IDs
    _validate_emby_id(playlist_id, "playlist_id")
    for item_id in item_ids:
        _validate_emby_id(item_id, "item_id")

    if not item_ids:
        raise ServiceValidationError("item_ids cannot be empty")

    for entity_id in entity_ids:
        coordinator = _get_coordinator_for_entity(hass, entity_id)
        effective_user_id = user_id or _get_user_id_for_entity(hass, entity_id, coordinator)

        if not effective_user_id:
            raise ServiceValidationError(
                f"No user_id available for {entity_id}. Please provide user_id parameter."
            )

        try:
            await coordinator.client.async_add_to_playlist(
                playlist_id=playlist_id,
                item_ids=item_ids,
                user_id=effective_user_id,
            )
            _LOGGER.info(
                "Added %d items to playlist %s for user %s",
                len(item_ids),
                playlist_id,
                effective_user_id,
            )
        except EmbyConnectionError as err:
            raise HomeAssistantError(
                f"Failed to add items to playlist for {entity_id}: Connection error"
            ) from err
        except EmbyError as err:
            raise HomeAssistantError(
                f"Failed to add items to playlist for {entity_id}: {err}"
            ) from err


async def async_remove_from_playlist(call: ServiceCall) -> None:
    """Remove items from a playlist."""
    entity_ids = _get_entity_ids_from_call(hass, call)
    playlist_id: str = call.data[ATTR_PLAYLIST_ID]
    playlist_item_ids: list[str] = call.data[ATTR_PLAYLIST_ITEM_IDS]

    # Validate IDs
    _validate_emby_id(playlist_id, "playlist_id")
    for playlist_item_id in playlist_item_ids:
        _validate_emby_id(playlist_item_id, "playlist_item_id")

    if not playlist_item_ids:
        raise ServiceValidationError("playlist_item_ids cannot be empty")

    for entity_id in entity_ids:
        coordinator = _get_coordinator_for_entity(hass, entity_id)

        try:
            await coordinator.client.async_remove_from_playlist(
                playlist_id=playlist_id,
                playlist_item_ids=playlist_item_ids,
            )
            _LOGGER.info(
                "Removed %d items from playlist %s",
                len(playlist_item_ids),
                playlist_id,
            )
        except EmbyConnectionError as err:
            raise HomeAssistantError(
                f"Failed to remove items from playlist for {entity_id}: Connection error"
            ) from err
        except EmbyError as err:
            raise HomeAssistantError(
                f"Failed to remove items from playlist for {entity_id}: {err}"
            ) from err
```

**Pattern Reference:** See existing handlers in `services.py` (lines 225-379)

#### 17.3.3 Service Registration

Add to the end of `async_setup_services()`:

```python
# Register services (add after existing service registrations around line 418)
hass.services.async_register(
    DOMAIN,
    SERVICE_CREATE_PLAYLIST,
    async_create_playlist,
    schema=CREATE_PLAYLIST_SCHEMA,
)
hass.services.async_register(
    DOMAIN,
    SERVICE_ADD_TO_PLAYLIST,
    async_add_to_playlist,
    schema=ADD_TO_PLAYLIST_SCHEMA,
)
hass.services.async_register(
    DOMAIN,
    SERVICE_REMOVE_FROM_PLAYLIST,
    async_remove_from_playlist,
    schema=REMOVE_FROM_PLAYLIST_SCHEMA,
)
```

#### 17.3.4 Service Unload

Add to `async_unload_services()`:

```python
# Remove services (add after existing service removals around line 443)
hass.services.async_remove(DOMAIN, SERVICE_CREATE_PLAYLIST)
hass.services.async_remove(DOMAIN, SERVICE_ADD_TO_PLAYLIST)
hass.services.async_remove(DOMAIN, SERVICE_REMOVE_FROM_PLAYLIST)
```

**Pattern Reference:** See `async_unload_services()` in `services.py` (lines 428-445)

#### 17.3.5 Service YAML Definitions

Add to `services.yaml`:

```yaml
create_playlist:
  name: Create Playlist
  description: Create a new playlist on the Emby server.
  target:
    entity:
      integration: embymedia
      domain: media_player
  fields:
    playlist_name:
      name: Playlist Name
      description: Name for the new playlist.
      required: true
      example: "My Favorites"
      selector:
        text:
    media_type:
      name: Media Type
      description: Type of media the playlist will contain.
      required: true
      default: "Audio"
      selector:
        select:
          options:
            - "Audio"
            - "Video"
    item_ids:
      name: Initial Items
      description: Optional list of item IDs to add to the playlist.
      selector:
        object:
    user_id:
      name: User ID
      description: Optional user ID (uses session user if not specified).
      selector:
        text:

add_to_playlist:
  name: Add to Playlist
  description: Add items to an existing playlist.
  target:
    entity:
      integration: embymedia
      domain: media_player
  fields:
    playlist_id:
      name: Playlist ID
      description: The Emby playlist ID.
      required: true
      example: "abc123"
      selector:
        text:
    item_ids:
      name: Item IDs
      description: List of Emby item IDs to add to the playlist.
      required: true
      selector:
        object:
    user_id:
      name: User ID
      description: Optional user ID (uses session user if not specified).
      selector:
        text:

remove_from_playlist:
  name: Remove from Playlist
  description: Remove items from a playlist.
  target:
    entity:
      integration: embymedia
      domain: media_player
  fields:
    playlist_id:
      name: Playlist ID
      description: The Emby playlist ID.
      required: true
      example: "abc123"
      selector:
        text:
    playlist_item_ids:
      name: Playlist Item IDs
      description: List of PlaylistItemId values (NOT media item IDs). Get these from the playlist sensor's items attribute.
      required: true
      selector:
        object:
```

**Pattern Reference:** See existing service definitions in `services.yaml` (lines 1-146)

**Acceptance Criteria:**
- [ ] Three new service constants and schemas added
- [ ] Three service handlers implemented with proper error handling
- [ ] Services registered and unloaded correctly
- [ ] Service YAML definitions added with complete field descriptions
- [ ] Validation for all ID parameters using `_validate_emby_id()`
- [ ] Proper logging of service calls

**Tests:**
- [ ] `test_service_create_playlist()` - successful creation
- [ ] `test_service_create_playlist_empty_name()` - error on empty name
- [ ] `test_service_create_playlist_invalid_type()` - error on invalid media_type
- [ ] `test_service_create_playlist_no_user()` - error when user_id unavailable
- [ ] `test_service_add_to_playlist()` - successful addition
- [ ] `test_service_add_to_playlist_empty_ids()` - error on empty item_ids
- [ ] `test_service_remove_from_playlist()` - successful removal
- [ ] `test_service_remove_from_playlist_empty_ids()` - error on empty playlist_item_ids
- [ ] All tests in `tests/test_services.py`

---

### Task 17.4: Playlist Sensor

**Files:** `custom_components/embymedia/sensor.py`

Add a sensor to display playlist count and list.

#### 17.4.1 EmbyPlaylistSensor Class

Add to `sensor.py` after the user sensors (around line 400+):

```python
class EmbyPlaylistSensor(EmbyCoordinatorEntity, SensorEntity):
    """Sensor for Emby playlists.

    Shows the count of user's playlists with the full list in attributes.
    """

    _attr_icon = "mdi:playlist-music"
    _attr_native_unit_of_measurement = "playlists"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: EmbyLibraryCoordinator,
        config_entry_id: str,
        server_name: str,
        user_id: str,
    ) -> None:
        """Initialize the playlist sensor.

        Args:
            coordinator: The library coordinator.
            config_entry_id: Config entry ID.
            server_name: Server name for entity naming.
            user_id: User ID to fetch playlists for.
        """
        super().__init__(coordinator, config_entry_id)
        self._server_name = server_name
        self._user_id = user_id
        self._attr_unique_id = f"{config_entry_id}_playlists"
        self._attr_name = f"{server_name} Playlists"

    @property
    def native_value(self) -> int | None:
        """Return the playlist count."""
        if self.coordinator.data is None:
            return None

        playlists = self.coordinator.data.get("playlists", [])
        return len(playlists)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return playlist details as attributes."""
        if self.coordinator.data is None:
            return {}

        playlists = self.coordinator.data.get("playlists", [])

        # Build playlist list with useful info
        playlist_list: list[dict[str, str | int]] = []
        for playlist in playlists:
            playlist_list.append({
                "id": playlist.get("Id", ""),
                "name": playlist.get("Name", ""),
                "type": playlist.get("MediaType", "Unknown"),
                "item_count": playlist.get("ChildCount", 0),
            })

        return {
            "playlists": playlist_list,
            "user_id": self._user_id,
        }
```

**Pattern Reference:** Similar to user sensors in `sensor.py` (search for `EmbyFavoritesSensor` pattern)

#### 17.4.2 Update EmbyLibraryCoordinator

Modify `EmbyLibraryCoordinator._async_update_data()` in `coordinator_sensors.py` to fetch playlists:

```python
async def _async_update_data(self) -> dict[str, object]:
    """Fetch library data from Emby.

    Returns:
        Dictionary with library counts and user data.
    """
    try:
        # Existing code for item_counts, scheduled_tasks, virtual_folders...

        # Add playlist fetching (after user sensors data around line 180+)
        playlists: list[EmbyBrowseItem] = []
        if self._user_id:
            try:
                playlists = await self.client.async_get_playlists(self._user_id)
            except EmbyError as err:
                _LOGGER.debug("Failed to fetch playlists: %s", err)

        return {
            "item_counts": item_counts,
            "scheduled_tasks": scheduled_tasks,
            "virtual_folders": virtual_folders,
            "favorites_count": favorites_count,
            "continue_watching_count": continue_watching_count,
            "playlists": playlists,  # Add this
        }
    except EmbyError as err:
        # Existing error handling...
```

**Pattern Reference:** See existing coordinator data fetching in `coordinator_sensors.py`

#### 17.4.3 Register Sensor

Add to `async_setup_entry()` in `sensor.py`:

```python
async def async_setup_entry(
    hass: HomeAssistant,
    entry: EmbyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Emby sensor platform."""
    # ... existing code ...

    # Add after user sensors (around line 100+)
    if enable_user_sensors and user_id:
        # ... existing user sensors ...

        # Add playlist sensor
        entities.append(
            EmbyPlaylistSensor(
                coordinator=library_coordinator,
                config_entry_id=entry.entry_id,
                server_name=server_name,
                user_id=user_id,
            )
        )
```

**Pattern Reference:** See existing sensor setup in `sensor.py` around line 50-100

**Acceptance Criteria:**
- [ ] `EmbyPlaylistSensor` class added to `sensor.py`
- [ ] Sensor shows count as state
- [ ] Sensor attributes include full playlist list with id, name, type, item_count
- [ ] `EmbyLibraryCoordinator` fetches playlists
- [ ] Sensor registered in platform setup
- [ ] Sensor only created when user sensors are enabled
- [ ] Icon is `mdi:playlist-music`

**Tests:**
- [ ] `test_playlist_sensor_state()` - state shows count
- [ ] `test_playlist_sensor_attributes()` - attributes contain playlist list
- [ ] `test_playlist_sensor_no_data()` - None when coordinator has no data
- [ ] `test_playlist_sensor_empty_list()` - 0 when no playlists
- [ ] `test_coordinator_fetch_playlists()` - coordinator fetches playlists
- [ ] All tests in `tests/test_sensor.py`

---

### Task 17.5: Playlist Browsing Enhancement

**Files:** `custom_components/embymedia/browse.py`, `custom_components/embymedia/media_player.py`

Enhance media browser to show playlists are playable and expandable.

#### 17.5.1 Update Browse Helper

The browse helpers already support playlists. Verify in `browse.py`:

```python
# In _EMBY_TYPE_TO_MEDIA_CLASS (line 8)
"Playlist": MediaClass.PLAYLIST,  # Already present

# In _PLAYABLE_TYPES (line 24)
"Playlist",  # Already present

# In _EXPANDABLE_TYPES (line 37)
"Playlist",  # Already present
```

**Action:** Verify these entries exist, no code changes needed.

#### 17.5.2 Verify Playlist Support

Check that `async_browse_media()` in `media_player.py` already handles playlists correctly:

- Browse into playlists to see items (uses `async_get_playlist_items()`)
- Play entire playlist
- Playlists appear in music library categories

**Action:** Manual testing to verify existing implementation works with new API methods.

**Acceptance Criteria:**
- [ ] Playlists marked as both playable and expandable
- [ ] Clicking playlist in media browser shows its items
- [ ] Playing playlist queues all items

**Tests:**
- [ ] `test_browse_playlist()` - can browse into playlist
- [ ] `test_playlist_playable()` - playlist marked as can_play
- [ ] `test_playlist_expandable()` - playlist marked as can_expand
- [ ] Tests in `tests/test_media_player.py`

---

### Task 17.6: Documentation

**Files:** `README.md`, `CHANGELOG.md`

#### 17.6.1 Update README

Add new section after "Library Management Services":

```markdown
### Playlist Management

Create and manage playlists directly from Home Assistant.

**Create a Playlist:**
```yaml
service: embymedia.create_playlist
target:
  entity_id: media_player.living_room_tv
data:
  playlist_name: "Road Trip Mix"
  media_type: "Audio"
  item_ids:
    - "abc123"
    - "def456"
```

**Add Items to Playlist:**
```yaml
service: embymedia.add_to_playlist
target:
  entity_id: media_player.living_room_tv
data:
  playlist_id: "playlist123"
  item_ids:
    - "ghi789"
    - "jkl012"
```

**Remove Items from Playlist:**
```yaml
# First, get PlaylistItemIds from the sensor
# sensor.emby_server_playlists -> attributes -> playlists

service: embymedia.remove_from_playlist
target:
  entity_id: media_player.living_room_tv
data:
  playlist_id: "playlist123"
  playlist_item_ids:
    - "playlistitem_001"
    - "playlistitem_002"
```

**Playlist Sensor:**

The `sensor.{server}_playlists` entity shows your playlist count with details in attributes:

```yaml
state: 5
attributes:
  playlists:
    - id: "playlist1"
      name: "Workout Mix"
      type: "Audio"
      item_count: 25
    - id: "playlist2"
      name: "Movie Night"
      type: "Video"
      item_count: 12
```

**Important Notes:**
- Playlists can contain either Audio OR Video items, not mixed
- When removing items, use `PlaylistItemId` from the sensor attributes, NOT the media item ID
- Playlists are user-specific - each user has their own playlists
```

#### 17.6.2 Update CHANGELOG

Add to the "Unreleased" section:

```markdown
## [Unreleased]

### Added
- **Playlist Management** (Phase 17)
  - New service: `embymedia.create_playlist` - Create new playlists
  - New service: `embymedia.add_to_playlist` - Add items to playlists
  - New service: `embymedia.remove_from_playlist` - Remove items from playlists
  - New sensor: `sensor.{server}_playlists` - Shows playlist count and list
  - Support for both Audio and Video playlists
```

**Acceptance Criteria:**
- [ ] README section added with clear examples
- [ ] CHANGELOG entry added
- [ ] Important notes about PlaylistItemId vs ItemId included
- [ ] Examples show proper service call syntax

---

### Task 17.7: Testing & Quality Assurance

**Files:** `tests/test_api.py`, `tests/test_services.py`, `tests/test_sensor.py`

#### 17.7.1 API Method Tests

All API method tests in `tests/test_api.py`:

```python
async def test_async_create_playlist(mock_emby_client: EmbyClient) -> None:
    """Test creating a playlist."""
    # Test successful creation
    # Test with initial items
    # Test error handling

async def test_async_create_playlist_invalid_type(mock_emby_client: EmbyClient) -> None:
    """Test creating playlist with invalid media type."""
    # Should raise ValueError

async def test_async_add_to_playlist(mock_emby_client: EmbyClient) -> None:
    """Test adding items to playlist."""
    # Test successful addition
    # Test error handling

async def test_async_remove_from_playlist(mock_emby_client: EmbyClient) -> None:
    """Test removing items from playlist."""
    # Test successful removal
    # Test error handling

async def test_async_get_playlists(mock_emby_client: EmbyClient) -> None:
    """Test getting user playlists."""
    # Test successful fetch
    # Test empty list
```

#### 17.7.2 Service Tests

All service tests in `tests/test_services.py`:

```python
async def test_service_create_playlist(hass: HomeAssistant, ...) -> None:
    """Test create_playlist service."""
    # Test successful creation
    # Test validation errors

async def test_service_add_to_playlist(hass: HomeAssistant, ...) -> None:
    """Test add_to_playlist service."""
    # Test successful addition
    # Test validation errors

async def test_service_remove_from_playlist(hass: HomeAssistant, ...) -> None:
    """Test remove_from_playlist service."""
    # Test successful removal
    # Test validation errors
```

#### 17.7.3 Sensor Tests

All sensor tests in `tests/test_sensor.py`:

```python
async def test_playlist_sensor(hass: HomeAssistant, ...) -> None:
    """Test playlist sensor state and attributes."""
    # Test count
    # Test attributes
    # Test empty list
```

#### 17.7.4 Coverage Requirements

- [ ] 100% code coverage for all new code
- [ ] All edge cases tested
- [ ] All error paths tested
- [ ] Type checking passes (mypy strict)
- [ ] Linting passes (ruff)

**Acceptance Criteria:**
- [ ] Minimum 40 new tests added
- [ ] All tests pass
- [ ] 100% code coverage maintained
- [ ] No type errors
- [ ] No linting errors

---

## Dependencies

### Required Before This Phase
- ✅ Phase 8 (Library Management Services) - Service patterns
- ✅ Phase 12 (Sensor Platform) - Coordinator and sensor patterns

### Blocks Future Phases
- None (standalone feature)

---

## Testing Strategy

### Unit Tests
1. **API Layer** - Mock HTTP responses for all endpoints
2. **Service Layer** - Mock coordinator calls, test validation
3. **Sensor Layer** - Mock coordinator data, test state/attributes

### Integration Tests
1. Create playlist → verify it appears in sensor
2. Add items → verify item count increases
3. Remove items → verify item count decreases
4. Full workflow test

### Manual Testing Checklist
- [ ] Create Audio playlist through service
- [ ] Create Video playlist through service
- [ ] Add items to playlist
- [ ] Remove items using PlaylistItemId
- [ ] Verify sensor updates after operations
- [ ] Browse playlist in media browser
- [ ] Play entire playlist
- [ ] Verify error messages are user-friendly

---

## API Reference

### Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `POST /Playlists` | POST | Create playlist |
| `POST /Playlists/{Id}/Items` | POST | Add items |
| `DELETE /Playlists/{Id}/Items` | DELETE | Remove items |
| `GET /Users/{userId}/Items?IncludeItemTypes=Playlist` | GET | List playlists |
| `GET /Playlists/{Id}/Items` | GET | Get playlist items (existing) |

### Request/Response Examples

**Create Playlist:**
```http
POST /Playlists?Name=My%20Mix&MediaType=Audio&UserId=user123&Ids=item1,item2
Content-Type: application/json
X-Emby-Token: your-api-key

Response:
{
  "Id": "playlist123"
}
```

**Add to Playlist:**
```http
POST /Playlists/playlist123/Items?Ids=item3,item4&UserId=user123
X-Emby-Token: your-api-key
```

**Remove from Playlist:**
```http
DELETE /Playlists/playlist123/Items?EntryIds=playlistitem_001,playlistitem_002
X-Emby-Token: your-api-key
```

---

## Success Criteria

### Minimum Viable Implementation
- [ ] Can create playlists from HA
- [ ] Can add items to playlists
- [ ] Can remove items from playlists
- [ ] Sensor shows playlist count

### Full Feature Set
- [ ] All services working with proper validation
- [ ] Sensor shows detailed playlist list
- [ ] Error handling for all edge cases
- [ ] Documentation complete

### Production Ready
- [ ] 100% test coverage
- [ ] All integration tests passing
- [ ] Manual testing complete
- [ ] README and CHANGELOG updated

---

## Known Limitations

1. **PlaylistItemId Complexity**: Users must use PlaylistItemId (not ItemId) for removal. This is documented but may cause confusion.
2. **No Playlist Deletion**: This phase doesn't implement playlist deletion - that would require a separate service.
3. **No Reordering**: Playlist item reordering is not supported in this phase.
4. **Mixed Content**: Playlists cannot mix Audio and Video items - this is an Emby limitation.

---

## Future Enhancements

Potential additions for future phases:

1. **Playlist Deletion Service** - `embymedia.delete_playlist`
2. **Playlist Reordering** - `embymedia.reorder_playlist_items`
3. **Quick Actions** - "Add currently playing item to playlist"
4. **Smart Playlists** - Create playlists based on filters
5. **Playlist Sharing** - Share playlists between users
6. **Playlist Export** - Export playlist as M3U/PLS

---

## Estimated Effort

| Task | Estimated Time |
|------|----------------|
| 17.1 TypedDicts | 30 minutes |
| 17.2 API Methods | 2 hours |
| 17.3 Services | 2 hours |
| 17.4 Sensor | 1.5 hours |
| 17.5 Browse Enhancement | 30 minutes |
| 17.6 Documentation | 1 hour |
| 17.7 Testing | 3 hours |
| **Total** | **~10.5 hours** |

---

## References

- [Emby REST API Documentation](https://dev.emby.media/doc/restapi/index.html)
- Phase 8 Tasks (Library Management Services pattern)
- Phase 12 Tasks (Sensor platform pattern)
- `custom_components/embymedia/services.py` - Service implementation examples
- `custom_components/embymedia/sensor.py` - Sensor implementation examples
