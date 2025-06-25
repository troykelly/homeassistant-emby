"""Integration test verifying **entity-less** Emby media browsing (issue #238).

The scenario mirrors a user opening Home Assistant's *Media* sidebar **without
selecting any target entity**.  In this mode the frontend talks directly to
the *media_source* provider that we ship with the integration.  The test
therefore exercises :pymeth:`custom_components.embymedia.media_source.EmbyMediaSource.async_browse_media`
on a fully initialised provider instance wired up with a stubbed
:class:`custom_components.embymedia.api.EmbyAPI` implementation.

No network traffic is sent – the stub returns canned JSON so the code path is
identical to production whilst remaining deterministic and fast.
"""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass

import pytest

# ---------------------------------------------------------------------------
# Home Assistant stub helpers – *identical* to the ones used by the unit test
# test_media_source_browse.py but duplicated here to keep the integration test
# self-contained and easier to reason about.
# ---------------------------------------------------------------------------


def _install_homeassistant_stubs() -> None:  # noqa: D401 – helper, not a test
    """Populate *sys.modules* with minimal HA packages required by provider."""

    parent_ns = "homeassistant.components"

    # Ensure the top-level *homeassistant* package exists.
    if "homeassistant" not in sys.modules:
        sys.modules["homeassistant"] = types.ModuleType("homeassistant")

    if parent_ns not in sys.modules:
        sys.modules[parent_ns] = types.ModuleType(parent_ns)

    # --------------------------------------------------------------
    # media_source.models – carries data-classes HA passes around
    # --------------------------------------------------------------

    models_mod = types.ModuleType(f"{parent_ns}.media_source.models")

    class MediaSourceItem:  # pylint: disable=too-few-public-methods
        def __init__(self, identifier: str | None = None):
            self.identifier = identifier or ""

    @dataclass(slots=True)
    class ResolveMediaSource:  # noqa: D401 – mimic HA naming
        url: str
        mime_type: str | None = None

    class BrowseMediaSource:  # pylint: disable=too-few-public-methods
        """Flexible stub that accepts arbitrary keyword arguments."""

        def __init__(
            self,
            *,
            domain: str | None,
            identifier: str | None,
            **kwargs,
        ) -> None:  # noqa: D401 – mirror HA signature in spirit

            self.domain = domain
            self.identifier = identifier

            # Persist commonly accessed attributes when supplied so that test
            # assertions can introspect them.  Fallbacks make the implementation
            # tolerant to future changes without requiring test updates.
            self.media_class = kwargs.get("media_class")
            self.media_content_type = kwargs.get("media_content_type")
            self.title = kwargs.get("title")
            self.can_play = kwargs.get("can_play")
            self.can_expand = kwargs.get("can_expand")
            self.children = kwargs.get("children")

    models_mod.MediaSourceItem = MediaSourceItem  # type: ignore[attr-defined]
    models_mod.ResolveMediaSource = ResolveMediaSource  # type: ignore[attr-defined]
    models_mod.BrowseMediaSource = BrowseMediaSource  # type: ignore[attr-defined]

    # --------------------------------------------------------------
    # media_source package – base class + BrowseError exception
    # --------------------------------------------------------------

    ms_mod = types.ModuleType(f"{parent_ns}.media_source")

    class BrowseError(RuntimeError):
        """Stub matching HA's original exception type."""

    class MediaSource:  # pylint: disable=too-few-public-methods
        def __init__(self, domain: str, name: str):  # noqa: D401 – mimic sig
            self.domain = domain
            self.name = name

    ms_mod.MediaSource = MediaSource  # type: ignore[attr-defined]
    ms_mod.BrowseError = BrowseError  # type: ignore[attr-defined]
    ms_mod.models = models_mod  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # media_player – only stub when the real component is **not** present.
    # ------------------------------------------------------------------

    if f"{parent_ns}.media_player" not in sys.modules:
        mp_mod = types.ModuleType(f"{parent_ns}.media_player")

        class _SimpleEnum(str):
            def __new__(cls, value: str):  # noqa: D401 – behave like Enum/str
                return str.__new__(cls, value)

        class MediaClass(_SimpleEnum):
            DIRECTORY = "directory"
            MOVIE = "movie"
            TV_SHOW = "tvshow"

        class MediaType(_SimpleEnum):
            VIDEO = "video"
            MOVIE = "movie"

        # The search test-suite expects these helpers to exist.

        class SearchMediaQuery(dict):  # type: ignore[misc]
            """Very small stand-in mimicking HA's helper dataclass."""

            def __init__(self, *args, **kwargs):  # noqa: D401 – keep flexible
                super().__init__(*args, **kwargs)

        DOMAIN = "media_player"

        class BrowseMedia:  # pylint: disable=too-few-public-methods
            def __init__(self, **kwargs):
                for key, val in kwargs.items():
                    setattr(self, key, val)

        mp_mod.MediaClass = MediaClass  # type: ignore[attr-defined]
        mp_mod.MediaType = MediaType  # type: ignore[attr-defined]
        mp_mod.SearchMediaQuery = SearchMediaQuery  # type: ignore[attr-defined]
        mp_mod.DOMAIN = DOMAIN  # type: ignore[attr-defined]
        mp_mod.BrowseMedia = BrowseMedia  # type: ignore[attr-defined]

        sys.modules[mp_mod.__name__] = mp_mod

        # Attach stub to parent components namespace.
        components_pkg = sys.modules[parent_ns]
        components_pkg.media_player = mp_mod  # type: ignore[attr-defined]

    # --------------------------------------------------------------
    # Register *media_source* stubs regardless.
    # --------------------------------------------------------------

    sys.modules[models_mod.__name__] = models_mod
    sys.modules[ms_mod.__name__] = ms_mod

    components_pkg = sys.modules[parent_ns]
    components_pkg.media_source = ms_mod  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Stub *EmbyAPI* returning canned payloads for browse calls
