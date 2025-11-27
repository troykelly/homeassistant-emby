"""Tests for discovery image entities (Phase 15)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from homeassistant.components.image import ImageEntity

from custom_components.embymedia.const import DOMAIN
from custom_components.embymedia.coordinator_discovery import (
    EmbyDiscoveryCoordinator,
    EmbyDiscoveryData,
)
from custom_components.embymedia.image_discovery import (
    EmbyContinueWatchingImage,
    EmbyNextUpImage,
    EmbyRecentlyAddedImage,
    EmbySuggestionsImage,
)

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_hass() -> MagicMock:
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.config.api = MagicMock()
    hass.config.api.base_url = "http://localhost:8123"
    return hass


@pytest.fixture
def mock_coordinator() -> MagicMock:
    """Create a mock discovery coordinator."""
    coordinator = MagicMock(spec=EmbyDiscoveryCoordinator)
    coordinator.server_id = "server123"
    coordinator.server_name = "Emby Server"
    coordinator.user_id = "user456"
    coordinator.user_name = "testuser"
    coordinator.last_update_success = True
    coordinator.data = EmbyDiscoveryData(
        next_up=[],
        continue_watching=[],
        recently_added=[],
        suggestions=[],
    )
    return coordinator


@pytest.fixture
def mock_coordinator_with_data() -> MagicMock:
    """Create a mock coordinator with sample data."""
    coordinator = MagicMock(spec=EmbyDiscoveryCoordinator)
    coordinator.server_id = "server123"
    coordinator.server_name = "Emby Server"
    coordinator.user_id = "user456"
    coordinator.user_name = "testuser"
    coordinator.last_update_success = True
    coordinator.data = EmbyDiscoveryData(
        next_up=[
            {
                "Id": "episode1",
                "Name": "The Next Episode",
                "Type": "Episode",
                "SeriesName": "Test Series",
                "SeriesId": "series1",
                "ImageTags": {"Primary": "tag1"},
                "SeriesPrimaryImageTag": "seriestag1",
            },
        ],
        continue_watching=[
            {
                "Id": "movie1",
                "Name": "Paused Movie",
                "Type": "Movie",
                "ImageTags": {"Primary": "movietag1"},
            },
        ],
        recently_added=[
            {
                "Id": "new1",
                "Name": "New Movie",
                "Type": "Movie",
                "ImageTags": {"Primary": "newtag1"},
            },
        ],
        suggestions=[
            {
                "Id": "suggest1",
                "Name": "Suggested Movie",
                "Type": "Movie",
                "ImageTags": {"Primary": "suggesttag1"},
            },
        ],
    )
    return coordinator


class TestEmbyNextUpImage:
    """Tests for EmbyNextUpImage."""

    def test_is_image_entity(
        self,
        mock_hass: MagicMock,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test that it's an ImageEntity."""
        image = EmbyNextUpImage(mock_hass, mock_coordinator, "Emby Server")
        assert isinstance(image, ImageEntity)

    def test_unique_id(
        self,
        mock_hass: MagicMock,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test unique_id format."""
        image = EmbyNextUpImage(mock_hass, mock_coordinator, "Emby Server")
        assert image._attr_unique_id == "server123_user456_next_up_image"

    def test_name(
        self,
        mock_hass: MagicMock,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test entity name includes user name."""
        image = EmbyNextUpImage(mock_hass, mock_coordinator, "Emby Server")
        assert image._attr_name == "testuser Next Up"

    def test_image_url_empty_data(
        self,
        mock_hass: MagicMock,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test image_url is None when no data."""
        image = EmbyNextUpImage(mock_hass, mock_coordinator, "Emby Server")
        assert image._attr_image_url is None

    def test_image_url_with_data(
        self,
        mock_hass: MagicMock,
        mock_coordinator_with_data: MagicMock,
    ) -> None:
        """Test image_url points to proxy with first item."""
        image = EmbyNextUpImage(mock_hass, mock_coordinator_with_data, "Emby Server")
        # For episodes, should use series image
        expected_url = "/api/embymedia/image/server123/series1/Primary?maxWidth=300&maxHeight=450&tag=seriestag1"
        assert image._attr_image_url == expected_url

    def test_image_last_updated_set(
        self,
        mock_hass: MagicMock,
        mock_coordinator_with_data: MagicMock,
    ) -> None:
        """Test image_last_updated is set."""
        image = EmbyNextUpImage(mock_hass, mock_coordinator_with_data, "Emby Server")
        assert image._attr_image_last_updated is not None
        assert isinstance(image._attr_image_last_updated, datetime)

    def test_device_info(
        self,
        mock_hass: MagicMock,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test device_info links to server."""
        image = EmbyNextUpImage(mock_hass, mock_coordinator, "Emby Server")
        device_info = image.device_info
        assert device_info is not None
        assert device_info["identifiers"] == {(DOMAIN, "server123")}
        assert device_info["name"] == "Emby Server"

    def test_coordinator_update_changes_url(
        self,
        mock_hass: MagicMock,
        mock_coordinator_with_data: MagicMock,
    ) -> None:
        """Test that coordinator update changes image URL when data changes."""
        image = EmbyNextUpImage(mock_hass, mock_coordinator_with_data, "Emby Server")
        old_url = image._attr_image_url

        # Change the data
        mock_coordinator_with_data.data = EmbyDiscoveryData(
            next_up=[
                {
                    "Id": "episode2",
                    "Name": "Different Episode",
                    "Type": "Episode",
                    "SeriesId": "series2",
                    "ImageTags": {"Primary": "newtag"},
                    "SeriesPrimaryImageTag": "newseriestag",
                },
            ],
            continue_watching=[],
            recently_added=[],
            suggestions=[],
        )

        # Manually test the URL update logic (without calling parent which needs full HA context)
        new_url = image._get_image_url()
        assert new_url != old_url
        assert "series2" in str(new_url)
        assert "newseriestag" in str(new_url)


class TestEmbyContinueWatchingImage:
    """Tests for EmbyContinueWatchingImage."""

    def test_unique_id(
        self,
        mock_hass: MagicMock,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test unique_id format."""
        image = EmbyContinueWatchingImage(mock_hass, mock_coordinator, "Emby Server")
        assert image._attr_unique_id == "server123_user456_continue_watching_image"

    def test_image_url_with_movie(
        self,
        mock_hass: MagicMock,
        mock_coordinator_with_data: MagicMock,
    ) -> None:
        """Test image_url for movie uses item image."""
        image = EmbyContinueWatchingImage(mock_hass, mock_coordinator_with_data, "Emby Server")
        # Movies use their own primary image
        expected_url = (
            "/api/embymedia/image/server123/movie1/Primary?maxWidth=300&maxHeight=450&tag=movietag1"
        )
        assert image._attr_image_url == expected_url


class TestEmbyRecentlyAddedImage:
    """Tests for EmbyRecentlyAddedImage."""

    def test_unique_id(
        self,
        mock_hass: MagicMock,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test unique_id format."""
        image = EmbyRecentlyAddedImage(mock_hass, mock_coordinator, "Emby Server")
        assert image._attr_unique_id == "server123_user456_recently_added_image"

    def test_image_url_with_data(
        self,
        mock_hass: MagicMock,
        mock_coordinator_with_data: MagicMock,
    ) -> None:
        """Test image_url for recently added."""
        image = EmbyRecentlyAddedImage(mock_hass, mock_coordinator_with_data, "Emby Server")
        expected_url = (
            "/api/embymedia/image/server123/new1/Primary?maxWidth=300&maxHeight=450&tag=newtag1"
        )
        assert image._attr_image_url == expected_url


class TestEmbySuggestionsImage:
    """Tests for EmbySuggestionsImage."""

    def test_unique_id(
        self,
        mock_hass: MagicMock,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test unique_id format."""
        image = EmbySuggestionsImage(mock_hass, mock_coordinator, "Emby Server")
        assert image._attr_unique_id == "server123_user456_suggestions_image"

    def test_image_url_with_data(
        self,
        mock_hass: MagicMock,
        mock_coordinator_with_data: MagicMock,
    ) -> None:
        """Test image_url for suggestions."""
        image = EmbySuggestionsImage(mock_hass, mock_coordinator_with_data, "Emby Server")
        expected_url = "/api/embymedia/image/server123/suggest1/Primary?maxWidth=300&maxHeight=450&tag=suggesttag1"
        assert image._attr_image_url == expected_url


class TestDiscoveryImageNoData:
    """Test image entities handle no data gracefully."""

    def test_no_coordinator_data(
        self,
        mock_hass: MagicMock,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test image_url is None when coordinator.data is None."""
        mock_coordinator.data = None
        image = EmbyNextUpImage(mock_hass, mock_coordinator, "Emby Server")
        assert image._attr_image_url is None

    def test_available_when_no_data(
        self,
        mock_hass: MagicMock,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test entity is unavailable when no data."""
        mock_coordinator.data = None
        mock_coordinator.last_update_success = True
        image = EmbyNextUpImage(mock_hass, mock_coordinator, "Emby Server")
        # Should still be available even without image data
        assert image.available is True

    def test_unavailable_when_coordinator_failed(
        self,
        mock_hass: MagicMock,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test entity is unavailable when coordinator failed."""
        mock_coordinator.last_update_success = False
        image = EmbyNextUpImage(mock_hass, mock_coordinator, "Emby Server")
        assert image.available is False
