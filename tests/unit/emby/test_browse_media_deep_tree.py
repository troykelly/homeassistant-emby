"""Deep navigation tests for *async_browse_media* (GitHub issue #78).

This module verifies that the Emby browse implementation correctly exposes a
multi-level content hierarchy and preserves the `media_class`, `can_play` and
`can_expand` flags on every level:

root (library) → TV Show → Season → Episode (playable leaf)
"""

from __future__ import annotations

import types
from typing import Dict, List, Any

import pytest

from homeassistant.components.media_player.const import MediaClass
from homeassistant.components.media_player.browse_media import BrowseMedia


class _StubEmbyAPI:  # pylint: disable=too-few-public-methods
    """Minimal stub exposing only the endpoints used by the code-path."""

    def __init__(self):
        self.views: List[Dict[str, Any]] = []
        self.items_by_id: Dict[str, Dict[str, Any]] = {}
        self.children_by_parent: Dict[str, List[Dict[str, Any]]] = {}

        self._base = "http://emby.local"  # required by thumbnail helper

    # ------------------------------------------------------------------
    # API surface consumed by *async_browse_media*
    # ------------------------------------------------------------------

    async def get_user_views(self, _user_id: str):  # noqa: D401 – mimic signature
        return self.views

    async def get_item(self, item_id: str):  # noqa: D401 – simple map lookup
        return self.items_by_id.get(item_id)

    async def get_item_children(
        self,
        parent_id: str,
        *,
        user_id: str | None = None,  # noqa: D401 – parity with real method
        start_index: int = 0,
        limit: int = 100,
    ):  # noqa: D401 – simplified slice
        slice_ = self.children_by_parent.get(parent_id, [])[start_index : start_index + limit]
        return {
            "Items": slice_,
            "TotalRecordCount": len(self.children_by_parent.get(parent_id, [])),
        }

    # *get_sessions* may be called when the helper fails to resolve *UserId*
    # from the device object.  Tests inject it directly therefore the method
    # must not be invoked.

    async def get_sessions(self, *_, **__):  # noqa: D401 – pragma: no cover
        raise AssertionError("Unexpected call to get_sessions during deep tree test")


# ---------------------------------------------------------------------------
# Fixtures – EmbyDevice instance & populated deep library hierarchy
# ---------------------------------------------------------------------------


@pytest.fixture()
def emby_device(monkeypatch):  # noqa: D401 – pytest naming convention
    """Return an *EmbyDevice* wired with the stub API and deep hierarchy."""

    from custom_components.embymedia.media_player import EmbyDevice as _EmbyDevice

    dev = _EmbyDevice.__new__(_EmbyDevice)  # type: ignore[arg-type]

    # Minimal pyemby stub – only attributes accessed by the logic under test
    # are populated.
    stub_inner = types.SimpleNamespace(
        session_raw={"UserId": "user-42"},
    )

    dev.device = stub_inner
    dev.device_id = "device-deep"
    dev._current_session_id = None  # pylint: disable=protected-access
    dev.hass = object()  # pyright: ignore[reportAttributeAccessIssue]

    api = _StubEmbyAPI()
    dev._get_emby_api = lambda: api  # type: ignore[attr-defined]
    dev._api_stub = api  # type: ignore[attr-defined]

    # --------------------------------------------------------------
    # Build deep hierarchy
    # --------------------------------------------------------------

    # Root library
    api.views.append(
        {
            "Id": "lib-tv",
            "Name": "TV Shows",
            "CollectionType": "tvshows",
        }
    )

    # The library itself (directory)
    api.items_by_id["lib-tv"] = {
        "Id": "lib-tv",
        "Name": "TV Shows",
        "CollectionType": "tvshows",
    }

    # Show → Season → Episode
    api.children_by_parent["lib-tv"] = [
        {
            "Id": "show-1",
            "Name": "The Expanse",
            "Type": "Series",
        }
    ]

    api.items_by_id["show-1"] = {
        "Id": "show-1",
        "Name": "The Expanse",
        "Type": "Series",
    }

    api.children_by_parent["show-1"] = [
        {
            "Id": "season-1",
            "Name": "Season 1",
            "Type": "Season",
        }
    ]

    api.items_by_id["season-1"] = {
        "Id": "season-1",
        "Name": "Season 1",
        "Type": "Season",
    }

    api.children_by_parent["season-1"] = [
        {
            "Id": "ep-1",
            "Name": "Dulcinea",
            "Type": "Episode",
        }
    ]

    api.items_by_id["ep-1"] = {
        "Id": "ep-1",
        "Name": "Dulcinea",
        "Type": "Episode",
    }

    return dev


# ---------------------------------------------------------------------------
# Test – navigate deep tree
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deep_tree_navigation(emby_device):  # noqa: D401 – pytest naming convention
    """Navigate library → show → season → episode and assert flags."""

    # Level 0 – root
    root: BrowseMedia = await emby_device.async_browse_media()

    # The first child is the TV library registered above
    tv_lib_node = root.children[0]  # type: ignore[index]
    assert tv_lib_node.media_class == MediaClass.TV_SHOW
    assert tv_lib_node.can_expand is True

    # Level 1 – inside TV library (should list shows)
    tv_library: BrowseMedia = await emby_device.async_browse_media(
        media_content_id=tv_lib_node.media_content_id
    )
    first_show = tv_library.children[0]  # type: ignore[index]
    assert first_show.title == "The Expanse"
    assert first_show.media_class == MediaClass.TV_SHOW

    # Level 2 – seasons directory for the show
    seasons_dir: BrowseMedia = await emby_device.async_browse_media(
        media_content_id=first_show.media_content_id
    )
    season_node = seasons_dir.children[0]  # type: ignore[index]
    assert season_node.media_class == MediaClass.SEASON

    # Level 3 – episode leaf
    season_browse: BrowseMedia = await emby_device.async_browse_media(
        media_content_id=season_node.media_content_id
    )
    episode_node = season_browse.children[0]  # type: ignore[index]
    assert episode_node.can_play is True
    assert episode_node.can_expand is False
    assert episode_node.media_class == MediaClass.EPISODE
