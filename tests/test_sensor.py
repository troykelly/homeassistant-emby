"""Tests for Phase 12 sensor platform."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from homeassistant.components.sensor import SensorStateClass
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.embymedia.const import (
    CONF_API_KEY,
    CONF_VERIFY_SSL,
    DOMAIN,
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
def mock_server_data() -> dict[str, object]:
    """Create mock server coordinator data."""
    return {
        "server_version": "4.9.2.0",
        "has_pending_restart": False,
        "has_update_available": False,
        "scheduled_tasks": [],
        "running_tasks_count": 0,
        "library_scan_active": False,
        "library_scan_progress": None,
    }


@pytest.fixture
def mock_library_data() -> dict[str, object]:
    """Create mock library coordinator data."""
    return {
        "movie_count": 1209,
        "series_count": 374,
        "episode_count": 4620,
        "artist_count": 500,
        "album_count": 800,
        "song_count": 14341,
        "virtual_folders": [
            {
                "Name": "Movies",
                "ItemId": "lib-movies",
                "CollectionType": "movies",
                "Locations": ["/media/movies"],
            }
        ],
    }


class TestEmbyVersionSensor:
    """Tests for server version sensor."""

    async def test_sensor_creation(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_data: dict[str, object],
    ) -> None:
        """Test server version sensor is created."""
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator
        from custom_components.embymedia.sensor import EmbyVersionSensor

        mock_coordinator = MagicMock(spec=EmbyServerCoordinator)
        mock_coordinator.data = mock_server_data
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyVersionSensor(coordinator=mock_coordinator)

        assert sensor.unique_id == "test-server-id_server_version"
        assert sensor.native_value == "4.9.2.0"
        assert sensor.entity_category is not None  # Should be DIAGNOSTIC


class TestEmbyActiveSessionsSensor:
    """Tests for active sessions sensor."""

    async def test_sensor_no_sessions(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_data: dict[str, object],
    ) -> None:
        """Test active sessions sensor with no sessions."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator
        from custom_components.embymedia.sensor import EmbyActiveSessionsSensor

        mock_coordinator = MagicMock(spec=EmbyDataUpdateCoordinator)
        mock_coordinator.data = {}  # No sessions
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyActiveSessionsSensor(coordinator=mock_coordinator)

        assert sensor.unique_id == "test-server-id_active_sessions"
        assert sensor.native_value == 0
        assert sensor.state_class == SensorStateClass.MEASUREMENT

    async def test_sensor_with_sessions(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test active sessions sensor with active sessions."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator
        from custom_components.embymedia.sensor import EmbyActiveSessionsSensor

        mock_coordinator = MagicMock(spec=EmbyDataUpdateCoordinator)
        mock_coordinator.data = {
            "device-1": MagicMock(),
            "device-2": MagicMock(),
            "device-3": MagicMock(),
        }
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyActiveSessionsSensor(coordinator=mock_coordinator)

        assert sensor.native_value == 3


class TestEmbyRunningTasksSensor:
    """Tests for running tasks sensor."""

    async def test_sensor_no_tasks(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_data: dict[str, object],
    ) -> None:
        """Test running tasks sensor with no tasks."""
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator
        from custom_components.embymedia.sensor import EmbyRunningTasksSensor

        mock_coordinator = MagicMock(spec=EmbyServerCoordinator)
        mock_coordinator.data = mock_server_data
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyRunningTasksSensor(coordinator=mock_coordinator)

        assert sensor.unique_id == "test-server-id_running_tasks"
        assert sensor.native_value == 0

    async def test_sensor_with_tasks(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test running tasks sensor with running tasks."""
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator
        from custom_components.embymedia.sensor import EmbyRunningTasksSensor

        server_data = {
            "server_version": "4.9.2.0",
            "has_pending_restart": False,
            "has_update_available": False,
            "scheduled_tasks": [],
            "running_tasks_count": 2,
            "library_scan_active": True,
            "library_scan_progress": 50.0,
        }

        mock_coordinator = MagicMock(spec=EmbyServerCoordinator)
        mock_coordinator.data = server_data
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyRunningTasksSensor(coordinator=mock_coordinator)

        assert sensor.native_value == 2


class TestEmbyMovieCountSensor:
    """Tests for movie count sensor."""

    async def test_sensor_value(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_library_data: dict[str, object],
    ) -> None:
        """Test movie count sensor returns correct value."""
        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator
        from custom_components.embymedia.sensor import EmbyMovieCountSensor

        mock_coordinator = MagicMock(spec=EmbyLibraryCoordinator)
        mock_coordinator.data = mock_library_data
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyMovieCountSensor(coordinator=mock_coordinator, server_name="Test Server")

        assert sensor.unique_id == "test-server-id_movie_count"
        assert sensor.native_value == 1209
        assert sensor.icon == "mdi:movie"


class TestEmbySeriesCountSensor:
    """Tests for series count sensor."""

    async def test_sensor_value(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_library_data: dict[str, object],
    ) -> None:
        """Test series count sensor returns correct value."""
        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator
        from custom_components.embymedia.sensor import EmbySeriesCountSensor

        mock_coordinator = MagicMock(spec=EmbyLibraryCoordinator)
        mock_coordinator.data = mock_library_data
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbySeriesCountSensor(coordinator=mock_coordinator, server_name="Test Server")

        assert sensor.unique_id == "test-server-id_series_count"
        assert sensor.native_value == 374
        assert sensor.icon == "mdi:television"


class TestEmbyEpisodeCountSensor:
    """Tests for episode count sensor."""

    async def test_sensor_value(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_library_data: dict[str, object],
    ) -> None:
        """Test episode count sensor returns correct value."""
        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator
        from custom_components.embymedia.sensor import EmbyEpisodeCountSensor

        mock_coordinator = MagicMock(spec=EmbyLibraryCoordinator)
        mock_coordinator.data = mock_library_data
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyEpisodeCountSensor(coordinator=mock_coordinator, server_name="Test Server")

        assert sensor.unique_id == "test-server-id_episode_count"
        assert sensor.native_value == 4620
        assert sensor.icon == "mdi:television-play"


class TestEmbySongCountSensor:
    """Tests for song count sensor."""

    async def test_sensor_value(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_library_data: dict[str, object],
    ) -> None:
        """Test song count sensor returns correct value."""
        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator
        from custom_components.embymedia.sensor import EmbySongCountSensor

        mock_coordinator = MagicMock(spec=EmbyLibraryCoordinator)
        mock_coordinator.data = mock_library_data
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbySongCountSensor(coordinator=mock_coordinator, server_name="Test Server")

        assert sensor.unique_id == "test-server-id_song_count"
        assert sensor.native_value == 14341
        assert sensor.icon == "mdi:music"


class TestAsyncSetupEntry:
    """Tests for async_setup_entry function."""

    async def test_setup_entry_creates_sensors(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_data: dict[str, object],
        mock_library_data: dict[str, object],
    ) -> None:
        """Test that setup creates all sensors."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator
        from custom_components.embymedia.coordinator_sensors import (
            EmbyLibraryCoordinator,
            EmbyServerCoordinator,
        )
        from custom_components.embymedia.sensor import async_setup_entry

        mock_server_coordinator = MagicMock(spec=EmbyServerCoordinator)
        mock_server_coordinator.data = mock_server_data
        mock_server_coordinator.last_update_success = True
        mock_server_coordinator.server_id = "test-server-id"
        mock_server_coordinator.server_name = "Test Server"
        mock_server_coordinator.config_entry = mock_config_entry

        mock_library_coordinator = MagicMock(spec=EmbyLibraryCoordinator)
        mock_library_coordinator.data = mock_library_data
        mock_library_coordinator.last_update_success = True
        mock_library_coordinator.server_id = "test-server-id"
        mock_library_coordinator.config_entry = mock_config_entry

        mock_session_coordinator = MagicMock(spec=EmbyDataUpdateCoordinator)
        mock_session_coordinator.data = {}
        mock_session_coordinator.last_update_success = True
        mock_session_coordinator.server_id = "test-server-id"
        mock_session_coordinator.server_name = "Test Server"
        mock_session_coordinator.config_entry = mock_config_entry

        class RuntimeData:
            server_coordinator = mock_server_coordinator
            library_coordinator = mock_library_coordinator
            session_coordinator = mock_session_coordinator
            discovery_coordinator = None

        mock_config_entry.runtime_data = RuntimeData()

        entities_added: list[object] = []

        def mock_add_entities(entities: list[object], update: bool = False) -> None:
            entities_added.extend(entities)

        await async_setup_entry(hass, mock_config_entry, mock_add_entities)

        # Should have created sensors (version, active sessions, running tasks, library counts)
        assert len(entities_added) >= 6


class TestSensorDataNone:
    """Tests for sensors when coordinator data is None."""

    async def test_version_sensor_returns_none_when_data_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test version sensor returns None when coordinator data is None."""
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator
        from custom_components.embymedia.sensor import EmbyVersionSensor

        mock_coordinator = MagicMock(spec=EmbyServerCoordinator)
        mock_coordinator.data = None
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyVersionSensor(coordinator=mock_coordinator)

        assert sensor.native_value is None

    async def test_running_tasks_sensor_returns_none_when_data_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test running tasks sensor returns None when coordinator data is None."""
        from custom_components.embymedia.coordinator_sensors import EmbyServerCoordinator
        from custom_components.embymedia.sensor import EmbyRunningTasksSensor

        mock_coordinator = MagicMock(spec=EmbyServerCoordinator)
        mock_coordinator.data = None
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyRunningTasksSensor(coordinator=mock_coordinator)

        assert sensor.native_value is None

    async def test_active_sessions_sensor_returns_zero_when_data_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test active sessions sensor returns 0 when coordinator data is None."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator
        from custom_components.embymedia.sensor import EmbyActiveSessionsSensor

        mock_coordinator = MagicMock(spec=EmbyDataUpdateCoordinator)
        mock_coordinator.data = None
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyActiveSessionsSensor(coordinator=mock_coordinator)

        # Should return 0 when data is None
        assert sensor.native_value == 0

    async def test_movie_count_sensor_returns_none_when_data_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test movie count sensor returns None when coordinator data is None."""
        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator
        from custom_components.embymedia.sensor import EmbyMovieCountSensor

        mock_coordinator = MagicMock(spec=EmbyLibraryCoordinator)
        mock_coordinator.data = None
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyMovieCountSensor(coordinator=mock_coordinator, server_name="Test Server")

        assert sensor.native_value is None

    async def test_series_count_sensor_returns_none_when_data_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test series count sensor returns None when coordinator data is None."""
        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator
        from custom_components.embymedia.sensor import EmbySeriesCountSensor

        mock_coordinator = MagicMock(spec=EmbyLibraryCoordinator)
        mock_coordinator.data = None
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbySeriesCountSensor(coordinator=mock_coordinator, server_name="Test Server")

        assert sensor.native_value is None

    async def test_episode_count_sensor_returns_none_when_data_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test episode count sensor returns None when coordinator data is None."""
        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator
        from custom_components.embymedia.sensor import EmbyEpisodeCountSensor

        mock_coordinator = MagicMock(spec=EmbyLibraryCoordinator)
        mock_coordinator.data = None
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyEpisodeCountSensor(coordinator=mock_coordinator, server_name="Test Server")

        assert sensor.native_value is None

    async def test_song_count_sensor_returns_none_when_data_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test song count sensor returns None when coordinator data is None."""
        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator
        from custom_components.embymedia.sensor import EmbySongCountSensor

        mock_coordinator = MagicMock(spec=EmbyLibraryCoordinator)
        mock_coordinator.data = None
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbySongCountSensor(coordinator=mock_coordinator, server_name="Test Server")

        assert sensor.native_value is None

    async def test_album_count_sensor_returns_none_when_data_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test album count sensor returns None when coordinator data is None."""
        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator
        from custom_components.embymedia.sensor import EmbyAlbumCountSensor

        mock_coordinator = MagicMock(spec=EmbyLibraryCoordinator)
        mock_coordinator.data = None
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyAlbumCountSensor(coordinator=mock_coordinator, server_name="Test Server")

        assert sensor.native_value is None

    async def test_artist_count_sensor_returns_none_when_data_none(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test artist count sensor returns None when coordinator data is None."""
        from custom_components.embymedia.coordinator_sensors import EmbyLibraryCoordinator
        from custom_components.embymedia.sensor import EmbyArtistCountSensor

        mock_coordinator = MagicMock(spec=EmbyLibraryCoordinator)
        mock_coordinator.data = None
        mock_coordinator.last_update_success = True
        mock_coordinator.server_id = "test-server-id"
        mock_coordinator.config_entry = mock_config_entry

        sensor = EmbyArtistCountSensor(coordinator=mock_coordinator, server_name="Test Server")

        assert sensor.native_value is None
