"""Tests for letter browsing helper method (Phase 22).

These tests verify the generic letter browsing helper is properly implemented.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.media_player import MediaType
from homeassistant.components.media_player.browse_media import BrowseMedia

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


@pytest.fixture
def mock_coordinator_for_letter_browse() -> MagicMock:
    """Create a mock coordinator for letter browsing tests."""
    coordinator = MagicMock()
    coordinator.server_id = "server-123"
    coordinator.server_name = "Test Server"
    coordinator.last_update_success = True
    coordinator.async_add_listener = MagicMock(return_value=MagicMock())
    coordinator.client = MagicMock()
    coordinator.client.base_url = "http://emby.local:8096"
    coordinator.client.api_key = "test-api-key"
    # Make async_get_items return an AsyncMock
    coordinator.client.async_get_items = AsyncMock(
        return_value={"Items": [], "TotalRecordCount": 0}
    )
    return coordinator


@pytest.fixture
def mock_session_with_user_for_letter() -> MagicMock:
    """Create a mock session with user ID."""
    from custom_components.embymedia.models import EmbySession

    return EmbySession(
        session_id="session-1",
        device_id="device-abc-123",
        device_name="Test Device",
        client_name="Test Client",
        user_id="user-123",
        user_name="TestUser",
        supports_remote_control=True,
    )


class TestLetterBrowsingHelper:
    """Tests for the _async_browse_items_by_letter helper method."""

    @pytest.mark.asyncio
    async def test_helper_method_exists(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_letter_browse: MagicMock,
    ) -> None:
        """Test that _async_browse_items_by_letter method exists."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        player = EmbyMediaPlayer(mock_coordinator_for_letter_browse, "device-abc-123")

        assert hasattr(player, "_async_browse_items_by_letter"), (
            "EmbyMediaPlayer should have _async_browse_items_by_letter method"
        )

    @pytest.mark.asyncio
    async def test_helper_filters_letter_items(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_letter_browse: MagicMock,
        mock_session_with_user_for_letter: MagicMock,
    ) -> None:
        """Test helper correctly filters items by letter."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_letter_browse.get_session.return_value = (
            mock_session_with_user_for_letter
        )
        mock_coordinator_for_letter_browse.client.async_get_items.return_value = {
            "Items": [
                {"Id": "item-1", "Name": "Apple", "Type": "Movie"},
                {"Id": "item-2", "Name": "Avengers", "Type": "Movie"},
            ],
            "TotalRecordCount": 2,
        }

        player = EmbyMediaPlayer(mock_coordinator_for_letter_browse, "device-abc-123")

        # Call the helper method directly
        result = await player._async_browse_items_by_letter(
            user_id="user-123",
            library_id="lib-movies",
            letter="A",
            item_type="Movie",
            content_id_type="movieazletter",
            media_content_type=MediaType.VIDEO,
            title_prefix="Movies",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 2
        assert "Movies - A" in result.title
        assert result.media_content_type == MediaType.VIDEO

    @pytest.mark.asyncio
    async def test_helper_handles_hash_symbol(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_letter_browse: MagicMock,
        mock_session_with_user_for_letter: MagicMock,
    ) -> None:
        """Test helper correctly handles # for non-alphabetic items."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_letter_browse.get_session.return_value = (
            mock_session_with_user_for_letter
        )
        # Simulate returning items with various starting characters
        mock_coordinator_for_letter_browse.client.async_get_items.return_value = {
            "Items": [
                {"Id": "item-1", "Name": "123 Movie", "Type": "Movie"},
                {"Id": "item-2", "Name": "@ The Edge", "Type": "Movie"},
                {"Id": "item-3", "Name": "Apple", "Type": "Movie"},  # Should be filtered out
            ],
            "TotalRecordCount": 3,
        }

        player = EmbyMediaPlayer(mock_coordinator_for_letter_browse, "device-abc-123")

        result = await player._async_browse_items_by_letter(
            user_id="user-123",
            library_id="lib-movies",
            letter="#",
            item_type="Movie",
            content_id_type="movieazletter",
            media_content_type=MediaType.VIDEO,
            title_prefix="Movies",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        # "Apple" should be filtered out as it starts with a letter
        assert len(result.children) == 2
        assert "Movies - #" in result.title


class TestRefactoredMethods:
    """Tests verifying the original methods now use the helper."""

    @pytest.mark.asyncio
    async def test_artists_by_letter_uses_helper_result(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_letter_browse: MagicMock,
        mock_session_with_user_for_letter: MagicMock,
    ) -> None:
        """Test _async_browse_artists_by_letter returns correct result."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_letter_browse.get_session.return_value = (
            mock_session_with_user_for_letter
        )
        mock_coordinator_for_letter_browse.client.async_get_items.return_value = {
            "Items": [
                {"Id": "artist-1", "Name": "Adele", "Type": "MusicArtist"},
            ],
            "TotalRecordCount": 1,
        }

        player = EmbyMediaPlayer(mock_coordinator_for_letter_browse, "device-abc-123")

        result = await player._async_browse_artists_by_letter(
            user_id="user-123",
            library_id="lib-music",
            letter="A",
        )

        assert isinstance(result, BrowseMedia)
        assert result.media_content_type == MediaType.MUSIC
        assert "Artists - A" in result.title

    @pytest.mark.asyncio
    async def test_movies_by_letter_uses_helper_result(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_letter_browse: MagicMock,
        mock_session_with_user_for_letter: MagicMock,
    ) -> None:
        """Test _async_browse_movies_by_letter returns correct result."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_letter_browse.get_session.return_value = (
            mock_session_with_user_for_letter
        )
        mock_coordinator_for_letter_browse.client.async_get_items.return_value = {
            "Items": [
                {"Id": "movie-1", "Name": "Avatar", "Type": "Movie"},
            ],
            "TotalRecordCount": 1,
        }

        player = EmbyMediaPlayer(mock_coordinator_for_letter_browse, "device-abc-123")

        result = await player._async_browse_movies_by_letter(
            user_id="user-123",
            library_id="lib-movies",
            letter="A",
        )

        assert isinstance(result, BrowseMedia)
        assert result.media_content_type == MediaType.VIDEO
        assert "Movies - A" in result.title

    @pytest.mark.asyncio
    async def test_tv_by_letter_uses_helper_result(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_letter_browse: MagicMock,
        mock_session_with_user_for_letter: MagicMock,
    ) -> None:
        """Test _async_browse_tv_by_letter returns correct result."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_letter_browse.get_session.return_value = (
            mock_session_with_user_for_letter
        )
        mock_coordinator_for_letter_browse.client.async_get_items.return_value = {
            "Items": [
                {"Id": "series-1", "Name": "Arrow", "Type": "Series"},
            ],
            "TotalRecordCount": 1,
        }

        player = EmbyMediaPlayer(mock_coordinator_for_letter_browse, "device-abc-123")

        result = await player._async_browse_tv_by_letter(
            user_id="user-123",
            library_id="lib-tv",
            letter="A",
        )

        assert isinstance(result, BrowseMedia)
        assert result.media_content_type == MediaType.TVSHOW
        assert "TV Shows - A" in result.title
