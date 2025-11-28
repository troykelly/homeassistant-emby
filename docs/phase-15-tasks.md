# Phase 15: Smart Discovery Sensors

## Overview

This phase adds personalized content discovery sensors to expose recommendations from Emby including Next Up episodes, Continue Watching, Recently Added items, and Suggestions. These sensors help users discover what to watch next and integrate with Home Assistant dashboards and automations.

All sensors are grouped under the Emby server device and use a new `EmbyDiscoveryCoordinator` with configurable polling intervals.

## Implementation Status: COMPLETE ✅

---

## Background Research

### Emby Discovery APIs

Emby provides several personalized content endpoints:

| Endpoint | Purpose | Key Parameters |
|----------|---------|----------------|
| `/Shows/NextUp` | Next episode to watch for TV series | `UserId`, `Limit`, `EnableImages`, `Legacynextup` |
| `/Users/{id}/Items` with `Filters=IsResumable` | Partially watched content | `UserId`, `Limit`, `SortBy`, `SortOrder` |
| `/Users/{id}/Items/Latest` | Recently added content | `UserId`, `Limit`, `IncludeItemTypes` |
| `/Users/{id}/Suggestions` | Personalized recommendations | `UserId`, `Limit`, `Type` |

### Response Structures

All endpoints return lists of items with standard Emby item structure:
- `Id`, `Name`, `Type`
- `ImageTags` (for artwork)
- `UserData` (play state, progress, favorite status)
- `RunTimeTicks`, `ProductionYear`
- Type-specific fields (SeriesName, IndexNumber, etc.)

---

## Task Breakdown

### Task 15.1: TypedDicts for Discovery API

**Files:** `custom_components/embymedia/const.py`

Add TypedDicts for discovery API responses.

#### 15.1.1 NextUpItem TypedDict

```python
class NextUpItem(TypedDict, total=False):
    """Next up episode item from /Shows/NextUp.

    Represents the next episode to watch in a TV series.
    """
    # Standard item fields
    Id: str
    Name: str
    Type: str  # "Episode"
    SeriesName: str
    SeasonName: str
    IndexNumber: int  # Episode number
    ParentIndexNumber: int  # Season number

    # Series context
    SeriesId: str
    SeasonId: str

    # Metadata
    Overview: str
    RunTimeTicks: int
    ProductionYear: int
    PremiereDate: str

    # Images
    ImageTags: dict[str, str]
    SeriesPrimaryImageTag: str

    # User data
    UserData: dict[str, object]
```

**Reference pattern:** `EmbyNowPlayingItem` in `const.py:259-285`

#### 15.1.2 ResumableItem TypedDict

```python
class ResumableItem(TypedDict, total=False):
    """Resumable item from Continue Watching.

    Represents a partially watched movie or episode.
    """
    # Standard item fields
    Id: str
    Name: str
    Type: str  # "Movie" or "Episode"

    # TV-specific (only for episodes)
    SeriesName: str
    SeasonName: str
    IndexNumber: int
    ParentIndexNumber: int
    SeriesId: str

    # Metadata
    Overview: str
    RunTimeTicks: int
    ProductionYear: int

    # Images
    ImageTags: dict[str, str]
    BackdropImageTags: list[str]

    # User data with progress
    UserData: dict[str, object]  # Contains PlaybackPositionTicks, PlayedPercentage
```

**Reference pattern:** `EmbyBrowseItem` in `const.py:229-243`

#### 15.1.3 LatestMediaItem TypedDict

```python
class LatestMediaItem(TypedDict, total=False):
    """Latest media item from /Users/{id}/Items/Latest.

    Represents recently added content (movie, episode, album, etc.).
    """
    # Standard item fields
    Id: str
    Name: str
    Type: str  # "Movie", "Episode", "Audio", etc.

    # TV-specific
    SeriesName: str
    SeasonName: str
    IndexNumber: int
    ParentIndexNumber: int

    # Music-specific
    Album: str
    AlbumArtist: str
    Artists: list[str]

    # Metadata
    Overview: str
    RunTimeTicks: int
    ProductionYear: int
    DateCreated: str

    # Images
    ImageTags: dict[str, str]
```

**Reference pattern:** `EmbyBrowseItem` in `const.py:229-243`

#### 15.1.4 SuggestionItem TypedDict

```python
class SuggestionItem(TypedDict, total=False):
    """Suggestion item from /Users/{id}/Suggestions.

    Represents a personalized recommendation.
    """
    # Standard item fields
    Id: str
    Name: str
    Type: str  # "Movie", "Series", "Audio", etc.

    # Metadata
    Overview: str
    RunTimeTicks: int
    ProductionYear: int
    CommunityRating: float
    CriticRating: int

    # Images
    ImageTags: dict[str, str]
    BackdropImageTags: list[str]

    # User data
    UserData: dict[str, object]
```

**Reference pattern:** `EmbyBrowseItem` in `const.py:229-243`

**Tests:**
- [ ] Type annotation validation
- [ ] Optional field handling
- [ ] TypedDict compatibility with API responses

**Acceptance Criteria:**
- All TypedDicts defined with proper field types
- Use `NotRequired` for optional fields
- Follow existing patterns in `const.py`

---

### Task 15.2: Discovery API Methods

**Files:** `custom_components/embymedia/api.py`

Add API methods for fetching discovery data.

#### 15.2.1 async_get_next_up method

