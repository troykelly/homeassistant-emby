"""Integration tests for volume and mute control (GitHub issue #194).

These end-to-end tests wire up the real *custom_components.embymedia* helper
modules while stubbing **only** the outbound HTTP layer so that the execution
path remains identical to production code – no Home Assistant core instance or
live Emby server is required.

Covered behaviour:

1. ``async_set_volume_level`` must POST a *GeneralCommand* payload with
   ``Name = "VolumeSet"`` and the absolute integer ``Volume`` argument.
2. ``async_mute_volume`` must POST a *GeneralCommand* payload with
   ``Name = "Mute"`` and a native boolean ``Mute`` argument – *both* mute and
   un-mute operations are verified.

The tests purposefully mirror the lightweight stub pattern used by
``tests/integration/emby/test_play_media_integration.py`` to keep runtime and
complexity low.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, List

import pytest

# ---------------------------------------------------------------------------
# Stubs & helpers
# ---------------------------------------------------------------------------


class _StubHTTP:  # pylint: disable=too-few-public-methods
    """Record outgoing Emby REST calls and return canned JSON bodies."""

    def __init__(self) -> None:  # noqa: D401 – simple container type
        self.calls: List[tuple[str, str, dict[str, Any]]] = []

    async def handler(self, _self_ref, method: str, path: str, **kwargs: Any):  # noqa: D401, ANN001
        """Replacement for :pymeth:`custom_components.embymedia.api.EmbyAPI._request`."""

        # Store the call for later assertions (kwargs include *params*/*json*).
        self.calls.append((method, path, kwargs))

        # ------------------------------------------------------------------
        # Fake minimal responses expected by the integration                
        # ------------------------------------------------------------------

        # Session enumeration – return a single session that matches the
        # fake device id so that *_resolve_session_id* succeeds.
        if path == "/Sessions":
            return [
                {
                    "Id": "sess-123",
                    "DeviceId": "dev1",
                    "PlayState": {"State": "Idle"},
                }
            ]

        # Commands – simply accept any POST to */Sessions/{id}/Command*.
        if path.startswith("/Sessions/") and path.endswith("/Command") and method == "POST":
            return {}

        # Any other path is unexpected in this test scope.
        raise RuntimeError(f"Unhandled EmbyAPI request {method} {path}")


class _Device(SimpleNamespace):
    """Minimal replica of the underlying *pyemby* device object."""

    def __init__(self):  # noqa: D401 – keep inline for brevity
        super().__init__(
            supports_remote_control=True,
            name="Living Room",
            state="Idle",
            username="john",
            session_id="sess-123",
            unique_id="dev1",
            # *session_raw* is required for volume / mute properties but not
            # accessed by the methods under test, therefore keep it minimal.
            session_raw={"PlayState": {"VolumeLevel": 55, "IsMuted": False}},
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def http_stub(monkeypatch):
    """Patch :pymeth:`EmbyAPI._request` so no real HTTP is performed."""

    from custom_components.embymedia import api as api_mod

    stub = _StubHTTP()

    async def _patched(self_api, method: str, path: str, **kwargs: Any):  # noqa: D401, ANN001
        return await stub.handler(self_api, method, path, **kwargs)

    monkeypatch.setattr(api_mod.EmbyAPI, "_request", _patched, raising=True)

    return stub


@pytest.fixture()
def emby_device(monkeypatch):  # noqa: D401 – pytest fixture naming
    """Return an *EmbyDevice* instance wired with the HTTP stub."""

    from custom_components.embymedia.media_player import EmbyDevice

    dev = EmbyDevice.__new__(EmbyDevice)  # type: ignore[arg-type]

    # Inject fake device + minimal server meta so *_get_emby_api* works.
    dev.device = _Device()
    dev.device_id = "dev1"
    dev.emby = SimpleNamespace(_host="h", _api_key="k", _port=8096, _ssl=False)
    dev.hass = None  # not needed outside of HA core  # pyright: ignore[reportAttributeAccessIssue]

    # Ensure Home Assistant method doesn't explode when invoked.
    dev.async_write_ha_state = lambda *_, **__: None  # type: ignore[assignment]

    # Internal session cache used by *_resolve_session_id* – initialise to *None*.
    dev._current_session_id = None  # type: ignore[attr-defined, protected-access]

    return dev


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("level,pct", [(0.0, 0), (0.55, 55), (1.0, 100)])
async def test_async_set_volume_level_integration(http_stub, emby_device, level, pct):  # noqa: D401, ANN001
    """Ensure a proper *VolumeSet* command is emitted for various inputs."""

    # Act – trigger the Home Assistant service handler.
    await emby_device.async_set_volume_level(level)

    # Last HTTP request must be the POST to */Command* with expected payload.
    method, path, kwargs = http_stub.calls[-1]

    assert (method, path) == ("POST", "/Sessions/sess-123/Command")

    payload = kwargs["json"]
    assert payload["Name"] == "VolumeSet"
    assert payload["Arguments"]["Volume"] == pct


@pytest.mark.asyncio
@pytest.mark.parametrize("mute_flag", [True, False])
async def test_async_mute_volume_integration(http_stub, emby_device, mute_flag):  # noqa: D401, ANN001
    """Ensure a proper *Mute* command with native boolean flag is sent."""

    await emby_device.async_mute_volume(mute_flag)

    method, path, kwargs = http_stub.calls[-1]

    assert (method, path) == ("POST", "/Sessions/sess-123/Command")

    payload = kwargs["json"]
    assert payload["Name"] == "Mute"
    assert payload["Arguments"]["Mute"] is mute_flag
