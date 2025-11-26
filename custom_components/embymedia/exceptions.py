"""Exceptions for the Emby integration."""

from __future__ import annotations


class EmbyError(Exception):
    """Base exception for Emby integration.

    Supports Home Assistant translation framework for user-friendly error messages.

    Attributes:
        translation_key: Key for looking up translated message.
        translation_placeholders: Values to substitute in translated message.
    """

    def __init__(
        self,
        message: str,
        translation_key: str | None = None,
        translation_placeholders: dict[str, str] | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: The error message (English, for logs).
            translation_key: Optional translation key for HA UI.
            translation_placeholders: Optional placeholders for translation.
        """
        super().__init__(message)
        self.translation_key = translation_key
        self.translation_placeholders = translation_placeholders or {}


class EmbyConnectionError(EmbyError):
    """Exception raised when connection to Emby server fails.

    This includes network errors, timeouts, and DNS resolution failures.
    """

    def __init__(
        self,
        message: str,
        host: str = "",
        port: int = 0,
    ) -> None:
        """Initialize with connection details.

        Args:
            message: The error message.
            host: The server host (for translation placeholder).
            port: The server port (for translation placeholder).
        """
        super().__init__(
            message,
            translation_key="connection_failed",
            translation_placeholders={"host": host, "port": str(port)},
        )


class EmbyAuthenticationError(EmbyError):
    """Exception raised when authentication fails.

    Raised for HTTP 401 or 403 responses from the Emby server.
    """

    def __init__(self, message: str) -> None:
        """Initialize authentication error.

        Args:
            message: The error message.
        """
        super().__init__(
            message,
            translation_key="authentication_failed",
        )


class EmbyNotFoundError(EmbyError):
    """Exception raised when a requested resource is not found.

    Raised for HTTP 404 responses from the Emby server.
    """

    def __init__(self, message: str) -> None:
        """Initialize not found error.

        Args:
            message: The error message.
        """
        super().__init__(message, translation_key="not_found")


class EmbyServerError(EmbyError):
    """Exception raised when Emby server returns a server error.

    Raised for HTTP 5xx responses from the Emby server.
    """

    def __init__(self, message: str) -> None:
        """Initialize server error.

        Args:
            message: The error message.
        """
        super().__init__(message, translation_key="server_error")


class EmbyTimeoutError(EmbyConnectionError):
    """Exception raised when a request times out.

    Inherits from EmbyConnectionError as timeouts are a form of connection failure.
    """

    def __init__(self, message: str, host: str = "", port: int = 0) -> None:
        """Initialize timeout error.

        Args:
            message: The error message.
            host: The server host.
            port: The server port.
        """
        super().__init__(message, host=host, port=port)
        self.translation_key = "timeout"


class EmbySSLError(EmbyConnectionError):
    """Exception raised for SSL/TLS certificate errors.

    Inherits from EmbyConnectionError as SSL errors prevent connection.
    """

    def __init__(self, message: str, host: str = "", port: int = 0) -> None:
        """Initialize SSL error.

        Args:
            message: The error message.
            host: The server host.
            port: The server port.
        """
        super().__init__(message, host=host, port=port)
        self.translation_key = "ssl_error"


class EmbyWebSocketError(EmbyError):
    """Base exception for WebSocket operations."""

    def __init__(self, message: str) -> None:
        """Initialize WebSocket error.

        Args:
            message: The error message.
        """
        super().__init__(message, translation_key="websocket_error")


class EmbyWebSocketConnectionError(EmbyWebSocketError):
    """Exception raised when WebSocket connection fails.

    This includes connection failures, unexpected disconnections,
    and network errors specific to WebSocket.
    """


class EmbyWebSocketAuthError(EmbyWebSocketError):
    """Exception raised when WebSocket authentication fails.

    Raised when the server rejects the API key during WebSocket handshake.
    """

    def __init__(self, message: str) -> None:
        """Initialize WebSocket auth error.

        Args:
            message: The error message.
        """
        super().__init__(message)
        self.translation_key = "websocket_auth_failed"
