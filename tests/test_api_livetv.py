"""Tests for Live TV API methods.

Phase 16: Live TV & DVR Integration
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.embymedia.api import EmbyClient
from custom_components.embymedia.const import (
    EmbyLiveTvInfo,
    EmbyProgram,
    EmbyRecording,
    EmbySeriesTimer,
    EmbyTimer,
    EmbyTimerDefaults,
)
from custom_components.embymedia.exceptions import (
    EmbyConnectionError,
)

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def mock_session() -> Generator[MagicMock]:
    """Create mock aiohttp session."""
    with patch("aiohttp.ClientSession") as mock:
        session = MagicMock()
        mock.return_value.__aenter__ = AsyncMock(return_value=session)
        mock.return_value.__aexit__ = AsyncMock(return_value=None)
        yield session


@pytest.fixture
def emby_client() -> EmbyClient:
    """Create an EmbyClient instance for testing."""
    return EmbyClient(
        host="emby.local",
        port=8096,
        api_key="test_api_key",
        ssl=False,
        verify_ssl=True,
    )


class TestLiveTvInfo:
    """Tests for async_get_live_tv_info method."""

    async def test_get_live_tv_info_success(
        self, emby_client: EmbyClient, mock_session: MagicMock
    ) -> None:
        """Test successful Live TV info retrieval."""
        mock_response: EmbyLiveTvInfo = {
            "IsEnabled": True,
            "EnabledUsers": ["user1", "user2"],
        }

        with patch.object(emby_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await emby_client.async_get_live_tv_info()

            assert result["IsEnabled"] is True
            assert result["EnabledUsers"] == ["user1", "user2"]
            mock_req.assert_called_once_with("GET", "/LiveTv/Info")

    async def test_get_live_tv_info_disabled(self, emby_client: EmbyClient) -> None:
        """Test Live TV info when disabled."""
        mock_response: EmbyLiveTvInfo = {
            "IsEnabled": False,
            "EnabledUsers": [],
        }

        with patch.object(emby_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await emby_client.async_get_live_tv_info()

            assert result["IsEnabled"] is False
            assert result["EnabledUsers"] == []

    async def test_get_live_tv_info_connection_error(self, emby_client: EmbyClient) -> None:
        """Test Live TV info with connection error."""
        with patch.object(emby_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = EmbyConnectionError("Connection failed")

            with pytest.raises(EmbyConnectionError):
                await emby_client.async_get_live_tv_info()


class TestRecordings:
    """Tests for async_get_recordings method."""

    async def test_get_recordings_success(self, emby_client: EmbyClient) -> None:
        """Test successful recordings retrieval."""
        mock_response = {
            "Items": [
                {
                    "Id": "rec1",
                    "Name": "Recording 1",
                    "Type": "Recording",
                    "ChannelId": "ch1",
                    "ChannelName": "CNN",
                    "StartDate": "2025-11-27T20:00:00Z",
                    "EndDate": "2025-11-27T21:00:00Z",
                    "Status": "Completed",
                }
            ],
            "TotalRecordCount": 1,
        }

        with patch.object(emby_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await emby_client.async_get_recordings(user_id="user1")

            assert len(result) == 1
            assert result[0]["Id"] == "rec1"
            assert result[0]["Status"] == "Completed"
            mock_req.assert_called_once()

    async def test_get_recordings_with_status_filter(self, emby_client: EmbyClient) -> None:
        """Test recordings retrieval with status filter."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(emby_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            await emby_client.async_get_recordings(user_id="user1", status="InProgress")

            call_args = mock_req.call_args
            assert "Status=InProgress" in call_args[0][1]

    async def test_get_recordings_with_series_timer_id(self, emby_client: EmbyClient) -> None:
        """Test recordings retrieval filtered by series timer."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(emby_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            await emby_client.async_get_recordings(user_id="user1", series_timer_id="st123")

            call_args = mock_req.call_args
            assert "SeriesTimerId=st123" in call_args[0][1]

    async def test_get_recordings_in_progress(self, emby_client: EmbyClient) -> None:
        """Test recordings retrieval filtering currently recording."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(emby_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            await emby_client.async_get_recordings(user_id="user1", is_in_progress=True)

            call_args = mock_req.call_args
            assert "IsInProgress=true" in call_args[0][1]


