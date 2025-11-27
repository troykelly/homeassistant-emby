"""Tests for device ID generation (Phase 13.8)."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.embymedia.const import get_ha_device_id


class TestDeviceIdGeneration:
    """Tests for get_ha_device_id function."""

    def test_returns_string(self) -> None:
        """Test that get_ha_device_id returns a string."""
        mock_hass = MagicMock()
        mock_hass.data = {"core.uuid": "test-uuid-12345"}

        device_id = get_ha_device_id(mock_hass)

        assert isinstance(device_id, str)

    def test_includes_homeassistant_prefix(self) -> None:
        """Test that device ID includes homeassistant prefix."""
        mock_hass = MagicMock()
        mock_hass.data = {"core.uuid": "test-uuid"}

        device_id = get_ha_device_id(mock_hass)

        assert device_id.startswith("homeassistant-")

    def test_includes_ha_uuid(self) -> None:
        """Test that device ID includes HA installation UUID."""
        mock_hass = MagicMock()
        mock_hass.data = {"core.uuid": "abc123"}

        device_id = get_ha_device_id(mock_hass)

        assert "abc123" in device_id
        assert device_id == "homeassistant-abc123"

    def test_handles_missing_uuid(self) -> None:
        """Test that missing UUID is handled gracefully."""
        mock_hass = MagicMock()
        mock_hass.data = {}

        device_id = get_ha_device_id(mock_hass)

        assert device_id == "homeassistant-unknown"

    def test_stable_across_calls(self) -> None:
        """Test that device ID is stable across multiple calls."""
        mock_hass = MagicMock()
        mock_hass.data = {"core.uuid": "stable-uuid"}

        device_id_1 = get_ha_device_id(mock_hass)
        device_id_2 = get_ha_device_id(mock_hass)

        assert device_id_1 == device_id_2


class TestPlaySessionIdGeneration:
    """Tests for play session ID generation."""

    def test_generate_play_session_id_returns_string(self) -> None:
        """Test that generate_play_session_id returns a string."""
        from custom_components.embymedia.const import generate_play_session_id

        session_id = generate_play_session_id()

        assert isinstance(session_id, str)

    def test_generate_play_session_id_unique(self) -> None:
        """Test that generated session IDs are unique."""
        from custom_components.embymedia.const import generate_play_session_id

        session_ids = [generate_play_session_id() for _ in range(100)]

        # All should be unique
        assert len(set(session_ids)) == 100

    def test_generate_play_session_id_format(self) -> None:
        """Test that session ID has expected format (UUID-like)."""
        from custom_components.embymedia.const import generate_play_session_id

        session_id = generate_play_session_id()

        # Should be a valid length for hex UUID
        assert len(session_id) == 32  # UUID without dashes
