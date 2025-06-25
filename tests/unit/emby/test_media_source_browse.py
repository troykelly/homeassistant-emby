"""Unit tests for *async_browse_media* implementation (GitHub issue #237)."""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass

import pytest

# ---------------------------------------------------------------------------
# Dynamic stubs for *homeassistant.components.media_source* & friends
# ---------------------------------------------------------------------------


def _install_media_source_stubs():  # noqa: D401 – helper, not a test
    """Populate *sys.modules* with minimal Home Assistant stubs."""

    parent_name = "homeassistant.components"

    # Ensure top-level *homeassistant* package exists.
    if "homeassistant" not in sys.modules:
        sys.modules["homeassistant"] = types.ModuleType("homeassistant")

    if parent_name not in sys.modules:
        sys.modules[parent_name] = types.ModuleType(parent_name)

    # --------------------------------------------------------------
    # media_source.models module – carries data-classes
    # --------------------------------------------------------------

    models_mod = types.ModuleType(f"{parent_name}.media_source.models")

    class MediaSourceItem:  # pylint: disable=too-few-public-methods
        def __init__(self, identifier: str):
            self.identifier = identifier

    @dataclass(slots=True)
    class ResolveMediaSource:  # noqa: D401 – minimal stub
        url: str
        mime_type: str | None = None

    class BrowseMediaSource:  # pylint: disable=too-few-public-methods
        """Flexible stub replicating the essential behaviour."""

        def __init__(
            self,
            *,
            domain: str | None,
            identifier: str | None,
            **kwargs,
        ) -> None:  # noqa: D401 – accept arbitrary props

            self.domain = domain
            self.identifier = identifier

            # Materialise common BrowseMedia attributes so test assertions work.
            self.media_class = kwargs.get("media_class")
            self.media_content_type = kwargs.get("media_content_type")
            self.title = kwargs.get("title")
            self.can_play = kwargs.get("can_play")
            self.can_expand = kwargs.get("can_expand")
            self.children = kwargs.get("children", [])

    models_mod.MediaSourceItem = MediaSourceItem  # type: ignore[attr-defined]
    models_mod.ResolveMediaSource = ResolveMediaSource  # type: ignore[attr-defined]
    models_mod.BrowseMediaSource = BrowseMediaSource  # type: ignore[attr-defined]

    # --------------------------------------------------------------
    # media_source module – exposes base-class & error
    # --------------------------------------------------------------

    ms_mod = types.ModuleType(f"{parent_name}.media_source")

    class BrowseError(RuntimeError):
        """Stub replicating HA exception."""

    class MediaSource:  # pylint: disable=too-few-public-methods
        def __init__(self, domain: str, name: str):  # noqa: D401 – mimic sig
            self.domain = domain
            self.name = name

    ms_mod.MediaSource = MediaSource  # type: ignore[attr-defined]
    ms_mod.BrowseError = BrowseError  # type: ignore[attr-defined]
    ms_mod.models = models_mod  # type: ignore[attr-defined]

    # --------------------------------------------------------------
    # media_player sub-module – required for enumerations
    # --------------------------------------------------------------

    mp_mod = types.ModuleType(f"{parent_name}.media_player")

    class BrowseMedia:  # pylint: disable=too-few-public-methods
        def __init__(self, **kwargs):  # noqa: D401 – ignore details
            for k, v in kwargs.items():
                setattr(self, k, v)

    class _SimpleEnum(str):
        def __new__(cls, value):
            return str.__new__(cls, value)

    class MediaClass(_SimpleEnum):
        DIRECTORY = "directory"
        MOVIE = "movie"
        TV_SHOW = "tvshow"
        MUSIC = "music"

    class MediaType(_SimpleEnum):
        VIDEO = "video"
        MUSIC = "music"

    mp_mod.BrowseMedia = BrowseMedia  # type: ignore[attr-defined]
    mp_mod.MediaClass = MediaClass  # type: ignore[attr-defined]
    mp_mod.MediaType = MediaType  # type: ignore[attr-defined]

    # --------------------------------------------------------------
    # Register sub-modules
    # --------------------------------------------------------------

    sys.modules[models_mod.__name__] = models_mod
    sys.modules[ms_mod.__name__] = ms_mod
    sys.modules[mp_mod.__name__] = mp_mod

    # Attach *media_source* and *media_player* to parent namespace.
    components_pkg = sys.modules[parent_name]
    components_pkg.media_source = ms_mod  # type: ignore[attr-defined]
    components_pkg.media_player = mp_mod  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Stub *EmbyAPI* exposing only the methods used by the browse helper
