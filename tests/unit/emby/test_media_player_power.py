"""Unit-tests for power management (turn_on / turn_off) – GitHub issue #77."""

from __future__ import annotations

from types import SimpleNamespace
from typing import List

import pytest


# ---------------------------------------------------------------------------
# Helper stubs mirroring the pattern used by volume & shuffle tests
# ---------------------------------------------------------------------------


class _StubAPI:  # pylint: disable=too-few-public-methods
    """Fake replacement for :class:`custom_components.embymedia.api.EmbyAPI`."""

    def __init__(self) -> None:  # noqa: D401 – minimal helper
        self.power_calls: List[dict] = []

    async def power_state(self, session_id, turn_on):  # noqa: D401 – test stub
        self.power_calls.append({"session_id": session_id, "turn_on": turn_on})


class _Device(SimpleNamespace):
    """Light-weight stand-in replicating *pyemby.EmbyDevice* attributes."""

    def __init__(self, *, state: str = "Off") -> None:  # noqa: D401
        super().__init__(
            supports_remote_control=True,
            name="Bedroom TV",
            session_raw={},  # not needed for these tests
            session_id="sess-power",
            unique_id="dev-power",
            state=state,
        )


# ---------------------------------------------------------------------------
# Fixture returning an *EmbyDevice* with stubs wired
# ---------------------------------------------------------------------------


@pytest.fixture()
def emby_device(monkeypatch):  # noqa: D401 – fixture pattern matches others
    from custom_components.embymedia.media_player import EmbyDevice

    dev = EmbyDevice.__new__(EmbyDevice)  # type: ignore[arg-type]

    dev.device = _Device()
    dev.device_id = "dev-power"
    dev.emby = SimpleNamespace(_host="h", _api_key="k", _port=8096, _ssl=False)
    dev.hass = None  # pyright: ignore[reportAttributeAccessIssue]

    # Disable HA state writes so tests run outside a full HA instance.
    dev.async_write_ha_state = lambda *_, **__: None  # type: ignore[assignment]

    stub_api = _StubAPI()
    monkeypatch.setattr(dev, "_get_emby_api", lambda self=dev: stub_api)  # type: ignore[arg-type]

    async def _fixed_session(*_, **__):  # noqa: D401 – minimal async stub
        return "sess-power"

    monkeypatch.setattr(dev, "_resolve_session_id", _fixed_session)

    return dev


# ---------------------------------------------------------------------------
# Tests – service handlers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_turn_on_calls_api(emby_device):  # noqa: D401
    """`async_turn_on` must delegate to :pyfunc:`api.power_state`."""

    await emby_device.async_turn_on()

    stub_api: _StubAPI = emby_device._get_emby_api()  # type: ignore[attr-defined]
    assert stub_api.power_calls == [
        {"session_id": "sess-power", "turn_on": True}
    ]


@pytest.mark.asyncio
async def test_async_turn_off_calls_api(emby_device):  # noqa: D401
    """`async_turn_off` must delegate to :pyfunc:`api.power_state`."""

    await emby_device.async_turn_off()

    stub_api: _StubAPI = emby_device._get_emby_api()  # type: ignore[attr-defined]
    assert stub_api.power_calls == [
        {"session_id": "sess-power", "turn_on": False}
    ]
