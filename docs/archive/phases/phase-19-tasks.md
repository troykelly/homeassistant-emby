# Phase 19: Collection Management - Detailed Tasks

## Overview

Collection (BoxSet) lifecycle management and enhanced library browsing by person, tag, and other metadata.

This phase adds:
- Services to create and manage collections
- Collection count sensors with list attributes
- Person browsing in media browser (actors, directors, writers)
- Tag-based filtering and browsing
- Enhanced metadata navigation capabilities

---

## Task 19.1: Collection Creation API Methods

### Description

Add API methods for creating collections and managing their contents.

### Acceptance Criteria

- `async_create_collection()` creates a new BoxSet via `POST /Collections`
- `async_add_to_collection()` adds items to a collection
- `async_remove_from_collection()` removes items from a collection
- All methods follow existing API client patterns
- Proper error handling with integration exceptions
- Type-safe with no `Any` usage

### File References

- **Modify:** `/workspaces/homeassistant-emby/custom_components/embymedia/api.py`
- **Modify:** `/workspaces/homeassistant-emby/custom_components/embymedia/const.py`
- **Create tests:** `/workspaces/homeassistant-emby/tests/test_api_collections.py`

### TypedDicts Needed

Add to `const.py`:

```python
class EmbyCreateCollectionRequest(TypedDict):
    """Request body for creating a collection.

    POST /Collections?Name={name}&Ids={item_ids}
    """
    Name: str
    Ids: str  # Comma-separated item IDs


class EmbyCollectionResponse(TypedDict):
    """Response from collection creation.

    Returns the newly created collection item.
    """
    Id: str
    Name: str
    Type: str  # "BoxSet"
    ItemCount: NotRequired[int]
```

### Implementation Pattern

Follow the existing `async_mark_played()` pattern from `api.py` (lines 752-769):

```python
async def async_create_collection(
    self,
    name: str,
    item_ids: list[str] | None = None,
) -> EmbyCollectionResponse:
    """Create a new collection (BoxSet).

    Args:
        name: Collection name.
        item_ids: Optional list of item IDs to add initially.

    Returns:
        Collection response with new collection ID.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    params = [f"Name={quote(name)}"]
    if item_ids:
        params.append(f"Ids={','.join(item_ids)}")

    query_string = "&".join(params)
    endpoint = f"/Collections?{query_string}"
    response = await self._request_post_json(endpoint)
    return response  # type: ignore[return-value]


async def async_add_to_collection(
    self,
    collection_id: str,
    item_ids: list[str],
) -> None:
    """Add items to a collection.

    Args:
        collection_id: The collection ID.
        item_ids: List of item IDs to add.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    ids_param = ",".join(item_ids)
    endpoint = f"/Collections/{collection_id}/Items?Ids={ids_param}"
    await self._request_post(endpoint)


async def async_remove_from_collection(
    self,
    collection_id: str,
    item_ids: list[str],
) -> None:
    """Remove items from a collection.

    Args:
        collection_id: The collection ID.
        item_ids: List of item IDs to remove.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    ids_param = ",".join(item_ids)
    endpoint = f"/Collections/{collection_id}/Items?Ids={ids_param}"
    await self._request_delete(endpoint)
```

### Test Requirements

Create `tests/test_api_collections.py` following the pattern from `tests/test_api.py`:

```python
"""Tests for Emby API collection methods."""

import pytest
from custom_components.embymedia.api import EmbyClient
from custom_components.embymedia.exceptions import (
    EmbyAuthenticationError,
    EmbyConnectionError,
)


async def test_create_collection(
    emby_client: EmbyClient,
    aioclient_mock: Any,
) -> None:
    """Test creating a collection."""
    # RED: Write test that fails
    # GREEN: Implement method
    # REFACTOR: Clean up


async def test_add_to_collection(
    emby_client: EmbyClient,
    aioclient_mock: Any,
) -> None:
    """Test adding items to collection."""
    # Test with single item
    # Test with multiple items


async def test_remove_from_collection(
    emby_client: EmbyClient,
    aioclient_mock: Any,
) -> None:
    """Test removing items from collection."""
    # Test successful removal


async def test_create_collection_auth_error(
    emby_client: EmbyClient,
    aioclient_mock: Any,
) -> None:
    """Test collection creation with auth error."""
    # Verify EmbyAuthenticationError raised on 401
```

---

## Task 19.2: Collection Management Services

### Description

Create Home Assistant services for collection management.

### Acceptance Criteria

- `embymedia.create_collection` service creates a new collection
- `embymedia.add_to_collection` service adds items to existing collection
- Service schemas validate all inputs
- Services support both entity_id and device_id targeting
- Services follow existing service pattern from `services.py`

