"""Tests for configurable polling intervals (Issue #292).

These tests verify that:
- Options flow allows configuring library and server polling intervals
- Coordinators respect configured intervals
- Validation enforces reasonable ranges
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestPollingIntervalConstants:
    """Test polling interval constants exist."""

    def test_library_scan_interval_constants_exist(self) -> None:
        """Test that library scan interval constants are defined."""
        from custom_components.embymedia.const import (
            CONF_LIBRARY_SCAN_INTERVAL,
            DEFAULT_LIBRARY_SCAN_INTERVAL,
            MAX_LIBRARY_SCAN_INTERVAL,
            MIN_LIBRARY_SCAN_INTERVAL,
        )

        assert CONF_LIBRARY_SCAN_INTERVAL == "library_scan_interval"
        assert DEFAULT_LIBRARY_SCAN_INTERVAL == 3600  # 1 hour
        assert MIN_LIBRARY_SCAN_INTERVAL == 3600  # 1 hour minimum
        assert MAX_LIBRARY_SCAN_INTERVAL == 86400  # 24 hours maximum

    def test_server_scan_interval_constants_exist(self) -> None:
        """Test that server scan interval constants are defined."""
        from custom_components.embymedia.const import (
            CONF_SERVER_SCAN_INTERVAL,
            DEFAULT_SERVER_SCAN_INTERVAL,
            MAX_SERVER_SCAN_INTERVAL,
            MIN_SERVER_SCAN_INTERVAL,
        )

        assert CONF_SERVER_SCAN_INTERVAL == "server_scan_interval"
        assert DEFAULT_SERVER_SCAN_INTERVAL == 300  # 5 minutes
        assert MIN_SERVER_SCAN_INTERVAL == 300  # 5 minutes minimum
        assert MAX_SERVER_SCAN_INTERVAL == 3600  # 1 hour maximum


class TestOptionsFlowPollingIntervals:
    """Test options flow includes polling interval configuration."""

    @pytest.mark.asyncio
    async def test_options_flow_includes_library_interval(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that options flow includes library scan interval field."""
        from homeassistant.config_entries import ConfigEntry

        from custom_components.embymedia.config_flow import EmbyOptionsFlowHandler
        from custom_components.embymedia.const import (
            CONF_LIBRARY_SCAN_INTERVAL,
        )

        mock_entry = MagicMock(spec=ConfigEntry)
        mock_entry.options = {}

        handler = EmbyOptionsFlowHandler()
        handler._config_entry = mock_entry
        handler.hass = hass

        result = await handler.async_step_init()

        # Verify form is shown with library interval field
        assert result["type"] == "form"
        schema = result["data_schema"]
        schema_keys = [str(k) for k in schema.schema]
        assert CONF_LIBRARY_SCAN_INTERVAL in schema_keys

    @pytest.mark.asyncio
    async def test_options_flow_includes_server_interval(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that options flow includes server scan interval field."""
        from homeassistant.config_entries import ConfigEntry

        from custom_components.embymedia.config_flow import EmbyOptionsFlowHandler
        from custom_components.embymedia.const import (
            CONF_SERVER_SCAN_INTERVAL,
        )

        mock_entry = MagicMock(spec=ConfigEntry)
        mock_entry.options = {}

        handler = EmbyOptionsFlowHandler()
        handler._config_entry = mock_entry
        handler.hass = hass

        result = await handler.async_step_init()

        # Verify form is shown with server interval field
        assert result["type"] == "form"
        schema = result["data_schema"]
        schema_keys = [str(k) for k in schema.schema]
        assert CONF_SERVER_SCAN_INTERVAL in schema_keys

    @pytest.mark.asyncio
    async def test_options_flow_saves_polling_intervals(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that options flow saves polling interval configuration."""
        from homeassistant.config_entries import ConfigEntry

        from custom_components.embymedia.config_flow import EmbyOptionsFlowHandler
        from custom_components.embymedia.const import (
            CONF_LIBRARY_SCAN_INTERVAL,
            CONF_SERVER_SCAN_INTERVAL,
        )

        mock_entry = MagicMock(spec=ConfigEntry)
        mock_entry.options = {}

        handler = EmbyOptionsFlowHandler()
        handler._config_entry = mock_entry
        handler.hass = hass

        # Simulate user input with custom intervals
        user_input = {
            "scan_interval": 30,
            CONF_LIBRARY_SCAN_INTERVAL: 7200,  # 2 hours
            CONF_SERVER_SCAN_INTERVAL: 600,  # 10 minutes
        }

        result = await handler.async_step_init(user_input=user_input)

        assert result["type"] == "create_entry"
        assert result["data"][CONF_LIBRARY_SCAN_INTERVAL] == 7200
        assert result["data"][CONF_SERVER_SCAN_INTERVAL] == 600


class TestLibraryCoordinatorUsesConfiguredInterval:
    """Test that EmbyLibraryCoordinator respects configured interval."""

    @pytest.mark.asyncio
    async def test_library_coordinator_uses_config_interval(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test EmbyLibraryCoordinator uses interval from config entry options."""
        from datetime import timedelta

        from custom_components.embymedia.const import CONF_LIBRARY_SCAN_INTERVAL
        from custom_components.embymedia.coordinator_sensors import (
            EmbyLibraryCoordinator,
        )

        mock_client = MagicMock()
        mock_config_entry = MagicMock()
        mock_config_entry.options = {CONF_LIBRARY_SCAN_INTERVAL: 7200}  # 2 hours

        # Library coordinator reads from options when scan_interval not provided
        coordinator = EmbyLibraryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            config_entry=mock_config_entry,
        )

        assert coordinator.update_interval == timedelta(seconds=7200)

    @pytest.mark.asyncio
    async def test_library_coordinator_uses_default_when_not_configured(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test EmbyLibraryCoordinator uses default when not in options."""
        from datetime import timedelta

        from custom_components.embymedia.const import DEFAULT_LIBRARY_SCAN_INTERVAL
        from custom_components.embymedia.coordinator_sensors import (
            EmbyLibraryCoordinator,
        )

        mock_client = MagicMock()
        mock_config_entry = MagicMock()
        mock_config_entry.options = {}  # No interval configured

        coordinator = EmbyLibraryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            config_entry=mock_config_entry,
        )

        assert coordinator.update_interval == timedelta(seconds=DEFAULT_LIBRARY_SCAN_INTERVAL)


class TestServerCoordinatorUsesConfiguredInterval:
    """Test that EmbyServerCoordinator respects configured interval."""

    @pytest.mark.asyncio
    async def test_server_coordinator_uses_config_interval(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test EmbyServerCoordinator uses interval from config entry options."""
        from datetime import timedelta

        from custom_components.embymedia.const import CONF_SERVER_SCAN_INTERVAL
        from custom_components.embymedia.coordinator_sensors import (
            EmbyServerCoordinator,
        )

        mock_client = MagicMock()
        mock_config_entry = MagicMock()
        mock_config_entry.options = {CONF_SERVER_SCAN_INTERVAL: 600}  # 10 minutes

        # Server coordinator reads from options when scan_interval not provided
        coordinator = EmbyServerCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        assert coordinator.update_interval == timedelta(seconds=600)

    @pytest.mark.asyncio
    async def test_server_coordinator_uses_default_when_not_configured(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test EmbyServerCoordinator uses default when not in options."""
        from datetime import timedelta

        from custom_components.embymedia.const import DEFAULT_SERVER_SCAN_INTERVAL
        from custom_components.embymedia.coordinator_sensors import (
            EmbyServerCoordinator,
        )

        mock_client = MagicMock()
        mock_config_entry = MagicMock()
        mock_config_entry.options = {}  # No interval configured

        coordinator = EmbyServerCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        assert coordinator.update_interval == timedelta(seconds=DEFAULT_SERVER_SCAN_INTERVAL)
