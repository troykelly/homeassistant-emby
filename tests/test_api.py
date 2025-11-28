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

    def test_client_properties(self) -> None:
        """Test client exposes properties correctly."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-key",
            ssl=True,
        )
        assert client.host == "emby.local"
        assert client.port == 8096
        assert client.api_key == "test-key"
        assert client.ssl is True


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
    async def test_validate_connection_success(self, mock_server_info: dict[str, Any]) -> None:
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
                side_effect=aiohttp.ClientConnectorError(MagicMock(), OSError("Connection refused"))
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
    async def test_get_server_info_success(self, mock_server_info: dict[str, Any]) -> None:
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
    async def test_get_server_info_caches_server_id(self, mock_server_info: dict[str, Any]) -> None:
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
    async def test_get_public_info_success(self, mock_public_info: dict[str, Any]) -> None:
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
    async def test_get_public_info_no_auth(self, mock_public_info: dict[str, Any]) -> None:
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
    async def test_async_context_manager(self, mock_server_info: dict[str, Any]) -> None:
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


class TestSendPlaybackCommand:
    """Test sending playback commands."""

    @pytest.mark.asyncio
    async def test_send_playback_command_success(self) -> None:
        """Test sending playback command successfully."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 204
            mock_response.reason = "No Content"
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            await client.async_send_playback_command("session-123", "Pause")

            # Verify POST was called with correct endpoint
            mock_session.post.assert_called_once()
            call_args = mock_session.post.call_args
            assert "/Sessions/session-123/Playing/Pause" in str(call_args)
            await client.close()

    @pytest.mark.asyncio
    async def test_send_playback_command_with_args(self) -> None:
        """Test sending playback command with arguments."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 204
            mock_response.reason = "No Content"
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            await client.async_send_playback_command(
                "session-123",
                "Seek",
                {"SeekPositionTicks": 50000000},
            )

            # Verify POST was called
            mock_session.post.assert_called_once()
            call_args = mock_session.post.call_args
            # Verify JSON body contains the seek position
            assert call_args.kwargs.get("json") == {"SeekPositionTicks": 50000000}
            await client.close()


class TestSendCommand:
    """Test sending general commands."""

    @pytest.mark.asyncio
    async def test_send_command_success(self) -> None:
        """Test sending general command successfully."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 204
            mock_response.reason = "No Content"
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            await client.async_send_command("session-123", "Mute")

            # Verify POST was called with correct endpoint
            mock_session.post.assert_called_once()
            call_args = mock_session.post.call_args
            assert "/Sessions/session-123/Command/Mute" in str(call_args)
            await client.close()

    @pytest.mark.asyncio
    async def test_send_command_with_args(self) -> None:
        """Test sending general command with arguments."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 204
            mock_response.reason = "No Content"
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            await client.async_send_command(
                "session-123",
                "SetVolume",
                {"Volume": 50},
            )

            # Verify POST was called
            mock_session.post.assert_called_once()
            call_args = mock_session.post.call_args
            # Verify JSON body contains the volume
            assert call_args.kwargs.get("json") == {"Volume": 50}
            await client.close()

    @pytest.mark.asyncio
    async def test_send_command_auth_error(self) -> None:
        """Test authentication error when sending command."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 401
            mock_response.reason = "Unauthorized"
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="bad-key",
            )
            with pytest.raises(EmbyAuthenticationError):
                await client.async_send_command("session-123", "Mute")
            await client.close()


class TestGetImageUrl:
    """Test image URL generation."""

    def test_get_image_url_basic(self) -> None:
        """Test basic image URL generation."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )
        url = client.get_image_url("item-123")
        assert url == "http://emby.local:8096/Items/item-123/Images/Primary?api_key=test-api-key"

    def test_get_image_url_with_image_type(self) -> None:
        """Test URL generation with different image type."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )
        url = client.get_image_url("item-123", image_type="Backdrop")
        assert "/Images/Backdrop?" in url

    def test_get_image_url_with_max_width(self) -> None:
        """Test URL generation with maxWidth parameter."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )
        url = client.get_image_url("item-123", max_width=300)
        assert "maxWidth=300" in url

    def test_get_image_url_with_max_height(self) -> None:
        """Test URL generation with maxHeight parameter."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )
        url = client.get_image_url("item-123", max_height=400)
        assert "maxHeight=400" in url

    def test_get_image_url_with_tag(self) -> None:
        """Test URL generation with cache tag."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )
        url = client.get_image_url("item-123", tag="abc123def456")
        assert "tag=abc123def456" in url

    def test_get_image_url_with_all_params(self) -> None:
        """Test URL generation with all parameters."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )
        url = client.get_image_url(
            "item-123",
            image_type="Thumb",
            max_width=300,
            max_height=200,
            tag="mytag",
        )
        assert "/Items/item-123/Images/Thumb?" in url
        assert "api_key=test-api-key" in url
        assert "maxWidth=300" in url
        assert "maxHeight=200" in url
        assert "tag=mytag" in url

    def test_get_image_url_with_ssl(self) -> None:
        """Test URL generation with HTTPS."""
        client = EmbyClient(
            host="emby.local",
            port=8920,
            api_key="test-api-key",
            ssl=True,
        )
        url = client.get_image_url("item-123")
        assert url.startswith("https://")

    def test_get_image_url_special_characters_in_item_id(self) -> None:
        """Test URL encoding of special characters in item_id."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )
        # Item IDs shouldn't have special chars but test encoding anyway
        url = client.get_image_url("item/123")
        # The URL should be properly constructed
        assert "Items/item/123/Images/Primary" in url or "Items/item%2F123/Images/Primary" in url


class TestGetUserViews:
    """Test user library views retrieval."""

    @pytest.mark.asyncio
    async def test_get_user_views_success(self) -> None:
        """Test successful user views retrieval."""
        mock_views = {
            "Items": [
                {
                    "Id": "library-movies",
                    "Name": "Movies",
                    "CollectionType": "movies",
                    "ImageTags": {"Primary": "abc123"},
                },
                {
                    "Id": "library-tvshows",
                    "Name": "TV Shows",
                    "CollectionType": "tvshows",
                },
            ],
        }
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(return_value=mock_views)
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
            views = await client.async_get_user_views("user-123")
            assert len(views) == 2
            assert views[0]["Name"] == "Movies"
            assert views[1]["Name"] == "TV Shows"
            await client.close()

    @pytest.mark.asyncio
    async def test_get_user_views_empty(self) -> None:
        """Test empty user views handled."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(return_value={"Items": []})
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
            views = await client.async_get_user_views("user-123")
            assert views == []
            await client.close()


