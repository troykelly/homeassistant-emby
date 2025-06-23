"""Unit-tests for shuffle & repeat support (GitHub issue #76)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import List

import pytest


# ---------------------------------------------------------------------------
# Helper stubs – mirrors the pattern used by *test_media_player_volume.py*
# ---------------------------------------------------------------------------


class _StubAPI:  # pylint: disable=too-few-public-methods
    """Fake replacement for :class:`custom_components.embymedia.api.EmbyAPI`."""

    def __init__(self) -> None:  # noqa: D401 – minimal helper
        self.shuffle_calls: List[dict] = []
        self.repeat_calls: List[dict] = []

    async def shuffle(self, session_id, shuffle):  # noqa: D401 – test stub
        self.shuffle_calls.append({"session_id": session_id, "shuffle": shuffle})

    async def repeat(self, session_id, mode):  # noqa: D401 – test stub
        self.repeat_calls.append({"session_id": session_id, "mode": mode})


class _Device(SimpleNamespace):
    """Light-weight stand-in replicating *pyemby.EmbyDevice* attributes."""

    def __init__(
        self,
        *,
        is_shuffled: bool = False,
        repeat_mode: str = "RepeatNone",
    ) -> None:  # noqa: D401 – keep test helper minimal

        play_state: dict = {
            "IsShuffled": is_shuffled,
            "RepeatMode": repeat_mode,
        }

        super().__init__(
            supports_remote_control=True,
            name="Office",
            session_raw={"PlayState": play_state},
            session_id="sess-123",
            unique_id="dev-123",
        )


# ---------------------------------------------------------------------------
# Fixture returning an *EmbyDevice* wired with the stubs above
# ---------------------------------------------------------------------------


@pytest.fixture()
def emby_device(monkeypatch):  # noqa: D401 – fixture name matches other tests
    from custom_components.embymedia.media_player import EmbyDevice

    dev = EmbyDevice.__new__(EmbyDevice)  # type: ignore[arg-type]

    dev.device = _Device()  # defaults: not shuffled, repeat off
    dev.device_id = "dev-123"
    dev.emby = SimpleNamespace(_host="h", _api_key="k", _port=8096, _ssl=False)
    dev.hass = None  # pyright: ignore[reportAttributeAccessIssue]

    dev.async_write_ha_state = lambda *_, **__: None  # type: ignore[assignment]

    stub_api = _StubAPI()
    monkeypatch.setattr(dev, "_get_emby_api", lambda self=dev: stub_api)  # type: ignore[arg-type]

    async def _fixed_session(*_, **__):  # noqa: D401 – minimal async stub
        return "sess-123"

    monkeypatch.setattr(dev, "_resolve_session_id", _fixed_session)

    return dev


# ---------------------------------------------------------------------------
# Tests – properties
# ---------------------------------------------------------------------------


def test_shuffle_property_from_session(emby_device):  # noqa: D401
    """`shuffle` property must reflect the payload."""

    assert emby_device.shuffle is False

    # Toggle directly in session payload – property should track changes.
    emby_device.device.session_raw["PlayState"]["IsShuffled"] = True
    assert emby_device.shuffle is True


def test_repeat_property_from_session(monkeypatch, emby_device):  # noqa: D401
    """`repeat` property maps Emby identifiers to HA values."""

    # Parametrise manually – mapping dict must be in sync with implementation.
    cases = {
        "RepeatNone": "off",
        "RepeatAll": "all",
        "RepeatOne": "one",
    }

    try:
        from homeassistant.components.media_player.const import RepeatMode  # type: ignore

        enum_available = True
    except ImportError:
        enum_available = False

    for emby_val, expected in cases.items():
        emby_device.device.session_raw["PlayState"]["RepeatMode"] = emby_val

        if enum_available:
            from homeassistant.components.media_player.const import RepeatMode  # type: ignore

            assert emby_device.repeat == RepeatMode(expected)  # type: ignore[arg-type]
        else:
            assert emby_device.repeat == expected


# ---------------------------------------------------------------------------
# Tests – service handlers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("new_state", [True, False])
async def test_async_set_shuffle_calls_api(emby_device, new_state):  # noqa: D401
    """Ensure *async_set_shuffle* delegates to :pyfunc:`api.shuffle`."""

    await emby_device.async_set_shuffle(new_state)

    stub_api: _StubAPI = emby_device._get_emby_api()  # type: ignore[attr-defined]
    assert stub_api.shuffle_calls == [
        {"session_id": "sess-123", "shuffle": new_state}
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ha_mode, emby_mode",
    [
        ("off", "RepeatNone"),
        ("all", "RepeatAll"),
        ("one", "RepeatOne"),
    ],
)
async def test_async_set_repeat_calls_api(monkeypatch, emby_device, ha_mode, emby_mode):  # noqa: D401
    """Ensure *async_set_repeat* converts mode and delegates to :pyfunc:`api.repeat`."""

    # Pass as enum when available, fallback to str otherwise.
    try:
        from homeassistant.components.media_player.const import RepeatMode  # type: ignore

        repeat_param = RepeatMode(ha_mode)  # type: ignore[call-arg]
    except ImportError:
        repeat_param = ha_mode  # legacy HA versions

    await emby_device.async_set_repeat(repeat_param)

    stub_api: _StubAPI = emby_device._get_emby_api()  # type: ignore[attr-defined]
    assert stub_api.repeat_calls == [
        {"session_id": "sess-123", "mode": emby_mode}
    ]
