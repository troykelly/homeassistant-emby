"""Tests for tag browsing in media player.

Phase 19: Collection Management - Task 19.7
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.media_player import BrowseMedia
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


class TestTagBrowsing:
    """Tests for tag browsing functionality."""

    async def test_browse_movie_tags_category_exists(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test that '_async_browse_movie_tags' method exists."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        # Verify the method exists
        assert hasattr(EmbyMediaPlayer, "_async_browse_movie_tags")

    async def test_browse_movie_tags_returns_tags(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test browsing tags in movie library returns tag list."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        # Mock client
        mock_client = MagicMock()
        mock_coordinator.client = mock_client

        # Mock tags response
        mock_client.async_get_tags = AsyncMock(
            return_value=[
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
            ]
        )

        # Create media player with mock coordinator
        media_player = EmbyMediaPlayer(mock_coordinator, "test-device")

        # Call the browse method
        result = await media_player._async_browse_movie_tags(
            user_id="test-user",
            library_id="library-movies",
        )

        # Verify result structure
        assert isinstance(result, BrowseMedia)
        assert result.title == "Tags"
        assert result.can_expand is True
        assert result.can_play is False
        assert len(result.children) == 2

        # Verify children
        assert result.children[0].title == "Favorite"
        assert result.children[1].title == "Watch Later"

    async def test_browse_movies_by_tag(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test browsing movies with a specific tag."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        # Mock client
        mock_client = MagicMock()
        mock_coordinator.client = mock_client

        # Mock items response
        mock_client.async_get_items_by_tag = AsyncMock(
            return_value=[
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
            ]
        )

        # Create media player with mock coordinator
        media_player = EmbyMediaPlayer(mock_coordinator, "test-device")

        # Call the browse method
        result = await media_player._async_browse_movies_by_tag(
            user_id="test-user",
            library_id="library-movies",
            tag_id="tag-1",
        )

        # Verify result structure
        assert isinstance(result, BrowseMedia)
        assert result.can_expand is True
        assert len(result.children) == 2
        assert result.children[0].title == "Tagged Movie 1"
        assert result.children[1].title == "Tagged Movie 2"

    async def test_browse_movie_tags_empty(
        self,
        hass: HomeAssistant,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test browsing tags when library has no tags."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        # Mock client
        mock_client = MagicMock()
        mock_coordinator.client = mock_client

        # Mock empty tags response
        mock_client.async_get_tags = AsyncMock(return_value=[])

        # Create media player with mock coordinator
        media_player = EmbyMediaPlayer(mock_coordinator, "test-device")

        # Call the browse method
        result = await media_player._async_browse_movie_tags(
            user_id="test-user",
            library_id="library-movies",
        )

        # Verify result structure
        assert isinstance(result, BrowseMedia)
        assert result.title == "Tags"
        assert len(result.children) == 0


class TestTagBrowsingRouting:
    """Tests for tag browsing URL routing."""

    async def test_movietags_routing(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test routing to movie tags browse."""
        from custom_components.embymedia.browse import decode_content_id

        # Test decode_content_id supports movietags
        content_type, ids = decode_content_id("movietags:library-123")

        assert content_type == "movietags"
        assert ids[0] == "library-123"

    async def test_movietag_routing(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test routing to movies by tag browse."""
        from custom_components.embymedia.browse import decode_content_id

        # Test decode_content_id supports movietag
        content_type, ids = decode_content_id("movietag:library-123:tag-456")

        assert content_type == "movietag"
        assert ids[0] == "library-123"
        assert ids[1] == "tag-456"