```python
async def async_get_next_up(
    self,
    user_id: str,
    limit: int = 10,
    enable_images: bool = True,
    legacy_next_up: bool = True,
) -> list[NextUpItem]:
    """Get next up episodes for user.

    Fetches the next episode to watch for each TV series the user is
    currently watching.

    Args:
        user_id: The user ID.
        limit: Maximum number of episodes to return.
        enable_images: Include image information.
        legacy_next_up: Use legacy next up logic (Legacynextup=true).
            Legacy mode is more reliable on some Emby versions.

    Returns:
        List of next up episode items.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    params: list[str] = [
        f"UserId={user_id}",
        f"Limit={limit}",
        f"EnableImages={str(enable_images).lower()}",
    ]
    if legacy_next_up:
        params.append("Legacynextup=true")

    query_string = "&".join(params)
    endpoint = f"/Shows/NextUp?{query_string}"
    response = await self._request(HTTP_GET, endpoint)
    items: list[NextUpItem] = response.get("Items", [])  # type: ignore[assignment]
    return items
```

**Reference pattern:** `async_get_user_views()` in `api.py:869-885`

**Tests:**
- [ ] Test with mocked response
- [ ] Test limit parameter
- [ ] Test legacy_next_up parameter
- [ ] Test empty response
- [ ] Test error handling

#### 15.2.2 async_get_resumable_items method

```python
async def async_get_resumable_items(
    self,
    user_id: str,
    limit: int = 10,
    include_item_types: str | None = None,
) -> list[ResumableItem]:
    """Get resumable items (Continue Watching) for user.

    Fetches movies and episodes that have been partially watched.

    Args:
        user_id: The user ID.
        limit: Maximum number of items to return.
        include_item_types: Filter by item type (e.g., "Movie,Episode").

    Returns:
        List of resumable items sorted by last played date.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    params: list[str] = [
        "Filters=IsResumable",
        f"Limit={limit}",
        "SortBy=DatePlayed",
        "SortOrder=Descending",
        "Recursive=true",
    ]
    if include_item_types:
        params.append(f"IncludeItemTypes={include_item_types}")

    query_string = "&".join(params)
    endpoint = f"/Users/{user_id}/Items?{query_string}"
    response = await self._request(HTTP_GET, endpoint)
    items: list[ResumableItem] = response.get("Items", [])  # type: ignore[assignment]
    return items
```

**Reference pattern:** `async_get_items()` in `api.py:887-950`

**Tests:**
- [ ] Test with mocked response
- [ ] Test limit parameter
- [ ] Test include_item_types filter
- [ ] Test sorting by DatePlayed
- [ ] Test empty response

#### 15.2.3 async_get_latest_media method

```python
async def async_get_latest_media(
    self,
    user_id: str,
    limit: int = 10,
    include_item_types: str | None = None,
    parent_id: str | None = None,
) -> list[LatestMediaItem]:
    """Get recently added media items.

    Fetches the most recently added content to the library.

    Args:
        user_id: The user ID.
        limit: Maximum number of items to return.
        include_item_types: Filter by item type (e.g., "Movie,Episode,Audio").
        parent_id: Optional library ID to filter within.

    Returns:
        List of latest media items sorted by date added.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    params: list[str] = [f"Limit={limit}"]
    if include_item_types:
        params.append(f"IncludeItemTypes={include_item_types}")
    if parent_id:
        params.append(f"ParentId={parent_id}")

    query_string = "&".join(params)
    endpoint = f"/Users/{user_id}/Items/Latest?{query_string}"
    response = await self._request(HTTP_GET, endpoint)
    # /Items/Latest returns array directly, not wrapped in Items property
    return response  # type: ignore[return-value]
```

**Reference pattern:** `async_get_user_views()` in `api.py:869-885`

**Tests:**
- [ ] Test with mocked response
- [ ] Test limit parameter
- [ ] Test include_item_types filter
- [ ] Test parent_id filter
- [ ] Test empty response

#### 15.2.4 async_get_suggestions method

```python
async def async_get_suggestions(
    self,
    user_id: str,
    limit: int = 10,
    suggestion_type: str | None = None,
) -> list[SuggestionItem]:
    """Get personalized suggestions for user.

    Fetches content recommendations based on watch history.

    Args:
        user_id: The user ID.
        limit: Maximum number of suggestions to return.
        suggestion_type: Optional type filter (e.g., "Movie", "Series").

    Returns:
        List of suggested items.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    params: list[str] = [f"Limit={limit}"]
    if suggestion_type:
        params.append(f"Type={suggestion_type}")

    query_string = "&".join(params)
    endpoint = f"/Users/{user_id}/Suggestions?{query_string}"
    response = await self._request(HTTP_GET, endpoint)
    items: list[SuggestionItem] = response.get("Items", [])  # type: ignore[assignment]
    return items
```

**Reference pattern:** `async_get_user_views()` in `api.py:869-885`

**Tests:**
- [ ] Test with mocked response
- [ ] Test limit parameter
- [ ] Test suggestion_type filter
- [ ] Test empty response
- [ ] Test error handling

**Acceptance Criteria:**
- All four API methods implemented
- Methods follow existing patterns in `api.py`
- Complete type annotations (no `Any`)
- Error handling for connection/auth failures
- 100% test coverage for each method

---

### Task 15.3: Discovery Coordinator

**Files:** `custom_components/embymedia/coordinator_sensors.py`

Add a new coordinator for discovery data with configurable polling.

#### 15.3.1 EmbyDiscoveryData TypedDict

```python
class EmbyDiscoveryData(TypedDict, total=False):
    """Type definition for discovery coordinator data.

    All fields are optional since they depend on user configuration
    and Emby server features.
    """
    # Next up episodes
    next_up_items: list[NextUpItem]

    # Continue watching
    resumable_items: list[ResumableItem]

    # Recently added
    latest_movies: list[LatestMediaItem]
    latest_episodes: list[LatestMediaItem]
    latest_music: list[LatestMediaItem]

    # Suggestions
    suggestions: list[SuggestionItem]
```

**Reference pattern:** `EmbyLibraryData` in `coordinator_sensors.py:43-64`

#### 15.3.2 EmbyDiscoveryCoordinator class