### File References

- **Modify:** `/workspaces/homeassistant-emby/custom_components/embymedia/services.py`
- **Modify:** `/workspaces/homeassistant-emby/custom_components/embymedia/strings.json`
- **Create:** `/workspaces/homeassistant-emby/custom_components/embymedia/services.yaml`
- **Create tests:** `/workspaces/homeassistant-emby/tests/test_services_collections.py`

### Service Constants

Add to the service attributes section in `services.py` (after line 40):

```python
# Collection service attributes
ATTR_COLLECTION_NAME = "collection_name"
ATTR_COLLECTION_ID = "collection_id"
ATTR_ITEM_IDS = "item_ids"

# Service names (add after line 31)
SERVICE_CREATE_COLLECTION = "create_collection"
SERVICE_ADD_TO_COLLECTION = "add_to_collection"
```

### Service Schemas

Add after existing schemas (after line 78):

```python
CREATE_COLLECTION_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(ATTR_COLLECTION_NAME): cv.string,
        vol.Optional(ATTR_ITEM_IDS): vol.All(cv.ensure_list, [cv.string]),
    }
)

ADD_TO_COLLECTION_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(ATTR_COLLECTION_ID): cv.string,
        vol.Required(ATTR_ITEM_IDS): vol.All(cv.ensure_list, [cv.string]),
    }
)
```

### Implementation Pattern

Follow the existing service pattern from `async_mark_played()` (lines 225-257):

```python
async def async_create_collection(call: ServiceCall) -> None:
    """Create a collection."""
    entity_ids = _get_entity_ids_from_call(hass, call)
    collection_name: str = call.data[ATTR_COLLECTION_NAME]
    item_ids: list[str] | None = call.data.get(ATTR_ITEM_IDS)

    # Validate collection name
    if not collection_name or not collection_name.strip():
        raise ServiceValidationError("Collection name cannot be empty")

    # Validate item IDs if provided
    if item_ids:
        for item_id in item_ids:
            _validate_emby_id(item_id, "item_id")

    for entity_id in entity_ids:
        coordinator = _get_coordinator_for_entity(hass, entity_id)

        try:
            await coordinator.client.async_create_collection(
                name=collection_name,
                item_ids=item_ids,
            )
        except EmbyConnectionError as err:
            raise HomeAssistantError(
                f"Failed to create collection for {entity_id}: Connection error"
            ) from err
        except EmbyError as err:
            raise HomeAssistantError(
                f"Failed to create collection for {entity_id}: {err}"
            ) from err


async def async_add_to_collection(call: ServiceCall) -> None:
    """Add items to a collection."""
    entity_ids = _get_entity_ids_from_call(hass, call)
    collection_id: str = call.data[ATTR_COLLECTION_ID]
    item_ids: list[str] = call.data[ATTR_ITEM_IDS]

    # Validate IDs
    _validate_emby_id(collection_id, "collection_id")
    for item_id in item_ids:
        _validate_emby_id(item_id, "item_id")

    for entity_id in entity_ids:
        coordinator = _get_coordinator_for_entity(hass, entity_id)

        try:
            await coordinator.client.async_add_to_collection(
                collection_id=collection_id,
                item_ids=item_ids,
            )
        except EmbyConnectionError as err:
            raise HomeAssistantError(
                f"Failed to add to collection for {entity_id}: Connection error"
            ) from err
        except EmbyError as err:
            raise HomeAssistantError(
                f"Failed to add to collection for {entity_id}: {err}"
            ) from err
```

### Service Registration

Add to `async_setup_services()` (after line 423):

```python
    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_COLLECTION,
        async_create_collection,
        schema=CREATE_COLLECTION_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_TO_COLLECTION,
        async_add_to_collection,
        schema=ADD_TO_COLLECTION_SCHEMA,
    )
```

### Service Unload

Add to `async_unload_services()` (after line 443):

```python
    hass.services.async_remove(DOMAIN, SERVICE_CREATE_COLLECTION)
    hass.services.async_remove(DOMAIN, SERVICE_ADD_TO_COLLECTION)
```

### Test Requirements

Create comprehensive service tests:

```python
"""Tests for collection services."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError


async def test_create_collection(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_emby_client: MagicMock,
) -> None:
    """Test creating a collection."""
    # Test successful creation
    # Test with item IDs
    # Test without item IDs


async def test_create_collection_invalid_name(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test creating collection with invalid name."""
    # Verify ServiceValidationError raised


async def test_add_to_collection(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_emby_client: MagicMock,
) -> None:
    """Test adding items to collection."""
    # Test successful addition


async def test_add_to_collection_invalid_id(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test adding with invalid collection ID."""
    # Verify ServiceValidationError raised
```

