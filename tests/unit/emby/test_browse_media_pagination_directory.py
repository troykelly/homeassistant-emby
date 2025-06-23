"""Regression tests for directory pagination (GitHub #134).

These tests verify that *async_browse_media* correctly injects virtual
"Prev" / "Next" nodes when browsing *regular* Emby folders that contain more
items than the configured page size (100).

The existing unit-tests already cover the same behaviour for the *resume*
virtual directory – this suite exercises the generic `/Items/{id}/Children`
path to ensure the logic is applied consistently across all code branches.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

# Keep the constant in sync with the module default.  Importing it avoids the
# risk of drift when developers adjust the value in the future.
from custom_components.embymedia.media_player import _PAGE_SIZE  # pylint: disable=protected-access


class _DirAPI:  # pylint: disable=too-few-public-methods
    """Stub implementation emulating an Emby folder with many children."""

    def __init__(self):  # noqa: D401
        self._base = "https://emby.local"  # pylint: disable=invalid-name

    # -------------------------
    # Required endpoints (async)
    # -------------------------

    async def get_item(self, _item_id):  # noqa: D401 – minimal payload
        return {"Id": _item_id, "Name": "Big Folder", "Type": "Folder"}

    async def get_item_children(  # noqa: D401, ANN001 – signature mirrors real client
        self,
        _item_id,
        *,
        user_id: str,
        start_index: int,
        limit: int,
    ):
        # Build *limit* dummy child items so pagination behaviour can be
        # tested without network calls.
        items = [
            {
                "Id": f"child-{i+start_index}",
                "Name": f"Child {i+start_index}",
                "Type": "Movie",
                "ImageTags": {},
            }
            for i in range(limit)
        ]

        return {
            "Items": items,
            # Large folder – deliberately more than two pages so both Prev &
            # Next nodes appear in intermediate slices.
            "TotalRecordCount": _PAGE_SIZE * 2 + 50,  # e.g. 250 when _PAGE_SIZE == 100
        }

    # The tests below call *async_browse_media* which performs a session
    # lookup when *UserId* is not embedded in the device object.  Exposing a
    # no-op method satisfies that branch without extensive mocking.
    async def get_sessions(self, *, force_refresh: bool = False):  # noqa: D401, ANN001 – unused
        return []


# ---------------------------------------------------------------------------
# Fixture – returns a fully wired *EmbyDevice*
# ---------------------------------------------------------------------------


@pytest.fixture()
def emby_device(monkeypatch):  # noqa: D401 – naming consistent with suite
    """Return an *EmbyDevice* instance backed by *_DirAPI*."""

    from custom_components.embymedia.media_player import EmbyDevice

    dev = EmbyDevice.__new__(EmbyDevice)  # type: ignore[arg-type]

    # Fake pyemby device – only the attributes required by browse logic.
    fake_device = SimpleNamespace(
        supports_remote_control=True,
        name="Living Room TV",
        state="Idle",
        username="alice",
        session_id="sess-abc",
        unique_id="dev-42",
        session_raw={"UserId": "user-42"},
    )

    dev.device = fake_device
    dev.device_id = "dev-42"
    dev.emby = SimpleNamespace(_host="h", _api_key="k", _port=8096, _ssl=False)
    dev.hass = None  # pyright: ignore[reportAttributeAccessIssue]
    dev._current_session_id = None  # pylint: disable=protected-access

    # Replace API accessor with our stub implementation.
    stub_api = _DirAPI()
    monkeypatch.setattr(dev, "_get_emby_api", lambda _self=dev: stub_api)  # type: ignore[arg-type]

    # Silence Home Assistant specific side-effects during unit tests.
    dev.async_write_ha_state = lambda *_, **__: None  # type: ignore[assignment]

    return dev


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_directory_first_page_has_next(emby_device):  # noqa: D401
    """Page *0* should expose a trailing *Next →* node only."""

    root_uri = "emby://dir-123"
    node = await emby_device.async_browse_media(media_content_id=root_uri)  # type: ignore[arg-type]

    titles = [child.title for child in node.children]

    # No *Prev* on the first slice; *Next* must be present.
    assert titles[0] != "← Prev" and titles[-1] == "Next →"

    # Clicking the *Next* tile should carry the correct query parameter.
    next_uri = node.children[-1].media_content_id  # type: ignore[arg-type]
    assert next_uri.endswith("start=" + str(_PAGE_SIZE))


@pytest.mark.asyncio
async def test_directory_middle_page_has_prev_and_next(emby_device):  # noqa: D401
    """Intermediate slices must prepend *Prev* and append *Next*."""

    # Manually request the second slice (start=100).
    second_uri = f"emby://dir-123?start={_PAGE_SIZE}"
    node = await emby_device.async_browse_media(media_content_id=second_uri)  # type: ignore[arg-type]

    titles = [child.title for child in node.children]

    assert titles[0] == "← Prev" and titles[-1] == "Next →"

    # Verify query parameters advance/rewind correctly.
    prev_uri = node.children[0].media_content_id  # type: ignore[arg-type]
    next_uri = node.children[-1].media_content_id  # type: ignore[arg-type]

    assert prev_uri.endswith("start=0")
    assert next_uri.endswith("start=" + str(_PAGE_SIZE * 2))


@pytest.mark.asyncio
async def test_directory_last_page_has_prev_only(emby_device):  # noqa: D401
    """The final slice should only include a *Prev* tile."""

    last_uri = f"emby://dir-123?start={_PAGE_SIZE * 2}"
    node = await emby_device.async_browse_media(media_content_id=last_uri)  # type: ignore[arg-type]

    titles = [child.title for child in node.children]

    assert titles[0] == "← Prev" and "Next →" not in titles