```python
class EmbyDiscoveryCoordinator(DataUpdateCoordinator[EmbyDiscoveryData]):
    """Coordinator for fetching discovery and recommendation data.

    Polls discovery information at configurable intervals (default: 15 minutes)
    including:
    - Next up episodes (continue watching TV shows)
    - Resumable items (partially watched content)
    - Recently added content (movies, episodes, music)
    - Personalized suggestions

    All data is user-specific and requires a configured user_id.

    Attributes:
        client: The Emby API client instance.
        server_id: The Emby server ID.
        config_entry: Config entry for reading options.
        user_id: User ID for personalized discovery (required).
    """

    client: EmbyClient
    server_id: str
    config_entry: EmbyConfigEntry
    _user_id: str

    def __init__(
        self,
        hass: HomeAssistant,
        client: EmbyClient,
        server_id: str,
        config_entry: EmbyConfigEntry,
        user_id: str,
        scan_interval: int = DEFAULT_DISCOVERY_SCAN_INTERVAL,
    ) -> None:
        """Initialize the discovery coordinator.

        Args:
            hass: Home Assistant instance.
            client: Emby API client.
            server_id: Unique server identifier.
            config_entry: Config entry for reading options.
            user_id: User ID for personalized recommendations.
            scan_interval: Polling interval in seconds (default: 900).
        """
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{server_id}_discovery",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.server_id = server_id
        self.config_entry = config_entry
        self._user_id = user_id

    @property
    def user_id(self) -> str:
        """Return the configured user ID."""
        return self._user_id

    async def _async_update_data(self) -> EmbyDiscoveryData:
        """Fetch discovery data from Emby server.

        Returns:
            Discovery data with next up, resumable, latest, and suggestions.

        Raises:
            UpdateFailed: If fetching data fails.
        """
        try:
            # Fetch all discovery data in parallel for efficiency
            results = await asyncio.gather(
                # Next up episodes
                self.client.async_get_next_up(
                    user_id=self._user_id,
                    limit=10,
                ),
                # Continue watching (resumable items)
                self.client.async_get_resumable_items(
                    user_id=self._user_id,
                    limit=10,
                ),
                # Recently added movies
                self.client.async_get_latest_media(
                    user_id=self._user_id,
                    limit=10,
                    include_item_types="Movie",
                ),
                # Recently added episodes
                self.client.async_get_latest_media(
                    user_id=self._user_id,
                    limit=10,
                    include_item_types="Episode",
                ),
                # Recently added music
                self.client.async_get_latest_media(
                    user_id=self._user_id,
                    limit=10,
                    include_item_types="Audio",
                ),
                # Suggestions
                self.client.async_get_suggestions(
                    user_id=self._user_id,
                    limit=10,
                ),
                return_exceptions=False,
            )

            return EmbyDiscoveryData(
                next_up_items=results[0],
                resumable_items=results[1],
                latest_movies=results[2],
                latest_episodes=results[3],
                latest_music=results[4],
                suggestions=results[5],
            )

        except EmbyConnectionError as err:
            raise UpdateFailed(f"Failed to connect to Emby server: {err}") from err
        except EmbyError as err:
            raise UpdateFailed(f"Error fetching discovery data: {err}") from err
```

**Reference pattern:** `EmbyLibraryCoordinator` in `coordinator_sensors.py:164-269`

**Tests:**
- [ ] Test coordinator initialization
- [ ] Test _async_update_data with mocked responses
- [ ] Test parallel API calls with asyncio.gather
- [ ] Test error handling (connection failure, auth error)
- [ ] Test UpdateFailed exception
- [ ] Test with missing user_id
- [ ] Test user_id property

**Acceptance Criteria:**
- Coordinator follows pattern of existing coordinators
- Uses `asyncio.gather()` for parallel API calls
- Proper error handling with `UpdateFailed`
- User ID is required (no None check needed)
- Default 15-minute scan interval
- Complete type annotations

---

### Task 15.4: Configuration Constants

**Files:** `custom_components/embymedia/const.py`

Add configuration constants for discovery sensors.

```python
# Discovery sensor option keys (Phase 15)
CONF_ENABLE_DISCOVERY_SENSORS: Final = "enable_discovery_sensors"
CONF_DISCOVERY_SCAN_INTERVAL: Final = "discovery_scan_interval"

# Default discovery values
DEFAULT_ENABLE_DISCOVERY_SENSORS: Final = True
DEFAULT_DISCOVERY_SCAN_INTERVAL: Final = 900  # 15 minutes in seconds
```

**Reference pattern:** Sensor constants in `const.py:99-103`

**Tests:**
- [ ] Constants are defined as Final
- [ ] Default values are appropriate types
- [ ] Constants follow naming conventions

**Acceptance Criteria:**
- Constants added to const.py
- Follow existing patterns (CONF_*, DEFAULT_*)
- Use Final type annotation

---

### Task 15.5: Discovery Sensor Entities

**Files:** `custom_components/embymedia/sensor.py`

Add sensor entities for discovery data.

#### 15.5.1 Base class for discovery sensors

```python
class EmbyDiscoverySensorBase(
    CoordinatorEntity[EmbyDiscoveryCoordinator],
    SensorEntity,
):
    """Base class for Emby discovery sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EmbyDiscoveryCoordinator,
        server_name: str,
    ) -> None:
        """Initialize the sensor.

        Args:
            coordinator: The discovery data coordinator.
            server_name: The server name for device info.
        """
        super().__init__(coordinator)
        self._server_name = server_name

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.server_id)},
            name=self._server_name,
            manufacturer="Emby",
            model="Emby Server",
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None
```

**Reference pattern:** `EmbyLibrarySensorBase` in `sensor.py:216-252`

#### 15.5.2 Next Up Sensor

