"""Tests for Phase 12 API methods for sensor platform."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

from custom_components.embymedia.api import EmbyClient
from custom_components.embymedia.const import (
    EmbyItemCounts,
    EmbyScheduledTask,
    EmbyVirtualFolder,
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


class TestAsyncGetItemCounts:
    """Tests for async_get_item_counts API method."""

    async def test_get_item_counts_success(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test successful retrieval of item counts."""
        mock_response: EmbyItemCounts = {
            "MovieCount": 1209,
            "SeriesCount": 374,
            "EpisodeCount": 4620,
            "ArtistCount": 500,
            "AlbumCount": 800,
            "SongCount": 14341,
            "GameCount": 0,
            "GameSystemCount": 0,
            "TrailerCount": 10,
            "MusicVideoCount": 25,
            "BoxSetCount": 15,
            "BookCount": 100,
            "ItemCount": 21994,
        }

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_request:
            result = await emby_client.async_get_item_counts()

            mock_request.assert_called_once_with("GET", "/Items/Counts")
            assert result["MovieCount"] == 1209
            assert result["SeriesCount"] == 374
            assert result["EpisodeCount"] == 4620
            assert result["SongCount"] == 14341

    async def test_get_item_counts_with_user_id(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test item counts retrieval with user ID filter."""
        mock_response: EmbyItemCounts = {
            "MovieCount": 500,
            "SeriesCount": 100,
            "EpisodeCount": 1000,
            "ArtistCount": 200,
            "AlbumCount": 300,
            "SongCount": 5000,
            "GameCount": 0,
            "GameSystemCount": 0,
            "TrailerCount": 5,
            "MusicVideoCount": 10,
            "BoxSetCount": 5,
            "BookCount": 50,
            "ItemCount": 7170,
        }

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_request:
            result = await emby_client.async_get_item_counts(user_id="user-123")

            mock_request.assert_called_once_with("GET", "/Items/Counts?UserId=user-123")
            assert result["MovieCount"] == 500


class TestAsyncGetScheduledTasks:
    """Tests for async_get_scheduled_tasks API method."""

    async def test_get_scheduled_tasks_success(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test successful retrieval of scheduled tasks."""
        mock_response: list[EmbyScheduledTask] = [
            {
                "Name": "Scan media library",
                "State": "Idle",
                "Id": "task-1",
                "Description": "Scans all libraries",
                "Category": "Library",
                "IsHidden": False,
                "Key": "RefreshLibrary",
                "Triggers": [],
            },
            {
                "Name": "Clean cache",
                "State": "Running",
                "Id": "task-2",
                "Description": "Cleans cache files",
                "Category": "Maintenance",
                "IsHidden": False,
                "Key": "CleanCache",
                "Triggers": [],
                "CurrentProgressPercentage": 45.5,
            },
        ]

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_request:
            result = await emby_client.async_get_scheduled_tasks()

            mock_request.assert_called_once_with("GET", "/ScheduledTasks")
            assert len(result) == 2
            assert result[0]["Name"] == "Scan media library"
            assert result[0]["State"] == "Idle"
            assert result[1]["State"] == "Running"
            assert result[1]["CurrentProgressPercentage"] == 45.5

    async def test_get_scheduled_tasks_with_hidden(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test scheduled tasks including hidden tasks."""
        mock_response: list[EmbyScheduledTask] = [
            {
                "Name": "Internal task",
                "State": "Idle",
                "Id": "task-hidden",
                "Description": "Internal",
                "Category": "System",
                "IsHidden": True,
                "Key": "Internal",
                "Triggers": [],
            },
        ]

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_request:
            result = await emby_client.async_get_scheduled_tasks(include_hidden=True)

            mock_request.assert_called_once_with("GET", "/ScheduledTasks?IsHidden=true")
            assert result[0]["IsHidden"] is True


class TestAsyncGetVirtualFolders:
    """Tests for async_get_virtual_folders API method."""

    async def test_get_virtual_folders_success(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test successful retrieval of virtual folders."""
        mock_response: list[EmbyVirtualFolder] = [
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
                "Locations": ["/media/tv", "/media/tv2"],
            },
            {
                "Name": "Music",
                "ItemId": "lib-music",
                "CollectionType": "music",
                "Locations": ["/media/music"],
                "RefreshProgress": 50.0,
                "RefreshStatus": "Active",
            },
        ]

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_request:
            result = await emby_client.async_get_virtual_folders()

            mock_request.assert_called_once_with("GET", "/Library/VirtualFolders")
            assert len(result) == 3
            assert result[0]["Name"] == "Movies"
            assert result[0]["CollectionType"] == "movies"
            assert result[2]["RefreshProgress"] == 50.0


class TestAsyncGetUserItemCount:
    """Tests for async_get_user_item_count API method."""

    async def test_get_user_favorites_count(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test counting user favorite items."""
        mock_response = {
            "Items": [],
            "TotalRecordCount": 42,
            "StartIndex": 0,
        }

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_request:
            result = await emby_client.async_get_user_item_count(
                user_id="user-123",
                filters="IsFavorite",
            )

            mock_request.assert_called_once_with(
                "GET",
                "/Users/user-123/Items?Filters=IsFavorite&Limit=0&Recursive=true",
            )
            assert result == 42

    async def test_get_user_played_count(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test counting user played/watched items."""
        mock_response = {
            "Items": [],
            "TotalRecordCount": 1500,
            "StartIndex": 0,
        }

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_request:
            result = await emby_client.async_get_user_item_count(
                user_id="user-456",
                filters="IsPlayed",
            )

            mock_request.assert_called_once_with(
                "GET",
                "/Users/user-456/Items?Filters=IsPlayed&Limit=0&Recursive=true",
            )
            assert result == 1500

    async def test_get_user_resumable_count(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test counting user resumable/in-progress items."""
        mock_response = {
            "Items": [],
            "TotalRecordCount": 8,
            "StartIndex": 0,
        }

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_request:
            result = await emby_client.async_get_user_item_count(
                user_id="user-789",
                filters="IsResumable",
            )

            mock_request.assert_called_once_with(
                "GET",
                "/Users/user-789/Items?Filters=IsResumable&Limit=0&Recursive=true",
            )
            assert result == 8

    async def test_get_user_item_count_with_parent_id(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test counting items within a specific library."""
        mock_response = {
            "Items": [],
            "TotalRecordCount": 250,
            "StartIndex": 0,
        }

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_request:
            result = await emby_client.async_get_user_item_count(
                user_id="user-123",
                parent_id="lib-movies",
            )

            mock_request.assert_called_once_with(
                "GET",
                "/Users/user-123/Items?Limit=0&Recursive=true&ParentId=lib-movies",
            )
            assert result == 250


class TestAsyncGetArtistCount:
    """Tests for async_get_artist_count API method.

    This method works around the Emby /Items/Counts endpoint bug where
    ArtistCount always returns 0. Instead, it queries the /Artists endpoint
    with Limit=0 to get the accurate TotalRecordCount.

    See: https://emby.media/community/index.php?/topic/98298-boxset-count-now-broken-in-http-api/
    """

    async def test_get_artist_count_success(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test successful retrieval of artist count."""
        mock_response = {
            "Items": [],
            "TotalRecordCount": 956,
        }

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_request:
            result = await emby_client.async_get_artist_count()

            mock_request.assert_called_once_with("GET", "/Artists?Limit=0")
            assert result == 956

    async def test_get_artist_count_empty_library(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test artist count returns 0 for empty music library."""
        mock_response = {
            "Items": [],
            "TotalRecordCount": 0,
        }

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_request:
            result = await emby_client.async_get_artist_count()

            mock_request.assert_called_once_with("GET", "/Artists?Limit=0")
            assert result == 0

    async def test_get_artist_count_with_user_id(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test artist count with user ID filter."""
        mock_response = {
            "Items": [],
            "TotalRecordCount": 500,
        }

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_request:
            result = await emby_client.async_get_artist_count(user_id="user-123")

            mock_request.assert_called_once_with("GET", "/Artists?Limit=0&UserId=user-123")
            assert result == 500
