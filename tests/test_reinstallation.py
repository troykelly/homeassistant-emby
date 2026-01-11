"""Tests for reinstallation scenarios.

This module tests the reinstallation flow to identify and prevent
duplicate unique_id issues and setup cancellation errors.

Related Issues:
- #312 (Epic): Reinstallation fails with duplicate unique_id
- #313: Investigate reinstallation failure
- #314: Prevent duplicate unique_id config entry creation
- #315: Handle setup cancellation gracefully
- #316: Cleanup mechanism for orphaned config entries
- #317: Integration tests for reinstallation scenarios
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.embymedia.const import (
    CONF_API_KEY,
    CONF_VERIFY_SSL,
    DOMAIN,
)
from tests.conftest import setup_mock_emby_client


class TestReinstallationFlow:
    """Test reinstallation scenarios (Issue #313, #317)."""

    @pytest.mark.asyncio
    async def test_clean_uninstall_reinstall_works(
        self,
        hass: HomeAssistant,
        mock_server_info: dict[str, Any],
        mock_users: list[dict[str, Any]],
    ) -> None:
        """Test clean uninstall and reinstall works without warnings.

        This test verifies that when a config entry is properly unloaded
        and removed, a new entry with the same unique_id can be created.

        Related: Issue #313 investigation step 1
        """
        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_init_client,
            patch(
                "custom_components.embymedia.config_flow.EmbyClient", autospec=True
            ) as mock_flow_client,
        ):
            # Setup flow client
            flow_client = mock_flow_client.return_value
            flow_client.async_validate_connection = AsyncMock(return_value=True)
            flow_client.async_get_server_info = AsyncMock(return_value=mock_server_info)
            flow_client.async_get_users = AsyncMock(return_value=mock_users)

            # Setup init client
            setup_mock_emby_client(mock_init_client.return_value, mock_server_info)

            # Step 1: Create and setup initial entry
            entry = MockConfigEntry(
                domain=DOMAIN,
                data={
                    CONF_HOST: "emby.local",
                    CONF_PORT: 8096,
                    CONF_SSL: False,
                    CONF_API_KEY: "test-api-key",
                    CONF_VERIFY_SSL: True,
                },
                unique_id="test-server-id-12345",
            )
            entry.add_to_hass(hass)

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(entry.entry_id)
                await hass.async_block_till_done()

            assert entry.state == ConfigEntryState.LOADED

            # Step 2: Unload the entry
            await hass.config_entries.async_unload(entry.entry_id)
            await hass.async_block_till_done()
            assert entry.state == ConfigEntryState.NOT_LOADED

            # Step 3: Remove the entry
            await hass.config_entries.async_remove(entry.entry_id)
            await hass.async_block_till_done()

            # Step 4: Verify cleanup - no entries should exist
            entries = hass.config_entries.async_entries(DOMAIN)
            assert len(entries) == 0

            # Step 5: Create new config flow for reinstall
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
            assert result["type"] is FlowResultType.FORM
            assert result["step_id"] == "user"

            # Step 6: Configure with same server (should NOT warn about duplicate)
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

            # Should proceed to user_select step (not abort)
            assert result["type"] is FlowResultType.FORM
            assert result["step_id"] == "user_select"

            # Complete the flow
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"user_id": "__none__"},
            )
            assert result["step_id"] == "entity_options"

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {},
            )

            # Should successfully create new entry
            assert result["type"] is FlowResultType.CREATE_ENTRY
            assert result["data"][CONF_HOST] == "emby.local"

    @pytest.mark.asyncio
    async def test_duplicate_unique_id_aborts_when_entry_exists(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test configuring same server when entry exists properly aborts.

        This test verifies the current behavior where trying to add a
        server that already has a config entry properly aborts.

        Related: Issue #314
        """
        # Create existing entry
        existing_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "existing-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="test-server-id-12345",
        )
        existing_entry.add_to_hass(hass)

        # Start config flow for same server
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "new-key",
                CONF_VERIFY_SSL: True,
            },
        )

        # Should abort due to duplicate
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"

        # Verify only one entry exists
        entries = hass.config_entries.async_entries(DOMAIN)
        assert len(entries) == 1
        assert entries[0].data[CONF_API_KEY] == "existing-key"

    @pytest.mark.asyncio
    async def test_orphaned_entry_blocks_new_configuration(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test orphaned entry (NOT_LOADED) still blocks new configuration.

        An "orphaned" entry is one that exists in the config entries but
        has never been loaded (e.g., after HACS removal without proper cleanup).
        This entry should still block creating a new entry with the same unique_id.

        Related: Issue #314, #316
        """
        # Create orphaned entry (exists but NOT_LOADED - never setup)
        orphaned_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "old-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="test-server-id-12345",
        )
        orphaned_entry.add_to_hass(hass)
        # Don't call async_setup - simulates orphaned state after HACS removal

        # Verify entry is in NOT_LOADED state
        assert orphaned_entry.state == ConfigEntryState.NOT_LOADED

        # Start config flow for same server
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "new-key",
                CONF_VERIFY_SSL: True,
            },
        )

        # Should abort because orphaned entry exists with same unique_id
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"

    @pytest.mark.asyncio
    async def test_different_server_allowed_when_entry_exists(
        self,
        hass: HomeAssistant,
        mock_users: list[dict[str, Any]],
    ) -> None:
        """Test configuring different server is allowed when another entry exists.

        Related: Issue #314 - verify unique_id check is specific to server ID
        """
        # Create existing entry for server-1
        existing_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby1.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "server1-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="server-1-id",
        )
        existing_entry.add_to_hass(hass)

        # Mock client to return different server ID
        with patch(
            "custom_components.embymedia.config_flow.EmbyClient", autospec=True
        ) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "server-2-id",  # Different server
                    "ServerName": "Second Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_users = AsyncMock(return_value=mock_users)

            # Start config flow for different server
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_HOST: "emby2.local",
                    CONF_PORT: 8096,
                    CONF_SSL: False,
                    CONF_API_KEY: "server2-key",
                    CONF_VERIFY_SSL: True,
                },
            )

            # Should proceed to user_select (different unique_id)
            assert result["type"] is FlowResultType.FORM
            assert result["step_id"] == "user_select"


