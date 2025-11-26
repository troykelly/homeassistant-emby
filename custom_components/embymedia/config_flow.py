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
    CONF_ENABLE_WEBSOCKET,
    CONF_IGNORED_DEVICES,
    CONF_MAX_AUDIO_BITRATE,
    CONF_MAX_VIDEO_BITRATE,
    CONF_USER_ID,
    CONF_VERIFY_SSL,
    CONF_VIDEO_CONTAINER,
    DEFAULT_DIRECT_PLAY,
    DEFAULT_ENABLE_WEBSOCKET,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SSL,
    DEFAULT_VERIFY_SSL,
    DEFAULT_VIDEO_CONTAINER,
    DOMAIN,
    EMBY_MIN_VERSION,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
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


class EmbyConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg,misc]
    """Handle a config flow for Emby."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._reauth_entry: ConfigEntry | None = None
        self._server_info: EmbyServerInfo | None = None
        self._user_input: EmbyConfigFlowUserInput | None = None
        self._users: list[EmbyUser] | None = None
        self._client: EmbyClient | None = None

    async def async_step_user(
        self,
        user_input: EmbyConfigFlowUserInput | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial step.

        Args:
            user_input: User-provided configuration data.

        Returns:
            Config flow result (form or entry creation).
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate and normalize input
            errors = self._validate_input(user_input)

            if not errors:
                # Normalize the host
                user_input["host"] = normalize_host(user_input["host"])

                # Attempt connection
                errors = await self._async_validate_connection(user_input)

            if not errors:
                # Store validated input and proceed to user selection
                self._user_input = user_input
                return await self.async_step_user_select()

            # Re-show form with errors (preserve input except API key)
            return self.async_show_form(
                step_id="user",
                data_schema=_build_user_schema(user_input),
                errors=errors,
            )

        # Show initial form
        return self.async_show_form(
            step_id="user",
            data_schema=_build_user_schema(),
            errors=errors,
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
            # Store selected user ID (empty string means admin context)
            user_id = user_input.get(CONF_USER_ID, "")
            return await self._async_create_entry_with_user(user_id)

        # Build user selection options
        user_options: dict[str, str] = {}
        if self._users:
            for user in self._users:
                user_id = str(user.get("Id", ""))
                user_name = str(user.get("Name", "Unknown"))
                user_options[user_id] = user_name

        # Add option to skip user selection (admin context)
        user_options[""] = "Use admin context (no user)"

        return self.async_show_form(
            step_id="user_select",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USER_ID, default=""): vol.In(user_options),
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
    ) -> ConfigFlowResult:
        """Create config entry with user selection.

        Args:
            user_id: Selected user ID (empty for admin context).

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

        data = {
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
            version: Server version string (e.g., "4.8.0.0").

        Returns:
            True if version is supported.
        """
        try:
            # Parse version (handle formats like "4.8.0.0")
            parts = version.split(".")
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 0

            min_parts = EMBY_MIN_VERSION.split(".")
            min_major = int(min_parts[0]) if len(min_parts) > 0 else 0
            min_minor = int(min_parts[1]) if len(min_parts) > 1 else 0

            if major > min_major:
                return True
            if major == min_major and minor >= min_minor:
                return True
            return False

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
    @callback  # type: ignore[misc]
    def async_get_options_flow(
        config_entry: ConfigEntry,  # noqa: ARG004
    ) -> EmbyOptionsFlowHandler:
        """Create the options flow.

        Args:
            config_entry: The config entry to configure.

        Returns:
            Options flow handler instance.
        """
        return EmbyOptionsFlowHandler()


class EmbyOptionsFlowHandler(OptionsFlow):  # type: ignore[misc]
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
                        default=self.config_entry.options.get(
                            CONF_IGNORED_DEVICES, ""
                        ),
                    ): str,
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
                        CONF_MAX_VIDEO_BITRATE,
                        default=self.config_entry.options.get(CONF_MAX_VIDEO_BITRATE),
                    ): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=1))),
                    vol.Optional(
                        CONF_MAX_AUDIO_BITRATE,
                        default=self.config_entry.options.get(CONF_MAX_AUDIO_BITRATE),
                    ): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=1))),
                }
            ),
        )
