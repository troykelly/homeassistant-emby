"""Tests for Emby media browser functionality."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.media_player import MediaClass, MediaType
from homeassistant.components.media_player.browse_media import BrowseMedia
from homeassistant.core import HomeAssistant

from custom_components.embymedia.browse import (
    decode_content_id,
    encode_content_id,
)


class TestContentIdEncoding:
    """Test content ID encoding functions."""

    def test_encode_content_id_no_ids(self) -> None:
        """Test encoding content ID with no IDs."""
        result = encode_content_id("root")
        assert result == "root"

    def test_encode_content_id_single(self) -> None:
        """Test encoding content ID with single ID."""
        result = encode_content_id("library", "abc123")
        assert result == "library:abc123"

    def test_encode_content_id_multiple(self) -> None:
        """Test encoding content ID with multiple IDs."""
        result = encode_content_id("season", "series123", "season456")
        assert result == "season:series123:season456"

    def test_decode_content_id_single(self) -> None:
        """Test decoding content ID with single ID."""
        content_type, ids = decode_content_id("library:abc123")
        assert content_type == "library"
        assert ids == ["abc123"]

    def test_decode_content_id_multiple(self) -> None:
        """Test decoding content ID with multiple IDs."""
        content_type, ids = decode_content_id("season:series123:season456")
        assert content_type == "season"
        assert ids == ["series123", "season456"]

    def test_content_id_roundtrip(self) -> None:
        """Test encoding then decoding preserves values."""
        original_type = "episode"
        original_ids = ["series789", "season1", "ep5"]
        encoded = encode_content_id(original_type, *original_ids)
        decoded_type, decoded_ids = decode_content_id(encoded)
        assert decoded_type == original_type
        assert decoded_ids == original_ids

    def test_decode_content_id_type_only(self) -> None:
        """Test decoding content ID with no IDs."""
        content_type, ids = decode_content_id("root")
        assert content_type == "root"
        assert ids == []


class TestContentTypeMapping:
    """Test Emby type to HA MediaClass mapping."""

    def test_emby_type_to_media_class_movie(self) -> None:
        """Test Movie maps to MOVIE class."""
        from custom_components.embymedia.browse import emby_type_to_media_class
        from homeassistant.components.media_player import MediaClass

        assert emby_type_to_media_class("Movie") == MediaClass.MOVIE

    def test_emby_type_to_media_class_series(self) -> None:
        """Test Series maps to TV_SHOW class."""
        from custom_components.embymedia.browse import emby_type_to_media_class
        from homeassistant.components.media_player import MediaClass

        assert emby_type_to_media_class("Series") == MediaClass.TV_SHOW

    def test_emby_type_to_media_class_season(self) -> None:
        """Test Season maps to SEASON class."""
        from custom_components.embymedia.browse import emby_type_to_media_class
        from homeassistant.components.media_player import MediaClass

        assert emby_type_to_media_class("Season") == MediaClass.SEASON

    def test_emby_type_to_media_class_episode(self) -> None:
        """Test Episode maps to EPISODE class."""
        from custom_components.embymedia.browse import emby_type_to_media_class
        from homeassistant.components.media_player import MediaClass

        assert emby_type_to_media_class("Episode") == MediaClass.EPISODE

    def test_emby_type_to_media_class_audio(self) -> None:
        """Test Audio maps to TRACK class."""
        from custom_components.embymedia.browse import emby_type_to_media_class
        from homeassistant.components.media_player import MediaClass

        assert emby_type_to_media_class("Audio") == MediaClass.TRACK

    def test_emby_type_to_media_class_album(self) -> None:
        """Test MusicAlbum maps to ALBUM class."""
        from custom_components.embymedia.browse import emby_type_to_media_class
        from homeassistant.components.media_player import MediaClass

        assert emby_type_to_media_class("MusicAlbum") == MediaClass.ALBUM

    def test_emby_type_to_media_class_artist(self) -> None:
        """Test MusicArtist maps to ARTIST class."""
        from custom_components.embymedia.browse import emby_type_to_media_class
        from homeassistant.components.media_player import MediaClass

        assert emby_type_to_media_class("MusicArtist") == MediaClass.ARTIST

    def test_emby_type_to_media_class_collection_folder(self) -> None:
        """Test CollectionFolder maps to DIRECTORY class."""
        from custom_components.embymedia.browse import emby_type_to_media_class
        from homeassistant.components.media_player import MediaClass

        assert emby_type_to_media_class("CollectionFolder") == MediaClass.DIRECTORY

    def test_emby_type_to_media_class_unknown(self) -> None:
        """Test unknown type maps to DIRECTORY class."""
        from custom_components.embymedia.browse import emby_type_to_media_class
        from homeassistant.components.media_player import MediaClass

        assert emby_type_to_media_class("Unknown") == MediaClass.DIRECTORY


class TestCanPlayLogic:
    """Test can_play determination."""

    def test_can_play_movie(self) -> None:
        """Test Movie is playable."""
        from custom_components.embymedia.browse import can_play_emby_type

        assert can_play_emby_type("Movie") is True

    def test_can_play_episode(self) -> None:
        """Test Episode is playable."""
        from custom_components.embymedia.browse import can_play_emby_type

        assert can_play_emby_type("Episode") is True

    def test_can_play_audio(self) -> None:
        """Test Audio is playable."""
        from custom_components.embymedia.browse import can_play_emby_type

        assert can_play_emby_type("Audio") is True

    def test_cannot_play_series(self) -> None:
        """Test Series is not directly playable."""
        from custom_components.embymedia.browse import can_play_emby_type

        assert can_play_emby_type("Series") is False

    def test_cannot_play_season(self) -> None:
        """Test Season is not directly playable."""
        from custom_components.embymedia.browse import can_play_emby_type

        assert can_play_emby_type("Season") is False

    def test_cannot_play_collection(self) -> None:
        """Test CollectionFolder is not directly playable."""
        from custom_components.embymedia.browse import can_play_emby_type

        assert can_play_emby_type("CollectionFolder") is False


class TestCanExpandLogic:
    """Test can_expand determination."""

    def test_can_expand_series(self) -> None:
        """Test Series can be expanded."""
        from custom_components.embymedia.browse import can_expand_emby_type

        assert can_expand_emby_type("Series") is True

    def test_can_expand_season(self) -> None:
        """Test Season can be expanded."""
        from custom_components.embymedia.browse import can_expand_emby_type

        assert can_expand_emby_type("Season") is True

    def test_can_expand_collection(self) -> None:
        """Test CollectionFolder can be expanded."""
        from custom_components.embymedia.browse import can_expand_emby_type

        assert can_expand_emby_type("CollectionFolder") is True

    def test_cannot_expand_movie(self) -> None:
        """Test Movie cannot be expanded."""
        from custom_components.embymedia.browse import can_expand_emby_type

        assert can_expand_emby_type("Movie") is False

    def test_cannot_expand_episode(self) -> None:
        """Test Episode cannot be expanded."""
        from custom_components.embymedia.browse import can_expand_emby_type

        assert can_expand_emby_type("Episode") is False

    def test_cannot_expand_audio(self) -> None:
        """Test Audio cannot be expanded."""
        from custom_components.embymedia.browse import can_expand_emby_type

        assert can_expand_emby_type("Audio") is False


# =============================================================================
# Tests for async_browse_media in EmbyMediaPlayer
# =============================================================================


@pytest.fixture
def mock_coordinator_for_browse(hass: HomeAssistant) -> MagicMock:
    """Create a mock coordinator for browse testing."""
    coordinator = MagicMock()
    coordinator.server_id = "server-123"
    coordinator.server_name = "My Emby Server"
    coordinator.last_update_success = True
    coordinator.data = {}
    coordinator.get_session = MagicMock(return_value=None)
    coordinator.async_add_listener = MagicMock(return_value=MagicMock())

    # Mock the client
    client = MagicMock()
    client.async_get_user_views = AsyncMock()
    client.async_get_items = AsyncMock()
    client.async_get_seasons = AsyncMock()
    client.async_get_episodes = AsyncMock()
    client.get_image_url = MagicMock(return_value="http://emby:8096/image.jpg")
    coordinator.client = client

    return coordinator


@pytest.fixture
def mock_session_with_user() -> MagicMock:
    """Create a mock session with user ID."""
    session = MagicMock()
    session.device_id = "device-abc-123"
    session.device_name = "Living Room TV"
    session.client_name = "Emby Theater"
    session.app_version = "4.8.0.0"
    session.is_playing = False
    session.play_state = None
    session.supports_remote_control = True
    session.supported_commands = ["SetVolume", "Mute"]
    session.user_id = "user-xyz-789"
    return session


class TestBrowseMediaRoot:
    """Test browsing at root level (libraries)."""

    @pytest.mark.asyncio
    async def test_browse_media_root_returns_libraries(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test root level browse returns library list."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        # Setup mock to return user views (libraries)
        mock_coordinator_for_browse.client.async_get_user_views.return_value = [
            {"Id": "lib-movies", "Name": "Movies", "CollectionType": "movies"},
            {"Id": "lib-tvshows", "Name": "TV Shows", "CollectionType": "tvshows"},
        ]
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media()

        assert isinstance(result, BrowseMedia)
        assert result.title == "Emby"
        assert result.can_expand is True
        assert result.can_play is False
        assert result.children is not None
        assert len(result.children) == 2
        assert result.children[0].title == "Movies"
        assert result.children[1].title == "TV Shows"

    @pytest.mark.asyncio
    async def test_browse_media_root_with_no_session(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
    ) -> None:
        """Test root browse when no session returns empty root."""
        from homeassistant.components.media_player.errors import BrowseError

        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = None

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-xyz")

        # When no session, we have no user_id, so browsing should raise BrowseError
        with pytest.raises(BrowseError):
            await player.async_browse_media()


class TestBrowseMediaLibrary:
    """Test browsing library contents."""

    @pytest.mark.asyncio
    async def test_browse_media_movies_library(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing movies library returns movies."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_items.return_value = {
            "Items": [
                {"Id": "movie-1", "Name": "Test Movie 1", "Type": "Movie"},
                {"Id": "movie-2", "Name": "Test Movie 2", "Type": "Movie"},
            ],
            "TotalRecordCount": 2,
            "StartIndex": 0,
        }
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.VIDEO,
            media_content_id="library:lib-movies",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 2
        # Movies should be playable
        assert result.children[0].can_play is True
        assert result.children[0].can_expand is False

    @pytest.mark.asyncio
    async def test_browse_media_tvshows_library(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing TV shows library returns series."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_items.return_value = {
            "Items": [
                {"Id": "series-1", "Name": "Test Series", "Type": "Series"},
            ],
            "TotalRecordCount": 1,
            "StartIndex": 0,
        }
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.TVSHOW,
            media_content_id="library:lib-tvshows",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        # Series should be expandable, not directly playable
        assert result.children[0].can_play is False
        assert result.children[0].can_expand is True


class TestBrowseMediaHierarchy:
    """Test hierarchical browsing (series -> season -> episode)."""

    @pytest.mark.asyncio
    async def test_browse_media_series_returns_seasons(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing a series returns its seasons."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_seasons.return_value = [
            {"Id": "season-1", "Name": "Season 1", "Type": "Season", "IndexNumber": 1},
            {"Id": "season-2", "Name": "Season 2", "Type": "Season", "IndexNumber": 2},
        ]
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.TVSHOW,
            media_content_id="series:series-abc",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 2
        # Seasons should be expandable
        assert result.children[0].can_expand is True

    @pytest.mark.asyncio
    async def test_browse_media_season_returns_episodes(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing a season returns its episodes."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_episodes.return_value = [
            {"Id": "ep-1", "Name": "Episode 1", "Type": "Episode", "IndexNumber": 1},
            {"Id": "ep-2", "Name": "Episode 2", "Type": "Episode", "IndexNumber": 2},
        ]
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.TVSHOW,
            media_content_id="season:series-abc:season-1",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 2
        # Episodes should be playable
        assert result.children[0].can_play is True
        assert result.children[0].can_expand is False


class TestBrowseMediaErrors:
    """Test browse media error handling."""

    @pytest.mark.asyncio
    async def test_browse_media_unknown_content_type(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing unknown content type raises error."""
        from homeassistant.components.media_player.errors import BrowseError

        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        with pytest.raises(BrowseError) as exc_info:
            await player.async_browse_media(
                media_content_type=MediaType.VIDEO,
                media_content_id="unknown:xyz",
            )
        assert "Unknown content type" in str(exc_info.value)


