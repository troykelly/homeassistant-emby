"""Tests for Emby diagnostics platform (Phase 9.4)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.embymedia.const import DOMAIN

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_config_entry() -> MagicMock:
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test-entry-id"
    entry.data = {
        "host": "emby.local",
        "port": 8096,
        "api_key": "secret-api-key-12345",
        "ssl": False,
        "verify_ssl": True,
        "user_id": "user-123",
    }
    entry.options = {"scan_interval": 10}
    return entry


@pytest.fixture
def mock_coordinator() -> MagicMock:
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.server_id = "server-abc123"
    coordinator.server_name = "Test Emby Server"
    coordinator.last_update_success_time = None
    coordinator.update_interval = MagicMock(__str__=lambda s: "0:00:10")
    coordinator.data = {}
    coordinator._websocket_enabled = False
    coordinator.client = MagicMock()
    coordinator.client.browse_cache = MagicMock()
    coordinator.client.browse_cache.get_stats.return_value = {
        "hits": 0,
        "misses": 0,
        "entries": 0,
    }
    return coordinator


@pytest.fixture
def mock_runtime_data(mock_coordinator: MagicMock) -> MagicMock:
    """Create a mock runtime data wrapper with session_coordinator."""
    runtime_data = MagicMock()
    runtime_data.session_coordinator = mock_coordinator
    return runtime_data


class TestConfigEntryDiagnostics:
    """Test config entry diagnostics."""

    @pytest.mark.asyncio
    async def test_diagnostics_redacts_api_key(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
        mock_runtime_data: MagicMock,
    ) -> None:
        """Test diagnostics redacts sensitive API key."""
        from custom_components.embymedia.diagnostics import (
            async_get_config_entry_diagnostics,
        )

        mock_config_entry.runtime_data = mock_runtime_data

        result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        # API key should be redacted
        assert result["config_entry"]["data"]["api_key"] == "**REDACTED**"
        # Other data should be present
        assert result["config_entry"]["data"]["host"] == "emby.local"
        assert result["config_entry"]["data"]["port"] == 8096

    @pytest.mark.asyncio
    async def test_diagnostics_includes_server_info(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
        mock_runtime_data: MagicMock,
    ) -> None:
        """Test diagnostics includes server information."""
        from custom_components.embymedia.diagnostics import (
            async_get_config_entry_diagnostics,
        )

        mock_config_entry.runtime_data = mock_runtime_data

        result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        assert "server_info" in result
        assert result["server_info"]["server_id"] == "server-abc123"
        assert result["server_info"]["server_name"] == "Test Emby Server"

    @pytest.mark.asyncio
    async def test_diagnostics_includes_connection_status(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
        mock_runtime_data: MagicMock,
    ) -> None:
        """Test diagnostics includes connection status."""
        from custom_components.embymedia.diagnostics import (
            async_get_config_entry_diagnostics,
        )

        mock_config_entry.runtime_data = mock_runtime_data

        result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        assert "connection_status" in result
        assert "websocket_enabled" in result["connection_status"]
        assert "update_interval" in result["connection_status"]

    @pytest.mark.asyncio
    async def test_diagnostics_includes_sessions(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
        mock_runtime_data: MagicMock,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test diagnostics includes session information."""
        from custom_components.embymedia.diagnostics import (
            async_get_config_entry_diagnostics,
        )

        # Add mock session data
        mock_session = MagicMock()
        mock_session.device_id = "device-123"
        mock_session.device_name = "Living Room TV"
        mock_session.client_name = "Emby Theater"
        mock_session.now_playing = None

        mock_coordinator.data = {"device-123": mock_session}
        mock_config_entry.runtime_data = mock_runtime_data

        result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        assert "sessions" in result
        assert result["sessions"]["active_count"] == 1
        assert len(result["sessions"]["sessions"]) == 1
        assert result["sessions"]["sessions"][0]["device_id"] == "device-123"
        assert result["sessions"]["sessions"][0]["device_name"] == "Living Room TV"

    @pytest.mark.asyncio
    async def test_diagnostics_includes_cache_stats(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
        mock_runtime_data: MagicMock,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test diagnostics includes cache statistics when available."""
        from custom_components.embymedia.diagnostics import (
            async_get_config_entry_diagnostics,
        )

        # Configure mock cache to return stats
        mock_coordinator.client.browse_cache.get_stats.return_value = {
            "hits": 100,
            "misses": 20,
            "entries": 50,
        }
        mock_config_entry.runtime_data = mock_runtime_data

        result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        assert "cache_stats" in result
        assert result["cache_stats"]["hits"] == 100
        assert result["cache_stats"]["misses"] == 20
        assert result["cache_stats"]["entries"] == 50

    @pytest.mark.asyncio
    async def test_diagnostics_handles_no_data(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
        mock_runtime_data: MagicMock,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test diagnostics handles missing coordinator data."""
        from custom_components.embymedia.diagnostics import (
            async_get_config_entry_diagnostics,
        )

        mock_coordinator.data = None
        mock_config_entry.runtime_data = mock_runtime_data

        result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

        assert result["sessions"]["active_count"] == 0
        assert result["sessions"]["sessions"] == []


class TestDeviceDiagnostics:
    """Test per-device diagnostics."""

    @pytest.mark.asyncio
    async def test_device_diagnostics_online(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
        mock_runtime_data: MagicMock,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test diagnostics for online device."""
        from custom_components.embymedia.diagnostics import (
            async_get_device_diagnostics,
        )

        # Create mock session
        mock_session = MagicMock()
        mock_session.device_id = "device-123"
        mock_session.device_name = "Living Room TV"
        mock_session.client_name = "Emby Theater"
        mock_session.app_version = "4.9.2.0"
        mock_session.supports_remote_control = True
        mock_session.supported_commands = ["Play", "Pause", "Stop"]
        mock_session.now_playing = None
        mock_session.play_state = MagicMock()
        mock_session.play_state.is_paused = False
        mock_session.play_state.volume_level = 80
        mock_session.play_state.is_muted = False

        mock_coordinator.data = {"device-123": mock_session}
        mock_config_entry.runtime_data = mock_runtime_data

        # Mock device
        mock_device = MagicMock()
        mock_device.identifiers = {(DOMAIN, "device-123")}

        result = await async_get_device_diagnostics(hass, mock_config_entry, mock_device)

        assert result["status"] == "online"
        assert result["device_name"] == "Living Room TV"
        assert result["client"] == "Emby Theater"
        assert result["supports_remote_control"] is True

    @pytest.mark.asyncio
    async def test_device_diagnostics_offline(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
        mock_runtime_data: MagicMock,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test diagnostics for offline device."""
        from custom_components.embymedia.diagnostics import (
            async_get_device_diagnostics,
        )

        mock_coordinator.data = {}  # Empty - device not active
        mock_config_entry.runtime_data = mock_runtime_data

        # Mock device
        mock_device = MagicMock()
        mock_device.identifiers = {(DOMAIN, "device-123")}

        result = await async_get_device_diagnostics(hass, mock_config_entry, mock_device)

        assert result["device_id"] == "device-123"
        assert result["status"] == "offline"

    @pytest.mark.asyncio
    async def test_device_diagnostics_not_found(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
        mock_runtime_data: MagicMock,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test diagnostics when device not found."""
        from custom_components.embymedia.diagnostics import (
            async_get_device_diagnostics,
        )

        mock_coordinator.data = {}
        mock_config_entry.runtime_data = mock_runtime_data

        # Mock device with unknown identifier
        mock_device = MagicMock()
        mock_device.identifiers = {("other_domain", "unknown")}

        result = await async_get_device_diagnostics(hass, mock_config_entry, mock_device)

        assert result["error"] == "Device not found"

    @pytest.mark.asyncio
    async def test_device_diagnostics_with_playback(
        self,
        hass: HomeAssistant,
        mock_config_entry: MagicMock,
        mock_runtime_data: MagicMock,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test diagnostics includes now playing info."""
        from custom_components.embymedia.diagnostics import (
            async_get_device_diagnostics,
        )

        # Create mock now playing item
        mock_now_playing = MagicMock()
        mock_now_playing.item_id = "item-456"
        mock_now_playing.name = "Test Movie"
        mock_now_playing.media_type = MagicMock()
        mock_now_playing.media_type.value = "Movie"

        # Create mock session
        mock_session = MagicMock()
        mock_session.device_id = "device-123"
        mock_session.device_name = "Living Room TV"
        mock_session.client_name = "Emby Theater"
        mock_session.app_version = "4.9.2.0"
        mock_session.supports_remote_control = True
        mock_session.supported_commands = ["Play", "Pause"]
        mock_session.now_playing = mock_now_playing
        mock_session.play_state = MagicMock()
        mock_session.play_state.is_paused = False
        mock_session.play_state.volume_level = 100
        mock_session.play_state.is_muted = False

        mock_coordinator.data = {"device-123": mock_session}
        mock_config_entry.runtime_data = mock_runtime_data

        # Mock device
        mock_device = MagicMock()
        mock_device.identifiers = {(DOMAIN, "device-123")}

        result = await async_get_device_diagnostics(hass, mock_config_entry, mock_device)

        assert result["now_playing"] is not None
        assert result["now_playing"]["item_id"] == "item-456"
        assert result["now_playing"]["name"] == "Test Movie"
        assert result["now_playing"]["type"] == "Movie"
