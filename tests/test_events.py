"""Tests for Home Assistant event firing (Phase 21)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
)

from custom_components.embymedia.const import (
    CONF_API_KEY,
    DOMAIN,
    EmbyLibraryChangedData,
    EmbyNotificationData,
    EmbyUserChangedData,
    EmbyUserDataChangedData,
    EmbyUserDataChangedItemData,
)

if TYPE_CHECKING:
    from custom_components.embymedia.const import EmbyConfigEntry


@pytest.fixture
def mock_emby_client() -> MagicMock:
    """Create a mock Emby API client."""
    client = MagicMock()
    client.async_get_sessions = AsyncMock(return_value=[])
    client.clear_browse_cache = MagicMock()
    client.host = "emby.local"
    client.port = 8096
    client.api_key = "test-api-key"
    client.ssl = False
    return client


@pytest.fixture
def mock_config_entry(hass: HomeAssistant) -> EmbyConfigEntry:
    """Create a mock config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "emby.local",
            "port": 8096,
            CONF_API_KEY: "test-api-key",
        },
        options={},
        unique_id="server-123",
    )
    entry.add_to_hass(hass)
    return entry  # type: ignore[return-value]


class TestWebSocketEventTypedDicts:
    """Test TypedDict structures for WebSocket events."""

    def test_library_changed_data_typeddict(self) -> None:
        """Test EmbyLibraryChangedData TypedDict structure."""
        data: EmbyLibraryChangedData = {
            "ItemsAdded": ["item1", "item2"],
            "ItemsUpdated": ["item3"],
            "ItemsRemoved": [],
            "FoldersAddedTo": ["lib1"],
            "FoldersRemovedFrom": [],
        }
        assert data["ItemsAdded"] == ["item1", "item2"]
        assert data["ItemsUpdated"] == ["item3"]
        assert data["ItemsRemoved"] == []
        assert data["FoldersAddedTo"] == ["lib1"]

    def test_library_changed_data_optional_fields(self) -> None:
        """Test EmbyLibraryChangedData with optional CollectionFolders."""
        data: EmbyLibraryChangedData = {
            "ItemsAdded": ["item1"],
            "ItemsUpdated": [],
            "ItemsRemoved": [],
            "FoldersAddedTo": [],
            "FoldersRemovedFrom": [],
            "CollectionFolders": ["collection1"],
        }
        assert data.get("CollectionFolders") == ["collection1"]

    def test_user_data_changed_item_typeddict(self) -> None:
        """Test EmbyUserDataChangedItemData TypedDict structure."""
        item_data: EmbyUserDataChangedItemData = {
            "ItemId": "item1",
            "UserId": "user1",
            "IsFavorite": True,
            "Played": False,
        }
        assert item_data["ItemId"] == "item1"
        assert item_data["UserId"] == "user1"
        assert item_data["IsFavorite"] is True
        assert item_data["Played"] is False

    def test_user_data_changed_item_all_fields(self) -> None:
        """Test EmbyUserDataChangedItemData with all optional fields."""
        item_data: EmbyUserDataChangedItemData = {
            "ItemId": "item1",
            "UserId": "user1",
            "IsFavorite": True,
            "Played": True,
            "PlaybackPositionTicks": 50000000,
            "PlayCount": 3,
            "Rating": 8.5,
            "LastPlayedDate": "2025-01-15T10:30:00Z",
        }
        assert item_data["PlaybackPositionTicks"] == 50000000
        assert item_data["PlayCount"] == 3
        assert item_data["Rating"] == 8.5
        assert item_data["LastPlayedDate"] == "2025-01-15T10:30:00Z"

    def test_user_data_changed_data_typeddict(self) -> None:
        """Test EmbyUserDataChangedData TypedDict structure."""
        data: EmbyUserDataChangedData = {
            "UserDataList": [
                {
                    "ItemId": "item1",
                    "UserId": "user1",
                    "IsFavorite": True,
                    "Played": False,
                }
            ]
        }
        assert len(data["UserDataList"]) == 1
        assert data["UserDataList"][0]["ItemId"] == "item1"

    def test_notification_data_typeddict(self) -> None:
        """Test EmbyNotificationData TypedDict structure."""
        data: EmbyNotificationData = {
            "Name": "Library Scan Complete",
            "Description": "The library scan completed successfully",
            "NotificationType": "Info",
            "Level": "Normal",
            "Date": "2025-01-15T10:30:00Z",
        }
        assert data["Name"] == "Library Scan Complete"
        assert data["Level"] == "Normal"
        assert data["NotificationType"] == "Info"

    def test_notification_data_with_url(self) -> None:
        """Test EmbyNotificationData with optional URL."""
        data: EmbyNotificationData = {
            "Name": "Update Available",
            "NotificationType": "Update",
            "Level": "Warning",
            "Date": "2025-01-15T10:30:00Z",
            "Url": "https://emby.media/download",
        }
        assert data.get("Url") == "https://emby.media/download"

    def test_user_changed_data_typeddict(self) -> None:
        """Test EmbyUserChangedData TypedDict structure."""
        data: EmbyUserChangedData = {
            "UserId": "user1",
        }
        assert data["UserId"] == "user1"

    def test_user_changed_data_with_username(self) -> None:
        """Test EmbyUserChangedData with optional UserName."""
        data: EmbyUserChangedData = {
            "UserId": "user1",
            "UserName": "John Doe",
        }
        assert data.get("UserName") == "John Doe"


