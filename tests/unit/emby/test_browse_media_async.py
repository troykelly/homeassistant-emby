"""Unit tests targeting :pymeth:`EmbyDevice.async_browse_media`.

The browse implementation contains a large amount of branching logic to build
the hierarchical *BrowseMedia* tree.  These tests focus on the most
important/high-level paths so the codebase gains meaningful coverage without
mocking every conceivable edge-case:

1. Root browse – returns library *views* plus the two virtual folders
   (Continue Watching / Favorites).
2. *Resume* virtual folder – validates pagination behaviour (Next/Prev nodes)
   and mapping of child items.
3. Error handling – unsupported URI scheme must raise *HomeAssistantError*.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest


# ---------------------------------------------------------------------------
# Shared helpers / constants
# ---------------------------------------------------------------------------


PAGE_SIZE = 100  # must stay in sync with *_PAGE_SIZE* constant in the module


class _StubAPI:  # pylint: disable=too-few-public-methods
    """Fake implementation exposing the small subset used by *async_browse_media*."""

    def __init__(self):  # noqa: D401 – minimal helper
        self._base = "https://emby.example.com"  # pylint: disable=invalid-name

    # -------------------------
    # API endpoints (async)
    # -------------------------

    async def get_user_views(self, _user_id):  # noqa: D401
        return [
            {"Id": "view1", "Name": "Movies", "CollectionType": "movies"},
            {"Id": "view2", "Name": "Shows", "CollectionType": "tvshows"},
        ]

    async def get_resume_items(self, _user_id, *, start_index: int, limit: int):  # noqa: D401
        # Build *limit* dummy movies so pagination paths can be tested.
        items = [
            {
                "Id": f"item-{i+start_index}",
                "Name": f"Resume {i+start_index}",
                "Type": "Movie",
                "ImageTags": {},
            }
            for i in range(limit)
        ]

        return {
            "Items": items,
            "TotalRecordCount": 250,  # deliberately > PAGE_SIZE to trigger Next node
        }

    async def get_favorite_items(self, _user_id, *, start_index: int, limit: int):  # noqa: D401
        # Simpler payload – no pagination required by the tests below.
        return {
            "Items": [
                {
                    "Id": "fav-1",
                    "Name": "Fav Movie",
                    "Type": "Movie",
                    "ImageTags": {},
                }
            ],
            "TotalRecordCount": 1,
        }

    async def get_item(self, _item_id):  # noqa: D401 – not used but defined for completeness
        return None

    async def get_sessions(self, *, force_refresh: bool = False):  # noqa: D401, ANN001 – unused
        return []


# ---------------------------------------------------------------------------
# Fixture – returns a fully wired *EmbyDevice*
# ---------------------------------------------------------------------------


@pytest.fixture()
def emby_device(monkeypatch):  # noqa: D401 – naming style consistent with suite
    from custom_components.embymedia.media_player import EmbyDevice

    dev = EmbyDevice.__new__(EmbyDevice)  # type: ignore[arg-type]

    # Fake *pyemby* device – only attributes referenced by the browse logic
    fake_device = SimpleNamespace(
        supports_remote_control=True,
        name="TV",
        state="Idle",
        username="john",
        session_id="sess-xyz",
        unique_id="dev123",
        session_raw={"UserId": "user-123"},
    )

    dev.device = fake_device
    dev.device_id = "dev123"
    dev.emby = SimpleNamespace(_host="h", _api_key="k", _port=8096, _ssl=False)
    dev.hass = None  # pyright: ignore[reportAttributeAccessIssue]
    dev._current_session_id = None  # pylint: disable=protected-access

    # Patch *async_write_ha_state* to a no-op so the tests do not require HA.
    dev.async_write_ha_state = lambda *_, **__: None  # type: ignore[assignment]

    # Inject *StubAPI* implementation.
    stub_api = _StubAPI()
    monkeypatch.setattr(dev, "_get_emby_api", lambda _self=dev: stub_api)  # type: ignore[arg-type]

    return dev


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_browse_root_includes_views_and_virtual_folders(emby_device):  # noqa: D401
    """Root browse should return *views* + two virtual directories."""

    root_node = await emby_device.async_browse_media()  # type: ignore[arg-type]

    # Two Emby *views* + Resume + Favorites → 4 children.
    assert len(root_node.children) == 4  # type: ignore[arg-type]

    titles = {child.title for child in root_node.children}
    assert {"Movies", "Shows", "Continue Watching", "Favorites"} <= titles


@pytest.mark.asyncio
async def test_browse_resume_pagination_nodes(emby_device):  # noqa: D401
    """The *resume* virtual folder must expose a *Next →* node when more data is available."""

    resume_node = await emby_device.async_browse_media(media_content_id="emby://resume")  # type: ignore[arg-type]

    # `_StubAPI.get_resume_items` returns exactly ``PAGE_SIZE`` items and
    # reports *TotalRecordCount* 250, therefore a single *Next →* node should
    # be appended.
    titles = [child.title for child in resume_node.children]

    assert titles[-1] == "Next →"

    # Follow the *Next* link – ensure it prepends a *Prev* node and (again)
    # appends the next *Next* node.
    next_uri = resume_node.children[-1].media_content_id  # type: ignore[arg-type]
    assert next_uri.endswith("start=100")

    second_slice = await emby_device.async_browse_media(media_content_id=next_uri)  # type: ignore[arg-type]

    slice_titles = [child.title for child in second_slice.children]

    assert slice_titles[0] == "← Prev" and slice_titles[-1] == "Next →"


@pytest.mark.asyncio
async def test_async_browse_media_invalid_scheme_raises(emby_device):  # noqa: D401
    """Unsupported scheme must bubble up as *HomeAssistantError*."""

    from homeassistant.exceptions import HomeAssistantError

    with pytest.raises(HomeAssistantError):
        await emby_device.async_browse_media(media_content_id="http://not-emby")  # type: ignore[arg-type]