---

## Task 19.3: Collection Sensors

### Description

Create sensor entities for collection tracking and monitoring.

### Acceptance Criteria

- `sensor.{server}_collections` entity shows total collection count
- Sensor attributes include list of collections with item counts
- Sensor uses library coordinator for efficient updates
- Follows existing sensor patterns from Phase 12
- Type-safe with proper TypedDicts

### File References

- **Modify:** `/workspaces/homeassistant-emby/custom_components/embymedia/sensor.py`
- **Modify:** `/workspaces/homeassistant-emby/custom_components/embymedia/api.py`
- **Modify:** `/workspaces/homeassistant-emby/custom_components/embymedia/const.py`
- **Create tests:** `/workspaces/homeassistant-emby/tests/test_sensor_collections.py`

### API Method Required

Add to `api.py`:

```python
async def async_get_collections(
    self,
    user_id: str,
) -> list[EmbyBrowseItem]:
    """Get all collections (BoxSets) for a user.

    Args:
        user_id: The user ID.

    Returns:
        List of collection items.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    result = await self.async_get_items(
        user_id,
        include_item_types="BoxSet",
        recursive=True,
        sort_by="SortName",
        sort_order="Ascending",
    )
    items: list[EmbyBrowseItem] = result.get("Items", [])  # type: ignore[assignment]
    return items
```

### Sensor Implementation Pattern

Follow the existing `EmbyLibraryCountSensor` pattern from `sensor.py`:

```python
class EmbyCollectionSensor(CoordinatorEntity[EmbyLibraryCoordinator], SensorEntity):
    """Sensor for collection count and list.

    Shows total number of collections (BoxSets) with detailed list
    in attributes including item counts.
    """

    _attr_name = "Collections"
    _attr_icon = "mdi:folder-multiple"
    _attr_native_unit_of_measurement = "collections"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: EmbyLibraryCoordinator,
        server_id: str,
        server_name: str,
        user_id: str,
    ) -> None:
        """Initialize the collections sensor.

        Args:
            coordinator: The library coordinator.
            server_id: The Emby server ID.
            server_name: The Emby server name.
            user_id: The user ID for API calls.
        """
        super().__init__(coordinator)
        self._server_id = server_id
        self._server_name = server_name
        self._user_id = user_id
        self._attr_unique_id = f"{server_id}_collections"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, server_id)},
            name=f"Emby Server ({server_name})",
            manufacturer="Emby",
            model="Media Server",
        )

    @property
    def native_value(self) -> int:
        """Return the number of collections."""
        if self.coordinator.data is None:
            return 0
        collections = self.coordinator.data.get("collections", [])
        return len(collections)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return collection details.

        Returns:
            Dictionary with collection list and metadata.
        """
        if self.coordinator.data is None:
            return {}

        collections = self.coordinator.data.get("collections", [])

        # Build collection list with item counts
        collection_list = []
        for collection in collections:
            collection_list.append({
                "id": collection["Id"],
                "name": collection["Name"],
                "item_count": collection.get("ChildCount", 0),
            })

        return {
            "collections": collection_list,
            "total_count": len(collections),
        }
```

### Coordinator Enhancement

Add collection data fetching to `EmbyLibraryCoordinator._async_update_data()`:

```python
# Fetch collections if user_id available
collections: list[EmbyBrowseItem] = []
if self._user_id:
    try:
        collections = await self.client.async_get_collections(self._user_id)
    except EmbyError as err:
        _LOGGER.debug("Failed to fetch collections: %s", err)

return {
    "item_counts": item_counts,
    "virtual_folders": virtual_folders,
    "collections": collections,  # Add to return dict
}
```

### Test Requirements

```python
"""Tests for collection sensor."""

import pytest
from custom_components.embymedia.sensor import EmbyCollectionSensor


async def test_collection_sensor_state(
    hass: HomeAssistant,
    mock_library_coordinator: EmbyLibraryCoordinator,
) -> None:
    """Test collection sensor state."""
    # Test count with multiple collections
    # Test count with zero collections


async def test_collection_sensor_attributes(
    hass: HomeAssistant,
    mock_library_coordinator: EmbyLibraryCoordinator,
) -> None:
    """Test collection sensor attributes."""
    # Verify collection list format
    # Verify item counts
    # Verify collection names and IDs
```

---

## Task 19.4: Person Browsing API Methods

### Description

Add API methods for browsing persons (actors, directors, writers) in the library.

