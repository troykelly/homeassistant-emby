"""Support to interface with the Emby API."""

from __future__ import annotations

import logging

from pyemby import EmbyServer
import voluptuous as vol

from homeassistant.helpers import config_validation as cv

from homeassistant.components.media_player import (
    PLATFORM_SCHEMA as MEDIA_PLAYER_PLATFORM_SCHEMA,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
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
# Service data validation – ``media_player.play_media``
# -----------------------------------------------------------------------------

# Home Assistant passes the *media_type* and *media_id* parameters explicitly
# to :py:meth:`async_play_media`, while any additional fields are forwarded via
# **kwargs.  We build a small voluptuous schema so the integration fails fast
# and with useful error messages when mis-used.

PLAY_MEDIA_SCHEMA = vol.Schema(
    {
        vol.Required("media_type"): cv.string,
        vol.Required("media_id"): cv.string,
        # When *enqueue* is true the item will be queued *after* the current
        # one rather than interrupting playback immediately.
        vol.Optional("enqueue", default=False): cv.boolean,
        # Optional start position in **seconds** – will be converted to Emby
        # ticks (100 ns units) internally.
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
    # Public helper – session id mapping (used by play_media helper)
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

    @property
    def name(self):
        """Return the name of the device."""
        return f"Emby {self.device.name}" or DEVICE_DEFAULT_NAME

    @property
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

    @property
    def app_name(self):
        """Return current user as app_name."""
        # Ideally the media_player object would have a user property.
        return self.device.username

    @property
    def media_content_id(self):
        """Content ID of current playing media."""
        return self.device.media_id

    @property
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

    @property
    def media_duration(self):
        """Return the duration of current playing media in seconds."""
        return self.device.media_runtime

    @property
    def media_position(self):
        """Return the position of current playing media in seconds."""
        return self.media_status_last_position

    @property
    def media_position_updated_at(self):
        """When was the position of the current playing media valid.

        Returns value from homeassistant.util.dt.utcnow().
        """
        return self.media_status_received

    @property
    def media_image_url(self):
        """Return the image URL of current playing media."""
        return self.device.media_image_url

    @property
    def media_title(self):
        """Return the title of current playing media."""
        return self.device.media_title

    @property
    def media_season(self):
        """Season of current playing media (TV Show only)."""
        return self.device.media_season

    @property
    def media_series_title(self):
        """Return the title of the series of current playing media (TV)."""
        return self.device.media_series_title

    @property
    def media_episode(self):
        """Return the episode of current playing media (TV only)."""
        return self.device.media_episode

    @property
    def media_album_name(self):
        """Return the album name of current playing media (Music only)."""
        return self.device.media_album_name

    @property
    def media_artist(self):
        """Return the artist of current playing media (Music track only)."""
        return self.device.media_artist

    @property
    def media_album_artist(self):
        """Return the album artist of current playing media (Music only)."""
        return self.device.media_album_artist

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Flag media player features that are supported."""
        if self.supports_remote_control:
            return SUPPORT_EMBY
        return MediaPlayerEntityFeature(0)

    @property
    def extra_state_attributes(self):
        """Expose additional attributes – mainly the live Emby session id."""
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
    # Home Assistant service handler – play_media
    # ------------------------------------------------------------------

    async def async_play_media(
        self,
        media_type: str | None,
        media_id: str,
        **kwargs,
    ) -> None:  # noqa: D401 – verbatim HA signature
        """Handle the *play_media* service call for this entity.

        The implementation follows these steps:

        1. Validate + normalise arguments via ``PLAY_MEDIA_SCHEMA``.
        2. Resolve the payload to a concrete Emby ``ItemId`` using
           :pyfunc:`components.emby.search_resolver.resolve_media_item`.
        3. Determine the current Emby ``SessionId`` for the target device –
           refreshes the sessions list when necessary.
        4. Trigger remote playback through :class:`components.emby.api.EmbyAPI`.
        """

        from homeassistant.exceptions import HomeAssistantError

        # ------------------------------------------------------------------
        # 1. Merge fixed params with **kwargs and validate.
        # ------------------------------------------------------------------

        payload = {"media_type": media_type, "media_id": media_id}
        payload.update(kwargs or {})

        try:
            validated = PLAY_MEDIA_SCHEMA(payload)
        except vol.Invalid as exc:
            raise HomeAssistantError(f"Invalid play_media payload: {exc}") from exc

        enqueue: bool = validated["enqueue"]
        position: int | None = validated.get("position")

        # ------------------------------------------------------------------
        # 2. Resolve to a concrete Emby item.
        # ------------------------------------------------------------------

        # Lazily instantiate the minimal API helper – we reuse it across calls
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

        play_command = "PlayNext" if enqueue else "PlayNow"
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

        # Fast-path – existing mapping.
        if self._current_session_id:
            return self._current_session_id

        # Poll the Sessions endpoint to find a matching device when idle / new.
        try:
            sessions = await api.get_sessions(force_refresh=True)
        except Exception as exc:  # noqa: BLE001 – wrap as generic
            _LOGGER.warning("Could not refresh Emby sessions: %s", exc)
            return None

        # Each session payload includes a DeviceId we can correlate with the
        # stable id used by pyemby (self.device.id / self.device.unique_id).
        for sess in sessions:
            if sess.get("DeviceId") in (self.device_id, getattr(self.device, "unique_id", None)):
                self._current_session_id = sess.get("Id")
                return self._current_session_id

        return None