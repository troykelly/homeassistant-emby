"""Tests for Emby media browser functionality."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.media_player import (
    MediaClass,
    MediaPlayerEntityFeature,
    MediaType,
)
from homeassistant.components.media_player.browse_media import BrowseMedia
from homeassistant.core import HomeAssistant

from custom_components.embymedia.browse import (
    decode_content_id,
    emby_type_to_media_class,
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
        assert emby_type_to_media_class("Movie") == MediaClass.MOVIE

    def test_emby_type_to_media_class_series(self) -> None:
        """Test Series maps to TV_SHOW class."""
        assert emby_type_to_media_class("Series") == MediaClass.TV_SHOW

    def test_emby_type_to_media_class_season(self) -> None:
        """Test Season maps to SEASON class."""
        assert emby_type_to_media_class("Season") == MediaClass.SEASON

    def test_emby_type_to_media_class_episode(self) -> None:
        """Test Episode maps to EPISODE class."""
        assert emby_type_to_media_class("Episode") == MediaClass.EPISODE

    def test_emby_type_to_media_class_audio(self) -> None:
        """Test Audio maps to TRACK class."""
        assert emby_type_to_media_class("Audio") == MediaClass.TRACK

    def test_emby_type_to_media_class_album(self) -> None:
        """Test MusicAlbum maps to ALBUM class."""
        assert emby_type_to_media_class("MusicAlbum") == MediaClass.ALBUM

    def test_emby_type_to_media_class_artist(self) -> None:
        """Test MusicArtist maps to ARTIST class."""
        assert emby_type_to_media_class("MusicArtist") == MediaClass.ARTIST

    def test_emby_type_to_media_class_collection_folder(self) -> None:
        """Test CollectionFolder maps to DIRECTORY class."""
        assert emby_type_to_media_class("CollectionFolder") == MediaClass.DIRECTORY

    def test_emby_type_to_media_class_unknown(self) -> None:
        """Test unknown type maps to DIRECTORY class."""
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
    session.app_version = "4.9.2.0"
    session.is_playing = False
    session.play_state = None
    session.supports_remote_control = True
    session.supported_commands = ["SetVolume", "Mute"]
    session.user_id = "user-xyz-789"
    session.session_id = "session-xyz"
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
            start_position_ticks=0,
            play_command="PlayNow",
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
            start_position_ticks=0,
            play_command="PlayNow",
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
            start_position_ticks=0,
            play_command="PlayNow",
        )

    @pytest.mark.asyncio
    async def test_play_media_with_trailing_colon(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test play media extracts empty ID when content ID has trailing colon."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user
        mock_coordinator_for_browse.client.async_play_items = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        # Edge case: content ID format with colon but empty ID (e.g., "item:")
        # decode_content_id("item:") returns ("item", [""])
        await player.async_play_media(
            media_type=MediaType.VIDEO,
            media_id="item:",
        )

        # Should extract the empty string as the ID
        mock_coordinator_for_browse.client.async_play_items.assert_called_once_with(
            "session-xyz",
            [""],
            start_position_ticks=0,
            play_command="PlayNow",
        )


# =============================================================================
# Tests for Music Browsing (Artist -> Album -> Track)
# =============================================================================


class TestBrowseMusicArtist:
    """Test browsing music artist hierarchy."""

    @pytest.mark.asyncio
    async def test_browse_media_artist_returns_albums(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing an artist returns their albums."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_artist_albums = AsyncMock(
            return_value=[
                {"Id": "album-1", "Name": "Album 1", "Type": "MusicAlbum"},
                {"Id": "album-2", "Name": "Album 2", "Type": "MusicAlbum"},
            ]
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.MUSIC,
            media_content_id="artist:artist-xyz",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 2
        # Albums should be expandable AND playable (queues all tracks)
        assert result.children[0].can_expand is True
        assert result.children[0].can_play is True
        assert result.children[0].media_class == MediaClass.ALBUM

    @pytest.mark.asyncio
    async def test_browse_media_album_returns_tracks(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing an album returns its tracks."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_album_tracks = AsyncMock(
            return_value=[
                {"Id": "track-1", "Name": "Track 1", "Type": "Audio", "IndexNumber": 1},
                {"Id": "track-2", "Name": "Track 2", "Type": "Audio", "IndexNumber": 2},
            ]
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.MUSIC,
            media_content_id="album:album-xyz",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 2
        # Tracks should be playable
        assert result.children[0].can_play is True
        assert result.children[0].can_expand is False
        assert result.children[0].media_class == MediaClass.TRACK

    @pytest.mark.asyncio
    async def test_browse_media_music_library_returns_artists(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing music library returns artists."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_items.return_value = {
            "Items": [
                {"Id": "artist-1", "Name": "Artist 1", "Type": "MusicArtist"},
                {"Id": "artist-2", "Name": "Artist 2", "Type": "MusicArtist"},
            ],
            "TotalRecordCount": 2,
            "StartIndex": 0,
        }
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.MUSIC,
            media_content_id="library:lib-music",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 2
        # Artists should be expandable
        assert result.children[0].can_expand is True
        assert result.children[0].can_play is False
        assert result.children[0].media_class == MediaClass.ARTIST

    @pytest.mark.asyncio
    async def test_play_media_track(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test playing a track from browse."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user
        mock_coordinator_for_browse.client.async_play_items = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        await player.async_play_media(
            media_type=MediaType.MUSIC,
            media_id="item:track-123",
        )

        mock_coordinator_for_browse.client.async_play_items.assert_called_once_with(
            "session-xyz",
            ["track-123"],
            start_position_ticks=0,
            play_command="PlayNow",
        )


# =============================================================================
# Tests for Playlist Browsing
# =============================================================================


class TestBrowsePlaylist:
    """Test browsing playlists."""

    @pytest.mark.asyncio
    async def test_browse_media_playlist_returns_items(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing a playlist returns its items."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_playlist_items = AsyncMock(
            return_value=[
                {"Id": "track-1", "Name": "Track 1", "Type": "Audio"},
                {"Id": "movie-1", "Name": "Movie 1", "Type": "Movie"},
            ]
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.PLAYLIST,
            media_content_id="playlist:playlist-xyz",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 2
        # Playlist items should be playable
        assert result.children[0].can_play is True


# =============================================================================
# Tests for Enqueue Support
# =============================================================================


class TestEnqueueSupport:
    """Test enqueue media functionality."""

    @pytest.mark.asyncio
    async def test_play_media_enqueue_add(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test play media with enqueue=add adds to queue."""
        from homeassistant.components.media_player import MediaPlayerEnqueue

        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user
        mock_coordinator_for_browse.client.async_play_items = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        await player.async_play_media(
            media_type=MediaType.MUSIC,
            media_id="item:track-123",
            enqueue=MediaPlayerEnqueue.ADD,
        )

        mock_coordinator_for_browse.client.async_play_items.assert_called_once_with(
            "session-xyz",
            ["track-123"],
            start_position_ticks=0,
            play_command="PlayLast",
        )

    @pytest.mark.asyncio
    async def test_play_media_enqueue_next(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test play media with enqueue=next plays next."""
        from homeassistant.components.media_player import MediaPlayerEnqueue

        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user
        mock_coordinator_for_browse.client.async_play_items = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        await player.async_play_media(
            media_type=MediaType.MUSIC,
            media_id="item:track-123",
            enqueue=MediaPlayerEnqueue.NEXT,
        )

        mock_coordinator_for_browse.client.async_play_items.assert_called_once_with(
            "session-xyz",
            ["track-123"],
            start_position_ticks=0,
            play_command="PlayNext",
        )

    @pytest.mark.asyncio
    async def test_play_media_enqueue_replace(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test play media with enqueue=replace replaces queue."""
        from homeassistant.components.media_player import MediaPlayerEnqueue

        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user
        mock_coordinator_for_browse.client.async_play_items = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        await player.async_play_media(
            media_type=MediaType.MUSIC,
            media_id="item:track-123",
            enqueue=MediaPlayerEnqueue.REPLACE,
        )

        mock_coordinator_for_browse.client.async_play_items.assert_called_once_with(
            "session-xyz",
            ["track-123"],
            start_position_ticks=0,
            play_command="PlayNow",
        )

    @pytest.mark.asyncio
    async def test_play_media_enqueue_play(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test play media with enqueue=play uses PlayNow."""
        from homeassistant.components.media_player import MediaPlayerEnqueue

        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user
        mock_coordinator_for_browse.client.async_play_items = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        await player.async_play_media(
            media_type=MediaType.MUSIC,
            media_id="item:track-123",
            enqueue=MediaPlayerEnqueue.PLAY,
        )

        mock_coordinator_for_browse.client.async_play_items.assert_called_once_with(
            "session-xyz",
            ["track-123"],
            start_position_ticks=0,
            play_command="PlayNow",
        )

    def test_supported_features_includes_enqueue(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test supported features includes MEDIA_ENQUEUE."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        features = player.supported_features

        assert features & MediaPlayerEntityFeature.MEDIA_ENQUEUE


# =============================================================================
# Tests for Queue Multiple Items (Albums/Seasons)
# =============================================================================


class TestQueueMultipleItems:
    """Test queuing multiple items like albums or seasons."""

    @pytest.mark.asyncio
    async def test_play_album_queues_all_tracks(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test playing an album queues all its tracks."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        # Mock to return album tracks
        mock_coordinator_for_browse.client.async_get_album_tracks = AsyncMock(
            return_value=[
                {"Id": "track-1", "Name": "Track 1", "Type": "Audio"},
                {"Id": "track-2", "Name": "Track 2", "Type": "Audio"},
                {"Id": "track-3", "Name": "Track 3", "Type": "Audio"},
            ]
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user
        mock_coordinator_for_browse.client.async_play_items = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        await player.async_play_media(
            media_type=MediaType.MUSIC,
            media_id="album:album-xyz",
        )

        # Should play all tracks from the album
        mock_coordinator_for_browse.client.async_play_items.assert_called_once_with(
            "session-xyz",
            ["track-1", "track-2", "track-3"],
            start_position_ticks=0,
            play_command="PlayNow",
        )

    @pytest.mark.asyncio
    async def test_play_season_queues_all_episodes(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test playing a season queues all its episodes."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        # Mock to return season episodes
        mock_coordinator_for_browse.client.async_get_episodes.return_value = [
            {"Id": "ep-1", "Name": "Episode 1", "Type": "Episode"},
            {"Id": "ep-2", "Name": "Episode 2", "Type": "Episode"},
        ]
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user
        mock_coordinator_for_browse.client.async_play_items = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        await player.async_play_media(
            media_type=MediaType.TVSHOW,
            media_id="season:series-abc:season-1",
        )

        # Should play all episodes from the season
        mock_coordinator_for_browse.client.async_play_items.assert_called_once_with(
            "session-xyz",
            ["ep-1", "ep-2"],
            start_position_ticks=0,
            play_command="PlayNow",
        )

    @pytest.mark.asyncio
    async def test_play_playlist_queues_all_items(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test playing a playlist queues all its items."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_playlist_items = AsyncMock(
            return_value=[
                {"Id": "item-1", "Name": "Item 1", "Type": "Audio"},
                {"Id": "item-2", "Name": "Item 2", "Type": "Movie"},
            ]
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user
        mock_coordinator_for_browse.client.async_play_items = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        await player.async_play_media(
            media_type=MediaType.PLAYLIST,
            media_id="playlist:playlist-xyz",
        )

        mock_coordinator_for_browse.client.async_play_items.assert_called_once_with(
            "session-xyz",
            ["item-1", "item-2"],
            start_position_ticks=0,
            play_command="PlayNow",
        )

    @pytest.mark.asyncio
    async def test_resolve_play_media_ids_no_session(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
    ) -> None:
        """Test _resolve_play_media_ids when no session returns original ids."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = None

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player._resolve_play_media_ids("album", ["album-123"])

        # Should return original ids unchanged
        assert result == ["album-123"]

    @pytest.mark.asyncio
    async def test_resolve_play_media_ids_empty_ids(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test _resolve_play_media_ids with empty ids returns empty list."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player._resolve_play_media_ids("item", [])

        assert result == []


# =============================================================================
# Tests for item_to_browse_media with different types
# =============================================================================


class TestItemToBrowseMedia:
    """Test _item_to_browse_media with different item types."""

    def test_item_to_browse_media_music_album(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
    ) -> None:
        """Test _item_to_browse_media with MusicAlbum type."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.get_image_url.return_value = (
            "http://emby.local/image.jpg"
        )

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = player._item_to_browse_media(
            {"Id": "album-123", "Name": "Test Album", "Type": "MusicAlbum"}
        )

        assert result.media_content_id == "album:album-123"
        assert result.media_class == MediaClass.ALBUM

    def test_item_to_browse_media_playlist(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
    ) -> None:
        """Test _item_to_browse_media with Playlist type."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.get_image_url.return_value = (
            "http://emby.local/image.jpg"
        )

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = player._item_to_browse_media(
            {"Id": "playlist-123", "Name": "Test Playlist", "Type": "Playlist"}
        )

        assert result.media_content_id == "playlist:playlist-123"
        assert result.media_class == MediaClass.PLAYLIST

    def test_album_to_browse_media_with_thumbnail(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
    ) -> None:
        """Test _album_to_browse_media generates thumbnail when Primary tag exists."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.get_image_url.return_value = (
            "http://emby.local/album-image.jpg"
        )

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = player._album_to_browse_media(
            {
                "Id": "album-123",
                "Name": "Test Album",
                "Type": "MusicAlbum",
                "ImageTags": {"Primary": "tag123"},
            }
        )

        assert result.thumbnail == "http://emby.local/album-image.jpg"
        mock_coordinator_for_browse.client.get_image_url.assert_called_once_with(
            "album-123", image_type="Primary", tag="tag123"
        )

    def test_track_to_browse_media_with_thumbnail(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
    ) -> None:
        """Test _track_to_browse_media generates thumbnail when Primary tag exists."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.get_image_url.return_value = (
            "http://emby.local/track-image.jpg"
        )

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = player._track_to_browse_media(
            {
                "Id": "track-123",
                "Name": "Test Track",
                "Type": "Audio",
                "ImageTags": {"Primary": "tag456"},
            }
        )

        assert result.thumbnail == "http://emby.local/track-image.jpg"
        mock_coordinator_for_browse.client.get_image_url.assert_called_once_with(
            "track-123", image_type="Primary", tag="tag456"
        )


# =============================================================================
# Tests for Collection Browsing
# =============================================================================


class TestBrowseCollection:
    """Test browsing collections (BoxSets)."""

    @pytest.mark.asyncio
    async def test_browse_media_collection_returns_items(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing a collection returns its items."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_collection_items = AsyncMock(
            return_value=[
                {"Id": "movie-1", "Name": "Movie 1", "Type": "Movie"},
                {"Id": "movie-2", "Name": "Movie 2", "Type": "Movie"},
            ]
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.VIDEO,
            media_content_id="collection:collection-xyz",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 2
        # Collection items should be playable
        assert result.children[0].can_play is True

    def test_item_to_browse_media_boxset(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
    ) -> None:
        """Test _item_to_browse_media with BoxSet (collection) type."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.get_image_url.return_value = (
            "http://emby.local/image.jpg"
        )

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = player._item_to_browse_media(
            {"Id": "collection-123", "Name": "Test Collection", "Type": "BoxSet"}
        )

        assert result.media_content_id == "collection:collection-123"
        assert result.can_expand is True


# =============================================================================
# Tests for Live TV Browsing
# =============================================================================


class TestBrowseLiveTV:
    """Test browsing Live TV channels."""

    @pytest.mark.asyncio
    async def test_browse_media_livetv_returns_channels(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing Live TV returns channels."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_live_tv_channels = AsyncMock(
            return_value=[
                {"Id": "ch-1", "Name": "Channel 1", "Type": "TvChannel"},
                {"Id": "ch-2", "Name": "Channel 2", "Type": "TvChannel"},
            ]
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.CHANNEL,
            media_content_id="livetv:",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 2
        # Channels should be playable
        assert result.children[0].can_play is True
        assert result.children[0].media_class == MediaClass.CHANNEL


# =============================================================================
# Tests for Shuffle/Repeat Options
# =============================================================================


class TestShuffleRepeatOptions:
    """Test shuffle and repeat mode support."""

    def test_supported_features_includes_shuffle_repeat(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test supported features includes SHUFFLE_SET and REPEAT_SET."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        features = player.supported_features

        assert features & MediaPlayerEntityFeature.SHUFFLE_SET
        assert features & MediaPlayerEntityFeature.REPEAT_SET

    @pytest.mark.asyncio
    async def test_set_shuffle_on(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test enabling shuffle mode."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user
        mock_coordinator_for_browse.client.async_send_general_command = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        await player.async_set_shuffle(shuffle=True)

        mock_coordinator_for_browse.client.async_send_general_command.assert_called_once_with(
            "session-xyz",
            "SetShuffleQueue",
            {"ShuffleMode": "Shuffle"},
        )

    @pytest.mark.asyncio
    async def test_set_shuffle_off(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test disabling shuffle mode."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user
        mock_coordinator_for_browse.client.async_send_general_command = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        await player.async_set_shuffle(shuffle=False)

        mock_coordinator_for_browse.client.async_send_general_command.assert_called_once_with(
            "session-xyz",
            "SetShuffleQueue",
            {"ShuffleMode": "Sorted"},
        )

    @pytest.mark.asyncio
    async def test_set_repeat_off(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test setting repeat mode to off."""
        from homeassistant.components.media_player import RepeatMode

        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user
        mock_coordinator_for_browse.client.async_send_general_command = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        await player.async_set_repeat(repeat=RepeatMode.OFF)

        mock_coordinator_for_browse.client.async_send_general_command.assert_called_once_with(
            "session-xyz",
            "SetRepeatMode",
            {"RepeatMode": "RepeatNone"},
        )

    @pytest.mark.asyncio
    async def test_set_repeat_one(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test setting repeat mode to one."""
        from homeassistant.components.media_player import RepeatMode

        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user
        mock_coordinator_for_browse.client.async_send_general_command = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        await player.async_set_repeat(repeat=RepeatMode.ONE)

        mock_coordinator_for_browse.client.async_send_general_command.assert_called_once_with(
            "session-xyz",
            "SetRepeatMode",
            {"RepeatMode": "RepeatOne"},
        )

    @pytest.mark.asyncio
    async def test_set_repeat_all(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test setting repeat mode to all."""
        from homeassistant.components.media_player import RepeatMode

        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user
        mock_coordinator_for_browse.client.async_send_general_command = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        await player.async_set_repeat(repeat=RepeatMode.ALL)

        mock_coordinator_for_browse.client.async_send_general_command.assert_called_once_with(
            "session-xyz",
            "SetRepeatMode",
            {"RepeatMode": "RepeatAll"},
        )

    @pytest.mark.asyncio
    async def test_set_shuffle_no_session(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
    ) -> None:
        """Test set shuffle when no session does nothing."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = None
        mock_coordinator_for_browse.client.async_send_general_command = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        await player.async_set_shuffle(shuffle=True)

        # Should not call API
        mock_coordinator_for_browse.client.async_send_general_command.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_repeat_no_session(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
    ) -> None:
        """Test set repeat when no session does nothing."""
        from homeassistant.components.media_player import RepeatMode

        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = None
        mock_coordinator_for_browse.client.async_send_general_command = AsyncMock()

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        await player.async_set_repeat(repeat=RepeatMode.ALL)

        # Should not call API
        mock_coordinator_for_browse.client.async_send_general_command.assert_not_called()


# =============================================================================
# Tests for Music Library Special Handling
# =============================================================================


class TestMusicLibraryBrowsing:
    """Test special handling for music library browsing."""

    @pytest.mark.asyncio
    async def test_browse_music_library_shows_categories(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test that browsing a music library shows category menu (Artists, Albums, etc).

        When browsing a music library (CollectionType=music), the implementation
        should show category options for browsing instead of immediately listing artists.
        """
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.MUSIC,
            media_content_id="musiclibrary:lib-music",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        # Should have categories: Artists, Albums, Genres, Playlists
        assert len(result.children) == 4
        category_titles = [child.title for child in result.children]
        assert "Artists" in category_titles
        assert "Albums" in category_titles
        assert "Genres" in category_titles
        assert "Playlists" in category_titles

        # Categories should be expandable but not playable
        for child in result.children:
            assert child.can_expand is True
            assert child.can_play is False
            # Categories can be DIRECTORY or PLAYLIST (for playlists category)
            assert child.media_class in (MediaClass.DIRECTORY, MediaClass.PLAYLIST)

    @pytest.mark.asyncio
    async def test_browse_music_artists_category_shows_letters(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test that browsing Artists category shows A-Z letter filters."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.MUSIC,
            media_content_id="musicartists:lib-music",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        # Should have A-Z + # for numbers/symbols = 27 items
        assert len(result.children) == 27
        # Check first few letters
        assert result.children[0].title == "#"  # Numbers/symbols first
        assert result.children[1].title == "A"
        assert result.children[2].title == "B"
        assert result.children[-1].title == "Z"

        # Letters should be expandable
        for child in result.children:
            assert child.can_expand is True
            assert child.can_play is False

    @pytest.mark.asyncio
    async def test_browse_artists_by_letter_fetches_filtered_artists(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test that browsing a letter fetches artists starting with that letter."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_items.return_value = {
            "Items": [
                {"Id": "artist-1", "Name": "AC/DC", "Type": "MusicArtist"},
                {"Id": "artist-2", "Name": "Aerosmith", "Type": "MusicArtist"},
            ],
            "TotalRecordCount": 2,
            "StartIndex": 0,
        }
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.MUSIC,
            media_content_id="musicartistletter:lib-music:A",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 2
        # Artists should be expandable
        assert result.children[0].can_expand is True
        assert result.children[0].media_class == MediaClass.ARTIST
        assert result.children[0].media_content_id == "artist:artist-1"

        # Verify the API was called with name_starts_with filter
        mock_coordinator_for_browse.client.async_get_items.assert_called_once_with(
            "user-xyz-789",
            parent_id="lib-music",
            include_item_types="MusicArtist",
            recursive=True,
            name_starts_with="A",
        )

    @pytest.mark.asyncio
    async def test_browse_music_albums_category_fetches_all_albums(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test that browsing Albums category shows A-Z letter filters for albums."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.MUSIC,
            media_content_id="musicalbums:lib-music",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        # Should have A-Z + # for numbers/symbols = 27 items
        assert len(result.children) == 27

    @pytest.mark.asyncio
    async def test_browse_music_genres_category_fetches_genres(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test that browsing Genres category fetches music genres."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_music_genres = AsyncMock(
            return_value=[
                {"Id": "genre-1", "Name": "Rock"},
                {"Id": "genre-2", "Name": "Jazz"},
            ]
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.MUSIC,
            media_content_id="musicgenres:lib-music",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 2
        assert result.children[0].title == "Rock"
        assert result.children[1].title == "Jazz"

    @pytest.mark.asyncio
    async def test_browse_music_playlists_category_fetches_playlists(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test that browsing Playlists category fetches music playlists."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_items.return_value = {
            "Items": [
                {"Id": "pl-1", "Name": "My Favorites", "Type": "Playlist"},
                {"Id": "pl-2", "Name": "Party Mix", "Type": "Playlist"},
            ],
            "TotalRecordCount": 2,
            "StartIndex": 0,
        }
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.MUSIC,
            media_content_id="musicplaylists:lib-music",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 2
        assert result.children[0].title == "My Favorites"
        # Playlists should be playable and expandable
        assert result.children[0].can_play is True
        assert result.children[0].can_expand is True

    @pytest.mark.asyncio
    async def test_root_browse_encodes_all_library_types_correctly(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test root browse encodes all library types with correct prefixes."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_user_views.return_value = [
            {"Id": "lib-movies", "Name": "Movies", "CollectionType": "movies"},
            {"Id": "lib-tvshows", "Name": "TV Shows", "CollectionType": "tvshows"},
            {"Id": "lib-music", "Name": "Music", "CollectionType": "music"},
            {"Id": "lib-livetv", "Name": "Live TV", "CollectionType": "livetv"},
        ]
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media()

        assert result.children is not None
        assert len(result.children) == 4
        # Movies library should use movielibrary: prefix for category browsing
        assert result.children[0].media_content_id == "movielibrary:lib-movies"
        # TV Shows library should use tvlibrary: prefix for category browsing
        assert result.children[1].media_content_id == "tvlibrary:lib-tvshows"
        # Music library should use musiclibrary: prefix for special handling
        assert result.children[2].media_content_id == "musiclibrary:lib-music"
        # Live TV library should use livetv prefix for special handling
        assert result.children[3].media_content_id == "livetv"

    @pytest.mark.asyncio
    async def test_root_browse_unknown_library_type_uses_generic_prefix(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test root browse uses generic library: prefix for unknown types."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_user_views.return_value = [
            {"Id": "lib-photos", "Name": "Photos", "CollectionType": "photos"},
            {"Id": "lib-books", "Name": "Books", "CollectionType": "books"},
        ]
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media()

        assert result.children is not None
        assert len(result.children) == 2
        # Unknown library types should use generic library: prefix
        assert result.children[0].media_content_id == "library:lib-photos"
        assert result.children[1].media_content_id == "library:lib-books"


class TestMusicBrowsingEdgeCases:
    """Test edge cases for music library browsing."""

    @pytest.mark.asyncio
    async def test_browse_artists_by_hash_symbol(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test that browsing # (hash) filters non-alpha artists."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        # Return mixed results - API doesn't filter non-alpha, we must do it
        mock_coordinator_for_browse.client.async_get_items.return_value = {
            "Items": [
                {"Id": "artist-1", "Name": "2Pac", "Type": "MusicArtist"},
                {"Id": "artist-2", "Name": "3 Doors Down", "Type": "MusicArtist"},
                {
                    "Id": "artist-3",
                    "Name": "AC/DC",
                    "Type": "MusicArtist",
                },  # Should be filtered out
            ],
            "TotalRecordCount": 3,
            "StartIndex": 0,
        }
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.MUSIC,
            media_content_id="musicartistletter:lib-music:#",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        # Only non-alpha artists should be included
        assert len(result.children) == 2
        assert result.children[0].title == "2Pac"
        assert result.children[1].title == "3 Doors Down"

    @pytest.mark.asyncio
    async def test_browse_albums_by_letter(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test that browsing albums by letter fetches filtered albums."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_items.return_value = {
            "Items": [
                {"Id": "album-1", "Name": "Abbey Road", "Type": "MusicAlbum"},
                {"Id": "album-2", "Name": "Appetite for Destruction", "Type": "MusicAlbum"},
            ],
            "TotalRecordCount": 2,
            "StartIndex": 0,
        }
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.MUSIC,
            media_content_id="musicalbumletter:lib-music:A",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 2
        assert result.children[0].title == "Abbey Road"
        # Albums should be playable and expandable
        assert result.children[0].can_play is True
        assert result.children[0].can_expand is True

        # Verify API was called with correct filter
        mock_coordinator_for_browse.client.async_get_items.assert_called_once_with(
            "user-xyz-789",
            parent_id="lib-music",
            include_item_types="MusicAlbum",
            recursive=True,
            name_starts_with="A",
        )

    @pytest.mark.asyncio
    async def test_browse_albums_by_hash_symbol(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test that browsing # (hash) filters non-alpha albums."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_items.return_value = {
            "Items": [
                {"Id": "album-1", "Name": "1989", "Type": "MusicAlbum"},
                {"Id": "album-2", "Name": "21", "Type": "MusicAlbum"},
                {"Id": "album-3", "Name": "Abbey Road", "Type": "MusicAlbum"},  # Filtered
            ],
            "TotalRecordCount": 3,
            "StartIndex": 0,
        }
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.MUSIC,
            media_content_id="musicalbumletter:lib-music:#",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 2

    @pytest.mark.asyncio
    async def test_browse_genre_items(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test that browsing a genre shows albums in that genre."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_items.return_value = {
            "Items": [
                {"Id": "album-1", "Name": "Rock Album 1", "Type": "MusicAlbum"},
                {"Id": "album-2", "Name": "Rock Album 2", "Type": "MusicAlbum"},
            ],
            "TotalRecordCount": 2,
            "StartIndex": 0,
        }
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.MUSIC,
            media_content_id="musicgenre:lib-music:genre-rock",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 2
        assert result.media_class == MediaClass.GENRE


class TestLiveTVLibraryBrowsing:
    """Test special handling for Live TV library browsing."""

    @pytest.mark.asyncio
    async def test_browse_livetv_library_uses_channels_api(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test that browsing Live TV library fetches channels via dedicated API.

        When browsing a Live TV library (CollectionType=livetv), the implementation
        should use async_get_live_tv_channels instead of async_get_items.
        """
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_live_tv_channels = AsyncMock(
            return_value=[
                {"Id": "ch-1", "Name": "Channel 1", "Type": "TvChannel"},
                {"Id": "ch-2", "Name": "Channel 2", "Type": "TvChannel"},
            ]
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.CHANNEL,
            media_content_id="livetv:",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 2
        # Channels should be playable
        assert result.children[0].can_play is True
        assert result.children[0].media_class == MediaClass.CHANNEL
        # Content IDs should encode as item (playable)
        assert result.children[0].media_content_id == "item:ch-1"

        # Verify the Live TV channels API was called
        mock_coordinator_for_browse.client.async_get_live_tv_channels.assert_called_once_with(
            "user-xyz-789"
        )


class TestMovieLibraryBrowsing:
    """Test movie library category-based browsing."""

    @pytest.mark.asyncio
    async def test_browse_movie_library_shows_categories(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test that browsing a movies library shows category menu."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.VIDEO,
            media_content_id="movielibrary:lib-movies",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        # Should have categories: A-Z, Year, Decade, Genre, Collections
        assert len(result.children) >= 5
        category_titles = [c.title for c in result.children]
        assert "A-Z" in category_titles
        assert "Year" in category_titles
        assert "Decade" in category_titles
        assert "Genre" in category_titles
        assert "Collections" in category_titles

    @pytest.mark.asyncio
    async def test_browse_movie_az_shows_letters(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test that browsing movie A-Z shows letter menu."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.VIDEO,
            media_content_id="movieaz:lib-movies",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        # Should have 27 items: # + A-Z
        assert len(result.children) == 27
        assert result.children[0].title == "#"
        assert result.children[1].title == "A"
        assert result.children[-1].title == "Z"

    @pytest.mark.asyncio
    async def test_browse_movies_by_letter(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing movies starting with a specific letter."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_items = AsyncMock(
            return_value={
                "Items": [
                    {"Id": "movie-1", "Name": "Avatar", "Type": "Movie", "ImageTags": {}},
                    {"Id": "movie-2", "Name": "Alien", "Type": "Movie", "ImageTags": {}},
                ],
                "TotalRecordCount": 2,
            }
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.VIDEO,
            media_content_id="movieazletter:lib-movies:A",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 2
        assert result.children[0].title == "Avatar"
        # Verify API was called with name filter
        mock_coordinator_for_browse.client.async_get_items.assert_called_once()
        call_kwargs = mock_coordinator_for_browse.client.async_get_items.call_args.kwargs
        assert call_kwargs.get("name_starts_with") == "A"
        assert call_kwargs.get("include_item_types") == "Movie"

    @pytest.mark.asyncio
    async def test_browse_movie_years_shows_year_list(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing movie years shows available years."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_years = AsyncMock(
            return_value=[
                {"Name": "2024", "Id": "2024"},
                {"Name": "2023", "Id": "2023"},
                {"Name": "2022", "Id": "2022"},
            ]
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.VIDEO,
            media_content_id="movieyear:lib-movies",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 3
        # Years should be sorted newest first
        assert result.children[0].title == "2024"

    @pytest.mark.asyncio
    async def test_browse_movies_by_year(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing movies from a specific year."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_items = AsyncMock(
            return_value={
                "Items": [
                    {"Id": "movie-1", "Name": "Movie 2024", "Type": "Movie", "ImageTags": {}},
                ],
                "TotalRecordCount": 1,
            }
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.VIDEO,
            media_content_id="movieyearitems:lib-movies:2024",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 1
        # Verify API was called with year filter
        mock_coordinator_for_browse.client.async_get_items.assert_called_once()
        call_kwargs = mock_coordinator_for_browse.client.async_get_items.call_args.kwargs
        assert call_kwargs.get("years") == "2024"

    @pytest.mark.asyncio
    async def test_browse_movie_years_api_error_returns_empty(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing movie years returns empty list when API fails."""
        from custom_components.embymedia.exceptions import EmbyServerError
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        # Simulate Emby server returning 500 error (happens on some servers)
        mock_coordinator_for_browse.client.async_get_years = AsyncMock(
            side_effect=EmbyServerError("Server error: 500 Internal Server Error")
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.VIDEO,
            media_content_id="movieyear:lib-movies",
        )

        # Should return empty children instead of raising an error
        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 0

    @pytest.mark.asyncio
    async def test_browse_movies_by_year_api_error_returns_empty(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing movies by year returns empty list when API fails."""
        from custom_components.embymedia.exceptions import EmbyServerError
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        # Simulate Emby server returning 500 error
        mock_coordinator_for_browse.client.async_get_items = AsyncMock(
            side_effect=EmbyServerError("Server error: 500 Internal Server Error")
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.VIDEO,
            media_content_id="movieyearitems:lib-movies:2024",
        )

        # Should return empty children instead of raising an error
        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 0

    @pytest.mark.asyncio
    async def test_browse_movie_decades_shows_decades(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing movie decades shows decade list."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.VIDEO,
            media_content_id="moviedecade:lib-movies",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        # Should have decades from 1920s to 2020s
        assert len(result.children) >= 10
        decade_titles = [c.title for c in result.children]
        assert "2020s" in decade_titles
        assert "2010s" in decade_titles
        assert "1990s" in decade_titles

    @pytest.mark.asyncio
    async def test_browse_movies_by_decade(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing movies from a specific decade."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_items = AsyncMock(
            return_value={
                "Items": [
                    {"Id": "movie-1", "Name": "90s Movie", "Type": "Movie", "ImageTags": {}},
                ],
                "TotalRecordCount": 1,
            }
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.VIDEO,
            media_content_id="moviedecadeitems:lib-movies:1990",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        # Verify API was called with decade year range
        mock_coordinator_for_browse.client.async_get_items.assert_called_once()
        call_kwargs = mock_coordinator_for_browse.client.async_get_items.call_args.kwargs
        # Decade should filter years 1990-1999
        assert "1990" in call_kwargs.get("years", "")

    @pytest.mark.asyncio
    async def test_browse_movie_genres_shows_genres(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing movie genres shows genre list."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_genres = AsyncMock(
            return_value=[
                {"Id": "genre-1", "Name": "Action"},
                {"Id": "genre-2", "Name": "Comedy"},
                {"Id": "genre-3", "Name": "Drama"},
            ]
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.VIDEO,
            media_content_id="moviegenre:lib-movies",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 3
        assert result.children[0].title == "Action"
        assert result.children[0].media_class == MediaClass.GENRE

    @pytest.mark.asyncio
    async def test_browse_movies_by_genre(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing movies in a specific genre."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_items = AsyncMock(
            return_value={
                "Items": [
                    {"Id": "movie-1", "Name": "Action Movie", "Type": "Movie", "ImageTags": {}},
                ],
                "TotalRecordCount": 1,
            }
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.VIDEO,
            media_content_id="moviegenreitems:lib-movies:genre-action",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        # Verify API was called with genre filter
        mock_coordinator_for_browse.client.async_get_items.assert_called_once()
        call_kwargs = mock_coordinator_for_browse.client.async_get_items.call_args.kwargs
        assert call_kwargs.get("genre_ids") == "genre-action"

    @pytest.mark.asyncio
    async def test_browse_movie_collections_shows_collections(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing movie collections shows collection list."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_items = AsyncMock(
            return_value={
                "Items": [
                    {"Id": "box-1", "Name": "Marvel Collection", "Type": "BoxSet", "ImageTags": {}},
                    {
                        "Id": "box-2",
                        "Name": "Star Wars Collection",
                        "Type": "BoxSet",
                        "ImageTags": {},
                    },
                ],
                "TotalRecordCount": 2,
            }
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.VIDEO,
            media_content_id="moviecollection:lib-movies",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 2
        assert result.children[0].title == "Marvel Collection"
        # Collections should be expandable (can browse into them)
        assert result.children[0].can_expand is True


class TestTVShowLibraryBrowsing:
    """Test TV show library category-based browsing."""

    @pytest.mark.asyncio
    async def test_browse_tv_library_shows_categories(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test that browsing a TV shows library shows category menu."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.TVSHOW,
            media_content_id="tvlibrary:lib-tv",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        # Should have categories: A-Z, Year, Decade, Genre
        assert len(result.children) >= 4
        category_titles = [c.title for c in result.children]
        assert "A-Z" in category_titles
        assert "Year" in category_titles
        assert "Decade" in category_titles
        assert "Genre" in category_titles

    @pytest.mark.asyncio
    async def test_browse_tv_az_shows_letters(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test that browsing TV A-Z shows letter menu."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.TVSHOW,
            media_content_id="tvaz:lib-tv",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        # Should have 27 items: # + A-Z
        assert len(result.children) == 27

    @pytest.mark.asyncio
    async def test_browse_tv_by_letter(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing TV shows starting with a specific letter."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_items = AsyncMock(
            return_value={
                "Items": [
                    {"Id": "tv-1", "Name": "The X-Files", "Type": "Series", "ImageTags": {}},
                ],
                "TotalRecordCount": 1,
            }
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.TVSHOW,
            media_content_id="tvazletter:lib-tv:X",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 1
        # TV shows should be expandable (to seasons)
        assert result.children[0].can_expand is True

    @pytest.mark.asyncio
    async def test_browse_tv_genres_shows_genres(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing TV genres shows genre list."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_genres = AsyncMock(
            return_value=[
                {"Id": "genre-1", "Name": "Sci-Fi"},
                {"Id": "genre-2", "Name": "Drama"},
            ]
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.TVSHOW,
            media_content_id="tvgenre:lib-tv",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 2

    @pytest.mark.asyncio
    async def test_browse_tv_years_shows_year_list(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing TV show years shows available years."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_years = AsyncMock(
            return_value=[
                {"Name": "2024", "Id": "2024"},
                {"Name": "2023", "Id": "2023"},
            ]
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.TVSHOW,
            media_content_id="tvyear:lib-tv",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 2

    @pytest.mark.asyncio
    async def test_browse_tv_by_year(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing TV shows from a specific year."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_items = AsyncMock(
            return_value={
                "Items": [
                    {"Id": "tv-1", "Name": "Show 2024", "Type": "Series", "ImageTags": {}},
                ],
                "TotalRecordCount": 1,
            }
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.TVSHOW,
            media_content_id="tvyearitems:lib-tv:2024",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 1

    @pytest.mark.asyncio
    async def test_browse_tv_years_api_error_returns_empty(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing TV years returns empty list when API fails."""
        from custom_components.embymedia.exceptions import EmbyServerError
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        # Simulate Emby server returning 500 error
        mock_coordinator_for_browse.client.async_get_years = AsyncMock(
            side_effect=EmbyServerError("Server error: 500 Internal Server Error")
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.TVSHOW,
            media_content_id="tvyear:lib-tv",
        )

        # Should return empty children instead of raising an error
        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 0

    @pytest.mark.asyncio
    async def test_browse_tv_by_year_api_error_returns_empty(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing TV shows by year returns empty list when API fails."""
        from custom_components.embymedia.exceptions import EmbyServerError
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        # Simulate Emby server returning 500 error
        mock_coordinator_for_browse.client.async_get_items = AsyncMock(
            side_effect=EmbyServerError("Server error: 500 Internal Server Error")
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.TVSHOW,
            media_content_id="tvyearitems:lib-tv:2024",
        )

        # Should return empty children instead of raising an error
        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 0

    @pytest.mark.asyncio
    async def test_browse_tv_decades_shows_decades(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing TV show decades shows decade list."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.TVSHOW,
            media_content_id="tvdecade:lib-tv",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        # Should have decades from 1920s to 2020s
        assert len(result.children) >= 10
        decade_titles = [c.title for c in result.children]
        assert "2020s" in decade_titles

    @pytest.mark.asyncio
    async def test_browse_tv_by_decade(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing TV shows from a specific decade."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_items = AsyncMock(
            return_value={
                "Items": [
                    {"Id": "tv-1", "Name": "90s Show", "Type": "Series", "ImageTags": {}},
                ],
                "TotalRecordCount": 1,
            }
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.TVSHOW,
            media_content_id="tvdecadeitems:lib-tv:1990",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None

    @pytest.mark.asyncio
    async def test_browse_tv_by_genre(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing TV shows in a specific genre."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_items = AsyncMock(
            return_value={
                "Items": [
                    {"Id": "tv-1", "Name": "Sci-Fi Show", "Type": "Series", "ImageTags": {}},
                ],
                "TotalRecordCount": 1,
            }
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.TVSHOW,
            media_content_id="tvgenreitems:lib-tv:genre-scifi",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None

    @pytest.mark.asyncio
    async def test_browse_movies_by_letter_non_alpha(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing movies starting with # (non-alpha)."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_items = AsyncMock(
            return_value={
                "Items": [
                    {
                        "Id": "movie-1",
                        "Name": "2001: A Space Odyssey",
                        "Type": "Movie",
                        "ImageTags": {},
                    },
                    {"Id": "movie-2", "Name": "Alien", "Type": "Movie", "ImageTags": {}},
                ],
                "TotalRecordCount": 2,
            }
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.VIDEO,
            media_content_id="movieazletter:lib-movies:#",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        # Only "2001: A Space Odyssey" should be included (starts with number)
        assert len(result.children) == 1
        assert result.children[0].title == "2001: A Space Odyssey"

    @pytest.mark.asyncio
    async def test_browse_tv_by_letter_non_alpha(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing TV shows starting with # (non-alpha)."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_items = AsyncMock(
            return_value={
                "Items": [
                    {"Id": "tv-1", "Name": "24", "Type": "Series", "ImageTags": {}},
                    {"Id": "tv-2", "Name": "The X-Files", "Type": "Series", "ImageTags": {}},
                ],
                "TotalRecordCount": 2,
            }
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.TVSHOW,
            media_content_id="tvazletter:lib-tv:#",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        # Only "24" should be included (starts with number)
        assert len(result.children) == 1
        assert result.children[0].title == "24"

    @pytest.mark.asyncio
    async def test_browse_movie_studios_shows_studios(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing movie studios shows studio list."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_studios = AsyncMock(
            return_value=[
                {"Id": "studio-1", "Name": "Warner Bros"},
                {"Id": "studio-2", "Name": "Disney"},
                {"Id": "studio-3", "Name": "Netflix"},
            ]
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.VIDEO,
            media_content_id="moviestudio:lib-movies",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 3
        assert result.children[0].title == "Warner Bros"
        assert result.children[1].title == "Disney"
        assert result.children[2].title == "Netflix"

    @pytest.mark.asyncio
    async def test_browse_movies_by_studio(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing movies from a specific studio."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_items = AsyncMock(
            return_value={
                "Items": [
                    {"Id": "movie-1", "Name": "Batman", "Type": "Movie", "ImageTags": {}},
                    {"Id": "movie-2", "Name": "Superman", "Type": "Movie", "ImageTags": {}},
                ],
                "TotalRecordCount": 2,
            }
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.VIDEO,
            media_content_id="moviestudioitems:lib-movies:studio-warner",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 2
        # Verify API was called with studio filter
        mock_coordinator_for_browse.client.async_get_items.assert_called_once()
        call_kwargs = mock_coordinator_for_browse.client.async_get_items.call_args.kwargs
        assert call_kwargs.get("studio_ids") == "studio-warner"

    @pytest.mark.asyncio
    async def test_browse_tv_studios_shows_networks(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing TV studios shows network list."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_studios = AsyncMock(
            return_value=[
                {"Id": "network-1", "Name": "HBO"},
                {"Id": "network-2", "Name": "NBC"},
            ]
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.TVSHOW,
            media_content_id="tvstudio:lib-tv",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 2
        assert result.children[0].title == "HBO"
        assert result.children[1].title == "NBC"

    @pytest.mark.asyncio
    async def test_browse_tv_by_studio(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test browsing TV shows from a specific network."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_items = AsyncMock(
            return_value={
                "Items": [
                    {
                        "Id": "tv-1",
                        "Name": "Game of Thrones",
                        "Type": "Series",
                        "ImageTags": {},
                    },
                ],
                "TotalRecordCount": 1,
            }
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.TVSHOW,
            media_content_id="tvstudioitems:lib-tv:network-hbo",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 1
        # Verify API was called with studio filter
        mock_coordinator_for_browse.client.async_get_items.assert_called_once()
        call_kwargs = mock_coordinator_for_browse.client.async_get_items.call_args.kwargs
        assert call_kwargs.get("studio_ids") == "network-hbo"


class TestGenreFiltering:
    """Test genre filtering in music library browsing."""

    @pytest.mark.asyncio
    async def test_browse_genre_items_uses_genre_id_filter(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test that browsing genre items passes genre_ids to API."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_items = AsyncMock(
            return_value={
                "Items": [
                    {
                        "Id": "album-1",
                        "Name": "Best of Rock",
                        "Type": "MusicAlbum",
                        "ImageTags": {},
                    },
                ],
                "TotalRecordCount": 1,
            }
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.MUSIC,
            media_content_id="musicgenre:lib-music:genre-rock-123",
        )

        assert isinstance(result, BrowseMedia)
        # Verify API was called with genre_ids filter
        mock_coordinator_for_browse.client.async_get_items.assert_called_once()
        call_kwargs = mock_coordinator_for_browse.client.async_get_items.call_args.kwargs
        assert call_kwargs.get("genre_ids") == "genre-rock-123"

    @pytest.mark.asyncio
    async def test_browse_genre_items_returns_albums(
        self,
        hass: HomeAssistant,
        mock_coordinator_for_browse: MagicMock,
        mock_session_with_user: MagicMock,
    ) -> None:
        """Test that browsing genre items returns albums."""
        from custom_components.embymedia.media_player import EmbyMediaPlayer

        mock_coordinator_for_browse.client.async_get_items = AsyncMock(
            return_value={
                "Items": [
                    {
                        "Id": "album-1",
                        "Name": "Rock Album 1",
                        "Type": "MusicAlbum",
                        "ImageTags": {},
                    },
                    {
                        "Id": "album-2",
                        "Name": "Rock Album 2",
                        "Type": "MusicAlbum",
                        "ImageTags": {},
                    },
                ],
                "TotalRecordCount": 2,
            }
        )
        mock_coordinator_for_browse.get_session.return_value = mock_session_with_user

        player = EmbyMediaPlayer(mock_coordinator_for_browse, "device-abc-123")
        result = await player.async_browse_media(
            media_content_type=MediaType.MUSIC,
            media_content_id="musicgenre:lib-music:genre-rock-456",
        )

        assert isinstance(result, BrowseMedia)
        assert result.children is not None
        assert len(result.children) == 2
        assert result.children[0].title == "Rock Album 1"
        assert result.children[1].title == "Rock Album 2"
