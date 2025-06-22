"""Exercise *async_setup_platform* path to increase coverage for setup logic."""

from __future__ import annotations

import asyncio

import pytest


# ---------------------------------------------------------------------------
# Stubs – Fake Home Assistant core + Emby server
# ---------------------------------------------------------------------------


class _FakeBus:  # pylint: disable=too-few-public-methods
    def __init__(self):
        self.listeners = []

    def async_listen_once(self, event_type, callback):  # noqa: D401
        self.listeners.append((event_type, callback))


class _FakeHass:  # pylint: disable=too-few-public-methods
    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.bus = _FakeBus()


class _FakeDevice(dict):
    """Dictionary subclass so attribute access works via key lookup."""

    def __getattr__(self, item):
        return self[item]


class _FakeEmbyServer:  # pylint: disable=too-few-public-methods
    """Drop-in replacement for ``pyemby.EmbyServer`` used during setup."""

    last_instance = None  # type: _FakeEmbyServer | None

    def __init__(self, host, key, port, ssl, loop):  # noqa: D401 – mimic signature
        self._host = host
        self._api_key = key
        self._port = port
        self._ssl = ssl
        self.loop = loop

        self.devices: dict[str, _FakeDevice] = {}

        self._new_cb = None
        self._stale_cb = None

        _FakeEmbyServer.last_instance = self

    # ------------------------------------------------------------------
    # Interface expected by the integration
    # ------------------------------------------------------------------

    def add_new_devices_callback(self, cb):  # noqa: D401
        self._new_cb = cb

    def add_stale_devices_callback(self, cb):  # noqa: D401
        self._stale_cb = cb

    def start(self):  # noqa: D401 – no-op
        self.started = True  # type: ignore[attr-defined]

    async def stop(self):  # noqa: D401 – no-op
        self.stopped = True  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_setup_platform(monkeypatch):  # noqa: D401 – pytest naming
    """Run the setup routine and verify device callbacks operate as intended."""

    from components.emby import media_player as mp_mod

    # Patch external dependency *pyemby.EmbyServer* with our stub.
    monkeypatch.setattr(mp_mod, "EmbyServer", _FakeEmbyServer)

    # Track entities added via async_add_entities.
    added_entities = []

    def _add_entities(ents, update=False):  # noqa: D401
        added_entities.extend(ents)

    hass = _FakeHass()

    config = {
        "api_key": "k",
        "host": "h",
        "port": 8096,
        "ssl": False,
    }

    # Run the coroutine under test.
    await mp_mod.async_setup_platform(hass, config, _add_entities)

    # The stub Emby server instance should now be available.
    server = _FakeEmbyServer.last_instance
    assert server is not None

    # Simulate discovery of a new device by injecting one into *server.devices*
    fake_dev = _FakeDevice(
        state="Playing",
        name="Kitchen",
        supports_remote_control=True,
        session_id="sess-k",
        media_type="Movie",
    )
    server.devices["dev-k"] = fake_dev

    # Trigger the callback that was registered during setup.
    assert server._new_cb is not None
    server._new_cb(None)

    # One entity must have been created and passed to HA.
    assert len(added_entities) == 1

    ent = added_entities[0]
    # Basic sanity – ensure the wrapper exposes the expected name property.
    assert ent.name == "Emby Kitchen"

    # Exercise a handful of convenience properties for coverage.
    _ = (
        ent.state,
        ent.supported_features,
        ent.extra_state_attributes,
        ent.media_content_type,
    )

    # ------------------------------------------------------------------
    # Also exercise the *lazy _get_emby_api* logic which is not hit by other
    # unit-tests because it is usually monkey-patched.
    # ------------------------------------------------------------------

    class _DummyApi:  # noqa: D401 – minimal stub
        def __init__(self, *_, **__):  # noqa: D401 – ignore params
            pass

    import components.emby.api as api_mod

    # Swap the real helper with the stub then call the method.
    monkeypatch.setattr(api_mod, "EmbyAPI", _DummyApi)

    api_obj = ent._get_emby_api()  # pylint: disable=protected-access
    assert isinstance(api_obj, _DummyApi)
