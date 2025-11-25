"""Media browsing utilities for Emby integration."""

from __future__ import annotations

from homeassistant.components.media_player import MediaClass

# Mapping from Emby item types to Home Assistant MediaClass
_EMBY_TYPE_TO_MEDIA_CLASS: dict[str, MediaClass] = {
    "Movie": MediaClass.MOVIE,
    "Series": MediaClass.TV_SHOW,
    "Season": MediaClass.SEASON,
    "Episode": MediaClass.EPISODE,
    "Audio": MediaClass.TRACK,
    "MusicAlbum": MediaClass.ALBUM,
    "MusicArtist": MediaClass.ARTIST,
    "Playlist": MediaClass.PLAYLIST,
    "TvChannel": MediaClass.CHANNEL,
    "CollectionFolder": MediaClass.DIRECTORY,
    "Folder": MediaClass.DIRECTORY,
}

# Emby types that are directly playable
_PLAYABLE_TYPES: frozenset[str] = frozenset(
    {
        "Movie",
        "Episode",
        "Audio",
        "TvChannel",
        "MusicVideo",
        "Trailer",
    }
)

# Emby types that can be expanded (have children)
_EXPANDABLE_TYPES: frozenset[str] = frozenset(
    {
        "Series",
        "Season",
        "MusicAlbum",
        "MusicArtist",
        "Playlist",
        "CollectionFolder",
        "Folder",
    }
)


def encode_content_id(content_type: str, *ids: str) -> str:
    """Encode content type and IDs into a content_id string.

    Args:
        content_type: The type of content (library, series, season, etc.).
        ids: Variable number of IDs to include.

    Returns:
        Encoded content ID string in format "type:id1:id2:...".

    Examples:
        >>> encode_content_id("library", "abc123")
        'library:abc123'
        >>> encode_content_id("season", "series1", "season1")
        'season:series1:season1'
    """
    if ids:
        return f"{content_type}:{':'.join(ids)}"
    return content_type


def decode_content_id(content_id: str) -> tuple[str, list[str]]:
    """Decode content_id string into type and ID parts.

    Args:
        content_id: Encoded content ID string.

    Returns:
        Tuple of (content_type, list_of_ids).

    Examples:
        >>> decode_content_id("library:abc123")
        ('library', ['abc123'])
        >>> decode_content_id("season:series1:season1")
        ('season', ['series1', 'season1'])
        >>> decode_content_id("root")
        ('root', [])
    """
    parts = content_id.split(":")
    content_type = parts[0]
    ids = parts[1:] if len(parts) > 1 else []
    return content_type, ids


def emby_type_to_media_class(emby_type: str) -> MediaClass:
    """Map Emby item type to Home Assistant MediaClass.

    Args:
        emby_type: The Emby item type (Movie, Series, Episode, etc.).

    Returns:
        Corresponding HA MediaClass, defaults to DIRECTORY for unknown types.
    """
    return _EMBY_TYPE_TO_MEDIA_CLASS.get(emby_type, MediaClass.DIRECTORY)


def can_play_emby_type(emby_type: str) -> bool:
    """Check if an Emby item type is directly playable.

    Args:
        emby_type: The Emby item type.

    Returns:
        True if the item can be played directly.
    """
    return emby_type in _PLAYABLE_TYPES


def can_expand_emby_type(emby_type: str) -> bool:
    """Check if an Emby item type can be expanded (has children).

    Args:
        emby_type: The Emby item type.

    Returns:
        True if the item can be expanded to show children.
    """
    return emby_type in _EXPANDABLE_TYPES


__all__ = [
    "can_expand_emby_type",
    "can_play_emby_type",
    "decode_content_id",
    "emby_type_to_media_class",
    "encode_content_id",
]
