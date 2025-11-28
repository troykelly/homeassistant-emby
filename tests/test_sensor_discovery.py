"""Tests for discovery sensor entities (Phase 15)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from custom_components.embymedia.const import DOMAIN
from custom_components.embymedia.coordinator_discovery import (
    EmbyDiscoveryCoordinator,
    EmbyDiscoveryData,
)
from custom_components.embymedia.sensor_discovery import (
    EmbyContinueWatchingSensor,
    EmbyNextUpSensor,
    EmbyRecentlyAddedSensor,
    EmbySuggestionsSensor,
)

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock Emby client."""
    client = MagicMock()
    client.get_image_url = MagicMock(
        side_effect=lambda item_id,
        image_type="Primary",
        max_width=None,
        max_height=None,
        tag=None: f"https://emby.local/Items/{item_id}/Images/{image_type}"
    )
    return client


@pytest.fixture
def mock_coordinator(mock_client: MagicMock) -> MagicMock:
    """Create a mock discovery coordinator."""
    coordinator = MagicMock(spec=EmbyDiscoveryCoordinator)
    coordinator.server_id = "server123"
    coordinator.server_name = "Emby Server"
    coordinator.user_id = "user456"
    coordinator.user_name = "testuser"
    coordinator.last_update_success = True
    coordinator.client = mock_client
    coordinator.data = EmbyDiscoveryData(
        next_up=[],
        continue_watching=[],
        recently_added=[],
        suggestions=[],
    )
    return coordinator


@pytest.fixture
def mock_coordinator_with_data(mock_client: MagicMock) -> MagicMock:
    """Create a mock coordinator with sample data."""
    coordinator = MagicMock(spec=EmbyDiscoveryCoordinator)
    coordinator.server_id = "server123"
    coordinator.server_name = "Emby Server"
    coordinator.user_id = "user456"
    coordinator.user_name = "testuser"
    coordinator.last_update_success = True
    coordinator.client = mock_client
    coordinator.data = EmbyDiscoveryData(
        next_up=[
            {
                "Id": "episode1",
                "Name": "The Next Episode",
                "Type": "Episode",
                "SeriesName": "Test Series",
                "SeriesId": "series1",
                "SeasonName": "Season 1",
                "IndexNumber": 5,
                "ParentIndexNumber": 1,
                "ImageTags": {"Primary": "tag1"},
                "SeriesPrimaryImageTag": "seriestag1",
            },
            {
                "Id": "episode2",
                "Name": "Another Episode",
                "Type": "Episode",
                "SeriesName": "Another Series",
                "SeriesId": "series2",
                "SeasonName": "Season 2",
                "IndexNumber": 3,
                "ParentIndexNumber": 2,
                "ImageTags": {},
            },
        ],
        continue_watching=[
            {
                "Id": "movie1",
                "Name": "Paused Movie",
                "Type": "Movie",
                "RunTimeTicks": 72000000000,
                "UserData": {"PlayedPercentage": 50.0},
                "ImageTags": {"Primary": "movietag1"},
            },
        ],
        recently_added=[
            {
                "Id": "new1",
                "Name": "New Movie",
                "Type": "Movie",
                "ProductionYear": 2024,
                "ImageTags": {"Primary": "newtag1"},
            },
            {
                "Id": "new2",
                "Name": "New Episode",
                "Type": "Episode",
                "SeriesName": "New Series",
                "SeriesId": "newseries1",
                "ImageTags": {},
            },
            {
                "Id": "new3",
                "Name": "New Song",
                "Type": "Audio",
                "ImageTags": {},
            },
        ],
        suggestions=[
            {
                "Id": "suggest1",
                "Name": "Suggested Movie",
                "Type": "Movie",
                "CommunityRating": 8.5,
                "ProductionYear": 2023,
                "ImageTags": {"Primary": "suggesttag1"},
            },
        ],
    )
    return coordinator


