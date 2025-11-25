"""Tests for Emby media browser functionality."""

from __future__ import annotations

import pytest

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
