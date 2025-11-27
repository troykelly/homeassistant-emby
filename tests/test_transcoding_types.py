"""Tests for transcoding TypedDicts (Phase 13)."""

from __future__ import annotations


class TestMediaStreamInfoTypedDict:
    """Tests for MediaStreamInfo TypedDict."""

    def test_media_stream_info_exists(self) -> None:
        """Test MediaStreamInfo TypedDict is importable."""
        from custom_components.embymedia.const import MediaStreamInfo

        assert MediaStreamInfo is not None

    def test_media_stream_info_video_stream(self) -> None:
        """Test MediaStreamInfo can represent a video stream."""
        from custom_components.embymedia.const import MediaStreamInfo

        video_stream: MediaStreamInfo = {
            "Index": 0,
            "Type": "Video",
            "Codec": "h264",
            "Width": 1920,
            "Height": 1080,
            "BitRate": 8000000,
            "AspectRatio": "16:9",
            "AverageFrameRate": 23.976,
            "Profile": "High",
            "Level": 4.1,
            "IsDefault": True,
        }
        assert video_stream["Type"] == "Video"
        assert video_stream["Codec"] == "h264"
        assert video_stream["Width"] == 1920

    def test_media_stream_info_audio_stream(self) -> None:
        """Test MediaStreamInfo can represent an audio stream."""
        from custom_components.embymedia.const import MediaStreamInfo

        audio_stream: MediaStreamInfo = {
            "Index": 1,
            "Type": "Audio",
            "Codec": "aac",
            "Language": "eng",
            "Title": "English",
            "IsDefault": True,
            "Channels": 6,
            "SampleRate": 48000,
            "ChannelLayout": "5.1",
        }
        assert audio_stream["Type"] == "Audio"
        assert audio_stream["Channels"] == 6

    def test_media_stream_info_subtitle_stream(self) -> None:
        """Test MediaStreamInfo can represent a subtitle stream."""
        from custom_components.embymedia.const import MediaStreamInfo

        subtitle_stream: MediaStreamInfo = {
            "Index": 2,
            "Type": "Subtitle",
            "Codec": "srt",
            "Language": "eng",
            "Title": "English",
            "IsDefault": False,
            "IsForced": False,
        }
        assert subtitle_stream["Type"] == "Subtitle"


class TestMediaSourceInfoTypedDict:
    """Tests for MediaSourceInfo TypedDict."""

    def test_media_source_info_exists(self) -> None:
        """Test MediaSourceInfo TypedDict is importable."""
        from custom_components.embymedia.const import MediaSourceInfo

        assert MediaSourceInfo is not None

    def test_media_source_info_direct_stream(self) -> None:
        """Test MediaSourceInfo for direct stream scenario."""
        from custom_components.embymedia.const import MediaSourceInfo

        source: MediaSourceInfo = {
            "Id": "source-123",
            "Name": "Movie.mkv",
            "Path": "/media/movies/Movie.mkv",
            "Protocol": "File",
            "Container": "mkv",
            "Size": 5000000000,
            "Bitrate": 8000000,
            "RunTimeTicks": 72000000000,
            "SupportsTranscoding": True,
            "SupportsDirectStream": True,
            "SupportsDirectPlay": False,
            "DirectStreamUrl": "/Videos/123/stream?static=true",
            "MediaStreams": [],
            "DefaultAudioStreamIndex": 1,
            "DefaultSubtitleStreamIndex": -1,
        }
        assert source["SupportsDirectStream"] is True
        assert source["Container"] == "mkv"

    def test_media_source_info_transcoding(self) -> None:
        """Test MediaSourceInfo for transcoding scenario."""
        from custom_components.embymedia.const import MediaSourceInfo

        source: MediaSourceInfo = {
            "Id": "source-456",
            "Name": "Movie.mkv",
            "Container": "mkv",
            "SupportsTranscoding": True,
            "SupportsDirectStream": False,
            "SupportsDirectPlay": False,
            "TranscodingUrl": "/Videos/456/master.m3u8?DeviceId=xxx",
            "TranscodingSubProtocol": "hls",
            "TranscodingContainer": "ts",
        }
        assert source["SupportsDirectStream"] is False
        assert source["TranscodingSubProtocol"] == "hls"


class TestPlaybackInfoResponseTypedDict:
    """Tests for PlaybackInfoResponse TypedDict."""

    def test_playback_info_response_exists(self) -> None:
        """Test PlaybackInfoResponse TypedDict is importable."""
        from custom_components.embymedia.const import PlaybackInfoResponse

        assert PlaybackInfoResponse is not None

    def test_playback_info_response_success(self) -> None:
        """Test PlaybackInfoResponse for successful response."""
        from custom_components.embymedia.const import PlaybackInfoResponse

        response: PlaybackInfoResponse = {
            "MediaSources": [
                {
                    "Id": "source-123",
                    "Container": "mkv",
                    "SupportsDirectStream": True,
                    "SupportsTranscoding": True,
                    "SupportsDirectPlay": False,
                }
            ],
            "PlaySessionId": "abc123def456",
        }
        assert len(response["MediaSources"]) == 1
        assert response["PlaySessionId"] == "abc123def456"

    def test_playback_info_response_with_error(self) -> None:
        """Test PlaybackInfoResponse with error code."""
        from custom_components.embymedia.const import PlaybackInfoResponse

        response: PlaybackInfoResponse = {
            "MediaSources": [],
            "PlaySessionId": "",
            "ErrorCode": "NoCompatibleStream",
        }
        assert response["ErrorCode"] == "NoCompatibleStream"


