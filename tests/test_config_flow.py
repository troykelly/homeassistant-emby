"""Tests for Emby config flow."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.emby.const import (
    CONF_API_KEY,
    CONF_VERIFY_SSL,
    DOMAIN,
)
from custom_components.emby.exceptions import (
    EmbyAuthenticationError,
    EmbyConnectionError,
    EmbySSLError,
    EmbyTimeoutError,
)


class TestConfigFlow:
    """Test config flow."""

    @pytest.mark.asyncio
    async def test_form_displayed(self, hass: HomeAssistant) -> None:
        """Test form is displayed on initial step."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {}

    @pytest.mark.asyncio
    async def test_successful_config(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test full flow completes successfully."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "Test Emby Server"
        assert result["data"][CONF_HOST] == "emby.local"
        assert result["data"][CONF_PORT] == 8096
        assert result["data"][CONF_API_KEY] == "test-api-key"

    @pytest.mark.asyncio
    async def test_connection_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test connection error shows message."""
        with patch(
            "custom_components.emby.config_flow.EmbyClient"
        ) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(
                side_effect=EmbyConnectionError("Connection refused")
            )

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_HOST: "emby.local",
                    CONF_PORT: 8096,
                    CONF_SSL: False,
                    CONF_API_KEY: "test-api-key",
                    CONF_VERIFY_SSL: True,
                },
            )

            assert result["type"] is FlowResultType.FORM
            assert result["errors"]["base"] == "cannot_connect"

    @pytest.mark.asyncio
    async def test_auth_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test auth error shows message."""
        with patch(
            "custom_components.emby.config_flow.EmbyClient"
        ) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(
                side_effect=EmbyAuthenticationError("Invalid API key")
            )

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_HOST: "emby.local",
                    CONF_PORT: 8096,
                    CONF_SSL: False,
                    CONF_API_KEY: "bad-api-key",
                    CONF_VERIFY_SSL: True,
                },
            )

            assert result["type"] is FlowResultType.FORM
            assert result["errors"]["base"] == "invalid_auth"

    @pytest.mark.asyncio
    async def test_timeout_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test timeout error shows message."""
        with patch(
            "custom_components.emby.config_flow.EmbyClient"
        ) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(
                side_effect=EmbyTimeoutError("Request timed out")
            )

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_HOST: "emby.local",
                    CONF_PORT: 8096,
                    CONF_SSL: False,
                    CONF_API_KEY: "test-api-key",
                    CONF_VERIFY_SSL: True,
                },
            )

            assert result["type"] is FlowResultType.FORM
            assert result["errors"]["base"] == "timeout"

    @pytest.mark.asyncio
    async def test_ssl_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test SSL error shows message."""
        with patch(
            "custom_components.emby.config_flow.EmbyClient"
        ) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(
                side_effect=EmbySSLError("SSL certificate verification failed")
            )

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_HOST: "emby.local",
                    CONF_PORT: 8920,
                    CONF_SSL: True,
                    CONF_API_KEY: "test-api-key",
                    CONF_VERIFY_SSL: True,
                },
            )

            assert result["type"] is FlowResultType.FORM
            assert result["errors"]["base"] == "ssl_error"

    @pytest.mark.asyncio
    async def test_unknown_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test unknown error handled gracefully."""
        with patch(
            "custom_components.emby.config_flow.EmbyClient"
        ) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(
                side_effect=RuntimeError("Unexpected error")
            )

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_HOST: "emby.local",
                    CONF_PORT: 8096,
                    CONF_SSL: False,
                    CONF_API_KEY: "test-api-key",
                    CONF_VERIFY_SSL: True,
                },
            )

            assert result["type"] is FlowResultType.FORM
            assert result["errors"]["base"] == "unknown"

    @pytest.mark.asyncio
    async def test_duplicate_server(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test duplicate server aborts."""
        mock_config_entry.add_to_hass(hass)

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"

    @pytest.mark.asyncio
    async def test_invalid_host_empty(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test empty host shows error."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"][CONF_HOST] == "invalid_host"

    @pytest.mark.asyncio
    async def test_host_normalization(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test protocol prefix removed from host."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "https://emby.local/",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_HOST] == "emby.local"

    @pytest.mark.asyncio
    async def test_version_check_supported(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test supported version accepted."""
        with patch(
            "custom_components.emby.config_flow.EmbyClient"
        ) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "server-123",
                    "ServerName": "Test Server",
                    "Version": "4.8.0.0",
                }
            )

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_HOST: "emby.local",
                    CONF_PORT: 8096,
                    CONF_SSL: False,
                    CONF_API_KEY: "test-api-key",
                    CONF_VERIFY_SSL: True,
                },
            )

            assert result["type"] is FlowResultType.CREATE_ENTRY

    @pytest.mark.asyncio
    async def test_version_check_unsupported(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test unsupported version rejected."""
        with patch(
            "custom_components.emby.config_flow.EmbyClient"
        ) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "server-123",
                    "ServerName": "Test Server",
                    "Version": "4.6.0.0",
                }
            )

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_HOST: "emby.local",
                    CONF_PORT: 8096,
                    CONF_SSL: False,
                    CONF_API_KEY: "test-api-key",
                    CONF_VERIFY_SSL: True,
                },
            )

            assert result["type"] is FlowResultType.FORM
            assert result["errors"]["base"] == "unsupported_version"

    @pytest.mark.asyncio
    async def test_version_check_higher_major_supported(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test higher major version accepted."""
        with patch(
            "custom_components.emby.config_flow.EmbyClient"
        ) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "server-123",
                    "ServerName": "Test Server",
                    "Version": "5.0.0.0",  # Higher major version
                }
            )

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_HOST: "emby.local",
                    CONF_PORT: 8096,
                    CONF_SSL: False,
                    CONF_API_KEY: "test-api-key",
                    CONF_VERIFY_SSL: True,
                },
            )

            assert result["type"] is FlowResultType.CREATE_ENTRY

    @pytest.mark.asyncio
    async def test_version_check_invalid_version_allowed(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test invalid version string is allowed (returns True)."""
        with patch(
            "custom_components.emby.config_flow.EmbyClient"
        ) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "server-123",
                    "ServerName": "Test Server",
                    "Version": "invalid",  # Invalid version string
                }
            )

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_HOST: "emby.local",
                    CONF_PORT: 8096,
                    CONF_SSL: False,
                    CONF_API_KEY: "test-api-key",
                    CONF_VERIFY_SSL: True,
                },
            )

            # Invalid versions are allowed to pass
            assert result["type"] is FlowResultType.CREATE_ENTRY

    @pytest.mark.asyncio
    async def test_invalid_api_key_empty(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test empty API key shows error."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "   ",  # Whitespace only
                CONF_VERIFY_SSL: True,
            },
        )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"][CONF_API_KEY] == "invalid_auth"


