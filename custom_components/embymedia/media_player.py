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
    from homeassistant.components.media_player.const import MediaPlayerEnqueue as _HAEnqueue  # type: ignore[attr-defined]

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
# stdlib typing helpers -------------------------------------------------------
from typing import Any

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

# Home Assistant *media_source* helpers – used for fallback browsing paths
# and to detect *media-source://* identifiers in a robust way (replaces the
# previous manual string check).

from homeassistant.components import media_source as ha_media_source  # noqa: WPS433 - runtime import is acceptable
from homeassistant.components.media_source import is_media_source_id

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

    # Live-TV recording types – surfaced via the *Live TV* section in Emby.
    # A *Recording* represents a single, directly playable file while
    # *RecordingSeries* groups multiple recordings under the same schedule.
    #
    # BoxSet is Emby’s term for a curated collection of movies or shows.  It
    # behaves like a folder from the user’s perspective.

    "Recording": (MediaClass.VIDEO, "recording", True, False),
    "RecordingSeries": (MediaClass.DIRECTORY, "recording_series", False, True),
    "BoxSet": (MediaClass.DIRECTORY, "boxset", False, True),
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
        # Optional explicit Emby user id/profile name for parental control.
        vol.Optional("user_id"): cv.string,
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
# -----------------------------------------------------------------------------
# Default Emby ports – fixes GitHub issue #181
# -----------------------------------------------------------------------------
# Emby's upstream defaults differ from the **generic** web ports used by the
# original implementation.  The incorrect values (80/443) prevented the
# integration from connecting when the user did **not** explicitly specify a
# custom *port* in the YAML or Config-Flow set-up.  Update the constants to
# match the upstream server defaults so that out-of-the-box configurations
# work again.

DEFAULT_PORT = 8096  # default HTTP port exposed by Emby
DEFAULT_SSL_PORT = 8920  # default HTTPS port exposed by Emby
DEFAULT_SSL = False

