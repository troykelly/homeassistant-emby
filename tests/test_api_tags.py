"""Tests for Emby API tag methods.

Phase 19: Collection Management - Task 19.6
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientSession

from custom_components.embymedia.api import EmbyClient
from custom_components.embymedia.exceptions import (
    EmbyAuthenticationError,
    EmbyConnectionError,
)


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock aiohttp session."""
    return MagicMock(spec=ClientSession)


@pytest.fixture
def emby_client(mock_session: MagicMock) -> EmbyClient:
    """Create an EmbyClient with mock session."""
    return EmbyClient(
        host="emby.local",
        port=8096,
        api_key="test-api-key",
        session=mock_session,
    )


class TestAsyncGetTags:
    """Tests for async_get_tags method."""

    async def test_get_tags_basic(self, emby_client: EmbyClient) -> None:
        """Test fetching tags without filters."""
        mock_response = {
            "Items": [
                {
                    "Id": "tag-1",
                    "Name": "Favorite",
                    "Type": "Tag",
                },
                {
                    "Id": "tag-2",
                    "Name": "Watch Later",
                    "Type": "Tag",
                },
            ],
            "TotalRecordCount": 2,
        }

        with patch.object(
            emby_client, "_request", new_callable=AsyncMock, return_value=mock_response
        ) as mock_request:
            result = await emby_client.async_get_tags(user_id="user-123")

            assert len(result) == 2
            assert result[0]["Name"] == "Favorite"
            assert result[1]["Name"] == "Watch Later"

            # Verify API call
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert "Tags" in call_args[0][1]
            assert "UserId=user-123" in call_args[0][1]

    async def test_get_tags_with_parent_id(self, emby_client: EmbyClient) -> None:
        """Test fetching tags filtered by parent library."""
        mock_response = {
            "Items": [{"Id": "tag-1", "Name": "Tag", "Type": "Tag"}],
            "TotalRecordCount": 1,
        }

        with patch.object(
            emby_client, "_request", new_callable=AsyncMock, return_value=mock_response
        ) as mock_request:
            result = await emby_client.async_get_tags(
                user_id="user-123",
                parent_id="library-movies",
            )

            assert len(result) == 1
            call_args = mock_request.call_args
            assert "ParentId=library-movies" in call_args[0][1]

    async def test_get_tags_with_item_types(self, emby_client: EmbyClient) -> None:
        """Test fetching tags filtered by item types."""
        mock_response = {
            "Items": [{"Id": "tag-1", "Name": "Movie Tag", "Type": "Tag"}],
            "TotalRecordCount": 1,
        }

        with patch.object(
            emby_client, "_request", new_callable=AsyncMock, return_value=mock_response
        ) as mock_request:
            result = await emby_client.async_get_tags(
                user_id="user-123",
                include_item_types="Movie",
            )

            assert len(result) == 1
            call_args = mock_request.call_args
            assert "IncludeItemTypes=Movie" in call_args[0][1]

    async def test_get_tags_cached(self, emby_client: EmbyClient) -> None:
        """Test that tags list is cached."""
        mock_response = {
            "Items": [{"Id": "tag-1", "Name": "Tag", "Type": "Tag"}],
            "TotalRecordCount": 1,
        }

        with patch.object(
            emby_client, "_request", new_callable=AsyncMock, return_value=mock_response
        ) as mock_request:
            # First call
            result1 = await emby_client.async_get_tags(user_id="user-123")
            # Second call should hit cache
            result2 = await emby_client.async_get_tags(user_id="user-123")

            assert result1 == result2
            # Should only make one API call due to caching
            assert mock_request.call_count == 1

    async def test_get_tags_connection_error(self, emby_client: EmbyClient) -> None:
        """Test connection error handling."""
        with (
            patch.object(
                emby_client,
                "_request",
                new_callable=AsyncMock,
                side_effect=EmbyConnectionError("Connection failed"),
            ),
            pytest.raises(EmbyConnectionError),
        ):
            await emby_client.async_get_tags(user_id="user-123")

    async def test_get_tags_auth_error(self, emby_client: EmbyClient) -> None:
        """Test authentication error handling."""
        with (
            patch.object(
                emby_client,
                "_request",
                new_callable=AsyncMock,
                side_effect=EmbyAuthenticationError("Auth failed"),
            ),
            pytest.raises(EmbyAuthenticationError),
        ):
            await emby_client.async_get_tags(user_id="user-123")