### Acceptance Criteria

- `async_get_persons()` fetches persons list from `/Persons` endpoint
- Support filtering by person type (Actor, Director, Writer)
- Support pagination with limit/offset
- Proper TypedDict for person response
- Follow existing API patterns

### File References

- **Modify:** `/workspaces/homeassistant-emby/custom_components/embymedia/api.py`
- **Modify:** `/workspaces/homeassistant-emby/custom_components/embymedia/const.py`
- **Create tests:** `/workspaces/homeassistant-emby/tests/test_api_persons.py`

### TypedDicts Needed

Add to `const.py`:

```python
class EmbyPerson(TypedDict):
    """Type definition for person from /Persons endpoint.

    Represents an actor, director, writer, etc.
    """
    Id: str
    Name: str
    Type: str  # "Person"
    PrimaryImageTag: NotRequired[str]
    ImageTags: NotRequired[dict[str, str]]
    Role: NotRequired[str]  # "Actor", "Director", "Writer", etc.


class EmbyPersonsResponse(TypedDict):
    """Response from /Persons endpoint."""
    Items: list[EmbyPerson]
    TotalRecordCount: int
    StartIndex: int
```

### Implementation Pattern

Follow the existing `async_get_genres()` pattern (lines 1135-1176):

```python
async def async_get_persons(
    self,
    user_id: str,
    parent_id: str | None = None,
    person_types: str | None = None,
    limit: int = 100,
    start_index: int = 0,
) -> EmbyPersonsResponse:
    """Get persons (actors, directors, writers) from the library.

    Args:
        user_id: The user ID.
        parent_id: Optional parent library ID to filter persons.
        person_types: Optional person types to filter (e.g., "Actor,Director").
        limit: Maximum number of results to return.
        start_index: Pagination offset.

    Returns:
        Persons response with list of persons.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    # Check cache first (persons lists are relatively stable)
    cache_key = self._browse_cache.generate_key(
        "persons",
        user_id,
        parent_id=parent_id,
        person_types=person_types,
    )
    cached = self._browse_cache.get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]

    params = [
        f"UserId={user_id}",
        "SortBy=SortName",
        "SortOrder=Ascending",
        f"Limit={limit}",
        f"StartIndex={start_index}",
    ]
    if parent_id:
        params.append(f"ParentId={parent_id}")
    if person_types:
        params.append(f"PersonTypes={person_types}")

    query_string = "&".join(params)
    endpoint = f"/Persons?{query_string}"
    response = await self._request(HTTP_GET, endpoint)

    # Cache the result
    self._browse_cache.set(cache_key, response)
    return response  # type: ignore[return-value]


async def async_get_person_items(
    self,
    user_id: str,
    person_id: str,
    include_item_types: str | None = None,
    limit: int = 100,
) -> list[EmbyBrowseItem]:
    """Get items featuring a specific person.

    Args:
        user_id: The user ID.
        person_id: The person ID.
        include_item_types: Optional item types to filter (e.g., "Movie,Series").
        limit: Maximum number of results.

    Returns:
        List of items featuring this person.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    params = [
        f"PersonIds={person_id}",
        "Recursive=true",
        "SortBy=SortName",
        "SortOrder=Ascending",
        f"Limit={limit}",
    ]
    if include_item_types:
        params.append(f"IncludeItemTypes={include_item_types}")

    query_string = "&".join(params)
    endpoint = f"/Users/{user_id}/Items?{query_string}"
    response = await self._request(HTTP_GET, endpoint)
    items: list[EmbyBrowseItem] = response.get("Items", [])  # type: ignore[assignment]
    return items
```

### Test Requirements

```python
"""Tests for person API methods."""

import pytest
from custom_components.embymedia.api import EmbyClient


async def test_get_persons(
    emby_client: EmbyClient,
    aioclient_mock: Any,
) -> None:
    """Test fetching persons list."""
    # Test without filters
    # Test with parent_id filter
    # Test with person_types filter


async def test_get_persons_cached(
    emby_client: EmbyClient,
    aioclient_mock: Any,
) -> None:
    """Test persons list caching."""
    # Verify cache hit on second call


async def test_get_person_items(
    emby_client: EmbyClient,
    aioclient_mock: Any,
) -> None:
    """Test fetching items for a person."""
    # Test actor's filmography
    # Test director's works
```

---

## Task 19.5: Person Browsing in Media Player

### Description

Integrate person browsing into the media player's browse_media interface.

### Acceptance Criteria

- Movie libraries show "People" category
- TV libraries show "People" category
- Person list shows actors, directors, writers
- Clicking person shows their filmography
- Person images displayed when available
- Follows existing browse patterns

