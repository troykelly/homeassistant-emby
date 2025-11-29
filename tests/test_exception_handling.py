"""Tests for refined exception handling (Phase 22).

These tests verify that specific exception types are caught instead of broad
Exception catches.
"""

from __future__ import annotations

import ast
import inspect
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass


def _get_exception_names(node: ast.ExceptHandler) -> list[str]:
    """Extract exception type names from an ExceptHandler node."""
    if node.type is None:
        return []

    if isinstance(node.type, ast.Name):
        return [node.type.id]

    if isinstance(node.type, ast.Tuple):
        names: list[str] = []
        for elt in node.type.elts:
            if isinstance(elt, ast.Name):
                names.append(elt.id)
            elif isinstance(elt, ast.Attribute):
                names.append(elt.attr)
        return names

    if isinstance(node.type, ast.Attribute):
        return [node.type.attr]

    return []


def _module_has_exception_type(module_name: str, exception_names: set[str]) -> bool:
    """Check if module catches any of the specified exception types."""
    import importlib

    module = importlib.import_module(module_name)
    source = inspect.getsource(module)
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        caught_names = _get_exception_names(node)
        if any(name in exception_names for name in caught_names):
            return True
    return False


def _module_has_bare_exception(module_name: str) -> bool:
    """Check if module uses bare 'except Exception:' patterns."""
    import importlib

    module = importlib.import_module(module_name)
    source = inspect.getsource(module)
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        caught_names = _get_exception_names(node)
        if "Exception" in caught_names:
            return True
    return False


class TestExceptionHandlingRefinement:
    """Tests verifying exception handling uses specific types."""

    def test_init_discovery_coordinator_catches_emby_error(self) -> None:
        """Test __init__.py catches EmbyError for discovery coordinator setup."""
        assert _module_has_exception_type(
            "custom_components.embymedia",
            {"EmbyError"},
        ), (
            "__init__.py should catch EmbyError instead of broad Exception "
            "for discovery coordinator setup"
        )

    def test_init_websocket_catches_specific_exceptions(self) -> None:
        """Test __init__.py catches specific exceptions for WebSocket setup."""
        assert _module_has_exception_type(
            "custom_components.embymedia",
            {"EmbyWebSocketError", "OSError"},
        ), (
            "__init__.py should catch specific exceptions (EmbyWebSocketError, OSError) "
            "instead of broad Exception for WebSocket setup"
        )

    def test_remote_catches_specific_exceptions(self) -> None:
        """Test remote.py catches specific exceptions for command sending."""
        assert _module_has_exception_type(
            "custom_components.embymedia.remote",
            {"EmbyError", "ClientError", "OSError"},
        ), (
            "remote.py should catch specific exceptions (EmbyError, ClientError) "
            "instead of broad Exception for command sending"
        )

    def test_image_discovery_catches_network_exceptions(self) -> None:
        """Test image_discovery.py catches specific network exceptions."""
        assert _module_has_exception_type(
            "custom_components.embymedia.image_discovery",
            {"ClientError", "OSError", "TimeoutError"},
        ), (
            "image_discovery.py should catch specific exceptions "
            "(ClientError, OSError, TimeoutError) instead of broad Exception"
        )


class TestNoBroadExceptionCatches:
    """Tests verifying no bare 'except Exception:' patterns remain in key files."""

    @pytest.mark.parametrize(
        "module_name",
        [
            "custom_components.embymedia",
            "custom_components.embymedia.remote",
            "custom_components.embymedia.image_discovery",
        ],
    )
    def test_no_bare_except_exception(self, module_name: str) -> None:
        """Verify module doesn't use bare 'except Exception:' patterns."""
        assert not _module_has_bare_exception(module_name), (
            f"{module_name} should not use bare 'except Exception:' patterns. "
            "Use specific exception types instead."
        )
