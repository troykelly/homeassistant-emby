"""Tests for Emby integration setup."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.embymedia.const import (
    CONF_API_KEY,
    CONF_SCAN_INTERVAL,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EmbyRuntimeData,
)
from custom_components.embymedia.exceptions import (
    EmbyAuthenticationError,
    EmbyConnectionError,
)

from .conftest import (
    create_mock_library_coordinator,
    create_mock_server_coordinator,
    create_mock_session_coordinator,
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
        """Test entry sets up correctly with all coordinators."""
        mock_config_entry.add_to_hass(hass)

        session_coordinator = create_mock_session_coordinator()
        server_coordinator = create_mock_server_coordinator()
        library_coordinator = create_mock_library_coordinator()

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.EmbyDataUpdateCoordinator",
            ) as mock_session_coordinator_class,
            patch(
                "custom_components.embymedia.EmbyServerCoordinator",
            ) as mock_server_coordinator_class,
            patch(
                "custom_components.embymedia.EmbyLibraryCoordinator",
            ) as mock_library_coordinator_class,
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(return_value=mock_server_info)
            client.async_get_sessions = AsyncMock(return_value=[])

            mock_session_coordinator_class.return_value = session_coordinator
            mock_server_coordinator_class.return_value = server_coordinator
            mock_library_coordinator_class.return_value = library_coordinator

            result = await hass.config_entries.async_setup(mock_config_entry.entry_id)

            assert result is True
            assert mock_config_entry.state is ConfigEntryState.LOADED
            # Verify session coordinator was created with correct params
            mock_session_coordinator_class.assert_called_once()
            call_kwargs = mock_session_coordinator_class.call_args.kwargs
            assert call_kwargs["hass"] is hass
            assert call_kwargs["server_id"] == mock_server_info["Id"]
            assert call_kwargs["server_name"] == mock_server_info["ServerName"]
            # Verify runtime_data is EmbyRuntimeData with all coordinators
            assert isinstance(mock_config_entry.runtime_data, EmbyRuntimeData)
            assert mock_config_entry.runtime_data.session_coordinator is session_coordinator
            assert mock_config_entry.runtime_data.server_coordinator is server_coordinator
            assert mock_config_entry.runtime_data.library_coordinator is library_coordinator

    @pytest.mark.asyncio
    async def test_setup_entry_coordinator_first_refresh(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test all coordinator first refreshes are called during setup."""
        mock_config_entry.add_to_hass(hass)

        session_coordinator = create_mock_session_coordinator()
        server_coordinator = create_mock_server_coordinator()
        library_coordinator = create_mock_library_coordinator()

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.EmbyDataUpdateCoordinator",
            ) as mock_session_coordinator_class,
            patch(
                "custom_components.embymedia.EmbyServerCoordinator",
            ) as mock_server_coordinator_class,
            patch(
                "custom_components.embymedia.EmbyLibraryCoordinator",
            ) as mock_library_coordinator_class,
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(return_value=mock_server_info)

            mock_session_coordinator_class.return_value = session_coordinator
            mock_server_coordinator_class.return_value = server_coordinator
            mock_library_coordinator_class.return_value = library_coordinator

            await hass.config_entries.async_setup(mock_config_entry.entry_id)

            # All coordinators should have first refresh called
            session_coordinator.async_config_entry_first_refresh.assert_called_once()
            server_coordinator.async_config_entry_first_refresh.assert_called_once()
            library_coordinator.async_config_entry_first_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_entry_scan_interval_from_options(
        self,
        hass: HomeAssistant,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test scan interval is taken from options."""
        custom_scan_interval = 60
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Test Server",
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
            options={CONF_SCAN_INTERVAL: custom_scan_interval},
            unique_id="test-server-id",
        )
        entry.add_to_hass(hass)

        session_coordinator = create_mock_session_coordinator()
        server_coordinator = create_mock_server_coordinator()
        library_coordinator = create_mock_library_coordinator()

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.EmbyDataUpdateCoordinator",
            ) as mock_session_coordinator_class,
            patch(
                "custom_components.embymedia.EmbyServerCoordinator",
            ) as mock_server_coordinator_class,
            patch(
                "custom_components.embymedia.EmbyLibraryCoordinator",
            ) as mock_library_coordinator_class,
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(return_value=mock_server_info)

            mock_session_coordinator_class.return_value = session_coordinator
            mock_server_coordinator_class.return_value = server_coordinator
            mock_library_coordinator_class.return_value = library_coordinator

            await hass.config_entries.async_setup(entry.entry_id)

            call_kwargs = mock_session_coordinator_class.call_args.kwargs
            assert call_kwargs["scan_interval"] == custom_scan_interval

    @pytest.mark.asyncio
    async def test_setup_entry_default_scan_interval(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test default scan interval when not in options."""
        mock_config_entry.add_to_hass(hass)

        session_coordinator = create_mock_session_coordinator()
        server_coordinator = create_mock_server_coordinator()
        library_coordinator = create_mock_library_coordinator()

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.EmbyDataUpdateCoordinator",
            ) as mock_session_coordinator_class,
            patch(
                "custom_components.embymedia.EmbyServerCoordinator",
            ) as mock_server_coordinator_class,
            patch(
                "custom_components.embymedia.EmbyLibraryCoordinator",
            ) as mock_library_coordinator_class,
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(return_value=mock_server_info)

            mock_session_coordinator_class.return_value = session_coordinator
            mock_server_coordinator_class.return_value = server_coordinator
            mock_library_coordinator_class.return_value = library_coordinator

            await hass.config_entries.async_setup(mock_config_entry.entry_id)

            call_kwargs = mock_session_coordinator_class.call_args.kwargs
            assert call_kwargs["scan_interval"] == DEFAULT_SCAN_INTERVAL

    @pytest.mark.asyncio
    async def test_setup_entry_connection_failure(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test setup raises ConfigEntryNotReady on connection failure."""
        mock_config_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
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

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
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

        session_coordinator = create_mock_session_coordinator()
        server_coordinator = create_mock_server_coordinator()
        library_coordinator = create_mock_library_coordinator()

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.EmbyDataUpdateCoordinator",
            ) as mock_session_coordinator_class,
            patch(
                "custom_components.embymedia.EmbyServerCoordinator",
            ) as mock_server_coordinator_class,
            patch(
                "custom_components.embymedia.EmbyLibraryCoordinator",
            ) as mock_library_coordinator_class,
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(return_value=mock_server_info)

            mock_session_coordinator_class.return_value = session_coordinator
            mock_server_coordinator_class.return_value = server_coordinator
            mock_library_coordinator_class.return_value = library_coordinator

            await hass.config_entries.async_setup(mock_config_entry.entry_id)
            assert mock_config_entry.state is ConfigEntryState.LOADED

            result = await hass.config_entries.async_unload(mock_config_entry.entry_id)

            assert result is True
            assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


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

        session_coordinator = create_mock_session_coordinator()
        server_coordinator = create_mock_server_coordinator()
        library_coordinator = create_mock_library_coordinator()

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.EmbyDataUpdateCoordinator",
            ) as mock_session_coordinator_class,
            patch(
                "custom_components.embymedia.EmbyServerCoordinator",
            ) as mock_server_coordinator_class,
            patch(
                "custom_components.embymedia.EmbyLibraryCoordinator",
            ) as mock_library_coordinator_class,
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(return_value=mock_server_info)

            mock_session_coordinator_class.return_value = session_coordinator
            mock_server_coordinator_class.return_value = server_coordinator
            mock_library_coordinator_class.return_value = library_coordinator

            await hass.config_entries.async_setup(mock_config_entry.entry_id)
            assert mock_config_entry.state is ConfigEntryState.LOADED

            # Update options - this should trigger reload
            hass.config_entries.async_update_entry(mock_config_entry, options={"scan_interval": 30})
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

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.EmbyDataUpdateCoordinator",
            ) as mock_session_coordinator_class,
            patch(
                "custom_components.embymedia.EmbyServerCoordinator",
            ) as mock_server_coordinator_class,
            patch(
                "custom_components.embymedia.EmbyLibraryCoordinator",
            ) as mock_library_coordinator_class,
        ):
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

            # Create coordinators for each call
            def create_session_coord(*args: object, **kwargs: object) -> MagicMock:
                return create_mock_session_coordinator(
                    server_id=str(kwargs.get("server_id", "test")),
                    server_name=str(kwargs.get("server_name", "Test")),
                )

            def create_server_coord(*args: object, **kwargs: object) -> MagicMock:
                return create_mock_server_coordinator(
                    server_id=str(kwargs.get("server_id", "test")),
                    server_name=str(kwargs.get("server_name", "Test")),
                )

            def create_library_coord(*args: object, **kwargs: object) -> MagicMock:
                return create_mock_library_coordinator(
                    server_id=str(kwargs.get("server_id", "test")),
                )

            mock_session_coordinator_class.side_effect = create_session_coord
            mock_server_coordinator_class.side_effect = create_server_coord
            mock_library_coordinator_class.side_effect = create_library_coord

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
            # Both entries have EmbyRuntimeData with coordinators
            assert isinstance(entry1.runtime_data, EmbyRuntimeData)
            assert isinstance(entry2.runtime_data, EmbyRuntimeData)
            assert entry1.runtime_data.session_coordinator is not None
            assert entry2.runtime_data.session_coordinator is not None


class TestServerDeviceRegistration:
    """Test server device registration."""

    @pytest.mark.asyncio
    async def test_server_device_registered_before_entities(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test that the Emby server device is registered before entity setup.

        This fixes the via_device warning where entities reference
        a server device that doesn't exist yet.
        """
        from homeassistant.helpers import device_registry as dr

        mock_config_entry.add_to_hass(hass)

        session_coordinator = create_mock_session_coordinator()
        server_coordinator = create_mock_server_coordinator()
        library_coordinator = create_mock_library_coordinator()

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.EmbyDataUpdateCoordinator",
            ) as mock_session_coordinator_class,
            patch(
                "custom_components.embymedia.EmbyServerCoordinator",
            ) as mock_server_coordinator_class,
            patch(
                "custom_components.embymedia.EmbyLibraryCoordinator",
            ) as mock_library_coordinator_class,
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(return_value=mock_server_info)

            mock_session_coordinator_class.return_value = session_coordinator
            mock_server_coordinator_class.return_value = server_coordinator
            mock_library_coordinator_class.return_value = library_coordinator

            await hass.config_entries.async_setup(mock_config_entry.entry_id)

            # Verify server device was registered
            device_registry = dr.async_get(hass)
            server_device = device_registry.async_get_device(
                identifiers={(DOMAIN, mock_server_info["Id"])}
            )

            assert server_device is not None
            assert server_device.manufacturer == "Emby"
            assert server_device.model == "Emby Server"
            assert server_device.name == mock_server_info["ServerName"]
            assert server_device.sw_version == mock_server_info["Version"]

    @pytest.mark.asyncio
    async def test_server_device_has_config_entry(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test server device is linked to config entry."""
        from homeassistant.helpers import device_registry as dr

        mock_config_entry.add_to_hass(hass)

        session_coordinator = create_mock_session_coordinator()
        server_coordinator = create_mock_server_coordinator()
        library_coordinator = create_mock_library_coordinator()

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.EmbyDataUpdateCoordinator",
            ) as mock_session_coordinator_class,
            patch(
                "custom_components.embymedia.EmbyServerCoordinator",
            ) as mock_server_coordinator_class,
            patch(
                "custom_components.embymedia.EmbyLibraryCoordinator",
            ) as mock_library_coordinator_class,
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(return_value=mock_server_info)

            mock_session_coordinator_class.return_value = session_coordinator
            mock_server_coordinator_class.return_value = server_coordinator
            mock_library_coordinator_class.return_value = library_coordinator

            await hass.config_entries.async_setup(mock_config_entry.entry_id)

            device_registry = dr.async_get(hass)
            server_device = device_registry.async_get_device(
                identifiers={(DOMAIN, mock_server_info["Id"])}
            )

            assert server_device is not None
            assert mock_config_entry.entry_id in server_device.config_entries


class TestWebSocketSetup:
    """Test WebSocket setup during integration initialization."""

    @pytest.mark.asyncio
    async def test_setup_starts_websocket(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test WebSocket is started during setup."""
        mock_config_entry.add_to_hass(hass)

        session_coordinator = create_mock_session_coordinator()
        server_coordinator = create_mock_server_coordinator()
        library_coordinator = create_mock_library_coordinator()

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.EmbyDataUpdateCoordinator",
            ) as mock_session_coordinator_class,
            patch(
                "custom_components.embymedia.EmbyServerCoordinator",
            ) as mock_server_coordinator_class,
            patch(
                "custom_components.embymedia.EmbyLibraryCoordinator",
            ) as mock_library_coordinator_class,
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(return_value=mock_server_info)

            mock_session_coordinator_class.return_value = session_coordinator
            mock_server_coordinator_class.return_value = server_coordinator
            mock_library_coordinator_class.return_value = library_coordinator

            await hass.config_entries.async_setup(mock_config_entry.entry_id)

            # WebSocket setup should be called on session coordinator
            session_coordinator.async_setup_websocket.assert_called_once()

    @pytest.mark.asyncio
    async def test_unload_stops_websocket(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test WebSocket is stopped during unload."""
        mock_config_entry.add_to_hass(hass)

        session_coordinator = create_mock_session_coordinator()
        server_coordinator = create_mock_server_coordinator()
        library_coordinator = create_mock_library_coordinator()

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.EmbyDataUpdateCoordinator",
            ) as mock_session_coordinator_class,
            patch(
                "custom_components.embymedia.EmbyServerCoordinator",
            ) as mock_server_coordinator_class,
            patch(
                "custom_components.embymedia.EmbyLibraryCoordinator",
            ) as mock_library_coordinator_class,
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(return_value=mock_server_info)

            mock_session_coordinator_class.return_value = session_coordinator
            mock_server_coordinator_class.return_value = server_coordinator
            mock_library_coordinator_class.return_value = library_coordinator

            await hass.config_entries.async_setup(mock_config_entry.entry_id)
            assert mock_config_entry.state is ConfigEntryState.LOADED

            await hass.config_entries.async_unload(mock_config_entry.entry_id)

            # WebSocket shutdown should be called via on_unload callback
            session_coordinator.async_shutdown_websocket.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_succeeds_if_websocket_fails(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test integration setup succeeds even if WebSocket setup fails."""
        mock_config_entry.add_to_hass(hass)

        session_coordinator = create_mock_session_coordinator()
        # Make WebSocket setup fail
        session_coordinator.async_setup_websocket = AsyncMock(side_effect=Exception("WebSocket failed"))
        server_coordinator = create_mock_server_coordinator()
        library_coordinator = create_mock_library_coordinator()

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.EmbyDataUpdateCoordinator",
            ) as mock_session_coordinator_class,
            patch(
                "custom_components.embymedia.EmbyServerCoordinator",
            ) as mock_server_coordinator_class,
            patch(
                "custom_components.embymedia.EmbyLibraryCoordinator",
            ) as mock_library_coordinator_class,
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(return_value=mock_server_info)

            mock_session_coordinator_class.return_value = session_coordinator
            mock_server_coordinator_class.return_value = server_coordinator
            mock_library_coordinator_class.return_value = library_coordinator

            # Setup should still succeed
            result = await hass.config_entries.async_setup(mock_config_entry.entry_id)

            assert result is True
            assert mock_config_entry.state is ConfigEntryState.LOADED


class TestBackwardCompatibility:
    """Test backward compatibility with old runtime_data access."""

    @pytest.mark.asyncio
    async def test_coordinator_property_returns_session_coordinator(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test that runtime_data.coordinator returns session_coordinator for backward compatibility."""
        mock_config_entry.add_to_hass(hass)

        session_coordinator = create_mock_session_coordinator()
        server_coordinator = create_mock_server_coordinator()
        library_coordinator = create_mock_library_coordinator()

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.EmbyDataUpdateCoordinator",
            ) as mock_session_coordinator_class,
            patch(
                "custom_components.embymedia.EmbyServerCoordinator",
            ) as mock_server_coordinator_class,
            patch(
                "custom_components.embymedia.EmbyLibraryCoordinator",
            ) as mock_library_coordinator_class,
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(return_value=mock_server_info)

            mock_session_coordinator_class.return_value = session_coordinator
            mock_server_coordinator_class.return_value = server_coordinator
            mock_library_coordinator_class.return_value = library_coordinator

            await hass.config_entries.async_setup(mock_config_entry.entry_id)

            # The .coordinator property should return session_coordinator
            assert mock_config_entry.runtime_data.coordinator is session_coordinator
