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

from .const import (
    CONF_PREFIX_BUTTON,
    DEFAULT_PREFIX_BUTTON,
    DOMAIN,
    EmbyConfigEntry,
    EmbyScheduledTask,
)

if TYPE_CHECKING:
    from .coordinator import EmbyDataUpdateCoordinator
    from .coordinator_sensors import EmbyServerCoordinator

# Limit concurrent button presses to prevent overwhelming the Emby server
# Value of 1 means only one press action at a time per entity
# This is required for Home Assistant Integration Quality Scale Silver tier
PARALLEL_UPDATES = 1

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
    coordinator: EmbyDataUpdateCoordinator = entry.runtime_data.session_coordinator
    server_coordinator: EmbyServerCoordinator = entry.runtime_data.server_coordinator

    entities: list[ButtonEntity] = [
        EmbyRefreshLibraryButton(coordinator),
        EmbyRunLibraryScanButton(server_coordinator),
    ]

    async_add_entities(entities)


class EmbyRefreshLibraryButton(CoordinatorEntity["EmbyDataUpdateCoordinator"], ButtonEntity):
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
    def suggested_object_id(self) -> str | None:
        """Return suggested object ID for entity ID generation.

        This ensures the entity ID includes the 'Emby' prefix when the option
        is enabled, matching the device name.

        Returns:
            Suggested object ID string (e.g., "emby_server_refresh_library").
        """
        use_prefix: bool = self.coordinator.config_entry.options.get(
            CONF_PREFIX_BUTTON, DEFAULT_PREFIX_BUTTON
        )
        server_name = self.coordinator.server_name
        device_name = f"Emby {server_name}" if use_prefix else server_name
        # Include the entity name suffix for the full object ID
        return f"{device_name} Refresh Library"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the Emby server.

        Links this button to the main Emby server device.
        Note: We don't set the device name here as it's already set
        in __init__.py when the server device is first registered.

        Returns:
            DeviceInfo for device registry.
        """
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.server_id)},
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


class EmbyRunLibraryScanButton(CoordinatorEntity["EmbyServerCoordinator"], ButtonEntity):
    """Button to trigger library scan scheduled task.

    This button finds the library scan scheduled task and triggers it
    to run immediately. This is different from refresh_library which
    uses a different API endpoint.

    Attributes:
        _attr_name: Entity name ("Run Library Scan").
        _attr_device_class: IDENTIFY class for action buttons.
        _attr_has_entity_name: Uses device name as prefix.
    """

    _attr_name = "Run Library Scan"
    _attr_device_class = ButtonDeviceClass.IDENTIFY
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EmbyServerCoordinator,
    ) -> None:
        """Initialize the run library scan button.

        Args:
            coordinator: Server data update coordinator.
        """
        super().__init__(coordinator)

    @property
    def unique_id(self) -> str:
        """Return unique ID for the entity.

        Returns:
            Unique identifier string based on server ID.
        """
        return f"{self.coordinator.server_id}_run_library_scan"

    @property
    def suggested_object_id(self) -> str | None:
        """Return suggested object ID for entity ID generation.

        This ensures the entity ID includes the 'Emby' prefix when the option
        is enabled, matching the device name.

        Returns:
            Suggested object ID string (e.g., "emby_server_run_library_scan").
        """
        use_prefix: bool = self.coordinator.config_entry.options.get(
            CONF_PREFIX_BUTTON, DEFAULT_PREFIX_BUTTON
        )
        server_name = self.coordinator.server_name
        device_name = f"Emby {server_name}" if use_prefix else server_name
        return f"{device_name} Run Library Scan"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the Emby server.

        Links this button to the main Emby server device.
        Note: We don't set the device name here as it's already set
        in __init__.py when the server device is first registered.

        Returns:
            DeviceInfo for device registry.
        """
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.server_id)},
            manufacturer="Emby",
        )

    async def async_press(self) -> None:
        """Handle button press - trigger library scan task.

        Finds the library scan scheduled task and triggers it to run
        immediately. Errors are logged but not raised to avoid
        interrupting automation flows.
        """
        try:
            # Get scheduled tasks to find library scan task ID
            tasks: list[
                EmbyScheduledTask
            ] = await self.coordinator.client.async_get_scheduled_tasks()

            # Find library scan task (search by key)
            library_scan_task: EmbyScheduledTask | None = None
            for task in tasks:
                if task.get("Key") == "RefreshLibrary":
                    library_scan_task = task
                    break

            if library_scan_task is None:
                _LOGGER.error(
                    "Library scan scheduled task not found on %s",
                    self.coordinator.server_name,
                )
                return

            task_id = library_scan_task["Id"]
            await self.coordinator.client.async_run_scheduled_task(task_id=task_id)

            _LOGGER.info(
                "Library scan triggered on %s",
                self.coordinator.server_name,
            )
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error(
                "Failed to trigger library scan on %s: %s",
                self.coordinator.server_name,
                err,
            )


__all__ = ["EmbyRefreshLibraryButton", "EmbyRunLibraryScanButton", "async_setup_entry"]
