"""Support to interface with the Emby API."""

# Pyright settings – this module intentionally overrides several
# ``cached_property`` descriptors from Home Assistant core with *regular*
# ``@property`` getters because the underlying values need to update on every
# read (they are **not** static).  This triggers
# *reportIncompatibleVariableOverride* diagnostics as the descriptor types do
# not match.  Suppress the noise for the whole file so we can keep the code
# concise without sprinkling `# pyright: ignore[override]` on dozens of
# properties.

# pyright: reportIncompatibleVariableOverride=false

from __future__ import annotations

import logging

from pyemby import EmbyServer
import voluptuous as vol

from homeassistant.helpers import config_validation as cv

# NOTE: Home Assistant exports most *MediaPlayer* helper enums/constants via
# *homeassistant.components.media_player.const*.  Importing from the package
# root works at runtime because the module re-exports the names, however the
# public typing stubs mark these symbols as *private* re-exports which causes
# Pyright to raise *reportPrivateImportUsage*.  Import directly from the
# canonical public location instead so static analysis is happy.

from homeassistant.components.media_player import (
    PLATFORM_SCHEMA as MEDIA_PLAYER_PLATFORM_SCHEMA,
    MediaPlayerEntity,
)
# -----------------------------------------------------------------------------
# Home Assistant *media_player* constants & helpers
# -----------------------------------------------------------------------------

from homeassistant.components.media_player.const import (
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)

# ``MediaPlayerEnqueue`` was added to Home Assistant 2024.11.  Older Core
# releases (and therefore CI environments pinned to earlier versions) do not
# expose the enum yet.  Import it when available and fall back to a *local*
# poly-fill that mimics the public interface so the integration remains
# compatible with both old and new versions.

from enum import Enum

try:
    # Home Assistant ≥2024.11
    from homeassistant.components.media_player.const import MediaPlayerEnqueue as _HAEnqueue

    MediaPlayerEnqueue = _HAEnqueue  # type: ignore[invalid-name]
except (ImportError, AttributeError):  # pragma: no cover – fallback path

    class MediaPlayerEnqueue(str, Enum):  # type: ignore[override] – local shim
        """Minimal replacement that reflects the official Core enum values."""

        PLAY = "play"
        NEXT = "next"
        ADD = "add"

# Re-export for *mypy/pyright* consumers – the alias is always defined.
__all__: list[str] = [
    # public HA helpers
    "MediaPlayerEnqueue",
]
from homeassistant.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_PORT,
    CONF_SSL,
    DEVICE_DEFAULT_NAME,
    EVENT_HOMEASSISTANT_START,
    EVENT_HOMEASSISTANT_STOP,
)
# -----------------------------------------------------------------------------
# Additional imports required for media browsing support (issue #24 / task #27)
# -----------------------------------------------------------------------------

# Media browsing helpers from Home Assistant core.
# NOTE: ``media_source`` fallback support (GitHub issue #28) relies on the
# *async_browse_media* helper which lives in the *media_source* component.  We
# import it lazily via the package namespace so that test-suites which stub
# Home Assistant can inject a lightweight replacement before this module is
# imported.
# *BrowseMedia* lives in *browse_media* sub-module but the *MediaClass* enum
# was moved to the public *const* module in Home Assistant core.  Importing it
# from the old location triggers a Pyright *reportPrivateImportUsage* error.

from homeassistant.components.media_player.browse_media import BrowseMedia
from homeassistant.components.media_player.const import MediaClass

# Alias the *media_source* component so our code can delegate browsing requests
# for paths outside the Emby namespace (i.e. ``media-source://``).  The import
# is intentionally placed **after** the standard library ones so that unit
# tests may inject a stub implementation via *sys.modules* before importing
# this integration module.

from homeassistant.components import media_source as ha_media_source  # noqa: WPS433 - runtime import is acceptable

from urllib.parse import urlparse, parse_qs, urlencode

# Home Assistant helper error type
from homeassistant.exceptions import HomeAssistantError

# -----------------------------------------------------------------------------
# Constants & small mappings used by the browsing helpers
# -----------------------------------------------------------------------------

_EMBY_URI_SCHEME = "emby"

# Number of children fetched per request - kept deliberately small so that the
# browse tree stays responsive on large libraries.  Users can navigate further
# via the automatically generated "Next →" / "← Prev" nodes.
_PAGE_SIZE = 100

# Mapping Emby Item `Type` → Home Assistant `MediaClass` / content_type.  The
# table is based on the design document attached to GitHub issue #25.