class TestEmbyNextUpSensor:
    """Tests for EmbyNextUpSensor."""

    def test_sensor_initialization(
        self,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test sensor initializes correctly."""
        sensor = EmbyNextUpSensor(mock_coordinator, "Emby Server")

        assert sensor._attr_unique_id == "server123_user456_next_up"
        assert sensor._attr_name == "testuser Next Up"
        assert sensor._attr_translation_key == "next_up"
        assert sensor._attr_icon == "mdi:television-play"

    def test_native_value_with_data(
        self,
        mock_coordinator_with_data: MagicMock,
    ) -> None:
        """Test native_value returns count when data present."""
        sensor = EmbyNextUpSensor(mock_coordinator_with_data, "Emby Server")

        assert sensor.native_value == 2

    def test_native_value_empty(
        self,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test native_value returns 0 when empty."""
        sensor = EmbyNextUpSensor(mock_coordinator, "Emby Server")

        assert sensor.native_value == 0

    def test_native_value_no_data(
        self,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test native_value returns None when no data."""
        mock_coordinator.data = None
        sensor = EmbyNextUpSensor(mock_coordinator, "Emby Server")

        assert sensor.native_value is None

    def test_extra_state_attributes(
        self,
        mock_coordinator_with_data: MagicMock,
    ) -> None:
        """Test extra_state_attributes contains item list."""
        sensor = EmbyNextUpSensor(mock_coordinator_with_data, "Emby Server")

        attrs = sensor.extra_state_attributes
        assert attrs is not None
        assert "items" in attrs
        assert "user_id" in attrs
        assert attrs["user_id"] == "user456"
        items = attrs["items"]
        assert len(items) == 2
        assert items[0]["id"] == "episode1"
        assert items[0]["name"] == "The Next Episode"
        assert items[0]["series_name"] == "Test Series"
        assert items[0]["series_id"] == "series1"
        assert items[0]["season_name"] == "Season 1"
        assert items[0]["episode_number"] == 5
        assert items[0]["season_number"] == 1
        # Image URLs - series image preferred for episodes
        assert items[0]["image_url"] == "https://emby.local/Items/series1/Images/Primary"
        assert items[0]["backdrop_url"] == "https://emby.local/Items/episode1/Images/Backdrop"
        # Second item has series_id so uses series image (no primary tag doesn't prevent series lookup)
        assert items[1]["image_url"] == "https://emby.local/Items/series2/Images/Primary"

    def test_available_when_coordinator_success(
        self,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test available returns True when coordinator successful."""
        sensor = EmbyNextUpSensor(mock_coordinator, "Emby Server")

        assert sensor.available is True

    def test_unavailable_when_coordinator_failed(
        self,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test available returns False when coordinator failed."""
        mock_coordinator.last_update_success = False
        sensor = EmbyNextUpSensor(mock_coordinator, "Emby Server")

        assert sensor.available is False

    def test_extra_state_attributes_no_data(
        self,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test extra_state_attributes returns None when no data."""
        mock_coordinator.data = None
        sensor = EmbyNextUpSensor(mock_coordinator, "Emby Server")

        assert sensor.extra_state_attributes is None


class TestEmbyContinueWatchingSensor:
    """Tests for EmbyContinueWatchingSensor."""

    def test_sensor_initialization(
        self,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test sensor initializes correctly."""
        sensor = EmbyContinueWatchingSensor(mock_coordinator, "Emby Server")

        assert sensor._attr_unique_id == "server123_user456_continue_watching"
        assert sensor._attr_name == "testuser Continue Watching"
        assert sensor._attr_translation_key == "continue_watching"
        assert sensor._attr_icon == "mdi:play-pause"

    def test_native_value_with_data(
        self,
        mock_coordinator_with_data: MagicMock,
    ) -> None:
        """Test native_value returns count when data present."""
        sensor = EmbyContinueWatchingSensor(mock_coordinator_with_data, "Emby Server")

        assert sensor.native_value == 1

    def test_extra_state_attributes(
        self,
        mock_coordinator_with_data: MagicMock,
    ) -> None:
        """Test extra_state_attributes contains item list with progress."""
        sensor = EmbyContinueWatchingSensor(mock_coordinator_with_data, "Emby Server")

        attrs = sensor.extra_state_attributes
        assert attrs is not None
        assert "items" in attrs
        assert "user_id" in attrs
        assert attrs["user_id"] == "user456"
        items = attrs["items"]
        assert len(items) == 1
        assert items[0]["id"] == "movie1"
        assert items[0]["name"] == "Paused Movie"
        assert items[0]["type"] == "Movie"
        assert items[0]["progress_percent"] == 50.0
        # Image URLs for movies
        assert items[0]["image_url"] == "https://emby.local/Items/movie1/Images/Primary"
        assert items[0]["backdrop_url"] == "https://emby.local/Items/movie1/Images/Backdrop"

    def test_native_value_no_data(
        self,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test native_value returns None when no data."""
        mock_coordinator.data = None
        sensor = EmbyContinueWatchingSensor(mock_coordinator, "Emby Server")

        assert sensor.native_value is None

    def test_extra_state_attributes_no_data(
        self,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test extra_state_attributes returns None when no data."""
        mock_coordinator.data = None
        sensor = EmbyContinueWatchingSensor(mock_coordinator, "Emby Server")

        assert sensor.extra_state_attributes is None


class TestEmbyRecentlyAddedSensor:
    """Tests for EmbyRecentlyAddedSensor."""

    def test_sensor_initialization(
        self,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test sensor initializes correctly."""
        sensor = EmbyRecentlyAddedSensor(mock_coordinator, "Emby Server")

        assert sensor._attr_unique_id == "server123_user456_recently_added"
        assert sensor._attr_name == "testuser Recently Added"
        assert sensor._attr_translation_key == "recently_added"
        assert sensor._attr_icon == "mdi:new-box"

    def test_native_value_with_data(
        self,
        mock_coordinator_with_data: MagicMock,
    ) -> None:
        """Test native_value returns count when data present."""
        sensor = EmbyRecentlyAddedSensor(mock_coordinator_with_data, "Emby Server")

        assert sensor.native_value == 3

    def test_extra_state_attributes(
        self,
        mock_coordinator_with_data: MagicMock,
    ) -> None:
        """Test extra_state_attributes contains item list."""
        sensor = EmbyRecentlyAddedSensor(mock_coordinator_with_data, "Emby Server")

        attrs = sensor.extra_state_attributes
        assert attrs is not None
        assert "items" in attrs
        assert "user_id" in attrs
        assert attrs["user_id"] == "user456"
        items = attrs["items"]
        assert len(items) == 3
        assert items[0]["id"] == "new1"
        assert items[0]["type"] == "Movie"
        # Image URLs
        assert items[0]["image_url"] == "https://emby.local/Items/new1/Images/Primary"
        assert items[0]["backdrop_url"] == "https://emby.local/Items/new1/Images/Backdrop"
        # Episode falls back to item image when no series tag
        assert items[1]["image_url"] == "https://emby.local/Items/newseries1/Images/Primary"

    def test_native_value_no_data(
        self,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test native_value returns None when no data."""
        mock_coordinator.data = None
        sensor = EmbyRecentlyAddedSensor(mock_coordinator, "Emby Server")

        assert sensor.native_value is None

    def test_extra_state_attributes_no_data(
        self,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test extra_state_attributes returns None when no data."""
        mock_coordinator.data = None
        sensor = EmbyRecentlyAddedSensor(mock_coordinator, "Emby Server")

        assert sensor.extra_state_attributes is None


class TestEmbySuggestionsSensor:
    """Tests for EmbySuggestionsSensor."""

    def test_sensor_initialization(
        self,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test sensor initializes correctly."""
        sensor = EmbySuggestionsSensor(mock_coordinator, "Emby Server")

        assert sensor._attr_unique_id == "server123_user456_suggestions"
        assert sensor._attr_name == "testuser Suggestions"
        assert sensor._attr_translation_key == "suggestions"
        assert sensor._attr_icon == "mdi:lightbulb"

    def test_native_value_with_data(
        self,
        mock_coordinator_with_data: MagicMock,
    ) -> None:
        """Test native_value returns count when data present."""
        sensor = EmbySuggestionsSensor(mock_coordinator_with_data, "Emby Server")

        assert sensor.native_value == 1

    def test_extra_state_attributes(
        self,
        mock_coordinator_with_data: MagicMock,
    ) -> None:
        """Test extra_state_attributes contains item list with ratings."""
        sensor = EmbySuggestionsSensor(mock_coordinator_with_data, "Emby Server")

        attrs = sensor.extra_state_attributes
        assert attrs is not None
        assert "items" in attrs
        assert "user_id" in attrs
        assert attrs["user_id"] == "user456"
        items = attrs["items"]
        assert len(items) == 1
        assert items[0]["id"] == "suggest1"
        assert items[0]["name"] == "Suggested Movie"
        assert items[0]["rating"] == 8.5
        # Image URLs
        assert items[0]["image_url"] == "https://emby.local/Items/suggest1/Images/Primary"
        assert items[0]["backdrop_url"] == "https://emby.local/Items/suggest1/Images/Backdrop"

    def test_native_value_no_data(
        self,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test native_value returns None when no data."""
        mock_coordinator.data = None
        sensor = EmbySuggestionsSensor(mock_coordinator, "Emby Server")

        assert sensor.native_value is None

    def test_extra_state_attributes_no_data(
        self,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test extra_state_attributes returns None when no data."""
        mock_coordinator.data = None
        sensor = EmbySuggestionsSensor(mock_coordinator, "Emby Server")

        assert sensor.extra_state_attributes is None


class TestDiscoverySensorDeviceInfo:
    """Test device info for discovery sensors."""

    def test_device_info(
        self,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test device_info returns correct structure."""
        sensor = EmbyNextUpSensor(mock_coordinator, "Emby Server")

        device_info = sensor.device_info
        assert device_info is not None
        assert device_info["identifiers"] == {(DOMAIN, "server123")}
        assert device_info["name"] == "Emby Server"
        assert device_info["manufacturer"] == "Emby"
        assert device_info["model"] == "Emby Server"


class TestImageUrlEdgeCases:
    """Test edge cases for image URL methods."""

    def test_get_image_url_with_none_item_id(
        self,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test _get_image_url returns None for empty item_id."""
        sensor = EmbyNextUpSensor(mock_coordinator, "Emby Server")
        result = sensor._get_image_url(None, {"Primary": "tag"})
        assert result is None

    def test_get_series_image_url_with_none_series_id(
        self,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test _get_series_image_url returns None for empty series_id."""
        sensor = EmbyNextUpSensor(mock_coordinator, "Emby Server")
        result = sensor._get_series_image_url(None, "seriestag")
        assert result is None

    def test_next_up_episode_fallback_to_item_image(
        self,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test Next Up falls back to episode image when no series image."""
        # Episode without series info should use item image
        mock_coordinator.data = EmbyDiscoveryData(
            next_up=[
                {
                    "Id": "episode1",
                    "Name": "Episode Name",
                    "Type": "Episode",
                    "SeriesId": None,
                    "ImageTags": {"Primary": "episodetag"},
                    "SeriesPrimaryImageTag": None,
                },
            ],
            continue_watching=[],
            recently_added=[],
            suggestions=[],
        )
        sensor = EmbyNextUpSensor(mock_coordinator, "Emby Server")
        attrs = sensor.extra_state_attributes
        # Should fall back to episode image
        assert attrs is not None
        assert attrs["items"][0]["image_url"] is not None

    def test_continue_watching_episode_with_series(
        self,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test Continue Watching uses series image for episodes."""
        mock_coordinator.data = EmbyDiscoveryData(
            next_up=[],
            continue_watching=[
                {
                    "Id": "episode1",
                    "Name": "Episode Name",
                    "Type": "Episode",
                    "SeriesId": "series1",
                    "SeriesName": "Test Series",
                    "ImageTags": {"Primary": "episodetag"},
                    "SeriesPrimaryImageTag": "seriestag",
                    "UserData": {"PlaybackPositionTicks": 100000000},
                },
            ],
            recently_added=[],
            suggestions=[],
        )
        sensor = EmbyContinueWatchingSensor(mock_coordinator, "Emby Server")
        attrs = sensor.extra_state_attributes
        assert attrs is not None
        # Should use series image for episodes
        assert "series1" in attrs["items"][0]["image_url"]

    def test_suggestions_series_type_without_series_id(
        self,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test Suggestions uses item image for Series without SeriesId."""
        mock_coordinator.data = EmbyDiscoveryData(
            next_up=[],
            continue_watching=[],
            recently_added=[],
            suggestions=[
                {
                    "Id": "series1",
                    "Name": "A Series",
                    "Type": "Series",
                    "SeriesId": None,
                    "ImageTags": {"Primary": "seriestag"},
                    "SeriesPrimaryImageTag": None,
                },
            ],
        )
        sensor = EmbySuggestionsSensor(mock_coordinator, "Emby Server")
        attrs = sensor.extra_state_attributes
        assert attrs is not None
        # Should use item image since no SeriesId
        assert "series1" in attrs["items"][0]["image_url"]

    def test_suggestions_episode_with_series_id(
        self,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test Suggestions uses series image for Episode with SeriesId."""
        mock_coordinator.data = EmbyDiscoveryData(
            next_up=[],
            continue_watching=[],
            recently_added=[],
            suggestions=[
                {
                    "Id": "episode1",
                    "Name": "An Episode",
                    "Type": "Episode",
                    "SeriesId": "parent_series",
                    "ImageTags": {"Primary": "episodetag"},
                    "SeriesPrimaryImageTag": "seriestag",
                },
            ],
        )
        sensor = EmbySuggestionsSensor(mock_coordinator, "Emby Server")
        attrs = sensor.extra_state_attributes
        assert attrs is not None
        # Should use series image for episodes with SeriesId
        assert "parent_series" in attrs["items"][0]["image_url"]
