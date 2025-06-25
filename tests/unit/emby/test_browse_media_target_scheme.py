"""Tests covering *device-less* playback browse behaviour (GitHub issue #221).

The Emby integration must expose ``media-source://emby/<ItemId>`` identifiers
for **leaf** nodes whenever the user intends to play the media on a target
that is *not* an Emby client (Chromecast, Sonos, etc.).

This module verifies that:

1. The private helper :pyfunc:`EmbyDevice._is_emby_client` correctly detects
   Emby vs. non-Emby entity_ids.
2. ``_emby_item_to_browse`` swaps the URI scheme to *media-source* when the
   flag set by :pyfunc:`EmbyDevice.async_browse_media` is active.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest


# ---------------------------------------------------------------------------
# Fixture – minimal EmbyDevice instance
# ---------------------------------------------------------------------------


@pytest.fixture()
def emby_device(monkeypatch):  # noqa: D401 – naming aligned with existing suite
    """Return a bare-bones *EmbyDevice* with stubs for external deps."""

    from custom_components.embymedia.media_player import EmbyDevice

    dev = EmbyDevice.__new__(EmbyDevice)  # type: ignore[arg-type]

    # Inject trivial *EmbyAPI* stub (only *thumbnail* helper relies on it).
    class _StubAPI:  # pylint: disable=too-few-public-methods
        def __init__(self) -> None:  # noqa: D401
            self._base = "https://emby.test"  # pylint: disable=invalid-name

    monkeypatch.setattr(dev, "_get_emby_api", lambda: _StubAPI())

    dev.async_write_ha_state = lambda *_, **__: None  # type: ignore[assignment]

    return dev


# ---------------------------------------------------------------------------
# _is_emby_client
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "entity_id, expected",
    [
        (None, True),
        ("media_player.emby_living_room", True),
        ("media_player.sonos_kitchen", False),
        ("light.kitchen", False),  # wrong domain
        ("malformed_id", False),  # missing domain separator
    ],
)
def test_is_emby_client_detection(emby_device, entity_id, expected):  # noqa: D401
    """Entity id prefix detection must match the mapping table."""

    assert emby_device._is_emby_client(entity_id) is expected  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Leaf node URI scheme swap when *media-source* required
# ---------------------------------------------------------------------------


def test_leaf_scheme_media_source_swapped(emby_device):  # noqa: D401
    """Leaf nodes must use *media-source* URI when the flag is set."""

    # Activate *media-source* mode exactly how async_browse_media does it.
    setattr(emby_device, "_browse_use_media_source", True)

    movie_item = {
        "Id": "m1",
        "Name": "Demo Movie",
        "Type": "Movie",
    }

    node = emby_device._emby_item_to_browse(movie_item)  # type: ignore[attr-defined]

    assert node.media_content_id == "media-source://emby/m1"

    # Directories must *not* change their scheme – ensures navigation keeps
    # flowing through the Emby specific browse handler.
    season_item = {
        "Id": "s1",
        "Name": "Season 1",
        "Type": "Season",
    }

    season_node = emby_device._emby_item_to_browse(season_item)  # type: ignore[attr-defined]

    assert season_node.media_content_id == "emby://s1"
