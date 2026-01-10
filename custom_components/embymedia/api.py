"""Emby API client."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Self, cast

import aiohttp

from .cache import BrowseCache
from .coalescer import RequestCoalescer
from .const import (
    DEFAULT_TIMEOUT,
    DEFAULT_VERIFY_SSL,
    EMBY_TICKS_PER_SECOND,
    ENDPOINT_SESSIONS,
    ENDPOINT_SYSTEM_INFO,
    ENDPOINT_SYSTEM_INFO_PUBLIC,
    ENDPOINT_USERS,
    HEADER_AUTHORIZATION,
    HTTP_GET,
    MAX_SEARCH_TERM_LENGTH,
    USER_AGENT_TEMPLATE,
    DeviceProfile,
    PlaybackInfoResponse,
    sanitize_api_key,
)
from .exceptions import (
    EmbyAuthenticationError,
    EmbyConnectionError,
    EmbyNotFoundError,
    EmbyServerError,
    EmbySSLError,
    EmbyTimeoutError,
)
from .metrics import MetricsCollector

if TYPE_CHECKING:
    from .const import (
        EmbyActivityLogResponse,
        EmbyBrowseItem,
        EmbyCollectionCreateResponse,
        EmbyDevicesResponse,
        EmbyItemCounts,
        EmbyItemsResponse,
        EmbyLibraryItem,
        EmbyLiveTvInfo,
        EmbyPersonsResponse,
        EmbyPlugin,
        EmbyProgram,
        EmbyPublicInfo,
        EmbyRecording,
        EmbyScheduledTask,
        EmbySeriesTimer,
        EmbyServerInfo,
        EmbySessionResponse,
        EmbyTag,
        EmbyTimer,
        EmbyTimerDefaults,
        EmbyUser,
        EmbyVirtualFolder,
        LatestMediaItem,
        NextUpItem,
        ResumableItem,
        SuggestionItem,
        UserCountsResult,
    )

_LOGGER = logging.getLogger(__name__)

# Version for User-Agent header
__version__ = "0.1.0"


class EmbyClient:
    """Async client for Emby API.

    This client handles all HTTP communication with the Emby server,
    including authentication, error handling, and response parsing.

    Attributes:
        host: Emby server hostname or IP address.
        port: Emby server port number.
        ssl: Whether to use HTTPS.
        verify_ssl: Whether to verify SSL certificates.

    Example:
        ```python
        async with EmbyClient(
            host="192.168.1.100",
            port=8096,
            api_key="your-api-key",
        ) as client:
            info = await client.async_get_server_info()
            print(f"Connected to {info['ServerName']}")
        ```
    """

    def __init__(
        self,
        host: str,
        port: int,
        api_key: str,
        ssl: bool = False,
        verify_ssl: bool = DEFAULT_VERIFY_SSL,
        timeout: int = DEFAULT_TIMEOUT,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the Emby client.

        Args:
            host: Emby server hostname or IP address.
            port: Emby server port number.
            api_key: API key for authentication.
            ssl: Whether to use HTTPS. Defaults to False.
            verify_ssl: Whether to verify SSL certificates. Defaults to True.
            timeout: Request timeout in seconds. Defaults to 10.
            session: Optional aiohttp session to reuse. If not provided,
                     a new session will be created.
        """
        self._host = host
        self._port = port
        self._api_key = api_key
        self._ssl = ssl
        self._verify_ssl = verify_ssl
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session = session
        self._owns_session = session is None
        self._server_id: str | None = None
        # Browse cache for expensive API calls (5 minute TTL)
        self._browse_cache = BrowseCache(ttl_seconds=300.0, max_entries=500)
        # Metrics collector for API call tracking (#293)
        self._metrics = MetricsCollector()
        # Request coalescer for concurrent identical requests (#290)
        self._coalescer = RequestCoalescer()

    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit async context manager."""
        await self.close()

    @property
    def host(self) -> str:
        """Return the server hostname."""
        return self._host

    @property
    def port(self) -> int:
        """Return the server port."""
        return self._port

    @property
    def api_key(self) -> str:
        """Return the API key."""
        return self._api_key

    @property
    def ssl(self) -> bool:
        """Return whether SSL is enabled."""
        return self._ssl

    @property
    def base_url(self) -> str:
        """Return the base URL for API requests.

        Returns:
            Full base URL including protocol, host, and port.
        """
        protocol = "https" if self._ssl else "http"
        return f"{protocol}://{self._host}:{self._port}"

    @property
    def server_id(self) -> str | None:
        """Return the server ID if known.

        Returns:
            Server ID or None if not yet connected.
        """
        return self._server_id

    @property
    def browse_cache(self) -> BrowseCache:
        """Return the browse cache.

        Returns:
            The browse cache instance.
        """
        return self._browse_cache

    @property
    def metrics(self) -> MetricsCollector:
        """Return the metrics collector.

        Returns:
            The metrics collector instance.
        """
        return self._metrics

    def clear_browse_cache(self) -> None:
        """Clear the browse cache.

        Useful when library contents have changed.
        """
        self._browse_cache.clear()

    def get_coalescer_stats(self) -> dict[str, int]:
        """Get request coalescer statistics.

        Returns:
            Dictionary with coalescing statistics including:
            - total_requests: Total number of coalesce() calls
            - coalesced_requests: Number of requests that were coalesced
            - in_flight: Current number of in-flight requests
        """
        return self._coalescer.get_stats()

    def reset_coalescer_stats(self) -> None:
        """Reset request coalescer statistics."""
        self._coalescer.reset_stats()

    def _get_headers(self, include_auth: bool = True) -> dict[str, str]:
        """Build headers for API requests.

        Args:
            include_auth: Whether to include authentication header.

        Returns:
            Dictionary of HTTP headers.
        """
        headers = {
            "User-Agent": USER_AGENT_TEMPLATE.format(version=__version__),
            "Accept": "application/json",
        }
        if include_auth:
            headers[HEADER_AUTHORIZATION] = self._api_key
        return headers

    def _get_ssl_context(self) -> bool:
        """Get SSL context for requests.

        Returns:
            SSL context or False to disable verification.
        """
        if not self._ssl:
            return True  # No SSL
        if not self._verify_ssl:
            return False  # Disable verification
        return True  # Use default SSL context with verification

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session.

        Returns:
            Active aiohttp client session.
        """
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self._timeout,
            )
            self._owns_session = True
        return self._session

    async def _request(
        self,
        method: str,
        endpoint: str,
        include_auth: bool = True,
    ) -> dict[str, object]:
        """Make an HTTP request to the Emby API.

        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint path.
            include_auth: Whether to include authentication.

        Returns:
            Parsed JSON response as dictionary.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: Authentication failed (401/403).
            EmbyNotFoundError: Resource not found (404).
            EmbyServerError: Server error (5xx).
            EmbyTimeoutError: Request timed out.
            EmbySSLError: SSL certificate error.
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers(include_auth)
        ssl_context = self._get_ssl_context()

        _LOGGER.debug(
            "Emby API request: %s %s (auth=%s, key=%s)",
            method,
            endpoint,
            include_auth,
            sanitize_api_key(self._api_key) if include_auth else "N/A",
        )

        session = await self._get_session()
        start_time = time.perf_counter()
        is_error = False

        try:
            async with session.request(
                method,
                url,
                headers=headers,
                ssl=ssl_context,
            ) as response:
                _LOGGER.debug(
                    "Emby API response: %s %s for %s %s",
                    response.status,
                    response.reason,
                    method,
                    endpoint,
                )

                if response.status in (401, 403):
                    is_error = True
                    raise EmbyAuthenticationError(
                        f"Authentication failed: {response.status} {response.reason}"
                    )

                if response.status == 404:
                    is_error = True
                    raise EmbyNotFoundError(f"Resource not found: {endpoint}")

                if response.status >= 500:
                    is_error = True
                    raise EmbyServerError(f"Server error: {response.status} {response.reason}")

                response.raise_for_status()

                try:
                    return await response.json()  # type: ignore[no-any-return]
                except (aiohttp.ContentTypeError, ValueError) as err:
                    _LOGGER.error(
                        "Emby API returned invalid JSON for %s %s: %s",
                        method,
                        endpoint,
                        err,
                    )
                    is_error = True
                    raise EmbyServerError(f"Server returned invalid JSON: {err}") from err

        except aiohttp.ClientSSLError as err:
            is_error = True
            _LOGGER.error(
                "Emby API SSL error for %s %s: %s",
                method,
                endpoint,
                err,
            )
            raise EmbySSLError(f"SSL certificate error: {err}") from err

        except TimeoutError as err:
            is_error = True
            _LOGGER.error(
                "Emby API timeout for %s %s",
                method,
                endpoint,
            )
            raise EmbyTimeoutError(f"Request timed out after {self._timeout.total}s") from err

        except aiohttp.ClientConnectorError as err:
            is_error = True
            _LOGGER.error(
                "Emby API connection error for %s %s: %s",
                method,
                endpoint,
                err,
            )
            raise EmbyConnectionError(
                f"Failed to connect to {self._host}:{self._port}: {err}"
            ) from err

        except aiohttp.ClientResponseError as err:
            is_error = True
            _LOGGER.error(
                "Emby API error: %s %s for %s %s",
                err.status,
                err.message,
                method,
                endpoint,
            )
            if err.status in (401, 403):
                raise EmbyAuthenticationError(f"Authentication failed: {err.status}") from err
            if err.status == 404:
                raise EmbyNotFoundError(f"Resource not found: {endpoint}") from err
            if err.status >= 500:
                raise EmbyServerError(f"Server error: {err.status}") from err
            raise EmbyConnectionError(f"HTTP error: {err.status}") from err

        except aiohttp.ClientError as err:
            is_error = True
            _LOGGER.error(
                "Emby API client error for %s %s: %s",
                method,
                endpoint,
                err,
            )
            raise EmbyConnectionError(f"Client error: {err}") from err

        finally:
            # Record API metrics (#293)
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._metrics.record_api_call(endpoint, duration_ms, error=is_error)

    async def _coalesced_request(
        self,
        method: str,
        endpoint: str,
        include_auth: bool = True,
    ) -> dict[str, object]:
        """Make a coalesced HTTP GET request to the Emby API.

        For GET requests, this wraps the request in the coalescer to prevent
        duplicate concurrent requests for the same endpoint. Only the first
        request is executed; subsequent identical concurrent requests wait
        for and share the same result.

        Args:
            method: HTTP method (should be GET for coalescing).
            endpoint: API endpoint path.
            include_auth: Whether to include authentication.

        Returns:
            Parsed JSON response as dictionary.

        Note:
            Only GET requests should be coalesced. POST/DELETE requests have
            side effects and must always execute individually.
        """
        if method != HTTP_GET:
            # Non-GET requests should not be coalesced
            return await self._request(method, endpoint, include_auth)

        # Generate unique key for this request
        coalesce_key = f"{endpoint}:auth={include_auth}"

        return await self._coalescer.coalesce(
            coalesce_key,
            lambda: self._request(method, endpoint, include_auth),
        )

    async def async_validate_connection(self) -> bool:
        """Validate connection and authentication.

        Attempts to connect to the server and verify the API key is valid.

        Returns:
            True if connection and authentication succeed.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        await self._request(HTTP_GET, ENDPOINT_SYSTEM_INFO)
        return True

    async def async_get_server_info(self) -> EmbyServerInfo:
        """Get server information (requires authentication).

        Uses request coalescing to prevent duplicate concurrent requests.

        Returns:
            Server information including ID, name, and version.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        response = await self._coalesced_request(HTTP_GET, ENDPOINT_SYSTEM_INFO)
        # Cache server ID for later use
        self._server_id = str(response.get("Id", ""))
        return response  # type: ignore[return-value]

    async def async_get_public_info(self) -> EmbyPublicInfo:
        """Get public server information (no authentication required).

        Useful for checking server availability before authentication.

        Returns:
            Public server information.

        Raises:
            EmbyConnectionError: Connection failed.
        """
        response = await self._request(
            HTTP_GET,
            ENDPOINT_SYSTEM_INFO_PUBLIC,
            include_auth=False,
        )
        return response  # type: ignore[return-value]

    async def async_ping(self) -> bool:
        """Lightweight health check using public endpoint.

        This is more efficient than async_get_server_info for checking
        if the server is reachable, as it doesn't require authentication
        and returns minimal data.

        Returns:
            True if server is reachable.

        Raises:
            EmbyConnectionError: Connection failed.
        """
        await self._request(
            HTTP_GET,
            ENDPOINT_SYSTEM_INFO_PUBLIC,
            include_auth=False,
        )
        return True

    async def async_get_users(self) -> list[EmbyUser]:
        """Get list of users.

        Returns:
            List of user objects.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        response = await self._request(HTTP_GET, ENDPOINT_USERS)
        return response  # type: ignore[return-value]

    async def async_get_sessions(self) -> list[EmbySessionResponse]:
        """Get list of active sessions.

        Uses request coalescing to prevent duplicate concurrent requests
        when multiple entities refresh simultaneously.

        Returns:
            List of session objects representing connected clients.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        response = await self._coalesced_request(HTTP_GET, ENDPOINT_SESSIONS)
        return response  # type: ignore[return-value]

    async def _request_post(
        self,
        endpoint: str,
        data: dict[str, object] | None = None,
    ) -> None:
        """Make a POST request to the Emby API.

        Args:
            endpoint: API endpoint path.
            data: Optional JSON body.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: Authentication failed.
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        ssl_context = self._get_ssl_context()

        _LOGGER.debug(
            "Emby API POST request: %s (data=%s)",
            endpoint,
            data,
        )

        session = await self._get_session()
        start_time = time.perf_counter()
        is_error = False

        try:
            async with session.post(
                url,
                headers=headers,
                json=data,
                ssl=ssl_context,
            ) as response:
                _LOGGER.debug(
                    "Emby API response: %s %s for POST %s",
                    response.status,
                    response.reason,
                    endpoint,
                )

                if response.status in (401, 403):
                    is_error = True
                    raise EmbyAuthenticationError(f"Authentication failed: {response.status}")

                # 204 No Content is success
                if response.status == 204:
                    return

                response.raise_for_status()

        except aiohttp.ClientSSLError as err:
            is_error = True
            raise EmbySSLError(f"SSL certificate error: {err}") from err

        except TimeoutError as err:
            is_error = True
            raise EmbyTimeoutError(f"Request timed out after {self._timeout.total}s") from err

        except aiohttp.ClientConnectorError as err:
            is_error = True
            raise EmbyConnectionError(
                f"Failed to connect to {self._host}:{self._port}: {err}"
            ) from err

        except aiohttp.ClientError as err:
            is_error = True
            raise EmbyConnectionError(f"Client error: {err}") from err

        finally:
            # Record API metrics (#293)
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._metrics.record_api_call(endpoint, duration_ms, error=is_error)

    async def _request_post_json(
        self,
        endpoint: str,
        data: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Make a POST request to the Emby API and return JSON response.

        Args:
            endpoint: API endpoint path.
            data: Optional JSON body.

        Returns:
            Parsed JSON response as dictionary.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: Authentication failed.
            EmbyNotFoundError: Resource not found.
            EmbyServerError: Server error.
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        headers["Content-Type"] = "application/json"
        ssl_context = self._get_ssl_context()

        _LOGGER.debug(
            "Emby API POST JSON request: %s (data=%s)",
            endpoint,
            data,
        )

        session = await self._get_session()
        start_time = time.perf_counter()
        is_error = False

        try:
            async with session.post(
                url,
                headers=headers,
                json=data,
                ssl=ssl_context,
            ) as response:
                _LOGGER.debug(
                    "Emby API response: %s %s for POST %s",
                    response.status,
                    response.reason,
                    endpoint,
                )

                if response.status in (401, 403):
                    is_error = True
                    raise EmbyAuthenticationError(
                        f"Authentication failed: {response.status} {response.reason}"
                    )

                if response.status == 404:
                    is_error = True
                    raise EmbyNotFoundError(f"Resource not found: {endpoint}")

                if response.status >= 500:
                    is_error = True
                    raise EmbyServerError(f"Server error: {response.status} {response.reason}")

                response.raise_for_status()
                return await response.json()  # type: ignore[no-any-return]

        except aiohttp.ClientSSLError as err:
            is_error = True
            raise EmbySSLError(f"SSL certificate error: {err}") from err

        except TimeoutError as err:
            is_error = True
            raise EmbyTimeoutError(f"Request timed out after {self._timeout.total}s") from err

        except aiohttp.ClientConnectorError as err:
            is_error = True
            raise EmbyConnectionError(
                f"Failed to connect to {self._host}:{self._port}: {err}"
            ) from err

        except aiohttp.ClientError as err:
            is_error = True
            raise EmbyConnectionError(f"Client error: {err}") from err

        finally:
            # Record API metrics (#293)
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._metrics.record_api_call(endpoint, duration_ms, error=is_error)

    async def _request_delete(
        self,
        endpoint: str,
    ) -> None:
        """Make a DELETE request to the Emby API.

        Args:
            endpoint: API endpoint path.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: Authentication failed.
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        ssl_context = self._get_ssl_context()

        _LOGGER.debug("Emby API DELETE request: %s", endpoint)

        session = await self._get_session()
        start_time = time.perf_counter()
        is_error = False

        try:
            async with session.delete(
                url,
                headers=headers,
                ssl=ssl_context,
            ) as response:
                _LOGGER.debug(
                    "Emby API response: %s %s for DELETE %s",
                    response.status,
                    response.reason,
                    endpoint,
                )

                if response.status in (401, 403):
                    is_error = True
                    raise EmbyAuthenticationError(f"Authentication failed: {response.status}")

                # 204 No Content is success
                if response.status == 204:
                    return

                response.raise_for_status()

        except aiohttp.ClientSSLError as err:
            is_error = True
            raise EmbySSLError(f"SSL certificate error: {err}") from err

        except TimeoutError as err:
            is_error = True
            raise EmbyTimeoutError(f"Request timed out after {self._timeout.total}s") from err

        except aiohttp.ClientConnectorError as err:
            is_error = True
            raise EmbyConnectionError(
                f"Failed to connect to {self._host}:{self._port}: {err}"
            ) from err

        except aiohttp.ClientError as err:
            is_error = True
            raise EmbyConnectionError(f"Client error: {err}") from err

        finally:
            # Record API metrics (#293)
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._metrics.record_api_call(endpoint, duration_ms, error=is_error)

    async def async_send_playback_command(
        self,
        session_id: str,
        command: str,
        args: dict[str, object] | None = None,
    ) -> None:
        """Send a playback command to a session.

        Args:
            session_id: The session ID to send command to.
            command: Playback command (Play, Pause, Stop, etc.).
            args: Optional command arguments.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = f"/Sessions/{session_id}/Playing/{command}"
        await self._request_post(endpoint, data=args)

    async def async_stop_playback(self, session_id: str) -> None:
        """Stop playback on a session.

        Convenience method that sends the Stop command.

        Args:
            session_id: The session ID to stop playback on.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        await self.async_send_playback_command(session_id, "Stop")

    def get_image_url(
        self,
        item_id: str,
        image_type: str = "Primary",
        max_width: int | None = None,
        max_height: int | None = None,
        tag: str | None = None,
    ) -> str:
        """Generate URL for item image.

        Args:
            item_id: The item ID.
            image_type: Image type (Primary, Backdrop, Thumb, etc.).
            max_width: Optional maximum width.
            max_height: Optional maximum height.
            tag: Optional image tag for cache busting.

        Returns:
            Full URL to the image with authentication.
        """
        url = f"{self.base_url}/Items/{item_id}/Images/{image_type}"
        params: list[str] = [f"api_key={self._api_key}"]

        if tag is not None:
            params.append(f"tag={tag}")
        if max_width is not None:
            params.append(f"maxWidth={max_width}")
        if max_height is not None:
            params.append(f"maxHeight={max_height}")

        return f"{url}?{'&'.join(params)}"

    async def async_send_command(
        self,
        session_id: str,
        command: str,
        args: dict[str, object] | None = None,
    ) -> None:
        """Send a general command to a session.

        Args:
            session_id: The session ID to send command to.
            command: Command name (SetVolume, Mute, etc.).
            args: Optional command arguments.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = f"/Sessions/{session_id}/Command/{command}"
        await self._request_post(endpoint, data=args)

    async def async_send_general_command(
        self,
        session_id: str,
        command: str,
        args: dict[str, str] | None = None,
    ) -> None:
        """Send a general command with arguments to a session.

        Used for commands like SetRepeatMode, SetShuffleQueue that require
        a JSON body with Name and Arguments fields.

        Args:
            session_id: The session ID to send command to.
            command: General command name (SetRepeatMode, SetShuffleQueue).
            args: Command arguments as key-value pairs.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = f"/Sessions/{session_id}/Command"
        body: dict[str, str | dict[str, str]] = {"Name": command}
        if args:
            body["Arguments"] = args
        await self._request_post(endpoint, data=body)  # type: ignore[arg-type]

    async def async_send_message(
        self,
        session_id: str,
        text: str,
        header: str = "",
        timeout_ms: int = 5000,
    ) -> None:
        """Send a message to a session.

        Displays a message overlay on the Emby client.

        Args:
            session_id: Target session ID.
            text: Message body text.
            header: Optional message header.
            timeout_ms: Display duration in milliseconds.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = f"/Sessions/{session_id}/Message"
        data = {
            "Text": text,
            "Header": header,
            "TimeoutMs": timeout_ms,
        }
        await self._request_post(endpoint, data=data)

    # Library Management Methods (Phase 8.3)

    async def async_mark_played(
        self,
        user_id: str,
        item_id: str,
    ) -> None:
        """Mark an item as played.

        Args:
            user_id: User ID.
            item_id: Item ID to mark as played.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = f"/Users/{user_id}/PlayedItems/{item_id}"
        await self._request_post(endpoint)

    async def async_mark_unplayed(
        self,
        user_id: str,
        item_id: str,
    ) -> None:
        """Mark an item as unplayed.

        Args:
            user_id: User ID.
            item_id: Item ID to mark as unplayed.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = f"/Users/{user_id}/PlayedItems/{item_id}"
        await self._request_delete(endpoint)

    async def async_add_favorite(
        self,
        user_id: str,
        item_id: str,
    ) -> None:
        """Add an item to user favorites.

        Args:
            user_id: User ID.
            item_id: Item ID to add to favorites.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = f"/Users/{user_id}/FavoriteItems/{item_id}"
        await self._request_post(endpoint)

    async def async_remove_favorite(
        self,
        user_id: str,
        item_id: str,
    ) -> None:
        """Remove an item from user favorites.

        Args:
            user_id: User ID.
            item_id: Item ID to remove from favorites.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = f"/Users/{user_id}/FavoriteItems/{item_id}"
        await self._request_delete(endpoint)

    async def async_refresh_library(
        self,
        library_id: str | None = None,
    ) -> None:
        """Trigger a library scan.

        Args:
            library_id: Optional specific library to refresh.
                       If None, refreshes all libraries.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = f"/Items/{library_id}/Refresh" if library_id else "/Library/Refresh"
        await self._request_post(endpoint)

    async def async_refresh_item(
        self,
        item_id: str,
        metadata_refresh: bool = True,
        image_refresh: bool = True,
    ) -> None:
        """Refresh metadata for a specific item.

        Args:
            item_id: Item ID to refresh.
            metadata_refresh: Whether to refresh metadata.
            image_refresh: Whether to refresh images.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        params = []
        if metadata_refresh:
            params.append("MetadataRefreshMode=FullRefresh")
        if image_refresh:
            params.append("ImageRefreshMode=FullRefresh")

        query = "&".join(params) if params else ""
        endpoint = f"/Items/{item_id}/Refresh?{query}" if query else f"/Items/{item_id}/Refresh"
        await self._request_post(endpoint)

    async def async_get_user_views(self, user_id: str) -> list[EmbyLibraryItem]:
        """Get available libraries for a user.

        Args:
            user_id: The user ID.

        Returns:
            List of library items.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = f"/Users/{user_id}/Views"
        response = await self._request(HTTP_GET, endpoint)
        items: list[EmbyLibraryItem] = response.get("Items", [])  # type: ignore[assignment]
        return items

    async def async_get_items(
        self,
        user_id: str,
        parent_id: str | None = None,
        include_item_types: str | None = None,
        sort_by: str = "SortName",
        sort_order: str = "Ascending",
        limit: int = 100,
        start_index: int = 0,
        recursive: bool = False,
        name_starts_with: str | None = None,
        years: str | None = None,
        genre_ids: str | None = None,
        studio_ids: str | None = None,
    ) -> EmbyItemsResponse:
        """Get items from a library or folder.

        Args:
            user_id: The user ID.
            parent_id: Parent library/folder ID.
            include_item_types: Filter by item type.
            sort_by: Sort field.
            sort_order: Sort direction.
            limit: Max items to return.
            start_index: Pagination offset.
            recursive: Include nested items.
            name_starts_with: Filter by name starting with letter.
            years: Comma-separated years to filter by (e.g., "2020,2021,2022").
            genre_ids: Comma-separated genre IDs to filter by.
            studio_ids: Comma-separated studio IDs to filter by.

        Returns:
            Items response with items and total count.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        # Build query parameters
        params: list[str] = [
            f"SortBy={sort_by}",
            f"SortOrder={sort_order}",
            f"Limit={limit}",
            f"StartIndex={start_index}",
        ]
        if parent_id:
            params.append(f"ParentId={parent_id}")
        if include_item_types:
            params.append(f"IncludeItemTypes={include_item_types}")
        if recursive:
            params.append("Recursive=true")
        if name_starts_with:
            params.append(f"NameStartsWith={name_starts_with}")
        if years:
            params.append(f"Years={years}")
        if genre_ids:
            params.append(f"GenreIds={genre_ids}")
        if studio_ids:
            params.append(f"StudioIds={studio_ids}")

        query_string = "&".join(params)
        endpoint = f"/Users/{user_id}/Items?{query_string}"
        response = await self._request(HTTP_GET, endpoint)
        return response  # type: ignore[return-value]

    async def async_get_seasons(
        self,
        user_id: str,
        series_id: str,
    ) -> list[EmbyBrowseItem]:
        """Get seasons for a TV series.

        Args:
            user_id: The user ID.
            series_id: The series ID.

        Returns:
            List of season items.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = f"/Shows/{series_id}/Seasons?UserId={user_id}"
        response = await self._request(HTTP_GET, endpoint)
        items: list[EmbyBrowseItem] = response.get("Items", [])  # type: ignore[assignment]
        return items

    async def async_get_episodes(
        self,
        user_id: str,
        series_id: str,
        season_id: str | None = None,
    ) -> list[EmbyBrowseItem]:
        """Get episodes for a series or season.

        Args:
            user_id: The user ID.
            series_id: The series ID.
            season_id: Optional season ID to filter episodes.

        Returns:
            List of episode items.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = f"/Shows/{series_id}/Episodes?UserId={user_id}"
        if season_id:
            endpoint += f"&SeasonId={season_id}"
        response = await self._request(HTTP_GET, endpoint)
        items: list[EmbyBrowseItem] = response.get("Items", [])  # type: ignore[assignment]
        return items

    async def async_get_artist_albums(
        self,
        user_id: str,
        artist_id: str,
    ) -> list[EmbyBrowseItem]:
        """Get albums for a music artist.

        Args:
            user_id: The user ID.
            artist_id: The artist ID.

        Returns:
            List of album items.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = (
            f"/Users/{user_id}/Items?"
            f"ArtistIds={artist_id}&"
            f"IncludeItemTypes=MusicAlbum&"
            f"SortBy=SortName&SortOrder=Ascending&Recursive=true"
        )
        response = await self._request(HTTP_GET, endpoint)
        items: list[EmbyBrowseItem] = response.get("Items", [])  # type: ignore[assignment]
        return items

    async def async_get_album_tracks(
        self,
        user_id: str,
        album_id: str,
    ) -> list[EmbyBrowseItem]:
        """Get tracks for a music album.

        Args:
            user_id: The user ID.
            album_id: The album ID.

        Returns:
            List of audio track items sorted by track number.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = (
            f"/Users/{user_id}/Items?"
            f"ParentId={album_id}&"
            f"IncludeItemTypes=Audio&"
            f"SortBy=SortName&SortOrder=Ascending"
        )
        response = await self._request(HTTP_GET, endpoint)
        items: list[EmbyBrowseItem] = response.get("Items", [])  # type: ignore[assignment]
        return items

    async def async_get_music_genres(
        self,
        user_id: str,
        parent_id: str | None = None,
    ) -> list[EmbyBrowseItem]:
        """Get music genres from the library.

        Args:
            user_id: The user ID.
            parent_id: Optional parent library ID to filter genres.

        Returns:
            List of genre items.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        params = [f"UserId={user_id}", "SortBy=SortName", "SortOrder=Ascending"]
        if parent_id:
            params.append(f"ParentId={parent_id}")

        query_string = "&".join(params)
        endpoint = f"/MusicGenres?{query_string}"
        response = await self._request(HTTP_GET, endpoint)
        items: list[EmbyBrowseItem] = response.get("Items", [])  # type: ignore[assignment]
        return items

    async def async_search_items(
        self,
        user_id: str,
        search_term: str,
        include_item_types: str | None = None,
        limit: int = 50,
    ) -> list[EmbyBrowseItem]:
        """Search for items in the library.

        Args:
            user_id: The user ID.
            search_term: The search query string.
            include_item_types: Comma-separated item types to include (e.g., "Episode,Movie").
            limit: Maximum number of results to return.

        Returns:
            List of matching items.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
            ValueError: Search term is too long or invalid.
        """
        from urllib.parse import quote

        # Validate search term length
        if len(search_term) > MAX_SEARCH_TERM_LENGTH:
            raise ValueError(
                f"Search term exceeds maximum length of {MAX_SEARCH_TERM_LENGTH} characters"
            )
        if not search_term.strip():
            raise ValueError("Search term cannot be empty")

        params = [
            f"SearchTerm={quote(search_term)}",
            f"Limit={limit}",
            "Recursive=true",
            "SortBy=SortName",
            "SortOrder=Ascending",
        ]
        if include_item_types:
            params.append(f"IncludeItemTypes={quote(include_item_types)}")

        query_string = "&".join(params)
        endpoint = f"/Users/{user_id}/Items?{query_string}"
        response = await self._request(HTTP_GET, endpoint)
        items: list[EmbyBrowseItem] = response.get("Items", [])  # type: ignore[assignment]
        return items

    async def async_get_genres(
        self,
        user_id: str,
        parent_id: str | None = None,
        include_item_types: str | None = None,
    ) -> list[EmbyBrowseItem]:
        """Get genres from the library.

        Args:
            user_id: The user ID.
            parent_id: Optional parent library ID to filter genres.
            include_item_types: Optional item types to filter genres (e.g., "Movie", "Series").

        Returns:
            List of genre items.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        # Check cache first
        cache_key = self._browse_cache.generate_key(
            "genres", user_id, parent_id=parent_id, include_item_types=include_item_types
        )
        cached = self._browse_cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        params = [f"UserId={user_id}", "SortBy=SortName", "SortOrder=Ascending"]
        if parent_id:
            params.append(f"ParentId={parent_id}")
        if include_item_types:
            params.append(f"IncludeItemTypes={include_item_types}")

        query_string = "&".join(params)
        endpoint = f"/Genres?{query_string}"
        response = await self._request(HTTP_GET, endpoint)
        items: list[EmbyBrowseItem] = response.get("Items", [])  # type: ignore[assignment]

        # Cache the result
        self._browse_cache.set(cache_key, items)
        return items

    async def async_get_studios(
        self,
        user_id: str,
        parent_id: str | None = None,
        include_item_types: str | None = None,
    ) -> list[EmbyBrowseItem]:
        """Get studios from the library.

        Args:
            user_id: The user ID.
            parent_id: Optional parent library ID to filter studios.
            include_item_types: Optional item types to filter studios (e.g., "Movie", "Series").

        Returns:
            List of studio items.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        # Check cache first
        cache_key = self._browse_cache.generate_key(
            "studios", user_id, parent_id=parent_id, include_item_types=include_item_types
        )
        cached = self._browse_cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        params = [f"UserId={user_id}", "SortBy=SortName", "SortOrder=Ascending"]
        if parent_id:
            params.append(f"ParentId={parent_id}")
        if include_item_types:
            params.append(f"IncludeItemTypes={include_item_types}")

        query_string = "&".join(params)
        endpoint = f"/Studios?{query_string}"
        response = await self._request(HTTP_GET, endpoint)
        items: list[EmbyBrowseItem] = response.get("Items", [])  # type: ignore[assignment]

        # Cache the result
        self._browse_cache.set(cache_key, items)
        return items

    async def async_get_years(
        self,
        user_id: str,
        parent_id: str | None = None,
        include_item_types: str | None = None,
    ) -> list[EmbyBrowseItem]:
        """Get years from the library.

        The Emby /Years endpoint is unreliable (returns 500 error on many servers).
        This method uses a fallback approach: fetch items with ProductionYear field
        and extract unique years.

        Args:
            user_id: The user ID.
            parent_id: Optional parent library ID to filter years.
            include_item_types: Optional item types to filter years (e.g., "Movie", "Series").

        Returns:
            List of year items sorted newest first.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        # Check cache first
        cache_key = self._browse_cache.generate_key(
            "years", user_id, parent_id=parent_id, include_item_types=include_item_types
        )
        cached = self._browse_cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        # Try the /Years endpoint first
        try:
            params = ["SortBy=SortName", "SortOrder=Descending"]
            if parent_id:
                params.append(f"ParentId={parent_id}")
            if include_item_types:
                params.append(f"IncludeItemTypes={include_item_types}")

            query_string = "&".join(params)
            endpoint = f"/Years?{query_string}"
            response = await self._request(HTTP_GET, endpoint)
            items: list[EmbyBrowseItem] = response.get("Items", [])  # type: ignore[assignment]

            # If we got results, cache and return
            if items:
                self._browse_cache.set(cache_key, items)
                return items
        except EmbyServerError:
            # /Years endpoint failed, use fallback
            pass

        # Fallback: Extract years from items with ProductionYear field
        items = await self._extract_years_from_items(user_id, parent_id, include_item_types)

        # Cache the result
        self._browse_cache.set(cache_key, items)
        return items

    async def _extract_years_from_items(
        self,
        user_id: str,
        parent_id: str | None = None,
        include_item_types: str | None = None,
    ) -> list[EmbyBrowseItem]:
        """Extract unique years from library items.

        Fetches items with ProductionYear field and builds a list of unique years.

        Args:
            user_id: The user ID.
            parent_id: Optional parent library ID.
            include_item_types: Optional item types filter.

        Returns:
            List of year items sorted newest first.
        """
        # Fetch items with ProductionYear field
        params = [
            f"UserId={user_id}",
            "SortBy=ProductionYear",
            "SortOrder=Descending",
            "Fields=ProductionYear",
            "Recursive=true",
            "Limit=10000",  # Get all items to extract years
        ]
        if parent_id:
            params.append(f"ParentId={parent_id}")
        if include_item_types:
            params.append(f"IncludeItemTypes={include_item_types}")

        query_string = "&".join(params)
        endpoint = f"/Users/{user_id}/Items?{query_string}"
        response = await self._request(HTTP_GET, endpoint)

        # Extract unique years
        years_set: set[int] = set()
        response_dict = cast(dict[str, list[dict[str, int | str]]], response)
        for item in response_dict.get("Items", []):
            year = item.get("ProductionYear")
            if year and isinstance(year, int):
                years_set.add(year)

        # Convert to EmbyBrowseItem format, sorted newest first
        items: list[EmbyBrowseItem] = []
        for year in sorted(years_set, reverse=True):
            items.append(
                {
                    "Id": str(year),
                    "Name": str(year),
                    "Type": "Year",
                }
            )

        return items

    async def async_get_playlist_items(
        self,
        user_id: str,
        playlist_id: str,
    ) -> list[EmbyBrowseItem]:
        """Get items in a playlist.

        Args:
            user_id: The user ID.
            playlist_id: The playlist ID.

        Returns:
            List of playlist items (audio, video, etc.).

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = f"/Playlists/{playlist_id}/Items?UserId={user_id}"
        response = await self._request(HTTP_GET, endpoint)
        items: list[EmbyBrowseItem] = response.get("Items", [])  # type: ignore[assignment]
        return items

    # =========================================================================
    # Playlist Management API Methods (Phase 17)
    # =========================================================================

    async def async_create_playlist(
        self,
        name: str,
        media_type: str,
        user_id: str,
        item_ids: list[str] | None = None,
    ) -> str:
        """Create a new playlist.

        Args:
            name: Playlist name.
            media_type: "Audio" or "Video".
            user_id: User ID who owns the playlist.
            item_ids: Optional list of item IDs to add initially.

        Returns:
            The newly created playlist ID.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
            ValueError: Invalid media_type.

        Example:
            >>> playlist_id = await client.async_create_playlist(
            ...     name="My Favorites",
            ...     media_type="Audio",
            ...     user_id="user123",
            ...     item_ids=["item1", "item2"]
            ... )
        """
        from urllib.parse import quote

        if media_type not in ("Audio", "Video"):
            raise ValueError(f"Invalid media_type: {media_type}. Must be 'Audio' or 'Video'")

        # Build query parameters
        params: list[str] = [
            f"Name={quote(name)}",
            f"MediaType={media_type}",
            f"UserId={user_id}",
        ]
        if item_ids:
            params.append(f"Ids={','.join(item_ids)}")

        query_string = "&".join(params)
        endpoint = f"/Playlists?{query_string}"

        response = await self._request_post_json(endpoint)
        playlist_id: str = str(response["Id"])
        return playlist_id

    async def async_add_to_playlist(
        self,
        playlist_id: str,
        item_ids: list[str],
        user_id: str,
    ) -> None:
        """Add items to a playlist.

        Args:
            playlist_id: The playlist ID.
            item_ids: List of item IDs to add.
            user_id: User ID (required for permissions).

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
            EmbyNotFoundError: Playlist not found.

        Example:
            >>> await client.async_add_to_playlist(
            ...     playlist_id="playlist123",
            ...     item_ids=["item1", "item2"],
            ...     user_id="user123"
            ... )
        """
        # Items are added via query string parameters
        params: list[str] = [
            f"Ids={','.join(item_ids)}",
            f"UserId={user_id}",
        ]
        query_string = "&".join(params)
        endpoint = f"/Playlists/{playlist_id}/Items?{query_string}"
        await self._request_post(endpoint)

    async def async_remove_from_playlist(
        self,
        playlist_id: str,
        playlist_item_ids: list[str],
    ) -> None:
        """Remove items from a playlist.

        IMPORTANT: Use PlaylistItemId from playlist items, NOT the media item ID.

        Args:
            playlist_id: The playlist ID.
            playlist_item_ids: List of PlaylistItemId values (from GET /Playlists/{Id}/Items).

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
            EmbyNotFoundError: Playlist not found.

        Example:
            >>> # First get playlist items to obtain PlaylistItemIds
            >>> items = await client.async_get_playlist_items("user123", "playlist123")
            >>> playlist_item_ids = [item["PlaylistItemId"] for item in items]
            >>>
            >>> # Then remove by PlaylistItemId
            >>> await client.async_remove_from_playlist(
            ...     playlist_id="playlist123",
            ...     playlist_item_ids=playlist_item_ids[:2]  # Remove first 2 items
            ... )
        """
        # Items are removed via query string with EntryIds
        entry_ids = ",".join(playlist_item_ids)
        endpoint = f"/Playlists/{playlist_id}/Items?EntryIds={entry_ids}"
        await self._request_delete(endpoint)

    async def async_get_playlists(
        self,
        user_id: str,
    ) -> list[EmbyBrowseItem]:
        """Get user's playlists.

        Args:
            user_id: The user ID.

        Returns:
            List of playlist items.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.

        Example:
            >>> playlists = await client.async_get_playlists("user123")
            >>> for playlist in playlists:
            ...     print(f"{playlist['Name']}: {playlist['Id']}")
        """
        endpoint = (
            f"/Users/{user_id}/Items?"
            f"IncludeItemTypes=Playlist&"
            f"SortBy=SortName&SortOrder=Ascending&"
            f"Recursive=true"
        )
        response = await self._request(HTTP_GET, endpoint)
        items: list[EmbyBrowseItem] = response.get("Items", [])  # type: ignore[assignment]
        return items

    async def async_get_collection_items(
        self,
        user_id: str,
        collection_id: str,
    ) -> list[EmbyBrowseItem]:
        """Get items in a collection (BoxSet).

        Args:
            user_id: The user ID.
            collection_id: The collection (BoxSet) ID.

        Returns:
            List of collection items.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = (
            f"/Users/{user_id}/Items?ParentId={collection_id}&SortBy=SortName&SortOrder=Ascending"
        )
        response = await self._request(HTTP_GET, endpoint)
        items: list[EmbyBrowseItem] = response.get("Items", [])  # type: ignore[assignment]
        return items

    async def async_get_live_tv_channels(
        self,
        user_id: str,
    ) -> list[EmbyBrowseItem]:
        """Get Live TV channels.

        Args:
            user_id: The user ID.

        Returns:
            List of Live TV channels.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = f"/LiveTv/Channels?UserId={user_id}"
        response = await self._request(HTTP_GET, endpoint)
        items: list[EmbyBrowseItem] = response.get("Items", [])  # type: ignore[assignment]
        return items

    # =========================================================================
    # Sensor Platform API Methods (Phase 12)
    # =========================================================================

    async def async_get_item_counts(
        self,
        user_id: str | None = None,
    ) -> EmbyItemCounts:
        """Get library item counts.

        Uses request coalescing to prevent duplicate concurrent requests.

        Args:
            user_id: Optional user ID to filter by user's visible items.

        Returns:
            Item counts response with counts for each media type.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = "/Items/Counts"
        if user_id:
            endpoint = f"{endpoint}?UserId={user_id}"
        response = await self._coalesced_request(HTTP_GET, endpoint)
        return response  # type: ignore[return-value]

    async def async_get_scheduled_tasks(
        self,
        include_hidden: bool = False,
    ) -> list[EmbyScheduledTask]:
        """Get scheduled tasks status.

        Args:
            include_hidden: Whether to include hidden tasks.

        Returns:
            List of scheduled tasks with their current state.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = "/ScheduledTasks"
        if include_hidden:
            endpoint = f"{endpoint}?IsHidden=true"
        response = await self._request(HTTP_GET, endpoint)
        return response  # type: ignore[return-value]

    async def async_get_virtual_folders(self) -> list[EmbyVirtualFolder]:
        """Get virtual folders (libraries) configuration.

        Returns:
            List of virtual folders with library info and locations.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        response = await self._request(HTTP_GET, "/Library/VirtualFolders")
        return response  # type: ignore[return-value]

    async def async_get_user_item_count(
        self,
        user_id: str,
        filters: str | None = None,
        parent_id: str | None = None,
    ) -> int:
        """Get count of items matching filters for a user.

        Args:
            user_id: User ID.
            filters: Filter string (e.g., "IsFavorite", "IsPlayed", "IsResumable").
            parent_id: Optional parent library ID to filter within.

        Returns:
            Total count of matching items.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        params: list[str] = ["Limit=0", "Recursive=true"]
        if filters:
            params.insert(0, f"Filters={filters}")
        if parent_id:
            params.append(f"ParentId={parent_id}")

        query_string = "&".join(params)
        endpoint = f"/Users/{user_id}/Items?{query_string}"
        response = await self._request(HTTP_GET, endpoint)
        total_count = response.get("TotalRecordCount", 0)
        return int(total_count) if isinstance(total_count, int | float | str) else 0

    async def async_get_all_user_counts(
        self,
        user_id: str,
    ) -> UserCountsResult:
        """Get all user-specific counts in a single batch operation.

        This method consolidates multiple count API calls into a single
        parallel fetch, improving efficiency when all counts are needed
        at once (e.g., for discovery coordinator updates).

        Fetches in parallel:
        - Favorites count (IsFavorite filter)
        - Played count (IsPlayed filter)
        - Resumable count (IsResumable filter)
        - Playlist count (number of playlists)

        Args:
            user_id: The user ID to get counts for.

        Returns:
            UserCountsResult with all count values.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.

        Example:
            >>> counts = await client.async_get_all_user_counts("user123")
            >>> print(f"Favorites: {counts['favorites_count']}")
            >>> print(f"Played: {counts['played_count']}")
        """
        # Fetch all counts in parallel for efficiency
        favorites, played, resumable, playlists = await asyncio.gather(
            self.async_get_user_item_count(user_id=user_id, filters="IsFavorite"),
            self.async_get_user_item_count(user_id=user_id, filters="IsPlayed"),
            self.async_get_user_item_count(user_id=user_id, filters="IsResumable"),
            self.async_get_playlists(user_id=user_id),
        )

        return {
            "favorites_count": favorites,
            "played_count": played,
            "resumable_count": resumable,
            "playlist_count": len(playlists),
        }

    async def async_get_artist_count(
        self,
        user_id: str | None = None,
    ) -> int:
        """Get count of music artists in the library.

        This method works around a known Emby API bug where the /Items/Counts
        endpoint returns 0 for ArtistCount. Instead, it queries the /Artists
        endpoint with Limit=0 to get the accurate TotalRecordCount.

        See: https://emby.media/community/index.php?/topic/98298-boxset-count-now-broken-in-http-api/

        TODO: Remove this workaround when Emby fixes the /Items/Counts endpoint
        to return accurate ArtistCount values. Monitor the above forum thread
        for updates.

        Args:
            user_id: Optional user ID to filter by user's visible items.

        Returns:
            Total count of music artists.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = "/Artists?Limit=0"
        if user_id:
            endpoint = f"{endpoint}&UserId={user_id}"
        response = await self._request(HTTP_GET, endpoint)
        total_count = response.get("TotalRecordCount", 0)
        return int(total_count) if isinstance(total_count, int | float | str) else 0

    async def async_get_boxset_count(
        self,
        user_id: str | None = None,
    ) -> int:
        """Get count of BoxSets (collections) in the library.

        This method works around a known Emby API bug where the /Items/Counts
        endpoint returns 0 for BoxSetCount. Instead, it queries the /Items
        endpoint with IncludeItemTypes=BoxSet and Limit=0 to get the accurate
        TotalRecordCount.

        See: https://emby.media/community/index.php?/topic/98298-boxset-count-now-broken-in-http-api/

        TODO: Remove this workaround when Emby fixes the /Items/Counts endpoint
        to return accurate BoxSetCount values. Monitor the above forum thread
        for updates.

        Args:
            user_id: Optional user ID to filter by user's visible items.

        Returns:
            Total count of BoxSets.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        if user_id:
            endpoint = f"/Users/{user_id}/Items?IncludeItemTypes=BoxSet&Limit=0&Recursive=true"
        else:
            endpoint = "/Items?IncludeItemTypes=BoxSet&Limit=0&Recursive=true"
        response = await self._request(HTTP_GET, endpoint)
        total_count = response.get("TotalRecordCount", 0)
        return int(total_count) if isinstance(total_count, int | float | str) else 0

    async def async_play_items(
        self,
        session_id: str,
        item_ids: list[str],
        start_position_ticks: int = 0,
        play_command: str = "PlayNow",
    ) -> None:
        """Play items on a session.

        Args:
            session_id: Target session ID.
            item_ids: List of item IDs to play.
            start_position_ticks: Starting position.
            play_command: PlayNow, PlayNext, or PlayLast.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = f"/Sessions/{session_id}/Playing"
        data: dict[str, object] = {
            "ItemIds": ",".join(item_ids),
            "StartPositionTicks": start_position_ticks,
            "PlayCommand": play_command,
        }
        await self._request_post(endpoint, data=data)

    def get_video_stream_url(
        self,
        item_id: str,
        container: str = "mp4",
        static: bool = True,
        video_codec: str | None = None,
        audio_codec: str | None = None,
        max_width: int | None = None,
        max_height: int | None = None,
        audio_stream_index: int | None = None,
        subtitle_stream_index: int | None = None,
    ) -> str:
        """Generate URL for video streaming.

        Args:
            item_id: Video item ID.
            container: Output container format (mp4, mkv, webm).
            static: Direct play without transcoding.
            video_codec: Video codec for transcoding (h264, hevc, vp9).
            audio_codec: Audio codec for transcoding (aac, mp3, opus).
            max_width: Maximum video width.
            max_height: Maximum video height.
            audio_stream_index: Audio track index to use.
            subtitle_stream_index: Subtitle track index.

        Returns:
            Full streaming URL with authentication.
        """
        url = f"{self.base_url}/Videos/{item_id}/stream"
        params: list[str] = [
            f"api_key={self._api_key}",
            f"Container={container}",
            f"Static={'true' if static else 'false'}",
        ]

        if video_codec is not None:
            params.append(f"VideoCodec={video_codec}")
        if audio_codec is not None:
            params.append(f"AudioCodec={audio_codec}")
        if max_width is not None:
            params.append(f"MaxWidth={max_width}")
        if max_height is not None:
            params.append(f"MaxHeight={max_height}")
        if audio_stream_index is not None:
            params.append(f"AudioStreamIndex={audio_stream_index}")
        if subtitle_stream_index is not None:
            params.append(f"SubtitleStreamIndex={subtitle_stream_index}")

        return f"{url}?{'&'.join(params)}"

    def get_audio_stream_url(
        self,
        item_id: str,
        container: str = "mp3",
        static: bool = True,
        audio_codec: str | None = None,
        max_bitrate: int | None = None,
    ) -> str:
        """Generate URL for audio streaming.

        Args:
            item_id: Audio item ID.
            container: Output format (mp3, flac, aac).
            static: Direct play without transcoding.
            audio_codec: Audio codec for transcoding.
            max_bitrate: Maximum bitrate in bps.

        Returns:
            Full streaming URL with authentication.
        """
        url = f"{self.base_url}/Audio/{item_id}/stream"
        params: list[str] = [
            f"api_key={self._api_key}",
            f"Container={container}",
            f"Static={'true' if static else 'false'}",
        ]

        if audio_codec is not None:
            params.append(f"AudioCodec={audio_codec}")
        if max_bitrate is not None:
            params.append(f"MaxAudioBitRate={max_bitrate}")

        return f"{url}?{'&'.join(params)}"

    def get_hls_url(self, item_id: str) -> str:
        """Generate HLS adaptive streaming URL.

        Args:
            item_id: Video item ID.

        Returns:
            HLS master playlist URL with authentication.
        """
        url = f"{self.base_url}/Videos/{item_id}/master.m3u8"
        return f"{url}?api_key={self._api_key}"

    def get_user_image_url(
        self,
        user_id: str,
        image_tag: str | None = None,
        max_width: int | None = None,
        max_height: int | None = None,
    ) -> str:
        """Generate URL for user profile image (avatar).

        Args:
            user_id: User ID.
            image_tag: Optional image tag for cache busting.
            max_width: Optional maximum width for image.
            max_height: Optional maximum height for image.

        Returns:
            Full URL to the user's profile image with authentication.
        """
        url = f"{self.base_url}/Users/{user_id}/Images/Primary"
        params: list[str] = [f"api_key={self._api_key}"]

        if image_tag is not None:
            params.append(f"tag={image_tag}")
        if max_width is not None:
            params.append(f"maxWidth={max_width}")
        if max_height is not None:
            params.append(f"maxHeight={max_height}")

        return f"{url}?{'&'.join(params)}"

    # =========================================================================
    # PlaybackInfo API Methods (Phase 13)
    # =========================================================================

    async def async_get_playback_info(
        self,
        item_id: str,
        user_id: str,
        device_profile: DeviceProfile | None = None,
        max_streaming_bitrate: int | None = None,
        start_position_ticks: int | None = None,
        audio_stream_index: int | None = None,
        subtitle_stream_index: int | None = None,
        enable_direct_play: bool | None = None,
        enable_direct_stream: bool | None = None,
        enable_transcoding: bool | None = None,
    ) -> PlaybackInfoResponse:
        """Get playback info for a media item.

        This method queries the Emby server for the optimal playback method
        based on the device profile and streaming capabilities.

        Args:
            item_id: The media item ID.
            user_id: The user ID.
            device_profile: Device capabilities profile. Defaults to UNIVERSAL_PROFILE.
            max_streaming_bitrate: Maximum bitrate for streaming in bps.
            start_position_ticks: Starting position in ticks.
            audio_stream_index: Preferred audio track index.
            subtitle_stream_index: Preferred subtitle track index.
            enable_direct_play: Allow direct play if supported.
            enable_direct_stream: Allow direct stream if supported.
            enable_transcoding: Allow transcoding if needed.

        Returns:
            PlaybackInfoResponse with MediaSources and PlaySessionId.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
            EmbyNotFoundError: Item not found.
        """
        from .profiles import UNIVERSAL_PROFILE

        # Build request body
        body: dict[str, object] = {
            "UserId": user_id,
            "DeviceProfile": device_profile if device_profile else UNIVERSAL_PROFILE,
        }

        if max_streaming_bitrate is not None:
            body["MaxStreamingBitrate"] = max_streaming_bitrate
        if start_position_ticks is not None:
            body["StartTimeTicks"] = start_position_ticks
        if audio_stream_index is not None:
            body["AudioStreamIndex"] = audio_stream_index
        if subtitle_stream_index is not None:
            body["SubtitleStreamIndex"] = subtitle_stream_index
        if enable_direct_play is not None:
            body["EnableDirectPlay"] = enable_direct_play
        if enable_direct_stream is not None:
            body["EnableDirectStream"] = enable_direct_stream
        if enable_transcoding is not None:
            body["EnableTranscoding"] = enable_transcoding

        endpoint = f"/Items/{item_id}/PlaybackInfo"
        response = await self._request_post_json(endpoint, body)
        return response  # type: ignore[return-value]

    async def async_stop_transcoding(
        self,
        device_id: str,
        play_session_id: str | None = None,
    ) -> None:
        """Stop active transcoding for a device.

        Args:
            device_id: The device ID.
            play_session_id: Optional specific play session to stop.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = f"/Videos/ActiveEncodings?DeviceId={device_id}"
        if play_session_id:
            endpoint += f"&PlaySessionId={play_session_id}"
        await self._request_delete(endpoint)

    def get_universal_audio_url(
        self,
        item_id: str,
        user_id: str,
        device_id: str,
        max_streaming_bitrate: int | None = None,
        container: str | None = None,
        transcoding_container: str | None = None,
        transcoding_protocol: str | None = None,
        audio_codec: str | None = None,
        max_sample_rate: int | None = None,
        play_session_id: str | None = None,
    ) -> str:
        """Generate URL for universal audio streaming.

        The universal audio endpoint automatically determines the best
        playback method based on the provided parameters.

        Args:
            item_id: Audio item ID.
            user_id: User ID.
            device_id: Device ID for session tracking.
            max_streaming_bitrate: Maximum bitrate in bps.
            container: Preferred containers (comma-separated, e.g., "mp3,aac,flac").
            transcoding_container: Container for transcoding.
            transcoding_protocol: Transcoding protocol (hls, http).
            audio_codec: Audio codec preference.
            max_sample_rate: Maximum sample rate in Hz.
            play_session_id: Play session ID for tracking.

        Returns:
            Full streaming URL with authentication.
        """
        url = f"{self.base_url}/Audio/{item_id}/universal"
        params: list[str] = [
            f"api_key={self._api_key}",
            f"UserId={user_id}",
            f"DeviceId={device_id}",
        ]

        if max_streaming_bitrate is not None:
            params.append(f"MaxStreamingBitrate={max_streaming_bitrate}")
        if container:
            params.append(f"Container={container}")
        if transcoding_container:
            params.append(f"TranscodingContainer={transcoding_container}")
        if transcoding_protocol:
            params.append(f"TranscodingProtocol={transcoding_protocol}")
        if audio_codec:
            params.append(f"AudioCodec={audio_codec}")
        if max_sample_rate is not None:
            params.append(f"MaxSampleRate={max_sample_rate}")
        if play_session_id:
            params.append(f"PlaySessionId={play_session_id}")

        return f"{url}?{'&'.join(params)}"

    # =========================================================================
    # Discovery API Methods (Phase 15)
    # =========================================================================

    async def async_get_next_up(
        self,
        user_id: str,
        limit: int = 10,
        enable_images: bool = True,
        legacy_next_up: bool = True,
    ) -> list[NextUpItem]:
        """Get next up episodes for user.

        Fetches the next episode to watch for each TV series the user is
        currently watching.

        Args:
            user_id: The user ID.
            limit: Maximum number of episodes to return.
            enable_images: Include image information.
            legacy_next_up: Use legacy next up logic (Legacynextup=true).
                Legacy mode is more reliable on some Emby versions.

        Returns:
            List of next up episode items.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        params: list[str] = [
            f"UserId={user_id}",
            f"Limit={limit}",
            f"EnableImages={str(enable_images).lower()}",
        ]
        if legacy_next_up:
            params.append("Legacynextup=true")

        query_string = "&".join(params)
        endpoint = f"/Shows/NextUp?{query_string}"
        response = await self._request(HTTP_GET, endpoint)
        items: list[NextUpItem] = response.get("Items", [])  # type: ignore[assignment]
        return items

    async def async_get_resumable_items(
        self,
        user_id: str,
        limit: int = 10,
        include_item_types: str | None = None,
    ) -> list[ResumableItem]:
        """Get resumable items (Continue Watching) for user.

        Fetches movies and episodes that have been partially watched.

        Args:
            user_id: The user ID.
            limit: Maximum number of items to return.
            include_item_types: Filter by item type (e.g., "Movie,Episode").

        Returns:
            List of resumable items sorted by last played date.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        params: list[str] = [
            "Filters=IsResumable",
            f"Limit={limit}",
            "SortBy=DatePlayed",
            "SortOrder=Descending",
            "Recursive=true",
        ]
        if include_item_types:
            params.append(f"IncludeItemTypes={include_item_types}")

        query_string = "&".join(params)
        endpoint = f"/Users/{user_id}/Items?{query_string}"
        response = await self._request(HTTP_GET, endpoint)
        items: list[ResumableItem] = response.get("Items", [])  # type: ignore[assignment]
        return items

    async def async_get_latest_media(
        self,
        user_id: str,
        limit: int = 10,
        include_item_types: str | None = None,
        parent_id: str | None = None,
    ) -> list[LatestMediaItem]:
        """Get recently added media items.

        Fetches the most recently added content to the library.

        Args:
            user_id: The user ID.
            limit: Maximum number of items to return.
            include_item_types: Filter by item type (e.g., "Movie,Episode,Audio").
            parent_id: Optional library ID to filter within.

        Returns:
            List of latest media items sorted by date added.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        params: list[str] = [f"Limit={limit}"]
        if include_item_types:
            params.append(f"IncludeItemTypes={include_item_types}")
        if parent_id:
            params.append(f"ParentId={parent_id}")

        query_string = "&".join(params)
        endpoint = f"/Users/{user_id}/Items/Latest?{query_string}"
        # /Items/Latest returns array directly, not wrapped in Items property
        response = await self._request(HTTP_GET, endpoint)
        return response  # type: ignore[return-value]

    async def async_get_suggestions(
        self,
        user_id: str,
        limit: int = 10,
        suggestion_type: str | None = None,
    ) -> list[SuggestionItem]:
        """Get personalized suggestions for user.

        Fetches content recommendations based on watch history.

        Args:
            user_id: The user ID.
            limit: Maximum number of suggestions to return.
            suggestion_type: Optional type filter (e.g., "Movie", "Series").

        Returns:
            List of suggested items.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        params: list[str] = [f"Limit={limit}"]
        if suggestion_type:
            params.append(f"Type={suggestion_type}")

        query_string = "&".join(params)
        endpoint = f"/Users/{user_id}/Suggestions?{query_string}"
        response = await self._request(HTTP_GET, endpoint)
        items: list[SuggestionItem] = response.get("Items", [])  # type: ignore[assignment]
        return items

    # =========================================================================
    # Instant Mix & Similar Items API Methods (Phase 14)
    # =========================================================================

    async def async_get_instant_mix(
        self,
        user_id: str,
        item_id: str,
        limit: int = 100,
    ) -> list[EmbyBrowseItem]:
        """Get instant mix based on item.

        Creates a dynamic playlist of similar items to the seed item.

        Args:
            user_id: User ID.
            item_id: Seed item ID (song, album, artist, etc.).
            limit: Maximum number of items to return.

        Returns:
            List of items for the instant mix.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
            EmbyNotFoundError: Item not found.
        """
        endpoint = f"/Items/{item_id}/InstantMix?UserId={user_id}&Limit={limit}"
        response = await self._request(HTTP_GET, endpoint)
        items: list[EmbyBrowseItem] = response.get("Items", [])  # type: ignore[assignment]
        return items

    async def async_get_artist_instant_mix(
        self,
        user_id: str,
        artist_id: str,
        limit: int = 100,
    ) -> list[EmbyBrowseItem]:
        """Get instant mix based on artist.

        Creates a dynamic playlist based on artist's catalog and similar artists.

        Args:
            user_id: User ID.
            artist_id: Artist ID.
            limit: Maximum number of items to return.

        Returns:
            List of items for the instant mix.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
            EmbyNotFoundError: Artist not found.
        """
        endpoint = f"/Artists/InstantMix?UserId={user_id}&Id={artist_id}&Limit={limit}"
        response = await self._request(HTTP_GET, endpoint)
        items: list[EmbyBrowseItem] = response.get("Items", [])  # type: ignore[assignment]
        return items

    async def async_get_similar_items(
        self,
        user_id: str,
        item_id: str,
        limit: int = 20,
    ) -> list[EmbyBrowseItem]:
        """Get similar items based on item.

        Finds items similar to the seed item based on metadata.

        Args:
            user_id: User ID.
            item_id: Seed item ID.
            limit: Maximum number of items to return.

        Returns:
            List of similar items.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
            EmbyNotFoundError: Item not found.
        """
        endpoint = f"/Items/{item_id}/Similar?UserId={user_id}&Limit={limit}"
        response = await self._request(HTTP_GET, endpoint)
        items: list[EmbyBrowseItem] = response.get("Items", [])  # type: ignore[assignment]
        return items

    # =========================================================================
    # Live TV & DVR API Methods (Phase 16)
    # =========================================================================

    async def async_get_live_tv_info(self) -> EmbyLiveTvInfo:
        """Get Live TV configuration and status.

        Returns:
            Live TV info including enabled status and tuner count.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        response = await self._request(HTTP_GET, "/LiveTv/Info")
        return response  # type: ignore[return-value]

    async def async_get_recordings(
        self,
        user_id: str,
        status: str | None = None,
        series_timer_id: str | None = None,
        is_in_progress: bool | None = None,
    ) -> list[EmbyRecording]:
        """Get recorded programs.

        Args:
            user_id: User ID to filter recordings.
            status: Filter by status ("Completed", "InProgress", etc.).
            series_timer_id: Filter by series timer ID.
            is_in_progress: Filter for currently recording programs.

        Returns:
            List of recording items.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        params: list[str] = [f"UserId={user_id}"]
        if status:
            params.append(f"Status={status}")
        if series_timer_id:
            params.append(f"SeriesTimerId={series_timer_id}")
        if is_in_progress is not None:
            params.append(f"IsInProgress={'true' if is_in_progress else 'false'}")

        query_string = "&".join(params)
        endpoint = f"/LiveTv/Recordings?{query_string}"
        response = await self._request(HTTP_GET, endpoint)
        items: list[EmbyRecording] = response.get("Items", [])  # type: ignore[assignment]
        return items

    async def async_get_timers(
        self,
        channel_id: str | None = None,
        series_timer_id: str | None = None,
    ) -> list[EmbyTimer]:
        """Get scheduled recording timers.

        Args:
            channel_id: Filter by channel ID.
            series_timer_id: Filter by series timer ID.

        Returns:
            List of timer objects.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        params: list[str] = []
        if channel_id:
            params.append(f"ChannelId={channel_id}")
        if series_timer_id:
            params.append(f"SeriesTimerId={series_timer_id}")

        query_string = "&".join(params) if params else ""
        endpoint = f"/LiveTv/Timers?{query_string}" if query_string else "/LiveTv/Timers"
        response = await self._request(HTTP_GET, endpoint)
        items: list[EmbyTimer] = response.get("Items", [])  # type: ignore[assignment]
        return items

    async def async_get_timer_defaults(
        self,
        program_id: str,
    ) -> EmbyTimerDefaults:
        """Get default timer settings for a program.

        Args:
            program_id: Program ID to get defaults for.

        Returns:
            Timer defaults with pre-populated settings.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = f"/LiveTv/Timers/Defaults?ProgramId={program_id}"
        response = await self._request(HTTP_GET, endpoint)
        return response  # type: ignore[return-value]

    async def async_create_timer(
        self,
        timer_data: dict[str, object],
    ) -> None:
        """Create a new recording timer.

        Args:
            timer_data: Timer configuration (typically from get_timer_defaults).

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        await self._request_post("/LiveTv/Timers", data=timer_data)

    async def async_cancel_timer(
        self,
        timer_id: str,
    ) -> None:
        """Cancel a recording timer.

        Args:
            timer_id: Timer ID to cancel.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        await self._request_delete(f"/LiveTv/Timers/{timer_id}")

    async def async_get_series_timers(self) -> list[EmbySeriesTimer]:
        """Get series recording timers.

        Returns:
            List of series timer objects.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        response = await self._request(HTTP_GET, "/LiveTv/SeriesTimers")
        items: list[EmbySeriesTimer] = response.get("Items", [])  # type: ignore[assignment]
        return items

    async def async_create_series_timer(
        self,
        series_timer_data: dict[str, object],
    ) -> None:
        """Create a new series recording timer.

        Args:
            series_timer_data: Series timer configuration.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        await self._request_post("/LiveTv/SeriesTimers", data=series_timer_data)

    async def async_cancel_series_timer(
        self,
        series_timer_id: str,
    ) -> None:
        """Cancel a series recording timer.

        Args:
            series_timer_id: Series timer ID to cancel.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        await self._request_delete(f"/LiveTv/SeriesTimers/{series_timer_id}")

    async def async_get_programs(
        self,
        user_id: str,
        channel_ids: list[str] | None = None,
        min_start_date: str | None = None,
        max_start_date: str | None = None,
        has_aired: bool | None = None,
        is_airing: bool | None = None,
    ) -> list[EmbyProgram]:
        """Get EPG program data.

        Args:
            user_id: User ID for personalization.
            channel_ids: Filter by channel IDs.
            min_start_date: Minimum start date (ISO 8601).
            max_start_date: Maximum start date (ISO 8601).
            has_aired: Filter for aired programs.
            is_airing: Filter for currently airing programs.

        Returns:
            List of program objects.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        params: list[str] = [f"UserId={user_id}"]
        if channel_ids:
            params.append(f"ChannelIds={','.join(channel_ids)}")
        if min_start_date:
            params.append(f"MinStartDate={min_start_date}")
        if max_start_date:
            params.append(f"MaxStartDate={max_start_date}")
        if has_aired is not None:
            params.append(f"HasAired={'true' if has_aired else 'false'}")
        if is_airing is not None:
            params.append(f"IsAiring={'true' if is_airing else 'false'}")

        query_string = "&".join(params)
        endpoint = f"/LiveTv/Programs?{query_string}"
        response = await self._request(HTTP_GET, endpoint)
        items: list[EmbyProgram] = response.get("Items", [])  # type: ignore[assignment]
        return items

    async def async_get_recommended_programs(
        self,
        user_id: str,
        limit: int = 10,
    ) -> list[EmbyProgram]:
        """Get recommended programs for a user.

        Args:
            user_id: User ID for personalization.
            limit: Maximum number of programs to return.

        Returns:
            List of recommended program objects.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = f"/LiveTv/Programs/Recommended?UserId={user_id}&Limit={limit}"
        response = await self._request(HTTP_GET, endpoint)
        items: list[EmbyProgram] = response.get("Items", [])  # type: ignore[assignment]
        return items

    # =========================================================================
    # Activity & Device API Methods (Phase 18)
    # =========================================================================

    async def async_get_activity_log(
        self,
        start_index: int = 0,
        limit: int = 50,
        min_date: str | None = None,
        has_user_id: bool | None = None,
    ) -> EmbyActivityLogResponse:
        """Get server activity log entries.

        Args:
            start_index: Pagination offset. Defaults to 0.
            limit: Maximum entries to return. Defaults to 50.
            min_date: ISO 8601 date string to filter entries after.
            has_user_id: Filter to entries associated with a user.

        Returns:
            Activity log response with entries and total count.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        params: list[str] = [
            f"StartIndex={start_index}",
            f"Limit={limit}",
        ]
        if min_date:
            params.append(f"MinDate={min_date}")
        if has_user_id is not None:
            params.append(f"HasUserId={'true' if has_user_id else 'false'}")

        query_string = "&".join(params)
        endpoint = f"/System/ActivityLog/Entries?{query_string}"
        response = await self._request(HTTP_GET, endpoint)
        return response  # type: ignore[return-value]

    async def async_get_devices(
        self,
        user_id: str | None = None,
    ) -> EmbyDevicesResponse:
        """Get registered devices.

        Args:
            user_id: Optional user ID to filter devices.

        Returns:
            Devices response with device list and total count.
            Note: TotalRecordCount may be 0 even with items (Emby API quirk).

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = "/Devices"
        if user_id:
            endpoint = f"{endpoint}?UserId={user_id}"
        response = await self._request(HTTP_GET, endpoint)
        return response  # type: ignore[return-value]

    # =========================================================================
    # Collection Management API Methods (Phase 19)
    # =========================================================================

    async def async_create_collection(
        self,
        name: str,
        item_ids: list[str] | None = None,
    ) -> EmbyCollectionCreateResponse:
        """Create a new collection (BoxSet).

        Args:
            name: Collection name.
            item_ids: Optional list of item IDs to add initially.

        Returns:
            Collection response with new collection ID and name.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        from urllib.parse import quote

        params = [f"Name={quote(name)}"]
        if item_ids:
            params.append(f"Ids={','.join(item_ids)}")

        query_string = "&".join(params)
        endpoint = f"/Collections?{query_string}"
        response = await self._request_post_json(endpoint)
        return response  # type: ignore[return-value]

    async def async_add_to_collection(
        self,
        collection_id: str,
        item_ids: list[str],
    ) -> None:
        """Add items to a collection.

        Args:
            collection_id: The collection ID.
            item_ids: List of item IDs to add.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        ids_param = ",".join(item_ids)
        endpoint = f"/Collections/{collection_id}/Items?Ids={ids_param}"
        await self._request_post(endpoint)

    async def async_remove_from_collection(
        self,
        collection_id: str,
        item_ids: list[str],
    ) -> None:
        """Remove items from a collection.

        Args:
            collection_id: The collection ID.
            item_ids: List of item IDs to remove.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        ids_param = ",".join(item_ids)
        endpoint = f"/Collections/{collection_id}/Items?Ids={ids_param}"
        await self._request_delete(endpoint)

    async def async_get_collections(
        self,
        user_id: str,
    ) -> list[EmbyBrowseItem]:
        """Get all collections (BoxSets) for a user.

        Args:
            user_id: The user ID.

        Returns:
            List of collection items.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        result = await self.async_get_items(
            user_id,
            include_item_types="BoxSet",
            recursive=True,
            sort_by="SortName",
            sort_order="Ascending",
        )
        return result.get("Items", [])

    # =========================================================================
    # Person Browsing API Methods (Phase 19)
    # =========================================================================

    async def async_get_persons(
        self,
        user_id: str,
        parent_id: str | None = None,
        person_types: str | None = None,
        limit: int = 100,
        start_index: int = 0,
    ) -> EmbyPersonsResponse:
        """Get persons (actors, directors, writers) from the library.

        Args:
            user_id: The user ID.
            parent_id: Optional parent library ID to filter persons.
            person_types: Optional person types to filter (e.g., "Actor,Director").
            limit: Maximum number of results to return.
            start_index: Pagination offset.

        Returns:
            Persons response with list of persons.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        # Check cache first (persons lists are relatively stable)
        cache_key = self._browse_cache.generate_key(
            "persons",
            user_id,
            parent_id=parent_id,
            person_types=person_types,
            limit=str(limit),
            start_index=str(start_index),
        )
        cached = self._browse_cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        params = [
            f"UserId={user_id}",
            "SortBy=SortName",
            "SortOrder=Ascending",
            f"Limit={limit}",
            f"StartIndex={start_index}",
        ]
        if parent_id:
            params.append(f"ParentId={parent_id}")
        if person_types:
            params.append(f"PersonTypes={person_types}")

        query_string = "&".join(params)
        endpoint = f"/Persons?{query_string}"
        response = await self._request(HTTP_GET, endpoint)

        # Cache the result
        self._browse_cache.set(cache_key, response)
        return response  # type: ignore[return-value]

    async def async_get_person_items(
        self,
        user_id: str,
        person_id: str,
        include_item_types: str | None = None,
        limit: int = 100,
    ) -> list[EmbyBrowseItem]:
        """Get items featuring a specific person.

        Args:
            user_id: The user ID.
            person_id: The person ID.
            include_item_types: Optional item types to filter (e.g., "Movie,Series").
            limit: Maximum number of results.

        Returns:
            List of items featuring this person.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        params = [
            f"PersonIds={person_id}",
            "Recursive=true",
            "SortBy=SortName",
            "SortOrder=Ascending",
            f"Limit={limit}",
        ]
        if include_item_types:
            params.append(f"IncludeItemTypes={include_item_types}")

        query_string = "&".join(params)
        endpoint = f"/Users/{user_id}/Items?{query_string}"
        response = await self._request(HTTP_GET, endpoint)
        items: list[EmbyBrowseItem] = response.get("Items", [])  # type: ignore[assignment]
        return items

    # =========================================================================
    # Tag Browsing API Methods (Phase 19)
    # =========================================================================

    async def async_get_tags(
        self,
        user_id: str,
        parent_id: str | None = None,
        include_item_types: str | None = None,
    ) -> list[EmbyTag]:
        """Get user-defined tags from the library.

        Args:
            user_id: The user ID.
            parent_id: Optional parent library ID to filter tags.
            include_item_types: Optional item types to filter tags.

        Returns:
            List of tag items.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        # Check cache first
        cache_key = self._browse_cache.generate_key(
            "tags",
            user_id,
            parent_id=parent_id,
            include_item_types=include_item_types,
        )
        cached = self._browse_cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        params = [f"UserId={user_id}", "SortBy=SortName", "SortOrder=Ascending"]
        if parent_id:
            params.append(f"ParentId={parent_id}")
        if include_item_types:
            params.append(f"IncludeItemTypes={include_item_types}")

        query_string = "&".join(params)
        endpoint = f"/Tags?{query_string}"
        response = await self._request(HTTP_GET, endpoint)
        items: list[EmbyTag] = response.get("Items", [])  # type: ignore[assignment]

        # Cache the result
        self._browse_cache.set(cache_key, items)
        return items

    async def async_get_items_by_tag(
        self,
        user_id: str,
        tag_id: str,
        parent_id: str | None = None,
        include_item_types: str | None = None,
        limit: int = 100,
    ) -> list[EmbyBrowseItem]:
        """Get items with a specific tag.

        Args:
            user_id: The user ID.
            tag_id: The tag ID to filter by.
            parent_id: Optional parent library ID.
            include_item_types: Optional item types to filter.
            limit: Maximum number of results.

        Returns:
            List of items with this tag.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        params = [
            f"TagIds={tag_id}",
            "Recursive=true",
            "SortBy=SortName",
            "SortOrder=Ascending",
            f"Limit={limit}",
        ]
        if parent_id:
            params.append(f"ParentId={parent_id}")
        if include_item_types:
            params.append(f"IncludeItemTypes={include_item_types}")

        query_string = "&".join(params)
        endpoint = f"/Users/{user_id}/Items?{query_string}"
        response = await self._request(HTTP_GET, endpoint)
        items: list[EmbyBrowseItem] = response.get("Items", [])  # type: ignore[assignment]
        return items

    # =========================================================================
    # Server Administration API Methods (Phase 20)
    # =========================================================================

    async def async_run_scheduled_task(
        self,
        task_id: str,
    ) -> None:
        """Trigger a scheduled task to run immediately.

        Args:
            task_id: The scheduled task ID to trigger.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
            EmbyNotFoundError: Task ID not found.
        """
        endpoint = f"/ScheduledTasks/Running/{task_id}"
        await self._request_post(endpoint)

    async def async_restart_server(self) -> None:
        """Restart the Emby server.

        This operation is asynchronous. The server will begin restarting
        but the API call returns immediately.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = "/System/Restart"
        await self._request_post(endpoint)

    async def async_shutdown_server(self) -> None:
        """Shutdown the Emby server.

        This operation is asynchronous. The server will begin shutting down
        but the API call returns immediately.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        endpoint = "/System/Shutdown"
        await self._request_post(endpoint)

    async def async_get_plugins(self) -> list[EmbyPlugin]:
        """Get list of installed plugins.

        Returns:
            List of plugin objects with version information.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        response = await self._request(HTTP_GET, "/Plugins")
        return response  # type: ignore[return-value]

    async def close(self) -> None:
        """Close the client session.

        Only closes the session if it was created by this client.
        Sessions provided externally are not closed.
        """
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()


# =============================================================================
# Utility Functions
# =============================================================================


def ticks_to_seconds(ticks: int) -> float:
    """Convert Emby ticks to seconds.

    Emby uses "ticks" where 10,000,000 ticks = 1 second.

    Args:
        ticks: Time value in Emby ticks.

    Returns:
        Time value in seconds.

    Examples:
        >>> ticks_to_seconds(10_000_000)
        1.0
        >>> ticks_to_seconds(0)
        0.0
        >>> ticks_to_seconds(5_000_000)
        0.5
    """
    return ticks / EMBY_TICKS_PER_SECOND


def seconds_to_ticks(seconds: float) -> int:
    """Convert seconds to Emby ticks.

    Args:
        seconds: Time value in seconds.

    Returns:
        Time value in Emby ticks.

    Examples:
        >>> seconds_to_ticks(1.0)
        10000000
        >>> seconds_to_ticks(0.0)
        0
        >>> seconds_to_ticks(0.5)
        5000000
    """
    return int(seconds * EMBY_TICKS_PER_SECOND)
