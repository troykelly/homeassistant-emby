"""Binary sensor platform for Emby integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator_sensors import EmbyServerCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .const import EmbyConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: EmbyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Emby binary sensors from a config entry.

    Args:
        hass: Home Assistant instance.
        config_entry: Config entry for the integration.
        async_add_entities: Callback to add entities.
    """
    runtime_data = config_entry.runtime_data
    server_coordinator: EmbyServerCoordinator = runtime_data.server_coordinator

    entities: list[BinarySensorEntity] = [
        EmbyServerConnectedBinarySensor(server_coordinator),
        EmbyPendingRestartBinarySensor(server_coordinator),
        EmbyUpdateAvailableBinarySensor(server_coordinator),
        EmbyLibraryScanActiveBinarySensor(server_coordinator),
        EmbyLiveTvEnabledBinarySensor(server_coordinator),
    ]

    async_add_entities(entities)


class EmbyServerBinarySensorBase(
    CoordinatorEntity[EmbyServerCoordinator],
    BinarySensorEntity,
):
    """Base class for Emby server binary sensors.

    Provides common functionality for all server-related binary sensors.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EmbyServerCoordinator,
    ) -> None:
        """Initialize the binary sensor.

        Args:
            coordinator: The server data coordinator.
        """
        super().__init__(coordinator)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information.

        Returns:
            DeviceInfo for the Emby server.
        """
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.server_id)},
            name=self.coordinator.server_name,
            manufacturer="Emby",
            model="Emby Server",
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available.

        Returns:
            True if coordinator has data.
        """
        return self.coordinator.last_update_success and self.coordinator.data is not None


class EmbyServerConnectedBinarySensor(EmbyServerBinarySensorBase):
    """Binary sensor for server connectivity status.

    Shows whether the Emby server is reachable.
    """

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "server_connected"

    def __init__(self, coordinator: EmbyServerCoordinator) -> None:
        """Initialize the sensor.

        Args:
            coordinator: The server data coordinator.
        """
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.server_id}_server_connected"

    @property
    def is_on(self) -> bool:
        """Return True if server is connected.

        Returns:
            True if last update was successful.
        """
        return bool(self.coordinator.last_update_success)


class EmbyPendingRestartBinarySensor(EmbyServerBinarySensorBase):
    """Binary sensor for server pending restart status.

    Shows whether the server needs to be restarted.
    """

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_translation_key = "pending_restart"

    def __init__(self, coordinator: EmbyServerCoordinator) -> None:
        """Initialize the sensor.

        Args:
            coordinator: The server data coordinator.
        """
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.server_id}_pending_restart"

    @property
    def is_on(self) -> bool | None:
        """Return True if restart is pending.

        Returns:
            True if server has pending restart, None if unknown.
        """
        if self.coordinator.data is None:
            return None
        return bool(self.coordinator.data.get("has_pending_restart", False))


class EmbyUpdateAvailableBinarySensor(EmbyServerBinarySensorBase):
    """Binary sensor for server update availability.

    Shows whether a server update is available.
    """

    _attr_device_class = BinarySensorDeviceClass.UPDATE
    _attr_translation_key = "update_available"

    def __init__(self, coordinator: EmbyServerCoordinator) -> None:
        """Initialize the sensor.

        Args:
            coordinator: The server data coordinator.
        """
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.server_id}_update_available"

    @property
    def is_on(self) -> bool | None:
        """Return True if update is available.

        Returns:
            True if server has update available, None if unknown.
        """
        if self.coordinator.data is None:
            return None
        return bool(self.coordinator.data.get("has_update_available", False))


class EmbyLibraryScanActiveBinarySensor(EmbyServerBinarySensorBase):
    """Binary sensor for library scan status.

    Shows whether a library scan is currently running.
    """

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_translation_key = "library_scan_active"

    def __init__(self, coordinator: EmbyServerCoordinator) -> None:
        """Initialize the sensor.

        Args:
            coordinator: The server data coordinator.
        """
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.server_id}_library_scan_active"

    @property
    def is_on(self) -> bool | None:
        """Return True if library scan is active.

        Returns:
            True if library scan is running, None if unknown.
        """
        if self.coordinator.data is None:
            return None
        return bool(self.coordinator.data.get("library_scan_active", False))

    @property
    def extra_state_attributes(self) -> dict[str, float] | None:
        """Return extra state attributes.

        Returns:
            Progress percentage if scan is active.
        """
        if self.coordinator.data is None:
            return None

        progress = self.coordinator.data.get("library_scan_progress")
        if progress is not None:
            return {"progress_percent": progress}
        return None


class EmbyLiveTvEnabledBinarySensor(EmbyServerBinarySensorBase):
    """Binary sensor for Live TV enabled status.

    Shows whether Live TV is enabled on the server.
    """

    _attr_translation_key = "live_tv_enabled"
    _attr_icon = "mdi:television-classic"

    def __init__(self, coordinator: EmbyServerCoordinator) -> None:
        """Initialize the sensor.

        Args:
            coordinator: The server data coordinator.
        """
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.server_id}_live_tv_enabled"

    @property
    def is_on(self) -> bool | None:
        """Return True if Live TV is enabled.

        Returns:
            True if Live TV is enabled, None if unknown.
        """
        if self.coordinator.data is None:
            return None
        return bool(self.coordinator.data.get("live_tv_enabled", False))

    @property
    def extra_state_attributes(self) -> dict[str, int] | None:
        """Return extra state attributes.

        Returns:
            Tuner count and active recordings if available.
        """
        if self.coordinator.data is None:
            return None

        attrs: dict[str, int] = {}
        tuner_count = self.coordinator.data.get("live_tv_tuner_count")
        if tuner_count is not None:
            attrs["tuner_count"] = tuner_count

        active_recordings = self.coordinator.data.get("live_tv_active_recordings")
        if active_recordings is not None:
            attrs["active_recordings"] = active_recordings

        return attrs if attrs else None


__all__ = [
    "EmbyLibraryScanActiveBinarySensor",
    "EmbyLiveTvEnabledBinarySensor",
    "EmbyPendingRestartBinarySensor",
    "EmbyServerConnectedBinarySensor",
    "EmbyUpdateAvailableBinarySensor",
    "async_setup_entry",
]
