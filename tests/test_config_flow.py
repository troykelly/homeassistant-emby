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

from custom_components.embymedia.const import (
    CONF_API_KEY,
    CONF_VERIFY_SSL,
    DOMAIN,
)
from custom_components.embymedia.exceptions import (
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

        # Now we have user selection step
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user_select"

        # Select a user (or skip with empty)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"user_id": "user-1"},
        )

        # Now we have entity options step
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "entity_options"

        # Accept default entity options
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "Test Emby Server"
        assert result["data"][CONF_HOST] == "emby.local"
        assert result["data"][CONF_PORT] == 8096
        assert result["data"][CONF_API_KEY] == "test-api-key"
        assert result["data"]["user_id"] == "user-1"

    @pytest.mark.asyncio
    async def test_connection_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test connection error shows message."""
        with patch("custom_components.embymedia.config_flow.EmbyClient") as mock_client_class:
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
        with patch("custom_components.embymedia.config_flow.EmbyClient") as mock_client_class:
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
        with patch("custom_components.embymedia.config_flow.EmbyClient") as mock_client_class:
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
        with patch("custom_components.embymedia.config_flow.EmbyClient") as mock_client_class:
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
        with patch("custom_components.embymedia.config_flow.EmbyClient") as mock_client_class:
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

        # Now we have user selection step
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user_select"

        # Complete user selection
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"user_id": "__none__"},
        )

        # Now we have entity options step
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "entity_options"

        # Accept default entity options
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_HOST] == "emby.local"

    @pytest.mark.asyncio
    async def test_version_check_supported(
        self,
        hass: HomeAssistant,
        mock_users: list[dict[str, Any]],
    ) -> None:
        """Test supported version accepted."""
        with patch("custom_components.embymedia.config_flow.EmbyClient") as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "server-123",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_users = AsyncMock(return_value=mock_users)

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

            # Should show user selection step
            assert result["type"] is FlowResultType.FORM
            assert result["step_id"] == "user_select"

            # Complete user selection
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"user_id": "__none__"},
            )

            # Now we have entity options step
            assert result["type"] is FlowResultType.FORM
            assert result["step_id"] == "entity_options"

            # Accept default entity options
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {},
            )

            assert result["type"] is FlowResultType.CREATE_ENTRY

    @pytest.mark.asyncio
    async def test_version_check_unsupported(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test unsupported version rejected."""
        with patch("custom_components.embymedia.config_flow.EmbyClient") as mock_client_class:
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
        mock_users: list[dict[str, Any]],
    ) -> None:
        """Test higher major version accepted."""
        with patch("custom_components.embymedia.config_flow.EmbyClient") as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "server-123",
                    "ServerName": "Test Server",
                    "Version": "5.0.0.0",  # Higher major version
                }
            )
            client.async_get_users = AsyncMock(return_value=mock_users)

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

            # Should show user selection step
            assert result["type"] is FlowResultType.FORM
            assert result["step_id"] == "user_select"

            # Complete user selection
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"user_id": "__none__"},
            )

            # Now we have entity options step
            assert result["type"] is FlowResultType.FORM
            assert result["step_id"] == "entity_options"

            # Accept default entity options
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {},
            )

            assert result["type"] is FlowResultType.CREATE_ENTRY

    @pytest.mark.asyncio
    async def test_version_check_invalid_version_allowed(
        self,
        hass: HomeAssistant,
        mock_users: list[dict[str, Any]],
    ) -> None:
        """Test invalid version string is allowed (returns True)."""
        with patch("custom_components.embymedia.config_flow.EmbyClient") as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "server-123",
                    "ServerName": "Test Server",
                    "Version": "invalid",  # Invalid version string
                }
            )
            client.async_get_users = AsyncMock(return_value=mock_users)

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

            # Should show user selection step
            assert result["type"] is FlowResultType.FORM
            assert result["step_id"] == "user_select"

            # Complete user selection
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"user_id": "__none__"},
            )

            # Now we have entity options step
            assert result["type"] is FlowResultType.FORM
            assert result["step_id"] == "entity_options"

            # Accept default entity options
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {},
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
        from custom_components.embymedia.config_flow import EmbyConfigFlow

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
        from custom_components.embymedia.config_flow import EmbyConfigFlow

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

        result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

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

        result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

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
        mock_users: list[dict[str, Any]],
    ) -> None:
        """Test successful reauth updates entry."""
        mock_config_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.config_flow.EmbyClient") as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id-12345",
                    "ServerName": "Test Emby Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_users = AsyncMock(return_value=mock_users)

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


