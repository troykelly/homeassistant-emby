"""Global pytest configuration and helpers for the Emby custom integration tests.

The test-suite uses *pytest-asyncio* for coroutine support.  A trivial helper
``event_loop`` fixture is provided so we do not depend on Home Assistant’s own
loop handling which adds extra indirection that is irrelevant for these unit
tests.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

import pytest

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


@pytest.fixture(scope="session")  # type: ignore[misc] – declared once for all tests
def event_loop() -> asyncio.AbstractEventLoop:  # noqa: D401 – pytest naming convention
    """Return an *asyncio* event-loop for the test-session.

    Pytest’s default behaviour creates a fresh loop per test-function when
    *pytest-asyncio* is installed.  Home Assistant’s helpers expect the loop
    to be reused, therefore we create a **single** session-scoped loop which
    mirrors HA’s runtime behaviour while still isolating the unit tests from
    the actual Home Assistant test harness.
    """

    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


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
