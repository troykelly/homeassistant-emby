"""Tests for Phase 8.1: Multiple Users Support."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.embymedia.const import (
    CONF_API_KEY,
    CONF_USER_ID,
    DOMAIN,
)

if TYPE_CHECKING:
    from custom_components.embymedia.const import EmbyConfigEntry


@pytest.fixture
def mock_config_entry(hass: HomeAssistant) -> EmbyConfigEntry:
    """Create a mock config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "emby.local",
            "port": 8096,
            CONF_API_KEY: "test-api-key",
        },
        options={},
        unique_id="server-123",
    )
    entry.add_to_hass(hass)
    return entry  # type: ignore[return-value]


class TestConfigFlowUserSelection:
    """Test user selection in config flow."""

    @pytest.mark.asyncio
    async def test_config_flow_shows_user_selection(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test config flow shows user selection step after connection."""
        with (
            patch("custom_components.embymedia.config_flow.EmbyClient") as mock_client_class,
        ):
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.async_validate_connection = AsyncMock(return_value=True)
            mock_client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "server-123",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            mock_client.async_get_users = AsyncMock(
                return_value=[
                    {"Id": "user-1", "Name": "Admin"},
                    {"Id": "user-2", "Name": "Guest"},
                ]
            )

            result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})

            assert result["type"] is FlowResultType.FORM
            assert result["step_id"] == "user"

            # Submit connection details
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    "host": "emby.local",
                    "port": 8096,
                    "ssl": False,
                    "api_key": "test-key",
                    "verify_ssl": True,
                },
            )

            # Should show user selection step
            assert result["type"] is FlowResultType.FORM
            assert result["step_id"] == "user_select"

    @pytest.mark.asyncio
    async def test_config_flow_user_selection_creates_entry(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test selecting a user creates config entry with user_id."""
        with (
            patch("custom_components.embymedia.config_flow.EmbyClient") as mock_client_class,
        ):
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.async_validate_connection = AsyncMock(return_value=True)
            mock_client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "server-123",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            mock_client.async_get_users = AsyncMock(
                return_value=[
                    {"Id": "user-1", "Name": "Admin"},
                    {"Id": "user-2", "Name": "Guest"},
                ]
            )

            result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    "host": "emby.local",
                    "port": 8096,
                    "ssl": False,
                    "api_key": "test-key",
                    "verify_ssl": True,
                },
            )

            # Select a user
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_USER_ID: "user-1"},
            )

            assert result["type"] is FlowResultType.CREATE_ENTRY
            assert result["data"][CONF_USER_ID] == "user-1"

    @pytest.mark.asyncio
    async def test_config_flow_skip_user_selection(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test skipping user selection uses no user context."""
        with (
            patch("custom_components.embymedia.config_flow.EmbyClient") as mock_client_class,
            patch(
                "custom_components.embymedia.async_setup_entry",
                return_value=True,
            ),
        ):
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.async_validate_connection = AsyncMock(return_value=True)
            mock_client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "server-123",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            mock_client.async_get_users = AsyncMock(
                return_value=[
                    {"Id": "user-1", "Name": "Admin"},
                ]
            )

            result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    "host": "emby.local",
                    "port": 8096,
                    "ssl": False,
                    "api_key": "test-key",
                    "verify_ssl": True,
                },
            )

            # Skip user selection (__none__ sentinel means admin context)
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {CONF_USER_ID: "__none__"},
            )

            assert result["type"] is FlowResultType.CREATE_ENTRY
            # Empty string user_id is not stored (admin context)
            assert CONF_USER_ID not in result["data"]


class TestCoordinatorUserContext:
    """Test coordinator with user context."""

    @pytest.mark.asyncio
    async def test_coordinator_has_user_id_property(
        self,
        hass: HomeAssistant,
        mock_config_entry: EmbyConfigEntry,
    ) -> None:
        """Test coordinator exposes user_id property."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_client = MagicMock()
        mock_client.async_get_sessions = AsyncMock(return_value=[])

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
            user_id="user-1",
        )

        assert coordinator.user_id == "user-1"

    @pytest.mark.asyncio
    async def test_coordinator_user_id_none_when_not_set(
        self,
        hass: HomeAssistant,
        mock_config_entry: EmbyConfigEntry,
    ) -> None:
        """Test coordinator user_id is None when not configured."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_client = MagicMock()
        mock_client.async_get_sessions = AsyncMock(return_value=[])

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        assert coordinator.user_id is None


class TestOptionsFlowUserSwitch:
    """Test user switching in options flow."""

    @pytest.mark.asyncio
    async def test_options_flow_shows_current_user(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test options flow shows current user selection."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "host": "emby.local",
                "port": 8096,
                "api_key": "test-key",
                CONF_USER_ID: "user-1",
            },
            options={},
            unique_id="server-123",
        )
        entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(entry.entry_id)

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"
        # Options flow should include user_id option
        schema = result["data_schema"]
        assert schema is not None
