"""Fixtures for Emby integration tests."""
from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.emby.const import (
    CONF_API_KEY,
    CONF_VERIFY_SSL,
    DOMAIN,
)


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
        "Version": "4.8.0.0",
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
        "Version": "4.8.0.0",
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
        "custom_components.emby.config_flow.EmbyClient", autospec=True
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
    with patch(
        "custom_components.emby.EmbyClient", autospec=True
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
def mock_aiohttp_session() -> Generator[MagicMock]:
    """Mock aiohttp ClientSession."""
    with patch("aiohttp.ClientSession", autospec=True) as mock_session:
        session = mock_session.return_value
        session.closed = False
        session.close = AsyncMock()
        yield session
