"""Live server tests for Emby API.

These tests run against a real Emby server to validate the API methods.
They require EMBY_URL and EMBY_API_KEY environment variables.

Run with: python -m pytest tests/live/ -v -s -p no:socket
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

import pytest

from custom_components.embymedia.api import EmbyClient


@pytest.fixture
def live_emby_url() -> str | None:
    """Get live Emby URL from environment."""
    return os.environ.get("EMBY_URL")


@pytest.fixture
def live_emby_api_key() -> str | None:
    """Get live Emby API key from environment."""
    return os.environ.get("EMBY_API_KEY")


@pytest.fixture
def requires_live_server(live_emby_url: str | None, live_emby_api_key: str | None) -> None:
    """Skip test if live server credentials not available."""
    if not live_emby_url or not live_emby_api_key:
        pytest.skip("EMBY_URL and EMBY_API_KEY required for live tests")


@pytest.fixture
async def live_client(
    live_emby_url: str | None,
    live_emby_api_key: str | None,
    requires_live_server: None,
) -> EmbyClient:
    """Create client connected to live server."""
    assert live_emby_url is not None
    assert live_emby_api_key is not None

    parsed = urlparse(live_emby_url)
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 8096)
    ssl = parsed.scheme == "https"

    client = EmbyClient(
        host=host,
        port=port,
        api_key=live_emby_api_key,
        ssl=ssl,
        verify_ssl=True,
    )
    return client


class TestLiveServerConnection:
    """Test connection to live server."""

    @pytest.mark.asyncio
    async def test_connection_and_server_info(
        self, live_client: EmbyClient, requires_live_server: None
    ) -> None:
        """Test basic connection and get server info."""
        try:
            info = await live_client.async_get_server_info()
            print(f"\nServer: {info.get('ServerName')}")
            print(f"Version: {info.get('Version')}")
            print(f"Server ID: {info.get('Id')}")
            assert "Id" in info
            assert "ServerName" in info
        finally:
            await live_client.close()


class TestLiveUserViews:
    """Test user views API against live server."""

    @pytest.mark.asyncio
    async def test_get_user_views(
        self, live_client: EmbyClient, requires_live_server: None
    ) -> None:
        """Test getting user views (libraries)."""
        try:
            # First get users to find a user ID
            users = await live_client.async_get_users()
            if not users:
                pytest.skip("No users found on server")

            user_id = users[0]["Id"]
            print(f"\nUsing user: {users[0].get('Name')} ({user_id})")

            # Get user views (libraries)
            views = await live_client.async_get_user_views(user_id)
            print(f"Found {len(views)} libraries:")
            for view in views:
                print(
                    f"  - {view.get('Name')} ({view.get('CollectionType', 'unknown')}) "
                    f"[{view.get('Id')}]"
                )

            assert isinstance(views, list)
            if views:
                assert "Id" in views[0]
                assert "Name" in views[0]
        finally:
            await live_client.close()


class TestLiveGetItems:
    """Test get items API against live server."""

    @pytest.mark.asyncio
    async def test_get_items_from_library(
        self, live_client: EmbyClient, requires_live_server: None
    ) -> None:
        """Test getting items from a library."""
        try:
            users = await live_client.async_get_users()
            if not users:
                pytest.skip("No users found on server")

            user_id = users[0]["Id"]
            views = await live_client.async_get_user_views(user_id)
            if not views:
                pytest.skip("No libraries found")

            # Find a library with items
            for view in views:
                library_id = view["Id"]
                print(f"\nBrowsing library: {view.get('Name')}")

                result = await live_client.async_get_items(user_id, parent_id=library_id, limit=5)

                print(f"Found {result.get('TotalRecordCount', 0)} items")
                items = result.get("Items", [])
                for item in items[:5]:
                    print(f"  - {item.get('Name')} ({item.get('Type')})")

                if items:
                    assert "Id" in items[0]
                    assert "Name" in items[0]
                    assert "Type" in items[0]
                    break
        finally:
            await live_client.close()


class TestLiveGetSeasons:
    """Test get seasons API against live server."""

    @pytest.mark.asyncio
    async def test_get_seasons_for_series(
        self, live_client: EmbyClient, requires_live_server: None
    ) -> None:
        """Test getting seasons for a TV series."""
        try:
            users = await live_client.async_get_users()
            if not users:
                pytest.skip("No users found on server")

            user_id = users[0]["Id"]

            # Find TV shows library and a series
            result = await live_client.async_get_items(
                user_id, include_item_types="Series", limit=1, recursive=True
            )

            items = result.get("Items", [])
            if not items:
                pytest.skip("No TV series found on server")

            series = items[0]
            series_id = series["Id"]
            print(f"\nGetting seasons for: {series.get('Name')}")

            seasons = await live_client.async_get_seasons(user_id, series_id)
            print(f"Found {len(seasons)} seasons:")
            for season in seasons:
                print(f"  - {season.get('Name')} (Index: {season.get('IndexNumber')})")

            # May have 0 seasons if it's a mini-series
            assert isinstance(seasons, list)
        finally:
            await live_client.close()


class TestLiveGetEpisodes:
    """Test get episodes API against live server."""

    @pytest.mark.asyncio
    async def test_get_episodes_for_season(
        self, live_client: EmbyClient, requires_live_server: None
    ) -> None:
        """Test getting episodes for a season."""
        try:
            users = await live_client.async_get_users()
            if not users:
                pytest.skip("No users found on server")

            user_id = users[0]["Id"]

            # Find a series
            result = await live_client.async_get_items(
                user_id, include_item_types="Series", limit=1, recursive=True
            )

            items = result.get("Items", [])
            if not items:
                pytest.skip("No TV series found on server")

            series = items[0]
            series_id = series["Id"]

            # Get seasons
            seasons = await live_client.async_get_seasons(user_id, series_id)
            if not seasons:
                pytest.skip("No seasons found")

            season_id = seasons[0]["Id"]
            print(f"\nGetting episodes for: {series.get('Name')} - {seasons[0].get('Name')}")

            episodes = await live_client.async_get_episodes(user_id, series_id, season_id)
            print(f"Found {len(episodes)} episodes:")
            for ep in episodes[:5]:  # Show first 5
                print(f"  - E{ep.get('IndexNumber', '?')}: {ep.get('Name')}")

            if episodes:
                assert "Id" in episodes[0]
                assert "Name" in episodes[0]
        finally:
            await live_client.close()
