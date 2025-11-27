"""Emby API client."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Self, cast

import aiohttp

from .cache import BrowseCache
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

if TYPE_CHECKING:
    from .const import (
        EmbyBrowseItem,
        EmbyItemCounts,
        EmbyItemsResponse,
        EmbyLibraryItem,
        EmbyPublicInfo,
        EmbyScheduledTask,
        EmbyServerInfo,
        EmbySessionResponse,
        EmbyUser,
        EmbyVirtualFolder,
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

    def clear_browse_cache(self) -> None:
        """Clear the browse cache.

        Useful when library contents have changed.
        """
        self._browse_cache.clear()

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

                try:
                    return await response.json()  # type: ignore[no-any-return]
                except (aiohttp.ContentTypeError, ValueError) as err:
                    _LOGGER.error(
                        "Emby API returned invalid JSON for %s %s: %s",
                        method,
                        endpoint,
                        err,
                    )
                    raise EmbyServerError(f"Server returned invalid JSON: {err}") from err

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
            raise EmbySSLError(f"SSL certificate error: {err}") from err

        except TimeoutError as err:
            raise EmbyTimeoutError(f"Request timed out after {self._timeout.total}s") from err

        except aiohttp.ClientConnectorError as err:
            raise EmbyConnectionError(
                f"Failed to connect to {self._host}:{self._port}: {err}"
            ) from err

        except aiohttp.ClientError as err:
            raise EmbyConnectionError(f"Client error: {err}") from err

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
        response = await self._request(HTTP_GET, endpoint)
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
