"""Unit tests for :pymeth:`custom_components.embymedia.api.EmbyAPI.get_item` cache (GitHub #139)."""

from __future__ import annotations

from types import SimpleNamespace

import asyncio

import pytest


class _DummySession:  # pragma: no cover – extremely small helper
    """Minimal *aiohttp* compatible stub – exposes only the *close* coroutine."""

    async def close(self):  # noqa: D401 – signature must match aiohttp
        return None


@pytest.mark.asyncio()
async def test_get_item_uses_in_memory_cache(monkeypatch):  # noqa: D401
    """Second *get_item* call for the same id must avoid a network hit."""

    # ------------------------------------------------------------------
    # Arrange – create *EmbyAPI* instance with patched *_request*
    # ------------------------------------------------------------------

    from custom_components.embymedia.api import EmbyAPI

    api = EmbyAPI(
        hass=None,
        host="emby.local",
        api_key="k",
        session=_DummySession(),
    )

    calls: list[tuple[str, str]] = []

    async def _fake_request(method: str, path: str, **_kwargs):  # noqa: D401, ANN001 – stub
        """Record call and return dummy JSON payload."""

        calls.append((method, path))
        # Minimal item payload – only *Id* attribute accessed by callers.
        return {"Id": "123", "Name": "Test"}

    # Patch the *bound* attribute – no self parameter expected.
    monkeypatch.setattr(api, "_request", _fake_request, raising=True)

    # ------------------------------------------------------------------
    # Act – call twice in quick succession
    # ------------------------------------------------------------------

    item1 = await api.get_item("123")
    item2 = await api.get_item("123")

    # ------------------------------------------------------------------
    # Assert – underlying HTTP request executed *once*; payload identical
    # ------------------------------------------------------------------

    assert len(calls) == 1
    assert item1 == item2 == {"Id": "123", "Name": "Test"}
