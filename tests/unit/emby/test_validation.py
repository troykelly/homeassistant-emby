"""Validation tests for the *play_media* service payload schema."""

from __future__ import annotations

import pytest

from custom_components.embymedia.media_player import PLAY_MEDIA_SCHEMA


def test_schema_accepts_minimal_payload():
    """A minimal valid payload (type + id) must pass."""

    data = {"media_type": "movie", "media_id": "some-id"}
    validated = PLAY_MEDIA_SCHEMA(data)
    assert validated == {"media_type": "movie", "media_id": "some-id", "enqueue": False}


@pytest.mark.parametrize(
    "payload",
    [
        {},  # missing everything
        {"media_type": "movie"},  # missing id
        {"media_id": "abc"},  # missing type
        {"media_type": "movie", "media_id": "x", "enqueue": "maybe"},  # unparseable bool
        {"media_type": "movie", "media_id": "x", "position": -5},  # negative seek
    ],
)
def test_schema_rejects_invalid(payload):
    """Payloads that do not meet the schema raise *vol.Invalid*."""

    import voluptuous as vol

    with pytest.raises(vol.Invalid):
        PLAY_MEDIA_SCHEMA(payload)
