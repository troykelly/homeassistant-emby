"""Unit-tests for :pyfunc:`EmbyDevice.async_get_browse_image` (GitHub #109)."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Re-usable *EmbyDevice* stub
# ---------------------------------------------------------------------------


def _make_emby_device(monkeypatch):  # noqa: D401 – local helper
    """Return an *EmbyDevice* instance wired with stub helpers."""

    from custom_components.embymedia.media_player import EmbyDevice

    dev: EmbyDevice = EmbyDevice.__new__(EmbyDevice)  # type: ignore[arg-type]

    class _StubAPI:  # pylint: disable=too-few-public-methods
        """Expose the single attribute used by the thumbnail helper."""

        def __init__(self):
            self._base = "https://emby.example.com"  # pylint: disable=invalid-name

    monkeypatch.setattr(dev, "_get_emby_api", lambda _self=dev: _StubAPI())  # type: ignore[arg-type]

    return dev


# ---------------------------------------------------------------------------
# Happy-path – Emby returns bytes & mime-type
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_async_get_browse_image_ok(monkeypatch):  # noqa: D401
    dev = _make_emby_device(monkeypatch)

    expected_url = "https://emby.example.com/Items/xyz/Images/Primary?maxWidth=500"

    async def _fake_fetch(url):  # noqa: D401
        # Caller must hit the exact URL so Home Assistant can leverage cache
        # look-ups – regression guard.
        assert url == expected_url
        return b"img-bytes", "image/jpeg"

    monkeypatch.setattr(dev, "_async_fetch_image", _fake_fetch)

    img_bytes, mime_type = await dev.async_get_browse_image("movie", "xyz")

    assert img_bytes == b"img-bytes" and mime_type == "image/jpeg"


# ---------------------------------------------------------------------------
# Error path – Emby returns HTTP 404 → *HomeAssistantError*
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_async_get_browse_image_error(monkeypatch):  # noqa: D401
    from homeassistant.exceptions import HomeAssistantError

    dev = _make_emby_device(monkeypatch)

    async def _fake_fetch(_url):  # noqa: D401 – ignore URL in this test
        return None, None

    monkeypatch.setattr(dev, "_async_fetch_image", _fake_fetch)

    with pytest.raises(HomeAssistantError):
        await dev.async_get_browse_image("movie", "nope")


# ---------------------------------------------------------------------------
# Security – reject *media_image_id* that contains a URL (GitHub #123)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_async_get_browse_image_reject_malicious_id(monkeypatch):  # noqa: D401
    """Ensure the helper raises when *media_image_id* looks like a URL."""

    from homeassistant.exceptions import HomeAssistantError

    dev = _make_emby_device(monkeypatch)

    # No network call should be attempted – *media_image_id* validation fires
    async def _fake_fetch(_url):  # pragma: no cover
        raise AssertionError("_async_fetch_image must not be called on invalid input")

    monkeypatch.setattr(dev, "_async_fetch_image", _fake_fetch)

    with pytest.raises(HomeAssistantError):
        await dev.async_get_browse_image(
            "movie",
            "xyz",
            media_image_id="https://evil.invalid/logo.png",
        )
