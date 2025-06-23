"""Integration tests for *async_search_media* using patched HTTP layer.

These tests exercise the full helper stack (``EmbyAPI`` + ``EmbyDevice``)
while intercepting outbound HTTP requests so no real Emby server is required.
"""

from __future__ import annotations

from types import SimpleNamespace

from typing import Any, List

import pytest


# ---------------------------------------------------------------------------
# HTTP stub – replaces *EmbyAPI._request*
# ---------------------------------------------------------------------------


class _StubHTTP:  # pylint: disable=too-few-public-methods
    """Collect outgoing REST calls and return canned JSON responses."""

    def __init__(self) -> None:  # noqa: D401
        self.calls: List[tuple[str, str, dict[str, Any]]] = []

    async def handler(self, _self_ref, method: str, path: str, **kwargs: Any):  # noqa: D401
        """Replacement for :pymeth:`EmbyAPI._request`."""

        # Record call for later assertions
        self.calls.append((method, path, kwargs))

        # Search endpoint – return one dummy movie entry
        if path == "/Items" and method == "GET":
            params = kwargs.get("params", {})
            term = params.get("SearchTerm")
            if term == "bad":
                return {"Items": []}

            return {
                "Items": [
                    {"Id": "item-1", "Name": term, "Type": "Movie", "ImageTags": {}},
                    {"Id": "item-2", "Name": f"{term} 2", "Type": "Movie", "ImageTags": {}},
                ]
            }

        # Any other endpoint – return minimal acceptable payloads
        if path == "/Sessions" and method == "GET":
            return [
                {
                    "Id": "sess-123",
                    "DeviceId": "dev1",
                    "UserId": "user-1",
                    "PlayState": {"State": "Idle"},
                }
            ]

        raise RuntimeError(f"Unhandled EmbyAPI request {method} {path}")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def http_stub(monkeypatch):
    """Patch the low-level HTTP helper used by :class:`EmbyAPI`."""

    from custom_components.embymedia import api as api_mod

    stub = _StubHTTP()

    async def _patched(self_api, method: str, path: str, **kwargs):  # noqa: D401, ANN001
        return await stub.handler(self_api, method, path, **kwargs)

    monkeypatch.setattr(api_mod.EmbyAPI, "_request", _patched, raising=True)

    return stub


@pytest.fixture()
def emby_device(monkeypatch):  # noqa: D401 – naming
    """Return an *EmbyDevice* wired with fake pyemby device metadata."""

    from custom_components.embymedia.media_player import EmbyDevice

    dev = EmbyDevice.__new__(EmbyDevice)  # type: ignore[arg-type]

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
    dev.emby = SimpleNamespace(_host="h", _api_key="k", _port=8096, _ssl=False)
    dev.hass = None  # pyright: ignore[reportAttributeAccessIssue]
    dev.async_write_ha_state = lambda *_, **__: None  # type: ignore[assignment]

    return dev


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_search_media_integration(http_stub, emby_device):  # noqa: D401, ANN001
    """End-to-end verification that search returns expected BrowseMedia list."""

    from homeassistant.components.media_player import MediaType, SearchMediaQuery

    query = SearchMediaQuery(search_query="The Matrix", media_content_type=MediaType.MOVIE)

    search_result = await emby_device.async_search_media(query)

    # Two items returned by the stub -> SearchMedia should wrap them.
    assert len(search_result.result) == 2
    assert search_result.result[0].title == "The Matrix"

    # At least one result must be *playable* as per spec.
    assert any(child.can_play for child in search_result.result)

    # Confirm a single GET /Items call recorded with correct params.
    items_calls = [c for c in http_stub.calls if c[1] == "/Items"]
    assert len(items_calls) == 1
    method, path, kwargs = items_calls[0]
    assert method == "GET" and path == "/Items"
    assert kwargs["params"]["IncludeItemTypes"] == "Movie"
