"""Unit tests for the extra *remote-control* helpers added by issue #79.

The tests validate that each public wrapper funnels into the private
``_request`` helper with the correct HTTP method, path and JSON payload.  A
light-weight *recorder* stub is injected via monkeypatching so the helper can
be inspected without performing real network I/O.
"""

from __future__ import annotations

from types import SimpleNamespace

from typing import Any, Dict

import pytest

from custom_components.embymedia.api import EmbyAPI


class _Recorder:
    """Replaces :py:meth:`EmbyAPI._request` to capture outgoing calls."""

    def __init__(self) -> None:  # noqa: D401 – simple initialiser
        self.calls: list[Dict[str, Any]] = []

    async def __call__(self, method: str, path: str, **kwargs):  # noqa: D401 – async callback
        self.calls.append({"method": method, "path": path, **kwargs})
        # All helper methods expect an *empty* response body.
        return {}


# ---------------------------------------------------------------------------
# set_volume – clamps & sends SetVolume command
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("input_level,expected_pct", [(0.0, 0), (0.5, 50), (1.0, 100), (-1, 0), (2, 100)])
async def test_set_volume_sends_correct_json(monkeypatch, input_level, expected_pct):
    recorder = _Recorder()

    api = EmbyAPI(None, host="emby", api_key="k", session=SimpleNamespace())
    monkeypatch.setattr(api, "_request", recorder)  # type: ignore[attr-defined]

    await api.set_volume("sess-X", input_level)

    assert len(recorder.calls) == 1
    call = recorder.calls[0]

    assert call["method"] == "POST"
    assert call["path"] == "/Sessions/sess-X/Command"

    payload = call["json"]
    assert payload["Name"] == "SetVolume"
    assert payload["Arguments"]["Volume"] == expected_pct


# ---------------------------------------------------------------------------
# mute
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("mute_flag", [True, False])
async def test_mute_command(monkeypatch, mute_flag):
    recorder = _Recorder()
    api = EmbyAPI(None, host="emby", api_key="k", session=SimpleNamespace())
    monkeypatch.setattr(api, "_request", recorder)  # type: ignore[attr-defined]

    await api.mute("sess-1", mute_flag)

    payload = recorder.calls[0]["json"]
    expected_name = "Mute" if mute_flag else "Unmute"

    assert payload["Name"] == expected_name
    # Mute/Unmute commands carry **no** arguments in modern Emby builds.
    assert payload["Arguments"] == {}


# ---------------------------------------------------------------------------
# shuffle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_shuffle_command(monkeypatch):
    recorder = _Recorder()
    api = EmbyAPI(None, host="emby", api_key="k", session=SimpleNamespace())
    monkeypatch.setattr(api, "_request", recorder)  # type: ignore[attr-defined]

    await api.shuffle("sess-2", True)

    payload = recorder.calls[0]["json"]
    assert payload["Name"] == "Shuffle"
    assert payload["Arguments"]["Shuffle"] == "true"


# ---------------------------------------------------------------------------
# repeat
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["RepeatNone", "RepeatAll", "RepeatOne"])
async def test_repeat_valid_modes(monkeypatch, mode):
    recorder = _Recorder()
    api = EmbyAPI(None, host="emby", api_key="k", session=SimpleNamespace())
    monkeypatch.setattr(api, "_request", recorder)  # type: ignore[attr-defined]

    await api.repeat("sess-3", mode)

    payload = recorder.calls[0]["json"]
    assert payload["Name"] == "Repeat"
    assert payload["Arguments"]["Mode"] == mode


@pytest.mark.asyncio
async def test_repeat_invalid_mode_raises(monkeypatch):
    api = EmbyAPI(None, host="emby", api_key="k", session=SimpleNamespace())

    with pytest.raises(ValueError):
        await api.repeat("sess-3", "InvalidMode")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# power_state – on & off
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_power_state_command(monkeypatch):
    recorder = _Recorder()
    api = EmbyAPI(None, host="emby", api_key="k", session=SimpleNamespace())
    monkeypatch.setattr(api, "_request", recorder)  # type: ignore[attr-defined]

    await api.power_state("sess-on", True)
    await api.power_state("sess-off", False)

    first, second = recorder.calls

    assert first["json"]["Name"] == "DisplayOn"
    assert second["json"]["Name"] == "Standby"