class TestPlaybackInfoRequestTypedDict:
    """Tests for PlaybackInfoRequest TypedDict."""

    def test_playback_info_request_exists(self) -> None:
        """Test PlaybackInfoRequest TypedDict is importable."""
        from custom_components.embymedia.const import PlaybackInfoRequest

        assert PlaybackInfoRequest is not None

    def test_playback_info_request_minimal(self) -> None:
        """Test PlaybackInfoRequest with minimal fields."""
        from custom_components.embymedia.const import PlaybackInfoRequest

        request: PlaybackInfoRequest = {
            "UserId": "user-123",
            "MaxStreamingBitrate": 40000000,
        }
        assert request["UserId"] == "user-123"

    def test_playback_info_request_full(self) -> None:
        """Test PlaybackInfoRequest with all fields."""
        from custom_components.embymedia.const import (
            DeviceProfile,
            PlaybackInfoRequest,
        )

        profile: DeviceProfile = {
            "Name": "Test Profile",
            "MaxStreamingBitrate": 40000000,
        }

        request: PlaybackInfoRequest = {
            "UserId": "user-123",
            "MaxStreamingBitrate": 40000000,
            "StartTimeTicks": 0,
            "AudioStreamIndex": 1,
            "SubtitleStreamIndex": -1,
            "MaxAudioChannels": 6,
            "MediaSourceId": "source-123",
            "DeviceProfile": profile,
            "EnableDirectPlay": True,
            "EnableDirectStream": True,
            "EnableTranscoding": True,
            "AllowVideoStreamCopy": True,
            "AllowAudioStreamCopy": True,
            "AutoOpenLiveStream": False,
        }
        assert request["EnableDirectStream"] is True
        assert request["DeviceProfile"]["Name"] == "Test Profile"


class TestDirectPlayProfileTypedDict:
    """Tests for DirectPlayProfile TypedDict."""

    def test_direct_play_profile_exists(self) -> None:
        """Test DirectPlayProfile TypedDict is importable."""
        from custom_components.embymedia.const import DirectPlayProfile

        assert DirectPlayProfile is not None

    def test_direct_play_profile_video(self) -> None:
        """Test DirectPlayProfile for video."""
        from custom_components.embymedia.const import DirectPlayProfile

        profile: DirectPlayProfile = {
            "Container": "mp4,mkv,webm",
            "VideoCodec": "h264,hevc",
            "AudioCodec": "aac,mp3,ac3",
            "Type": "Video",
        }
        assert profile["Type"] == "Video"
        assert "h264" in profile["VideoCodec"]

    def test_direct_play_profile_audio(self) -> None:
        """Test DirectPlayProfile for audio."""
        from custom_components.embymedia.const import DirectPlayProfile

        profile: DirectPlayProfile = {
            "Container": "mp3,aac,flac,ogg",
            "AudioCodec": "mp3,aac,flac,vorbis",
            "Type": "Audio",
        }
        assert profile["Type"] == "Audio"


class TestTranscodingProfileTypedDict:
    """Tests for TranscodingProfile TypedDict."""

    def test_transcoding_profile_exists(self) -> None:
        """Test TranscodingProfile TypedDict is importable."""
        from custom_components.embymedia.const import TranscodingProfile

        assert TranscodingProfile is not None

    def test_transcoding_profile_hls_video(self) -> None:
        """Test TranscodingProfile for HLS video transcoding."""
        from custom_components.embymedia.const import TranscodingProfile

        profile: TranscodingProfile = {
            "Container": "ts",
            "Type": "Video",
            "VideoCodec": "h264",
            "AudioCodec": "aac",
            "Protocol": "hls",
            "Context": "Streaming",
            "MaxAudioChannels": "2",
            "SegmentLength": 6,
            "MinSegments": 1,
            "BreakOnNonKeyFrames": True,
        }
        assert profile["Protocol"] == "hls"
        assert profile["Container"] == "ts"

    def test_transcoding_profile_progressive_audio(self) -> None:
        """Test TranscodingProfile for progressive audio."""
        from custom_components.embymedia.const import TranscodingProfile

        profile: TranscodingProfile = {
            "Container": "mp3",
            "Type": "Audio",
            "AudioCodec": "mp3",
            "Context": "Streaming",
        }
        assert profile["Type"] == "Audio"


