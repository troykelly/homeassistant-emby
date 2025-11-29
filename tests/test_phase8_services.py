"""Tests for Phase 8.2 & 8.3: Remote Control and Library Management Services."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.embymedia.const import DOMAIN

from .conftest import add_coordinator_mocks


@pytest.fixture
def mock_coordinator() -> MagicMock:
    """Create a mock coordinator with client."""
    coordinator = MagicMock()
    coordinator.client = MagicMock()
    coordinator.user_id = "user-123"
    coordinator.data = {}
    return coordinator


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create mock config entry for service tests."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "emby.local",
            "port": 8096,
            "api_key": "test-key",
            "user_id": "user-123",
        },
        unique_id="server-123",
    )


class TestSendMessageService:
    """Test send_message service."""

    @pytest.mark.asyncio
    async def test_service_registered(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test send_message service is registered."""
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.embymedia.EmbyClient",
            autospec=True,
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.async_get_server_info = AsyncMock(
                return_value={"Id": "server-123", "ServerName": "Test"}
            )
            mock_client.async_get_sessions = AsyncMock(return_value=[])
            mock_client.browse_cache = MagicMock()
            mock_client.browse_cache.get_stats = MagicMock(return_value={})
            add_coordinator_mocks(mock_client)

            await hass.config_entries.async_setup(mock_config_entry.entry_id)
            await hass.async_block_till_done()

            # Check service is registered
            assert hass.services.has_service(DOMAIN, "send_message")


class TestMarkPlayedService:
    """Test mark_played service."""

    @pytest.mark.asyncio
    async def test_service_registered(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test mark_played service is registered."""
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.embymedia.EmbyClient",
            autospec=True,
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.async_get_server_info = AsyncMock(
                return_value={"Id": "server-123", "ServerName": "Test"}
            )
            mock_client.async_get_sessions = AsyncMock(return_value=[])
            mock_client.browse_cache = MagicMock()
            mock_client.browse_cache.get_stats = MagicMock(return_value={})
            add_coordinator_mocks(mock_client)

            await hass.config_entries.async_setup(mock_config_entry.entry_id)
            await hass.async_block_till_done()

            # Check service is registered
            assert hass.services.has_service(DOMAIN, "mark_played")


class TestMarkUnplayedService:
    """Test mark_unplayed service."""

    @pytest.mark.asyncio
    async def test_service_registered(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test mark_unplayed service is registered."""
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.embymedia.EmbyClient",
            autospec=True,
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.async_get_server_info = AsyncMock(
                return_value={"Id": "server-123", "ServerName": "Test"}
            )
            mock_client.async_get_sessions = AsyncMock(return_value=[])
            mock_client.browse_cache = MagicMock()
            mock_client.browse_cache.get_stats = MagicMock(return_value={})
            add_coordinator_mocks(mock_client)

            await hass.config_entries.async_setup(mock_config_entry.entry_id)
            await hass.async_block_till_done()

            # Check service is registered
            assert hass.services.has_service(DOMAIN, "mark_unplayed")


class TestFavoriteServices:
    """Test favorite management services."""

    @pytest.mark.asyncio
    async def test_add_favorite_registered(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test add_favorite service is registered."""
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.embymedia.EmbyClient",
            autospec=True,
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.async_get_server_info = AsyncMock(
                return_value={"Id": "server-123", "ServerName": "Test"}
            )
            mock_client.async_get_sessions = AsyncMock(return_value=[])
            mock_client.browse_cache = MagicMock()
            mock_client.browse_cache.get_stats = MagicMock(return_value={})
            add_coordinator_mocks(mock_client)

            await hass.config_entries.async_setup(mock_config_entry.entry_id)
            await hass.async_block_till_done()

            # Check service is registered
            assert hass.services.has_service(DOMAIN, "add_favorite")

    @pytest.mark.asyncio
    async def test_remove_favorite_registered(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test remove_favorite service is registered."""
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.embymedia.EmbyClient",
            autospec=True,
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.async_get_server_info = AsyncMock(
                return_value={"Id": "server-123", "ServerName": "Test"}
            )
            mock_client.async_get_sessions = AsyncMock(return_value=[])
            mock_client.browse_cache = MagicMock()
            mock_client.browse_cache.get_stats = MagicMock(return_value={})
            add_coordinator_mocks(mock_client)

            await hass.config_entries.async_setup(mock_config_entry.entry_id)
            await hass.async_block_till_done()

            # Check service is registered
            assert hass.services.has_service(DOMAIN, "remove_favorite")


class TestLibraryServices:
    """Test library management services."""

    @pytest.mark.asyncio
    async def test_refresh_library_registered(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test refresh_library service is registered."""
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.embymedia.EmbyClient",
            autospec=True,
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.async_get_server_info = AsyncMock(
                return_value={"Id": "server-123", "ServerName": "Test"}
            )
            mock_client.async_get_sessions = AsyncMock(return_value=[])
            mock_client.browse_cache = MagicMock()
            mock_client.browse_cache.get_stats = MagicMock(return_value={})
            add_coordinator_mocks(mock_client)

            await hass.config_entries.async_setup(mock_config_entry.entry_id)
            await hass.async_block_till_done()

            # Check service is registered
            assert hass.services.has_service(DOMAIN, "refresh_library")

    @pytest.mark.asyncio
    async def test_send_command_registered(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test send_command service is registered."""
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.embymedia.EmbyClient",
            autospec=True,
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.async_get_server_info = AsyncMock(
                return_value={"Id": "server-123", "ServerName": "Test"}
            )
            mock_client.async_get_sessions = AsyncMock(return_value=[])
            mock_client.browse_cache = MagicMock()
            mock_client.browse_cache.get_stats = MagicMock(return_value={})
            add_coordinator_mocks(mock_client)

            await hass.config_entries.async_setup(mock_config_entry.entry_id)
            await hass.async_block_till_done()

            # Check service is registered
            assert hass.services.has_service(DOMAIN, "send_command")


class TestAPIClientMethods:
    """Test API client has methods for services."""

    def test_mark_played_method_exists(self) -> None:
        """Test async_mark_played method exists on client."""
        from custom_components.embymedia.api import EmbyClient

        assert hasattr(EmbyClient, "async_mark_played")

    def test_mark_unplayed_method_exists(self) -> None:
        """Test async_mark_unplayed method exists on client."""
        from custom_components.embymedia.api import EmbyClient

        assert hasattr(EmbyClient, "async_mark_unplayed")

    def test_add_favorite_method_exists(self) -> None:
        """Test async_add_favorite method exists on client."""
        from custom_components.embymedia.api import EmbyClient

        assert hasattr(EmbyClient, "async_add_favorite")

    def test_remove_favorite_method_exists(self) -> None:
        """Test async_remove_favorite method exists on client."""
        from custom_components.embymedia.api import EmbyClient

        assert hasattr(EmbyClient, "async_remove_favorite")

    def test_refresh_library_method_exists(self) -> None:
        """Test async_refresh_library method exists on client."""
        from custom_components.embymedia.api import EmbyClient

        assert hasattr(EmbyClient, "async_refresh_library")

    def test_refresh_item_method_exists(self) -> None:
        """Test async_refresh_item method exists on client."""
        from custom_components.embymedia.api import EmbyClient

        assert hasattr(EmbyClient, "async_refresh_item")

    def test_send_message_method_exists(self) -> None:
        """Test async_send_message method exists on client."""
        from custom_components.embymedia.api import EmbyClient

        assert hasattr(EmbyClient, "async_send_message")