```python
class EmbyNextUpSensor(EmbyDiscoverySensorBase):
    """Sensor for next up episodes.

    Shows count of next episodes to watch with full list as attributes.
    """

    _attr_icon = "mdi:television-play"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "next_up"

    def __init__(
        self,
        coordinator: EmbyDiscoveryCoordinator,
        server_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, server_name)
        self._attr_unique_id = f"{coordinator.server_id}_next_up"

    @property
    def native_value(self) -> int | None:
        """Return the count of next up episodes."""
        if self.coordinator.data is None:
            return None
        items = self.coordinator.data.get("next_up_items", [])
        return len(items)

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return attributes with episode details."""
        if self.coordinator.data is None:
            return None

        items = self.coordinator.data.get("next_up_items", [])
        if not items:
            return {"episodes": []}

        episodes = []
        for item in items:
            episodes.append({
                "id": item.get("Id"),
                "title": item.get("Name"),
                "series": item.get("SeriesName"),
                "season": item.get("ParentIndexNumber"),
                "episode": item.get("IndexNumber"),
                "image_url": self._get_image_url(item),
            })

        return {"episodes": episodes}

    def _get_image_url(self, item: NextUpItem) -> str | None:
        """Get image URL for item."""
        image_tags = item.get("ImageTags", {})
        primary_tag = image_tags.get("Primary")
        if primary_tag:
            return self.coordinator.client.get_image_url(
                item_id=item["Id"],
                image_type="Primary",
                tag=primary_tag,
            )
        return None
```

**Reference pattern:** `EmbyMovieCountSensor` in `sensor.py:255-274`

**Tests:**
- [ ] Test sensor initialization
- [ ] Test native_value with items
- [ ] Test native_value with empty list
- [ ] Test native_value with None data
- [ ] Test extra_state_attributes structure
- [ ] Test image URL generation
- [ ] Test unique_id format

#### 15.5.3 Continue Watching Sensor

```python
class EmbyContinueWatchingSensor(EmbyDiscoverySensorBase):
    """Sensor for continue watching (resumable items).

    Shows count of partially watched content with list as attributes.
    """

    _attr_icon = "mdi:play-pause"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "continue_watching"

    def __init__(
        self,
        coordinator: EmbyDiscoveryCoordinator,
        server_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, server_name)
        self._attr_unique_id = f"{coordinator.server_id}_continue_watching"

    @property
    def native_value(self) -> int | None:
        """Return the count of resumable items."""
        if self.coordinator.data is None:
            return None
        items = self.coordinator.data.get("resumable_items", [])
        return len(items)

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return attributes with item details and progress."""
        if self.coordinator.data is None:
            return None

        items = self.coordinator.data.get("resumable_items", [])
        if not items:
            return {"items": []}

        resumable = []
        for item in items:
            user_data = item.get("UserData", {})
            position_ticks = user_data.get("PlaybackPositionTicks", 0)
            runtime_ticks = item.get("RunTimeTicks", 1)

            # Calculate progress percentage
            progress = 0
            if runtime_ticks and position_ticks:
                progress = int((position_ticks / runtime_ticks) * 100)

            resumable.append({
                "id": item.get("Id"),
                "title": item.get("Name"),
                "type": item.get("Type"),
                "series": item.get("SeriesName"),  # None for movies
                "progress_percent": progress,
                "image_url": self._get_image_url(item),
            })

        return {"items": resumable}

    def _get_image_url(self, item: ResumableItem) -> str | None:
        """Get image URL for item."""
        image_tags = item.get("ImageTags", {})
        primary_tag = image_tags.get("Primary")
        if primary_tag:
            return self.coordinator.client.get_image_url(
                item_id=item["Id"],
                image_type="Primary",
                tag=primary_tag,
            )
        return None
```

**Tests:**
- [ ] Test sensor initialization
- [ ] Test native_value
- [ ] Test extra_state_attributes structure
- [ ] Test progress_percent calculation
- [ ] Test with movies and episodes
- [ ] Test image URL generation

#### 15.5.4 Recently Added Sensors