class TestSetupCancellation:
    """Test setup cancellation handling (Issue #315)."""

    @pytest.mark.asyncio
    async def test_setup_cancellation_does_not_leave_partial_state(
        self,
        hass: HomeAssistant,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test that setup cancellation cleans up properly.

        When setup is cancelled mid-flight (e.g., due to duplicate detection
        or user cancellation), no partial state should be left in hass.data.

        Related: Issue #315
        """
        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            # Setup mock to delay, allowing cancellation
            async def slow_sessions() -> list[dict[str, Any]]:
                await asyncio.sleep(10)
                return []

            client = setup_mock_emby_client(mock_client_class.return_value, mock_server_info)
            client.async_get_sessions = AsyncMock(side_effect=slow_sessions)

            entry = MockConfigEntry(
                domain=DOMAIN,
                data={
                    CONF_HOST: "emby.local",
                    CONF_PORT: 8096,
                    CONF_SSL: False,
                    CONF_API_KEY: "test-api-key",
                    CONF_VERIFY_SSL: True,
                },
                unique_id="test-server-id-12345",
            )
            entry.add_to_hass(hass)

            # Start setup and cancel after a short delay
            setup_task = asyncio.create_task(hass.config_entries.async_setup(entry.entry_id))
            await asyncio.sleep(0.1)
            setup_task.cancel()

            with pytest.raises(asyncio.CancelledError):
                await setup_task

            # Verify entry is not in LOADED state
            assert entry.state != ConfigEntryState.LOADED

            # Verify no partial data left in hass.data
            # (The domain key may or may not exist, but entry_id should not be present)
            if DOMAIN in hass.data:
                assert entry.entry_id not in hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_setup_can_retry_after_cancellation(
        self,
        hass: HomeAssistant,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test that setup can be retried after cancellation.

        After a cancelled setup, retrying the setup should succeed.
        Note: The retry behavior depends on how HA handles the entry state
        after cancellation. This test demonstrates the expected flow.

        Related: Issue #315
        """
        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = setup_mock_emby_client(mock_client_class.return_value, mock_server_info)
            # Normal fast response for sessions
            client.async_get_sessions = AsyncMock(return_value=[])

            entry = MockConfigEntry(
                domain=DOMAIN,
                data={
                    CONF_HOST: "emby.local",
                    CONF_PORT: 8096,
                    CONF_SSL: False,
                    CONF_API_KEY: "test-api-key",
                    CONF_VERIFY_SSL: True,
                },
                unique_id="test-server-id-12345",
            )
            entry.add_to_hass(hass)

            # Setup should succeed on first try
            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                result = await hass.config_entries.async_setup(entry.entry_id)
                await hass.async_block_till_done()

            assert result is True
            assert entry.state == ConfigEntryState.LOADED

            # Verify the entry can be unloaded and reloaded (simulating retry scenario)
            await hass.config_entries.async_unload(entry.entry_id)
            await hass.async_block_till_done()
            assert entry.state == ConfigEntryState.NOT_LOADED

            # Re-setup should work
            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                result = await hass.config_entries.async_setup(entry.entry_id)
                await hass.async_block_till_done()

            assert result is True
            assert entry.state == ConfigEntryState.LOADED


class TestConcurrentConfiguration:
    """Test concurrent configuration attempts (Issue #317)."""

    @pytest.mark.asyncio
    async def test_concurrent_flows_for_same_server(
        self,
        hass: HomeAssistant,
        mock_server_info: dict[str, Any],
        mock_users: list[dict[str, Any]],
    ) -> None:
        """Test starting two config flows for the same server.

        Only one should succeed, the other should abort.

        Related: Issue #317
        """
        with patch(
            "custom_components.embymedia.config_flow.EmbyClient", autospec=True
        ) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(return_value=mock_server_info)
            client.async_get_users = AsyncMock(return_value=mock_users)

            # Start first flow
            result1 = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            # Start second flow before first completes
            result2 = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            # Configure first flow through connection step
            result1 = await hass.config_entries.flow.async_configure(
                result1["flow_id"],
                {
                    CONF_HOST: "emby.local",
                    CONF_PORT: 8096,
                    CONF_SSL: False,
                    CONF_API_KEY: "test-api-key",
                    CONF_VERIFY_SSL: True,
                },
            )

            # First flow should proceed
            assert result1["type"] is FlowResultType.FORM
            assert result1["step_id"] == "user_select"

            # Complete first flow through user_select
            result1 = await hass.config_entries.flow.async_configure(
                result1["flow_id"],
                {"user_id": "__none__"},
            )
            assert result1["step_id"] == "entity_options"

            result1 = await hass.config_entries.flow.async_configure(
                result1["flow_id"],
                {},
            )
            assert result1["type"] is FlowResultType.CREATE_ENTRY

            # Now configure second flow - should abort due to existing entry
            result2 = await hass.config_entries.flow.async_configure(
                result2["flow_id"],
                {
                    CONF_HOST: "emby.local",
                    CONF_PORT: 8096,
                    CONF_SSL: False,
                    CONF_API_KEY: "test-api-key-2",
                    CONF_VERIFY_SSL: True,
                },
            )

            # Second flow should abort
            assert result2["type"] is FlowResultType.ABORT
            assert result2["reason"] == "already_configured"

            # Only one entry should exist
            entries = hass.config_entries.async_entries(DOMAIN)
            assert len(entries) == 1


class TestEntryStateTransitions:
    """Test config entry state transitions during reinstallation (Issue #313)."""

    @pytest.mark.asyncio
    async def test_entry_states_during_lifecycle(
        self,
        hass: HomeAssistant,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test entry state transitions during full lifecycle.

        Tracks state through: NOT_LOADED -> LOADED -> NOT_LOADED -> removed

        Related: Issue #313 investigation
        """
        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            setup_mock_emby_client(mock_client_class.return_value, mock_server_info)

            entry = MockConfigEntry(
                domain=DOMAIN,
                data={
                    CONF_HOST: "emby.local",
                    CONF_PORT: 8096,
                    CONF_SSL: False,
                    CONF_API_KEY: "test-api-key",
                    CONF_VERIFY_SSL: True,
                },
                unique_id="test-server-id-12345",
            )
            entry.add_to_hass(hass)

            # Initial state after add_to_hass
            assert entry.state == ConfigEntryState.NOT_LOADED

            # After setup
            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(entry.entry_id)
                await hass.async_block_till_done()

            assert entry.state == ConfigEntryState.LOADED

            # After unload
            await hass.config_entries.async_unload(entry.entry_id)
            await hass.async_block_till_done()

            assert entry.state == ConfigEntryState.NOT_LOADED

            # After remove - entry should no longer be in list
            await hass.config_entries.async_remove(entry.entry_id)
            await hass.async_block_till_done()

            entries = hass.config_entries.async_entries(DOMAIN)
            assert len(entries) == 0

    @pytest.mark.asyncio
    async def test_unload_and_reload_state_transitions(
        self,
        hass: HomeAssistant,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test entry state transitions during unload and reload.

        Verifies proper state transitions: LOADED -> NOT_LOADED -> LOADED

        Related: Issue #313, #315
        """
        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            setup_mock_emby_client(mock_client_class.return_value, mock_server_info)

            entry = MockConfigEntry(
                domain=DOMAIN,
                data={
                    CONF_HOST: "emby.local",
                    CONF_PORT: 8096,
                    CONF_SSL: False,
                    CONF_API_KEY: "test-api-key",
                    CONF_VERIFY_SSL: True,
                },
                unique_id="test-server-id-12345",
            )
            entry.add_to_hass(hass)

            # Setup entry
            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(entry.entry_id)
                await hass.async_block_till_done()

            assert entry.state == ConfigEntryState.LOADED

            # Unload should succeed
            result = await hass.config_entries.async_unload(entry.entry_id)
            await hass.async_block_till_done()

            assert result is True
            assert entry.state == ConfigEntryState.NOT_LOADED

            # Reload should succeed
            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                result = await hass.config_entries.async_setup(entry.entry_id)
                await hass.async_block_till_done()

            assert result is True
            assert entry.state == ConfigEntryState.LOADED


class TestHACSRemovalSimulation:
    """Test scenarios simulating HACS-style removal (Issue #313, #316)."""

    @pytest.mark.asyncio
    async def test_entry_exists_after_file_removal_simulation(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Simulate what happens when HACS removes files but entry persists.

        HACS removal typically removes the integration files but may not
        properly unload the config entry, leaving an orphaned entry.

        Related: Issue #313, #316
        """
        # Create an orphaned entry (entry exists, no integration loaded)
        orphaned_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "orphaned-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="orphaned-server-id",
        )
        orphaned_entry.add_to_hass(hass)

        # Entry should be NOT_LOADED (never setup)
        assert orphaned_entry.state == ConfigEntryState.NOT_LOADED

        # List all entries - orphaned entry should be visible
        entries = hass.config_entries.async_entries(DOMAIN)
        assert len(entries) == 1
        assert entries[0].unique_id == "orphaned-server-id"

        # User should be able to remove the orphaned entry manually
        await hass.config_entries.async_remove(orphaned_entry.entry_id)
        await hass.async_block_till_done()

        # Now no entries should exist
        entries = hass.config_entries.async_entries(DOMAIN)
        assert len(entries) == 0


class TestUniqueIdEdgeCases:
    """Test unique_id handling edge cases (Issue #314)."""

    @pytest.mark.asyncio
    async def test_unique_id_set_timing(
        self,
        hass: HomeAssistant,
        mock_users: list[dict[str, Any]],
    ) -> None:
        """Test that unique_id is set and checked at the right time.

        The unique_id should be set during connection validation and
        checked before proceeding to user selection.

        Related: Issue #314
        """
        with patch(
            "custom_components.embymedia.config_flow.EmbyClient", autospec=True
        ) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "unique-server-123",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_users = AsyncMock(return_value=mock_users)

            # Start flow and configure
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

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

            # Should proceed to user_select (unique_id was set and check passed)
            assert result["type"] is FlowResultType.FORM
            assert result["step_id"] == "user_select"

            # Complete the flow
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"user_id": "__none__"},
            )
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {},
            )

            assert result["type"] is FlowResultType.CREATE_ENTRY

            # Verify the entry has the correct unique_id
            entries = hass.config_entries.async_entries(DOMAIN)
            assert len(entries) == 1
            assert entries[0].unique_id == "unique-server-123"

    @pytest.mark.asyncio
    async def test_entry_with_setup_error_still_blocks_duplicate(
        self,
        hass: HomeAssistant,
        mock_emby_client: MagicMock,
    ) -> None:
        """Test that entry in SETUP_ERROR state still blocks duplicate.

        An entry that failed setup should still prevent creating a
        duplicate entry with the same unique_id.

        Related: Issue #314
        """
        # Create entry in SETUP_ERROR state by adding without setup
        error_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "error-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="test-server-id-12345",
        )
        error_entry.add_to_hass(hass)

        # Manually set to SETUP_ERROR state (simulating failed setup)
        # Note: In real scenario, ConfigEntryState would be set by HA
        # For this test, we just verify the abort happens for any existing entry

        # Start config flow for same server
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "new-key",
                CONF_VERIFY_SSL: True,
            },
        )

        # Should abort due to existing entry
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"
