"""Integration tests for reinstallation scenarios.

This module provides comprehensive integration tests to verify that
reinstallation, uninstallation, and recovery scenarios work correctly.

Related Issues:
- #312 (Epic): Reinstallation fails with duplicate unique_id
- #317: Add integration tests for reinstallation scenarios
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.embymedia.const import (
    CONF_API_KEY,
    CONF_VERIFY_SSL,
    DOMAIN,
)
from tests.conftest import add_coordinator_mocks


class TestCleanReinstallFlow:
    """Test clean uninstall and reinstall scenarios (#317)."""

    @pytest.mark.asyncio
    async def test_full_install_unload_remove_reinstall_cycle(
        self,
        hass: HomeAssistant,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test complete cycle: install → configure → unload → remove → reinstall.

        This is the most important reinstallation test - verifies the entire
        lifecycle works without issues.

        Related: Issue #317
        """
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="full-cycle-server-123",
            title="Full Cycle Test Server",
        )
        entry.add_to_hass(hass)

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ),
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(return_value=mock_server_info)
            client.async_get_sessions = AsyncMock(return_value=[])
            client.async_get_users = AsyncMock(return_value=[])
            client.close = AsyncMock()
            client.base_url = "http://emby.local:8096"
            client.api_key = "test-key"
            add_coordinator_mocks(client)

            # Step 1: Initial setup
            await async_setup_component(hass, DOMAIN, {})
            await hass.async_block_till_done()
            assert entry.state == ConfigEntryState.LOADED, "Initial setup should succeed"

            # Step 2: Unload
            unload_result = await hass.config_entries.async_unload(entry.entry_id)
            await hass.async_block_till_done()
            assert unload_result is True, "Unload should succeed"
            assert entry.state == ConfigEntryState.NOT_LOADED, "Entry should be unloaded"

            # Step 3: Remove
            await hass.config_entries.async_remove(entry.entry_id)
            await hass.async_block_till_done()
            entries = hass.config_entries.async_entries(DOMAIN)
            assert len(entries) == 0, "Entry should be removed"

            # Step 4: Reinstall with same unique_id
            new_entry = MockConfigEntry(
                domain=DOMAIN,
                data={
                    CONF_HOST: "emby.local",
                    CONF_PORT: 8096,
                    CONF_SSL: False,
                    CONF_API_KEY: "test-key",
                    CONF_VERIFY_SSL: True,
                },
                unique_id="full-cycle-server-123",  # Same unique_id
                title="Reinstalled Server",
            )
            new_entry.add_to_hass(hass)

            # Step 5: Setup reinstalled entry
            setup_result = await hass.config_entries.async_setup(new_entry.entry_id)
            await hass.async_block_till_done()
            assert setup_result is True, "Reinstall setup should succeed"
            assert new_entry.state == ConfigEntryState.LOADED, "Reinstalled entry should be loaded"

    @pytest.mark.asyncio
    async def test_reinstall_different_server(
        self,
        hass: HomeAssistant,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test replacing one server with another (different unique_id).

        Related: Issue #317
        """
        old_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "old-emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "old-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="old-server-111",
            title="Old Server",
        )
        old_entry.add_to_hass(hass)

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ),
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(return_value=mock_server_info)
            client.async_get_sessions = AsyncMock(return_value=[])
            client.async_get_users = AsyncMock(return_value=[])
            client.close = AsyncMock()
            client.base_url = "http://emby.local:8096"
            client.api_key = "test-key"
            add_coordinator_mocks(client)

            # Setup old entry
            await async_setup_component(hass, DOMAIN, {})
            await hass.async_block_till_done()
            assert old_entry.state == ConfigEntryState.LOADED

            # Remove old entry
            await hass.config_entries.async_unload(old_entry.entry_id)
            await hass.config_entries.async_remove(old_entry.entry_id)
            await hass.async_block_till_done()

            # Add new entry with different unique_id
            new_entry = MockConfigEntry(
                domain=DOMAIN,
                data={
                    CONF_HOST: "new-emby.local",
                    CONF_PORT: 8096,
                    CONF_SSL: False,
                    CONF_API_KEY: "new-key",
                    CONF_VERIFY_SSL: True,
                },
                unique_id="new-server-222",  # Different unique_id
                title="New Server",
            )
            new_entry.add_to_hass(hass)

            # Setup new entry - should succeed
            setup_result = await hass.config_entries.async_setup(new_entry.entry_id)
            await hass.async_block_till_done()
            assert setup_result is True
            assert new_entry.state == ConfigEntryState.LOADED