class TestGetItems:
    """Test library items retrieval."""

    @pytest.mark.asyncio
    async def test_get_items_from_library(self) -> None:
        """Test getting items from a library."""
        mock_items = {
            "Items": [
                {
                    "Id": "movie-123",
                    "Name": "Test Movie",
                    "Type": "Movie",
                    "ProductionYear": 2024,
                },
                {
                    "Id": "movie-456",
                    "Name": "Another Movie",
                    "Type": "Movie",
                },
            ],
            "TotalRecordCount": 2,
            "StartIndex": 0,
        }
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(return_value=mock_items)
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
            result = await client.async_get_items("user-123", parent_id="library-movies")
            assert len(result["Items"]) == 2
            assert result["TotalRecordCount"] == 2
            assert result["Items"][0]["Name"] == "Test Movie"
            await client.close()

    @pytest.mark.asyncio
    async def test_get_items_with_type_filter(self) -> None:
        """Test getting items with type filter."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(
                return_value={"Items": [], "TotalRecordCount": 0, "StartIndex": 0}
            )
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
            await client.async_get_items(
                "user-123",
                parent_id="library-123",
                include_item_types="Movie",
            )

            # Verify the query params include IncludeItemTypes
            call_args = mock_session.request.call_args
            assert "IncludeItemTypes" in str(call_args)
            await client.close()

    @pytest.mark.asyncio
    async def test_get_items_pagination(self) -> None:
        """Test pagination support."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(
                return_value={"Items": [], "TotalRecordCount": 100, "StartIndex": 50}
            )
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
            result = await client.async_get_items(
                "user-123",
                limit=25,
                start_index=50,
            )
            assert result["StartIndex"] == 50
            await client.close()

    @pytest.mark.asyncio
    async def test_get_items_recursive(self) -> None:
        """Test recursive browsing."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(
                return_value={"Items": [], "TotalRecordCount": 0, "StartIndex": 0}
            )
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
            await client.async_get_items(
                "user-123",
                parent_id="library-123",
                recursive=True,
            )

            # Verify the query params include Recursive
            call_args = mock_session.request.call_args
            assert "Recursive=true" in str(call_args)
            await client.close()

    @pytest.mark.asyncio
    async def test_get_items_name_starts_with(self) -> None:
        """Test name_starts_with filtering."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(
                return_value={"Items": [], "TotalRecordCount": 0, "StartIndex": 0}
            )
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
            await client.async_get_items(
                "user-123",
                parent_id="library-123",
                include_item_types="MusicArtist",
                name_starts_with="A",
            )

            # Verify the query params include NameStartsWith
            call_args = mock_session.request.call_args
            assert "NameStartsWith=A" in str(call_args)
            await client.close()

    @pytest.mark.asyncio
    async def test_get_items_with_years_filter(self) -> None:
        """Test years filtering."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(
                return_value={"Items": [], "TotalRecordCount": 0, "StartIndex": 0}
            )
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
            await client.async_get_items(
                "user-123",
                parent_id="library-123",
                include_item_types="Movie",
                years="2023",
            )

            # Verify the query params include Years
            call_args = mock_session.request.call_args
            assert "Years=2023" in str(call_args)
            await client.close()

    @pytest.mark.asyncio
    async def test_get_items_with_genre_ids_filter(self) -> None:
        """Test genre_ids filtering."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(
                return_value={"Items": [], "TotalRecordCount": 0, "StartIndex": 0}
            )
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
            await client.async_get_items(
                "user-123",
                parent_id="library-123",
                include_item_types="Movie",
                genre_ids="genre-action-123",
            )

            # Verify the query params include GenreIds
            call_args = mock_session.request.call_args
            assert "GenreIds=genre-action-123" in str(call_args)
            await client.close()


class TestGetMusicGenres:
    """Test music genres retrieval."""

    @pytest.mark.asyncio
    async def test_get_music_genres_success(self) -> None:
        """Test successful music genres retrieval."""
        mock_genres = {
            "Items": [
                {"Id": "genre-1", "Name": "Rock"},
                {"Id": "genre-2", "Name": "Jazz"},
            ],
            "TotalRecordCount": 2,
        }

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(return_value=mock_genres)
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
            result = await client.async_get_music_genres("user-123", "library-123")

            assert len(result) == 2
            assert result[0]["Name"] == "Rock"
            assert result[1]["Name"] == "Jazz"
            await client.close()


