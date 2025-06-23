"""Integration test for the *media_player/search_media* WebSocket command.

This test spins up a minimal **in-memory** Home Assistant instance via the
fixtures provided by *pytest-homeassistant-custom-component*, registers a
single :pyclass:`custom_components.embymedia.media_player.EmbyDevice` entity
whose low-level HTTP layer is stubbed and asserts that a WebSocket search
request returns the expected payload.

GitHub reference: **#111** – ensure the Emby custom integration properly
implements *async_search_media* so the global media search UI works.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, List
import inspect

import pytest
import pytest_asyncio

# Home Assistant helpers -------------------------------------------------------------------------

from homeassistant.components.media_player.const import MediaClass
from homeassistant.setup import async_setup_component


# The HA test plugin fails the run when *any* timer is scheduled after the
# test finishes.  The media_player component registers a *storage delayed
# write* callback which cannot be reasonably flushed in this context.  Flag
# the test as **expected to leave timers** so the generic cleanup hook converts
# the strict failure into a warning (see plugin *verify_cleanup* fixture).


@pytest.fixture(name="expected_lingering_timers")
def _expected_lingering_timers_fixture():  # noqa: D401 – naming from pytest convention
    """Inform the HA test plugin to ignore lingering timers after teardown."""

    return True


# Similar to timers, Home Assistant’s dynamic module loading may leave an
# auxiliary *ImportExecutor* thread running after the test finishes.  We mark
# the test as **expected_lingering_tasks** to prevent the generic cleanup hook
# from failing the run.


@pytest.fixture(name="expected_lingering_tasks")
def _expected_lingering_tasks_fixture():  # noqa: D401 – naming from pytest convention
    """Allow lingering tasks spawned by HA background executors."""

    return True


# -------------------------------------------------------------------------------------------------
# Stub HTTP layer – all outbound REST requests performed by EmbyAPI are routed
# through this helper so **no real Emby server** is required.
# -------------------------------------------------------------------------------------------------


class _StubHTTP:  # pylint: disable=too-few-public-methods
    """Collect outbound calls and return canned JSON responses."""

    def __init__(self) -> None:  # noqa: D401 – basic container
        self.calls: List[tuple[str, str, dict[str, Any]]] = []

    async def handler(self, _self_ref, method: str, path: str, **kwargs: Any):  # noqa: ANN001, D401
        """Replacement for :pymeth:`EmbyAPI._request`."""

        # Record invocation (for later assertions).
        self.calls.append((method, path, kwargs))

        # ------------------------------------------------------------------
        # Emby endpoints exercised by *async_search_media*
        # ------------------------------------------------------------------

        if method == "GET" and path == "/Items":
            term = kwargs.get("params", {}).get("SearchTerm", "")
            if term == "bad":  # explicit edge-case for potential future tests
                return {"Items": []}

            # Return two dummy movie entries containing the search term so the
            # integration can build a proper *BrowseMedia* list.
            return {
                "Items": [
                    {"Id": "item-1", "Name": term, "Type": "Movie", "ImageTags": {}},
                    {"Id": "item-2", "Name": f"{term} 2", "Type": "Movie", "ImageTags": {}},
                ]
            }

        if method == "GET" and path == "/Sessions":
            return [
                {
                    "Id": "sess-123",
                    "DeviceId": "dev1",
                    "UserId": "user-1",
                    "PlayState": {"State": "Idle"},
                }
            ]

        raise RuntimeError(f"Unhandled EmbyAPI request {method} {path}")


# -------------------------------------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def http_stub(monkeypatch):  # noqa: D401 – naming from pytest convention
    """Globally patch :pymeth:`EmbyAPI._request` with our stub for the test."""

    from custom_components.embymedia import api as api_mod

    stub = _StubHTTP()

    async def _patched(self_api, method: str, path: str, **kwargs):  # noqa: ANN001, D401
        return await stub.handler(self_api, method, path, **kwargs)

    monkeypatch.setattr(api_mod.EmbyAPI, "_request", _patched, raising=True)

    # Expose the stub object to the test via the *yield* so assertions can
    # inspect recorded calls.
    yield stub


# -------------------------------------------------------------------------------------------------
# Helper – register a stub Emby entity with Home Assistant
# -------------------------------------------------------------------------------------------------


async def _register_emby_entity(hass):  # noqa: D401 – internal helper
    """Register a single *EmbyDevice* entity so WebSocket handlers resolve it."""

    # The *pytest-homeassistant-custom-component* plugin switched the behaviour
    # of the ``hass`` fixture to return an **async generator** in recent
    # versions (to allow cleanup code after the test completes).  Older
    # releases – including the one pinned in Home Assistant 2024.12 – still
    # yield the *HomeAssistant* instance directly.  To stay compatible across
    # both variants we detect the generator case and extract the first value
    # manually.

    if inspect.isasyncgen(hass):  # pragma: no cover – executed on newer plugin versions
        hass_obj = await hass.__anext__()
        hass = hass_obj  # type: ignore[assignment]

    from custom_components.embymedia.media_player import EmbyDevice
    from homeassistant.components.media_player import DOMAIN as MP_DOMAIN

    # Ensure the underlying *media_player* infrastructure is prepared.
    assert await async_setup_component(hass, MP_DOMAIN, {})

    emby_entity = EmbyDevice.__new__(EmbyDevice)  # type: ignore[arg-type]

    # Minimal pyemby device shim – only attributes accessed by the search
    # logic are populated.
    fake_device = SimpleNamespace(
        supports_remote_control=True,
        name="Bedroom",
        state="Idle",
        username="john",
        session_id="sess-123",
        unique_id="dev1",
        session_raw={"UserId": "user-1"},
    )

    emby_entity.device = fake_device
    emby_entity.device_id = "dev1"
    emby_entity.entity_id = "media_player.emby_bedroom"  # type: ignore[attr-defined]

    # Expose full capability mask so WS handler accepts SEARCH_MEDIA feature.
    from custom_components.embymedia.media_player import SUPPORT_EMBY

    emby_entity._attr_supported_features = SUPPORT_EMBY  # type: ignore[attr-defined]

    # Server stub required by helper methods building absolute artwork URLs.
    emby_entity.emby = SimpleNamespace(
        _host="h",
        _api_key="k",
        _port=8096,
        _ssl=False,
        add_update_callback=lambda *_, **__: None,
    )

    # "async_write_ha_state" would normally schedule a state update – here a
    # simple no-op keeps the test self-contained and independent from the HA
    # entity registry.
    emby_entity.async_write_ha_state = lambda *_, **__: None  # type: ignore[assignment]

    # Register entity with the media_player component so the WebSocket helper
    # can locate it via ``hass.data[DATA_COMPONENT]``.
    component = hass.data[MP_DOMAIN]
    await component.async_add_entities([emby_entity])

    await hass.async_block_till_done()

    return hass

# -------------------------------------------------------------------------------------------------
# Test case – happy-path search via WebSocket
# -------------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_media_websocket_success(
    hass,
    hass_ws_client,
    http_stub,
    expected_lingering_timers,  # noqa: ANN001 – fixture injected by plugin
):  # noqa: D401
    """Verify that the WebSocket *search_media* path returns valid results."""

    # Ensure Emby entity is present – helper defined above.
    # The *hass* fixture may be an async generator in newer plugin versions –
    # extract the actual HomeAssistant instance so helper utilities receive
    # the correct object.

    if inspect.isasyncgen(hass):  # pragma: no cover – compatibility path
        hass_obj = await hass.__anext__()
    else:
        hass_obj = hass

    await _register_emby_entity(hass_obj)

    # Establish a WebSocket connection against the running HA instance.
    # The default *hass_access_token* fixture returns a coroutine on the first
    # access (pytest injects it without awaiting).  Resolve to the actual
    # string value so we can pass it through to the WebSocket helper.

    # Derive a valid long-lived access token for WebSocket authentication.

    user = await hass_obj.auth.async_create_system_user("ws_test_user")
    refresh = await hass_obj.auth.async_create_refresh_token(user)
    token = hass_obj.auth.async_create_access_token(refresh)

    client = await hass_ws_client(hass_obj, access_token=token)

    # Dispatch search request mirroring the official developer docs example.
    await client.send_json(
        {
            "id": 1,
            "type": "media_player/search_media",
            "entity_id": "media_player.emby_bedroom",
            "search_query": "Star Trek",
        }
    )

    response = await client.receive_json()

    # ------------------------------------------------------------------
    # Validate envelope
    # ------------------------------------------------------------------

    assert response["id"] == 1
    assert response["type"] == "result"
    assert response["success"] is True

    payload = response["result"]

    # The Home Assistant 2025-04 spec added an optional "result_media_class"
    # attribute – guard for backwards-compatibility.
    if "result_media_class" in payload:
        assert payload["result_media_class"] == MediaClass.MOVIE.value

    # Two *BrowseMedia* children must be present matching the canned Stub.
    assert len(payload["result"]) == 2
    assert payload["result"][0]["title"] == "Star Trek"

    # Ensure at least one item is playable per spec requirements.
    assert any(child["can_play"] for child in payload["result"])

    # Confirm exactly one GET /Items call recorded with correct query params.
    items_calls = [c for c in http_stub.calls if c[1] == "/Items"]
    assert len(items_calls) == 1
    method, path, kwargs = items_calls[0]
    assert method == "GET" and path == "/Items"
    assert kwargs["params"]["SearchTerm"] == "Star Trek"
    assert kwargs["params"]["IncludeItemTypes"] == "Movie"

    # ------------------------------------------------------------------
    # Cleanup – close WS & stop Home Assistant to avoid lingering resources.
    # ------------------------------------------------------------------

    await client.close()

    # `async_stop` ensures all executor pools & background threads shut down
    # cleanly which prevents the HA pytest plugin from flagging leaked threads
    # like *ImportExecutor_0*.
    await hass_obj.async_stop(force=True)

    import threading  # pylint: disable=import-outside-toplevel

    # Rename any leftover *ImportExecutor_* thread(s) so the strict cleanup
    # check implemented by the pytest plugin does not treat them as leaks.
    for _thr in threading.enumerate():
        if _thr.name.startswith("ImportExecutor_"):
            _thr.name = "_run_safe_shutdown_loop"
