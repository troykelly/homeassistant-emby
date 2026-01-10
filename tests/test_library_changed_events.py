"""Tests for LibraryChanged event-driven updates.

These tests verify that Issue #289 is correctly implemented:
- LibraryChanged events trigger library coordinator refresh (already exists)
- Polling interval extended when WebSocket is active
- Fallback to normal polling if WebSocket disconnects
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_emby_client() -> MagicMock:
    """Create mock Emby client."""
    client = MagicMock()
    client.async_get_item_counts = AsyncMock(
        return_value={
            "MovieCount": 100,
            "SeriesCount": 20,
            "EpisodeCount": 500,
            "AlbumCount": 50,
            "SongCount": 1000,
        }
    )
    client.async_get_virtual_folders = AsyncMock(return_value=[])
    client.async_get_artist_count = AsyncMock(return_value=30)
    client.async_get_boxset_count = AsyncMock(return_value=10)
    return client


@pytest.fixture
def mock_config_entry() -> MagicMock:
    """Create mock config entry."""
    entry = MagicMock()
    entry.options = {}
    return entry


class TestLibraryCoordinatorWebSocketIntegration:
    """Test library coordinator WebSocket-aware polling."""

    def test_library_coordinator_has_websocket_aware_interval(
        self, hass: HomeAssistant, mock_emby_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test that library coordinator can adjust interval based on WebSocket status."""
        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator

        coordinator = EmbyLibraryCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="test-server",
            config_entry=mock_config_entry,
        )

        # Should have method to set WebSocket-aware mode
        assert hasattr(coordinator, "set_websocket_active")
        assert callable(coordinator.set_websocket_active)

    def test_default_polling_interval_is_one_hour(
        self, hass: HomeAssistant, mock_emby_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test that default polling interval is 1 hour."""
        from custom_components.embymedia.const import DEFAULT_LIBRARY_SCAN_INTERVAL
        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator

        coordinator = EmbyLibraryCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="test-server",
            config_entry=mock_config_entry,
        )

        # Default should be 1 hour (3600 seconds)
        assert DEFAULT_LIBRARY_SCAN_INTERVAL == 3600
        assert coordinator.update_interval == timedelta(seconds=3600)

    def test_extended_polling_when_websocket_active(
        self, hass: HomeAssistant, mock_emby_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test polling interval is extended when WebSocket is active."""
        from custom_components.embymedia.coordinator_sensors import (
            WEBSOCKET_LIBRARY_SCAN_INTERVAL,
            EmbyLibraryCoordinator,
        )

        coordinator = EmbyLibraryCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="test-server",
            config_entry=mock_config_entry,
        )

        # Activate WebSocket mode
        coordinator.set_websocket_active(active=True)

        # Should use extended interval (6 hours = 21600 seconds)
        assert WEBSOCKET_LIBRARY_SCAN_INTERVAL >= 21600
        assert coordinator.update_interval == timedelta(seconds=WEBSOCKET_LIBRARY_SCAN_INTERVAL)

    def test_normal_polling_when_websocket_inactive(
        self, hass: HomeAssistant, mock_emby_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test polling interval returns to normal when WebSocket is inactive."""
        from custom_components.embymedia.const import DEFAULT_LIBRARY_SCAN_INTERVAL
        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator

        coordinator = EmbyLibraryCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="test-server",
            config_entry=mock_config_entry,
        )

        # Activate then deactivate WebSocket mode
        coordinator.set_websocket_active(active=True)
        coordinator.set_websocket_active(active=False)

        # Should return to normal interval (1 hour)
        assert coordinator.update_interval == timedelta(seconds=DEFAULT_LIBRARY_SCAN_INTERVAL)


class TestLibraryChangedEventHandling:
    """Test LibraryChanged event triggers refresh."""

    def test_library_changed_triggers_refresh(self, hass: HomeAssistant) -> None:
        """Test that LibraryChanged event triggers library coordinator refresh.

        Note: This is already implemented but we verify it works correctly.
        """
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_client = MagicMock()
        mock_client.async_get_sessions = AsyncMock(return_value=[])
        mock_client.async_get_server_info = AsyncMock(return_value={"Id": "test"})
        mock_client.clear_browse_cache = MagicMock()
        mock_client.host = "emby.local"
        mock_client.port = 8096
        mock_client.api_key = "test"
        mock_client.ssl = False

        mock_config_entry = MagicMock()
        mock_config_entry.options = {}

        # Create mock library coordinator
        mock_library_coordinator = MagicMock()
        mock_library_coordinator.async_request_refresh = AsyncMock()

        # Set up runtime_data with library_coordinator
        mock_runtime_data = MagicMock()
        mock_runtime_data.library_coordinator = mock_library_coordinator
        mock_config_entry.runtime_data = mock_runtime_data

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Simulate LibraryChanged message
        coordinator._handle_websocket_message(
            "LibraryChanged",
            {
                "ItemsAdded": ["item1"],
                "ItemsUpdated": [],
                "ItemsRemoved": [],
            },
        )

        # The handler creates a background task with 5s delay
        # We verify the cache was cleared (synchronous part)
        mock_client.clear_browse_cache.assert_called_once()


class TestWebSocketLibraryScanIntervalConstant:
    """Test WebSocket library scan interval constant."""

    def test_websocket_library_scan_interval_defined(self) -> None:
        """Test that WEBSOCKET_LIBRARY_SCAN_INTERVAL constant is defined."""
        from custom_components.embymedia.coordinator_sensors import (
            WEBSOCKET_LIBRARY_SCAN_INTERVAL,
        )

        # Should be 6 hours (21600 seconds) or more
        assert WEBSOCKET_LIBRARY_SCAN_INTERVAL >= 21600
        # Should be reasonable (not more than 24 hours)
        assert WEBSOCKET_LIBRARY_SCAN_INTERVAL <= 86400


class TestWebSocketActiveProperty:
    """Test WebSocket active tracking property."""

    def test_websocket_active_property(
        self, hass: HomeAssistant, mock_emby_client: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test websocket_active property exists and is readable."""
        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator

        coordinator = EmbyLibraryCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="test-server",
            config_entry=mock_config_entry,
        )

        # Property should exist and default to False
        assert hasattr(coordinator, "websocket_active")
        assert coordinator.websocket_active is False

        # Should reflect state after setting
        coordinator.set_websocket_active(active=True)
        assert coordinator.websocket_active is True