class TestValidateInput:
    """Test input validation directly."""

    @pytest.mark.asyncio
    async def test_invalid_port_zero(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test port value of 0 shows error."""
        # Create flow instance manually to test _validate_input directly
        from custom_components.emby.config_flow import EmbyConfigFlow

        flow = EmbyConfigFlow()
        flow.hass = hass

        # Test with port 0 (should fail validation)
        user_input = {
            "host": "emby.local",
            "port": 0,  # Invalid port
            "ssl": False,
            "api_key": "valid-key",
            "verify_ssl": True,
        }
        errors = flow._validate_input(user_input)
        assert errors.get("port") == "invalid_port"

    @pytest.mark.asyncio
    async def test_create_entry_without_server_info(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test entry creation uses fallback when server_info is None."""
        from custom_components.emby.config_flow import EmbyConfigFlow

        flow = EmbyConfigFlow()
        flow.hass = hass
        flow._server_info = None  # Defensive scenario

        user_input = {
            "host": "emby.local",
            "port": 8096,
            "ssl": False,
            "api_key": "test-key",
            "verify_ssl": True,
        }

        result = await flow._async_create_entry(user_input)
        assert result["title"] == "Emby (emby.local)"


class TestOptionsFlow:
    """Test options flow."""

    @pytest.mark.asyncio
    async def test_options_flow(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test options can be modified."""
        mock_config_entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(
            mock_config_entry.entry_id
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {"scan_interval": 30},
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"]["scan_interval"] == 30

    @pytest.mark.asyncio
    async def test_options_flow_default_values(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test default values populated in options."""
        mock_config_entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(
            mock_config_entry.entry_id
        )

        assert result["type"] is FlowResultType.FORM
        # Default scan interval should be shown
        schema = result["data_schema"]
        assert schema is not None


class TestReauthFlow:
    """Test reauth flow."""

    @pytest.mark.asyncio
    async def test_reauth_flow(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test reauth flow shows form."""
        mock_config_entry.add_to_hass(hass)

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": mock_config_entry.entry_id,
            },
            data=mock_config_entry.data,
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"

    @pytest.mark.asyncio
    async def test_reauth_flow_success(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test successful reauth updates entry."""
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.emby.config_flow.EmbyClient"
        ) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id-12345",
                    "ServerName": "Test Emby Server",
                    "Version": "4.8.0.0",
                }
            )

            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={
                    "source": config_entries.SOURCE_REAUTH,
                    "entry_id": mock_config_entry.entry_id,
                },
                data=mock_config_entry.data,
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_API_KEY: "new-api-key"},
            )

            assert result["type"] is FlowResultType.ABORT
            assert result["reason"] == "reauth_successful"
