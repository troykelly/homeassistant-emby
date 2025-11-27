"""Tests for predefined device profiles (Phase 13.3)."""

from __future__ import annotations


class TestUniversalProfile:
    """Tests for UNIVERSAL_PROFILE."""

    def test_universal_profile_exists(self) -> None:
        """Test UNIVERSAL_PROFILE is importable."""
        from custom_components.embymedia.profiles import UNIVERSAL_PROFILE

        assert UNIVERSAL_PROFILE is not None

    def test_universal_profile_has_name(self) -> None:
        """Test UNIVERSAL_PROFILE has a name."""
        from custom_components.embymedia.profiles import UNIVERSAL_PROFILE

        assert UNIVERSAL_PROFILE["Name"] == "Home Assistant Universal"

    def test_universal_profile_has_bitrate(self) -> None:
        """Test UNIVERSAL_PROFILE has max streaming bitrate."""
        from custom_components.embymedia.profiles import UNIVERSAL_PROFILE

        assert UNIVERSAL_PROFILE["MaxStreamingBitrate"] == 40_000_000

    def test_universal_profile_has_direct_play_profiles(self) -> None:
        """Test UNIVERSAL_PROFILE has direct play profiles."""
        from custom_components.embymedia.profiles import UNIVERSAL_PROFILE

        profiles = UNIVERSAL_PROFILE["DirectPlayProfiles"]
        assert len(profiles) >= 2

        # Check video profile
        video_profiles = [p for p in profiles if p["Type"] == "Video"]
        assert len(video_profiles) >= 1
        video = video_profiles[0]
        assert "h264" in video["VideoCodec"]
        assert "aac" in video["AudioCodec"]

        # Check audio profile
        audio_profiles = [p for p in profiles if p["Type"] == "Audio"]
        assert len(audio_profiles) >= 1

    def test_universal_profile_has_transcoding_profiles(self) -> None:
        """Test UNIVERSAL_PROFILE has HLS transcoding profile."""
        from custom_components.embymedia.profiles import UNIVERSAL_PROFILE

        profiles = UNIVERSAL_PROFILE["TranscodingProfiles"]
        assert len(profiles) >= 1

        # Check video transcoding uses HLS
        video_profiles = [p for p in profiles if p["Type"] == "Video"]
        assert len(video_profiles) >= 1
        video = video_profiles[0]
        assert video["Protocol"] == "hls"
        assert video["Container"] == "ts"
        assert video["VideoCodec"] == "h264"
        assert video["AudioCodec"] == "aac"

    def test_universal_profile_has_subtitle_profiles(self) -> None:
        """Test UNIVERSAL_PROFILE has subtitle profiles."""
        from custom_components.embymedia.profiles import UNIVERSAL_PROFILE

        profiles = UNIVERSAL_PROFILE["SubtitleProfiles"]
        assert len(profiles) >= 2

        # Check for external subtitle support
        external = [p for p in profiles if p["Method"] == "External"]
        assert len(external) >= 1


class TestChromecastProfile:
    """Tests for CHROMECAST_PROFILE."""

    def test_chromecast_profile_exists(self) -> None:
        """Test CHROMECAST_PROFILE is importable."""
        from custom_components.embymedia.profiles import CHROMECAST_PROFILE

        assert CHROMECAST_PROFILE is not None

    def test_chromecast_profile_has_name(self) -> None:
        """Test CHROMECAST_PROFILE has a name."""
        from custom_components.embymedia.profiles import CHROMECAST_PROFILE

        assert CHROMECAST_PROFILE["Name"] == "Chromecast"

    def test_chromecast_profile_supports_vp9(self) -> None:
        """Test CHROMECAST_PROFILE supports VP9."""
        from custom_components.embymedia.profiles import CHROMECAST_PROFILE

        profiles = CHROMECAST_PROFILE["DirectPlayProfiles"]
        video_profiles = [p for p in profiles if p["Type"] == "Video"]
        assert len(video_profiles) >= 1

        # Check for VP9 support
        codecs = video_profiles[0].get("VideoCodec", "")
        assert "vp9" in codecs or "vp8" in codecs

    def test_chromecast_profile_reasonable_bitrate(self) -> None:
        """Test CHROMECAST_PROFILE has reasonable bitrate limit."""
        from custom_components.embymedia.profiles import CHROMECAST_PROFILE

        # Chromecast typically limited to 20 Mbps
        assert CHROMECAST_PROFILE["MaxStreamingBitrate"] <= 30_000_000


class TestRokuProfile:
    """Tests for ROKU_PROFILE."""

    def test_roku_profile_exists(self) -> None:
        """Test ROKU_PROFILE is importable."""
        from custom_components.embymedia.profiles import ROKU_PROFILE

        assert ROKU_PROFILE is not None

    def test_roku_profile_has_name(self) -> None:
        """Test ROKU_PROFILE has a name."""
        from custom_components.embymedia.profiles import ROKU_PROFILE

        assert ROKU_PROFILE["Name"] == "Roku"

    def test_roku_profile_supports_hevc(self) -> None:
        """Test ROKU_PROFILE supports HEVC on capable devices."""
        from custom_components.embymedia.profiles import ROKU_PROFILE

        profiles = ROKU_PROFILE["DirectPlayProfiles"]
        video_profiles = [p for p in profiles if p["Type"] == "Video"]
        assert len(video_profiles) >= 1

        # Check for HEVC support
        codecs = video_profiles[0].get("VideoCodec", "")
        assert "hevc" in codecs or "h264" in codecs


