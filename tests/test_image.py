"""Tests for Emby image proxy view."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from aiohttp import web
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.embymedia.const import DOMAIN
from custom_components.embymedia.image_proxy import (
    CACHE_TIME_WITH_TAG,
    CACHE_TIME_WITHOUT_TAG,
    EmbyImageProxyView,
    async_setup_image_proxy,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestCacheConstants:
    """Tests for cache time constants."""

    def test_cache_time_with_tag(self) -> None:
        """Test cache time with tag is 1 year."""
        assert CACHE_TIME_WITH_TAG == 31536000  # 365 * 24 * 60 * 60

    def test_cache_time_without_tag(self) -> None:
        """Test cache time without tag is 5 minutes."""
        assert CACHE_TIME_WITHOUT_TAG == 300  # 5 * 60


class TestEmbyImageProxyView:
    """Tests for EmbyImageProxyView."""

    def test_view_url_pattern(self) -> None:
        """Test that the view URL pattern is correct."""
        view = EmbyImageProxyView()
        assert view.url == "/api/embymedia/image/{server_id}/{item_id}/{image_type}"

    def test_view_name(self) -> None:
        """Test that the view name is correct."""
        view = EmbyImageProxyView()
        assert view.name == "api:embymedia:image"

    def test_view_requires_auth_is_false(self) -> None:
        """Test that the view does not require authentication.

        Images should be accessible without HA authentication since
        the proxy handles Emby authentication internally.
        """
        view = EmbyImageProxyView()
        assert view.requires_auth is False


class TestImageProxySetup:
    """Tests for image proxy setup."""

    async def test_async_setup_image_proxy_registers_view(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that async_setup_image_proxy registers the view."""
        mock_register = MagicMock()
        hass.http = MagicMock()
        hass.http.register_view = mock_register

        await async_setup_image_proxy(hass)

        mock_register.assert_called_once()
        call_args = mock_register.call_args[0]
        assert isinstance(call_args[0], EmbyImageProxyView)


