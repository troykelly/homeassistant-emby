"""Regression test for shared *EmbyAPI* injection (epic #217).

The test boots the `async_setup_platform` flow from *media_player* with a
minimal Home Assistant stub and verifies that a **shared** `EmbyAPI` handle is
stored under `hass.data['embymedia']["<host:port>"]['api']`.  This is the
location expected by the *media_source* provider.

The bug fixed in PR #241 omitted this step which caused the global Media
browser to fail.  The test guards against future regressions.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest


# ---------------------------------------------------------------------------
# Home Assistant stubs (tiny subset)
# ---------------------------------------------------------------------------


class _StubBus:  # pylint: disable=too-few-public-methods
    """Imitates Home Assistant's event bus interface used by setup."""

    def async_listen_once(self, _event: str, _cb):  # noqa: D401 – signature only
        # Test does not need to fire the callback – we are interested in the
        # synchronous part of async_setup_platform.
        return None


class _StubHass:  # pylint: disable=too-few-public-methods
    """Very small Home Assistant replacement for this regression test."""

    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.bus = _StubBus()
        self.data: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Stub *pyemby.EmbyServer* so no network / websocket work kicks in.
# ---------------------------------------------------------------------------


class _StubServer:  # pylint: disable=too-few-public-methods
    def __init__(self, host: str, api_key: str, port: int, ssl: bool, _loop):  # noqa: D401
        self._host = host
        self._api_key = api_key
        self._port = port
        self._ssl = ssl

        # attributes referenced by async_setup_platform
        self.devices: Dict[str, Any] = {}

    # The real EmbyServer registers callbacks – we ignore them.
    def add_new_devices_callback(self, *_):  # noqa: D401 – stub
        pass

    def add_stale_devices_callback(self, *_):  # noqa: D401 – stub
        pass

    def start(self):  # noqa: D401 – stub
        pass

    async def stop(self):  # noqa: D401 – stub
        pass


# ---------------------------------------------------------------------------
# Test – verify shared API injection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_shared_embyapi_injected(monkeypatch):  # noqa: D401 – pytest naming
    """`async_setup_platform` must expose a shared EmbyAPI in `hass.data`."""

    # Patch *EmbyServer* inside the media_player module **before** import.
    monkeypatch.setattr(
        "custom_components.embymedia.media_player.EmbyServer", _StubServer, raising=True
    )

    # Import target after patching so it picks up the stub.
    from custom_components.embymedia.media_player import (
        async_setup_platform,
        PLATFORM_SCHEMA,
    )

    # Build a minimal, *validated* config using the real voluptuous schema so
    # we test the exact path executed in production.
    raw_cfg = {
        "platform": "embymedia",  # required by Home Assistant platform schema
        "host": "emby.local",
        "api_key": "abc123",
        "port": 8096,
        "ssl": False,
    }

    cfg = PLATFORM_SCHEMA(raw_cfg)  # type: ignore[arg-type]

    hass = _StubHass()

    added_entities: List[Any] = []

    def _async_add_entities(entities, _update_before_add=False):  # noqa: D401 – signature mimic
        added_entities.extend(entities)

    # Run the setup coroutine.
    await async_setup_platform(hass, cfg, _async_add_entities)

    key = f"{cfg['host']}:{cfg['port']}"

    assert "embymedia" in hass.data
    assert key in hass.data["embymedia"]
    bucket = hass.data["embymedia"][key]

    assert "api" in bucket
    # Avoid importing EmbyAPI here (heavier) – just assert it has the expected attrs.
    shared_api = bucket["api"]
    assert hasattr(shared_api, "_base")  # noqa: SLF001 – internal attr check
    assert added_entities == []  # no devices because stub server has none