### File References

- **Modify:** `/workspaces/homeassistant-emby/custom_components/embymedia/media_player.py`
- **Modify:** `/workspaces/homeassistant-emby/custom_components/embymedia/browse.py`
- **Create tests:** `/workspaces/homeassistant-emby/tests/test_browse_persons.py`

### Browse Helper Updates

Add to `browse.py` (after existing mappings):

```python
# Update _EMBY_TYPE_TO_MEDIA_CLASS
_EMBY_TYPE_TO_MEDIA_CLASS: dict[str, MediaClass] = {
    # ... existing mappings ...
    "Person": MediaClass.DIRECTORY,
}

# Update _EXPANDABLE_TYPES
_EXPANDABLE_TYPES: frozenset[str] = frozenset(
    {
        # ... existing types ...
        "Person",
    }
)
```

### Media Player Browse Methods

Add to `media_player.py` after existing browse methods:

```python
async def _async_browse_movie_people(self, user_id: str, library_id: str) -> BrowseMedia:
    """Browse people in movie library.

    Args:
        user_id: The user ID for API calls.
        library_id: The movies library ID.

    Returns:
        BrowseMedia with person list as children.
    """
    coordinator: EmbyDataUpdateCoordinator = self.coordinator
    client = coordinator.client

    # Fetch persons from movie library
    persons_response = await client.async_get_persons(
        user_id,
        parent_id=library_id,
        limit=200,
    )
    persons = persons_response.get("Items", [])

    children: list[BrowseMedia] = []
    for person in persons:
        children.append(self._person_to_browse_media(person))

    return BrowseMedia(
        media_class=MediaClass.DIRECTORY,
        media_content_id=encode_content_id("moviepeople", library_id),
        media_content_type=MediaType.VIDEO,
        title="People",
        can_play=False,
        can_expand=True,
        children=children,
    )


async def _async_browse_person(
    self, user_id: str, person_id: str, library_id: str
) -> BrowseMedia:
    """Browse a person's filmography.

    Args:
        user_id: The user ID for API calls.
        person_id: The person ID.
        library_id: The library ID for filtering.

    Returns:
        BrowseMedia with person's works as children.
    """
    coordinator: EmbyDataUpdateCoordinator = self.coordinator
    client = coordinator.client

    # Fetch items featuring this person
    items = await client.async_get_person_items(
        user_id,
        person_id,
        include_item_types="Movie,Series",
        limit=200,
    )

    children: list[BrowseMedia] = []
    for item in items:
        children.append(self._item_to_browse_media(item))

    return BrowseMedia(
        media_class=MediaClass.DIRECTORY,
        media_content_id=encode_content_id("person", library_id, person_id),
        media_content_type=MediaType.VIDEO,
        title="Filmography",
        can_play=False,
        can_expand=True,
        children=children,
    )


def _person_to_browse_media(self, person: EmbyPerson) -> BrowseMedia:
    """Convert a person item to BrowseMedia.

    Args:
        person: The person from API.

    Returns:
        BrowseMedia representation of the person.
    """
    coordinator: EmbyDataUpdateCoordinator = self.coordinator
    client = coordinator.client

    # Get thumbnail if available
    thumbnail: str | None = None
    image_tags = person.get("ImageTags", {})
    if "Primary" in image_tags:
        thumbnail = client.get_image_url(
            person["Id"], image_type="Primary", tag=image_tags["Primary"]
        )

    return BrowseMedia(
        media_class=MediaClass.DIRECTORY,
        media_content_id=encode_content_id("person", person["Id"]),
        media_content_type=MediaType.VIDEO,
        title=person["Name"],
        can_play=False,
        can_expand=True,
        thumbnail=thumbnail,
    )
```

### Update Category Menus

Modify `_async_browse_movie_library()` (line 1666):

```python
async def _async_browse_movie_library(self, user_id: str, library_id: str) -> BrowseMedia:
    """Browse a movies library - show category menu."""
    categories = [
        ("A-Z", "movieaz", MediaClass.DIRECTORY),
        ("Year", "movieyear", MediaClass.DIRECTORY),
        ("Decade", "moviedecade", MediaClass.DIRECTORY),
        ("Genre", "moviegenre", MediaClass.DIRECTORY),
        ("Studio", "moviestudio", MediaClass.DIRECTORY),
        ("People", "moviepeople", MediaClass.DIRECTORY),  # NEW
        ("Collections", "moviecollection", MediaClass.DIRECTORY),
    ]
    # ... rest of implementation
```

### Add Routing

Add to `async_browse_media()` routing section (after line 805):

