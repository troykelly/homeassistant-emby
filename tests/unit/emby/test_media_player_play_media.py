"""Extensive tests for :pyfunc:`components.emby.media_player.EmbyDevice.async_play_media`."""

from __future__ import annotations

from types import SimpleNamespace

import asyncio
from typing import List

import pytest


# ---------------------------------------------------------------------------
# Helper stubs
# ---------------------------------------------------------------------------


class _StubAPI:  # pylint: disable=too-few-public-methods
    """Fake replacement for :class:`components.emby.api.EmbyAPI`."""

    def __init__(self) -> None:
        self.play_calls: List[dict] = []

    async def play(self, session_id, item_ids, *, play_command="PlayNow", start_position_ticks=None):  # noqa: D401
        self.play_calls.append(
            {
                "session_id": session_id,
                "item_ids": item_ids,
                "play_command": play_command,
                "start_position_ticks": start_position_ticks,
            }
        )


class _Device(SimpleNamespace):
    """Replica of the light attribute-container used by *EmbyDevice*."""

    def __init__(self):  # noqa: D401
        super().__init__(
            supports_remote_control=True,
            name="Living Room",
            state="Playing",
            username="john",
            media_id="m1",
            media_type="Movie",
            media_runtime=3600,
            media_position=120,
            is_nowplaying=True,
            media_image_url="http://img",
            media_title="The Matrix",
            media_season=2,
            media_series_title="Matrix Series",
            media_episode=5,
            media_album_name="Album",
            media_artist="Artist",
            media_album_artist="AlbumArtist",
            session_id="sess-initial",
            unique_id="dev1",
        )

        # Track whether "play/pause/..." helpers are invoked by wrappers.
        self._played = False

    # Helper methods invoked by EmbyDevice’s wrappers ----------------------
    async def media_play(self):  # noqa: D401
        self._played = True

    async def media_pause(self):  # noqa: D401
        self._paused = True  # type: ignore[attr-defined]

    async def media_stop(self):  # noqa: D401
        self._stopped = True  # type: ignore[attr-defined]

    async def media_next(self):  # noqa: D401
        self._next = True  # type: ignore[attr-defined]

    async def media_previous(self):  # noqa: D401
        self._previous = True  # type: ignore[attr-defined]

    async def media_seek(self, position):  # noqa: D401
        self._seek = position  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Fixture returning an *EmbyDevice* instance wired with stubs
# ---------------------------------------------------------------------------


@pytest.fixture()
def emby_device(monkeypatch):  # noqa: D401 – pytest naming convention
    """Return an *EmbyDevice* wired with fake dependencies suitable for unit-tests."""

    from components.emby.media_player import EmbyDevice

    dev = EmbyDevice.__new__(EmbyDevice)  # type: ignore[arg-type]

    # Minimal attributes expected by the class ---------------------------
    stub_device = _Device()
    dev.device = stub_device
    dev.device_id = "dev1"
    dev.emby = SimpleNamespace(_host="h", _api_key="k", _port=8096, _ssl=False)
    dev.hass = None  # hass not required for these unit-tests
    dev._current_session_id = None  # pylint: disable=protected-access

    # Home Assistant's Entity base-class expects a *hass* instance when state
    # updates are written.  We monkey-patch the *async_write_ha_state* helper
    # so the unit-test can run in isolation without spinning up a full HA core.
    dev.async_write_ha_state = lambda *_, **__: None  # type: ignore[assignment]

    # Patch helpers ------------------------------------------------------
    api = _StubAPI()
    monkeypatch.setattr(dev, "_get_emby_api", lambda self=dev: api)  # type: ignore[arg-type]
    async def _fixed_session(*_, **__):  # noqa: D401
        return "sess-123"

    monkeypatch.setattr(dev, "_resolve_session_id", _fixed_session)  # success path by default

    # Patch resolver – always return a dummy item.
    import components.emby.search_resolver as resolver_mod

    async def _fake_resolver(*_, **__):  # noqa: D401
        return {"Id": "item-1"}

    monkeypatch.setattr(resolver_mod, "resolve_media_item", _fake_resolver)

    return dev


# ---------------------------------------------------------------------------
# Tests – success path & various failure modes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_play_media_success(emby_device):
    """Happy-path – ensure *play()* is called with correct parameters and state updated."""

    await emby_device.async_play_media(media_type="movie", media_id="The Matrix")

    stub_api: _StubAPI = emby_device._get_emby_api()  # type: ignore[attr-defined]

    # One play call recorded with correct arguments.
    assert len(stub_api.play_calls) == 1
    play_kwargs = stub_api.play_calls[0]
    assert play_kwargs["session_id"] == "sess-123"
    assert play_kwargs["item_ids"] == ["item-1"]
    assert play_kwargs["play_command"] == "PlayNow"
    assert play_kwargs["start_position_ticks"] is None

    # `_current_session_id` must be persisted for next invocation.
    assert emby_device.get_current_session_id() == "sess-123"


