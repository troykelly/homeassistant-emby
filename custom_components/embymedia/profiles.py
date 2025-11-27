"""Predefined device profiles for transcoding (Phase 13).

This module contains predefined DeviceProfile configurations for common
streaming devices. These profiles tell the Emby server what formats the
target device can play directly vs what needs to be transcoded.

Device Profiles:
- UNIVERSAL_PROFILE: Safe fallback that works on most devices (H.264/AAC)
- CHROMECAST_PROFILE: Optimized for Chromecast devices
- ROKU_PROFILE: Optimized for Roku devices
- APPLETV_PROFILE: Optimized for Apple TV
- AUDIO_ONLY_PROFILE: For audio-only devices (Sonos, Google Home, etc.)

Usage:
    from custom_components.embymedia.profiles import get_device_profile

    profile = get_device_profile("chromecast")
"""

from __future__ import annotations

from typing import Final

from .const import DeviceProfile

# =============================================================================
# Universal Profile - Safe fallback for most devices
# =============================================================================

UNIVERSAL_PROFILE: Final[DeviceProfile] = {
    "Name": "Home Assistant Universal",
    "MaxStreamingBitrate": 40_000_000,  # 40 Mbps
    "MaxStaticBitrate": 100_000_000,  # 100 Mbps
    "MusicStreamingTranscodingBitrate": 320_000,  # 320 kbps
    "DirectPlayProfiles": [
        {
            "Container": "mp4,m4v,mov",
            "VideoCodec": "h264",
            "AudioCodec": "aac,mp3,ac3",
            "Type": "Video",
        },
        {
            "Container": "mp3,aac,m4a,flac,wav,ogg",
            "AudioCodec": "mp3,aac,flac,vorbis,pcm",
            "Type": "Audio",
        },
    ],
    "TranscodingProfiles": [
        {
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
        },
        {
            "Container": "mp3",
            "Type": "Audio",
            "AudioCodec": "mp3",
            "Context": "Streaming",
        },
    ],
    "SubtitleProfiles": [
        {"Format": "srt", "Method": "External"},
        {"Format": "vtt", "Method": "External"},
        {"Format": "ass", "Method": "External"},
        {"Format": "sub", "Method": "External"},
    ],
}

# =============================================================================
# Chromecast Profile - Optimized for Chromecast devices
# =============================================================================

CHROMECAST_PROFILE: Final[DeviceProfile] = {
    "Name": "Chromecast",
    "MaxStreamingBitrate": 20_000_000,  # 20 Mbps (typical Chromecast limit)
    "MaxStaticBitrate": 40_000_000,
    "MusicStreamingTranscodingBitrate": 320_000,
    "DirectPlayProfiles": [
        {
            "Container": "mp4,webm,mkv",
            "VideoCodec": "h264,vp8,vp9",
            "AudioCodec": "aac,mp3,vorbis,opus,flac",
            "Type": "Video",
        },
        {
            "Container": "mp3,aac,m4a,flac,wav,ogg,webm",
            "AudioCodec": "mp3,aac,flac,vorbis,opus",
            "Type": "Audio",
        },
    ],
    "TranscodingProfiles": [
        {
            "Container": "ts",
            "Type": "Video",
            "VideoCodec": "h264",
            "AudioCodec": "aac",
            "Protocol": "hls",
            "Context": "Streaming",
            "MaxAudioChannels": "2",
            "SegmentLength": 3,
            "MinSegments": 2,
            "BreakOnNonKeyFrames": True,
        },
        {
            "Container": "mp3",
            "Type": "Audio",
            "AudioCodec": "mp3",
            "Context": "Streaming",
        },
    ],
    "SubtitleProfiles": [
        {"Format": "vtt", "Method": "External"},
        {"Format": "srt", "Method": "External"},
    ],
}

# =============================================================================
# Roku Profile - Optimized for Roku devices
# =============================================================================