class TestImageProxyGet:
    """Tests for image proxy GET request handling."""

    @pytest.fixture
    def mock_coordinator(self) -> MagicMock:
        """Create a mock coordinator."""
        coordinator = MagicMock()
        coordinator.client = MagicMock()
        coordinator.client.base_url = "http://emby.local:8096"
        coordinator.client.api_key = "test-api-key"
        return coordinator

    @pytest.fixture
    def mock_config_entry(self, mock_coordinator: MagicMock) -> MockConfigEntry:
        """Create a mock config entry with runtime data."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "host": "emby.local",
                "port": 8096,
                "api_key": "test-api-key",
            },
            unique_id="server-123",
        )
        entry.runtime_data = MagicMock(session_coordinator=mock_coordinator)
        return entry

    async def test_get_image_proxies_request(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test that GET request proxies to Emby server."""
        mock_config_entry.add_to_hass(hass)

        # Mock the aiohttp ClientSession response with streaming
        mock_response = MagicMock()
        mock_response.status = HTTPStatus.OK
        mock_response.headers = {"Content-Type": "image/jpeg"}

        # Mock iter_chunked for streaming
        async def mock_iter_chunked(chunk_size: int) -> AsyncMock:
            yield b"fake image data"

        mock_response.content = MagicMock()
        mock_response.content.iter_chunked = mock_iter_chunked

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=AsyncMock())
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "custom_components.embymedia.image_proxy.async_get_clientsession",
                return_value=mock_session,
            ),
            patch.object(web.StreamResponse, "prepare", new_callable=AsyncMock),
            patch.object(web.StreamResponse, "write", new_callable=AsyncMock),
            patch.object(web.StreamResponse, "write_eof", new_callable=AsyncMock),
        ):
            view = EmbyImageProxyView()
            view.hass = hass

            # Create mock request
            request = MagicMock(spec=web.Request)
            request.query = {}

            response = await view.get(
                request,
                server_id="server-123",
                item_id="item-456",
                image_type="Primary",
            )

            # Now returns StreamResponse for successful requests
            assert response.status == HTTPStatus.OK
            assert isinstance(response, web.StreamResponse)

    async def test_get_image_includes_query_params(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test that query params are forwarded to Emby."""
        mock_config_entry.add_to_hass(hass)

        mock_response = MagicMock()
        mock_response.status = HTTPStatus.OK
        mock_response.headers = {"Content-Type": "image/jpeg"}

        # Mock iter_chunked for streaming
        async def mock_iter_chunked(chunk_size: int) -> AsyncMock:
            yield b"image data"

        mock_response.content = MagicMock()
        mock_response.content.iter_chunked = mock_iter_chunked

        mock_session = MagicMock()

        captured_url: str | None = None

        # Create async context manager for the mock response
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        def capture_url(url: str, **kwargs: object) -> MagicMock:
            nonlocal captured_url
            captured_url = url
            return mock_context

        mock_session.get = capture_url

        with (
            patch(
                "custom_components.embymedia.image_proxy.async_get_clientsession",
                return_value=mock_session,
            ),
            patch.object(web.StreamResponse, "prepare", new_callable=AsyncMock),
            patch.object(web.StreamResponse, "write", new_callable=AsyncMock),
            patch.object(web.StreamResponse, "write_eof", new_callable=AsyncMock),
        ):
            view = EmbyImageProxyView()
            view.hass = hass

            request = MagicMock(spec=web.Request)
            request.query = {"maxWidth": "300", "maxHeight": "300", "tag": "abc123"}

            await view.get(
                request,
                server_id="server-123",
                item_id="item-456",
                image_type="Primary",
            )

            assert captured_url is not None
            assert "maxWidth=300" in captured_url
            assert "maxHeight=300" in captured_url
            assert "tag=abc123" in captured_url

    async def test_get_image_server_not_found(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that 404 is returned when server is not found."""
        view = EmbyImageProxyView()
        view.hass = hass

        request = MagicMock(spec=web.Request)
        request.query = {}

        response = await view.get(
            request,
            server_id="nonexistent-server",
            item_id="item-456",
            image_type="Primary",
        )

        assert response.status == HTTPStatus.NOT_FOUND

    async def test_get_image_returns_cache_headers(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test that cache headers are set on response."""
        mock_config_entry.add_to_hass(hass)

        mock_response = MagicMock()
        mock_response.status = HTTPStatus.OK
        mock_response.headers = {"Content-Type": "image/jpeg"}

        # Mock iter_chunked for streaming
        async def mock_iter_chunked(chunk_size: int) -> AsyncMock:
            yield b"image data"

        mock_response.content = MagicMock()
        mock_response.content.iter_chunked = mock_iter_chunked

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=AsyncMock())
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "custom_components.embymedia.image_proxy.async_get_clientsession",
                return_value=mock_session,
            ),
            patch.object(web.StreamResponse, "prepare", new_callable=AsyncMock),
            patch.object(web.StreamResponse, "write", new_callable=AsyncMock),
            patch.object(web.StreamResponse, "write_eof", new_callable=AsyncMock),
        ):
            view = EmbyImageProxyView()
            view.hass = hass

            request = MagicMock(spec=web.Request)
            request.query = {"tag": "abc123"}  # Tag provided for caching

            response = await view.get(
                request,
                server_id="server-123",
                item_id="item-456",
                image_type="Primary",
            )

            # When tag is provided, cache for a long time
            assert "Cache-Control" in response.headers
            assert "max-age" in response.headers["Cache-Control"]

    async def test_get_image_no_cache_without_tag(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test that cache is minimal without tag."""
        mock_config_entry.add_to_hass(hass)

        mock_response = MagicMock()
        mock_response.status = HTTPStatus.OK
        mock_response.headers = {"Content-Type": "image/jpeg"}

        # Mock iter_chunked for streaming
        async def mock_iter_chunked(chunk_size: int) -> AsyncMock:
            yield b"image data"

        mock_response.content = MagicMock()
        mock_response.content.iter_chunked = mock_iter_chunked

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=AsyncMock())
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "custom_components.embymedia.image_proxy.async_get_clientsession",
                return_value=mock_session,
            ),
            patch.object(web.StreamResponse, "prepare", new_callable=AsyncMock),
            patch.object(web.StreamResponse, "write", new_callable=AsyncMock),
            patch.object(web.StreamResponse, "write_eof", new_callable=AsyncMock),
        ):
            view = EmbyImageProxyView()
            view.hass = hass

            request = MagicMock(spec=web.Request)
            request.query = {}  # No tag

            response = await view.get(
                request,
                server_id="server-123",
                item_id="item-456",
                image_type="Primary",
            )

            # Without tag, cache for shorter time
            assert "Cache-Control" in response.headers

    async def test_get_image_emby_error_propagated(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test that Emby server errors are propagated."""
        mock_config_entry.add_to_hass(hass)

        mock_response = MagicMock()
        mock_response.status = HTTPStatus.NOT_FOUND
        mock_response.headers = {}
        mock_response.read = AsyncMock(return_value=b"")

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=AsyncMock())
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "custom_components.embymedia.image_proxy.async_get_clientsession",
            return_value=mock_session,
        ):
            view = EmbyImageProxyView()
            view.hass = hass

            request = MagicMock(spec=web.Request)
            request.query = {}

            response = await view.get(
                request,
                server_id="server-123",
                item_id="nonexistent-item",
                image_type="Primary",
            )

            assert response.status == HTTPStatus.NOT_FOUND

    async def test_get_image_network_error(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test that network errors return 502 Bad Gateway."""
        mock_config_entry.add_to_hass(hass)

        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=aiohttp.ClientError("Network error"))

        with patch(
            "custom_components.embymedia.image_proxy.async_get_clientsession",
            return_value=mock_session,
        ):
            view = EmbyImageProxyView()
            view.hass = hass

            request = MagicMock(spec=web.Request)
            request.query = {}

            response = await view.get(
                request,
                server_id="server-123",
                item_id="item-456",
                image_type="Primary",
            )

            assert response.status == HTTPStatus.BAD_GATEWAY
            assert "Network error" in response.text

    async def test_get_image_finds_coordinator_by_server_id_attribute(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that coordinator is found by server_id attribute."""
        # Create a coordinator with server_id attribute
        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-by-attr"
        mock_coordinator.client = MagicMock()
        mock_coordinator.client.base_url = "http://emby.local:8096"
        mock_coordinator.client.api_key = "test-api-key"

        mock_config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "host": "emby.local",
                "port": 8096,
                "api_key": "test-api-key",
            },
            unique_id="different-unique-id",  # Different from server_id
        )
        mock_config_entry.runtime_data = MagicMock(session_coordinator=mock_coordinator)
        mock_config_entry.add_to_hass(hass)

        mock_response = MagicMock()
        mock_response.status = HTTPStatus.OK
        mock_response.headers = {"Content-Type": "image/jpeg"}

        # Mock iter_chunked for streaming
        async def mock_iter_chunked(chunk_size: int) -> AsyncMock:
            yield b"image data"

        mock_response.content = MagicMock()
        mock_response.content.iter_chunked = mock_iter_chunked

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=AsyncMock())
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "custom_components.embymedia.image_proxy.async_get_clientsession",
                return_value=mock_session,
            ),
            patch.object(web.StreamResponse, "prepare", new_callable=AsyncMock),
            patch.object(web.StreamResponse, "write", new_callable=AsyncMock),
            patch.object(web.StreamResponse, "write_eof", new_callable=AsyncMock),
        ):
            view = EmbyImageProxyView()
            view.hass = hass

            request = MagicMock(spec=web.Request)
            request.query = {}

            response = await view.get(
                request,
                server_id="server-by-attr",
                item_id="item-456",
                image_type="Primary",
            )

            assert response.status == HTTPStatus.OK


class TestImageProxyResize:
    """Tests for image proxy resize parameters."""

    @pytest.fixture
    def mock_coordinator(self) -> MagicMock:
        """Create a mock coordinator."""
        coordinator = MagicMock()
        coordinator.client = MagicMock()
        coordinator.client.base_url = "http://emby.local:8096"
        coordinator.client.api_key = "test-api-key"
        return coordinator

    @pytest.fixture
    def mock_config_entry(self, mock_coordinator: MagicMock) -> MockConfigEntry:
        """Create a mock config entry with runtime data."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "host": "emby.local",
                "port": 8096,
                "api_key": "test-api-key",
            },
            unique_id="server-123",
        )
        entry.runtime_data = MagicMock(session_coordinator=mock_coordinator)
        return entry

    async def test_resize_params_forwarded(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test that resize parameters are forwarded to Emby."""
        mock_config_entry.add_to_hass(hass)

        mock_response = MagicMock()
        mock_response.status = HTTPStatus.OK
        mock_response.headers = {"Content-Type": "image/jpeg"}

        # Mock iter_chunked for streaming
        async def mock_iter_chunked(chunk_size: int) -> AsyncMock:
            yield b"resized image"

        mock_response.content = MagicMock()
        mock_response.content.iter_chunked = mock_iter_chunked

        captured_url: str | None = None

        def capture_url(url: str, **kwargs: object) -> MagicMock:
            nonlocal captured_url
            captured_url = url
            mock_get = MagicMock()
            mock_get.__aenter__ = AsyncMock(return_value=mock_response)
            mock_get.__aexit__ = AsyncMock(return_value=None)
            return mock_get

        mock_session = MagicMock()
        mock_session.get = capture_url

        with (
            patch(
                "custom_components.embymedia.image_proxy.async_get_clientsession",
                return_value=mock_session,
            ),
            patch.object(web.StreamResponse, "prepare", new_callable=AsyncMock),
            patch.object(web.StreamResponse, "write", new_callable=AsyncMock),
            patch.object(web.StreamResponse, "write_eof", new_callable=AsyncMock),
        ):
            view = EmbyImageProxyView()
            view.hass = hass

            request = MagicMock(spec=web.Request)
            request.query = {"maxWidth": "500", "maxHeight": "500", "quality": "90"}

            await view.get(
                request,
                server_id="server-123",
                item_id="item-456",
                image_type="Primary",
            )

            assert captured_url is not None
            assert "maxWidth=500" in captured_url
            assert "maxHeight=500" in captured_url
            assert "quality=90" in captured_url


class TestImageProxyErrors:
    """Tests for image proxy error handling."""

    @pytest.fixture
    def mock_coordinator(self) -> MagicMock:
        """Create a mock coordinator."""
        coordinator = MagicMock()
        coordinator.client = MagicMock()
        coordinator.client.base_url = "http://emby.local:8096"
        coordinator.client.api_key = "test-api-key"
        return coordinator

    @pytest.fixture
    def mock_config_entry(self, mock_coordinator: MagicMock) -> MockConfigEntry:
        """Create a mock config entry with runtime data."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "host": "emby.local",
                "port": 8096,
                "api_key": "test-api-key",
            },
            unique_id="server-123",
        )
        entry.runtime_data = MagicMock(session_coordinator=mock_coordinator)
        return entry

    async def test_get_image_timeout_error(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test that timeout errors return 504 Gateway Timeout."""
        mock_config_entry.add_to_hass(hass)

        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=TimeoutError("Request timed out"))

        with patch(
            "custom_components.embymedia.image_proxy.async_get_clientsession",
            return_value=mock_session,
        ):
            view = EmbyImageProxyView()
            view.hass = hass

            request = MagicMock(spec=web.Request)
            request.query = {}

            response = await view.get(
                request,
                server_id="server-123",
                item_id="item-456",
                image_type="Primary",
            )

            assert response.status == HTTPStatus.GATEWAY_TIMEOUT
            assert "Timeout" in response.text

    async def test_get_image_os_error(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test that OS errors return 502 Bad Gateway."""
        mock_config_entry.add_to_hass(hass)

        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=OSError("Connection reset"))

        with patch(
            "custom_components.embymedia.image_proxy.async_get_clientsession",
            return_value=mock_session,
        ):
            view = EmbyImageProxyView()
            view.hass = hass

            request = MagicMock(spec=web.Request)
            request.query = {}

            response = await view.get(
                request,
                server_id="server-123",
                item_id="item-456",
                image_type="Primary",
            )

            assert response.status == HTTPStatus.BAD_GATEWAY
            assert "Error fetching image" in response.text


