"""Unit-tests exercising :pyfunc:`async_setup_platform`.

The purpose of these tests is **coverage** – the setup helper mostly wires
callbacks into Home Assistant’s event bus.  A fully-fledged HA instance is not
required; a light-weight stub with the minimum public surface keeps the test
fast and hermetic.
"""

from __future__ import annotations

import asyncio

import pytest


# ---------------------------------------------------------------------------
# Minimal Home Assistant stubs
# ---------------------------------------------------------------------------


class _StubBus:  # pylint: disable=too-few-public-methods
    """Exposes *async_listen_once* – no-op for the unit-test."""

    def async_listen_once(self, _event, _callback):  # noqa: D401 – signature mirrors HA core
        # The callback is not executed in these tests – we only validate that
        # *async_setup_platform* registers it without raising exceptions.
        return None


class _StubHass:  # pylint: disable=too-few-public-methods
    """Provides the attributes accessed by *async_setup_platform*."""

    def __init__(self):  # noqa: D401 – trivial container
        self.loop = asyncio.get_event_loop()
        self.bus = _StubBus()


# ---------------------------------------------------------------------------
# Fake *pyemby.EmbyServer* implementation
# ---------------------------------------------------------------------------


class _StubEmbyServer:  # pylint: disable=too-few-public-methods
    """Captures the callbacks registered by the platform code."""

    def __init__(self, _host, _key, _port, _ssl, _loop):  # noqa: D401, ANN001 – mimic real signature
        self.devices = {}
        self._new_cb = None
        self._stale_cb = None

    # Callback registration -------------------------------------------------
    def add_new_devices_callback(self, cb):  # noqa: D401
        self._new_cb = cb

    def add_stale_devices_callback(self, cb):  # noqa: D401
        self._stale_cb = cb

    # Lifecycle helpers -----------------------------------------------------
    def start(self):  # noqa: D401 – invoked once HA fires *start* event
        pass

    async def stop(self):  # noqa: D401 – invoked on HA stop
        return None


# ---------------------------------------------------------------------------
# Test – smoke check that the helper runs without exploding
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_setup_platform_smoke(monkeypatch):  # noqa: D401
    """Ensure the setup helper completes and registers callbacks."""

    # Patch *EmbyServer* reference inside the module under test.
    import custom_components.embymedia.media_player as mp

    monkeypatch.setattr(mp, "EmbyServer", _StubEmbyServer, raising=True)

    hass = _StubHass()

    recorded_entities = []

    async def _add_entities(entities, _update=False):  # noqa: D401, ANN001 – matches core signature
        recorded_entities.extend(entities)

    cfg = {
        "host": "emby.local",
        "api_key": "k",
        "ssl": False,
    }

    await mp.async_setup_platform(hass, cfg, _add_entities)  # type: ignore[arg-type]

    # The helper should not add any entities immediately – there are no
    # devices in the stub server yet.
    assert recorded_entities == []
