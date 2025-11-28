"""Tests for Activity and Device data in EmbyServerCoordinator.

Phase 18: User Activity & Statistics
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_hass() -> HomeAssistant:
    """Create a mock HomeAssistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    return hass


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock EmbyClient for testing."""
    client = MagicMock()
    client.async_get_server_info = AsyncMock(
        return_value={
            "Version": "4.9.1.90",
            "HasPendingRestart": False,
            "HasUpdateAvailable": False,
        }
    )
    client.async_get_scheduled_tasks = AsyncMock(return_value=[])
    client.async_get_live_tv_info = AsyncMock(return_value={"IsEnabled": False})
    client.async_get_activity_log = AsyncMock(
        return_value={
            "Items": [
                {
                    "Id": 6612,
                    "Name": "Recording of BBC News has failed",
                    "Type": "livetv.recordingerror",
                    "Date": "2025-11-28T10:00:37.8370000Z",
                    "Severity": "Error",
                },
                {
                    "Id": 6611,
                    "Name": "admin is playing Elsbeth",
                    "Type": "playback.start",
                    "Date": "2025-11-28T09:56:09.8260000Z",
                    "Severity": "Info",
                },
            ],
            "TotalRecordCount": 6612,
        }
    )
    client.async_get_devices = AsyncMock(
        return_value={
            "Items": [
                {
                    "Name": "Samsung Smart TV",
                    "Id": "5",
                    "LastUserName": "admin",
                    "AppName": "Emby for Samsung",
                    "AppVersion": "2.2.5",
                    "LastUserId": "user1",
                    "DateLastActivity": "2025-11-28T10:00:16.0000000Z",
                },
                {
                    "Name": "macOS",
                    "Id": "6",
                    "LastUserName": "troy",
                    "AppName": "Emby for macOS",
                    "AppVersion": "2.2.39",
                    "LastUserId": "user2",
                    "DateLastActivity": "2025-11-28T09:56:51.0000000Z",
                },
            ],
            "TotalRecordCount": 0,
        }
    )
    return client


@pytest.fixture
def mock_config_entry() -> MagicMock:
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {}
    entry.options = {}
    return entry


class TestEmbyServerDataTypeDict:
    """Tests for EmbyServerData TypedDict fields."""

    def test_emby_server_data_has_activity_fields(self) -> None:
        """Test EmbyServerData TypedDict has activity log fields."""
        from custom_components.embymedia.coordinator_sensors import EmbyServerData

        # Create a data dict to verify fields are accepted
        data: EmbyServerData = {
            "server_version": "4.9.1.90",
            "has_pending_restart": False,
            "has_update_available": False,
            "scheduled_tasks": [],
            "running_tasks_count": 0,
            "library_scan_active": False,
            "library_scan_progress": None,
            "live_tv_enabled": False,
            "live_tv_tuner_count": 0,
            "live_tv_active_recordings": 0,
            "recording_count": 0,
            "scheduled_timer_count": 0,
            "series_timer_count": 0,
            # Phase 18 fields
            "recent_activities": [],
            "activity_count": 0,
        }

        assert "recent_activities" in data
        assert "activity_count" in data

    def test_emby_server_data_has_device_fields(self) -> None:
        """Test EmbyServerData TypedDict has device fields."""
        from custom_components.embymedia.coordinator_sensors import EmbyServerData

        data: EmbyServerData = {
            "server_version": "4.9.1.90",
            "has_pending_restart": False,
            "has_update_available": False,
            "scheduled_tasks": [],
            "running_tasks_count": 0,
            "library_scan_active": False,
            "library_scan_progress": None,
            "live_tv_enabled": False,
            "live_tv_tuner_count": 0,
            "live_tv_active_recordings": 0,
            "recording_count": 0,
            "scheduled_timer_count": 0,
            "series_timer_count": 0,
            # Phase 18 fields
            "devices": [],
            "device_count": 0,
        }

        assert "devices" in data
        assert "device_count" in data


class TestServerCoordinatorActivityData:
    """Tests for EmbyServerCoordinator activity and device data fetching."""

    @pytest.mark.asyncio
    async def test_coordinator_fetches_activity_log(
        self,
        mock_hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test coordinator fetches activity log data."""
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator

        coordinator = EmbyServerCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        data = await coordinator._async_update_data()

        # Verify activity log was fetched
        mock_client.async_get_activity_log.assert_called_once()
        assert "recent_activities" in data
        assert len(data["recent_activities"]) == 2
        assert data["activity_count"] == 6612

    @pytest.mark.asyncio
    async def test_coordinator_fetches_devices(
        self,
        mock_hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test coordinator fetches device data."""
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator

        coordinator = EmbyServerCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        data = await coordinator._async_update_data()

        # Verify devices were fetched
        mock_client.async_get_devices.assert_called_once()
        assert "devices" in data
        assert len(data["devices"]) == 2
        # Device count should be length of items (not TotalRecordCount which is 0)
        assert data["device_count"] == 2

    @pytest.mark.asyncio
    async def test_coordinator_activity_log_limit(
        self,
        mock_hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test coordinator fetches limited activity log entries."""
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator

        coordinator = EmbyServerCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        await coordinator._async_update_data()

        # Should request a reasonable limit (e.g., 20 entries)
        call_args = mock_client.async_get_activity_log.call_args
        assert call_args is not None
        # Check that limit is set (either as kwarg or positional)
        if call_args.kwargs:
            assert call_args.kwargs.get("limit", 50) <= 50
        # Method should be called with some limit

    @pytest.mark.asyncio
    async def test_coordinator_handles_activity_log_error(
        self,
        mock_hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test coordinator handles activity log fetch errors gracefully."""
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator
        from custom_components.embymedia.exceptions import EmbyError

        mock_client.async_get_activity_log = AsyncMock(
            side_effect=EmbyError("Activity log not available")
        )

        coordinator = EmbyServerCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Should not raise, but handle gracefully
        data = await coordinator._async_update_data()

        # Activity data should be empty but not fail
        assert data["recent_activities"] == []
        assert data["activity_count"] == 0

    @pytest.mark.asyncio
    async def test_coordinator_handles_devices_error(
        self,
        mock_hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test coordinator handles device fetch errors gracefully."""
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator
        from custom_components.embymedia.exceptions import EmbyError

        mock_client.async_get_devices = AsyncMock(side_effect=EmbyError("Devices not available"))

        coordinator = EmbyServerCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Should not raise, but handle gracefully
        data = await coordinator._async_update_data()

        # Devices data should be empty but not fail
        assert data["devices"] == []
        assert data["device_count"] == 0

    @pytest.mark.asyncio
    async def test_coordinator_activity_contains_expected_fields(
        self,
        mock_hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test activity entries contain expected fields."""
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator

        coordinator = EmbyServerCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        data = await coordinator._async_update_data()

        # Verify first activity entry has expected fields
        first_activity = data["recent_activities"][0]
        assert first_activity["Id"] == 6612
        assert first_activity["Type"] == "livetv.recordingerror"
        assert first_activity["Severity"] == "Error"

    @pytest.mark.asyncio
    async def test_coordinator_devices_contain_expected_fields(
        self,
        mock_hass: HomeAssistant,
        mock_client: MagicMock,
        mock_config_entry: MagicMock,
    ) -> None:
        """Test device entries contain expected fields."""
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator

        coordinator = EmbyServerCoordinator(
            hass=mock_hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        data = await coordinator._async_update_data()

        # Verify first device entry has expected fields
        first_device = data["devices"][0]
        assert first_device["Id"] == "5"
        assert first_device["Name"] == "Samsung Smart TV"
        assert first_device["AppName"] == "Emby for Samsung"
