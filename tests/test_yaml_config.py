"""Tests for Emby YAML configuration support."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.core import HomeAssistant

from custom_components.embymedia.const import (
    CONF_API_KEY,
    CONF_DIRECT_PLAY,
    CONF_ENABLE_WEBSOCKET,
    CONF_IGNORE_WEB_PLAYERS,
    CONF_IGNORED_DEVICES,
    CONF_MAX_AUDIO_BITRATE,
    CONF_MAX_VIDEO_BITRATE,
    CONF_SCAN_INTERVAL,
    CONF_VERIFY_SSL,
    CONF_VIDEO_CONTAINER,
    DOMAIN,
)


class TestYamlConfigSchema:
    """Test YAML configuration schema validation."""

    @pytest.mark.asyncio
    async def test_yaml_config_minimal(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test minimal YAML configuration."""
        from custom_components.embymedia import CONFIG_SCHEMA

        config = {
            DOMAIN: {
                CONF_HOST: "emby.local",
                CONF_API_KEY: "test-api-key",
            }
        }

        validated = CONFIG_SCHEMA(config)
        assert validated[DOMAIN][CONF_HOST] == "emby.local"
        assert validated[DOMAIN][CONF_API_KEY] == "test-api-key"
        # Check defaults
        assert validated[DOMAIN][CONF_PORT] == 8096
        assert validated[DOMAIN][CONF_SSL] is False

    @pytest.mark.asyncio
    async def test_yaml_config_full(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test full YAML configuration with all options."""
        from custom_components.embymedia import CONFIG_SCHEMA

        config = {
            DOMAIN: {
                CONF_HOST: "emby.example.com",
                CONF_API_KEY: "my-secret-key",
                CONF_PORT: 443,
                CONF_SSL: True,
                CONF_VERIFY_SSL: False,
                CONF_SCAN_INTERVAL: 30,
                CONF_ENABLE_WEBSOCKET: True,
                CONF_IGNORED_DEVICES: "Device1,Device2",
                CONF_DIRECT_PLAY: False,
                CONF_VIDEO_CONTAINER: "mkv",
                CONF_MAX_VIDEO_BITRATE: 10000,
                CONF_MAX_AUDIO_BITRATE: 320,
            }
        }

        validated = CONFIG_SCHEMA(config)
        assert validated[DOMAIN][CONF_HOST] == "emby.example.com"
        assert validated[DOMAIN][CONF_PORT] == 443
        assert validated[DOMAIN][CONF_SSL] is True
        assert validated[DOMAIN][CONF_VERIFY_SSL] is False
        assert validated[DOMAIN][CONF_SCAN_INTERVAL] == 30
        assert validated[DOMAIN][CONF_ENABLE_WEBSOCKET] is True
        assert validated[DOMAIN][CONF_IGNORED_DEVICES] == "Device1,Device2"
        assert validated[DOMAIN][CONF_DIRECT_PLAY] is False
        assert validated[DOMAIN][CONF_VIDEO_CONTAINER] == "mkv"

    @pytest.mark.asyncio
    async def test_yaml_config_missing_required_host(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test YAML config validation fails without host."""
        import voluptuous as vol

        from custom_components.embymedia import CONFIG_SCHEMA

        config = {
            DOMAIN: {
                CONF_API_KEY: "test-api-key",
                # Missing CONF_HOST
            }
        }

        with pytest.raises(vol.MultipleInvalid):
            CONFIG_SCHEMA(config)

    @pytest.mark.asyncio
    async def test_yaml_config_missing_required_api_key(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test YAML config validation fails without api_key."""
        import voluptuous as vol

        from custom_components.embymedia import CONFIG_SCHEMA

        config = {
            DOMAIN: {
                CONF_HOST: "emby.local",
                # Missing CONF_API_KEY
            }
        }

        with pytest.raises(vol.MultipleInvalid):
            CONFIG_SCHEMA(config)

    @pytest.mark.asyncio
    async def test_yaml_config_invalid_port(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test YAML config validation fails with invalid port."""
        import voluptuous as vol

        from custom_components.embymedia import CONFIG_SCHEMA

        config = {
            DOMAIN: {
                CONF_HOST: "emby.local",
                CONF_API_KEY: "test-api-key",
                CONF_PORT: 99999,  # Invalid port
            }
        }

        with pytest.raises(vol.MultipleInvalid):
            CONFIG_SCHEMA(config)


class TestAsyncSetup:
    """Test async_setup function for YAML configuration."""

    @pytest.mark.asyncio
    async def test_async_setup_no_config(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test async_setup with no domain config returns True."""
        from custom_components.embymedia import async_setup

        result = await async_setup(hass, {})
        assert result is True

    @pytest.mark.asyncio
    async def test_async_setup_triggers_import_flow(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test async_setup triggers config flow import."""
        from custom_components.embymedia import async_setup

        config = {
            DOMAIN: {
                CONF_HOST: "emby.local",
                CONF_API_KEY: "test-api-key",
                CONF_PORT: 8096,
                CONF_SSL: False,
            }
        }

        with patch.object(
            hass.config_entries.flow, "async_init", new_callable=AsyncMock
        ) as mock_init:
            result = await async_setup(hass, config)

            assert result is True
            mock_init.assert_called_once_with(
                DOMAIN,
                context={"source": "import"},
                data=config[DOMAIN],
            )


class TestConfigFlowImport:
    """Test config flow import step."""

    @pytest.mark.asyncio
    async def test_import_creates_config_entry(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test import step creates config entry from YAML."""
        from custom_components.embymedia.config_flow import EmbyConfigFlow

        flow = EmbyConfigFlow()
        flow.hass = hass

        import_data = {
            CONF_HOST: "emby.local",
            CONF_API_KEY: "test-api-key",
            CONF_PORT: 8096,
            CONF_SSL: False,
        }

        with (
            patch.object(flow, "async_set_unique_id", new_callable=AsyncMock) as mock_unique_id,
            patch.object(flow, "_abort_if_unique_id_configured") as mock_abort,
            patch("custom_components.embymedia.config_flow.EmbyClient") as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client.async_validate_connection = AsyncMock()
            mock_client.async_get_server_info = AsyncMock(
                return_value={"Id": "server-123", "ServerName": "Test Server"}
            )
            mock_client_class.return_value = mock_client

            result = await flow.async_step_import(import_data)

            assert result["type"] == "create_entry"
            assert result["title"] == "Test Server"
            assert result["data"][CONF_HOST] == "emby.local"
            assert result["data"][CONF_API_KEY] == "test-api-key"
            mock_unique_id.assert_called_once()
            mock_abort.assert_called_once()

    @pytest.mark.asyncio
    async def test_import_with_all_options(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test import step with all configuration options."""
        from custom_components.embymedia.config_flow import EmbyConfigFlow

        flow = EmbyConfigFlow()
        flow.hass = hass

        import_data = {
            CONF_HOST: "emby.example.com",
            CONF_API_KEY: "my-key",
            CONF_PORT: 443,
            CONF_SSL: True,
            CONF_VERIFY_SSL: False,
            CONF_SCAN_INTERVAL: 30,
            CONF_ENABLE_WEBSOCKET: False,
            CONF_IGNORED_DEVICES: "TV1,TV2",
            CONF_IGNORE_WEB_PLAYERS: True,
            CONF_DIRECT_PLAY: False,
            CONF_VIDEO_CONTAINER: "mkv",
            CONF_MAX_VIDEO_BITRATE: 8000,
            CONF_MAX_AUDIO_BITRATE: 256,
        }

        with (
            patch.object(flow, "async_set_unique_id", new_callable=AsyncMock),
            patch.object(flow, "_abort_if_unique_id_configured"),
            patch("custom_components.embymedia.config_flow.EmbyClient") as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client.async_validate_connection = AsyncMock()
            mock_client.async_get_server_info = AsyncMock(
                return_value={"Id": "server-456", "ServerName": "Production Emby"}
            )
            mock_client_class.return_value = mock_client

            result = await flow.async_step_import(import_data)

            assert result["type"] == "create_entry"
            # Data should contain connection info
            assert result["data"][CONF_HOST] == "emby.example.com"
            assert result["data"][CONF_PORT] == 443
            assert result["data"][CONF_SSL] is True
            # Options should contain tunable settings
            assert result["options"][CONF_SCAN_INTERVAL] == 30
            assert result["options"][CONF_ENABLE_WEBSOCKET] is False
            assert result["options"][CONF_IGNORE_WEB_PLAYERS] is True

    @pytest.mark.asyncio
    async def test_import_duplicate_aborts(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test import step aborts if already configured."""
        from homeassistant.data_entry_flow import AbortFlow

        from custom_components.embymedia.config_flow import EmbyConfigFlow

        flow = EmbyConfigFlow()
        flow.hass = hass

        import_data = {
            CONF_HOST: "emby.local",
            CONF_API_KEY: "test-api-key",
        }

        with (
            patch("custom_components.embymedia.config_flow.EmbyClient") as mock_client_class,
            patch.object(flow, "async_set_unique_id", new_callable=AsyncMock),
            patch.object(
                flow, "_abort_if_unique_id_configured", side_effect=AbortFlow("already_configured")
            ),
        ):
            mock_client = MagicMock()
            mock_client.async_validate_connection = AsyncMock()
            mock_client.async_get_server_info = AsyncMock(
                return_value={"Id": "server-123", "ServerName": "Test Server"}
            )
            mock_client_class.return_value = mock_client

            with pytest.raises(AbortFlow) as exc_info:
                await flow.async_step_import(import_data)
            assert exc_info.value.reason == "already_configured"

    @pytest.mark.asyncio
    async def test_import_connection_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test import step handles connection errors."""
        from custom_components.embymedia.config_flow import EmbyConfigFlow
        from custom_components.embymedia.exceptions import EmbyConnectionError

        flow = EmbyConfigFlow()
        flow.hass = hass

        import_data = {
            CONF_HOST: "emby.local",
            CONF_API_KEY: "test-api-key",
        }

        with (
            patch.object(flow, "async_set_unique_id", new_callable=AsyncMock),
            patch.object(flow, "_abort_if_unique_id_configured"),
            patch("custom_components.embymedia.config_flow.EmbyClient") as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client.async_validate_connection = AsyncMock(
                side_effect=EmbyConnectionError("Connection failed")
            )
            mock_client_class.return_value = mock_client

            result = await flow.async_step_import(import_data)

            assert result["type"] == "abort"
            assert result["reason"] == "cannot_connect"

    @pytest.mark.asyncio
    async def test_import_auth_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test import step handles authentication errors."""
        from custom_components.embymedia.config_flow import EmbyConfigFlow
        from custom_components.embymedia.exceptions import EmbyAuthenticationError

        flow = EmbyConfigFlow()
        flow.hass = hass

        import_data = {
            CONF_HOST: "emby.local",
            CONF_API_KEY: "bad-api-key",
        }

        with (
            patch.object(flow, "async_set_unique_id", new_callable=AsyncMock),
            patch.object(flow, "_abort_if_unique_id_configured"),
            patch("custom_components.embymedia.config_flow.EmbyClient") as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client.async_validate_connection = AsyncMock(
                side_effect=EmbyAuthenticationError("Invalid API key")
            )
            mock_client_class.return_value = mock_client

            result = await flow.async_step_import(import_data)

            assert result["type"] == "abort"
            assert result["reason"] == "invalid_auth"

    @pytest.mark.asyncio
    async def test_import_unexpected_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test import step handles unexpected errors."""
        from custom_components.embymedia.config_flow import EmbyConfigFlow

        flow = EmbyConfigFlow()
        flow.hass = hass

        import_data = {
            CONF_HOST: "emby.local",
            CONF_API_KEY: "test-api-key",
        }

        with (
            patch.object(flow, "async_set_unique_id", new_callable=AsyncMock),
            patch.object(flow, "_abort_if_unique_id_configured"),
            patch("custom_components.embymedia.config_flow.EmbyClient") as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client.async_validate_connection = AsyncMock(
                side_effect=RuntimeError("Unexpected error")
            )
            mock_client_class.return_value = mock_client

            result = await flow.async_step_import(import_data)

            assert result["type"] == "abort"
            assert result["reason"] == "unknown"