class TestLibraryUpdatedEvent:
    """Test embymedia_library_updated event firing."""

    @pytest.mark.asyncio
    async def test_library_changed_fires_event(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: EmbyConfigEntry,
    ) -> None:
        """Test LibraryChanged WebSocket message fires HA event."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        # Create a mock runtime_data
        mock_library_coordinator = MagicMock()
        mock_library_coordinator.async_request_refresh = AsyncMock()
        mock_runtime_data = MagicMock()
        mock_runtime_data.library_coordinator = mock_library_coordinator
        mock_config_entry.runtime_data = mock_runtime_data

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        events = async_capture_events(hass, "embymedia_library_updated")

        # Simulate LibraryChanged WebSocket message
        coordinator._handle_websocket_message(
            "LibraryChanged",
            {
                "ItemsAdded": ["item1", "item2"],
                "ItemsUpdated": ["item3"],
                "ItemsRemoved": [],
                "FoldersAddedTo": ["lib1"],
                "FoldersRemovedFrom": [],
            },
        )

        await hass.async_block_till_done()

        assert len(events) == 1
        event = events[0]
        assert event.event_type == "embymedia_library_updated"
        assert event.data["server_id"] == "server-123"
        assert event.data["server_name"] == "Test Server"
        assert event.data["items_added"] == ["item1", "item2"]
        assert event.data["items_updated"] == ["item3"]
        assert event.data["items_removed"] == []
        assert event.data["folders_added_to"] == ["lib1"]
        assert event.data["folders_removed_from"] == []

    @pytest.mark.asyncio
    async def test_library_changed_clears_browse_cache(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: EmbyConfigEntry,
    ) -> None:
        """Test LibraryChanged clears browse cache."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_runtime_data = MagicMock()
        mock_runtime_data.library_coordinator = MagicMock()
        mock_config_entry.runtime_data = mock_runtime_data

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        coordinator._handle_websocket_message(
            "LibraryChanged",
            {"ItemsAdded": ["item1"]},
        )

        mock_emby_client.clear_browse_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_library_changed_with_empty_fields(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: EmbyConfigEntry,
    ) -> None:
        """Test LibraryChanged with missing fields defaults to empty lists."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_runtime_data = MagicMock()
        mock_runtime_data.library_coordinator = MagicMock()
        mock_config_entry.runtime_data = mock_runtime_data

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        events = async_capture_events(hass, "embymedia_library_updated")

        # Minimal data with only ItemsAdded
        coordinator._handle_websocket_message(
            "LibraryChanged",
            {"ItemsAdded": ["item1"]},
        )

        await hass.async_block_till_done()

        assert len(events) == 1
        event = events[0]
        assert event.data["items_added"] == ["item1"]
        assert event.data["items_updated"] == []
        assert event.data["items_removed"] == []

    @pytest.mark.asyncio
    async def test_library_changed_invalid_data_no_event(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: EmbyConfigEntry,
    ) -> None:
        """Test LibraryChanged with invalid data doesn't fire event."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_runtime_data = MagicMock()
        mock_runtime_data.library_coordinator = MagicMock()
        mock_config_entry.runtime_data = mock_runtime_data

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        events = async_capture_events(hass, "embymedia_library_updated")

        # Send invalid data (string instead of dict)
        coordinator._handle_websocket_message("LibraryChanged", "invalid")

        await hass.async_block_till_done()

        assert len(events) == 0


