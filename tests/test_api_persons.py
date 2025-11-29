"""Tests for Emby API person methods.

Phase 19: Collection Management - Task 19.4
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


class TestAsyncGetPersons:
    """Tests for async_get_persons method."""

    async def test_get_persons_basic(self, emby_client: EmbyClient) -> None:
        """Test fetching persons without filters."""
        mock_response = {
            "Items": [
                {
                    "Id": "person-1",
                    "Name": "Tom Hanks",
                    "Type": "Person",
                },
                {
                    "Id": "person-2",
                    "Name": "Steven Spielberg",
                    "Type": "Person",
                },
            ],
            "TotalRecordCount": 2,
            "StartIndex": 0,
        }

        with patch.object(
            emby_client, "_request", new_callable=AsyncMock, return_value=mock_response
        ) as mock_request:
            result = await emby_client.async_get_persons(user_id="user-123")

            assert result["TotalRecordCount"] == 2
            assert len(result["Items"]) == 2
            assert result["Items"][0]["Name"] == "Tom Hanks"
            assert result["Items"][1]["Name"] == "Steven Spielberg"

            # Verify API call
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert "Persons" in call_args[0][1]
            assert "UserId=user-123" in call_args[0][1]

    async def test_get_persons_with_parent_id(self, emby_client: EmbyClient) -> None:
        """Test fetching persons filtered by parent library."""
        mock_response = {
            "Items": [{"Id": "person-1", "Name": "Actor", "Type": "Person"}],
            "TotalRecordCount": 1,
            "StartIndex": 0,
        }

        with patch.object(
            emby_client, "_request", new_callable=AsyncMock, return_value=mock_response
        ) as mock_request:
            result = await emby_client.async_get_persons(
                user_id="user-123",
                parent_id="library-movies",
            )

            assert result["TotalRecordCount"] == 1
            call_args = mock_request.call_args
            assert "ParentId=library-movies" in call_args[0][1]

    async def test_get_persons_with_person_types(self, emby_client: EmbyClient) -> None:
        """Test fetching persons filtered by type (Actor, Director)."""
        mock_response = {
            "Items": [{"Id": "person-1", "Name": "Director", "Type": "Person"}],
            "TotalRecordCount": 1,
            "StartIndex": 0,
        }

        with patch.object(
            emby_client, "_request", new_callable=AsyncMock, return_value=mock_response
        ) as mock_request:
            result = await emby_client.async_get_persons(
                user_id="user-123",
                person_types="Director",
            )

            assert result["TotalRecordCount"] == 1
            call_args = mock_request.call_args
            assert "PersonTypes=Director" in call_args[0][1]

    async def test_get_persons_with_pagination(self, emby_client: EmbyClient) -> None:
        """Test fetching persons with limit and offset."""
        mock_response = {
            "Items": [{"Id": "person-1", "Name": "Actor", "Type": "Person"}],
            "TotalRecordCount": 100,
            "StartIndex": 50,
        }

        with patch.object(
            emby_client, "_request", new_callable=AsyncMock, return_value=mock_response
        ) as mock_request:
            result = await emby_client.async_get_persons(
                user_id="user-123",
                limit=25,
                start_index=50,
            )

            assert result["StartIndex"] == 50
            call_args = mock_request.call_args
            assert "Limit=25" in call_args[0][1]
            assert "StartIndex=50" in call_args[0][1]

    async def test_get_persons_cached(self, emby_client: EmbyClient) -> None:
        """Test that persons list is cached."""
        mock_response = {
            "Items": [{"Id": "person-1", "Name": "Actor", "Type": "Person"}],
            "TotalRecordCount": 1,
            "StartIndex": 0,
        }

        with patch.object(
            emby_client, "_request", new_callable=AsyncMock, return_value=mock_response
        ) as mock_request:
            # First call
            result1 = await emby_client.async_get_persons(user_id="user-123")
            # Second call should hit cache
            result2 = await emby_client.async_get_persons(user_id="user-123")

            assert result1 == result2
            # Should only make one API call due to caching
            assert mock_request.call_count == 1

    async def test_get_persons_connection_error(self, emby_client: EmbyClient) -> None:
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
            await emby_client.async_get_persons(user_id="user-123")

    async def test_get_persons_auth_error(self, emby_client: EmbyClient) -> None:
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
            await emby_client.async_get_persons(user_id="user-123")


class TestAsyncGetPersonItems:
    """Tests for async_get_person_items method."""

    async def test_get_person_items_basic(self, emby_client: EmbyClient) -> None:
        """Test fetching items for a person."""
        mock_response = {
            "Items": [
                {
                    "Id": "movie-1",
                    "Name": "Forrest Gump",
                    "Type": "Movie",
                },
                {
                    "Id": "movie-2",
                    "Name": "Cast Away",
                    "Type": "Movie",
                },
            ],
            "TotalRecordCount": 2,
        }

        with patch.object(
            emby_client, "_request", new_callable=AsyncMock, return_value=mock_response
        ) as mock_request:
            result = await emby_client.async_get_person_items(
                user_id="user-123",
                person_id="person-tom-hanks",
            )

            assert len(result) == 2
            assert result[0]["Name"] == "Forrest Gump"
            assert result[1]["Name"] == "Cast Away"

            # Verify API call
            call_args = mock_request.call_args
            assert "PersonIds=person-tom-hanks" in call_args[0][1]

    async def test_get_person_items_with_type_filter(self, emby_client: EmbyClient) -> None:
        """Test fetching items with type filter."""
        mock_response = {
            "Items": [{"Id": "movie-1", "Name": "Movie", "Type": "Movie"}],
            "TotalRecordCount": 1,
        }

        with patch.object(
            emby_client, "_request", new_callable=AsyncMock, return_value=mock_response
        ) as mock_request:
            result = await emby_client.async_get_person_items(
                user_id="user-123",
                person_id="person-1",
                include_item_types="Movie",
            )

            assert len(result) == 1
            call_args = mock_request.call_args
            assert "IncludeItemTypes=Movie" in call_args[0][1]

    async def test_get_person_items_with_limit(self, emby_client: EmbyClient) -> None:
        """Test fetching items with custom limit."""
        mock_response = {
            "Items": [{"Id": "movie-1", "Name": "Movie", "Type": "Movie"}],
            "TotalRecordCount": 1,
        }

        with patch.object(
            emby_client, "_request", new_callable=AsyncMock, return_value=mock_response
        ) as mock_request:
            await emby_client.async_get_person_items(
                user_id="user-123",
                person_id="person-1",
                limit=50,
            )

            call_args = mock_request.call_args
            assert "Limit=50" in call_args[0][1]

    async def test_get_person_items_empty(self, emby_client: EmbyClient) -> None:
        """Test fetching items when person has no items."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(
            emby_client, "_request", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await emby_client.async_get_person_items(
                user_id="user-123",
                person_id="person-unknown",
            )

            assert len(result) == 0

    async def test_get_person_items_connection_error(self, emby_client: EmbyClient) -> None:
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
            await emby_client.async_get_person_items(
                user_id="user-123",
                person_id="person-1",
            )
