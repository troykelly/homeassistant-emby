"""Tests for Phase 12 sensor TypedDicts and API methods."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.embymedia.const import (
    EmbyItemCounts,
    EmbyScheduledTask,
    EmbyScheduledTaskResult,
    EmbyVirtualFolder,
    EmbyVirtualFolderLocation,
)

if TYPE_CHECKING:
    pass


class TestEmbyItemCountsTypedDict:
    """Tests for EmbyItemCounts TypedDict."""

    def test_item_counts_structure(self) -> None:
        """Test EmbyItemCounts can be instantiated with correct fields."""
        counts: EmbyItemCounts = {
            "MovieCount": 1209,
            "SeriesCount": 374,
            "EpisodeCount": 4620,
            "ArtistCount": 500,
            "AlbumCount": 800,
            "SongCount": 14341,
            "GameCount": 0,
            "GameSystemCount": 0,
            "TrailerCount": 10,
            "MusicVideoCount": 25,
            "BoxSetCount": 15,
            "BookCount": 100,
            "ItemCount": 21994,
        }

        assert counts["MovieCount"] == 1209
        assert counts["SeriesCount"] == 374
        assert counts["EpisodeCount"] == 4620
        assert counts["ArtistCount"] == 500
        assert counts["AlbumCount"] == 800
        assert counts["SongCount"] == 14341
        assert counts["ItemCount"] == 21994

    def test_item_counts_required_fields(self) -> None:
        """Test that all required fields are present."""
        # All fields in EmbyItemCounts should be required
        minimal_counts: EmbyItemCounts = {
            "MovieCount": 0,
            "SeriesCount": 0,
            "EpisodeCount": 0,
            "ArtistCount": 0,
            "AlbumCount": 0,
            "SongCount": 0,
            "GameCount": 0,
            "GameSystemCount": 0,
            "TrailerCount": 0,
            "MusicVideoCount": 0,
            "BoxSetCount": 0,
            "BookCount": 0,
            "ItemCount": 0,
        }

        assert minimal_counts["MovieCount"] == 0
        assert minimal_counts["ItemCount"] == 0


class TestEmbyScheduledTaskTypedDict:
    """Tests for EmbyScheduledTask TypedDict."""

    def test_scheduled_task_idle(self) -> None:
        """Test EmbyScheduledTask for an idle task."""
        task: EmbyScheduledTask = {
            "Name": "Scan media library",
            "State": "Idle",
            "Id": "task-123",
            "Description": "Scans all libraries for new content",
            "Category": "Library",
            "IsHidden": False,
            "Key": "RefreshLibrary",
            "Triggers": [],
        }

        assert task["Name"] == "Scan media library"
        assert task["State"] == "Idle"
        assert task["Id"] == "task-123"
        assert task["IsHidden"] is False

    def test_scheduled_task_running_with_progress(self) -> None:
        """Test EmbyScheduledTask for a running task with progress."""
        task: EmbyScheduledTask = {
            "Name": "Scan media library",
            "State": "Running",
            "Id": "task-123",
            "Description": "Scans all libraries for new content",
            "Category": "Library",
            "IsHidden": False,
            "Key": "RefreshLibrary",
            "Triggers": [],
            "CurrentProgressPercentage": 45.5,
        }

        assert task["State"] == "Running"
        assert task["CurrentProgressPercentage"] == 45.5

    def test_scheduled_task_with_last_result(self) -> None:
        """Test EmbyScheduledTask with last execution result."""
        result: EmbyScheduledTaskResult = {
            "StartTimeUtc": "2024-01-15T10:00:00Z",
            "EndTimeUtc": "2024-01-15T10:30:00Z",
            "Status": "Completed",
            "Name": "Scan media library",
            "Key": "RefreshLibrary",
            "Id": "result-456",
        }

        task: EmbyScheduledTask = {
            "Name": "Scan media library",
            "State": "Idle",
            "Id": "task-123",
            "Description": "Scans all libraries for new content",
            "Category": "Library",
            "IsHidden": False,
            "Key": "RefreshLibrary",
            "Triggers": [],
            "LastExecutionResult": result,
        }

        assert task["LastExecutionResult"]["Status"] == "Completed"
        assert task["LastExecutionResult"]["StartTimeUtc"] == "2024-01-15T10:00:00Z"


class TestEmbyVirtualFolderTypedDict:
    """Tests for EmbyVirtualFolder TypedDict."""

    def test_virtual_folder_basic(self) -> None:
        """Test EmbyVirtualFolder basic structure."""
        folder: EmbyVirtualFolder = {
            "Name": "Movies",
            "ItemId": "lib-movies-123",
            "CollectionType": "movies",
            "Locations": ["/media/movies"],
        }

        assert folder["Name"] == "Movies"
        assert folder["ItemId"] == "lib-movies-123"
        assert folder["CollectionType"] == "movies"
        assert folder["Locations"] == ["/media/movies"]

    def test_virtual_folder_with_refresh_status(self) -> None:
        """Test EmbyVirtualFolder with refresh status."""
        folder: EmbyVirtualFolder = {
            "Name": "TV Shows",
            "ItemId": "lib-tv-456",
            "CollectionType": "tvshows",
            "Locations": ["/media/tv", "/media/tv2"],
            "RefreshProgress": 67.3,
            "RefreshStatus": "Active",
        }

        assert folder["RefreshProgress"] == 67.3
        assert folder["RefreshStatus"] == "Active"
        assert len(folder["Locations"]) == 2

    def test_virtual_folder_music(self) -> None:
        """Test EmbyVirtualFolder for music library."""
        folder: EmbyVirtualFolder = {
            "Name": "Music",
            "ItemId": "lib-music-789",
            "CollectionType": "music",
            "Locations": ["/media/music"],
        }

        assert folder["CollectionType"] == "music"


class TestEmbyVirtualFolderLocationTypedDict:
    """Tests for EmbyVirtualFolderLocation TypedDict."""

    def test_location_structure(self) -> None:
        """Test EmbyVirtualFolderLocation structure."""
        location: EmbyVirtualFolderLocation = {
            "Path": "/media/movies",
        }

        assert location["Path"] == "/media/movies"
