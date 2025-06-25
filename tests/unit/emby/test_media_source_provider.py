"""Unit-tests for Emby *media_source* provider (GitHub issue #220)."""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass

import pytest


# ---------------------------------------------------------------------------
# Dynamic stubs for *homeassistant.components.media_source*
# ---------------------------------------------------------------------------


def _install_media_source_stubs(monkeypatch):  # noqa: D401 – helper, not a test
    """Create minimal *media_source* packages in *sys.modules*.

    The real Home Assistant packages are **not** available when the unit tests
    run in isolation.  We therefore patch *sys.modules* so that the provider
    can import the expected names without raising *ModuleNotFoundError*.
    """

    parent_name = "homeassistant.components"

    # Ensure ``homeassistant`` top-level package exists.
    if "homeassistant" not in sys.modules:  # pragma: no cover – normally absent
        sys.modules["homeassistant"] = types.ModuleType("homeassistant")

    # Parent *components* namespace.
    if parent_name not in sys.modules:
        sys.modules[parent_name] = types.ModuleType(parent_name)

    # ------------------------------------------------------------------
    # models sub-module providing the data-classes.
    # ------------------------------------------------------------------

    models_mod = types.ModuleType(f"{parent_name}.media_source.models")

    class MediaSourceItem:  # pylint: disable=too-few-public-methods
        def __init__(self, identifier: str):
            self.identifier = identifier

    @dataclass(slots=True)
    class ResolveMediaSource:  # noqa: D401 – mimic HA naming
        url: str
        mime_type: str | None = None

    models_mod.MediaSourceItem = MediaSourceItem  # type: ignore[attr-defined]
    models_mod.ResolveMediaSource = ResolveMediaSource  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # media_source sub-module exposing *MediaSource* base & *BrowseError*.
    # ------------------------------------------------------------------

    ms_mod = types.ModuleType(f"{parent_name}.media_source")

    class BrowseError(RuntimeError):
        """Stub replicating HA exception type."""

    class MediaSource:  # pylint: disable=too-few-public-methods
        """Very small replacement replicating essential behaviour."""

        def __init__(self, domain: str, name: str):  # noqa: D401 – mimic HA signature
            self.domain = domain
            self.name = name

    ms_mod.MediaSource = MediaSource  # type: ignore[attr-defined]
    ms_mod.BrowseError = BrowseError  # type: ignore[attr-defined]

    # Link *models* as attribute for ``from … import models`` style.
    ms_mod.models = models_mod  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Register all sub-modules under their fully qualified names.
    # ------------------------------------------------------------------

    sys.modules[models_mod.__name__] = models_mod
    sys.modules[ms_mod.__name__] = ms_mod

    # Also attach to parent components namespace so *from homeassistant.components import media_source* works
    components_pkg = sys.modules[parent_name]
    setattr(components_pkg, "media_source", ms_mod)


# ---------------------------------------------------------------------------
# Fixture – stub Home Assistant handle with EmbyAPI mock
# ---------------------------------------------------------------------------


from custom_components.embymedia.api import EmbyAPI


class _StubEmbyAPI(EmbyAPI):  # type: ignore[misc]
    """Tiny :class:`EmbyAPI` replacement for unit-tests."""

    # pylint: disable=useless-super-delegation

    def __init__(self, return_url: str | None = None, exception: Exception | None = None):
        # Bypass parent initialisation entirely – we just need the method.
        self._return_url = return_url
        self._exception = exception

    async def get_stream_url(self, *_args, **_kwargs):  # noqa: D401 – retains signature
        if self._exception:
            raise self._exception  # pylint: disable=raising-bad-type
        return self._return_url  # type: ignore[return-value]


@pytest.fixture(autouse=True)
def _patch_media_source(monkeypatch):  # noqa: D401 – implicit fixture
    """Ensure media_source stubs are present for **all** tests in this module."""

    _install_media_source_stubs(monkeypatch)


def _make_hass(api) -> object:  # noqa: D401 – helper
    """Return a minimal *hass* stub exposing ``data`` mapping."""

    hass = types.SimpleNamespace()
    # Emulate config-entry bucket – key does not matter as long as *api* is reachable.
    hass.data = {  # type: ignore[attr-defined]
        "embymedia": {"entry-id": {"api": api}}
    }
    return hass


# ---------------------------------------------------------------------------
# Tests – success & error paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_media_success(monkeypatch):  # noqa: D401 – pytest naming
    """Provider must convert *ItemId* into final URL via EmbyAPI."""

    # Arrange – stub API & hass.
    url = "http://example.com/stream.mp4?api_key=xyz"
    api_stub = _StubEmbyAPI(return_url=url)

    hass = _make_hass(api_stub)

    # Import the provider **after** stubs are installed.
    from custom_components.embymedia.media_source import (
        EmbyMediaSource,
        SOURCE_DOMAIN,
    )

    from homeassistant.components.media_source.models import MediaSourceItem  # type: ignore

    provider = EmbyMediaSource(hass)

    item = MediaSourceItem(identifier="123")

    result = await provider.async_resolve_media(item)

    assert result.url == url
    assert result.mime_type == "video/mp4"

    # The provider must use the correct *source* name constant.
    assert provider.domain == SOURCE_DOMAIN  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_resolve_media_error(monkeypatch):  # noqa: D401 – pytest naming
    """Provider must raise *BrowseError* when EmbyAPI fails."""

    from custom_components.embymedia.media_source import EmbyMediaSource, BrowseError
    from homeassistant.components.media_source.models import MediaSourceItem  # type: ignore
    from custom_components.embymedia.api import EmbyApiError

    api_stub = _StubEmbyAPI(exception=EmbyApiError("boom"))

    hass = _make_hass(api_stub)

    provider = EmbyMediaSource(hass)

    item = MediaSourceItem(identifier="123")

    with pytest.raises(BrowseError):
        await provider.async_resolve_media(item)