SUPPORT_EMBY = (
    MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.PREVIOUS_TRACK
    | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.SEEK
    | MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.PLAY_MEDIA
    # Issue #75 – expose volume & mute controls when the target device
    # supports Emby's remote-control API.  The flags are included in the
    # *base* capability mask so that the existing initialisation logic can
    # continue to apply the constant wholesale based on
    # ``device.supports_remote_control``.
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_MUTE
    # Issue #76 – expose shuffle & repeat controls when the target device
    # supports Emby's remote-control API. These flags utilise the modern
    # *MediaPlayerEntityFeature* values rather than the deprecated integer
    # constants for clarity and forward-compatibility.
    | MediaPlayerEntityFeature.SHUFFLE_SET
    | MediaPlayerEntityFeature.REPEAT_SET
    # Issue #77 – expose power on/off controls when supported.  Older Home
    # Assistant cores (<2024.11) did not yet ship the *TURN_ON* / *TURN_OFF*
    # feature flags.  Add them conditionally so the integration continues to
    # import on legacy versions used by the test-suite.
    | (
        MediaPlayerEntityFeature.TURN_ON
        if hasattr(MediaPlayerEntityFeature, "TURN_ON")
        else MediaPlayerEntityFeature(0)
    )
    | (
        MediaPlayerEntityFeature.TURN_OFF
        if hasattr(MediaPlayerEntityFeature, "TURN_OFF")
        else MediaPlayerEntityFeature(0)
    )
    # Issue #108 – expose browse, search, enqueue & announce capabilities so
    # the Home Assistant UI renders the Media panel and related controls.
    | (
        MediaPlayerEntityFeature.BROWSE_MEDIA
        if hasattr(MediaPlayerEntityFeature, "BROWSE_MEDIA")
        else MediaPlayerEntityFeature(0)
    )
    | (
        MediaPlayerEntityFeature.SEARCH_MEDIA
        if hasattr(MediaPlayerEntityFeature, "SEARCH_MEDIA")
        else MediaPlayerEntityFeature(0)
    )
    | (
        MediaPlayerEntityFeature.MEDIA_ENQUEUE
        if hasattr(MediaPlayerEntityFeature, "MEDIA_ENQUEUE")
        else MediaPlayerEntityFeature(0)
    )
    | (
        MediaPlayerEntityFeature.MEDIA_ANNOUNCE
        if hasattr(MediaPlayerEntityFeature, "MEDIA_ANNOUNCE")
        else MediaPlayerEntityFeature(0)
    )
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

        # Feature flags depend on the *current* capabilities reported by the
        # Emby client.  They may change while Home Assistant is running (for
        # example when the user disables the "Allow remote control" toggle in
        # the Emby settings).  Compute the initial mask via the shared helper
        # so we can reuse the same logic every time the payload updates – see
        # GitHub issue #88.

        self._update_supported_features()

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
        # Refresh feature flags *before* we propagate the state update so the
        # UI always reflects the latest capabilities.  The helper performs an
        # internal *no-op* when the mask remains unchanged to avoid
        # unnecessary entity registry churn.

        self._update_supported_features()

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
    # Private helpers – dynamic feature handling (GitHub issue #88)
    # ---------------------------------------------------------------------

    # ---------------------------------------------------------------------
    # Private helpers – permission / capability detection
    # ---------------------------------------------------------------------

    def _device_allows_remote_control(self) -> bool:  # noqa: D401 – simple helper
        """Return *True* when the underlying Emby device permits remote control.

        Emby 4.9 introduced a breaking change to the *Sessions* websocket
        payload: the previously *flat* ``SupportsRemoteControl`` field moved
        under the nested ``HasPermission.RemoteControl`` key.  When running
        against an updated server the original ``supports_remote_control``
        attribute exposed by *pyemby* therefore disappears and the integration
        falsely assumes that the client no longer supports transport
        controls.  This helper inspects **both** the legacy attribute *and*
        the new nested structure so we remain compatible with all supported
        server versions.
        """

        # 1. Preferred path – attribute exposed by *pyemby* up to Emby ≤ 4.8
        attr_val = getattr(self.device, "supports_remote_control", None)
        if attr_val is not None:
            return bool(attr_val)

        # 2. Fallback – inspect raw session dictionary (available on all
        #    *pyemby* device instances).
        session_raw = getattr(self.device, "session_raw", None)
        if isinstance(session_raw, dict):
            # a. Legacy flat key
            if "SupportsRemoteControl" in session_raw:
                return bool(session_raw.get("SupportsRemoteControl"))

            # b. New nested permission structure
            perms = session_raw.get("HasPermission")
            if isinstance(perms, dict):
                return bool(perms.get("RemoteControl", False))

        # Default – remote control not allowed / unknown
        return False

    def _update_supported_features(self) -> None:
        """Recalculate *supported_features* based on current capabilities.

        The method compares the freshly computed mask with the attribute’s
        previous value and only updates it when a change is detected to avoid
        needless entity state churn.  Callers must ensure
        :pyfunc:`async_write_ha_state` is invoked afterwards when a change
        should be propagated to Home Assistant.
        """

        new_mask: MediaPlayerEntityFeature = (
            SUPPORT_EMBY if self._device_allows_remote_control() else MediaPlayerEntityFeature(0)
        )

        # Assign when different so Home Assistant can pick up the change.
        if new_mask != getattr(self, "_attr_supported_features", None):
            self._attr_supported_features = new_mask

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
        """Return *True* when the device allows remote commands via Emby."""

        # Keep the public interface unchanged but delegate the logic to the
        # compatibility helper so callers transparently benefit from the new
        # detection code.
        return self._device_allows_remote_control()

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
        # Home Assistant passes ``media_content_type`` and
        # ``media_content_id`` *concatenated* in the second parameter when
        # routing *BrowseMedia* websocket calls – the value therefore looks
        # like ``"tvshow,emby://<id>"`` rather than a plain ``emby://`` URI.
        #
        # Older Home Assistant versions (and several unit-tests within this
        # repository) still call the helper with a *bare* URI.  Normalise the
        # incoming parameters so that downstream logic can assume
        # ``media_content_id`` contains a pure Emby identifier.
        #
        # GitHub issue #132 tracks the bug.
        # --------------------------------------------------------------

        if media_content_id and "," in media_content_id:
            possible_type, possible_id = media_content_id.split(",", 1)

            # Only treat the string as *combined* when the suffix clearly
            # carries an Emby or media-source URI.  This guards against edge
            # cases where a legitimate identifier may contain a comma (very
            # unlikely but defensive coding costs little).
            if possible_id.startswith("emby://") or possible_id.startswith("media-source://"):
                if not media_content_type:
                    media_content_type = possible_type
                media_content_id = possible_id

        # --------------------------------------------------------------
        # Home Assistant *media_source* fallback (issue #28)
        # --------------------------------------------------------------

        if media_content_id and is_media_source_id(media_content_id):
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

            # Normalise the *pyemby* device identifier – the library appends
            # the *Client* name to the raw *DeviceId* ("<id>.<Client>") while
            # the REST `/Sessions` payload strips that suffix.  Compare both
            # the full string **and** the bare prefix so we reliably match
            # regardless of the formatting differences.  GitHub issue #176.

            this_dev_prefix = self.device_id.split(".", 1)[0]
            for sess in sessions:
                sess_dev_id = sess.get("DeviceId")
                if not sess_dev_id:
                    continue

                if sess_dev_id in (
                    self.device_id,
                    getattr(self.device, "unique_id", None),
                    this_dev_prefix,
                ):
                    user_id = sess.get("UserId")
                    break

        if not user_id:
            raise HomeAssistantError("Unable to determine Emby user for media browsing")

        # ------------------------------------------------------------------
        # ROOT LEVEL - libraries / views
        # ------------------------------------------------------------------

        if not media_content_id:  # root browse
            views = await api.get_user_views(user_id)

            # GitHub issue #78 – prepend *virtual* directories for Resume &
            # Favorites so users can quickly access their personal lists.

            children: list[BrowseMedia] = []

            # Existing libraries first to keep the original ordering relied on
            # by unit-tests and to avoid breaking user muscle-memory.
            children.extend(self._emby_view_to_browse(item) for item in views)

            # Append virtual folders.  We *always* expose them even when the
            # underlying list may be empty because Emby will happily return
            # an empty collection which the UI renders gracefully.

            children.append(
                BrowseMedia(
                    title="Continue Watching",
                    media_class=MediaClass.DIRECTORY,
                    media_content_id=f"{_EMBY_URI_SCHEME}://resume",
                    media_content_type="directory",
                    can_play=False,
                    can_expand=True,
                    thumbnail=None,
                )
            )

            children.append(
                BrowseMedia(
                    title="Favorites",
                    media_class=MediaClass.DIRECTORY,
                    media_content_id=f"{_EMBY_URI_SCHEME}://favorites",
                    media_content_type="directory",
                    can_play=False,
                    can_expand=True,
                    thumbnail=None,
                )
            )

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

        # ------------------------------------------------------------------
        # Virtual directories – *resume* & *favorites*
        # ------------------------------------------------------------------

        if item_id in ("resume", "favorites"):
            if item_id == "resume":
                slice_payload = await api.get_resume_items(
                    user_id,
                    start_index=start_idx,
                    limit=_PAGE_SIZE,
                )
                title = "Continue Watching"
            else:  # "favorites"
                slice_payload = await api.get_favorite_items(
                    user_id,
                    start_index=start_idx,
                    limit=_PAGE_SIZE,
                )
                title = "Favorites"

            child_items: list[dict] = slice_payload.get("Items", []) if isinstance(slice_payload, dict) else []
            total_count: int = slice_payload.get("TotalRecordCount", len(child_items)) if isinstance(slice_payload, dict) else len(child_items)

            children = [self._emby_item_to_browse(child) for child in child_items]

            # Pagination nodes same logic as regular directories
            if start_idx > 0:
                prev_start = max(0, start_idx - _PAGE_SIZE)
                children.insert(0, self._make_pagination_node("← Prev", item_id, prev_start))

            if (start_idx + _PAGE_SIZE) < total_count:
                next_start = start_idx + _PAGE_SIZE
                children.append(self._make_pagination_node("Next →", item_id, next_start))

            return BrowseMedia(
                title=title,
                media_class=MediaClass.DIRECTORY,
                media_content_id=media_content_id,
                media_content_type="directory",
                can_play=False,
                can_expand=True,
                children=children,
            )

        # Fetch metadata for the item to know whether it can expand.  The
        # *EmbyAPI.get_item* helper (introduced in v0.30) accepts an optional
        # *user_id* keyword so it can fall back to the user-scoped Emby REST
        # endpoint when the global variant does not expose the requested
        # object (behaviour observed for TV shows – see GitHub issue #182).
        #
        # Earlier unit-test stubs still implement the *legacy* single-argument
        # signature therefore we inspect the callable at runtime and only
        # forward the *user_id* when the parameter is supported.  This keeps
        # the public behaviour untouched while avoiding a blanket refactor of
        # the extensive test-suite shipped with the repository.

        import inspect  # local import – very cheap & avoids polluting module top

        if "user_id" in inspect.signature(api.get_item).parameters:  # pragma: no cover – py311 signature caching
            item = await api.get_item(item_id, user_id=user_id)
        else:  # fallback for stubs / third-party overrides
            item = await api.get_item(item_id)
        # --------------------------------------------------------------
        # Fallback for *library roots* where `/Items/{id}` is not exposed.
        # --------------------------------------------------------------

        if item is None:
            # Some library containers (e.g. *Movies* / *TV Shows*) are *views*
            # only addressable through the *user scoped* `/Items` listing and
            # therefore do **not** resolve via `/Items/{id}` at all.  Treat
            # such ids as *generic directories* and obtain children through
            # the broader `/Users/{user}/Items?ParentId=` endpoint (issue
            # #167).

            # Retrieve user *views* (libraries) so we can determine whether
            # *item_id* actually represents a *library root* (e.g. *Movies*,
            # *TV Shows*).  Only in that case do we attempt the *expensive*
            # `/Users/{user}/Items` query.  This mirrors the original error
            # handling expectations exercised by
            # *tests/integration/emby/test_browse_media_hierarchy.py* where an
            # **unknown** identifier is meant to raise *HomeAssistantError*
            # **without** hitting additional REST endpoints.

            views_meta = await api.get_user_views(user_id)

            matched_view = next((v for v in views_meta if str(v.get("Id")) == item_id), None)

            # Item truly does not exist → propagate error so the UI shows red
            # banner – this path intentionally avoids the *user items* lookup
            # to keep the failure response lightweight and to maintain
            # backwards-compatibility with existing test-stubs that do not
            # implement the endpoint (see GitHub issue #161).
            if matched_view is None:
                raise HomeAssistantError("Emby item not found - the library may have changed")

            # ----------------------------------------------------------
            # Valid library root – fetch children slice for pagination.
            #
            # Special case *Live TV* which is **not** exposed via the generic
            # `/Users/{user}/Items` endpoint.  The server instead provides a
            # dedicated `/LiveTv/Channels` route returning `TvChannel` items.
            # Falling back to the *generic* endpoint results in a confusing
            # mix of unrelated objects (most notably *artists*) – exactly the
            # bug tracked in GitHub issue #202.
            # ----------------------------------------------------------

            if matched_view.get("CollectionType", "").lower() == "livetv":
                slice_payload = await api.get_live_tv_channels(
                    user_id,
                    start_index=start_idx,
                    limit=_PAGE_SIZE,
                )
            else:
                slice_payload = await api.get_user_items(
                    user_id,
                    parent_id=item_id,
                    start_index=start_idx,
                    limit=_PAGE_SIZE,
                )

            child_items: list[dict] = slice_payload.get("Items", []) if isinstance(slice_payload, dict) else []
            total_count: int = (
                slice_payload.get("TotalRecordCount", len(child_items)) if isinstance(slice_payload, dict) else len(child_items)
            )

            children = [self._emby_item_to_browse(child) for child in child_items]

            if start_idx > 0:
                prev_start = max(0, start_idx - _PAGE_SIZE)
                children.insert(0, self._make_pagination_node("← Prev", item_id, prev_start))

            if (start_idx + _PAGE_SIZE) < total_count:
                next_start = start_idx + _PAGE_SIZE
                children.append(self._make_pagination_node("Next →", item_id, next_start))

            media_class, content_type = _COLLECTION_TYPE_MAP.get(
                matched_view.get("CollectionType", "folder"),
                (MediaClass.DIRECTORY, "directory"),
            )

            return BrowseMedia(
                title=matched_view.get("Name", "Emby Directory"),
                media_class=media_class,
                media_content_id=media_content_id,
                media_content_type=content_type,
                can_play=False,
                can_expand=True,
                children=children,
            )

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
                # Conditionally proxy artwork – see issue #122.
                thumbnail=self._thumbnail_url(item_id),
            )

        # ------------------------------------------------------------------
        # Expandable directory - fetch children slice.
        # ------------------------------------------------------------------

        # Fetch children – some *library root* ids fail with 404 when routed
        # through the generic ``/Items/{id}/Children`` endpoint even though a
        # metadata lookup via ``/Items/{id}`` succeeds (behaviour observed
        # on Emby 4.8 for *Movies* / *TV Shows* top-level containers).  When
        # this happens we transparently fall back to the *user-scoped*
        # ``/Users/{id}/Items`` query which always works.  GitHub issue #176.

        from custom_components.embymedia.api import EmbyApiError  # local import to avoid circular

        # --------------------------------------------------------------
        # Special case – *Live TV* user view (GitHub issue #202)
        # --------------------------------------------------------------
        # When the Emby server is queried through the **user-scoped**
        #   `/Users/{id}/Items/{viewId}` endpoint the *Live TV* root resolves
        # to an object of ``Type == 'UserView'`` **with**
        # ``CollectionType == 'livetv'``.  Fetching children through the
        # generic ``/Items/{id}/Children`` route, however, yields a random
        # mix of *artists* and *audio tracks* instead of `TvChannel`
        # objects – the very bug tracked in issue #202.
        #
        # Detect that scenario up-front and route the request to the
        # dedicated ``/LiveTv/Channels`` helper instead of the generic
        # children listing.  This logic complements the earlier *library
        # root* fallback that handles the case where the *global* ``/Items``
        # lookup already failed (resulting in *item is None*).
        # --------------------------------------------------------------

        if item.get("CollectionType", "").lower() == "livetv":
            slice_payload = await api.get_live_tv_channels(
                user_id,
                start_index=start_idx,
                limit=_PAGE_SIZE,
            )
        else:
            try:
                slice_payload = await api.get_item_children(
                    item_id,
                    user_id=user_id,
                    start_index=start_idx,
                    limit=_PAGE_SIZE,
                )
            except EmbyApiError:
                # Fallback – treat *item_id* as *ParentId* under the user scope.
                slice_payload = await api.get_user_items(
                    user_id,
                    parent_id=item_id,
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
            # Thumbnails are served through the Home Assistant proxy so
            # remote users (Nabu Casa, reverse proxies) can access them
            # without a direct connection to the Emby server.
            thumbnail=self._thumbnail_url(item_id),
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
            thumbnail=self._thumbnail_url(item_id),
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
            # When dealing with a *root* Emby view the collection is known to
            # be *homogeneous* – e.g. the *Movies* library exclusively
            # contains movie items.  Surfacing the common media class via the
            # ``children_media_class`` attribute allows the Home Assistant
            # frontend to render the correct icon immediately without issuing
            # an additional network request for the first child entry.
            #
            # We deliberately omit the attribute for *generic* folders (where
            # ``media_class`` resolves to *DIRECTORY*) as the contained items
            # may differ in type causing the UI to mis-classify them.
            children_media_class=(media_class if media_class is not MediaClass.DIRECTORY else None),
            # Provide thumbnail – conditionally proxy through Home Assistant
            # only when the request originates from outside the local
            # network, as recommended by the Home Assistant developer
            # documentation.  Local requests are served the *direct* Emby
            # image URL which avoids unnecessary bandwidth usage and lowers
            # latency on the Home Assistant instance (GitHub issue #122).
            thumbnail=self._thumbnail_url(item_id),
        )

    # ------------------------------------------------------------------
    # Thumbnail utility – conditional proxying (issue #122)
    # ------------------------------------------------------------------

    def _thumbnail_url(self, item_id: str) -> str | None:
        """Return thumbnail URL following HA proxy guidance.

        When the incoming HTTP request originates from the *internal* network we
        can safely hand the browser the direct Emby image URL which avoids an
        unnecessary round-trip through Home Assistant.  For **external**
        clients we return the Home Assistant proxy endpoint produced by
        ``get_browse_image_url`` so that Home Assistant hides the Emby server
        details and handles authentication.
        """

        # Runtime import keeps home assistant stubs optional for unit tests.
        from homeassistant.helpers.network import is_internal_request  # noqa: WPS433 – allowed

        try:
            internal = is_internal_request(self.hass)
        except Exception:  # pragma: no cover – very defensive, always fallback
            internal = False

        if internal:
            api = self._get_emby_api()
            return f"{api._base}/Items/{item_id}/Images/Primary?maxWidth=500"  # pylint: disable=protected-access

        # External request – use HA proxy which will trigger *async_get_browse_image*.
        # We pass dummy *content_type* as it is only used for MIME heuristics
        # by the underlying helper.  The `MediaPlayerEntity` base class does
        # not validate the value beyond being truthy.
        return self.get_browse_image_url("image", item_id)

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

    # ------------------------------------------------------------------
    # Album-art proxy – Home Assistant > Emby
    # ------------------------------------------------------------------

    async def async_get_browse_image(  # noqa: D401 - verbatim HA signature
        self,
        media_content_type: str,
        media_content_id: str,
        media_image_id: str | None = None,
    ) -> tuple[bytes | None, str | None]:
        """Fetch artwork for *media browser* nodes via Home Assistant proxy.

        Home Assistant requests thumbnails from entities with an authenticated
        internal URL generated by
        :pyfunc:`homeassistant.components.media_player.MediaPlayerEntity.get_browse_image_url`.

        The default implementation returns ``(None, None)`` signalling *not
        implemented*.  We override the helper and retrieve the image bytes
        from the underlying Emby server so remote clients (Nabu Casa,
        reverse proxies) do **not** require direct network access.
        Security notes
        --------------
        The Home Assistant guidelines explicitly warn integrations to **never
        round-trip raw URLs** via the ``media_image_id`` argument as that would
        allow a malicious actor to coerce Home Assistant into fetching
        arbitrary internal resources.  The Emby integration does **not** make
        use of the argument at the moment – nevertheless we validate it to
        ensure future changes or forged API requests cannot introduce a
        vulnerability (GitHub issue #123).

        Acceptable values:

        • ``None`` – the common path when the frontend does not supply an
          identifier.
        • Opaque Emby identifiers (GUID / numeric ItemId).  These never
          contain a URI scheme or "//" separator.

        Any value that *looks like* a URL (contains ``://``) is rejected with
        :class:`homeassistant.exceptions.HomeAssistantError`.
        """

        # ------------------------------------------------------------------
        # Input validation – reject *media_image_id* that encodes a URL.  This
        # follows the security recommendation from HA developer docs.
        # ------------------------------------------------------------------

        if media_image_id and "://" in media_image_id:
            # Raising the error directly is safe because *HomeAssistantError*
            # is imported at module level.  Importing the symbol inside this
            # conditional would shadow the global binding and confuse static
            # analysis (Pyright would flag it as potentially unbound on code
            # paths that do **not** execute the branch).  Rely on the global
            # import instead.

            raise HomeAssistantError("media_image_id must not be a URL")

        # ------------------------------------------------------------------
        # media_source:// fallback – delegate to the core helper before we
        # attempt to build an Emby specific URL.  This allows automations or
        # UI flows that mix and match items from different sources to work
        # transparently (GitHub issue #136).
        # ------------------------------------------------------------------

        if is_media_source_id(media_content_id):
            # The media_source helper requires a valid Home Assistant context.
            # Guard against accidental early calls during entity set-up.
            if self.hass is None:  # pragma: no cover – defensive path
                raise HomeAssistantError("media_source browsing requires Home Assistant context")

            # *async_get_browse_image* is available starting with Home
            # Assistant 2024.6.  The typing stubs shipped with older Core
            # versions do not expose the helper which trips up Pyright’s
            # *reportAttributeAccessIssue* check.  The runtime implementation
            # is present in all supported versions, therefore we silence the
            # warning for static analysis.

            return await ha_media_source.async_get_browse_image(  # type: ignore[attr-defined]
                self.hass,
                media_content_id,
                media_image_id,
            )

        # ------------------------------------------------------------------
        # Construct the Emby artwork URL – we intentionally skip resolving the
        # *tag* query parameter as Emby will happily serve the latest cached
        # image without it.  Passing the explicit *tag* would require an
        # *additional* REST round-trip (*/Items/<id>) which is avoided for
        # performance reasons.
        # ------------------------------------------------------------------

        # Construct the Emby artwork URL – we intentionally skip resolving
        # the *tag* query parameter as Emby will happily serve the latest
        # cached image without it.  Passing the explicit *tag* would require
        # an *additional* REST round-trip (\*/Items/<id>) which is avoided
        # for performance reasons.

        api = self._get_emby_api()
        image_url = f"{api._base}/Items/{media_content_id}/Images/Primary?maxWidth=500"  # pylint: disable=protected-access

        image_bytes, content_type = await self._async_fetch_image(image_url)

        # When Emby returns an error (404, 401, …) the helper yields *None* –
        # propagate a standard Home Assistant error so the frontend can show
        # a placeholder icon instead of breaking the entire browse request.
        if image_bytes is None:
            raise HomeAssistantError("Unable to retrieve artwork from Emby server")

        return image_bytes, content_type

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
        if media_type == "Recording":
            return MediaType.VIDEO
        if media_type == "RecordingSeries":
            return "directory"
        if media_type == "BoxSet":
            return "directory"
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
        if self._device_allows_remote_control():
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

    # ------------------------------------------------------------------
    # Volume & mute support (GitHub issue #75)
    # ------------------------------------------------------------------

    @property  # type: ignore[override]
    def volume_level(self) -> float | None:  # noqa: D401 – HA naming convention
        """Return the current volume level (0.0 – 1.0) if reported by Emby.

        The Emby *session* payload exposes ``VolumeLevel`` as an **integer
        percentage** (0–100) nested under the ``PlayState`` object.  When the
        attribute is unavailable (older server, unsupported client, idle
        session …) the helper returns *None* so Home Assistant can gracefully
        disable the volume slider.
        """

        try:
            play_state = self.device.session_raw.get("PlayState", {})  # type: ignore[dict-item]
            vol_pct = play_state.get("VolumeLevel")
            if vol_pct is None:
                return None
            # Clamp & normalise – defensive against bad data.
            vol_pct = max(0, min(100, int(vol_pct)))
            return vol_pct / 100.0
        except Exception:  # pragma: no cover – any malformed payload treated as unknown
            return None

    @property  # type: ignore[override]
    def is_volume_muted(self) -> bool | None:  # noqa: D401 – HA naming convention
        """Return *True* when the client is muted (if known)."""

        try:
            play_state = self.device.session_raw.get("PlayState", {})  # type: ignore[dict-item]
            return play_state.get("IsMuted")  # type: ignore[return-value]
        except Exception:  # pragma: no cover – malformed payload
            return None

    async def async_set_volume_level(self, volume: float) -> None:
        """Set the absolute *volume* on the client.

        Home Assistant guarantees ``volume`` is between 0.0 and 1.0.  The
        helper converts the value to the percentage format required by Emby
        and relays it via :pyclass:`custom_components.embymedia.api.EmbyAPI`.
        """

        api = self._get_emby_api()
        session_id = await self._resolve_session_id(api)
        if not session_id:
            from homeassistant.exceptions import HomeAssistantError

            raise HomeAssistantError("Unable to determine active Emby session for volume control")

        try:
            await api.set_volume(session_id, volume)
        except Exception as exc:  # noqa: BLE001 – wrap all network/HTTP failures
            from homeassistant.exceptions import HomeAssistantError

            raise HomeAssistantError(f"Emby volume_set failed: {exc}") from exc

        # Optimistic state update – websocket will confirm shortly.
        self.async_write_ha_state()

    async def async_mute_volume(self, mute: bool) -> None:
        """Toggle mute state on the target client."""

        api = self._get_emby_api()
        session_id = await self._resolve_session_id(api)
        if not session_id:
            from homeassistant.exceptions import HomeAssistantError

            raise HomeAssistantError("Unable to determine active Emby session for mute control")

        try:
            await api.mute(session_id, mute)
        except Exception as exc:  # noqa: BLE001
            from homeassistant.exceptions import HomeAssistantError

            raise HomeAssistantError(f"Emby mute failed: {exc}") from exc

        self.async_write_ha_state()

    # ------------------------------------------------------------------
    # Shuffle & repeat support (GitHub issue #76)
    # ------------------------------------------------------------------

    # The *shuffle* and *repeat* helpers are modelled closely after the volume
    # implementation above:  property access translates the raw Emby session
    # payload into Home Assistant friendly types while the *async_set_*
    # service handlers delegate the actual command to :pyclass:`EmbyAPI`.

    # ----------------------
    # Properties – readonly
    # ----------------------

    @property  # type: ignore[override]
    def shuffle(self) -> bool | None:  # noqa: D401 – HA naming convention
        """Return *True* when shuffle is enabled on the client (if known)."""

        try:
            play_state = self.device.session_raw.get("PlayState", {})  # type: ignore[dict-item]
            # The official Emby schema exposes ``IsShuffled`` as a boolean
            # flag.  Fallback to *None* when the attribute is missing so that
            # Home Assistant disables the UI control gracefully.
            return play_state.get("IsShuffled")  # type: ignore[return-value]
        except Exception:  # pragma: no cover – malformed payload
            return None

    @property  # type: ignore[override]
    def repeat(self):  # type: ignore[override] – dynamic type depends on HA version
        """Return current repeat mode as a *RepeatMode* enum when available.

        Home Assistant 2024.11 introduced the public *RepeatMode* enum.  Older
        versions still rely on the plain string constants
        ``REPEAT_MODE_OFF/ONE/ALL``.  Import *RepeatMode* optimistically and
        fall back to raw strings when unavailable so the integration remains
        compatible with both release lines.
        """

        try:
            from homeassistant.components.media_player.const import RepeatMode  # type: ignore

            has_repeat_enum = True
        except ImportError:  # pragma: no cover – fallback for older HA
            has_repeat_enum = False

        try:
            play_state = self.device.session_raw.get("PlayState", {})  # type: ignore[dict-item]
            repeat_raw: str | None = play_state.get("RepeatMode")
            if repeat_raw is None:
                return None

            # Map Emby → HA identifiers
            mapping = {
                "RepeatNone": "off",
                "RepeatAll": "all",
                "RepeatOne": "one",
            }
            ha_mode = mapping.get(repeat_raw, None)
            if ha_mode is None:
                return None  # unexpected value – expose as unknown

            if has_repeat_enum:
                return RepeatMode(ha_mode)  # type: ignore[call-arg]
            return ha_mode  # str for legacy cores
        except Exception:  # pragma: no cover – malformed payload / guard
            return None

    # ----------------------
    # Service handlers
    # ----------------------

    async def async_set_shuffle(self, shuffle: bool) -> None:  # noqa: D401 – HA naming
        """Enable or disable *shuffle* mode on the client."""

        api = self._get_emby_api()
        session_id = await self._resolve_session_id(api)
        if not session_id:
            from homeassistant.exceptions import HomeAssistantError

            raise HomeAssistantError("Unable to determine active Emby session for shuffle control")

        try:
            await api.shuffle(session_id, shuffle)
        except Exception as exc:  # noqa: BLE001 – any network / HTTP failure
            from homeassistant.exceptions import HomeAssistantError

            raise HomeAssistantError(f"Emby shuffle failed: {exc}") from exc

        # Optimistic local update – websocket will confirm quickly.
        self.async_write_ha_state()

    async def async_set_repeat(self, repeat):  # type: ignore[override] – dynamic typing
        """Set *repeat* mode on the client.

        The *repeat* parameter can be either a :class:`RepeatMode` enum or the
        corresponding string identifier ("off" / "one" / "all").  The helper
        translates the value to Emby's expected *Repeat<Mode>* form.
        """

        try:
            from homeassistant.components.media_player.const import RepeatMode  # type: ignore

            if isinstance(repeat, RepeatMode):  # newer HA – enum instance
                repeat_val: str = repeat.value  # type: ignore[assignment]
            else:  # Accept plain strings for older cores / service data
                repeat_val = str(repeat)
        except ImportError:  # pragma: no cover – legacy HA path
            repeat_val = str(repeat)

        mapping = {
            "off": "RepeatNone",
            "all": "RepeatAll",
            "one": "RepeatOne",
        }
        emby_mode = mapping.get(repeat_val.lower())
        if emby_mode is None:
            from homeassistant.exceptions import HomeAssistantError

            raise HomeAssistantError(f"Invalid repeat mode: {repeat}")

        api = self._get_emby_api()
        session_id = await self._resolve_session_id(api)
        if not session_id:
            from homeassistant.exceptions import HomeAssistantError

            raise HomeAssistantError("Unable to determine active Emby session for repeat control")

        try:
            await api.repeat(session_id, emby_mode)
        except Exception as exc:  # noqa: BLE001
            from homeassistant.exceptions import HomeAssistantError

            raise HomeAssistantError(f"Emby repeat failed: {exc}") from exc

        # Optimistic state update – websocket will update soon
        self.async_write_ha_state()

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
    # Power management – turn_on / turn_off (GitHub issue #77)
    # ------------------------------------------------------------------

    async def async_turn_on(self) -> None:  # noqa: D401 – HA naming
        """Wake the target Emby client from standby when supported."""

        api = self._get_emby_api()
        session_id = await self._resolve_session_id(api)

        if not session_id:
            # Without a valid session id the remote command cannot be
            # delivered.  Raise a standard HA error so callers receive a
            # consistent failure signal (Assist / UI toast etc.).  The helper
            # purposefully *does not* attempt any discovery fallback because
            # the Sessions endpoint already provides our best chance at
            # mapping device ↔ session when idle.
            from homeassistant.exceptions import HomeAssistantError

            raise HomeAssistantError("Unable to determine active Emby session for turn_on command")

        try:
            await api.power_state(session_id, True)
        except Exception as exc:  # noqa: BLE001 – network / HTTP level
            from homeassistant.exceptions import HomeAssistantError

            raise HomeAssistantError(f"Emby turn_on failed: {exc}") from exc

        # Optimistic local update – websocket event will follow shortly and
        # update the *state* property but updating immediately results in a
        # snappier UI response.
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:  # noqa: D401 – HA naming
        """Put the target Emby client into standby when supported."""

        api = self._get_emby_api()
        session_id = await self._resolve_session_id(api)

        if not session_id:
            from homeassistant.exceptions import HomeAssistantError

            raise HomeAssistantError("Unable to determine active Emby session for turn_off command")

        try:
            await api.power_state(session_id, False)
        except Exception as exc:  # noqa: BLE001 – network / HTTP level
            from homeassistant.exceptions import HomeAssistantError

            raise HomeAssistantError(f"Emby turn_off failed: {exc}") from exc

        self.async_write_ha_state()

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
        user_id: str | None = None,
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

        # Use *Any* for values so we can assign strings, bools and enums
        payload: dict[str, Any] = {
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

        # New parameter – user_id
        if user_id is not None:
            payload["user_id"] = user_id
        elif "user_id" in kwargs:
            payload["user_id"] = kwargs["user_id"]

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
        resolved_user_id: str | None = validated.get("user_id")

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
                user_id=resolved_user_id,
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
            await api.play(
                session_id,
                [item_id],
                play_command=play_command,
                start_position_ticks=start_ticks,
                controlling_user_id=resolved_user_id,
            )
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

    # ------------------------------------------------------------------
    # Home Assistant – media search implementation (issue #74)
    # ------------------------------------------------------------------

    async def async_search_media(self, query):  # type: ignore[override]
        """Handle the global media search request.

        The Home Assistant UI and voice assistants forward a
        :class:`homeassistant.components.media_player.SearchMediaQuery`
        instance containing the raw *search text* and optional content
        filters.  The integration must respond with a
        :class:`homeassistant.components.media_player.SearchMedia` data
        structure wrapping one or more :class:`BrowseMedia` entries that the
        caller can subsequently *play* or *expand*.

        The implementation purposefully re-uses the existing lightweight
        lookup helpers to stay consistent with ``async_play_media``:

        1. Convert the Home Assistant *media_type* filter (when supplied) to
           the corresponding Emby *ItemType* list using the mapping from
           ``components.emby.search_resolver``.
        2. Execute a single ``/Items`` query via :class:`components.emby.api.EmbyAPI`.
        3. Wrap the resulting list (may be empty) into ``BrowseMedia`` nodes
           using the same private helpers employed by the browsing feature so
           UI presentation stays uniform.
        """

        # Lazy imports for optional HA stubs ------------------------------
        from homeassistant.exceptions import HomeAssistantError
        from homeassistant.components.media_player.browse_media import (
            SearchMedia,
            SearchMediaQuery,
        )  # noqa: WPS433 – runtime import is acceptable

        if not isinstance(query, SearchMediaQuery):  # defensive guard – keeps mypy & tests happy
            raise HomeAssistantError("Invalid query object passed to async_search_media")

        search_term: str = query.search_query.strip()
        if not search_term:
            raise HomeAssistantError("Empty search query")

        # ------------------------------------------------------------------
        # Determine Emby *IncludeItemTypes* filter from HA *media_type*.
        # ------------------------------------------------------------------

        from .search_resolver import _MEDIA_TYPE_MAP  # re-use the proven map

        # ------------------------------------------------------------------
        # Derive an *IncludeItemTypes* filter for the Emby search.
        # ------------------------------------------------------------------

        include_types: list[str] | None = None

        # 1. Honour explicit media_type hints provided by the caller (voice
        #    assistant, UI etc.) when present.
        if query.media_content_type and query.media_content_type in _MEDIA_TYPE_MAP:
            include_types = list(_MEDIA_TYPE_MAP[query.media_content_type])

        # 2. Home Assistant may omit the *media_content_type* field entirely –
        #    this happens for example when the user invokes a global search
        #    via the WebSocket API.  The official docs (and the core
        #    `plex` integration used as reference) default to a **movie**
        #    search in that case to reduce the result set to something
        #    sensible while still matching the majority of free-form queries.
        if include_types is None:
            include_types = ["Movie"]

        # ------------------------------------------------------------------
        # Execute the search via the shared EmbyAPI instance.
        # ------------------------------------------------------------------

        api = self._get_emby_api()

        # Attempt to respect parental control by forwarding the active Emby
        # *UserId* whenever we can derive it from the current session.
        user_id: str | None = None
        session_raw = getattr(self.device, "session_raw", None)
        if isinstance(session_raw, dict):
            user_id = session_raw.get("UserId")

        # Fallback – refresh sessions list when we have no user attached yet.
        if not user_id:
            try:
                sessions = await api.get_sessions(force_refresh=True)
            except Exception:  # noqa: BLE001 – surfaced later
                sessions = []

            for sess in sessions:
                if sess.get("DeviceId") in (self.device_id, getattr(self.device, "unique_id", None)):
                    user_id = sess.get("UserId")
                    break

        try:
            results = await api.search(
                search_term=search_term,
                item_types=include_types,
                user_id=user_id,
                limit=5,
            )
        except Exception as exc:  # noqa: BLE001 – wrap generically
            raise HomeAssistantError(f"Error during Emby search: {exc}") from exc

        if not results:
            raise HomeAssistantError("No matching items found")

        # Convert JSON payloads -> BrowseMedia nodes -----------------------
        browse_nodes = [self._emby_item_to_browse(item) for item in results]

        # ------------------------------------------------------------------
        # Build *SearchMedia* response.  Home Assistant 2025-04 spec adds the
        # optional *result_media_class* attribute that should be populated
        # when the top-level search results are homogeneous.  Earlier Core
        # versions – including the ones used by our CI matrix – do **not**
        # expose the new attribute yet.  Runtime inspection is therefore
        # required to keep backwards-compatibility.

        # Determine a common media_class for all returned items (if any).
        result_media_class = None
        if browse_nodes:
            first_class = browse_nodes[0].media_class
            if all(node.media_class == first_class for node in browse_nodes):
                result_media_class = first_class

        # Construct the dataclass using the attribute only when supported by
        # the running Home Assistant version.
        # Pyright running against older Core stubs does not know the new
        # *result_media_class* parameter.  The conditional check above ensures
        # we only reference it when present at *runtime*; nevertheless the
        # static analyzer flags this as an invalid argument.  Silence the
        # false-positive via an explicit *type: ignore*.

        if "result_media_class" in SearchMedia.__dataclass_fields__:  # type: ignore[attr-defined]
            from typing import cast, Any  # Any required for cast target – used below

            SearchMediaDynamic = cast(Any, SearchMedia)
            _ = Any  # prevent pyright unused-import false positive
            return SearchMediaDynamic(
                result=browse_nodes,
                result_media_class=result_media_class,
            )

        # Fallback – Core version prior to 2025-04.
        return SearchMedia(result=browse_nodes)