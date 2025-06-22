"""End-to-end *play_media* integration tests exercising the full stack.

The unit-test suite already verifies :pyfunc:`components.emby.media_player.EmbyDevice`
in isolation by monkey-patching most dependencies.  These **integration** tests
wire up the real helper modules (``components.emby.api`` and
``components.emby.search_resolver``) while stubbing *only* the outbound HTTP
requests so the code path stays identical to production without requiring a
live Emby server.

Behaviour covered:

1. Successful ``play_media`` call – library search, session resolution and the
   final POST to ``/Sessions/{id}/Playing``.
2. Lookup failure – ensure a *HomeAssistantError* bubbles up when the resolver
   cannot find a matching item.

The implementation purposefully avoids spinning up a full Home Assistant core
instance to keep runtime low; instead it reuses the light-weight *Fake* device
pattern from the existing unit tests.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, List

import pytest


# ---------------------------------------------------------------------------
# Stubs & helpers
# ---------------------------------------------------------------------------


class _StubHTTP:  # pylint: disable=too-few-public-methods
    """Record outgoing Emby REST calls and return canned responses."""

    def __init__(self) -> None:  # noqa: D401 – simple container
        self.calls: List[tuple[str, str, dict[str, Any]]] = []

    async def handler(self, _self_ref, method: str, path: str, **kwargs: Any):  # noqa: D401, ANN001 – match signature
        """Replacement for :pymeth:`components.emby.api.EmbyAPI._request`."""

        # Store call for later assertions – kwargs include *params/json*.
        self.calls.append((method, path, kwargs))

        # ------------------------------------------------------------------
        # Fake minimal responses expected by the integration.
        # ------------------------------------------------------------------

        if path == "/Sessions":
            return [
                {
                    "Id": "sess-123",
                    "DeviceId": "dev1",
                    "PlayState": {"State": "Idle"},
                }
            ]

        # Library search – we only ever ask for ``/Items`` in the current
        # implementation.  Return a single dummy movie when the search term is
        # not "bad".
        if path == "/Items" and method == "GET":
            params = kwargs.get("params", {})
            term = params.get("SearchTerm")
            if term == "bad":
                return {"Items": []}
            return {"Items": [{"Id": "item-1", "Name": term, "Type": "Movie"}]}

        # Remote playback – accept any POST to the expected endpoint.
        if path.startswith("/Sessions/") and path.endswith("/Playing") and method == "POST":
            return {}

        # Fallback – raise to highlight unhandled paths.
        raise RuntimeError(f"Unhandled EmbyAPI request {method} {path}")


class _Device(SimpleNamespace):
    """Minimal replica of the pyemby device used by *EmbyDevice*."""

    def __init__(self):  # noqa: D401 – keep inline for brevity
        super().__init__(
            supports_remote_control=True,
            name="Living Room",
            state="Idle",
            username="john",
            media_id=None,
            media_type="Movie",
            media_runtime=None,
            media_position=None,
            is_nowplaying=False,
            media_image_url=None,
            media_title=None,
            media_season=None,
            media_series_title=None,
            media_episode=None,
            media_album_name=None,
            media_artist=None,
            media_album_artist=None,
            session_id="sess-123",
            unique_id="dev1",
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def http_stub(monkeypatch):
    """Patch :pymeth:`EmbyAPI._request` so no real HTTP is executed."""

    from custom_components.emby import api as api_mod

    stub = _StubHTTP()

    async def _patched(self_api, method: str, path: str, **kwargs: Any):  # noqa: D401 – match original signature
        """Delegate to the *stub* instance while keeping original *self* param."""

        return await stub.handler(self_api, method, path, **kwargs)

    monkeypatch.setattr(api_mod.EmbyAPI, "_request", _patched, raising=True)

    return stub


@pytest.fixture()
def emby_device(monkeypatch):  # noqa: D401 – pytest naming
    """Return an :class:`components.emby.media_player.EmbyDevice` wired with stubs."""

    from custom_components.emby.media_player import EmbyDevice

    dev = EmbyDevice.__new__(EmbyDevice)  # type: ignore[arg-type]

    # Inject fake device + minimal server metadata so *_get_emby_api* works.
    stub_device = _Device()
    dev.device = stub_device
    dev.device_id = "dev1"
    dev.emby = SimpleNamespace(_host="h", _api_key="k", _port=8096, _ssl=False)
    dev.hass = None  # not needed for these integration tests
    dev._current_session_id = None  # pylint: disable=protected-access

    # Ensure Home Assistant's entity method does not fail when called.
    dev.async_write_ha_state = lambda *_, **__: None  # type: ignore[assignment]

    return dev


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_play_media_success(http_stub, emby_device):  # noqa: D401, ANN001
    """Full happy-path – verify that *play()* is invoked with correct args."""

    await emby_device.async_play_media(media_type="movie", media_id="The Matrix")

    # The stub recorded outbound REST calls – last one must be the playback.
    assert http_stub.calls[-1][0:2] == ("POST", "/Sessions/sess-123/Playing")

    # Ensure ID mapping persisted.
    assert emby_device.get_current_session_id() == "sess-123"


@pytest.mark.asyncio
async def test_play_media_lookup_failure(http_stub, emby_device):  # noqa: D401, ANN001
    """Resolver returns no items → HomeAssistantError should be raised."""

    from homeassistant.exceptions import HomeAssistantError

    with pytest.raises(HomeAssistantError):
        await emby_device.async_play_media("movie", "bad")
