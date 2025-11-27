"""Tests for MediaSource transcoding session management (Phase 13.7)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.embymedia.media_source import EmbyMediaSource

if TYPE_CHECKING:
    pass


class TestSessionTracking:
    """Tests for transcoding session tracking."""

    def test_init_creates_empty_sessions_dict(self) -> None:
        """Test that __init__ creates empty _active_sessions dict."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)
        media_source.__init__(MagicMock())  # type: ignore[misc]

        assert hasattr(media_source, "_active_sessions")
        assert media_source._active_sessions == {}

    def test_register_session_adds_to_dict(self) -> None:
        """Test registering a transcoding session."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)
        media_source.hass = MagicMock()
        media_source._active_sessions = {}

        media_source.register_session("play-session-123", "device-abc")

        assert "play-session-123" in media_source._active_sessions
        assert media_source._active_sessions["play-session-123"] == "device-abc"

    def test_unregister_session_removes_from_dict(self) -> None:
        """Test unregistering a transcoding session."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)
        media_source._active_sessions = {"play-session-123": "device-abc"}

        media_source.unregister_session("play-session-123")

        assert "play-session-123" not in media_source._active_sessions

    def test_unregister_nonexistent_session_no_error(self) -> None:
        """Test unregistering a non-existent session doesn't raise."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)
        media_source._active_sessions = {}

        # Should not raise
        media_source.unregister_session("nonexistent")

    def test_get_active_sessions_returns_copy(self) -> None:
        """Test getting active sessions returns a copy."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)
        media_source._active_sessions = {"session-1": "device-1", "session-2": "device-2"}

        sessions = media_source.get_active_sessions()

        assert sessions == {"session-1": "device-1", "session-2": "device-2"}
        # Should be a copy, not the same dict
        sessions["session-3"] = "device-3"
        assert "session-3" not in media_source._active_sessions


class TestSessionCleanup:
    """Tests for session cleanup on unload."""

    @pytest.mark.asyncio
    async def test_cleanup_sessions_stops_all_active(self) -> None:
        """Test cleanup_sessions stops all active transcoding sessions."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)
        media_source._active_sessions = {
            "session-1": "device-1",
            "session-2": "device-2",
        }

        mock_coordinator = MagicMock()
        mock_coordinator.client.async_stop_transcoding = AsyncMock()

        await media_source.async_cleanup_sessions(mock_coordinator)

        # Should have called stop_transcoding for each session
        assert mock_coordinator.client.async_stop_transcoding.call_count == 2
        # Sessions should be cleared
        assert media_source._active_sessions == {}

    @pytest.mark.asyncio
    async def test_cleanup_sessions_handles_errors_gracefully(self) -> None:
        """Test cleanup continues even if one stop fails."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)
        media_source._active_sessions = {
            "session-1": "device-1",
            "session-2": "device-2",
        }

        mock_coordinator = MagicMock()
        # First call fails, second succeeds
        mock_coordinator.client.async_stop_transcoding = AsyncMock(
            side_effect=[Exception("Network error"), None]
        )

        # Should not raise
        await media_source.async_cleanup_sessions(mock_coordinator)

        # Should still try both sessions
        assert mock_coordinator.client.async_stop_transcoding.call_count == 2
        # Sessions should be cleared even if errors occurred
        assert media_source._active_sessions == {}

    @pytest.mark.asyncio
    async def test_cleanup_sessions_empty_does_nothing(self) -> None:
        """Test cleanup with no active sessions does nothing."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)
        media_source._active_sessions = {}

        mock_coordinator = MagicMock()
        mock_coordinator.client.async_stop_transcoding = AsyncMock()

        await media_source.async_cleanup_sessions(mock_coordinator)

        mock_coordinator.client.async_stop_transcoding.assert_not_called()
