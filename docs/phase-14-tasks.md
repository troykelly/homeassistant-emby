# Phase 14: Enhanced Playback & Queue Management - Task Breakdown

## Overview

Phase 14 adds advanced playback features to enhance the user experience:
- **Instant Mix Support** - Radio mode from any item or artist
- **Similar Items** - Discover related content
- **Queue Management** - Visualize and control the playback queue
- **Announcement Support** - TTS integration with auto-pause/resume

**Dependencies:** Phase 3 (Media Player Entity), Phase 8 (Services)

**Testing Standard:** TDD with RED-GREEN-REFACTOR. 100% code coverage required.

**Type Safety:** No `Any` types (except `**kwargs: Any` for HA overrides). Use TypedDict for API responses.

---

## Task 1: Instant Mix API Methods

**Acceptance Criteria:**
- `async_get_instant_mix(user_id, item_id, limit)` method in `EmbyClient`
- `async_get_artist_instant_mix(user_id, artist_id, limit)` method in `EmbyClient`
- TypedDict for response structure
- Full test coverage

### Implementation Details

**File:** `/workspaces/homeassistant-emby/custom_components/embymedia/api.py`

**Add after line 1609 (after `get_audio_stream_url` method):**

```python
async def async_get_instant_mix(
    self,
    user_id: str,
    item_id: str,
    limit: int = 100,
) -> list[EmbyBrowseItem]:
    """Get instant mix based on item.

    Creates a dynamic playlist of similar items to the seed item.

    Args:
        user_id: User ID.
        item_id: Seed item ID (song, album, artist, etc.).
        limit: Maximum number of items to return.

    Returns:
        List of items for the instant mix.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
        EmbyNotFoundError: Item not found.
    """
    endpoint = f"/Items/{item_id}/InstantMix?UserId={user_id}&Limit={limit}"
    response = await self._request(HTTP_GET, endpoint)
    items: list[EmbyBrowseItem] = response.get("Items", [])  # type: ignore[assignment]
    return items

async def async_get_artist_instant_mix(
    self,
    user_id: str,
    artist_id: str,
    limit: int = 100,
) -> list[EmbyBrowseItem]:
    """Get instant mix based on artist.

    Creates a dynamic playlist based on artist's catalog and similar artists.

    Args:
        user_id: User ID.
        artist_id: Artist ID.
        limit: Maximum number of items to return.

    Returns:
        List of items for the instant mix.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
        EmbyNotFoundError: Artist not found.
    """
    endpoint = f"/Artists/InstantMix?UserId={user_id}&Id={artist_id}&Limit={limit}"
    response = await self._request(HTTP_GET, endpoint)
    items: list[EmbyBrowseItem] = response.get("Items", [])  # type: ignore[assignment]
    return items
```

**Pattern Reference:** Based on existing `async_get_album_tracks()` at line 1030-1056 in `api.py`.

### Tests Required

**File:** `/workspaces/homeassistant-emby/tests/test_api.py`

1. `test_async_get_instant_mix_success` - Normal instant mix request
2. `test_async_get_instant_mix_empty` - No results returned
3. `test_async_get_instant_mix_custom_limit` - With custom limit parameter
4. `test_async_get_instant_mix_not_found` - Item ID not found (404)
5. `test_async_get_artist_instant_mix_success` - Artist instant mix request
6. `test_async_get_artist_instant_mix_not_found` - Artist ID not found (404)

**Test Pattern Example:**
```python
async def test_async_get_instant_mix_success(
    emby_client: EmbyClient,
    mock_aiohttp_session: aioresponses,
) -> None:
    """Test getting instant mix from item."""
    mock_aiohttp_session.get(
        "http://emby.local:8096/Items/item123/InstantMix?UserId=user1&Limit=50",
        payload={
            "Items": [
                {"Id": "song1", "Name": "Similar Song 1", "Type": "Audio"},
                {"Id": "song2", "Name": "Similar Song 2", "Type": "Audio"},
            ],
            "TotalRecordCount": 2,
        },
    )

    items = await emby_client.async_get_instant_mix("user1", "item123", limit=50)

    assert len(items) == 2
    assert items[0]["Id"] == "song1"
    assert items[0]["Name"] == "Similar Song 1"
```

