"""Tests for Emby API client."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.embymedia.api import (
    EmbyClient,
    seconds_to_ticks,
    ticks_to_seconds,
)
from custom_components.embymedia.const import EMBY_TICKS_PER_SECOND
from custom_components.embymedia.exceptions import (
    EmbyAuthenticationError,
    EmbyConnectionError,
    EmbyNotFoundError,
    EmbyServerError,
    EmbySSLError,
    EmbyTimeoutError,
)


class TestEmbyClientInitialization:
    """Test EmbyClient initialization."""

    def test_client_initialization(self) -> None:
        """Test client stores parameters correctly."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
            verify_ssl=True,
            timeout=30,
        )
        assert client._host == "emby.local"
        assert client._port == 8096
        assert client._api_key == "test-key"
        assert client._ssl is False
        assert client._verify_ssl is True

    def test_client_default_values(self) -> None:
        """Test client uses default values."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-key",
        )
        assert client._ssl is False
        assert client._verify_ssl is True


class TestBaseUrl:
    """Test base URL generation."""

    def test_base_url_http(self) -> None:
        """Test base URL generation without SSL."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=False,
        )
        assert client.base_url == "http://emby.local:8096"

    def test_base_url_https(self) -> None:
        """Test base URL generation with SSL."""
        client = EmbyClient(
            host="emby.local",
            port=8920,
            api_key="test-key",
            ssl=True,
        )
        assert client.base_url == "https://emby.local:8920"

    def test_base_url_custom_port(self) -> None:
        """Test base URL with custom port."""
        client = EmbyClient(
            host="192.168.1.100",
            port=9999,
            api_key="test-key",
            ssl=False,
        )
        assert client.base_url == "http://192.168.1.100:9999"


class TestHeaders:
    """Test HTTP headers generation."""

    def test_headers_include_auth(self) -> None:
        """Test auth header included when required."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="my-secret-key",
        )
        headers = client._get_headers(include_auth=True)
        assert "X-Emby-Token" in headers
        assert headers["X-Emby-Token"] == "my-secret-key"

    def test_headers_exclude_auth(self) -> None:
        """Test auth header excluded when not required."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="my-secret-key",
        )
        headers = client._get_headers(include_auth=False)
        assert "X-Emby-Token" not in headers

    def test_user_agent_header(self) -> None:
        """Test User-Agent header is set."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-key",
        )
        headers = client._get_headers()
        assert "User-Agent" in headers
        assert "HomeAssistant/Emby" in headers["User-Agent"]

    def test_accept_header(self) -> None:
        """Test Accept header is set."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-key",
        )
        headers = client._get_headers()
        assert headers["Accept"] == "application/json"


class TestValidateConnection:
    """Test connection validation."""

    @pytest.mark.asyncio
    async def test_validate_connection_success(
        self, mock_server_info: dict[str, Any]
    ) -> None:
        """Test successful connection validation."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(return_value=mock_server_info)
            mock_response.raise_for_status = MagicMock()
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            result = await client.async_validate_connection()
            assert result is True
            await client.close()

    @pytest.mark.asyncio
    async def test_validate_connection_auth_error(self) -> None:
        """Test 401 response raises EmbyAuthenticationError."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 401
            mock_response.reason = "Unauthorized"
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="bad-key",
            )
            with pytest.raises(EmbyAuthenticationError):
                await client.async_validate_connection()
            await client.close()

    @pytest.mark.asyncio
    async def test_validate_connection_403_error(self) -> None:
        """Test 403 response raises EmbyAuthenticationError."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 403
            mock_response.reason = "Forbidden"
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="bad-key",
            )
            with pytest.raises(EmbyAuthenticationError):
                await client.async_validate_connection()
            await client.close()

    @pytest.mark.asyncio
    async def test_validate_connection_connection_error(self) -> None:
        """Test connection failure raises EmbyConnectionError."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.request = MagicMock(
                side_effect=aiohttp.ClientConnectorError(
                    MagicMock(), OSError("Connection refused")
                )
            )
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            with pytest.raises(EmbyConnectionError):
                await client.async_validate_connection()
            await client.close()

    @pytest.mark.asyncio
    async def test_validate_connection_timeout(self) -> None:
        """Test timeout raises EmbyTimeoutError."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.request = MagicMock(side_effect=TimeoutError())
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            with pytest.raises(EmbyTimeoutError):
                await client.async_validate_connection()
            await client.close()

    @pytest.mark.asyncio
    async def test_validate_connection_ssl_error(self) -> None:
        """Test SSL error raises EmbySSLError."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            ssl_error = OSError("SSL certificate verify failed")
            mock_session.request = MagicMock(
                side_effect=aiohttp.ClientSSLError(MagicMock(), ssl_error)
            )
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8920,
                api_key="test-key",
                ssl=True,
            )
            with pytest.raises(EmbySSLError):
                await client.async_validate_connection()
            await client.close()


