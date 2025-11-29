"""Tests for Server Administration services.

Phase 20: Server Administration
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.embymedia.const import (
    CONF_API_KEY,
    CONF_VERIFY_SSL,
    DOMAIN,
)
from custom_components.embymedia.exceptions import (
    EmbyConnectionError,
    EmbyNotFoundError,
)


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "emby.local",
            CONF_PORT: 8096,
            CONF_SSL: False,
            CONF_API_KEY: "test-api-key",
            CONF_VERIFY_SSL: True,
        },
        unique_id="test-server-id",
    )


class TestRunScheduledTaskService:
    """Tests for run_scheduled_task service."""

    async def test_service_registered(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that run_scheduled_task service is registered."""
        from custom_components.embymedia.services import (
            SERVICE_RUN_SCHEDULED_TASK,
            async_setup_services,
        )

        await async_setup_services(hass)
        assert hass.services.has_service(DOMAIN, SERVICE_RUN_SCHEDULED_TASK)

    async def test_run_scheduled_task_success(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test run_scheduled_task service success."""
        mock_config_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(return_value=[])
            client.async_get_item_counts = AsyncMock(
                return_value={"MovieCount": 0, "SeriesCount": 0}
            )
            client.async_get_scheduled_tasks = AsyncMock(return_value=[])
            client.async_get_plugins = AsyncMock(return_value=[])
            client.async_run_scheduled_task = AsyncMock()
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_config_entry.entry_id)
                await hass.async_block_till_done()

                # Call service
                await hass.services.async_call(
                    DOMAIN,
                    "run_scheduled_task",
                    {"task_id": "6330ee8fb4a957f33981f89aa78b030f"},
                    blocking=True,
                )

                # Verify API was called
                client.async_run_scheduled_task.assert_called_once_with(
                    task_id="6330ee8fb4a957f33981f89aa78b030f"
                )

    async def test_run_scheduled_task_not_found(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test run_scheduled_task raises error for non-existent task."""
        mock_config_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(return_value=[])
            client.async_get_item_counts = AsyncMock(
                return_value={"MovieCount": 0, "SeriesCount": 0}
            )
            client.async_get_scheduled_tasks = AsyncMock(return_value=[])
            client.async_get_plugins = AsyncMock(return_value=[])
            client.async_run_scheduled_task = AsyncMock(
                side_effect=EmbyNotFoundError("Task not found")
            )
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_config_entry.entry_id)
                await hass.async_block_till_done()

                # Call service - should raise HomeAssistantError
                with pytest.raises(HomeAssistantError) as exc_info:
                    await hass.services.async_call(
                        DOMAIN,
                        "run_scheduled_task",
                        {"task_id": "non-existent-task"},
                        blocking=True,
                    )

                assert "not found" in str(exc_info.value).lower()

    async def test_run_scheduled_task_invalid_id(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test run_scheduled_task validates task_id format."""
        mock_config_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(return_value=[])
            client.async_get_item_counts = AsyncMock(
                return_value={"MovieCount": 0, "SeriesCount": 0}
            )
            client.async_get_scheduled_tasks = AsyncMock(return_value=[])
            client.async_get_plugins = AsyncMock(return_value=[])
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_config_entry.entry_id)
                await hass.async_block_till_done()

                # Call service with invalid ID containing special chars
                with pytest.raises(ServiceValidationError):
                    await hass.services.async_call(
                        DOMAIN,
                        "run_scheduled_task",
                        {"task_id": "invalid;task&id"},
                        blocking=True,
                    )


class TestRestartServerService:
    """Tests for restart_server service."""

    async def test_service_registered(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that restart_server service is registered."""
        from custom_components.embymedia.services import (
            SERVICE_RESTART_SERVER,
            async_setup_services,
        )

        await async_setup_services(hass)
        assert hass.services.has_service(DOMAIN, SERVICE_RESTART_SERVER)

    async def test_restart_server_success(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test restart_server service success."""
        mock_config_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(return_value=[])
            client.async_get_item_counts = AsyncMock(
                return_value={"MovieCount": 0, "SeriesCount": 0}
            )
            client.async_get_scheduled_tasks = AsyncMock(return_value=[])
            client.async_get_plugins = AsyncMock(return_value=[])
            client.async_restart_server = AsyncMock()
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_config_entry.entry_id)
                await hass.async_block_till_done()

                # Call service
                await hass.services.async_call(
                    DOMAIN,
                    "restart_server",
                    {},
                    blocking=True,
                )

                # Verify API was called
                client.async_restart_server.assert_called_once()

    async def test_restart_server_connection_error(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test restart_server handles connection error."""
        mock_config_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(return_value=[])
            client.async_get_item_counts = AsyncMock(
                return_value={"MovieCount": 0, "SeriesCount": 0}
            )
            client.async_get_scheduled_tasks = AsyncMock(return_value=[])
            client.async_get_plugins = AsyncMock(return_value=[])
            client.async_restart_server = AsyncMock(
                side_effect=EmbyConnectionError("Connection failed")
            )
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_config_entry.entry_id)
                await hass.async_block_till_done()

                # Call service - should raise HomeAssistantError
                with pytest.raises(HomeAssistantError) as exc_info:
                    await hass.services.async_call(
                        DOMAIN,
                        "restart_server",
                        {},
                        blocking=True,
                    )

                assert "connection error" in str(exc_info.value).lower()


class TestShutdownServerService:
    """Tests for shutdown_server service."""

    async def test_service_registered(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that shutdown_server service is registered."""
        from custom_components.embymedia.services import (
            SERVICE_SHUTDOWN_SERVER,
            async_setup_services,
        )

        await async_setup_services(hass)
        assert hass.services.has_service(DOMAIN, SERVICE_SHUTDOWN_SERVER)

    async def test_shutdown_server_success(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test shutdown_server service success."""
        mock_config_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(return_value=[])
            client.async_get_item_counts = AsyncMock(
                return_value={"MovieCount": 0, "SeriesCount": 0}
            )
            client.async_get_scheduled_tasks = AsyncMock(return_value=[])
            client.async_get_plugins = AsyncMock(return_value=[])
            client.async_shutdown_server = AsyncMock()
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_config_entry.entry_id)
                await hass.async_block_till_done()

                # Call service
                await hass.services.async_call(
                    DOMAIN,
                    "shutdown_server",
                    {},
                    blocking=True,
                )

                # Verify API was called
                client.async_shutdown_server.assert_called_once()

    async def test_shutdown_server_connection_error(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test shutdown_server handles connection error."""
        mock_config_entry.add_to_hass(hass)

        with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock_client_class:
            client = mock_client_class.return_value
            client.async_validate_connection = AsyncMock(return_value=True)
            client.async_get_server_info = AsyncMock(
                return_value={
                    "Id": "test-server-id",
                    "ServerName": "Test Server",
                    "Version": "4.9.2.0",
                }
            )
            client.async_get_sessions = AsyncMock(return_value=[])
            client.async_get_item_counts = AsyncMock(
                return_value={"MovieCount": 0, "SeriesCount": 0}
            )
            client.async_get_scheduled_tasks = AsyncMock(return_value=[])
            client.async_get_plugins = AsyncMock(return_value=[])
            client.async_shutdown_server = AsyncMock(
                side_effect=EmbyConnectionError("Connection failed")
            )
            client.close = AsyncMock()

            with patch(
                "custom_components.embymedia.coordinator.EmbyDataUpdateCoordinator.async_setup_websocket",
                new_callable=AsyncMock,
            ):
                await hass.config_entries.async_setup(mock_config_entry.entry_id)
                await hass.async_block_till_done()

                # Call service - should raise HomeAssistantError
                with pytest.raises(HomeAssistantError) as exc_info:
                    await hass.services.async_call(
                        DOMAIN,
                        "shutdown_server",
                        {},
                        blocking=True,
                    )

                assert "connection error" in str(exc_info.value).lower()


class TestNoConfigEntry:
    """Tests for services when no config entry exists."""

    async def test_run_scheduled_task_no_entry(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test run_scheduled_task raises error when no config entry."""
        from custom_components.embymedia.services import async_setup_services

        await async_setup_services(hass)

        with pytest.raises(HomeAssistantError) as exc_info:
            await hass.services.async_call(
                DOMAIN,
                "run_scheduled_task",
                {"task_id": "some-task-id"},
                blocking=True,
            )

        assert "no emby" in str(exc_info.value).lower()

    async def test_restart_server_no_entry(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test restart_server raises error when no config entry."""
        from custom_components.embymedia.services import async_setup_services

        await async_setup_services(hass)

        with pytest.raises(HomeAssistantError) as exc_info:
            await hass.services.async_call(
                DOMAIN,
                "restart_server",
                {},
                blocking=True,
            )

        assert "no emby" in str(exc_info.value).lower()

    async def test_shutdown_server_no_entry(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test shutdown_server raises error when no config entry."""
        from custom_components.embymedia.services import async_setup_services

        await async_setup_services(hass)

        with pytest.raises(HomeAssistantError) as exc_info:
            await hass.services.async_call(
                DOMAIN,
                "shutdown_server",
                {},
                blocking=True,
            )

        assert "no emby" in str(exc_info.value).lower()