class TestAsyncGetItemsByTag:
    """Tests for async_get_items_by_tag method."""

    async def test_get_items_by_tag_basic(self, emby_client: EmbyClient) -> None:
        """Test fetching items by tag."""
        mock_response = {
            "Items": [
                {
                    "Id": "movie-1",
                    "Name": "Tagged Movie 1",
                    "Type": "Movie",
                },
                {
                    "Id": "movie-2",
                    "Name": "Tagged Movie 2",
                    "Type": "Movie",
                },
            ],
            "TotalRecordCount": 2,
        }

        with patch.object(
            emby_client, "_request", new_callable=AsyncMock, return_value=mock_response
        ) as mock_request:
            result = await emby_client.async_get_items_by_tag(
                user_id="user-123",
                tag_id="tag-1",
            )

            assert len(result) == 2
            assert result[0]["Name"] == "Tagged Movie 1"
            assert result[1]["Name"] == "Tagged Movie 2"

            # Verify API call
            call_args = mock_request.call_args
            assert "TagIds=tag-1" in call_args[0][1]

    async def test_get_items_by_tag_with_parent_id(self, emby_client: EmbyClient) -> None:
        """Test fetching items by tag with parent library filter."""
        mock_response = {
            "Items": [{"Id": "movie-1", "Name": "Movie", "Type": "Movie"}],
            "TotalRecordCount": 1,
        }

        with patch.object(
            emby_client, "_request", new_callable=AsyncMock, return_value=mock_response
        ) as mock_request:
            result = await emby_client.async_get_items_by_tag(
                user_id="user-123",
                tag_id="tag-1",
                parent_id="library-movies",
            )

            assert len(result) == 1
            call_args = mock_request.call_args
            assert "ParentId=library-movies" in call_args[0][1]

    async def test_get_items_by_tag_with_type_filter(self, emby_client: EmbyClient) -> None:
        """Test fetching items by tag with type filter."""
        mock_response = {
            "Items": [{"Id": "movie-1", "Name": "Movie", "Type": "Movie"}],
            "TotalRecordCount": 1,
        }

        with patch.object(
            emby_client, "_request", new_callable=AsyncMock, return_value=mock_response
        ) as mock_request:
            await emby_client.async_get_items_by_tag(
                user_id="user-123",
                tag_id="tag-1",
                include_item_types="Movie",
            )

            call_args = mock_request.call_args
            assert "IncludeItemTypes=Movie" in call_args[0][1]

    async def test_get_items_by_tag_with_limit(self, emby_client: EmbyClient) -> None:
        """Test fetching items by tag with custom limit."""
        mock_response = {
            "Items": [{"Id": "movie-1", "Name": "Movie", "Type": "Movie"}],
            "TotalRecordCount": 1,
        }

        with patch.object(
            emby_client, "_request", new_callable=AsyncMock, return_value=mock_response
        ) as mock_request:
            await emby_client.async_get_items_by_tag(
                user_id="user-123",
                tag_id="tag-1",
                limit=50,
            )

            call_args = mock_request.call_args
            assert "Limit=50" in call_args[0][1]

    async def test_get_items_by_tag_empty(self, emby_client: EmbyClient) -> None:
        """Test fetching items when tag has no items."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(
            emby_client, "_request", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await emby_client.async_get_items_by_tag(
                user_id="user-123",
                tag_id="tag-unknown",
            )

            assert len(result) == 0

    async def test_get_items_by_tag_connection_error(self, emby_client: EmbyClient) -> None:
        """Test connection error handling."""
        with (
            patch.object(
                emby_client,
                "_request",
                new_callable=AsyncMock,
                side_effect=EmbyConnectionError("Connection failed"),
            ),
            pytest.raises(EmbyConnectionError),
        ):
            await emby_client.async_get_items_by_tag(
                user_id="user-123",
                tag_id="tag-1",
            )