---

## Task 2: Similar Items API Method

**Acceptance Criteria:**
- `async_get_similar_items(user_id, item_id, limit)` method in `EmbyClient`
- Returns list of similar items
- Full test coverage

### Implementation Details

**File:** `/workspaces/homeassistant-emby/custom_components/embymedia/api.py`

**Add after the instant mix methods:**

```python
async def async_get_similar_items(
    self,
    user_id: str,
    item_id: str,
    limit: int = 20,
) -> list[EmbyBrowseItem]:
    """Get similar items based on item.

    Finds items similar to the seed item based on metadata.

    Args:
        user_id: User ID.
        item_id: Seed item ID.
        limit: Maximum number of items to return.

    Returns:
        List of similar items.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
        EmbyNotFoundError: Item not found.
    """
    endpoint = f"/Items/{item_id}/Similar?UserId={user_id}&Limit={limit}"
    response = await self._request(HTTP_GET, endpoint)
    items: list[EmbyBrowseItem] = response.get("Items", [])  # type: ignore[assignment]
    return items
```

### Tests Required

**File:** `/workspaces/homeassistant-emby/tests/test_api.py`

1. `test_async_get_similar_items_success` - Normal similar items request
2. `test_async_get_similar_items_empty` - No similar items found
3. `test_async_get_similar_items_custom_limit` - With custom limit
4. `test_async_get_similar_items_not_found` - Item ID not found (404)

---

## Task 3: Queue Data in Session Model

**Acceptance Criteria:**
- `EmbyPlaybackState` dataclass includes queue fields
- Parse `NowPlayingQueue` from session response
- Full test coverage

### Implementation Details

**File:** `/workspaces/homeassistant-emby/custom_components/embymedia/models.py`

**Update `EmbyPlaybackState` dataclass (currently at line 52-98):**

Add new fields after line 65 (`repeat_mode: RepeatMode`):

```python
    queue_items: list[str]  # List of item IDs in queue
    queue_position: int  # Current position in queue (0-based)
```

**Update `from_api_response` class method (currently at line 67-98):**

Add after line 96 (before the return statement):

```python
        # Parse queue information if available
        queue_items: list[str] = []
        queue_position: int = 0

        now_playing_queue = play_state.get("NowPlayingQueue")
        if now_playing_queue and isinstance(now_playing_queue, list):
            queue_items = [item["Id"] for item in now_playing_queue if "Id" in item]

            # Find current position in queue
            now_playing_item_id = data.get("NowPlayingItem", {}).get("Id")
            if now_playing_item_id and now_playing_item_id in queue_items:
                queue_position = queue_items.index(now_playing_item_id)
```

**Update return statement to include new fields:**
```python
        return cls(
            position_seconds=position_seconds,
            can_seek=play_state.get("CanSeek", False),
            is_paused=play_state.get("IsPaused", False),
            is_muted=play_state.get("IsMuted", False),
            volume_level=volume_level,
            audio_stream_index=play_state.get("AudioStreamIndex"),
            subtitle_stream_index=play_state.get("SubtitleStreamIndex"),
            repeat_mode=repeat_mode,
            queue_items=queue_items,
            queue_position=queue_position,
        )
```

**Pattern Reference:** Based on existing `EmbyPlaybackState.from_api_response()` at lines 67-98 in `models.py`.

### TypedDict Update

**File:** `/workspaces/homeassistant-emby/custom_components/embymedia/const.py`

**Update `EmbyPlayState` TypedDict (currently at line 287-304):**

Add after line 303 (`RepeatMode: NotRequired[str]`):

```python
    NowPlayingQueue: NotRequired[list[dict[str, str]]]  # List of queue items
```

### Tests Required

**File:** `/workspaces/homeassistant-emby/tests/test_models.py`

1. `test_playback_state_with_queue` - Parse queue data from session
2. `test_playback_state_queue_position` - Correct queue position calculation
3. `test_playback_state_empty_queue` - No queue data present
4. `test_playback_state_invalid_queue` - Malformed queue data

---

