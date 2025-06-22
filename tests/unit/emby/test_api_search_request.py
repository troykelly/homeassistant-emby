"""Extra coverage for :class:`custom_components.embymedia.api.EmbyAPI` – *search*, *get_item* and low-level error handling."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from aiohttp import ClientError, ClientResponseError

from custom_components.embymedia.api import EmbyAPI, EmbyApiError


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


class _FakeResp:
    """Very small stub emulating :class:`aiohttp.ClientResponse`."""

    def __init__(self, *, status: int = 200, json_data=None, text="", content_type="application/json"):
        self.status = status
        self._json_data = json_data
        self._text_data = text
        self.content_type = content_type

    async def __aenter__(self):  # noqa: D401 – context manager helper
        return self

    async def __aexit__(self, exc_type, exc, tb):  # noqa: D401
        return False

    def raise_for_status(self):
        if self.status >= 400:
            # Provide *request_info* with minimal attributes expected by
            # aiohttp when the exception is stringified.
            req_info = SimpleNamespace(real_url="http://fake")
            # Constructing *ClientResponseError* with minimal stubs intentionally skips
            # several optional aiohttp internals – tell Pyright to relax
            # the strict type checks for this test helper.
            raise ClientResponseError(
                request_info=req_info,  # pyright: ignore[reportArgumentType]
                history=None,  # pyright: ignore[reportArgumentType]
                status=self.status,
                message="fail",
                headers=None,
            )

    async def json(self):  # noqa: D401
        return self._json_data

    async def text(self):  # noqa: D401
        return self._text_data


class _FakeSession:  # pylint: disable=too-few-public-methods
    """Replaces the underlying aiohttp session inside EmbyAPI.

    The real aiohttp API returns an **object** that behaves as an asynchronous
    context-manager – it is *not* awaited explicitly in the production code. We
    therefore provide a *regular* (non-async) ``request`` method that returns
    :class:`_FakeResp` which already implements ``__aenter__/__aexit__``.
    """

    def __init__(self):
        self._next_resp = _FakeResp(json_data={})
        self.last_call = None

    def queue(self, resp):  # add response for next request
        self._next_resp = resp

    def request(self, method, url, **kwargs):  # noqa: D401 – signature compatible
        self.last_call = {"method": method, "url": url, **kwargs}

        # Simulate network-layer exception when *_next_resp* is an exception instance.
        if isinstance(self._next_resp, Exception):
            raise self._next_resp

        return self._next_resp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_happy_path(monkeypatch):
    """`search()` must return the ``Items`` list from the API response."""

    fake_session = _FakeSession()
    monkeypatch.setattr(EmbyAPI, "_CACHE_TTL", 0)  # disable caching for isolation

    api = EmbyAPI(None, host="h", api_key="k", session=fake_session)

    fake_items = [{"Id": "1"}, {"Id": "2"}]
    fake_session.queue(_FakeResp(json_data={"Items": fake_items}))

    got = await api.search(search_term="matrix")
    assert got == fake_items


@pytest.mark.asyncio
async def test_search_missing_items_key(monkeypatch):
    """When the server returns a dict **without** ``Items`` the helper must return an empty list."""

    fake_session = _FakeSession()
    api = EmbyAPI(None, host="h", api_key="k", session=fake_session)

    fake_session.queue(_FakeResp(json_data={"Something": "else"}))

    got = await api.search(search_term="foo")
    assert got == []


@pytest.mark.asyncio
async def test_get_item_not_found(monkeypatch):
    """404 from the server must be translated into *None* result by `get_item`."""

    fake_session = _FakeSession()

    # The internal _request helper will raise EmbyApiError -> should be swallowed by get_item.
    async def _boom(*_, **__):  # noqa: D401 – dummy
        raise EmbyApiError("404")

    api = EmbyAPI(None, host="h", api_key="k", session=fake_session)
    monkeypatch.setattr(api, "_request", _boom)  # type: ignore[attr-defined]

    res = await api.get_item("missing")
    assert res is None


@pytest.mark.asyncio
async def test_request_error_handling():
    """Low-level `_request` must translate network & HTTP errors to EmbyApiError."""

    fake_session = _FakeSession()
    api = EmbyAPI(None, host="h", api_key="k", session=fake_session)

    # 1. HTTP 500 response -> ClientResponseError -> EmbyApiError
    fake_session.queue(_FakeResp(status=500))
    with pytest.raises(EmbyApiError):
        await api._request("GET", "/test")  # pylint: disable=protected-access

    # 2. Underlying network error
    fake_session.queue(ClientError("boom"))
    with pytest.raises(EmbyApiError):
        await api._request("GET", "/test")  # pylint: disable=protected-access
