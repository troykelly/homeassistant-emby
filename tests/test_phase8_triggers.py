"""Tests for Phase 8.4: Automation Triggers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.embymedia.const import DOMAIN
from custom_components.embymedia.device_trigger import (
    TRIGGER_TYPES,
    async_get_triggers,
)


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "emby.local",
            "port": 8096,
            "api_key": "test-key",
        },
        unique_id="server-123",
    )


class TestDeviceTriggers:
    """Test device trigger functionality."""

    def test_trigger_types_defined(self) -> None:
        """Test trigger types are defined."""
        assert "playback_started" in TRIGGER_TYPES
        assert "playback_stopped" in TRIGGER_TYPES
        assert "playback_paused" in TRIGGER_TYPES
        assert "playback_resumed" in TRIGGER_TYPES
        assert "media_changed" in TRIGGER_TYPES
        assert "session_connected" in TRIGGER_TYPES
        assert "session_disconnected" in TRIGGER_TYPES

    @pytest.mark.asyncio
    async def test_async_get_triggers_returns_list(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test async_get_triggers returns a list."""
        mock_config_entry.add_to_hass(hass)

        # Create device registry entry
        device_reg = dr.async_get(hass)
        device = device_reg.async_get_or_create(
            config_entry_id=mock_config_entry.entry_id,
            identifiers={(DOMAIN, "test-device")},
            name="Test Device",
        )

        triggers = await async_get_triggers(hass, device.id)
        assert isinstance(triggers, list)

    @pytest.mark.asyncio
    async def test_async_get_triggers_for_media_player(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test triggers are returned for media player entities."""
        mock_config_entry.add_to_hass(hass)

        # Create device registry entry
        device_reg = dr.async_get(hass)
        device = device_reg.async_get_or_create(
            config_entry_id=mock_config_entry.entry_id,
            identifiers={(DOMAIN, "test-device")},
            name="Test Device",
        )

        # Create entity registry entry for media player
        entity_reg = er.async_get(hass)
        entity_reg.async_get_or_create(
            "media_player",
            DOMAIN,
            "test-device",
            config_entry=mock_config_entry,
            device_id=device.id,
        )

        triggers = await async_get_triggers(hass, device.id)

        # Should have one trigger for each trigger type
        assert len(triggers) == len(TRIGGER_TYPES)

        # All trigger types should be represented
        trigger_types_in_result = {t["type"] for t in triggers}
        assert trigger_types_in_result == TRIGGER_TYPES


class TestTriggerSchema:
    """Test trigger schema validation."""

    def test_trigger_schema_exists(self) -> None:
        """Test TRIGGER_SCHEMA is defined."""
        from custom_components.embymedia.device_trigger import TRIGGER_SCHEMA

        assert TRIGGER_SCHEMA is not None


class TestEventFiring:
    """Test event firing from coordinator."""

    @pytest.mark.asyncio
    async def test_coordinator_fires_playback_events(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test coordinator fires playback events."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator
        from custom_components.embymedia.models import EmbyMediaItem, EmbySession, MediaType

        mock_config_entry.add_to_hass(hass)

        mock_client = MagicMock()
        mock_client.async_get_sessions = MagicMock(return_value=[])

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Create entity registry entry
        # Unique ID format is: {server_id}_{device_id}
        entity_reg = er.async_get(hass)
        entity_reg.async_get_or_create(
            "media_player",
            DOMAIN,
            "server-123_device-1",
        )

        # Track fired events
        events: list[dict] = []

        def capture_event(event):
            events.append(event.data)

        hass.bus.async_listen(f"{DOMAIN}_event", capture_event)

        # Initial state: nothing playing
        old_session = EmbySession(
            session_id="sess-1",
            device_id="device-1",
            device_name="Test Device",
            client_name="Test Client",
            now_playing=None,
        )

        # New state: something playing (for reference, actual processing uses raw data)
        _new_session = EmbySession(
            session_id="sess-1",
            device_id="device-1",
            device_name="Test Device",
            client_name="Test Client",
            now_playing=EmbyMediaItem(
                item_id="item-1",
                name="Test Movie",
                media_type=MediaType.MOVIE,
            ),
        )

        # Simulate session data processing
        coordinator._previous_sessions = {"device-1"}
        coordinator.data = {"device-1": old_session}

        coordinator._process_sessions_data(
            [
                {
                    "Id": "sess-1",
                    "DeviceId": "device-1",
                    "DeviceName": "Test Device",
                    "Client": "Test Client",
                    "SupportsRemoteControl": True,
                    "NowPlayingItem": {
                        "Id": "item-1",
                        "Name": "Test Movie",
                        "Type": "Movie",
                    },
                }
            ]
        )

        # Allow event processing
        await hass.async_block_till_done()

        # Should have fired playback_started event
        playback_events = [e for e in events if e.get("type") == "playback_started"]
        assert len(playback_events) >= 1


class TestPollingEventFiring:
    """Test event firing from polling path (Issue #285).

    When sessions are updated via polling (_async_update_data), playback
    events should be fired just like when using WebSocket path.
    """

    @pytest.mark.asyncio
    async def test_polling_fires_playback_stopped_event(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test polling fires playback_stopped when media stops (Issue #285).

        This tests the scenario where:
        1. A session is playing media
        2. On the next poll, the session no longer has NowPlayingItem
        3. A playback_stopped event should be fired

        This is the bug reported in Issue #285 - the polling path
        (_async_update_data) was not firing events, only the WebSocket
        path (_process_sessions_data) was.
        """
        from unittest.mock import AsyncMock

        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_config_entry.add_to_hass(hass)

        mock_client = MagicMock()
        # First poll: session is playing media
        # Second poll: session is idle (no NowPlayingItem)
        mock_client.async_get_sessions = AsyncMock(
            side_effect=[
                # First call returns session with playing media
                [
                    {
                        "Id": "sess-1",
                        "DeviceId": "device-1",
                        "DeviceName": "Test Device",
                        "Client": "Test Client",
                        "SupportsRemoteControl": True,
                        "NowPlayingItem": {
                            "Id": "item-1",
                            "Name": "Test Movie",
                            "Type": "Movie",
                        },
                    }
                ],
                # Second call returns session without playing media
                [
                    {
                        "Id": "sess-1",
                        "DeviceId": "device-1",
                        "DeviceName": "Test Device",
                        "Client": "Test Client",
                        "SupportsRemoteControl": True,
                        # No NowPlayingItem - playback stopped
                    }
                ],
            ]
        )

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        # Create entity registry entry so _fire_event can find the entity
        entity_reg = er.async_get(hass)
        entity_reg.async_get_or_create(
            "media_player",
            DOMAIN,
            "server-123_device-1",
        )

        # Track fired events
        events: list[dict] = []

        def capture_event(event):
            events.append(event.data)

        hass.bus.async_listen(f"{DOMAIN}_event", capture_event)

        # First refresh - starts playing
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        # Clear events from first refresh (may have session_connected)
        events.clear()

        # Second refresh - stops playing
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        # Should have fired playback_stopped event
        playback_stopped_events = [e for e in events if e.get("type") == "playback_stopped"]
        assert len(playback_stopped_events) == 1, (
            f"Expected 1 playback_stopped event, got {len(playback_stopped_events)}. "
            f"Events fired: {events}"
        )

    @pytest.mark.asyncio
    async def test_polling_fires_playback_started_event(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test polling fires playback_started when media starts (Issue #285)."""
        from unittest.mock import AsyncMock

        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

        mock_config_entry.add_to_hass(hass)

        mock_client = MagicMock()
        mock_client.async_get_sessions = AsyncMock(
            side_effect=[
                # First call: session idle
                [
                    {
                        "Id": "sess-1",
                        "DeviceId": "device-1",
                        "DeviceName": "Test Device",
                        "Client": "Test Client",
                        "SupportsRemoteControl": True,
                    }
                ],
                # Second call: session playing
                [
                    {
                        "Id": "sess-1",
                        "DeviceId": "device-1",
                        "DeviceName": "Test Device",
                        "Client": "Test Client",
                        "SupportsRemoteControl": True,
                        "NowPlayingItem": {
                            "Id": "item-1",
                            "Name": "Test Movie",
                            "Type": "Movie",
                        },
                    }
                ],
            ]
        )

        coordinator = EmbyDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            server_id="server-123",
            server_name="Test Server",
            config_entry=mock_config_entry,
        )

        entity_reg = er.async_get(hass)
        entity_reg.async_get_or_create(
            "media_player",
            DOMAIN,
            "server-123_device-1",
        )

        events: list[dict] = []

        def capture_event(event):
            events.append(event.data)

        hass.bus.async_listen(f"{DOMAIN}_event", capture_event)

        # First refresh - session idle
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        events.clear()

        # Second refresh - starts playing
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        # Should have fired playback_started event
        playback_started_events = [e for e in events if e.get("type") == "playback_started"]
        assert len(playback_started_events) == 1, (
            f"Expected 1 playback_started event, got {len(playback_started_events)}. "
            f"Events fired: {events}"
        )


class TestDeviceTriggerCapabilities:
    """Test device trigger capabilities."""

    @pytest.mark.asyncio
    async def test_get_trigger_capabilities_returns_empty_dict(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test get_trigger_capabilities returns empty dict."""
        from custom_components.embymedia.device_trigger import async_get_trigger_capabilities

        result = await async_get_trigger_capabilities(hass, {})
        assert result == {}
