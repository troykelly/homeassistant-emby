"""Remote platform for Emby integration.

This module provides a RemoteEntity for controlling Emby media clients.
It allows sending navigation and control commands to Emby clients through
the standard Home Assistant remote platform.

Supported Commands:
    Navigation:
        - MoveUp, MoveDown, MoveLeft, MoveRight
        - PageUp, PageDown
        - PreviousLetter, NextLetter

    Selection & Menu:
        - Select - Confirm selection
        - Back - Go back
        - GoHome - Navigate to home screen
        - GoToSettings - Navigate to settings
        - ToggleContextMenu - Show/hide info menu
        - ToggleOsdMenu - Show/hide video OSD

    Playback Control:
        - VolumeUp, VolumeDown
        - Mute, Unmute, ToggleMute
        - SetVolume (requires 'volume' in kwargs, 0-100)
        - SetAudioStreamIndex (requires 'index' in kwargs)
        - SetSubtitleStreamIndex (requires 'index' in kwargs)

    Other:
        - TakeScreenshot
        - SendString (requires 'string' in kwargs)

Example Usage:
    # Single command
    await hass.services.async_call(
        "remote", "send_command",
        {"entity_id": "remote.living_room_tv_remote", "command": "GoHome"}
    )

    # Multiple commands
    await hass.services.async_call(
        "remote", "send_command",
        {"entity_id": "remote.living_room_tv_remote",
         "command": ["MoveDown", "MoveDown", "Select"]}
    )

    # Command with repeats
    await hass.services.async_call(
        "remote", "send_command",
        {"entity_id": "remote.living_room_tv_remote",
         "command": "VolumeUp", "num_repeats": 5}
    )
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from typing import TYPE_CHECKING

from homeassistant.components.remote import RemoteEntity, RemoteEntityFeature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_PREFIX_REMOTE, DEFAULT_PREFIX_REMOTE, EmbyConfigEntry
from .entity import EmbyEntity
from .exceptions import EmbyError

if TYPE_CHECKING:
    from .coordinator import EmbyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EmbyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Emby remote platform.

    Creates a RemoteEntity for each active Emby client session. New entities
    are automatically created when new sessions are discovered by the
    coordinator.

    Args:
        hass: Home Assistant instance.
        entry: Config entry containing the coordinator.
        async_add_entities: Callback to add entities to Home Assistant.
    """
    coordinator: EmbyDataUpdateCoordinator = entry.runtime_data.session_coordinator
    known_devices: set[str] = set()

    @callback
    def async_add_remote_entities() -> None:
        """Add remote entities for active sessions."""
        if coordinator.data is None:
            return

        new_entities: list[EmbyRemoteEntity] = []
        for device_id in coordinator.data:
            if device_id not in known_devices:
                _LOGGER.debug("Adding remote entity for device: %s", device_id)
                known_devices.add(device_id)
                new_entities.append(EmbyRemoteEntity(coordinator, device_id))

        if new_entities:
            async_add_entities(new_entities)

    # Add existing entities
    async_add_remote_entities()

    # Listen for new sessions
    entry.async_on_unload(coordinator.async_add_listener(async_add_remote_entities))


