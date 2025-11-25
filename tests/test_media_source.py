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

        # Set up mock coordinator
        mock_coordinator = MagicMock()
        mock_coordinator.server_id = mock_server_info["Id"]
        mock_coordinator.server_name = mock_server_info["ServerName"]
        mock_coordinator.client = MagicMock()
        mock_coordinator.data = {}

        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "coordinator": mock_coordinator,
        }

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

        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "coordinator": mock_coordinator,
        }

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

        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "coordinator": mock_coordinator,
        }

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

        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "coordinator": mock_coordinator,
        }

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

        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "coordinator": mock_coordinator,
        }

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

        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "coordinator": mock_coordinator,
        }

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

        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "coordinator": mock_coordinator,
        }

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(hass, DOMAIN, f"{mock_server_info['Id']}/season/season-123", None)

        result = await media_source.async_browse_media(item)

        assert result is not None
        assert len(result.children) == 2

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

        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "coordinator": mock_coordinator,
        }

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

        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][mock_config_entry.entry_id] = {
            "coordinator": mock_coordinator,
        }

        media_source = EmbyMediaSource(hass)
        item = MediaSourceItem(hass, DOMAIN, f"{mock_server_info['Id']}/episode/ep-123", None)

        result = await media_source.async_resolve_media(item)

        assert result.mime_type == "video/mp4"
        mock_client.get_video_stream_url.assert_called_once_with("ep-123")
