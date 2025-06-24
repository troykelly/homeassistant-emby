"""Connection matrix tests for :class:`custom_components.embymedia.api.EmbyAPI`.

These test-cases validate that the helper correctly interprets the various
``host``/``port``/``ssl`` combinations that users can configure via the Home
Assistant UI or YAML.  They *do not* perform real network traffic – the goal
is to ensure that the composed *base* URL is accurate so that downstream HTTP
requests hit the intended endpoint.

The scenarios mirror the acceptance-criteria enumerated in GitHub *issue
#182* – *add connection test matrix (HTTP/HTTPS & ports)*.
"""

from __future__ import annotations

import pytest


# Unit under test ----------------------------------------------------------------

from custom_components.embymedia.api import EmbyAPI


# ---------------------------------------------------------------------------
# Positive cases – helper must build the correct ``_base`` URL
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ssl_flag,port,expected_base",
    [
        # 1. HTTP standard port (80)
        (False, 80, "http://emby.local:80"),
        # 2. HTTP custom port (8096 – Emby's default)
        (False, 8096, "http://emby.local:8096"),
        # 3. HTTPS standard port (443)
        (True, 443, "https://emby.local:443"),
        # 4. HTTPS custom port (8920 – Emby's TLS default)
        (True, 8920, "https://emby.local:8920"),
    ],
)
def test_base_url_composition(ssl_flag: bool, port: int, expected_base: str):  # noqa: D401 – test name conventions
    """Ensure the internal ``_base`` attribute reflects all parameter combos."""

    # A *real* aiohttp.ClientSession* requires a running event-loop.  For this
    # static attribute test we can pass a **dummy** object instead because no
    # HTTP requests are executed.

    from types import SimpleNamespace

    api = EmbyAPI(
        None,
        host="emby.local",
        api_key="dummy",
        ssl=ssl_flag,
        port=port,
        session=SimpleNamespace(),
    )

    # The *private* attribute is part of the public contract for our unit
    # tests – accessing it directly is fine within the repository context.
    assert api._base == expected_base  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Negative cases – low-level connectivity errors must surface as *EmbyApiError*
# ---------------------------------------------------------------------------


# The *ClientResponseError* constructor requires a *request_info* object that
# exposes a ``real_url`` attribute for its ``__str__`` implementation.  A very
# small stub (``types.SimpleNamespace(real_url="...")``) is sufficient.

import types
from aiohttp import ClientError, ClientResponseError

from custom_components.embymedia.api import EmbyApiError


class _RaisingSession:  # pylint: disable=too-few-public-methods
    """Very small *aiohttp* stand-in that always raises the supplied *error*."""

    def __init__(self, exc_to_raise: Exception) -> None:
        self._exc = exc_to_raise

    # ``aiohttp.ClientSession.request`` is implemented as an *async context
    # manager*.  We therefore need to return a helper that supports the
    # ``async with`` protocol and raises when entered.

    class _RaiseCtx:  # pylint: disable=too-few-public-methods
        def __init__(self, exc: Exception):
            self._exc = exc

        async def __aenter__(self):  # noqa: D401 – context-manager protocol
            raise self._exc

        async def __aexit__(self, exc_type, exc, tb):  # noqa: D401 – unused parameters
            return False

    def request(self, *_args, **_kwargs):  # noqa: D401 – mimic ``aiohttp`` signature
        return self._RaiseCtx(self._exc)


# Prepare the parametrised *exceptions* outside of the decorator so we can
# construct the *ClientResponseError* with the required *request_info* stub.

_PARAM_EXCEPTIONS = [
    ClientError("network boom"),
    ClientResponseError(
        request_info=types.SimpleNamespace(real_url="http://emby.local"),
        history=(),
        status=401,
        message="unauth",
        headers=None,
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("exc_type", _PARAM_EXCEPTIONS)
async def test_request_error_translation(exc_type):  # noqa: D401 – test name conventions
    """Both *ClientError* and *ClientResponseError* must translate to *EmbyApiError*."""

    api = EmbyAPI(None, host="emby.local", api_key="dummy", ssl=False, port=8096, session=_RaisingSession(exc_type))

    # Force a call that goes through the *internal* _request helper.
    with pytest.raises(EmbyApiError):
        await api.get_sessions(force_refresh=True)