class TestGetServerInfo:
    """Test server info retrieval."""

    @pytest.mark.asyncio
    async def test_get_server_info_success(
        self, mock_server_info: dict[str, Any]
    ) -> None:
        """Test successful server info retrieval."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(return_value=mock_server_info)
            mock_response.raise_for_status = MagicMock()
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            info = await client.async_get_server_info()
            assert info["Id"] == "test-server-id-12345"
            assert info["ServerName"] == "Test Emby Server"
            await client.close()

    @pytest.mark.asyncio
    async def test_get_server_info_caches_server_id(
        self, mock_server_info: dict[str, Any]
    ) -> None:
        """Test server ID is cached after retrieval."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(return_value=mock_server_info)
            mock_response.raise_for_status = MagicMock()
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            assert client.server_id is None
            await client.async_get_server_info()
            assert client.server_id == "test-server-id-12345"
            await client.close()


class TestGetPublicInfo:
    """Test public server info retrieval."""

    @pytest.mark.asyncio
    async def test_get_public_info_success(
        self, mock_public_info: dict[str, Any]
    ) -> None:
        """Test successful public info retrieval."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(return_value=mock_public_info)
            mock_response.raise_for_status = MagicMock()
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            info = await client.async_get_public_info()
            assert info["Id"] == "test-server-id-12345"
            await client.close()

    @pytest.mark.asyncio
    async def test_get_public_info_no_auth(
        self, mock_public_info: dict[str, Any]
    ) -> None:
        """Test public info request doesn't include auth header."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(return_value=mock_public_info)
            mock_response.raise_for_status = MagicMock()
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            await client.async_get_public_info()

            # Check headers in the request call
            call_args = mock_session.request.call_args
            headers = call_args.kwargs.get("headers", {})
            assert "X-Emby-Token" not in headers
            await client.close()


class TestGetUsers:
    """Test user list retrieval."""

    @pytest.mark.asyncio
    async def test_get_users_success(self, mock_users: list[dict[str, Any]]) -> None:
        """Test successful user list retrieval."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(return_value=mock_users)
            mock_response.raise_for_status = MagicMock()
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            users = await client.async_get_users()
            assert len(users) == 1
            assert users[0]["Name"] == "TestUser"
            await client.close()

    @pytest.mark.asyncio
    async def test_get_users_empty(self) -> None:
        """Test empty user list handled."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(return_value=[])
            mock_response.raise_for_status = MagicMock()
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            users = await client.async_get_users()
            assert users == []
            await client.close()


