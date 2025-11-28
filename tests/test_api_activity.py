"""Tests for Activity Log API methods.

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


class TestActivityLogAPI:
    """Tests for async_get_activity_log API method."""

    @pytest.mark.asyncio
    async def test_async_get_activity_log_exists(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_get_activity_log method exists."""
        assert hasattr(mock_client, "async_get_activity_log")
        assert callable(mock_client.async_get_activity_log)

    @pytest.mark.asyncio
    async def test_async_get_activity_log_returns_response(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_get_activity_log returns activity log response."""
        mock_response = {
            "Items": [
                {
                    "Id": 6612,
                    "Name": "Recording of BBC News has failed",
                    "Type": "livetv.recordingerror",
                    "Date": "2025-11-28T10:00:37.8370000Z",
                    "Severity": "Error",
                }
            ],
            "TotalRecordCount": 6612,
        }

        with patch.object(mock_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await mock_client.async_get_activity_log()

            assert result["Items"] is not None
            assert result["TotalRecordCount"] == 6612

    @pytest.mark.asyncio
    async def test_async_get_activity_log_calls_correct_endpoint(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_get_activity_log calls the correct API endpoint."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(mock_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await mock_client.async_get_activity_log()

            # Should call with GET and the activity log endpoint
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0][0] == "GET"
            assert "/System/ActivityLog/Entries" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_async_get_activity_log_with_limit(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_get_activity_log with limit parameter."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(mock_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await mock_client.async_get_activity_log(limit=10)

            call_args = mock_request.call_args
            endpoint = call_args[0][1]
            assert "Limit=10" in endpoint

    @pytest.mark.asyncio
    async def test_async_get_activity_log_with_start_index(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_get_activity_log with start_index parameter."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(mock_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await mock_client.async_get_activity_log(start_index=100)

            call_args = mock_request.call_args
            endpoint = call_args[0][1]
            assert "StartIndex=100" in endpoint

    @pytest.mark.asyncio
    async def test_async_get_activity_log_with_min_date(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_get_activity_log with min_date filter."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(mock_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await mock_client.async_get_activity_log(min_date="2025-11-28T00:00:00.0000000Z")

            call_args = mock_request.call_args
            endpoint = call_args[0][1]
            assert "MinDate=" in endpoint

    @pytest.mark.asyncio
    async def test_async_get_activity_log_with_has_user_id_true(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_get_activity_log with has_user_id=True filter."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(mock_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await mock_client.async_get_activity_log(has_user_id=True)

            call_args = mock_request.call_args
            endpoint = call_args[0][1]
            assert "HasUserId=true" in endpoint

    @pytest.mark.asyncio
    async def test_async_get_activity_log_with_has_user_id_false(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_get_activity_log with has_user_id=False filter."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(mock_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await mock_client.async_get_activity_log(has_user_id=False)

            call_args = mock_request.call_args
            endpoint = call_args[0][1]
            assert "HasUserId=false" in endpoint

    @pytest.mark.asyncio
    async def test_async_get_activity_log_default_limit(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_get_activity_log uses default limit of 50."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(mock_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await mock_client.async_get_activity_log()

            call_args = mock_request.call_args
            endpoint = call_args[0][1]
            # Default limit should be 50
            assert "Limit=50" in endpoint

    @pytest.mark.asyncio
    async def test_async_get_activity_log_default_start_index(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_get_activity_log uses default start_index of 0."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(mock_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await mock_client.async_get_activity_log()

            call_args = mock_request.call_args
            endpoint = call_args[0][1]
            # Default start_index should be 0
            assert "StartIndex=0" in endpoint

    @pytest.mark.asyncio
    async def test_async_get_activity_log_with_all_parameters(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_get_activity_log with all parameters."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(mock_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await mock_client.async_get_activity_log(
                start_index=50,
                limit=25,
                min_date="2025-11-01T00:00:00Z",
                has_user_id=True,
            )

            call_args = mock_request.call_args
            endpoint = call_args[0][1]
            assert "StartIndex=50" in endpoint
            assert "Limit=25" in endpoint
            assert "MinDate=" in endpoint
            assert "HasUserId=true" in endpoint

    @pytest.mark.asyncio
    async def test_async_get_activity_log_parses_items(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_get_activity_log correctly parses activity items."""
        mock_response = {
            "Items": [
                {
                    "Id": 6611,
                    "Name": "admin is playing Elsbeth - S3, Ep6",
                    "Type": "playback.start",
                    "ItemId": "121947",
                    "Date": "2025-11-28T09:56:09.8260000Z",
                    "UserId": "1",
                    "UserPrimaryImageTag": "b1145a695b3dbf0b91bb1e266151c129",
                    "Severity": "Info",
                },
                {
                    "Id": 6610,
                    "Name": "admin has finished playing Grand Designs",
                    "Type": "playback.stop",
                    "ItemId": "118555",
                    "Date": "2025-11-28T09:55:30.7810000Z",
                    "UserId": "1",
                    "UserPrimaryImageTag": "b1145a695b3dbf0b91bb1e266151c129",
                    "Severity": "Info",
                },
            ],
            "TotalRecordCount": 6612,
        }

        with patch.object(mock_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await mock_client.async_get_activity_log()

            assert len(result["Items"]) == 2
            assert result["Items"][0]["Type"] == "playback.start"
            assert result["Items"][1]["Type"] == "playback.stop"