@pytest.mark.asyncio
async def test_async_play_media_enqueue_with_position(monkeypatch, emby_device):
    """Verify optional arguments *enqueue* and *position* are propagated."""

    await emby_device.async_play_media("movie", "MovieX", enqueue=True, position=5)

    stub_api: _StubAPI = emby_device._get_emby_api()  # type: ignore[attr-defined]
    call = stub_api.play_calls[-1]
    assert call["play_command"] == "PlayNext"  # enqueue flag handled
    assert call["start_position_ticks"] == 5 * 10_000_000


@pytest.mark.asyncio
async def test_async_play_media_lookup_failure(monkeypatch, emby_device):
    """A *MediaLookupError* must be surfaced as *HomeAssistantError*."""

    from components.emby.search_resolver import MediaLookupError
    from homeassistant.exceptions import HomeAssistantError

    import components.emby.search_resolver as resolver_mod
    monkeypatch.setattr(resolver_mod, "resolve_media_item", lambda *_, **__: (_ for _ in ()).throw(MediaLookupError("fail")))

    with pytest.raises(HomeAssistantError):
        await emby_device.async_play_media("movie", "bad")


@pytest.mark.asyncio
async def test_async_play_media_session_failure(monkeypatch, emby_device):
    """Missing session id must raise *HomeAssistantError*."""

    from homeassistant.exceptions import HomeAssistantError

    async def _no_session(*_, **__):  # noqa: D401
        return None

    monkeypatch.setattr(emby_device, "_resolve_session_id", _no_session)

    with pytest.raises(HomeAssistantError):
        await emby_device.async_play_media("movie", "x")


@pytest.mark.asyncio
async def test_async_play_media_play_error(monkeypatch, emby_device):
    """Errors from `api.play` get wrapped into *HomeAssistantError*."""

    from homeassistant.exceptions import HomeAssistantError

    # Replace api.play with implementation that raises.
    api = emby_device._get_emby_api()  # type: ignore[attr-defined]

    async def _boom(*_, **__):  # noqa: D401 – helper
        raise RuntimeError("boom")

    monkeypatch.setattr(api, "play", _boom)

    with pytest.raises(HomeAssistantError):
        await emby_device.async_play_media("movie", "x")


# ---------------------------------------------------------------------------
# Tests – property wrappers & supported feature flags
# ---------------------------------------------------------------------------


def test_media_player_properties(monkeypatch):
    """Exercise the various *EmbyDevice* properties that map to *device*."""

    from components.emby.media_player import EmbyDevice, SUPPORT_EMBY, MediaPlayerEntityFeature, MediaType

    dev = EmbyDevice.__new__(EmbyDevice)  # type: ignore[arg-type]
    stub = _Device()
    dev.device = stub
    dev.device_id = "dev1"
    dev._current_session_id = stub.session_id  # pylint: disable=protected-access

    # Basic attribute pass-throughs
    assert dev.supports_remote_control is True
    assert dev.supported_features == SUPPORT_EMBY
    assert dev.name == "Emby Living Room"

    # State mapping
    assert dev.state.name == "PLAYING"

    # Media type translation
    mapping = {
        "Episode": MediaType.TVSHOW,
        "Movie": MediaType.MOVIE,
        "Trailer": "trailer",
        "Music": MediaType.MUSIC,
        "Video": MediaType.VIDEO,
        "Audio": MediaType.MUSIC,
        "TvChannel": MediaType.CHANNEL,
    }

    for raw, expected in mapping.items():
        stub.media_type = raw
        assert dev.media_content_type == expected

    # Position helpers
    stub.media_position = 130
    dev.media_status_last_position = 130
    dev.media_status_received = None
    assert dev.media_position == 130

    # Extra state attrs
    assert dev.extra_state_attributes == {"emby_session_id": stub.session_id}

    # Verify wrapper methods call underlying stubs (e.g. play/pause)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(dev.async_media_play())
    assert stub._played is True

    # Exercise remaining simple pass-through properties for coverage.
    _ = (
        dev.media_duration,
        dev.media_image_url,
        dev.media_title,
        dev.media_season,
        dev.media_series_title,
        dev.media_episode,
        dev.media_album_name,
        dev.media_artist,
        dev.media_album_artist,
    )
