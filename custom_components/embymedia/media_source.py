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
        domain_data = self.hass.data.get(DOMAIN, {})

        for entry_data in domain_data.values():
            if isinstance(entry_data, dict):
                coordinator = entry_data.get("coordinator")
                if coordinator is not None:
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

                children.append(
                    BrowseMediaSource(
                        domain=DOMAIN,
                        identifier=build_identifier(coordinator.server_id, "library", view_id),
                        media_class=media_class,
                        media_content_type=MediaType.VIDEO,
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

        can_play = item_type in ("movie", "episode", "audio", "musicvideo")
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
