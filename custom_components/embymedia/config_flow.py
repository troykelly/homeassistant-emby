"""Config flow for Emby integration."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.core import callback
from homeassistant.data_entry_flow import AbortFlow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EmbyClient
from .const import (
    CONF_API_KEY,
    CONF_DIRECT_PLAY,
    CONF_ENABLE_DISCOVERY_SENSORS,
    CONF_ENABLE_WEBSOCKET,
    CONF_IGNORE_WEB_PLAYERS,
    CONF_IGNORED_DEVICES,
    CONF_MAX_AUDIO_BITRATE,
    CONF_MAX_VIDEO_BITRATE,
    CONF_PREFIX_BUTTON,
    CONF_PREFIX_MEDIA_PLAYER,
    CONF_PREFIX_NOTIFY,
    CONF_PREFIX_REMOTE,
    CONF_SCAN_INTERVAL,
    CONF_TRANSCODING_PROFILE,
    CONF_USER_ID,
    CONF_VERIFY_SSL,
    CONF_VIDEO_CONTAINER,
    DEFAULT_DIRECT_PLAY,
    DEFAULT_ENABLE_DISCOVERY_SENSORS,
    DEFAULT_ENABLE_WEBSOCKET,
    DEFAULT_IGNORE_WEB_PLAYERS,
    DEFAULT_PORT,
    DEFAULT_PREFIX_BUTTON,
    DEFAULT_PREFIX_MEDIA_PLAYER,
    DEFAULT_PREFIX_NOTIFY,
    DEFAULT_PREFIX_REMOTE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SSL,
    DEFAULT_TRANSCODING_PROFILE,
    DEFAULT_VERIFY_SSL,
    DEFAULT_VIDEO_CONTAINER,
    DOMAIN,
    EMBY_MIN_VERSION,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    TRANSCODING_PROFILES,
    VIDEO_CONTAINERS,
    EmbyConfigFlowUserInput,
    EmbyServerInfo,
    EmbyUser,
    normalize_host,
)
from .exceptions import (
    EmbyAuthenticationError,
    EmbyConnectionError,
    EmbySSLError,
    EmbyTimeoutError,
)

_LOGGER = logging.getLogger(__name__)


def _build_user_schema(
    defaults: EmbyConfigFlowUserInput | None = None,
) -> vol.Schema:
    """Build the user input schema with optional defaults.

    Args:
        defaults: Optional default values from previous input.

    Returns:
        Voluptuous schema for user step.
    """
    return vol.Schema(
        {
            vol.Required(
                CONF_HOST,
                default=defaults.get("host", "") if defaults else "",
            ): str,
            vol.Required(
                CONF_PORT,
                default=defaults.get("port", DEFAULT_PORT) if defaults else DEFAULT_PORT,
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
            vol.Required(
                CONF_SSL,
                default=defaults.get("ssl", DEFAULT_SSL) if defaults else DEFAULT_SSL,
            ): bool,
            vol.Required(CONF_API_KEY): str,
            vol.Required(
                CONF_VERIFY_SSL,
                default=(
                    defaults.get("verify_ssl", DEFAULT_VERIFY_SSL)
                    if defaults
                    else DEFAULT_VERIFY_SSL
                ),
            ): bool,
        }
    )


class EmbyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Emby."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._reauth_entry: ConfigEntry[object] | None = None
        self._server_info: EmbyServerInfo | None = None
        self._user_input: EmbyConfigFlowUserInput | None = None
        self._users: list[EmbyUser] | None = None
        self._client: EmbyClient | None = None
        self._selected_user_id: str = ""

    async def async_step_user(
        self,
        user_input: dict[str, object] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial step.

        Args:
            user_input: User-provided configuration data.

        Returns:
            Config flow result (form or entry creation).
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            # Cast to typed input for validation
            port_val = user_input.get("port", DEFAULT_PORT)
            typed_input: EmbyConfigFlowUserInput = {
                "host": str(user_input.get("host", "")),
                "port": int(port_val) if isinstance(port_val, int | str) else DEFAULT_PORT,
                "ssl": bool(user_input.get("ssl", DEFAULT_SSL)),
                "api_key": str(user_input.get("api_key", "")),
                "verify_ssl": bool(user_input.get("verify_ssl", DEFAULT_VERIFY_SSL)),
            }

            # Validate and normalize input
            errors = self._validate_input(typed_input)

            if not errors:
                # Normalize the host
                typed_input["host"] = normalize_host(typed_input["host"])

                # Attempt connection
                errors = await self._async_validate_connection(typed_input)

            if not errors:
                # Store validated input and proceed to user selection
                self._user_input = typed_input
                return await self.async_step_user_select()

            # Re-show form with errors (preserve input except API key)
            return self.async_show_form(
                step_id="user",
                data_schema=_build_user_schema(typed_input),
                errors=errors,
            )

        # Show initial form
        return self.async_show_form(
            step_id="user",
            data_schema=_build_user_schema(),
            errors=errors,
        )

    async def async_step_import(
        self,
        import_data: dict[str, object],
    ) -> ConfigFlowResult:
        """Handle import from YAML configuration.

        This step is triggered when the integration is configured via YAML.
        It validates the connection and creates a config entry.

        Args:
            import_data: Configuration data from YAML.

        Returns:
            Config flow result (create_entry or abort).
        """
        # Extract and normalize connection data
        host = normalize_host(str(import_data.get(CONF_HOST, "")))
        port_value = import_data.get(CONF_PORT, DEFAULT_PORT)
        port = int(port_value) if isinstance(port_value, int | str) else DEFAULT_PORT
        ssl = bool(import_data.get(CONF_SSL, DEFAULT_SSL))
        api_key = str(import_data.get(CONF_API_KEY, ""))
        verify_ssl = bool(import_data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL))

        # Create client and validate connection
        session = async_get_clientsession(self.hass)
        client = EmbyClient(
            host=host,
            port=port,
            api_key=api_key,
            ssl=ssl,
            verify_ssl=verify_ssl,
            session=session,
        )

        try:
            await client.async_validate_connection()
            server_info = await client.async_get_server_info()

            # Set unique ID and check for duplicates
            server_id = str(server_info["Id"])
            await self.async_set_unique_id(server_id)
            self._abort_if_unique_id_configured()

            server_name = str(server_info.get("ServerName", f"Emby ({host})"))

        except EmbyAuthenticationError:
            _LOGGER.error("Invalid API key for YAML Emby configuration: %s", host)
            return self.async_abort(reason="invalid_auth")
        except EmbyConnectionError:
            _LOGGER.error("Cannot connect to Emby server from YAML configuration: %s", host)
            return self.async_abort(reason="cannot_connect")
        except AbortFlow:
            # Re-raise AbortFlow exceptions (e.g., already_configured)
            raise
        except Exception:
            _LOGGER.exception("Unexpected error during YAML import for Emby")
            return self.async_abort(reason="unknown")

        # Build data dict (connection info)
        data: dict[str, object] = {
            CONF_HOST: host,
            CONF_PORT: port,
            CONF_SSL: ssl,
            CONF_API_KEY: api_key,
            CONF_VERIFY_SSL: verify_ssl,
        }

        # Build options dict (tunable settings from YAML)
        options: dict[str, object] = {}

        # Scan interval
        if CONF_SCAN_INTERVAL in import_data:
            scan_val = import_data[CONF_SCAN_INTERVAL]
            if isinstance(scan_val, int | str):
                options[CONF_SCAN_INTERVAL] = int(scan_val)

        # WebSocket toggle
        if CONF_ENABLE_WEBSOCKET in import_data:
            options[CONF_ENABLE_WEBSOCKET] = bool(import_data[CONF_ENABLE_WEBSOCKET])

        # Ignored devices (comma-separated string)
        if CONF_IGNORED_DEVICES in import_data:
            options[CONF_IGNORED_DEVICES] = str(import_data[CONF_IGNORED_DEVICES])

        # Ignore web players option
        if CONF_IGNORE_WEB_PLAYERS in import_data:
            options[CONF_IGNORE_WEB_PLAYERS] = bool(import_data[CONF_IGNORE_WEB_PLAYERS])

        # Streaming/transcoding options
        if CONF_DIRECT_PLAY in import_data:
            options[CONF_DIRECT_PLAY] = bool(import_data[CONF_DIRECT_PLAY])

        if CONF_VIDEO_CONTAINER in import_data:
            options[CONF_VIDEO_CONTAINER] = str(import_data[CONF_VIDEO_CONTAINER])

        if CONF_MAX_VIDEO_BITRATE in import_data:
            video_bitrate_val = import_data[CONF_MAX_VIDEO_BITRATE]
            if isinstance(video_bitrate_val, int | str):
                options[CONF_MAX_VIDEO_BITRATE] = int(video_bitrate_val)

        if CONF_MAX_AUDIO_BITRATE in import_data:
            audio_bitrate_val = import_data[CONF_MAX_AUDIO_BITRATE]
            if isinstance(audio_bitrate_val, int | str):
                options[CONF_MAX_AUDIO_BITRATE] = int(audio_bitrate_val)

        _LOGGER.info(
            "Imported Emby configuration from YAML for server: %s",
            server_name,
        )

        return self.async_create_entry(
            title=server_name,
            data=data,
            options=options,
        )

    async def async_step_user_select(
        self,
        user_input: dict[str, str] | None = None,
    ) -> ConfigFlowResult:
        """Handle user selection step.

        Args:
            user_input: User selection from form.

        Returns:
            Config flow result (form or entry creation).
        """
        if user_input is not None:
            # Store selected user ID (convert sentinel to empty string for admin context)
            user_id = user_input.get(CONF_USER_ID, "")
            if user_id == "__none__":
                user_id = ""
            self._selected_user_id = user_id
            # Proceed to entity prefix options step
            return await self.async_step_entity_options()

        # Build user selection options
        # Use "__none__" as sentinel for admin context since empty string fails validation
        user_options: dict[str, str] = {"__none__": "Use admin context (no user)"}
        if self._users:
            for user in self._users:
                user_id = str(user.get("Id", ""))
                user_name = str(user.get("Name", "Unknown"))
                if user_id:  # Only add if valid ID
                    user_options[user_id] = user_name

        return self.async_show_form(
            step_id="user_select",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USER_ID, default="__none__"): vol.In(user_options),
                }
            ),
            description_placeholders={
                "server_name": (
                    self._server_info.get("ServerName", "Emby Server")
                    if self._server_info
                    else "Emby Server"
                ),
            },
        )

    async def async_step_entity_options(
        self,
        user_input: dict[str, bool] | None = None,
    ) -> ConfigFlowResult:
        """Handle entity naming options step.

        Allows users to configure entity name prefixes during initial setup.

        Args:
            user_input: User-provided prefix options.

        Returns:
            Config flow result (form or entry creation).
        """
        if user_input is not None:
            # Create entry with prefix options
            options: dict[str, bool] = {
                CONF_PREFIX_MEDIA_PLAYER: user_input.get(
                    CONF_PREFIX_MEDIA_PLAYER, DEFAULT_PREFIX_MEDIA_PLAYER
                ),
                CONF_PREFIX_NOTIFY: user_input.get(CONF_PREFIX_NOTIFY, DEFAULT_PREFIX_NOTIFY),
                CONF_PREFIX_REMOTE: user_input.get(CONF_PREFIX_REMOTE, DEFAULT_PREFIX_REMOTE),
                CONF_PREFIX_BUTTON: user_input.get(CONF_PREFIX_BUTTON, DEFAULT_PREFIX_BUTTON),
            }
            return await self._async_create_entry_with_user(self._selected_user_id, options)

        # Show entity options form with all prefixes enabled by default
        return self.async_show_form(
            step_id="entity_options",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_PREFIX_MEDIA_PLAYER,
                        default=DEFAULT_PREFIX_MEDIA_PLAYER,
                    ): bool,
                    vol.Optional(
                        CONF_PREFIX_NOTIFY,
                        default=DEFAULT_PREFIX_NOTIFY,
                    ): bool,
                    vol.Optional(
                        CONF_PREFIX_REMOTE,
                        default=DEFAULT_PREFIX_REMOTE,
                    ): bool,
                    vol.Optional(
                        CONF_PREFIX_BUTTON,
                        default=DEFAULT_PREFIX_BUTTON,
                    ): bool,
                }
            ),
            description_placeholders={
                "server_name": (
                    self._server_info.get("ServerName", "Emby Server")
                    if self._server_info
                    else "Emby Server"
                ),
            },
        )

    async def _async_create_entry_with_user(
        self,
        user_id: str,
        options: dict[str, bool] | None = None,
    ) -> ConfigFlowResult:
        """Create config entry with user selection and options.

        Args:
            user_id: Selected user ID (empty for admin context).
            options: Optional dict of prefix options from entity_options step.

        Returns:
            Config entry creation result.
        """
        if self._user_input is None:
            return self.async_abort(reason="unknown")

        server_info = self._server_info
        if server_info is not None:
            server_name = server_info.get("ServerName") or f"Emby ({self._user_input['host']})"
        else:
            server_name = f"Emby ({self._user_input['host']})"

        data: dict[str, object] = {
            CONF_HOST: self._user_input["host"],
            CONF_PORT: self._user_input["port"],
            CONF_SSL: self._user_input.get("ssl", DEFAULT_SSL),
            CONF_API_KEY: self._user_input["api_key"],
            CONF_VERIFY_SSL: self._user_input.get("verify_ssl", DEFAULT_VERIFY_SSL),
        }

        # Only store user_id if a user was selected
        if user_id:
            data[CONF_USER_ID] = user_id

        return self.async_create_entry(
            title=server_name,
            data=data,
            options=options or {},
        )

    def _validate_input(
        self,
        user_input: EmbyConfigFlowUserInput,
    ) -> dict[str, str]:
        """Validate user input before attempting connection.

        Args:
            user_input: User-provided configuration data.

        Returns:
            Dictionary of field-specific errors.
        """
        errors: dict[str, str] = {}

        # Validate host
        host = user_input.get("host", "").strip()
        if not host:
            errors[CONF_HOST] = "invalid_host"

        # Validate port (schema handles range, but double-check)
        port = user_input.get("port", 0)
        if not (1 <= port <= 65535):
            errors[CONF_PORT] = "invalid_port"

        # Validate API key is not empty
        api_key = user_input.get("api_key", "").strip()
        if not api_key:
            errors[CONF_API_KEY] = "invalid_auth"

        return errors

    async def _async_validate_connection(
        self,
        user_input: EmbyConfigFlowUserInput,
    ) -> dict[str, str]:
        """Validate the connection to the Emby server.

        Args:
            user_input: User-provided configuration data.

        Returns:
            Dictionary of errors (empty if successful).
        """
        errors: dict[str, str] = {}

        session = async_get_clientsession(self.hass)
        client = EmbyClient(
            host=user_input["host"],
            port=user_input["port"],
            api_key=user_input["api_key"],
            ssl=user_input.get("ssl", DEFAULT_SSL),
            verify_ssl=user_input.get("verify_ssl", DEFAULT_VERIFY_SSL),
            session=session,
        )

        try:
            await client.async_validate_connection()
            server_info = await client.async_get_server_info()

            # Check server version compatibility
            version = str(server_info.get("Version", "0.0.0"))
            if not self._is_version_supported(version):
                _LOGGER.warning(
                    "Emby server version %s is not supported (minimum: %s)",
                    version,
                    EMBY_MIN_VERSION,
                )
                errors["base"] = "unsupported_version"
                return errors

            # Set unique ID and check for duplicates
            server_id = str(server_info["Id"])
            await self.async_set_unique_id(server_id)

            if self._reauth_entry is None:
                self._abort_if_unique_id_configured()

            # Store server info for entry creation
            self._server_info = server_info

            # Fetch users for user selection step
            self._users = await client.async_get_users()
            self._client = client

        except EmbyTimeoutError:
            errors["base"] = "timeout"
        except EmbySSLError:
            errors["base"] = "ssl_error"
        except EmbyConnectionError:
            errors["base"] = "cannot_connect"
        except EmbyAuthenticationError:
            errors["base"] = "invalid_auth"
        except AbortFlow:
            # Re-raise AbortFlow exceptions (e.g., already_configured)
            raise
        except Exception:
            _LOGGER.exception("Unexpected error during Emby config flow")
            errors["base"] = "unknown"

        return errors

    def _is_version_supported(self, version: str) -> bool:
        """Check if the Emby server version is supported.

        Args:
            version: Server version string (e.g., "4.9.1.90").

        Returns:
            True if version is supported.
        """
        try:
            # Parse version (handle formats like "4.9.1.90")
            def parse_version(ver: str) -> tuple[int, int, int, int]:
                parts = ver.split(".")
                return (
                    int(parts[0]) if len(parts) > 0 else 0,
                    int(parts[1]) if len(parts) > 1 else 0,
                    int(parts[2]) if len(parts) > 2 else 0,
                    int(parts[3]) if len(parts) > 3 else 0,
                )

            current = parse_version(version)
            minimum = parse_version(EMBY_MIN_VERSION)

            # Compare version tuples (lexicographic comparison)
            return current >= minimum

        except (ValueError, IndexError):
            _LOGGER.warning("Could not parse Emby version: %s", version)
            return True  # Allow unknown versions

    async def _async_create_entry(
        self,
        user_input: EmbyConfigFlowUserInput,
    ) -> ConfigFlowResult:
        """Create the config entry.

        Args:
            user_input: Validated configuration data.

        Returns:
            Config entry creation result.
        """
        server_info = self._server_info
        if server_info is not None:
            server_name = server_info.get("ServerName") or f"Emby ({user_input['host']})"
        else:
            server_name = f"Emby ({user_input['host']})"

        if self._reauth_entry is not None:
            # Update existing entry for reauth, preserving user_id
            existing_user_id = self._reauth_entry.data.get(CONF_USER_ID)
            data = {
                CONF_HOST: user_input["host"],
                CONF_PORT: user_input["port"],
                CONF_SSL: user_input.get("ssl", DEFAULT_SSL),
                CONF_API_KEY: user_input["api_key"],
                CONF_VERIFY_SSL: user_input.get("verify_ssl", DEFAULT_VERIFY_SSL),
            }
            if existing_user_id:
                data[CONF_USER_ID] = existing_user_id

            self.hass.config_entries.async_update_entry(
                self._reauth_entry,
                data=data,
            )
            await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
            return self.async_abort(reason="reauth_successful")

        return self.async_create_entry(
            title=server_name,
            data={
                CONF_HOST: user_input["host"],
                CONF_PORT: user_input["port"],
                CONF_SSL: user_input.get("ssl", DEFAULT_SSL),
                CONF_API_KEY: user_input["api_key"],
                CONF_VERIFY_SSL: user_input.get("verify_ssl", DEFAULT_VERIFY_SSL),
            },
        )

    async def async_step_reauth(
        self,
        entry_data: dict[str, object],
    ) -> ConfigFlowResult:
        """Handle re-authentication.

        Args:
            entry_data: Existing entry data.

        Returns:
            Config flow result for reauth confirmation.
        """
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, str] | None = None,
    ) -> ConfigFlowResult:
        """Handle re-authentication confirmation.

        Args:
            user_input: New API key from user.

        Returns:
            Config flow result.
        """
        errors: dict[str, str] = {}

        if user_input is not None and self._reauth_entry is not None:
            # Merge with existing entry data
            full_input: EmbyConfigFlowUserInput = {
                "host": str(self._reauth_entry.data[CONF_HOST]),
                "port": int(self._reauth_entry.data[CONF_PORT]),
                "ssl": bool(self._reauth_entry.data.get(CONF_SSL, DEFAULT_SSL)),
                "api_key": user_input[CONF_API_KEY],
                "verify_ssl": bool(
                    self._reauth_entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
                ),
            }

            errors = await self._async_validate_connection(full_input)

            if not errors:
                return await self._async_create_entry(full_input)

        # Show reauth form
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "server_name": (self._reauth_entry.title if self._reauth_entry else "Emby Server"),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry[object],
    ) -> EmbyOptionsFlowHandler:
        """Create the options flow.

        Args:
            config_entry: The config entry to configure.

        Returns:
            Options flow handler instance.
        """
        return EmbyOptionsFlowHandler()


class EmbyOptionsFlowHandler(OptionsFlow):
    """Handle Emby options."""

    async def async_step_init(
        self,
        user_input: dict[str, int | bool | str] | None = None,
    ) -> ConfigFlowResult:
        """Manage the options.

        Args:
            user_input: User-provided options.

        Returns:
            Config flow result.
        """
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "scan_interval",
                        default=self.config_entry.options.get(
                            "scan_interval", DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                    vol.Optional(
                        CONF_ENABLE_WEBSOCKET,
                        default=self.config_entry.options.get(
                            CONF_ENABLE_WEBSOCKET, DEFAULT_ENABLE_WEBSOCKET
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_IGNORED_DEVICES,
                        default=self.config_entry.options.get(CONF_IGNORED_DEVICES, ""),
                    ): str,
                    vol.Optional(
                        CONF_IGNORE_WEB_PLAYERS,
                        default=self.config_entry.options.get(
                            CONF_IGNORE_WEB_PLAYERS, DEFAULT_IGNORE_WEB_PLAYERS
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_DIRECT_PLAY,
                        default=self.config_entry.options.get(
                            CONF_DIRECT_PLAY, DEFAULT_DIRECT_PLAY
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_VIDEO_CONTAINER,
                        default=self.config_entry.options.get(
                            CONF_VIDEO_CONTAINER, DEFAULT_VIDEO_CONTAINER
                        ),
                    ): vol.In(VIDEO_CONTAINERS),
                    vol.Optional(
                        CONF_TRANSCODING_PROFILE,
                        default=self.config_entry.options.get(
                            CONF_TRANSCODING_PROFILE, DEFAULT_TRANSCODING_PROFILE
                        ),
                    ): vol.In(TRANSCODING_PROFILES),
                    vol.Optional(
                        CONF_MAX_VIDEO_BITRATE,
                        default=self.config_entry.options.get(CONF_MAX_VIDEO_BITRATE),
                    ): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=1))),
                    vol.Optional(
                        CONF_MAX_AUDIO_BITRATE,
                        default=self.config_entry.options.get(CONF_MAX_AUDIO_BITRATE),
                    ): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=1))),
                    # Phase 11: Entity name prefix toggles
                    vol.Optional(
                        CONF_PREFIX_MEDIA_PLAYER,
                        default=self.config_entry.options.get(
                            CONF_PREFIX_MEDIA_PLAYER, DEFAULT_PREFIX_MEDIA_PLAYER
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_PREFIX_NOTIFY,
                        default=self.config_entry.options.get(
                            CONF_PREFIX_NOTIFY, DEFAULT_PREFIX_NOTIFY
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_PREFIX_REMOTE,
                        default=self.config_entry.options.get(
                            CONF_PREFIX_REMOTE, DEFAULT_PREFIX_REMOTE
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_PREFIX_BUTTON,
                        default=self.config_entry.options.get(
                            CONF_PREFIX_BUTTON, DEFAULT_PREFIX_BUTTON
                        ),
                    ): bool,
                    # Phase 15: Discovery sensors toggle
                    vol.Optional(
                        CONF_ENABLE_DISCOVERY_SENSORS,
                        default=self.config_entry.options.get(
                            CONF_ENABLE_DISCOVERY_SENSORS, DEFAULT_ENABLE_DISCOVERY_SENSORS
                        ),
                    ): bool,
                }
            ),
        )