class TestGetSessions:
    """Test session list retrieval."""

    @pytest.mark.asyncio
    async def test_get_sessions_success(self) -> None:
        """Test successful sessions retrieval."""
        mock_sessions = [
            {
                "Id": "session-1",
                "Client": "Emby Theater",
                "DeviceId": "device-abc",
                "DeviceName": "Living Room TV",
                "SupportsRemoteControl": True,
            },
            {
                "Id": "session-2",
                "Client": "Emby Mobile",
                "DeviceId": "device-def",
                "DeviceName": "Phone",
                "SupportsRemoteControl": True,
            },
        ]
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(return_value=mock_sessions)
            mock_response.raise_for_status = MagicMock()
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            sessions = await client.async_get_sessions()
            assert len(sessions) == 2
            assert sessions[0]["DeviceName"] == "Living Room TV"
            assert sessions[1]["Client"] == "Emby Mobile"
            await client.close()

    @pytest.mark.asyncio
    async def test_get_sessions_empty(self) -> None:
        """Test empty sessions list handled."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(return_value=[])
            mock_response.raise_for_status = MagicMock()
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            sessions = await client.async_get_sessions()
            assert sessions == []
            await client.close()

    @pytest.mark.asyncio
    async def test_get_sessions_auth_error(self) -> None:
        """Test authentication error when getting sessions."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 401
            mock_response.reason = "Unauthorized"
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="bad-key",
            )
            with pytest.raises(EmbyAuthenticationError):
                await client.async_get_sessions()
            await client.close()


class TestHttpErrors:
    """Test HTTP error handling."""

    @pytest.mark.asyncio
    async def test_server_error_500(self) -> None:
        """Test 500 response raises EmbyServerError."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 500
            mock_response.reason = "Internal Server Error"
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            with pytest.raises(EmbyServerError):
                await client.async_validate_connection()
            await client.close()

    @pytest.mark.asyncio
    async def test_not_found_404(self) -> None:
        """Test 404 response raises EmbyNotFoundError."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 404
            mock_response.reason = "Not Found"
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            with pytest.raises(EmbyNotFoundError):
                await client.async_validate_connection()
            await client.close()


class TestClientResponseError:
    """Test ClientResponseError handling in exception handler."""

    @pytest.mark.asyncio
    async def test_client_response_error_401(self) -> None:
        """Test ClientResponseError with 401 raises auth error."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.request = MagicMock(
                side_effect=aiohttp.ClientResponseError(
                    request_info=MagicMock(),
                    history=(),
                    status=401,
                    message="Unauthorized",
                )
            )
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            with pytest.raises(EmbyAuthenticationError):
                await client.async_validate_connection()
            await client.close()

    @pytest.mark.asyncio
    async def test_client_response_error_404(self) -> None:
        """Test ClientResponseError with 404 raises not found error."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.request = MagicMock(
                side_effect=aiohttp.ClientResponseError(
                    request_info=MagicMock(),
                    history=(),
                    status=404,
                    message="Not Found",
                )
            )
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            with pytest.raises(EmbyNotFoundError):
                await client.async_validate_connection()
            await client.close()

    @pytest.mark.asyncio
    async def test_client_response_error_500(self) -> None:
        """Test ClientResponseError with 500 raises server error."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.request = MagicMock(
                side_effect=aiohttp.ClientResponseError(
                    request_info=MagicMock(),
                    history=(),
                    status=500,
                    message="Internal Server Error",
                )
            )
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            with pytest.raises(EmbyServerError):
                await client.async_validate_connection()
            await client.close()

    @pytest.mark.asyncio
    async def test_client_response_error_other(self) -> None:
        """Test ClientResponseError with other status raises connection error."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.request = MagicMock(
                side_effect=aiohttp.ClientResponseError(
                    request_info=MagicMock(),
                    history=(),
                    status=400,
                    message="Bad Request",
                )
            )
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            with pytest.raises(EmbyConnectionError):
                await client.async_validate_connection()
            await client.close()