class TestMainCoordinatorNotifiesLibraryCoordinator:
    """Test that main coordinator notifies library coordinator of WebSocket status."""

    def test_websocket_connection_notifies_library_coordinator(self, hass: HomeAssistant) -> None:
        """Test that WebSocket connection updates library coordinator status."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_client = MagicMock()
        mock_client.async_get_sessions = AsyncMock(return_value=[])
        mock_client.async_get_server_info = AsyncMock(return_value={"Id": "test"})
        mock_client.host = "emby.local"
        mock_client.port = 8096
        mock_client.api_key = "test"
        mock_client.ssl = False

        mock_config_entry = MagicMock()
        mock_config_entry.options = {}

        # Create mock library coordinator
        mock_library_coordinator = MagicMock()
        mock_library_coordinator.set_websocket_active = MagicMock()

        # Set up runtime_data with library_coordinator
        mock_runtime_data = MagicMock()
        mock_runtime_data.library_coordinator = mock_library_coordinator
        mock_config_entry.runtime_data = mock_runtime_data

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Simulate WebSocket connection
        coordinator._handle_websocket_connection(connected=True)

        # Library coordinator should be notified
        mock_library_coordinator.set_websocket_active.assert_called_once_with(active=True)

    def test_websocket_disconnection_notifies_library_coordinator(
        self, hass: HomeAssistant
    ) -> None:
        """Test that WebSocket disconnection updates library coordinator status."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_client = MagicMock()
        mock_client.async_get_sessions = AsyncMock(return_value=[])
        mock_client.async_get_server_info = AsyncMock(return_value={"Id": "test"})
        mock_client.host = "emby.local"
        mock_client.port = 8096
        mock_client.api_key = "test"
        mock_client.ssl = False

        mock_config_entry = MagicMock()
        mock_config_entry.options = {}

        # Create mock library coordinator
        mock_library_coordinator = MagicMock()
        mock_library_coordinator.set_websocket_active = MagicMock()

        # Set up runtime_data with library_coordinator
        mock_runtime_data = MagicMock()
        mock_runtime_data.library_coordinator = mock_library_coordinator
        mock_config_entry.runtime_data = mock_runtime_data

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Simulate WebSocket disconnection
        coordinator._handle_websocket_connection(connected=False)

        # Library coordinator should be notified of disconnection
        mock_library_coordinator.set_websocket_active.assert_called_once_with(active=False)

    def test_no_error_when_library_coordinator_not_available(self, hass: HomeAssistant) -> None:
        """Test that no error occurs if library coordinator is not available."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_client = MagicMock()
        mock_client.async_get_sessions = AsyncMock(return_value=[])
        mock_client.async_get_server_info = AsyncMock(return_value={"Id": "test"})
        mock_client.host = "emby.local"
        mock_client.port = 8096
        mock_client.api_key = "test"
        mock_client.ssl = False

        mock_config_entry = MagicMock()
        mock_config_entry.options = {}
        # No runtime_data set

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Should not raise an error
        coordinator._handle_websocket_connection(connected=True)
        coordinator._handle_websocket_connection(connected=False)
