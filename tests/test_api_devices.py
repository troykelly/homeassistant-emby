"""Tests for Devices API methods.

Phase 18: User Activity & Statistics
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

if TYPE_CHECKING:
    from custom_components.embymedia.api import EmbyClient


@pytest.fixture
def mock_client() -> EmbyClient:
    """Create a mock EmbyClient for testing."""
    from custom_components.embymedia.api import EmbyClient

    client = EmbyClient(
        host="test.local",
        port=8096,
        api_key="test-api-key",
    )
    return client


class TestDevicesAPI:
    """Tests for async_get_devices API method."""

    @pytest.mark.asyncio
    async def test_async_get_devices_exists(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_get_devices method exists."""
        assert hasattr(mock_client, "async_get_devices")
        assert callable(mock_client.async_get_devices)

    @pytest.mark.asyncio
    async def test_async_get_devices_returns_response(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_get_devices returns devices response."""
        mock_response = {
            "Items": [
                {
                    "Name": "Samsung Smart TV",
                    "Id": "5",
                    "ReportedDeviceId": "9beb4c7a-2785-48e9-8e43-be15c34e0435",
                    "LastUserName": "admin",
                    "AppName": "Emby for Samsung",
                    "AppVersion": "2.2.5",
                    "LastUserId": "eb0d7e33ee184e36aa011be275ae01f2",
                    "DateLastActivity": "2025-11-28T10:00:16.0000000Z",
                    "IconUrl": "https://example.com/icon.png",
                    "IpAddress": "192.168.1.100",
                }
            ],
            "TotalRecordCount": 0,  # Emby quirk: often returns 0
        }

        with patch.object(mock_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await mock_client.async_get_devices()

            assert result["Items"] is not None
            assert len(result["Items"]) == 1

    @pytest.mark.asyncio
    async def test_async_get_devices_calls_correct_endpoint(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_get_devices calls the correct API endpoint."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(mock_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await mock_client.async_get_devices()

            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0][0] == "GET"
            assert "/Devices" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_async_get_devices_with_user_id_filter(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_get_devices with user_id filter."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(mock_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await mock_client.async_get_devices(user_id="user123")

            call_args = mock_request.call_args
            endpoint = call_args[0][1]
            assert "UserId=user123" in endpoint

    @pytest.mark.asyncio
    async def test_async_get_devices_without_user_id(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_get_devices without user_id returns all devices."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(mock_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await mock_client.async_get_devices()

            call_args = mock_request.call_args
            endpoint = call_args[0][1]
            # Should not have UserId parameter
            assert "UserId=" not in endpoint

    @pytest.mark.asyncio
    async def test_async_get_devices_parses_multiple_devices(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_get_devices correctly parses multiple devices."""
        mock_response = {
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
                {
                    "Name": "Pixel 6 Pro",
                    "Id": "9",
                    "LastUserName": "troy",
                    "AppName": "Emby for Android",
                    "AppVersion": "3.5.16",
                    "LastUserId": "user2",
                    "DateLastActivity": "2025-11-28T05:55:52.0000000Z",
                },
            ],
            "TotalRecordCount": 0,
        }

        with patch.object(mock_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await mock_client.async_get_devices()

            assert len(result["Items"]) == 3
            assert result["Items"][0]["AppName"] == "Emby for Samsung"
            assert result["Items"][1]["AppName"] == "Emby for macOS"
            assert result["Items"][2]["AppName"] == "Emby for Android"

    @pytest.mark.asyncio
    async def test_async_get_devices_empty_response(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_get_devices handles empty device list."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(mock_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await mock_client.async_get_devices()

            assert result["Items"] == []
            assert result["TotalRecordCount"] == 0
