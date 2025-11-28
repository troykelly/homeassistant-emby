"""Tests for Activity Log TypedDicts in const.py.

Phase 18: User Activity & Statistics
"""

from __future__ import annotations

from typing import TYPE_CHECKING, get_type_hints

if TYPE_CHECKING:
    pass


class TestActivityLogTypedDicts:
    """Tests for Activity Log TypedDicts."""

    def test_emby_activity_log_entry_exists(self) -> None:
        """Test EmbyActivityLogEntry TypedDict is defined."""
        from custom_components.embymedia.const import EmbyActivityLogEntry

        # TypedDict should be importable
        assert EmbyActivityLogEntry is not None

    def test_emby_activity_log_entry_has_required_fields(self) -> None:
        """Test EmbyActivityLogEntry has required fields from API."""
        from custom_components.embymedia.const import EmbyActivityLogEntry

        hints = get_type_hints(EmbyActivityLogEntry)

        # Based on actual API response:
        # {"Id":6612,"Name":"Recording of...","Type":"livetv.recordingerror",
        #  "Date":"2025-11-28T10:00:37.8370000Z","Severity":"Error"}
        assert "Id" in hints
        assert "Name" in hints
        assert "Type" in hints
        assert "Date" in hints
        assert "Severity" in hints

    def test_emby_activity_log_entry_has_optional_fields(self) -> None:
        """Test EmbyActivityLogEntry has optional fields from API."""
        from custom_components.embymedia.const import EmbyActivityLogEntry

        hints = get_type_hints(EmbyActivityLogEntry)

        # Optional fields from API (may not be present):
        # "UserId", "UserPrimaryImageTag", "ItemId", "Overview", "ShortOverview"
        assert "UserId" in hints
        assert "ItemId" in hints
        assert "UserPrimaryImageTag" in hints
        assert "Overview" in hints
        assert "ShortOverview" in hints

    def test_emby_activity_log_entry_field_types(self) -> None:
        """Test EmbyActivityLogEntry field types are correct."""
        from custom_components.embymedia.const import EmbyActivityLogEntry

        hints = get_type_hints(EmbyActivityLogEntry)

        # Id is int in Emby (unlike other IDs which are strings)
        assert hints["Id"] is int
        assert hints["Name"] is str
        assert hints["Type"] is str
        assert hints["Date"] is str
        assert hints["Severity"] is str
        assert hints["UserId"] is str
        assert hints["ItemId"] is str

    def test_emby_activity_log_response_exists(self) -> None:
        """Test EmbyActivityLogResponse TypedDict is defined."""
        from custom_components.embymedia.const import EmbyActivityLogResponse

        assert EmbyActivityLogResponse is not None

    def test_emby_activity_log_response_has_fields(self) -> None:
        """Test EmbyActivityLogResponse has required fields."""
        from custom_components.embymedia.const import EmbyActivityLogResponse

        hints = get_type_hints(EmbyActivityLogResponse)

        # Based on actual API response:
        # {"Items":[...],"TotalRecordCount":6612}
        assert "Items" in hints
        assert "TotalRecordCount" in hints

    def test_emby_activity_log_response_items_type(self) -> None:
        """Test EmbyActivityLogResponse.Items is list of EmbyActivityLogEntry."""
        from custom_components.embymedia.const import (
            EmbyActivityLogEntry,
            EmbyActivityLogResponse,
        )

        hints = get_type_hints(EmbyActivityLogResponse)

        # Items should be list[EmbyActivityLogEntry]
        assert hints["Items"] == list[EmbyActivityLogEntry]

    def test_emby_activity_log_entry_can_be_created(self) -> None:
        """Test EmbyActivityLogEntry can be instantiated with valid data."""
        from custom_components.embymedia.const import EmbyActivityLogEntry

        # Based on actual API response
        entry: EmbyActivityLogEntry = {
            "Id": 6612,
            "Name": "Recording of BBC News has failed on media",
            "Type": "livetv.recordingerror",
            "Date": "2025-11-28T10:00:37.8370000Z",
            "Severity": "Error",
        }

        assert entry["Id"] == 6612
        assert entry["Type"] == "livetv.recordingerror"
        assert entry["Severity"] == "Error"

    def test_emby_activity_log_entry_with_optional_fields(self) -> None:
        """Test EmbyActivityLogEntry with all optional fields."""
        from custom_components.embymedia.const import EmbyActivityLogEntry

        # Based on actual API response with user context
        entry: EmbyActivityLogEntry = {
            "Id": 6611,
            "Name": "admin is playing Elsbeth - S3, Ep6",
            "Type": "playback.start",
            "ItemId": "121947",
            "Date": "2025-11-28T09:56:09.8260000Z",
            "UserId": "1",
            "UserPrimaryImageTag": "b1145a695b3dbf0b91bb1e266151c129",
            "Severity": "Info",
        }

        assert entry["UserId"] == "1"
        assert entry["ItemId"] == "121947"
        assert entry["UserPrimaryImageTag"] == "b1145a695b3dbf0b91bb1e266151c129"

    def test_emby_activity_log_response_can_be_created(self) -> None:
        """Test EmbyActivityLogResponse can be instantiated."""
        from custom_components.embymedia.const import (
            EmbyActivityLogEntry,
            EmbyActivityLogResponse,
        )

        entry: EmbyActivityLogEntry = {
            "Id": 6612,
            "Name": "Test activity",
            "Type": "test.type",
            "Date": "2025-11-28T10:00:00.0000000Z",
            "Severity": "Info",
        }

        response: EmbyActivityLogResponse = {
            "Items": [entry],
            "TotalRecordCount": 100,
        }

        assert len(response["Items"]) == 1
        assert response["TotalRecordCount"] == 100


class TestActivityLogNoAnyTypes:
    """Tests to ensure no Any types are used in Activity Log TypedDicts."""

    def test_emby_activity_log_entry_no_any_types(self) -> None:
        """Test EmbyActivityLogEntry has no Any types."""
        from typing import Any

        from custom_components.embymedia.const import EmbyActivityLogEntry

        hints = get_type_hints(EmbyActivityLogEntry)

        for field_name, field_type in hints.items():
            # Check the type is not Any
            assert field_type is not Any, f"Field {field_name} uses Any type"

    def test_emby_activity_log_response_no_any_types(self) -> None:
        """Test EmbyActivityLogResponse has no Any types."""
        from typing import Any

        from custom_components.embymedia.const import EmbyActivityLogResponse

        hints = get_type_hints(EmbyActivityLogResponse)

        for field_name, field_type in hints.items():
            assert field_type is not Any, f"Field {field_name} uses Any type"
