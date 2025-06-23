"""Unit-tests for volume & mute support (GitHub issue #75)."""

from __future__ import annotations

from types import SimpleNamespace

from typing import List

import pytest


# ---------------------------------------------------------------------------
# Helper stubs
# ---------------------------------------------------------------------------


class _StubAPI:  # pylint: disable=too-few-public-methods
    """Fake replacement for :class:`custom_components.embymedia.api.EmbyAPI`."""

    def __init__(self) -> None:  # noqa: D401 – keep test helper minimal
        self.set_volume_calls: List[dict] = []
        self.mute_calls: List[dict] = []

    async def set_volume(self, session_id, volume_level):  # noqa: D401
        self.set_volume_calls.append({"session_id": session_id, "volume_level": volume_level})

    async def mute(self, session_id, mute):  # noqa: D401
        self.mute_calls.append({"session_id": session_id, "mute": mute})


class _Device(SimpleNamespace):
    """Light-weight stand-in replicating *pyemby.EmbyDevice* attributes."""

    def __init__(self, *, vol_pct: int | None = 55, muted: bool = False):  # noqa: D401
        # Build a fake session payload containing the required PlayState info.
        play_state: dict = {}
        if vol_pct is not None:
            play_state["VolumeLevel"] = vol_pct
        play_state["IsMuted"] = muted

        super().__init__(
            supports_remote_control=True,
            name="Living Room",
            session_raw={"PlayState": play_state},
            session_id="sess-abc",
            unique_id="dev-abc",
        )


# ---------------------------------------------------------------------------
# Fixture returning an *EmbyDevice* wired with stubs
# ---------------------------------------------------------------------------


@pytest.fixture()
def emby_device(monkeypatch):  # noqa: D401
    """Return an *EmbyDevice* instance suitable for isolated tests."""

    from custom_components.embymedia.media_player import EmbyDevice

    dev = EmbyDevice.__new__(EmbyDevice)  # type: ignore[arg-type]

    dev.device = _Device()  # default 55 % volume, unmuted
    dev.device_id = "dev-abc"
    dev.emby = SimpleNamespace(_host="h", _api_key="k", _port=8096, _ssl=False)
    dev.hass = None  # pyright: ignore[reportAttributeAccessIssue]

    # *async_write_ha_state* is a simple no-op so tests run outside HA.
    dev.async_write_ha_state = lambda *_, **__: None  # type: ignore[assignment]

    # Patch API helper + session resolver --------------------------------
    stub_api = _StubAPI()
    monkeypatch.setattr(dev, "_get_emby_api", lambda self=dev: stub_api)  # type: ignore[arg-type]
    async def _fixed_session(*_, **__):  # noqa: D401 – minimal async stub
        return "sess-abc"

    monkeypatch.setattr(dev, "_resolve_session_id", _fixed_session)

    return dev


# ---------------------------------------------------------------------------
# Tests – properties
# ---------------------------------------------------------------------------


def test_volume_properties_from_session(emby_device):  # noqa: D401
    """`volume_level` & `is_volume_muted` must reflect the session payload."""

    assert emby_device.volume_level == 0.55
    assert emby_device.is_volume_muted is False


def test_volume_properties_missing(monkeypatch, emby_device):  # noqa: D401
    """Missing values in *PlayState* should yield *None* so HA disables UI."""

    # Remove VolumeLevel key entirely.
    emby_device.device.session_raw["PlayState"].pop("VolumeLevel", None)

    assert emby_device.volume_level is None


# ---------------------------------------------------------------------------
# Tests – service handlers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_set_volume_level_calls_api(emby_device):  # noqa: D401
    """Ensure *async_set_volume_level* delegates to :pyfunc:`api.set_volume`."""

    await emby_device.async_set_volume_level(0.32)

    stub_api: _StubAPI = emby_device._get_emby_api()  # type: ignore[attr-defined]
    assert stub_api.set_volume_calls == [{"session_id": "sess-abc", "volume_level": 0.32}]


@pytest.mark.asyncio
async def test_async_mute_volume_calls_api(emby_device):  # noqa: D401
    """Ensure *async_mute_volume* delegates to :pyfunc:`api.mute`."""

    await emby_device.async_mute_volume(True)

    stub_api: _StubAPI = emby_device._get_emby_api()  # type: ignore[attr-defined]
    assert stub_api.mute_calls == [{"session_id": "sess-abc", "mute": True}]
