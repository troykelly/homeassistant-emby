"""Tests for Emby integration exceptions."""

from __future__ import annotations

from custom_components.embymedia.exceptions import (
    EmbyAuthenticationError,
    EmbyConnectionError,
    EmbyError,
    EmbyNotFoundError,
    EmbyServerError,
    EmbySSLError,
    EmbyTimeoutError,
)


class TestExceptionHierarchy:
    """Test exception inheritance hierarchy."""

    def test_emby_error_is_base_exception(self) -> None:
        """Test EmbyError is the base exception class."""
        err = EmbyError("test error")
        assert isinstance(err, Exception)
        assert str(err) == "test error"

    def test_emby_connection_error_inherits_from_emby_error(self) -> None:
        """Test EmbyConnectionError inherits from EmbyError."""
        err = EmbyConnectionError("connection failed")
        assert isinstance(err, EmbyError)
        assert isinstance(err, Exception)

    def test_emby_authentication_error_inherits_from_emby_error(self) -> None:
        """Test EmbyAuthenticationError inherits from EmbyError."""
        err = EmbyAuthenticationError("auth failed")
        assert isinstance(err, EmbyError)
        assert isinstance(err, Exception)

    def test_emby_not_found_error_inherits_from_emby_error(self) -> None:
        """Test EmbyNotFoundError inherits from EmbyError."""
        err = EmbyNotFoundError("not found")
        assert isinstance(err, EmbyError)
        assert isinstance(err, Exception)

    def test_emby_server_error_inherits_from_emby_error(self) -> None:
        """Test EmbyServerError inherits from EmbyError."""
        err = EmbyServerError("server error")
        assert isinstance(err, EmbyError)
        assert isinstance(err, Exception)

    def test_emby_timeout_error_inherits_from_connection_error(self) -> None:
        """Test EmbyTimeoutError inherits from EmbyConnectionError."""
        err = EmbyTimeoutError("timeout")
        assert isinstance(err, EmbyConnectionError)
        assert isinstance(err, EmbyError)
        assert isinstance(err, Exception)

    def test_emby_ssl_error_inherits_from_connection_error(self) -> None:
        """Test EmbySSLError inherits from EmbyConnectionError."""
        err = EmbySSLError("ssl error")
        assert isinstance(err, EmbyConnectionError)
        assert isinstance(err, EmbyError)
        assert isinstance(err, Exception)


class TestExceptionMessages:
    """Test exception message handling."""

    def test_exception_stores_message(self) -> None:
        """Test exceptions can store custom messages."""
        message = "Custom error message"
        err = EmbyError(message)
        assert str(err) == message

    def test_exception_with_empty_message(self) -> None:
        """Test exceptions handle empty messages."""
        err = EmbyError("")
        assert str(err) == ""

    def test_exception_with_no_message(self) -> None:
        """Test exceptions handle no message."""
        err = EmbyError()
        assert str(err) == ""


class TestExceptionChaining:
    """Test exception chaining from cause."""

    def test_exception_can_chain_from_cause(self) -> None:
        """Test exceptions can be chained from a cause."""
        original = ValueError("original error")
        chained = EmbyConnectionError("wrapped error")
        chained.__cause__ = original
        assert chained.__cause__ is original

    def test_exception_chaining_with_raise_from(self) -> None:
        """Test exception chaining using raise...from syntax."""
        original = ValueError("original")
        try:
            try:
                raise original
            except ValueError as err:
                raise EmbyError("chained") from err
        except EmbyError as err:
            assert err.__cause__ is original
            assert str(err) == "chained"
