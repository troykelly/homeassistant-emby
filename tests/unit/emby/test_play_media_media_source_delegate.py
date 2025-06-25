"""Unit test verifying *media_source* delegation in ``async_play_media`` (issue #222).

The integration must **not** attempt to look up the Emby library or trigger a
remote *play* command when the caller passes a ``media-source://`` identifier.
Instead it should delegate the request back to Home Assistant *core* by
resolving the path through the *media_source* helper **before** any Emby REST
calls happen.
"""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace
from typing import Any, List

import pytest


# ---------------------------------------------------------------------------
# Fixtures – stub *media_source* component & EmbyDevice
# ---------------------------------------------------------------------------


@pytest.fixture()
def media_source_stub(monkeypatch):  # noqa: D401 – pytest naming convention
    """Inject a lightweight *media_source* stub into *sys.modules*.

    The integration imports the component via::

        from homeassistant.components import media_source as ha_media_source

    Therefore we have to provide **both** modules:

    1. ``homeassistant.components.media_source`` – actual stub implementation
    2. ``homeassistant.components`` – parent package (when not already present)
    """

    parent_name = "homeassistant.components"

    # Ensure parent namespace exists for the sub-module attribute injection.
    if parent_name not in sys.modules:  # pragma: no cover – usually present
        parent_mod = types.ModuleType(parent_name)
        sys.modules[parent_name] = parent_mod
    else:
        parent_mod = sys.modules[parent_name]

    # Create stub *media_source* sub-module exposing *async_resolve_media*.
    ms_mod = types.ModuleType(f"{parent_name}.media_source")

    _calls: List[tuple[Any, str, str | None]] = []  # record (hass, id, entity_id?)

    async def _async_resolve_media(hass, media_id, entity_id=None):  # noqa: D401 – mimic HA signature
        """Record invocation & return dummy *ResolveMediaSource*."""

        _calls.append((hass, media_id, entity_id))

        # Minimal anonymous object matching HA's "ResolveMediaSource" API.
        return SimpleNamespace(url="https://example/test.mp3", mime_type="audio/mpeg")

    ms_mod.async_resolve_media = _async_resolve_media  # type: ignore[attr-defined]

    full_mod_name = f"{parent_name}.media_source"
    sys.modules[full_mod_name] = ms_mod
    setattr(parent_mod, "media_source", ms_mod)

    # Patch the reference held by the already imported *media_player* module.
    import custom_components.embymedia.media_player as mp_mod  # noqa: WPS433 – module loaded during tests

    monkeypatch.setattr(mp_mod, "ha_media_source", ms_mod, raising=False)

    yield _calls  # expose recorded invocations to the test

    # Cleanup – remove stub sub-module again.
    sys.modules.pop(full_mod_name, None)


@pytest.fixture()
def emby_device(monkeypatch):  # noqa: D401 – pytest naming
    """Return an *EmbyDevice* instance with stubs blocking HTTP calls."""

    from custom_components.embymedia.media_player import EmbyDevice

    dev = EmbyDevice.__new__(EmbyDevice)  # type: ignore[arg-type]

    # Configure minimal *pyemby* device structure used by the code path – no
    # attributes are accessed after the early *media_source* return.
    inner_dev = SimpleNamespace(session_raw={})
    dev.device = inner_dev
    dev.device_id = "dev-stub"

    # Provide stub for *_get_emby_api* that raises when invoked – the test
    # asserts that the helper is **not** called for the delegation path.
    def _unexpected_api_call(*_, **__):  # noqa: D401 – keep generic signature
        raise RuntimeError("_get_emby_api must not be called for media_source delegation path")

    monkeypatch.setattr(dev, "_get_emby_api", _unexpected_api_call, raising=True)

    # Minimal Home Assistant *hass* surrogate – only identity comparison used.
    dev.hass = object()  # pyright: ignore[reportAttributeAccessIssue]

    # Ensure entity writes do not fail.
    dev.async_write_ha_state = lambda *_, **__: None  # type: ignore[assignment]

    return dev


# ---------------------------------------------------------------------------
# Tests – verify delegation flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_play_media_delegates_to_media_source(media_source_stub, emby_device):  # noqa: D401
    """`async_play_media` must call *media_source.async_resolve_media* early."""

    calls = media_source_stub  # alias for readability

    await emby_device.async_play_media(
        media_type="music",
        media_id="media-source://emby/12345",
    )

    # Exactly one delegation call must have been recorded.
    assert len(calls) == 1

    hass_obj, received_id, entity_hint = calls[0]

    # Verify arguments forwarded correctly
    assert hass_obj is emby_device.hass
    assert received_id == "media-source://emby/12345"
    # `entity_id` parameter is optional – ensure we pass *something*.
    assert entity_hint in (None, emby_device.entity_id)

    # No Emby REST calls should have happened – see fixture stub.
