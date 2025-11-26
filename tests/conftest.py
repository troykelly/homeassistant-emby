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
