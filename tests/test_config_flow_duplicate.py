"""Tests for config flow duplicate unique_id prevention.

This module tests that the config flow properly prevents creating entries
with duplicate unique IDs, especially in multi-step flows where the
unique_id check happens in an earlier step than entry creation.

Related Issues:
- #312 (Epic): Reinstallation fails with duplicate unique_id
- #314: Prevent duplicate unique_id config entry creation
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

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
from tests.conftest import add_coordinator_mocks


class TestDuplicateUniqueIdPrevention:
    """Tests for preventing duplicate unique_id entry creation (#314)."""

    @pytest.mark.asyncio
    async def test_final_check_prevents_duplicate_in_multi_step_flow(
        self,
        hass: HomeAssistant,
        mock_users: list[dict[str, Any]],
    ) -> None:
        """Test that final duplicate check prevents race condition.

        Scenario:
        1. Flow 1 starts and sets unique_id in step 1
        2. Flow 2 starts, connects to same server, gets same unique_id
        3. Flow 2 should abort when Flow 1's entry already exists

        This test ensures the abort happens even if the entry is created
        between the initial unique_id check and the final entry creation.

        Related: Issue #314
        """
        server_info = {
            "Id": "race-condition-server-123",
            "ServerName": "Race Condition Server",
            "Version": "4.9.2.0",
        }

        with patch(
            "custom_components.embymedia.config_flow.EmbyClient", autospec=True
        ) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(return_value=server_info)
            client.async_get_users = AsyncMock(return_value=mock_users)

            # Start Flow 1
            result1 = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            # Configure Flow 1 through connection step (sets unique_id)
            result1 = await hass.config_entries.flow.async_configure(
                result1["flow_id"],
                {
                    CONF_HOST: "emby1.local",
                    CONF_PORT: 8096,
                    CONF_SSL: False,
                    CONF_API_KEY: "key1",
                    CONF_VERIFY_SSL: True,
                },
            )
            assert result1["step_id"] == "user_select"

            # Start Flow 2 (simulating concurrent config attempt)
            result2 = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            # Configure Flow 2 through connection step (same server)
            result2 = await hass.config_entries.flow.async_configure(
                result2["flow_id"],
                {
                    CONF_HOST: "emby2.local",  # Different host, same server
                    CONF_PORT: 8096,
                    CONF_SSL: False,
                    CONF_API_KEY: "key2",
                    CONF_VERIFY_SSL: True,
                },
            )

            # Flow 2 should have already aborted since same unique_id
            assert result2["type"] is FlowResultType.ABORT
            assert result2["reason"] == "already_in_progress"

    @pytest.mark.asyncio
    async def test_entry_created_between_steps_blocks_completion(
        self,
        hass: HomeAssistant,
        mock_users: list[dict[str, Any]],
    ) -> None:
        """Test that an entry created between steps blocks flow completion.

        Scenario:
        1. Flow starts and passes unique_id check (no existing entry)
        2. Entry is created by another source (e.g., YAML import) before flow completes
        3. Flow should abort when trying to create entry

        This is the core race condition the fix addresses.

        Related: Issue #314
        """
        server_info = {
            "Id": "injected-entry-server-456",
            "ServerName": "Test Server",
            "Version": "4.9.2.0",
        }

        # Patch both config_flow and __init__ EmbyClient to prevent real network calls
        with (
            patch(
                "custom_components.embymedia.config_flow.EmbyClient", autospec=True
            ) as mock_client_class,
            patch(
                "custom_components.embymedia.EmbyClient", autospec=True
            ) as mock_init_client_class,
        ):
            # Setup config_flow client mock
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(return_value=server_info)
            client.async_get_users = AsyncMock(return_value=mock_users)

            # Setup __init__ client mock (for setup path if it triggers)
            init_client = mock_init_client_class.return_value
            init_client.async_validate_connection = AsyncMock(return_value=True)
            init_client.async_get_server_info = AsyncMock(return_value=server_info)
            init_client.async_get_sessions = AsyncMock(return_value=[])
            init_client.close = AsyncMock()
            init_client.base_url = "http://emby.local:8096"
            add_coordinator_mocks(init_client)

            # Start flow and get through connection step
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
            assert result["step_id"] == "user_select"

            # Simulate another entry being created with same unique_id
            # (e.g., from YAML import or parallel flow that completed faster)
            # Add as a MockConfigEntry but DON'T trigger setup
            injected_entry = MockConfigEntry(
                domain=DOMAIN,
                data={
                    CONF_HOST: "injected.local",
                    CONF_PORT: 8096,
                    CONF_SSL: False,
                    CONF_API_KEY: "injected-key",
                    CONF_VERIFY_SSL: True,
                },
                unique_id="injected-entry-server-456",
            )
            # Use add_to_hass which adds entry to registry without triggering setup
            injected_entry.add_to_hass(hass)

            # Complete user_select step
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"user_id": "__none__"},
            )
            assert result["step_id"] == "entity_options"

            # Complete entity_options - this should abort due to duplicate
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {},
            )

            # The flow MUST abort, not create a duplicate entry
            assert result["type"] is FlowResultType.ABORT
            assert result["reason"] == "already_configured"

            # Verify only the injected entry exists
            entries = hass.config_entries.async_entries(DOMAIN)
            assert len(entries) == 1
            assert entries[0].data[CONF_HOST] == "injected.local"

    @pytest.mark.asyncio
    async def test_no_duplicate_warning_in_normal_flow(
        self,
        hass: HomeAssistant,
        mock_server_info: dict[str, Any],
        mock_users: list[dict[str, Any]],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that normal flow completion doesn't trigger duplicate warning.

        A successful flow completion should not log any duplicate warnings.

        Related: Issue #314
        """
        with patch(
            "custom_components.embymedia.config_flow.EmbyClient", autospec=True
        ) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(return_value=mock_server_info)
            client.async_get_users = AsyncMock(return_value=mock_users)

            # Complete full flow
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

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"user_id": "__none__"},
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {},
            )

            # Should successfully create entry
            assert result["type"] is FlowResultType.CREATE_ENTRY

            # No duplicate-related warnings should be logged
            duplicate_warnings = [
                r
                for r in caplog.records
                if "duplicate" in r.message.lower() or "unique" in r.message.lower()
            ]
            assert len(duplicate_warnings) == 0

    @pytest.mark.asyncio
    async def test_reauth_flow_updates_existing_entry(
        self,
        hass: HomeAssistant,
        mock_server_info: dict[str, Any],
        mock_users: list[dict[str, Any]],
    ) -> None:
        """Test that reauth flow properly updates existing entry.

        Reauth should update the existing entry, not create a new one.

        Related: Issue #314
        """
        # Create existing entry
        existing_entry = MockConfigEntry(
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
        existing_entry.add_to_hass(hass)

        with patch(
            "custom_components.embymedia.config_flow.EmbyClient", autospec=True
        ) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(return_value=mock_server_info)
            client.async_get_users = AsyncMock(return_value=mock_users)

            # Start reauth flow
            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={
                    "source": config_entries.SOURCE_REAUTH,
                    "entry_id": existing_entry.entry_id,
                },
                data=existing_entry.data,
            )

            # Should show reauth form
            assert result["type"] is FlowResultType.FORM
            assert result["step_id"] == "reauth_confirm"

            # Complete reauth with new API key
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_API_KEY: "new-key",
                },
            )

            # Should abort with reauth_successful
            assert result["type"] is FlowResultType.ABORT
            assert result["reason"] == "reauth_successful"

            # Should still have only one entry
            entries = hass.config_entries.async_entries(DOMAIN)
            assert len(entries) == 1
            # The entry should have the new API key
            assert entries[0].data[CONF_API_KEY] == "new-key"
