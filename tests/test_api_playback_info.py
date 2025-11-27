"""Tests for PlaybackInfo API methods (Phase 13.4)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.embymedia.api import EmbyClient
from custom_components.embymedia.const import (
    PlaybackInfoResponse,
)
from custom_components.embymedia.exceptions import (
    EmbyAuthenticationError,
    EmbyConnectionError,
    EmbyNotFoundError,
)
from custom_components.embymedia.profiles import UNIVERSAL_PROFILE


@pytest.fixture
def mock_session() -> MagicMock:
    """Create mock aiohttp session."""
    return MagicMock(spec=aiohttp.ClientSession)


@pytest.fixture
def emby_client(mock_session: MagicMock) -> EmbyClient:
    """Create EmbyClient with mock session."""
    return EmbyClient(
        host="emby.local",
        port=8096,
        api_key="test-api-key",
        ssl=False,
        session=mock_session,
    )


class TestAsyncGetPlaybackInfo:
    """Tests for async_get_playback_info method."""

    @pytest.mark.asyncio
    async def test_get_playback_info_direct_stream(self, emby_client: EmbyClient) -> None:
        """Test getting playback info for direct stream scenario."""
        mock_response: PlaybackInfoResponse = {
            "MediaSources": [
                {
                    "Id": "source-123",
                    "Name": "Movie.mp4",
                    "Container": "mp4",
                    "SupportsDirectPlay": False,
                    "SupportsDirectStream": True,
                    "SupportsTranscoding": True,
                    "DirectStreamUrl": "/Videos/123/stream?static=true",
                    "Bitrate": 8000000,
                }
            ],
            "PlaySessionId": "session-abc123",
        }

        with patch.object(
            emby_client, "_request_post_json", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await emby_client.async_get_playback_info(
                item_id="item-123",
                user_id="user-456",
            )

            assert result["PlaySessionId"] == "session-abc123"
            assert len(result["MediaSources"]) == 1
            assert result["MediaSources"][0]["SupportsDirectStream"] is True

    @pytest.mark.asyncio
    async def test_get_playback_info_transcoding(self, emby_client: EmbyClient) -> None:
        """Test getting playback info for transcoding scenario."""
        mock_response: PlaybackInfoResponse = {
            "MediaSources": [
                {
                    "Id": "source-456",
                    "Name": "Movie.mkv",
                    "Container": "mkv",
                    "SupportsDirectPlay": False,
                    "SupportsDirectStream": False,
                    "SupportsTranscoding": True,
                    "TranscodingUrl": "/Videos/456/master.m3u8?DeviceId=xxx",
                    "TranscodingSubProtocol": "hls",
                    "TranscodingContainer": "ts",
                }
            ],
            "PlaySessionId": "session-def456",
        }

        with patch.object(
            emby_client, "_request_post_json", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await emby_client.async_get_playback_info(
                item_id="item-456",
                user_id="user-789",
                device_profile=UNIVERSAL_PROFILE,
            )

            assert result["PlaySessionId"] == "session-def456"
            source = result["MediaSources"][0]
            assert source["SupportsTranscoding"] is True
            assert source["TranscodingSubProtocol"] == "hls"

    @pytest.mark.asyncio
    async def test_get_playback_info_with_all_options(self, emby_client: EmbyClient) -> None:
        """Test getting playback info with all options specified."""
        mock_response: PlaybackInfoResponse = {
            "MediaSources": [{"Id": "source-1", "Container": "mp4"}],
            "PlaySessionId": "session-xyz",
        }

        with patch.object(
            emby_client, "_request_post_json", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            await emby_client.async_get_playback_info(
                item_id="item-123",
                user_id="user-456",
                device_profile=UNIVERSAL_PROFILE,
                max_streaming_bitrate=20_000_000,
                start_position_ticks=100000000,
                audio_stream_index=1,
                subtitle_stream_index=2,
                enable_direct_play=False,
                enable_direct_stream=True,
                enable_transcoding=True,
            )

            # Verify request was made with correct body
            call_args = mock_request.call_args
            assert call_args is not None
            endpoint, body = call_args[0]
            assert "/Items/item-123/PlaybackInfo" in endpoint
            assert body["UserId"] == "user-456"
            assert body["MaxStreamingBitrate"] == 20_000_000
            assert body["StartTimeTicks"] == 100000000
            assert body["AudioStreamIndex"] == 1
            assert body["SubtitleStreamIndex"] == 2
            assert body["EnableDirectPlay"] is False
            assert body["EnableDirectStream"] is True
            assert body["EnableTranscoding"] is True

    @pytest.mark.asyncio
    async def test_get_playback_info_uses_default_profile(self, emby_client: EmbyClient) -> None:
        """Test that default UNIVERSAL_PROFILE is used when none specified."""
        mock_response: PlaybackInfoResponse = {
            "MediaSources": [],
            "PlaySessionId": "session-123",
        }

        with patch.object(
            emby_client, "_request_post_json", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            await emby_client.async_get_playback_info(
                item_id="item-123",
                user_id="user-456",
            )

            call_args = mock_request.call_args
            assert call_args is not None
            _, body = call_args[0]
            assert "DeviceProfile" in body
            assert body["DeviceProfile"]["Name"] == "Home Assistant Universal"

    @pytest.mark.asyncio
    async def test_get_playback_info_error_handling(self, emby_client: EmbyClient) -> None:
        """Test error handling for playback info request."""
        with patch.object(
            emby_client, "_request_post_json", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = EmbyNotFoundError("Item not found")

            with pytest.raises(EmbyNotFoundError):
                await emby_client.async_get_playback_info(
                    item_id="nonexistent",
                    user_id="user-456",
                )


class TestAsyncStopTranscoding:
    """Tests for async_stop_transcoding method."""

    @pytest.mark.asyncio
    async def test_stop_transcoding_basic(self, emby_client: EmbyClient) -> None:
        """Test stopping transcoding for a device."""
        with patch.object(emby_client, "_request_delete", new_callable=AsyncMock) as mock_delete:
            await emby_client.async_stop_transcoding(device_id="device-123")

            mock_delete.assert_called_once()
            call_args = mock_delete.call_args[0][0]
            assert "DeviceId=device-123" in call_args
            assert "/Videos/ActiveEncodings" in call_args

    @pytest.mark.asyncio
    async def test_stop_transcoding_with_session_id(self, emby_client: EmbyClient) -> None:
        """Test stopping transcoding with specific session ID."""
        with patch.object(emby_client, "_request_delete", new_callable=AsyncMock) as mock_delete:
            await emby_client.async_stop_transcoding(
                device_id="device-123",
                play_session_id="session-456",
            )

            call_args = mock_delete.call_args[0][0]
            assert "DeviceId=device-123" in call_args
            assert "PlaySessionId=session-456" in call_args


class TestGetUniversalAudioUrl:
    """Tests for get_universal_audio_url method."""

    def test_get_universal_audio_url_basic(self, emby_client: EmbyClient) -> None:
        """Test generating basic universal audio URL."""
        url = emby_client.get_universal_audio_url(
            item_id="audio-123",
            user_id="user-456",
            device_id="device-789",
        )

        assert "/Audio/audio-123/universal" in url
        assert "UserId=user-456" in url
        assert "DeviceId=device-789" in url
        assert "api_key=test-api-key" in url

    def test_get_universal_audio_url_with_all_params(self, emby_client: EmbyClient) -> None:
        """Test generating universal audio URL with all parameters."""
        url = emby_client.get_universal_audio_url(
            item_id="audio-123",
            user_id="user-456",
            device_id="device-789",
            max_streaming_bitrate=320000,
            container="mp3,aac,flac",
            transcoding_container="mp3",
            transcoding_protocol="hls",
            audio_codec="mp3",
            max_sample_rate=48000,
            play_session_id="session-abc",
        )

        assert "MaxStreamingBitrate=320000" in url
        assert "Container=mp3,aac,flac" in url or "Container=mp3%2Caac%2Cflac" in url
        assert "TranscodingContainer=mp3" in url
        assert "TranscodingProtocol=hls" in url
        assert "AudioCodec=mp3" in url
        assert "MaxSampleRate=48000" in url
        assert "PlaySessionId=session-abc" in url

    def test_get_universal_audio_url_no_transcoding_protocol(self, emby_client: EmbyClient) -> None:
        """Test universal audio URL without transcoding protocol (progressive)."""
        url = emby_client.get_universal_audio_url(
            item_id="audio-123",
            user_id="user-456",
            device_id="device-789",
            transcoding_protocol="",  # Empty = progressive
        )

        # Should not include TranscodingProtocol if empty
        assert "TranscodingProtocol=" not in url or "TranscodingProtocol=&" in url


class TestRequestPostJson:
    """Tests for _request_post_json helper method."""

    @pytest.mark.asyncio
    async def test_request_post_json_success(self, emby_client: EmbyClient) -> None:
        """Test successful POST with JSON response."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"success": True})

        with patch.object(emby_client, "_get_session", new_callable=AsyncMock) as mock_get_session:
            mock_session = MagicMock()
            mock_session.post = MagicMock(
                return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_response))
            )
            mock_get_session.return_value = mock_session

            result = await emby_client._request_post_json("/test/endpoint", {"key": "value"})

            assert result == {"success": True}

    @pytest.mark.asyncio
    async def test_request_post_json_auth_error(self, emby_client: EmbyClient) -> None:
        """Test POST with authentication error."""
        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.reason = "Unauthorized"

        with patch.object(emby_client, "_get_session", new_callable=AsyncMock) as mock_get_session:
            mock_session = MagicMock()
            mock_session.post = MagicMock(
                return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_response))
            )
            mock_get_session.return_value = mock_session

            with pytest.raises(EmbyAuthenticationError):
                await emby_client._request_post_json("/test/endpoint", {})

    @pytest.mark.asyncio
    async def test_request_post_json_not_found_error(self, emby_client: EmbyClient) -> None:
        """Test POST with 404 not found error."""
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.reason = "Not Found"

        with patch.object(emby_client, "_get_session", new_callable=AsyncMock) as mock_get_session:
            mock_session = MagicMock()
            mock_session.post = MagicMock(
                return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_response))
            )
            mock_get_session.return_value = mock_session

            with pytest.raises(EmbyNotFoundError):
                await emby_client._request_post_json("/test/endpoint", {})

    @pytest.mark.asyncio
    async def test_request_post_json_server_error(self, emby_client: EmbyClient) -> None:
        """Test POST with 500 server error."""
        from custom_components.embymedia.exceptions import EmbyServerError

        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.reason = "Internal Server Error"

        with patch.object(emby_client, "_get_session", new_callable=AsyncMock) as mock_get_session:
            mock_session = MagicMock()
            mock_session.post = MagicMock(
                return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_response))
            )
            mock_get_session.return_value = mock_session

            with pytest.raises(EmbyServerError):
                await emby_client._request_post_json("/test/endpoint", {})

    @pytest.mark.asyncio
    async def test_request_post_json_ssl_error(self, emby_client: EmbyClient) -> None:
        """Test POST with SSL error."""
        from ssl import SSLCertVerificationError

        from custom_components.embymedia.exceptions import EmbySSLError

        with patch.object(emby_client, "_get_session", new_callable=AsyncMock) as mock_get_session:
            mock_session = MagicMock()
            # Create a proper SSL error
            ssl_error = SSLCertVerificationError(1, "certificate verify failed")
            mock_session.post = MagicMock(
                side_effect=aiohttp.ClientSSLError(MagicMock(), ssl_error)
            )
            mock_get_session.return_value = mock_session

            with pytest.raises(EmbySSLError):
                await emby_client._request_post_json("/test/endpoint", {})

    @pytest.mark.asyncio
    async def test_request_post_json_timeout_error(self, emby_client: EmbyClient) -> None:
        """Test POST with timeout error."""
        from custom_components.embymedia.exceptions import EmbyTimeoutError

        with patch.object(emby_client, "_get_session", new_callable=AsyncMock) as mock_get_session:
            mock_session = MagicMock()
            mock_session.post = MagicMock(side_effect=TimeoutError())
            mock_get_session.return_value = mock_session

            with pytest.raises(EmbyTimeoutError):
                await emby_client._request_post_json("/test/endpoint", {})

    @pytest.mark.asyncio
    async def test_request_post_json_connection_error(self, emby_client: EmbyClient) -> None:
        """Test POST with connection error."""
        with patch.object(emby_client, "_get_session", new_callable=AsyncMock) as mock_get_session:
            mock_session = MagicMock()
            mock_session.post = MagicMock(
                side_effect=aiohttp.ClientConnectorError(MagicMock(), OSError("Connection refused"))
            )
            mock_get_session.return_value = mock_session

            with pytest.raises(EmbyConnectionError):
                await emby_client._request_post_json("/test/endpoint", {})

    @pytest.mark.asyncio
    async def test_request_post_json_client_error(self, emby_client: EmbyClient) -> None:
        """Test POST with generic client error."""
        with patch.object(emby_client, "_get_session", new_callable=AsyncMock) as mock_get_session:
            mock_session = MagicMock()
            mock_session.post = MagicMock(side_effect=aiohttp.ClientError("Generic error"))
            mock_get_session.return_value = mock_session

            with pytest.raises(EmbyConnectionError):
                await emby_client._request_post_json("/test/endpoint", {})
