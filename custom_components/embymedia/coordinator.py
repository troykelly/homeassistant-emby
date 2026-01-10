"""Data update coordinator for Emby integration."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any

import aiohttp
from homeassistant.const import CONF_ENTITY_ID, CONF_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import EmbyClient
from .const import (
    CONF_IGNORE_WEB_PLAYERS,
    CONF_WEBSOCKET_INTERVAL,
    DEFAULT_IGNORE_WEB_PLAYERS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_WEBSOCKET_INTERVAL,
    DOMAIN,
    WEB_PLAYER_CLIENTS_LOWER,
    WEBSOCKET_POLL_INTERVAL,
    EmbyConfigEntry,
    EmbyLibraryChangedData,
    EmbyNotificationData,
    EmbyUserChangedData,
    EmbyUserDataChangedData,
)
from .exceptions import EmbyConnectionError, EmbyError
from .models import EmbySession, parse_session
from .websocket import EmbyWebSocket

if TYPE_CHECKING:
    from .const import EmbySessionResponse

# Minimum time between WebSocket-triggered refreshes (debouncing)
WEBSOCKET_REFRESH_DEBOUNCE = timedelta(seconds=2)

# Emby uses ticks (100 nanoseconds) for time tracking
EMBY_TICKS_PER_SECOND = 10_000_000

# Maximum seconds between playback progress updates to count as real playback
# Larger gaps indicate seeks rather than actual watch time
MAX_PLAYBACK_DELTA_SECONDS = 60

# Default maximum age in seconds for stale playback session cleanup (1 hour)
DEFAULT_STALE_SESSION_MAX_AGE = 3600

# WebSocket stability tracking - disable polling after N consecutive successful messages
WEBSOCKET_STABLE_THRESHOLD = 5

# Health check interval when polling is disabled (5 minutes)
HEALTH_CHECK_INTERVAL = 300

_LOGGER = logging.getLogger(__name__)


class EmbyDataUpdateCoordinator(DataUpdateCoordinator[dict[str, EmbySession]]):
    """Coordinator for fetching Emby session data.

    This coordinator polls the Emby server for active sessions and
    maintains a dictionary mapping device_id to EmbySession.

    Using device_id (not session_id) as the key ensures entities
    persist across client reconnections.

    Attributes:
        client: The Emby API client instance.
        server_id: The Emby server ID.
        server_name: The Emby server name.
    """

    client: EmbyClient
    server_id: str
    server_name: str
    config_entry: EmbyConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: EmbyClient,
        server_id: str,
        server_name: str,
        config_entry: EmbyConfigEntry,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
        user_id: str | None = None,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance.
            client: Emby API client.
            server_id: Unique server identifier.
            server_name: Human-readable server name.
            config_entry: Config entry for reading options.
            scan_interval: Polling interval in seconds.
            user_id: Optional user ID for user-specific context.
        """
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{server_id}",
            update_interval=timedelta(seconds=scan_interval),
            always_update=False,
        )
        self.client = client
        self.server_id = server_id
        self.server_name = server_name
        self.config_entry = config_entry
        self._user_id = user_id
        self._previous_sessions: set[str] = set()
        self._websocket: EmbyWebSocket | None = None
        self._websocket_enabled: bool = False
        self._websocket_receive_task: asyncio.Task[None] | None = None
        self._configured_scan_interval = scan_interval
        # Resilience tracking
        self._consecutive_failures: int = 0
        self._max_consecutive_failures: int = 5
        # Debouncing for WebSocket-triggered refreshes
        self._last_websocket_refresh: datetime | None = None
        # Playback tracking (Phase 18) - per user
        # Key is "{user_id}:{session_id}" to track per-user sessions
        self._playback_sessions: dict[str, dict[str, int | str]] = {}
        # Per-user watch time: user_id -> seconds watched today
        self._user_watch_times: dict[str, int] = {}
        self._last_reset_date: date = date.today()
        # WebSocket stability tracking (Issue #287)
        self._ws_consecutive_success: int = 0
        self._polling_disabled: bool = False
        self._health_check_task: asyncio.Task[None] | None = None

    @property
    def user_id(self) -> str | None:
        """Return the configured user ID.

        Returns:
            User ID if configured, None otherwise.
        """
        return self._user_id

    @property
    def websocket(self) -> EmbyWebSocket | None:
        """Return the WebSocket client instance."""
        return self._websocket

    @property
    def websocket_enabled(self) -> bool:
        """Return True if WebSocket is enabled."""
        return self._websocket_enabled

    @property
    def ignore_web_players(self) -> bool:
        """Return True if web browser players should be ignored."""
        return bool(
            self.config_entry.options.get(CONF_IGNORE_WEB_PLAYERS, DEFAULT_IGNORE_WEB_PLAYERS)
        )

    @property
    def daily_watch_time(self) -> int:
        """Return total watch time today in seconds (all users combined).

        Returns:
            Total seconds of video watched today.
        """
        return sum(self._user_watch_times.values())

    @property
    def user_watch_times(self) -> dict[str, int]:
        """Return per-user watch times.

        Returns:
            Dictionary mapping user_id to seconds watched today.
        """
        return self._user_watch_times

    def get_user_watch_time(self, user_id: str) -> int:
        """Return watch time for a specific user.

        Args:
            user_id: The Emby user ID.

        Returns:
            Seconds watched today by the specified user.
        """
        return self._user_watch_times.get(user_id, 0)

    @property
    def playback_sessions(self) -> dict[str, dict[str, int | str]]:
        """Return currently tracked playback sessions.

        Returns:
            Dictionary mapping session IDs to session tracking data.
        """
        return self._playback_sessions

    # Class constant for WebSocket stability threshold
    WEBSOCKET_STABLE_THRESHOLD: int = WEBSOCKET_STABLE_THRESHOLD

    @property
    def polling_disabled(self) -> bool:
        """Return True if polling is disabled (WebSocket stable).

        Returns:
            True if WebSocket is stable and polling is disabled.
        """
        return self._polling_disabled

    def _on_websocket_message_success(self) -> None:
        """Handle successful WebSocket message receipt.

        Increments the consecutive success counter and disables
        polling if the stability threshold is reached.
        """
        self._ws_consecutive_success += 1
        if (
            self._ws_consecutive_success >= WEBSOCKET_STABLE_THRESHOLD
            and not self._polling_disabled
        ):
            self._disable_polling()

    def _on_websocket_error(self) -> None:
        """Handle WebSocket error.

        Resets the consecutive success counter and re-enables polling.
        """
        self._ws_consecutive_success = 0
        if self._polling_disabled:
            self._enable_polling()

    def _disable_polling(self) -> None:
        """Disable polling when WebSocket is stable.

        Sets update_interval to None to stop polling and schedules
        periodic health checks instead.
        """
        self._polling_disabled = True
        self.update_interval = None  # type: ignore[misc]
        _LOGGER.info(
            "WebSocket stable after %d messages, disabling polling for %s",
            self._ws_consecutive_success,
            self.server_name,
        )
        # Schedule health checks
        self._schedule_health_check()

    def _enable_polling(self, use_websocket_interval: bool = False) -> None:
        """Re-enable polling when WebSocket becomes unstable.

        Restores the update_interval and cancels health check task.

        Args:
            use_websocket_interval: If True, use the WebSocket poll interval.
                If False (default), use the configured scan interval.
        """
        self._polling_disabled = False
        if use_websocket_interval:
            self.update_interval = timedelta(seconds=WEBSOCKET_POLL_INTERVAL)  # type: ignore[misc]
        else:
            self.update_interval = timedelta(seconds=self._configured_scan_interval)  # type: ignore[misc]
        _LOGGER.info(
            "Re-enabling polling for %s (interval: %s)",
            self.server_name,
            self.update_interval,
        )
        # Cancel health check task
        if self._health_check_task is not None:
            self._health_check_task.cancel()
            self._health_check_task = None

    def _schedule_health_check(self) -> None:
        """Schedule periodic health checks while polling is disabled."""
        if self._health_check_task is not None:
            self._health_check_task.cancel()

        async def _health_check_loop() -> None:
            """Run health checks periodically."""
            while self._polling_disabled:
                await asyncio.sleep(HEALTH_CHECK_INTERVAL)
                if self._polling_disabled:
                    await self.async_health_check()

        self._health_check_task = self.hass.async_create_task(_health_check_loop())

    async def async_health_check(self) -> None:
        """Perform a lightweight health check.

        Uses ping to verify server connectivity without fetching full session data.
        If the health check fails, polling is re-enabled.
        """
        try:
            await self.client.async_ping()
            _LOGGER.debug("Health check passed for %s", self.server_name)
        except EmbyConnectionError as err:
            _LOGGER.warning(
                "Health check failed for %s: %s - re-enabling polling",
                self.server_name,
                err,
            )
            self._on_websocket_error()
        except EmbyError as err:
            _LOGGER.warning(
                "Health check error for %s: %s",
                self.server_name,
                err,
            )

    def _is_web_player(self, session: EmbySession) -> bool:
        """Check if a session is from a web browser.

        Uses O(1) lookup with pre-computed lowercase set for efficiency.

        Args:
            session: The session to check.

        Returns:
            True if the session is from a web browser client.
        """
        client_name = session.client_name.lower()
        return client_name in WEB_PLAYER_CLIENTS_LOWER

    def _track_playback_progress(self, data: Mapping[str, Any]) -> None:
        """Track playback progress for watch time statistics (per user).

        Calculates watch time from position deltas, ignoring backward seeks
        and large forward jumps (which indicate seeks rather than actual playback).

        Args:
            data: PlaybackProgress WebSocket event data or session data with PlayState.
        """
        # Reset daily counters if it's a new day
        today = date.today()
        if today != self._last_reset_date:
            self._user_watch_times.clear()
            self._last_reset_date = today

        # Extract user ID - required for per-user tracking
        user_id = str(data.get("UserId") or "")
        if not user_id:
            return

        # Extract session ID - use PlaySessionId, DeviceId, or Id as fallback
        session_id = str(data.get("PlaySessionId") or data.get("DeviceId") or data.get("Id") or "")
        if not session_id:
            return

        # Create a unique key combining user and session
        tracking_key = f"{user_id}:{session_id}"

        # Handle both direct PositionTicks and nested PlayState.PositionTicks
        position_ticks = data.get("PositionTicks")
        if position_ticks is None:
            play_state = data.get("PlayState", {})
            if isinstance(play_state, dict):
                position_ticks = play_state.get("PositionTicks")

        if not isinstance(position_ticks, int) or position_ticks is None:
            position_ticks = 0

        # Get item info from either direct fields or nested NowPlayingItem
        now_playing = data.get("NowPlayingItem", {})
        if not isinstance(now_playing, dict):
            now_playing = {}
        item_id = str(data.get("ItemId") or now_playing.get("Id", ""))
        item_name = str(data.get("ItemName") or now_playing.get("Name", ""))
        user_name = str(data.get("UserName") or "")

        # Skip if paused (from PlayState)
        play_state = data.get("PlayState", {})
        if isinstance(play_state, dict) and play_state.get("IsPaused"):
            # Update position but don't count paused time
            self._playback_sessions[tracking_key] = {
                "position_ticks": position_ticks,
                "last_update": datetime.now().isoformat(),
                "item_id": item_id,
                "item_name": item_name,
                "user_id": user_id,
                "user_name": user_name,
            }
            return

        # Calculate watch time since last update (only for existing sessions)
        if tracking_key in self._playback_sessions:
            last_position = self._playback_sessions[tracking_key].get("position_ticks", 0)
            if isinstance(last_position, int) and position_ticks > last_position:
                # Only count forward progress
                ticks_delta = position_ticks - last_position
                seconds_delta = ticks_delta // EMBY_TICKS_PER_SECOND
                # Sanity check: don't count huge jumps (likely seeks)
                if seconds_delta <= MAX_PLAYBACK_DELTA_SECONDS:
                    # Add to user's watch time
                    current_user_time = self._user_watch_times.get(user_id, 0)
                    self._user_watch_times[user_id] = current_user_time + seconds_delta
                    _LOGGER.debug(
                        "Watch time added for user %s: %d seconds (user total: %d)",
                        user_name or user_id,
                        seconds_delta,
                        self._user_watch_times[user_id],
                    )

        # Update session tracking
        self._playback_sessions[tracking_key] = {
            "position_ticks": position_ticks,
            "last_update": datetime.now().isoformat(),
            "item_id": item_id,
            "item_name": item_name,
            "user_id": user_id,
            "user_name": user_name,
        }

    def _cleanup_playback_session(self, data: Mapping[str, Any]) -> None:
        """Remove playback session tracking when playback stops.

        Args:
            data: PlaybackStopped WebSocket event data.
        """
        user_id = str(data.get("UserId", ""))
        device_id = str(data.get("DeviceId", ""))
        play_session_id = str(data.get("PlaySessionId", "")) or device_id
        tracking_key = f"{user_id}:{play_session_id}"
        removed = self._playback_sessions.pop(tracking_key, None)
        if removed:
            _LOGGER.debug("Cleaned up playback session: %s", tracking_key)

        # Invalidate discovery cache for this user (playback affected their discovery data)
        if user_id:
            self._invalidate_discovery_cache_for_user(user_id)

    def _cleanup_session_tracking(self, data: Mapping[str, Any]) -> None:
        """Remove all tracking for a session that ended.

        Args:
            data: SessionEnded WebSocket event data.
        """
        device_id = str(data.get("DeviceId", ""))
        if not device_id:
            return

        # Remove any entries containing this device_id
        keys_to_remove = [k for k in self._playback_sessions if device_id in k]
        for key in keys_to_remove:
            self._playback_sessions.pop(key, None)
            _LOGGER.debug("Cleaned up session tracking for device: %s", key)

    def _cleanup_stale_sessions(self, max_age_seconds: int = DEFAULT_STALE_SESSION_MAX_AGE) -> None:
        """Remove playback sessions older than max_age_seconds.

        This prevents memory leaks from sessions that ended without proper cleanup
        (e.g., client disconnected without sending PlaybackStopped).

        Args:
            max_age_seconds: Maximum age in seconds before a session is considered stale.
        """
        now = datetime.now()
        keys_to_remove: list[str] = []

        for key, session_data in self._playback_sessions.items():
            last_update_str = session_data.get("last_update")
            if not last_update_str:
                # No timestamp - treat as stale
                keys_to_remove.append(key)
                continue

            try:
                last_update = datetime.fromisoformat(str(last_update_str))
                age = (now - last_update).total_seconds()
                if age > max_age_seconds:
                    keys_to_remove.append(key)
            except (ValueError, TypeError):
                # Invalid timestamp - treat as stale
                keys_to_remove.append(key)

        for key in keys_to_remove:
            self._playback_sessions.pop(key, None)
            _LOGGER.debug("Cleaned up stale playback session: %s", key)

    def _invalidate_discovery_cache_for_user(self, user_id: str) -> None:
        """Invalidate discovery cache for a specific user.

        Called when user-specific events occur (PlaybackStopped, UserDataChanged).

        Args:
            user_id: The user ID whose cache should be invalidated.
        """
        runtime_data = getattr(self.config_entry, "runtime_data", None)
        if runtime_data is None:
            return

        discovery_coordinators = getattr(runtime_data, "discovery_coordinators", None)
        if not discovery_coordinators:
            return

        coordinator = discovery_coordinators.get(user_id)
        if coordinator is not None:
            coordinator.invalidate_cache_for_user(user_id)
            _LOGGER.debug(
                "Invalidated discovery cache for user %s on %s",
                user_id,
                self.server_name,
            )

    def _invalidate_all_discovery_caches(self) -> None:
        """Invalidate discovery cache for all users.

        Called when global events occur (LibraryChanged) that affect all users.
        """
        runtime_data = getattr(self.config_entry, "runtime_data", None)
        if runtime_data is None:
            return

        discovery_coordinators = getattr(runtime_data, "discovery_coordinators", None)
        if not discovery_coordinators:
            return

        for coordinator in discovery_coordinators.values():
            coordinator.on_library_changed()

        _LOGGER.debug(
            "Invalidated discovery cache for all users (%d) on %s",
            len(discovery_coordinators),
            self.server_name,
        )

    async def _async_update_data(self) -> dict[str, EmbySession]:
        """Fetch session data from Emby server with graceful degradation.

        Returns:
            Dictionary mapping device_id to EmbySession.

        Raises:
            UpdateFailed: If fetching data fails and no cached data available.
        """
        try:
            sessions_data: list[EmbySessionResponse] = await self.client.async_get_sessions()
            # Success - reset failure counter
            self._consecutive_failures = 0
        except EmbyConnectionError as err:
            self._consecutive_failures += 1
            # Check if recovery is needed
            if self._consecutive_failures >= self._max_consecutive_failures:
                await self._attempt_recovery()
            # Return cached data if available
            if self.data is not None:
                _LOGGER.warning(
                    "Failed to fetch sessions, using cached data: %s",
                    err,
                )
                cached: dict[str, EmbySession] = self.data
                return cached
            raise UpdateFailed(f"Failed to connect to Emby server: {err}") from err
        except EmbyError as err:
            self._consecutive_failures += 1
            raise UpdateFailed(f"Error fetching sessions: {err}") from err

        # Parse sessions and index by device_id
        sessions: dict[str, EmbySession] = {}
        ignore_web = self.ignore_web_players
        for session_data in sessions_data:
            try:
                session = parse_session(session_data)
                # Filter to only sessions that support remote control
                # These are the ones we can create media players for
                if not session.supports_remote_control:
                    continue
                # Filter out web browser players if option is enabled
                if ignore_web and self._is_web_player(session):
                    _LOGGER.debug(
                        "Ignoring web browser session: %s (%s)",
                        session.device_name,
                        session.client_name,
                    )
                    continue
                sessions[session.device_id] = session
            except (KeyError, ValueError) as err:
                _LOGGER.warning(
                    "Failed to parse session data: %s - %s",
                    err,
                    session_data.get("DeviceName", "Unknown"),
                )
                continue

        # Log session changes
        current_devices = set(sessions.keys())
        added = current_devices - self._previous_sessions
        removed = self._previous_sessions - current_devices

        for device_id in added:
            session = sessions[device_id]
            _LOGGER.debug(
                "New session detected: %s (%s)",
                session.device_name,
                session.client_name,
            )

        for device_id in removed:
            _LOGGER.debug("Session removed: %s", device_id)

        self._previous_sessions = current_devices

        return sessions

    async def _attempt_recovery(self) -> None:
        """Attempt to recover from repeated failures.

        Tries to reconnect WebSocket and verify server is responding.
        """
        _LOGGER.info(
            "Attempting automatic recovery after %d failures",
            self._consecutive_failures,
        )

        # Try to reconnect WebSocket by starting reconnect loop
        if self._websocket is not None:
            await self._websocket.async_start_reconnect_loop()

        # Refresh server info to verify connectivity
        try:
            await self.client.async_get_server_info()
            _LOGGER.info("Recovery successful, server is responding")
        except EmbyError:
            _LOGGER.warning("Recovery failed, server still unreachable")

    def get_session(self, device_id: str) -> EmbySession | None:
        """Get a specific session by device ID.

        Args:
            device_id: The device ID to look up.

        Returns:
            The session if found, None otherwise.
        """
        if self.data is None:
            return None
        result: EmbySession | None = self.data.get(device_id)
        return result

    async def async_setup_websocket(
        self,
        session: aiohttp.ClientSession,
    ) -> None:
        """Set up WebSocket connection for real-time updates.

        Args:
            session: aiohttp ClientSession for WebSocket connection.
        """
        self._websocket = EmbyWebSocket(
            host=self.client.host,
            port=self.client.port,
            api_key=self.client.api_key,
            ssl=self.client.ssl,
            device_id=f"ha-emby-{self.server_id}",
            session=session,
        )

        # Set up callbacks
        self._websocket.set_message_callback(self._handle_websocket_message)
        self._websocket.set_connection_callback(self._handle_websocket_connection)

        # Connect to WebSocket
        try:
            await self._websocket.async_connect()
            # Subscribe to session updates (with error handling)
            # Use configured interval or default
            interval_ms = self.config_entry.options.get(
                CONF_WEBSOCKET_INTERVAL, DEFAULT_WEBSOCKET_INTERVAL
            )
            try:
                await self._websocket.async_subscribe_sessions(interval_ms=interval_ms)
            except RuntimeError as err:
                _LOGGER.warning(
                    "Failed to subscribe to WebSocket sessions for %s: %s",
                    self.server_name,
                    err,
                )
                self._websocket_enabled = False
                return
            self._websocket_enabled = True
            # Reduce polling interval since we have real-time updates
            self.update_interval = timedelta(seconds=WEBSOCKET_POLL_INTERVAL)  # type: ignore[misc]
            _LOGGER.info("WebSocket connected to Emby server %s", self.server_name)
            # Start receive loop in background and store task for cleanup
            self._websocket_receive_task = self.hass.async_create_task(
                self._async_websocket_receive_loop()
            )
        except aiohttp.ClientError as err:
            _LOGGER.warning(
                "Failed to connect WebSocket to %s: %s",
                self.server_name,
                err,
            )
            self._websocket_enabled = False

    async def _async_websocket_receive_loop(self) -> None:
        """Run the WebSocket receive loop."""
        if self._websocket is None:
            return
        try:
            await self._websocket.async_run_receive_loop()
        except asyncio.CancelledError:
            _LOGGER.debug("WebSocket receive loop cancelled")
            raise
        except aiohttp.ClientError as err:
            _LOGGER.warning("WebSocket client error: %s", err)
        except OSError as err:
            _LOGGER.warning("WebSocket OS error: %s", err)
        finally:
            # Connection lost, trigger reconnect or fallback
            if self._websocket_enabled:
                self._handle_websocket_connection(False)

    async def async_shutdown_websocket(self) -> None:
        """Shut down WebSocket connection."""
        # Cancel the receive loop task first
        if self._websocket_receive_task is not None:
            self._websocket_receive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._websocket_receive_task
            self._websocket_receive_task = None

        if self._websocket is not None:
            await self._websocket.async_stop_reconnect_loop()
            self._websocket = None
            self._websocket_enabled = False
            _LOGGER.info("WebSocket disconnected from Emby server %s", self.server_name)

    def _handle_websocket_message(
        self,
        message_type: str,
        data: Any,
    ) -> None:
        """Handle incoming WebSocket messages.

        Args:
            message_type: The type of message received.
            data: The message payload.
        """
        # Track WebSocket stability for polling optimization (Issue #287)
        self._on_websocket_message_success()

        if message_type == "Sessions":
            # Direct session update from WebSocket
            self._process_sessions_data(data)
        elif message_type == "PlaybackProgress":
            # Track playback progress for watch time statistics (Phase 18)
            self._track_playback_progress(data)
            # Also trigger a refresh to get latest session state
            self._trigger_debounced_refresh()
        elif message_type == "PlaybackStarted":
            # Trigger a refresh to get latest session state (with debouncing)
            self._trigger_debounced_refresh()
        elif message_type == "PlaybackStopped":
            # Clean up playback session tracking when playback stops
            self._cleanup_playback_session(data)
            self._trigger_debounced_refresh()
        elif message_type == "SessionEnded":
            # Clean up all tracking for a session that ended
            self._cleanup_session_tracking(data)
            self._trigger_debounced_refresh()
        elif message_type == "ServerRestarting":
            _LOGGER.info("Emby server %s is restarting", self.server_name)
        elif message_type == "ServerShuttingDown":
            _LOGGER.warning("Emby server %s is shutting down", self.server_name)
        # Phase 21: Library and user data events
        elif message_type == "LibraryChanged":
            self._handle_library_changed(data)
        elif message_type == "UserDataChanged":
            self._handle_user_data_changed(data)
        elif message_type == "NotificationAdded":
            self._handle_notification_added(data)
        elif message_type in ("UserUpdated", "UserDeleted"):
            self._handle_user_changed(message_type, data)
        else:
            _LOGGER.debug("Unhandled WebSocket message type: %s", message_type)

    def _trigger_debounced_refresh(self) -> None:
        """Trigger a refresh with debouncing to prevent excessive API calls."""
        now = datetime.now()
        if (
            self._last_websocket_refresh is None
            or now - self._last_websocket_refresh > WEBSOCKET_REFRESH_DEBOUNCE
        ):
            self._last_websocket_refresh = now
            self.hass.async_create_task(self.async_refresh())

    def _handle_websocket_connection(self, connected: bool) -> None:
        """Handle WebSocket connection state changes.

        Args:
            connected: True if connected, False if disconnected.
        """
        if connected:
            _LOGGER.info(
                "WebSocket connected, reducing poll interval to %d seconds",
                WEBSOCKET_POLL_INTERVAL,
            )
            self.update_interval = timedelta(seconds=WEBSOCKET_POLL_INTERVAL)  # type: ignore[misc]
        else:
            _LOGGER.warning("WebSocket disconnected from Emby server. Using polling fallback")
            # Reset WebSocket stability tracking (Issue #287)
            self._ws_consecutive_success = 0
            # Always restore configured polling interval on disconnect
            self._polling_disabled = False
            self.update_interval = timedelta(seconds=self._configured_scan_interval)  # type: ignore[misc]
            # Cancel health check task if running
            if self._health_check_task is not None:
                self._health_check_task.cancel()
                self._health_check_task = None

    def _process_sessions_data(
        self,
        sessions_data: list[EmbySessionResponse],
    ) -> None:
        """Process sessions data from WebSocket and update coordinator.

        Args:
            sessions_data: List of session data dictionaries from the API.
        """
        old_sessions = self.data or {}
        sessions: dict[str, EmbySession] = {}

        for session_data in sessions_data:
            try:
                session = parse_session(session_data)
                if session.supports_remote_control:
                    sessions[session.device_id] = session

                # Track playback progress for sessions with active playback (Phase 18)
                if session_data.get("NowPlayingItem"):
                    self._track_playback_progress(session_data)
            except (KeyError, ValueError) as err:
                _LOGGER.warning(
                    "Failed to parse session data from WebSocket: %s - %s",
                    err,
                    session_data.get("DeviceName", "Unknown"),
                )
                continue

        # Detect changes and fire events
        current_devices = set(sessions.keys())
        added = current_devices - self._previous_sessions
        removed = self._previous_sessions - current_devices

        for device_id in added:
            session = sessions[device_id]
            _LOGGER.debug(
                "New session detected: %s (%s)",
                session.device_name,
                session.client_name,
            )
            self._fire_event(device_id, "session_connected")

        for device_id in removed:
            _LOGGER.debug("Session removed: %s", device_id)
            self._fire_event(device_id, "session_disconnected")

        # Check for playback state changes
        for device_id, session in sessions.items():
            old_session = old_sessions.get(device_id)
            if old_session is None:
                # New session, already handled
                continue

            # Check playback started/stopped
            old_playing = old_session.now_playing
            new_playing = session.now_playing

            if old_playing is None and new_playing is not None:
                # Playback started
                self._fire_event(
                    device_id,
                    "playback_started",
                    {
                        "media_content_id": new_playing.item_id,
                        "media_content_type": new_playing.media_type.value
                        if new_playing.media_type
                        else None,
                        "media_title": new_playing.name,
                    },
                )
            elif old_playing is not None and new_playing is None:
                # Playback stopped
                self._fire_event(device_id, "playback_stopped")
            elif old_playing is not None and new_playing is not None:
                # Check for media change
                if old_playing.item_id != new_playing.item_id:
                    self._fire_event(
                        device_id,
                        "media_changed",
                        {
                            "media_content_id": new_playing.item_id,
                            "media_content_type": new_playing.media_type.value
                            if new_playing.media_type
                            else None,
                            "media_title": new_playing.name,
                        },
                    )

                # Check pause state
                old_paused = old_session.play_state.is_paused if old_session.play_state else False
                new_paused = session.play_state.is_paused if session.play_state else False
                if old_paused != new_paused:
                    if new_paused:
                        self._fire_event(device_id, "playback_paused")
                    else:
                        self._fire_event(device_id, "playback_resumed")

        self._previous_sessions = current_devices

        # Update coordinator data and notify listeners
        self.async_set_updated_data(sessions)

    def _fire_event(
        self,
        device_id: str,
        event_type: str,
        extra_data: dict[str, str | None] | None = None,
    ) -> None:
        """Fire an Emby event for automations.

        Args:
            device_id: The device ID the event is for.
            event_type: Type of event (playback_started, etc).
            extra_data: Optional extra data to include in the event.
        """
        entity_id = self._get_entity_id_for_device(device_id)
        if not entity_id:
            _LOGGER.debug(
                "Cannot fire event %s for device %s - no entity found",
                event_type,
                device_id,
            )
            return

        data: dict[str, str | None] = {
            CONF_ENTITY_ID: entity_id,
            CONF_TYPE: event_type,
        }
        if extra_data:
            data.update(extra_data)

        self.hass.bus.async_fire(f"{DOMAIN}_event", data)
        _LOGGER.debug("Fired %s event for %s", event_type, entity_id)

    def _get_entity_id_for_device(self, device_id: str) -> str | None:
        """Get entity ID for a device ID.

        Args:
            device_id: The device ID to look up.

        Returns:
            Entity ID if found, None otherwise.
        """
        entity_registry = er.async_get(self.hass)

        # The unique_id of our media_player entities is {server_id}_{device_id}
        unique_id = f"{self.server_id}_{device_id}"
        entity_id: str | None = entity_registry.async_get_entity_id(
            "media_player", DOMAIN, unique_id
        )
        return entity_id

    # =========================================================================
    # Phase 21: WebSocket Event Handlers
    # =========================================================================

    def _handle_library_changed(self, data: object) -> None:
        """Handle LibraryChanged WebSocket message.

        Fired when items are added, updated, or removed from libraries.
        Clears browse cache and triggers coordinator refresh.

        Args:
            data: Message data from WebSocket.
        """
        if not isinstance(data, dict):
            return

        library_data: EmbyLibraryChangedData = data  # type: ignore[assignment]

        # Clear browse cache since library contents changed
        self.client.clear_browse_cache()

        # Fire Home Assistant event
        self.hass.bus.async_fire(
            "embymedia_library_updated",
            {
                "server_id": self.server_id,
                "server_name": self.server_name,
                "items_added": library_data.get("ItemsAdded", []),
                "items_updated": library_data.get("ItemsUpdated", []),
                "items_removed": library_data.get("ItemsRemoved", []),
                "folders_added_to": library_data.get("FoldersAddedTo", []),
                "folders_removed_from": library_data.get("FoldersRemovedFrom", []),
            },
        )

        _LOGGER.debug(
            "Library changed on %s: %d added, %d updated, %d removed",
            self.server_name,
            len(library_data.get("ItemsAdded", [])),
            len(library_data.get("ItemsUpdated", [])),
            len(library_data.get("ItemsRemoved", [])),
        )

        # Trigger library coordinator refresh (in background, non-blocking)
        # Use debounced delay to prevent excessive refreshes during bulk operations
        runtime_data = getattr(self.config_entry, "runtime_data", None)
        if runtime_data is not None and hasattr(runtime_data, "library_coordinator"):
            library_coordinator = runtime_data.library_coordinator

            async def _delayed_refresh() -> None:
                """Refresh library coordinator after debounce delay."""
                await asyncio.sleep(5)
                await library_coordinator.async_request_refresh()

            self.hass.async_create_task(_delayed_refresh())

        # Invalidate discovery cache for all users (library content affects discovery)
        self._invalidate_all_discovery_caches()

    def _handle_user_data_changed(self, data: object) -> None:
        """Handle UserDataChanged WebSocket message.

        Fired when user-specific item data changes (favorites, played, ratings).

        Args:
            data: Message data from WebSocket.
        """
        if not isinstance(data, dict):
            return

        user_data: EmbyUserDataChangedData = data  # type: ignore[assignment]
        user_data_list = user_data.get("UserDataList", [])

        for item_data in user_data_list:
            item_id = item_data.get("ItemId")
            user_id = item_data.get("UserId")

            if not item_id or not user_id:
                continue

            # Fire Home Assistant event for each changed item
            self.hass.bus.async_fire(
                "embymedia_user_data_changed",
                {
                    "server_id": self.server_id,
                    "server_name": self.server_name,
                    "user_id": user_id,
                    "item_id": item_id,
                    "is_favorite": item_data.get("IsFavorite"),
                    "played": item_data.get("Played"),
                    "playback_position_ticks": item_data.get("PlaybackPositionTicks"),
                    "play_count": item_data.get("PlayCount"),
                    "rating": item_data.get("Rating"),
                    "last_played_date": item_data.get("LastPlayedDate"),
                },
            )

        _LOGGER.debug(
            "User data changed on %s: %d items updated",
            self.server_name,
            len(user_data_list),
        )

        # Invalidate discovery cache for affected users
        affected_users = {item_data.get("UserId") for item_data in user_data_list}
        for user_id in affected_users:
            if user_id:
                self._invalidate_discovery_cache_for_user(str(user_id))

    def _handle_notification_added(self, data: object) -> None:
        """Handle NotificationAdded WebSocket message.

        Fired when a server notification is created.
        Forwards the notification to Home Assistant.

        Args:
            data: Message data from WebSocket.
        """
        if not isinstance(data, dict):
            return

        notification: EmbyNotificationData = data  # type: ignore[assignment]
        name = notification.get("Name", "")
        description = notification.get("Description")
        level = notification.get("Level", "Normal")

        # Fire Home Assistant event
        self.hass.bus.async_fire(
            "embymedia_notification",
            {
                "server_id": self.server_id,
                "server_name": self.server_name,
                "name": name,
                "description": description,
                "level": level,
                "notification_type": notification.get("NotificationType", "Info"),
                "url": notification.get("Url"),
                "date": notification.get("Date"),
            },
        )

        _LOGGER.info(
            "Notification from %s [%s]: %s - %s",
            self.server_name,
            level,
            name,
            description,
        )

    def _handle_user_changed(self, message_type: str, data: object) -> None:
        """Handle UserUpdated/UserDeleted WebSocket message.

        Fired when user accounts are modified or deleted.

        Args:
            message_type: "UserUpdated" or "UserDeleted"
            data: Message data from WebSocket.
        """
        if not isinstance(data, dict):
            return

        user_data: EmbyUserChangedData = data  # type: ignore[assignment]
        user_id = user_data.get("UserId")

        if not user_id:
            return

        # Fire Home Assistant event
        self.hass.bus.async_fire(
            "embymedia_user_changed",
            {
                "server_id": self.server_id,
                "server_name": self.server_name,
                "user_id": user_id,
                "user_name": user_data.get("UserName"),
                "change_type": "deleted" if message_type == "UserDeleted" else "updated",
            },
        )

        _LOGGER.info(
            "User %s on %s: %s",
            user_id,
            self.server_name,
            "deleted" if message_type == "UserDeleted" else "updated",
        )


__all__ = ["EmbyDataUpdateCoordinator"]
