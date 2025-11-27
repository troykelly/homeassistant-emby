"""Tests for MediaSource transcoding resolution (Phase 13.5)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from custom_components.embymedia.const import (
    MediaSourceInfo,
)
from custom_components.embymedia.media_source import (
    EmbyMediaSource,
)

if TYPE_CHECKING:
    pass


class TestMediaSourceSelection:
    """Tests for _select_media_source method."""

    def test_select_media_source_prefers_direct_stream(self) -> None:
        """Test that direct stream source is preferred."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)

        sources: list[MediaSourceInfo] = [
            {
                "Id": "source-1",
                "Container": "mkv",
                "SupportsDirectPlay": False,
                "SupportsDirectStream": False,
                "SupportsTranscoding": True,
            },
            {
                "Id": "source-2",
                "Container": "mp4",
                "SupportsDirectPlay": False,
                "SupportsDirectStream": True,
                "SupportsTranscoding": True,
            },
        ]

        selected = media_source._select_media_source(sources)
        assert selected["Id"] == "source-2"
        assert selected["SupportsDirectStream"] is True

    def test_select_media_source_falls_back_to_transcoding(self) -> None:
        """Test fallback to transcoding when direct stream not available."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)

        sources: list[MediaSourceInfo] = [
            {
                "Id": "source-1",
                "Container": "mkv",
                "SupportsDirectPlay": False,
                "SupportsDirectStream": False,
                "SupportsTranscoding": True,
            },
        ]

        selected = media_source._select_media_source(sources)
        assert selected["Id"] == "source-1"
        assert selected["SupportsTranscoding"] is True

    def test_select_media_source_empty_list_raises(self) -> None:
        """Test that empty source list raises error."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)

        sources: list[MediaSourceInfo] = []

        with pytest.raises(ValueError, match="No media sources available"):
            media_source._select_media_source(sources)

    def test_select_media_source_prefers_direct_play(self) -> None:
        """Test that direct play is most preferred."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)

        sources: list[MediaSourceInfo] = [
            {
                "Id": "source-1",
                "Container": "mp4",
                "SupportsDirectPlay": True,
                "SupportsDirectStream": True,
                "SupportsTranscoding": True,
            },
            {
                "Id": "source-2",
                "Container": "mp4",
                "SupportsDirectPlay": False,
                "SupportsDirectStream": True,
                "SupportsTranscoding": True,
            },
        ]

        selected = media_source._select_media_source(sources)
        assert selected["Id"] == "source-1"
        assert selected["SupportsDirectPlay"] is True

    def test_select_media_source_fallback_no_capabilities(self) -> None:
        """Test fallback when no capability flags are set."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)

        # Source with no capability flags - rare edge case
        sources: list[MediaSourceInfo] = [
            {
                "Id": "source-1",
                "Container": "mp4",
                "SupportsDirectPlay": False,
                "SupportsDirectStream": False,
                "SupportsTranscoding": False,
            },
        ]

        # Should still return the first source as fallback
        selected = media_source._select_media_source(sources)
        assert selected["Id"] == "source-1"