class TestClientError:
    """Test generic ClientError handling."""

    @pytest.mark.asyncio
    async def test_client_error_raises_connection_error(self) -> None:
        """Test ClientError raises EmbyConnectionError."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.request = MagicMock(
                side_effect=aiohttp.ClientError("Generic client error")
            )
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            with pytest.raises(EmbyConnectionError):
                await client.async_validate_connection()
            await client.close()


class TestSslContext:
    """Test SSL context generation."""

    def test_ssl_enabled_verify_disabled(self) -> None:
        """Test SSL context when SSL enabled but verify disabled."""
        client = EmbyClient(
            host="emby.local",
            port=8920,
            api_key="test-key",
            ssl=True,
            verify_ssl=False,
        )
        ssl_context = client._get_ssl_context()
        assert ssl_context is False


class TestSessionManagement:
    """Test session management."""

    @pytest.mark.asyncio
    async def test_session_created_if_not_provided(self) -> None:
        """Test new session created when none provided."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-key",
        )
        assert client._session is None
        assert client._owns_session is True

    @pytest.mark.asyncio
    async def test_session_not_closed_if_external(self) -> None:
        """Test external session not closed."""
        external_session = MagicMock()
        external_session.closed = False
        external_session.close = AsyncMock()

        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-key",
            session=external_session,
        )
        assert client._owns_session is False
        await client.close()
        external_session.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_session_closed_if_internal(self) -> None:
        """Test internal session closed on close()."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            # Force session creation
            await client._get_session()
            assert client._owns_session is True
            await client.close()
            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_context_manager(
        self, mock_server_info: dict[str, Any]
    ) -> None:
        """Test context manager works correctly."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(return_value=mock_server_info)
            mock_response.raise_for_status = MagicMock()
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            async with EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            ) as client:
                info = await client.async_get_server_info()
                assert info["ServerName"] == "Test Emby Server"


class TestTickConversion:
    """Test tick conversion utilities."""

    def test_ticks_to_seconds(self) -> None:
        """Test tick to seconds conversion accuracy."""
        assert ticks_to_seconds(EMBY_TICKS_PER_SECOND) == 1.0
        assert ticks_to_seconds(EMBY_TICKS_PER_SECOND * 60) == 60.0
        assert ticks_to_seconds(EMBY_TICKS_PER_SECOND * 3600) == 3600.0

    def test_ticks_to_seconds_zero(self) -> None:
        """Test zero ticks returns zero."""
        assert ticks_to_seconds(0) == 0.0

    def test_ticks_to_seconds_fractional(self) -> None:
        """Test fractional seconds conversion."""
        assert ticks_to_seconds(5_000_000) == 0.5
        assert ticks_to_seconds(2_500_000) == 0.25

    def test_ticks_to_seconds_negative(self) -> None:
        """Test negative ticks handled."""
        assert ticks_to_seconds(-EMBY_TICKS_PER_SECOND) == -1.0

    def test_seconds_to_ticks(self) -> None:
        """Test seconds to ticks conversion accuracy."""
        assert seconds_to_ticks(1.0) == EMBY_TICKS_PER_SECOND
        assert seconds_to_ticks(60.0) == EMBY_TICKS_PER_SECOND * 60
        assert seconds_to_ticks(3600.0) == EMBY_TICKS_PER_SECOND * 3600

    def test_seconds_to_ticks_zero(self) -> None:
        """Test zero seconds returns zero."""
        assert seconds_to_ticks(0.0) == 0

    def test_seconds_to_ticks_fractional(self) -> None:
        """Test fractional seconds handled."""
        assert seconds_to_ticks(0.5) == 5_000_000
        assert seconds_to_ticks(0.25) == 2_500_000

    def test_ticks_conversion_roundtrip(self) -> None:
        """Test roundtrip conversion preserves value."""
        original = 123456789
        converted = seconds_to_ticks(ticks_to_seconds(original))
        assert converted == original

        original_seconds = 123.456
        converted_seconds = ticks_to_seconds(seconds_to_ticks(original_seconds))
        assert abs(converted_seconds - original_seconds) < 0.0001