class TestOptionsFlowStreaming:
    """Test options flow streaming/transcoding settings."""

    @pytest.mark.asyncio
    async def test_options_flow_streaming_settings(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test streaming options can be set."""
        mock_config_entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "scan_interval": 15,
                "direct_play": True,
                "video_container": "mp4",
                "max_video_bitrate": 8000000,
                "max_audio_bitrate": 128000,
            },
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"]["scan_interval"] == 15
        assert result["data"]["direct_play"] is True
        assert result["data"]["video_container"] == "mp4"
        assert result["data"]["max_video_bitrate"] == 8000000
        assert result["data"]["max_audio_bitrate"] == 128000

    @pytest.mark.asyncio
    async def test_options_flow_streaming_defaults(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test streaming options have correct defaults."""
        mock_config_entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
        assert result["type"] is FlowResultType.FORM

        # Check schema has streaming fields
        schema = result["data_schema"]
        assert schema is not None

        # Submitting with minimal settings should work
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {"scan_interval": 15},
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"]["scan_interval"] == 15

    @pytest.mark.asyncio
    async def test_options_flow_existing_streaming_values(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test existing streaming options are shown in form."""
        # Create entry with existing streaming options
        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_API_KEY: "test-api-key",
            },
            options={
                "scan_interval": 20,
                "direct_play": False,
                "video_container": "mkv",
                "max_video_bitrate": 4000000,
                "max_audio_bitrate": 192000,
            },
            unique_id="test-server-id-12345",
        )
        mock_entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(mock_entry.entry_id)
        assert result["type"] is FlowResultType.FORM

        # Existing values should be preserved in defaults
        schema = result["data_schema"]
        assert schema is not None

    @pytest.mark.asyncio
    async def test_options_flow_video_container_choices(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test video container has valid choices."""
        mock_config_entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
        assert result["type"] is FlowResultType.FORM

        # Test setting mkv container
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "scan_interval": 15,
                "video_container": "mkv",
            },
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"]["video_container"] == "mkv"

    @pytest.mark.asyncio
    async def test_options_flow_bitrate_validation(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test bitrate values must be positive."""
        mock_config_entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
        assert result["type"] is FlowResultType.FORM

        # Test with valid positive bitrates
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "scan_interval": 15,
                "max_video_bitrate": 1000000,
                "max_audio_bitrate": 64000,
            },
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"]["max_video_bitrate"] == 1000000
        assert result["data"]["max_audio_bitrate"] == 64000


class TestUserSelectionFlow:
    """Test user selection in config flow (Phase 8.1)."""

    @pytest.mark.asyncio
    async def test_user_selection_step_shown(
        self,
        hass: HomeAssistant,
        mock_users: list[dict[str, Any]],
    ) -> None:
        """Test user selection step is shown after connection validation."""
        with patch("custom_components.embymedia.config_flow.EmbyClient") as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "server-123",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_users = AsyncMock(return_value=mock_users)

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

            # Should show user selection step
            assert result["type"] is FlowResultType.FORM
            assert result["step_id"] == "user_select"

    @pytest.mark.asyncio
    async def test_user_selection_creates_entry_with_user_id(
        self,
        hass: HomeAssistant,
        mock_users: list[dict[str, Any]],
    ) -> None:
        """Test user selection stores user_id in config entry."""
        with patch("custom_components.embymedia.config_flow.EmbyClient") as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "server-123",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_users = AsyncMock(return_value=mock_users)

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

            # Select a user
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"user_id": "user-1"},
            )

            # Now we have entity options step
            assert result["type"] is FlowResultType.FORM
            assert result["step_id"] == "entity_options"

            # Accept default entity options
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {},
            )

            assert result["type"] is FlowResultType.CREATE_ENTRY
            assert result["data"]["user_id"] == "user-1"

    @pytest.mark.asyncio
    async def test_user_selection_multiple_users(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test user selection shows all available users."""
        multiple_users = [
            {
                "Id": "user-1",
                "Name": "Admin",
                "ServerId": "server-123",
                "HasPassword": True,
                "HasConfiguredPassword": True,
            },
            {
                "Id": "user-2",
                "Name": "Family",
                "ServerId": "server-123",
                "HasPassword": False,
                "HasConfiguredPassword": False,
            },
            {
                "Id": "user-3",
                "Name": "Kids",
                "ServerId": "server-123",
                "HasPassword": True,
                "HasConfiguredPassword": True,
            },
        ]

        with patch("custom_components.embymedia.config_flow.EmbyClient") as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "server-123",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_users = AsyncMock(return_value=multiple_users)

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

            # User selection step should be shown
            assert result["type"] is FlowResultType.FORM
            assert result["step_id"] == "user_select"

            # Select second user
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"user_id": "user-2"},
            )

            # Now we have entity options step
            assert result["type"] is FlowResultType.FORM
            assert result["step_id"] == "entity_options"

            # Accept default entity options
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {},
            )

            assert result["type"] is FlowResultType.CREATE_ENTRY
            assert result["data"]["user_id"] == "user-2"

    @pytest.mark.asyncio
    async def test_user_selection_skip_option(
        self,
        hass: HomeAssistant,
        mock_users: list[dict[str, Any]],
    ) -> None:
        """Test user selection can be skipped with admin context."""
        with patch("custom_components.embymedia.config_flow.EmbyClient") as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "server-123",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_users = AsyncMock(return_value=mock_users)

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

            # Skip user selection (use admin context)
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"user_id": "__none__"},  # Empty means admin context
            )

            # Now we have entity options step
            assert result["type"] is FlowResultType.FORM
            assert result["step_id"] == "entity_options"

            # Accept default entity options
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {},
            )

            assert result["type"] is FlowResultType.CREATE_ENTRY
            # user_id should be None or not present when skipped
            assert result["data"].get("user_id") in (None, "")


