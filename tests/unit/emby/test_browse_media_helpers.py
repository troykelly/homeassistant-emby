"""Unit-tests for the *private* browse-media helper functions.

The Emby *media_player* implementation exposes a rich set of helper methods
used by :pyfunc:`EmbyDevice.async_browse_media`.

While the public browse API itself is covered by integration tests, the
internal building blocks had no dedicated unit-tests yet.  Exercising them in
isolation gives us deterministic coverage without having to stub the entire
Emby REST surface.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest


# ---------------------------------------------------------------------------
# Bare-bones *EmbyDevice* fixture wired with minimal dependencies
# ---------------------------------------------------------------------------


@pytest.fixture()
def emby_device(monkeypatch):  # noqa: D401 – reuse naming convention of other tests
    """Return an ``EmbyDevice`` instance with helper stubs attached."""

    from custom_components.embymedia.media_player import EmbyDevice

    dev = EmbyDevice.__new__(EmbyDevice)  # type: ignore[arg-type]

    # ``_parse_emby_uri`` and friends do **not** access *self.device* but the
    # thumbnail builder needs a working *EmbyAPI* instance.  We therefore
    # provide a trivial stub exposing the single *private* attribute used in
    # the URL construction.
    class _StubAPI:  # pylint: disable=too-few-public-methods
        def __init__(self) -> None:  # noqa: D401
            self._base = "https://emby.example.com"  # pylint: disable=invalid-name

    # Patch the protected helper so the unit-tests remain self-contained.
    monkeypatch.setattr(dev, "_get_emby_api", lambda _self=dev: _StubAPI())  # type: ignore[arg-type]

    # ``async_write_ha_state`` is invoked by some helpers – replace with no-op.
    dev.async_write_ha_state = lambda *_, **__: None  # type: ignore[assignment]

    return dev


# ---------------------------------------------------------------------------
# _parse_emby_uri
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "uri, expected_id, expected_start",
    [
        ("emby://123", "123", 0),
        ("emby://movieId?start=200", "movieId", 200),
        ("emby:///folder", "folder", 0),  # path variant without netloc
    ],
)
def test_parse_emby_uri_valid(emby_device, uri, expected_id, expected_start):  # noqa: D401
    """Valid ``emby://`` URIs must be parsed into ``(item_id, start)``."""

    item_id, start_idx = emby_device._parse_emby_uri(uri)  # type: ignore[attr-defined]
    assert (item_id, start_idx) == (expected_id, expected_start)


@pytest.mark.parametrize("uri", ["http://foo", "media-source://bar", "emby://"])
def test_parse_emby_uri_invalid(emby_device, uri):  # noqa: D401
    """Non-Emby or malformed URIs must raise *HomeAssistantError*."""

    from homeassistant.exceptions import HomeAssistantError

    with pytest.raises(HomeAssistantError):
        emby_device._parse_emby_uri(uri)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# _map_item_type – verify selected mappings instead of duplicating the table
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "item_type, expected_play, expected_expand",
    [
        ("Movie", True, False),
        ("Series", False, True),
        ("Folder", False, True),  # default mapping
    ],
)
def test_map_item_type_basic(emby_device, item_type, expected_play, expected_expand):  # noqa: D401
    from homeassistant.components.media_player.const import MediaClass

    media_class, _content_type, can_play, can_expand = emby_device._map_item_type(  # type: ignore[attr-defined]
        {"Type": item_type}
    )

    # Simple sanity checks – focus on *play* / *expand* capabilities which drive UI decisions.
    assert can_play is expected_play
    assert can_expand is expected_expand
    # Defensive: returned *media_class* must be a valid enum member
    assert isinstance(media_class, MediaClass)


def test_map_item_type_unknown_defaults_to_directory(emby_device):  # noqa: D401
    from homeassistant.components.media_player.const import MediaClass

    media_class, content_type, can_play, can_expand = emby_device._map_item_type(  # type: ignore[attr-defined]
        {"Type": "CompletelyUnknown"}
    )

    assert media_class is MediaClass.DIRECTORY and content_type == "directory"
    assert can_play is False and can_expand is True


# ---------------------------------------------------------------------------
# Thumbnail builder – primary path & fallback
# ---------------------------------------------------------------------------


def test_build_thumbnail_url_primary_tag(emby_device):  # noqa: D401
    """Primary image tag must be embedded into the constructed URL."""

    item = {"Id": "789", "ImageTags": {"Primary": "pTag"}}

    url = emby_device._build_thumbnail_url(item)  # type: ignore[attr-defined]

    # Basic structure validation – cover host, path & query string.
    assert url == "https://emby.example.com/Items/789/Images/Primary?tag=pTag&maxWidth=500"


def test_build_thumbnail_url_no_image_returns_none(emby_device):  # noqa: D401
    item = {"Id": "noimg"}
    assert emby_device._build_thumbnail_url(item) is None  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Pagination helper – ensure query string encoded correctly
# ---------------------------------------------------------------------------


def test_make_pagination_node(emby_device):  # noqa: D401
    node = emby_device._make_pagination_node("Next →", "abc", 300)  # type: ignore[attr-defined]

    assert node.title == "Next →"
    assert node.media_content_id == "emby://abc?start=300"
    assert node.can_expand is True and node.can_play is False


# ---------------------------------------------------------------------------
# _emby_item_to_browse & _emby_view_to_browse – smoke tests
# ---------------------------------------------------------------------------


def test_emby_item_to_browse_movie(emby_device):  # noqa: D401
    item = {
        "Id": "456",
        "Name": "Test Movie",
        "Type": "Movie",
        "ImageTags": {"Primary": "img"},
    }

    node = emby_device._emby_item_to_browse(item)  # type: ignore[attr-defined]

    from homeassistant.components.media_player.const import MediaClass

    assert node.title == "Test Movie"
    assert node.media_content_id == "emby://456"
    assert node.media_class is MediaClass.MOVIE
    assert node.can_play is True and node.can_expand is False
    assert node.thumbnail is not None


def test_emby_view_to_browse_movies_collection(emby_device):  # noqa: D401
    view = {
        "Id": "v1",
        "Name": "Movies",
        "CollectionType": "movies",
        "ImageTags": {},
    }

    node = emby_device._emby_view_to_browse(view)  # type: ignore[attr-defined]

    assert node.title == "Movies"
    assert node.media_content_type == "movies"
    assert node.can_expand is True and node.can_play is False
