"""Unit-tests for :pymod:`custom_components.embymedia.id_helpers` (issue #161)."""

from __future__ import annotations

import pytest


from custom_components.embymedia.id_helpers import decode_item_id, encode_item_id


# ---------------------------------------------------------------------------
# Round-trip property – typed vs. legacy variant
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "media_type,item_id",
    [
        ("Movie", "12345"),
        ("TvChannel", "channel 9"),  # whitespace → percent-encoded
        (None, "abc-def"),  # legacy (no type)
    ],
)
def test_encode_decode_roundtrip(media_type, item_id):  # noqa: D401 – tests keep camelCase naming
    uri = encode_item_id(item_id, media_type=media_type)

    decoded_type, decoded_id = decode_item_id(uri)

    assert decoded_id == item_id
    assert decoded_type == media_type


# ---------------------------------------------------------------------------
# Concrete string expectations to guard against behavioural drift
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "media_type,item_id,expected_uri",
    [
        ("Movie", "123", "emby://Movie/123"),
        (None, "xyz", "emby://xyz"),
        ("MusicAlbum", "The Wall", "emby://MusicAlbum/The%20Wall"),
    ],
)
def test_encode_expected_formats(media_type, item_id, expected_uri):  # noqa: D401
    assert encode_item_id(item_id, media_type=media_type) == expected_uri


# ---------------------------------------------------------------------------
# Validation – broken inputs must raise ValueError
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "http://not-emby/id",
        "emby://",  # missing id
        "",
    ],
)
def test_decode_invalid(value):  # noqa: D401
    with pytest.raises(ValueError):
        decode_item_id(value)