```python
class EmbyRecentlyAddedMoviesSensor(EmbyDiscoverySensorBase):
    """Sensor for recently added movies."""

    _attr_icon = "mdi:new-box"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "recently_added_movies"

    def __init__(
        self,
        coordinator: EmbyDiscoveryCoordinator,
        server_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, server_name)
        self._attr_unique_id = f"{coordinator.server_id}_recently_added_movies"

    @property
    def native_value(self) -> int | None:
        """Return the count of recently added movies."""
        if self.coordinator.data is None:
            return None
        items = self.coordinator.data.get("latest_movies", [])
        return len(items)

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return attributes with movie details."""
        if self.coordinator.data is None:
            return None

        items = self.coordinator.data.get("latest_movies", [])
        if not items:
            return {"movies": []}

        movies = []
        for item in items:
            movies.append({
                "id": item.get("Id"),
                "title": item.get("Name"),
                "year": item.get("ProductionYear"),
                "date_added": item.get("DateCreated"),
                "image_url": self._get_image_url(item),
            })

        return {"movies": movies}

    def _get_image_url(self, item: LatestMediaItem) -> str | None:
        """Get image URL for item."""
        image_tags = item.get("ImageTags", {})
        primary_tag = image_tags.get("Primary")
        if primary_tag:
            return self.coordinator.client.get_image_url(
                item_id=item["Id"],
                image_type="Primary",
                tag=primary_tag,
            )
        return None


class EmbyRecentlyAddedEpisodesSensor(EmbyDiscoverySensorBase):
    """Sensor for recently added episodes."""

    _attr_icon = "mdi:new-box"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "recently_added_episodes"

    def __init__(
        self,
        coordinator: EmbyDiscoveryCoordinator,
        server_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, server_name)
        self._attr_unique_id = f"{coordinator.server_id}_recently_added_episodes"

    @property
    def native_value(self) -> int | None:
        """Return the count of recently added episodes."""
        if self.coordinator.data is None:
            return None
        items = self.coordinator.data.get("latest_episodes", [])
        return len(items)

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return attributes with episode details."""
        if self.coordinator.data is None:
            return None

        items = self.coordinator.data.get("latest_episodes", [])
        if not items:
            return {"episodes": []}

        episodes = []
        for item in items:
            episodes.append({
                "id": item.get("Id"),
                "title": item.get("Name"),
                "series": item.get("SeriesName"),
                "season": item.get("ParentIndexNumber"),
                "episode": item.get("IndexNumber"),
                "date_added": item.get("DateCreated"),
                "image_url": self._get_image_url(item),
            })

        return {"episodes": episodes}

    def _get_image_url(self, item: LatestMediaItem) -> str | None:
        """Get image URL for item."""
        image_tags = item.get("ImageTags", {})
        primary_tag = image_tags.get("Primary")
        if primary_tag:
            return self.coordinator.client.get_image_url(
                item_id=item["Id"],
                image_type="Primary",
                tag=primary_tag,
            )
        return None


class EmbyRecentlyAddedMusicSensor(EmbyDiscoverySensorBase):
    """Sensor for recently added music."""

    _attr_icon = "mdi:music-box"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "recently_added_music"

    def __init__(
        self,
        coordinator: EmbyDiscoveryCoordinator,
        server_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, server_name)
        self._attr_unique_id = f"{coordinator.server_id}_recently_added_music"

    @property
    def native_value(self) -> int | None:
        """Return the count of recently added songs."""
        if self.coordinator.data is None:
            return None
        items = self.coordinator.data.get("latest_music", [])
        return len(items)

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return attributes with song details."""
        if self.coordinator.data is None:
            return None

        items = self.coordinator.data.get("latest_music", [])
        if not items:
            return {"tracks": []}

        tracks = []
        for item in items:
            tracks.append({
                "id": item.get("Id"),
                "title": item.get("Name"),
                "album": item.get("Album"),
                "artist": item.get("AlbumArtist"),
                "date_added": item.get("DateCreated"),
                "image_url": self._get_image_url(item),
            })

        return {"tracks": tracks}

    def _get_image_url(self, item: LatestMediaItem) -> str | None:
        """Get image URL for item."""
        image_tags = item.get("ImageTags", {})
        primary_tag = image_tags.get("Primary")
        if primary_tag:
            return self.coordinator.client.get_image_url(
                item_id=item["Id"],
                image_type="Primary",
                tag=primary_tag,
            )
        return None
```

**Tests:**
- [ ] Test each sensor initialization
- [ ] Test native_value for each
- [ ] Test extra_state_attributes structure
- [ ] Test with empty lists
- [ ] Test image URL generation

#### 15.5.5 Suggestions Sensor

```python
class EmbySuggestionsSensor(EmbyDiscoverySensorBase):
    """Sensor for personalized suggestions."""

    _attr_icon = "mdi:lightbulb-on"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "suggestions"

    def __init__(
        self,
        coordinator: EmbyDiscoveryCoordinator,
        server_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, server_name)
        self._attr_unique_id = f"{coordinator.server_id}_suggestions"

    @property
    def native_value(self) -> int | None:
        """Return the count of suggestions."""
        if self.coordinator.data is None:
            return None
        items = self.coordinator.data.get("suggestions", [])
        return len(items)

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return attributes with suggestion details."""
        if self.coordinator.data is None:
            return None

        items = self.coordinator.data.get("suggestions", [])
        if not items:
            return {"items": []}

        suggestions = []
        for item in items:
            suggestions.append({
                "id": item.get("Id"),
                "title": item.get("Name"),
                "type": item.get("Type"),
                "year": item.get("ProductionYear"),
                "rating": item.get("CommunityRating"),
                "image_url": self._get_image_url(item),
            })

        return {"items": suggestions}

    def _get_image_url(self, item: SuggestionItem) -> str | None:
        """Get image URL for item."""
        image_tags = item.get("ImageTags", {})
        primary_tag = image_tags.get("Primary")
        if primary_tag:
            return self.coordinator.client.get_image_url(
                item_id=item["Id"],
                image_type="Primary",
                tag=primary_tag,
            )
        return None
```

**Tests:**
- [ ] Test sensor initialization
- [ ] Test native_value
- [ ] Test extra_state_attributes structure
- [ ] Test with various item types
- [ ] Test image URL generation

**Acceptance Criteria:**
- All sensor classes follow existing patterns
- Base class reduces code duplication
- Sensors show counts as native_value
- Full item details in extra_state_attributes
- Image URLs included when available
- Proper icon selection
- Translation keys defined
- 100% test coverage

---

### Task 15.6: Integration Updates

**Files:**
- `custom_components/embymedia/__init__.py`
- `custom_components/embymedia/const.py`
- `custom_components/embymedia/sensor.py`

#### 15.6.1 Update EmbyRuntimeData

Add discovery coordinator to runtime data:

```python
class EmbyRuntimeData:
    """Runtime data for Emby integration."""

    def __init__(
        self,
        session_coordinator: EmbyDataUpdateCoordinator,
        server_coordinator: EmbyServerCoordinator,
        library_coordinator: EmbyLibraryCoordinator,
        discovery_coordinator: EmbyDiscoveryCoordinator | None = None,
    ) -> None:
        """Initialize runtime data.

        Args:
            session_coordinator: Coordinator for session/media player data.
            server_coordinator: Coordinator for server status data.
            library_coordinator: Coordinator for library counts data.
            discovery_coordinator: Optional coordinator for discovery data.
        """
        self.session_coordinator = session_coordinator
        self.server_coordinator = server_coordinator
        self.library_coordinator = library_coordinator
        self.discovery_coordinator = discovery_coordinator
```