class TestSearchItems:
    """Test search functionality."""

    @pytest.mark.asyncio
    async def test_search_items_success(self) -> None:
        """Test successful search query."""
        mock_search_results = {
            "Items": [
                {"Id": "ep-1", "Name": "X Files S1E12", "Type": "Episode"},
                {"Id": "ep-2", "Name": "X Files S2E5", "Type": "Episode"},
            ],
            "TotalRecordCount": 2,
            "StartIndex": 0,
        }

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(return_value=mock_search_results)
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
            result = await client.async_search_items("user-123", "X Files Season 1 Episode 12")

            assert len(result) == 2
            assert result[0]["Name"] == "X Files S1E12"

            # Verify the API was called with search term
            call_args = mock_session.request.call_args
            assert "SearchTerm=" in str(call_args)
            await client.close()

    @pytest.mark.asyncio
    async def test_search_items_with_type_filter(self) -> None:
        """Test search with item type filter."""
        mock_search_results = {
            "Items": [{"Id": "ep-1", "Name": "Test Episode", "Type": "Episode"}],
            "TotalRecordCount": 1,
            "StartIndex": 0,
        }

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(return_value=mock_search_results)
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
            await client.async_search_items("user-123", "Test", include_item_types="Episode,Movie")

            call_args = mock_session.request.call_args
            assert "IncludeItemTypes=Episode%2CMovie" in str(call_args)
            await client.close()


class TestGetSeasons:
    """Test TV show seasons retrieval."""

    @pytest.mark.asyncio
    async def test_get_seasons_success(self) -> None:
        """Test successful seasons retrieval."""
        mock_seasons = {
            "Items": [
                {"Id": "season-1", "Name": "Season 1", "IndexNumber": 1},
                {"Id": "season-2", "Name": "Season 2", "IndexNumber": 2},
            ],
        }
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(return_value=mock_seasons)
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
            seasons = await client.async_get_seasons("user-123", "series-abc")
            assert len(seasons) == 2
            assert seasons[0]["Name"] == "Season 1"
            await client.close()


class TestGetEpisodes:
    """Test TV show episodes retrieval."""

    @pytest.mark.asyncio
    async def test_get_episodes_by_season(self) -> None:
        """Test getting episodes for a season."""
        mock_episodes = {
            "Items": [
                {"Id": "ep-1", "Name": "Episode 1", "IndexNumber": 1},
                {"Id": "ep-2", "Name": "Episode 2", "IndexNumber": 2},
            ],
        }
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(return_value=mock_episodes)
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
            episodes = await client.async_get_episodes("user-123", "series-abc", "season-1")
            assert len(episodes) == 2
            assert episodes[0]["Name"] == "Episode 1"
            await client.close()


class TestGetArtistAlbums:
    """Test music artist album retrieval."""

    @pytest.mark.asyncio
    async def test_get_artist_albums(self) -> None:
        """Test getting albums for an artist."""
        mock_albums = {
            "Items": [
                {"Id": "album-1", "Name": "Album 1", "Type": "MusicAlbum"},
                {"Id": "album-2", "Name": "Album 2", "Type": "MusicAlbum"},
            ],
        }
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(return_value=mock_albums)
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
            albums = await client.async_get_artist_albums("user-123", "artist-xyz")
            assert len(albums) == 2
            assert albums[0]["Name"] == "Album 1"
            assert albums[0]["Type"] == "MusicAlbum"

            # Verify endpoint includes correct query params
            call_args = mock_session.request.call_args
            assert "ArtistIds=artist-xyz" in str(call_args)
            assert "IncludeItemTypes=MusicAlbum" in str(call_args)
            await client.close()


class TestGetAlbumTracks:
    """Test music album track retrieval."""

    @pytest.mark.asyncio
    async def test_get_album_tracks(self) -> None:
        """Test getting tracks for an album."""
        mock_tracks = {
            "Items": [
                {"Id": "track-1", "Name": "Track 1", "Type": "Audio", "IndexNumber": 1},
                {"Id": "track-2", "Name": "Track 2", "Type": "Audio", "IndexNumber": 2},
            ],
        }
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(return_value=mock_tracks)
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
            tracks = await client.async_get_album_tracks("user-123", "album-xyz")
            assert len(tracks) == 2
            assert tracks[0]["Name"] == "Track 1"
            assert tracks[0]["Type"] == "Audio"

            # Verify endpoint includes correct query params
            call_args = mock_session.request.call_args
            assert "ParentId=album-xyz" in str(call_args)
            assert "IncludeItemTypes=Audio" in str(call_args)
            await client.close()


class TestGetPlaylistItems:
    """Test playlist items retrieval."""

    @pytest.mark.asyncio
    async def test_get_playlist_items(self) -> None:
        """Test getting items from a playlist."""
        mock_items = {
            "Items": [
                {"Id": "track-1", "Name": "Track 1", "Type": "Audio"},
                {"Id": "movie-1", "Name": "Movie 1", "Type": "Movie"},
            ],
        }
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(return_value=mock_items)
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
            items = await client.async_get_playlist_items("user-123", "playlist-xyz")
            assert len(items) == 2
            assert items[0]["Name"] == "Track 1"
            assert items[1]["Name"] == "Movie 1"

            # Verify endpoint includes correct path
            call_args = mock_session.request.call_args
            assert "/Playlists/playlist-xyz/Items" in str(call_args)
            await client.close()


