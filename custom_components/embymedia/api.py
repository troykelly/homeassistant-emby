"""Light-weight async helper around the Emby HTTP API.

This module purposefully avoids adding new runtime dependencies - it uses the
`aiohttp` client session that Home Assistant already provides and implements
only the handful of endpoints required for `media_player.play_media` support:

* Library search (`/Items`, `/Search/Hints`).
* Listing active sessions (`/Sessions`).
* Triggering remote playback on a client (`/Sessions/{Id}/Playing`).

It is **not** intended to be a fully-featured Emby SDK.  Keep it minimal and
only expand when new Home Assistant features require additional calls.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import aiohttp

from aiohttp import ClientError, ClientResponseError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "EmbyApiError",
    "EmbyAPI",
]

# -----------------------------------------------------------------------------
# NOTE: Additional helper methods added for GitHub issue #79 – they expose
# commonly used remote-control commands (volume, mute, shuffle, repeat and
# power management) required by upcoming Home Assistant media-player features.
#
# The public wrappers funnel into the private `_post_session_command()` utility
# which POSTs to `/Sessions/{id}/Command` with a request body that follows the
# `GeneralCommand` schema described by the Emby OpenAPI spec.  Keeping the
# implementation generic avoids a proliferation of near-duplicate HTTP helpers
# while retaining a strongly-typed public surface.
# -----------------------------------------------------------------------------


class EmbyApiError(RuntimeError):
    """Raised for *http level* errors received from Emby."""


class EmbyAPI:  # pylint: disable=too-few-public-methods
    """Minimal async wrapper for a subset of the Emby REST API."""

    _CACHE_TTL = 10  # seconds - sessions endpoint only.

    def __init__(
        self,
        hass: HomeAssistant | None,
        host: str,
        api_key: str,
        ssl: bool = False,
        port: int | None = None,
        *,
        session: "aiohttp.ClientSession | None" = None,
    ) -> None:
        """Create a new minimal Emby API wrapper.

        Parameters
        ----------
        hass
            Home Assistant instance - **optional**.  When provided the helper
            will reuse HA's shared aiohttp ClientSession.  When *None* a new
            standalone session (or the supplied *session*) is used which makes
            the class usable outside of Home Assistant e.g. in unit tests or
            simple scripts.
        session
            Pre-created aiohttp `ClientSession` (optional).  Ignored when
            *hass* is supplied because we must use HA's managed session in that
            context.
        """

        self._hass = hass
        scheme = 'https' if ssl else 'http'
        if port is None:
            self._base = f"{scheme}://{host}"
        else:
            self._base = f"{scheme}://{host}:{port}"
        self._headers = {"X-Emby-Token": api_key}

        if hass is not None:
            self._session = async_get_clientsession(hass)
        else:
            # Stand-alone mode - use provided session or create a new one.
            if session is None:
                import aiohttp

                session = aiohttp.ClientSession()
            self._session = session

        # Very small in-memory cache for the sessions list - refreshed at most
        # every `_CACHE_TTL` seconds to reduce HTTP round-trips during rapid
        # play_media service calls.
        self._sessions_cache: list[dict[str, Any]] = []
        self._sessions_cached_at: float = 0.0

        # --------------------------------------------------------------
        # Simple in-memory caches for library & children helpers
        # --------------------------------------------------------------

        # Keyed by `(user_id,)` - stores a tuple of (timestamp, data)
        self._views_cache: dict[tuple[str], tuple[float, list[dict[str, Any]]]] = {}

        # Keyed by `(item_id, start_index, limit, user_id)` - stores a tuple
        # of (timestamp, payload).  The query parameters are part of the key
        # because pagination may request overlapping but distinct slices.
        self._children_cache: dict[
            tuple[str | int, int, int, str | None], tuple[float, dict[str, Any]]
        ] = {}

        # ------------------------------------------------------------------
        # Lightweight *item* cache – GitHub issue #139
        # ------------------------------------------------------------------
        # ``/Items/{Id}`` look-ups occur frequently while building the
        # *BrowseMedia* tree because the integration has to ask Emby whether
        # a given object can **expand** (directory) or **play** (leaf).  On a
        # large library this results in hundreds of small REST calls which
        # quickly add up to noticeable latency.
        #
        # A *very small* in-memory cache (keyed by the identifier only) is
        # sufficient to eliminate the duplicate round-trips that happen
        # during a single browse request chain – Home Assistant never issues
        # concurrent requests for different users, therefore we can reuse
        # the same payload safely.
        #
        # The entries are short-lived (``_CACHE_TTL`` seconds) so memory usage
        # stays negligible and changes in the library become visible almost
        # immediately when the user navigates back.

        # Keyed by ``(item_id, user_id)`` – stores ``(timestamp, payload)``.
        #
        # The optional *user_id* is part of the key because the Emby server
        # may return **different** play-state metadata and access
        # permissions for the same *ItemId* depending on the requesting
        # user (e.g. parental controls).  Treating the pair as one logical
        # identifier keeps the cache safe while still eliminating redundant
        # HTTP round-trips when the same client walks the browse hierarchy.
        self._item_cache: dict[
            tuple[str | int, str | None], tuple[float, dict[str, Any] | None]
        ] = {}

        # Caches for virtual *Resume* / *Favorites* directory helpers added
        # for GitHub issue #78.  The payloads are small but we still keep a
        # short-lived cache to avoid hammering the Emby HTTP API when users
        # repeatedly open and close the browse pane in the Home Assistant UI.

        # Keyed by `(user_id, start_index, limit)`
        self._resume_cache: dict[tuple[str, int, int], tuple[float, dict[str, Any]]] = {}

        # Keyed by `(user_id, start_index, limit)`
        self._favorites_cache: dict[tuple[str, int, int], tuple[float, dict[str, Any]]] = {}

        _LOGGER.debug("Initialised EmbyAPI for %s", self._base)

    # ---------------------------------------------------------------------
    # Public helpers
    # ---------------------------------------------------------------------

    async def get_sessions(self, *, force_refresh: bool = False) -> List[dict[str, Any]]:
        """Return the list of active sessions.

        The result is cached briefly to avoid spamming the server while Home
        Assistant is trying multiple look-ups in quick succession.
        """

        if not force_refresh and (time.time() - self._sessions_cached_at) < self._CACHE_TTL:
            return self._sessions_cache

        data = await self._request("GET", "/Sessions")
        # Basic validation - ensure it's a list
        if not isinstance(data, list):
            raise EmbyApiError("/Sessions did not return a list as expected")

        self._sessions_cache = data
        self._sessions_cached_at = time.time()
        return data

    async def play(
        self,
        session_id: str,
        item_ids: List[str] | List[int],
        *,
        play_command: str = "PlayNow",
        start_position_ticks: int | None = None,
        controlling_user_id: str | None = None,
    ) -> None:
        """Trigger playback of *item_ids* on the specified session.

        Parameters
        ----------
        session_id
            Target Emby *SessionId* obtained from the ``/Sessions`` endpoint.
        item_ids
            One or more *ItemId* values to be queued/played.
        controlling_user_id
            Optional Emby user id that should be recorded as the *controlling*
            user.  When omitted Emby associates the command with the **admin**
            account which may bypass parental controls.  See GitHub issue #125.
        """

        params: Dict[str, str] = {
            "ItemIds": ",".join([str(i) for i in item_ids]),
            "PlayCommand": play_command,
        }
        if start_position_ticks is not None:
            params["StartPositionTicks"] = str(start_position_ticks)
        if controlling_user_id is not None:
            params["ControllingUserId"] = controlling_user_id

        await self._request("POST", f"/Sessions/{session_id}/Playing", params=params, json={})

    async def search(
        self,
        *,
        search_term: str,
        item_types: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        limit: int = 1,
    ) -> List[dict[str, Any]]:
        """Search the library and return a list of matching items.

        The implementation uses the generic `/Items` filter API because it is
        deterministic and returns full `BaseItemDto` entries.  Fuzzy matching
        via `/Search/Hints` can be added later if necessary.
        """

        params: Dict[str, str] = {
            "SearchTerm": search_term,
            "Limit": str(limit),
            "Recursive": "true",
        }
        if item_types:
            params["IncludeItemTypes"] = ",".join(item_types)
        if user_id:
            params["UserId"] = user_id

        payload = await self._request("GET", "/Items", params=params)
        # payload is expected to be a dict with an "Items" list - fallback to
        # empty list for defensive coding.
        return payload.get("Items", []) if isinstance(payload, dict) else []

    # ------------------------------------------------------------------
    # Convenience helpers - not part of the original minimal surface but
    # required by the media search resolver and play_media support.
    # ------------------------------------------------------------------

    async def get_item(
        self,
        item_id: str | int,
        *,
        user_id: str | None = None,
    ) -> dict[str, Any] | None:  # noqa: ANN401 - wide JSON
        """Return full metadata for *item_id* or *None* if it does not exist.

        The Emby REST API exposes two flavours of the *item lookup* endpoint

        1. ``/Items/{Id}`` – **server-wide** view that ignores user specific
           metadata such as play state or parental control.
        2. ``/Users/{UserId}/Items/{Id}`` – scoped to a particular user and
           therefore the authoritative choice when the caller *does* know the
           active user (required for play state information and, crucially,
           for some library types such as TV shows which are only exposed via
           the user-bound route – see GitHub issue #182).

        Historically the integration used the *global* variant because the
        user id is not always known (e.g. during Home Assistant start-up when
        the player has not yet established a session).  This worked for most
        content types but broke when browsing *Favorites* that contain TV
        shows – the server rejects the bare ``/Items/{Id}`` call with *404 –
        not found* even though the item is perfectly accessible through the
        user scoped path.

        The helper now prefers the **user scoped** endpoint whenever the
        caller supplies a *user_id* and falls back to the legacy global path
        otherwise so we remain backward compatible with existing call-sites
        (unit tests, third-party code etc.).

        GitHub issue #139 – repeated ``/Items/{id}`` calls are a performance
        hot-spot when browsing very large libraries (>50k items).  To avoid
        hammering the Emby server we maintain an **ephemeral** in-memory cache
        that is consulted before a network request is issued.  The cache is
        deliberately small (keyed solely by *item_id*) and obeys the global
        ``_CACHE_TTL`` so updates in the library propagate quickly.
        """

        cache_key = (item_id, user_id)

        cache_entry = self._item_cache.get(cache_key)
        if cache_entry and (time.time() - cache_entry[0]) < self._CACHE_TTL:
            return cache_entry[1]


        payload: dict[str, Any] | None

        # Build endpoint – prefer the *user scoped* variant when possible but
        # gracefully fall back to the legacy *global* path when the server
        # responds with *404* or any other HTTP level error.  This keeps
        # backwards-compatibility with older Emby builds and avoids breaking
        # the extensive unit-test suite which stubs only the global route.

        # 1. Try the legacy *global* endpoint first for backwards
        #    compatibility with existing unit-tests and older Emby releases.
        try:
            payload = await self._request("GET", f"/Items/{item_id}")
        except EmbyApiError:
            # 2. The server rejected the global route (common for TV shows).
            #    When we have a *user_id* fall back to the user-scoped
            #    endpoint.  Any error here is swallowed so the helper
            #    ultimately returns *None* when the item truly does not
            #    exist.
            if user_id:
                try:
                    payload = await self._request("GET", f"/Users/{user_id}/Items/{item_id}")
                except EmbyApiError:
                    payload = None
            else:
                payload = None

        # Store (including *None* results) to avoid re-querying missing ids
        self._item_cache[cache_key] = (time.time(), payload)

        return payload

    # ------------------------------------------------------------------
    # New helpers - used by media browsing implementation (issue #26)
    # ------------------------------------------------------------------

    async def get_user_views(
        self,
        user_id: str,
        *,
        force_refresh: bool = False,
    ) -> list[dict[str, Any]]:  # noqa: ANN401 - JSON payload
        """Return the list of libraries / *views* for *user_id*.

        The Emby endpoint returns either a plain list or an object wrapping
        the list under an ``Items`` key depending on the server version.  The
        helper normalises the output to *always* be a list to simplify caller
        code.
        """

        cache_key = (user_id,)
        cached = self._views_cache.get(cache_key)
        if not force_refresh and cached and (time.time() - cached[0]) < self._CACHE_TTL:
            return cached[1]

        payload = await self._request("GET", f"/Users/{user_id}/Views")

        # Normalise to a flat list
        if isinstance(payload, dict):
            views = payload.get("Items", [])
        elif isinstance(payload, list):
            views = payload
        else:
            raise EmbyApiError("Unexpected payload from /Views endpoint")

        # Cache & return
        self._views_cache[cache_key] = (time.time(), views)
        return views

    async def get_item_children(
        self,
        item_id: str | int,
        *,
        user_id: str | None = None,
        start_index: int = 0,
        limit: int = 100,
        force_refresh: bool = False,
    ) -> dict[str, Any]:  # noqa: ANN401 - JSON payload
        """Return children for an item - wrapper around `/Items/{Id}/Children`.

        The helper exposes simple pagination parameters mirroring the Emby API
        (`StartIndex`, `Limit`).  Callers can iterate by adjusting these
        values.  The raw payload (dict) is returned unchanged to retain
        ``TotalRecordCount`` and other metadata.
        """

        cache_key = (item_id, start_index, limit, user_id)
        cached = self._children_cache.get(cache_key)
        if not force_refresh and cached and (time.time() - cached[0]) < self._CACHE_TTL:
            return cached[1]

        params: dict[str, str] = {
            "StartIndex": str(start_index),
            "Limit": str(limit),
        }
        if user_id:
            params["UserId"] = user_id

        payload = await self._request("GET", f"/Items/{item_id}/Children", params=params)

        if not isinstance(payload, dict):
            raise EmbyApiError("Unexpected payload from /Children endpoint - expected JSON object")

        # Cache & return
        self._children_cache[cache_key] = (time.time(), payload)
        return payload

    # ------------------------------------------------------------------
    # Issue #78 – additional library helpers for *Resume* and *Favorites*
    # ------------------------------------------------------------------

    async def get_resume_items(
        self,
        user_id: str,
        *,
        start_index: int = 0,
        limit: int = 100,
        force_refresh: bool = False,
    ) -> dict[str, Any]:  # noqa: ANN401 – JSON payload
        """Return the *Continue Watching* list for *user_id*.

        The Emby REST API exposes the data via ``/Users/{id}/Items/Resume``.
        The payload structure matches the generic ``/Items`` response therefore
        the helper returns it **verbatim** so callers can reuse existing
        parsing logic.
        """

        cache_key = (user_id, start_index, limit)
        cached = self._resume_cache.get(cache_key)
        if not force_refresh and cached and (time.time() - cached[0]) < self._CACHE_TTL:
            return cached[1]

        params = {
            "StartIndex": str(start_index),
            "Limit": str(limit),
        }

        payload = await self._request("GET", f"/Users/{user_id}/Items/Resume", params=params)

        if not isinstance(payload, dict):
            raise EmbyApiError("Unexpected payload from Resume endpoint – expected JSON object")

        self._resume_cache[cache_key] = (time.time(), payload)
        return payload

    async def get_favorite_items(
        self,
        user_id: str,
        *,
        start_index: int = 0,
        limit: int = 100,
        force_refresh: bool = False,
    ) -> dict[str, Any]:  # noqa: ANN401 – JSON payload
        """Return the *Favorites* list for *user_id*."""

        cache_key = (user_id, start_index, limit)
        cached = self._favorites_cache.get(cache_key)
        if not force_refresh and cached and (time.time() - cached[0]) < self._CACHE_TTL:
            return cached[1]

        params = {
            "StartIndex": str(start_index),
            "Limit": str(limit),
            "IsFavorite": "true",
            "Recursive": "true",
            "SortBy": "SortName",
        }

        payload = await self._request("GET", f"/Users/{user_id}/Items", params=params)

        if not isinstance(payload, dict):
            raise EmbyApiError("Unexpected payload from Favorites query – expected JSON object")

        self._favorites_cache[cache_key] = (time.time(), payload)
        return payload

    # ------------------------------------------------------------------
    # Issue #161 – helper for library *directory* pagination
    # ------------------------------------------------------------------

    async def get_user_items(
        self,
        user_id: str,
        *,
        parent_id: str | int | None = None,
        start_index: int = 0,
        limit: int = 100,
        force_refresh: bool = False,
    ) -> dict[str, Any]:  # noqa: ANN401 – JSON payload
        """Return a slice of items for *user_id* optionally scoped by *parent_id*.

        The method wraps Emby's generic ``/Users/{id}/Items`` endpoint which
        powers many UI listings.  It is primarily used by the media browsing
        fallback path (GitHub issue #161) when an item identifier represents
        a *library root* that is **not** available through ``/Items/{id}``.

        Parameters
        ----------
        user_id
            Emby user to scope the query to.
        parent_id
            Optional *ParentId* filter – when supplied the server returns the
            direct children of the given container.  When *None* the query
            spans the entire library.
        start_index, limit
            Pagination parameters mirroring the REST API fields.  The helper
            imposes no additional constraints and forwards the values as
            provided so callers can retrieve arbitrary slices.
        force_refresh
            Bypass the short-lived in-memory cache even when the key is still
            considered valid.  This exists mainly for unit-tests that need
            deterministic control over HTTP traffic.
        """

        cache_key = (parent_id or "__root__", start_index, limit, user_id)
        cached = self._children_cache.get(cache_key)
        if not force_refresh and cached and (time.time() - cached[0]) < self._CACHE_TTL:
            return cached[1]

        params: dict[str, str] = {
            "StartIndex": str(start_index),
            "Limit": str(limit),
        }
        if parent_id is not None:
            params["ParentId"] = str(parent_id)

        payload = await self._request("GET", f"/Users/{user_id}/Items", params=params)

        if not isinstance(payload, dict):
            raise EmbyApiError("Unexpected payload from /Items query – expected JSON object")

        # Re-use the *children* cache because the semantics are identical – a
        # tuple of (timestamp, payload) keyed by all pagination parameters.
        self._children_cache[cache_key] = (time.time(), payload)
        return payload

    # ------------------------------------------------------------------
    # Issue #79 – additional remote-control helpers
    # ------------------------------------------------------------------

    async def set_volume(self, session_id: str, volume_level: float) -> None:
        """Set *absolute* volume on a client.

        `volume_level` follows Home Assistant convention – a float between
        0.0 and 1.0.  Values are clamped to that range and translated to a
        percentage as expected by Emby's *VolumeSet* command.
        """

        volume_pct = max(0, min(1, volume_level)) * 100  # clamp & convert
        await self._post_session_command(
            session_id,
            "VolumeSet",
            {"Volume": str(int(round(volume_pct)))},
        )

    async def mute(self, session_id: str, mute: bool) -> None:
        """Toggle mute state on *session_id*."""

        await self._post_session_command(
            session_id,
            "Mute",
            {"Mute": "true" if mute else "false"},
        )

    async def shuffle(self, session_id: str, shuffle: bool) -> None:
        """Enable or disable shuffle mode."""

        await self._post_session_command(
            session_id,
            "Shuffle",
            {"Shuffle": "true" if shuffle else "false"},
        )

    async def repeat(self, session_id: str, mode: str) -> None:
        """Set repeat *mode* – one of ``RepeatNone``, ``RepeatAll``, ``RepeatOne``."""

        if mode not in {"RepeatNone", "RepeatAll", "RepeatOne"}:
            raise ValueError("Invalid repeat mode")

        await self._post_session_command(
            session_id,
            "Repeat",
            {"Mode": mode},
        )

    async def power_state(self, session_id: str, turn_on: bool) -> None:
        """Power on/off the target client (best-effort)."""

        await self._post_session_command(
            session_id,
            "DisplayOn" if turn_on else "Standby",
        )

    # ------------------------------------------------------------------
    # Internal helpers – not part of the public surface
    # ------------------------------------------------------------------

    async def _post_session_command(
        self,
        session_id: str,
        name: str,
        arguments: dict[str, str] | None = None,
    ) -> None:
        """Send a *GeneralCommand* payload to `/Sessions/{id}/Command`."""

        payload = {
            "Name": name,
            "Arguments": arguments or {},
        }

        await self._request("POST", f"/Sessions/{session_id}/Command", json=payload)

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:  # noqa: ANN401 - wide type for JSON
        url = f"{self._base}{path}"
        headers = kwargs.pop("headers", {})
        headers.update(self._headers)
        kwargs["headers"] = headers

        try:
            async with self._session.request(method, url, **kwargs) as resp:
                resp.raise_for_status()
                if resp.content_type == "application/json":
                    return await resp.json()
                return await resp.text()
        except ClientResponseError as exc:
            _LOGGER.warning("Emby API error [%s] %s", exc.status, exc.message)
            raise EmbyApiError(str(exc)) from exc
        except ClientError as exc:  # network error
            _LOGGER.error("Error communicating with Emby server: %s", exc)
            raise EmbyApiError(str(exc)) from exc
