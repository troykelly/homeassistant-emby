"""Exceptions for the Emby integration."""
from __future__ import annotations


class EmbyError(Exception):
    """Base exception for Emby integration."""


class EmbyConnectionError(EmbyError):
    """Exception raised when connection to Emby server fails.

    This includes network errors, timeouts, and DNS resolution failures.
    """


class EmbyAuthenticationError(EmbyError):
    """Exception raised when authentication fails.

    Raised for HTTP 401 or 403 responses from the Emby server.
    """


class EmbyNotFoundError(EmbyError):
    """Exception raised when a requested resource is not found.

    Raised for HTTP 404 responses from the Emby server.
    """


class EmbyServerError(EmbyError):
    """Exception raised when Emby server returns a server error.

    Raised for HTTP 5xx responses from the Emby server.
    """


class EmbyTimeoutError(EmbyConnectionError):
    """Exception raised when a request times out.

    Inherits from EmbyConnectionError as timeouts are a form of connection failure.
    """


class EmbySSLError(EmbyConnectionError):
    """Exception raised for SSL/TLS certificate errors.

    Inherits from EmbyConnectionError as SSL errors prevent connection.
    """
