"""Tests for Emby integration constants and utilities."""

from __future__ import annotations

from custom_components.embymedia.const import (
    DOMAIN,
    normalize_host,
    sanitize_api_key,
)


class TestSanitizeApiKey:
    """Test API key sanitization for logging."""

    def test_sanitize_api_key_long(self) -> None:
        """Test long API key is truncated correctly."""
        api_key = "abcdefghij1234567890"
        result = sanitize_api_key(api_key)
        assert result == "abcd...90"
        assert "abcdefghij" not in result

    def test_sanitize_api_key_exactly_seven_chars(self) -> None:
        """Test 7-character API key is sanitized."""
        api_key = "abcdefg"
        result = sanitize_api_key(api_key)
        assert result == "abcd...fg"

    def test_sanitize_api_key_six_chars_returns_masked(self) -> None:
        """Test 6-character API key returns masked."""
        api_key = "abcdef"
        result = sanitize_api_key(api_key)
        assert result == "***"

    def test_sanitize_api_key_short_returns_masked(self) -> None:
        """Test short API key returns masked."""
        api_key = "abc"
        result = sanitize_api_key(api_key)
        assert result == "***"

    def test_sanitize_api_key_empty_returns_masked(self) -> None:
        """Test empty API key returns masked."""
        api_key = ""
        result = sanitize_api_key(api_key)
        assert result == "***"

    def test_sanitize_api_key_single_char_returns_masked(self) -> None:
        """Test single character API key returns masked."""
        api_key = "a"
        result = sanitize_api_key(api_key)
        assert result == "***"


class TestNormalizeHost:
    """Test host normalization for user input."""

    def test_normalize_host_plain(self) -> None:
        """Test plain hostname unchanged."""
        host = "emby.local"
        result = normalize_host(host)
        assert result == "emby.local"

    def test_normalize_host_ip_address(self) -> None:
        """Test IP address unchanged."""
        host = "192.168.1.100"
        result = normalize_host(host)
        assert result == "192.168.1.100"

    def test_normalize_host_http_prefix(self) -> None:
        """Test HTTP prefix is removed."""
        host = "http://emby.local"
        result = normalize_host(host)
        assert result == "emby.local"

    def test_normalize_host_https_prefix(self) -> None:
        """Test HTTPS prefix is removed."""
        host = "https://emby.local"
        result = normalize_host(host)
        assert result == "emby.local"

    def test_normalize_host_trailing_slash(self) -> None:
        """Test trailing slash is removed."""
        host = "emby.local/"
        result = normalize_host(host)
        assert result == "emby.local"

    def test_normalize_host_multiple_trailing_slashes(self) -> None:
        """Test multiple trailing slashes are removed."""
        host = "emby.local///"
        result = normalize_host(host)
        assert result == "emby.local"

    def test_normalize_host_whitespace(self) -> None:
        """Test whitespace is stripped."""
        host = "  emby.local  "
        result = normalize_host(host)
        assert result == "emby.local"

    def test_normalize_host_combined(self) -> None:
        """Test multiple normalizations applied together."""
        host = "  https://emby.local/  "
        result = normalize_host(host)
        assert result == "emby.local"

    def test_normalize_host_with_port_in_path(self) -> None:
        """Test host with port preserved after normalization."""
        host = "http://emby.local:8096/"
        result = normalize_host(host)
        assert result == "emby.local:8096"

    def test_normalize_host_uppercase_protocol(self) -> None:
        """Test uppercase protocol is handled."""
        host = "HTTP://emby.local"
        result = normalize_host(host)
        assert result == "emby.local"

    def test_normalize_host_mixed_case_protocol(self) -> None:
        """Test mixed case protocol is handled."""
        host = "HtTpS://emby.local"
        result = normalize_host(host)
        assert result == "emby.local"


class TestDomainConstant:
    """Test domain constant is correct."""

    def test_domain_value(self) -> None:
        """Test domain constant has correct value."""
        assert DOMAIN == "embymedia"


