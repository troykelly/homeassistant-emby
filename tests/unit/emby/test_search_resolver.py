"""Unit tests for *components.emby.search_resolver* utilities."""

from __future__ import annotations

import pytest

from custom_components.embymedia.search_resolver import (
    MediaLookupError,
    _looks_like_item_id,
    resolve_media_item,
)


# ---------------------------------------------------------------------------
# Tests – _looks_like_item_id heuristic
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        ("1234", False),  # too short numeric
        ("abcdef12", True),  # 8-char hex -> accepted
        ("550e8400-e29b-41d4-a716-446655440000", True),  # canonical uuid
        ("1917", False),  # numeric movie title – should *not* match
        ("S02E05", False),  # looks like episode notation, not id
    ],
)
def test_looks_like_item_id(value: str, expected: bool) -> None:
    """Verify the simple heuristic used to detect raw Emby ItemIds."""

    assert _looks_like_item_id(value) is expected


# ---------------------------------------------------------------------------
# Tests – resolve_media_item
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_with_direct_item_id(fake_emby_api):  # noqa: D401 – pytest naming convention
    """When the caller supplies a raw ItemId the resolver must shortcut."""

    # Arrange – fake API returns the object directly, no search required.
    fake_emby_api._item_response = {"Id": "abcdef12", "Name": "Dummy Movie"}

    # Act
    item = await resolve_media_item(
        fake_emby_api,
        media_type="movie",
        media_id="abcdef12",  # 8-char hex passes the heuristic
    )

    # Assert
    assert item["Id"] == "abcdef12"
    # The stub must have recorded exactly one *get_item* invocation and **no** search.
    assert fake_emby_api._get_item_calls == ["abcdef12"]
    assert fake_emby_api._search_calls == []


@pytest.mark.asyncio
async def test_resolve_via_search(fake_emby_api):  # noqa: D401 – pytest naming
    """The common path – find the first match returned by /Items."""

    fake_emby_api._item_response = None  # ensure direct id fallback fails
    fake_emby_api._search_response = [
        {"Id": "item1", "Name": "The Matrix"},
        {"Id": "item2", "Name": "Other"},
    ]

    item = await resolve_media_item(
        fake_emby_api,
        media_type="movie",
        media_id="The Matrix",
    )

    assert item["Name"] == "The Matrix"
    # Verify that search filter included the mapped Emby item-type "Movie".
    assert fake_emby_api._search_calls[0]["item_types"] == ["Movie"]


@pytest.mark.asyncio
async def test_resolve_no_results(fake_emby_api):
    """When the API returns no matches an explicit error must be raised."""

    fake_emby_api._item_response = None
    fake_emby_api._search_response = []

    with pytest.raises(MediaLookupError):
        await resolve_media_item(
            fake_emby_api,
            media_type="movie",
            media_id="Unknown title",
        )


@pytest.mark.asyncio
async def test_resolve_api_error(fake_emby_api):
    """HTTP-layer failures are surfaced as *MediaLookupError*."""

    from custom_components.embymedia.api import EmbyApiError

    fake_emby_api._item_response = None
    fake_emby_api._search_response = EmbyApiError("boom")

    with pytest.raises(MediaLookupError):
        await resolve_media_item(fake_emby_api, media_type="movie", media_id="x")


# ---------------------------------------------------------------------------
# New regression – GitHub issue #202 (Live TV channel playback)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_channel_raw_id_shortcuts(fake_emby_api):  # noqa: D401 – naming
    """Raw *TvChannel* ids must bypass the `/Items/{id}` lookup (#202)."""

    # Arrange – provoke the fallback path by returning *None* for get_item.
    fake_emby_api._item_response = None

    # Use an 8-digit numeric id which passes the *looks like id* heuristic.
    channel_id = "10665430"

    item = await resolve_media_item(
        fake_emby_api,
        media_type="channel",
        media_id=channel_id,
    )

    # Resolver must *not* attempt a full-text search when the id can be used
    # as-is for playback.
    assert fake_emby_api._search_calls == []

    # The returned mapping must preserve the identifier and mark the object
    # as *TvChannel* so higher layers can set the correct *media_class*.
    assert item == {"Id": channel_id, "Type": "TvChannel"}


@pytest.mark.asyncio
async def test_resolve_channel_emby_uri(fake_emby_api):  # noqa: D401
    """`emby://<id>` URIs must resolve to direct channel items."""

    fake_emby_api._item_response = None

    channel_id = "1066543"  # 7-digit typical Emby channel id
    item = await resolve_media_item(
        fake_emby_api,
        media_type="channel",
        media_id=f"emby://{channel_id}",
    )

    assert item == {"Id": channel_id, "Type": "TvChannel"}
    # No search/api get_item attempted beyond the shortcut heuristics.
    assert fake_emby_api._search_calls == []


# ---------------------------------------------------------------------------
# Fixtures used within this module only
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_emby_api():  # noqa: D401 – pytest naming
    """Return a fresh stub matching EmbyAPI's public surface."""

    from tests.conftest import FakeEmbyAPI

    return FakeEmbyAPI()
