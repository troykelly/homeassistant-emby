"""Emby image proxy view."""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING

import aiohttp
from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .coordinator import EmbyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Cache time in seconds when image tag is provided (1 year)
CACHE_TIME_WITH_TAG = 31536000

# Cache time in seconds when no tag is provided (5 minutes)
CACHE_TIME_WITHOUT_TAG = 300

# Chunk size for streaming images (64KB)
STREAM_CHUNK_SIZE = 65536

# Timeout for image fetch requests (seconds)
IMAGE_FETCH_TIMEOUT = 10


async def async_setup_image_proxy(hass: HomeAssistant) -> None:
    """Set up the Emby image proxy view.

    Args:
        hass: Home Assistant instance.
    """
    hass.http.register_view(EmbyImageProxyView())
    _LOGGER.debug("Emby image proxy view registered")


class EmbyImageProxyView(HomeAssistantView):
    """Proxy view for Emby images.

    This view proxies image requests to the Emby server, handling
    authentication internally so that images can be accessed without
    exposing the API key to clients.

    URL pattern: /api/embymedia/image/{server_id}/{item_id}/{image_type}

    Query parameters are forwarded to the Emby server:
    - maxWidth: Maximum image width
    - maxHeight: Maximum image height
    - quality: JPEG quality (0-100)
    - tag: Image tag for cache busting
    """

    url = "/api/embymedia/image/{server_id}/{item_id}/{image_type}"
    name = "api:embymedia:image"
    requires_auth = False  # Images are public, Emby auth is handled internally

    async def get(
        self,
        request: web.Request,
        server_id: str,
        item_id: str,
        image_type: str,
    ) -> web.StreamResponse:
        """Handle GET request for an image with streaming response.

        Uses streaming to avoid loading large images fully into memory.
        Chunks are forwarded from Emby to the client as they arrive.

        Args:
            request: The aiohttp request.
            server_id: The Emby server ID.
            item_id: The item ID to get the image for.
            image_type: The image type (Primary, Backdrop, Thumb, etc.).

        Returns:
            A streaming response with the image data.
        """
        # Get hass from self (set by HA view registration) or from request app
        hass: HomeAssistant = getattr(self, "hass", None) or request.app["hass"]

        # Find the coordinator for the server
        coordinator = self._find_coordinator(hass, server_id)
        if coordinator is None:
            return web.Response(
                status=HTTPStatus.NOT_FOUND,
                text=f"Server {server_id} not found",
            )

        # Build the Emby image URL
        emby_url = self._build_emby_url(
            coordinator.client.base_url,
            coordinator.client.api_key,
            item_id,
            image_type,
            dict(request.query),
        )

        # Fetch the image from Emby with streaming
        session = async_get_clientsession(hass)
        timeout = aiohttp.ClientTimeout(total=IMAGE_FETCH_TIMEOUT)
        try:
            async with session.get(emby_url, timeout=timeout) as response:
                # For error responses, return a regular response with the status
                if response.status != HTTPStatus.OK:
                    body = await response.read()
                    return web.Response(
                        status=response.status,
                        body=body,
                        headers=self._build_response_headers(
                            response.headers.get("Content-Type", "application/octet-stream"),
                            "tag" in request.query,
                        ),
                    )

                # Build streaming response with headers
                headers = self._build_response_headers(
                    response.headers.get("Content-Type", "application/octet-stream"),
                    "tag" in request.query,
                )
                stream_response = web.StreamResponse(
                    status=HTTPStatus.OK,
                    headers=headers,
                )

                # Prepare the response (starts sending headers to client)
                await stream_response.prepare(request)

                # Stream chunks from Emby to client
                async for chunk in response.content.iter_chunked(STREAM_CHUNK_SIZE):
                    await stream_response.write(chunk)

                # Finalize the response
                await stream_response.write_eof()
                return stream_response

        except aiohttp.ClientError as err:
            _LOGGER.warning("Network error fetching image from Emby: %s", err)
            return web.Response(
                status=HTTPStatus.BAD_GATEWAY,
                text="Network error fetching image from Emby server",
            )
        except TimeoutError:
            _LOGGER.warning("Timeout fetching image from Emby")
            return web.Response(
                status=HTTPStatus.GATEWAY_TIMEOUT,
                text="Timeout fetching image from Emby server",
            )
        except OSError as err:
            _LOGGER.warning("OS error fetching image from Emby: %s", err)
            return web.Response(
                status=HTTPStatus.BAD_GATEWAY,
                text="Error fetching image from Emby server",
            )

    def _find_coordinator(
        self,
        hass: HomeAssistant,
        server_id: str,
    ) -> EmbyDataUpdateCoordinator | None:
        """Find the coordinator for a server ID.

        Args:
            hass: Home Assistant instance.
            server_id: The server ID to find.

        Returns:
            The coordinator if found, None otherwise.
        """
        for entry in hass.config_entries.async_entries(DOMAIN):
            if hasattr(entry, "runtime_data") and entry.runtime_data is not None:
                coordinator: EmbyDataUpdateCoordinator = entry.runtime_data.session_coordinator
                if hasattr(coordinator, "server_id") and coordinator.server_id == server_id:
                    return coordinator
                # Also check by unique_id which should match server_id
                if entry.unique_id == server_id:
                    return coordinator
        return None

    def _build_emby_url(
        self,
        base_url: str,
        api_key: str,
        item_id: str,
        image_type: str,
        query_params: dict[str, str],
    ) -> str:
        """Build the full URL to fetch the image from Emby.

        Args:
            base_url: The Emby server base URL.
            api_key: The API key for authentication.
            item_id: The item ID.
            image_type: The image type.
            query_params: Additional query parameters from the request.

        Returns:
            The full URL to fetch the image.
        """
        url = f"{base_url}/Items/{item_id}/Images/{image_type}"
        params: list[str] = [f"api_key={api_key}"]

        # Forward relevant query parameters
        for key in ("maxWidth", "maxHeight", "quality", "tag"):
            if key in query_params:
                params.append(f"{key}={query_params[key]}")

        return f"{url}?{'&'.join(params)}"

    def _build_response_headers(
        self,
        content_type: str,
        has_tag: bool,
    ) -> dict[str, str]:
        """Build response headers with caching information.

        Args:
            content_type: The Content-Type of the image.
            has_tag: Whether an image tag was provided.

        Returns:
            Dictionary of response headers.
        """
        cache_time = CACHE_TIME_WITH_TAG if has_tag else CACHE_TIME_WITHOUT_TAG
        return {
            "Content-Type": content_type,
            "Cache-Control": f"public, max-age={cache_time}",
        }