ROKU_PROFILE: Final[DeviceProfile] = {
    "Name": "Roku",
    "MaxStreamingBitrate": 25_000_000,  # 25 Mbps
    "MaxStaticBitrate": 60_000_000,
    "MusicStreamingTranscodingBitrate": 320_000,
    "DirectPlayProfiles": [
        {
            "Container": "mp4,mkv,mov,m4v",
            "VideoCodec": "h264,hevc",
            "AudioCodec": "aac,ac3,eac3,mp3,dts,pcm",
            "Type": "Video",
        },
        {
            "Container": "mp3,aac,m4a,flac,wav,ogg,wma",
            "AudioCodec": "mp3,aac,flac,vorbis,wma,alac,pcm",
            "Type": "Audio",
        },
    ],
    "TranscodingProfiles": [
        {
            "Container": "ts",
            "Type": "Video",
            "VideoCodec": "h264",
            "AudioCodec": "aac",
            "Protocol": "hls",
            "Context": "Streaming",
            "MaxAudioChannels": "6",
            "SegmentLength": 6,
            "MinSegments": 1,
            "BreakOnNonKeyFrames": True,
        },
        {
            "Container": "mp3",
            "Type": "Audio",
            "AudioCodec": "mp3",
            "Context": "Streaming",
        },
    ],
    "SubtitleProfiles": [
        {"Format": "srt", "Method": "External"},
        {"Format": "vtt", "Method": "External"},
        {"Format": "ass", "Method": "Encode"},
    ],
}

# =============================================================================
# Apple TV Profile - Optimized for Apple TV
# =============================================================================

APPLETV_PROFILE: Final[DeviceProfile] = {
    "Name": "Apple TV",
    "MaxStreamingBitrate": 40_000_000,  # 40 Mbps (Apple TV handles high bitrates)
    "MaxStaticBitrate": 100_000_000,
    "MusicStreamingTranscodingBitrate": 320_000,
    "DirectPlayProfiles": [
        {
            "Container": "mp4,mov,m4v,mkv",
            "VideoCodec": "h264,hevc,h265",
            "AudioCodec": "aac,ac3,eac3,alac,mp3,flac",
            "Type": "Video",
        },
        {
            "Container": "mp3,aac,m4a,flac,wav,alac",
            "AudioCodec": "mp3,aac,alac,flac,pcm",
            "Type": "Audio",
        },
    ],
    "TranscodingProfiles": [
        {
            "Container": "ts",
            "Type": "Video",
            "VideoCodec": "h264",
            "AudioCodec": "aac",
            "Protocol": "hls",
            "Context": "Streaming",
            "MaxAudioChannels": "6",
            "SegmentLength": 6,
            "MinSegments": 1,
            "BreakOnNonKeyFrames": True,
        },
        {
            "Container": "mp3",
            "Type": "Audio",
            "AudioCodec": "aac",
            "Context": "Streaming",
        },
    ],
    "SubtitleProfiles": [
        {"Format": "srt", "Method": "External"},
        {"Format": "vtt", "Method": "External"},
        {"Format": "ass", "Method": "Encode"},
    ],
}

# =============================================================================
# Audio Only Profile - For speakers (Sonos, Google Home, etc.)
# =============================================================================

AUDIO_ONLY_PROFILE: Final[DeviceProfile] = {
    "Name": "Audio Only",
    "MaxStreamingBitrate": 10_000_000,  # 10 Mbps (audio doesn't need much)
    "MaxStaticBitrate": 20_000_000,
    "MusicStreamingTranscodingBitrate": 320_000,
    "DirectPlayProfiles": [
        {
            "Container": "mp3,aac,m4a,flac,wav,ogg,wma,alac",
            "AudioCodec": "mp3,aac,flac,vorbis,opus,wma,alac,pcm",
            "Type": "Audio",
        },
    ],
    "TranscodingProfiles": [
        {
            "Container": "mp3",
            "Type": "Audio",
            "AudioCodec": "mp3",
            "Context": "Streaming",
        },
        {
            "Container": "aac",
            "Type": "Audio",
            "AudioCodec": "aac",
            "Context": "Streaming",
        },
    ],
    "SubtitleProfiles": [],
}

# =============================================================================
# Profile Dictionary - For lookup by name
# =============================================================================

DEVICE_PROFILES: Final[dict[str, DeviceProfile]] = {
    "universal": UNIVERSAL_PROFILE,
    "chromecast": CHROMECAST_PROFILE,
    "roku": ROKU_PROFILE,
    "appletv": APPLETV_PROFILE,
    "audio_only": AUDIO_ONLY_PROFILE,
}


def get_device_profile(name: str) -> DeviceProfile:
    """Get a device profile by name.

    Args:
        name: Profile name (case-insensitive). One of:
            - "universal" (default)
            - "chromecast"
            - "roku"
            - "appletv"
            - "audio_only"

    Returns:
        The corresponding DeviceProfile. Returns UNIVERSAL_PROFILE
        if the name is not recognized.
    """
    return DEVICE_PROFILES.get(name.lower(), UNIVERSAL_PROFILE)