class TestBrowseMediaThumbnails:
    """Test thumbnail generation in browse media."""

    @pytest.mark.asyncio
    async def test_library_thumbnail_generation(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test library thumbnails are generated correctly."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_user_views.return_value = [
            {
                "Id": "lib-1",
                "Name": "Movies",
                "CollectionType": "movies",
                "ImageTags": {"Primary": "abc123"},
            },
        ]
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media()

        assert result.children is not None
        assert result.children[0].thumbnail == "http://emby:8096/image.jpg"

    @pytest.mark.asyncio
    async def test_item_thumbnail_generation(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test item thumbnails are generated correctly."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_items.return_value = {
            "Items": [
                {
                    "Id": "movie-1",
                    "Name": "Test Movie",
                    "Type": "Movie",
                    "ImageTags": {"Primary": "def456"},
                },
            ],
            "TotalRecordCount": 1,
            "StartIndex": 0,
        }
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.VIDEO,
            media_content_id="library:lib-movies",
        )

        assert result.children is not None
        assert result.children[0].thumbnail == "http://emby:8096/image.jpg"

    @pytest.mark.asyncio
    async def test_season_thumbnail_generation(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test season thumbnails are generated correctly."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_seasons.return_value = [
            {
                "Id": "season-1",
                "Name": "Season 1",
                "Type": "Season",
                "IndexNumber": 1,
                "ImageTags": {"Primary": "ghi789"},
            },
        ]
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.TVSHOW,
            media_content_id="series:series-abc",
        )

        assert result.children is not None
        assert result.children[0].thumbnail == "http://emby:8096/image.jpg"

    @pytest.mark.asyncio
    async def test_folder_item_browse(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing a folder item uses library content ID."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_items.return_value = {
            "Items": [
                {
                    "Id": "folder-1",
                    "Name": "TV Shows Folder",
                    "Type": "Folder",
                },
            ],
            "TotalRecordCount": 1,
            "StartIndex": 0,
        }
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.VIDEO,
            media_content_id="library:lib-movies",
        )

        assert result.children is not None
        # Folder should get library: prefix content ID
        assert result.children[0].media_content_id == "library:folder-1"
        # Folder should be expandable
        assert result.children[0].can_expand is True


