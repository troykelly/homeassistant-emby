"""Button platform for Emby integration.

This module provides ButtonEntity implementations for server-level actions
that can be triggered via the Home Assistant button platform.

Available Buttons:
    Refresh Library:
        Triggers a full library scan on the Emby server.
        This refreshes metadata for all libraries.

Example Usage in Automations:
    # Trigger library refresh via automation
    automation:
      - alias: "Nightly Library Refresh"
        trigger:
          - platform: time
            at: "03:00:00"
        action:
          - service: button.press
            target:
              entity_id: button.emby_server_refresh_library

    # Trigger via service call
    service: button.press
    target:
      entity_id: button.emby_server_refresh_library
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, EmbyConfigEntry

if TYPE_CHECKING:
    from .coordinator import EmbyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EmbyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Emby button platform.

    Creates button entities for server-level actions like library refresh.

    Args:
        hass: Home Assistant instance.
        entry: Config entry containing the coordinator.
        async_add_entities: Callback to add entities to Home Assistant.
    """
    coordinator: EmbyDataUpdateCoordinator = entry.runtime_data

    entities: list[ButtonEntity] = [
        EmbyRefreshLibraryButton(coordinator),
    ]

    async_add_entities(entities)


class EmbyRefreshLibraryButton(CoordinatorEntity["EmbyDataUpdateCoordinator"], ButtonEntity):  # type: ignore[misc]
    """Button to trigger library refresh on Emby server.

    When pressed, this button triggers a full library scan on the Emby
    server. This is useful for refreshing metadata after adding new
    media files or making changes to the library structure.

    Attributes:
        _attr_name: Entity name ("Refresh Library").
        _attr_device_class: IDENTIFY class for action buttons.
        _attr_has_entity_name: Uses device name as prefix.
    """

    _attr_name = "Refresh Library"
    _attr_device_class = ButtonDeviceClass.IDENTIFY
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EmbyDataUpdateCoordinator,
    ) -> None:
        """Initialize the refresh library button.

        Args:
            coordinator: Data update coordinator for the Emby server.
        """
        super().__init__(coordinator)

    @property
    def unique_id(self) -> str:
        """Return unique ID for the entity.

        Returns:
            Unique identifier string based on server ID.
        """
        return f"{self.coordinator.server_id}_refresh_library"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the Emby server.

        Links this button to the main Emby server device.

        Returns:
            DeviceInfo for device registry.
        """
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.server_id)},
            name=self.coordinator.server_name,
            manufacturer="Emby",
        )

    async def async_press(self) -> None:
        """Handle button press - trigger library refresh.

        Calls the Emby API to start a full library scan.
        Errors are logged but not raised to avoid interrupting
        automation flows.
        """
        try:
            await self.coordinator.client.async_refresh_library(library_id=None)
            _LOGGER.info(
                "Library refresh triggered on %s",
                self.coordinator.server_name,
            )
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error(
                "Failed to trigger library refresh on %s: %s",
                self.coordinator.server_name,
                err,
            )


__all__ = ["EmbyRefreshLibraryButton", "async_setup_entry"]
