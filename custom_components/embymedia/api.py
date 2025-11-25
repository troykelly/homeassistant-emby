"""Emby API client."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Self

import aiohttp

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
    USER_AGENT_TEMPLATE,
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

if TYPE_CHECKING:
    from .const import (
        EmbyBrowseItem,
        EmbyItemsResponse,
        EmbyLibraryItem,
        EmbyPublicInfo,
        EmbyServerInfo,
        EmbySessionResponse,
        EmbyUser,
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
                    raise EmbyAuthenticationError(
                        f"Authentication failed: {response.status} {response.reason}"
                    )

                if response.status == 404:
                    raise EmbyNotFoundError(f"Resource not found: {endpoint}")

                if response.status >= 500:
                    raise EmbyServerError(f"Server error: {response.status} {response.reason}")

                response.raise_for_status()

                return await response.json()  # type: ignore[no-any-return]

        except aiohttp.ClientSSLError as err:
            _LOGGER.error(
                "Emby API SSL error for %s %s: %s",
                method,
                endpoint,
                err,
            )
            raise EmbySSLError(f"SSL certificate error: {err}") from err

        except TimeoutError as err:
            _LOGGER.error(
                "Emby API timeout for %s %s",
                method,
                endpoint,
            )
            raise EmbyTimeoutError(f"Request timed out after {self._timeout.total}s") from err

        except aiohttp.ClientConnectorError as err:
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
            _LOGGER.error(
                "Emby API client error for %s %s: %s",
                method,
                endpoint,
                err,
            )
            raise EmbyConnectionError(f"Client error: {err}") from err

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

        Returns:
            Server information including ID, name, and version.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        response = await self._request(HTTP_GET, ENDPOINT_SYSTEM_INFO)
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

        Returns:
            List of session objects representing connected clients.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        response = await self._request(HTTP_GET, ENDPOINT_SESSIONS)
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
                    raise EmbyAuthenticationError(f"Authentication failed: {response.status}")

                # 204 No Content is success
                if response.status == 204:
                    return

                response.raise_for_status()

        except aiohttp.ClientSSLError as err:
            raise EmbySSLError(f"SSL certificate error: {err}") from err

        except TimeoutError as err:
            raise EmbyTimeoutError(f"Request timed out after {self._timeout.total}s") from err

        except aiohttp.ClientConnectorError as err:
            raise EmbyConnectionError(
                f"Failed to connect to {self._host}:{self._port}: {err}"
            ) from err

        except aiohttp.ClientError as err:
            raise EmbyConnectionError(f"Client error: {err}") from err

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
