"""Tests for web player detection optimization (Phase 22).

These tests verify the web player detection uses efficient O(1) lookup
with pre-computed lowercase set.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


@pytest.fixture
def mock_coordinator_for_web_player() -> MagicMock:
    """Create a mock coordinator for web player tests."""
    from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator

    coordinator = MagicMock(spec=EmbyDataUpdateCoordinator)
    return coordinator


class TestWebPlayerClientsConstant:
    """Tests for the WEB_PLAYER_CLIENTS_LOWER constant."""

    def test_lowercase_set_exists(self) -> None:
        """Test that WEB_PLAYER_CLIENTS_LOWER constant exists."""
        from custom_components.embymedia.const import WEB_PLAYER_CLIENTS_LOWER

        assert isinstance(WEB_PLAYER_CLIENTS_LOWER, frozenset)

    def test_lowercase_set_contains_expected_clients(self) -> None:
        """Test that the lowercase set contains expected clients."""
        from custom_components.embymedia.const import WEB_PLAYER_CLIENTS_LOWER

        expected_clients = {
            "emby web",
            "emby mobile web",
            "chrome",
            "firefox",
            "safari",
            "edge",
            "opera",
            "brave",
            "vivaldi",
            "internet explorer",
            "microsoft edge",
        }
        assert expected_clients == WEB_PLAYER_CLIENTS_LOWER

    def test_all_values_are_lowercase(self) -> None:
        """Test that all values in the set are lowercase."""
        from custom_components.embymedia.const import WEB_PLAYER_CLIENTS_LOWER

        for client in WEB_PLAYER_CLIENTS_LOWER:
            assert client == client.lower(), f"'{client}' should be lowercase"


class TestIsWebPlayerMethod:
    """Tests for the _is_web_player method optimization."""

    @pytest.mark.asyncio
    async def test_detects_emby_web(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test detection of 'Emby Web' client."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator
        from custom_components.embymedia.models import EmbySession

        coordinator = MagicMock(spec=EmbyDataUpdateCoordinator)
        # Call the real method
        session = EmbySession(
            session_id="test-1",
            device_id="device-1",
            device_name="Browser",
            client_name="Emby Web",
            user_id="user-1",
            user_name="TestUser",
            supports_remote_control=True,
        )

        # We need to call the actual method, not a mock
        result = EmbyDataUpdateCoordinator._is_web_player(coordinator, session)
        assert result is True

    @pytest.mark.asyncio
    async def test_detects_chrome(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test detection of 'Chrome' client."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator
        from custom_components.embymedia.models import EmbySession

        coordinator = MagicMock(spec=EmbyDataUpdateCoordinator)
        session = EmbySession(
            session_id="test-2",
            device_id="device-2",
            device_name="Browser",
            client_name="Chrome",
            user_id="user-1",
            user_name="TestUser",
            supports_remote_control=True,
        )

        result = EmbyDataUpdateCoordinator._is_web_player(coordinator, session)
        assert result is True

    @pytest.mark.asyncio
    async def test_case_insensitive(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that detection is case-insensitive."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator
        from custom_components.embymedia.models import EmbySession

        coordinator = MagicMock(spec=EmbyDataUpdateCoordinator)
        session = EmbySession(
            session_id="test-3",
            device_id="device-3",
            device_name="Browser",
            client_name="FIREFOX",  # Uppercase
            user_id="user-1",
            user_name="TestUser",
            supports_remote_control=True,
        )

        result = EmbyDataUpdateCoordinator._is_web_player(coordinator, session)
        assert result is True

    @pytest.mark.asyncio
    async def test_non_web_player_returns_false(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that non-web player clients return False."""
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator
        from custom_components.embymedia.models import EmbySession

        coordinator = MagicMock(spec=EmbyDataUpdateCoordinator)
        session = EmbySession(
            session_id="test-4",
            device_id="device-4",
            device_name="Living Room",
            client_name="Emby Theater",  # Desktop app, not web
            user_id="user-1",
            user_name="TestUser",
            supports_remote_control=True,
        )

        result = EmbyDataUpdateCoordinator._is_web_player(coordinator, session)
        assert result is False

    @pytest.mark.asyncio
    async def test_all_known_web_clients(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test all known web clients are detected."""
        from custom_components.embymedia.const import WEB_PLAYER_CLIENTS_LOWER
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator
        from custom_components.embymedia.models import EmbySession

        coordinator = MagicMock(spec=EmbyDataUpdateCoordinator)

        for client_name in WEB_PLAYER_CLIENTS_LOWER:
            session = EmbySession(
                session_id=f"test-{client_name}",
                device_id=f"device-{client_name}",
                device_name="Browser",
                client_name=client_name,
                user_id="user-1",
                user_name="TestUser",
                supports_remote_control=True,
            )

            result = EmbyDataUpdateCoordinator._is_web_player(coordinator, session)
            assert result is True, f"Should detect '{client_name}' as web player"


class TestExactMatchBehavior:
    """Tests verifying exact match behavior (not substring)."""

    @pytest.mark.asyncio
    async def test_partial_match_not_detected(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that partial/substring matches are NOT detected.

        This verifies the optimization to exact matching works correctly.
        Extended client names like 'Mozilla Firefox' won't match 'Firefox'.
        """
        from custom_components.embymedia.coordinator import EmbyDataUpdateCoordinator
        from custom_components.embymedia.models import EmbySession

        coordinator = MagicMock(spec=EmbyDataUpdateCoordinator)

        # These should NOT match with exact matching
        non_matching_clients = [
            "Mozilla Firefox",  # Contains 'Firefox' but not exact
            "Google Chrome",  # Contains 'Chrome' but not exact
            "Apple Safari",  # Contains 'Safari' but not exact
            "Chromium",  # Similar to Chrome but not exact
            "Firefox Developer Edition",  # Extended Firefox name
        ]

        for client_name in non_matching_clients:
            session = EmbySession(
                session_id=f"test-{client_name}",
                device_id=f"device-{client_name}",
                device_name="Browser",
                client_name=client_name,
                user_id="user-1",
                user_name="TestUser",
                supports_remote_control=True,
            )

            result = EmbyDataUpdateCoordinator._is_web_player(coordinator, session)
            assert result is False, f"'{client_name}' should NOT match with exact matching"
