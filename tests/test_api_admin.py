"""Tests for Phase 20 API methods for server administration."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

from custom_components.embymedia.api import EmbyClient
from custom_components.embymedia.const import EmbyPlugin
from custom_components.embymedia.exceptions import (
    EmbyAuthenticationError,
    EmbyConnectionError,
    EmbyNotFoundError,
)

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock aiohttp ClientSession."""
    return AsyncMock(spec=aiohttp.ClientSession)


@pytest.fixture
def emby_client(mock_session: AsyncMock) -> EmbyClient:
    """Create an EmbyClient instance for testing."""
    return EmbyClient(
        host="emby.local",
        port=8096,
        api_key="test-api-key",
        ssl=False,
        session=mock_session,
    )


class TestAsyncRunScheduledTask:
    """Tests for async_run_scheduled_task API method."""

    async def test_run_scheduled_task_success(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test successful triggering of a scheduled task."""
        task_id = "6330ee8fb4a957f33981f89aa78b030f"

        with patch.object(
            emby_client,
            "_request_post",
            new_callable=AsyncMock,
        ) as mock_request:
            await emby_client.async_run_scheduled_task(task_id=task_id)

            mock_request.assert_called_once_with(f"/ScheduledTasks/Running/{task_id}")

    async def test_run_scheduled_task_not_found(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test triggering non-existent task raises EmbyNotFoundError."""
        task_id = "non-existent-task"

        with (
            patch.object(
                emby_client,
                "_request_post",
                new_callable=AsyncMock,
                side_effect=EmbyNotFoundError("Task not found"),
            ),
            pytest.raises(EmbyNotFoundError),
        ):
            await emby_client.async_run_scheduled_task(task_id=task_id)

    async def test_run_scheduled_task_connection_error(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test connection error during task trigger."""
        task_id = "6330ee8fb4a957f33981f89aa78b030f"

        with (
            patch.object(
                emby_client,
                "_request_post",
                new_callable=AsyncMock,
                side_effect=EmbyConnectionError("Connection failed"),
            ),
            pytest.raises(EmbyConnectionError),
        ):
            await emby_client.async_run_scheduled_task(task_id=task_id)

    async def test_run_scheduled_task_auth_error(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test auth error during task trigger."""
        task_id = "6330ee8fb4a957f33981f89aa78b030f"

        with (
            patch.object(
                emby_client,
                "_request_post",
                new_callable=AsyncMock,
                side_effect=EmbyAuthenticationError("Auth failed"),
            ),
            pytest.raises(EmbyAuthenticationError),
        ):
            await emby_client.async_run_scheduled_task(task_id=task_id)


class TestAsyncRestartServer:
    """Tests for async_restart_server API method."""

    async def test_restart_server_success(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test successful server restart."""
        with patch.object(
            emby_client,
            "_request_post",
            new_callable=AsyncMock,
        ) as mock_request:
            await emby_client.async_restart_server()

            mock_request.assert_called_once_with("/System/Restart")

    async def test_restart_server_connection_error(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test connection error during restart."""
        with (
            patch.object(
                emby_client,
                "_request_post",
                new_callable=AsyncMock,
                side_effect=EmbyConnectionError("Connection failed"),
            ),
            pytest.raises(EmbyConnectionError),
        ):
            await emby_client.async_restart_server()

    async def test_restart_server_auth_error(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test auth error during restart."""
        with (
            patch.object(
                emby_client,
                "_request_post",
                new_callable=AsyncMock,
                side_effect=EmbyAuthenticationError("Auth failed"),
            ),
            pytest.raises(EmbyAuthenticationError),
        ):
            await emby_client.async_restart_server()


class TestAsyncShutdownServer:
    """Tests for async_shutdown_server API method."""

    async def test_shutdown_server_success(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test successful server shutdown."""
        with patch.object(
            emby_client,
            "_request_post",
            new_callable=AsyncMock,
        ) as mock_request:
            await emby_client.async_shutdown_server()

            mock_request.assert_called_once_with("/System/Shutdown")

    async def test_shutdown_server_connection_error(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test connection error during shutdown."""
        with (
            patch.object(
                emby_client,
                "_request_post",
                new_callable=AsyncMock,
                side_effect=EmbyConnectionError("Connection failed"),
            ),
            pytest.raises(EmbyConnectionError),
        ):
            await emby_client.async_shutdown_server()

    async def test_shutdown_server_auth_error(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test auth error during shutdown."""
        with (
            patch.object(
                emby_client,
                "_request_post",
                new_callable=AsyncMock,
                side_effect=EmbyAuthenticationError("Auth failed"),
            ),
            pytest.raises(EmbyAuthenticationError),
        ):
            await emby_client.async_shutdown_server()


class TestAsyncGetPlugins:
    """Tests for async_get_plugins API method."""

    async def test_get_plugins_success(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test successful retrieval of plugins."""
        mock_response: list[EmbyPlugin] = [
            {
                "Name": "Backup & Restore",
                "Version": "1.8.2.0",
                "ConfigurationFileName": "MBBackup.xml",
                "Description": "Backup & Restore for Emby Server",
                "Id": "e711475e-efad-431b-8527-033ba9873a34",
            },
            {
                "Name": "DLNA",
                "Version": "1.5.4.0",
                "Description": "DLNA server support",
                "Id": "8c6ddb20-18b1-4131-9285-796179a71c0f",
            },
        ]

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_request:
            result = await emby_client.async_get_plugins()

            mock_request.assert_called_once_with("GET", "/Plugins")
            assert len(result) == 2
            assert result[0]["Name"] == "Backup & Restore"
            assert result[0]["Version"] == "1.8.2.0"
            assert result[0]["Id"] == "e711475e-efad-431b-8527-033ba9873a34"
            assert result[1]["Name"] == "DLNA"

    async def test_get_plugins_empty(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test getting plugins when none installed."""
        mock_response: list[EmbyPlugin] = []

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_request:
            result = await emby_client.async_get_plugins()

            mock_request.assert_called_once_with("GET", "/Plugins")
            assert result == []

    async def test_get_plugins_connection_error(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test connection error during plugin retrieval."""
        with (
            patch.object(
                emby_client,
                "_request",
                new_callable=AsyncMock,
                side_effect=EmbyConnectionError("Connection failed"),
            ),
            pytest.raises(EmbyConnectionError),
        ):
            await emby_client.async_get_plugins()

    async def test_get_plugins_auth_error(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test auth error during plugin retrieval."""
        with (
            patch.object(
                emby_client,
                "_request",
                new_callable=AsyncMock,
                side_effect=EmbyAuthenticationError("Auth failed"),
            ),
            pytest.raises(EmbyAuthenticationError),
        ):
            await emby_client.async_get_plugins()
