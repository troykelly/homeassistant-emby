"""Base entity for Emby integration."""
from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

if TYPE_CHECKING:
    from .coordinator import EmbyDataUpdateCoordinator
    from .models import EmbySession


class EmbyEntity(CoordinatorEntity["EmbyDataUpdateCoordinator"]):
    """Base class for Emby entities.

    Provides common functionality including:
    - Device info generation
    - Unique ID management
    - Availability based on session presence
    - Session data access

    Attributes:
        _device_id: The stable device identifier.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the entity.

        Args:
            coordinator: The data update coordinator.
            device_id: The stable device identifier for this entity.
        """
        super().__init__(coordinator)
        self._device_id = device_id

    @property
    def session(self) -> EmbySession | None:
        """Return the current session data.

        Returns:
            The session if available, None otherwise.
        """
        return self.coordinator.get_session(self._device_id)

    @property
    def available(self) -> bool:
        """Return True if entity is available.

        Entity is available when:
        - Coordinator has data
        - Session exists in coordinator data
        """
        return self.coordinator.last_update_success and self.session is not None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information.

        Returns:
            DeviceInfo for device registry.
        """
        session = self.session
        if session is None:
            # Fallback device info when session not available
            return DeviceInfo(
                identifiers={(DOMAIN, self._device_id)},
                name=f"Emby Client {self._device_id[:8]}",
                manufacturer="Emby",
                via_device=(DOMAIN, self.coordinator.server_id),
            )

        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=session.device_name,
            manufacturer="Emby",
            model=session.client_name,
            sw_version=session.app_version,
            via_device=(DOMAIN, self.coordinator.server_id),
        )

    @property
    def unique_id(self) -> str:
        """Return unique ID for the entity.

        Uses device_id which persists across session reconnections.
        """
        return f"{self.coordinator.server_id}_{self._device_id}"


__all__ = ["EmbyEntity"]
