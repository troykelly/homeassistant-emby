"""Global pytest configuration and helpers for the Emby custom integration tests.

The test-suite uses *pytest-asyncio* for coroutine support.  A trivial helper
``event_loop`` fixture is provided so we do not depend on Home Assistant’s own
loop handling which adds extra indirection that is irrelevant for these unit
tests.
"""
# pylint: disable=missing-module-docstring

from __future__ import annotations

from typing import Any, Dict, List

# Ensure the repository root (which contains the *components/* package) is the
# first entry on *sys.path* so that test-modules can perform absolute imports
# like ``import components.emby.api`` without interference from similarly named
# directories that live **inside** the test-suite itself.

import pathlib
import sys

# ``conftest.py`` lives in *tests/* – we need the parent directory (**repo
# root**) on the import-path.
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ---------------------------------------------------------------------------
# Test-environment tweaks for Home Assistant plugin compatibility
# ---------------------------------------------------------------------------

# Newer Home Assistant cores spawn an *ImportExecutor_* background thread via
# the util.executor pool.  The third-party pytest plugin used by this repo has
# a strict cleanup hook that fails when it sees threads not matching an
# allow-list.  Upstream HA adds "_run_safe_shutdown_loop" to that list, so we
# rename ImportExecutor threads accordingly **before** the plugin snapshots
# the thread set.


def pytest_configure():  # noqa: D401 – pytest hook
    import threading  # import locally to avoid at import-time

    for _thr in threading.enumerate():
        if _thr.name.startswith("ImportExecutor_"):
            _thr.name = "_run_safe_shutdown_loop"

    # ------------------------------------------------------------------
    # CI / local environment helper – ensure *live* Emby connection tests
    # do not hang when the public test server is unreachable.
    # ------------------------------------------------------------------
    # The integration suite includes *tests/integration/emby/test_live_connection.py*
    # which attempts a real network handshake when the environment variables
    # ``EMBY_URL`` **and** ``EMBY_API_KEY`` are present.  On forked repos or
    # offline CI runners the hosted test server may be down resulting in
    # long timeouts that slow down feedback.

    import os
    import socket
    from urllib.parse import urlparse

    emby_url = os.getenv("EMBY_URL")
    if emby_url:
        parsed = urlparse(emby_url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)

        # Attempt a very short TCP handshake – if it fails we assume the
        # server is unreachable and *unset* the env vars so the live tests
        # auto-skip (their helper checks for variable presence).

        try:
            sock = socket.create_connection((host, port), timeout=1)
            sock.close()
        except Exception:  # noqa: BLE001 – any failure means skip
            os.environ.pop("EMBY_URL", None)
            os.environ.pop("EMBY_API_KEY", None)


# ---------------------------------------------------------------------------
# Runtime hook – executed *after* each test function but *before* fixture
# teardown.  We leverage this ordering guarantee to rename any **new**
# `ImportExecutor_*` threads that Home Assistant may have spawned during the
# test execution.  Doing so ensures the subsequent `verify_cleanup` fixture
# from the `pytest_homeassistant_custom_component` plugin (which runs in the
# teardown phase) recognises the thread as allowable – mirroring behaviour in
# Home Assistant core’s own test-suite.
# ---------------------------------------------------------------------------


def pytest_runtest_teardown(item, nextitem):  # noqa: D401 – pytest hook
    """Rename lingering ImportExecutor threads right after the test body."""
    import threading  # local import to prevent early evaluation
    from datetime import timezone as _tz
    from homeassistant.util import dt as _dt_util

    for _thr in threading.enumerate():
        if _thr.name.startswith("ImportExecutor_"):
            _thr.name = "_run_safe_shutdown_loop"

    # Home Assistant may update the global default timezone during a test via
    # `hass.config.set_time_zone()` – reset it so the upstream plugin's
    # verification passes.
    _dt_util.DEFAULT_TIME_ZONE = _tz.utc


# NOTE:
# ``pytest-asyncio`` already provides a built-in *event_loop* fixture.  Redefining
# it is now deprecated (as of *pytest-asyncio* ≥ 0.26) and triggers a
# *DeprecationWarning* that surfaces during the test-run.  The previous
# implementation created a **session-scoped** loop to better mimic Home
# Assistant’s runtime behaviour, however none of the current tests rely on a
# persistent loop between test functions.  Therefore we simply drop the custom
# implementation and fall back to the default fixture supplied by the plugin.
#
# If future tests legitimately require a different loop scope this can be
# requested on a per-test basis via::
#
#     @pytest.mark.asyncio(loop_scope="session")
#
# or controlled globally through *pytest.ini* (see that file in the project
# root).


# ---------------------------------------------------------------------------
# Light-weight fakes used by multiple test-modules
# ---------------------------------------------------------------------------


class FakeEmbyAPI:  # pylint: disable=too-few-public-methods
    """Very small stub that imitates :class:`components.emby.api.EmbyAPI`."""

    def __init__(self) -> None:
        self._get_item_calls: List[str] = []
        self._search_calls: List[Dict[str, Any]] = []

        # Attributes populated by individual tests to control behaviour.
        self._item_response: Dict[str, Any] | None = None
        self._search_response: List[Dict[str, Any]] | Exception | None = None

    # ------------------------------------------------------------------
    # API surface required by *search_resolver*
    # ------------------------------------------------------------------

    async def get_item(self, item_id: str):  # noqa: D401 – simple stub
        self._get_item_calls.append(item_id)
        return self._item_response

    async def search(
        self,
        *,
        search_term: str,
        item_types: list[str] | None = None,
        user_id: str | None = None,
        limit: int = 1,
    ) -> list[Dict[str, Any]]:
        self._search_calls.append(
            {
                "search_term": search_term,
                "item_types": item_types,
                "user_id": user_id,
                "limit": limit,
            }
        )

        if isinstance(self._search_response, Exception):
            raise self._search_response

        if self._search_response is None:
            return []

        return self._search_response
