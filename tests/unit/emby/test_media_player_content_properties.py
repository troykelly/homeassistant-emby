"""Unit tests for the media content *@property* helpers on :class:`EmbyDevice`.

These simple accessors constitute a sizable chunk of lines that were not
executed by previous tests yet are nonetheless important public API surface.
The test creates a minimal *device* stub containing every attribute referenced
by the properties and verifies correct passthrough / mapping behaviour.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest


@pytest.fixture()
def emby_device():  # noqa: D401 – matches fixture naming convention across suite
    """Return an *EmbyDevice* instance wired with a fully-featured stub device."""

    from custom_components.embymedia.media_player import EmbyDevice

    dev = EmbyDevice.__new__(EmbyDevice)  # type: ignore[arg-type]

    # Construct a stub *pyemby* device holding all attributes accessed by the
    # properties under test.
    stub = SimpleNamespace(
        username="john",
        media_id="movie-1",
        media_type="Movie",
        media_runtime=7200,
        media_position=None,
        is_nowplaying=False,
        media_image_url="https://img",
        media_title="The Matrix",
        media_season="1",
        media_series_title="The Matrix Series",
        media_episode="1",
        media_album_name="OST",
        media_artist="Artist",
        media_album_artist="Album Artist",
    )

    dev.device = stub

    # Fallback attributes used by some helpers
    dev.media_status_last_position = 0
    dev.media_status_received = None

    # Provide no-op for HA state writes so the instance can run outside HA.
    dev.async_write_ha_state = lambda *_, **__: None  # type: ignore[assignment]

    return dev


# ---------------------------------------------------------------------------
# Individual property checks
# ---------------------------------------------------------------------------


def test_app_name_passthrough(emby_device):  # noqa: D401
    assert emby_device.app_name == "john"


def test_media_content_id_passthrough(emby_device):  # noqa: D401
    assert emby_device.media_content_id == "movie-1"


@pytest.mark.parametrize(
    "media_type, expected",
    [
        ("Episode", "tvshow"),
        ("Movie", "movie"),
        ("Trailer", "trailer"),
        ("Music", "music"),
        ("Video", "video"),
        ("Audio", "music"),
        ("TvChannel", "channel"),
        ("Recording", "video"),
        ("RecordingSeries", "directory"),
        ("BoxSet", "directory"),
        ("Unknown", None),
    ],
)
def test_media_content_type_mapping(emby_device, media_type, expected):  # noqa: D401
    emby_device.device.media_type = media_type

    from homeassistant.components.media_player.const import MediaType

    result = emby_device.media_content_type

    if expected is None:
        assert result is None
    elif isinstance(expected, str):
        # Map expected string to the enum where applicable
        assert result == getattr(MediaType, expected.upper(), expected)


def test_misc_content_properties_passthrough(emby_device):  # noqa: D401
    assert emby_device.media_duration == 7200
    assert emby_device.media_image_url == "https://img"
    assert emby_device.media_title == "The Matrix"
    assert emby_device.media_season == "1"
    assert emby_device.media_series_title == "The Matrix Series"
    assert emby_device.media_episode == "1"
    assert emby_device.media_album_name == "OST"
    assert emby_device.media_artist == "Artist"
    assert emby_device.media_album_artist == "Album Artist"
