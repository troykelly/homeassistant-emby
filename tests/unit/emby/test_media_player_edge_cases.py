"""Edge-case and error-path tests for :class:`EmbyDevice` browse & state logic."""

from __future__ import annotations

from types import SimpleNamespace

import pytest


# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def emby_device(monkeypatch):  # noqa: D401
    """Return a fully constructed *EmbyDevice* executing the real ``__init__``."""

    from custom_components.embymedia.media_player import EmbyDevice

    # Stub *EmbyServer*
    class _StubServer:  # pylint: disable=too-few-public-methods
        def __init__(self):  # noqa: D401
            self.devices = {}

        # The constructor registers an update callback – store it for later.
        def add_update_callback(self, cb, _dev_id):  # noqa: D401
            self._cb = cb

    stub_server = _StubServer()

    # Build a minimal *pyemby* device object with all attributes referenced in
    # the constructor and later properties.
    device_id = "dev-1"
    stub_device = SimpleNamespace(
        name="Living Room",
        supports_remote_control=True,
        session_id="sess-1",
        state="Idle",
        media_position=10,
        is_nowplaying=True,
        session_raw={},
    )

    stub_server.devices[device_id] = stub_device

    dev = EmbyDevice(stub_server, device_id)

    # Provide dummy *hass* & async_write_ha_state so the entity can operate.
    dev.hass = SimpleNamespace(bus=None)  # type: ignore[attr-defined]
    dev.async_write_ha_state = lambda *_, **__: None  # type: ignore[assignment]

    # Patch *_get_emby_api* so browse tests remain hermetic.
    fake_api = SimpleNamespace(
        get_sessions=lambda *_, **__: [
            {"DeviceId": device_id, "UserId": "user-x"}
        ],
    )

    monkeypatch.setattr(dev, "_get_emby_api", lambda _self=dev: fake_api)  # type: ignore[arg-type]

    return dev, stub_server, stub_device


# ---------------------------------------------------------------------------
# State mapping – ensures PAUSED/PLAYING/IDLE/OFF branches are executed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw_state, expected", [
    ("Paused", "paused"),
    ("Playing", "playing"),
    ("Idle", "idle"),
    ("Off", "off"),
])
def test_state_mapping(emby_device, raw_state, expected):  # noqa: D401
    dev, _svr, stub = emby_device
    stub.state = raw_state

    from homeassistant.components.media_player.const import MediaPlayerState

    enum_val = getattr(MediaPlayerState, expected.upper())
    assert dev.state == enum_val


# ---------------------------------------------------------------------------
# *async_update_callback* – ensure position tracking & feature refresh lines
# ---------------------------------------------------------------------------


def test_async_update_callback_tracks_position(monkeypatch, emby_device):  # noqa: D401
    dev, _svr, stub = emby_device

    # Initial callback with a media_position different from *last* triggers the
    # timestamp update path (lines ~390-392).
    stub.media_position = 20

    dev.async_update_callback({})  # type: ignore[arg-type]

    assert dev.media_status_last_position == 20
    assert dev.media_status_received is not None

    # Second callback – same position => no update (exercise branch 389). Reset
    # position so the *elif* path (no position + not playing) triggers.
    stub.media_position = None
    stub.is_nowplaying = False

    dev.async_update_callback({})  # type: ignore[arg-type]

    assert dev.media_status_last_position is None


# ---------------------------------------------------------------------------
# *async_browse_media* – error branches (missing hass, invalid path, no user)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_browse_media_requires_hass(emby_device):  # noqa: D401
    dev, _svr, _stub = emby_device
    dev.hass = None  # force missing context

    from homeassistant.exceptions import HomeAssistantError

    with pytest.raises(HomeAssistantError):
        await dev.async_browse_media(media_content_id="media-source://something")


@pytest.mark.asyncio
async def test_browse_media_invalid_media_source_path(emby_device, monkeypatch):  # noqa: D401
    dev, _svr, _stub = emby_device

    # Provide *hass* context dummy so first check passes
    dev.hass = SimpleNamespace()

    # Patch HA helper to return *None* so the 2nd error branch (line 512-513) is executed.
    async def _fake_browse(_hass, _id):  # noqa: D401, ANN001
        return None

    monkeypatch.setattr(
        "custom_components.embymedia.media_player.ha_media_source.async_browse_media",
        _fake_browse,
        raising=False,
    )

    from homeassistant.exceptions import HomeAssistantError

    with pytest.raises(HomeAssistantError):
        await dev.async_browse_media(media_content_id="media-source://abc")


@pytest.mark.asyncio
async def test_browse_media_no_user_found(emby_device, monkeypatch):  # noqa: D401
    dev, _svr, stub = emby_device

    # Remove *UserId* so lookup via /Sessions path is required but returns no match.
    stub.session_raw = {}

    # The fake API already returns user-x match -> adjust to mismatch to force error.
    async def _sessions_stub(*_, **__):  # noqa: D401, ANN001
        return [{"DeviceId": "other"}]

    fake_api = SimpleNamespace(get_sessions=_sessions_stub)
    monkeypatch.setattr(dev, "_get_emby_api", lambda _self=dev: fake_api)  # type: ignore[arg-type]

    from homeassistant.exceptions import HomeAssistantError

    with pytest.raises(HomeAssistantError):
        await dev.async_browse_media()
