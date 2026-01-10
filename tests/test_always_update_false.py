"""Tests for always_update=False on all coordinators (Issue #295).

These tests verify that all DataUpdateCoordinators are configured with
always_update=False to prevent unnecessary entity updates and state writes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestEmbyDataUpdateCoordinatorAlwaysUpdate:
    """Tests for EmbyDataUpdateCoordinator always_update setting."""

    @pytest.mark.asyncio
    async def test_coordinator_has_always_update_false(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that EmbyDataUpdateCoordinator has always_update=False."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_client = MagicMock()
        mock_client.async_get_sessions = AsyncMock(return_value=[])

        mock_entry = MagicMock()
        mock_entry.options = {}

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            config_entry=mock_entry,
            server_id="test-server",
            server_name="Test Server",
        )

        # Verify always_update is False
        assert coordinator.always_update is False


class TestEmbyServerCoordinatorAlwaysUpdate:
    """Tests for EmbyServerCoordinator always_update setting."""

    @pytest.mark.asyncio
    async def test_server_coordinator_has_always_update_false(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that EmbyServerCoordinator has always_update=False."""
        from custom_components.embymedia.coordinator_sensors import (
            EmbyServerCoordinator,
        )

        mock_client = MagicMock()
        mock_entry = MagicMock()

        coordinator = EmbyServerCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            server_name="Test Server",
            config_entry=mock_entry,
        )

        # Verify always_update is False
        assert coordinator.always_update is False


class TestEmbyLibraryCoordinatorAlwaysUpdate:
    """Tests for EmbyLibraryCoordinator always_update setting."""

    @pytest.mark.asyncio
    async def test_library_coordinator_has_always_update_false(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that EmbyLibraryCoordinator has always_update=False."""
        from custom_components.embymedia.coordinator_sensors import (
            EmbyLibraryCoordinator,
        )

        mock_client = MagicMock()
        mock_entry = MagicMock()

        coordinator = EmbyLibraryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            config_entry=mock_entry,
        )

        # Verify always_update is False
        assert coordinator.always_update is False


class TestEmbyDiscoveryCoordinatorAlwaysUpdate:
    """Tests for EmbyDiscoveryCoordinator always_update setting."""

    @pytest.mark.asyncio
    async def test_discovery_coordinator_has_always_update_false(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that EmbyDiscoveryCoordinator has always_update=False."""
        from custom_components.embymedia.coordinator_discovery import (
            EmbyDiscoveryCoordinator,
        )

        mock_client = MagicMock()
        mock_entry = MagicMock()

        coordinator = EmbyDiscoveryCoordinator(
            hass=hass,
            client=mock_client,
            server_id="test-server",
            config_entry=mock_entry,
            user_id="test-user-id",
        )

        # Verify always_update is False
        assert coordinator.always_update is False