```python
        if content_type == "moviepeople" and ids:
            return await self._async_browse_movie_people(user_id, ids[0])
        if content_type == "person" and len(ids) >= 2:
            return await self._async_browse_person(user_id, ids[1], ids[0])
```

### Test Requirements

```python
"""Tests for person browsing."""

import pytest
from custom_components.embymedia.media_player import EmbyMediaPlayer


async def test_browse_movie_people(
    hass: HomeAssistant,
    mock_media_player: EmbyMediaPlayer,
) -> None:
    """Test browsing people in movie library."""
    # Verify person list displayed
    # Verify person names and images


async def test_browse_person_filmography(
    hass: HomeAssistant,
    mock_media_player: EmbyMediaPlayer,
) -> None:
    """Test browsing person's filmography."""
    # Verify actor's movies listed
    # Verify director's works listed
```

---

## Task 19.6: Tag Browsing API Methods

### Description

Add API methods for browsing user-defined tags.

### Acceptance Criteria

- `async_get_tags()` fetches tags list from `/Tags` endpoint
- Support filtering by parent library
- Proper TypedDict for tag response
- Follow existing API patterns
- Tag list is cached

### File References

- **Modify:** `/workspaces/homeassistant-emby/custom_components/embymedia/api.py`
- **Modify:** `/workspaces/homeassistant-emby/custom_components/embymedia/const.py`
- **Create tests:** `/workspaces/homeassistant-emby/tests/test_api_tags.py`

### TypedDicts Needed

Add to `const.py`:

```python
class EmbyTag(TypedDict):
    """Type definition for tag from /Tags endpoint.

    Represents a user-defined tag.
    """
    Id: str
    Name: str
    Type: str  # "Tag"


class EmbyTagsResponse(TypedDict):
    """Response from /Tags endpoint."""
    Items: list[EmbyTag]
    TotalRecordCount: int
```

### Implementation Pattern

Follow the existing `async_get_genres()` pattern:

```python
async def async_get_tags(
    self,
    user_id: str,
    parent_id: str | None = None,
    include_item_types: str | None = None,
) -> list[EmbyTag]:
    """Get user-defined tags from the library.

    Args:
        user_id: The user ID.
        parent_id: Optional parent library ID to filter tags.
        include_item_types: Optional item types to filter tags.

    Returns:
        List of tag items.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    # Check cache first
    cache_key = self._browse_cache.generate_key(
        "tags", user_id, parent_id=parent_id, include_item_types=include_item_types
    )
    cached = self._browse_cache.get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]

    params = [f"UserId={user_id}", "SortBy=SortName", "SortOrder=Ascending"]
    if parent_id:
        params.append(f"ParentId={parent_id}")
    if include_item_types:
        params.append(f"IncludeItemTypes={include_item_types}")

    query_string = "&".join(params)
    endpoint = f"/Tags?{query_string}"
    response = await self._request(HTTP_GET, endpoint)
    items: list[EmbyTag] = response.get("Items", [])  # type: ignore[assignment]

    # Cache the result
    self._browse_cache.set(cache_key, items)
    return items


async def async_get_items_by_tag(
    self,
    user_id: str,
    tag_id: str,
    parent_id: str | None = None,
    include_item_types: str | None = None,
    limit: int = 100,
) -> list[EmbyBrowseItem]:
    """Get items with a specific tag.

    Args:
        user_id: The user ID.
        tag_id: The tag ID to filter by.
        parent_id: Optional parent library ID.
        include_item_types: Optional item types to filter.
        limit: Maximum number of results.

    Returns:
        List of items with this tag.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    params = [
        f"TagIds={tag_id}",
        "Recursive=true",
        "SortBy=SortName",
        "SortOrder=Ascending",
        f"Limit={limit}",
    ]
    if parent_id:
        params.append(f"ParentId={parent_id}")
    if include_item_types:
        params.append(f"IncludeItemTypes={include_item_types}")

    query_string = "&".join(params)
    endpoint = f"/Users/{user_id}/Items?{query_string}"
    response = await self._request(HTTP_GET, endpoint)
    items: list[EmbyBrowseItem] = response.get("Items", [])  # type: ignore[assignment]
    return items
```

### Test Requirements

```python
"""Tests for tag API methods."""

import pytest
from custom_components.embymedia.api import EmbyClient


async def test_get_tags(
    emby_client: EmbyClient,
    aioclient_mock: Any,
) -> None:
    """Test fetching tags list."""
    # Test without filters
    # Test with parent_id
    # Test with include_item_types


async def test_get_tags_cached(
    emby_client: EmbyClient,
    aioclient_mock: Any,
) -> None:
    """Test tags list caching."""
    # Verify cache behavior


async def test_get_items_by_tag(
    emby_client: EmbyClient,
    aioclient_mock: Any,
) -> None:
    """Test fetching items by tag."""
    # Verify filtered results
```

