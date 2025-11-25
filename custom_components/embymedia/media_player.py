"""Media player platform for Emby integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import EmbyEntity

if TYPE_CHECKING:
    from .const import EmbyConfigEntry
    from .coordinator import EmbyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EmbyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Emby media player from config entry.

    Args:
        hass: Home Assistant instance.
        entry: Config entry being set up.
        async_add_entities: Callback to add entities.
    """
    coordinator: EmbyDataUpdateCoordinator = entry.runtime_data
    _LOGGER.debug("Setting up Emby media player platform")

    # Track which entities we've created
    known_devices: set[str] = set()

    @callback  # type: ignore[misc]
    def async_add_new_entities() -> None:
        """Add entities for new sessions."""
        if coordinator.data is None:
            return

        new_entities: list[EmbyMediaPlayer] = []
        for device_id in coordinator.data:
            if device_id not in known_devices:
                _LOGGER.debug("Adding media player for device: %s", device_id)
                known_devices.add(device_id)
                new_entities.append(EmbyMediaPlayer(coordinator, device_id))

        if new_entities:
            async_add_entities(new_entities)

    # Add entities for existing sessions
    async_add_new_entities()

    # Listen for coordinator updates to add new entities
    entry.async_on_unload(coordinator.async_add_listener(async_add_new_entities))


class EmbyMediaPlayer(EmbyEntity, MediaPlayerEntity):  # type: ignore[misc]
    """Representation of an Emby media player.

    This entity represents a single Emby client session that can
    play media. Full playback control is implemented in Phase 3.
    """

    _attr_name = None  # Use device name

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the media player.

        Args:
            coordinator: The data update coordinator.
            device_id: The stable device identifier.
        """
        super().__init__(coordinator, device_id)

    @property
    def state(self) -> MediaPlayerState:
        """Return the state of the player.

        Returns:
            Current player state.
        """
        session = self.session
        if session is None:
            return MediaPlayerState.OFF

        if not session.is_playing:
            return MediaPlayerState.IDLE

        if session.play_state and session.play_state.is_paused:
            return MediaPlayerState.PAUSED

        return MediaPlayerState.PLAYING

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Return the supported features.

        Features are dynamically determined based on session capabilities.

        Returns:
            Bitmask of supported features.
        """
        session = self.session
        if session is None:
            return MediaPlayerEntityFeature(0)

        if not session.supports_remote_control:
            return MediaPlayerEntityFeature(0)

        features = (
            MediaPlayerEntityFeature.PAUSE
            | MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.STOP
            | MediaPlayerEntityFeature.NEXT_TRACK
            | MediaPlayerEntityFeature.PREVIOUS_TRACK
            | MediaPlayerEntityFeature.PLAY_MEDIA
        )

        # Volume control if supported
        if "SetVolume" in session.supported_commands:
            features |= MediaPlayerEntityFeature.VOLUME_SET
        if "Mute" in session.supported_commands:
            features |= MediaPlayerEntityFeature.VOLUME_MUTE

        # Seek if playback supports it
        if session.play_state and session.play_state.can_seek:
            features |= MediaPlayerEntityFeature.SEEK

        return features


__all__ = ["EmbyMediaPlayer", "async_setup_entry"]
