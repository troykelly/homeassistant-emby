"""Unit tests for the *library* helper methods added in issue #26.

These cover:
* `get_user_views()` – correct HTTP path, normalisation & caching.
* `get_item_children()` – correct HTTP path/query parameters & caching.
"""

from __future__ import annotations

from typing import Any, Dict
from types import SimpleNamespace

import pytest

from components.emby.api import EmbyAPI


# ---------------------------------------------------------------------------
# Test scaffolding – simple recorder that fakes `_request` responses.
# ---------------------------------------------------------------------------


class _RequestRecorder:
    """Helper that records calls and returns stubbed responses."""

    def __init__(self):
        self.calls: list[Dict[str, Any]] = []

    async def __call__(self, method: str, path: str, **kwargs):  # noqa: D401
        self.calls.append({"method": method, "path": path, **kwargs})

        # Return dummy payloads depending on the endpoint requested.
        if path.endswith("/Views"):
            return {"Items": [{"Id": "lib-1", "Name": "Movies"}]}

        if path.endswith("/Children"):
            return {
                "Items": [
                    {"Id": "child-1", "Name": "Item 1"},
                    {"Id": "child-2", "Name": "Item 2"},
                ],
                "TotalRecordCount": 2,
            }

        raise AssertionError(f"Unexpected path requested in test: {path}")


# ---------------------------------------------------------------------------
# Tests – get_user_views()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_user_views_normalises_and_caches(monkeypatch):
    recorder = _RequestRecorder()
    api = EmbyAPI(None, host="emby", api_key="k", session=SimpleNamespace())
    monkeypatch.setattr(api, "_request", recorder)  # type: ignore[attr-defined]

    # First call performs HTTP request and returns normalised *list*.
    libs1 = await api.get_user_views("user-123")
    assert libs1 == [{"Id": "lib-1", "Name": "Movies"}]
    assert len(recorder.calls) == 1
    assert recorder.calls[0]["path"] == "/Users/user-123/Views"

    # Second call without force-refresh should hit cache (no extra HTTP).
    libs2 = await api.get_user_views("user-123")
    assert libs2 is libs1
    assert len(recorder.calls) == 1


# ---------------------------------------------------------------------------
# Tests – get_item_children()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_item_children_params_and_caching(monkeypatch):
    recorder = _RequestRecorder()
    api = EmbyAPI(None, host="emby", api_key="k", session=SimpleNamespace())
    monkeypatch.setattr(api, "_request", recorder)  # type: ignore[attr-defined]

    payload1 = await api.get_item_children(
        "parent-1", user_id="user-123", start_index=10, limit=5
    )

    # Verify the response is forwarded unchanged.
    assert payload1["TotalRecordCount"] == 2
    assert len(recorder.calls) == 1

    call = recorder.calls[0]
    assert call["path"] == "/Items/parent-1/Children"

    # Query params must be correctly forwarded.
    expected_params = {"StartIndex": "10", "Limit": "5", "UserId": "user-123"}
    assert call["params"] == expected_params

    # Second identical call should be served from cache.
    payload2 = await api.get_item_children(
        "parent-1", user_id="user-123", start_index=10, limit=5
    )
    assert payload2 is payload1
    assert len(recorder.calls) == 1  # no extra HTTP
