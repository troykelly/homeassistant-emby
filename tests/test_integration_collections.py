"""Integration tests for Phase 19: Collection Management features.

Tests complete workflows for:
- Collection creation and management
- Person browsing
- Tag browsing
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.media_player import BrowseMedia, MediaType
from homeassistant.core import HomeAssistant

from custom_components.embymedia.const import DOMAIN

if TYPE_CHECKING:
    from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry for testing."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "emby.local",
            "port": 8096,
            "api_key": "test-api-key",
            "user_id": "test-user-id",
        },
        unique_id="test-server-id",
    )


@pytest.fixture
def mock_coordinator(hass: HomeAssistant) -> MagicMock:
    """Create a mock coordinator with client."""
    coordinator = MagicMock()
    coordinator.server_id = "test-server-id"
    coordinator.server_name = "Test Server"
    coordinator.last_update_success = True
    coordinator.data = {}
    coordinator.get_session = MagicMock(return_value=None)
    coordinator.async_add_listener = MagicMock(return_value=MagicMock())

    # Mock client
    client = MagicMock()
    coordinator.client = client

    return coordinator


class TestCollectionWorkflow:
    """Test complete collection management workflow."""

    async def test_collection_create_and_browse_workflow(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test complete collection workflow.

        1. Create collection via API
        2. Add items to collection
        3. Browse collection in media player
        """
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        client = mock_coordinator.client

        # Step 1: Mock collection creation
        client.async_create_collection = AsyncMock(
            return_value={
                "Id": "collection-123",
                "Name": "Marvel Movies",
                "Type": "BoxSet",
            }
        )

        # Step 2: Mock add to collection
        client.async_add_to_collection = AsyncMock()

        # Step 3: Mock browse collection items
        client.async_get_collection_items = AsyncMock(
            return_value=[
                {
                    "Id": "movie-1",
                    "Name": "Iron Man",
                    "Type": "Movie",
                    "ImageTags": {"Primary": "tag1"},
                },
                {
                    "Id": "movie-2",
                    "Name": "Thor",
                    "Type": "Movie",
                    "ImageTags": {"Primary": "tag2"},
                },
            ]
        )

        # Mock get_image_url for thumbnails
        client.get_image_url = MagicMock(return_value="http://emby.local/image")

        # Create collection
        result = await client.async_create_collection(
            name="Marvel Movies",
            item_ids=["movie-1", "movie-2"],
        )

        assert result["Id"] == "collection-123"
        assert result["Name"] == "Marvel Movies"

        # Add more items
        await client.async_add_to_collection(
            collection_id="collection-123",
            item_ids=["movie-3"],
        )

        client.async_add_to_collection.assert_called_once_with(
            collection_id="collection-123",
            item_ids=["movie-3"],
        )

        # Browse collection
        media_player = EmbyMediaPlayer(mock_coordinator, "test-device")
        browse_result = await media_player._async_browse_collection("test-user", "collection-123")

        assert isinstance(browse_result, BrowseMedia)
        assert browse_result.can_expand is True
        assert len(browse_result.children) == 2
        assert browse_result.children[0].title == "Iron Man"
        assert browse_result.children[1].title == "Thor"

    async def test_collection_sensor_integration(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test collection sensor with coordinator data."""
        from custom_components.embymedia.sensor import EmbyCollectionCountSensor

        # Create mock coordinator with collection data matching actual implementation
        coordinator = MagicMock()
        coordinator.server_id = "test-server"
        coordinator.data = {
            "collection_count": 3,
        }
        coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        # Create sensor with correct signature
        sensor = EmbyCollectionCountSensor(
            coordinator=coordinator,
            server_name="Test Server",
        )

        # Verify state
        assert sensor.native_value == 3
        assert sensor._attr_unique_id == "test-server_collection_count"


class TestPersonBrowsingWorkflow:
    """Test person browsing workflow."""

    async def test_person_browse_full_workflow(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test complete person browsing workflow.

        1. Browse to movie library
        2. Select People category
        3. Select a person
        4. View filmography
        """
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        client = mock_coordinator.client

        # Mock persons list
        client.async_get_persons = AsyncMock(
            return_value={
                "Items": [
                    {
                        "Id": "person-1",
                        "Name": "Robert Downey Jr.",
                        "Type": "Person",
                        "ImageTags": {"Primary": "actor-img"},
                    },
                    {
                        "Id": "person-2",
                        "Name": "Chris Evans",
                        "Type": "Person",
                        "ImageTags": {},
                    },
                ],
                "TotalRecordCount": 2,
                "StartIndex": 0,
            }
        )

        # Mock person's filmography
        client.async_get_person_items = AsyncMock(
            return_value=[
                {"Id": "movie-1", "Name": "Iron Man", "Type": "Movie", "ImageTags": {}},
                {"Id": "movie-2", "Name": "Avengers", "Type": "Movie", "ImageTags": {}},
                {
                    "Id": "movie-3",
                    "Name": "Endgame",
                    "Type": "Movie",
                    "ImageTags": {},
                },
            ]
        )

        client.get_image_url = MagicMock(return_value="http://emby.local/image")

        # Create media player
        media_player = EmbyMediaPlayer(mock_coordinator, "test-device")

        # Step 1: Browse People category
        people_result = await media_player._async_browse_movie_people("test-user", "library-movies")

        assert isinstance(people_result, BrowseMedia)
        assert people_result.title == "People"
        assert len(people_result.children) == 2
        assert people_result.children[0].title == "Robert Downey Jr."
        assert people_result.children[1].title == "Chris Evans"

        # Step 2: Browse person's filmography
        filmography_result = await media_player._async_browse_person(
            "test-user", "person-1", "library-movies"
        )

        assert isinstance(filmography_result, BrowseMedia)
        assert filmography_result.title == "Filmography"
        assert len(filmography_result.children) == 3
        assert filmography_result.children[0].title == "Iron Man"
        assert filmography_result.children[1].title == "Avengers"
        assert filmography_result.children[2].title == "Endgame"

    async def test_person_browse_with_different_roles(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test browsing persons with different roles (actor, director)."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        client = mock_coordinator.client

        # Mock persons with different roles
        client.async_get_persons = AsyncMock(
            return_value={
                "Items": [
                    {
                        "Id": "person-1",
                        "Name": "Christopher Nolan",
                        "Type": "Person",
                        "Role": "Director",
                        "ImageTags": {},
                    },
                    {
                        "Id": "person-2",
                        "Name": "Hans Zimmer",
                        "Type": "Person",
                        "Role": "Composer",
                        "ImageTags": {},
                    },
                ],
                "TotalRecordCount": 2,
                "StartIndex": 0,
            }
        )

        client.get_image_url = MagicMock(return_value=None)

        media_player = EmbyMediaPlayer(mock_coordinator, "test-device")

        result = await media_player._async_browse_movie_people("test-user", "lib-123")

        assert len(result.children) == 2
        # Verify person names are displayed
        person_names = [child.title for child in result.children]
        assert "Christopher Nolan" in person_names
        assert "Hans Zimmer" in person_names


class TestTagBrowsingWorkflow:
    """Test tag browsing workflow."""

    async def test_tag_browse_full_workflow(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test complete tag browsing workflow.

        1. Browse to library
        2. Select Tags category
        3. Select a tag
        4. View tagged items
        """
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        client = mock_coordinator.client

        # Mock tags list
        client.async_get_tags = AsyncMock(
            return_value=[
                {"Id": "tag-1", "Name": "Favorite", "Type": "Tag"},
                {"Id": "tag-2", "Name": "Watch Later", "Type": "Tag"},
                {"Id": "tag-3", "Name": "Family Movie", "Type": "Tag"},
            ]
        )

        # Mock items by tag
        client.async_get_items_by_tag = AsyncMock(
            return_value=[
                {"Id": "movie-1", "Name": "The Lion King", "Type": "Movie", "ImageTags": {}},
                {"Id": "movie-2", "Name": "Finding Nemo", "Type": "Movie", "ImageTags": {}},
            ]
        )

        client.get_image_url = MagicMock(return_value=None)

        media_player = EmbyMediaPlayer(mock_coordinator, "test-device")

        # Step 1: Browse Tags category
        tags_result = await media_player._async_browse_movie_tags("test-user", "library-movies")

        assert isinstance(tags_result, BrowseMedia)
        assert tags_result.title == "Tags"
        assert len(tags_result.children) == 3
        assert tags_result.children[0].title == "Favorite"
        assert tags_result.children[1].title == "Watch Later"
        assert tags_result.children[2].title == "Family Movie"

        # Step 2: Browse items with specific tag
        tagged_result = await media_player._async_browse_movies_by_tag(
            "test-user", "library-movies", "tag-3"
        )

        assert isinstance(tagged_result, BrowseMedia)
        assert tagged_result.title == "Movies by Tag"
        assert len(tagged_result.children) == 2
        assert tagged_result.children[0].title == "The Lion King"
        assert tagged_result.children[1].title == "Finding Nemo"

    async def test_tag_browse_empty_tags(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test browsing tags when no tags exist."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        client = mock_coordinator.client
        client.async_get_tags = AsyncMock(return_value=[])
        client.get_image_url = MagicMock(return_value=None)

        media_player = EmbyMediaPlayer(mock_coordinator, "test-device")

        result = await media_player._async_browse_movie_tags("test-user", "lib-123")

        assert isinstance(result, BrowseMedia)
        assert result.title == "Tags"
        assert len(result.children) == 0

    async def test_tag_browse_empty_items(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test browsing a tag with no items."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        client = mock_coordinator.client
        client.async_get_items_by_tag = AsyncMock(return_value=[])
        client.get_image_url = MagicMock(return_value=None)

        media_player = EmbyMediaPlayer(mock_coordinator, "test-device")

        result = await media_player._async_browse_movies_by_tag("test-user", "lib-123", "tag-empty")

        assert isinstance(result, BrowseMedia)
        assert len(result.children) == 0


class TestBrowseMediaRouting:
    """Test browse_media routing for new content types."""

    async def test_movietags_routing(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test routing to movie tags category."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        client = mock_coordinator.client
        client.async_get_tags = AsyncMock(return_value=[])

        # Mock session with user_id
        mock_session = MagicMock()
        mock_session.user_id = "test-user"
        mock_coordinator.get_session = MagicMock(return_value=mock_session)

        media_player = EmbyMediaPlayer(mock_coordinator, "test-device")

        result = await media_player.async_browse_media(
            media_content_type=MediaType.VIDEO,
            media_content_id="movietags:library-123",
        )

        assert isinstance(result, BrowseMedia)
        assert result.title == "Tags"

    async def test_movietag_items_routing(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test routing to movies by specific tag."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        client = mock_coordinator.client
        client.async_get_items_by_tag = AsyncMock(return_value=[])
        client.get_image_url = MagicMock(return_value=None)

        # Mock session with user_id
        mock_session = MagicMock()
        mock_session.user_id = "test-user"
        mock_coordinator.get_session = MagicMock(return_value=mock_session)

        media_player = EmbyMediaPlayer(mock_coordinator, "test-device")

        result = await media_player.async_browse_media(
            media_content_type=MediaType.VIDEO,
            media_content_id="movietag:library-123:tag-456",
        )

        assert isinstance(result, BrowseMedia)
        assert result.title == "Movies by Tag"

    async def test_moviepeople_routing(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test routing to movie people category."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        client = mock_coordinator.client
        client.async_get_persons = AsyncMock(
            return_value={"Items": [], "TotalRecordCount": 0, "StartIndex": 0}
        )

        # Mock session with user_id
        mock_session = MagicMock()
        mock_session.user_id = "test-user"
        mock_coordinator.get_session = MagicMock(return_value=mock_session)

        media_player = EmbyMediaPlayer(mock_coordinator, "test-device")

        result = await media_player.async_browse_media(
            media_content_type=MediaType.VIDEO,
            media_content_id="moviepeople:library-123",
        )

        assert isinstance(result, BrowseMedia)
        assert result.title == "People"

    async def test_person_filmography_routing(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test routing to person filmography."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        client = mock_coordinator.client
        client.async_get_person_items = AsyncMock(return_value=[])
        client.get_image_url = MagicMock(return_value=None)

        # Mock session with user_id
        mock_session = MagicMock()
        mock_session.user_id = "test-user"
        mock_coordinator.get_session = MagicMock(return_value=mock_session)

        media_player = EmbyMediaPlayer(mock_coordinator, "test-device")

        result = await media_player.async_browse_media(
            media_content_type=MediaType.VIDEO,
            media_content_id="person:library-123:person-456",
        )

        assert isinstance(result, BrowseMedia)
        assert result.title == "Filmography"


class TestMovieLibraryCategories:
    """Test movie library shows all expected categories."""

    async def test_movie_library_includes_all_categories(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test that movie library shows People and Tags categories."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        client = mock_coordinator.client
        client.get_image_url = MagicMock(return_value=None)

        media_player = EmbyMediaPlayer(mock_coordinator, "test-device")

        result = await media_player._async_browse_movie_library("test-user", "library-movies")

        assert isinstance(result, BrowseMedia)
        assert result.title == "Movies Library"

        # Get all category titles
        category_titles = [child.title for child in result.children]

        # Verify all expected categories are present
        expected_categories = [
            "A-Z",
            "Year",
            "Decade",
            "Genre",
            "Studio",
            "People",
            "Tags",
            "Collections",
        ]

        for expected in expected_categories:
            assert expected in category_titles, f"Missing category: {expected}"

        # Verify order - People should come before Tags, Tags before Collections
        people_idx = category_titles.index("People")
        tags_idx = category_titles.index("Tags")
        collections_idx = category_titles.index("Collections")

        assert people_idx < tags_idx, "People should come before Tags"
        assert tags_idx < collections_idx, "Tags should come before Collections"
