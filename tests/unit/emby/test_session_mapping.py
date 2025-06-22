"""Unit tests for the *EmbyDevice._resolve_session_id* helper."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.emby.media_player import EmbyDevice


class _FakeApi:  # pylint: disable=too-few-public-methods
    """Minimal stub exposing *get_sessions* expected by the helper."""

    def __init__(self, sessions, exc: Exception | None = None):
        self._sessions = sessions
        self._exc = exc
        self.calls: int = 0

    async def get_sessions(self, *, force_refresh: bool = False):  # noqa: D401
        self.calls += 1
        if self._exc:
            raise self._exc
        return self._sessions


def _make_device(device_id="dev1", unique_id="u1", session_id=None):  # noqa: D401
    """Return an *EmbyDevice* instance with only the attributes we need."""

    dev = EmbyDevice.__new__(EmbyDevice)  # type: ignore[arg-type]
    # Attributes normally initialised by EmbyDevice.__init__
    dev._current_session_id = session_id  # pylint: disable=protected-access
    dev.device_id = device_id
    dev.device = SimpleNamespace(unique_id=unique_id, session_id=session_id)

    return dev


@pytest.mark.asyncio
async def test_session_cached():
    """When the mapping is already cached the API must *not* be queried."""

    dev = _make_device(session_id="cached-sess")
    api = _FakeApi([])

    sid = await dev._resolve_session_id(api)  # pylint: disable=protected-access
    assert sid == "cached-sess"
    assert api.calls == 0


@pytest.mark.asyncio
async def test_session_refresh_success():
    """A matching DeviceId in the refreshed sessions list must be returned."""

    dev = _make_device()
    api = _FakeApi([
        {"DeviceId": "other", "Id": "sess-x"},
        {"DeviceId": "dev1", "Id": "sess-expected"},
    ])

    sid = await dev._resolve_session_id(api)  # pylint: disable=protected-access
    assert sid == "sess-expected"
    assert api.calls == 1


@pytest.mark.asyncio
async def test_session_refresh_failure():
    """API errors are swallowed and *None* is returned (helper is resilient)."""

    dev = _make_device()
    api = _FakeApi([], exc=RuntimeError("boom"))

    sid = await dev._resolve_session_id(api)  # pylint: disable=protected-access
    assert sid is None
