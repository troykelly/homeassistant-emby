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
