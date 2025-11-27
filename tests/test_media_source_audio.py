"""Tests for MediaSource audio universal endpoint (Phase 13.9)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from homeassistant.components.media_source import MediaSourceItem

from custom_components.embymedia.media_source import EmbyMediaSource

if TYPE_CHECKING:
    pass


def create_media_item(identifier: str) -> MediaSourceItem:
    """Create a mock MediaSourceItem with the given identifier."""
    item = MagicMock(spec=MediaSourceItem)
    item.identifier = identifier
    return item


class TestAudioUniversalEndpoint:
    """Tests for audio resolution using universal endpoint."""

    @pytest.mark.asyncio
    async def test_audio_resolution_uses_universal_endpoint(self) -> None:
        """Test that audio resolution uses the universal audio endpoint."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)
        media_source.hass = MagicMock()
        media_source.hass.data = {"core.uuid": "test-uuid"}
        media_source._active_sessions = {}

        mock_coordinator = MagicMock()
        mock_coordinator.client.get_universal_audio_url.return_value = (
            "http://emby.local:8096/Audio/123/universal?api_key=xyz"
        )
        mock_coordinator.config_entry.options = {}

        # Patch _get_coordinator to return our mock
        media_source._get_coordinator = MagicMock(return_value=mock_coordinator)

        # Create a media source item for audio
        item = create_media_item("server-123/track/audio-item-456")

        result = await media_source.async_resolve_media(item)

        # Verify universal audio URL was used
        mock_coordinator.client.get_universal_audio_url.assert_called_once()
        call_kwargs = mock_coordinator.client.get_universal_audio_url.call_args
        assert call_kwargs.kwargs["item_id"] == "audio-item-456"
        assert "device_id" in call_kwargs.kwargs
        assert result.url == "http://emby.local:8096/Audio/123/universal?api_key=xyz"

    @pytest.mark.asyncio
    async def test_audio_resolution_includes_device_id(self) -> None:
        """Test that audio resolution includes HA device ID."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)
        media_source.hass = MagicMock()
        media_source.hass.data = {"core.uuid": "my-ha-uuid"}
        media_source._active_sessions = {}

        mock_coordinator = MagicMock()
        mock_coordinator.client.get_universal_audio_url.return_value = "http://test.url"
        mock_coordinator.config_entry.options = {}
        media_source._get_coordinator = MagicMock(return_value=mock_coordinator)

        item = create_media_item("server-123/track/item-789")

        await media_source.async_resolve_media(item)

        call_kwargs = mock_coordinator.client.get_universal_audio_url.call_args.kwargs
        assert call_kwargs["device_id"] == "homeassistant-my-ha-uuid"

    @pytest.mark.asyncio
    async def test_audio_resolution_returns_correct_mime_type(self) -> None:
        """Test that audio resolution returns audio/mpeg MIME type."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)
        media_source.hass = MagicMock()
        media_source.hass.data = {}
        media_source._active_sessions = {}

        mock_coordinator = MagicMock()
        mock_coordinator.client.get_universal_audio_url.return_value = "http://test.url"
        mock_coordinator.config_entry.options = {}
        media_source._get_coordinator = MagicMock(return_value=mock_coordinator)

        item = create_media_item("server-123/track/item-789")

        result = await media_source.async_resolve_media(item)

        assert result.mime_type == "audio/mpeg"

    @pytest.mark.asyncio
    async def test_audio_type_also_uses_universal_endpoint(self) -> None:
        """Test that 'audio' content type also uses universal endpoint."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)
        media_source.hass = MagicMock()
        media_source.hass.data = {}
        media_source._active_sessions = {}

        mock_coordinator = MagicMock()
        mock_coordinator.client.get_universal_audio_url.return_value = "http://test.url"
        mock_coordinator.config_entry.options = {}
        media_source._get_coordinator = MagicMock(return_value=mock_coordinator)

        item = create_media_item("server-123/audio/item-789")

        await media_source.async_resolve_media(item)

        mock_coordinator.client.get_universal_audio_url.assert_called_once()


class TestAudioContainerNegotiation:
    """Tests for audio container format negotiation."""

    @pytest.mark.asyncio
    async def test_audio_uses_default_containers(self) -> None:
        """Test that audio uses sensible default container list."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)
        media_source.hass = MagicMock()
        media_source.hass.data = {}
        media_source._active_sessions = {}

        mock_coordinator = MagicMock()
        mock_coordinator.client.get_universal_audio_url.return_value = "http://test.url"
        mock_coordinator.config_entry.options = {}
        media_source._get_coordinator = MagicMock(return_value=mock_coordinator)

        item = create_media_item("server-123/track/item-789")

        await media_source.async_resolve_media(item)

        call_kwargs = mock_coordinator.client.get_universal_audio_url.call_args.kwargs
        # Should support multiple container formats
        container = call_kwargs.get("container", "")
        # Common audio containers that should be supported
        assert any(fmt in container for fmt in ["mp3", "aac", "flac", "ogg", "m4a"])

    @pytest.mark.asyncio
    async def test_audio_sets_transcoding_container(self) -> None:
        """Test that mp3 is set as fallback transcoding container."""
        media_source = EmbyMediaSource.__new__(EmbyMediaSource)
        media_source.hass = MagicMock()
        media_source.hass.data = {}
        media_source._active_sessions = {}

        mock_coordinator = MagicMock()
        mock_coordinator.client.get_universal_audio_url.return_value = "http://test.url"
        mock_coordinator.config_entry.options = {}
        media_source._get_coordinator = MagicMock(return_value=mock_coordinator)

        item = create_media_item("server-123/track/item-789")

        await media_source.async_resolve_media(item)

        call_kwargs = mock_coordinator.client.get_universal_audio_url.call_args.kwargs
        # MP3 is widely supported as transcoding fallback
        assert call_kwargs.get("transcoding_container") == "mp3"