class TestUserDataChangedEvent:
    """Test embymedia_user_data_changed event firing."""

    @pytest.mark.asyncio
    async def test_user_data_changed_fires_event(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: EmbyConfigEntry,
    ) -> None:
        """Test UserDataChanged WebSocket message fires HA event."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_runtime_data = MagicMock()
        mock_config_entry.runtime_data = mock_runtime_data

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        events = async_capture_events(hass, "embymedia_user_data_changed")

        coordinator._handle_websocket_message(
            "UserDataChanged",
            {
                "UserDataList": [
                    {
                        "ItemId": "item1",
                        "UserId": "user1",
                        "IsFavorite": True,
                        "Played": False,
                    }
                ]
            },
        )

        await hass.async_block_till_done()

        assert len(events) == 1
        event = events[0]
        assert event.event_type == "embymedia_user_data_changed"
        assert event.data["server_id"] == "server-123"
        assert event.data["server_name"] == "Test Server"
        assert event.data["item_id"] == "item1"
        assert event.data["user_id"] == "user1"
        assert event.data["is_favorite"] is True
        assert event.data["played"] is False

    @pytest.mark.asyncio
    async def test_user_data_changed_multiple_items(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: EmbyConfigEntry,
    ) -> None:
        """Test UserDataChanged fires event for each item."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_runtime_data = MagicMock()
        mock_config_entry.runtime_data = mock_runtime_data

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        events = async_capture_events(hass, "embymedia_user_data_changed")

        coordinator._handle_websocket_message(
            "UserDataChanged",
            {
                "UserDataList": [
                    {"ItemId": "item1", "UserId": "user1", "IsFavorite": True},
                    {"ItemId": "item2", "UserId": "user1", "Played": True},
                ]
            },
        )

        await hass.async_block_till_done()

        assert len(events) == 2
        assert events[0].data["item_id"] == "item1"
        assert events[0].data["is_favorite"] is True
        assert events[1].data["item_id"] == "item2"
        assert events[1].data["played"] is True

    @pytest.mark.asyncio
    async def test_user_data_changed_all_fields(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: EmbyConfigEntry,
    ) -> None:
        """Test UserDataChanged includes all optional fields."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_runtime_data = MagicMock()
        mock_config_entry.runtime_data = mock_runtime_data

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        events = async_capture_events(hass, "embymedia_user_data_changed")

        coordinator._handle_websocket_message(
            "UserDataChanged",
            {
                "UserDataList": [
                    {
                        "ItemId": "item1",
                        "UserId": "user1",
                        "IsFavorite": True,
                        "Played": True,
                        "PlaybackPositionTicks": 50000000,
                        "PlayCount": 3,
                        "Rating": 8.5,
                        "LastPlayedDate": "2025-01-15T10:30:00Z",
                    }
                ]
            },
        )

        await hass.async_block_till_done()

        assert len(events) == 1
        event = events[0]
        assert event.data["playback_position_ticks"] == 50000000
        assert event.data["play_count"] == 3
        assert event.data["rating"] == 8.5
        assert event.data["last_played_date"] == "2025-01-15T10:30:00Z"

    @pytest.mark.asyncio
    async def test_user_data_changed_skips_missing_ids(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: EmbyConfigEntry,
    ) -> None:
        """Test UserDataChanged skips items with missing ItemId or UserId."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_runtime_data = MagicMock()
        mock_config_entry.runtime_data = mock_runtime_data

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        events = async_capture_events(hass, "embymedia_user_data_changed")

        coordinator._handle_websocket_message(
            "UserDataChanged",
            {
                "UserDataList": [
                    {"ItemId": "item1"},  # Missing UserId
                    {"UserId": "user1"},  # Missing ItemId
                    {"ItemId": "item3", "UserId": "user1"},  # Valid
                ]
            },
        )

        await hass.async_block_till_done()

        # Only the valid item should fire an event
        assert len(events) == 1
        assert events[0].data["item_id"] == "item3"

    @pytest.mark.asyncio
    async def test_user_data_changed_invalid_data_no_event(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: EmbyConfigEntry,
    ) -> None:
        """Test UserDataChanged with invalid data doesn't fire event."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_runtime_data = MagicMock()
        mock_config_entry.runtime_data = mock_runtime_data

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        events = async_capture_events(hass, "embymedia_user_data_changed")

        # Send invalid data (string instead of dict)
        coordinator._handle_websocket_message("UserDataChanged", "invalid")

        await hass.async_block_till_done()

        assert len(events) == 0


class TestNotificationEvent:
    """Test embymedia_notification event firing."""

    @pytest.mark.asyncio
    async def test_notification_fires_event(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: EmbyConfigEntry,
    ) -> None:
        """Test NotificationAdded WebSocket message fires HA event."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_runtime_data = MagicMock()
        mock_config_entry.runtime_data = mock_runtime_data

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        events = async_capture_events(hass, "embymedia_notification")

        coordinator._handle_websocket_message(
            "NotificationAdded",
            {
                "Name": "Library Scan Complete",
                "Description": "Scan completed successfully",
                "Level": "Normal",
                "NotificationType": "Info",
                "Date": "2025-01-15T10:30:00Z",
            },
        )

        await hass.async_block_till_done()

        assert len(events) == 1
        event = events[0]
        assert event.event_type == "embymedia_notification"
        assert event.data["server_id"] == "server-123"
        assert event.data["server_name"] == "Test Server"
        assert event.data["name"] == "Library Scan Complete"
        assert event.data["description"] == "Scan completed successfully"
        assert event.data["level"] == "Normal"
        assert event.data["notification_type"] == "Info"
        assert event.data["date"] == "2025-01-15T10:30:00Z"

    @pytest.mark.asyncio
    async def test_notification_with_url(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: EmbyConfigEntry,
    ) -> None:
        """Test NotificationAdded with URL field."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_runtime_data = MagicMock()
        mock_config_entry.runtime_data = mock_runtime_data

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        events = async_capture_events(hass, "embymedia_notification")

        coordinator._handle_websocket_message(
            "NotificationAdded",
            {
                "Name": "Update Available",
                "Level": "Warning",
                "NotificationType": "Update",
                "Date": "2025-01-15T10:30:00Z",
                "Url": "https://emby.media/download",
            },
        )

        await hass.async_block_till_done()

        assert len(events) == 1
        assert events[0].data["url"] == "https://emby.media/download"

    @pytest.mark.asyncio
    async def test_notification_invalid_data_no_event(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: EmbyConfigEntry,
    ) -> None:
        """Test NotificationAdded with invalid data doesn't fire event."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_runtime_data = MagicMock()
        mock_config_entry.runtime_data = mock_runtime_data

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        events = async_capture_events(hass, "embymedia_notification")

        # Send invalid data (string instead of dict)
        coordinator._handle_websocket_message("NotificationAdded", "invalid")

        await hass.async_block_till_done()

        assert len(events) == 0