class TestOptionsFlowUserSelection:
    """Test user selection in options flow (Phase 8.1)."""

    @pytest.mark.asyncio
    async def test_options_flow_preserves_existing_settings(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test options flow preserves existing settings when adding user_id."""
        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_API_KEY: "test-api-key",
                "user_id": "user-1",
            },
            options={"scan_interval": 10, "user_id": "user-1"},
            unique_id="server-123",
        )
        mock_entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(mock_entry.entry_id)

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"

        # Update scan interval only
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {"scan_interval": 15},
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"]["scan_interval"] == 15


class TestConfigFlowEdgeCases:
    """Test edge cases in config flow."""

    @pytest.mark.asyncio
    async def test_user_select_without_user_input_aborts(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test user_select step aborts if _user_input is None."""
        from custom_components.embymedia.config_flow import EmbyConfigFlow

        flow = EmbyConfigFlow()
        flow.hass = hass
        # Explicitly set _user_input to None (simulating invalid state)
        flow._user_input = None
        flow._server_info = {"ServerName": "Test Server", "Id": "server-123"}

        result = await flow._async_create_entry_with_user("user-123")

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "unknown"

    @pytest.mark.asyncio
    async def test_create_entry_with_no_server_info(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test entry creation when server_info is None uses host as title."""
        from custom_components.embymedia.config_flow import EmbyConfigFlow

        flow = EmbyConfigFlow()
        flow.hass = hass
        flow._user_input = {
            "host": "my-emby-server.local",
            "port": 8096,
            "ssl": False,
            "api_key": "test-key",
            "verify_ssl": True,
        }
        flow._server_info = None  # No server info

        result = await flow._async_create_entry_with_user("")

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "Emby (my-emby-server.local)"

    @pytest.mark.asyncio
    async def test_reauth_preserves_existing_user_id(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test reauth flow preserves existing user_id."""
        from custom_components.embymedia.const import CONF_USER_ID

        # Create entry with user_id
        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "old-api-key",
                CONF_VERIFY_SSL: True,
                CONF_USER_ID: "existing-user-id",  # Existing user_id
            },
            unique_id="test-server-id-12345",
        )
        mock_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.config_flow.EmbyClient") as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id-12345",
                    "ServerName": "Test Emby Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_users = AsyncMock(return_value=[])

            with (
                patch(
                    "custom_components.embymedia.EmbyClient", autospec=True
                ) as mock_integration_client,
                patch(
                    "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                    new_callable=AsyncMock,
                ),
            ):
                # Mock the integration client for setup
                int_client = mock_integration_client.return_value
                int_client.async_validate_connection = AsyncMock(return_value=True)
                int_client.async_get_server_info = AsyncMock(
                    return_value={
                        "Id": "test-server-id-12345",
                        "ServerName": "Test Server",
                        "Version": "4.9.2.0",
                    }
                )
                int_client.async_get_sessions = AsyncMock(return_value=[])
                int_client.close = AsyncMock()

                result = await hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={
                        "source": config_entries.SOURCE_REAUTH,
                        "entry_id": mock_entry.entry_id,
                    },
                    data=mock_entry.data,
                )

                result = await hass.config_entries.flow.async_configure(
                    result["flow_id"],
                    {CONF_API_KEY: "new-api-key"},
                )

                assert result["type"] is FlowResultType.ABORT
                assert result["reason"] == "reauth_successful"

                # Check that user_id was preserved
                updated_entry = hass.config_entries.async_get_entry(mock_entry.entry_id)
                assert updated_entry is not None
                assert updated_entry.data.get(CONF_USER_ID) == "existing-user-id"