class TestImageProxyStreaming:
    """Tests for image proxy streaming functionality (Phase 22)."""

    @pytest.fixture
    def mock_coordinator(self) -> MagicMock:
        """Create a mock coordinator."""
        coordinator = MagicMock()
        coordinator.client = MagicMock()
        coordinator.client.base_url = "http://emby.local:8096"
        coordinator.client.api_key = "test-api-key"
        return coordinator

    @pytest.fixture
    def mock_config_entry(self, mock_coordinator: MagicMock) -> MockConfigEntry:
        """Create a mock config entry with runtime data."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "host": "emby.local",
                "port": 8096,
                "api_key": "test-api-key",
            },
            unique_id="server-123",
        )
        entry.runtime_data = MagicMock(session_coordinator=mock_coordinator)
        return entry

    async def test_streaming_response_used(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test that streaming response is used instead of loading full body."""
        mock_config_entry.add_to_hass(hass)

        # Create mock response with iter_chunked
        mock_response = MagicMock()
        mock_response.status = HTTPStatus.OK
        mock_response.headers = {"Content-Type": "image/jpeg"}

        # Mock the iter_chunked async iterator
        chunks = [b"chunk1", b"chunk2", b"chunk3"]

        async def mock_iter_chunked(chunk_size: int) -> AsyncMock:
            for chunk in chunks:
                yield chunk

        mock_response.content = MagicMock()
        mock_response.content.iter_chunked = mock_iter_chunked

        mock_session = MagicMock()
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context)

        # Mock StreamResponse.prepare and write methods
        with (
            patch(
                "custom_components.embymedia.image_proxy.async_get_clientsession",
                return_value=mock_session,
            ),
            patch.object(web.StreamResponse, "prepare", new_callable=AsyncMock) as mock_prepare,
            patch.object(web.StreamResponse, "write", new_callable=AsyncMock),
            patch.object(web.StreamResponse, "write_eof", new_callable=AsyncMock),
        ):
            view = EmbyImageProxyView()
            view.hass = hass

            # Create mock request with proper app attribute
            request = MagicMock(spec=web.Request)
            request.query = {}

            response = await view.get(
                request,
                server_id="server-123",
                item_id="item-456",
                image_type="Primary",
            )

            # Response should be a StreamResponse
            assert isinstance(response, web.StreamResponse)
            # prepare should have been called with the request
            mock_prepare.assert_called_once_with(request)

    async def test_streaming_handles_error_status(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test that error status codes return regular Response (not streaming)."""
        mock_config_entry.add_to_hass(hass)

        mock_response = MagicMock()
        mock_response.status = HTTPStatus.NOT_FOUND
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.read = AsyncMock(return_value=b"Not Found")

        mock_session = MagicMock()
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context)

        with patch(
            "custom_components.embymedia.image_proxy.async_get_clientsession",
            return_value=mock_session,
        ):
            view = EmbyImageProxyView()
            view.hass = hass

            request = MagicMock(spec=web.Request)
            request.query = {}

            response = await view.get(
                request,
                server_id="server-123",
                item_id="item-456",
                image_type="Primary",
            )

            # Error responses should return a regular Response with the status code
            assert isinstance(response, web.Response)
            assert response.status == HTTPStatus.NOT_FOUND


class TestImageProxyTimeout:
    """Tests for image proxy timeout configuration (Phase 22)."""

    @pytest.fixture
    def mock_coordinator(self) -> MagicMock:
        """Create a mock coordinator."""
        coordinator = MagicMock()
        coordinator.client = MagicMock()
        coordinator.client.base_url = "http://emby.local:8096"
        coordinator.client.api_key = "test-api-key"
        return coordinator

    @pytest.fixture
    def mock_config_entry(self, mock_coordinator: MagicMock) -> MockConfigEntry:
        """Create a mock config entry with runtime data."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "host": "emby.local",
                "port": 8096,
                "api_key": "test-api-key",
            },
            unique_id="server-123",
        )
        entry.runtime_data = MagicMock(session_coordinator=mock_coordinator)
        return entry

    def test_image_fetch_timeout_constant_exists(self) -> None:
        """Test that IMAGE_FETCH_TIMEOUT constant is defined."""
        from custom_components.embymedia.image_proxy import IMAGE_FETCH_TIMEOUT

        # Should be a reasonable timeout for image fetching (e.g., 10 seconds)
        assert isinstance(IMAGE_FETCH_TIMEOUT, int)
        assert IMAGE_FETCH_TIMEOUT > 0
        assert IMAGE_FETCH_TIMEOUT <= 30  # Reasonable upper bound

    async def test_get_image_uses_explicit_timeout(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test that GET request uses explicit timeout."""
        from custom_components.embymedia.image_proxy import IMAGE_FETCH_TIMEOUT

        mock_config_entry.add_to_hass(hass)

        mock_response = MagicMock()
        mock_response.status = HTTPStatus.OK
        mock_response.headers = {"Content-Type": "image/jpeg"}

        # Mock iter_chunked for streaming
        async def mock_iter_chunked(chunk_size: int) -> AsyncMock:
            yield b"image data"

        mock_response.content = MagicMock()
        mock_response.content.iter_chunked = mock_iter_chunked

        captured_timeout: aiohttp.ClientTimeout | None = None

        def capture_timeout(url: str, **kwargs: object) -> MagicMock:
            nonlocal captured_timeout
            captured_timeout = kwargs.get("timeout")  # type: ignore[assignment]
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            return mock_context

        mock_session = MagicMock()
        mock_session.get = capture_timeout

        with (
            patch(
                "custom_components.embymedia.image_proxy.async_get_clientsession",
                return_value=mock_session,
            ),
            patch.object(web.StreamResponse, "prepare", new_callable=AsyncMock),
            patch.object(web.StreamResponse, "write", new_callable=AsyncMock),
            patch.object(web.StreamResponse, "write_eof", new_callable=AsyncMock),
        ):
            view = EmbyImageProxyView()
            view.hass = hass

            request = MagicMock(spec=web.Request)
            request.query = {}

            await view.get(
                request,
                server_id="server-123",
                item_id="item-456",
                image_type="Primary",
            )

            # Timeout should be passed explicitly
            assert captured_timeout is not None
            assert isinstance(captured_timeout, aiohttp.ClientTimeout)
            assert captured_timeout.total == IMAGE_FETCH_TIMEOUT
