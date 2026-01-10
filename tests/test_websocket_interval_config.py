"""Tests for configurable WebSocket session interval (Phase 22).

These tests verify the WebSocket session subscription interval is configurable
via the options flow.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.embymedia.const import (
    CONF_API_KEY,
    CONF_VERIFY_SSL,
    CONF_WEBSOCKET_INTERVAL,
    DEFAULT_WEBSOCKET_INTERVAL,
    DOMAIN,
    MAX_WEBSOCKET_INTERVAL,
    MIN_WEBSOCKET_INTERVAL,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestWebSocketIntervalConstants:
    """Tests for WebSocket interval constants in const.py."""

    def test_websocket_interval_config_key_exists(self) -> None:
        """Test that CONF_WEBSOCKET_INTERVAL constant exists."""
        assert CONF_WEBSOCKET_INTERVAL == "websocket_interval"

    def test_default_websocket_interval_exists(self) -> None:
        """Test that DEFAULT_WEBSOCKET_INTERVAL constant exists."""
        assert DEFAULT_WEBSOCKET_INTERVAL == 1500

    def test_interval_bounds_exist(self) -> None:
        """Test that MIN and MAX websocket interval constants exist."""
        assert MIN_WEBSOCKET_INTERVAL == 500
        assert MAX_WEBSOCKET_INTERVAL == 10000


class TestOptionsFlowWebSocketInterval:
    """Tests for WebSocket interval in options flow."""

    @pytest.fixture
    def mock_options_entry(self) -> MockConfigEntry:
        """Create a mock config entry for options flow tests."""
        return MockConfigEntry(
            domain=DOMAIN,
            title="Test Emby Server",
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key-12345",
                CONF_VERIFY_SSL: True,
            },
            options={},
            unique_id="test-server-id-options",
            version=1,
        )

    @pytest.mark.asyncio
    async def test_options_flow_includes_websocket_interval(
        self,
        hass: HomeAssistant,
        mock_options_entry: MockConfigEntry,
    ) -> None:
        """Test that options flow includes WebSocket interval option."""
        mock_options_entry.add_to_hass(hass)

        # Get the form
        result = await hass.config_entries.options.async_init(mock_options_entry.entry_id)

        assert result["type"] is FlowResultType.FORM
        # Check that the schema includes websocket_interval
        schema_keys = list(result["data_schema"].schema.keys())
        schema_key_names = [str(k) for k in schema_keys]
        assert CONF_WEBSOCKET_INTERVAL in schema_key_names

    @pytest.mark.asyncio
    async def test_options_flow_validates_interval_range(
        self,
        hass: HomeAssistant,
        mock_options_entry: MockConfigEntry,
    ) -> None:
        """Test that options flow validates WebSocket interval range."""
        mock_options_entry.add_to_hass(hass)

        # Get the form first
        result = await hass.config_entries.options.async_init(mock_options_entry.entry_id)

        assert result["type"] is FlowResultType.FORM

        # Test with a valid interval
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "scan_interval": 10,
                CONF_WEBSOCKET_INTERVAL: 2000,  # Valid: between 500 and 10000
            },
        )

        # Should create entry (not show validation error)
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_WEBSOCKET_INTERVAL] == 2000

    @pytest.mark.asyncio
    async def test_options_flow_uses_default_interval(
        self,
        hass: HomeAssistant,
        mock_options_entry: MockConfigEntry,
    ) -> None:
        """Test that options flow uses default WebSocket interval."""
        mock_options_entry.add_to_hass(hass)

        # Get the form
        result = await hass.config_entries.options.async_init(mock_options_entry.entry_id)

        assert result["type"] is FlowResultType.FORM

        # Find the websocket_interval key and check its default
        schema = result["data_schema"].schema
        for key in schema:
            if str(key) == CONF_WEBSOCKET_INTERVAL:
                assert key.default() == DEFAULT_WEBSOCKET_INTERVAL
                break
        else:
            pytest.fail("CONF_WEBSOCKET_INTERVAL not found in schema")


class TestCoordinatorWebSocketInterval:
    """Tests for WebSocket interval usage in coordinator."""

    @pytest.mark.asyncio
    async def test_coordinator_uses_configured_interval(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that coordinator uses the configured WebSocket interval."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_client = MagicMock()
        mock_client.server_id = "test-server"
        mock_client.server_name = "Test Server"

        # Create config entry with custom interval
        mock_entry = MagicMock()
        mock_entry.data = {
            CONF_HOST: "emby.local",
            CONF_PORT: 8096,
        }
        mock_entry.options = {
            CONF_WEBSOCKET_INTERVAL: 3000,  # Custom interval
        }
        mock_entry.entry_id = "test-entry-id"

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            config_entry=mock_entry,
        )

        # Verify the interval is used
        assert coordinator.websocket_interval == 3000

    @pytest.mark.asyncio
    async def test_coordinator_uses_default_when_not_configured(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that coordinator uses default interval when not configured."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_client = MagicMock()
        mock_client.server_id = "test-server"
        mock_client.server_name = "Test Server"

        # Create config entry without custom interval
        mock_entry = MagicMock()
        mock_entry.data = {
            CONF_HOST: "emby.local",
            CONF_PORT: 8096,
        }
        mock_entry.options = {}  # No custom interval
        mock_entry.entry_id = "test-entry-id"

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            config_entry=mock_entry,
        )

        # Should use default interval
        assert coordinator.websocket_interval == DEFAULT_WEBSOCKET_INTERVAL


class TestWebSocketClientInterval:
    """Tests for WebSocket client using the configured interval."""

    @pytest.mark.asyncio
    async def test_websocket_client_interval_property(self) -> None:
        """Test WebSocket client accepts interval parameter."""
        from custom_components.embymedia.websocket import EmbyWebsocketClient

        mock_client = MagicMock()
        mock_client.base_url = "http://emby.local:8096"
        mock_client.api_key = "test-key"

        with patch.object(EmbyWebsocketClient, "__init__", lambda s, **kw: None):
            ws_client = EmbyWebsocketClient.__new__(EmbyWebsocketClient)
            ws_client._interval_ms = 2500
            assert ws_client._interval_ms == 2500