# ---------------------------------------------------------------------------


from custom_components.embymedia.api import EmbyAPI  # noqa: E402 – after stub install


class _StubEmbyAPI(EmbyAPI):  # type: ignore[misc]
    """Minimal async stub mimicking the subset used by *EmbyMediaSource*."""

    # pylint: disable=useless-super-delegation,too-few-public-methods

    def __init__(self):
        # Skip parent __init__ completely – we just override the needed methods.
        self._stub_base = "https://emby.local"  # pylint: disable=invalid-name

    # Active sessions – return single user so provider can pick up *UserId*.
    async def get_sessions(self, *, force_refresh: bool = False):  # noqa: D401 – match sig
        return [{"UserId": "user-x"}]

    # Root views
    async def get_user_views(self, _user_id):  # noqa: D401 – ignore param
        return [
            {"Id": "view-movies", "Name": "Movies", "CollectionType": "movies"},
            {"Id": "view-tv", "Name": "TV Shows", "CollectionType": "tvshows"},
        ]

    async def get_resume_items(self, _user_id, *, start_index: int, limit: int):  # noqa: D401
        # Pretend 3 resume entries in total → no pagination.
        items = [
            {"Id": "resume-1", "Name": "Resume 1", "Type": "Movie"},
            {"Id": "resume-2", "Name": "Resume 2", "Type": "Movie"},
            {"Id": "resume-3", "Name": "Resume 3", "Type": "Movie"},
        ][start_index : start_index + limit]

        return {"Items": items, "TotalRecordCount": 3}

    async def get_favorite_items(self, _user_id, *, start_index: int, limit: int):  # noqa: D401
        return {"Items": [], "TotalRecordCount": 0}

    async def get_item_children(self, *_args, **_kwargs):  # noqa: D401 – not reached in this test
        return {"Items": [], "TotalRecordCount": 0}


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _patch_ha_modules(monkeypatch):  # noqa: D401 – auto-fixture for all tests here
    _install_homeassistant_stubs()


@pytest.fixture()
def provider(monkeypatch):  # noqa: D401 – pytest naming convention
    """Return *EmbyMediaSource* instance wired with stubbed EmbyAPI."""

    from custom_components.embymedia.media_source import EmbyMediaSource

    hass = types.SimpleNamespace()
    # Mimic integration data layout – provider will iterate over *embymedia* dict.
    hass.data = {"embymedia": {"entry-1": {"api": _StubEmbyAPI()}}}

    return EmbyMediaSource(hass)


# ---------------------------------------------------------------------------
# Tests – root & Resume navigation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_global_media_root_lists_views_and_virtual(provider):  # noqa: D401
    """Root browse should include library views **and** virtual directories."""

    from homeassistant.components.media_source.models import MediaSourceItem  # type: ignore

    root_item = MediaSourceItem(identifier="")

    root_node = await provider.async_browse_media(root_item)  # type: ignore[arg-type]

    assert root_node.can_expand is True  # type: ignore[attr-defined]

    # Expect 4 direct children: 2 views + Resume + Favorites.
    assert len(root_node.children) == 4  # type: ignore[attr-defined]

    titles = {child.title for child in root_node.children}  # type: ignore[attr-defined]
    assert {"Movies", "TV Shows", "Continue Watching", "Favorites"} <= titles


@pytest.mark.asyncio
async def test_resume_folder_contains_items(provider):  # noqa: D401
    """Resume virtual directory should list stub items returned by API."""

    from homeassistant.components.media_source.models import MediaSourceItem  # type: ignore

    resume_node = await provider.async_browse_media(MediaSourceItem(identifier="resume"))  # type: ignore[arg-type]

    # 3 resume items returned by API → 3 children, no pagination.
    assert len(resume_node.children) == 3  # type: ignore[attr-defined]

    # Check metadata mapping of first child.
    first_child = resume_node.children[0]  # type: ignore[attr-defined]
    assert first_child.can_play is True  # type: ignore[attr-defined]
    assert first_child.media_content_type == "movie"  # type: ignore[attr-defined]