---

## Task 19.7: Tag Browsing in Media Player

### Description

Integrate tag browsing into the media player's browse_media interface.

### Acceptance Criteria

- Libraries show "Tags" category
- Tag list displays user-defined tags
- Clicking tag shows tagged items
- Follows existing browse patterns
- Works for all library types

### File References

- **Modify:** `/workspaces/homeassistant-emby/custom_components/embymedia/media_player.py`
- **Create tests:** `/workspaces/homeassistant-emby/tests/test_browse_tags.py`

### Media Player Browse Methods

Add to `media_player.py`:

```python
async def _async_browse_movie_tags(self, user_id: str, library_id: str) -> BrowseMedia:
    """Browse tags in movie library.

    Args:
        user_id: The user ID for API calls.
        library_id: The movies library ID.

    Returns:
        BrowseMedia with tag list as children.
    """
    coordinator: EmbyDataUpdateCoordinator = self.coordinator
    client = coordinator.client

    tags = await client.async_get_tags(
        user_id,
        parent_id=library_id,
        include_item_types="Movie",
    )

    children: list[BrowseMedia] = []
    for tag in tags:
        children.append(
            BrowseMedia(
                media_class=MediaClass.DIRECTORY,
                media_content_id=encode_content_id("movietag", library_id, tag["Id"]),
                media_content_type=MediaType.VIDEO,
                title=tag["Name"],
                can_play=False,
                can_expand=True,
                thumbnail=None,
            )
        )

    return BrowseMedia(
        media_class=MediaClass.DIRECTORY,
        media_content_id=encode_content_id("movietags", library_id),
        media_content_type=MediaType.VIDEO,
        title="Tags",
        can_play=False,
        can_expand=True,
        children=children,
    )


async def _async_browse_movies_by_tag(
    self, user_id: str, library_id: str, tag_id: str
) -> BrowseMedia:
    """Browse movies with a specific tag.

    Args:
        user_id: The user ID for API calls.
        library_id: The movies library ID.
        tag_id: The tag ID to filter by.

    Returns:
        BrowseMedia with tagged movies as children.
    """
    coordinator: EmbyDataUpdateCoordinator = self.coordinator
    client = coordinator.client

    items = await client.async_get_items_by_tag(
        user_id,
        tag_id,
        parent_id=library_id,
        include_item_types="Movie",
    )

    children: list[BrowseMedia] = []
    for item in items:
        children.append(self._item_to_browse_media(item))

    return BrowseMedia(
        media_class=MediaClass.DIRECTORY,
        media_content_id=encode_content_id("movietag", library_id, tag_id),
        media_content_type=MediaType.VIDEO,
        title="Movies by Tag",
        can_play=False,
        can_expand=True,
        children=children,
    )
```

### Update Category Menu

Modify `_async_browse_movie_library()`:

```python
    categories = [
        ("A-Z", "movieaz", MediaClass.DIRECTORY),
        ("Year", "movieyear", MediaClass.DIRECTORY),
        ("Decade", "moviedecade", MediaClass.DIRECTORY),
        ("Genre", "moviegenre", MediaClass.DIRECTORY),
        ("Studio", "moviestudio", MediaClass.DIRECTORY),
        ("People", "moviepeople", MediaClass.DIRECTORY),
        ("Tags", "movietags", MediaClass.DIRECTORY),  # NEW
        ("Collections", "moviecollection", MediaClass.DIRECTORY),
    ]
```

### Add Routing

Add to `async_browse_media()`:

```python
        if content_type == "movietags" and ids:
            return await self._async_browse_movie_tags(user_id, ids[0])
        if content_type == "movietag" and len(ids) >= 2:
            return await self._async_browse_movies_by_tag(user_id, ids[0], ids[1])
```

### Test Requirements

```python
"""Tests for tag browsing."""

import pytest
from custom_components.embymedia.media_player import EmbyMediaPlayer


async def test_browse_movie_tags(
    hass: HomeAssistant,
    mock_media_player: EmbyMediaPlayer,
) -> None:
    """Test browsing tags."""
    # Verify tag list


async def test_browse_movies_by_tag(
    hass: HomeAssistant,
    mock_media_player: EmbyMediaPlayer,
) -> None:
    """Test browsing items by tag."""
    # Verify filtered items
```

---

## Task 19.8: Integration Tests

