"""Utility helpers for encoding / decoding *Emby* `media_content_id` strings.

The Home Assistant media-browser API expects a *flat* string that can safely
traverse JSON, YAML and HTTP path segments without additional escaping.  While
the integration historically used the simple form::

    emby://<item_id>

this lacks **type information** which forces extra server round-trips whenever
the handler must decide whether the identifier is directly playable or needs
another browse step (movie vs. folder, channel vs. recording series, …).

GitHub issue #161 defines a deterministic scheme that embeds the *Emby* item
`Type` (e.g. ``Movie``, ``Series``, ``TvChannel``) *optionally* in front of the
identifier using a regular URI authority component::

    emby://{type}/{id}

The resulting string fulfils all requirements:

* URL-safe – both *type* and *id* are percent-encoded via
  :pyfunc:`urllib.parse.quote`.
* Fully reversible – :pyfunc:`decode_item_id` returns exactly the original
  tuple.
* Forward-compatible – additional query parameters (e.g. ``?start=200`` used
  for pagination) are preserved by the generic :pyfunc:`urllib.parse.urlparse`
  round-trip.

Only the two helpers below are public.  The rest of the integration will adopt
the new scheme incrementally in follow-up tasks to avoid breaking existing
tests while migration is in progress.
"""

from __future__ import annotations

from urllib.parse import quote, unquote, urlparse

__all__: list[str] = [
    "encode_item_id",
    "decode_item_id",
]


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def encode_item_id(item_id: str, *, media_type: str | None = None) -> str:  # noqa: D401 – helper function
    """Return a URL-safe ``emby://`` identifier for *item_id*.

    Parameters
    ----------
    item_id:
        Raw Emby *ItemId* as returned by the REST API.

    media_type:
        Optional Emby ``Type`` (``Movie``, ``Series``…) or collection type.  If
        supplied it is embedded between the scheme and the item id so that
        :pyfunc:`decode_item_id` can recover it without additional server
        metadata lookups.
    """

    if not item_id:
        raise ValueError("item_id must be a non-empty string")

    # Percent-encode so the output survives transport through path, query and
    # JSON contexts unchanged.
    safe_id = quote(item_id, safe="")

    if media_type:
        safe_type = quote(media_type, safe="")
        return f"emby://{safe_type}/{safe_id}"

    # Historical *type-less* form – preserved for backwards-compatibility.
    return f"emby://{safe_id}"


def decode_item_id(value: str) -> tuple[str | None, str]:  # noqa: D401 – helper function
    """Return ``(media_type, item_id)`` parsed from *value*.

    The helper accepts both the new *typed* form and the legacy
    ``emby://<item_id>`` variant so callers can migrate incrementally.
    """

    parsed = urlparse(value)

    if parsed.scheme != "emby":
        raise ValueError("unsupported scheme – expected 'emby://'")

    # *Typed* form – authority holds the type and the path holds the id.
    if parsed.netloc and parsed.path and parsed.path != "/":
        media_type = unquote(parsed.netloc)
        item_id = unquote(parsed.path.lstrip("/"))
        return media_type, item_id

    # *Legacy* form – the authority (or first path segment) is the id.
    if parsed.netloc:
        return None, unquote(parsed.netloc)

    if parsed.path and parsed.path != "/":
        return None, unquote(parsed.path.lstrip("/"))

    raise ValueError("invalid emby URI – missing item id")
