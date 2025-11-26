"""Fixtures for live Emby server tests.

These tests run against a real Emby server and require socket access.
Do NOT include pytest_plugins from parent conftest - these tests need real network access.
"""

from __future__ import annotations

import socket
from collections.abc import Generator

import pytest

# Restore original socket before any tests run
_original_socket = socket.socket


@pytest.fixture(scope="session", autouse=True)
def restore_socket() -> Generator[None]:
    """Restore original socket for live tests."""
    # Save current socket (may be patched)
    patched_socket = socket.socket
    # Restore original
    socket.socket = _original_socket
    yield
    # Put back the patched one for other tests
    socket.socket = patched_socket
