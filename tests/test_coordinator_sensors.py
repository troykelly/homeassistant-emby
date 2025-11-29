"""Tests for Phase 12 sensor coordinators."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.embymedia.const import (
    CONF_API_KEY,
    CONF_VERIFY_SSL,
    DEFAULT_LIBRARY_SCAN_INTERVAL,
    DEFAULT_SERVER_SCAN_INTERVAL,
    DOMAIN,
    EmbyScheduledTask,
    EmbyVirtualFolder,
)

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test Emby Server",
        data={
            CONF_HOST: "emby.local",
            CONF_PORT: 8096,
            CONF_SSL: False,
            CONF_API_KEY: "test-api-key-12345",
            CONF_VERIFY_SSL: True,
        },
        unique_id="test-server-id-12345",
        version=1,
    )


@pytest.fixture
def mock_emby_client() -> MagicMock:
    """Create a mock EmbyClient."""
    client = MagicMock()
    client.async_get_server_info = AsyncMock(
        return_value={
            "Id": "test-server-id",
            "ServerName": "Test Server",
            "Version": "4.9.2.0",
            "HasPendingRestart": False,
            "HasUpdateAvailable": False,
        }
    )
    client.async_get_item_counts = AsyncMock(
        return_value={
            "MovieCount": 100,
            "SeriesCount": 50,
            "EpisodeCount": 500,
            "ArtistCount": 25,
            "AlbumCount": 75,
            "SongCount": 1000,
            "GameCount": 0,
            "GameSystemCount": 0,
            "TrailerCount": 5,
            "MusicVideoCount": 10,
            "BoxSetCount": 5,
            "BookCount": 20,
            "ItemCount": 1790,
        }
    )
    client.async_get_scheduled_tasks = AsyncMock(return_value=[])
    client.async_get_virtual_folders = AsyncMock(
        return_value=[
            {
                "Name": "Movies",
                "ItemId": "lib-movies",
                "CollectionType": "movies",
                "Locations": ["/media/movies"],
            }
        ]
    )
    # Live TV info (Phase 16)
    client.async_get_live_tv_info = AsyncMock(
        return_value={
            "IsEnabled": True,
            "EnabledUsers": ["user-1", "user-2"],
            "TunerCount": 2,
            "ActiveRecordingCount": 0,
        }
    )
    client.async_get_timers = AsyncMock(return_value=[])
    client.async_get_series_timers = AsyncMock(return_value=[])
    client.async_get_recordings = AsyncMock(return_value=[])
    return client


class TestEmbyServerCoordinator:
    """Tests for EmbyServerCoordinator."""

    async def test_coordinator_creation(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test EmbyServerCoordinator can be created."""
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator

        coordinator = EmbyServerCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        assert coordinator.server_id == "test-server-id"
        assert coordinator.server_name == "Test Server"
        assert coordinator.update_interval == timedelta(seconds=DEFAULT_SERVER_SCAN_INTERVAL)

    async def test_coordinator_fetch_server_info(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test EmbyServerCoordinator fetches server info."""
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator

        coordinator = EmbyServerCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        await coordinator.async_refresh()

        assert coordinator.data is not None
        assert coordinator.data["server_version"] == "4.9.2.0"
        assert coordinator.data["has_pending_restart"] is False
        assert coordinator.data["has_update_available"] is False

    async def test_coordinator_fetch_scheduled_tasks(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test EmbyServerCoordinator fetches scheduled tasks."""
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator

        mock_tasks: list[EmbyScheduledTask] = [
            {
                "Name": "Scan media library",
                "State": "Running",
                "Id": "task-1",
                "Description": "Scans library",
                "Category": "Library",
                "IsHidden": False,
                "Key": "RefreshLibrary",
                "Triggers": [],
                "CurrentProgressPercentage": 45.5,
            },
        ]
        mock_emby_client.async_get_scheduled_tasks.return_value = mock_tasks

        coordinator = EmbyServerCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        await coordinator.async_refresh()

        assert coordinator.data is not None
        assert coordinator.data["scheduled_tasks"] == mock_tasks
        assert coordinator.data["running_tasks_count"] == 1
        assert coordinator.data["library_scan_active"] is True
        assert coordinator.data["library_scan_progress"] == 45.5


class TestEmbyLibraryCoordinator:
    """Tests for EmbyLibraryCoordinator."""

    async def test_coordinator_creation(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test EmbyLibraryCoordinator can be created."""
        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator

        coordinator = EmbyLibraryCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="test-server-id",
            config_entry=mock_config_entry,
        )

        assert coordinator.server_id == "test-server-id"
        assert coordinator.update_interval == timedelta(seconds=DEFAULT_LIBRARY_SCAN_INTERVAL)

    async def test_coordinator_fetch_item_counts(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test EmbyLibraryCoordinator fetches item counts."""
        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator

        coordinator = EmbyLibraryCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="test-server-id",
            config_entry=mock_config_entry,
        )

        await coordinator.async_refresh()

        assert coordinator.data is not None
        assert coordinator.data["movie_count"] == 100
        assert coordinator.data["series_count"] == 50
        assert coordinator.data["episode_count"] == 500
        assert coordinator.data["song_count"] == 1000

    async def test_coordinator_fetch_virtual_folders(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test EmbyLibraryCoordinator fetches virtual folders."""
        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator

        mock_folders: list[EmbyVirtualFolder] = [
            {
                "Name": "Movies",
                "ItemId": "lib-movies",
                "CollectionType": "movies",
                "Locations": ["/media/movies"],
            },
            {
                "Name": "TV Shows",
                "ItemId": "lib-tv",
                "CollectionType": "tvshows",
                "Locations": ["/media/tv"],
            },
        ]
        mock_emby_client.async_get_virtual_folders.return_value = mock_folders

        coordinator = EmbyLibraryCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="test-server-id",
            config_entry=mock_config_entry,
        )

        await coordinator.async_refresh()

        assert coordinator.data is not None
        assert coordinator.data["virtual_folders"] == mock_folders
        assert len(coordinator.data["virtual_folders"]) == 2

    async def test_coordinator_with_user_id(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test EmbyLibraryCoordinator with user ID fetches user counts."""
        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator

        mock_emby_client.async_get_user_item_count = AsyncMock(side_effect=[42, 500, 8])
        # Phase 17: Add playlist mock
        mock_emby_client.async_get_playlists = AsyncMock(return_value=[])
        # Phase 19: Add collection mock
        mock_emby_client.async_get_collections = AsyncMock(return_value=[])

        coordinator = EmbyLibraryCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="test-server-id",
            config_entry=mock_config_entry,
            user_id="user-123",
        )

        await coordinator.async_refresh()

        assert coordinator.data is not None
        assert coordinator.data["user_favorites_count"] == 42
        assert coordinator.data["user_played_count"] == 500
        assert coordinator.data["user_resumable_count"] == 8
        assert coordinator.data["playlist_count"] == 0
        assert coordinator.data["collection_count"] == 0

    async def test_coordinator_without_user_id(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test EmbyLibraryCoordinator without user ID doesn't fetch user counts."""
        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator

        coordinator = EmbyLibraryCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="test-server-id",
            config_entry=mock_config_entry,
            user_id=None,
        )

        await coordinator.async_refresh()

        assert coordinator.data is not None
        # User counts should not be present when no user_id
        assert "user_favorites_count" not in coordinator.data
        assert "user_played_count" not in coordinator.data
        assert "user_resumable_count" not in coordinator.data

    async def test_coordinator_user_id_property(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test EmbyLibraryCoordinator user_id property returns correct value."""
        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator

        coordinator = EmbyLibraryCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="test-server-id",
            config_entry=mock_config_entry,
            user_id="test-user-id",
        )

        assert coordinator.user_id == "test-user-id"


class TestCoordinatorErrorHandling:
    """Tests for coordinator error handling."""

    async def test_server_coordinator_connection_error(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test EmbyServerCoordinator handles connection errors."""
        from homeassistant.helpers.update_coordinator import UpdateFailed

        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator
        from custom_components.embymedia.exceptions import EmbyConnectionError

        mock_emby_client.async_get_server_info = AsyncMock(
            side_effect=EmbyConnectionError("Connection refused")
        )

        coordinator = EmbyServerCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        with pytest.raises(UpdateFailed, match="Failed to connect"):
            await coordinator._async_update_data()

    async def test_server_coordinator_emby_error(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test EmbyServerCoordinator handles generic Emby errors."""
        from homeassistant.helpers.update_coordinator import UpdateFailed

        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator
        from custom_components.embymedia.exceptions import EmbyError

        mock_emby_client.async_get_server_info = AsyncMock(side_effect=EmbyError("API error"))

        coordinator = EmbyServerCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        with pytest.raises(UpdateFailed, match="Error fetching server data"):
            await coordinator._async_update_data()

    async def test_library_coordinator_connection_error(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test EmbyLibraryCoordinator handles connection errors."""
        from homeassistant.helpers.update_coordinator import UpdateFailed

        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator
        from custom_components.embymedia.exceptions import EmbyConnectionError

        mock_emby_client.async_get_item_counts = AsyncMock(
            side_effect=EmbyConnectionError("Connection refused")
        )

        coordinator = EmbyLibraryCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="test-server-id",
            config_entry=mock_config_entry,
        )

        with pytest.raises(UpdateFailed, match="Failed to connect"):
            await coordinator._async_update_data()

    async def test_library_coordinator_emby_error(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test EmbyLibraryCoordinator handles generic Emby errors."""
        from homeassistant.helpers.update_coordinator import UpdateFailed

        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator
        from custom_components.embymedia.exceptions import EmbyError

        mock_emby_client.async_get_item_counts = AsyncMock(side_effect=EmbyError("API error"))

        coordinator = EmbyLibraryCoordinator(
            hass=hass,
            client=mock_emby_client,
            server_id="test-server-id",
            config_entry=mock_config_entry,
        )

        with pytest.raises(UpdateFailed, match="Error fetching library data"):
            await coordinator._async_update_data()


class TestCoordinatorParallelExecution:
    """Test that coordinators use asyncio.gather for parallel API calls."""

    async def test_server_coordinator_parallel_api_calls(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test that ServerCoordinator API calls run in parallel.

        The server coordinator makes independent API calls that should run in parallel.
        If they ran sequentially at 50ms each, it would take ~250ms.
        In parallel, they should complete in ~50ms (plus overhead).
        """
        import asyncio
        import time

        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator

        delay_seconds = 0.05  # 50ms per call

        async def slow_server_info(*args: object, **kwargs: object) -> dict[str, object]:
            await asyncio.sleep(delay_seconds)
            return {
                "Id": "test",
                "ServerName": "Test",
                "Version": "1.0.0",
                "HasPendingRestart": False,
                "HasUpdateAvailable": False,
            }

        async def slow_tasks(*args: object, **kwargs: object) -> list[object]:
            await asyncio.sleep(delay_seconds)
            return []

        async def slow_live_tv(*args: object, **kwargs: object) -> dict[str, object]:
            await asyncio.sleep(delay_seconds)
            return {"IsEnabled": False}

        async def slow_activity(*args: object, **kwargs: object) -> dict[str, object]:
            await asyncio.sleep(delay_seconds)
            return {"Items": [], "TotalRecordCount": 0}

        async def slow_devices(*args: object, **kwargs: object) -> dict[str, object]:
            await asyncio.sleep(delay_seconds)
            return {"Items": []}

        async def slow_plugins(*args: object, **kwargs: object) -> list[object]:
            await asyncio.sleep(delay_seconds)
            return []

        mock_client = MagicMock()
        mock_client.async_get_server_info = AsyncMock(side_effect=slow_server_info)
        mock_client.async_get_scheduled_tasks = AsyncMock(side_effect=slow_tasks)
        mock_client.async_get_live_tv_info = AsyncMock(side_effect=slow_live_tv)
        mock_client.async_get_activity_log = AsyncMock(side_effect=slow_activity)
        mock_client.async_get_devices = AsyncMock(side_effect=slow_devices)
        mock_client.async_get_plugins = AsyncMock(side_effect=slow_plugins)

        coordinator = EmbyServerCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        start = time.time()
        await coordinator._async_update_data()
        elapsed = time.time() - start

        # 6 calls at 50ms each:
        # Sequential: 300ms minimum
        # Parallel: ~50ms (plus overhead)
        assert elapsed < 0.2, (
            f"API calls took {elapsed:.3f}s - should be < 0.2s if running in parallel"
        )

    async def test_library_coordinator_parallel_api_calls(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test that LibraryCoordinator API calls run in parallel.

        The library coordinator makes independent API calls that should run in parallel.
        With a user_id, it makes 7 calls total. Sequential would take 350ms at 50ms each.
        """
        import asyncio
        import time

        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator

        delay_seconds = 0.05  # 50ms per call

        async def slow_counts(*args: object, **kwargs: object) -> dict[str, int]:
            await asyncio.sleep(delay_seconds)
            return {
                "MovieCount": 100,
                "SeriesCount": 50,
                "EpisodeCount": 500,
                "ArtistCount": 25,
                "AlbumCount": 75,
                "SongCount": 1000,
            }

        async def slow_folders(*args: object, **kwargs: object) -> list[object]:
            await asyncio.sleep(delay_seconds)
            return []

        async def slow_user_count(*args: object, **kwargs: object) -> int:
            await asyncio.sleep(delay_seconds)
            return 0

        async def slow_playlists(*args: object, **kwargs: object) -> list[object]:
            await asyncio.sleep(delay_seconds)
            return []

        async def slow_collections(*args: object, **kwargs: object) -> list[object]:
            await asyncio.sleep(delay_seconds)
            return []

        mock_client = MagicMock()
        mock_client.async_get_item_counts = AsyncMock(side_effect=slow_counts)
        mock_client.async_get_virtual_folders = AsyncMock(side_effect=slow_folders)
        mock_client.async_get_user_item_count = AsyncMock(side_effect=slow_user_count)
        mock_client.async_get_playlists = AsyncMock(side_effect=slow_playlists)
        mock_client.async_get_collections = AsyncMock(side_effect=slow_collections)

        coordinator = EmbyLibraryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server-id",
            config_entry=mock_config_entry,
            user_id="test-user-id",
        )

        start = time.time()
        await coordinator._async_update_data()
        elapsed = time.time() - start

        # 7 calls at 50ms each (counts, folders, 3x user_count, playlists, collections):
        # Sequential: 350ms minimum
        # Parallel: ~50ms (plus overhead)
        assert elapsed < 0.2, (
            f"API calls took {elapsed:.3f}s - should be < 0.2s if running in parallel"
        )

    async def test_server_coordinator_scheduled_tasks_error_handling(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test server coordinator handles scheduled tasks API errors gracefully."""
        from custom_components.embymedia.coordinator_sensors import (
            EmbyServerCoordinator,
        )
        from custom_components.embymedia.exceptions import EmbyError

        mock_client = MagicMock()
        mock_client.async_get_server_info = AsyncMock(
            return_value={
                "ServerName": "Test",
                "Version": "4.9.0",
                "Id": "test-id",
                "LocalAddress": "http://localhost:8096",
                "WanAddress": "",
                "OperatingSystem": "Linux",
                "CanLaunchWebBrowser": False,
                "HasUpdateAvailable": False,
                "HasPendingRestart": False,
            }
        )
        mock_client.async_get_scheduled_tasks = AsyncMock(side_effect=EmbyError("API error"))
        mock_client.async_get_live_tv_info = AsyncMock(return_value={"IsEnabled": False})
        mock_client.async_get_activity_log = AsyncMock(
            return_value={"Items": [], "TotalRecordCount": 0}
        )
        mock_client.async_get_devices = AsyncMock(return_value={"Items": []})
        mock_client.async_get_plugins = AsyncMock(return_value=[])

        coordinator = EmbyServerCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Should not raise - error is handled gracefully
        data = await coordinator._async_update_data()
        assert data is not None
        # Scheduled tasks should be empty due to error
        assert data.get("scheduled_tasks") == []

    async def test_server_coordinator_live_tv_error_handling(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test server coordinator handles Live TV API errors gracefully."""
        from custom_components.embymedia.coordinator_sensors import (
            EmbyServerCoordinator,
        )
        from custom_components.embymedia.exceptions import EmbyError

        mock_client = MagicMock()
        mock_client.async_get_server_info = AsyncMock(
            return_value={
                "ServerName": "Test",
                "Version": "4.9.0",
                "Id": "test-id",
                "LocalAddress": "http://localhost:8096",
                "WanAddress": "",
                "OperatingSystem": "Linux",
                "CanLaunchWebBrowser": False,
                "HasUpdateAvailable": False,
                "HasPendingRestart": False,
            }
        )
        mock_client.async_get_scheduled_tasks = AsyncMock(return_value=[])
        mock_client.async_get_live_tv_info = AsyncMock(side_effect=EmbyError("Live TV error"))
        mock_client.async_get_activity_log = AsyncMock(
            return_value={"Items": [], "TotalRecordCount": 0}
        )
        mock_client.async_get_devices = AsyncMock(return_value={"Items": []})
        mock_client.async_get_plugins = AsyncMock(return_value=[])

        coordinator = EmbyServerCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Should not raise - error is handled gracefully
        data = await coordinator._async_update_data()
        assert data is not None
        # Live TV should show as disabled due to error
        assert data.get("live_tv_enabled") is False

    async def test_server_coordinator_timers_error_handling(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test server coordinator handles timer API errors gracefully."""
        from custom_components.embymedia.coordinator_sensors import (
            EmbyServerCoordinator,
        )
        from custom_components.embymedia.exceptions import EmbyError

        mock_client = MagicMock()
        mock_client.async_get_server_info = AsyncMock(
            return_value={
                "ServerName": "Test",
                "Version": "4.9.0",
                "Id": "test-id",
                "LocalAddress": "http://localhost:8096",
                "WanAddress": "",
                "OperatingSystem": "Linux",
                "CanLaunchWebBrowser": False,
                "HasUpdateAvailable": False,
                "HasPendingRestart": False,
            }
        )
        mock_client.async_get_scheduled_tasks = AsyncMock(return_value=[])
        # Live TV is enabled but timer API fails
        mock_client.async_get_live_tv_info = AsyncMock(
            return_value={"IsEnabled": True, "EnabledUsers": ["user-1"]}
        )
        # Timer fetch fails
        mock_client.async_get_timers = AsyncMock(side_effect=EmbyError("Timer error"))
        mock_client.async_get_series_timers = AsyncMock(return_value=[])
        mock_client.async_get_recordings = AsyncMock(return_value=[])
        mock_client.async_get_activity_log = AsyncMock(
            return_value={"Items": [], "TotalRecordCount": 0}
        )
        mock_client.async_get_devices = AsyncMock(return_value={"Items": []})
        mock_client.async_get_plugins = AsyncMock(return_value=[])

        coordinator = EmbyServerCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server-id",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Should not raise - error is handled gracefully
        data = await coordinator._async_update_data()
        assert data is not None
        # Live TV should still show as enabled
        assert data.get("live_tv_enabled") is True
        # Timer counts should be 0 due to error
        assert data.get("scheduled_timer_count") == 0
        assert data.get("series_timer_count") == 0