class TestMimeTypeMapping:
    """Tests for _get_mime_type_for_container method."""

    def test_mime_type_mp4(self) -> None:
        """Test MIME type for MP4 container."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)
        assert media_source._get_mime_type_for_container("mp4") == "video/mp4"

    def test_mime_type_mkv(self) -> None:
        """Test MIME type for MKV container."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)
        assert media_source._get_mime_type_for_container("mkv") == "video/x-matroska"

    def test_mime_type_webm(self) -> None:
        """Test MIME type for WebM container."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)
        assert media_source._get_mime_type_for_container("webm") == "video/webm"

    def test_mime_type_mp3(self) -> None:
        """Test MIME type for MP3 container."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)
        assert media_source._get_mime_type_for_container("mp3") == "audio/mpeg"

    def test_mime_type_flac(self) -> None:
        """Test MIME type for FLAC container."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)
        assert media_source._get_mime_type_for_container("flac") == "audio/flac"

    def test_mime_type_unknown_defaults_to_octet_stream(self) -> None:
        """Test unknown container defaults to octet-stream."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)
        assert media_source._get_mime_type_for_container("unknown") == "application/octet-stream"

    def test_mime_type_ts(self) -> None:
        """Test MIME type for TS container (common for HLS)."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)
        assert media_source._get_mime_type_for_container("ts") == "video/mp2t"


class TestBuildDirectStreamUrl:
    """Tests for _build_direct_stream_url method."""

    def test_build_direct_stream_url_with_direct_stream_url(self) -> None:
        """Test building URL when DirectStreamUrl is provided."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)

        mock_coordinator = MagicMock()
        mock_coordinator.client.base_url = "http://emby.local:8096"
        mock_coordinator.client._api_key = "test-api-key"

        source: MediaSourceInfo = {
            "Id": "source-1",
            "Container": "mp4",
            "DirectStreamUrl": "/Videos/123/stream?static=true",
            "SupportsDirectStream": True,
        }

        url = media_source._build_direct_stream_url(mock_coordinator, source)

        assert "http://emby.local:8096" in url
        assert "/Videos/123/stream" in url
        assert "api_key=test-api-key" in url

    def test_build_direct_stream_url_without_direct_stream_url(self) -> None:
        """Test building URL when DirectStreamUrl is not provided."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)

        mock_coordinator = MagicMock()
        mock_coordinator.client.base_url = "http://emby.local:8096"
        mock_coordinator.client._api_key = "test-api-key"

        source: MediaSourceInfo = {
            "Id": "item-456",
            "Container": "mp4",
            "SupportsDirectStream": True,
        }

        url = media_source._build_direct_stream_url(mock_coordinator, source)

        assert "http://emby.local:8096" in url
        assert "/Videos/item-456/stream" in url or "/Audio/item-456/stream" in url
        assert "api_key=test-api-key" in url


class TestBuildTranscodingUrl:
    """Tests for _build_transcoding_url method."""

    def test_build_transcoding_url_with_hls(self) -> None:
        """Test building transcoding URL for HLS."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)

        mock_coordinator = MagicMock()
        mock_coordinator.client.base_url = "http://emby.local:8096"
        mock_coordinator.client._api_key = "test-api-key"

        source: MediaSourceInfo = {
            "Id": "source-1",
            "Container": "mkv",
            "TranscodingUrl": "/Videos/123/master.m3u8?DeviceId=xxx",
            "TranscodingSubProtocol": "hls",
            "SupportsTranscoding": True,
        }

        url = media_source._build_transcoding_url(mock_coordinator, source)

        assert "http://emby.local:8096" in url
        assert "/Videos/123/master.m3u8" in url
        assert "api_key=test-api-key" in url

    def test_build_transcoding_url_preserves_query_params(self) -> None:
        """Test that existing query params are preserved."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)

        mock_coordinator = MagicMock()
        mock_coordinator.client.base_url = "http://emby.local:8096"
        mock_coordinator.client._api_key = "test-api-key"

        source: MediaSourceInfo = {
            "Id": "source-1",
            "Container": "mkv",
            "TranscodingUrl": "/Videos/123/master.m3u8?DeviceId=xxx&PlaySessionId=abc",
            "TranscodingSubProtocol": "hls",
            "SupportsTranscoding": True,
        }

        url = media_source._build_transcoding_url(mock_coordinator, source)

        assert "DeviceId=xxx" in url
        assert "PlaySessionId=abc" in url
        assert "api_key=test-api-key" in url

    def test_build_transcoding_url_without_transcoding_url_raises(self) -> None:
        """Test that missing TranscodingUrl raises error."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)

        mock_coordinator = MagicMock()
        mock_coordinator.client.base_url = "http://emby.local:8096"

        source: MediaSourceInfo = {
            "Id": "source-1",
            "Container": "mkv",
            "SupportsTranscoding": True,
            # No TranscodingUrl
        }

        with pytest.raises(ValueError, match="No transcoding URL"):
            media_source._build_transcoding_url(mock_coordinator, source)


class TestGetDeviceProfile:
    """Tests for _get_device_profile method."""

    def test_get_device_profile_default(self) -> None:
        """Test getting default device profile."""
        from custom_components.embymedia.profiles import UNIVERSAL_PROFILE

        media_source = EmbyMediaSource.__new__(EmbyMediaSource)

        mock_coordinator = MagicMock()
        # No transcoding_profile in options
        mock_coordinator.config_entry.options = {}

        profile = media_source._get_device_profile(mock_coordinator)

        assert profile["Name"] == UNIVERSAL_PROFILE["Name"]

    def test_get_device_profile_chromecast(self) -> None:
        """Test getting chromecast device profile from config."""
        from custom_components.embymedia.profiles import CHROMECAST_PROFILE

        media_source = EmbyMediaSource.__new__(EmbyMediaSource)

        mock_coordinator = MagicMock()
        mock_coordinator.config_entry.options = {"transcoding_profile": "chromecast"}

        profile = media_source._get_device_profile(mock_coordinator)

        assert profile["Name"] == CHROMECAST_PROFILE["Name"]

    def test_get_device_profile_unknown_falls_back_to_universal(self) -> None:
        """Test unknown profile falls back to universal."""
        from custom_components.embymedia.profiles import UNIVERSAL_PROFILE

        media_source = EmbyMediaSource.__new__(EmbyMediaSource)

        mock_coordinator = MagicMock()
        mock_coordinator.config_entry.options = {"transcoding_profile": "unknown"}

        profile = media_source._get_device_profile(mock_coordinator)

        assert profile["Name"] == UNIVERSAL_PROFILE["Name"]
