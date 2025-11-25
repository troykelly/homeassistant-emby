"""Tests for Emby integration setup."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.emby.const import (
    CONF_API_KEY,
    CONF_VERIFY_SSL,
    DOMAIN,
)
from custom_components.emby.exceptions import (
    EmbyAuthenticationError,
    EmbyConnectionError,
)


class TestSetupEntry:
    """Test integration setup."""

    @pytest.mark.asyncio
    async def test_setup_entry_success(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test entry sets up correctly."""
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.emby.EmbyClient", autospec=True
        ) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(return_value=mock_server_info)

            result = await hass.config_entries.async_setup(mock_config_entry.entry_id)

            assert result is True
            assert mock_config_entry.state is ConfigEntryState.LOADED
            assert DOMAIN in hass.data
            assert mock_config_entry.entry_id in hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_setup_entry_connection_failure(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test setup raises ConfigEntryNotReady on connection failure."""
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.emby.EmbyClient", autospec=True
        ) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(
                side_effect=EmbyConnectionError("Connection refused")
            )

            result = await hass.config_entries.async_setup(mock_config_entry.entry_id)

            assert result is False
            assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY

    @pytest.mark.asyncio
    async def test_setup_entry_auth_failure(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test setup raises ConfigEntryAuthFailed on auth failure."""
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.emby.EmbyClient", autospec=True
        ) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(
                side_effect=EmbyAuthenticationError("Invalid API key")
            )

            result = await hass.config_entries.async_setup(mock_config_entry.entry_id)

            assert result is False
            assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR


class TestUnloadEntry:
    """Test integration unload."""

    @pytest.mark.asyncio
    async def test_unload_entry(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test entry unloads cleanly."""
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.emby.EmbyClient", autospec=True
        ) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(return_value=mock_server_info)

            await hass.config_entries.async_setup(mock_config_entry.entry_id)
            assert mock_config_entry.state is ConfigEntryState.LOADED

            result = await hass.config_entries.async_unload(mock_config_entry.entry_id)

            assert result is True
            assert mock_config_entry.state is ConfigEntryState.NOT_LOADED

    @pytest.mark.asyncio
    async def test_unload_entry_cleans_data(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test hass.data cleaned after unload."""
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.emby.EmbyClient", autospec=True
        ) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(return_value=mock_server_info)

            await hass.config_entries.async_setup(mock_config_entry.entry_id)
            assert DOMAIN in hass.data
            assert mock_config_entry.entry_id in hass.data[DOMAIN]

            await hass.config_entries.async_unload(mock_config_entry.entry_id)

            # Entry should be removed from hass.data
            assert mock_config_entry.entry_id not in hass.data.get(DOMAIN, {})


class TestOptionsUpdate:
    """Test options update handling."""

    @pytest.mark.asyncio
    async def test_options_update_reloads_entry(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test options update triggers reload."""
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.emby.EmbyClient", autospec=True
        ) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(return_value=mock_server_info)

            await hass.config_entries.async_setup(mock_config_entry.entry_id)
            assert mock_config_entry.state is ConfigEntryState.LOADED

            # Update options - this should trigger reload
            hass.config_entries.async_update_entry(
                mock_config_entry, options={"scan_interval": 30}
            )
            await hass.async_block_till_done()

            # Entry should be reloaded (still LOADED)
            assert mock_config_entry.state is ConfigEntryState.LOADED


class TestMultipleEntries:
    """Test multiple config entries."""

    @pytest.mark.asyncio
    async def test_multiple_entries(
        self,
        hass: HomeAssistant,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test multiple config entries supported."""
        server_info_1 = {**mock_server_info, "Id": "server-1", "ServerName": "Server 1"}
        server_info_2 = {**mock_server_info, "Id": "server-2", "ServerName": "Server 2"}

        with patch(
            "custom_components.emby.EmbyClient", autospec=True
        ) as mock_client_class:
            # Mock to return different info based on host
            def create_client(*args: object, **kwargs: object) -> MagicMock:
                client = MagicMock()
                client.async_validate_connection = AsyncMock(return_value=True)
                host = kwargs.get("host", "")
                if host == "server1.local":
                    client.async_get_server_info = AsyncMock(return_value=server_info_1)
                else:
                    client.async_get_server_info = AsyncMock(return_value=server_info_2)
                return client

            mock_client_class.side_effect = create_client

            # Create and add entries one at a time to ensure they setup properly
            entry1 = MockConfigEntry(
                domain=DOMAIN,
                title="Server 1",
                data={
                    CONF_HOST: "server1.local",
                    CONF_PORT: 8096,
                    CONF_SSL: False,
                    CONF_API_KEY: "key1",
                    CONF_VERIFY_SSL: True,
                },
                unique_id="server-1",
            )
            entry1.add_to_hass(hass)
            result1 = await hass.config_entries.async_setup(entry1.entry_id)

            entry2 = MockConfigEntry(
                domain=DOMAIN,
                title="Server 2",
                data={
                    CONF_HOST: "server2.local",
                    CONF_PORT: 8096,
                    CONF_SSL: False,
                    CONF_API_KEY: "key2",
                    CONF_VERIFY_SSL: True,
                },
                unique_id="server-2",
            )
            entry2.add_to_hass(hass)
            result2 = await hass.config_entries.async_setup(entry2.entry_id)

            assert result1 is True
            assert result2 is True
            assert entry1.state is ConfigEntryState.LOADED
            assert entry2.state is ConfigEntryState.LOADED
            assert entry1.entry_id in hass.data[DOMAIN]
            assert entry2.entry_id in hass.data[DOMAIN]
