"""Tests for Emby Media Source."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.media_source import Unresolvable
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.embymedia.const import DOMAIN


class TestEmbyMediaSourceCreation:
    """Test EmbyMediaSource creation and properties."""

    @pytest.mark.asyncio
    async def test_media_source_creation(self, hass: HomeAssistant) -> None:
        """Test media source can be created."""
        from custom_components.embymedia.media_source import EmbyMediaSource

        media_source = EmbyMediaSource(hass)
        assert media_source.name == "Emby"
        assert media_source.domain == DOMAIN

    @pytest.mark.asyncio
    async def test_async_get_media_source(self, hass: HomeAssistant) -> None:
        """Test async_get_media_source function."""
        from custom_components.embymedia.media_source import async_get_media_source

        media_source = await async_get_media_source(hass)
        assert media_source is not None
        assert media_source.name == "Emby"


class TestBrowseMediaSource:
    """Test media source browsing."""

    @pytest.mark.asyncio
    async def test_browse_root_no_servers(self, hass: HomeAssistant) -> None:
        """Test browsing root with no configured servers."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(hass, DOMAIN, None, None)

        result = await media_source.async_browse_media(item)

        assert result is not None
        assert result.title == "Emby"
        assert result.can_expand is True
        assert result.can_play is False
        # No children when no servers configured
        assert result.children is not None
        assert len(result.children) == 0

    @pytest.mark.asyncio
    async def test_browse_root_with_server(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test browsing root with a configured server."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)

        # Set up mock coordinator in runtime_data
        mock_coordinator = MagicMock()
        mock_coordinator.server_id = mock_server_info["Id"]
        mock_coordinator.server_name = mock_server_info["ServerName"]
        mock_coordinator.client = MagicMock()
        mock_coordinator.data = {}

        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(hass, DOMAIN, None, None)

        result = await media_source.async_browse_media(item)

        assert result is not None
        assert result.title == "Emby"
        assert len(result.children) == 1
        assert result.children[0].title == mock_server_info["ServerName"]

    @pytest.mark.asyncio
    async def test_browse_server_libraries(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test browsing a server's libraries."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)

        mock_views = [
            {
                "Id": "lib-movies",
                "Name": "Movies",
                "CollectionType": "movies",
                "ImageTags": {"Primary": "tag123"},  # Has image tag
            },
            {"Id": "lib-tvshows", "Name": "TV Shows", "CollectionType": "tvshows"},
        ]

        mock_client = MagicMock()
        mock_client.async_get_user_views = AsyncMock(return_value=mock_views)
        mock_client.get_image_url = MagicMock(return_value="http://emby.local:8096/image")

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = mock_server_info["Id"]
        mock_coordinator.server_name = mock_server_info["ServerName"]
        mock_coordinator.client = mock_client
        mock_coordinator.data = {
            "device-1": MagicMock(user_id="user-123"),
        }

        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator)

        media_source = EmbyMediaSource(hass)
        # Browse server by ID
        item = MediaSourceItem(hass, DOMAIN, mock_server_info["Id"], None)

        result = await media_source.async_browse_media(item)

        assert result is not None
        assert len(result.children) == 2
        assert result.children[0].title == "Movies"
        assert result.children[0].thumbnail == "http://emby.local:8096/image"
        assert result.children[1].title == "TV Shows"
        assert result.children[1].thumbnail is None  # No image tag


class TestResolveMedia:
    """Test media URL resolution."""

    @pytest.mark.asyncio
    async def test_resolve_video(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test resolving a video item to stream URL."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)

        mock_client = MagicMock()
        mock_client.get_video_stream_url = MagicMock(
            return_value="http://emby.local:8096/Videos/movie-123/stream?api_key=test"
        )

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = mock_server_info["Id"]
        mock_coordinator.client = mock_client

        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator)

        media_source = EmbyMediaSource(hass)
        # Format: server_id/content_type/item_id
        item = MediaSourceItem(hass, DOMAIN, f"{mock_server_info['Id']}/movie/movie-123", None)

        result = await media_source.async_resolve_media(item)

        assert result is not None
        assert "stream" in result.url
        assert result.mime_type == "video/mp4"

    @pytest.mark.asyncio
    async def test_resolve_audio(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test resolving an audio item to stream URL."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)

        mock_client = MagicMock()
        mock_client.get_audio_stream_url = MagicMock(
            return_value="http://emby.local:8096/Audio/track-456/stream?api_key=test"
        )

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = mock_server_info["Id"]
        mock_coordinator.client = mock_client

        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(hass, DOMAIN, f"{mock_server_info['Id']}/track/track-456", None)

        result = await media_source.async_resolve_media(item)

        assert result is not None
        assert "stream" in result.url
        assert result.mime_type == "audio/mpeg"

    @pytest.mark.asyncio
    async def test_resolve_invalid_identifier(self, hass: HomeAssistant) -> None:
        """Test resolving with invalid identifier raises error."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(hass, DOMAIN, "invalid", None)

        with pytest.raises(Unresolvable):
            await media_source.async_resolve_media(item)

    @pytest.mark.asyncio
    async def test_resolve_server_not_found(self, hass: HomeAssistant) -> None:
        """Test resolving with unknown server raises error."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(hass, DOMAIN, "unknown-server/movie/movie-123", None)

        with pytest.raises(Unresolvable):
            await media_source.async_resolve_media(item)


class TestContentIdParsing:
    """Test content ID parsing utilities."""

    def test_parse_identifier_valid(self) -> None:
        """Test parsing valid identifier."""
        from custom_components.embymedia.media_source import parse_identifier

        server_id, content_type, item_id = parse_identifier("server-123/movie/item-456")
        assert server_id == "server-123"
        assert content_type == "movie"
        assert item_id == "item-456"

    def test_parse_identifier_server_only(self) -> None:
        """Test parsing server-only identifier."""
        from custom_components.embymedia.media_source import parse_identifier

        server_id, content_type, item_id = parse_identifier("server-123")
        assert server_id == "server-123"
        assert content_type is None
        assert item_id is None

    def test_parse_identifier_library(self) -> None:
        """Test parsing library identifier."""
        from custom_components.embymedia.media_source import parse_identifier

        server_id, content_type, item_id = parse_identifier("server-123/library/lib-456")
        assert server_id == "server-123"
        assert content_type == "library"
        assert item_id == "lib-456"

    def test_build_identifier(self) -> None:
        """Test building identifier."""
        from custom_components.embymedia.media_source import build_identifier

        result = build_identifier("server-123", "movie", "item-456")
        assert result == "server-123/movie/item-456"

    def test_build_identifier_server_only(self) -> None:
        """Test building server-only identifier."""
        from custom_components.embymedia.media_source import build_identifier

        result = build_identifier("server-123")
        assert result == "server-123"

    def test_build_identifier_with_content_type_only(self) -> None:
        """Test building identifier with content type but no item ID."""
        from custom_components.embymedia.media_source import build_identifier

        result = build_identifier("server-123", "library")
        assert result == "server-123/library"


class TestMediaClassMapping:
    """Test media class mapping utilities."""

    def test_get_media_class_for_collection_movies(self) -> None:
        """Test media class for movies collection."""
        from homeassistant.components.media_player import MediaClass

        from custom_components.embymedia.media_source import EmbyMediaSource

        source = EmbyMediaSource.__new__(EmbyMediaSource)
        result = source._get_media_class_for_collection("movies")
        assert result == MediaClass.DIRECTORY

    def test_get_media_class_for_collection_tvshows(self) -> None:
        """Test media class for TV shows collection."""
        from homeassistant.components.media_player import MediaClass

        from custom_components.embymedia.media_source import EmbyMediaSource

        source = EmbyMediaSource.__new__(EmbyMediaSource)
        result = source._get_media_class_for_collection("tvshows")
        assert result == MediaClass.TV_SHOW

    def test_get_media_class_for_collection_music(self) -> None:
        """Test media class for music collection."""
        from homeassistant.components.media_player import MediaClass

        from custom_components.embymedia.media_source import EmbyMediaSource

        source = EmbyMediaSource.__new__(EmbyMediaSource)
        result = source._get_media_class_for_collection("music")
        assert result == MediaClass.MUSIC

    def test_get_media_class_for_collection_unknown(self) -> None:
        """Test media class for unknown collection."""
        from homeassistant.components.media_player import MediaClass

        from custom_components.embymedia.media_source import EmbyMediaSource

        source = EmbyMediaSource.__new__(EmbyMediaSource)
        result = source._get_media_class_for_collection("unknown")
        assert result == MediaClass.DIRECTORY

    def test_get_media_class_for_type_movie(self) -> None:
        """Test media class for movie type."""
        from homeassistant.components.media_player import MediaClass

        from custom_components.embymedia.media_source import EmbyMediaSource

        source = EmbyMediaSource.__new__(EmbyMediaSource)
        result = source._get_media_class_for_type("movie")
        assert result == MediaClass.MOVIE

    def test_get_media_class_for_type_series(self) -> None:
        """Test media class for series type."""
        from homeassistant.components.media_player import MediaClass

        from custom_components.embymedia.media_source import EmbyMediaSource

        source = EmbyMediaSource.__new__(EmbyMediaSource)
        result = source._get_media_class_for_type("series")
        assert result == MediaClass.TV_SHOW

    def test_get_media_class_for_type_episode(self) -> None:
        """Test media class for episode type."""
        from homeassistant.components.media_player import MediaClass

        from custom_components.embymedia.media_source import EmbyMediaSource

        source = EmbyMediaSource.__new__(EmbyMediaSource)
        result = source._get_media_class_for_type("episode")
        assert result == MediaClass.EPISODE

    def test_get_media_class_for_type_audio(self) -> None:
        """Test media class for audio type."""
        from homeassistant.components.media_player import MediaClass

        from custom_components.embymedia.media_source import EmbyMediaSource

        source = EmbyMediaSource.__new__(EmbyMediaSource)
        result = source._get_media_class_for_type("audio")
        assert result == MediaClass.TRACK

    def test_get_media_class_for_type_unknown(self) -> None:
        """Test media class for unknown type."""
        from homeassistant.components.media_player import MediaClass

        from custom_components.embymedia.media_source import EmbyMediaSource

        source = EmbyMediaSource.__new__(EmbyMediaSource)
        result = source._get_media_class_for_type("unknown")
        assert result == MediaClass.VIDEO


class TestBrowseLibraryAndItem:
    """Test library and item browsing."""

    @pytest.mark.asyncio
    async def test_browse_library(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test browsing a library's contents."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)

        mock_items = {
            "Items": [
                {"Id": "movie-1", "Name": "Movie 1", "Type": "Movie"},
                {"Id": "movie-2", "Name": "Movie 2", "Type": "Movie"},
            ],
            "TotalRecordCount": 2,
            "StartIndex": 0,
        }

        mock_client = MagicMock()
        mock_client.async_get_items = AsyncMock(return_value=mock_items)
        mock_client.get_image_url = MagicMock(return_value="http://emby.local:8096/image")

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = mock_server_info["Id"]
        mock_coordinator.server_name = mock_server_info["ServerName"]
        mock_coordinator.client = mock_client
        mock_coordinator.data = {
            "device-1": MagicMock(user_id="user-123"),
        }

        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(hass, DOMAIN, f"{mock_server_info['Id']}/library/lib-movies", None)

        result = await media_source.async_browse_media(item)

        assert result is not None
        assert len(result.children) == 2
        assert result.children[0].title == "Movie 1"

    @pytest.mark.asyncio
    async def test_browse_series_seasons(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test browsing a series to get seasons."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)

        mock_seasons = [
            {"Id": "season-1", "Name": "Season 1", "Type": "Season", "IndexNumber": 1},
            {"Id": "season-2", "Name": "Season 2", "Type": "Season", "IndexNumber": 2},
        ]

        mock_client = MagicMock()
        mock_client.async_get_seasons = AsyncMock(return_value=mock_seasons)
        mock_client.get_image_url = MagicMock(return_value="http://emby.local:8096/image")

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = mock_server_info["Id"]
        mock_coordinator.server_name = mock_server_info["ServerName"]
        mock_coordinator.client = mock_client
        mock_coordinator.data = {
            "device-1": MagicMock(user_id="user-123"),
        }

        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(hass, DOMAIN, f"{mock_server_info['Id']}/series/series-123", None)

        result = await media_source.async_browse_media(item)

        assert result is not None
        assert len(result.children) == 2
        mock_client.async_get_seasons.assert_called_once_with("user-123", "series-123")

    @pytest.mark.asyncio
    async def test_browse_season_episodes(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test browsing a season to get episodes."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)

        mock_episodes = {
            "Items": [
                {"Id": "ep-1", "Name": "Episode 1", "Type": "Episode", "IndexNumber": 1},
                {"Id": "ep-2", "Name": "Episode 2", "Type": "Episode", "IndexNumber": 2},
            ],
            "TotalRecordCount": 2,
            "StartIndex": 0,
        }

        mock_client = MagicMock()
        mock_client.async_get_items = AsyncMock(return_value=mock_episodes)
        mock_client.get_image_url = MagicMock(return_value="http://emby.local:8096/image")

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = mock_server_info["Id"]
        mock_coordinator.server_name = mock_server_info["ServerName"]
        mock_coordinator.client = mock_client
        mock_coordinator.data = {
            "device-1": MagicMock(user_id="user-123"),
        }

        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(hass, DOMAIN, f"{mock_server_info['Id']}/season/season-123", None)

        result = await media_source.async_browse_media(item)

        assert result is not None
        assert len(result.children) == 2

    @pytest.mark.asyncio
    async def test_browse_folder_contents(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test browsing a folder to get its contents."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)

        mock_items = {
            "Items": [
                {"Id": "series-1", "Name": "Show 1", "Type": "Series"},
                {"Id": "series-2", "Name": "Show 2", "Type": "Series"},
            ],
            "TotalRecordCount": 2,
            "StartIndex": 0,
        }

        mock_client = MagicMock()
        mock_client.async_get_items = AsyncMock(return_value=mock_items)
        mock_client.get_image_url = MagicMock(return_value="http://emby.local:8096/image")

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = mock_server_info["Id"]
        mock_coordinator.server_name = mock_server_info["ServerName"]
        mock_coordinator.client = mock_client
        mock_coordinator.data = {
            "device-1": MagicMock(user_id="user-123"),
        }

        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(hass, DOMAIN, f"{mock_server_info['Id']}/folder/folder-123", None)

        result = await media_source.async_browse_media(item)

        assert result is not None
        assert len(result.children) == 2
        assert result.children[0].title == "Show 1"
        mock_client.async_get_items.assert_called_once_with("user-123", parent_id="folder-123")

    @pytest.mark.asyncio
    async def test_browse_server_not_found(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test browsing unknown server raises error."""
        from homeassistant.components.media_source import MediaSourceItem, Unresolvable

        from custom_components.embymedia.media_source import EmbyMediaSource

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(hass, DOMAIN, "unknown-server", None)

        with pytest.raises(Unresolvable):
            await media_source.async_browse_media(item)

    @pytest.mark.asyncio
    async def test_browse_no_user_id(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test browsing when no user ID is available."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = mock_server_info["Id"]
        mock_coordinator.server_name = mock_server_info["ServerName"]
        mock_coordinator.client = MagicMock()
        # Empty data means no sessions, no user ID
        mock_coordinator.data = {}

        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(hass, DOMAIN, mock_server_info["Id"], None)

        result = await media_source.async_browse_media(item)

        # Should return empty children when no user ID available
        assert result is not None
        assert result.children is not None
        assert len(result.children) == 0


class TestItemToBrowseMediaSource:
    """Test item to browse media source conversion."""

    def test_item_with_primary_image(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test item with primary image tag gets thumbnail."""
        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_client = MagicMock()
        mock_client.get_image_url = MagicMock(return_value="http://emby/image")

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.client = mock_client

        media_source = EmbyMediaSource(hass)

        item = {
            "Id": "movie-123",
            "Name": "Test Movie",
            "Type": "Movie",
            "ImageTags": {"Primary": "tag123"},
        }

        result = media_source._item_to_browse_media_source(mock_coordinator, item)

        assert result.thumbnail == "http://emby/image"
        mock_client.get_image_url.assert_called_once()

    def test_item_without_image(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test item without image tag has no thumbnail."""
        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_client = MagicMock()

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.client = mock_client

        media_source = EmbyMediaSource(hass)

        item = {
            "Id": "movie-123",
            "Name": "Test Movie",
            "Type": "Movie",
        }

        result = media_source._item_to_browse_media_source(mock_coordinator, item)

        assert result.thumbnail is None

    def test_audio_item_media_type(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test audio item gets music media type."""
        from homeassistant.components.media_player import MediaType

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.client = MagicMock()

        media_source = EmbyMediaSource(hass)

        item = {
            "Id": "audio-123",
            "Name": "Test Track",
            "Type": "Audio",
        }

        result = media_source._item_to_browse_media_source(mock_coordinator, item)

        assert result.media_content_type == MediaType.MUSIC

    def test_playable_items(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test playable item types."""
        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.client = MagicMock()

        media_source = EmbyMediaSource(hass)

        playable_types = ["movie", "episode", "audio", "musicvideo"]

        for item_type in playable_types:
            item = {"Id": "item-123", "Name": "Test", "Type": item_type.title()}
            result = media_source._item_to_browse_media_source(mock_coordinator, item)
            assert result.can_play is True, f"{item_type} should be playable"

    def test_expandable_items(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test expandable item types."""
        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.client = MagicMock()

        media_source = EmbyMediaSource(hass)

        expandable_types = ["series", "season", "album", "folder"]

        for item_type in expandable_types:
            item = {"Id": "item-123", "Name": "Test", "Type": item_type.title()}
            result = media_source._item_to_browse_media_source(mock_coordinator, item)
            assert result.can_expand is True, f"{item_type} should be expandable"


class TestResolveMediaEdgeCases:
    """Test resolve media edge cases."""

    @pytest.mark.asyncio
    async def test_resolve_no_identifier(self, hass: HomeAssistant) -> None:
        """Test resolving with no identifier raises error."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(hass, DOMAIN, None, None)

        with pytest.raises(Unresolvable):
            await media_source.async_resolve_media(item)

    @pytest.mark.asyncio
    async def test_resolve_episode(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test resolving an episode to video stream URL."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)

        mock_client = MagicMock()
        mock_client.get_video_stream_url = MagicMock(
            return_value="http://emby.local:8096/Videos/ep-123/stream"
        )

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = mock_server_info["Id"]
        mock_coordinator.client = mock_client

        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(hass, DOMAIN, f"{mock_server_info['Id']}/episode/ep-123", None)

        result = await media_source.async_resolve_media(item)

        assert result.mime_type == "video/mp4"
        mock_client.get_video_stream_url.assert_called_once_with("ep-123")


class TestLiveTVLibraryBrowsing:
    """Test special handling for Live TV library browsing in media source."""

    @pytest.mark.asyncio
    async def test_browse_server_encodes_livetv_library_correctly(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test that Live TV library is encoded with livetv content type."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)

        mock_views = [
            {"Id": "lib-movies", "Name": "Movies", "CollectionType": "movies"},
            {"Id": "lib-livetv", "Name": "Live TV", "CollectionType": "livetv"},
        ]

        mock_client = MagicMock()
        mock_client.async_get_user_views = AsyncMock(return_value=mock_views)

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = mock_server_info["Id"]
        mock_coordinator.server_name = mock_server_info["ServerName"]
        mock_coordinator.client = mock_client
        mock_coordinator.data = {"device-1": MagicMock(user_id="user-123")}

        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(hass, DOMAIN, mock_server_info["Id"], None)

        result = await media_source.async_browse_media(item)

        assert result.children is not None
        assert len(result.children) == 2
        # Movies library should use movielibrary identifier for category browsing
        assert result.children[0].identifier == f"{mock_server_info['Id']}/movielibrary/lib-movies"
        # Live TV library should use livetv identifier
        assert result.children[1].identifier == f"{mock_server_info['Id']}/livetv"

    @pytest.mark.asyncio
    async def test_browse_livetv_fetches_channels(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test that browsing Live TV fetches channels via dedicated API."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)

        mock_channels = [
            {"Id": "ch-1", "Name": "Channel 1", "Type": "TvChannel"},
            {"Id": "ch-2", "Name": "Channel 2", "Type": "TvChannel"},
        ]

        mock_client = MagicMock()
        mock_client.async_get_live_tv_channels = AsyncMock(return_value=mock_channels)
        mock_client.get_image_url = MagicMock(return_value=None)

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = mock_server_info["Id"]
        mock_coordinator.server_name = mock_server_info["ServerName"]
        mock_coordinator.client = mock_client
        mock_coordinator.data = {"device-1": MagicMock(user_id="user-123")}

        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(hass, DOMAIN, f"{mock_server_info['Id']}/livetv", None)

        result = await media_source.async_browse_media(item)

        assert result.children is not None
        assert len(result.children) == 2
        assert result.children[0].title == "Channel 1"
        assert result.children[1].title == "Channel 2"
        # Channels should be playable
        assert result.children[0].can_play is True
        mock_client.async_get_live_tv_channels.assert_called_once_with("user-123")


class TestMovieLibraryBrowsingMediaSource:
    """Test movie library category browsing in media source."""

    @pytest.fixture
    def mock_coordinator_for_media_source(self, mock_server_info: dict[str, Any]) -> MagicMock:
        """Create a mock coordinator for media source tests."""
        mock_client = MagicMock()
        mock_client.async_get_items = AsyncMock(return_value={"Items": [], "TotalRecordCount": 0})
        mock_client.async_get_genres = AsyncMock(return_value=[])
        mock_client.async_get_years = AsyncMock(return_value=[])
        mock_client.get_image_url = MagicMock(return_value="http://test/image.jpg")

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = mock_server_info["Id"]
        mock_coordinator.server_name = mock_server_info["ServerName"]
        mock_coordinator.client = mock_client
        mock_coordinator.data = {"device-1": MagicMock(user_id="user-123")}
        return mock_coordinator

    @pytest.mark.asyncio
    async def test_browse_movie_library_shows_categories(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
        mock_coordinator_for_media_source: MagicMock,
    ) -> None:
        """Test browsing a movie library shows category menu."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)
        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator_for_media_source)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(
            hass, DOMAIN, f"{mock_server_info['Id']}/movielibrary/lib-movies", None
        )

        result = await media_source.async_browse_media(item)

        assert result.children is not None
        assert len(result.children) == 5
        titles = [c.title for c in result.children]
        assert "A-Z" in titles
        assert "Year" in titles
        assert "Decade" in titles
        assert "Genre" in titles
        assert "Collections" in titles

    @pytest.mark.asyncio
    async def test_browse_movie_az_shows_letters(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
        mock_coordinator_for_media_source: MagicMock,
    ) -> None:
        """Test browsing movie A-Z shows letter menu."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)
        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator_for_media_source)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(hass, DOMAIN, f"{mock_server_info['Id']}/movieaz/lib-movies", None)

        result = await media_source.async_browse_media(item)

        assert result.children is not None
        assert len(result.children) == 27  # A-Z + #
        assert result.children[0].title == "A"
        assert result.children[25].title == "Z"
        assert result.children[26].title == "#"

    @pytest.mark.asyncio
    async def test_browse_movies_by_letter(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
        mock_coordinator_for_media_source: MagicMock,
    ) -> None:
        """Test browsing movies by specific letter."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)
        mock_coordinator_for_media_source.client.async_get_items.return_value = {
            "Items": [
                {"Id": "m1", "Name": "Avatar", "Type": "Movie"},
            ],
            "TotalRecordCount": 1,
        }
        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator_for_media_source)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(
            hass, DOMAIN, f"{mock_server_info['Id']}/movieazletter/lib-movies/A", None
        )

        result = await media_source.async_browse_media(item)

        assert result.children is not None
        assert len(result.children) == 1
        mock_coordinator_for_media_source.client.async_get_items.assert_called_with(
            "user-123",
            parent_id="lib-movies",
            include_item_types="Movie",
            recursive=True,
            name_starts_with="A",
        )

    @pytest.mark.asyncio
    async def test_browse_movie_years(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
        mock_coordinator_for_media_source: MagicMock,
    ) -> None:
        """Test browsing movie years."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)
        mock_coordinator_for_media_source.client.async_get_years.return_value = [
            {"Id": "y1", "Name": "2024"},
            {"Id": "y2", "Name": "2023"},
        ]
        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator_for_media_source)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(hass, DOMAIN, f"{mock_server_info['Id']}/movieyear/lib-movies", None)

        result = await media_source.async_browse_media(item)

        assert result.children is not None
        assert len(result.children) == 2
        assert result.children[0].title == "2024"
        assert result.children[1].title == "2023"

    @pytest.mark.asyncio
    async def test_browse_movies_by_year(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
        mock_coordinator_for_media_source: MagicMock,
    ) -> None:
        """Test browsing movies by specific year."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)
        mock_coordinator_for_media_source.client.async_get_items.return_value = {
            "Items": [{"Id": "m1", "Name": "Test Movie", "Type": "Movie"}],
            "TotalRecordCount": 1,
        }
        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator_for_media_source)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(
            hass, DOMAIN, f"{mock_server_info['Id']}/movieyearitems/lib-movies/2024", None
        )

        result = await media_source.async_browse_media(item)

        assert result.children is not None
        mock_coordinator_for_media_source.client.async_get_items.assert_called_with(
            "user-123",
            parent_id="lib-movies",
            include_item_types="Movie",
            recursive=True,
            years="2024",
        )

    @pytest.mark.asyncio
    async def test_browse_movie_decades(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
        mock_coordinator_for_media_source: MagicMock,
    ) -> None:
        """Test browsing movie decades."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)
        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator_for_media_source)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(
            hass, DOMAIN, f"{mock_server_info['Id']}/moviedecade/lib-movies", None
        )

        result = await media_source.async_browse_media(item)

        assert result.children is not None
        assert len(result.children) == 11  # 2020s through 1920s
        assert result.children[0].title == "2020s"
        assert result.children[10].title == "1920s"

    @pytest.mark.asyncio
    async def test_browse_movies_by_decade(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
        mock_coordinator_for_media_source: MagicMock,
    ) -> None:
        """Test browsing movies by decade."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)
        mock_coordinator_for_media_source.client.async_get_items.return_value = {
            "Items": [{"Id": "m1", "Name": "90s Movie", "Type": "Movie"}],
            "TotalRecordCount": 1,
        }
        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator_for_media_source)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(
            hass,
            DOMAIN,
            f"{mock_server_info['Id']}/moviedecadeitems/lib-movies/1990s",
            None,
        )

        result = await media_source.async_browse_media(item)

        assert result.children is not None
        # Verify years 1990-1999 are queried
        call_kwargs = mock_coordinator_for_media_source.client.async_get_items.call_args.kwargs
        assert "1990" in call_kwargs["years"]
        assert "1999" in call_kwargs["years"]

    @pytest.mark.asyncio
    async def test_browse_movie_genres(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
        mock_coordinator_for_media_source: MagicMock,
    ) -> None:
        """Test browsing movie genres."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)
        mock_coordinator_for_media_source.client.async_get_genres.return_value = [
            {"Id": "g1", "Name": "Action"},
            {"Id": "g2", "Name": "Comedy"},
        ]
        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator_for_media_source)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(
            hass, DOMAIN, f"{mock_server_info['Id']}/moviegenre/lib-movies", None
        )

        result = await media_source.async_browse_media(item)

        assert result.children is not None
        assert len(result.children) == 2
        assert result.children[0].title == "Action"
        assert result.children[1].title == "Comedy"

    @pytest.mark.asyncio
    async def test_browse_movies_by_genre(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
        mock_coordinator_for_media_source: MagicMock,
    ) -> None:
        """Test browsing movies by genre."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)
        mock_coordinator_for_media_source.client.async_get_items.return_value = {
            "Items": [{"Id": "m1", "Name": "Action Movie", "Type": "Movie"}],
            "TotalRecordCount": 1,
        }
        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator_for_media_source)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(
            hass, DOMAIN, f"{mock_server_info['Id']}/moviegenreitems/lib-movies/g1", None
        )

        result = await media_source.async_browse_media(item)

        assert result.children is not None
        mock_coordinator_for_media_source.client.async_get_items.assert_called_with(
            "user-123",
            parent_id="lib-movies",
            include_item_types="Movie",
            recursive=True,
            genre_ids="g1",
        )

    @pytest.mark.asyncio
    async def test_browse_movie_collections(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
        mock_coordinator_for_media_source: MagicMock,
    ) -> None:
        """Test browsing movie collections."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)
        mock_coordinator_for_media_source.client.async_get_items.return_value = {
            "Items": [{"Id": "c1", "Name": "Marvel Collection", "Type": "BoxSet"}],
            "TotalRecordCount": 1,
        }
        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator_for_media_source)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(
            hass, DOMAIN, f"{mock_server_info['Id']}/moviecollection/lib-movies", None
        )

        result = await media_source.async_browse_media(item)

        assert result.children is not None
        mock_coordinator_for_media_source.client.async_get_items.assert_called_with(
            "user-123",
            parent_id="lib-movies",
            include_item_types="BoxSet",
            recursive=True,
        )


class TestTVLibraryBrowsingMediaSource:
    """Test TV library category browsing in media source."""

    @pytest.fixture
    def mock_coordinator_for_media_source(self, mock_server_info: dict[str, Any]) -> MagicMock:
        """Create a mock coordinator for media source tests."""
        mock_client = MagicMock()
        mock_client.async_get_items = AsyncMock(return_value={"Items": [], "TotalRecordCount": 0})
        mock_client.async_get_genres = AsyncMock(return_value=[])
        mock_client.async_get_years = AsyncMock(return_value=[])
        mock_client.get_image_url = MagicMock(return_value="http://test/image.jpg")

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = mock_server_info["Id"]
        mock_coordinator.server_name = mock_server_info["ServerName"]
        mock_coordinator.client = mock_client
        mock_coordinator.data = {"device-1": MagicMock(user_id="user-123")}
        return mock_coordinator

    @pytest.mark.asyncio
    async def test_browse_tv_library_shows_categories(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
        mock_coordinator_for_media_source: MagicMock,
    ) -> None:
        """Test browsing a TV library shows category menu."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)
        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator_for_media_source)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(hass, DOMAIN, f"{mock_server_info['Id']}/tvlibrary/lib-tv", None)

        result = await media_source.async_browse_media(item)

        assert result.children is not None
        assert len(result.children) == 4
        titles = [c.title for c in result.children]
        assert "A-Z" in titles
        assert "Year" in titles
        assert "Decade" in titles
        assert "Genre" in titles

    @pytest.mark.asyncio
    async def test_browse_tv_az_shows_letters(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
        mock_coordinator_for_media_source: MagicMock,
    ) -> None:
        """Test browsing TV A-Z shows letter menu."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)
        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator_for_media_source)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(hass, DOMAIN, f"{mock_server_info['Id']}/tvaz/lib-tv", None)

        result = await media_source.async_browse_media(item)

        assert result.children is not None
        assert len(result.children) == 27

    @pytest.mark.asyncio
    async def test_browse_tv_by_letter(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
        mock_coordinator_for_media_source: MagicMock,
    ) -> None:
        """Test browsing TV shows by letter."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)
        mock_coordinator_for_media_source.client.async_get_items.return_value = {
            "Items": [{"Id": "s1", "Name": "Breaking Bad", "Type": "Series"}],
            "TotalRecordCount": 1,
        }
        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator_for_media_source)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(hass, DOMAIN, f"{mock_server_info['Id']}/tvazletter/lib-tv/B", None)

        result = await media_source.async_browse_media(item)

        assert result.children is not None
        mock_coordinator_for_media_source.client.async_get_items.assert_called_with(
            "user-123",
            parent_id="lib-tv",
            include_item_types="Series",
            recursive=True,
            name_starts_with="B",
        )

    @pytest.mark.asyncio
    async def test_browse_tv_years(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
        mock_coordinator_for_media_source: MagicMock,
    ) -> None:
        """Test browsing TV years."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)
        mock_coordinator_for_media_source.client.async_get_years.return_value = [
            {"Id": "y1", "Name": "2024"},
        ]
        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator_for_media_source)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(hass, DOMAIN, f"{mock_server_info['Id']}/tvyear/lib-tv", None)

        result = await media_source.async_browse_media(item)

        assert result.children is not None
        assert len(result.children) == 1
        assert result.children[0].title == "2024"

    @pytest.mark.asyncio
    async def test_browse_tv_by_year(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
        mock_coordinator_for_media_source: MagicMock,
    ) -> None:
        """Test browsing TV shows by year."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)
        mock_coordinator_for_media_source.client.async_get_items.return_value = {
            "Items": [{"Id": "s1", "Name": "Test Show", "Type": "Series"}],
            "TotalRecordCount": 1,
        }
        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator_for_media_source)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(
            hass, DOMAIN, f"{mock_server_info['Id']}/tvyearitems/lib-tv/2024", None
        )

        result = await media_source.async_browse_media(item)

        assert result.children is not None
        mock_coordinator_for_media_source.client.async_get_items.assert_called_with(
            "user-123",
            parent_id="lib-tv",
            include_item_types="Series",
            recursive=True,
            years="2024",
        )

    @pytest.mark.asyncio
    async def test_browse_tv_decades(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
        mock_coordinator_for_media_source: MagicMock,
    ) -> None:
        """Test browsing TV decades."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)
        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator_for_media_source)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(hass, DOMAIN, f"{mock_server_info['Id']}/tvdecade/lib-tv", None)

        result = await media_source.async_browse_media(item)

        assert result.children is not None
        assert len(result.children) == 8  # 2020s through 1950s
        assert result.children[0].title == "2020s"

    @pytest.mark.asyncio
    async def test_browse_tv_by_decade(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
        mock_coordinator_for_media_source: MagicMock,
    ) -> None:
        """Test browsing TV shows by decade."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)
        mock_coordinator_for_media_source.client.async_get_items.return_value = {
            "Items": [{"Id": "s1", "Name": "90s Show", "Type": "Series"}],
            "TotalRecordCount": 1,
        }
        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator_for_media_source)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(
            hass, DOMAIN, f"{mock_server_info['Id']}/tvdecadeitems/lib-tv/1990s", None
        )

        result = await media_source.async_browse_media(item)

        assert result.children is not None
        call_kwargs = mock_coordinator_for_media_source.client.async_get_items.call_args.kwargs
        assert "1990" in call_kwargs["years"]

    @pytest.mark.asyncio
    async def test_browse_tv_genres(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
        mock_coordinator_for_media_source: MagicMock,
    ) -> None:
        """Test browsing TV genres."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)
        mock_coordinator_for_media_source.client.async_get_genres.return_value = [
            {"Id": "g1", "Name": "Drama"},
        ]
        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator_for_media_source)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(hass, DOMAIN, f"{mock_server_info['Id']}/tvgenre/lib-tv", None)

        result = await media_source.async_browse_media(item)

        assert result.children is not None
        assert len(result.children) == 1
        assert result.children[0].title == "Drama"

    @pytest.mark.asyncio
    async def test_browse_tv_by_genre(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
        mock_coordinator_for_media_source: MagicMock,
    ) -> None:
        """Test browsing TV shows by genre."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)
        mock_coordinator_for_media_source.client.async_get_items.return_value = {
            "Items": [{"Id": "s1", "Name": "Drama Show", "Type": "Series"}],
            "TotalRecordCount": 1,
        }
        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator_for_media_source)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(
            hass, DOMAIN, f"{mock_server_info['Id']}/tvgenreitems/lib-tv/g1", None
        )

        result = await media_source.async_browse_media(item)

        assert result.children is not None
        mock_coordinator_for_media_source.client.async_get_items.assert_called_with(
            "user-123",
            parent_id="lib-tv",
            include_item_types="Series",
            recursive=True,
            genre_ids="g1",
        )