class TestConcurrentConfigurationAttempts:
    """Test concurrent configuration attempts (#317)."""

    @pytest.mark.asyncio
    async def test_second_flow_aborts_when_entry_exists(
        self,
        hass: HomeAssistant,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test starting config flow when entry already exists aborts.

        This tests the scenario where a user tries to add the same server
        that's already configured.

        Related: Issue #317
        """
        # First, create an existing entry
        existing_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="test-server-id-12345",
            title="Existing Server",
        )
        existing_entry.add_to_hass(hass)

        with (
            patch(
                "custom_components.embymedia.config_flow.EmbyClient", autospec=True
            ) as mock_client_class,
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_init_client,
            patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ),
        ):
            # Setup mocks
            for mock_client in [mock_client_class.return_value, mock_init_client.return_value]:
                mock_client.async_validate_connection = AsyncMock(return_value=True)
                mock_client.async_get_server_info = AsyncMock(return_value=mock_server_info)
                mock_client.async_get_sessions = AsyncMock(return_value=[])
                mock_client.async_get_users = AsyncMock(return_value=[])
                mock_client.close = AsyncMock()
                mock_client.base_url = "http://emby.local:8096"
                mock_client.api_key = "test-key"
                add_coordinator_mocks(mock_client)

            # Setup existing entry
            await async_setup_component(hass, DOMAIN, {})
            await hass.async_block_till_done()
            assert existing_entry.state == ConfigEntryState.LOADED

            # Start a new flow trying to add same server
            result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
            assert result["type"] == "form"

            # Try to configure with same server
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_HOST: "emby.local",
                    CONF_PORT: 8096,
                    CONF_SSL: False,
                    CONF_API_KEY: "test-key",
                    CONF_VERIFY_SSL: True,
                },
            )

            # Should abort because server already configured
            assert result["type"] == "abort"
            assert result["reason"] == "already_configured"


class TestPartialUnloadRecovery:
    """Test recovery from partial unload scenarios (#317)."""

    @pytest.mark.asyncio
    async def test_unload_after_websocket_setup_fails(
        self,
        hass: HomeAssistant,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test unload works even if websocket setup partially failed.

        Related: Issue #317
        """
        from custom_components.embymedia.exceptions import EmbyWebSocketError

        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="partial-websocket-server",
            title="Partial WebSocket Server",
        )
        entry.add_to_hass(hass)

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
                side_effect=EmbyWebSocketError("WebSocket setup failed"),
            ),
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(return_value=mock_server_info)
            client.async_get_sessions = AsyncMock(return_value=[])
            client.async_get_users = AsyncMock(return_value=[])
            client.close = AsyncMock()
            client.base_url = "http://emby.local:8096"
            client.api_key = "test-key"
            add_coordinator_mocks(client)

            # Setup should still succeed (websocket is optional)
            await async_setup_component(hass, DOMAIN, {})
            await hass.async_block_till_done()
            assert entry.state == ConfigEntryState.LOADED

            # Unload should work cleanly
            unload_result = await hass.config_entries.async_unload(entry.entry_id)
            await hass.async_block_till_done()
            assert unload_result is True
            assert entry.state == ConfigEntryState.NOT_LOADED

    @pytest.mark.asyncio
    async def test_reload_after_partial_state(
        self,
        hass: HomeAssistant,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test reload works when entry was in partial state.

        Related: Issue #317
        """
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="partial-state-server",
            title="Partial State Server",
        )
        entry.add_to_hass(hass)

        call_count = 0

        async def fail_first_validation() -> bool:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                from custom_components.embymedia.exceptions import EmbyConnectionError

                raise EmbyConnectionError("First attempt fails")
            return True

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ),
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(side_effect=fail_first_validation)
            client.async_get_server_info = AsyncMock(return_value=mock_server_info)
            client.async_get_sessions = AsyncMock(return_value=[])
            client.async_get_users = AsyncMock(return_value=[])
            client.close = AsyncMock()
            client.base_url = "http://emby.local:8096"
            client.api_key = "test-key"
            add_coordinator_mocks(client)

            # First setup fails
            await async_setup_component(hass, DOMAIN, {})
            await hass.async_block_till_done()
            assert entry.state == ConfigEntryState.SETUP_RETRY

            # Reset for retry
            client.async_validate_connection.side_effect = None
            client.async_validate_connection.return_value = True

            # Reload should succeed
            await hass.config_entries.async_reload(entry.entry_id)
            await hass.async_block_till_done()
            assert entry.state == ConfigEntryState.LOADED


class TestMultipleServersReinstall:
    """Test reinstallation with multiple configured servers (#317)."""

    @pytest.mark.asyncio
    async def test_remove_one_server_keep_another(
        self,
        hass: HomeAssistant,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test removing one server doesn't affect another.

        Related: Issue #317
        """
        server1_info = {**mock_server_info, "Id": "server-1-id", "ServerName": "Server 1"}
        server2_info = {**mock_server_info, "Id": "server-2-id", "ServerName": "Server 2"}

        entry1 = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby1.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "key1",
                CONF_VERIFY_SSL: True,
            },
            unique_id="server-1-id",
            title="Server 1",
        )
        entry2 = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby2.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "key2",
                CONF_VERIFY_SSL: True,
            },
            unique_id="server-2-id",
            title="Server 2",
        )
        entry1.add_to_hass(hass)
        entry2.add_to_hass(hass)

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ),
        ):
            # Track which entry is being setup
            def get_mock_server_info(entry_host: str) -> dict[str, Any]:
                if "emby1" in entry_host:
                    return server1_info
                return server2_info

            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(side_effect=lambda: server1_info)
            client.async_get_sessions = AsyncMock(return_value=[])
            client.async_get_users = AsyncMock(return_value=[])
            client.close = AsyncMock()
            client.base_url = "http://emby.local:8096"
            client.api_key = "test-key"
            add_coordinator_mocks(client)

            # Setup both entries
            await async_setup_component(hass, DOMAIN, {})
            await hass.async_block_till_done()

            # Both should be loaded
            assert entry1.state == ConfigEntryState.LOADED
            assert entry2.state == ConfigEntryState.LOADED

            # Remove server 1
            await hass.config_entries.async_unload(entry1.entry_id)
            await hass.config_entries.async_remove(entry1.entry_id)
            await hass.async_block_till_done()

            # Server 2 should still be loaded
            assert entry2.state == ConfigEntryState.LOADED

            # Only one entry remaining
            entries = hass.config_entries.async_entries(DOMAIN)
            assert len(entries) == 1
            assert entries[0].unique_id == "server-2-id"


class TestEdgeCases:
    """Test edge cases in reinstallation (#317)."""

    @pytest.mark.asyncio
    async def test_rapid_install_uninstall_cycles(
        self,
        hass: HomeAssistant,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test rapid install/uninstall cycles don't cause issues.

        Related: Issue #317
        """
        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ),
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(return_value=mock_server_info)
            client.async_get_sessions = AsyncMock(return_value=[])
            client.async_get_users = AsyncMock(return_value=[])
            client.close = AsyncMock()
            client.base_url = "http://emby.local:8096"
            client.api_key = "test-key"
            add_coordinator_mocks(client)

            await async_setup_component(hass, DOMAIN, {})

            # Do 3 rapid install/uninstall cycles
            for i in range(3):
                entry = MockConfigEntry(
                    domain=DOMAIN,
                    data={
                        CONF_HOST: "emby.local",
                        CONF_PORT: 8096,
                        CONF_SSL: False,
                        CONF_API_KEY: "test-key",
                        CONF_VERIFY_SSL: True,
                    },
                    unique_id=f"rapid-cycle-{i}",
                    title=f"Rapid Cycle {i}",
                )
                entry.add_to_hass(hass)

                # Setup
                await hass.config_entries.async_setup(entry.entry_id)
                await hass.async_block_till_done()
                assert entry.state == ConfigEntryState.LOADED

                # Unload and remove
                await hass.config_entries.async_unload(entry.entry_id)
                await hass.config_entries.async_remove(entry.entry_id)
                await hass.async_block_till_done()

            # Should have no entries left
            entries = hass.config_entries.async_entries(DOMAIN)
            assert len(entries) == 0

    @pytest.mark.asyncio
    async def test_reinstall_after_config_change(
        self,
        hass: HomeAssistant,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test reinstall works with changed config (same server, different settings).

        Related: Issue #317
        """
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "old-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="config-change-server",
            title="Config Change Server",
        )
        entry.add_to_hass(hass)

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ),
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(return_value=mock_server_info)
            client.async_get_sessions = AsyncMock(return_value=[])
            client.async_get_users = AsyncMock(return_value=[])
            client.close = AsyncMock()
            client.base_url = "http://emby.local:8096"
            client.api_key = "test-key"
            add_coordinator_mocks(client)

            # Initial setup
            await async_setup_component(hass, DOMAIN, {})
            await hass.async_block_till_done()
            assert entry.state == ConfigEntryState.LOADED

            # Remove
            await hass.config_entries.async_unload(entry.entry_id)
            await hass.config_entries.async_remove(entry.entry_id)
            await hass.async_block_till_done()

            # Reinstall with different config (new API key, SSL enabled)
            new_entry = MockConfigEntry(
                domain=DOMAIN,
                data={
                    CONF_HOST: "emby.local",
                    CONF_PORT: 8920,  # Different port (HTTPS)
                    CONF_SSL: True,  # SSL enabled
                    CONF_API_KEY: "new-key",  # New API key
                    CONF_VERIFY_SSL: True,
                },
                unique_id="config-change-server",  # Same unique_id
                title="Config Change Server (Updated)",
            )
            new_entry.add_to_hass(hass)

            # Setup with new config should work
            await hass.config_entries.async_setup(new_entry.entry_id)
            await hass.async_block_till_done()
            assert new_entry.state == ConfigEntryState.LOADED