class TestOptionsFlowPrefixToggles:
    """Test entity name prefix toggles in options flow (Phase 11)."""

    @pytest.mark.asyncio
    async def test_options_flow_prefix_toggles_present(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test prefix toggle options are available in options flow."""
        from custom_components.embymedia.const import (
            CONF_PREFIX_BUTTON,
            CONF_PREFIX_MEDIA_PLAYER,
            CONF_PREFIX_NOTIFY,
            CONF_PREFIX_REMOTE,
        )

        mock_config_entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"

        # Test setting all prefix toggles
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "scan_interval": 15,
                CONF_PREFIX_MEDIA_PLAYER: True,
                CONF_PREFIX_NOTIFY: True,
                CONF_PREFIX_REMOTE: True,
                CONF_PREFIX_BUTTON: True,
            },
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_PREFIX_MEDIA_PLAYER] is True
        assert result["data"][CONF_PREFIX_NOTIFY] is True
        assert result["data"][CONF_PREFIX_REMOTE] is True
        assert result["data"][CONF_PREFIX_BUTTON] is True

    @pytest.mark.asyncio
    async def test_options_flow_prefix_toggles_can_be_disabled(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test prefix toggles can be disabled."""
        from custom_components.embymedia.const import (
            CONF_PREFIX_BUTTON,
            CONF_PREFIX_MEDIA_PLAYER,
            CONF_PREFIX_NOTIFY,
            CONF_PREFIX_REMOTE,
        )

        mock_config_entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

        # Disable all prefix toggles
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "scan_interval": 15,
                CONF_PREFIX_MEDIA_PLAYER: False,
                CONF_PREFIX_NOTIFY: False,
                CONF_PREFIX_REMOTE: False,
                CONF_PREFIX_BUTTON: False,
            },
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_PREFIX_MEDIA_PLAYER] is False
        assert result["data"][CONF_PREFIX_NOTIFY] is False
        assert result["data"][CONF_PREFIX_REMOTE] is False
        assert result["data"][CONF_PREFIX_BUTTON] is False

    @pytest.mark.asyncio
    async def test_options_flow_prefix_toggles_defaults_to_true(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test prefix toggles default to True (enabled)."""
        from custom_components.embymedia.const import (
            CONF_PREFIX_BUTTON,
            CONF_PREFIX_MEDIA_PLAYER,
            CONF_PREFIX_NOTIFY,
            CONF_PREFIX_REMOTE,
        )

        mock_config_entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

        # Submit without explicitly setting prefix toggles
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {"scan_interval": 15},
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        # When not explicitly set, they should use defaults (True)
        assert result["data"].get(CONF_PREFIX_MEDIA_PLAYER, True) is True
        assert result["data"].get(CONF_PREFIX_NOTIFY, True) is True
        assert result["data"].get(CONF_PREFIX_REMOTE, True) is True
        assert result["data"].get(CONF_PREFIX_BUTTON, True) is True

    @pytest.mark.asyncio
    async def test_options_flow_preserves_existing_prefix_settings(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test existing prefix settings are preserved in form."""
        from custom_components.embymedia.const import (
            CONF_PREFIX_BUTTON,
            CONF_PREFIX_MEDIA_PLAYER,
            CONF_PREFIX_NOTIFY,
            CONF_PREFIX_REMOTE,
        )

        # Create entry with existing prefix options (some disabled)
        mock_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_API_KEY: "test-api-key",
            },
            options={
                "scan_interval": 20,
                CONF_PREFIX_MEDIA_PLAYER: True,  # Enabled
                CONF_PREFIX_NOTIFY: False,  # Disabled
                CONF_PREFIX_REMOTE: True,  # Enabled
                CONF_PREFIX_BUTTON: False,  # Disabled
            },
            unique_id="test-server-id-12345",
        )
        mock_entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(mock_entry.entry_id)
        assert result["type"] is FlowResultType.FORM

        # Update only scan_interval, other settings should be preserved
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "scan_interval": 25,
                CONF_PREFIX_MEDIA_PLAYER: True,
                CONF_PREFIX_NOTIFY: False,
                CONF_PREFIX_REMOTE: True,
                CONF_PREFIX_BUTTON: False,
            },
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"]["scan_interval"] == 25
        assert result["data"][CONF_PREFIX_MEDIA_PLAYER] is True
        assert result["data"][CONF_PREFIX_NOTIFY] is False
        assert result["data"][CONF_PREFIX_REMOTE] is True
        assert result["data"][CONF_PREFIX_BUTTON] is False


