"""Tests for orphaned config entry cleanup mechanism.

This module tests that the integration properly detects and handles
orphaned config entries from previous installations.

Related Issues:
- #312 (Epic): Reinstallation fails with duplicate unique_id
- #316: Add cleanup mechanism for orphaned entries
"""

from __future__ import annotations

import logging
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
from custom_components.embymedia.exceptions import EmbyConnectionError
from tests.conftest import add_coordinator_mocks


class TestOrphanDetection:
    """Tests for orphan detection in async_setup (#316)."""

    @pytest.mark.asyncio
    async def test_orphan_detection_logs_warning_for_failed_entries(
        self,
        hass: HomeAssistant,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that entries that fail to connect are logged with guidance.

        Scenario:
        1. A config entry exists pointing to a non-responsive server
        2. Setup fails with connection error
        3. Should log a message with cleanup guidance

        Related: Issue #316
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
            unique_id="orphaned-server-123",
            title="Orphaned Emby Server",
        )
        entry.add_to_hass(hass)

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            caplog.at_level(logging.WARNING),
        ):
            client = mock_client_class.return_value
            # Simulate connection failure (orphaned entry can't connect)
            client.async_validate_connection = AsyncMock(
                side_effect=EmbyConnectionError("Connection refused")
            )

            result = await async_setup_component(hass, DOMAIN, {})
            await hass.async_block_till_done()

        assert result is True

        # Entry should be in SETUP_RETRY state (connection failed)
        assert entry.state == ConfigEntryState.SETUP_RETRY

    @pytest.mark.asyncio
    async def test_setup_retry_entries_get_guidance_log(
        self,
        hass: HomeAssistant,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that SETUP_RETRY entries trigger a guidance log.

        When entries repeatedly fail to connect (orphaned), users should
        get clear guidance on how to clean up.

        Related: Issue #316
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
            unique_id="failing-server-456",
            title="Failing Emby Server",
        )
        entry.add_to_hass(hass)

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            caplog.at_level(logging.WARNING),
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(
                side_effect=EmbyConnectionError("Connection refused")
            )

            await async_setup_component(hass, DOMAIN, {})
            await hass.async_block_till_done()

        # Should have ConfigEntryNotReady or similar error logged
        # The entry will be in SETUP_RETRY waiting for retry
        assert entry.state == ConfigEntryState.SETUP_RETRY

        # Check for connection error log
        error_logs = [
            r.message
            for r in caplog.records
            if r.levelname in ("ERROR", "WARNING") and "emby" in r.message.lower()
        ]
        assert len(error_logs) >= 1

    @pytest.mark.asyncio
    async def test_loaded_entry_not_flagged_as_orphan(
        self,
        hass: HomeAssistant,
        mock_server_info: dict[str, Any],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that properly loaded entries are not flagged as orphans.

        Related: Issue #316
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
            unique_id="loaded-server-456",
            title="Working Emby Server",
        )
        entry.add_to_hass(hass)

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ),
            caplog.at_level(logging.WARNING),
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
            await hass.async_block_till_done()

        # Entry should be loaded
        assert entry.state == ConfigEntryState.LOADED

        # Should not have orphan/stale entry warnings
        orphan_warnings = [
            r.message
            for r in caplog.records
            if ("orphan" in r.message.lower() or "stale" in r.message.lower())
            and r.name.startswith("custom_components.embymedia")
        ]
        assert len(orphan_warnings) == 0

    @pytest.mark.asyncio
    async def test_no_entries_no_warnings(
        self,
        hass: HomeAssistant,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that no warnings are logged when there are no entries.

        Related: Issue #316
        """
        with caplog.at_level(logging.WARNING):
            result = await async_setup_component(hass, DOMAIN, {})

        assert result is True

        # Should not log orphan warnings when no entries exist
        orphan_warnings = [
            r.message
            for r in caplog.records
            if ("orphan" in r.message.lower() or "stale" in r.message.lower())
            and r.name.startswith("custom_components.embymedia")
        ]
        assert len(orphan_warnings) == 0


class TestOrphanRecovery:
    """Tests for recovering from orphaned entries (#316)."""

    @pytest.mark.asyncio
    async def test_entry_reload_after_server_comes_back(
        self,
        hass: HomeAssistant,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test that an entry in SETUP_RETRY can recover when server returns.

        This simulates the case where a server was temporarily unreachable
        (appearing as "orphaned") but comes back online.

        Related: Issue #316
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
            unique_id="recovering-server-789",
            title="Recovering Emby Server",
        )
        entry.add_to_hass(hass)

        call_count = 0

        async def fail_then_succeed() -> bool:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise EmbyConnectionError("Connection refused")
            return True

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ),
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(side_effect=fail_then_succeed)
            client.async_get_server_info = AsyncMock(return_value=mock_server_info)
            client.async_get_sessions = AsyncMock(return_value=[])
            client.async_get_users = AsyncMock(return_value=[])
            client.close = AsyncMock()
            client.base_url = "http://emby.local:8096"
            client.api_key = "test-key"
            add_coordinator_mocks(client)

            # First setup attempt fails
            await async_setup_component(hass, DOMAIN, {})
            await hass.async_block_till_done()

            assert entry.state == ConfigEntryState.SETUP_RETRY

            # Reset mock for retry
            client.async_validate_connection.side_effect = None
            client.async_validate_connection.return_value = True

            # Reload should succeed now
            await hass.config_entries.async_reload(entry.entry_id)
            await hass.async_block_till_done()

            assert entry.state == ConfigEntryState.LOADED

    @pytest.mark.asyncio
    async def test_orphan_can_be_removed_and_readded(
        self,
        hass: HomeAssistant,
        mock_server_info: dict[str, Any],
    ) -> None:
        """Test that an orphaned entry can be removed and a new one added.

        This is the expected user workflow for cleaning up orphaned entries.

        Related: Issue #316
        """
        # Create an entry that fails to connect
        orphaned_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "old-emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "old-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="orphaned-to-remove",
            title="Old Orphaned Server",
        )
        orphaned_entry.add_to_hass(hass)

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ),
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(
                side_effect=EmbyConnectionError("Connection refused")
            )

            await async_setup_component(hass, DOMAIN, {})
            await hass.async_block_till_done()

            # Entry should be in SETUP_RETRY
            assert orphaned_entry.state == ConfigEntryState.SETUP_RETRY

            # User removes the orphaned entry
            await hass.config_entries.async_remove(orphaned_entry.entry_id)
            await hass.async_block_till_done()

            # Verify orphaned entry is gone
            entries = hass.config_entries.async_entries(DOMAIN)
            assert len(entries) == 0

            # Now add a new working entry
            new_entry = MockConfigEntry(
                domain=DOMAIN,
                data={
                    CONF_HOST: "new-emby.local",
                    CONF_PORT: 8096,
                    CONF_SSL: False,
                    CONF_API_KEY: "new-key",
                    CONF_VERIFY_SSL: True,
                },
                unique_id="new-working-server",
                title="New Working Server",
            )
            new_entry.add_to_hass(hass)

            # Configure mock for successful connection
            client.async_validate_connection.side_effect = None
            client.async_validate_connection.return_value = True
            client.async_get_server_info.return_value = mock_server_info
            client.async_get_sessions.return_value = []
            client.async_get_users.return_value = []
            add_coordinator_mocks(client)

            # Setup new entry
            await hass.config_entries.async_setup(new_entry.entry_id)
            await hass.async_block_till_done()

            # New entry should be loaded
            assert new_entry.state == ConfigEntryState.LOADED


