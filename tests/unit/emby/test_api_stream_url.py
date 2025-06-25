"""Unit tests for :py:meth:`custom_components.embymedia.api.EmbyAPI.get_stream_url`."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.embymedia.api import EmbyAPI, EmbyApiError


class _PlaybackRecorder:
    """Stub for :py:meth:`EmbyAPI._request` to capture calls & return fixtures."""

    def __init__(self, response_payload):
        self.response_payload = response_payload
        self.calls: list[dict[str, str]] = []

    async def __call__(self, method: str, path: str, **kwargs):  # noqa: D401
        self.calls.append({"method": method, "path": path, **kwargs})
        # Only the PlaybackInfo endpoint is expected in these unit tests.
        assert path.endswith("/PlaybackInfo"), "Unexpected endpoint invoked"
        return self.response_payload


# ---------------------------------------------------------------------------
# 1. Direct-play happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_stream_url_prefers_direct_play(monkeypatch):
    """The helper must return the *DirectStreamUrl* when available."""

    playback_payload = {
        "MediaSources": [
            {
                "Id": "ms1",
                "SupportsDirectPlay": True,
                "DirectStreamUrl": "/Videos/123/stream.mp4?Static=true&MediaSourceId=ms1",
            }
        ]
    }

    recorder = _PlaybackRecorder(playback_payload)
    api = EmbyAPI(None, host="emby", api_key="k", session=SimpleNamespace())
    monkeypatch.setattr(api, "_request", recorder)  # type: ignore[attr-defined]

    url = await api.get_stream_url("123")

    # The returned URL must be absolute and include the api_key query param.
    assert url.startswith("http://emby/Videos/123/stream.mp4")
    assert "api_key=k" in url

    # Exactly one HTTP call should have been made.
    assert len(recorder.calls) == 1
    call = recorder.calls[0]
    assert call["method"] == "POST"
    assert call["path"] == "/Items/123/PlaybackInfo"


# ---------------------------------------------------------------------------
# 2. Fallback to TranscodingUrl when direct play is not possible
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_stream_url_falls_back_to_hls(monkeypatch):
    """When direct play is not supported the first *TranscodingUrl* is used."""

    playback_payload = {
        "MediaSources": [
            {
                "Id": "ms1",
                "SupportsDirectPlay": False,
                "TranscodingUrl": "Videos/123/master.m3u8",
            }
        ]
    }

    recorder = _PlaybackRecorder(playback_payload)
    api = EmbyAPI(None, host="emby", api_key="token-xyz", session=SimpleNamespace())
    monkeypatch.setattr(api, "_request", recorder, raising=False)

    url = await api.get_stream_url("123")

    # The helper must prepend the server base for relative URLs.
    assert url == "http://emby/Videos/123/master.m3u8?api_key=token-xyz"


# ---------------------------------------------------------------------------
# 3. Error when no playable source is returned
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_stream_url_error_when_unplayable(monkeypatch):
    """The helper should raise *EmbyApiError* when no usable source exists."""

    playback_payload = {"MediaSources": []}

    recorder = _PlaybackRecorder(playback_payload)
    api = EmbyAPI(None, host="emby", api_key="k", session=SimpleNamespace())
    monkeypatch.setattr(api, "_request", recorder, raising=False)

    with pytest.raises(EmbyApiError):
        await api.get_stream_url("abc")
