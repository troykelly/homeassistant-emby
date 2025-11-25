#!/usr/bin/env python3
"""Script to test API methods against a live Emby server.

Run with: python scripts/test_live_api.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from urllib.parse import urlparse

# Add the custom_components to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from custom_components.embymedia.api import EmbyClient


async def main() -> None:
    """Run live API tests."""
    emby_url = os.environ.get("EMBY_URL")
    emby_api_key = os.environ.get("EMBY_API_KEY")

    if not emby_url or not emby_api_key:
        print("ERROR: EMBY_URL and EMBY_API_KEY environment variables required")
        sys.exit(1)

    parsed = urlparse(emby_url)
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 8096)
    ssl = parsed.scheme == "https"

    print(f"Connecting to Emby server at {host}:{port} (SSL: {ssl})")

    client = EmbyClient(
        host=host,
        port=port,
        api_key=emby_api_key,
        ssl=ssl,
        verify_ssl=True,
    )

    try:
        # Test 1: Server Info
        print("\n=== Test 1: Server Info ===")
        info = await client.async_get_server_info()
        print(f"Server Name: {info.get('ServerName')}")
        print(f"Server Version: {info.get('Version')}")
        print(f"Server ID: {info.get('Id')}")

        # Test 2: Get Users
        print("\n=== Test 2: Get Users ===")
        users = await client.async_get_users()
        if not users:
            print("No users found - cannot continue")
            return

        user = users[0]
        user_id = user["Id"]
        print(f"Found {len(users)} users, using: {user.get('Name')} ({user_id})")

        # Test 3: Get User Views (Libraries)
        print("\n=== Test 3: Get User Views (Libraries) ===")
        views = await client.async_get_user_views(user_id)
        print(f"Found {len(views)} libraries:")
        for view in views:
            collection_type = view.get("CollectionType", "unknown")
            print(f"  - {view.get('Name')} (type: {collection_type}) [ID: {view.get('Id')}]")

        # Test 4: Get Items from first library
        print("\n=== Test 4: Get Items from Library ===")
        if views:
            library = views[0]
            library_id = library["Id"]
            print(f"Browsing library: {library.get('Name')}")

            result = await client.async_get_items(user_id, parent_id=library_id, limit=5)
            total = result.get("TotalRecordCount", 0)
            items = result.get("Items", [])
            print(f"Found {total} total items, showing first {len(items)}:")
            for item in items:
                print(f"  - {item.get('Name')} ({item.get('Type')}) [ID: {item.get('Id')}]")

        # Test 5: Get TV Series and Seasons
        print("\n=== Test 5: Get TV Series and Seasons ===")
        result = await client.async_get_items(
            user_id, include_item_types="Series", limit=1, recursive=True
        )
        items = result.get("Items", [])
        if items:
            series = items[0]
            series_id = series["Id"]
            print(f"Found series: {series.get('Name')} [{series_id}]")

            seasons = await client.async_get_seasons(user_id, series_id)
            print(f"Found {len(seasons)} seasons:")
            for season in seasons:
                print(
                    f"  - {season.get('Name')} "
                    f"(Index: {season.get('IndexNumber', '?')}) "
                    f"[ID: {season.get('Id')}]"
                )

            # Test 6: Get Episodes
            if seasons:
                print("\n=== Test 6: Get Episodes ===")
                season = seasons[0]
                season_id = season["Id"]
                print(f"Getting episodes for: {season.get('Name')}")

                episodes = await client.async_get_episodes(user_id, series_id, season_id)
                print(f"Found {len(episodes)} episodes:")
                for ep in episodes[:5]:  # Show first 5
                    print(
                        f"  - E{ep.get('IndexNumber', '?')}: {ep.get('Name')} "
                        f"[ID: {ep.get('Id')}]"
                    )
        else:
            print("No TV series found, skipping seasons/episodes test")

        print("\n=== All tests passed! ===")

    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