class TestSendGeneralCommand:
    """Test general command sending."""

    @pytest.mark.asyncio
    async def test_send_general_command_with_args(self) -> None:
        """Test sending general command with arguments."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 204
            mock_response.reason = "No Content"
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            await client.async_send_general_command(
                "session-123",
                "SetRepeatMode",
                {"RepeatMode": "RepeatAll"},
            )

            # Verify the POST was called with correct endpoint
            mock_session.post.assert_called_once()
            call_args = mock_session.post.call_args
            assert "/Sessions/session-123/Command" in str(call_args)
            await client.close()

    @pytest.mark.asyncio
    async def test_send_general_command_without_args(self) -> None:
        """Test sending general command without arguments."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 204
            mock_response.reason = "No Content"
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            await client.async_send_general_command(
                "session-123",
                "ToggleMute",
                None,
            )

            mock_session.post.assert_called_once()
            call_args = mock_session.post.call_args
            assert "/Sessions/session-123/Command" in str(call_args)
            await client.close()


class TestGetCollectionItems:
    """Test collection (BoxSet) items retrieval."""

    @pytest.mark.asyncio
    async def test_get_collection_items(self) -> None:
        """Test getting items from a collection."""
        mock_items = {
            "Items": [
                {"Id": "movie-1", "Name": "Movie 1", "Type": "Movie"},
                {"Id": "movie-2", "Name": "Movie 2", "Type": "Movie"},
            ],
        }
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(return_value=mock_items)
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
            items = await client.async_get_collection_items("user-123", "collection-xyz")
            assert len(items) == 2
            assert items[0]["Name"] == "Movie 1"

            # Verify endpoint includes correct params
            call_args = mock_session.request.call_args
            assert "ParentId=collection-xyz" in str(call_args)
            await client.close()


class TestGetLiveTvChannels:
    """Test Live TV channels retrieval."""

    @pytest.mark.asyncio
    async def test_get_live_tv_channels(self) -> None:
        """Test getting Live TV channels."""
        mock_channels = {
            "Items": [
                {"Id": "ch-1", "Name": "Channel 1", "Type": "TvChannel"},
                {"Id": "ch-2", "Name": "Channel 2", "Type": "TvChannel"},
            ],
        }
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.json = AsyncMock(return_value=mock_channels)
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
            channels = await client.async_get_live_tv_channels("user-123")
            assert len(channels) == 2
            assert channels[0]["Name"] == "Channel 1"
            assert channels[0]["Type"] == "TvChannel"

            # Verify endpoint
            call_args = mock_session.request.call_args
            assert "/LiveTv/Channels" in str(call_args)
            await client.close()


class TestPlayItems:
    """Test play items on session."""

    @pytest.mark.asyncio
    async def test_play_items_single(self) -> None:
        """Test playing a single item."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 204
            mock_response.reason = "No Content"
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            await client.async_play_items("session-123", ["movie-456"])

            # Verify POST was called with correct endpoint
            mock_session.post.assert_called_once()
            call_args = mock_session.post.call_args
            assert "/Sessions/session-123/Playing" in str(call_args)
            await client.close()

    @pytest.mark.asyncio
    async def test_play_items_multiple(self) -> None:
        """Test playing multiple items."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 204
            mock_response.reason = "No Content"
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            await client.async_play_items("session-123", ["movie-1", "movie-2", "movie-3"])

            call_args = mock_session.post.call_args
            json_body = call_args.kwargs.get("json", {})
            assert "movie-1,movie-2,movie-3" in json_body.get("ItemIds", "")
            await client.close()


