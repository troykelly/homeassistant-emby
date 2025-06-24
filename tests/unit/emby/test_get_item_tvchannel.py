"""Unit tests – *TvChannel* fallback logic in :py:meth:`EmbyAPI.get_item`."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict

import pytest

from custom_components.embymedia.api import EmbyAPI, EmbyApiError


class _TvChannelStubber:
    """Stub for :py:meth:`EmbyAPI._request` used by the test.

    The callable emulates these Emby behaviours:

    1. ``/Items/{id}`` – raises *404* (wrapped as :class:`EmbyApiError`) for
       *TvChannel* objects because the real server does not expose channels
       through the generic *items* namespace.
    2. ``/LiveTv/Channels/{id}`` – returns a minimal JSON payload so that
       :py:meth:`EmbyAPI.get_item` can succeed via its new fallback route.
    """

    def __init__(self) -> None:  # noqa: D401 – simple stub helper
        self.calls: list[Dict[str, Any]] = []

    async def __call__(self, method: str, path: str, **kwargs: Any):  # noqa: D401 – stub signature
        self.calls.append({"method": method, "path": path, **kwargs})

        # Simulate server behaviour -----------------------------------------------------
        if path.startswith("/Items/"):
            # Generic item namespace – Emby responds with 404 for TvChannel ids.
            raise EmbyApiError("Not Found")

        if path.startswith("/LiveTv/Channels/"):
            # Dedicated Live-TV endpoint – return minimal channel metadata.
            channel_id = path.split("/")[-1]
            return {"Id": channel_id, "Type": "TvChannel", "Name": "Stub Channel"}

        # Defensive – any other route should not be used by the code-path under test.
        raise AssertionError(f"Unexpected API call to {path}")


# ---------------------------------------------------------------------------
# Test – get_item() must fall back to /LiveTv/Channels/{Id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_item_fallbacks_to_live_tv(monkeypatch):
    """`get_item()` should resolve TvChannel ids via the Live-TV endpoint."""

    stubber = _TvChannelStubber()

    # Stand-alone EmbyAPI instance – we pass a dummy aiohttp session (SimpleNamespace)
    # so that the helper does not attempt to create a *real* client session during the test.
    api = EmbyAPI(None, host="emby", api_key="k", session=SimpleNamespace())

    # Replace the private HTTP helper with our stub.
    monkeypatch.setattr(api, "_request", stubber)  # type: ignore[attr-defined]

    # Call under test – user_id intentionally omitted to replicate the common UI path.
    item = await api.get_item("12345")

    # The helper must return the *TvChannel* stub payload from the fallback route.
    assert item == {"Id": "12345", "Type": "TvChannel", "Name": "Stub Channel"}

    # Sanity check – ensure both the *items* lookup *and* the Live-TV fallback were attempted.
    paths = [c["path"] for c in stubber.calls]
    assert "/Items/12345" in paths
    assert "/LiveTv/Channels/12345" in paths
