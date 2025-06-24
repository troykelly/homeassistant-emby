"""Verify that *async_setup_platform* chooses the correct default port.

The integration should honour the official Emby defaults when the user does
**not** explicitly provide a *port* in the Home Assistant configuration or
config-flow:

* HTTP  – 8096
* HTTPS – 8920

Regression covered by GitHub issue #181.
"""

from __future__ import annotations

import asyncio

import pytest


class _RecorderEmbyServer:  # pylint: disable=too-few-public-methods
    """Light-weight stand-in for *pyemby.EmbyServer* that records init args."""

    last_args: tuple | None = None  # (host, key, port, ssl, loop)

    def __init__(self, host, key, port, ssl, loop):  # noqa: D401 – mimic signature
        # Store the received arguments so the test can assert on them.
        _RecorderEmbyServer.last_args = (host, key, port, ssl, loop)

        # Minimal surface expected by the integration (not used in this test)
        self.devices: dict = {}

    # Stubbed convenience helpers ------------------------------------------------
    def add_new_devices_callback(self, _cb):  # noqa: D401
        return None

    def add_stale_devices_callback(self, _cb):  # noqa: D401
        return None

    def start(self):  # noqa: D401 – no-op
        return None

    async def stop(self):  # noqa: D401 – no-op
        return None


class _FakeBus:  # pylint: disable=too-few-public-methods
    def async_listen_once(self, _event_type, _callback):  # noqa: D401
        return None


class _FakeHass:  # pylint: disable=too-few-public-methods
    """Very small stub sufficient for *async_setup_platform*."""

    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.bus = _FakeBus()


# ---------------------------------------------------------------------------
# Parametrised test cases – (ssl_flag, expected_port)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ssl_flag,expected_port",
    [
        (False, 8096),  # HTTP default
        (True, 8920),  # HTTPS default
    ],
)
async def test_default_port_selection(monkeypatch, ssl_flag, expected_port):  # noqa: D401
    """Ensure the integration selects the correct default Emby port."""

    from custom_components.embymedia import media_player as mp_mod

    # Replace the real *pyemby.EmbyServer* with our recorder stub.
    monkeypatch.setattr(mp_mod, "EmbyServer", _RecorderEmbyServer)

    hass = _FakeHass()

    config = {
        "api_key": "ABCDEF",
        "host": "emby.local",
        # *No* port defined – exercise the default inference logic.
        "ssl": ssl_flag,
    }

    # Call the coroutine under test. We do not care about entities so pass
    # a dummy async_add_entities callable.
    await mp_mod.async_setup_platform(hass, config, lambda _ents, update=False: None)  # type: ignore[arg-type]

    # Retrieve the arguments captured by our stubbed *EmbyServer*.
    assert _RecorderEmbyServer.last_args is not None
    _, _, port_arg, ssl_arg, _ = _RecorderEmbyServer.last_args

    # Verify that *async_setup_platform* passed the expected port and ssl
    # parameters to the underlying Emby client.
    assert port_arg == expected_port
    assert ssl_arg is ssl_flag


# ---------------------------------------------------------------------------
# Explicit custom port should be forwarded unchanged
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_custom_port_preserved(monkeypatch):  # noqa: D401
    """User-supplied *port* must be forwarded verbatim to EmbyServer."""

    from custom_components.embymedia import media_player as mp_mod

    monkeypatch.setattr(mp_mod, "EmbyServer", _RecorderEmbyServer)

    hass = _FakeHass()

    config = {
        "api_key": "XYZ",
        "host": "emby.local",
        "port": 12345,
        "ssl": False,
    }

    await mp_mod.async_setup_platform(hass, config, lambda _ents, update=False: None)  # type: ignore[arg-type]

    assert _RecorderEmbyServer.last_args is not None
    _, _, port_arg, _, _ = _RecorderEmbyServer.last_args
    assert port_arg == 12345
