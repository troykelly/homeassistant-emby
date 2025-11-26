"""Notify platform for Emby integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.notify import (
    NotifyEntity,
    NotifyEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_PREFIX_NOTIFY,
    DEFAULT_NOTIFICATION_TIMEOUT_MS,
    DEFAULT_PREFIX_NOTIFY,
    EmbyConfigEntry,
)
from .entity import EmbyEntity
from .exceptions import EmbyConnectionError, EmbyError

if TYPE_CHECKING:
    from .coordinator import EmbyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EmbyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Emby notify platform.

    Args:
        hass: Home Assistant instance.
        entry: Config entry.
        async_add_entities: Callback to add entities.
    """
    coordinator: EmbyDataUpdateCoordinator = entry.runtime_data
    known_devices: set[str] = set()

    @callback  # type: ignore[misc]
    def async_add_notify_entities() -> None:
        """Add notify entities for active sessions."""
        if coordinator.data is None:
            return

        new_entities: list[EmbyNotifyEntity] = []
        for device_id in coordinator.data:
            if device_id not in known_devices:
                _LOGGER.debug("Adding notify entity for device: %s", device_id)
                known_devices.add(device_id)
                new_entities.append(EmbyNotifyEntity(coordinator, device_id))

        if new_entities:
            async_add_entities(new_entities)

    # Add existing entities
    async_add_notify_entities()

    # Listen for new sessions
    entry.async_on_unload(coordinator.async_add_listener(async_add_notify_entities))


class EmbyNotifyEntity(EmbyEntity, NotifyEntity):  # type: ignore[misc]
    """Emby notification entity.

    Allows sending notifications to Emby clients via the standard
    Home Assistant notify service.
    """

    _attr_supported_features = NotifyEntityFeature.TITLE
    _attr_name: str | None = None  # Phase 11: Use device name only (no suffix)

    # Phase 11: Entity-specific prefix settings
    _prefix_key: str = CONF_PREFIX_NOTIFY
    _prefix_default: bool = DEFAULT_PREFIX_NOTIFY

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize notify entity.

        Args:
            coordinator: Data update coordinator.
            device_id: Emby device ID.
        """
        super().__init__(coordinator, device_id)

    @property
    def unique_id(self) -> str:
        """Return unique ID for the entity.

        Appends '_notify' to distinguish from media_player entity.
        """
        return f"{self.coordinator.server_id}_{self._device_id}_notify"

    async def async_send_message(
        self,
        message: str,
        title: str | None = None,
    ) -> None:
        """Send notification to Emby client.

        Args:
            message: Message text to display.
            title: Optional notification title/header.
        """
        # Use inherited session property from EmbyEntity
        current_session = self.session
        if current_session is None:
            _LOGGER.warning(
                "Cannot send notification - session not found for device %s",
                self._device_id,
            )
            return

        header = title or ""

        try:
            await self.coordinator.client.async_send_message(
                session_id=current_session.session_id,
                text=message,
                header=header,
                timeout_ms=DEFAULT_NOTIFICATION_TIMEOUT_MS,
            )
            _LOGGER.debug(
                "Sent notification to %s: %s",
                self._device_id,
                message[:50] + "..." if len(message) > 50 else message,
            )
        except EmbyConnectionError as err:
            _LOGGER.error(
                "Failed to send notification to %s (connection error): %s",
                self._device_id,
                err,
            )
        except EmbyError as err:
            _LOGGER.error(
                "Failed to send notification to %s: %s",
                self._device_id,
                err,
            )


__all__ = ["EmbyNotifyEntity", "async_setup_entry"]
