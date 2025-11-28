"""Tests for Collection API methods.

Phase 19: Collection Management
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch
from urllib.parse import quote

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


class TestCollectionCreationAPI:
    """Tests for async_create_collection API method."""

    @pytest.mark.asyncio
    async def test_async_create_collection_exists(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_create_collection method exists."""
        assert hasattr(mock_client, "async_create_collection")
        assert callable(mock_client.async_create_collection)

    @pytest.mark.asyncio
    async def test_async_create_collection_returns_response(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_create_collection returns collection response."""
        mock_response = {
            "Id": "12345",
            "Name": "Test Collection",
            "Type": "BoxSet",
        }

        with patch.object(
            mock_client, "_request_post_json", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await mock_client.async_create_collection(name="Test Collection")

            assert result["Id"] == "12345"
            assert result["Name"] == "Test Collection"

    @pytest.mark.asyncio
    async def test_async_create_collection_calls_correct_endpoint(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_create_collection calls the correct API endpoint."""
        mock_response = {"Id": "12345", "Name": "My Collection"}

        with patch.object(
            mock_client, "_request_post_json", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            await mock_client.async_create_collection(name="My Collection")

            mock_request.assert_called_once()
            call_args = mock_request.call_args
            endpoint = call_args[0][0]
            assert "/Collections?" in endpoint
            assert f"Name={quote('My Collection')}" in endpoint

    @pytest.mark.asyncio
    async def test_async_create_collection_with_item_ids(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_create_collection with initial item IDs."""
        mock_response = {"Id": "12345", "Name": "Movie Collection"}

        with patch.object(
            mock_client, "_request_post_json", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            await mock_client.async_create_collection(
                name="Movie Collection",
                item_ids=["item1", "item2", "item3"],
            )

            call_args = mock_request.call_args
            endpoint = call_args[0][0]
            assert "Ids=item1,item2,item3" in endpoint

    @pytest.mark.asyncio
    async def test_async_create_collection_with_special_characters(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_create_collection with special characters in name."""
        mock_response = {"Id": "12345", "Name": "Test & Special"}

        with patch.object(
            mock_client, "_request_post_json", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            await mock_client.async_create_collection(name="Test & Special")

            call_args = mock_request.call_args
            endpoint = call_args[0][0]
            # Name should be URL encoded
            assert quote("Test & Special") in endpoint

    @pytest.mark.asyncio
    async def test_async_create_collection_without_item_ids(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_create_collection without item IDs."""
        mock_response = {"Id": "12345", "Name": "Empty Collection"}

        with patch.object(
            mock_client, "_request_post_json", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            await mock_client.async_create_collection(name="Empty Collection")

            call_args = mock_request.call_args
            endpoint = call_args[0][0]
            # Should not have Ids parameter
            assert "Ids=" not in endpoint


class TestAddToCollectionAPI:
    """Tests for async_add_to_collection API method."""

    @pytest.mark.asyncio
    async def test_async_add_to_collection_exists(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_add_to_collection method exists."""
        assert hasattr(mock_client, "async_add_to_collection")
        assert callable(mock_client.async_add_to_collection)

    @pytest.mark.asyncio
    async def test_async_add_to_collection_calls_correct_endpoint(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_add_to_collection calls the correct API endpoint."""
        with patch.object(mock_client, "_request_post", new_callable=AsyncMock) as mock_request:
            await mock_client.async_add_to_collection(
                collection_id="collection123",
                item_ids=["item1", "item2"],
            )

            mock_request.assert_called_once()
            call_args = mock_request.call_args
            endpoint = call_args[0][0]
            assert "/Collections/collection123/Items" in endpoint
            assert "Ids=item1,item2" in endpoint

    @pytest.mark.asyncio
    async def test_async_add_to_collection_single_item(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_add_to_collection with single item."""
        with patch.object(mock_client, "_request_post", new_callable=AsyncMock) as mock_request:
            await mock_client.async_add_to_collection(
                collection_id="col123",
                item_ids=["single_item"],
            )

            call_args = mock_request.call_args
            endpoint = call_args[0][0]
            assert "Ids=single_item" in endpoint


class TestRemoveFromCollectionAPI:
    """Tests for async_remove_from_collection API method."""

    @pytest.mark.asyncio
    async def test_async_remove_from_collection_exists(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_remove_from_collection method exists."""
        assert hasattr(mock_client, "async_remove_from_collection")
        assert callable(mock_client.async_remove_from_collection)

    @pytest.mark.asyncio
    async def test_async_remove_from_collection_calls_correct_endpoint(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_remove_from_collection calls the correct API endpoint."""
        with patch.object(mock_client, "_request_delete", new_callable=AsyncMock) as mock_request:
            await mock_client.async_remove_from_collection(
                collection_id="collection123",
                item_ids=["item1", "item2"],
            )

            mock_request.assert_called_once()
            call_args = mock_request.call_args
            endpoint = call_args[0][0]
            assert "/Collections/collection123/Items" in endpoint
            assert "Ids=item1,item2" in endpoint

    @pytest.mark.asyncio
    async def test_async_remove_from_collection_single_item(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_remove_from_collection with single item."""
        with patch.object(mock_client, "_request_delete", new_callable=AsyncMock) as mock_request:
            await mock_client.async_remove_from_collection(
                collection_id="col123",
                item_ids=["single_item"],
            )

            call_args = mock_request.call_args
            endpoint = call_args[0][0]
            assert "Ids=single_item" in endpoint


class TestGetCollectionsAPI:
    """Tests for async_get_collections API method."""

    @pytest.mark.asyncio
    async def test_async_get_collections_exists(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_get_collections method exists."""
        assert hasattr(mock_client, "async_get_collections")
        assert callable(mock_client.async_get_collections)

    @pytest.mark.asyncio
    async def test_async_get_collections_returns_list(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_get_collections returns list of collections."""
        mock_response = {
            "Items": [
                {"Id": "1", "Name": "Collection 1", "Type": "BoxSet", "ChildCount": 5},
                {"Id": "2", "Name": "Collection 2", "Type": "BoxSet", "ChildCount": 3},
            ],
            "TotalRecordCount": 2,
        }

        with patch.object(mock_client, "async_get_items", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await mock_client.async_get_collections(user_id="user123")

            assert len(result) == 2
            assert result[0]["Name"] == "Collection 1"
            assert result[1]["Name"] == "Collection 2"

    @pytest.mark.asyncio
    async def test_async_get_collections_calls_get_items_with_boxset(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_get_collections filters for BoxSet type."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(mock_client, "async_get_items", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await mock_client.async_get_collections(user_id="user123")

            mock_request.assert_called_once()
            call_kwargs = mock_request.call_args.kwargs
            assert call_kwargs.get("include_item_types") == "BoxSet"
            assert call_kwargs.get("recursive") is True

    @pytest.mark.asyncio
    async def test_async_get_collections_returns_empty_list(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_get_collections returns empty list when no collections."""
        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(mock_client, "async_get_items", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await mock_client.async_get_collections(user_id="user123")

            assert result == []

    @pytest.mark.asyncio
    async def test_async_get_collections_includes_child_count(
        self,
        mock_client: EmbyClient,
    ) -> None:
        """Test async_get_collections includes ChildCount in returned items."""
        mock_response = {
            "Items": [
                {"Id": "1", "Name": "Marvel", "Type": "BoxSet", "ChildCount": 10},
            ],
            "TotalRecordCount": 1,
        }

        with patch.object(mock_client, "async_get_items", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await mock_client.async_get_collections(user_id="user123")

            assert result[0].get("ChildCount") == 10