# =============================================================================
# Tests for async_play_media in EmbyMediaPlayer
# =============================================================================


class TestAsyncPlayMedia:
    """Test play media functionality from browse."""

    @pytest.mark.asyncio
    async def test_play_media_movie(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test playing a movie from browse."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user
        mock_coordinator_for_browse.client.async_play_items = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        await player.async_play_media(
            media_type=MediaType.MOVIE,
            media_id="movie-123",
        )

        mock_coordinator_for_browse.client.async_play_items.assert_called_once_with(
            "session-xyz",
            ["movie-123"],
        )

    @pytest.mark.asyncio
    async def test_play_media_episode(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test playing an episode from browse."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user
        mock_coordinator_for_browse.client.async_play_items = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        await player.async_play_media(
            media_type=MediaType.TVSHOW,
            media_id="episode-456",
        )

        mock_coordinator_for_browse.client.async_play_items.assert_called_once_with(
            "session-xyz",
            ["episode-456"],
        )

    @pytest.mark.asyncio
    async def test_play_media_no_session(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
    ) -> None:
        """Test play media when no session is available does nothing."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = None
        mock_coordinator_for_browse.client.async_play_items = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-xyz")
        # Should not raise, just silently return
        await player.async_play_media(
            media_type=MediaType.MOVIE,
            media_id="movie-123",
        )

        # API should not be called
        mock_coordinator_for_browse.client.async_play_items.assert_not_called()

    @pytest.mark.asyncio
    async def test_play_media_with_item_content_id(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test play media extracts item ID from content ID format."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user
        mock_coordinator_for_browse.client.async_play_items = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        # Content ID format from browse: "item:movie-789"
        await player.async_play_media(
            media_type=MediaType.MOVIE,
            media_id="item:movie-789",
        )

        mock_coordinator_for_browse.client.async_play_items.assert_called_once_with(
            "session-xyz",
            ["movie-789"],
        )
