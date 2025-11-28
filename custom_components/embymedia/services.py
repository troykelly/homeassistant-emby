"""Services for the Emby integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.const import ATTR_DEVICE_ID, ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, MAX_SEARCH_TERM_LENGTH
from .exceptions import EmbyConnectionError, EmbyError

if TYPE_CHECKING:
    from .coordinator import EmbyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Service names
SERVICE_SEND_MESSAGE = "send_message"
SERVICE_SEND_COMMAND = "send_command"
SERVICE_MARK_PLAYED = "mark_played"
SERVICE_MARK_UNPLAYED = "mark_unplayed"
SERVICE_ADD_FAVORITE = "add_favorite"
SERVICE_REMOVE_FAVORITE = "remove_favorite"
SERVICE_REFRESH_LIBRARY = "refresh_library"
SERVICE_PLAY_INSTANT_MIX = "play_instant_mix"
SERVICE_PLAY_SIMILAR = "play_similar"
# Live TV services (Phase 16)
SERVICE_SCHEDULE_RECORDING = "schedule_recording"
SERVICE_CANCEL_RECORDING = "cancel_recording"
SERVICE_CANCEL_SERIES_TIMER = "cancel_series_timer"
# Playlist services (Phase 17)
SERVICE_CREATE_PLAYLIST = "create_playlist"
SERVICE_ADD_TO_PLAYLIST = "add_to_playlist"
SERVICE_REMOVE_FROM_PLAYLIST = "remove_from_playlist"
# Collection services (Phase 19)
SERVICE_CREATE_COLLECTION = "create_collection"
SERVICE_ADD_TO_COLLECTION = "add_to_collection"
SERVICE_REMOVE_FROM_COLLECTION = "remove_from_collection"

# Service attributes
ATTR_MESSAGE = "message"
ATTR_HEADER = "header"
ATTR_TIMEOUT_MS = "timeout_ms"
ATTR_COMMAND = "command"
ATTR_ITEM_ID = "item_id"
ATTR_LIBRARY_ID = "library_id"
ATTR_USER_ID = "user_id"
# Live TV service attributes (Phase 16)
ATTR_PROGRAM_ID = "program_id"
ATTR_TIMER_ID = "timer_id"
ATTR_SERIES_TIMER_ID = "series_timer_id"
ATTR_PRE_PADDING_SECONDS = "pre_padding_seconds"
ATTR_POST_PADDING_SECONDS = "post_padding_seconds"
# Playlist service attributes (Phase 17)
ATTR_NAME = "name"
ATTR_MEDIA_TYPE = "media_type"
ATTR_ITEM_IDS = "item_ids"
ATTR_PLAYLIST_ID = "playlist_id"
ATTR_PLAYLIST_ITEM_IDS = "playlist_item_ids"
# Collection service attributes (Phase 19)
ATTR_COLLECTION_NAME = "collection_name"
ATTR_COLLECTION_ID = "collection_id"

# Service schemas - support both entity_id and device_id targeting
SEND_MESSAGE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(ATTR_MESSAGE): cv.string,
        vol.Optional(ATTR_HEADER, default=""): cv.string,
        vol.Optional(ATTR_TIMEOUT_MS, default=5000): vol.All(
            vol.Coerce(int), vol.Range(min=1000, max=60000)
        ),
    }
)

SEND_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(ATTR_COMMAND): cv.string,
    }
)

ITEM_ACTION_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(ATTR_ITEM_ID): cv.string,
        vol.Optional(ATTR_USER_ID): cv.string,
    }
)

REFRESH_LIBRARY_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(ATTR_LIBRARY_ID): cv.string,
    }
)

PLAY_MIX_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(ATTR_ITEM_ID): cv.string,
        vol.Optional(ATTR_USER_ID): cv.string,
    }
)

# Live TV service schemas (Phase 16)
SCHEDULE_RECORDING_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(ATTR_PROGRAM_ID): cv.string,
        vol.Optional(ATTR_PRE_PADDING_SECONDS): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=3600)
        ),
        vol.Optional(ATTR_POST_PADDING_SECONDS): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=3600)
        ),
    }
)

CANCEL_RECORDING_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(ATTR_TIMER_ID): cv.string,
    }
)

CANCEL_SERIES_TIMER_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(ATTR_SERIES_TIMER_ID): cv.string,
    }
)

# Playlist service schemas (Phase 17)
CREATE_PLAYLIST_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(ATTR_NAME): cv.string,
        vol.Required(ATTR_MEDIA_TYPE): vol.In(["Audio", "Video"]),
        vol.Required(ATTR_USER_ID): cv.string,
        vol.Optional(ATTR_ITEM_IDS): vol.All(cv.ensure_list, [cv.string]),
    }
)

ADD_TO_PLAYLIST_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(ATTR_PLAYLIST_ID): cv.string,
        vol.Required(ATTR_ITEM_IDS): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(ATTR_USER_ID): cv.string,
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

# Collection service schemas (Phase 19)
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

REMOVE_FROM_COLLECTION_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(ATTR_COLLECTION_ID): cv.string,
        vol.Required(ATTR_ITEM_IDS): vol.All(cv.ensure_list, [cv.string]),
    }
)


def _validate_emby_id(id_value: str, id_name: str) -> None:
    """Validate an Emby ID.

    Args:
        id_value: The ID value to validate.
        id_name: Name of the ID for error messages.

    Raises:
        ServiceValidationError: If ID is invalid.
    """
    if not id_value or not id_value.strip():
        raise ServiceValidationError(f"Invalid {id_name}: cannot be empty")

    # Emby IDs are typically alphanumeric with possible dashes
    # They should not contain suspicious characters
    if len(id_value) > MAX_SEARCH_TERM_LENGTH:
        raise ServiceValidationError(
            f"Invalid {id_name}: exceeds maximum length of {MAX_SEARCH_TERM_LENGTH}"
        )

    # Basic validation - Emby IDs are alphanumeric with possible dashes/underscores
    invalid_chars = set(id_value) - set(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    )
    if invalid_chars:
        raise ServiceValidationError(f"Invalid {id_name}: contains invalid characters")


def _get_entity_ids_from_call(hass: HomeAssistant, call: ServiceCall) -> list[str]:
    """Get entity IDs from service call data (supports both entity_id and device_id).

    Args:
        hass: Home Assistant instance.
        call: Service call data.

    Returns:
        List of entity IDs to target.

    Raises:
        ServiceValidationError: If no valid targets provided.
    """
    entity_ids: list[str] = []

    # Get entity_ids directly specified
    if ATTR_ENTITY_ID in call.data:
        direct_ids = call.data[ATTR_ENTITY_ID]
        if isinstance(direct_ids, list):
            entity_ids.extend(direct_ids)
        elif isinstance(direct_ids, str):
            entity_ids.append(direct_ids)

    # Get entity_ids from device_ids
    if ATTR_DEVICE_ID in call.data:
        device_ids = call.data[ATTR_DEVICE_ID]
        if isinstance(device_ids, str):
            device_ids = [device_ids]

        device_registry = dr.async_get(hass)
        entity_registry = er.async_get(hass)

        for device_id in device_ids:
            # Validate device exists and is an Emby device
            device = device_registry.async_get(device_id)
            if device is None:
                raise ServiceValidationError(f"Device {device_id} not found")

            # Find media_player entities for this device (only media_player has sessions)
            # Button entities are server-level and don't have sessions
            for entry in er.async_entries_for_device(entity_registry, device_id):
                if entry.platform == DOMAIN and entry.domain == "media_player":
                    entity_ids.append(entry.entity_id)

    if not entity_ids:
        raise ServiceValidationError("No valid targets provided. Specify entity_id.")

    return entity_ids


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up Emby services.

    Args:
        hass: Home Assistant instance.
    """
    if hass.services.has_service(DOMAIN, SERVICE_SEND_MESSAGE):
        # Services already registered
        return

    async def async_send_message(call: ServiceCall) -> None:
        """Send a message to Emby clients."""
        entity_ids = _get_entity_ids_from_call(hass, call)
        message: str = call.data[ATTR_MESSAGE]
        header: str = call.data.get(ATTR_HEADER, "")
        timeout_ms: int = call.data.get(ATTR_TIMEOUT_MS, 5000)

        for entity_id in entity_ids:
            coordinator = _get_coordinator_for_entity(hass, entity_id)
            session_id = _get_session_id_for_entity(hass, entity_id, coordinator)

            if session_id is None:
                raise HomeAssistantError(
                    f"Session not found for {entity_id}. The device may be offline."
                )

            try:
                await coordinator.client.async_send_message(
                    session_id=session_id,
                    text=message,
                    header=header,
                    timeout_ms=timeout_ms,
                )
            except EmbyConnectionError as err:
                raise HomeAssistantError(
                    f"Failed to send message to {entity_id}: Connection error"
                ) from err
            except EmbyError as err:
                raise HomeAssistantError(f"Failed to send message to {entity_id}: {err}") from err

    async def async_send_command(call: ServiceCall) -> None:
        """Send a command to Emby clients."""
        entity_ids = _get_entity_ids_from_call(hass, call)
        command: str = call.data[ATTR_COMMAND]

        for entity_id in entity_ids:
            coordinator = _get_coordinator_for_entity(hass, entity_id)
            session_id = _get_session_id_for_entity(hass, entity_id, coordinator)

            if session_id is None:
                raise HomeAssistantError(
                    f"Session not found for {entity_id}. The device may be offline."
                )

            try:
                await coordinator.client.async_send_general_command(
                    session_id=session_id,
                    command=command,
                )
            except EmbyConnectionError as err:
                raise HomeAssistantError(
                    f"Failed to send command to {entity_id}: Connection error"
                ) from err
            except EmbyError as err:
                raise HomeAssistantError(f"Failed to send command to {entity_id}: {err}") from err

    async def async_mark_played(call: ServiceCall) -> None:
        """Mark item as played."""
        entity_ids = _get_entity_ids_from_call(hass, call)
        item_id: str = call.data[ATTR_ITEM_ID]
        user_id: str | None = call.data.get(ATTR_USER_ID)

        # Validate IDs
        _validate_emby_id(item_id, "item_id")
        if user_id:
            _validate_emby_id(user_id, "user_id")

        for entity_id in entity_ids:
            coordinator = _get_coordinator_for_entity(hass, entity_id)
            effective_user_id = user_id or _get_user_id_for_entity(hass, entity_id, coordinator)

            if not effective_user_id:
                raise ServiceValidationError(
                    f"No user_id available for {entity_id}. Please provide user_id parameter."
                )

            try:
                await coordinator.client.async_mark_played(
                    user_id=effective_user_id,
                    item_id=item_id,
                )
            except EmbyConnectionError as err:
                raise HomeAssistantError(
                    f"Failed to mark item played for {entity_id}: Connection error"
                ) from err
            except EmbyError as err:
                raise HomeAssistantError(
                    f"Failed to mark item played for {entity_id}: {err}"
                ) from err

    async def async_mark_unplayed(call: ServiceCall) -> None:
        """Mark item as unplayed."""
        entity_ids = _get_entity_ids_from_call(hass, call)
        item_id: str = call.data[ATTR_ITEM_ID]
        user_id: str | None = call.data.get(ATTR_USER_ID)

        # Validate IDs
        _validate_emby_id(item_id, "item_id")
        if user_id:
            _validate_emby_id(user_id, "user_id")

        for entity_id in entity_ids:
            coordinator = _get_coordinator_for_entity(hass, entity_id)
            effective_user_id = user_id or _get_user_id_for_entity(hass, entity_id, coordinator)

            if not effective_user_id:
                raise ServiceValidationError(
                    f"No user_id available for {entity_id}. Please provide user_id parameter."
                )

            try:
                await coordinator.client.async_mark_unplayed(
                    user_id=effective_user_id,
                    item_id=item_id,
                )
            except EmbyConnectionError as err:
                raise HomeAssistantError(
                    f"Failed to mark item unplayed for {entity_id}: Connection error"
                ) from err
            except EmbyError as err:
                raise HomeAssistantError(
                    f"Failed to mark item unplayed for {entity_id}: {err}"
                ) from err

    async def async_add_favorite(call: ServiceCall) -> None:
        """Add item to favorites."""
        entity_ids = _get_entity_ids_from_call(hass, call)
        item_id: str = call.data[ATTR_ITEM_ID]
        user_id: str | None = call.data.get(ATTR_USER_ID)

        # Validate IDs
        _validate_emby_id(item_id, "item_id")
        if user_id:
            _validate_emby_id(user_id, "user_id")

        for entity_id in entity_ids:
            coordinator = _get_coordinator_for_entity(hass, entity_id)
            effective_user_id = user_id or _get_user_id_for_entity(hass, entity_id, coordinator)

            if not effective_user_id:
                raise ServiceValidationError(
                    f"No user_id available for {entity_id}. Please provide user_id parameter."
                )

            try:
                await coordinator.client.async_add_favorite(
                    user_id=effective_user_id,
                    item_id=item_id,
                )
            except EmbyConnectionError as err:
                raise HomeAssistantError(
                    f"Failed to add favorite for {entity_id}: Connection error"
                ) from err
            except EmbyError as err:
                raise HomeAssistantError(f"Failed to add favorite for {entity_id}: {err}") from err

    async def async_remove_favorite(call: ServiceCall) -> None:
        """Remove item from favorites."""
        entity_ids = _get_entity_ids_from_call(hass, call)
        item_id: str = call.data[ATTR_ITEM_ID]
        user_id: str | None = call.data.get(ATTR_USER_ID)

        # Validate IDs
        _validate_emby_id(item_id, "item_id")
        if user_id:
            _validate_emby_id(user_id, "user_id")

        for entity_id in entity_ids:
            coordinator = _get_coordinator_for_entity(hass, entity_id)
            effective_user_id = user_id or _get_user_id_for_entity(hass, entity_id, coordinator)

            if not effective_user_id:
                raise ServiceValidationError(
                    f"No user_id available for {entity_id}. Please provide user_id parameter."
                )

            try:
                await coordinator.client.async_remove_favorite(
                    user_id=effective_user_id,
                    item_id=item_id,
                )
            except EmbyConnectionError as err:
                raise HomeAssistantError(
                    f"Failed to remove favorite for {entity_id}: Connection error"
                ) from err
            except EmbyError as err:
                raise HomeAssistantError(
                    f"Failed to remove favorite for {entity_id}: {err}"
                ) from err

    async def async_refresh_library(call: ServiceCall) -> None:
        """Trigger library refresh."""
        entity_ids = _get_entity_ids_from_call(hass, call)
        library_id: str | None = call.data.get(ATTR_LIBRARY_ID)

        # Validate library_id if provided
        if library_id:
            _validate_emby_id(library_id, "library_id")

        for entity_id in entity_ids:
            coordinator = _get_coordinator_for_entity(hass, entity_id)
            try:
                await coordinator.client.async_refresh_library(library_id=library_id)
            except EmbyConnectionError as err:
                raise HomeAssistantError(
                    f"Failed to refresh library for {entity_id}: Connection error"
                ) from err
            except EmbyError as err:
                raise HomeAssistantError(
                    f"Failed to refresh library for {entity_id}: {err}"
                ) from err

    async def async_play_instant_mix(call: ServiceCall) -> None:
        """Play instant mix based on an item."""
        entity_ids = _get_entity_ids_from_call(hass, call)
        item_id: str = call.data[ATTR_ITEM_ID]
        user_id: str | None = call.data.get(ATTR_USER_ID)

        # Validate IDs
        _validate_emby_id(item_id, "item_id")
        if user_id:
            _validate_emby_id(user_id, "user_id")

        for entity_id in entity_ids:
            coordinator = _get_coordinator_for_entity(hass, entity_id)
            effective_user_id = user_id or _get_user_id_for_entity(hass, entity_id, coordinator)

            if not effective_user_id:
                raise ServiceValidationError(
                    f"No user_id available for {entity_id}. Please provide user_id parameter."
                )

            session_id = _get_session_id_for_entity(hass, entity_id, coordinator)
            if session_id is None:
                raise ServiceValidationError(
                    f"No session found for {entity_id}. Is the device active?"
                )

            try:
                # Get instant mix items
                items = await coordinator.client.async_get_instant_mix(
                    user_id=effective_user_id,
                    item_id=item_id,
                )

                if not items:
                    raise HomeAssistantError(f"No instant mix items found for item {item_id}")

                # Play all items at once (Emby handles queuing internally)
                item_ids_to_play = [item["Id"] for item in items]
                await coordinator.client.async_play_items(
                    session_id=session_id,
                    item_ids=item_ids_to_play,
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
        """Play similar items based on an item."""
        entity_ids = _get_entity_ids_from_call(hass, call)
        item_id: str = call.data[ATTR_ITEM_ID]
        user_id: str | None = call.data.get(ATTR_USER_ID)

        # Validate IDs
        _validate_emby_id(item_id, "item_id")
        if user_id:
            _validate_emby_id(user_id, "user_id")

        for entity_id in entity_ids:
            coordinator = _get_coordinator_for_entity(hass, entity_id)
            effective_user_id = user_id or _get_user_id_for_entity(hass, entity_id, coordinator)

            if not effective_user_id:
                raise ServiceValidationError(
                    f"No user_id available for {entity_id}. Please provide user_id parameter."
                )

            session_id = _get_session_id_for_entity(hass, entity_id, coordinator)
            if session_id is None:
                raise ServiceValidationError(
                    f"No session found for {entity_id}. Is the device active?"
                )

            try:
                # Get similar items
                items = await coordinator.client.async_get_similar_items(
                    user_id=effective_user_id,
                    item_id=item_id,
                )

                if not items:
                    raise HomeAssistantError(f"No similar items found for item {item_id}")

                # Play all items at once (Emby handles queuing internally)
                item_ids_to_play = [item["Id"] for item in items]
                await coordinator.client.async_play_items(
                    session_id=session_id,
                    item_ids=item_ids_to_play,
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

    # Live TV Services (Phase 16)
    async def async_schedule_recording(call: ServiceCall) -> None:
        """Schedule a one-time recording."""
        entity_ids = _get_entity_ids_from_call(hass, call)
        program_id: str = call.data[ATTR_PROGRAM_ID]
        pre_padding: int | None = call.data.get(ATTR_PRE_PADDING_SECONDS)
        post_padding: int | None = call.data.get(ATTR_POST_PADDING_SECONDS)

        # Validate program ID
        _validate_emby_id(program_id, "program_id")

        for entity_id in entity_ids:
            coordinator = _get_coordinator_for_entity(hass, entity_id)

            try:
                # Get default timer settings from server
                timer_defaults = await coordinator.client.async_get_timer_defaults(
                    program_id=program_id
                )

                # Convert to mutable dict and override with user-provided values
                timer_data: dict[str, object] = dict(timer_defaults)
                if pre_padding is not None:
                    timer_data["PrePaddingSeconds"] = pre_padding
                if post_padding is not None:
                    timer_data["PostPaddingSeconds"] = post_padding

                # Create the timer
                await coordinator.client.async_create_timer(timer_data=timer_data)

            except EmbyConnectionError as err:
                raise HomeAssistantError(
                    f"Failed to schedule recording for {entity_id}: Connection error"
                ) from err
            except EmbyError as err:
                raise HomeAssistantError(
                    f"Failed to schedule recording for {entity_id}: {err}"
                ) from err

    async def async_cancel_recording(call: ServiceCall) -> None:
        """Cancel a scheduled recording."""
        entity_ids = _get_entity_ids_from_call(hass, call)
        timer_id: str = call.data[ATTR_TIMER_ID]

        # Validate timer ID
        _validate_emby_id(timer_id, "timer_id")

        for entity_id in entity_ids:
            coordinator = _get_coordinator_for_entity(hass, entity_id)

            try:
                await coordinator.client.async_cancel_timer(timer_id=timer_id)
            except EmbyConnectionError as err:
                raise HomeAssistantError(
                    f"Failed to cancel recording for {entity_id}: Connection error"
                ) from err
            except EmbyError as err:
                raise HomeAssistantError(
                    f"Failed to cancel recording for {entity_id}: {err}"
                ) from err

    async def async_cancel_series_timer(call: ServiceCall) -> None:
        """Cancel a series recording timer."""
        entity_ids = _get_entity_ids_from_call(hass, call)
        series_timer_id: str = call.data[ATTR_SERIES_TIMER_ID]

        # Validate series timer ID
        _validate_emby_id(series_timer_id, "series_timer_id")

        for entity_id in entity_ids:
            coordinator = _get_coordinator_for_entity(hass, entity_id)

            try:
                await coordinator.client.async_cancel_series_timer(series_timer_id=series_timer_id)
            except EmbyConnectionError as err:
                raise HomeAssistantError(
                    f"Failed to cancel series timer for {entity_id}: Connection error"
                ) from err
            except EmbyError as err:
                raise HomeAssistantError(
                    f"Failed to cancel series timer for {entity_id}: {err}"
                ) from err

    # Playlist Services (Phase 17)
    async def async_create_playlist(call: ServiceCall) -> None:
        """Create a new playlist."""
        entity_ids = _get_entity_ids_from_call(hass, call)
        name: str = call.data[ATTR_NAME]
        media_type: str = call.data[ATTR_MEDIA_TYPE]
        user_id: str = call.data[ATTR_USER_ID]
        item_ids: list[str] | None = call.data.get(ATTR_ITEM_IDS)

        # Validate IDs
        _validate_emby_id(user_id, "user_id")
        if item_ids:
            for item_id in item_ids:
                _validate_emby_id(item_id, "item_id")

        for entity_id in entity_ids:
            coordinator = _get_coordinator_for_entity(hass, entity_id)

            try:
                await coordinator.client.async_create_playlist(
                    name=name,
                    media_type=media_type,
                    user_id=user_id,
                    item_ids=item_ids,
                )
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
        user_id: str = call.data[ATTR_USER_ID]

        # Validate IDs
        _validate_emby_id(playlist_id, "playlist_id")
        _validate_emby_id(user_id, "user_id")
        for item_id in item_ids:
            _validate_emby_id(item_id, "item_id")

        for entity_id in entity_ids:
            coordinator = _get_coordinator_for_entity(hass, entity_id)

            try:
                await coordinator.client.async_add_to_playlist(
                    playlist_id=playlist_id,
                    item_ids=item_ids,
                    user_id=user_id,
                )
            except EmbyConnectionError as err:
                raise HomeAssistantError(
                    f"Failed to add to playlist for {entity_id}: Connection error"
                ) from err
            except EmbyError as err:
                raise HomeAssistantError(
                    f"Failed to add to playlist for {entity_id}: {err}"
                ) from err

    async def async_remove_from_playlist(call: ServiceCall) -> None:
        """Remove items from a playlist."""
        entity_ids = _get_entity_ids_from_call(hass, call)
        playlist_id: str = call.data[ATTR_PLAYLIST_ID]
        playlist_item_ids: list[str] = call.data[ATTR_PLAYLIST_ITEM_IDS]

        # Validate playlist_id
        _validate_emby_id(playlist_id, "playlist_id")

        for entity_id in entity_ids:
            coordinator = _get_coordinator_for_entity(hass, entity_id)

            try:
                await coordinator.client.async_remove_from_playlist(
                    playlist_id=playlist_id,
                    playlist_item_ids=playlist_item_ids,
                )
            except EmbyConnectionError as err:
                raise HomeAssistantError(
                    f"Failed to remove from playlist for {entity_id}: Connection error"
                ) from err
            except EmbyError as err:
                raise HomeAssistantError(
                    f"Failed to remove from playlist for {entity_id}: {err}"
                ) from err

    # Collection services (Phase 19)
    async def async_create_collection(call: ServiceCall) -> None:
        """Create a new collection."""
        entity_ids = _get_entity_ids_from_call(hass, call)
        collection_name: str = call.data[ATTR_COLLECTION_NAME]
        item_ids: list[str] | None = call.data.get(ATTR_ITEM_IDS)

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

    async def async_remove_from_collection(call: ServiceCall) -> None:
        """Remove items from a collection."""
        entity_ids = _get_entity_ids_from_call(hass, call)
        collection_id: str = call.data[ATTR_COLLECTION_ID]
        item_ids: list[str] = call.data[ATTR_ITEM_IDS]

        # Validate collection_id
        _validate_emby_id(collection_id, "collection_id")
        for item_id in item_ids:
            _validate_emby_id(item_id, "item_id")

        for entity_id in entity_ids:
            coordinator = _get_coordinator_for_entity(hass, entity_id)

            try:
                await coordinator.client.async_remove_from_collection(
                    collection_id=collection_id,
                    item_ids=item_ids,
                )
            except EmbyConnectionError as err:
                raise HomeAssistantError(
                    f"Failed to remove from collection for {entity_id}: Connection error"
                ) from err
            except EmbyError as err:
                raise HomeAssistantError(
                    f"Failed to remove from collection for {entity_id}: {err}"
                ) from err

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_MESSAGE,
        async_send_message,
        schema=SEND_MESSAGE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_COMMAND,
        async_send_command,
        schema=SEND_COMMAND_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_MARK_PLAYED,
        async_mark_played,
        schema=ITEM_ACTION_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_MARK_UNPLAYED,
        async_mark_unplayed,
        schema=ITEM_ACTION_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_FAVORITE,
        async_add_favorite,
        schema=ITEM_ACTION_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_FAVORITE,
        async_remove_favorite,
        schema=ITEM_ACTION_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_LIBRARY,
        async_refresh_library,
        schema=REFRESH_LIBRARY_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_PLAY_INSTANT_MIX,
        async_play_instant_mix,
        schema=PLAY_MIX_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_PLAY_SIMILAR,
        async_play_similar,
        schema=PLAY_MIX_SCHEMA,
    )
    # Live TV services (Phase 16)
    hass.services.async_register(
        DOMAIN,
        SERVICE_SCHEDULE_RECORDING,
        async_schedule_recording,
        schema=SCHEDULE_RECORDING_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CANCEL_RECORDING,
        async_cancel_recording,
        schema=CANCEL_RECORDING_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CANCEL_SERIES_TIMER,
        async_cancel_series_timer,
        schema=CANCEL_SERIES_TIMER_SCHEMA,
    )
    # Playlist services (Phase 17)
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
    # Collection services (Phase 19)
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
    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_FROM_COLLECTION,
        async_remove_from_collection,
        schema=REMOVE_FROM_COLLECTION_SCHEMA,
    )

    _LOGGER.debug("Emby services registered")


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload Emby services.

    Args:
        hass: Home Assistant instance.
    """
    if not hass.services.has_service(DOMAIN, SERVICE_SEND_MESSAGE):
        return

    hass.services.async_remove(DOMAIN, SERVICE_SEND_MESSAGE)
    hass.services.async_remove(DOMAIN, SERVICE_SEND_COMMAND)
    hass.services.async_remove(DOMAIN, SERVICE_MARK_PLAYED)
    hass.services.async_remove(DOMAIN, SERVICE_MARK_UNPLAYED)
    hass.services.async_remove(DOMAIN, SERVICE_ADD_FAVORITE)
    hass.services.async_remove(DOMAIN, SERVICE_REMOVE_FAVORITE)
    hass.services.async_remove(DOMAIN, SERVICE_REFRESH_LIBRARY)
    hass.services.async_remove(DOMAIN, SERVICE_PLAY_INSTANT_MIX)
    hass.services.async_remove(DOMAIN, SERVICE_PLAY_SIMILAR)
    # Live TV services (Phase 16)
    hass.services.async_remove(DOMAIN, SERVICE_SCHEDULE_RECORDING)
    hass.services.async_remove(DOMAIN, SERVICE_CANCEL_RECORDING)
    hass.services.async_remove(DOMAIN, SERVICE_CANCEL_SERIES_TIMER)
    # Playlist services (Phase 17)
    hass.services.async_remove(DOMAIN, SERVICE_CREATE_PLAYLIST)
    hass.services.async_remove(DOMAIN, SERVICE_ADD_TO_PLAYLIST)
    hass.services.async_remove(DOMAIN, SERVICE_REMOVE_FROM_PLAYLIST)
    # Collection services (Phase 19)
    hass.services.async_remove(DOMAIN, SERVICE_CREATE_COLLECTION)
    hass.services.async_remove(DOMAIN, SERVICE_ADD_TO_COLLECTION)
    hass.services.async_remove(DOMAIN, SERVICE_REMOVE_FROM_COLLECTION)

    _LOGGER.debug("Emby services unregistered")


def _get_coordinator_for_entity(
    hass: HomeAssistant,
    entity_id: str,
) -> EmbyDataUpdateCoordinator:
    """Get coordinator for an entity.

    Args:
        hass: Home Assistant instance.
        entity_id: Entity ID to look up.

    Returns:
        The coordinator for this entity.

    Raises:
        HomeAssistantError: If entity not found or not an Emby entity.
    """
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(entity_id)

    if entry is None:
        raise HomeAssistantError(f"Entity {entity_id} not found")

    if entry.platform != DOMAIN:
        raise HomeAssistantError(f"Entity {entity_id} is not an Emby entity")

    config_entry_id = entry.config_entry_id
    if config_entry_id is None:
        raise HomeAssistantError(f"Entity {entity_id} has no config entry")

    config_entry = hass.config_entries.async_get_entry(config_entry_id)
    if config_entry is None:
        raise HomeAssistantError(f"Config entry {config_entry_id} not found")

    coordinator: EmbyDataUpdateCoordinator = config_entry.runtime_data.session_coordinator
    return coordinator


def _get_session_id_for_entity(
    hass: HomeAssistant,
    entity_id: str,
    coordinator: EmbyDataUpdateCoordinator,
) -> str | None:
    """Get session ID for an entity.

    Args:
        hass: Home Assistant instance.
        entity_id: Entity ID to look up.
        coordinator: The coordinator to use.

    Returns:
        Session ID if found, None otherwise.
    """
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(entity_id)

    if entry is None:
        return None

    # Get device_id from the entity's unique_id
    # Unique ID format is: {server_id}_{device_id}
    unique_id = entry.unique_id
    if unique_id is None:
        return None

    # Extract device_id by splitting on first underscore
    parts = unique_id.split("_", 1)
    if len(parts) < 2:
        return None
    device_id = parts[1]

    # Look up session by device_id
    if coordinator.data is None:
        return None

    session = coordinator.data.get(device_id)
    if session is not None:
        session_id: str = session.session_id
        return session_id

    return None


def _get_user_id_for_entity(
    hass: HomeAssistant,
    entity_id: str,
    coordinator: EmbyDataUpdateCoordinator,
) -> str | None:
    """Get user ID for an entity.

    Args:
        hass: Home Assistant instance.
        entity_id: Entity ID to look up.
        coordinator: The coordinator to use.

    Returns:
        User ID if found, None otherwise.
    """
    entity_registry = er.async_get(hass)
    entry = entity_registry.async_get(entity_id)

    if entry is None:
        return None

    # Get device_id from the entity's unique_id
    # Unique ID format is: {server_id}_{device_id}
    unique_id = entry.unique_id
    if unique_id is None:
        return None

    # Extract device_id by splitting on first underscore
    parts = unique_id.split("_", 1)
    if len(parts) < 2:
        return None
    device_id = parts[1]

    # Look up session to get user ID
    if coordinator.data is None:
        return None

    session = coordinator.data.get(device_id)
    if session is not None and session.user_id:
        user_id: str = session.user_id
        return user_id

    # Fallback to config entry user_id
    config_entry_id = entry.config_entry_id
    if config_entry_id:
        config_entry = hass.config_entries.async_get_entry(config_entry_id)
        if config_entry:
            user_id_from_config = config_entry.data.get("user_id")
            if isinstance(user_id_from_config, str):
                return user_id_from_config

    return None