**Reference pattern:** `EmbyRuntimeData` in `const.py:20-47`

#### 15.6.2 Update async_setup_entry in __init__.py

Create discovery coordinator if user_id configured:

```python
async def async_setup_entry(hass: HomeAssistant, entry: EmbyConfigEntry) -> bool:
    """Set up Emby from a config entry."""
    # ... existing code ...

    # Get user_id from config if available
    user_id = entry.data.get(CONF_USER_ID)

    # ... create other coordinators ...

    # Create discovery coordinator if user configured
    discovery_coordinator = None
    if user_id and entry.options.get(CONF_ENABLE_DISCOVERY_SENSORS, DEFAULT_ENABLE_DISCOVERY_SENSORS):
        discovery_scan_interval = entry.options.get(
            CONF_DISCOVERY_SCAN_INTERVAL,
            DEFAULT_DISCOVERY_SCAN_INTERVAL,
        )
        discovery_coordinator = EmbyDiscoveryCoordinator(
            hass,
            client,
            server_id,
            entry,
            user_id,
            scan_interval=discovery_scan_interval,
        )
        await discovery_coordinator.async_config_entry_first_refresh()

    # Store runtime data
    entry.runtime_data = EmbyRuntimeData(
        session_coordinator=session_coordinator,
        server_coordinator=server_coordinator,
        library_coordinator=library_coordinator,
        discovery_coordinator=discovery_coordinator,
    )

    # ... rest of setup ...
```

**Reference pattern:** `async_setup_entry()` in `__init__.py`

#### 15.6.3 Update sensor platform setup

Add discovery sensors to platform:

```python
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EmbyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Emby sensors from a config entry."""
    runtime_data = config_entry.runtime_data
    server_coordinator: EmbyServerCoordinator = runtime_data.server_coordinator
    library_coordinator: EmbyLibraryCoordinator = runtime_data.library_coordinator
    session_coordinator: EmbyDataUpdateCoordinator = runtime_data.session_coordinator
    discovery_coordinator: EmbyDiscoveryCoordinator | None = runtime_data.discovery_coordinator
    server_name = server_coordinator.server_name

    entities: list[SensorEntity] = [
        # Server info sensors
        EmbyVersionSensor(server_coordinator),
        EmbyRunningTasksSensor(server_coordinator),
        # Session sensors
        EmbyActiveSessionsSensor(session_coordinator),
        # Library count sensors
        EmbyMovieCountSensor(library_coordinator, server_name),
        EmbySeriesCountSensor(library_coordinator, server_name),
        EmbyEpisodeCountSensor(library_coordinator, server_name),
        EmbySongCountSensor(library_coordinator, server_name),
        EmbyAlbumCountSensor(library_coordinator, server_name),
        EmbyArtistCountSensor(library_coordinator, server_name),
    ]

    # Add discovery sensors if coordinator available
    if discovery_coordinator is not None:
        entities.extend([
            EmbyNextUpSensor(discovery_coordinator, server_name),
            EmbyContinueWatchingSensor(discovery_coordinator, server_name),
            EmbyRecentlyAddedMoviesSensor(discovery_coordinator, server_name),
            EmbyRecentlyAddedEpisodesSensor(discovery_coordinator, server_name),
            EmbyRecentlyAddedMusicSensor(discovery_coordinator, server_name),
            EmbySuggestionsSensor(discovery_coordinator, server_name),
        ])

    async_add_entities(entities)
```

**Reference pattern:** `async_setup_entry()` in `sensor.py:32-65`

**Tests:**
- [ ] Test EmbyRuntimeData with discovery_coordinator
- [ ] Test EmbyRuntimeData with None discovery_coordinator
- [ ] Test async_setup_entry creates discovery coordinator when enabled
- [ ] Test async_setup_entry skips discovery coordinator when disabled
- [ ] Test async_setup_entry skips discovery coordinator when no user_id
- [ ] Test sensor platform adds discovery sensors when available
- [ ] Test sensor platform works without discovery sensors

**Acceptance Criteria:**
- Discovery coordinator is optional in runtime data
- Coordinator only created when user_id configured AND enabled
- Sensor platform handles missing coordinator gracefully
- No errors when discovery disabled

---

### Task 15.7: Translations

**Files:**
- `custom_components/embymedia/strings.json`
- `custom_components/embymedia/translations/en.json`

Add translation keys for discovery sensors:

```json
{
  "entity": {
    "sensor": {
      "next_up": {
        "name": "Next up"
      },
      "continue_watching": {
        "name": "Continue watching"
      },
      "recently_added_movies": {
        "name": "Recently added movies"
      },
      "recently_added_episodes": {
        "name": "Recently added episodes"
      },
      "recently_added_music": {
        "name": "Recently added music"
      },
      "suggestions": {
        "name": "Suggestions"
      }
    }
  },
  "config": {
    "options": {
      "step": {
        "init": {
          "data": {
            "enable_discovery_sensors": "Enable discovery sensors",
            "discovery_scan_interval": "Discovery scan interval (seconds)"
          },
          "data_description": {
            "enable_discovery_sensors": "Show sensors for next up, continue watching, recently added, and suggestions",
            "discovery_scan_interval": "How often to update discovery data (300-3600 seconds, default: 900)"
          }
        }
      }
    }
  }
}
```

**Reference pattern:** Sensor translations in `strings.json` and `en.json`

**Tests:**
- [ ] Verify translation keys match sensor translation_key attributes
- [ ] Verify all strings are present in both files
- [ ] Test sensor names display correctly in UI

**Acceptance Criteria:**
- Translation keys defined for all sensors
- Descriptions clear and concise
- Both strings.json and en.json updated
- Follow existing translation patterns

---

### Task 15.8: Options Flow Enhancement

