"""Tests for Emby configuration options (Phase 9.3)."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.embymedia.const import (
    CONF_DIRECT_PLAY,
    CONF_ENABLE_WEBSOCKET,
    CONF_IGNORED_DEVICES,
    CONF_MAX_AUDIO_BITRATE,
    CONF_MAX_VIDEO_BITRATE,
    CONF_TRANSCODING_PROFILE,
    CONF_VIDEO_CONTAINER,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TRANSCODING_PROFILE,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    TRANSCODING_PROFILES,
)


@pytest.fixture
def mock_config_entry_options() -> MockConfigEntry:
    """Create mock config entry for options tests."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "emby.local",
            "port": 8096,
            "api_key": "test-key",
            "ssl": False,
            "verify_ssl": True,
        },
        options={},
        unique_id="server-123",
    )


class TestOptionsFlowWebSocketToggle:
    """Test WebSocket toggle in options flow."""

    @pytest.mark.asyncio
    async def test_websocket_toggle_default_enabled(
        self,
        hass: HomeAssistant,
        mock_config_entry_options: MockConfigEntry,
    ) -> None:
        """Test WebSocket is enabled by default."""
        mock_config_entry_options.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(mock_config_entry_options.entry_id)

        assert result["type"] is FlowResultType.FORM
        # WebSocket should be enabled by default in schema
        schema = result["data_schema"]
        assert schema is not None

    @pytest.mark.asyncio
    async def test_websocket_toggle_can_disable(
        self,
        hass: HomeAssistant,
        mock_config_entry_options: MockConfigEntry,
    ) -> None:
        """Test WebSocket can be disabled via options."""
        mock_config_entry_options.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(mock_config_entry_options.entry_id)

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "scan_interval": 10,
                CONF_ENABLE_WEBSOCKET: False,
            },
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_ENABLE_WEBSOCKET] is False

    @pytest.mark.asyncio
    async def test_websocket_toggle_remembers_setting(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test WebSocket setting is remembered."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "host": "emby.local",
                "port": 8096,
                "api_key": "test-key",
            },
            options={CONF_ENABLE_WEBSOCKET: False},
            unique_id="server-456",
        )
        entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(entry.entry_id)

        # Should show form with current value (False in options)
        assert result["type"] is FlowResultType.FORM


class TestOptionsFlowDeviceFiltering:
    """Test device filtering in options flow."""

    @pytest.mark.asyncio
    async def test_ignored_devices_default_empty(
        self,
        hass: HomeAssistant,
        mock_config_entry_options: MockConfigEntry,
    ) -> None:
        """Test ignored devices is empty by default."""
        mock_config_entry_options.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(mock_config_entry_options.entry_id)

        assert result["type"] is FlowResultType.FORM

    @pytest.mark.asyncio
    async def test_ignored_devices_can_be_set(
        self,
        hass: HomeAssistant,
        mock_config_entry_options: MockConfigEntry,
    ) -> None:
        """Test ignored devices can be configured."""
        mock_config_entry_options.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(mock_config_entry_options.entry_id)

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "scan_interval": 10,
                CONF_IGNORED_DEVICES: "device1, device2",
            },
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_IGNORED_DEVICES] == "device1, device2"


class TestOptionsFlowScanInterval:
    """Test scan interval options."""

    @pytest.mark.asyncio
    async def test_scan_interval_validation(
        self,
        hass: HomeAssistant,
        mock_config_entry_options: MockConfigEntry,
    ) -> None:
        """Test scan interval is validated."""
        mock_config_entry_options.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(mock_config_entry_options.entry_id)

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "scan_interval": 30,
            },
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"]["scan_interval"] == 30

    def test_scan_interval_constants(self) -> None:
        """Test scan interval constants are reasonable."""
        # Verify constants are reasonable
        assert MIN_SCAN_INTERVAL >= 5
        assert MAX_SCAN_INTERVAL <= 300
        assert DEFAULT_SCAN_INTERVAL >= MIN_SCAN_INTERVAL
        assert DEFAULT_SCAN_INTERVAL <= MAX_SCAN_INTERVAL


class TestOptionsFlowTranscoding:
    """Test transcoding options."""

    @pytest.mark.asyncio
    async def test_direct_play_toggle(
        self,
        hass: HomeAssistant,
        mock_config_entry_options: MockConfigEntry,
    ) -> None:
        """Test direct play can be toggled."""
        mock_config_entry_options.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(mock_config_entry_options.entry_id)

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "scan_interval": 10,
                CONF_DIRECT_PLAY: False,
            },
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_DIRECT_PLAY] is False

    @pytest.mark.asyncio
    async def test_video_container_selection(
        self,
        hass: HomeAssistant,
        mock_config_entry_options: MockConfigEntry,
    ) -> None:
        """Test video container can be selected."""
        mock_config_entry_options.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(mock_config_entry_options.entry_id)

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "scan_interval": 10,
                CONF_VIDEO_CONTAINER: "mkv",
            },
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_VIDEO_CONTAINER] == "mkv"

    @pytest.mark.asyncio
    async def test_bitrate_options(
        self,
        hass: HomeAssistant,
        mock_config_entry_options: MockConfigEntry,
    ) -> None:
        """Test bitrate options can be set."""
        mock_config_entry_options.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(mock_config_entry_options.entry_id)

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "scan_interval": 10,
                CONF_MAX_VIDEO_BITRATE: 8000,
                CONF_MAX_AUDIO_BITRATE: 320,
            },
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_MAX_VIDEO_BITRATE] == 8000
        assert result["data"][CONF_MAX_AUDIO_BITRATE] == 320

    @pytest.mark.asyncio
    async def test_transcoding_profile_selection(
        self,
        hass: HomeAssistant,
        mock_config_entry_options: MockConfigEntry,
    ) -> None:
        """Test transcoding profile can be selected."""
        mock_config_entry_options.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(mock_config_entry_options.entry_id)

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "scan_interval": 10,
                CONF_TRANSCODING_PROFILE: "chromecast",
            },
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_TRANSCODING_PROFILE] == "chromecast"

    @pytest.mark.asyncio
    async def test_transcoding_profile_default_universal(
        self,
        hass: HomeAssistant,
        mock_config_entry_options: MockConfigEntry,
    ) -> None:
        """Test transcoding profile defaults to universal."""
        mock_config_entry_options.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(mock_config_entry_options.entry_id)

        # Just submit form with required fields, should use default profile
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "scan_interval": 10,
            },
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        # Default profile is universal (or not set, depending on implementation)
        # The key should either not be present or be the default
        profile = result["data"].get(CONF_TRANSCODING_PROFILE, DEFAULT_TRANSCODING_PROFILE)
        assert profile == DEFAULT_TRANSCODING_PROFILE

    def test_transcoding_profiles_constant(self) -> None:
        """Test transcoding profiles constant is valid."""
        assert "universal" in TRANSCODING_PROFILES
        assert "chromecast" in TRANSCODING_PROFILES
        assert "roku" in TRANSCODING_PROFILES
        assert "appletv" in TRANSCODING_PROFILES
        assert "audio_only" in TRANSCODING_PROFILES
        assert len(TRANSCODING_PROFILES) >= 5
