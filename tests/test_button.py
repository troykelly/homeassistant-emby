"""Tests for Emby button platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.button import ButtonDeviceClass
from homeassistant.core import HomeAssistant


class TestEmbyRefreshLibraryButton:
    """Test EmbyRefreshLibraryButton class."""

    def test_button_unique_id(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test button unique_id format."""
        from custom_components.embymedia.button import EmbyRefreshLibraryButton

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        button = EmbyRefreshLibraryButton(mock_coordinator)

        assert button.unique_id == "server-123_refresh_library"

    def test_button_name(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test button name is 'Refresh Library'."""
        from custom_components.embymedia.button import EmbyRefreshLibraryButton

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        button = EmbyRefreshLibraryButton(mock_coordinator)

        assert button.name == "Refresh Library"

    def test_button_device_class(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test button has IDENTIFY device class."""
        from custom_components.embymedia.button import EmbyRefreshLibraryButton

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        button = EmbyRefreshLibraryButton(mock_coordinator)

        assert button.device_class == ButtonDeviceClass.IDENTIFY

    def test_button_available(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test button is available when coordinator has data."""
        from custom_components.embymedia.button import EmbyRefreshLibraryButton

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.last_update_success = True
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        button = EmbyRefreshLibraryButton(mock_coordinator)

        assert button.available is True

    def test_button_device_info_links_to_server(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test button device info links to server device without overriding name.

        The button's device_info should only provide identifiers to link to
        the server device (which is registered in __init__.py). It should NOT
        set the name field, as that would overwrite the server's device name.
        """
        from custom_components.embymedia.button import EmbyRefreshLibraryButton
        from custom_components.embymedia.const import DOMAIN

        mock_config_entry = MagicMock()
        mock_config_entry.options = {}

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.config_entry = mock_config_entry
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        button = EmbyRefreshLibraryButton(mock_coordinator)
        device_info = button.device_info

        assert device_info is not None
        assert (DOMAIN, "server-123") in device_info["identifiers"]
        # Device name is NOT set by button - it's set in __init__.py
        assert "name" not in device_info
        assert device_info["manufacturer"] == "Emby"

    @pytest.mark.asyncio
    async def test_press_calls_api(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test pressing button calls refresh_library API."""
        from custom_components.embymedia.button import EmbyRefreshLibraryButton

        mock_client = MagicMock()
        mock_client.async_refresh_library = AsyncMock()

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.client = mock_client
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        button = EmbyRefreshLibraryButton(mock_coordinator)

        await button.async_press()

        mock_client.async_refresh_library.assert_called_once_with(library_id=None)

    @pytest.mark.asyncio
    async def test_press_handles_api_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test pressing button handles API errors gracefully."""
        from custom_components.embymedia.button import EmbyRefreshLibraryButton

        mock_client = MagicMock()
        mock_client.async_refresh_library = AsyncMock(side_effect=Exception("API Error"))

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.client = mock_client
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        button = EmbyRefreshLibraryButton(mock_coordinator)

        # Should not raise, just log error
        await button.async_press()

        mock_client.async_refresh_library.assert_called_once()


class TestAsyncSetupEntry:
    """Test async_setup_entry function."""

    @pytest.mark.asyncio
    async def test_setup_entry_adds_button_entities(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test setup_entry adds button entities."""
        from custom_components.embymedia.button import async_setup_entry

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        mock_entry = MagicMock()
        mock_entry.runtime_data = mock_coordinator

        added_entities: list = []

        def capture_entities(entities: list) -> None:
            added_entities.extend(entities)

        await async_setup_entry(hass, mock_entry, capture_entities)

        # Should add at least one button (refresh library)
        assert len(added_entities) >= 1
        # Check the refresh library button was added
        refresh_button = next(
            (e for e in added_entities if "refresh_library" in e.unique_id),
            None,
        )
        assert refresh_button is not None


class TestEmbyRefreshLibraryButtonSuggestedObjectId:
    """Test button suggested_object_id for correct entity ID generation (Phase 11)."""

    def test_suggested_object_id_with_prefix_enabled(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test suggested_object_id includes 'Emby' prefix and entity name."""
        from custom_components.embymedia.button import EmbyRefreshLibraryButton
        from custom_components.embymedia.const import CONF_PREFIX_BUTTON

        mock_config_entry = MagicMock()
        mock_config_entry.options = {CONF_PREFIX_BUTTON: True}

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.config_entry = mock_config_entry
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        button = EmbyRefreshLibraryButton(mock_coordinator)

        assert button.suggested_object_id == "Emby Test Server Refresh Library"

    def test_suggested_object_id_with_prefix_disabled(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test suggested_object_id excludes prefix when disabled."""
        from custom_components.embymedia.button import EmbyRefreshLibraryButton
        from custom_components.embymedia.const import CONF_PREFIX_BUTTON

        mock_config_entry = MagicMock()
        mock_config_entry.options = {CONF_PREFIX_BUTTON: False}

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.config_entry = mock_config_entry
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        button = EmbyRefreshLibraryButton(mock_coordinator)

        assert button.suggested_object_id == "Test Server Refresh Library"


class TestEmbyRunLibraryScanButton:
    """Test EmbyRunLibraryScanButton class (Phase 20)."""

    def test_button_unique_id(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test button unique_id format."""
        from custom_components.embymedia.button import EmbyRunLibraryScanButton

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        button = EmbyRunLibraryScanButton(mock_coordinator)

        assert button.unique_id == "server-123_run_library_scan"

    def test_button_name(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test button name is 'Run Library Scan'."""
        from custom_components.embymedia.button import EmbyRunLibraryScanButton

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        button = EmbyRunLibraryScanButton(mock_coordinator)

        assert button.name == "Run Library Scan"

    def test_button_device_class(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test button has IDENTIFY device class."""
        from custom_components.embymedia.button import EmbyRunLibraryScanButton

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        button = EmbyRunLibraryScanButton(mock_coordinator)

        assert button.device_class == ButtonDeviceClass.IDENTIFY

    @pytest.mark.asyncio
    async def test_press_calls_api_with_correct_task_id(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test pressing button triggers library scan task."""
        from custom_components.embymedia.button import EmbyRunLibraryScanButton

        mock_client = MagicMock()
        mock_client.async_get_scheduled_tasks = AsyncMock(
            return_value=[
                {"Id": "task-abc", "Key": "RefreshLibrary", "Name": "Scan media library"},
                {"Id": "task-def", "Key": "TasksCleanCache", "Name": "Clean cache"},
            ]
        )
        mock_client.async_run_scheduled_task = AsyncMock()

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.client = mock_client
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        button = EmbyRunLibraryScanButton(mock_coordinator)

        await button.async_press()

        mock_client.async_get_scheduled_tasks.assert_called_once()
        mock_client.async_run_scheduled_task.assert_called_once_with(task_id="task-abc")

    @pytest.mark.asyncio
    async def test_press_handles_task_not_found(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test pressing button handles missing library scan task gracefully."""
        from custom_components.embymedia.button import EmbyRunLibraryScanButton

        mock_client = MagicMock()
        mock_client.async_get_scheduled_tasks = AsyncMock(
            return_value=[
                {"Id": "task-def", "Key": "TasksCleanCache", "Name": "Clean cache"},
            ]
        )
        mock_client.async_run_scheduled_task = AsyncMock()

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.client = mock_client
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        button = EmbyRunLibraryScanButton(mock_coordinator)

        # Should not raise, just log error
        await button.async_press()

        mock_client.async_get_scheduled_tasks.assert_called_once()
        # Should not have called run_scheduled_task since task wasn't found
        mock_client.async_run_scheduled_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_press_handles_api_error(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test pressing button handles API errors gracefully."""
        from custom_components.embymedia.button import EmbyRunLibraryScanButton

        mock_client = MagicMock()
        mock_client.async_get_scheduled_tasks = AsyncMock(side_effect=Exception("API Error"))

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.client = mock_client
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        button = EmbyRunLibraryScanButton(mock_coordinator)

        # Should not raise, just log error
        await button.async_press()

        mock_client.async_get_scheduled_tasks.assert_called_once()

    def test_button_device_info_links_to_server(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test button device info links to server device without overriding name.

        The button's device_info should only provide identifiers to link to
        the server device (which is registered in __init__.py). It should NOT
        set the name field, as that would overwrite the server's device name.
        """
        from custom_components.embymedia.button import EmbyRunLibraryScanButton
        from custom_components.embymedia.const import DOMAIN

        mock_config_entry = MagicMock()
        mock_config_entry.options = {}

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.config_entry = mock_config_entry
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        button = EmbyRunLibraryScanButton(mock_coordinator)
        device_info = button.device_info

        assert device_info is not None
        assert (DOMAIN, "server-123") in device_info["identifiers"]
        # Device name is NOT set by button - it's set in __init__.py
        assert "name" not in device_info
        assert device_info["manufacturer"] == "Emby"

    def test_suggested_object_id_with_prefix_enabled(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test suggested_object_id includes 'Emby' prefix and entity name."""
        from custom_components.embymedia.button import EmbyRunLibraryScanButton
        from custom_components.embymedia.const import CONF_PREFIX_BUTTON

        mock_config_entry = MagicMock()
        mock_config_entry.options = {CONF_PREFIX_BUTTON: True}

        mock_coordinator = MagicMock()
        mock_coordinator.server_id = "server-123"
        mock_coordinator.server_name = "Test Server"
        mock_coordinator.config_entry = mock_config_entry
        mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

        button = EmbyRunLibraryScanButton(mock_coordinator)

        assert button.suggested_object_id == "Emby Test Server Run Library Scan"