class EmbyRemoteEntity(EmbyEntity, RemoteEntity):
    """Remote entity for controlling Emby media clients.

    This entity allows sending navigation and control commands to Emby
    clients using the standard Home Assistant remote platform services.

    The remote is considered "on" when the associated session is active.
    Turn on/off operations are no-ops since Emby clients don't support
    power control through the API.

    Attributes:
        _attr_name: Entity name suffix ("Remote").
        _attr_supported_features: No special features (basic command sending).
    """

    _attr_name: str | None = None  # Phase 11: Use device name only (no suffix)
    _attr_supported_features = RemoteEntityFeature(0)

    # Phase 11: Entity-specific prefix settings
    _prefix_key: str = CONF_PREFIX_REMOTE
    _prefix_default: bool = DEFAULT_PREFIX_REMOTE

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize remote entity.

        Args:
            coordinator: Data update coordinator managing Emby sessions.
            device_id: Emby device ID for this remote.
        """
        super().__init__(coordinator, device_id)

    @property
    def unique_id(self) -> str:
        """Return unique ID for the entity.

        Appends '_remote' to distinguish from other entity types
        (media_player, notify) for the same device.

        Returns:
            Unique identifier string.
        """
        return f"{self.coordinator.server_id}_{self._device_id}_remote"

    @property
    def is_on(self) -> bool:
        """Return True if remote is available (session exists).

        The remote is considered "on" when the Emby session is active.
        This doesn't represent actual power state since Emby clients
        don't have power control.

        Returns:
            True if session exists, False otherwise.
        """
        return self.session is not None

    async def async_turn_on(self, activity: str | None = None, **kwargs: object) -> None:
        """Turn on the remote (no-op).

        Emby clients don't support power control through the API.
        This method exists for API compatibility but performs no action.

        Args:
            activity: Ignored - activities not supported.
            **kwargs: Ignored - additional arguments not used.
        """
        _LOGGER.debug(
            "Turn on requested for %s (no-op - Emby doesn't support power control)",
            self._device_id,
        )

    async def async_turn_off(self, activity: str | None = None, **kwargs: object) -> None:
        """Turn off the remote (no-op).

        Emby clients don't support power control through the API.
        This method exists for API compatibility but performs no action.

        Args:
            activity: Ignored - activities not supported.
            **kwargs: Ignored - additional arguments not used.
        """
        _LOGGER.debug(
            "Turn off requested for %s (no-op - Emby doesn't support power control)",
            self._device_id,
        )

    async def async_send_command(self, command: Iterable[str], **kwargs: object) -> None:
        """Send command(s) to the Emby client.

        Sends one or more remote control commands to the Emby session.
        Commands are sent sequentially with optional delay between them.

        Args:
            command: Single command or iterable of commands to send.
                Supported commands include: GoHome, Back, Select,
                MoveUp, MoveDown, MoveLeft, MoveRight, VolumeUp,
                VolumeDown, Mute, ToggleMute, etc.
            **kwargs: Additional options:
                - num_repeats (int): Number of times to repeat each command.
                - delay_secs (float): Delay between commands in seconds.

        Example:
            # Send single command
            await entity.async_send_command(["GoHome"])

            # Send multiple commands with delay
            await entity.async_send_command(
                ["MoveDown", "Select"],
                delay_secs=0.5
            )

            # Repeat command multiple times
            await entity.async_send_command(["VolumeUp"], num_repeats=5)
        """
        current_session = self.session
        if current_session is None:
            _LOGGER.warning(
                "Cannot send command - session not found for device %s",
                self._device_id,
            )
            return

        # Extract optional parameters with type-safe defaults
        num_repeats_val = kwargs.get("num_repeats", 1)
        delay_secs_val = kwargs.get("delay_secs", 0)
        # Type-safe conversions for values from HA service schema
        num_repeats: int = (
            int(num_repeats_val) if isinstance(num_repeats_val, int | float | str) else 1
        )
        delay_secs: float = (
            float(delay_secs_val) if isinstance(delay_secs_val, int | float | str) else 0.0
        )

        commands = list(command)
        for _ in range(num_repeats):
            for idx, cmd in enumerate(commands):
                try:
                    await self.coordinator.client.async_send_command(
                        session_id=current_session.session_id,
                        command=cmd,
                        args=None,
                    )
                    _LOGGER.debug(
                        "Sent command '%s' to %s",
                        cmd,
                        self._device_id,
                    )
                except (EmbyError, OSError) as err:
                    _LOGGER.error(
                        "Failed to send command '%s' to %s: %s",
                        cmd,
                        self._device_id,
                        err,
                    )

                # Add delay between commands (but not after the last one)
                if delay_secs > 0 and idx < len(commands) - 1:
                    await asyncio.sleep(delay_secs)


__all__ = ["EmbyRemoteEntity", "async_setup_entry"]