## Task 4: Queue Attributes in Media Player

**Acceptance Criteria:**
- `queue_position` extra state attribute
- `queue_size` extra state attribute
- Full test coverage

### Implementation Details

**File:** `/workspaces/homeassistant-emby/custom_components/embymedia/media_player.py`

**Add after line 416 (after `is_volume_muted` property):**

```python
    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return entity specific state attributes.

        Returns:
            Dictionary of extra attributes.
        """
        session = self.session
        if session is None or session.play_state is None:
            return {}

        attrs: dict[str, object] = {}

        # Queue information
        queue_items = session.play_state.queue_items
        if queue_items:
            attrs["queue_size"] = len(queue_items)
            attrs["queue_position"] = session.play_state.queue_position + 1  # 1-based for display

        return attrs
```

**Pattern Reference:** Based on HA MediaPlayerEntity extra_state_attributes pattern. See example in [HA docs](https://developers.home-assistant.io/docs/core/entity/media-player/#extra-state-attributes).

### Tests Required

**File:** `/workspaces/homeassistant-emby/tests/test_media_player.py`

1. `test_queue_attributes_present` - Queue attributes when playing from queue
2. `test_queue_attributes_absent` - No queue attributes when no queue
3. `test_queue_position_calculation` - Correct 1-based position display

---

## Task 5: Clear Playlist Feature

**Acceptance Criteria:**
- `CLEAR_PLAYLIST` feature flag in `supported_features`
- `async_clear_playlist()` method implemented
- API call to clear queue
- Full test coverage

### Implementation Details

**File:** `/workspaces/homeassistant-emby/custom_components/embymedia/api.py`

**Add after the similar items method:**

```python
async def async_clear_queue(
    self,
    session_id: str,
) -> None:
    """Clear the playback queue for a session.

    Args:
        session_id: The session ID.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    endpoint = f"/Sessions/{session_id}/Playing/Stop"
    await self._request_post(endpoint)

    # Clear queue by sending empty PlayNow command
    endpoint = f"/Sessions/{session_id}/Playing"
    await self._request_post(endpoint, data={"ItemIds": "", "PlayCommand": "PlayNow"})
```

**File:** `/workspaces/homeassistant-emby/custom_components/embymedia/media_player.py`

**Update `supported_features` property (currently at line 140-180):**

Add `MediaPlayerEntityFeature.CLEAR_PLAYLIST` to the features bitmask (line 167):

```python
        features = (
            MediaPlayerEntityFeature.PAUSE
            | MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.STOP
            | MediaPlayerEntityFeature.NEXT_TRACK
            | MediaPlayerEntityFeature.PREVIOUS_TRACK
            | MediaPlayerEntityFeature.PLAY_MEDIA
            | MediaPlayerEntityFeature.BROWSE_MEDIA
            | MediaPlayerEntityFeature.MEDIA_ENQUEUE
            | MediaPlayerEntityFeature.SHUFFLE_SET
            | MediaPlayerEntityFeature.REPEAT_SET
            | MediaPlayerEntityFeature.SEARCH_MEDIA
            | MediaPlayerEntityFeature.CLEAR_PLAYLIST
        )
```

**Add method after line 564 (after `async_set_repeat` method):**

```python
    async def async_clear_playlist(self) -> None:
        """Clear the current playback queue."""
        session = self.session
        if session is None:
            return

        await self.coordinator.client.async_clear_queue(session.session_id)
```

### Tests Required

**File:** `/workspaces/homeassistant-emby/tests/test_api.py`

1. `test_async_clear_queue_success` - Clear queue API call
2. `test_async_clear_queue_connection_error` - Connection error handling

**File:** `/workspaces/homeassistant-emby/tests/test_media_player.py`

3. `test_clear_playlist_feature_supported` - Feature flag present
4. `test_async_clear_playlist_success` - Clear playlist method works
5. `test_async_clear_playlist_no_session` - No-op when no session

---

## Task 6: Play Instant Mix Service

**Acceptance Criteria:**
- `embymedia.play_instant_mix` service registered
- Service schema with entity_id, device_id, item_id, limit parameters
- Service calls API and plays instant mix
- Full test coverage

### Implementation Details

**File:** `/workspaces/homeassistant-emby/custom_components/embymedia/services.py`

**Add service constants after line 31 (after `SERVICE_REFRESH_LIBRARY`):**

```python
SERVICE_PLAY_INSTANT_MIX = "play_instant_mix"
SERVICE_PLAY_SIMILAR = "play_similar"
SERVICE_CLEAR_QUEUE = "clear_queue"
```

**Add service attributes after line 40 (after `ATTR_USER_ID`):**

```python
ATTR_LIMIT = "limit"
```

**Add service schemas after line 78 (after `REFRESH_LIBRARY_SCHEMA`):**

```python
PLAY_INSTANT_MIX_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(ATTR_ITEM_ID): cv.string,
        vol.Optional(ATTR_LIMIT, default=100): vol.All(
            vol.Coerce(int), vol.Range(min=10, max=200)
        ),
    }
)

PLAY_SIMILAR_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(ATTR_ITEM_ID): cv.string,
        vol.Optional(ATTR_LIMIT, default=20): vol.All(
            vol.Coerce(int), vol.Range(min=5, max=100)
        ),
    }
)

CLEAR_QUEUE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
    }
)
```

**Add service implementation in `async_setup_services` function before line 381 (before service registration):**

```python
    async def async_play_instant_mix(call: ServiceCall) -> None:
        """Play instant mix based on item or currently playing."""
        entity_ids = _get_entity_ids_from_call(hass, call)
        item_id: str | None = call.data.get(ATTR_ITEM_ID)
        limit: int = call.data.get(ATTR_LIMIT, 100)

        # Validate item_id if provided
        if item_id:
            _validate_emby_id(item_id, "item_id")

        for entity_id in entity_ids:
            coordinator = _get_coordinator_for_entity(hass, entity_id)
            session_id = _get_session_id_for_entity(hass, entity_id, coordinator)
            user_id = _get_user_id_for_entity(hass, entity_id, coordinator)

            if session_id is None:
                raise HomeAssistantError(
                    f"Session not found for {entity_id}. The device may be offline."
                )

            if user_id is None:
                raise ServiceValidationError(
                    f"No user_id available for {entity_id}."
                )

            # Determine item_id: use provided, or currently playing
            target_item_id = item_id
            if target_item_id is None:
                # Get currently playing item
                if coordinator.data is None:
                    raise HomeAssistantError(f"No session data for {entity_id}")

                device_id_parts = session_id.split("_", 1)
                if len(device_id_parts) < 2:
                    raise HomeAssistantError(f"Invalid session ID format for {entity_id}")
                device_id = device_id_parts[1]

                session = coordinator.data.get(device_id)
                if session is None or session.now_playing is None:
                    raise ServiceValidationError(
                        f"No item currently playing on {entity_id}. Provide item_id parameter."
                    )
                target_item_id = session.now_playing.item_id

            try:
                # Get instant mix items
                items = await coordinator.client.async_get_instant_mix(
                    user_id=user_id,
                    item_id=target_item_id,
                    limit=limit,
                )

                if not items:
                    raise ServiceValidationError(
                        f"No instant mix items found for item {target_item_id}"
                    )

                # Play the instant mix
                item_ids = [item["Id"] for item in items]
                await coordinator.client.async_play_items(
                    session_id=session_id,
                    item_ids=item_ids,
                    start_position_ticks=0,
                    play_command="PlayNow",
                )
            except EmbyConnectionError as err:
                raise HomeAssistantError(
                    f"Failed to play instant mix for {entity_id}: Connection error"
                ) from err
            except EmbyError as err:
                raise HomeAssistantError(
                    f"Failed to play instant mix for {entity_id}: {err}"
                ) from err

    async def async_play_similar(call: ServiceCall) -> None:
        """Play similar items based on item or currently playing."""
        entity_ids = _get_entity_ids_from_call(hass, call)
        item_id: str | None = call.data.get(ATTR_ITEM_ID)
        limit: int = call.data.get(ATTR_LIMIT, 20)

        # Validate item_id if provided
        if item_id:
            _validate_emby_id(item_id, "item_id")

        for entity_id in entity_ids:
            coordinator = _get_coordinator_for_entity(hass, entity_id)
            session_id = _get_session_id_for_entity(hass, entity_id, coordinator)
            user_id = _get_user_id_for_entity(hass, entity_id, coordinator)

            if session_id is None:
                raise HomeAssistantError(
                    f"Session not found for {entity_id}. The device may be offline."
                )

            if user_id is None:
                raise ServiceValidationError(
                    f"No user_id available for {entity_id}."
                )

            # Determine item_id: use provided, or currently playing
            target_item_id = item_id
            if target_item_id is None:
                # Get currently playing item (same logic as instant mix)
                if coordinator.data is None:
                    raise HomeAssistantError(f"No session data for {entity_id}")

                device_id_parts = session_id.split("_", 1)
                if len(device_id_parts) < 2:
                    raise HomeAssistantError(f"Invalid session ID format for {entity_id}")
                device_id = device_id_parts[1]

                session = coordinator.data.get(device_id)
                if session is None or session.now_playing is None:
                    raise ServiceValidationError(
                        f"No item currently playing on {entity_id}. Provide item_id parameter."
                    )
                target_item_id = session.now_playing.item_id

            try:
                # Get similar items
                items = await coordinator.client.async_get_similar_items(
                    user_id=user_id,
                    item_id=target_item_id,
                    limit=limit,
                )

                if not items:
                    raise ServiceValidationError(
                        f"No similar items found for item {target_item_id}"
                    )

                # Play the similar items
                item_ids = [item["Id"] for item in items]
                await coordinator.client.async_play_items(
                    session_id=session_id,
                    item_ids=item_ids,
                    start_position_ticks=0,
                    play_command="PlayNow",
                )
            except EmbyConnectionError as err:
                raise HomeAssistantError(
                    f"Failed to play similar items for {entity_id}: Connection error"
                ) from err
            except EmbyError as err:
                raise HomeAssistantError(
                    f"Failed to play similar items for {entity_id}: {err}"
                ) from err

    async def async_clear_queue(call: ServiceCall) -> None:
        """Clear the playback queue."""
        entity_ids = _get_entity_ids_from_call(hass, call)

        for entity_id in entity_ids:
            coordinator = _get_coordinator_for_entity(hass, entity_id)
            session_id = _get_session_id_for_entity(hass, entity_id, coordinator)

            if session_id is None:
                raise HomeAssistantError(
                    f"Session not found for {entity_id}. The device may be offline."
                )

            try:
                await coordinator.client.async_clear_queue(session_id=session_id)
            except EmbyConnectionError as err:
                raise HomeAssistantError(
                    f"Failed to clear queue for {entity_id}: Connection error"
                ) from err
            except EmbyError as err:
                raise HomeAssistantError(
                    f"Failed to clear queue for {entity_id}: {err}"
                ) from err
```

**Register services after line 423 (after last service registration):**

```python
    hass.services.async_register(
        DOMAIN,
        SERVICE_PLAY_INSTANT_MIX,
        async_play_instant_mix,
        schema=PLAY_INSTANT_MIX_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_PLAY_SIMILAR,
        async_play_similar,
        schema=PLAY_SIMILAR_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_QUEUE,
        async_clear_queue,
        schema=CLEAR_QUEUE_SCHEMA,
    )
```

**Update `async_unload_services` function after line 444 (after last service removal):**

```python
    hass.services.async_remove(DOMAIN, SERVICE_PLAY_INSTANT_MIX)
    hass.services.async_remove(DOMAIN, SERVICE_PLAY_SIMILAR)
    hass.services.async_remove(DOMAIN, SERVICE_CLEAR_QUEUE)
```

**Pattern Reference:** Based on existing service implementation in `services.py` lines 169-198 (`async_send_message`).

### Service Definitions

**File:** `/workspaces/homeassistant-emby/custom_components/embymedia/services.yaml`

Create new file with service definitions:

```yaml
play_instant_mix:
  name: Play Instant Mix
  description: Play an instant mix (radio mode) based on an item or currently playing content.
  fields:
    entity_id:
      name: Entity
      description: Target media player entity.
      selector:
        entity:
          domain: media_player
          integration: embymedia
    device_id:
      name: Device
      description: Target device (alternative to entity_id).
      selector:
        device:
          integration: embymedia
    item_id:
      name: Item ID
      description: Emby item ID to base instant mix on. If not provided, uses currently playing item.
      example: "abc123def456"
      selector:
        text:
    limit:
      name: Limit
      description: Maximum number of items in the instant mix.
      default: 100
      selector:
        number:
          min: 10
          max: 200
          step: 10

play_similar:
  name: Play Similar Items
  description: Play items similar to the specified item or currently playing content.
  fields:
    entity_id:
      name: Entity
      description: Target media player entity.
      selector:
        entity:
          domain: media_player
          integration: embymedia
    device_id:
      name: Device
      description: Target device (alternative to entity_id).
      selector:
        device:
          integration: embymedia
    item_id:
      name: Item ID
      description: Emby item ID to find similar items for. If not provided, uses currently playing item.
      example: "abc123def456"
      selector:
        text:
    limit:
      name: Limit
      description: Maximum number of similar items to play.
      default: 20
      selector:
        number:
          min: 5
          max: 100
          step: 5

clear_queue:
  name: Clear Queue
  description: Clear the playback queue for the media player.
  fields:
    entity_id:
      name: Entity
      description: Target media player entity.
      selector:
        entity:
          domain: media_player
          integration: embymedia
    device_id:
      name: Device
      description: Target device (alternative to entity_id).
      selector:
        device:
          integration: embymedia
```

### Tests Required

**File:** `/workspaces/homeassistant-emby/tests/test_services.py`

1. `test_play_instant_mix_with_item_id` - Play instant mix with explicit item ID
2. `test_play_instant_mix_from_now_playing` - Play instant mix from currently playing
3. `test_play_instant_mix_no_session` - Error when session not found
4. `test_play_instant_mix_no_playing_no_item_id` - Error when nothing playing and no item_id
5. `test_play_instant_mix_empty_results` - Error when no items returned
6. `test_play_instant_mix_connection_error` - Connection error handling
7. `test_play_similar_with_item_id` - Play similar with explicit item ID
8. `test_play_similar_from_now_playing` - Play similar from currently playing
9. `test_clear_queue_success` - Clear queue successfully
10. `test_clear_queue_no_session` - Error when session not found

---

## Task 7: Announcement Support (MEDIA_ANNOUNCE)

### ⚠️ NOT IMPLEMENTED - API Limitation

**Status:** Cannot be implemented due to Emby API limitations.

### Research Findings

After thorough research of the Emby REST API documentation:

1. **No `PlayUrl` Command Exists** - The Emby API does not have a command to play arbitrary URLs on clients.

2. **Play Command Requires Item IDs** - The `/Sessions/{Id}/Playing` endpoint only accepts `ItemIds` parameter, which must reference items already in the Emby library.

3. **Available Remote Control Commands** (from [Emby Remote Control Docs](https://dev.emby.media/doc/restapi/Remote-Control.html)):
   - Navigation: MoveUp, MoveDown, MoveLeft, MoveRight, PageUp, PageDown, Select, Back, GoHome, GoToSettings
   - Volume: VolumeUp, VolumeDown, Mute, Unmute, ToggleMute, SetVolume
   - Playback: SetAudioStreamIndex, SetSubtitleStreamIndex, SetPlaybackRate
   - Display: DisplayMessage, DisplayContent, ToggleFullscreen
   - **No PlayUrl, PlayByUrl, or PlayByPath command**

4. **TTS Requirements** - Home Assistant's TTS system generates audio URLs (e.g., `media-source://tts/...`), which cannot be played through the Emby API.

5. **Community Feature Request** - There is an [active feature request](https://emby.media/community/index.php?/topic/142642-add-server-side-audio-mixing-to-inject-%E2%80%9Cnext-up%E2%80%9D-or-emergency-announcements/) on the Emby Community forums for server-side audio mixing/announcement injection, confirming this is not currently supported.

### Alternatives Considered

1. **`.strm` Files** - Emby can play URLs via `.strm` files in the library, but this requires pre-creating library items and cannot be used for dynamic TTS content.

2. **DisplayMessage Command** - Could show text on screen, but this doesn't play audio.

3. **IPTV Plugin** - Requires plugin installation and is designed for live streams, not short announcements.

### Conclusion

The `MEDIA_ANNOUNCE` feature cannot be properly implemented for the Emby integration because Emby's API architecture requires all playable content to exist in the media library with an Item ID. External URLs (like TTS audio) cannot be played on Emby clients through the API.

This is a fundamental limitation of the Emby platform, not a limitation of this integration.

### References

- [Emby Remote Control API](https://dev.emby.media/doc/restapi/Remote-Control.html)
- [Emby Sessions Playing Endpoint](https://dev.emby.media/reference/RestAPI/SessionsService/postSessionsByIdPlaying.html)
- [HA Media Player Announce Docs](https://developers.home-assistant.io/docs/core/entity/media-player/#announcements)
- [Emby Community: URL Playback Discussion](https://emby.media/community/index.php?/topic/52423-url-playable-in-emby-player/)

---

## Task 8: Translations

**Acceptance Criteria:**
- Service descriptions in `en.json`
- Service field descriptions in `en.json`

### Implementation Details

**File:** `/workspaces/homeassistant-emby/custom_components/embymedia/strings.json`

**Add after existing services section:**

```json
  "services": {
    "send_message": {
      "name": "Send message",
      "description": "Send a message to an Emby client.",
      "fields": {
        "entity_id": {
          "name": "Entity",
          "description": "Target media player entity."
        },
        "device_id": {
          "name": "Device",
          "description": "Target device."
        },
        "message": {
          "name": "Message",
          "description": "Message text to display."
        },
        "header": {
          "name": "Header",
          "description": "Optional message header."
        },
        "timeout_ms": {
          "name": "Timeout (ms)",
          "description": "Display duration in milliseconds."
        }
      }
    },
    "play_instant_mix": {
      "name": "Play instant mix",
      "description": "Play an instant mix (radio mode) based on an item or currently playing content.",
      "fields": {
        "entity_id": {
          "name": "Entity",
          "description": "Target media player entity."
        },
        "device_id": {
          "name": "Device",
          "description": "Target device."
        },
        "item_id": {
          "name": "Item ID",
          "description": "Emby item ID to base instant mix on. If not provided, uses currently playing item."
        },
        "limit": {
          "name": "Limit",
          "description": "Maximum number of items in the instant mix."
        }
      }
    },
    "play_similar": {
      "name": "Play similar items",
      "description": "Play items similar to the specified item or currently playing content.",
      "fields": {
        "entity_id": {
          "name": "Entity",
          "description": "Target media player entity."
        },
        "device_id": {
          "name": "Device",
          "description": "Target device."
        },
        "item_id": {
          "name": "Item ID",
          "description": "Emby item ID to find similar items for. If not provided, uses currently playing item."
        },
        "limit": {
          "name": "Limit",
          "description": "Maximum number of similar items to play."
        }
      }
    },
    "clear_queue": {
      "name": "Clear queue",
      "description": "Clear the playback queue for the media player.",
      "fields": {
        "entity_id": {
          "name": "Entity",
          "description": "Target media player entity."
        },
        "device_id": {
          "name": "Device",
          "description": "Target device."
        }
      }
    }
  }
```

---

## Task 9: Documentation

**Acceptance Criteria:**
- README updated with Phase 14 features
- Service usage examples
- Queue management explanation

### Implementation Details

**File:** `/workspaces/homeassistant-emby/README.md`

Add new section after existing services documentation:

```markdown
### Enhanced Playback Features

#### Instant Mix (Radio Mode)

Play a dynamic playlist based on any item or artist:

```yaml
service: embymedia.play_instant_mix
target:
  entity_id: media_player.living_room_tv
data:
  item_id: "abc123"  # Optional - uses currently playing if omitted
  limit: 100
```

#### Similar Items

Play items similar to a specific item:

```yaml
service: embymedia.play_similar
target:
  entity_id: media_player.living_room_tv
data:
  item_id: "abc123"  # Optional - uses currently playing if omitted
  limit: 20
```

#### Queue Management

View queue status via state attributes:

```yaml
{{ state_attr('media_player.living_room_tv', 'queue_size') }}
{{ state_attr('media_player.living_room_tv', 'queue_position') }}
```

Clear the playback queue:

```yaml
service: embymedia.clear_queue
target:
  entity_id: media_player.living_room_tv
```

#### TTS Announcements

The media player supports announcements for TTS integration:

```yaml
service: tts.speak
target:
  entity_id: media_player.living_room_tv
data:
  message: "Dinner is ready!"
  options:
    announce: true  # Pauses playback, plays TTS, then resumes
```
```

---

## Testing Strategy

### Test Execution Order

1. **Task 1 Tests** - Instant Mix API (6 tests)
2. **Task 2 Tests** - Similar Items API (4 tests)
3. **Task 3 Tests** - Queue Data Parsing (4 tests)
4. **Task 4 Tests** - Queue Attributes (3 tests)
5. **Task 5 Tests** - Clear Playlist (5 tests)
6. **Task 6 Tests** - Services (10 tests)
7. **Task 7 Tests** - Announcements (5 tests)

**Total: ~37 new tests**

### Coverage Requirements

- All new code paths covered
- All error conditions tested
- Integration tests for service workflows
- Mock all API calls
- Test both success and failure paths

### TDD Workflow

For each task:

1. **RED** - Write failing test first
2. **GREEN** - Implement minimal code to pass
3. **REFACTOR** - Clean up while keeping tests green
4. **COMMIT** - Commit at each stage

---

## Integration Points

### Existing Code Modified

1. `api.py` - Add 4 new methods (instant mix, artist mix, similar, clear queue)
2. `models.py` - Update `EmbyPlaybackState` dataclass with queue fields
3. `const.py` - Update `EmbyPlayState` TypedDict
4. `media_player.py` - Add queue attributes, clear playlist, announcement support
5. `services.py` - Add 3 new services
6. `strings.json` - Add service translations

### New Files Created

1. `services.yaml` - Service definitions for UI

---

## Rollback Plan

If issues arise:

1. **Task-level rollback** - Each task is independent
2. **Feature flags** - Can disable services via service removal
3. **Queue attributes** - Return empty dict if parsing fails
4. **Announcement** - Graceful degradation if not supported

---

## Success Criteria

- All 37+ tests passing
- 100% code coverage maintained
- Mypy strict compliance (no `Any` types)
- Services visible in HA Services UI
- Queue attributes visible in Developer Tools
- Announcement works with TTS
- Documentation complete

---

## Known Limitations

1. **MEDIA_ANNOUNCE Not Supported** - The Emby API does not support playing external URLs on clients. TTS announcements require URL playback, which is not possible with Emby's current API. See Task 7 for detailed research.
2. **Queue API** - Emby's queue API is read-only in some clients. Clear queue uses stop playback workaround.
3. **Session ID Extraction** - Service helper assumes specific format. May need adjustment.

---

## Dependencies

**Python Packages:** None (uses existing dependencies)

**Home Assistant Version:** 2024.4.0+ (existing requirement)

**Emby Server Version:** 4.9.1.90+ (existing requirement)

---

## Estimated Effort

- **Task 1-2:** 2 hours (API methods + tests)
- **Task 3-4:** 2 hours (Queue data parsing + attributes)
- **Task 5:** 1 hour (Clear playlist feature)
- **Task 6:** 3 hours (Services implementation + tests)
- **Task 7:** 2 hours (Announcement support + tests)
- **Task 8-9:** 1 hour (Translations + docs)

**Total: ~11 hours**

---

## Review Checklist

- [ ] All tests pass (pytest)
- [ ] 100% code coverage (pytest-cov)
- [ ] Type checking passes (mypy --strict)
- [ ] Linting passes (ruff check)
- [ ] Formatting passes (ruff format)
- [ ] Services appear in HA UI
- [ ] Queue attributes visible
- [ ] TTS announcement works
- [ ] Documentation complete
- [ ] No `Any` types introduced
