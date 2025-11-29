"""Tests for person browsing in media player.

Phase 19: Collection Management - Task 19.5
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.media_player import BrowseMedia, MediaClass
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.embymedia.const import DOMAIN


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry for testing."""
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
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.server_id = "test-server-id"
    coordinator.server_name = "Test Server"
    coordinator.last_update_success = True
    coordinator.data = {}
    coordinator.get_session = MagicMock(return_value=None)
    coordinator.async_add_listener = MagicMock(return_value=MagicMock())
    return coordinator


class TestPersonBrowsing:
    """Tests for person browsing functionality."""

    async def test_browse_movie_people_category_exists(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test that 'People' category exists in movie library browse."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        # Verify the method exists
        assert hasattr(EmbyMediaPlayer, "_async_browse_movie_people")

    async def test_browse_movie_people_returns_persons(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test browsing people in movie library returns person list."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        # Mock client
        mock_client = MagicMock()
        mock_coordinator.client = mock_client

        # Mock persons response
        mock_client.async_get_persons = AsyncMock(
            return_value={
                "Items": [
                    {
                        "Id": "person-1",
                        "Name": "Tom Hanks",
                        "Type": "Person",
                        "ImageTags": {"Primary": "tag123"},
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
        )

        # Create media player with mock coordinator
        media_player = EmbyMediaPlayer(mock_coordinator, "test-device")

        # Call the browse method
        result = await media_player._async_browse_movie_people(
            user_id="test-user",
            library_id="library-movies",
        )

        # Verify result structure
        assert isinstance(result, BrowseMedia)
        assert result.title == "People"
        assert result.can_expand is True
        assert result.can_play is False
        assert len(result.children) == 2

        # Verify children
        assert result.children[0].title == "Tom Hanks"
        assert result.children[1].title == "Steven Spielberg"

    async def test_browse_person_filmography(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test browsing a person's filmography."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        # Mock client
        mock_client = MagicMock()
        mock_coordinator.client = mock_client

        # Mock person items response
        mock_client.async_get_person_items = AsyncMock(
            return_value=[
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
            ]
        )

        # Create media player with mock coordinator
        media_player = EmbyMediaPlayer(mock_coordinator, "test-device")

        # Call the browse method
        result = await media_player._async_browse_person(
            user_id="test-user",
            person_id="person-tom-hanks",
            library_id="library-movies",
        )

        # Verify result structure
        assert isinstance(result, BrowseMedia)
        assert result.can_expand is True
        assert len(result.children) == 2
        assert result.children[0].title == "Forrest Gump"
        assert result.children[1].title == "Cast Away"

    async def test_person_to_browse_media(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test converting person item to BrowseMedia."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        # Mock client
        mock_client = MagicMock()
        mock_coordinator.client = mock_client
        mock_client.get_image_url = MagicMock(
            return_value="http://emby.local/Items/person-1/Images/Primary"
        )

        # Create media player with mock coordinator
        media_player = EmbyMediaPlayer(mock_coordinator, "test-device")

        person = {
            "Id": "person-1",
            "Name": "Tom Hanks",
            "Type": "Person",
            "ImageTags": {"Primary": "tag123"},
        }

        result = media_player._person_to_browse_media(person, "library-movies")

        assert isinstance(result, BrowseMedia)
        assert result.title == "Tom Hanks"
        assert result.can_play is False
        assert result.can_expand is True
        assert result.media_class == MediaClass.DIRECTORY

    async def test_person_to_browse_media_no_image(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test converting person item without image to BrowseMedia."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        # Mock client
        mock_client = MagicMock()
        mock_coordinator.client = mock_client

        # Create media player with mock coordinator
        media_player = EmbyMediaPlayer(mock_coordinator, "test-device")

        person = {
            "Id": "person-2",
            "Name": "Unknown Actor",
            "Type": "Person",
        }

        result = media_player._person_to_browse_media(person, "library-movies")

        assert isinstance(result, BrowseMedia)
        assert result.title == "Unknown Actor"
        assert result.thumbnail is None


class TestPersonBrowsingRouting:
    """Tests for person browsing URL routing."""

    async def test_moviepeople_routing(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test routing to movie people browse."""
        from custom_components.embymedia.browse import decode_content_id

        # Test decode_content_id supports moviepeople
        content_type, ids = decode_content_id("moviepeople:library-123")

        assert content_type == "moviepeople"
        assert ids[0] == "library-123"

    async def test_person_routing(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test routing to person filmography browse."""
        from custom_components.embymedia.browse import decode_content_id

        # Test decode_content_id supports person
        content_type, ids = decode_content_id("person:library-123:person-456")

        assert content_type == "person"
        assert ids[0] == "library-123"
        assert ids[1] == "person-456"
