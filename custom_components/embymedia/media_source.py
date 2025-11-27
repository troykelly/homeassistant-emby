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

from .const import DOMAIN, MIME_TYPES, DeviceProfile, EmbyBrowseItem, MediaSourceInfo
from .exceptions import EmbyError
from .profiles import get_device_profile

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


class EmbyMediaSource(MediaSource):
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
        # Track active transcoding sessions: play_session_id -> device_id
        self._active_sessions: dict[str, str] = {}

    def register_session(self, play_session_id: str, device_id: str) -> None:
        """Register an active transcoding session.

        Args:
            play_session_id: The play session ID from Emby.
            device_id: The device ID associated with the session.
        """
        self._active_sessions[play_session_id] = device_id
        _LOGGER.debug(
            "Registered transcoding session %s for device %s",
            play_session_id,
            device_id,
        )

    def unregister_session(self, play_session_id: str) -> None:
        """Unregister a transcoding session.

        Args:
            play_session_id: The play session ID to remove.
        """
        if play_session_id in self._active_sessions:
            del self._active_sessions[play_session_id]
            _LOGGER.debug("Unregistered transcoding session %s", play_session_id)

    def get_active_sessions(self) -> dict[str, str]:
        """Get a copy of active transcoding sessions.

        Returns:
            Dictionary mapping play_session_id to device_id.
        """
        return dict(self._active_sessions)

    async def async_cleanup_sessions(
        self,
        coordinator: EmbyDataUpdateCoordinator,
    ) -> None:
        """Clean up all active transcoding sessions.

        Called when the integration is unloaded to stop any active
        transcoding sessions on the server.

        Args:
            coordinator: The coordinator with the client to use.
        """
        if not self._active_sessions:
            return

        _LOGGER.debug(
            "Cleaning up %d active transcoding sessions",
            len(self._active_sessions),
        )

        # Stop each transcoding session
        for play_session_id, device_id in list(self._active_sessions.items()):
            try:
                await coordinator.client.async_stop_transcoding(
                    device_id=device_id,
                    play_session_id=play_session_id,
                )
                _LOGGER.debug(
                    "Stopped transcoding session %s for device %s",
                    play_session_id,
                    device_id,
                )
            except Exception:
                _LOGGER.warning(
                    "Failed to stop transcoding session %s",
                    play_session_id,
                    exc_info=True,
                )

        # Clear all sessions
        self._active_sessions.clear()

    def _get_coordinators(self) -> dict[str, EmbyDataUpdateCoordinator]:
        """Get all configured Emby coordinators.

        Returns:
            Dictionary mapping server IDs to coordinators.
        """
        coordinators: dict[str, EmbyDataUpdateCoordinator] = {}

        # Get coordinators from config entries' runtime_data
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if hasattr(entry, "runtime_data") and entry.runtime_data is not None:
                coordinator = entry.runtime_data.session_coordinator
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
        if content_type == "moviestudio" and item_id:
            return await self._async_browse_movie_studios(coordinator, item_id)
        if content_type == "moviestudioitems" and item_id:
            parts = item_id.split("/")
            if len(parts) >= 2:
                return await self._async_browse_movies_by_studio(coordinator, parts[0], parts[1])

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
        if content_type == "tvstudio" and item_id:
            return await self._async_browse_tv_studios(coordinator, item_id)
        if content_type == "tvstudioitems" and item_id:
            parts = item_id.split("/")
            if len(parts) >= 2:
                return await self._async_browse_tv_by_studio(coordinator, parts[0], parts[1])

        # Music library category routing
        if content_type == "musiclibrary" and item_id:
            return await self._async_browse_music_library(coordinator, item_id)
        if content_type == "musicartists" and item_id:
            return await self._async_browse_music_artists(coordinator, item_id)
        if content_type == "musicartistletter" and item_id:
            parts = item_id.split("/")
            if len(parts) >= 2:
                return await self._async_browse_artists_by_letter(coordinator, parts[0], parts[1])
        if content_type == "musicalbums" and item_id:
            return await self._async_browse_music_albums(coordinator, item_id)
        if content_type == "musicalbumletter" and item_id:
            parts = item_id.split("/")
            if len(parts) >= 2:
                return await self._async_browse_albums_by_letter(coordinator, parts[0], parts[1])
        if content_type == "musicgenres" and item_id:
            return await self._async_browse_music_genres(coordinator, item_id)
        if content_type == "musicgenreitems" and item_id:
            parts = item_id.split("/")
            if len(parts) >= 2:
                return await self._async_browse_genre_items(coordinator, parts[0], parts[1])
        if content_type == "musicplaylists" and item_id:
            return await self._async_browse_music_playlists(coordinator, item_id)

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
                    identifier = build_identifier(coordinator.server_id, "musiclibrary", view_id)
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
            ("Studio", "moviestudio", MediaClass.DIRECTORY),
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
            try:
                years = await coordinator.client.async_get_years(
                    user_id, parent_id=library_id, include_item_types="Movie"
                )
            except EmbyError as err:
                _LOGGER.debug("Failed to get movie years: %s", err)
                years = []

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
            try:
                result = await coordinator.client.async_get_items(
                    user_id,
                    parent_id=library_id,
                    include_item_types="Movie",
                    recursive=True,
                    years=year,
                )
                items = result.get("Items", [])
            except EmbyError as err:
                _LOGGER.debug("Failed to get movies by year %s: %s", year, err)
                items = []

            for item in items:
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

    async def _async_browse_movie_studios(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
    ) -> BrowseMediaSource:
        """Browse movie studios."""
        children: list[BrowseMediaSource] = []
        user_id = self._get_user_id(coordinator)

        if user_id:
            studios = await coordinator.client.async_get_studios(
                user_id, parent_id=library_id, include_item_types="Movie"
            )
            for studio in studios:
                studio_id = studio.get("Id", "")
                studio_name = studio.get("Name", "Unknown")
                children.append(
                    BrowseMediaSource(
                        domain=DOMAIN,
                        identifier=build_identifier(
                            coordinator.server_id,
                            "moviestudioitems",
                            f"{library_id}/{studio_id}",
                        ),
                        media_class=MediaClass.DIRECTORY,
                        media_content_type=MediaType.VIDEO,
                        title=studio_name,
                        can_play=False,
                        can_expand=True,
                    )
                )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(coordinator.server_id, "moviestudio", library_id),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title="Studio",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_movies_by_studio(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
        studio_id: str,
    ) -> BrowseMediaSource:
        """Browse movies from a specific studio."""
        children: list[BrowseMediaSource] = []
        user_id = self._get_user_id(coordinator)

        if user_id:
            result = await coordinator.client.async_get_items(
                user_id,
                parent_id=library_id,
                include_item_types="Movie",
                recursive=True,
                studio_ids=studio_id,
            )
            for item in result.get("Items", []):
                children.append(self._item_to_browse_media_source(coordinator, item))

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(
                coordinator.server_id, "moviestudioitems", f"{library_id}/{studio_id}"
            ),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title="Studio",
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
            ("Studio", "tvstudio", MediaClass.DIRECTORY),
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
            try:
                years = await coordinator.client.async_get_years(
                    user_id, parent_id=library_id, include_item_types="Series"
                )
            except EmbyError as err:
                _LOGGER.debug("Failed to get TV years: %s", err)
                years = []

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
            try:
                result = await coordinator.client.async_get_items(
                    user_id,
                    parent_id=library_id,
                    include_item_types="Series",
                    recursive=True,
                    years=year,
                )
                items = result.get("Items", [])
            except EmbyError as err:
                _LOGGER.debug("Failed to get TV shows by year %s: %s", year, err)
                items = []

            for item in items:
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

    async def _async_browse_tv_studios(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
    ) -> BrowseMediaSource:
        """Browse TV studios/networks."""
        children: list[BrowseMediaSource] = []
        user_id = self._get_user_id(coordinator)

        if user_id:
            studios = await coordinator.client.async_get_studios(
                user_id, parent_id=library_id, include_item_types="Series"
            )
            for studio in studios:
                studio_id = studio.get("Id", "")
                studio_name = studio.get("Name", "Unknown")
                children.append(
                    BrowseMediaSource(
                        domain=DOMAIN,
                        identifier=build_identifier(
                            coordinator.server_id,
                            "tvstudioitems",
                            f"{library_id}/{studio_id}",
                        ),
                        media_class=MediaClass.DIRECTORY,
                        media_content_type=MediaType.VIDEO,
                        title=studio_name,
                        can_play=False,
                        can_expand=True,
                    )
                )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(coordinator.server_id, "tvstudio", library_id),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title="Studio",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_tv_by_studio(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
        studio_id: str,
    ) -> BrowseMediaSource:
        """Browse TV shows from a specific studio/network."""
        children: list[BrowseMediaSource] = []
        user_id = self._get_user_id(coordinator)

        if user_id:
            result = await coordinator.client.async_get_items(
                user_id,
                parent_id=library_id,
                include_item_types="Series",
                recursive=True,
                studio_ids=studio_id,
            )
            for item in result.get("Items", []):
                children.append(
                    self._item_to_browse_media_source(coordinator, item, content_type="series")
                )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(
                coordinator.server_id, "tvstudioitems", f"{library_id}/{studio_id}"
            ),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title="Studio",
            can_play=False,
            can_expand=True,
            children=children,
        )

    # =========================================================================
    # Music Library Browsing Methods
    # =========================================================================

    async def _async_browse_music_library(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
    ) -> BrowseMediaSource:
        """Browse a music library - show category menu.

        Music libraries show categories (Artists, Albums, Genres, Playlists)
        to organize large collections effectively.

        Args:
            coordinator: The server's coordinator.
            library_id: The music library ID.

        Returns:
            BrowseMediaSource with categories as children.
        """
        categories = [
            ("Artists", "musicartists", MediaClass.DIRECTORY),
            ("Albums", "musicalbums", MediaClass.DIRECTORY),
            ("Genres", "musicgenres", MediaClass.DIRECTORY),
            ("Playlists", "musicplaylists", MediaClass.PLAYLIST),
        ]

        children: list[BrowseMediaSource] = []
        for title, content_type, media_class in categories:
            children.append(
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=build_identifier(coordinator.server_id, content_type, library_id),
                    media_class=media_class,
                    media_content_type=MediaType.MUSIC,
                    title=title,
                    can_play=False,
                    can_expand=True,
                )
            )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(coordinator.server_id, "musiclibrary", library_id),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.MUSIC,
            title="Music Library",
            can_play=False,
            can_expand=True,
            children=children,
        )

    def _build_letter_menu(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        content_type: str,
        library_id: str,
    ) -> list[BrowseMediaSource]:
        """Build A-Z letter menu for large library navigation.

        Args:
            coordinator: The server's coordinator.
            content_type: The content type prefix (e.g., 'musicartistletter').
            library_id: The library ID.

        Returns:
            List of BrowseMediaSource items for # and A-Z letters.
        """
        letters = ["#"] + [chr(i) for i in range(ord("A"), ord("Z") + 1)]
        children: list[BrowseMediaSource] = []

        for letter in letters:
            children.append(
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=build_identifier(
                        coordinator.server_id, content_type, f"{library_id}/{letter}"
                    ),
                    media_class=MediaClass.DIRECTORY,
                    media_content_type=MediaType.MUSIC,
                    title=letter,
                    can_play=False,
                    can_expand=True,
                )
            )

        return children

    async def _async_browse_music_artists(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
    ) -> BrowseMediaSource:
        """Browse music artists category - show A-Z letter menu.

        Args:
            coordinator: The server's coordinator.
            library_id: The music library ID.

        Returns:
            BrowseMediaSource with A-Z letters as children.
        """
        children = self._build_letter_menu(coordinator, "musicartistletter", library_id)

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(coordinator.server_id, "musicartists", library_id),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.MUSIC,
            title="Artists",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_artists_by_letter(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
        letter: str,
    ) -> BrowseMediaSource:
        """Browse artists starting with a specific letter.

        Args:
            coordinator: The server's coordinator.
            library_id: The music library ID.
            letter: The letter to filter by (# for numbers/symbols).

        Returns:
            BrowseMediaSource with filtered artists as children.
        """
        children: list[BrowseMediaSource] = []
        user_id = self._get_user_id(coordinator)

        if user_id:
            try:
                # For "#", we need special handling - Emby uses empty string for non-alpha
                name_filter = "" if letter == "#" else letter

                result = await coordinator.client.async_get_items(
                    user_id,
                    parent_id=library_id,
                    include_item_types="MusicArtist",
                    recursive=True,
                    name_starts_with=name_filter if name_filter else None,
                )
                items = result.get("Items", [])

                # For "#", filter to non-alpha items manually
                if letter == "#":
                    items = [i for i in items if not i.get("Name", "")[0:1].isalpha()]

            except EmbyError as err:
                _LOGGER.debug("Failed to get artists by letter %s: %s", letter, err)
                items = []

            for item in items:
                children.append(
                    self._item_to_browse_media_source(coordinator, item, content_type="artist")
                )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(
                coordinator.server_id, "musicartistletter", f"{library_id}/{letter}"
            ),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.MUSIC,
            title=f"Artists - {letter}",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_music_albums(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
    ) -> BrowseMediaSource:
        """Browse music albums category - show A-Z letter menu.

        Args:
            coordinator: The server's coordinator.
            library_id: The music library ID.

        Returns:
            BrowseMediaSource with A-Z letters as children.
        """
        children = self._build_letter_menu(coordinator, "musicalbumletter", library_id)

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(coordinator.server_id, "musicalbums", library_id),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.MUSIC,
            title="Albums",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_albums_by_letter(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
        letter: str,
    ) -> BrowseMediaSource:
        """Browse albums starting with a specific letter.

        Args:
            coordinator: The server's coordinator.
            library_id: The music library ID.
            letter: The letter to filter by.

        Returns:
            BrowseMediaSource with filtered albums as children.
        """
        children: list[BrowseMediaSource] = []
        user_id = self._get_user_id(coordinator)

        if user_id:
            try:
                name_filter = "" if letter == "#" else letter

                result = await coordinator.client.async_get_items(
                    user_id,
                    parent_id=library_id,
                    include_item_types="MusicAlbum",
                    recursive=True,
                    name_starts_with=name_filter if name_filter else None,
                )
                items = result.get("Items", [])

                # For "#", filter to non-alpha items manually
                if letter == "#":
                    items = [i for i in items if not i.get("Name", "")[0:1].isalpha()]

            except EmbyError as err:
                _LOGGER.debug("Failed to get albums by letter %s: %s", letter, err)
                items = []

            for item in items:
                children.append(
                    self._item_to_browse_media_source(coordinator, item, content_type="album")
                )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(
                coordinator.server_id, "musicalbumletter", f"{library_id}/{letter}"
            ),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.MUSIC,
            title=f"Albums - {letter}",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_music_genres(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
    ) -> BrowseMediaSource:
        """Browse music genres.

        Args:
            coordinator: The server's coordinator.
            library_id: The music library ID.

        Returns:
            BrowseMediaSource with genres as children.
        """
        children: list[BrowseMediaSource] = []
        user_id = self._get_user_id(coordinator)

        if user_id:
            try:
                genres = await coordinator.client.async_get_music_genres(user_id, library_id)
            except EmbyError as err:
                _LOGGER.debug("Failed to get music genres: %s", err)
                genres = []

            for genre in genres:
                children.append(
                    BrowseMediaSource(
                        domain=DOMAIN,
                        identifier=build_identifier(
                            coordinator.server_id, "musicgenreitems", f"{library_id}/{genre['Id']}"
                        ),
                        media_class=MediaClass.GENRE,
                        media_content_type=MediaType.MUSIC,
                        title=genre["Name"],
                        can_play=False,
                        can_expand=True,
                    )
                )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(coordinator.server_id, "musicgenres", library_id),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.MUSIC,
            title="Genres",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_genre_items(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
        genre_id: str,
    ) -> BrowseMediaSource:
        """Browse items in a music genre.

        Args:
            coordinator: The server's coordinator.
            library_id: The music library ID.
            genre_id: The genre ID.

        Returns:
            BrowseMediaSource with albums in the genre as children.
        """
        children: list[BrowseMediaSource] = []
        user_id = self._get_user_id(coordinator)

        if user_id:
            try:
                # Fetch albums with this genre
                result = await coordinator.client.async_get_items(
                    user_id,
                    parent_id=library_id,
                    include_item_types="MusicAlbum",
                    recursive=True,
                    genre_ids=genre_id,
                )
                items = result.get("Items", [])
            except EmbyError as err:
                _LOGGER.debug("Failed to get genre items: %s", err)
                items = []

            for item in items:
                children.append(
                    self._item_to_browse_media_source(coordinator, item, content_type="album")
                )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(
                coordinator.server_id, "musicgenreitems", f"{library_id}/{genre_id}"
            ),
            media_class=MediaClass.GENRE,
            media_content_type=MediaType.MUSIC,
            title="Genre",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_browse_music_playlists(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        library_id: str,
    ) -> BrowseMediaSource:
        """Browse music playlists.

        Args:
            coordinator: The server's coordinator.
            library_id: The music library ID.

        Returns:
            BrowseMediaSource with playlists as children.
        """
        children: list[BrowseMediaSource] = []
        user_id = self._get_user_id(coordinator)

        if user_id:
            try:
                result = await coordinator.client.async_get_items(
                    user_id,
                    include_item_types="Playlist",
                    recursive=True,
                )
                items = result.get("Items", [])
            except EmbyError as err:
                _LOGGER.debug("Failed to get playlists: %s", err)
                items = []

            for item in items:
                children.append(
                    self._item_to_browse_media_source(coordinator, item, content_type="playlist")
                )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=build_identifier(coordinator.server_id, "musicplaylists", library_id),
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.MUSIC,
            title="Playlists",
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
            elif content_type == "artist":
                # Get albums for this artist
                albums = await coordinator.client.async_get_artist_albums(user_id, item_id)
                for album in albums:
                    album_browse = self._item_to_browse_media_source(
                        coordinator, album, content_type="album"
                    )
                    children.append(album_browse)
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
        can_expand = item_type in (
            "series",
            "season",
            "album",
            "musicalbum",
            "folder",
            "musicartist",
        )

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

    # =========================================================================
    # Transcoding Support Methods (Phase 13.5)
    # =========================================================================

    def _select_media_source(
        self,
        media_sources: list[MediaSourceInfo],
    ) -> MediaSourceInfo:
        """Select the best media source from available options.

        Priority order:
        1. Direct Play (most efficient, no server processing)
        2. Direct Stream (efficient, minimal processing)
        3. Transcoding (least efficient, requires server resources)

        Args:
            media_sources: List of available media sources.

        Returns:
            The selected media source.

        Raises:
            ValueError: If no media sources are available.
        """
        if not media_sources:
            raise ValueError("No media sources available")

        # Priority 1: Prefer direct play
        for source in media_sources:
            if source.get("SupportsDirectPlay"):
                return source

        # Priority 2: Prefer direct stream
        for source in media_sources:
            if source.get("SupportsDirectStream"):
                return source

        # Priority 3: Fall back to transcoding
        for source in media_sources:
            if source.get("SupportsTranscoding"):
                return source

        # Return first source if nothing matches (shouldn't happen)
        return media_sources[0]

    def _get_mime_type_for_container(self, container: str) -> str:
        """Get MIME type for container format.

        Args:
            container: Container format (mp4, mkv, mp3, etc.).

        Returns:
            MIME type string.
        """
        # Container to MIME type mapping
        mime_types: dict[str, str] = {
            # Video containers
            "mp4": "video/mp4",
            "m4v": "video/mp4",
            "mov": "video/quicktime",
            "mkv": "video/x-matroska",
            "webm": "video/webm",
            "avi": "video/x-msvideo",
            "wmv": "video/x-ms-wmv",
            "ts": "video/mp2t",
            "m2ts": "video/mp2t",
            # Audio containers
            "mp3": "audio/mpeg",
            "aac": "audio/aac",
            "m4a": "audio/mp4",
            "flac": "audio/flac",
            "wav": "audio/wav",
            "ogg": "audio/ogg",
            "opus": "audio/opus",
            "wma": "audio/x-ms-wma",
            # HLS
            "m3u8": "application/x-mpegURL",
        }
        return mime_types.get(container.lower(), "application/octet-stream")

    def _build_direct_stream_url(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        media_source: MediaSourceInfo,
    ) -> str:
        """Build authenticated direct stream URL.

        Args:
            coordinator: The coordinator with client access.
            media_source: The media source info.

        Returns:
            Full authenticated URL for direct streaming.
        """
        base_url = coordinator.client.base_url
        api_key = coordinator.client._api_key

        # Use DirectStreamUrl if provided
        direct_url = media_source.get("DirectStreamUrl")
        if direct_url:
            # DirectStreamUrl is relative, prepend base URL
            full_url = f"{base_url}{direct_url}"
            # Add API key if not already present
            if "api_key=" not in full_url:
                separator = "&" if "?" in full_url else "?"
                full_url = f"{full_url}{separator}api_key={api_key}"
            return full_url

        # Build URL from source ID (fallback)
        source_id = media_source.get("Id", "")
        container = media_source.get("Container", "mp4")
        return f"{base_url}/Videos/{source_id}/stream.{container}?api_key={api_key}&Static=true"

    def _build_transcoding_url(
        self,
        coordinator: EmbyDataUpdateCoordinator,
        media_source: MediaSourceInfo,
    ) -> str:
        """Build authenticated transcoding URL.

        Args:
            coordinator: The coordinator with client access.
            media_source: The media source info.

        Returns:
            Full authenticated URL for transcoded streaming.

        Raises:
            ValueError: If no transcoding URL is available.
        """
        transcoding_url = media_source.get("TranscodingUrl")
        if not transcoding_url:
            raise ValueError("No transcoding URL available in media source")

        base_url = coordinator.client.base_url
        api_key = coordinator.client._api_key

        # TranscodingUrl is relative, prepend base URL
        full_url = f"{base_url}{transcoding_url}"

        # Add API key if not already present
        if "api_key=" not in full_url:
            separator = "&" if "?" in full_url else "?"
            full_url = f"{full_url}{separator}api_key={api_key}"

        return full_url

    def _get_device_profile(
        self,
        coordinator: EmbyDataUpdateCoordinator,
    ) -> DeviceProfile:
        """Get device profile from config or use default.

        Args:
            coordinator: The coordinator with config entry.

        Returns:
            DeviceProfile to use for playback info requests.
        """
        # Get profile name from options
        profile_name = coordinator.config_entry.options.get("transcoding_profile", "universal")

        # Use get_device_profile which handles unknown names
        return get_device_profile(profile_name)

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