class TestMediaSourceTypedDicts:
    """Test TypedDicts for media source streaming."""

    def test_video_stream_params_types(self) -> None:
        """Test VideoStreamParams TypedDict structure."""
        from custom_components.embymedia.const import VideoStreamParams

        # Verify TypedDict can be instantiated with all fields
        params: VideoStreamParams = {
            "container": "mp4",
            "static": True,
            "audio_codec": "aac",
            "video_codec": "h264",
            "max_width": 1920,
            "max_height": 1080,
            "max_video_bitrate": 8000000,
            "max_audio_bitrate": 320000,
            "audio_stream_index": 1,
            "subtitle_stream_index": 0,
            "subtitle_method": "Encode",
        }
        assert params["container"] == "mp4"
        assert params["static"] is True
        assert params["max_width"] == 1920

    def test_video_stream_params_partial(self) -> None:
        """Test VideoStreamParams with only some fields."""
        from custom_components.embymedia.const import VideoStreamParams

        # All fields should be optional (total=False)
        params: VideoStreamParams = {
            "container": "mkv",
        }
        assert params["container"] == "mkv"

    def test_audio_stream_params_types(self) -> None:
        """Test AudioStreamParams TypedDict structure."""
        from custom_components.embymedia.const import AudioStreamParams

        params: AudioStreamParams = {
            "container": "mp3",
            "static": True,
            "audio_codec": "mp3",
            "max_bitrate": 320000,
        }
        assert params["container"] == "mp3"
        assert params["max_bitrate"] == 320000

    def test_audio_stream_params_partial(self) -> None:
        """Test AudioStreamParams with only some fields."""
        from custom_components.embymedia.const import AudioStreamParams

        params: AudioStreamParams = {
            "container": "flac",
        }
        assert params["container"] == "flac"

    def test_media_source_identifier_types(self) -> None:
        """Test MediaSourceIdentifier TypedDict structure."""
        from custom_components.embymedia.const import MediaSourceIdentifier

        identifier: MediaSourceIdentifier = {
            "server_id": "abc123",
            "content_type": "movie",
            "item_id": "mov456",
        }
        assert identifier["server_id"] == "abc123"
        assert identifier["content_type"] == "movie"
        assert identifier["item_id"] == "mov456"

    def test_mime_type_mapping_exists(self) -> None:
        """Test MIME type mapping constant exists."""
        from custom_components.embymedia.const import MIME_TYPES

        assert "movie" in MIME_TYPES
        assert "episode" in MIME_TYPES
        assert "track" in MIME_TYPES
        assert MIME_TYPES["movie"] == "video/mp4"
        assert MIME_TYPES["track"] == "audio/mpeg"


class TestPrefixConstants:
    """Test entity name prefix constants for Phase 11."""

    def test_prefix_constants_exist(self) -> None:
        """Test all prefix configuration constants exist."""
        from custom_components.embymedia.const import (
            CONF_PREFIX_BUTTON,
            CONF_PREFIX_MEDIA_PLAYER,
            CONF_PREFIX_NOTIFY,
            CONF_PREFIX_REMOTE,
        )

        assert CONF_PREFIX_MEDIA_PLAYER == "prefix_media_player"
        assert CONF_PREFIX_NOTIFY == "prefix_notify"
        assert CONF_PREFIX_REMOTE == "prefix_remote"
        assert CONF_PREFIX_BUTTON == "prefix_button"

    def test_default_prefix_constants_exist(self) -> None:
        """Test all default prefix values exist and are True."""
        from custom_components.embymedia.const import (
            DEFAULT_PREFIX_BUTTON,
            DEFAULT_PREFIX_MEDIA_PLAYER,
            DEFAULT_PREFIX_NOTIFY,
            DEFAULT_PREFIX_REMOTE,
        )

        # All defaults should be True (prefix enabled by default)
        assert DEFAULT_PREFIX_MEDIA_PLAYER is True
        assert DEFAULT_PREFIX_NOTIFY is True
        assert DEFAULT_PREFIX_REMOTE is True
        assert DEFAULT_PREFIX_BUTTON is True
