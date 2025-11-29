"""Fixtures for Emby integration tests."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.embymedia.const import (
    CONF_API_KEY,
    CONF_VERIFY_SSL,
    DOMAIN,
)

# Auto-use fixture to enable custom component loading for all tests
pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None]:
    """Enable custom integrations in Home Assistant."""
    yield


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
def mock_server_info() -> dict[str, Any]:
    """Return mock server info response."""
    return {
        "Id": "test-server-id-12345",
        "ServerName": "Test Emby Server",
        "Version": "4.9.2.0",
        "OperatingSystem": "Linux",
        "HasPendingRestart": False,
        "IsShuttingDown": False,
        "LocalAddress": "http://192.168.1.100:8096",
    }


@pytest.fixture
def mock_public_info() -> dict[str, Any]:
    """Return mock public info response."""
    return {
        "Id": "test-server-id-12345",
        "ServerName": "Test Emby Server",
        "Version": "4.9.2.0",
        "LocalAddress": "http://192.168.1.100:8096",
    }


@pytest.fixture
def mock_users() -> list[dict[str, Any]]:
    """Return mock users response."""
    return [
        {
            "Id": "user-1",
            "Name": "TestUser",
            "ServerId": "test-server-id-12345",
            "HasPassword": True,
            "HasConfiguredPassword": True,
        }
    ]


@pytest.fixture
def mock_emby_client(
    mock_server_info: dict[str, Any],
    mock_public_info: dict[str, Any],
    mock_users: list[dict[str, Any]],
) -> Generator[MagicMock]:
    """Mock EmbyClient for testing."""
    with patch(
        "custom_components.embymedia.config_flow.EmbyClient", autospec=True
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.async_validate_connection = AsyncMock(return_value=True)
        client.async_get_server_info = AsyncMock(return_value=mock_server_info)
        client.async_get_public_info = AsyncMock(return_value=mock_public_info)
        client.async_get_users = AsyncMock(return_value=mock_users)
        client.close = AsyncMock()
        client.base_url = "http://emby.local:8096"
        yield client


def add_coordinator_mocks(client: MagicMock) -> None:
    """Add all coordinator-related mocks to a client mock.

    This ensures the client mock has all methods required by the
    coordinators (server, library, discovery) for asyncio.gather() calls.

    Args:
        client: The mock client to add methods to.
    """
    # Server coordinator methods
    client.async_get_scheduled_tasks = AsyncMock(return_value=[])
    client.async_get_live_tv_info = AsyncMock(
        return_value={"IsEnabled": False, "TunerCount": 0, "ActiveRecordingCount": 0}
    )
    client.async_get_timers = AsyncMock(return_value=[])
    client.async_get_series_timers = AsyncMock(return_value=[])
    client.async_get_recordings = AsyncMock(return_value=[])
    client.async_get_activity_log = AsyncMock(return_value={"Items": [], "TotalRecordCount": 0})
    client.async_get_devices = AsyncMock(return_value={"Items": []})
    client.async_get_plugins = AsyncMock(return_value=[])

    # Library coordinator methods
    client.async_get_item_counts = AsyncMock(
        return_value={
            "MovieCount": 0,
            "SeriesCount": 0,
            "EpisodeCount": 0,
            "ArtistCount": 0,
            "AlbumCount": 0,
            "SongCount": 0,
        }
    )
    client.async_get_virtual_folders = AsyncMock(return_value=[])
    client.async_get_user_item_count = AsyncMock(return_value=0)
    client.async_get_playlists = AsyncMock(return_value=[])
    client.async_get_collections = AsyncMock(return_value=[])

    # Discovery coordinator methods
    client.async_get_next_up = AsyncMock(return_value=[])
    client.async_get_resumable_items = AsyncMock(return_value=[])
    client.async_get_latest_media = AsyncMock(return_value=[])
    client.async_get_suggestions = AsyncMock(return_value=[])


def setup_mock_emby_client(
    client: MagicMock,
    server_info: dict[str, Any] | None = None,
) -> MagicMock:
    """Setup a mock EmbyClient with all required mocks for testing.

    This is the recommended way to setup a mock EmbyClient when using
    patch("custom_components.embymedia.EmbyClient", autospec=True).

    Args:
        client: The mock client to setup (typically mock_client_class.return_value).
        server_info: Optional server info dict (defaults to basic test server info).

    Returns:
        The configured mock client.

    Example:
        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_cls:
            client = setup_mock_emby_client(mock_cls.return_value)
            # Now client has all required mocks
    """
    if server_info is None:
        server_info = {
            "Id": "test-server-id",
            "ServerName": "Test Server",
            "Version": "4.9.2.0",
        }

    # Basic client methods
    client.async_validate_connection = AsyncMock(return_value=True)
    client.async_get_server_info = AsyncMock(return_value=server_info)
    client.async_get_sessions = AsyncMock(return_value=[])
    client.async_get_users = AsyncMock(return_value=[])
    client.close = AsyncMock()
    client.base_url = "http://emby.local:8096"

    # Add all coordinator-related mocks
    add_coordinator_mocks(client)

    return client


@pytest.fixture
def mock_emby_client_init(
    mock_server_info: dict[str, Any],
    mock_public_info: dict[str, Any],
    mock_users: list[dict[str, Any]],
) -> Generator[MagicMock]:
    """Mock EmbyClient for __init__.py testing."""
    with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
        client = mock_client_class.return_value
        client.async_validate_connection = AsyncMock(return_value=True)
        client.async_get_server_info = AsyncMock(return_value=mock_server_info)
        client.async_get_public_info = AsyncMock(return_value=mock_public_info)
        client.async_get_users = AsyncMock(return_value=mock_users)
        client.close = AsyncMock()
        client.base_url = "http://emby.local:8096"
        # Add coordinator-related mocks
        add_coordinator_mocks(client)
        yield client


@pytest.fixture
def mock_aiohttp_session() -> Generator[MagicMock]:
    """Mock aiohttp ClientSession."""
    with patch("aiohttp.ClientSession", autospec=True) as mock_session:
        session = mock_session.return_value
        session.closed = False
        session.close = AsyncMock()
        yield session


def create_mock_session_coordinator(
    server_id: str = "test-server-id-12345",
    server_name: str = "Test Emby Server",
) -> MagicMock:
    """Create a mock session coordinator with required attributes.

    Args:
        server_id: The server ID for the coordinator.
        server_name: The server name for the coordinator.

    Returns:
        A MagicMock configured as a session coordinator.
    """
    coordinator = MagicMock()
    coordinator.server_id = server_id
    coordinator.server_name = server_name
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.async_setup_websocket = AsyncMock()
    coordinator.async_shutdown_websocket = AsyncMock()
    coordinator.data = {}
    coordinator.last_update_success = True
    return coordinator


def create_mock_server_coordinator(
    server_id: str = "test-server-id-12345",
    server_name: str = "Test Emby Server",
) -> MagicMock:
    """Create a mock server coordinator with required attributes.

    Args:
        server_id: The server ID for the coordinator.
        server_name: The server name for the coordinator.

    Returns:
        A MagicMock configured as a server coordinator.
    """
    coordinator = MagicMock()
    coordinator.server_id = server_id
    coordinator.server_name = server_name
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.data = {
        "server_version": "4.9.2.0",
        "has_pending_restart": False,
        "has_update_available": False,
        "is_shutting_down": False,
        "running_tasks_count": 0,
        "running_tasks": [],
        "libraries": [],
    }
    coordinator.last_update_success = True
    return coordinator


def create_mock_library_coordinator(
    server_id: str = "test-server-id-12345",
) -> MagicMock:
    """Create a mock library coordinator with required attributes.

    Args:
        server_id: The server ID for the coordinator.

    Returns:
        A MagicMock configured as a library coordinator.
    """
    coordinator = MagicMock()
    coordinator.server_id = server_id
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.data = {
        "movie_count": 100,
        "series_count": 50,
        "episode_count": 500,
        "song_count": 1000,
        "album_count": 100,
        "artist_count": 50,
    }
    coordinator.last_update_success = True
    return coordinator


@pytest.fixture
def mock_session_coordinator() -> MagicMock:
    """Create a mock session coordinator fixture."""
    return create_mock_session_coordinator()


@pytest.fixture
def mock_server_coordinator() -> MagicMock:
    """Create a mock server coordinator fixture."""
    return create_mock_server_coordinator()


@pytest.fixture
def mock_library_coordinator() -> MagicMock:
    """Create a mock library coordinator fixture."""
    return create_mock_library_coordinator()