_ITEM_TYPE_MAP: dict[str, tuple[MediaClass, str, bool, bool]] = {
    # ItemType: (media_class, content_type, can_play, can_expand)
    "Collection": (MediaClass.DIRECTORY, "directory", False, True),
    "Folder": (MediaClass.DIRECTORY, "directory", False, True),
    "Movie": (MediaClass.MOVIE, "movie", True, False),
    "Episode": (MediaClass.EPISODE, "episode", True, False),
    "Season": (MediaClass.SEASON, "season", False, True),
    "Series": (MediaClass.TV_SHOW, "tvshow", False, True),
    "MusicAlbum": (MediaClass.ALBUM, "album", False, True),
    "Audio": (MediaClass.TRACK, "music", True, False),
    "Playlist": (MediaClass.PLAYLIST, "playlist", True, True),
    "TvChannel": (MediaClass.CHANNEL, "channel", True, False),
    "Trailer": (MediaClass.VIDEO, "video", True, False),
    "Video": (MediaClass.VIDEO, "video", True, False),
}

# Fallback mapping for library / root views where `CollectionType` is returned
# instead of `Type`.
_COLLECTION_TYPE_MAP: dict[str, tuple[MediaClass, str]] = {
    "movies": (MediaClass.MOVIE, "movies"),
    "tvshows": (MediaClass.TV_SHOW, "tvshow"),
    "music": (MediaClass.MUSIC, "music"),
    "livetv": (MediaClass.CHANNEL, "channel"),
    "playlists": (MediaClass.PLAYLIST, "playlist"),
}

# -----------------------------------------------------------------------------
# Service data validation - ``media_player.play_media``
# -----------------------------------------------------------------------------

# Home Assistant passes the *media_type* and *media_id* parameters explicitly
# to :py:meth:`async_play_media`, while any additional fields are forwarded via
# **kwargs.  We build a small voluptuous schema so the integration fails fast
# and with useful error messages when mis-used.

# The play_media service passes a **service data** dictionary which ends up in
# ``**kwargs`` when Home Assistant calls :py:meth:`async_play_media`.  The
# schema below validates this dictionary for *backwards-compatibility* –
# callers invoking the method directly should use the new keyword parameters
# instead.

# Supported values for *enqueue*:
# * bool – legacy flag (*True*  → queue after current, *False* → play now)
# * str  – one of the new enum identifiers ("play", "next", "add")

_ENQUEUE_SCHEMA = vol.Any(cv.boolean, vol.In([e.value for e in MediaPlayerEnqueue]))

PLAY_MEDIA_SCHEMA = vol.Schema(
    {
        vol.Required("media_type"): cv.string,
        vol.Required("media_id"): cv.string,
        vol.Optional("enqueue"): _ENQUEUE_SCHEMA,
        vol.Optional("announce"): cv.boolean,
        # Optional start position in **seconds** – translated to Emby ticks
        vol.Optional("position"): vol.All(cv.positive_int, vol.Range(min=0)),
    },
    extra=vol.ALLOW_EXTRA,
)

from homeassistant.core import HomeAssistant, callback
# The `cv` alias already imported above.
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

MEDIA_TYPE_TRAILER = "trailer"

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8096
DEFAULT_SSL_PORT = 8920
DEFAULT_SSL = False

SUPPORT_EMBY = (
    MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.PREVIOUS_TRACK
    | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.SEEK
    | MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.PLAY_MEDIA
)

