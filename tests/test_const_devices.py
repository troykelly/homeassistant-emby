"""Tests for Device TypedDicts in const.py.

Phase 18: User Activity & Statistics
"""

from __future__ import annotations

from typing import get_type_hints


class TestDeviceTypedDicts:
    """Tests for Device TypedDicts."""

    def test_emby_device_info_exists(self) -> None:
        """Test EmbyDeviceInfo TypedDict is defined."""
        from custom_components.embymedia.const import EmbyDeviceInfo

        assert EmbyDeviceInfo is not None

    def test_emby_device_info_has_required_fields(self) -> None:
        """Test EmbyDeviceInfo has required fields from API."""
        from custom_components.embymedia.const import EmbyDeviceInfo

        hints = get_type_hints(EmbyDeviceInfo)

        # Based on actual API response:
        # {"Name":"Samsung Smart TV","Id":"5","ReportedDeviceId":"...",
        #  "LastUserName":"admin","AppName":"Emby for Samsung","AppVersion":"2.2.5",
        #  "LastUserId":"...","DateLastActivity":"2025-11-28T10:00:16.0000000Z",
        #  "IconUrl":"...","IpAddress":"..."}
        assert "Id" in hints
        assert "Name" in hints
        assert "LastUserName" in hints
        assert "LastUserId" in hints
        assert "DateLastActivity" in hints
        assert "AppName" in hints
        assert "AppVersion" in hints

    def test_emby_device_info_has_optional_fields(self) -> None:
        """Test EmbyDeviceInfo has optional fields from API."""
        from custom_components.embymedia.const import EmbyDeviceInfo

        hints = get_type_hints(EmbyDeviceInfo)

        # Optional fields from API
        assert "ReportedDeviceId" in hints
        assert "IconUrl" in hints
        assert "IpAddress" in hints

    def test_emby_device_info_field_types(self) -> None:
        """Test EmbyDeviceInfo field types are correct."""
        from custom_components.embymedia.const import EmbyDeviceInfo

        hints = get_type_hints(EmbyDeviceInfo)

        # All fields are strings
        assert hints["Id"] is str
        assert hints["Name"] is str
        assert hints["LastUserName"] is str
        assert hints["LastUserId"] is str
        assert hints["DateLastActivity"] is str
        assert hints["AppName"] is str
        assert hints["AppVersion"] is str

    def test_emby_devices_response_exists(self) -> None:
        """Test EmbyDevicesResponse TypedDict is defined."""
        from custom_components.embymedia.const import EmbyDevicesResponse

        assert EmbyDevicesResponse is not None

    def test_emby_devices_response_has_fields(self) -> None:
        """Test EmbyDevicesResponse has required fields."""
        from custom_components.embymedia.const import EmbyDevicesResponse

        hints = get_type_hints(EmbyDevicesResponse)

        # Based on actual API response:
        # {"Items":[...],"TotalRecordCount":0}
        # Note: TotalRecordCount is 0 in actual response (possible bug in Emby API)
        assert "Items" in hints
        assert "TotalRecordCount" in hints

    def test_emby_devices_response_items_type(self) -> None:
        """Test EmbyDevicesResponse.Items is list of EmbyDeviceInfo."""
        from custom_components.embymedia.const import (
            EmbyDeviceInfo,
            EmbyDevicesResponse,
        )

        hints = get_type_hints(EmbyDevicesResponse)

        assert hints["Items"] == list[EmbyDeviceInfo]

    def test_emby_device_info_can_be_created(self) -> None:
        """Test EmbyDeviceInfo can be instantiated with valid data."""
        from custom_components.embymedia.const import EmbyDeviceInfo

        # Based on actual API response
        device: EmbyDeviceInfo = {
            "Name": "Samsung Smart TV (QA75QN900FWXXY)",
            "Id": "5",
            "ReportedDeviceId": "9beb4c7a-2785-48e9-8e43-be15c34e0435",
            "LastUserName": "admin",
            "AppName": "Emby for Samsung",
            "AppVersion": "2.2.5",
            "LastUserId": "eb0d7e33ee184e36aa011be275ae01f2",
            "DateLastActivity": "2025-11-28T10:00:16.0000000Z",
            "IconUrl": "https://github.com/MediaBrowser/Emby.Resources/raw/master/images/devices/samsungtv.png",
            "IpAddress": "2404:79c0:1002:800:b2f2:f6ff:fe39:d572",
        }

        assert device["Id"] == "5"
        assert device["AppName"] == "Emby for Samsung"
        assert device["LastUserName"] == "admin"

    def test_emby_device_info_with_minimal_fields(self) -> None:
        """Test EmbyDeviceInfo with only essential fields."""
        from custom_components.embymedia.const import EmbyDeviceInfo

        device: EmbyDeviceInfo = {
            "Name": "Test Device",
            "Id": "1",
            "LastUserName": "test",
            "AppName": "Test App",
            "AppVersion": "1.0.0",
            "LastUserId": "user123",
            "DateLastActivity": "2025-11-28T00:00:00.0000000Z",
        }

        assert device["Name"] == "Test Device"

    def test_emby_devices_response_can_be_created(self) -> None:
        """Test EmbyDevicesResponse can be instantiated."""
        from custom_components.embymedia.const import (
            EmbyDeviceInfo,
            EmbyDevicesResponse,
        )

        device: EmbyDeviceInfo = {
            "Name": "Test Device",
            "Id": "1",
            "LastUserName": "test",
            "AppName": "Test App",
            "AppVersion": "1.0.0",
            "LastUserId": "user123",
            "DateLastActivity": "2025-11-28T00:00:00.0000000Z",
        }

        response: EmbyDevicesResponse = {
            "Items": [device],
            "TotalRecordCount": 1,
        }

        assert len(response["Items"]) == 1
        assert response["TotalRecordCount"] == 1


class TestDeviceNoAnyTypes:
    """Tests to ensure no Any types are used in Device TypedDicts."""

    def test_emby_device_info_no_any_types(self) -> None:
        """Test EmbyDeviceInfo has no Any types."""
        from typing import Any

        from custom_components.embymedia.const import EmbyDeviceInfo

        hints = get_type_hints(EmbyDeviceInfo)

        for field_name, field_type in hints.items():
            assert field_type is not Any, f"Field {field_name} uses Any type"

    def test_emby_devices_response_no_any_types(self) -> None:
        """Test EmbyDevicesResponse has no Any types."""
        from typing import Any

        from custom_components.embymedia.const import EmbyDevicesResponse

        hints = get_type_hints(EmbyDevicesResponse)

        for field_name, field_type in hints.items():
            assert field_type is not Any, f"Field {field_name} uses Any type"