class TestTimers:
    """Tests for timer-related API methods."""

    async def test_get_timers_success(self, emby_client: EmbyClient) -> None:
        """Test successful timers retrieval."""
        mock_response = {
            "Items": [
                {
                    "Id": "timer1",
                    "Type": "Timer",
                    "ChannelId": "ch1",
                    "ChannelName": "NBC",
                    "ProgramId": "prog1",
                    "Name": "Program 1",
                    "StartDate": "2025-11-28T20:00:00Z",
                    "EndDate": "2025-11-28T21:00:00Z",
                    "Status": "New",
                    "PrePaddingSeconds": 60,
                    "PostPaddingSeconds": 120,
                }
            ]
        }

        with patch.object(emby_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await emby_client.async_get_timers()

            assert len(result) == 1
            assert result[0]["Id"] == "timer1"
            assert result[0]["Status"] == "New"

    async def test_get_timers_with_channel_filter(self, emby_client: EmbyClient) -> None:
        """Test timers retrieval with channel filter."""
        mock_response = {"Items": []}

        with patch.object(emby_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            await emby_client.async_get_timers(channel_id="ch1")

            call_args = mock_req.call_args
            assert "ChannelId=ch1" in call_args[0][1]

    async def test_get_timers_with_series_timer_filter(self, emby_client: EmbyClient) -> None:
        """Test timers retrieval filtered by series timer ID."""
        mock_response = {"Items": []}

        with patch.object(emby_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            await emby_client.async_get_timers(series_timer_id="st123")

            call_args = mock_req.call_args
            assert "SeriesTimerId=st123" in call_args[0][1]

    async def test_get_timer_defaults_success(self, emby_client: EmbyClient) -> None:
        """Test getting timer defaults for a program."""
        mock_response: EmbyTimerDefaults = {
            "ProgramId": "prog1",
            "ChannelId": "ch1",
            "StartDate": "2025-11-28T20:00:00Z",
            "EndDate": "2025-11-28T21:00:00Z",
            "PrePaddingSeconds": 60,
            "PostPaddingSeconds": 120,
            "Priority": 0,
        }

        with patch.object(emby_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await emby_client.async_get_timer_defaults(program_id="prog1")

            assert result["ProgramId"] == "prog1"
            assert result["PrePaddingSeconds"] == 60
            mock_req.assert_called_once_with("GET", "/LiveTv/Timers/Defaults?ProgramId=prog1")

    async def test_create_timer_success(self, emby_client: EmbyClient) -> None:
        """Test creating a recording timer."""
        timer_data = {
            "ProgramId": "prog1",
            "ChannelId": "ch1",
            "StartDate": "2025-11-28T20:00:00Z",
            "EndDate": "2025-11-28T21:00:00Z",
            "PrePaddingSeconds": 60,
            "PostPaddingSeconds": 120,
        }

        with patch.object(emby_client, "_request_post", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = None

            await emby_client.async_create_timer(timer_data=timer_data)

            mock_req.assert_called_once_with("/LiveTv/Timers", data=timer_data)

    async def test_cancel_timer_success(self, emby_client: EmbyClient) -> None:
        """Test canceling a recording timer."""
        with patch.object(emby_client, "_request_delete", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = None

            await emby_client.async_cancel_timer(timer_id="timer1")

            mock_req.assert_called_once_with("/LiveTv/Timers/timer1")


class TestSeriesTimers:
    """Tests for series timer API methods."""

    async def test_get_series_timers_success(self, emby_client: EmbyClient) -> None:
        """Test successful series timers retrieval."""
        mock_response = {
            "Items": [
                {
                    "Id": "st1",
                    "Type": "SeriesTimer",
                    "Name": "News Show",
                    "ChannelId": "ch1",
                    "ChannelName": "ABC",
                    "RecordAnyTime": True,
                    "RecordNewOnly": True,
                    "SkipEpisodesInLibrary": True,
                    "Days": ["Monday", "Tuesday", "Wednesday"],
                }
            ]
        }

        with patch.object(emby_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await emby_client.async_get_series_timers()

            assert len(result) == 1
            assert result[0]["Id"] == "st1"
            assert result[0]["RecordAnyTime"] is True

    async def test_create_series_timer_success(self, emby_client: EmbyClient) -> None:
        """Test creating a series timer."""
        series_timer_data = {
            "ProgramId": "prog1",
            "ChannelId": "ch1",
            "RecordNewOnly": True,
            "SkipEpisodesInLibrary": True,
            "PrePaddingSeconds": 60,
            "PostPaddingSeconds": 120,
        }

        with patch.object(emby_client, "_request_post", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = None

            await emby_client.async_create_series_timer(series_timer_data=series_timer_data)

            mock_req.assert_called_once_with("/LiveTv/SeriesTimers", data=series_timer_data)

    async def test_cancel_series_timer_success(self, emby_client: EmbyClient) -> None:
        """Test canceling a series timer."""
        with patch.object(emby_client, "_request_delete", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = None

            await emby_client.async_cancel_series_timer(series_timer_id="st1")

            mock_req.assert_called_once_with("/LiveTv/SeriesTimers/st1")


class TestPrograms:
    """Tests for EPG program API methods."""

    async def test_get_programs_success(self, emby_client: EmbyClient) -> None:
        """Test successful programs retrieval."""
        mock_response = {
            "Items": [
                {
                    "Id": "prog1",
                    "Type": "Program",
                    "Name": "News",
                    "ChannelId": "ch1",
                    "ChannelName": "CNN",
                    "StartDate": "2025-11-28T20:00:00Z",
                    "EndDate": "2025-11-28T21:00:00Z",
                    "IsSeries": True,
                    "IsNews": True,
                }
            ],
            "TotalRecordCount": 1,
        }

        with patch.object(emby_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await emby_client.async_get_programs(user_id="user1")

            assert len(result) == 1
            assert result[0]["Id"] == "prog1"
            assert result[0]["IsSeries"] is True

    async def test_get_programs_with_date_filters(self, emby_client: EmbyClient) -> None:
        """Test programs retrieval with date filters."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(emby_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            await emby_client.async_get_programs(
                user_id="user1",
                min_start_date="2025-11-28T00:00:00Z",
                max_start_date="2025-11-29T00:00:00Z",
            )

            call_args = mock_req.call_args
            assert "MinStartDate=2025-11-28T00:00:00Z" in call_args[0][1]
            assert "MaxStartDate=2025-11-29T00:00:00Z" in call_args[0][1]

    async def test_get_programs_with_channel_ids(self, emby_client: EmbyClient) -> None:
        """Test programs retrieval with channel filter."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(emby_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            await emby_client.async_get_programs(user_id="user1", channel_ids=["ch1", "ch2"])

            call_args = mock_req.call_args
            assert "ChannelIds=ch1,ch2" in call_args[0][1]

    async def test_get_programs_airing_filter(self, emby_client: EmbyClient) -> None:
        """Test programs retrieval filtering for currently airing."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(emby_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            await emby_client.async_get_programs(user_id="user1", is_airing=True)

            call_args = mock_req.call_args
            assert "IsAiring=true" in call_args[0][1]

    async def test_get_programs_has_aired_filter(self, emby_client: EmbyClient) -> None:
        """Test programs retrieval filtering by has_aired status."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(emby_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            # Test with has_aired=True
            await emby_client.async_get_programs(user_id="user1", has_aired=True)

            call_args = mock_req.call_args
            assert "HasAired=true" in call_args[0][1]

        with patch.object(emby_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            # Test with has_aired=False
            await emby_client.async_get_programs(user_id="user1", has_aired=False)

            call_args = mock_req.call_args
            assert "HasAired=false" in call_args[0][1]

    async def test_get_recommended_programs_success(self, emby_client: EmbyClient) -> None:
        """Test getting recommended programs."""
        mock_response = {
            "Items": [
                {
                    "Id": "prog1",
                    "Type": "Program",
                    "Name": "Recommended Show",
                    "ChannelId": "ch1",
                    "ChannelName": "NBC",
                    "StartDate": "2025-11-28T21:00:00Z",
                    "EndDate": "2025-11-28T22:00:00Z",
                }
            ],
            "TotalRecordCount": 1,
        }

        with patch.object(emby_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response

            result = await emby_client.async_get_recommended_programs(user_id="user1", limit=10)

            assert len(result) == 1
            assert result[0]["Name"] == "Recommended Show"
            mock_req.assert_called_once_with(
                "GET", "/LiveTv/Programs/Recommended?UserId=user1&Limit=10"
            )


class TestTypedDicts:
    """Tests for Live TV TypedDict type annotations."""

    def test_livetv_info_typeddict(self) -> None:
        """Test EmbyLiveTvInfo TypedDict structure."""
        info: EmbyLiveTvInfo = {
            "IsEnabled": True,
            "EnabledUsers": ["user1", "user2"],
        }
        assert info["IsEnabled"] is True
        assert len(info["EnabledUsers"]) == 2

    def test_recording_typeddict(self) -> None:
        """Test EmbyRecording TypedDict structure."""
        recording: EmbyRecording = {
            "Id": "rec1",
            "Name": "Test Recording",
            "Type": "Recording",
            "ChannelId": "ch1",
            "ChannelName": "CNN",
            "StartDate": "2025-11-27T20:00:00Z",
            "EndDate": "2025-11-27T21:00:00Z",
            "Status": "Completed",
        }
        assert recording["Id"] == "rec1"
        assert recording["Status"] == "Completed"

    def test_timer_typeddict(self) -> None:
        """Test EmbyTimer TypedDict structure."""
        timer: EmbyTimer = {
            "Id": "timer1",
            "Type": "Timer",
            "ChannelId": "ch1",
            "ChannelName": "NBC",
            "ProgramId": "prog1",
            "Name": "Scheduled Show",
            "StartDate": "2025-11-28T20:00:00Z",
            "EndDate": "2025-11-28T21:00:00Z",
            "Status": "New",
        }
        assert timer["Id"] == "timer1"
        assert timer["Status"] == "New"

    def test_series_timer_typeddict(self) -> None:
        """Test EmbySeriesTimer TypedDict structure."""
        series_timer: EmbySeriesTimer = {
            "Id": "st1",
            "Type": "SeriesTimer",
            "Name": "Daily News",
            "ChannelId": "ch1",
            "ChannelName": "ABC",
            "ProgramId": "prog1",
            "RecordAnyTime": True,
            "RecordAnyChannel": False,
            "RecordNewOnly": True,
            "SkipEpisodesInLibrary": True,
            "Days": ["Monday", "Wednesday", "Friday"],
        }
        assert series_timer["Id"] == "st1"
        assert series_timer["RecordNewOnly"] is True
        assert len(series_timer["Days"]) == 3

    def test_program_typeddict(self) -> None:
        """Test EmbyProgram TypedDict structure."""
        program: EmbyProgram = {
            "Id": "prog1",
            "Type": "Program",
            "Name": "Evening News",
            "ChannelId": "ch1",
            "ChannelName": "CNN",
            "StartDate": "2025-11-28T18:00:00Z",
            "EndDate": "2025-11-28T19:00:00Z",
            "IsSeries": True,
            "IsNews": True,
            "IsLive": False,
        }
        assert program["Id"] == "prog1"
        assert program["IsSeries"] is True
        assert program["IsNews"] is True