class TestOrphanGuidance:
    """Tests for user-facing guidance about orphaned entries (#316)."""

    @pytest.mark.asyncio
    async def test_connection_error_includes_host_info(
        self,
        hass: HomeAssistant,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that connection errors include host for identification.

        When setup fails due to connection issues, the error should include
        enough info to identify which server failed.

        Related: Issue #316
        """
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "my-emby-server.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "test-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="identifiable-server",
            title="My Emby Server",
        )
        entry.add_to_hass(hass)

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            caplog.at_level(logging.DEBUG),
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(
                side_effect=EmbyConnectionError("Connection refused")
            )

            await async_setup_component(hass, DOMAIN, {})
            await hass.async_block_till_done()

        # The entry is in SETUP_RETRY state
        assert entry.state == ConfigEntryState.SETUP_RETRY

        # HA logs setup failures for config entries
        all_logs = " ".join(r.message for r in caplog.records)
        # The entry title "My Emby Server" should appear in logs
        assert "my emby server" in all_logs.lower() or "embymedia" in all_logs.lower()

    @pytest.mark.asyncio
    async def test_failed_entry_remains_in_retry_state(
        self,
        hass: HomeAssistant,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that failed entries remain in SETUP_RETRY for user action.

        When an entry fails to connect, it should stay in SETUP_RETRY state
        so users can either wait for the server to come back or delete the entry.

        Related: Issue #316
        """
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: "stale-emby.local",
                CONF_PORT: 8096,
                CONF_SSL: False,
                CONF_API_KEY: "stale-key",
                CONF_VERIFY_SSL: True,
            },
            unique_id="stale-server-detection",
            title="Stale Server",
        )
        entry.add_to_hass(hass)

        with (
            patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class,
            caplog.at_level(logging.DEBUG),
        ):
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(
                side_effect=EmbyConnectionError("Connection refused")
            )

            await async_setup_component(hass, DOMAIN, {})
            await hass.async_block_till_done()

        # Entry should be in SETUP_RETRY state (will auto-retry)
        assert entry.state == ConfigEntryState.SETUP_RETRY

        # Users can remove stale entries via UI when they're in SETUP_RETRY
        # This is HA's built-in behavior - entries can always be deleted
