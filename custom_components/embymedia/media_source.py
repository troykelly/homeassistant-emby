"""Emby Media Source implementation.

This module provides media source functionality that allows Emby content
to be played on any Home Assistant media player, not just Emby clients.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.media_player import MediaClass, MediaType
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)

from .const import DOMAIN, MIME_TYPES, EmbyBrowseItem

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .coordinator import EmbyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_get_media_source(hass: HomeAssistant) -> EmbyMediaSource:
    """Set up Emby media source.

    Args:
        hass: Home Assistant instance.

    Returns:
        Emby media source instance.
    """
    return EmbyMediaSource(hass)


def parse_identifier(
    identifier: str,
) -> tuple[str, str | None, str | None]:
    """Parse media source identifier.

    Format: server_id/content_type/item_id
    Examples:
        "server-123" -> ("server-123", None, None)
        "server-123/library/lib-456" -> ("server-123", "library", "lib-456")
        "server-123/movie/item-789" -> ("server-123", "movie", "item-789")

    Args:
        identifier: The identifier string to parse.

    Returns:
        Tuple of (server_id, content_type, item_id).
    """
    parts = identifier.split("/", 2)
    server_id = parts[0]
    content_type = parts[1] if len(parts) > 1 else None
    item_id = parts[2] if len(parts) > 2 else None
    return server_id, content_type, item_id


def build_identifier(
    server_id: str,
    content_type: str | None = None,
    item_id: str | None = None,
) -> str:
    """Build media source identifier.

    Args:
        server_id: The Emby server ID.
        content_type: Optional content type.
        item_id: Optional item ID.

    Returns:
        Formatted identifier string.
    """
    if content_type is None:
        return server_id
    if item_id is None:
        return f"{server_id}/{content_type}"
    return f"{server_id}/{content_type}/{item_id}"


class EmbyMediaSource(MediaSource):  # type: ignore[misc]
    """Emby media source for Home Assistant.

    Allows browsing and playing Emby content on any HA media player.
    """

    name: str = "Emby"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize Emby media source.

        Args:
            hass: Home Assistant instance.
        """
        super().__init__(DOMAIN)
        self.hass = hass

    def _get_coordinators(self) -> dict[str, EmbyDataUpdateCoordinator]:
        """Get all configured Emby coordinators.

        Returns:
            Dictionary mapping server IDs to coordinators.
        """
        coordinators: dict[str, EmbyDataUpdateCoordinator] = {}

        # Get coordinators from config entries' runtime_data
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if hasattr(entry, "runtime_data") and entry.runtime_data is not None:
                coordinator = entry.runtime_data
                if hasattr(coordinator, "server_id"):
                    coordinators[coordinator.server_id] = coordinator

        return coordinators

    def _get_coordinator(self, server_id: str) -> EmbyDataUpdateCoordinator | None:
        """Get coordinator for a specific server.

        Args:
            server_id: The server ID to look up.

        Returns:
            The coordinator or None if not found.
        """
        return self._get_coordinators().get(server_id)

    def _get_user_id(self, coordinator: EmbyDataUpdateCoordinator) -> str | None:
        """Get a user ID from the coordinator's sessions.

        Args:
            coordinator: The coordinator to get user ID from.

        Returns:
            A user ID or None if no sessions available.
        """
        for session in coordinator.data.values():
            user_id: str | None = session.user_id
            if user_id:
                return user_id
        return None

    async def async_browse_media(
        self,
        item: MediaSourceItem,
    ) -> BrowseMediaSource:
        """Browse Emby media.

        Args:
            item: The media source item to browse.

        Returns:
            Browse result with children.
        """
        if item.identifier is None:
            return await self._async_browse_root()

        server_id, content_type, item_id = parse_identifier(item.identifier)

        coordinator = self._get_coordinator(server_id)
        if coordinator is None:
            raise Unresolvable(f"Server {server_id} not found")

        if content_type is None:
            # Browse server libraries
            return await self._async_browse_server(coordinator)

        if content_type == "library" and item_id:
            # Browse library contents
            return await self._async_browse_library(coordinator, item_id)

        if content_type == "livetv":
            # Browse Live TV channels
            return await self._async_browse_livetv(coordinator)

        # Movie library category routing
        if content_type == "movielibrary" and item_id:
            return await self._async_browse_movie_library(coordinator, item_id)
        if content_type == "movieaz" and item_id:
            return await self._async_browse_movie_az(coordinator, item_id)
        if content_type == "movieazletter" and item_id:
            parts = item_id.split("/")
            if len(parts) >= 2:
                return await self._async_browse_movies_by_letter(coordinator, parts[0], parts[1])
        if content_type == "movieyear" and item_id:
            return await self._async_browse_movie_years(coordinator, item_id)
        if content_type == "movieyearitems" and item_id:
            parts = item_id.split("/")
            if len(parts) >= 2:
                return await self._async_browse_movies_by_year(coordinator, parts[0], parts[1])
        if content_type == "moviedecade" and item_id:
            return await self._async_browse_movie_decades(coordinator, item_id)
        if content_type == "moviedecadeitems" and item_id:
            parts = item_id.split("/")
            if len(parts) >= 2:
                return await self._async_browse_movies_by_decade(coordinator, parts[0], parts[1])
        if content_type == "moviegenre" and item_id:
            return await self._async_browse_movie_genres(coordinator, item_id)
        if content_type == "moviegenreitems" and item_id:
            parts = item_id.split("/")
            if len(parts) >= 2:
                return await self._async_browse_movies_by_genre(coordinator, parts[0], parts[1])
        if content_type == "moviecollection" and item_id:
            return await self._async_browse_movie_collections(coordinator, item_id)

        # TV library category routing
        if content_type == "tvlibrary" and item_id:
            return await self._async_browse_tv_library(coordinator, item_id)
        if content_type == "tvaz" and item_id:
            return await self._async_browse_tv_az(coordinator, item_id)
        if content_type == "tvazletter" and item_id:
            parts = item_id.split("/")
            if len(parts) >= 2:
                return await self._async_browse_tv_by_letter(coordinator, parts[0], parts[1])
        if content_type == "tvyear" and item_id:
            return await self._async_browse_tv_years(coordinator, item_id)
        if content_type == "tvyearitems" and item_id:
            parts = item_id.split("/")
            if len(parts) >= 2:
                return await self._async_browse_tv_by_year(coordinator, parts[0], parts[1])
        if content_type == "tvdecade" and item_id:
            return await self._async_browse_tv_decades(coordinator, item_id)
        if content_type == "tvdecadeitems" and item_id:
            parts = item_id.split("/")
            if len(parts) >= 2:
                return await self._async_browse_tv_by_decade(coordinator, parts[0], parts[1])
        if content_type == "tvgenre" and item_id:
            return await self._async_browse_tv_genres(coordinator, item_id)
        if content_type == "tvgenreitems" and item_id:
            parts = item_id.split("/")
            if len(parts) >= 2:
                return await self._async_browse_tv_by_genre(coordinator, parts[0], parts[1])

        # Browse item (e.g., series, album)
        return await self._async_browse_item(coordinator, content_type, item_id)

    async def _async_browse_root(self) -> BrowseMediaSource:
        """Browse root - show all configured servers.

        Returns:
            Browse result with server list.
        """
        children: list[BrowseMediaSource] = []
        coordinators = self._get_coordinators()

        for server_id, coordinator in coordinators.items():
            children.append(
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=server_id,
                    media_class=MediaClass.DIRECTORY,
                    media_content_type=MediaType.VIDEO,
                    title=coordinator.server_name,
                    can_play=False,
                    can_expand=True,
                    thumbnail=None,
                )
            )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=None,
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title="Emby",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_server(
        self,
        coordinator: EmbyDataUpdateCoordinator,
    ) -> BrowseMediaSource:
        """Browse a server's libraries.

        Args:
            coordinator: The server's coordinator.

        Returns:
            Browse result with library list.
        """
        children: list[BrowseMediaSource] = []
        user_id = self._get_user_id(coordinator)

        if user_id:
            views = await coordinator.client.async_get_user_views(user_id)

            for view in views:
                view_id = view["Id"]
                view_name = view["Name"]
                collection_type = view.get("CollectionType", "")

                # Determine media class based on collection type
                media_class = self._get_media_class_for_collection(collection_type)

                thumbnail = None
                if view.get("ImageTags", {}).get("Primary"):
                    thumbnail = coordinator.client.get_image_url(view_id)

                # Use special identifier for each library type
                if collection_type == "livetv":
                    identifier = build_identifier(coordinator.server_id, "livetv")
                    media_content_type = MediaType.CHANNEL
                elif collection_type == "movies":
                    identifier = build_identifier(coordinator.server_id, "movielibrary", view_id)
                    media_content_type = MediaType.VIDEO
                elif collection_type == "tvshows":
                    identifier = build_identifier(coordinator.server_id, "tvlibrary", view_id)
                    media_content_type = MediaType.VIDEO
                elif collection_type == "music":
                    identifier = build_identifier(coordinator.server_id, "library", view_id)
                    media_content_type = MediaType.MUSIC
                else:
                    identifier = build_identifier(coordinator.server_id, "library", view_id)
                    media_content_type = MediaType.VIDEO

                children.append(
                    BrowseMediaSource(
                        domain=DOMAIN,
                        identifier=identifier,
                        media_class=media_class,
                        media_content_type=media_content_type,
                        title=view_name,
                        can_play=False,
                        can_expand=True,
                        thumbnail=thumbnail,
                    )
                )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=coordinator.server_id,
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title=coordinator.server_name,
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_library(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
    ) -> BrowseMediaSource:
        """Browse a library's contents.

        Args:
            coordinator: The server's coordinator.
            library_id: The library ID to browse.

        Returns:
            Browse result with library contents.
        """
        children: list[BrowseMediaSource] = []
        user_id = self._get_user_id(coordinator)

        if user_id:
            result = await coordinator.client.async_get_items(
                user_id,
                parent_id=library_id,
                limit=100,
            )

            for item in result.get("Items", []):
                item_browse = self._item_to_browse_media_source(coordinator, item)
                children.append(item_browse)

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(coordinator.server_id, "library", library_id),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title="Library",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_livetv(
        self,
        coordinator: EmbyDataUpdateCoordinator,
    ) -> BrowseMediaSource:
        """Browse Live TV channels.

        Args:
            coordinator: The server's coordinator.

        Returns:
            Browse result with Live TV channels.
        """
        children: list[BrowseMediaSource] = []
        user_id = self._get_user_id(coordinator)

        if user_id:
            channels = await coordinator.client.async_get_live_tv_channels(user_id)

            for channel in channels:
                item_browse = self._item_to_browse_media_source(coordinator, channel)
                children.append(item_browse)

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(coordinator.server_id, "livetv"),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.CHANNEL,
            title="Live TV",
            can_play=False,
            can_expand=True,
            children=children,
        )

    # ==================== Movie Library Browsing ====================

    async def _async_browse_movie_library(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
    ) -> BrowseMediaSource:
        """Browse movie library categories."""
        categories = [
            ("A-Z", "movieaz", MediaClass.DIRECTORY),
            ("Year", "movieyear", MediaClass.DIRECTORY),
            ("Decade", "moviedecade", MediaClass.DIRECTORY),
            ("Genre", "moviegenre", MediaClass.DIRECTORY),
            ("Collections", "moviecollection", MediaClass.DIRECTORY),
        ]

        children: list[BrowseMediaSource] = []
        for title, content_type, media_class in categories:
            children.append(
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=build_identifier(coordinator.server_id, content_type, library_id),
                    media_class=media_class,
                    media_content_type=MediaType.VIDEO,
                    title=title,
                    can_play=False,
                    can_expand=True,
                )
            )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(coordinator.server_id, "movielibrary", library_id),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title="Movies",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_movie_az(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
    ) -> BrowseMediaSource:
        """Browse movies A-Z menu."""
        letters = [*"ABCDEFGHIJKLMNOPQRSTUVWXYZ", "#"]
        children: list[BrowseMediaSource] = []

        for letter in letters:
            children.append(
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=build_identifier(
                        coordinator.server_id, "movieazletter", f"{library_id}/{letter}"
                    ),
                    media_class=MediaClass.DIRECTORY,
                    media_content_type=MediaType.VIDEO,
                    title=letter,
                    can_play=False,
                    can_expand=True,
                )
            )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(coordinator.server_id, "movieaz", library_id),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title="A-Z",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_movies_by_letter(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
        letter: str,
    ) -> BrowseMediaSource:
        """Browse movies starting with a letter."""
        children: list[BrowseMediaSource] = []
        user_id = self._get_user_id(coordinator)

        if user_id:
            name_filter = None if letter == "#" else letter
            result = await coordinator.client.async_get_items(
                user_id,
                parent_id=library_id,
                include_item_types="Movie",
                recursive=True,
                name_starts_with=name_filter,
            )
            for item in result.get("Items", []):
                children.append(self._item_to_browse_media_source(coordinator, item))

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(
                coordinator.server_id, "movieazletter", f"{library_id}/{letter}"
            ),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title=letter,
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_movie_years(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
    ) -> BrowseMediaSource:
        """Browse available years for movies."""
        children: list[BrowseMediaSource] = []
        user_id = self._get_user_id(coordinator)

        if user_id:
            years = await coordinator.client.async_get_years(
                user_id, parent_id=library_id, include_item_types="Movie"
            )
            for year_item in years:
                year_name = year_item.get("Name", "Unknown")
                children.append(
                    BrowseMediaSource(
                        domain=DOMAIN,
                        identifier=build_identifier(
                            coordinator.server_id,
                            "movieyearitems",
                            f"{library_id}/{year_name}",
                        ),
                        media_class=MediaClass.DIRECTORY,
                        media_content_type=MediaType.VIDEO,
                        title=year_name,
                        can_play=False,
                        can_expand=True,
                    )
                )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(coordinator.server_id, "movieyear", library_id),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title="Year",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_movies_by_year(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
        year: str,
    ) -> BrowseMediaSource:
        """Browse movies from a specific year."""
        children: list[BrowseMediaSource] = []
        user_id = self._get_user_id(coordinator)

        if user_id:
            result = await coordinator.client.async_get_items(
                user_id,
                parent_id=library_id,
                include_item_types="Movie",
                recursive=True,
                years=year,
            )
            for item in result.get("Items", []):
                children.append(self._item_to_browse_media_source(coordinator, item))

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(
                coordinator.server_id, "movieyearitems", f"{library_id}/{year}"
            ),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title=year,
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_movie_decades(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
    ) -> BrowseMediaSource:
        """Browse movies by decade."""
        decades = [
            "2020s",
            "2010s",
            "2000s",
            "1990s",
            "1980s",
            "1970s",
            "1960s",
            "1950s",
            "1940s",
            "1930s",
            "1920s",
        ]
        children: list[BrowseMediaSource] = []

        for decade in decades:
            children.append(
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=build_identifier(
                        coordinator.server_id,
                        "moviedecadeitems",
                        f"{library_id}/{decade}",
                    ),
                    media_class=MediaClass.DIRECTORY,
                    media_content_type=MediaType.VIDEO,
                    title=decade,
                    can_play=False,
                    can_expand=True,
                )
            )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(coordinator.server_id, "moviedecade", library_id),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title="Decade",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_movies_by_decade(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
        decade: str,
    ) -> BrowseMediaSource:
        """Browse movies from a specific decade."""
        children: list[BrowseMediaSource] = []
        user_id = self._get_user_id(coordinator)

        if user_id:
            # Parse decade to get year range
            start_year = int(decade[:-1])
            years_param = ",".join(str(y) for y in range(start_year, start_year + 10))

            result = await coordinator.client.async_get_items(
                user_id,
                parent_id=library_id,
                include_item_types="Movie",
                recursive=True,
                years=years_param,
            )
            for item in result.get("Items", []):
                children.append(self._item_to_browse_media_source(coordinator, item))

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(
                coordinator.server_id, "moviedecadeitems", f"{library_id}/{decade}"
            ),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title=decade,
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_movie_genres(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
    ) -> BrowseMediaSource:
        """Browse movie genres."""
        children: list[BrowseMediaSource] = []
        user_id = self._get_user_id(coordinator)

        if user_id:
            genres = await coordinator.client.async_get_genres(
                user_id, parent_id=library_id, include_item_types="Movie"
            )
            for genre in genres:
                genre_id = genre.get("Id", "")
                genre_name = genre.get("Name", "Unknown")
                children.append(
                    BrowseMediaSource(
                        domain=DOMAIN,
                        identifier=build_identifier(
                            coordinator.server_id,
                            "moviegenreitems",
                            f"{library_id}/{genre_id}",
                        ),
                        media_class=MediaClass.GENRE,
                        media_content_type=MediaType.VIDEO,
                        title=genre_name,
                        can_play=False,
                        can_expand=True,
                    )
                )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(coordinator.server_id, "moviegenre", library_id),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title="Genre",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_movies_by_genre(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
        genre_id: str,
    ) -> BrowseMediaSource:
        """Browse movies in a specific genre."""
        children: list[BrowseMediaSource] = []
        user_id = self._get_user_id(coordinator)

        if user_id:
            result = await coordinator.client.async_get_items(
                user_id,
                parent_id=library_id,
                include_item_types="Movie",
                recursive=True,
                genre_ids=genre_id,
            )
            for item in result.get("Items", []):
                children.append(self._item_to_browse_media_source(coordinator, item))

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(
                coordinator.server_id, "moviegenreitems", f"{library_id}/{genre_id}"
            ),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title="Genre",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_movie_collections(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
    ) -> BrowseMediaSource:
        """Browse movie collections (BoxSets)."""
        children: list[BrowseMediaSource] = []
        user_id = self._get_user_id(coordinator)

        if user_id:
            result = await coordinator.client.async_get_items(
                user_id,
                parent_id=library_id,
                include_item_types="BoxSet",
                recursive=True,
            )
            for item in result.get("Items", []):
                children.append(
                    self._item_to_browse_media_source(coordinator, item, content_type="collection")
                )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(coordinator.server_id, "moviecollection", library_id),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title="Collections",
            can_play=False,
            can_expand=True,
            children=children,
        )

    # ==================== TV Library Browsing ====================

    async def _async_browse_tv_library(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
    ) -> BrowseMediaSource:
        """Browse TV library categories."""
        categories = [
            ("A-Z", "tvaz", MediaClass.DIRECTORY),
            ("Year", "tvyear", MediaClass.DIRECTORY),
            ("Decade", "tvdecade", MediaClass.DIRECTORY),
            ("Genre", "tvgenre", MediaClass.DIRECTORY),
        ]

        children: list[BrowseMediaSource] = []
        for title, content_type, media_class in categories:
            children.append(
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=build_identifier(coordinator.server_id, content_type, library_id),
                    media_class=media_class,
                    media_content_type=MediaType.VIDEO,
                    title=title,
                    can_play=False,
                    can_expand=True,
                )
            )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(coordinator.server_id, "tvlibrary", library_id),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title="TV Shows",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_tv_az(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
    ) -> BrowseMediaSource:
        """Browse TV shows A-Z menu."""
        letters = [*"ABCDEFGHIJKLMNOPQRSTUVWXYZ", "#"]
        children: list[BrowseMediaSource] = []

        for letter in letters:
            children.append(
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=build_identifier(
                        coordinator.server_id, "tvazletter", f"{library_id}/{letter}"
                    ),
                    media_class=MediaClass.DIRECTORY,
                    media_content_type=MediaType.VIDEO,
                    title=letter,
                    can_play=False,
                    can_expand=True,
                )
            )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(coordinator.server_id, "tvaz", library_id),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title="A-Z",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_tv_by_letter(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
        letter: str,
    ) -> BrowseMediaSource:
        """Browse TV shows starting with a letter."""
        children: list[BrowseMediaSource] = []
        user_id = self._get_user_id(coordinator)

        if user_id:
            name_filter = None if letter == "#" else letter
            result = await coordinator.client.async_get_items(
                user_id,
                parent_id=library_id,
                include_item_types="Series",
                recursive=True,
                name_starts_with=name_filter,
            )
            for item in result.get("Items", []):
                children.append(
                    self._item_to_browse_media_source(coordinator, item, content_type="series")
                )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(
                coordinator.server_id, "tvazletter", f"{library_id}/{letter}"
            ),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title=letter,
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_tv_years(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
    ) -> BrowseMediaSource:
        """Browse available years for TV shows."""
        children: list[BrowseMediaSource] = []
        user_id = self._get_user_id(coordinator)

        if user_id:
            years = await coordinator.client.async_get_years(
                user_id, parent_id=library_id, include_item_types="Series"
            )
            for year_item in years:
                year_name = year_item.get("Name", "Unknown")
                children.append(
                    BrowseMediaSource(
                        domain=DOMAIN,
                        identifier=build_identifier(
                            coordinator.server_id,
                            "tvyearitems",
                            f"{library_id}/{year_name}",
                        ),
                        media_class=MediaClass.DIRECTORY,
                        media_content_type=MediaType.VIDEO,
                        title=year_name,
                        can_play=False,
                        can_expand=True,
                    )
                )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(coordinator.server_id, "tvyear", library_id),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title="Year",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_tv_by_year(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
        year: str,
    ) -> BrowseMediaSource:
        """Browse TV shows from a specific year."""
        children: list[BrowseMediaSource] = []
        user_id = self._get_user_id(coordinator)

        if user_id:
            result = await coordinator.client.async_get_items(
                user_id,
                parent_id=library_id,
                include_item_types="Series",
                recursive=True,
                years=year,
            )
            for item in result.get("Items", []):
                children.append(
                    self._item_to_browse_media_source(coordinator, item, content_type="series")
                )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(
                coordinator.server_id, "tvyearitems", f"{library_id}/{year}"
            ),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title=year,
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_tv_decades(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
    ) -> BrowseMediaSource:
        """Browse TV shows by decade."""
        decades = [
            "2020s",
            "2010s",
            "2000s",
            "1990s",
            "1980s",
            "1970s",
            "1960s",
            "1950s",
        ]
        children: list[BrowseMediaSource] = []

        for decade in decades:
            children.append(
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=build_identifier(
                        coordinator.server_id, "tvdecadeitems", f"{library_id}/{decade}"
                    ),
                    media_class=MediaClass.DIRECTORY,
                    media_content_type=MediaType.VIDEO,
                    title=decade,
                    can_play=False,
                    can_expand=True,
                )
            )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(coordinator.server_id, "tvdecade", library_id),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title="Decade",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_tv_by_decade(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
        decade: str,
    ) -> BrowseMediaSource:
        """Browse TV shows from a specific decade."""
        children: list[BrowseMediaSource] = []
        user_id = self._get_user_id(coordinator)

        if user_id:
            start_year = int(decade[:-1])
            years_param = ",".join(str(y) for y in range(start_year, start_year + 10))

            result = await coordinator.client.async_get_items(
                user_id,
                parent_id=library_id,
                include_item_types="Series",
                recursive=True,
                years=years_param,
            )
            for item in result.get("Items", []):
                children.append(
                    self._item_to_browse_media_source(coordinator, item, content_type="series")
                )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(
                coordinator.server_id, "tvdecadeitems", f"{library_id}/{decade}"
            ),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title=decade,
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_tv_genres(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
    ) -> BrowseMediaSource:
        """Browse TV show genres."""
        children: list[BrowseMediaSource] = []
        user_id = self._get_user_id(coordinator)

        if user_id:
            genres = await coordinator.client.async_get_genres(
                user_id, parent_id=library_id, include_item_types="Series"
            )
            for genre in genres:
                genre_id = genre.get("Id", "")
                genre_name = genre.get("Name", "Unknown")
                children.append(
                    BrowseMediaSource(
                        domain=DOMAIN,
                        identifier=build_identifier(
                            coordinator.server_id,
                            "tvgenreitems",
                            f"{library_id}/{genre_id}",
                        ),
                        media_class=MediaClass.GENRE,
                        media_content_type=MediaType.VIDEO,
                        title=genre_name,
                        can_play=False,
                        can_expand=True,
                    )
                )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(coordinator.server_id, "tvgenre", library_id),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title="Genre",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_tv_by_genre(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
        genre_id: str,
    ) -> BrowseMediaSource:
        """Browse TV shows in a specific genre."""
        children: list[BrowseMediaSource] = []
        user_id = self._get_user_id(coordinator)

        if user_id:
            result = await coordinator.client.async_get_items(
                user_id,
                parent_id=library_id,
                include_item_types="Series",
                recursive=True,
                genre_ids=genre_id,
            )
            for item in result.get("Items", []):
                children.append(
                    self._item_to_browse_media_source(coordinator, item, content_type="series")
                )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(
                coordinator.server_id, "tvgenreitems", f"{library_id}/{genre_id}"
            ),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title="Genre",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_item(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        content_type: str,
        item_id: str | None,
    ) -> BrowseMediaSource:
        """Browse an item's children (e.g., series seasons, album tracks).

        Args:
            coordinator: The server's coordinator.
            content_type: The content type.
            item_id: The item ID to browse.

        Returns:
            Browse result with item children.
        """
        children: list[BrowseMediaSource] = []
        user_id = self._get_user_id(coordinator)

        if user_id and item_id:
            if content_type == "series":
                # Get seasons
                seasons = await coordinator.client.async_get_seasons(user_id, item_id)
                for season in seasons:
                    season_browse = self._item_to_browse_media_source(
                        coordinator, season, content_type="season"
                    )
                    children.append(season_browse)
            elif content_type == "season":
                # Get episodes - item_id here is the season ID
                # We need the series ID from the season
                result = await coordinator.client.async_get_items(
                    user_id,
                    parent_id=item_id,
                    include_item_types="Episode",
                )
                for episode in result.get("Items", []):
                    ep_browse = self._item_to_browse_media_source(coordinator, episode)
                    children.append(ep_browse)
            else:
                # Generic fallback for folders and other expandable types
                result = await coordinator.client.async_get_items(
                    user_id,
                    parent_id=item_id,
                )
                for child_item in result.get("Items", []):
                    child_browse = self._item_to_browse_media_source(coordinator, child_item)
                    children.append(child_browse)

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(coordinator.server_id, content_type, item_id),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title=content_type.title(),
            can_play=False,
            can_expand=True,
            children=children,
        )

    def _item_to_browse_media_source(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        item: EmbyBrowseItem,
        content_type: str | None = None,
    ) -> BrowseMediaSource:
        """Convert Emby item to BrowseMediaSource.

        Args:
            coordinator: The server's coordinator.
            item: The Emby item dictionary.
            content_type: Override content type.

        Returns:
            BrowseMediaSource for the item.
        """
        item_id = item["Id"]
        item_name = item["Name"]
        item_type = item["Type"].lower()

        if content_type is None:
            content_type = item_type

        can_play = item_type in ("movie", "episode", "audio", "musicvideo", "tvchannel")
        can_expand = item_type in ("series", "season", "album", "folder")

        media_class = self._get_media_class_for_type(item_type)
        media_content_type = MediaType.MUSIC if item_type in ("audio", "album") else MediaType.VIDEO

        thumbnail: str | None = None
        image_tags = item.get("ImageTags")
        if image_tags is not None and image_tags.get("Primary"):
            thumbnail = coordinator.client.get_image_url(item_id)

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(coordinator.server_id, content_type, item_id),
            media_class=media_class,
            media_content_type=media_content_type,
            title=item_name,
            can_play=can_play,
            can_expand=can_expand,
            thumbnail=thumbnail,
        )

    def _get_media_class_for_collection(self, collection_type: str) -> MediaClass:
        """Get media class for collection type.

        Args:
            collection_type: The Emby collection type.

        Returns:
            Appropriate MediaClass.
        """
        mapping: dict[str, MediaClass] = {
            "movies": MediaClass.DIRECTORY,
            "tvshows": MediaClass.TV_SHOW,
            "music": MediaClass.MUSIC,
            "homevideos": MediaClass.VIDEO,
            "photos": MediaClass.IMAGE,
        }
        return mapping.get(collection_type, MediaClass.DIRECTORY)

    def _get_media_class_for_type(self, item_type: str) -> MediaClass:
        """Get media class for item type.

        Args:
            item_type: The Emby item type.

        Returns:
            Appropriate MediaClass.
        """
        mapping: dict[str, MediaClass] = {
            "movie": MediaClass.MOVIE,
            "series": MediaClass.TV_SHOW,
            "season": MediaClass.SEASON,
            "episode": MediaClass.EPISODE,
            "audio": MediaClass.TRACK,
            "album": MediaClass.ALBUM,
            "musicvideo": MediaClass.VIDEO,
        }
        return mapping.get(item_type, MediaClass.VIDEO)

    async def async_resolve_media(
        self,
        item: MediaSourceItem,
    ) -> PlayMedia:
        """Resolve media item to a playable URL.

        Args:
            item: The media source item to resolve.

        Returns:
            PlayMedia with URL and MIME type.

        Raises:
            Unresolvable: If the item cannot be resolved.
        """
        if item.identifier is None:
            raise Unresolvable("No identifier provided")

        server_id, content_type, item_id = parse_identifier(item.identifier)

        if content_type is None or item_id is None:
            raise Unresolvable(f"Invalid identifier format: {item.identifier}")

        coordinator = self._get_coordinator(server_id)
        if coordinator is None:
            raise Unresolvable(f"Server {server_id} not found")

        # Generate stream URL based on content type
        if content_type in ("track", "audio"):
            url = coordinator.client.get_audio_stream_url(item_id)
            mime_type = MIME_TYPES.get(content_type, "audio/mpeg")
        else:
            url = coordinator.client.get_video_stream_url(item_id)
            mime_type = MIME_TYPES.get(content_type, "video/mp4")

        return PlayMedia(url=url, mime_type=mime_type)
