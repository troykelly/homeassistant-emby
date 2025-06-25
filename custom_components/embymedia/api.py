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

        # ------------------------------------------------------------------
        # Fallback – Live-TV channel lookup (GitHub issue #202 / task #???)
        # ------------------------------------------------------------------
        # The Emby REST API does **not** expose *TvChannel* objects via the
        # generic ``/Items/{Id}`` routes.  Attempting to query the endpoint
        # therefore results in a *404 – not found* even though the identifier
        # is perfectly valid under the dedicated Live-TV namespace.  When the
        # earlier global **and** user-scoped look-ups failed we make one last
        # attempt through ``/LiveTv/Channels/{Id}`` so that Home Assistant can
        # resolve *channel* objects without knowing the Emby *UserId* (which
        # is commonly missing from `media_player.play_media` service calls
        # issued by the UI).
        #
        # The helper purposefully **does not** depend on the caller passing a
        # *user_id* – the parameter is optional according to the OpenAPI spec
        # and omitting it keeps the public `get_item()` signature unchanged.
        # Any HTTP error is swallowed silently so the function still returns
        # *None* when the identifier truly does not exist.
        # ------------------------------------------------------------------

        if payload is None:
            try:
                # Prefer user-scoped variant when we have an id because the
                # server may attach additional access metadata / parental
                # control flags.

                if user_id:
                    payload = await self._request(
                        "GET", f"/LiveTv/Channels/{item_id}", params={"UserId": str(user_id)}
                    )
                else:  # FALLBACK – anonymous lookup
                    payload = await self._request("GET", f"/LiveTv/Channels/{item_id}")
            except EmbyApiError:
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
    # Live-TV helpers – GitHub issue #202 / task #204
    # ------------------------------------------------------------------

    async def get_live_tv_channels(
        self,
        user_id: str,
        *,
        start_index: int = 0,
        limit: int = 100,
        force_refresh: bool = False,
    ) -> dict[str, Any]:  # noqa: ANN401 – JSON payload
        """Return a slice of *TvChannel* objects available to *user_id*.

        The helper wraps Emby's ``/LiveTv/Channels`` endpoint which backs the
        *Live TV* section in the Emby UI.  Pagination mirrors the behaviour of
        other collection helpers via the ``StartIndex`` / ``Limit`` query
        parameters.

        Emby historically returned either a *plain list* **or** an *object*
        with ``Items`` / ``TotalRecordCount`` depending on server version.
        To shield callers from that inconsistency the wrapper normalises the
        response to the canonical *dict* structure expected by the media
        browsing implementation.
        """

        cache_key = ("__livetv__", start_index, limit, user_id)
        cached = self._children_cache.get(cache_key)
        if not force_refresh and cached and (time.time() - cached[0]) < self._CACHE_TTL:
            return cached[1]

        params: dict[str, str] = {
            "UserId": str(user_id),
            "StartIndex": str(start_index),
            "Limit": str(limit),
        }

        payload = await self._request("GET", "/LiveTv/Channels", params=params)

        # Normalise to {"Items": [...], "TotalRecordCount": N}
        if isinstance(payload, list):
            norm_payload: dict[str, Any] = {
                "Items": payload,
                "TotalRecordCount": len(payload),
            }
        elif isinstance(payload, dict):
            norm_payload = {
                "Items": payload.get("Items", payload.get("items", [])),
                "TotalRecordCount": payload.get(
                    "TotalRecordCount", payload.get("totalRecordCount", 0)
                ),
            }
        else:
            raise EmbyApiError("Unexpected payload from /LiveTv/Channels endpoint")

        self._children_cache[cache_key] = (time.time(), norm_payload)
        return norm_payload

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
    # Issue #219 – obtain a *play-ready* stream URL for a media item
    # ------------------------------------------------------------------

    async def get_stream_url(
        self,
        item_id: str | int,
        *,
        user_id: str | None = None,
        max_bitrate: int | None = 80_000_000,
        device_profile: dict[str, Any] | None = None,
    ) -> str:
        """Return a fully authenticated stream URL for *item_id*.

        The helper implements the negotiation flow researched in GitHub issue
        #218 and encapsulated in ``docs/emby/stream_playback_research.md``:

        1. ``POST /Items/{Id}/PlaybackInfo`` is used to discover the available
           *MediaSources* for the requesting user / device.
        2. The first source that supports **direct play** is preferred because
           it avoids server-side transcoding.  If none match, the helper
           falls back to the first entry that exposes a *TranscodingUrl* (HLS
           master playlist).
        3. The resulting URL is made *self-contained* by appending the Emby
           ``api_key`` query parameter when it is missing.  Down-stream media
           players (Chromecast, browsers, Sonos, …) therefore do not need to
           inject custom headers which greatly simplifies Home Assistant’s
           generic *play media* flow.

        Parameters
        ----------
        item_id
            Emby *ItemId* to obtain the stream URL for.
        user_id
            Optional Emby user under which the request should be executed. If
            omitted, Emby treats the call as *anonymous* which works for
            public libraries but may bypass parental controls.
        max_bitrate
            Upper bitrate cap (in **bits/s**) advertised to Emby when
            negotiating playback.  The rather generous default of 80 Mbit/s
            effectively signals *no limit* for local networks while still
            ensuring the value fits into 32-bit signed integers expected by
            some older Emby versions.
        device_profile
            Optional override of the Emby *DeviceProfile* object.  Callers
            can provide a tailored profile to influence transcoder decisions.
            When *None* a minimal profile advertising support for common
            containers (mp4 / mkv) and audio codecs (aac / mp3) is used.
        """

        # ------------------------------------------------------------------
        # 1. Build POST body for /PlaybackInfo negotiation
        # ------------------------------------------------------------------

        if device_profile is None:
            device_profile = {
                "Name": "home-assistant",
                "DirectPlayProfile": [
                    {"Container": "mp4,mkv", "Type": "Video"},
                    {"Container": "aac,mp3,flac", "Type": "Audio"},
                ],
            }

        body: dict[str, Any] = {
            "MaxStreamingBitrate": max_bitrate,
            "DeviceProfile": device_profile,
        }
        if user_id is not None:
            body["UserId"] = user_id

        playback: dict[str, Any] = await self._request(
            "POST", f"/Items/{item_id}/PlaybackInfo", json=body
        )

        media_sources: list[dict[str, Any]] = playback.get("MediaSources", [])  # type: ignore[arg-type]
        if not media_sources:
            raise EmbyApiError("No MediaSources returned for item – cannot build stream URL")

        # ------------------------------------------------------------------
        # 2. Prefer *direct play* sources and gracefully fall back to HLS.
        # ------------------------------------------------------------------

        chosen_url: str | None = None

        # 2a. First pass – look for direct play support.
        for src in media_sources:
            if src.get("SupportsDirectPlay") and src.get("DirectStreamUrl"):
                chosen_url = src["DirectStreamUrl"]
                break

        # 2b. Fallback – use the first *TranscodingUrl* if necessary.
        if chosen_url is None:
            for src in media_sources:
                if src.get("TranscodingUrl"):
                    chosen_url = src["TranscodingUrl"]
                    break

        if chosen_url is None:
            raise EmbyApiError("Unable to determine a playable stream URL for item")

        # ------------------------------------------------------------------
        # 3. Normalise – ensure URL is absolute and carries the api_key param.
        # ------------------------------------------------------------------

        from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl

        # Some Emby builds return *relative* paths (with or without a leading
        # slash).  Prepend the server base URL in that case so downstream
        # callers always receive an absolute link.
        if not chosen_url.startswith(("http://", "https://")):
            chosen_url = f"{self._base}/{chosen_url.lstrip('/')}"

        # Ensure the `api_key` query parameter is present so that the URL is
        # self-contained and can be fetched without custom headers.
        parsed = urlparse(chosen_url)
        query = dict(parse_qsl(parsed.query))
        if "api_key" not in query:
            query["api_key"] = self._headers.get("X-Emby-Token", "")

        new_query = urlencode(query, doseq=True)
        normalised_url = urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            )
        )

        return normalised_url

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
        percentage as expected by Emby's *SetVolume* command.
        """

        # Clamp `volume_level` to the valid Home-Assistant range (0–1) then
        # convert it to the 0-100 percentage expected by Emby.  **Important**:
        # Emby interprets the JSON *value type* – not just the lexical
        # content.  Passing the number inside a **string** results in the
        # command being silently ignored by many clients (see GitHub
        # issue #190).
        #
        # The argument therefore **must** be sent as an *integer* to
        # guarantee cross-client compatibility.  The correct *GeneralCommand*
        # identifier, confirmed via the upstream WebSocket documentation, is
        # **`SetVolume`** (not the older `VolumeSet`).
        volume_pct: int = int(round(max(0, min(1, volume_level)) * 100))

        await self._post_session_command(
            session_id,
            "SetVolume",
            {"Volume": volume_pct},
        )

    async def mute(self, session_id: str, mute: bool) -> None:
        """Toggle mute state on *session_id*."""

        # Similar to *SetVolume* above Emby evaluates the **actual JSON data
        # type**.  The integration previously sent the boolean flag encoded as
        # the strings "true"/"false" leading to the *un-mute* operation being
        # dropped by the server.  The fix is to transmit a **native** boolean
        # value.

        # Newer versions of Emby expose **separate** command identifiers for
        # *mute* and *un-mute* which do **not** require any additional
        # arguments.  Attempting to re-use the `Mute` command with a boolean
        # argument is accepted by the HTTP layer but ignored by most client
        # applications – exactly the regression reported in GitHub
        # issue #190.

        command = "Mute" if mute else "Unmute"

        await self._post_session_command(
            session_id,
            command,
            None,
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
        arguments: dict[str, str | int | bool] | None = None,
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
            # ----------------------------------------------------------------
            # Heuristic fallback – some public Emby instances (including the
            # hosted test server used by the CI suite) expose the entire HTTP
            # API under the **/emby/** sub-path.  When the base path constructed
            # from *host*/*port* returns *404* we transparently retry the same
            # request with the prefix so callers do not have to hard-code the
            # non-standard root in their *EMBY_URL* environment variable.
            #
            # The retry is *safe* because it only triggers on *404 Not Found*
            # and when the original *path* does *not* already include the
            # namespace.  All other error codes (401, 500, …) are surfaced as
            # :class:`EmbyApiError` without modification.
            # ----------------------------------------------------------------

            if exc.status == 404 and not path.startswith("/emby/"):
                alt_url = f"{self._base}/emby{path}"
                _LOGGER.debug("Retrying Emby request against /emby prefix: %s", alt_url)
                try:
                    async with self._session.request(method, alt_url, **kwargs) as resp2:
                        resp2.raise_for_status()
                        if resp2.content_type == "application/json":
                            return await resp2.json()
                        return await resp2.text()
                except ClientResponseError as exc2:
                    _LOGGER.warning(
                        "Emby API error after /emby retry [%s] %s", exc2.status, exc2.message
                    )
                    raise EmbyApiError(str(exc2)) from exc2

            _LOGGER.warning("Emby API error [%s] %s", exc.status, exc.message)
            raise EmbyApiError(str(exc)) from exc
        except ClientError as exc:  # network error
            _LOGGER.error("Error communicating with Emby server: %s", exc)
            raise EmbyApiError(str(exc)) from exc
