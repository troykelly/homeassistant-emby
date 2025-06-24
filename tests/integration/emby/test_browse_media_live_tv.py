"""Integration test for *Live TV* browsing (GitHub issue #202).

The regression surfaced when navigating into the **Live TV** view from the
Emby media browser root – the integration incorrectly queried the generic
`/Users/{user}/Items` endpoint which yields a list of *Artist* objects instead
of the expected `TvChannel` items.  The fix introduces a dedicated code path
that leverages the `/LiveTv/Channels` REST route.

This test exercises the behaviour on a fully wired
:pyclass:`custom_components.embymedia.media_player.EmbyDevice` instance with
all outbound HTTP calls stubbed so the logic can run without an actual Emby
server.
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

        # --------------------------------------------------------------
        # Emby endpoints exercised by *Live TV* browse flow
        # --------------------------------------------------------------

        # Root library views
        if path == "/Users/user-1/Views" and method == "GET":
            return {
                "Items": [
                    {"Id": "lib-live", "Name": "Live TV", "CollectionType": "livetv"},
                ]
            }

        # Attempt to resolve the view via the **global** `/Items/{id}` route –
        # Emby responds with *404* for library roots therefore we emulate the
        # same behaviour by raising :class:`EmbyApiError` so the integration
        # falls back to the user-scoped variant.
        if path == "/Items/lib-live" and method == "GET":
            from custom_components.embymedia.api import EmbyApiError

            raise EmbyApiError("Item not found")

        # The **user-scoped** endpoint *does* resolve and returns metadata
        # describing the *Live TV* view.  The payload intentionally contains
        # ``CollectionType == 'livetv'`` so the browsing logic recognises the
        # special view and queries `/LiveTv/Channels` for the actual
        # children instead of the generic `/Items/{id}/Children` route (bug
        # #202).
        if path == "/Users/user-1/Items/lib-live" and method == "GET":
            return {
                "Id": "lib-live",
                "Name": "Live TV",
                "Type": "UserView",
                "CollectionType": "livetv",
                "ImageTags": {},
                "UserData": {},
            }

        # Correct endpoint for channels listing – respond with two channels
        # so we can assert the mapping to *BrowseMedia* objects.
        if path == "/LiveTv/Channels" and method == "GET":
            # Verify that the caller forwarded pagination & user parameters
            params = kwargs.get("params", {})
            assert params.get("UserId") == "user-1"  # type: ignore[arg-type]

            return {
                "Items": [
                    {
                        "Id": "ch-1",
                        "Name": "BBC One",
                        "Type": "TvChannel",
                        "ImageTags": {"Primary": "img1"},
                    },
                    {
                        "Id": "ch-2",
                        "Name": "CNN",
                        "Type": "TvChannel",
                        "ImageTags": {"Primary": "img2"},
                    },
                ],
                "TotalRecordCount": 2,
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
def emby_device():  # noqa: D401 – pytest naming convention
    """Return a fully wired :class:`EmbyDevice` ready for integration tests."""

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

    # Provide attributes accessed by Home Assistant helpers.
    dev.entity_id = "media_player.emby_living_room"  # type: ignore[attr-defined]
    dev.async_write_ha_state = lambda *_, **__: None  # type: ignore[assignment]

    return dev


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_browse_live_tv_returns_channels(http_stub, emby_device):  # noqa: D401, ANN001
    """Verify that **Live TV** browse returns *TvChannel* objects."""

    from homeassistant.components.media_player.const import MediaClass

    # 1. Retrieve root – required to populate the Views cache inside
    #    *EmbyAPI* so the second call can resolve *Live TV* metadata without
    #    hitting additional endpoints.
    root_node = await emby_device.async_browse_media()

    live_tv_node = next(child for child in root_node.children if child.title == "Live TV")  # type: ignore[arg-type]

    # 2. Navigate into the Live TV container – this triggers the new helper
    #    which queries `/LiveTv/Channels`.
    channels_node = await emby_device.async_browse_media(
        live_tv_node.media_content_type,
        live_tv_node.media_content_id,
    )

    assert channels_node.children, "Expected channels list to be non-empty"  # type: ignore[arg-type]

    for child in channels_node.children:  # type: ignore[arg-type]
        assert child.media_class == MediaClass.CHANNEL  # type: ignore[attr-defined]

    # Ensure the correct HTTP endpoints were invoked in order.
    assert (
        ("GET", "/Users/user-1/Views")
        == http_stub.calls[0][0:2]
    )
    # Last call must be the channels endpoint
    assert http_stub.calls[-1][0:2] == ("GET", "/LiveTv/Channels")