class TestSubtitleProfileTypedDict:
    """Tests for SubtitleProfile TypedDict."""

    def test_subtitle_profile_exists(self) -> None:
        """Test SubtitleProfile TypedDict is importable."""
        from custom_components.embymedia.const import SubtitleProfile

        assert SubtitleProfile is not None

    def test_subtitle_profile_external(self) -> None:
        """Test SubtitleProfile for external subtitles."""
        from custom_components.embymedia.const import SubtitleProfile

        profile: SubtitleProfile = {
            "Format": "srt",
            "Method": "External",
        }
        assert profile["Method"] == "External"

    def test_subtitle_profile_embedded(self) -> None:
        """Test SubtitleProfile for embedded subtitles."""
        from custom_components.embymedia.const import SubtitleProfile

        profile: SubtitleProfile = {
            "Format": "ass",
            "Method": "Embed",
        }
        assert profile["Method"] == "Embed"

    def test_subtitle_profile_burn_in(self) -> None:
        """Test SubtitleProfile for burned-in subtitles."""
        from custom_components.embymedia.const import SubtitleProfile

        profile: SubtitleProfile = {
            "Format": "ass",
            "Method": "Encode",
        }
        assert profile["Method"] == "Encode"


class TestDeviceProfileTypedDict:
    """Tests for DeviceProfile TypedDict."""

    def test_device_profile_exists(self) -> None:
        """Test DeviceProfile TypedDict is importable."""
        from custom_components.embymedia.const import DeviceProfile

        assert DeviceProfile is not None

    def test_device_profile_minimal(self) -> None:
        """Test DeviceProfile with minimal fields."""
        from custom_components.embymedia.const import DeviceProfile

        profile: DeviceProfile = {
            "Name": "Test Device",
            "MaxStreamingBitrate": 40000000,
        }
        assert profile["Name"] == "Test Device"

    def test_device_profile_full(self) -> None:
        """Test DeviceProfile with all fields."""
        from custom_components.embymedia.const import DeviceProfile

        profile: DeviceProfile = {
            "Name": "Full Test Device",
            "Id": "device-123",
            "MaxStreamingBitrate": 40000000,
            "MaxStaticBitrate": 100000000,
            "MusicStreamingTranscodingBitrate": 320000,
            "DirectPlayProfiles": [
                {
                    "Container": "mp4",
                    "VideoCodec": "h264",
                    "AudioCodec": "aac",
                    "Type": "Video",
                }
            ],
            "TranscodingProfiles": [
                {
                    "Container": "ts",
                    "Type": "Video",
                    "VideoCodec": "h264",
                    "AudioCodec": "aac",
                    "Protocol": "hls",
                }
            ],
            "SubtitleProfiles": [
                {"Format": "srt", "Method": "External"},
            ],
        }
        assert len(profile["DirectPlayProfiles"]) == 1
        assert len(profile["TranscodingProfiles"]) == 1
        assert len(profile["SubtitleProfiles"]) == 1


class TestTranscodingConstants:
    """Tests for transcoding-related constants."""

    def test_transcoding_profile_choices_exist(self) -> None:
        """Test TRANSCODING_PROFILES constant exists."""
        from custom_components.embymedia.const import TRANSCODING_PROFILES

        assert isinstance(TRANSCODING_PROFILES, list)
        assert "universal" in TRANSCODING_PROFILES
        assert "chromecast" in TRANSCODING_PROFILES
        assert "roku" in TRANSCODING_PROFILES
        assert "appletv" in TRANSCODING_PROFILES
        assert "audio_only" in TRANSCODING_PROFILES

    def test_transcoding_config_keys_exist(self) -> None:
        """Test transcoding configuration keys exist."""
        from custom_components.embymedia.const import (
            CONF_MAX_STREAMING_BITRATE,
            CONF_MAX_VIDEO_HEIGHT,
            CONF_MAX_VIDEO_WIDTH,
            CONF_PREFER_DIRECT_PLAY,
            CONF_TRANSCODING_PROFILE,
        )

        assert CONF_TRANSCODING_PROFILE == "transcoding_profile"
        assert CONF_MAX_STREAMING_BITRATE == "max_streaming_bitrate"
        assert CONF_PREFER_DIRECT_PLAY == "prefer_direct_play"
        assert CONF_MAX_VIDEO_WIDTH == "max_video_width"
        assert CONF_MAX_VIDEO_HEIGHT == "max_video_height"

    def test_transcoding_defaults_exist(self) -> None:
        """Test transcoding default values exist."""
        from custom_components.embymedia.const import (
            DEFAULT_MAX_STREAMING_BITRATE,
            DEFAULT_MAX_VIDEO_HEIGHT,
            DEFAULT_MAX_VIDEO_WIDTH,
            DEFAULT_PREFER_DIRECT_PLAY,
            DEFAULT_TRANSCODING_PROFILE,
        )

        assert DEFAULT_TRANSCODING_PROFILE == "universal"
        assert DEFAULT_MAX_STREAMING_BITRATE == 40_000_000  # 40 Mbps
        assert DEFAULT_PREFER_DIRECT_PLAY is True
        assert DEFAULT_MAX_VIDEO_WIDTH == 1920
        assert DEFAULT_MAX_VIDEO_HEIGHT == 1080

    def test_hls_mime_type_constant(self) -> None:
        """Test HLS MIME type constant exists."""
        from custom_components.embymedia.const import MIME_TYPE_HLS

        assert MIME_TYPE_HLS == "application/x-mpegURL"
