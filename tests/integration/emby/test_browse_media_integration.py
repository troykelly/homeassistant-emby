"""Integration tests for *async_browse_media* high-level flow (GitHub issue #110).

The goal of these tests is to exercise the complete *async_browse_media*
implementation on a real :pyclass:`custom_components.embymedia.media_player.EmbyDevice`
instance wired with a stubbed *EmbyAPI*.  No actual network traffic is issued –
all outbound HTTP calls are intercepted so the code path remains identical to
production without requiring a live Emby server.

Covered behaviour:

1. Root browse request returns Emby *views* (libraries) and includes correct
   metadata such as *media_class* and thumbnail URLs that are proxied through
   Home Assistant.
2. The *Movies* root view is represented with ``MediaClass.MOVIE`` and a
   thumbnail that starts with the standard HA proxy prefix
   ``/api/media_player_proxy/``.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, List

import pytest


# ---------------------------------------------------------------------------
# HTTP stub – replaces *EmbyAPI._request*
# ---------------------------------------------------------------------------


class _StubHTTP:  # pylint: disable=too-few-public-methods
    """Collect outbound REST calls and return canned JSON responses."""

    def __init__(self) -> None:  # noqa: D401 – minimal container
        self.calls: List[tuple[str, str, dict[str, Any]]] = []

    async def handler(self, _self_ref, method: str, path: str, **kwargs: Any):  # noqa: D401
        """Replacement for :pymeth:`EmbyAPI._request`."""

        # Record the call so assertions can inspect later.
        self.calls.append((method, path, kwargs))

        # ------------------------------------------------------------------
        # Emby endpoints exercised by *async_browse_media*
        # ------------------------------------------------------------------

        # Root browse → EmbyDevice.async_browse_media() will call
        # `get_user_views` i.e. GET /Users/{user_id}/Views
        if path == "/Users/user-1/Views" and method == "GET":
            return {
                "Items": [
                    {"Id": "lib-movies", "Name": "Movies", "CollectionType": "movies"},
                    {"Id": "lib-shows", "Name": "TV Shows", "CollectionType": "tvshows"},
                ]
            }

        raise RuntimeError(f"Unhandled EmbyAPI request {method} {path}")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def http_stub(monkeypatch):
    """Patch :pymeth:`EmbyAPI._request` globally for the duration of a test."""

    from custom_components.embymedia import api as api_mod

    stub = _StubHTTP()

    async def _patched(self_api, method: str, path: str, **kwargs: Any):  # noqa: D401
        return await stub.handler(self_api, method, path, **kwargs)

    monkeypatch.setattr(api_mod.EmbyAPI, "_request", _patched, raising=True)

    return stub


@pytest.fixture()
def emby_device(monkeypatch):  # noqa: D401 – pytest naming convention
    """Return a fully wired :class:`EmbyDevice` ready for integration tests."""

    from custom_components.embymedia.media_player import EmbyDevice

    dev = EmbyDevice.__new__(EmbyDevice)  # type: ignore[arg-type]

    # Fake pyemby device object – only the attributes accessed by the browse
    # logic are populated.
    fake_device = SimpleNamespace(
        supports_remote_control=True,
        name="Living Room",
        state="Idle",
        username="john",
        session_id="sess-123",
        unique_id="dev1",
        session_raw={"UserId": "user-1"},
    )

    dev.device = fake_device
    dev.device_id = "dev1"

    # Minimal Emby server stub (only attributes read by helper methods).
    dev.emby = SimpleNamespace(_host="h", _api_key="k", _port=8096, _ssl=False)

    # The entity runs outside a real Home Assistant instance in this test
    # suite, however Home Assistant helpers (e.g. get_browse_image_url)
    # reference ``entity_id`` and ``access_token``.  Assign a deterministic
    # value so assertions can rely on it.
    dev.entity_id = "media_player.emby_living_room"  # type: ignore[attr-defined]

    # ``async_write_ha_state`` would normally interact with HA – patch to a
    # simple no-op so we do not require an event loop or entity platform.
    dev.async_write_ha_state = lambda *_, **__: None  # type: ignore[assignment]

    return dev


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_browse_media_root_integration(http_stub, emby_device):  # noqa: D401, ANN001
    """Happy-path root browse – validate view mapping & thumbnail proxy."""

    from homeassistant.components.media_player.const import MediaClass

    root_node = await emby_device.async_browse_media()

    # The stub returns two Emby libraries → *BrowseMedia* root must include
    # those plus the two virtual folders (Resume / Favorites).
    assert len(root_node.children) == 4  # type: ignore[arg-type]

    # Extract the *Movies* view to inspect its metadata.
    movies_node = next(child for child in root_node.children if child.title == "Movies")  # type: ignore[arg-type]

    assert movies_node.media_class == MediaClass.MOVIE  # type: ignore[attr-defined]

    # Thumbnail must be routed via HA proxy so remote users can access it.
    assert movies_node.thumbnail is not None
    assert movies_node.thumbnail.startswith("/api/media_player_proxy/")

    # Ensure exactly one HTTP call was made and pointed at the correct Views endpoint.
    assert http_stub.calls[0][0:2] == ("GET", "/Users/user-1/Views")