PLATFORM_SCHEMA = MEDIA_PLAYER_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_HOST, default=DEFAULT_HOST): cv.string,
        vol.Optional(CONF_PORT): cv.port,
        vol.Optional(CONF_SSL, default=DEFAULT_SSL): cv.boolean,
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Emby platform."""

    host = config.get(CONF_HOST)
    key = config.get(CONF_API_KEY)
    port = config.get(CONF_PORT)
    ssl = config[CONF_SSL]

    if port is None:
        port = DEFAULT_SSL_PORT if ssl else DEFAULT_PORT

    _LOGGER.debug("Setting up Emby server at: %s:%s", host, port)

    emby = EmbyServer(host, key, port, ssl, hass.loop)

    active_emby_devices: dict[str, EmbyDevice] = {}
    inactive_emby_devices: dict[str, EmbyDevice] = {}

    @callback
    def device_update_callback(data):
        """Handle devices which are added to Emby."""
        new_devices = []
        active_devices = []
        for dev_id, dev in emby.devices.items():
            active_devices.append(dev_id)
            if (
                dev_id not in active_emby_devices
                and dev_id not in inactive_emby_devices
            ):
                new = EmbyDevice(emby, dev_id)
                active_emby_devices[dev_id] = new
                new_devices.append(new)

            elif dev_id in inactive_emby_devices and dev.state != "Off":
                add = inactive_emby_devices.pop(dev_id)
                active_emby_devices[dev_id] = add
                _LOGGER.debug("Showing %s, item: %s", dev_id, add)
                add.set_available(True)

        if new_devices:
            _LOGGER.debug("Adding new devices: %s", new_devices)
            async_add_entities(new_devices, True)

    @callback
    def device_removal_callback(data):
        """Handle the removal of devices from Emby."""
        if data in active_emby_devices:
            rem = active_emby_devices.pop(data)
            inactive_emby_devices[data] = rem
            _LOGGER.debug("Inactive %s, item: %s", data, rem)
            rem.set_available(False)

    @callback
    def start_emby(event):
        """Start Emby connection."""
        emby.start()

    async def stop_emby(event):
        """Stop Emby connection."""
        await emby.stop()

    emby.add_new_devices_callback(device_update_callback)
    emby.add_stale_devices_callback(device_removal_callback)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, start_emby)
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_emby)


class EmbyDevice(MediaPlayerEntity):
    """Representation of an Emby device."""

    _attr_should_poll = False

    def __init__(self, emby, device_id):
        """Initialize the Emby device."""
        _LOGGER.debug("New Emby Device initialized with ID: %s", device_id)
        self.emby = emby
        self.device_id = device_id
        self.device = self.emby.devices[self.device_id]

        self.media_status_last_position = None
        self.media_status_received = None

        # Keep track of the most recent Emby *session id* for this device so
        # that play_media and other remote-control helpers can reliably target
        # the correct websocket session even though Emby regenerates ids at
        # every new playback.
        self._current_session_id: str | None = self.device.session_id

        # Home Assistant modern entity model – use the *_attr_* pattern so we
        # avoid overriding a long list of simple ``@property`` helpers.  This
        # dramatically reduces boilerplate and aligns with the current best
        # practices enforced by Pyright / HA dev-tools (see GitHub issue #61).

        # * Display name shown in the UI never changes after construction so
        #   we can set it once.
        self._attr_name = f"Emby {self.device.name}" if self.device.name else DEVICE_DEFAULT_NAME

        # * Feature flags only depend on whether the target device supports
        #   Emby's remote-control API which is a static capability.  Capture
        #   the information up-front so we do not need a dedicated property
        #   override anymore.
        self._attr_supported_features = (
            SUPPORT_EMBY if self.device.supports_remote_control else MediaPlayerEntityFeature(0)
        )

        # Expose availability via the standard dynamic attribute so callers
        # can still toggle it through *set_available()*.
        self._attr_available = True

        self._attr_unique_id = device_id

    async def async_added_to_hass(self) -> None:
        """Register callback."""
        self.emby.add_update_callback(self.async_update_callback, self.device_id)

    @callback
    def async_update_callback(self, msg):
        """Handle device updates."""
        # Always capture the latest session id provided by pyemby so external
        # helpers can request it on-demand.
        self._current_session_id = self.device.session_id
        # Check if we should update progress
        if self.device.media_position:
            if self.device.media_position != self.media_status_last_position:
                self.media_status_last_position = self.device.media_position
                self.media_status_received = dt_util.utcnow()
        elif not self.device.is_nowplaying:
            # No position, but we have an old value and are still playing
            self.media_status_last_position = None
            self.media_status_received = None

        self.async_write_ha_state()

    # ---------------------------------------------------------------------
    # Public helper - session id mapping (used by play_media helper)
    # ---------------------------------------------------------------------

    def get_current_session_id(self) -> str | None:
        """Return the most recent Emby `SessionId` for this device.

        The value updates every time a playstate websocket event is received.
        If the device is idle (no active session) the method returns *None*.
        """

        return self._current_session_id

    def set_available(self, value: bool) -> None:
        """Set available property."""
        self._attr_available = value

    @property
    def supports_remote_control(self):
        """Return control ability."""
        return self.device.supports_remote_control

    @property  # pyright: ignore[override]
    def state(self) -> MediaPlayerState | None:
        """Return the state of the device."""
        state = self.device.state
        if state == "Paused":
            return MediaPlayerState.PAUSED
        if state == "Playing":
            return MediaPlayerState.PLAYING
        if state == "Idle":
            return MediaPlayerState.IDLE
        if state == "Off":
            return MediaPlayerState.OFF
        return None






    # ------------------------------------------------------------------
    # Home Assistant media browsing implementation (issue #24 - task #27)
    # ------------------------------------------------------------------

    async def async_browse_media(
        self,
        media_content_type: str | None = None,
        media_content_id: str | None = None,
    ) -> BrowseMedia:  # noqa: D401 - verbatim HA signature
        """Return a BrowseMedia tree for the requested path.

        The method implements a minimal yet fully functional browsing
        hierarchy that surfaces the user's Emby *views* (libraries) at the
        root level and then delegates to `/Items/{id}/Children` for deeper
        navigation.

        * ``media_content_id`` ``None`` → root (libraries)
        * ``emby://<item_id>[?start=N]`` → children or leaf depending on
          whether the item can expand / play.

        Pagination is handled by *synthetic* "Prev" / "Next" nodes which the
        UI can follow to request subsequent slices of the list.  Each slice
        returns up to ``_PAGE_SIZE`` items.
        """


        # --------------------------------------------------------------
        # Home Assistant *media_source* fallback (issue #28)
        # --------------------------------------------------------------

        if media_content_id and media_content_id.startswith("media-source://"):
            # Delegate the request - Home Assistant core handles all built-in
            # libraries (TTS, local media, etc.).  We purposefully pass *None*
            # for the *entity_id* parameter because the current integration
            # does not expose one.  The helper accepts *None* which instructs
            # it to return a generic browse tree detached from a specific
            # media_player entity.

            if self.hass is None:
                raise HomeAssistantError("media_source browsing requires Home Assistant context")

            browse_result = await ha_media_source.async_browse_media(
                self.hass,
                media_content_id,
            )

            # The helper returns *None* when the path is invalid - convert to
            # a standard Home Assistant error so the frontend can display a
            # proper message to the user instead of crashing.
            if browse_result is None:
                raise HomeAssistantError("media_source path not found")

            return browse_result

        # --------------------------------------------------------------
        # Emby library browsing (default path)
        # --------------------------------------------------------------

        api = self._get_emby_api()

        # Determine the Emby user id - we look it up from the current session
        # object (preferred) falling back to a fresh sessions call when not
        # available (e.g. player is idle on HA startup).
        user_id: str | None = self.device.session_raw.get("UserId")
        if not user_id:
            sessions = await api.get_sessions(force_refresh=True)
            for sess in sessions:
                if sess.get("DeviceId") in (self.device_id, getattr(self.device, "unique_id", None)):
                    user_id = sess.get("UserId")
                    break

        if not user_id:
            raise HomeAssistantError("Unable to determine Emby user for media browsing")

        # ------------------------------------------------------------------
        # ROOT LEVEL - libraries / views
        # ------------------------------------------------------------------

        if not media_content_id:  # root browse
            views = await api.get_user_views(user_id)
            children: list[BrowseMedia] = [
                self._emby_view_to_browse(item) for item in views
            ]

            # Assemble the root node
            return BrowseMedia(
                title="Emby Library",
                media_class=MediaClass.DIRECTORY,
                media_content_id="emby://root",
                media_content_type="directory",
                can_play=False,
                can_expand=True,
                children=children,
            )

        # ------------------------------------------------------------------
        # CHILD LEVEL - parse URI and decide whether to return children or a
        # playable leaf node.
        # ------------------------------------------------------------------

        item_id, start_idx = self._parse_emby_uri(media_content_id)

        # Fetch metadata for the item to know whether it can expand.
        item = await api.get_item(item_id)
        if item is None:
            raise HomeAssistantError("Emby item not found - the library may have changed")

        media_class, content_type, can_play, can_expand = self._map_item_type(item)

        # If the item is playable *and* cannot expand we simply return the leaf
        # node - Home Assistant will subsequently call `async_play_media` when
        # the user clicks it.
        if not can_expand:
            return BrowseMedia(
                title=item.get("Name", "Unknown"),
                media_class=media_class,
                media_content_id=media_content_id,
                media_content_type=content_type,
                can_play=can_play,
                can_expand=False,
                children=None,
                thumbnail=self._build_thumbnail_url(item),
            )

        # ------------------------------------------------------------------
        # Expandable directory - fetch children slice.
        # ------------------------------------------------------------------

        slice_payload = await api.get_item_children(
            item_id,
            user_id=user_id,
            start_index=start_idx,
            limit=_PAGE_SIZE,
        )

        # Extract children & total count - defend against edge cases.
        child_items: list[dict] = slice_payload.get("Items", []) if isinstance(slice_payload, dict) else []
        total_count: int = slice_payload.get("TotalRecordCount", len(child_items)) if isinstance(slice_payload, dict) else len(child_items)

        children: list[BrowseMedia] = [self._emby_item_to_browse(child) for child in child_items]

        # Pagination - prepend/append prev/next nodes when applicable.
        if start_idx > 0:
            prev_start = max(0, start_idx - _PAGE_SIZE)
            children.insert(
                0,
                self._make_pagination_node("← Prev", item_id, prev_start),
            )

        if (start_idx + _PAGE_SIZE) < total_count:
            next_start = start_idx + _PAGE_SIZE
            children.append(
                self._make_pagination_node("Next →", item_id, next_start),
            )

        # Assemble directory node
        return BrowseMedia(
            title=item.get("Name", "Unknown"),
            media_class=media_class,
            media_content_id=media_content_id,
            media_content_type=content_type,
            can_play=can_play,
            can_expand=True,
            children=children,
            thumbnail=self._build_thumbnail_url(item),
        )

    # ------------------------------------------------------------------
    # Private helpers - browser building
    # ------------------------------------------------------------------

    def _parse_emby_uri(self, value: str) -> tuple[str, int]:
        """Return (item_id, start_index) parsed from *value*.

        Any `media_content_id` not conforming to the `emby://` scheme raises
        a :class:`HomeAssistantError`.  The only exception is the
        ``media-source://`` scheme which is intercepted *before* this helper
        is called so the request can be delegated to Home Assistant’s
        *media_source* component.
        """

        parsed = urlparse(value)
        if parsed.scheme != _EMBY_URI_SCHEME:
            raise HomeAssistantError("Unsupported media_content_id - expected emby:// URI")

        item_id = parsed.netloc or parsed.path.lstrip("/")  # netloc holds first segment when no // present
        if not item_id:
            raise HomeAssistantError("Invalid emby URI - missing item id")

        qs = parse_qs(parsed.query)
        start_idx = int(qs.get("start", [0])[0])
        return item_id, start_idx

    def _map_item_type(self, item: dict) -> tuple[MediaClass, str, bool, bool]:  # noqa: ANN401 - JSON in
        """Return mapping tuple for an Emby item payload."""

        item_type = item.get("Type") or item.get("CollectionType") or "Folder"

        if item_type in _ITEM_TYPE_MAP:
            return _ITEM_TYPE_MAP[item_type]

        # Fallback for collection types when not in main map
        if item_type in _COLLECTION_TYPE_MAP:
            mc, ct = _COLLECTION_TYPE_MAP[item_type]
            return (mc, ct, False, True)

        # Unknown type - treat as generic directory
        return (MediaClass.DIRECTORY, "directory", False, True)

    def _emby_item_to_browse(self, item: dict) -> BrowseMedia:  # noqa: ANN401
        """Convert a generic Emby item to a BrowseMedia node."""

        media_class, content_type, can_play, can_expand = self._map_item_type(item)
        item_id = str(item.get("Id"))
        uri = f"{_EMBY_URI_SCHEME}://{item_id}"

        return BrowseMedia(
            title=item.get("Name", "Unknown"),
            media_class=media_class,
            media_content_id=uri,
            media_content_type=content_type,
            can_play=can_play,
            can_expand=can_expand,
            thumbnail=self._build_thumbnail_url(item),
        )

    def _emby_view_to_browse(self, item: dict) -> BrowseMedia:  # noqa: ANN401
        """Convert a /Views item (library root) to a BrowseMedia node."""

        # /Views entries provide `CollectionType` instead of `Type`
        collection_type = item.get("CollectionType", "folder")
        media_class, content_type = _COLLECTION_TYPE_MAP.get(
            collection_type, (MediaClass.DIRECTORY, "directory")
        )

        item_id = str(item.get("Id"))
        uri = f"{_EMBY_URI_SCHEME}://{item_id}"

        return BrowseMedia(
            title=item.get("Name", "Unknown"),
            media_class=media_class,
            media_content_id=uri,
            media_content_type=content_type,
            can_play=False,
            can_expand=True,
            thumbnail=self._build_thumbnail_url(item),
        )

    def _build_thumbnail_url(self, item: dict) -> str | None:  # noqa: ANN401 - JSON
        """Return Emby image URL for *item* or *None* when not available."""

        # Prefer Primary image tag.
        image_tag = None
        if isinstance(item.get("ImageTags"), dict):
            image_tag = item["ImageTags"].get("Primary") or item["ImageTags"].get("Backdrop")

        if not image_tag:
            return None

        api = self._get_emby_api()
        # The EmbyAPI keeps the base URL without trailing slash.
        return f"{api._base}/Items/{item.get('Id')}/Images/Primary?tag={image_tag}&maxWidth=500"  # pylint: disable=protected-access

    def _make_pagination_node(self, title: str, parent_id: str, start: int) -> BrowseMedia:
        """Return a synthetic Prev/Next BrowseMedia directory node."""

        query = urlencode({"start": start})
        uri = f"{_EMBY_URI_SCHEME}://{parent_id}?{query}"

        return BrowseMedia(
            title=title,
            media_class=MediaClass.DIRECTORY,
            media_content_id=uri,
            media_content_type="directory",
            can_play=False,
            can_expand=True,
        )

    @property  # pyright: ignore[override]
    def app_name(self):
        """Return current user as app_name."""
        # Ideally the media_player object would have a user property.
        return self.device.username

    @property  # pyright: ignore[override]
    def media_content_id(self):
        """Content ID of current playing media."""
        return self.device.media_id

    @property  # pyright: ignore[override]
    def media_content_type(self) -> MediaType | str | None:
        """Content type of current playing media."""
        media_type = self.device.media_type
        if media_type == "Episode":
            return MediaType.TVSHOW
        if media_type == "Movie":
            return MediaType.MOVIE
        if media_type == "Trailer":
            return MEDIA_TYPE_TRAILER
        if media_type == "Music":
            return MediaType.MUSIC
        if media_type == "Video":
            return MediaType.VIDEO
        if media_type == "Audio":
            return MediaType.MUSIC
        if media_type == "TvChannel":
            return MediaType.CHANNEL
        return None

    @property  # pyright: ignore[override]
    def media_duration(self):
        """Return the duration of current playing media in seconds."""
        return self.device.media_runtime

    @property  # pyright: ignore[override]
    def media_position(self):
        """Return the position of current playing media in seconds."""
        return self.media_status_last_position

    @property  # pyright: ignore[override]
    def media_position_updated_at(self):
        """When was the position of the current playing media valid.

        Returns value from homeassistant.util.dt.utcnow().
        """
        return self.media_status_received

    @property  # pyright: ignore[override]
    def media_image_url(self):
        """Return the image URL of current playing media."""
        return self.device.media_image_url

    @property  # pyright: ignore[override]
    def media_title(self):
        """Return the title of current playing media."""
        return self.device.media_title

    @property  # pyright: ignore[override]
    def media_season(self):
        """Season of current playing media (TV Show only)."""
        return self.device.media_season

    @property  # pyright: ignore[override]
    def media_series_title(self):
        """Return the title of the series of current playing media (TV)."""
        return self.device.media_series_title

    @property  # pyright: ignore[override]
    def media_episode(self):
        """Return the episode of current playing media (TV only)."""
        return self.device.media_episode

    @property  # pyright: ignore[override]
    def media_album_name(self):
        """Return the album name of current playing media (Music only)."""
        return self.device.media_album_name

    @property  # pyright: ignore[override]
    def media_artist(self):
        """Return the artist of current playing media (Music track only)."""
        return self.device.media_artist

    @property  # pyright: ignore[override]
    def media_album_artist(self):
        """Return the album artist of current playing media (Music only)."""
        return self.device.media_album_artist


    # ------------------------------------------------------------------
    # Compatibility wrappers – allow unit-tests / external callers that
    # instantiate the class via ``__new__`` (bypassing ``__init__``) to still
    # receive meaningful default values.  This pattern is common in the test
    # suite which wires in stub *device* instances directly.
    # ------------------------------------------------------------------

    @property  # type: ignore[override]
    def supported_features(self) -> MediaPlayerEntityFeature:  # noqa: D401 – HA signature
        """Return feature flags taking *_attr_supported_features* into account.

        When the instance was created through the regular constructor the
        attribute is pre-computed and simply returned.  Should the attribute
        be missing (e.g. because the test-suite bypassed ``__init__``) we
        fall back to the legacy behaviour and derive the flags from the stub
        *device* object so assertions remain valid.
        """

        attr_val = getattr(self, "_attr_supported_features", None)
        # When the instance was created via ``__init__`` the value is an
        # *int*-backed ``MediaPlayerEntityFeature`` flag enum.  For raw
        # ``__new__`` constructions (as done by several unit-tests) the class
        # attribute inherited from Home Assistant is still a *property*
        # descriptor which we must ignore.

        from types import MemberDescriptorType, FunctionType  # local import avoid cost

        if (
            attr_val is not None
            and not isinstance(attr_val, (property, MemberDescriptorType, FunctionType))
            and attr_val != MediaPlayerEntityFeature(0)
        ):
            return attr_val  # type: ignore[return-value]

        # Legacy / test path – determine on demand.
        if getattr(self.device, "supports_remote_control", False):
            return SUPPORT_EMBY
        return MediaPlayerEntityFeature(0)

    # NOTE: The *name* property does not require a compatibility wrapper –
    # Home Assistant’s *Entity* base-class already returns ``_attr_name`` when
    # defined.  However, some unit-tests bypass ``__init__`` entirely which
    # means the attribute is never initialised.  Provide a small compatibility
    # shim so those tests continue to see the expected value without requiring
    # intrusive refactors.

    @property
    def name(self):  # type: ignore[override]
        """Return the display name handling both old & new attribute styles."""

        if hasattr(self, "_attr_name") and self._attr_name is not None:
            return self._attr_name

        # Legacy path – fabricate the value from the underlying *device*.
        dev_name = getattr(self.device, "name", None)
        if dev_name:
            return f"Emby {dev_name}"

        return DEVICE_DEFAULT_NAME

    @property  # pyright: ignore[override]
    def extra_state_attributes(self):
        """Expose additional attributes - mainly the live Emby session id."""
        return {
            "emby_session_id": self._current_session_id,
        }

    async def async_media_play(self) -> None:
        """Play media."""
        await self.device.media_play()

    async def async_media_pause(self) -> None:
        """Pause the media player."""
        await self.device.media_pause()

    async def async_media_stop(self) -> None:
        """Stop the media player."""
        await self.device.media_stop()

    async def async_media_next_track(self) -> None:
        """Send next track command."""
        await self.device.media_next()

    async def async_media_previous_track(self) -> None:
        """Send next track command."""
        await self.device.media_previous()

    async def async_media_seek(self, position: float) -> None:
        """Send seek command."""
        await self.device.media_seek(position)

    # ------------------------------------------------------------------
    # Home Assistant service handler - play_media
    # ------------------------------------------------------------------

    async def async_play_media(
        self,
        media_type: str | None,
        media_id: str,
        *,
        enqueue: MediaPlayerEnqueue | bool | str | None = None,
        announce: bool | None = None,
        **kwargs,
    ) -> None:  # noqa: D401 - verbatim HA signature
        """Handle the *play_media* service call for this entity.

        The implementation follows these steps:

        1. Validate + normalise arguments via ``PLAY_MEDIA_SCHEMA``.
        2. Resolve the payload to a concrete Emby ``ItemId`` using
           :pyfunc:`components.emby.search_resolver.resolve_media_item`.
        3. Determine the current Emby ``SessionId`` for the target device -
           refreshes the sessions list when necessary.
        4. Trigger remote playback through :class:`components.emby.api.EmbyAPI`.
        """

        from homeassistant.exceptions import HomeAssistantError

        # ------------------------------------------------------------------
        # 1. Merge fixed params with **kwargs and validate.
        # ------------------------------------------------------------------

        # ------------------------------------------------------------------
        # 0. Merge *service data* payload (kwargs) for compatibility.
        # ------------------------------------------------------------------

        # Home Assistant passes any additional service data into **kwargs**.
        # Combine it with the explicit parameters so we can reuse the existing
        # voluptuous schema for validation while still supporting the new
        # keyword arguments.

        payload = {
            "media_type": media_type,
            "media_id": media_id,
        }
        # Prefer explicit parameters over **kwargs**
        if enqueue is not None:
            payload["enqueue"] = enqueue
        elif "enqueue" in kwargs:
            payload["enqueue"] = kwargs["enqueue"]

        if announce is not None:
            payload["announce"] = announce
        elif "announce" in kwargs:
            payload["announce"] = kwargs["announce"]

        # Position is still supplied via service data only.
        if "position" in kwargs:
            payload["position"] = kwargs["position"]

        try:
            validated = PLAY_MEDIA_SCHEMA(payload)
        except vol.Invalid as exc:
            raise HomeAssistantError(f"Invalid play_media payload: {exc}") from exc

        raw_enqueue = validated.get("enqueue")
        announce_flag: bool = validated.get("announce", False)
        position: int | None = validated.get("position")

        # ------------------------------------------------------------------
        # Normalise *enqueue* → MediaPlayerEnqueue | None
        # ------------------------------------------------------------------

        enqueue_enum: MediaPlayerEnqueue | None = None

        if raw_enqueue is None:
            enqueue_enum = None
        elif isinstance(raw_enqueue, MediaPlayerEnqueue):
            enqueue_enum = raw_enqueue
        elif isinstance(raw_enqueue, bool):
            # Legacy flag – True → NEXT; False acts as omitted / play now
            enqueue_enum = MediaPlayerEnqueue.NEXT if raw_enqueue else None
        elif isinstance(raw_enqueue, str):
            try:
                enqueue_enum = MediaPlayerEnqueue(raw_enqueue)
            except ValueError as exc:
                raise HomeAssistantError(
                    f"Invalid enqueue value '{raw_enqueue}' – expected one of {[e.value for e in MediaPlayerEnqueue]}"
                ) from exc
        else:  # pragma: no cover – schema should have blocked this
            raise HomeAssistantError("Unsupported type for 'enqueue' parameter")

        # ------------------------------------------------------------------
        # 2. Resolve to a concrete Emby item.
        # ------------------------------------------------------------------

        # Lazily instantiate the minimal API helper - we reuse it across calls
        # so that session caching etc. remains effective.
        api = self._get_emby_api()

        from .search_resolver import resolve_media_item, MediaLookupError

        try:
            item = await resolve_media_item(
                api,
                media_type=media_type,
                media_id=media_id,
                user_id=None,  # TODO: expose user choice in a future update
            )
        except MediaLookupError as exc:
            raise HomeAssistantError(str(exc)) from exc

        item_id = item.get("Id") or item.get("id")
        if not item_id:
            raise HomeAssistantError("Emby item did not contain an 'Id' key")

        # ------------------------------------------------------------------
        # 3. Determine / refresh session id mapping.
        # ------------------------------------------------------------------

        session_id = await self._resolve_session_id(api)
        if not session_id:
            raise HomeAssistantError("Unable to determine active Emby session for device")

        # ------------------------------------------------------------------
        # 4. Trigger playback.
        # ------------------------------------------------------------------

        if announce_flag:
            play_command = "PlayAnnouncement"
        else:
            if enqueue_enum is None or enqueue_enum == MediaPlayerEnqueue.PLAY:
                play_command = "PlayNow"
            else:
                # Map enum → Emby command.  According to the Emby REST docs
                # valid values are PlayNow, PlayNext, PlayLast, PlayInstantMix
                # and PlayShuffle.

                if enqueue_enum == MediaPlayerEnqueue.NEXT:
                    play_command = "PlayNext"
                elif enqueue_enum == MediaPlayerEnqueue.ADD:
                    play_command = "PlayLast"
                else:  # pragma: no cover – defensive fallback
                    play_command = "PlayNext"

        start_ticks: int | None = None
        if position is not None:
            start_ticks = position * 10_000_000  # seconds -> 100 ns ticks

        try:
            await api.play(session_id, [item_id], play_command=play_command, start_position_ticks=start_ticks)
        except Exception as exc:  # broad catch -> wrap as HA error
            raise HomeAssistantError(f"Emby playback failed: {exc}") from exc

        # Optimistically update entity state; full state will come via websocket.
        # Record the session id so future calls can skip the lookup step.  The
        # websocket listener will soon deliver a play_state update which will
        # refresh entity attributes, but we trigger a state write now for a
        # snappier UI.
        self._current_session_id = session_id
        self.async_write_ha_state()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_emby_api(self):
        """Return (and cache) a lazily-instantiated :class:`EmbyAPI`."""

        if not hasattr(self, "_emby_api"):
            from .api import EmbyAPI  # local import to avoid cycles

            server = self.emby  # pyemby.EmbyServer instance
            self._emby_api = EmbyAPI(
                self.hass,
                host=server._host,  # pylint: disable=protected-access
                api_key=server._api_key,  # pylint: disable=protected-access
                port=server._port,  # pylint: disable=protected-access
                ssl=server._ssl,  # pylint: disable=protected-access
            )

        return self._emby_api

    async def _resolve_session_id(self, api):
        """Return a fresh session id for this player (refreshing if needed)."""

        # Fast-path - existing mapping.
        if self._current_session_id:
            return self._current_session_id

        # Poll the Sessions endpoint to find a matching device when idle / new.
        try:
            sessions = await api.get_sessions(force_refresh=True)
        except Exception as exc:  # noqa: BLE001 - wrap as generic
            _LOGGER.warning("Could not refresh Emby sessions: %s", exc)
            return None

        # Each session payload includes a DeviceId we can correlate with the
        # stable id used by pyemby (self.device.id / self.device.unique_id).
        for sess in sessions:
            if sess.get("DeviceId") in (self.device_id, getattr(self.device, "unique_id", None)):
                self._current_session_id = sess.get("Id")
                return self._current_session_id

        return None