**Files:** `custom_components/embymedia/config_flow.py`

Add discovery sensor options to the options flow.

```python
class EmbyOptionsFlowHandler(OptionsFlow):
    """Handle Emby options."""

    async def async_step_init(
        self, user_input: dict[str, object] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get user_id to determine if discovery sensors can be enabled
        user_id = self.config_entry.data.get(CONF_USER_ID)

        # Base options schema
        options_schema = {
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=self.config_entry.options.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)),
            # ... existing options ...
        }

        # Add discovery options if user_id configured
        if user_id:
            options_schema.update({
                vol.Optional(
                    CONF_ENABLE_DISCOVERY_SENSORS,
                    default=self.config_entry.options.get(
                        CONF_ENABLE_DISCOVERY_SENSORS,
                        DEFAULT_ENABLE_DISCOVERY_SENSORS,
                    ),
                ): bool,
                vol.Optional(
                    CONF_DISCOVERY_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_DISCOVERY_SCAN_INTERVAL,
                        DEFAULT_DISCOVERY_SCAN_INTERVAL,
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=300, max=3600)),
            })

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(options_schema),
        )
```

**Reference pattern:** `EmbyOptionsFlowHandler` in `config_flow.py`

**Tests:**
- [x] Test options flow with user_id configured
- [x] Test options flow without user_id (no discovery options)
- [x] Test enable_discovery_sensors toggle
- [x] Test discovery_scan_interval validation (300-3600)
- [x] Test default values
- [x] Test saving options

**Acceptance Criteria:**
- Discovery options only shown when user_id configured
- Scan interval validated (300-3600 seconds)
- Default values match constants
- Options persist correctly

---

### Task 15.9: Testing

**Files:**
- `tests/test_api_discovery.py` (new)
- `tests/test_coordinator_discovery.py` (new)
- `tests/test_sensor_discovery.py` (new)
- `tests/test_discovery_integration.py` (new)

#### 15.9.1 API Method Tests

```python
"""Tests for discovery API methods."""

async def test_get_next_up(
    mock_aiohttp_client: aioresponses,
    emby_client: EmbyClient,
) -> None:
    """Test async_get_next_up method."""
    # Mock response
    # Test limit parameter
    # Test legacy_next_up parameter
    # Test empty response

async def test_get_resumable_items(
    mock_aiohttp_client: aioresponses,
    emby_client: EmbyClient,
) -> None:
    """Test async_get_resumable_items method."""
    # Mock response with IsResumable filter
    # Test include_item_types parameter
    # Test sorting

async def test_get_latest_media(
    mock_aiohttp_client: aioresponses,
    emby_client: EmbyClient,
) -> None:
    """Test async_get_latest_media method."""
    # Mock response
    # Test include_item_types parameter
    # Test parent_id parameter

async def test_get_suggestions(
    mock_aiohttp_client: aioresponses,
    emby_client: EmbyClient,
) -> None:
    """Test async_get_suggestions method."""
    # Mock response
    # Test suggestion_type parameter
```

**Reference pattern:** API tests in `tests/test_api_sensor_methods.py`

#### 15.9.2 Coordinator Tests

```python
"""Tests for discovery coordinator."""

async def test_discovery_coordinator_init() -> None:
    """Test discovery coordinator initialization."""

async def test_discovery_coordinator_update(
    mock_emby_client: MagicMock,
) -> None:
    """Test discovery coordinator data update."""
    # Mock all API methods
    # Verify asyncio.gather usage
    # Check data structure

async def test_discovery_coordinator_error_handling(
    mock_emby_client: MagicMock,
) -> None:
    """Test coordinator error handling."""
    # Test connection error
    # Test auth error
    # Verify UpdateFailed raised
```

**Reference pattern:** `tests/test_coordinator_sensors.py`

#### 15.9.3 Sensor Entity Tests

```python
"""Tests for discovery sensor entities."""

async def test_next_up_sensor(
    discovery_coordinator: EmbyDiscoveryCoordinator,
) -> None:
    """Test next up sensor."""
    # Test native_value
    # Test extra_state_attributes
    # Test image URL generation

async def test_continue_watching_sensor(
    discovery_coordinator: EmbyDiscoveryCoordinator,
) -> None:
    """Test continue watching sensor."""
    # Test progress calculation
    # Test attributes structure

async def test_recently_added_sensors(
    discovery_coordinator: EmbyDiscoveryCoordinator,
) -> None:
    """Test all three recently added sensors."""
    # Test movies sensor
    # Test episodes sensor
    # Test music sensor

async def test_suggestions_sensor(
    discovery_coordinator: EmbyDiscoveryCoordinator,
) -> None:
    """Test suggestions sensor."""
```

**Reference pattern:** `tests/test_sensor.py`

#### 15.9.4 Integration Tests

```python
"""Integration tests for discovery sensors."""

async def test_setup_with_user_id(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setup creates discovery coordinator with user_id."""

async def test_setup_without_user_id(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setup skips discovery when no user_id."""

async def test_setup_with_discovery_disabled(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setup skips discovery when disabled in options."""

async def test_sensor_platform_setup(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test sensor platform adds discovery sensors."""
    # Verify all 6 discovery sensors created
    # Verify sensors have correct unique_ids
```

**Tests Coverage Goals:**
- [ ] 100% code coverage for all new code
- [ ] All API methods tested with mocks
- [ ] Coordinator tested with success and error cases
- [ ] All sensor entities tested
- [ ] Integration scenarios tested
- [ ] Edge cases covered (empty lists, None data, missing user_id)

**Acceptance Criteria:**
- Minimum 100% code coverage
- All tests pass
- No mypy errors
- No ruff errors
- Follow existing test patterns

---

## Files Created/Modified

