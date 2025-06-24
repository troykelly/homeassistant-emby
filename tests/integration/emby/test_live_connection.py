"""Live integration tests against the *real* Emby test server.

These tests exercise the *happy* and *error* connection paths of the minimal
``EmbyAPI`` wrapper using the **public test server** that ships with the
development environment.  The server details are provided through the
``EMBY_URL`` and ``EMBY_API_KEY`` environment variables which are injected by
the CI harness as well as the local *devcontainer* so developers can run the
suite offline.

The cases are intentionally narrow – they do **not** attempt to verify
functional behaviour beyond *connectivity* because media-library contents vary
between test environments.  Their sole purpose is to ensure that:

1.  A *correct* configuration (host, port, SSL) successfully establishes an
    authenticated connection (``GET /Sessions`` returns *any* JSON list).
2.  An *incorrect* configuration (same host but wrong port) fails with an
    :class:`~custom_components.embymedia.api.EmbyApiError` which is surfaced
    by the helper.

The tests are skipped automatically when the environment variables are not
set.  This keeps the default developer workflow fast and avoids network calls
in contexts where the live server is not reachable (e.g. forks without the
secret variables).
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

import pytest


# The helper under test --------------------------------------------------------

from custom_components.embymedia.api import EmbyAPI, EmbyApiError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_live_server_details():  # noqa: D401 – small internal utility
    """Return the (host, port, ssl, api_key) tuple from *env* – or *None*."""

    emby_url = os.getenv("EMBY_URL")
    api_key = os.getenv("EMBY_API_KEY")

    if not emby_url or not api_key:
        return None

    parsed = urlparse(emby_url)

    host = parsed.hostname or "localhost"
    port = parsed.port  # may be *None* → default (80/443) implied by scheme
    ssl_flag = parsed.scheme == "https"

    return host, port, ssl_flag, api_key


# ---------------------------------------------------------------------------
# Positive – correct configuration succeeds
# ---------------------------------------------------------------------------


import asyncio


@pytest.mark.asyncio
# Enable **real** network access for this test – the project wide *pytest-socket*
# plugin blocks all outgoing traffic by default to ensure unit tests remain
# hermetic.  The live connectivity checks necessarily require a TCP connection
# to the hosted Emby instance, therefore we opt-in explicitly.
@pytest.mark.enable_socket
async def test_connection_success():  # noqa: D401 – test name
    """Validate that a *correct* config connects and returns a JSON list."""

    details = _get_live_server_details()
    if details is None:
        pytest.skip("EMBY_URL / EMBY_API_KEY not set – live tests skipped.")

    host, port, ssl_flag, api_key = details

    # Ensure the *pytest-socket* restrictions are fully lifted for the network
    # call regardless of the global CLI flags the test-runner might set.
    # Import inline to avoid a hard dependency for callers outside the pytest
    # context (e.g. IDE run configs).
    import pytest_socket as _pysock  # type: ignore

    _pysock.enable_socket()
    # Allow the public test server host so the *allow-hosts* CLI restriction
    # (when present) does not reject the outbound TCP handshake.
    _pysock.socket_allow_hosts([host])

    api = EmbyAPI(None, host, api_key, ssl=ssl_flag, port=port)

    # Wrap the call in a short timeout so the test suite does not hang when the
    # external service is temporarily unreachable.
    sessions = await asyncio.wait_for(api.get_sessions(force_refresh=True), timeout=10)

    # The endpoint must return *some* JSON list (can be empty)
    assert isinstance(sessions, list)


# ---------------------------------------------------------------------------
# Negative – wrong port must raise *EmbyApiError*
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Negative – wrong port must raise *EmbyApiError*
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
# The negative test requires *socket* access as well because the helper must
# attempt the (failing) TCP handshake in order to raise the appropriate error
# type.
@pytest.mark.enable_socket
async def test_connection_failure_wrong_port():  # noqa: D401 – test name
    """Ensure that an *incorrect* port triggers a connection error."""

    details = _get_live_server_details()
    if details is None:
        pytest.skip("EMBY_URL / EMBY_API_KEY not set – live tests skipped.")

    host, port, ssl_flag, api_key = details

    # Pick a *likely closed* port to trigger failure deterministically.  When
    # the live server runs on 443 we use 444, otherwise we add +1 to the
    # detected port.  As a last resort fall back to 65535 which is almost
    # guaranteed to be closed.
    wrong_port: int
    if port is None:
        wrong_port = 444 if ssl_flag else 65535
    else:
        wrong_port = port + 1 if port < 65534 else port - 1

    import pytest_socket as _pysock  # type: ignore

    _pysock.enable_socket()
    _pysock.socket_allow_hosts([host])

    api = EmbyAPI(None, host, api_key, ssl=ssl_flag, port=wrong_port)

    with pytest.raises(EmbyApiError):
        await asyncio.wait_for(api.get_sessions(force_refresh=True), timeout=10)