### Description

Create comprehensive integration tests for Phase 19 features.

### Acceptance Criteria

- Test complete collection creation workflow
- Test collection sensor with real data
- Test person browsing workflow
- Test tag browsing workflow
- All tests pass with 100% coverage

### File References

- **Create:** `/workspaces/homeassistant-emby/tests/test_integration_collections.py`

### Test Coverage Requirements

```python
"""Integration tests for Phase 19 features."""

import pytest
from homeassistant.core import HomeAssistant


async def test_collection_workflow(
    hass: HomeAssistant,
    setup_integration: None,
) -> None:
    """Test complete collection management workflow.

    1. Create collection via service
    2. Add items to collection
    3. Verify sensor updates
    4. Browse collection in media player
    """
    # Full workflow test


async def test_person_browsing_workflow(
    hass: HomeAssistant,
    setup_integration: None,
) -> None:
    """Test person browsing workflow.

    1. Browse to movie library
    2. Select People category
    3. Select a person
    4. View filmography
    """
    # Full browsing test


async def test_tag_browsing_workflow(
    hass: HomeAssistant,
    setup_integration: None,
) -> None:
    """Test tag browsing workflow.

    1. Browse to library
    2. Select Tags category
    3. Select a tag
    4. View tagged items
    """
    # Full browsing test
```

---

## Task 19.9: Documentation Updates

### Description

Update all documentation to reflect Phase 19 features.

### Acceptance Criteria

- README.md updated with collection services
- Service documentation includes examples
- Sensor documentation updated
- Browse features documented
- CHANGELOG.md updated

### File References

- **Modify:** `/workspaces/homeassistant-emby/README.md`
- **Modify:** `/workspaces/homeassistant-emby/CHANGELOG.md`
- **Create:** `/workspaces/homeassistant-emby/docs/services.md` (if not exists)

### Documentation Sections

#### README.md - Services Section

```markdown
### Collection Management

Create and manage collections (BoxSets):

```yaml
# Create a new collection
service: embymedia.create_collection
data:
  entity_id: media_player.living_room_tv
  collection_name: "Marvel Movies"
  item_ids:
    - "abc123"
    - "def456"

# Add items to existing collection
service: embymedia.add_to_collection
data:
  entity_id: media_player.living_room_tv
  collection_id: "collection_id_here"
  item_ids:
    - "ghi789"
```

### Enhanced Browsing

- **People**: Browse actors, directors, and writers
- **Tags**: Filter by user-defined tags
- **Collections**: View and browse BoxSets

---

## Testing Strategy

### TDD Workflow for Each Task

1. **RED Phase**
   - Write failing test first
   - Test must fail for the right reason
   - If test passes immediately, test is wrong

2. **GREEN Phase**
   - Write minimal code to pass test
   - Focus on functionality, not optimization
   - All tests must pass

3. **REFACTOR Phase**
   - Improve code while keeping tests green
   - Apply type safety (no `Any`)
   - Follow project patterns

### Coverage Requirements

- 100% line coverage for all new code
- 100% branch coverage for conditionals
- All error paths tested
- All type annotations validated by mypy

---

## Dependencies Between Tasks

```
Task 19.1 (Collection API)
    ├── Task 19.2 (Collection Services)
    └── Task 19.3 (Collection Sensors)

Task 19.4 (Person API)
    └── Task 19.5 (Person Browse UI)

Task 19.6 (Tag API)
    └── Task 19.7 (Tag Browse UI)

All tasks ──> Task 19.8 (Integration Tests)
All tasks ──> Task 19.9 (Documentation)
```

### Recommended Execution Order

1. Task 19.1 - Collection API (foundation)
2. Task 19.2 - Collection Services (builds on API)
3. Task 19.3 - Collection Sensors (builds on API)
4. Task 19.4 - Person API (independent)
5. Task 19.5 - Person Browse UI (builds on Person API)
6. Task 19.6 - Tag API (independent)
7. Task 19.7 - Tag Browse UI (builds on Tag API)
8. Task 19.8 - Integration Tests (validates all)
9. Task 19.9 - Documentation (final)

---

## Success Criteria

Phase 19 is complete when:

- ✅ All services work without errors
- ✅ Collection sensor displays accurate counts
- ✅ Person browsing shows filmography
- ✅ Tag browsing filters correctly
- ✅ All tests pass with 100% coverage
- ✅ mypy passes with strict mode
- ✅ ruff linting passes
- ✅ Documentation is complete and accurate
- ✅ No `Any` types in new code (except HA overrides)
- ✅ All TypedDicts properly defined
- ✅ Integration tests validate workflows
