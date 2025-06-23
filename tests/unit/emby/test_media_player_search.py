"""Unit tests for *EmbyDevice.async_search_media* (issue #74)."""

from __future__ import annotations

from types import SimpleNamespace

from typing import Any, List

import pytest


# ---------------------------------------------------------------------------
# Helper stubs mimicking the minimal public surface needed for the tests
# ---------------------------------------------------------------------------


class _StubAPI:  # pylint: disable=too-few-public-methods
    """Fake replacement for :class:`custom_components.embymedia.api.EmbyAPI`."""

    def __init__(self) -> None:  # noqa: D401 – simple container
        self._search_response: Any | Exception = []
        self.search_calls: List[dict[str, Any]] = []

    async def search(
        self,
        *,
        search_term: str,
        item_types: list[str] | None = None,
        user_id: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:  # noqa: D401 – match signature
        self.search_calls.append(
            {
                "search_term": search_term,
                "item_types": item_types,
                "user_id": user_id,
                "limit": limit,
            }
        )

        if isinstance(self._search_response, Exception):
            raise self._search_response  # pragma: no cover – error path

        return self._search_response  # type: ignore[return-value]

    async def get_sessions(self, *, force_refresh: bool = False):  # noqa: D401 – used by helper
        return [
            {
                "Id": "sess-123",
                "DeviceId": "dev1",
                "UserId": "user-1",
            }
        ]


class _Device(SimpleNamespace):
    """Replica of the lightweight pyemby device used by *EmbyDevice*."""

    def __init__(self):  # noqa: D401 – keep inline for brevity
        super().__init__(
            supports_remote_control=True,
            name="Living Room",
            state="Playing",
            username="john",
            session_id="sess-123",
            unique_id="dev1",
            # ``session_raw`` included so the code can extract the UserId.
            session_raw={"UserId": "user-1"},
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def emby_device(monkeypatch):  # noqa: D401 – pytest naming convention
    """Return an *EmbyDevice* wired with fake dependencies suitable for unit-tests."""

    from custom_components.embymedia.media_player import EmbyDevice

    dev = EmbyDevice.__new__(EmbyDevice)  # type: ignore[arg-type]

    # Minimal internal attributes expected by the class ------------------
    stub_device = _Device()
    dev.device = stub_device
    dev.device_id = "dev1"
    dev.emby = SimpleNamespace(_host="h", _api_key="k", _port=8096, _ssl=False)
    dev.hass = None  # not required for these unit-tests  # pyright: ignore[reportAttributeAccessIssue]

    # Entity helper patched so *async_write_ha_state* does not require HA core
    dev.async_write_ha_state = lambda *_, **__: None  # type: ignore[assignment]

    # Patch *EmbyAPI* helper --------------------------------------------
    api_stub = _StubAPI()
    monkeypatch.setattr(dev, "_get_emby_api", lambda self=dev: api_stub)  # type: ignore[arg-type]

    # _resolve_session_id not used by async_search_media – no patch needed.

    return dev


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_search_media_success(emby_device):  # noqa: D401 – pytest style naming
    """Happy-path – returns a SearchMedia object with one BrowseMedia child."""

    from homeassistant.components.media_player import MediaType, SearchMediaQuery

    # Arrange -----------------------------------------------------------
    api_stub: _StubAPI = emby_device._get_emby_api()  # type: ignore[attr-defined]
    api_stub._search_response = [
        {"Id": "item-1", "Name": "The Matrix", "Type": "Movie"},
    ]

    # Act ---------------------------------------------------------------
    query = SearchMediaQuery(
        search_query="The Matrix",
        media_content_type=MediaType.MOVIE,
    )

    result = await emby_device.async_search_media(query)

    # Assert ------------------------------------------------------------
    assert result.result  # non-empty
    assert len(result.result) == 1
    node = result.result[0]
    assert node.title == "The Matrix"

    # Verify correct filter mapping was applied (Movie)
    assert api_stub.search_calls[0]["item_types"] == ["Movie"]


@pytest.mark.asyncio
async def test_async_search_media_not_found(emby_device):  # noqa: D401
    """When no results are returned a *HomeAssistantError* must be raised."""

    from homeassistant.components.media_player import MediaType, SearchMediaQuery
    from homeassistant.exceptions import HomeAssistantError

    api_stub: _StubAPI = emby_device._get_emby_api()  # type: ignore[attr-defined]
    api_stub._search_response = []  # nothing found

    query = SearchMediaQuery(search_query="Unknown", media_content_type=MediaType.MOVIE)

    with pytest.raises(HomeAssistantError):
        await emby_device.async_search_media(query)

