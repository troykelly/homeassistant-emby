"""Regression tests for remote control permission detection (issue #226).

These tests exercise the internal helper responsible for translating Emby
`Session` payloads into Home Assistant *supported_features* bit-masks.  They
cover *all* known payload shapes so that future upstream changes cannot hide
from CI again.
"""

from __future__ import annotations

from types import SimpleNamespace


# ---------------------------------------------------------------------------
# Local lightweight *pyemby.EmbyDevice* stand-in
# ---------------------------------------------------------------------------


class _Device(SimpleNamespace):  # noqa: D401 – minimal stub
    """Stub replicating the relevant public attributes of *pyemby.EmbyDevice*."""

    def __init__(self, session_raw: dict[str, object]):
        # NOTE: *supports_remote_control* **must not** be present on this stub.
        # The attribute disappeared in Emby ≥4.9 and the goal of these tests
        # is to ensure the integration copes with its absence.
        super().__init__(
            name="Living room",
            session_raw=session_raw,
            session_id="sess-abc",
            unique_id="dev-abc",
            media_position=None,
            is_nowplaying=False,
        )


# ---------------------------------------------------------------------------
# Small helper returning a fully wired *EmbyDevice* instance
# ---------------------------------------------------------------------------


def _make_emby_device(session_raw: dict[str, object]):
    """Return an *EmbyDevice* initialised with the provided *session_raw*."""

    from custom_components.embymedia.media_player import EmbyDevice

    dev = EmbyDevice.__new__(EmbyDevice)  # type: ignore[arg-type]

    dev.device = _Device(session_raw=session_raw)
    dev.device_id = "dev-abc"
    # minimal *EmbyServer* stub – only attributes accessed by the code under
    # test are required, therefore use an in-memory namespace.
    dev.emby = SimpleNamespace(_host="h", _api_key="k", _port=8096, _ssl=False)

    # suppress Home Assistant side-effects
    dev.async_write_ha_state = lambda *_, **__: None  # type: ignore[assignment]

    # compute initial mask just like the real constructor would
    dev._update_supported_features()  # type: ignore[attr-defined]

    return dev


# ---------------------------------------------------------------------------
# Tests – legacy vs. new payload shapes
# ---------------------------------------------------------------------------


def test_legacy_flat_flag_restores_full_feature_mask():  # noqa: D401
    """Flat *SupportsRemoteControl* → full feature mask expected."""

    from custom_components.embymedia.media_player import SUPPORT_EMBY

    dev = _make_emby_device({"SupportsRemoteControl": True})

    assert dev.supported_features == SUPPORT_EMBY


def test_nested_permission_flag_restores_full_feature_mask():  # noqa: D401
    """Nested *HasPermission.RemoteControl* → full feature mask expected."""

    from custom_components.embymedia.media_player import SUPPORT_EMBY

    dev = _make_emby_device({"HasPermission": {"RemoteControl": True}})

    assert dev.supported_features == SUPPORT_EMBY


def test_absent_permission_drops_all_features():  # noqa: D401
    """Missing permission flag → no media player features exposed."""

    from custom_components.embymedia.media_player import MediaPlayerEntityFeature

    dev = _make_emby_device({})

    assert dev.supported_features == MediaPlayerEntityFeature(0)
