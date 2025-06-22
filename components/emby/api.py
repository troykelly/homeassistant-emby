"""Light-weight async helper around the Emby HTTP API.

This module purposefully avoids adding new runtime dependencies – it uses the
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
from typing import Any, Dict, List, Optional

from aiohttp import ClientError, ClientResponseError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "EmbyApiError",
    "EmbyAPI",
]


class EmbyApiError(RuntimeError):
    """Raised for *http level* errors received from Emby."""


class EmbyAPI:  # pylint: disable=too-few-public-methods
    """Minimal async wrapper for a subset of the Emby REST API."""

    _CACHE_TTL = 10  # seconds – sessions endpoint only.

    def __init__(
        self,
        hass: HomeAssistant | None,
        host: str,
        api_key: str,
        port: int | None = None,
        ssl: bool,
        *,
        session=None,
    ) -> None:
        """Create a new minimal Emby API wrapper.

        Parameters
        ----------
        hass
            Home Assistant instance – **optional**.  When provided the helper
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
            # Stand-alone mode – use provided session or create a new one.
            if session is None:
                import aiohttp

                session = aiohttp.ClientSession()
            self._session = session

        # Very small in-memory cache for the sessions list – refreshed at most
        # every `_CACHE_TTL` seconds to reduce HTTP round-trips during rapid
        # play_media service calls.
        self._sessions_cache: list[dict[str, Any]] = []
        self._sessions_cached_at: float = 0.0

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
        # Basic validation – ensure it's a list
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
    ) -> None:
        """Trigger playback of *item_ids* on the specified session."""

        params: Dict[str, str] = {
            "ItemIds": ",".join([str(i) for i in item_ids]),
            "PlayCommand": play_command,
        }
        if start_position_ticks is not None:
            params["StartPositionTicks"] = str(start_position_ticks)

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
        # payload is expected to be a dict with an "Items" list – fallback to
        # empty list for defensive coding.
        return payload.get("Items", []) if isinstance(payload, dict) else []

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:  # noqa: ANN401 – wide type for JSON
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
