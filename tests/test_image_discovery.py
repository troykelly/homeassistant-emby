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
    coordinator.client = MagicMock()
    coordinator.client.get_image_url = MagicMock(
        side_effect=lambda item_id,
        image_type="Primary",
        max_width=None,
        max_height=None,
        tag=None: f"https://emby.local/Items/{item_id}/Images/{image_type}?tag={tag}"
    )
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

    def test_no_image_when_empty_data(
        self,
        mock_hass: MagicMock,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test _current_image_id is None when no data."""
        image = EmbyNextUpImage(mock_hass, mock_coordinator, "Emby Server")
        assert image._current_image_id is None

    def test_image_id_with_data(
        self,
        mock_hass: MagicMock,
        mock_coordinator_with_data: MagicMock,
    ) -> None:
        """Test image uses series ID for episodes."""
        image = EmbyNextUpImage(mock_hass, mock_coordinator_with_data, "Emby Server")
        # For episodes, should use series image
        target_id, tag = image._get_image_info()
        assert target_id == "series1"
        assert tag == "seriestag1"

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

    def test_coordinator_update_detects_change(
        self,
        mock_hass: MagicMock,
        mock_coordinator_with_data: MagicMock,
    ) -> None:
        """Test that coordinator update detects image changes."""
        image = EmbyNextUpImage(mock_hass, mock_coordinator_with_data, "Emby Server")
        old_image_id = image._current_image_id

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

        # Manually test the image info update logic
        new_target_id, new_tag = image._get_image_info()
        assert new_target_id != old_image_id
        assert new_target_id == "series2"
        assert new_tag == "newseriestag"


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

    def test_image_info_for_movie(
        self,
        mock_hass: MagicMock,
        mock_coordinator_with_data: MagicMock,
    ) -> None:
        """Test image info for movie uses item image."""
        image = EmbyContinueWatchingImage(mock_hass, mock_coordinator_with_data, "Emby Server")
        # Movies use their own primary image
        target_id, tag = image._get_image_info()
        assert target_id == "movie1"
        assert tag == "movietag1"


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

    def test_image_info_with_data(
        self,
        mock_hass: MagicMock,
        mock_coordinator_with_data: MagicMock,
    ) -> None:
        """Test image info for recently added."""
        image = EmbyRecentlyAddedImage(mock_hass, mock_coordinator_with_data, "Emby Server")
        target_id, tag = image._get_image_info()
        assert target_id == "new1"
        assert tag == "newtag1"


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

    def test_image_info_with_data(
        self,
        mock_hass: MagicMock,
        mock_coordinator_with_data: MagicMock,
    ) -> None:
        """Test image info for suggestions."""
        image = EmbySuggestionsImage(mock_hass, mock_coordinator_with_data, "Emby Server")
        target_id, tag = image._get_image_info()
        assert target_id == "suggest1"
        assert tag == "suggesttag1"


class TestDiscoveryImageNoData:
    """Test image entities handle no data gracefully."""

    def test_no_coordinator_data(
        self,
        mock_hass: MagicMock,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test image_id is None when coordinator.data is None."""
        mock_coordinator.data = None
        image = EmbyNextUpImage(mock_hass, mock_coordinator, "Emby Server")
        assert image._current_image_id is None

    def test_available_when_no_data(
        self,
        mock_hass: MagicMock,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test entity is available when coordinator successful."""
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

    def test_item_with_empty_id(
        self,
        mock_hass: MagicMock,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test _get_image_info returns None when item has empty Id."""
        mock_coordinator.data = EmbyDiscoveryData(
            next_up=[{"Id": "", "Name": "Test"}],
            continue_watching=[],
            recently_added=[],
            suggestions=[],
        )
        image = EmbyNextUpImage(mock_hass, mock_coordinator, "Emby Server")
        target_id, tag = image._get_image_info()
        assert target_id is None
        assert tag is None


class TestAsyncImage:
    """Test async_image method."""

    @pytest.mark.asyncio
    async def test_async_image_success(
        self,
        mock_hass: MagicMock,
        mock_coordinator_with_data: MagicMock,
    ) -> None:
        """Test async_image returns bytes on success."""
        from unittest.mock import AsyncMock, patch

        image = EmbyNextUpImage(mock_hass, mock_coordinator_with_data, "Emby Server")

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"Content-Type": "image/png"}
        mock_response.read = AsyncMock(return_value=b"fake image data")

        mock_session = MagicMock()
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context)

        with patch(
            "custom_components.embymedia.image_discovery.async_get_clientsession",
            return_value=mock_session,
        ):
            result = await image.async_image()

        assert result == b"fake image data"
        assert image._attr_content_type == "image/png"

    @pytest.mark.asyncio
    async def test_async_image_no_target_id(
        self,
        mock_hass: MagicMock,
        mock_coordinator: MagicMock,
    ) -> None:
        """Test async_image returns None when no target_id."""
        image = EmbyNextUpImage(mock_hass, mock_coordinator, "Emby Server")
        result = await image.async_image()
        assert result is None

    @pytest.mark.asyncio
    async def test_async_image_http_error(
        self,
        mock_hass: MagicMock,
        mock_coordinator_with_data: MagicMock,
    ) -> None:
        """Test async_image returns None on HTTP error."""
        from unittest.mock import AsyncMock, patch

        image = EmbyNextUpImage(mock_hass, mock_coordinator_with_data, "Emby Server")

        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.headers = {}

        mock_session = MagicMock()
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context)

        with patch(
            "custom_components.embymedia.image_discovery.async_get_clientsession",
            return_value=mock_session,
        ):
            result = await image.async_image()

        assert result is None

    @pytest.mark.asyncio
    async def test_async_image_exception(
        self,
        mock_hass: MagicMock,
        mock_coordinator_with_data: MagicMock,
    ) -> None:
        """Test async_image returns None on network exception."""
        from unittest.mock import AsyncMock, patch

        import aiohttp

        image = EmbyNextUpImage(mock_hass, mock_coordinator_with_data, "Emby Server")

        mock_session = MagicMock()
        mock_context = AsyncMock()
        # Use specific exception type that is caught by the handler
        mock_context.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("Connection failed"))
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context)

        with patch(
            "custom_components.embymedia.image_discovery.async_get_clientsession",
            return_value=mock_session,
        ):
            result = await image.async_image()

        assert result is None