class TestUserChangedEvent:
    """Test embymedia_user_changed event firing."""

    @pytest.mark.asyncio
    async def test_user_updated_fires_event(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: EmbyConfigEntry,
    ) -> None:
        """Test UserUpdated WebSocket message fires HA event."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_runtime_data = MagicMock()
        mock_config_entry.runtime_data = mock_runtime_data

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        events = async_capture_events(hass, "embymedia_user_changed")

        coordinator._handle_websocket_message(
            "UserUpdated",
            {
                "UserId": "user1",
                "UserName": "John Doe",
            },
        )

        await hass.async_block_till_done()

        assert len(events) == 1
        event = events[0]
        assert event.event_type == "embymedia_user_changed"
        assert event.data["server_id"] == "server-123"
        assert event.data["server_name"] == "Test Server"
        assert event.data["user_id"] == "user1"
        assert event.data["user_name"] == "John Doe"
        assert event.data["change_type"] == "updated"

    @pytest.mark.asyncio
    async def test_user_deleted_fires_event(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: EmbyConfigEntry,
    ) -> None:
        """Test UserDeleted WebSocket message fires HA event."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_runtime_data = MagicMock()
        mock_config_entry.runtime_data = mock_runtime_data

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        events = async_capture_events(hass, "embymedia_user_changed")

        coordinator._handle_websocket_message(
            "UserDeleted",
            {"UserId": "user1"},
        )

        await hass.async_block_till_done()

        assert len(events) == 1
        event = events[0]
        assert event.data["user_id"] == "user1"
        assert event.data["change_type"] == "deleted"
        assert event.data["user_name"] is None

    @pytest.mark.asyncio
    async def test_user_changed_missing_user_id_no_event(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: EmbyConfigEntry,
    ) -> None:
        """Test UserUpdated with missing UserId doesn't fire event."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_runtime_data = MagicMock()
        mock_config_entry.runtime_data = mock_runtime_data

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        events = async_capture_events(hass, "embymedia_user_changed")

        # Send data without UserId
        coordinator._handle_websocket_message("UserUpdated", {"UserName": "John Doe"})

        await hass.async_block_till_done()

        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_user_changed_invalid_data_no_event(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: EmbyConfigEntry,
    ) -> None:
        """Test UserUpdated with invalid data doesn't fire event."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_runtime_data = MagicMock()
        mock_config_entry.runtime_data = mock_runtime_data

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        events = async_capture_events(hass, "embymedia_user_changed")

        # Send invalid data (string instead of dict)
        coordinator._handle_websocket_message("UserUpdated", "invalid")

        await hass.async_block_till_done()

        assert len(events) == 0