class TestRequestPostErrors:
    """Test POST request error handling."""

    @pytest.mark.asyncio
    async def test_request_post_ssl_error(self) -> None:
        """Test SSL error in POST request."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            ssl_error = OSError("SSL certificate verify failed")
            mock_session.post = MagicMock(
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
                await client.async_send_command("session-123", "Mute")
            await client.close()

    @pytest.mark.asyncio
    async def test_request_post_timeout(self) -> None:
        """Test timeout in POST request."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.post = MagicMock(side_effect=TimeoutError())
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            with pytest.raises(EmbyTimeoutError):
                await client.async_send_command("session-123", "Mute")
            await client.close()

    @pytest.mark.asyncio
    async def test_request_post_connection_error(self) -> None:
        """Test connection error in POST request."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.post = MagicMock(
                side_effect=aiohttp.ClientConnectorError(MagicMock(), OSError("Connection refused"))
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
                await client.async_send_command("session-123", "Mute")
            await client.close()

    @pytest.mark.asyncio
    async def test_request_post_client_error(self) -> None:
        """Test generic client error in POST request."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.post = MagicMock(side_effect=aiohttp.ClientError("Generic error"))
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            with pytest.raises(EmbyConnectionError):
                await client.async_send_command("session-123", "Mute")
            await client.close()

    @pytest.mark.asyncio
    async def test_request_post_raises_for_status(self) -> None:
        """Test non-204 success status calls raise_for_status."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.reason = "OK"
            mock_response.raise_for_status = MagicMock()
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            await client.async_send_command("session-123", "Mute")

            mock_response.raise_for_status.assert_called_once()
            await client.close()


class TestStreamUrls:
    """Test stream URL generation for media source."""

    def test_get_video_stream_url_direct(self) -> None:
        """Test video stream URL with direct play."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )
        url = client.get_video_stream_url("video-123")
        assert "emby.local:8096" in url
        assert "/Videos/video-123/stream" in url
        assert "api_key=test-api-key" in url
        assert "Static=true" in url
        assert "Container=mp4" in url

    def test_get_video_stream_url_transcode(self) -> None:
        """Test video stream URL with transcoding parameters."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )
        url = client.get_video_stream_url(
            "video-123",
            container="mkv",
            static=False,
            video_codec="h264",
            audio_codec="aac",
            max_width=1920,
            max_height=1080,
        )
        assert "Container=mkv" in url
        assert "Static=false" in url
        assert "VideoCodec=h264" in url
        assert "AudioCodec=aac" in url
        assert "MaxWidth=1920" in url
        assert "MaxHeight=1080" in url

    def test_get_video_stream_url_with_audio_subtitle_index(self) -> None:
        """Test video stream URL with audio and subtitle stream indices."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )
        url = client.get_video_stream_url(
            "video-123",
            audio_stream_index=1,
            subtitle_stream_index=2,
        )
        assert "AudioStreamIndex=1" in url
        assert "SubtitleStreamIndex=2" in url

    def test_get_audio_stream_url_direct(self) -> None:
        """Test audio stream URL with direct play."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )
        url = client.get_audio_stream_url("audio-123")
        assert "emby.local:8096" in url
        assert "/Audio/audio-123/stream" in url
        assert "api_key=test-api-key" in url
        assert "Static=true" in url
        assert "Container=mp3" in url

    def test_get_audio_stream_url_transcode(self) -> None:
        """Test audio stream URL with transcoding."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )
        url = client.get_audio_stream_url(
            "audio-123",
            container="flac",
            static=False,
            audio_codec="flac",
            max_bitrate=320000,
        )
        assert "Container=flac" in url
        assert "Static=false" in url
        assert "AudioCodec=flac" in url
        assert "MaxAudioBitRate=320000" in url

    def test_get_hls_url(self) -> None:
        """Test HLS adaptive streaming URL generation."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )
        url = client.get_hls_url("video-123")
        assert "emby.local:8096" in url
        assert "/Videos/video-123/master.m3u8" in url
        assert "api_key=test-api-key" in url

    def test_stream_urls_with_ssl(self) -> None:
        """Test stream URLs with HTTPS."""
        client = EmbyClient(
            host="emby.local",
            port=8920,
            api_key="test-api-key",
            ssl=True,
        )
        video_url = client.get_video_stream_url("video-123")
        audio_url = client.get_audio_stream_url("audio-123")
        hls_url = client.get_hls_url("video-123")

        assert video_url.startswith("https://")
        assert audio_url.startswith("https://")
        assert hls_url.startswith("https://")

    def test_get_user_image_url_basic(self) -> None:
        """Test user image URL generation with basic parameters."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )
        url = client.get_user_image_url("user-123")
        assert "emby.local:8096" in url
        assert "/Users/user-123/Images/Primary" in url
        assert "api_key=test-api-key" in url

    def test_get_user_image_url_with_tag(self) -> None:
        """Test user image URL with cache tag."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )
        url = client.get_user_image_url("user-123", image_tag="abc123")
        assert "tag=abc123" in url

    def test_get_user_image_url_with_dimensions(self) -> None:
        """Test user image URL with size constraints."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )
        url = client.get_user_image_url(
            "user-123",
            max_width=100,
            max_height=100,
        )
        assert "maxWidth=100" in url
        assert "maxHeight=100" in url

    def test_get_user_image_url_with_ssl(self) -> None:
        """Test user image URL with HTTPS."""
        client = EmbyClient(
            host="emby.local",
            port=8920,
            api_key="test-api-key",
            ssl=True,
        )
        url = client.get_user_image_url("user-123")
        assert url.startswith("https://")