class TestHandleCoordinatorUpdate:
    """Test _handle_coordinator_update method."""

    def test_coordinator_update_no_change(
        self,
        mock_hass: MagicMock,
        mock_coordinator_with_data: MagicMock,
    ) -> None:
        """Test coordinator update when image doesn't change."""
        from unittest.mock import patch

        from homeassistant.helpers.update_coordinator import CoordinatorEntity

        image = EmbyNextUpImage(mock_hass, mock_coordinator_with_data, "Emby Server")
        old_timestamp = image._attr_image_last_updated
        old_image_id = image._current_image_id

        # Mock the super()._handle_coordinator_update to avoid hass issues
        with patch.object(
            CoordinatorEntity,
            "_handle_coordinator_update",
            return_value=None,
        ):
            # Call update without changing data - image should stay the same
            image._handle_coordinator_update()

        # Timestamp should not change since image didn't change
        assert image._attr_image_last_updated == old_timestamp
        assert image._current_image_id == old_image_id

    def test_coordinator_update_image_changed(
        self,
        mock_hass: MagicMock,
        mock_coordinator_with_data: MagicMock,
    ) -> None:
        """Test coordinator update when image changes."""
        from unittest.mock import patch

        from homeassistant.helpers.update_coordinator import CoordinatorEntity

        image = EmbyNextUpImage(mock_hass, mock_coordinator_with_data, "Emby Server")
        old_timestamp = image._attr_image_last_updated

        # Change the data to a different series
        mock_coordinator_with_data.data = EmbyDiscoveryData(
            next_up=[
                {
                    "Id": "episode999",
                    "Name": "New Episode",
                    "Type": "Episode",
                    "SeriesId": "newseries",
                    "ImageTags": {"Primary": "newtag"},
                    "SeriesPrimaryImageTag": "newseriestag",
                },
            ],
            continue_watching=[],
            recently_added=[],
            suggestions=[],
        )

        # Mock the super()._handle_coordinator_update to avoid hass issues
        with patch.object(
            CoordinatorEntity,
            "_handle_coordinator_update",
            return_value=None,
        ):
            # Call update - image should change
            image._handle_coordinator_update()

        # Timestamp should change and cached image should be cleared
        assert image._current_image_id == "newseries"
        assert image._attr_image_last_updated != old_timestamp
