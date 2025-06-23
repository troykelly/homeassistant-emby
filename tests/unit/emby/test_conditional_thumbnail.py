"""Unit-tests for conditional thumbnail proxying (GitHub issue #122)."""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Re-usable EmbyDevice stub mirroring helpers from other test modules
# ---------------------------------------------------------------------------


def _make_emby_device(monkeypatch):  # noqa: D401 – local helper
    """Return a minimal *EmbyDevice* instance suitable for unit-testing."""

    from custom_components.embymedia.media_player import EmbyDevice

    dev: EmbyDevice = EmbyDevice.__new__(EmbyDevice)  # type: ignore[arg-type]

    class _StubAPI:  # pylint: disable=too-few-public-methods
        def __init__(self):  # noqa: D401 – trivial init
            self._base = "https://emby.example.com"  # pylint: disable=invalid-name

    # Inject *EmbyAPI* helper stub so URL construction works without network.
    monkeypatch.setattr(dev, "_get_emby_api", lambda _self=dev: _StubAPI())  # type: ignore[arg-type]

    # Provide dummy HASS object – the conditional helper only passes it
    # through to *is_internal_request* and never dereferences attributes.
    dev.hass = object()  # type: ignore[assignment]

    return dev


# ---------------------------------------------------------------------------
# Behaviour tests
# ---------------------------------------------------------------------------


def test_thumbnail_internal_request(monkeypatch):  # noqa: D401
    """Local/internal requests should receive the *direct* Emby URL."""

    dev = _make_emby_device(monkeypatch)

    # Simulate internal request context
    monkeypatch.setattr(
        "homeassistant.helpers.network.is_internal_request",
        lambda _hass: True,
    )

    url = dev._thumbnail_url("abc")  # type: ignore[attr-defined]

    assert url == "https://emby.example.com/Items/abc/Images/Primary?maxWidth=500"


def test_thumbnail_external_request(monkeypatch):  # noqa: D401
    """External requests must be proxied through Home Assistant."""

    dev = _make_emby_device(monkeypatch)

    # Simulate external request context
    monkeypatch.setattr(
        "homeassistant.helpers.network.is_internal_request",
        lambda _hass: False,
    )

    # Patch *get_browse_image_url* so the helper can construct a predictable
    # proxy string without requiring a fully-initialised entity/hass setup.
    monkeypatch.setattr(dev, "get_browse_image_url", lambda *_: "proxy://abc")  # type: ignore[arg-type]

    url = dev._thumbnail_url("abc")  # type: ignore[attr-defined]

    assert url == "proxy://abc"