class TestBrowseCacheIntegration:
    """Tests for browse cache integration in API client."""

    def test_client_has_browse_cache(self) -> None:
        """Test that client has a browse cache."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )
        assert client.browse_cache is not None
        assert client.browse_cache._ttl == 300.0  # 5 minutes
        assert client.browse_cache._max_entries == 500

    def test_clear_browse_cache(self) -> None:
        """Test clearing the browse cache."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )
        # Add something to cache
        client.browse_cache.set("test_key", {"data": "value"})
        assert client.browse_cache.get("test_key") is not None

        # Clear the cache
        client.clear_browse_cache()
        assert client.browse_cache.get("test_key") is None

    @pytest.mark.asyncio
    async def test_async_get_genres_uses_cache(self) -> None:
        """Test that async_get_genres uses caching."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )

        mock_response = {
            "Items": [
                {"Id": "genre-1", "Name": "Action"},
                {"Id": "genre-2", "Name": "Comedy"},
            ]
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            # First call should hit API (with include_item_types)
            result1 = await client.async_get_genres(
                "user-123", parent_id="lib-1", include_item_types="Movie"
            )
            assert len(result1) == 2
            assert mock_request.call_count == 1

            # Second call should use cache
            result2 = await client.async_get_genres(
                "user-123", parent_id="lib-1", include_item_types="Movie"
            )
            assert result2 == result1
            assert mock_request.call_count == 1  # Still 1, not 2

            # Different params should hit API
            await client.async_get_genres("user-123", parent_id="lib-2")
            assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_async_get_years_uses_cache(self) -> None:
        """Test that async_get_years uses caching."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )

        mock_response = {
            "Items": [
                {"Name": "2024", "Id": "2024"},
                {"Name": "2023", "Id": "2023"},
            ]
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            # First call should hit API (with include_item_types)
            result1 = await client.async_get_years(
                "user-123", parent_id="lib-1", include_item_types="Movie"
            )
            assert len(result1) == 2
            assert mock_request.call_count == 1

            # Second call should use cache
            result2 = await client.async_get_years(
                "user-123", parent_id="lib-1", include_item_types="Movie"
            )
            assert result2 == result1
            assert mock_request.call_count == 1  # Still 1, not 2

    @pytest.mark.asyncio
    async def test_async_get_studios_success(self) -> None:
        """Test that async_get_studios fetches studios list."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )

        mock_response = {
            "Items": [
                {"Id": "studio-1", "Name": "Warner Bros"},
                {"Id": "studio-2", "Name": "Disney"},
            ],
            "TotalRecordCount": 2,
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.async_get_studios(
                "user-123", parent_id="lib-movies", include_item_types="Movie"
            )

            assert len(result) == 2
            assert result[0]["Name"] == "Warner Bros"
            assert result[1]["Name"] == "Disney"
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_get_studios_uses_cache(self) -> None:
        """Test that async_get_studios uses caching."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )

        mock_response = {
            "Items": [{"Id": "studio-1", "Name": "Netflix"}],
            "TotalRecordCount": 1,
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result1 = await client.async_get_studios(
                "user-123", parent_id="lib-1", include_item_types="Movie"
            )
            assert mock_request.call_count == 1

            result2 = await client.async_get_studios(
                "user-123", parent_id="lib-1", include_item_types="Movie"
            )
            assert result2 == result1
            assert mock_request.call_count == 1  # Still 1, cached

    @pytest.mark.asyncio
    async def test_async_get_years_fallback_on_server_error(self) -> None:
        """Test that async_get_years falls back to extracting from items."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )

        # Mock items with ProductionYear field
        mock_items_response = {
            "Items": [
                {"Id": "movie-1", "Name": "Movie 1", "ProductionYear": 2020},
                {"Id": "movie-2", "Name": "Movie 2", "ProductionYear": 2020},
                {"Id": "movie-3", "Name": "Movie 3", "ProductionYear": 2019},
            ],
            "TotalRecordCount": 3,
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            # First call for /Years fails with server error
            mock_request.side_effect = [
                EmbyServerError("500 Internal Server Error"),
                mock_items_response,
            ]

            result = await client.async_get_years(
                "user-123", parent_id="lib-movies", include_item_types="Movie"
            )

            # Should have extracted unique years
            assert len(result) == 2
            year_names = [item["Name"] for item in result]
            assert "2020" in year_names
            assert "2019" in year_names
            # Years should be sorted descending
            assert result[0]["Name"] == "2020"
            assert result[1]["Name"] == "2019"

    @pytest.mark.asyncio
    async def test_async_get_years_fallback_on_empty_result(self) -> None:
        """Test fallback when /Years returns empty."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )

        mock_items_response = {
            "Items": [
                {"Id": "movie-1", "Name": "Movie 1", "ProductionYear": 2023},
            ],
            "TotalRecordCount": 1,
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            # First call returns empty, second call gets items
            mock_request.side_effect = [
                {"Items": [], "TotalRecordCount": 0},
                mock_items_response,
            ]

            result = await client.async_get_years(
                "user-123", parent_id="lib-movies", include_item_types="Movie"
            )

            assert len(result) == 1
            assert result[0]["Name"] == "2023"

    @pytest.mark.asyncio
    async def test_async_get_items_with_studio_ids(self) -> None:
        """Test async_get_items with studio_ids filter."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )

        mock_response = {
            "Items": [{"Id": "movie-1", "Name": "Studio Movie"}],
            "TotalRecordCount": 1,
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await client.async_get_items(
                "user-123",
                parent_id="lib-movies",
                include_item_types="Movie",
                studio_ids="studio-123",
            )

            assert len(result.get("Items", [])) == 1
            # Verify studio_ids was in the request
            call_args = mock_request.call_args
            assert "StudioIds=studio-123" in call_args[0][1]


class TestRemoteControlAPI:
    """Test remote control API methods (Phase 8.2)."""

    @pytest.mark.asyncio
    async def test_send_message_success(self) -> None:
        """Test sending message to session."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )

        with patch.object(client, "_request_post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = None

            await client.async_send_message(
                session_id="session-123",
                text="Test message",
                header="Test Header",
                timeout_ms=5000,
            )

            mock_post.assert_called_once_with(
                "/Sessions/session-123/Message",
                data={
                    "Text": "Test message",
                    "Header": "Test Header",
                    "TimeoutMs": 5000,
                },
            )

    @pytest.mark.asyncio
    async def test_send_message_default_timeout(self) -> None:
        """Test sending message with default timeout."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )

        with patch.object(client, "_request_post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = None

            await client.async_send_message(
                session_id="session-123",
                text="Quick message",
            )

            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[1]["data"]["TimeoutMs"] == 5000  # Default

    @pytest.mark.asyncio
    async def test_send_general_command(self) -> None:
        """Test sending general command to session."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )

        with patch.object(client, "_request_post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = None

            await client.async_send_general_command(
                session_id="session-123",
                command="MoveUp",
            )

            mock_post.assert_called_once_with(
                "/Sessions/session-123/Command",
                data={"Name": "MoveUp"},
            )

    @pytest.mark.asyncio
    async def test_send_general_command_with_args(self) -> None:
        """Test sending general command with arguments."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )

        with patch.object(client, "_request_post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = None

            await client.async_send_general_command(
                session_id="session-123",
                command="DisplayContent",
                args={"ItemId": "item-456"},
            )

            mock_post.assert_called_once_with(
                "/Sessions/session-123/Command",
                data={
                    "Name": "DisplayContent",
                    "Arguments": {"ItemId": "item-456"},
                },
            )


class TestLibraryManagementAPI:
    """Test library management API methods (Phase 8.3)."""

    @pytest.mark.asyncio
    async def test_mark_played(self) -> None:
        """Test marking item as played."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )

        with patch.object(client, "_request_post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = None

            await client.async_mark_played(
                user_id="user-123",
                item_id="item-456",
            )

            mock_post.assert_called_once_with(
                "/Users/user-123/PlayedItems/item-456",
            )

    @pytest.mark.asyncio
    async def test_mark_unplayed(self) -> None:
        """Test marking item as unplayed."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )

        with patch.object(client, "_request_delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = None

            await client.async_mark_unplayed(
                user_id="user-123",
                item_id="item-456",
            )

            mock_delete.assert_called_once_with(
                "/Users/user-123/PlayedItems/item-456",
            )

    @pytest.mark.asyncio
    async def test_add_favorite(self) -> None:
        """Test adding item to favorites."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )

        with patch.object(client, "_request_post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = None

            await client.async_add_favorite(
                user_id="user-123",
                item_id="item-456",
            )

            mock_post.assert_called_once_with(
                "/Users/user-123/FavoriteItems/item-456",
            )

    @pytest.mark.asyncio
    async def test_remove_favorite(self) -> None:
        """Test removing item from favorites."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )

        with patch.object(client, "_request_delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = None

            await client.async_remove_favorite(
                user_id="user-123",
                item_id="item-456",
            )

            mock_delete.assert_called_once_with(
                "/Users/user-123/FavoriteItems/item-456",
            )

    @pytest.mark.asyncio
    async def test_refresh_library(self) -> None:
        """Test triggering full library refresh."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )

        with patch.object(client, "_request_post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = None

            await client.async_refresh_library()

            mock_post.assert_called_once_with("/Library/Refresh")

    @pytest.mark.asyncio
    async def test_refresh_library_specific(self) -> None:
        """Test refreshing specific library."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )

        with patch.object(client, "_request_post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = None

            await client.async_refresh_library(library_id="lib-123")

            mock_post.assert_called_once_with("/Items/lib-123/Refresh")

    @pytest.mark.asyncio
    async def test_refresh_item(self) -> None:
        """Test refreshing item metadata."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )

        with patch.object(client, "_request_post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = None

            await client.async_refresh_item(item_id="item-456")

            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "/Items/item-456/Refresh" in call_args[0][0]


class TestRequestDeleteMethod:
    """Test the _request_delete HTTP method."""

    @pytest.mark.asyncio
    async def test_request_delete_success(self) -> None:
        """Test successful DELETE request."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 204
            mock_response.reason = "No Content"
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.delete = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )

            # This should succeed - async_mark_unplayed uses _request_delete
            await client.async_mark_unplayed(
                user_id="user-123",
                item_id="item-456",
            )

            # Verify delete was called
            mock_session.delete.assert_called()
            await client.close()

    @pytest.mark.asyncio
    async def test_request_delete_auth_error(self) -> None:
        """Test authentication error in DELETE request."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 401
            mock_response.reason = "Unauthorized"
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.delete = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )

            with pytest.raises(EmbyAuthenticationError):
                await client.async_mark_unplayed(
                    user_id="user-123",
                    item_id="item-456",
                )
            await client.close()

    @pytest.mark.asyncio
    async def test_request_delete_ssl_error(self) -> None:
        """Test SSL error in DELETE request."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            ssl_error = OSError("SSL certificate verify failed")
            mock_session.delete = MagicMock(
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
                await client.async_remove_favorite(
                    user_id="user-123",
                    item_id="item-456",
                )
            await client.close()

    @pytest.mark.asyncio
    async def test_request_delete_timeout(self) -> None:
        """Test timeout in DELETE request."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.delete = MagicMock(side_effect=TimeoutError())
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            with pytest.raises(EmbyTimeoutError):
                await client.async_remove_favorite(
                    user_id="user-123",
                    item_id="item-456",
                )
            await client.close()

    @pytest.mark.asyncio
    async def test_request_delete_connection_error(self) -> None:
        """Test connection error in DELETE request."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.delete = MagicMock(
                side_effect=aiohttp.ClientConnectorError(MagicMock(), OSError("Connection refused"))
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
                await client.async_mark_unplayed(
                    user_id="user-123",
                    item_id="item-456",
                )
            await client.close()

    @pytest.mark.asyncio
    async def test_request_delete_client_error(self) -> None:
        """Test generic client error in DELETE request."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.delete = MagicMock(side_effect=aiohttp.ClientError("Generic error"))
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            with pytest.raises(EmbyConnectionError):
                await client.async_mark_unplayed(
                    user_id="user-123",
                    item_id="item-456",
                )
            await client.close()

    @pytest.mark.asyncio
    async def test_request_delete_unexpected_status_code(self) -> None:
        """Test unexpected status code triggers raise_for_status."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 404
            mock_response.reason = "Not Found"
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            # Make raise_for_status raise an error
            mock_response.raise_for_status = MagicMock(
                side_effect=aiohttp.ClientResponseError(
                    MagicMock(),
                    (),
                    status=404,
                    message="Not Found",
                )
            )

            mock_session = MagicMock()
            mock_session.delete = MagicMock(return_value=mock_response)
            mock_session.closed = False
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )

            # ClientResponseError is a ClientError, so it should be wrapped
            with pytest.raises(EmbyConnectionError):
                await client.async_mark_unplayed(
                    user_id="user-123",
                    item_id="item-456",
                )
            await client.close()


class TestSearchValidation:
    """Tests for search term validation in API."""

    @pytest.mark.asyncio
    async def test_search_term_too_long(self) -> None:
        """Test that overly long search terms raise ValueError."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-key",
        )

        long_search = "a" * 201  # MAX_SEARCH_TERM_LENGTH is 200
        with pytest.raises(ValueError) as exc_info:
            await client.async_search_items("user-123", long_search)

        assert "exceeds maximum length" in str(exc_info.value)
        await client.close()

    @pytest.mark.asyncio
    async def test_search_term_empty(self) -> None:
        """Test that empty search terms raise ValueError."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-key",
        )

        with pytest.raises(ValueError) as exc_info:
            await client.async_search_items("user-123", "   ")

        assert "cannot be empty" in str(exc_info.value)
        await client.close()

    @pytest.mark.asyncio
    async def test_search_term_valid_length(self) -> None:
        """Test that valid length search terms work."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"Items": []})
            mock_response.raise_for_status = MagicMock()

            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_session.request = MagicMock(return_value=mock_context)
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = EmbyClient(
                host="emby.local",
                port=8096,
                api_key="test-key",
            )
            # Force session creation
            await client._get_session()

            # Valid 200-character search term (exactly at limit)
            valid_search = "a" * 200
            result = await client.async_search_items("user-123", valid_search)

            # Result is a list of items, should be empty list from our mock
            assert result == []
            await client.close()


class TestInstantMixAPI:
    """Tests for Instant Mix API methods."""

    @pytest.mark.asyncio
    async def test_async_get_instant_mix_success(self) -> None:
        """Test getting instant mix from item returns items."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )

        mock_response = {
            "Items": [
                {"Id": "song1", "Name": "Similar Song 1", "Type": "Audio"},
                {"Id": "song2", "Name": "Similar Song 2", "Type": "Audio"},
            ],
            "TotalRecordCount": 2,
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            items = await client.async_get_instant_mix("user-123", "item-abc", limit=50)

            assert len(items) == 2
            assert items[0]["Id"] == "song1"
            assert items[0]["Name"] == "Similar Song 1"
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert "/Items/item-abc/InstantMix" in call_args[0][1]
            assert "UserId=user-123" in call_args[0][1]
            assert "Limit=50" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_async_get_instant_mix_empty(self) -> None:
        """Test getting instant mix when no results returned."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )

        mock_response = {
            "Items": [],
            "TotalRecordCount": 0,
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            items = await client.async_get_instant_mix("user-123", "item-abc")

            assert items == []

    @pytest.mark.asyncio
    async def test_async_get_instant_mix_custom_limit(self) -> None:
        """Test getting instant mix with custom limit parameter."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )

        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await client.async_get_instant_mix("user-123", "item-abc", limit=200)

            call_args = mock_request.call_args
            assert "Limit=200" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_async_get_instant_mix_default_limit(self) -> None:
        """Test getting instant mix uses default limit of 100."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )

        mock_response = {"Items": [], "TotalRecordCount": 0}

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            await client.async_get_instant_mix("user-123", "item-abc")

            call_args = mock_request.call_args
            assert "Limit=100" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_async_get_instant_mix_not_found(self) -> None:
        """Test getting instant mix when item not found raises error."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = EmbyNotFoundError("Item not found")

            with pytest.raises(EmbyNotFoundError):
                await client.async_get_instant_mix("user-123", "nonexistent-item")

    @pytest.mark.asyncio
    async def test_async_get_artist_instant_mix_success(self) -> None:
        """Test getting instant mix from artist returns items."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )

        mock_response = {
            "Items": [
                {"Id": "song1", "Name": "Artist Song 1", "Type": "Audio"},
                {"Id": "song2", "Name": "Artist Song 2", "Type": "Audio"},
                {"Id": "song3", "Name": "Similar Artist Song", "Type": "Audio"},
            ],
            "TotalRecordCount": 3,
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            items = await client.async_get_artist_instant_mix("user-123", "artist-xyz", limit=75)

            assert len(items) == 3
            assert items[0]["Id"] == "song1"
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert "/Artists/InstantMix" in call_args[0][1]
            assert "UserId=user-123" in call_args[0][1]
            assert "Id=artist-xyz" in call_args[0][1]
            assert "Limit=75" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_async_get_artist_instant_mix_not_found(self) -> None:
        """Test getting artist instant mix when artist not found raises error."""
        client = EmbyClient(
            host="emby.local",
            port=8096,
            api_key="test-api-key",
        )

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = EmbyNotFoundError("Artist not found")

            with pytest.raises(EmbyNotFoundError):
                await client.async_get_artist_instant_mix("user-123", "nonexistent-artist")