# ---------------------------------------------------------------------------


from custom_components.embymedia.api import EmbyAPI  # move import below stubs to avoid circular


class _StubEmbyAPI(EmbyAPI):  # type: ignore[misc]
    """Mock implementation returning hard-coded library data."""

    # pylint: disable=useless-super-delegation,too-few-public-methods

    def __init__(self):  # noqa: D401 – no base initialisation
        # Deliberately bypass parent __init__ – we only need method stubs.
        self._base = "https://emby.local"  # pylint: disable=invalid-name

    # Active sessions – returns single user
    async def get_sessions(self, *, force_refresh: bool = False):  # noqa: D401 – unused param
        return [{"UserId": "user-1"}]

    async def get_user_views(self, _user_id):  # noqa: D401 – mimic sig
        return [
            {"Id": "view1", "Name": "Movies", "CollectionType": "movies"},
            {"Id": "view2", "Name": "Shows", "CollectionType": "tvshows"},
        ]

    async def get_resume_items(self, _user_id, *, start_index: int, limit: int):  # noqa: D401
        items = [
            {
                "Id": f"resume-{i+start_index}",
                "Name": f"Resume {i}",
                "Type": "Movie",
            }
            for i in range(limit)
        ]
        return {
            "Items": items,
            "TotalRecordCount": 150,
        }

    async def get_favorite_items(self, _user_id, *, start_index: int, limit: int):  # noqa: D401
        return {
            "Items": [
                {"Id": "fav1", "Name": "Fav 1", "Type": "Movie"},
                {"Id": "fav2", "Name": "Fav 2", "Type": "Movie"},
            ],
            "TotalRecordCount": 2,
        }

    async def get_item_children(self, *_args, **_kwargs):  # noqa: D401 – not used in tests
        return {"Items": [], "TotalRecordCount": 0}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _patch_homeassistant_modules(monkeypatch):  # noqa: D401 – auto fixture
    _install_media_source_stubs()


@pytest.fixture()
def provider(monkeypatch):  # noqa: D401 – naming per pytest convention
    """Return an initialised *EmbyMediaSource* instance with stub API."""

    from custom_components.embymedia.media_source import EmbyMediaSource

    hass = types.SimpleNamespace()
    hass.data = {"embymedia": {"entry": {"api": _StubEmbyAPI()}}}

    prov = EmbyMediaSource(hass)
    return prov


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_browse_root_includes_views_and_virtual_dirs(provider):  # noqa: D401
    """Root browse should list Emby views plus Resume & Favorites folders."""

    from homeassistant.components.media_source.models import MediaSourceItem  # type: ignore

    root_item = MediaSourceItem(identifier="")

    tree = await provider.async_browse_media(root_item)  # type: ignore[arg-type]

    # Expect 4 children: 2 views + Resume + Favorites
    assert len(tree.children) == 4  # type: ignore[attr-defined]

    titles = {child.title for child in tree.children}
    assert {"Movies", "Shows", "Continue Watching", "Favorites"} <= titles


@pytest.mark.asyncio
async def test_browse_resume_pagination_nodes(provider):  # noqa: D401
    """Resume folder must expose Next tile when more items available."""

    from homeassistant.components.media_source.models import MediaSourceItem  # type: ignore

    resume_item = MediaSourceItem(identifier="resume")
    resume_dir = await provider.async_browse_media(resume_item)  # type: ignore[arg-type]

    # The stub API returns PAGE_SIZE (100) items out of 150 total → Next tile
    last_child_title = resume_dir.children[-1].title  # type: ignore[attr-defined]
    assert last_child_title == "Next →"