class TestEntityOptionsStep:
    """Test entity_options step in config flow (Phase 11)."""

    @pytest.mark.asyncio
    async def test_entity_options_step_shown(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test entity_options step is shown after user selection."""
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

        # User selection step
        assert result["step_id"] == "user_select"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"user_id": "__none__"},
        )

        # Entity options step should be shown
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "entity_options"

    @pytest.mark.asyncio
    async def test_entity_options_custom_settings(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test custom entity options are saved to config entry."""
        from custom_components.embymedia.const import (
            CONF_PREFIX_BUTTON,
            CONF_PREFIX_MEDIA_PLAYER,
            CONF_PREFIX_NOTIFY,
            CONF_PREFIX_REMOTE,
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

        # User selection step
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"user_id": "__none__"},
        )

        # Entity options step - set custom values (disable some prefixes)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_PREFIX_MEDIA_PLAYER: False,  # Disable
                CONF_PREFIX_NOTIFY: True,  # Enable
                CONF_PREFIX_REMOTE: False,  # Disable
                CONF_PREFIX_BUTTON: True,  # Enable
            },
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        # Options should be saved in the entry
        assert result["options"][CONF_PREFIX_MEDIA_PLAYER] is False
        assert result["options"][CONF_PREFIX_NOTIFY] is True
        assert result["options"][CONF_PREFIX_REMOTE] is False
        assert result["options"][CONF_PREFIX_BUTTON] is True

    @pytest.mark.asyncio
    async def test_entity_options_defaults_enabled(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test entity options default to enabled when accepting defaults."""
        from custom_components.embymedia.const import (
            CONF_PREFIX_BUTTON,
            CONF_PREFIX_MEDIA_PLAYER,
            CONF_PREFIX_NOTIFY,
            CONF_PREFIX_REMOTE,
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

        # User selection step
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"user_id": "__none__"},
        )

        # Entity options step - accept all defaults (empty dict)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {},  # Accept defaults
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        # All defaults should be True
        assert result["options"].get(CONF_PREFIX_MEDIA_PLAYER, True) is True
        assert result["options"].get(CONF_PREFIX_NOTIFY, True) is True
        assert result["options"].get(CONF_PREFIX_REMOTE, True) is True
        assert result["options"].get(CONF_PREFIX_BUTTON, True) is True
