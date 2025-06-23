"""Regression tests for GitHub issue #132.

The Home Assistant frontend concatenates ``media_content_type`` and
``media_content_id`` with a comma when requesting a browse path.  The Emby
integration previously expected a *bare* ``emby://`` URI which caused the
helper to bail out with *Unsupported media_content_id*.  This module ensures
that the implementation now correctly splits and handles the combined
parameter.
"""

from __future__ import annotations

import types

import pytest


class _StubEmbyAPI:  # pylint: disable=too-few-public-methods
    """Very small stub exposing just enough API surface for the test."""

    def __init__(self):
        # Expose ``_base`` so the thumbnail helper can build URLs.
        self._base = "http://emby.local"  # pylint: disable=invalid-name

    async def get_user_views(self, _user_id):  # noqa: D401 – unused in this test
        return []

    async def get_item(self, item_id):  # noqa: D401 – minimal metadata payload
        # Return a *library* directory so the browse helper treats it as
        # expandable.
        return {
            "Id": item_id,
            "Name": "TV Shows",
            "CollectionType": "tvshows",
        }

    async def get_item_children(
        self,
        _parent_id,
        *,
        user_id: str | None = None,  # noqa: D401 – kept for parity
        start_index: int = 0,
        limit: int = 100,
    ):  # noqa: D401 – returns empty slice
        return {
            "Items": [],
            "TotalRecordCount": 0,
        }

    async def get_sessions(self, *_, **__):  # noqa: D401 – pragma: no cover
        return []


@pytest.fixture()
def emby_device(monkeypatch):  # noqa: D401 – pytest naming convention
    """Return an *EmbyDevice* instance wired with the stub API."""

    from custom_components.embymedia.media_player import EmbyDevice as _EmbyDevice

    dev = _EmbyDevice.__new__(_EmbyDevice)  # type: ignore[arg-type]

    # Provide minimal *pyemby* device attributes accessed by the code.
    dev.device = types.SimpleNamespace(session_raw={"UserId": "user-1"})
    dev.device_id = "dev-combined"
    dev._current_session_id = None  # pylint: disable=protected-access
    dev.hass = object()  # pyright: ignore[reportAttributeAccessIssue]

    # Inject stub API implementation.
    api = _StubEmbyAPI()
    dev._get_emby_api = lambda: api  # type: ignore[attr-defined]

    return dev


# ---------------------------------------------------------------------------
# Test – combined parameter is handled
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_combined_content_type_and_id_handled(emby_device):  # noqa: D401
    """Requesting "tvshow,emby://<id>" must return a *BrowseMedia* node."""

    from homeassistant.components.media_player.browse_media import BrowseMedia

    path = "tvshow,emby://lib-tv"

    result: BrowseMedia = await emby_device.async_browse_media(
        media_content_id=path,
    )

    # The helper should treat the item as a *directory* (library) and mark it
    # as expandable even though our stub returns no children.
    assert result.can_expand is True
    assert result.title == "TV Shows"