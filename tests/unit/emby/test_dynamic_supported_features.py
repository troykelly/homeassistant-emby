"""Unit tests for dynamic *supported_features* handling (GitHub issue #88)."""

from __future__ import annotations

from types import SimpleNamespace


import pytest


# ---------------------------------------------------------------------------
# Stub helpers – minimal replacements for external dependencies
# ---------------------------------------------------------------------------


class _Device(SimpleNamespace):
    """Light-weight stand-in replicating *pyemby.EmbyDevice* attributes."""

    def __init__(self, *, supports_remote_control: bool = True):  # noqa: D401 – keep helper minimal
        super().__init__(
            supports_remote_control=supports_remote_control,
            name="Bedroom",
            session_raw={},
            session_id="sess-xyz",
            unique_id="dev-xyz",
            media_position=None,
            is_nowplaying=False,
        )


# ---------------------------------------------------------------------------
# Fixture returning a bare-bones *EmbyDevice* instance wired with the stub
# ---------------------------------------------------------------------------


@pytest.fixture()
def emby_device():  # noqa: D401 – matches pattern of other unit tests
    """Return an *EmbyDevice* suitable for isolated feature tests."""

    from custom_components.embymedia.media_player import EmbyDevice, SUPPORT_EMBY

    dev = EmbyDevice.__new__(EmbyDevice)  # type: ignore[arg-type]

    # Wire required attributes manually – the constructor is bypassed to keep
    # the fixture lean and decoupled from unrelated initialisation code.
    dev.device = _Device()
    dev.device_id = "dev-xyz"
    dev.emby = SimpleNamespace(_host="h", _api_key="k", _port=8096, _ssl=False)

    # Stub *async_write_ha_state* to a no-op so the tests can run outside HA.
    dev.async_write_ha_state = lambda *_, **__: None  # type: ignore[assignment]

    # Explicitly call helper to compute initial mask as the real constructor
    # would normally do this step.
    dev._update_supported_features()  # type: ignore[attr-defined]

    # Verify pre-condition – remote control enabled yields full mask.
    assert dev.supported_features == SUPPORT_EMBY  # type: ignore[attr-defined]

    return dev


# ---------------------------------------------------------------------------
# Tests – runtime capability change handling
# ---------------------------------------------------------------------------


def test_supported_features_updates_on_capability_change(emby_device):  # noqa: D401
    """`supported_features` must adapt when *supports_remote_control* flips."""

    from custom_components.embymedia.media_player import MediaPlayerEntityFeature

    # 1. Disable remote control in the underlying _Device stub and trigger
    #    the websocket callback.  The helper should downgrade the feature
    #    mask to zero.
    emby_device.device.supports_remote_control = False

    emby_device.async_update_callback({})  # type: ignore[arg-type]

    assert emby_device.supported_features == MediaPlayerEntityFeature(0)

    # 2. Re-enable remote control – mask should switch back to full feature set.
    emby_device.device.supports_remote_control = True

    emby_device.async_update_callback({})  # type: ignore[arg-type]

    from custom_components.embymedia.media_player import SUPPORT_EMBY
    assert emby_device.supported_features == SUPPORT_EMBY

    assert emby_device.supported_features == SUPPORT_EMBY

    # ------------------------------------------------------------------
    # Additional explicit checks for new capability flags (issue #108)
    # ------------------------------------------------------------------

    # Verify that the extended feature mask now includes browse, search,
    # enqueue and announce capabilities when available in the running Core.

    optional_flags = [
        getattr(MediaPlayerEntityFeature, name, MediaPlayerEntityFeature(0))
        for name in (
            "BROWSE_MEDIA",
            "SEARCH_MEDIA",
            "MEDIA_ENQUEUE",
            "MEDIA_ANNOUNCE",
        )
    ]

    # All optional flags that exist in the current Home Assistant installation
    # must be set in the computed feature mask.
    for flag in optional_flags:
        if flag != MediaPlayerEntityFeature(0):
            assert emby_device.supported_features & flag == flag
