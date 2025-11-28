"""Tests for discovery API methods."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

from custom_components.embymedia.api import EmbyClient
from custom_components.embymedia.const import (
    LatestMediaItem,
    NextUpItem,
    ResumableItem,
    SuggestionItem,
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


class TestAsyncGetNextUp:
    """Tests for async_get_next_up method."""

    async def test_get_next_up_returns_episodes(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test async_get_next_up returns next up episodes."""
        mock_response = {
            "Items": [
                {
                    "Id": "episode1",
                    "Name": "Episode 5",
                    "Type": "Episode",
                    "SeriesName": "Test Series",
                    "SeasonName": "Season 1",
                    "IndexNumber": 5,
                    "ParentIndexNumber": 1,
                    "SeriesId": "series1",
                    "SeasonId": "season1",
                    "ImageTags": {"Primary": "tag123"},
                    "UserData": {"Played": False},
                }
            ],
            "TotalRecordCount": 1,
        }

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_request:
            result = await emby_client.async_get_next_up(user_id="user123")

            mock_request.assert_called_once_with(
                "GET",
                "/Shows/NextUp?UserId=user123&Limit=10&EnableImages=true&Legacynextup=true",
            )
            assert len(result) == 1
            assert result[0]["Id"] == "episode1"
            assert result[0]["Name"] == "Episode 5"
            assert result[0]["SeriesName"] == "Test Series"

    async def test_get_next_up_with_limit(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test async_get_next_up respects limit parameter."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_request:
            result = await emby_client.async_get_next_up(user_id="user123", limit=5)

            mock_request.assert_called_once_with(
                "GET",
                "/Shows/NextUp?UserId=user123&Limit=5&EnableImages=true&Legacynextup=true",
            )
            assert result == []

    async def test_get_next_up_without_legacy_mode(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test async_get_next_up without legacy next up mode."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_request:
            result = await emby_client.async_get_next_up(
                user_id="user123",
                legacy_next_up=False,
            )

            mock_request.assert_called_once_with(
                "GET",
                "/Shows/NextUp?UserId=user123&Limit=10&EnableImages=true",
            )
            assert result == []

    async def test_get_next_up_empty_response(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test async_get_next_up with empty response."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await emby_client.async_get_next_up(user_id="user123")
            assert result == []


class TestAsyncGetResumableItems:
    """Tests for async_get_resumable_items method."""

    async def test_get_resumable_items_returns_items(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test async_get_resumable_items returns resumable items."""
        mock_response = {
            "Items": [
                {
                    "Id": "movie1",
                    "Name": "Test Movie",
                    "Type": "Movie",
                    "RunTimeTicks": 72000000000,
                    "ImageTags": {"Primary": "tag123"},
                    "UserData": {
                        "PlaybackPositionTicks": 36000000000,
                        "PlayedPercentage": 50.0,
                        "Played": False,
                    },
                },
                {
                    "Id": "episode1",
                    "Name": "Test Episode",
                    "Type": "Episode",
                    "SeriesName": "Test Series",
                    "SeriesId": "series1",
                    "IndexNumber": 3,
                    "ParentIndexNumber": 1,
                    "RunTimeTicks": 36000000000,
                    "ImageTags": {},
                    "UserData": {
                        "PlaybackPositionTicks": 18000000000,
                        "PlayedPercentage": 50.0,
                        "Played": False,
                    },
                },
            ],
            "TotalRecordCount": 2,
        }

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_request:
            result = await emby_client.async_get_resumable_items(user_id="user123")

            mock_request.assert_called_once_with(
                "GET",
                "/Users/user123/Items?Filters=IsResumable&Limit=10"
                "&SortBy=DatePlayed&SortOrder=Descending&Recursive=true",
            )
            assert len(result) == 2
            assert result[0]["Id"] == "movie1"
            assert result[0]["Type"] == "Movie"
            assert result[1]["SeriesName"] == "Test Series"

    async def test_get_resumable_items_with_item_types(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test async_get_resumable_items with item type filter."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_request:
            result = await emby_client.async_get_resumable_items(
                user_id="user123",
                include_item_types="Movie",
            )

            mock_request.assert_called_once_with(
                "GET",
                "/Users/user123/Items?Filters=IsResumable&Limit=10"
                "&SortBy=DatePlayed&SortOrder=Descending&Recursive=true"
                "&IncludeItemTypes=Movie",
            )
            assert result == []

    async def test_get_resumable_items_empty_response(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test async_get_resumable_items with empty response."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await emby_client.async_get_resumable_items(user_id="user123")
            assert result == []


class TestAsyncGetLatestMedia:
    """Tests for async_get_latest_media method."""

    async def test_get_latest_media_movies(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test async_get_latest_media returns latest movies."""
        # Note: /Items/Latest returns array directly, not wrapped in Items
        mock_response = [
            {
                "Id": "movie1",
                "Name": "New Movie",
                "Type": "Movie",
                "ProductionYear": 2024,
                "ImageTags": {"Primary": "tag123"},
                "DateCreated": "2024-01-15T10:00:00Z",
            }
        ]

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_request:
            result = await emby_client.async_get_latest_media(
                user_id="user123",
                include_item_types="Movie",
            )

            mock_request.assert_called_once_with(
                "GET",
                "/Users/user123/Items/Latest?Limit=10&IncludeItemTypes=Movie",
            )
            assert len(result) == 1
            assert result[0]["Id"] == "movie1"
            assert result[0]["Name"] == "New Movie"

    async def test_get_latest_media_episodes(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test async_get_latest_media returns latest episodes."""
        mock_response = [
            {
                "Id": "episode1",
                "Name": "New Episode",
                "Type": "Episode",
                "SeriesName": "Test Series",
                "IndexNumber": 5,
                "ParentIndexNumber": 2,
                "ImageTags": {},
                "DateCreated": "2024-01-15T10:00:00Z",
            }
        ]

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_request:
            result = await emby_client.async_get_latest_media(
                user_id="user123",
                include_item_types="Episode",
            )

            mock_request.assert_called_once_with(
                "GET",
                "/Users/user123/Items/Latest?Limit=10&IncludeItemTypes=Episode",
            )
            assert len(result) == 1
            assert result[0]["SeriesName"] == "Test Series"

    async def test_get_latest_media_with_parent_id(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test async_get_latest_media with parent ID filter."""
        mock_response: list[LatestMediaItem] = []

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_request:
            result = await emby_client.async_get_latest_media(
                user_id="user123",
                parent_id="library123",
            )

            mock_request.assert_called_once_with(
                "GET",
                "/Users/user123/Items/Latest?Limit=10&ParentId=library123",
            )
            assert result == []

    async def test_get_latest_media_empty_response(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test async_get_latest_media with empty response."""
        mock_response: list[LatestMediaItem] = []

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await emby_client.async_get_latest_media(user_id="user123")
            assert result == []


class TestAsyncGetSuggestions:
    """Tests for async_get_suggestions method."""

    async def test_get_suggestions_returns_items(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test async_get_suggestions returns suggestions."""
        mock_response = {
            "Items": [
                {
                    "Id": "movie1",
                    "Name": "Suggested Movie",
                    "Type": "Movie",
                    "ProductionYear": 2023,
                    "CommunityRating": 8.5,
                    "ImageTags": {"Primary": "tag123"},
                }
            ],
            "TotalRecordCount": 1,
        }

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_request:
            result = await emby_client.async_get_suggestions(user_id="user123")

            mock_request.assert_called_once_with(
                "GET",
                "/Users/user123/Suggestions?Limit=10",
            )
            assert len(result) == 1
            assert result[0]["Id"] == "movie1"
            assert result[0]["Name"] == "Suggested Movie"

    async def test_get_suggestions_with_type_filter(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test async_get_suggestions with type filter."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_request:
            result = await emby_client.async_get_suggestions(
                user_id="user123",
                suggestion_type="Movie",
            )

            mock_request.assert_called_once_with(
                "GET",
                "/Users/user123/Suggestions?Limit=10&Type=Movie",
            )
            assert result == []

    async def test_get_suggestions_empty_response(
        self,
        emby_client: EmbyClient,
    ) -> None:
        """Test async_get_suggestions with empty response."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(
            emby_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await emby_client.async_get_suggestions(user_id="user123")
            assert result == []


class TestTypedDictStructures:
    """Tests that TypedDicts have correct structure."""

    def test_next_up_item_type_exists(self) -> None:
        """Test NextUpItem TypedDict is importable and has expected fields."""
        # Test that we can create a NextUpItem
        item: NextUpItem = {
            "Id": "test",
            "Name": "Test Episode",
            "Type": "Episode",
            "SeriesName": "Test Series",
            "SeasonName": "Season 1",
            "IndexNumber": 1,
            "ParentIndexNumber": 1,
        }
        assert item["Id"] == "test"

    def test_resumable_item_type_exists(self) -> None:
        """Test ResumableItem TypedDict is importable and has expected fields."""
        item: ResumableItem = {
            "Id": "test",
            "Name": "Test Movie",
            "Type": "Movie",
            "RunTimeTicks": 72000000000,
        }
        assert item["Id"] == "test"

    def test_latest_media_item_type_exists(self) -> None:
        """Test LatestMediaItem TypedDict is importable and has expected fields."""
        item: LatestMediaItem = {
            "Id": "test",
            "Name": "New Movie",
            "Type": "Movie",
            "ProductionYear": 2024,
        }
        assert item["Id"] == "test"

    def test_suggestion_item_type_exists(self) -> None:
        """Test SuggestionItem TypedDict is importable and has expected fields."""
        item: SuggestionItem = {
            "Id": "test",
            "Name": "Suggested Movie",
            "Type": "Movie",
            "CommunityRating": 8.5,
        }
        assert item["Id"] == "test"
