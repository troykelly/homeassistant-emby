#!/usr/bin/env python3
"""Script to explore browse structure on live Emby server."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from custom_components.embymedia.api import EmbyClient


async def main() -> None:
    """Explore browse structure."""
    emby_url = os.environ.get("EMBY_URL")
    emby_api_key = os.environ.get("EMBY_API_KEY")

    if not emby_url or not emby_api_key:
        print("ERROR: EMBY_URL and EMBY_API_KEY required")
        sys.exit(1)

    parsed = urlparse(emby_url)
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 8096)
    ssl = parsed.scheme == "https"

    client = EmbyClient(host=host, port=port, api_key=emby_api_key, ssl=ssl)

    try:
        users = await client.async_get_users()
        user_id = users[0]["Id"]
        print(f"User: {users[0].get('Name')} ({user_id})")

        views = await client.async_get_user_views(user_id)

        # Find movies library
        movies_library = next((v for v in views if v.get("CollectionType") == "movies"), None)
        if movies_library:
            print(f"\n=== Movies Library: {movies_library.get('Name')} ===")
            result = await client.async_get_items(user_id, parent_id=movies_library["Id"], limit=5)
            for item in result.get("Items", []):
                img_tags = item.get("ImageTags", {})
                print(
                    f"  - {item.get('Name')} ({item.get('Type')}) "
                    f"Year: {item.get('ProductionYear')} "
                    f"Images: {list(img_tags.keys())}"
                )

        # Find TV shows library
        tv_library = next((v for v in views if v.get("CollectionType") == "tvshows"), None)
        if tv_library:
            print(f"\n=== TV Shows Library: {tv_library.get('Name')} ===")
            result = await client.async_get_items(user_id, parent_id=tv_library["Id"], limit=5)
            for item in result.get("Items", []):
                print(f"  - {item.get('Name')} ({item.get('Type')}) [ID: {item.get('Id')}]")

            # Try to get Series directly with recursive
            print("\n=== TV Series (recursive) ===")
            result = await client.async_get_items(
                user_id,
                parent_id=tv_library["Id"],
                include_item_types="Series",
                limit=5,
                recursive=True,
            )
            for item in result.get("Items", []):
                img_tags = item.get("ImageTags", {})
                print(
                    f"  - {item.get('Name')} ({item.get('Type')}) "
                    f"Images: {list(img_tags.keys())}"
                )

        # Find music library
        music_library = next((v for v in views if v.get("CollectionType") == "music"), None)
        if music_library:
            print(f"\n=== Music Library: {music_library.get('Name')} ===")
            # Get artists
            result = await client.async_get_items(
                user_id,
                parent_id=music_library["Id"],
                include_item_types="MusicArtist",
                limit=3,
                recursive=True,
            )
            for item in result.get("Items", []):
                print(f"  Artist: {item.get('Name')} ({item.get('Type')})")

            # Get albums
            result = await client.async_get_items(
                user_id,
                parent_id=music_library["Id"],
                include_item_types="MusicAlbum",
                limit=3,
                recursive=True,
            )
            for item in result.get("Items", []):
                print(f"  Album: {item.get('Name')} ({item.get('Type')})")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
