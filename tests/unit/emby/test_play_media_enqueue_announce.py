"""Additional unit-tests for *async_play_media* covering *enqueue* & *announce* logic."""

from __future__ import annotations

from types import SimpleNamespace

import pytest


class _StubHTTP:  # pylint: disable=too-few-public-methods
    """Records outgoing REST calls initiated by :pyclass:`EmbyAPI`."""

    def __init__(self):  # noqa: D401
        self.calls = []

    async def handler(self, _self_ref, method: str, path: str, **kwargs):  # noqa: D401, ANN001
        # Store *method*, *path* and keyword arguments so the test can inspect
        # the *PlayCommand* query parameter.
        self.calls.append((method, path, kwargs))

        # Provide canned responses expected by the integration.
        if path == "/Sessions":
            return [
                {
                    "Id": "sess-42",
                    "DeviceId": "dev-42",
                    "PlayState": {"State": "Idle"},
                }
            ]

        # *resolve_media_item* shortcut → EmbyAPI.search not used when patched
        # in these tests.

        # Playback endpoint – return empty body.
        if path.startswith("/Sessions/") and path.endswith("/Playing"):
            return {}

        raise RuntimeError(f"Unhandled EmbyAPI request {method} {path}")


@pytest.fixture()
def emby_device(monkeypatch):  # noqa: D401
    """Return an *EmbyDevice* wired with stubs suitable for enqueue tests."""

    from custom_components.embymedia.media_player import EmbyDevice

    dev = EmbyDevice.__new__(EmbyDevice)  # type: ignore[arg-type]

    fake_device = SimpleNamespace(
        supports_remote_control=True,
        name="Player",
        state="Idle",
        username="john",
        session_id="sess-42",
        unique_id="dev-42",
        session_raw={"UserId": "user-42"},
    )

    dev.device = fake_device
    dev.device_id = "dev-42"
    dev.emby = SimpleNamespace(_host="h", _api_key="k", _port=8096, _ssl=False)
    dev.hass = None  # pyright: ignore[reportAttributeAccessIssue]
    dev._current_session_id = None  # pylint: disable=protected-access

    dev.async_write_ha_state = lambda *_, **__: None  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Patch low-level HTTP layer so no real network I/O occurs.
    # ------------------------------------------------------------------

    from custom_components.embymedia import api as api_mod

    http_stub = _StubHTTP()

    async def _patched(self_api, method: str, path: str, **kwargs):  # noqa: D401, ANN001
        return await http_stub.handler(self_api, method, path, **kwargs)

    monkeypatch.setattr(api_mod.EmbyAPI, "_request", _patched, raising=True)

    # ------------------------------------------------------------------
    # Shortcut the *search* helper used by *resolve_media_item* so the stack
    # does not issue additional HTTP calls.
    # ------------------------------------------------------------------

    async def _search_stub(self_api, *, search_term, item_types, user_id=None, limit=1):  # noqa: D401, ANN001
        # Return a single dummy movie containing the search term.
        return [{"Id": "item-99", "Name": search_term, "Type": "Movie"}]

    monkeypatch.setattr(api_mod.EmbyAPI, "search", _search_stub, raising=True)

    return dev, http_stub


# ---------------------------------------------------------------------------
# Parameterised tests exercising the various *enqueue* / *announce* branches.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "enqueue_param, expected_command",
    [
        (True, "PlayNext"),  # legacy bool → next
        ("add", "PlayLast"),
        (None, "PlayNow"),
    ],
)
async def test_async_play_media_enqueue_variants(emby_device, enqueue_param, expected_command):  # noqa: D401
    dev, http_stub = emby_device
    # The function accepts keyword *enqueue* or service-data **kwargs*.  Pass
    # directly as keyword arg so the helper prefers the explicit parameter.
    await dev.async_play_media(
        media_type="movie",
        media_id="Test",
        enqueue=enqueue_param,
    )

    # Last recorded request must target the playback endpoint.
    _method, _path, kwargs = http_stub.calls[-1]
    assert kwargs["params"]["PlayCommand"] == expected_command


@pytest.mark.asyncio
async def test_async_play_media_announce_overrides_enqueue(emby_device):  # noqa: D401
    """When *announce=True* the helper must use *PlayAnnouncement*."""

    dev, http_stub = emby_device

    await dev.async_play_media(
        media_type="movie",
        media_id="Alarm",
        enqueue="add",  # should be ignored due to announce
        announce=True,
    )

    _method, _path, kwargs = http_stub.calls[-1]
    assert kwargs["params"]["PlayCommand"] == "PlayAnnouncement"


@pytest.mark.asyncio
async def test_async_play_media_invalid_enqueue_raises(emby_device):  # noqa: D401
    """Passing an unsupported *enqueue* string must raise *HomeAssistantError*."""

    from homeassistant.exceptions import HomeAssistantError

    dev, _stub = emby_device

    with pytest.raises(HomeAssistantError):
        await dev.async_play_media(
            media_type="movie",
            media_id="Bad",
            enqueue="invalid-value",  # type: ignore[arg-type]
        )
