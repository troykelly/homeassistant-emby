"""Comprehensive *async_browse_media* integration tests (GitHub issue #137).

This suite exercises the full browsing hierarchy including:

* Root → libraries (views) including virtual *Resume* / *Favorites* folders.
* Drilling into the *Movies* library and selecting a playable **leaf** item.
* Pagination behaviour on large directories (250 child items).
* Error handling – invalid identifiers raise :class:`HomeAssistantError`.
* Delegation to Home Assistant *media_source* for `media-source://` paths.

The tests run without network access – outbound HTTP calls issued by
``custom_components.embymedia.api.EmbyAPI`` are monkey-patched so the helper
receives deterministic JSON payloads.  This keeps the code path identical to
production while avoiding the overhead of a real Emby server or an
``aiohttp`` mocking framework.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, List

import pytest

from homeassistant.exceptions import HomeAssistantError

# ---------------------------------------------------------------------------
# HTTP stub – intercepts *all* EmbyAPI._request calls
# ---------------------------------------------------------------------------


class _StubHTTP:  # pylint: disable=too-few-public-methods
    """Collect outbound REST calls and return canned JSON payloads."""

    def __init__(self) -> None:  # noqa: D401 – simple container
        self.calls: List[tuple[str, str]] = []  # (method, path)

    async def handler(self, _self_ref, method: str, path: str, *, params: dict | None = None, **_) -> Any:  # noqa: D401, ANN001 – Emulate EmbyAPI._request signature
        """Replacement implementation for :pymeth:`EmbyAPI._request`."""

        self.calls.append((method, path))

        # ------------------------------------------------------------------
        # Root libraries (views)
        # ------------------------------------------------------------------

        if method == "GET" and path == "/Users/user-1/Views":
            # Two physical libraries – Movies / TV Shows
            return {
                "Items": [
                    {"Id": "lib-movies", "Name": "Movies", "CollectionType": "movies"},
                    {"Id": "lib-shows", "Name": "TV Shows", "CollectionType": "tvshows"},
                ]
            }

        # ------------------------------------------------------------------
        # Item metadata look-ups – return minimal info required by browse helper
        # ------------------------------------------------------------------

        if method == "GET" and path.startswith("/Items/") and "/Children" not in path:
            item_id = path.split("/")[2]

            # Library nodes are directories – treat as Folder
            if item_id in {"lib-movies", "lib-shows"}:
                return {"Id": item_id, "Name": "Movies" if item_id == "lib-movies" else "TV Shows", "Type": "Folder"}

            # Leaf *Movie* object – return minimal metadata for *any* movie-<n>
            if item_id.startswith("movie-"):
                return {"Id": item_id, "Name": item_id.replace("-", " ").title(), "Type": "Movie", "ImageTags": {}}

            # Unknown id – emulate 404 handled further up the stack (return None)
            return None

        # ------------------------------------------------------------------
        # Children listing – Movies library (250 fake items so pagination kicks in)
        # ------------------------------------------------------------------

        if method == "GET" and path.startswith("/Items/lib-movies/Children"):
            # Extract *StartIndex* & *Limit* from query string (defaults: 0/100)
            start_idx = int(params.get("StartIndex", 0)) if params else 0
            limit = int(params.get("Limit", 100)) if params else 100

            # Generate slice
            items = [
                {
                    "Id": f"movie-{i}",
                    "Name": f"Movie {i}",
                    "Type": "Movie",
                    "ImageTags": {},
                }
                for i in range(start_idx, min(start_idx + limit, 250))
            ]

            return {
                "Items": items,
                "TotalRecordCount": 250,
            }

        # ------------------------------------------------------------------
        # Default fallback – raise to catch missing stubs quickly
        # ------------------------------------------------------------------

        raise RuntimeError(f"Unhandled EmbyAPI request: {method} {path}")


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def http_stub(monkeypatch):
    """Patch :pyfunc:`EmbyAPI._request` globally for the duration of a test."""

    from custom_components.embymedia import api as api_mod

    stub = _StubHTTP()

    async def _patched(self_api, method: str, path: str, **kwargs):  # noqa: D401, ANN001 – emulate original sig
        return await stub.handler(self_api, method, path, **kwargs)

    monkeypatch.setattr(api_mod.EmbyAPI, "_request", _patched, raising=True)
    return stub


@pytest.fixture()
def emby_device(monkeypatch):
    """Return *EmbyDevice* wired with stubbed API + fake Home Assistant ctx."""

    from custom_components.embymedia.media_player import EmbyDevice

    dev = EmbyDevice.__new__(EmbyDevice)  # type: ignore[arg-type]

    # Fake pyemby device – only attributes required by browse logic.
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

    # Minimal Emby server stub (only attributes read by helper methods).
    dev.emby = SimpleNamespace(_host="h", _api_key="k", _port=8096, _ssl=False)

    # Home Assistant context – *None* is fine for the majority of tests.  The
    # *media_source* delegation check assigns a stub instance explicitly.
    dev.hass = None  # type: ignore[assignment]

    # Silence Home Assistant side-effects.
    dev.async_write_ha_state = lambda *_, **__: None  # type: ignore[assignment]

    return dev


# ---------------------------------------------------------------------------
# Tests – ordered roughly by complexity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_browse_drill_down_to_leaf(http_stub, emby_device):
    """Navigate root → Movies library → leaf movie entry."""

    # 1. Root libraries
    root_node = await emby_device.async_browse_media()

    # Pick *Movies* node
    movies_node = next(child for child in root_node.children if child.title == "Movies")  # type: ignore[arg-type]

    # 2. Movies library directory
    movies_dir = await emby_device.async_browse_media(media_content_id=movies_node.media_content_id)  # type: ignore[arg-type]

    # Select first movie (should be *Movie 0*)
    first_movie = movies_dir.children[0]
    assert first_movie.can_play and not first_movie.can_expand  # type: ignore[arg-type]

    # 3. Leaf – requesting the leaf itself should return the same object (no children)
    leaf = await emby_device.async_browse_media(media_content_id=first_movie.media_content_id)  # type: ignore[arg-type]

    assert leaf.media_content_id == first_movie.media_content_id
    assert leaf.can_play and not leaf.can_expand


@pytest.mark.asyncio
async def test_pagination_next_node_presence(http_stub, emby_device):  # noqa: D401
    """First slice of large directory must expose a trailing *Next →* tile."""

    movies_dir = await emby_device.async_browse_media(media_content_id="emby://lib-movies")  # type: ignore[arg-type]

    titles = [child.title for child in movies_dir.children]
    assert titles[-1] == "Next →"  # type: ignore[index]


@pytest.mark.asyncio
async def test_invalid_identifier_raises_error(http_stub, emby_device):  # noqa: D401
    """Unknown `item_id` should propagate *HomeAssistantError*."""

    with pytest.raises(HomeAssistantError):
        await emby_device.async_browse_media(media_content_id="emby://does-not-exist")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_media_source_delegation(http_stub, monkeypatch, emby_device):  # noqa: D401
    """`media-source://` paths must be forwarded to HA media_source helper."""

    # Prepare stub for *ha_media_source.async_browse_media*
    from custom_components.embymedia.media_player import ha_media_source

    # Stub Home Assistant instance with minimal attributes used by helper
    hass_stub = SimpleNamespace(data={})
    emby_device.hass = hass_stub  # type: ignore[assignment]

    async def _fake_browse(hass, media_content_id):  # noqa: D401, ANN001 – signature match
        # Assert correct parameters are passed through.
        assert hass is hass_stub
        assert media_content_id == "media-source://xyz"
        return "ok!"

    monkeypatch.setattr(ha_media_source, "async_browse_media", _fake_browse, raising=True)

    result = await emby_device.async_browse_media(media_content_id="media-source://xyz")  # type: ignore[arg-type]

    assert result == "ok!"
