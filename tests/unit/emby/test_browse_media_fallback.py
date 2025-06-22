"""Unit test verifying *media_source* fallback delegation (issue #28).

The Emby integration must pass through any ``media_content_id`` that starts
with ``media-source://`` to Home Assistant’s *media_source* helper instead of
attempting to resolve the path through the Emby API.
"""

from __future__ import annotations

import types
import sys
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# Fixture – patch *homeassistant.components.media_source*
# ---------------------------------------------------------------------------


@pytest.fixture()
def media_source_stub(monkeypatch):  # noqa: D401 – pytest naming convention
    """Inject a lightweight *media_source* stub into *sys.modules*.

    The integration imports the component via::

        from homeassistant.components import media_source as ha_media_source

    Therefore we have to provide **two** modules:

    1. ``homeassistant.components.media_source`` – actual stub implementation
    2. ``homeassistant.components`` – parent package (when not already present)
    """

    # Ensure parent namespace exists so ``import …components`` succeeds.
    parent_name = "homeassistant.components"
    if parent_name not in sys.modules:  # pragma: no cover – already present in most test-runs
        parent_mod = types.ModuleType(parent_name)
        sys.modules[parent_name] = parent_mod
    else:
        parent_mod = sys.modules[parent_name]

    # Create stub *media_source* sub-module with an async *browse* helper.
    ms_mod = types.ModuleType(f"{parent_name}.media_source")

    _calls: list[tuple[Any, str]] = []  # record (hass, media_content_id)

    async def _async_browse_media(hass, media_content_id):  # noqa: D401 – mimic signature
        _calls.append((hass, media_content_id))
        return {"title": "stub", "children": []}  # minimal BrowseMedia-like dict

    ms_mod.async_browse_media = _async_browse_media  # type: ignore[attr-defined]

    full_mod_name = f"{parent_name}.media_source"

    # Register sub-module under full name so the *import* statement resolves.
    sys.modules[full_mod_name] = ms_mod

    # Also expose as attribute on the parent for *from … import* semantics.
    setattr(parent_mod, "media_source", ms_mod)

    # ------------------------------------------------------------------
    # Ensure the Emby integration picks up the stub even when it has been
    # imported *before* this fixture runs (other tests import the module
    # earlier in the session).  We patch the attribute on the already loaded
    # module so the reference held in ``components.emby.media_player`` points
    # to our stub implementation.
    # ------------------------------------------------------------------

    import custom_components.embymedia.media_player as mp_mod  # local import – already loaded during tests

    setattr(mp_mod, "ha_media_source", ms_mod)

    # Yield call-list so individual test-functions can assert on it.
    yield _calls

    # Clean-up – remove stub from *sys.modules* to avoid leakage between tests.
    sys.modules.pop(f"{parent_name}.media_source", None)


# ---------------------------------------------------------------------------
# Fixture – minimal *EmbyDevice* instance under test
# ---------------------------------------------------------------------------


@pytest.fixture()
def emby_device(monkeypatch):  # noqa: D401 – pytest naming
    """Return an :class:`components.emby.media_player.EmbyDevice` stub.

    Only the attributes required by *async_browse_media* are initialised.  The
    HTTP helper and Emby API calls are **not** executed in this test – any
    accidental invocation would raise because we replace :pymeth:`_get_emby_api`
    with a function that throws.
    """

    from custom_components.embymedia.media_player import EmbyDevice

    dev = EmbyDevice.__new__(EmbyDevice)  # type: ignore[arg-type]

    # Inject dummy pyemby device – only *session_raw* is accessed by the code
    # path after the media_source early-return, therefore an empty mapping is
    # sufficient.
    stub_inner = types.SimpleNamespace(session_raw={})

    dev.device = stub_inner
    dev.device_id = "dev-x"
    dev._current_session_id = None  # pylint: disable=protected-access

    # The Home Assistant *hass* object is not used by the logic besides being
    # forwarded to the stub; we can pass any truthy object.
    dev.hass = object()  # pyright: ignore[reportAttributeAccessIssue]

    # Defensive – ensure the Emby API helper is **not** invoked during the
    # fallback path.  If it is, the test will fail with *RuntimeError*.
    def _unexpected_api_call(*_, **__):  # noqa: D401 – retaining signature
        raise RuntimeError("_get_emby_api must not be called for media_source paths")

    monkeypatch.setattr(dev, "_get_emby_api", _unexpected_api_call, raising=True)

    return dev


# ---------------------------------------------------------------------------
# Test – verify delegation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_media_source_delegation(media_source_stub, emby_device):  # noqa: D401 – pytest naming
    """`async_browse_media` must delegate *media-source://* URIs."""

    media_source_calls = media_source_stub  # alias for readability

    path = "media-source://media/folder"

    # Invoke the integration method under test.
    result = await emby_device.async_browse_media(media_content_id=path)

    # The stub helper must have been called exactly once with the original args.
    assert len(media_source_calls) == 1
    hass_obj, received_path = media_source_calls[0]

    assert hass_obj is emby_device.hass
    assert received_path == path

    # The result object returned by the stub must be propagated unchanged.
    assert result == {"title": "stub", "children": []}