class TestLibraryCoordinatorRefresh:
    """Test library coordinator refresh triggering."""

    @pytest.mark.asyncio
    async def test_library_changed_schedules_refresh(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: EmbyConfigEntry,
    ) -> None:
        """Test LibraryChanged schedules library coordinator refresh."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_library_coordinator = MagicMock()
        mock_library_coordinator.async_request_refresh = AsyncMock()
        mock_runtime_data = MagicMock()
        mock_runtime_data.library_coordinator = mock_library_coordinator
        mock_config_entry.runtime_data = mock_runtime_data

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        coordinator._handle_websocket_message(
            "LibraryChanged",
            {"ItemsAdded": ["item1"]},
        )

        # Wait for debounce (5 seconds) + buffer
        import asyncio

        await asyncio.sleep(6)
        await hass.async_block_till_done()

        # Library coordinator should be refreshed
        mock_library_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_library_changed_no_library_coordinator(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: EmbyConfigEntry,
    ) -> None:
        """Test LibraryChanged handles missing library coordinator gracefully."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        # No runtime_data set
        mock_config_entry.runtime_data = None

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        events = async_capture_events(hass, "embymedia_library_updated")

        # Should not raise, event should still fire
        coordinator._handle_websocket_message(
            "LibraryChanged",
            {"ItemsAdded": ["item1"]},
        )

        await hass.async_block_till_done()

        assert len(events) == 1
