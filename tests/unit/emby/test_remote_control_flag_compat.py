"""Regression tests for remote control flag detection (GitHub issue #225)."""

from __future__ import annotations

from types import SimpleNamespace


import pytest


# ---------------------------------------------------------------------------
# Helper – minimal *pyemby* device stand-in
# ---------------------------------------------------------------------------


class _StubDevice(SimpleNamespace):
    """Light-weight replacement emulating the attributes accessed by the code."""

    def __init__(
        self,
        *,
        supports_remote_control: object | None = None,
        session_raw: dict | None = None,
    ) -> None:  # noqa: D401 – simple stub
        super().__init__(
            # *supports_remote_control* intentionally allows **None** so the
            # attribute may be *missing* in the final instance when we delete
            # it further below.
            supports_remote_control=supports_remote_control,
            session_raw=session_raw or {},
            name="Living-room",
            session_id="sess-abc",
            unique_id="dev-abc",
            media_position=None,
            is_nowplaying=False,
        )


# ---------------------------------------------------------------------------
# Fixture – returns *EmbyDevice* wired with the provided stub
# ---------------------------------------------------------------------------


@pytest.fixture()
def make_emby_device():  # noqa: D401 – factory fixture
    """Factory that constructs an *EmbyDevice* around a supplied stub."""

    from custom_components.embymedia.media_player import EmbyDevice

    def _factory(stub: _StubDevice):
        dev = EmbyDevice.__new__(EmbyDevice)  # type: ignore[arg-type]

        dev.device = stub
        dev.device_id = stub.unique_id
        dev.emby = SimpleNamespace(_host="h", _api_key="k", _port=8096, _ssl=False)

        # Stub HA runtime helper to a no-op.
        dev.async_write_ha_state = lambda *_, **__: None  # type: ignore[assignment]

        dev._update_supported_features()  # type: ignore[attr-defined]

        return dev

    return _factory


# ---------------------------------------------------------------------------
# Tests – legacy flat flag and new nested permission structure
# ---------------------------------------------------------------------------


def _assert_mask(dev, expected_enabled: bool):  # noqa: D401 – helper
    """Assert that *supported_features* reflect *expected_enabled*."""

    from custom_components.embymedia.media_player import MediaPlayerEntityFeature, SUPPORT_EMBY

    if expected_enabled:
        assert dev.supported_features == SUPPORT_EMBY  # type: ignore[attr-defined]
    else:
        assert dev.supported_features == MediaPlayerEntityFeature(0)


def test_flat_supports_remote_control_flag(make_emby_device):  # noqa: D401
    """Old Emby payload exposes flat *SupportsRemoteControl* field."""

    stub = _StubDevice(
        supports_remote_control=None,  # attribute present but *None*
        session_raw={"SupportsRemoteControl": True},
    )

    # Remove attribute entirely to emulate missing field in newer pyemby.
    delattr(stub, "supports_remote_control")

    dev = make_emby_device(stub)

    _assert_mask(dev, expected_enabled=True)


def test_nested_has_permission_flag(make_emby_device):  # noqa: D401
    """New Emby payload nests flag under *HasPermission.RemoteControl*."""

    stub = _StubDevice(
        supports_remote_control=None,
        session_raw={"HasPermission": {"RemoteControl": True}},
    )

    # Ensure legacy attribute is missing.
    delattr(stub, "supports_remote_control")

    dev = make_emby_device(stub)

    _assert_mask(dev, expected_enabled=True)


def test_no_remote_control_permission(make_emby_device):  # noqa: D401
    """When neither flag is present the feature mask must be 0."""

    stub = _StubDevice(
        supports_remote_control=None,
        session_raw={},
    )

    delattr(stub, "supports_remote_control")

    dev = make_emby_device(stub)

    _assert_mask(dev, expected_enabled=False)
