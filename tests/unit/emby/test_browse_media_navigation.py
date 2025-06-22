"""Unit tests for Emby *async_browse_media* implementation (issue #29).

These tests exercise the **happy-path** navigation scenarios that the
`async_browse_media` helper inside :pymod:`components.emby.media_player`
implements:

* Root browse – returns Emby *views* (libraries)
* Navigating into a library – returns children (pagination slice)
* Navigating to a playable leaf – returns a non-expandable node

Error-handling as well as the *media_source* fallback path are covered by
separate test-modules.
"""

from __future__ import annotations

import types
from typing import Any, Dict, List

import pytest

from homeassistant.components.media_player.browse_media import BrowseMedia, MediaClass


# ---------------------------------------------------------------------------
# Lightweight stub for *custom_components.emby.api.EmbyAPI*
# ---------------------------------------------------------------------------


class _StubEmbyAPI:  # pylint: disable=too-few-public-methods
    """Very small subset of the real :class:`EmbyAPI` runtime behaviour."""

    def __init__(self):
        # Public so tests can patch directly.
        self.views: List[Dict[str, Any]] = []
        self.items_by_id: Dict[str, Dict[str, Any]] = {}
        self.children_by_parent: Dict[str, List[Dict[str, Any]]] = {}

        # The thumbnail helper prefixes URLs with *self._base*
        self._base = "http://emby.local"  # pylint: disable=invalid-name

    # ------------------------------------------------------------------
    # API surface utilised by *async_browse_media*
    # ------------------------------------------------------------------

    async def get_user_views(self, _user_id: str):  # noqa: D401 – mimic signature
        return self.views

    async def get_item(self, item_id: str):  # noqa: D401
        return self.items_by_id.get(item_id)

    async def get_item_children(
        self,
        parent_id: str,
        *,
        user_id: str | None = None,  # noqa: D401 – kept for parity
        start_index: int = 0,
        limit: int = 100,
    ):  # noqa: D401 – simple stub
        # Slice the pre-registered children list just like the real endpoint.
        all_children = self.children_by_parent.get(parent_id, [])
        slice_ = all_children[start_index : start_index + limit]

        return {
            "Items": slice_,
            "TotalRecordCount": len(all_children),
        }

    # The *async_browse_media* implementation may fall back to *get_sessions*
    # when the *UserId* cannot be resolved from the device object.  The tests
    # inject *UserId* directly therefore this helper is never invoked – it is
    # still provided defensively so an unexpected call leads to a readable
    # assertion failure instead of an *AttributeError*.

    async def get_sessions(self, *_, **__):  # noqa: D401 – pragma: no cover
        raise AssertionError("get_sessions called unexpectedly during tests")


# ---------------------------------------------------------------------------
# Fixture – reusable EmbyDevice instance prepared for browsing tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def emby_device(monkeypatch):  # noqa: D401 – pytest naming convention
    """Return an :class:`EmbyDevice` with *async_browse_media* ready to use."""

    from custom_components.emby.media_player import EmbyDevice as _EmbyDevice

    dev = _EmbyDevice.__new__(_EmbyDevice)  # type: ignore[arg-type]

    # The wrapped *pyemby* device object – only minimal attributes required
    # by the helper paths executed in this test-module are populated.
    stub_inner = types.SimpleNamespace(
        session_raw={"UserId": "user-1"},
    )

    dev.device = stub_inner
    dev.device_id = "device-x"
    dev._current_session_id = None  # pylint: disable=protected-access
    dev.hass = object()  # not used by code under test here

    # Prepare a fresh API stub and monkey-patch the resolver *for this
    # specific instance* – the same pattern is used by other unit tests in
    # the repository.
    api_stub = _StubEmbyAPI()
    dev._get_emby_api = lambda: api_stub  # type: ignore[attr-defined]  # noqa: WPS437

    # Expose the stub so individual test cases can pre-populate it with data.
    dev._api_stub = api_stub  # type: ignore[attr-defined]

    return dev


# ---------------------------------------------------------------------------
# Helper – register synthetic library with children & playable leaf
# ---------------------------------------------------------------------------


def _register_library(api: _StubEmbyAPI):  # noqa: D401 – internal helper
    """Populate *api* with deterministic fixtures used by tests."""

    # Two libraries at root level (movies & tv shows)
    api.views.extend(
        [
            {
                "Id": "lib-movies",
                "Name": "Movies",
                "CollectionType": "movies",
                "ImageTags": {"Primary": "thumb-movies"},
            },
            {
                "Id": "lib-tv",
                "Name": "TV Shows",
                "CollectionType": "tvshows",
                "ImageTags": {},
            },
        ]
    )

    # Metadata for *lib-movies* itself (treated as directory)
    api.items_by_id["lib-movies"] = {
        "Id": "lib-movies",
        "Name": "Movies",
        "CollectionType": "movies",
    }

    # Two playable movies inside the library
    api.children_by_parent["lib-movies"] = [
        {
            "Id": "mov-1",
            "Name": "Inception",
            "Type": "Movie",
        },
        {
            "Id": "mov-2",
            "Name": "Arrival",
            "Type": "Movie",
        },
    ]

    # Individual metadata for playable items
    api.items_by_id["mov-1"] = {
        "Id": "mov-1",
        "Name": "Inception",
        "Type": "Movie",
    }
    api.items_by_id["mov-2"] = {
        "Id": "mov-2",
        "Name": "Arrival",
        "Type": "Movie",
    }


# ---------------------------------------------------------------------------
# Tests – root, directory and leaf browsing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_root_browse_returns_views(emby_device):  # noqa: D401 – pytest naming
    """Root browse must list Emby *views* (libraries)."""

    api = emby_device._api_stub  # type: ignore[attr-defined]
    _register_library(api)

    result: BrowseMedia = await emby_device.async_browse_media()

    # Root node characteristics
    assert result.title == "Emby Library"
    assert result.media_class == MediaClass.DIRECTORY
    assert result.can_play is False
    assert result.can_expand is True

    # Two libraries expected
    assert result.children is not None
    assert len(result.children) == 2

    first_child = result.children[0]
    assert first_child.title == "Movies"
    assert first_child.media_class == MediaClass.MOVIE
    assert first_child.media_content_id == "emby://lib-movies"


@pytest.mark.asyncio
async def test_library_directory_browse_returns_children(emby_device):  # noqa: D401
    """Browsing into a library must return its children slice."""

    api = emby_device._api_stub  # type: ignore[attr-defined]
    _register_library(api)

    path = "emby://lib-movies"
    result: BrowseMedia = await emby_device.async_browse_media(media_content_id=path)

    # Directory node characteristics
    assert result.title == "Movies"
    assert result.media_class == MediaClass.MOVIE
    assert result.can_expand is True

    # Two playable child movies + no pagination for small list
    assert result.children is not None
    assert len(result.children) == 2

    child_titles = {c.title for c in result.children}
    assert {"Inception", "Arrival"} == child_titles


@pytest.mark.asyncio
async def test_leaf_browse_returns_playable_node(emby_device):  # noqa: D401
    """Playable leaf items must be returned with *can_play=True* and no children."""

    api = emby_device._api_stub  # type: ignore[attr-defined]
    _register_library(api)

    path = "emby://mov-1"
    result: BrowseMedia = await emby_device.async_browse_media(media_content_id=path)

    assert result.title == "Inception"
    assert result.can_play is True
    assert result.can_expand is False
    assert result.children is None