class TestMediaSourceLibraryTypeRouting:
    """Test library type identifier routing in media source."""

    @pytest.mark.asyncio
    async def test_server_browse_encodes_all_library_types(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test all library types get correct identifiers."""
        from homeassistant.components.media_source import MediaSourceItem

        from custom_components.embymedia.media_source import EmbyMediaSource

        mock_config_entry.add_to_hass(hass)

        mock_views = [
            {"Id": "lib-movies", "Name": "Movies", "CollectionType": "movies"},
            {"Id": "lib-tv", "Name": "TV Shows", "CollectionType": "tvshows"},
            {"Id": "lib-music", "Name": "Music", "CollectionType": "music"},
            {"Id": "lib-other", "Name": "Other", "CollectionType": "unknown"},
        ]

        mock_client = MagicMock()
        mock_client.async_get_user_views = AsyncMock(return_value=mock_views)

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = mock_server_info["Id"]
        mock_coordinator.server_name = mock_server_info["ServerName"]
        mock_coordinator.client = mock_client
        mock_coordinator.data = {"device-1": MagicMock(user_id="user-123")}

        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator)

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(hass, DOMAIN, mock_server_info["Id"], None)

        result = await media_source.async_browse_media(item)

        assert result.children is not None
        assert len(result.children) == 4
        # Movies -> movielibrary
        assert result.children[0].identifier == f"{mock_server_info['Id']}/movielibrary/lib-movies"
        # TV Shows -> tvlibrary
        assert result.children[1].identifier == f"{mock_server_info['Id']}/tvlibrary/lib-tv"
        # Music -> library (existing behavior)
        assert result.children[2].identifier == f"{mock_server_info['Id']}/library/lib-music"
        # Unknown -> library (fallback)
        assert result.children[3].identifier == f"{mock_server_info['Id']}/library/lib-other"
