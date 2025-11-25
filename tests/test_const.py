"""Tests for Emby integration constants and utilities."""
from __future__ import annotations

import pytest

from custom_components.emby.const import (
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
        assert DOMAIN == "emby"
