"""Unit tests for the thin :class:`components.emby.api.EmbyAPI` wrapper."""

from __future__ import annotations

from typing import Any, Dict

import pytest

from components.emby.api import EmbyAPI


class _RequestRecorder:
    """Helper that replaces :py:meth:`EmbyAPI._request` during the test."""

    def __init__(self):
        self.calls: list[Dict[str, Any]] = []

    async def __call__(self, method: str, path: str, **kwargs):  # noqa: D401
        # Record call-details so assertions can inspect them later.
        self.calls.append({"method": method, "path": path, **kwargs})

        # Dispatch fake responses tailored for the unit under test.
        if path == "/Sessions":
            return [
                {"Id": "sess-1", "DeviceId": "devA"},
                {"Id": "sess-2", "DeviceId": "devB"},
            ]

        # Individual item look-ups or /Playing requests are mocked with an
        # *empty* JSON body – not used by the code-path under test.
        return {}


# ---------------------------------------------------------------------------
# Tests – caching behaviour of get_sessions()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_sessions_caching(monkeypatch):
    """The helper must cache `/Sessions` for the configured TTL."""

    recorder = _RequestRecorder()

    api = EmbyAPI(None, host="emby", api_key="k")
    monkeypatch.setattr(api, "_request", recorder)  # type: ignore[attr-defined]

    # First call -> hits the recorder.
    sessions1 = await api.get_sessions()
    assert len(sessions1) == 2
    assert recorder.calls[-1]["path"] == "/Sessions"

    # Second call immediately afterwards should be served from the in-memory cache.
    sessions2 = await api.get_sessions()
    assert sessions2 is sessions1  # same list instance – cached
    assert len(recorder.calls) == 1  # no extra HTTP call

    # Force-refresh flag bypasses the cache.
    sessions3 = await api.get_sessions(force_refresh=True)
    assert sessions3 == sessions1
    assert len(recorder.calls) == 2  # second HTTP call issued


# ---------------------------------------------------------------------------
# Tests – play() argument handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_play_sends_correct_request(monkeypatch):
    """`play()` must call the internal HTTP helper with the correct arguments."""

    recorder = _RequestRecorder()
    api = EmbyAPI(None, host="emby", api_key="k")
    monkeypatch.setattr(api, "_request", recorder)  # type: ignore[attr-defined]

    await api.play("sess-123", ["item-1", "item-2"], play_command="PlayNow", start_position_ticks=90)

    # Exactly one internal request must have been made.
    assert len(recorder.calls) == 1
    call = recorder.calls[0]

    assert call["method"] == "POST"
    assert call["path"] == "/Sessions/sess-123/Playing"

    params = call["params"]
    assert params["ItemIds"] == "item-1,item-2"
    assert params["PlayCommand"] == "PlayNow"
    assert params["StartPositionTicks"] == "90"