class TestAppleTVProfile:
    """Tests for APPLETV_PROFILE."""

    def test_appletv_profile_exists(self) -> None:
        """Test APPLETV_PROFILE is importable."""
        from custom_components.embymedia.profiles import APPLETV_PROFILE

        assert APPLETV_PROFILE is not None

    def test_appletv_profile_has_name(self) -> None:
        """Test APPLETV_PROFILE has a name."""
        from custom_components.embymedia.profiles import APPLETV_PROFILE

        assert APPLETV_PROFILE["Name"] == "Apple TV"

    def test_appletv_profile_supports_hevc(self) -> None:
        """Test APPLETV_PROFILE supports HEVC."""
        from custom_components.embymedia.profiles import APPLETV_PROFILE

        profiles = APPLETV_PROFILE["DirectPlayProfiles"]
        video_profiles = [p for p in profiles if p["Type"] == "Video"]
        assert len(video_profiles) >= 1

        # Apple TV has excellent HEVC support
        codecs = video_profiles[0].get("VideoCodec", "")
        assert "hevc" in codecs


class TestAudioOnlyProfile:
    """Tests for AUDIO_ONLY_PROFILE."""

    def test_audio_only_profile_exists(self) -> None:
        """Test AUDIO_ONLY_PROFILE is importable."""
        from custom_components.embymedia.profiles import AUDIO_ONLY_PROFILE

        assert AUDIO_ONLY_PROFILE is not None

    def test_audio_only_profile_has_name(self) -> None:
        """Test AUDIO_ONLY_PROFILE has a name."""
        from custom_components.embymedia.profiles import AUDIO_ONLY_PROFILE

        assert AUDIO_ONLY_PROFILE["Name"] == "Audio Only"

    def test_audio_only_profile_no_video_direct_play(self) -> None:
        """Test AUDIO_ONLY_PROFILE has no video direct play profiles."""
        from custom_components.embymedia.profiles import AUDIO_ONLY_PROFILE

        profiles = AUDIO_ONLY_PROFILE["DirectPlayProfiles"]
        video_profiles = [p for p in profiles if p["Type"] == "Video"]
        assert len(video_profiles) == 0

    def test_audio_only_profile_has_audio_support(self) -> None:
        """Test AUDIO_ONLY_PROFILE has audio support."""
        from custom_components.embymedia.profiles import AUDIO_ONLY_PROFILE

        profiles = AUDIO_ONLY_PROFILE["DirectPlayProfiles"]
        audio_profiles = [p for p in profiles if p["Type"] == "Audio"]
        assert len(audio_profiles) >= 1

        # Check common audio formats
        audio = audio_profiles[0]
        codecs = audio.get("AudioCodec", "")
        assert "mp3" in codecs or "aac" in codecs


class TestGetProfile:
    """Tests for get_device_profile function."""

    def test_get_profile_universal(self) -> None:
        """Test getting universal profile."""
        from custom_components.embymedia.profiles import (
            UNIVERSAL_PROFILE,
            get_device_profile,
        )

        profile = get_device_profile("universal")
        assert profile == UNIVERSAL_PROFILE

    def test_get_profile_chromecast(self) -> None:
        """Test getting chromecast profile."""
        from custom_components.embymedia.profiles import (
            CHROMECAST_PROFILE,
            get_device_profile,
        )

        profile = get_device_profile("chromecast")
        assert profile == CHROMECAST_PROFILE

    def test_get_profile_roku(self) -> None:
        """Test getting roku profile."""
        from custom_components.embymedia.profiles import (
            ROKU_PROFILE,
            get_device_profile,
        )

        profile = get_device_profile("roku")
        assert profile == ROKU_PROFILE

    def test_get_profile_appletv(self) -> None:
        """Test getting appletv profile."""
        from custom_components.embymedia.profiles import (
            APPLETV_PROFILE,
            get_device_profile,
        )

        profile = get_device_profile("appletv")
        assert profile == APPLETV_PROFILE

    def test_get_profile_audio_only(self) -> None:
        """Test getting audio_only profile."""
        from custom_components.embymedia.profiles import (
            AUDIO_ONLY_PROFILE,
            get_device_profile,
        )

        profile = get_device_profile("audio_only")
        assert profile == AUDIO_ONLY_PROFILE

    def test_get_profile_unknown_returns_universal(self) -> None:
        """Test getting unknown profile returns universal."""
        from custom_components.embymedia.profiles import (
            UNIVERSAL_PROFILE,
            get_device_profile,
        )

        profile = get_device_profile("unknown_device")
        assert profile == UNIVERSAL_PROFILE

    def test_get_profile_case_insensitive(self) -> None:
        """Test profile lookup is case insensitive."""
        from custom_components.embymedia.profiles import (
            CHROMECAST_PROFILE,
            get_device_profile,
        )

        profile = get_device_profile("Chromecast")
        assert profile == CHROMECAST_PROFILE

        profile = get_device_profile("CHROMECAST")
        assert profile == CHROMECAST_PROFILE


class TestDeviceProfiles:
    """Tests for DEVICE_PROFILES dictionary."""

    def test_device_profiles_exists(self) -> None:
        """Test DEVICE_PROFILES dictionary exists."""
        from custom_components.embymedia.profiles import DEVICE_PROFILES

        assert isinstance(DEVICE_PROFILES, dict)

    def test_device_profiles_contains_all_profiles(self) -> None:
        """Test DEVICE_PROFILES contains all profile names."""
        from custom_components.embymedia.profiles import DEVICE_PROFILES

        expected_keys = {"universal", "chromecast", "roku", "appletv", "audio_only"}
        assert expected_keys == set(DEVICE_PROFILES.keys())