### New Files
- `tests/test_api_discovery.py` - Discovery API method tests
- `tests/test_coordinator_discovery.py` - Discovery coordinator tests
- `tests/test_sensor_discovery.py` - Discovery sensor entity tests
- `tests/test_discovery_integration.py` - Integration tests

### Modified Files
- `custom_components/embymedia/api.py` - Add 4 discovery API methods
- `custom_components/embymedia/const.py` - Add TypedDicts and constants
- `custom_components/embymedia/coordinator_sensors.py` - Add EmbyDiscoveryCoordinator
- `custom_components/embymedia/sensor.py` - Add 6 discovery sensor entities
- `custom_components/embymedia/__init__.py` - Create discovery coordinator
- `custom_components/embymedia/config_flow.py` - Add options flow fields
- `custom_components/embymedia/strings.json` - Add translations
- `custom_components/embymedia/translations/en.json` - Add translations

---

## Architecture

### Data Flow

```
EmbyDiscoveryCoordinator (15 min polling)
├── async_get_next_up() → next_up_items
├── async_get_resumable_items() → resumable_items
├── async_get_latest_media(Movie) → latest_movies
├── async_get_latest_media(Episode) → latest_episodes
├── async_get_latest_media(Audio) → latest_music
└── async_get_suggestions() → suggestions

EmbyDiscoveryData (TypedDict)
└── All 6 lists stored in coordinator.data

Discovery Sensors (6 total)
├── EmbyNextUpSensor
├── EmbyContinueWatchingSensor
├── EmbyRecentlyAddedMoviesSensor
├── EmbyRecentlyAddedEpisodesSensor
├── EmbyRecentlyAddedMusicSensor
└── EmbySuggestionsSensor
```

### Entity Hierarchy

All discovery sensors grouped under Emby server device:

```
Device: Emby {Server Name}
├── [Existing sensors...]
├── sensor.{server}_next_up
├── sensor.{server}_continue_watching
├── sensor.{server}_recently_added_movies
├── sensor.{server}_recently_added_episodes
├── sensor.{server}_recently_added_music
└── sensor.{server}_suggestions
```

### Configuration Flow

```
User selects user during config flow
    ↓
Config entry has user_id
    ↓
Options flow shows discovery toggles
    ↓
enable_discovery_sensors = true (default)
discovery_scan_interval = 900 (default, 15 min)
    ↓
EmbyDiscoveryCoordinator created in async_setup_entry
    ↓
Discovery sensors added to sensor platform
    ↓
Sensors poll every 15 minutes (configurable)
```

---

## Success Criteria

- [ ] All 6 discovery sensors implemented and working
- [ ] Discovery coordinator fetches data in parallel (asyncio.gather)
- [ ] Sensors show item counts as native_value
- [ ] Full item details in extra_state_attributes with image URLs
- [ ] Discovery coordinator only created when user_id configured
- [ ] Options flow allows enable/disable and interval configuration
- [ ] Default 15-minute polling interval
- [ ] 100% test coverage for all new code
- [ ] No `Any` types (strict typing)
- [ ] All translations complete
- [ ] Mypy strict compliance
- [ ] Ruff linting passes

---

## Implementation Notes

### API Endpoint Details

1. **Next Up** (`/Shows/NextUp`):
   - Returns next episode to watch for each series
   - `Legacynextup=true` is more reliable on older Emby versions
   - Sorted by last watched date

2. **Continue Watching** (`/Users/{id}/Items?Filters=IsResumable`):
   - Returns partially watched content
   - Includes `PlaybackPositionTicks` in `UserData`
   - Sort by `DatePlayed` descending for most recent first

3. **Recently Added** (`/Users/{id}/Items/Latest`):
   - Returns array directly (not wrapped in `Items` property)
   - Filter by `IncludeItemTypes` for movies/episodes/music
   - Limited to most recent items by `Limit` parameter

4. **Suggestions** (`/Users/{id}/Suggestions`):
   - Personalized based on watch history
   - May return empty list if insufficient viewing data
   - Can filter by `Type` parameter

### Progress Calculation

For Continue Watching sensor:
```python
progress_percent = (PlaybackPositionTicks / RunTimeTicks) * 100
```

Ensure `RunTimeTicks` is not zero before division.

### Image URL Generation

All sensors should include image URLs in attributes:
```python
client.get_image_url(
    item_id=item["Id"],
    image_type="Primary",
    tag=image_tags.get("Primary"),
)
```

Fallback to None if no image available.

### Performance Optimization

Use `asyncio.gather()` to fetch all discovery data in parallel:
- Reduces total coordinator update time
- All 6 API calls execute concurrently
- Fail fast if any call raises exception

---

## Future Enhancements (Not Implemented)

The following features could be added in future iterations:

- Per-library recently added sensors (configurable libraries)
- Filtering options for item types in sensors
- WebSocket events for real-time updates when items added
- Configurable item limits per sensor
- Custom sort orders for discovery lists
- Integration with media player for "Play Next Up" action
- Dashboard cards showing discovery content with thumbnails

---

## Dependencies

### Phase Dependencies
- **Requires:** Phase 12 (Sensor Platform) - coordinator patterns
- **Requires:** Phase 1 (API Client) - `EmbyClient` foundation
- **Requires:** User configuration in config flow

### External Dependencies
- Home Assistant 2024.4.0+
- Emby Server 4.9.1+
- User account on Emby server with viewing history

---

## Rollout Plan

1. **Phase 15.1-15.2**: Add TypedDicts and API methods (no UI impact)
2. **Phase 15.3-15.4**: Add coordinator and constants (backend only)
3. **Phase 15.5**: Add sensor entities (visible to users)
4. **Phase 15.6-15.7**: Integration and translations
5. **Phase 15.8**: Options flow (user configuration)
6. **Phase 15.9**: Testing (100% coverage)

Each step should maintain 100% test coverage and pass all CI checks before proceeding.
