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
    BrowseMediaSource = getattr(_models_mod, "BrowseMediaSource")  # type: ignore[assignment]

    _mp_mod = importlib.import_module("homeassistant.components.media_player")
    BrowseMedia = getattr(_mp_mod, "BrowseMedia")  # type: ignore[assignment]
    MediaClass = getattr(_mp_mod, "MediaClass")  # type: ignore[assignment]
    MediaType = getattr(_mp_mod, "MediaType")  # type: ignore[assignment]

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

    # -------------------------------------------------------------------
    # Additional stubs required for *browse* support (issue #237)
    # -------------------------------------------------------------------

    class _SimpleEnum(str):
        """Very small helper emulating *enum.Enum* string behaviour."""

        def __new__(cls, value: str):  # noqa: D401 – behaviour stub
            return str.__new__(cls, value)

        def __init__(self, value: str) -> None:  # noqa: D401 – no-op
            super().__init__()

    class MediaClass(_SimpleEnum):
        DIRECTORY = "directory"
        MOVIE = "movie"
        TV_SHOW = "tvshow"
        MUSIC = "music"
        ALBUM = "album"
        TRACK = "track"
        PLAYLIST = "playlist"
        CHANNEL = "channel"
        VIDEO = "video"

    class MediaType(_SimpleEnum):
        APP = "app"
        APPS = "apps"
        MUSIC = "music"
        VIDEO = "video"

    class BrowseMedia:  # pylint: disable=too-few-public-methods
        """Lightweight stand-in for Home Assistant's *BrowseMedia* class."""

        def __init__(
            self,
            *,
            media_class: str,
            media_content_id: str,
            media_content_type: str,
            title: str,
            can_play: bool,
            can_expand: bool,
            children: list["BrowseMedia"] | None = None,
            children_media_class: str | None = None,
            thumbnail: str | None = None,
        ) -> None:  # noqa: D401 – replicate key behaviour only
            self.media_class = media_class
            self.media_content_id = media_content_id
            self.media_content_type = media_content_type
            self.title = title
            self.can_play = can_play
            self.can_expand = can_expand
            self.children = children or []
            self.children_media_class = children_media_class
            self.thumbnail = thumbnail

    class BrowseMediaSource(BrowseMedia):  # pylint: disable=too-few-public-methods
        """Derivation adding *domain* / *identifier* semantics."""

        def __init__(
            self,
            *,
            domain: str | None,
            identifier: str | None,
            **kwargs: Any,
        ) -> None:  # noqa: D401 – mimic HA signature

            self.domain = domain
            self.identifier = identifier

            media_content_id = "media-source://"
            if domain:
                media_content_id += domain
            if identifier:
                media_content_id += f"/{identifier}"

            super().__init__(media_content_id=media_content_id, **kwargs)  # type: ignore[arg-type]


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

        # Import constants from the *media_player* module to ensure the browse
        # experience mirrors the entity-scoped tree.  The import is placed
        # inside ``__init__`` so that unit-tests which patch the module can
        # reliably monkey-patch the values **before** an instance is created.

        try:
            from .media_player import _PAGE_SIZE as PAGE_SIZE  # type: ignore
            from .media_player import _COLLECTION_TYPE_MAP, _ITEM_TYPE_MAP  # type: ignore

            self._page_size: int = PAGE_SIZE
            self._collection_type_map = _COLLECTION_TYPE_MAP
            self._item_type_map = _ITEM_TYPE_MAP
        except Exception:  # pragma: no cover – fallback when import fails
            self._page_size = 100  # reasonable default
            self._collection_type_map = {
                "movies": (MediaClass.MOVIE, "movies"),
                "tvshows": (MediaClass.TV_SHOW, "tvshow"),
                "music": (MediaClass.MUSIC, "music"),
            }
            self._item_type_map = {
                "Movie": (MediaClass.MOVIE, "movie", True, False),
                "Series": (MediaClass.TV_SHOW, "tvshow", False, True),
                "Episode": (MediaClass.VIDEO, "episode", True, False),
                "Season": (MediaClass.DIRECTORY, "season", False, True),
            }

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
    # Internal helpers – user id resolution & mapping utilities
    # ------------------------------------------------------------------

    async def _determine_user_id(self, api: EmbyAPI) -> str:
        """Return a *UserId* suitable for library browsing.

        The entity-less media browser does not carry a natural user context so
        we fall back to the *first* active session user returned by
        ``/Sessions``.  When the server has no active clients we attempt to
        locate a *user_id* entry in the Home Assistant config-entry bucket
        which advanced users often populate to enforce a controlled profile.
        """

        try:
            sessions = await api.get_sessions(force_refresh=True)
        except Exception:  # pragma: no cover – network / auth failure
            sessions = []

        if sessions:
            for sess in sessions:
                uid = sess.get("UserId") or sess.get("userId")
                if uid:
                    return str(uid)

        # No active sessions – inspect config entry meta.
        for entry in getattr(self.hass, "config_entries", []) or []:  # type: ignore[attr-defined]
            if getattr(entry, "domain", "") != "embymedia":
                continue
            uid = entry.data.get("user_id") if hasattr(entry, "data") else None
            if uid:
                return str(uid)

        raise BrowseError("Unable to determine an Emby user for media browsing")

    # -------------------------
    # Mapping helpers
    # -------------------------

    def _map_item_type(self, item: dict) -> tuple[str, str, bool, bool]:  # noqa: ANN401 – JSON in
        """Return ``(media_class, content_type, can_play, can_expand)`` tuple."""

        item_type = item.get("Type") or item.get("CollectionType") or "Folder"

        if item_type in self._item_type_map:
            return self._item_type_map[item_type]

        if item_type in self._collection_type_map:
            mc, ct = self._collection_type_map[item_type]
            return (mc, ct, False, True)

        return (MediaClass.DIRECTORY, "directory", False, True)

    def _item_to_browse(self, item: dict) -> "BrowseMediaSource":  # noqa: ANN401
        """Convert an Emby REST payload *item* into *BrowseMediaSource*."""

        media_class, content_type, can_play, can_expand = self._map_item_type(item)

        item_id = str(item.get("Id"))

        return BrowseMediaSource(
            domain=SOURCE_DOMAIN,
            identifier=item_id,
            media_class=media_class,
            media_content_type=content_type,
            title=item.get("Name", "Unknown"),
            can_play=can_play,
            can_expand=can_expand,
            thumbnail=None,
        )

    def _view_to_browse(self, item: dict) -> "BrowseMediaSource":  # noqa: ANN401
        """Convert a *view* (library root) item returned by `/Views`."""

        collection_type = item.get("CollectionType", "folder")
        media_class, content_type = self._collection_type_map.get(
            collection_type, (MediaClass.DIRECTORY, "directory")
        )

        item_id = str(item.get("Id"))

        return BrowseMediaSource(
            domain=SOURCE_DOMAIN,
            identifier=item_id,
            media_class=media_class,
            media_content_type=content_type,
            title=item.get("Name", "Unknown"),
            can_play=False,
            can_expand=True,
            children_media_class=None if media_class is MediaClass.DIRECTORY else media_class,
            thumbnail=None,
        )

    def _make_pagination_node(self, title: str, parent_id: str, start: int) -> "BrowseMediaSource":
        """Create a synthetic *Prev* / *Next* directory entry."""

        identifier = f"{parent_id}?start={start}"

        return BrowseMediaSource(
            domain=SOURCE_DOMAIN,
            identifier=identifier,
            media_class=MediaClass.DIRECTORY,
            media_content_type="directory",
            title=title,
            can_play=False,
            can_expand=True,
            thumbnail=None,
        )

    # ------------------------------------------------------------------
    # Public – browse implementation (GitHub issue #237)
    # ------------------------------------------------------------------

    async def async_browse_media(self, item: "MediaSourceItem") -> "BrowseMediaSource":  # type: ignore[override]
        """Return hierarchical *BrowseMediaSource* tree for *item*."""

        identifier: str | None = getattr(item, "identifier", None)

        api = self._get_api()
        user_id = await self._determine_user_id(api)

        # ROOT ----------------------------------------------------------------
        if not identifier:
            views = await api.get_user_views(user_id)

            children = [self._view_to_browse(v) for v in views]

            # Append virtual directories
            children.append(
                BrowseMediaSource(
                    domain=SOURCE_DOMAIN,
                    identifier="resume",
                    media_class=MediaClass.DIRECTORY,
                    media_content_type="directory",
                    title="Continue Watching",
                    can_play=False,
                    can_expand=True,
                )
            )

            children.append(
                BrowseMediaSource(
                    domain=SOURCE_DOMAIN,
                    identifier="favorites",
                    media_class=MediaClass.DIRECTORY,
                    media_content_type="directory",
                    title="Favorites",
                    can_play=False,
                    can_expand=True,
                )
            )

            return BrowseMediaSource(
                domain=SOURCE_DOMAIN,
                identifier=None,
                media_class=MediaClass.DIRECTORY,
                media_content_type="directory",
                title="Emby Library",
                can_play=False,
                can_expand=True,
                children=children,
            )

        # --------------------------------------------------------------
        # Pagination support – extract *start* query parameter when present.
        # --------------------------------------------------------------

        from urllib.parse import urlparse, parse_qs

        base_id = identifier
        start_idx = 0
        if "?" in identifier:
            parsed = urlparse(identifier)
            base_id = parsed.path
            qs = parse_qs(parsed.query)
            if "start" in qs:
                try:
                    start_idx = int(qs["start"][0])
                except (ValueError, TypeError):
                    start_idx = 0

        # VIRTUAL : resume / favorites ---------------------------------
        if base_id in ("resume", "favorites"):
            if base_id == "resume":
                slice_payload = await api.get_resume_items(
                    user_id, start_index=start_idx, limit=self._page_size
                )
                title = "Continue Watching"
            else:
                slice_payload = await api.get_favorite_items(
                    user_id, start_index=start_idx, limit=self._page_size
                )
                title = "Favorites"

            items = slice_payload.get("Items", []) if isinstance(slice_payload, dict) else []
            total = slice_payload.get("TotalRecordCount", len(items)) if isinstance(slice_payload, dict) else len(items)

            children_nodes = [self._item_to_browse(it) for it in items]

            # Prev / Next pagination tiles
            if start_idx > 0:
                prev_start = max(0, start_idx - self._page_size)
                children_nodes.insert(0, self._make_pagination_node("← Prev", base_id, prev_start))

            if (start_idx + self._page_size) < total:
                next_start = start_idx + self._page_size
                children_nodes.append(self._make_pagination_node("Next →", base_id, next_start))

            return BrowseMediaSource(
                domain=SOURCE_DOMAIN,
                identifier=identifier,
                media_class=MediaClass.DIRECTORY,
                media_content_type="directory",
                title=title,
                can_play=False,
                can_expand=True,
                children=children_nodes,
            )

        # LIBRARY / FOLDER / ITEM ---------------------------------------
        try:
            # Fetch children slice – first call to discover whether expandable.
            slice_payload = await api.get_item_children(
                base_id, user_id=user_id, start_index=start_idx, limit=self._page_size
            )
        except EmbyApiError as exc:
            LOGGER.warning("Failed to fetch children for %s: %s", base_id, exc)
            raise BrowseError(str(exc)) from exc

        child_items = slice_payload.get("Items", []) if isinstance(slice_payload, dict) else []
        total_count = slice_payload.get("TotalRecordCount", len(child_items)) if isinstance(slice_payload, dict) else len(child_items)

        children_nodes = [self._item_to_browse(it) for it in child_items]

        if start_idx > 0:
            prev_start = max(0, start_idx - self._page_size)
            children_nodes.insert(0, self._make_pagination_node("← Prev", base_id, prev_start))

        if (start_idx + self._page_size) < total_count:
            next_start = start_idx + self._page_size
            children_nodes.append(self._make_pagination_node("Next →", base_id, next_start))

        return BrowseMediaSource(
            domain=SOURCE_DOMAIN,
            identifier=identifier,
            media_class=MediaClass.DIRECTORY,
            media_content_type="directory",
            title=child_items[0].get("Name", "Unknown") if child_items else "Directory",
            can_play=False,
            can_expand=True,
            children=children_nodes,
        )

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
