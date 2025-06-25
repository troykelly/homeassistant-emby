"""Emby *media_source* provider (GitHub issue #220).

# pyright: reportUnusedImport=false, reportAssignmentType=false, reportAttributeAccessIssue=false

This module exposes library items from the Emby media server through Home
Assistant's *media source* infrastructure so that **any** player entity (e.g.
Chromecast, browser, Sonos) can request a stable URL via

    media-source://emby/<ItemId>

and receive a fully authenticated stream URL produced by
:pymeth:`custom_components.embymedia.api.EmbyAPI.get_stream_url`.

The provider intentionally keeps the implementation *minimal* – it does **not**
offer hierarchical browsing because Home Assistant already fetches the browse
tree through :pymeth:`media_player.async_browse_media`.  Its sole
responsibility is to translate an *ItemId* into a :class:`ResolveMediaSource`
object.

The file avoids hard dependencies on Home Assistant at **import time** to keep
unit-tests lightweight.  When the real integration is loaded inside HA, the
actual classes (``MediaSource``, ``MediaSourceItem`` …) are available.  During
stand-alone tests we fall back to **tiny stub definitions** so the module can
be imported without the full Home Assistant runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import mimetypes
from typing import Any


LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Conditional imports for *type checking* purposes only.  At **runtime** the
# module falls back to tiny local stubs when Home Assistant is not present –
# this keeps the test-suite independent of the full HA environment while still
# offering accurate type information to Pyright / editors.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Runtime fallbacks – only used when *homeassistant* cannot be imported.
# ---------------------------------------------------------------------------

try:
    import importlib

    _ms_mod = importlib.import_module("homeassistant.components.media_source")
    MediaSource = getattr(_ms_mod, "MediaSource")  # type: ignore[assignment]

    _models_mod = importlib.import_module("homeassistant.components.media_source.models")
    MediaSourceItem = getattr(_models_mod, "MediaSourceItem")  # type: ignore[assignment]
    ResolveMediaSource = getattr(_models_mod, "ResolveMediaSource")  # type: ignore[assignment]

    BrowseError = importlib.import_module("homeassistant.components.media_player.errors").BrowseError  # type: ignore[assignment]

except ModuleNotFoundError:  # pragma: no cover – expected during unit-tests

    class BrowseError(RuntimeError):
        """Lightweight stub matching the real HA exception signature."""

    class MediaSource:  # pylint: disable=too-few-public-methods
        """Tiny no-op base class so the provider can be instantiated."""

        name: str = "stub"

        def __init__(self, *_: Any, **__: Any) -> None:  # noqa: D401 – preserve HA signature
            pass

    class MediaSourceItem:  # pylint: disable=too-few-public-methods
        """Stub carrying the *identifier* attribute accessed by the provider."""

        def __init__(self, identifier: str, source: str | None = None) -> None:  # noqa: D401
            self.identifier = identifier
            self.source = source or "emby"

    @dataclass(slots=True)
    class ResolveMediaSource:  # noqa: D401 – align with HA naming
        """Minimal replacement for the HA data-class."""

        url: str
        mime_type: str | None = None


# ---------------------------------------------------------------------------
# Local imports – placed after the HA fallback stubs to avoid circular issues.
# ---------------------------------------------------------------------------

from .api import EmbyAPI, EmbyApiError

# Public constant so external callers can refer to the provider name.
SOURCE_DOMAIN = "emby"


# ---------------------------------------------------------------------------
# Helper – MIME type detection
# ---------------------------------------------------------------------------


def _guess_mime_type(url: str) -> str | None:
    """Return an RFC 2046 `mime/type` string based on *url* file extension."""

    # URL may carry query parameters – strip them before feeding into mimetypes.
    import urllib.parse as _ulib

    path = _ulib.urlparse(url).path
    mime, _ = mimetypes.guess_type(path)
    return mime


# ---------------------------------------------------------------------------
# Provider implementation
# ---------------------------------------------------------------------------


class EmbyMediaSource(MediaSource):  # type: ignore[misc]
    """Resolve ``media-source://emby/<ItemId>`` into a direct stream URL."""

    name: str = "Emby"

    def __init__(self, hass):  # noqa: D401 – signature mandated by HA
        super().__init__(SOURCE_DOMAIN, self.name)  # type: ignore[call-arg]
        self.hass = hass

    # ------------------------------------------------------------------
    # Helper – locate the shared EmbyAPI instance
    # ------------------------------------------------------------------

    def _get_api(self) -> EmbyAPI:
        """Return the *first* EmbyAPI client stored in *hass.data*."""

        domain_data = getattr(self.hass, "data", {}).get("embymedia")  # type: ignore[attr-defined]
        if not domain_data:
            raise BrowseError("Emby integration is not initialised – no API client available")

        # The integration usually stores per-config-entry buckets keyed by
        # entry_id.  Each maps to an object that exposes the **api** under
        # either ``api`` or ``emby_api`` – support both names for resilience.
        for entry in domain_data.values():
            api = entry.get("api") or entry.get("emby_api")
            if isinstance(api, EmbyAPI):
                return api

        raise BrowseError("Unable to locate EmbyAPI handle in hass.data")

    # ------------------------------------------------------------------
    # Core – resolve
    # ------------------------------------------------------------------

    async def async_resolve_media(self, item: MediaSourceItem) -> ResolveMediaSource:  # type: ignore[override]
        """Return :class:`ResolveMediaSource` for *item*.

        The provider accepts the following identifier formats:

        1. ``<ItemId>`` – plain item id.
        2. ``emby://stream/<ItemId>`` – emitted by older browse flows.
        3. ``emby_item/<ItemId>``  – legacy string kept for backwards compat.
        """

        raw_identifier: str = item.identifier  # pyright: ignore[reportGeneralTypeIssues]

        if not raw_identifier:
            raise BrowseError("Empty identifier supplied to Emby media source")

        # Normalise – strip legacy scheme/prefix components.
        if raw_identifier.startswith("emby://"):
            raw_identifier = raw_identifier[len("emby://") :]
            if raw_identifier.startswith("stream/"):
                raw_identifier = raw_identifier[len("stream/") :]

        if raw_identifier.startswith("emby_item/"):
            raw_identifier = raw_identifier[len("emby_item/") :]

        if not raw_identifier:
            raise BrowseError("Could not extract item id from identifier")

        api = self._get_api()

        try:
            stream_url: str = await api.get_stream_url(raw_identifier)
        except EmbyApiError as exc:
            LOGGER.warning("Failed to resolve Emby stream for %s: %s", raw_identifier, exc)
            raise BrowseError(f"Failed to resolve Emby stream – {exc}") from exc

        mime_type = _guess_mime_type(stream_url)

        return ResolveMediaSource(url=stream_url, mime_type=mime_type)


# ---------------------------------------------------------------------------
# Entrypoint required by Home Assistant – discovered via manifest
# ---------------------------------------------------------------------------


async def async_get_media_source(hass):  # noqa: D401 – signature mandated by HA
    """Return instance used by Home Assistant's *media source* registry."""

    return EmbyMediaSource(hass)
