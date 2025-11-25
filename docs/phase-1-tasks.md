# Phase 1: Foundation & Core Infrastructure - Detailed Tasks

> **Reference:** [Roadmap - Phase 1](./roadmap.md#phase-1-foundation--core-infrastructure)
>
> **Goal:** Establish the foundational infrastructure including project structure, API client, configuration flow, and basic integration setup.
>
> **Prerequisites:** None (this is the first phase)
>
> **Deliverables:**
> - Working config flow that connects to Emby server
> - API client with authentication and basic endpoints
> - Integration loads successfully in Home Assistant

---

## Table of Contents

1. [Task 1.1: Project Scaffolding](#task-11-project-scaffolding)
2. [Task 1.2: Emby API Client](#task-12-emby-api-client)
3. [Task 1.3: Config Flow](#task-13-config-flow)
4. [Task 1.4: Integration Setup](#task-14-integration-setup)
5. [Task 1.5: Testing Infrastructure](#task-15-testing-infrastructure)
6. [Task 1.6: HACS & Repository Setup](#task-16-hacs--repository-setup)
7. [Acceptance Criteria](#acceptance-criteria)
8. [Dependencies](#dependencies)

---

## Task 1.1: Project Scaffolding

### Overview

Create the directory structure and configuration files required for a Home Assistant custom integration.

### Subtasks

#### 1.1.1 Create Directory Structure

**Files to create:**
```
custom_components/
└── emby/
    ├── __init__.py
    ├── manifest.json
    ├── const.py
    ├── config_flow.py
    ├── api.py
    ├── exceptions.py
    ├── models.py           # Stub for Phase 2 dataclasses
    ├── coordinator.py      # Stub for Phase 2 coordinator
    ├── strings.json
    └── translations/
        └── en.json

tests/
├── __init__.py
├── conftest.py
├── test_api.py
├── test_config_flow.py
├── test_init.py
└── test_exceptions.py
```

**Acceptance Criteria:**
- [ ] All directories exist
- [ ] All files contain valid Python/JSON (no syntax errors)
- [ ] `__init__.py` files are present where required
- [ ] Stub files for Phase 2 components included

---

#### 1.1.2 Configure `manifest.json`

**File:** `custom_components/emby/manifest.json`

**Required Fields:**
```json
{
  "domain": "emby",
  "name": "Emby",
  "codeowners": ["@troykelly"],
  "config_flow": true,
  "dependencies": [],
  "documentation": "https://github.com/troykelly/homeassistant-emby",
  "integration_type": "hub",
  "iot_class": "local_polling",
  "issue_tracker": "https://github.com/troykelly/homeassistant-emby/issues",
  "requirements": ["aiohttp>=3.8.0,<4.0.0"],
  "version": "0.1.0",
  "homeassistant": "2024.1.0"
}
```

**Field Descriptions:**
| Field | Value | Reason |
|-------|-------|--------|
| `domain` | `"emby"` | Unique identifier for the integration |
| `name` | `"Emby"` | Human-readable name shown in UI |
| `config_flow` | `true` | Enables UI-based configuration |
| `integration_type` | `"hub"` | Indicates this is a hub integration with child devices |
| `iot_class` | `"local_polling"` | Indicates local network polling (changes to `local_push` in Phase 7) |
| `requirements` | `["aiohttp>=3.8.0,<4.0.0"]` | Python packages with upper bound for stability |
| `version` | `"0.1.0"` | Semantic version for HACS compatibility |
| `homeassistant` | `"2024.1.0"` | Minimum Home Assistant version required |

**Acceptance Criteria:**
- [ ] JSON is valid and parseable (validate with `jq . manifest.json`)
- [ ] All required fields present
- [ ] `integration_type` is `"hub"`
- [ ] Version follows semantic versioning
- [ ] `config_flow` is `true`
- [ ] `homeassistant` minimum version specified
- [ ] Requirements have upper version bound

---

#### 1.1.3 Set Up `const.py` - Constants and Types

**File:** `custom_components/emby/const.py`

**Required Constants:**
```python
"""Constants for the Emby integration."""
from __future__ import annotations

from typing import TYPE_CHECKING, Final, NotRequired, TypedDict

from homeassistant.const import Platform

if TYPE_CHECKING:
    from .coordinator import EmbyDataUpdateCoordinator
    from homeassistant.config_entries import ConfigEntry

# Integration domain
DOMAIN: Final = "emby"

# Type alias for config entry with runtime data
type EmbyConfigEntry = ConfigEntry[EmbyDataUpdateCoordinator]

# Configuration keys (use HA constants where available)
CONF_API_KEY: Final = "api_key"
CONF_USER_ID: Final = "user_id"
CONF_VERIFY_SSL: Final = "verify_ssl"

# Default values
DEFAULT_PORT: Final = 8096
DEFAULT_SSL: Final = False
DEFAULT_VERIFY_SSL: Final = True
DEFAULT_SCAN_INTERVAL: Final = 10  # seconds
DEFAULT_TIMEOUT: Final = 10  # seconds

# Scan interval limits
MIN_SCAN_INTERVAL: Final = 5
MAX_SCAN_INTERVAL: Final = 300

# API constants
EMBY_TICKS_PER_SECOND: Final = 10_000_000
EMBY_MIN_VERSION: Final = "4.7.0"

# HTTP constants
HEADER_AUTHORIZATION: Final = "X-Emby-Token"
USER_AGENT_TEMPLATE: Final = "HomeAssistant/Emby/{version}"

# HTTP methods
HTTP_GET: Final = "GET"
HTTP_POST: Final = "POST"
HTTP_PUT: Final = "PUT"
HTTP_DELETE: Final = "DELETE"

# API Endpoints
ENDPOINT_SYSTEM_INFO: Final = "/System/Info"
ENDPOINT_SYSTEM_INFO_PUBLIC: Final = "/System/Info/Public"
ENDPOINT_USERS: Final = "/Users"
ENDPOINT_SESSIONS: Final = "/Sessions"

# Platforms
PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER]


# =============================================================================
# TypedDicts for API Responses
# =============================================================================
# Note: TypedDicts are for API responses (external data)
# Dataclasses are for internal models (see models.py in Phase 2)
# =============================================================================

class EmbyServerInfo(TypedDict):
    """Type definition for /System/Info response."""

    Id: str
    ServerName: str
    Version: str
    OperatingSystem: str
    HasPendingRestart: bool
    IsShuttingDown: bool
    LocalAddress: str
    WanAddress: NotRequired[str]


class EmbyPublicInfo(TypedDict):
    """Type definition for /System/Info/Public response."""

    Id: str
    ServerName: str
    Version: str
    LocalAddress: str


class EmbyUser(TypedDict):
    """Type definition for user object."""

    Id: str
    Name: str
    ServerId: str
    HasPassword: bool
    HasConfiguredPassword: bool


class EmbyErrorResponse(TypedDict):
    """Type definition for error responses from Emby API."""

    ErrorCode: NotRequired[str]
    Message: NotRequired[str]


class EmbyConfigFlowUserInput(TypedDict):
    """Type definition for config flow user input."""

    host: str
    port: int
    ssl: bool
    api_key: str
    verify_ssl: NotRequired[bool]


# =============================================================================
# Utility Functions
# =============================================================================

def sanitize_api_key(api_key: str) -> str:
    """Sanitize API key for safe logging.

    Args:
        api_key: The full API key

    Returns:
        Truncated key safe for logging (first 4 + last 2 chars)
    """
    if len(api_key) <= 6:
        return "***"
    return f"{api_key[:4]}...{api_key[-2:]}"


def normalize_host(host: str) -> str:
    """Normalize host input from user.

    Removes protocol prefix and trailing slashes.

    Args:
        host: Raw host input from user

    Returns:
        Cleaned hostname or IP address
    """
    host = host.strip()
    # Remove protocol if present
    for prefix in ("https://", "http://"):
        if host.lower().startswith(prefix):
            host = host[len(prefix):]
    return host.rstrip("/")
```

**Acceptance Criteria:**
- [ ] All constants use `Final` type annotation
- [ ] TypedDicts defined for all API responses used in Phase 1
- [ ] `EmbyConfigEntry` type alias uses coordinator (Phase 2 compatible)
- [ ] No `Any` types used
- [ ] Modern Python syntax (`str | None`, not `Optional[str]`)
- [ ] API endpoint constants defined
- [ ] HTTP method constants defined
- [ ] Utility functions for sanitization and normalization
- [ ] Platform uses `Platform` enum, not string

---

#### 1.1.4 Create `strings.json` and Translations

**File:** `custom_components/emby/strings.json`

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Connect to Emby Server",
        "description": "Enter your Emby server connection details.",
        "data": {
          "host": "Host",
          "port": "Port",
          "ssl": "Use SSL",
          "api_key": "API Key",
          "verify_ssl": "Verify SSL Certificate"
        },
        "data_description": {
          "host": "Hostname or IP address of your Emby server (e.g., 192.168.1.100 or emby.local)",
          "port": "Port number (default: 8096, or 8920 for HTTPS)",
          "ssl": "Enable HTTPS connection",
          "api_key": "API key from Emby Dashboard > Advanced > API Keys",
          "verify_ssl": "Verify SSL certificate (disable only for self-signed certificates)"
        }
      },
      "reauth_confirm": {
        "title": "Re-authenticate Emby Server",
        "description": "The API key for {server_name} is no longer valid. Please enter a new API key."
      }
    },
    "error": {
      "cannot_connect": "Failed to connect to Emby server. Please check the host and port.",
      "invalid_auth": "Invalid API key. Please check your API key in Emby Dashboard > Advanced > API Keys.",
      "invalid_host": "Invalid hostname or IP address",
      "invalid_port": "Port must be between 1 and 65535",
      "timeout": "Connection timed out. The server may be unreachable or slow to respond.",
      "ssl_error": "SSL certificate verification failed. Enable 'Verify SSL Certificate' option or check your certificate.",
      "unsupported_version": "Emby server version {version} is not supported. Minimum required: {min_version}",
      "unknown": "An unexpected error occurred. Please check the logs for details."
    },
    "abort": {
      "already_configured": "This Emby server is already configured",
      "reauth_successful": "Re-authentication successful",
      "unsupported_version": "This Emby server version is not supported"
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "Emby Options",
        "description": "Configure optional settings for the Emby integration.",
        "data": {
          "scan_interval": "Scan interval (seconds)"
        },
        "data_description": {
          "scan_interval": "How often to poll the Emby server for updates (5-300 seconds)"
        }
      }
    }
  }
}
```

**File:** `custom_components/emby/translations/en.json`

Copy of `strings.json` (Home Assistant uses both).

**Acceptance Criteria:**
- [ ] Valid JSON syntax
- [ ] All config flow steps have translations
- [ ] All error codes have translations (expanded list)
- [ ] Abort reasons have translations
- [ ] `en.json` matches `strings.json`
- [ ] Reauth flow translations included
- [ ] Placeholder support for dynamic values (`{server_name}`, `{version}`)
- [ ] `data_description` provides helpful context for all fields
- [ ] `verify_ssl` field included

---

#### 1.1.5 Configure Development Tools

**File:** `pyproject.toml` (project root)

```toml
[project]
name = "homeassistant-emby"
version = "0.1.0"
description = "Home Assistant integration for Emby Media Server"
readme = "README.md"
license = {text = "Apache-2.0"}
requires-python = ">=3.12"
authors = [
    {name = "Troy Kelly", email = "troy@troykelly.com"}
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: End Users/Desktop",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3.12",
    "Topic :: Home Automation",
]

[project.urls]
Homepage = "https://github.com/troykelly/homeassistant-emby"
Repository = "https://github.com/troykelly/homeassistant-emby"
Issues = "https://github.com/troykelly/homeassistant-emby/issues"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
log_cli = true
log_cli_level = "DEBUG"

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_any_generics = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true

[[tool.mypy.overrides]]
module = "homeassistant.*"
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = "pytest_homeassistant_custom_component.*"
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = "voluptuous.*"
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = "aiohttp.*"
ignore_missing_imports = true

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # Pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
    "ARG",    # flake8-unused-arguments
    "SIM",    # flake8-simplify
    "TCH",    # flake8-type-checking
    "PTH",    # flake8-use-pathlib
    "RUF",    # Ruff-specific rules
]
ignore = [
    "E501",   # line too long (handled by formatter)
]

[tool.ruff.lint.isort]
known-first-party = ["custom_components.emby"]

[tool.coverage.run]
source = ["custom_components/emby"]
omit = ["tests/*"]

[tool.coverage.report]
fail_under = 100
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
```

**File:** `requirements_test.txt`

```
pytest>=7.0.0
pytest-asyncio>=0.23.0
pytest-cov>=4.0.0
pytest-homeassistant-custom-component>=0.13.0
aiohttp>=3.8.0,<4.0.0
mypy>=1.0.0
ruff>=0.1.0
pre-commit>=3.0.0
```

**File:** `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies:
          - homeassistant-stubs
        args: [--config-file=pyproject.toml]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
```

**Acceptance Criteria:**
- [ ] `pyproject.toml` configures pytest, mypy, ruff, and coverage
- [ ] mypy is set to strict mode
- [ ] Coverage threshold is 100%
- [ ] All test dependencies listed with version bounds
- [ ] Pre-commit hooks configured
- [ ] Ruff configured with comprehensive rule set
- [ ] Project metadata complete

---

#### 1.1.6 Create Stub Files for Phase 2

**File:** `custom_components/emby/coordinator.py`

```python
"""Data update coordinator for Emby integration."""
from __future__ import annotations

# Stub for Phase 2 implementation
# This file exists to support type imports in const.py

__all__ = ["EmbyDataUpdateCoordinator"]


class EmbyDataUpdateCoordinator:
    """Placeholder for Phase 2 coordinator implementation."""

    pass
```

**File:** `custom_components/emby/models.py`

```python
"""Data models for Emby integration."""
from __future__ import annotations

# Stub for Phase 2 implementation
# Dataclasses for internal models will be defined here
# Note: TypedDicts (in const.py) are for API responses
#       Dataclasses (here) are for internal application models

__all__: list[str] = []
```

**Acceptance Criteria:**
- [ ] Stub files exist and are syntactically valid
- [ ] `coordinator.py` exports `EmbyDataUpdateCoordinator`
- [ ] `models.py` has clear documentation about purpose
- [ ] Files support type imports without circular dependencies

---

## Task 1.2: Emby API Client

### Overview

Implement an async HTTP client for communicating with the Emby server API.

### Subtasks

#### 1.2.1 Create Custom Exceptions

**File:** `custom_components/emby/exceptions.py`

```python
"""Exceptions for the Emby integration."""
from __future__ import annotations


class EmbyError(Exception):
    """Base exception for Emby integration."""


class EmbyConnectionError(EmbyError):
    """Exception raised when connection to Emby server fails.

    This includes network errors, timeouts, and DNS resolution failures.
    """


class EmbyAuthenticationError(EmbyError):
    """Exception raised when authentication fails.

    Raised for HTTP 401 or 403 responses from the Emby server.
    """


class EmbyNotFoundError(EmbyError):
    """Exception raised when a requested resource is not found.

    Raised for HTTP 404 responses from the Emby server.
    """


class EmbyServerError(EmbyError):
    """Exception raised when Emby server returns a server error.

    Raised for HTTP 5xx responses from the Emby server.
    """


class EmbyTimeoutError(EmbyConnectionError):
    """Exception raised when a request times out.

    Inherits from EmbyConnectionError as timeouts are a form of connection failure.
    """


class EmbySSLError(EmbyConnectionError):
    """Exception raised for SSL/TLS certificate errors.

    Inherits from EmbyConnectionError as SSL errors prevent connection.
    """
```

**Acceptance Criteria:**
- [ ] Base exception class `EmbyError` defined
- [ ] Specific exceptions for connection, auth, not found, server errors
- [ ] `EmbyTimeoutError` inherits from `EmbyConnectionError`
- [ ] `EmbySSLError` inherits from `EmbyConnectionError`
- [ ] All exceptions inherit from `EmbyError`
- [ ] Docstrings for all classes explaining when each is raised

---

#### 1.2.2 Implement `EmbyClient` Class

**File:** `custom_components/emby/api.py`

**Class Structure:**
```python
"""Emby API client."""
from __future__ import annotations

import asyncio
import logging
import ssl
from typing import TYPE_CHECKING, Self

import aiohttp

from .const import (
    DEFAULT_TIMEOUT,
    DEFAULT_VERIFY_SSL,
    EMBY_TICKS_PER_SECOND,
    ENDPOINT_SESSIONS,
    ENDPOINT_SYSTEM_INFO,
    ENDPOINT_SYSTEM_INFO_PUBLIC,
    ENDPOINT_USERS,
    HEADER_AUTHORIZATION,
    HTTP_GET,
    USER_AGENT_TEMPLATE,
    sanitize_api_key,
)
from .exceptions import (
    EmbyAuthenticationError,
    EmbyConnectionError,
    EmbyNotFoundError,
    EmbyServerError,
    EmbySSLError,
    EmbyTimeoutError,
)

if TYPE_CHECKING:
    from .const import EmbyPublicInfo, EmbyServerInfo, EmbyUser

_LOGGER = logging.getLogger(__name__)

# Version for User-Agent header
__version__ = "0.1.0"


class EmbyClient:
    """Async client for Emby API.

    This client handles all HTTP communication with the Emby server,
    including authentication, error handling, and response parsing.

    Attributes:
        host: Emby server hostname or IP address.
        port: Emby server port number.
        ssl: Whether to use HTTPS.
        verify_ssl: Whether to verify SSL certificates.

    Example:
        ```python
        async with EmbyClient(
            host="192.168.1.100",
            port=8096,
            api_key="your-api-key",
        ) as client:
            info = await client.async_get_server_info()
            print(f"Connected to {info['ServerName']}")
        ```
    """

    def __init__(
        self,
        host: str,
        port: int,
        api_key: str,
        ssl: bool = False,
        verify_ssl: bool = DEFAULT_VERIFY_SSL,
        timeout: int = DEFAULT_TIMEOUT,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the Emby client.

        Args:
            host: Emby server hostname or IP address.
            port: Emby server port number.
            api_key: API key for authentication.
            ssl: Whether to use HTTPS. Defaults to False.
            verify_ssl: Whether to verify SSL certificates. Defaults to True.
            timeout: Request timeout in seconds. Defaults to 10.
            session: Optional aiohttp session to reuse. If not provided,
                     a new session will be created.
        """
        self._host = host
        self._port = port
        self._api_key = api_key
        self._ssl = ssl
        self._verify_ssl = verify_ssl
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session = session
        self._owns_session = session is None

    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit async context manager."""
        await self.close()

    @property
    def base_url(self) -> str:
        """Return the base URL for API requests.

        Returns:
            Full base URL including protocol, host, and port.
        """
        protocol = "https" if self._ssl else "http"
        return f"{protocol}://{self._host}:{self._port}"

    @property
    def server_id(self) -> str | None:
        """Return the server ID if known.

        Returns:
            Server ID or None if not yet connected.
        """
        return getattr(self, "_server_id", None)

    def _get_headers(self, include_auth: bool = True) -> dict[str, str]:
        """Build headers for API requests.

        Args:
            include_auth: Whether to include authentication header.

        Returns:
            Dictionary of HTTP headers.
        """
        headers = {
            "User-Agent": USER_AGENT_TEMPLATE.format(version=__version__),
            "Accept": "application/json",
        }
        if include_auth:
            headers[HEADER_AUTHORIZATION] = self._api_key
        return headers

    def _get_ssl_context(self) -> ssl.SSLContext | bool:
        """Get SSL context for requests.

        Returns:
            SSL context or False to disable verification.
        """
        if not self._ssl:
            return True  # No SSL
        if not self._verify_ssl:
            return False  # Disable verification
        return True  # Use default SSL context with verification

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session.

        Returns:
            Active aiohttp client session.
        """
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self._timeout,
            )
            self._owns_session = True
        return self._session

    async def _request(
        self,
        method: str,
        endpoint: str,
        include_auth: bool = True,
    ) -> dict[str, object]:
        """Make an HTTP request to the Emby API.

        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint path.
            include_auth: Whether to include authentication.

        Returns:
            Parsed JSON response as dictionary.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: Authentication failed (401/403).
            EmbyNotFoundError: Resource not found (404).
            EmbyServerError: Server error (5xx).
            EmbyTimeoutError: Request timed out.
            EmbySSLError: SSL certificate error.
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers(include_auth)
        ssl_context = self._get_ssl_context()

        _LOGGER.debug(
            "Emby API request: %s %s (auth=%s, key=%s)",
            method,
            endpoint,
            include_auth,
            sanitize_api_key(self._api_key) if include_auth else "N/A",
        )

        session = await self._get_session()

        try:
            async with session.request(
                method,
                url,
                headers=headers,
                ssl=ssl_context,
            ) as response:
                _LOGGER.debug(
                    "Emby API response: %s %s for %s %s",
                    response.status,
                    response.reason,
                    method,
                    endpoint,
                )

                if response.status in (401, 403):
                    raise EmbyAuthenticationError(
                        f"Authentication failed: {response.status} {response.reason}"
                    )

                if response.status == 404:
                    raise EmbyNotFoundError(
                        f"Resource not found: {endpoint}"
                    )

                if response.status >= 500:
                    raise EmbyServerError(
                        f"Server error: {response.status} {response.reason}"
                    )

                response.raise_for_status()

                return await response.json()  # type: ignore[no-any-return]

        except aiohttp.ClientSSLError as err:
            _LOGGER.error(
                "Emby API SSL error for %s %s: %s",
                method,
                endpoint,
                err,
            )
            raise EmbySSLError(f"SSL certificate error: {err}") from err

        except asyncio.TimeoutError as err:
            _LOGGER.error(
                "Emby API timeout for %s %s",
                method,
                endpoint,
            )
            raise EmbyTimeoutError(
                f"Request timed out after {self._timeout.total}s"
            ) from err

        except aiohttp.ClientConnectorError as err:
            _LOGGER.error(
                "Emby API connection error for %s %s: %s",
                method,
                endpoint,
                err,
            )
            raise EmbyConnectionError(
                f"Failed to connect to {self._host}:{self._port}: {err}"
            ) from err

        except aiohttp.ClientResponseError as err:
            _LOGGER.error(
                "Emby API error: %s %s for %s %s",
                err.status,
                err.message,
                method,
                endpoint,
            )
            if err.status in (401, 403):
                raise EmbyAuthenticationError(
                    f"Authentication failed: {err.status}"
                ) from err
            if err.status == 404:
                raise EmbyNotFoundError(f"Resource not found: {endpoint}") from err
            if err.status >= 500:
                raise EmbyServerError(f"Server error: {err.status}") from err
            raise EmbyConnectionError(f"HTTP error: {err.status}") from err

        except aiohttp.ClientError as err:
            _LOGGER.error(
                "Emby API client error for %s %s: %s",
                method,
                endpoint,
                err,
            )
            raise EmbyConnectionError(f"Client error: {err}") from err

    async def async_validate_connection(self) -> bool:
        """Validate connection and authentication.

        Attempts to connect to the server and verify the API key is valid.

        Returns:
            True if connection and authentication succeed.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        await self._request(HTTP_GET, ENDPOINT_SYSTEM_INFO)
        return True

    async def async_get_server_info(self) -> EmbyServerInfo:
        """Get server information (requires authentication).

        Returns:
            Server information including ID, name, and version.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        response = await self._request(HTTP_GET, ENDPOINT_SYSTEM_INFO)
        # Cache server ID for later use
        self._server_id = str(response.get("Id", ""))
        return response  # type: ignore[return-value]

    async def async_get_public_info(self) -> EmbyPublicInfo:
        """Get public server information (no authentication required).

        Useful for checking server availability before authentication.

        Returns:
            Public server information.

        Raises:
            EmbyConnectionError: Connection failed.
        """
        response = await self._request(
            HTTP_GET,
            ENDPOINT_SYSTEM_INFO_PUBLIC,
            include_auth=False,
        )
        return response  # type: ignore[return-value]

    async def async_get_users(self) -> list[EmbyUser]:
        """Get list of users.

        Returns:
            List of user objects.

        Raises:
            EmbyConnectionError: Connection failed.
            EmbyAuthenticationError: API key is invalid.
        """
        response = await self._request(HTTP_GET, ENDPOINT_USERS)
        return response  # type: ignore[return-value]

    async def close(self) -> None:
        """Close the client session.

        Only closes the session if it was created by this client.
        Sessions provided externally are not closed.
        """
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()


# =============================================================================
# Utility Functions
# =============================================================================

def ticks_to_seconds(ticks: int) -> float:
    """Convert Emby ticks to seconds.

    Emby uses "ticks" where 10,000,000 ticks = 1 second.

    Args:
        ticks: Time value in Emby ticks.

    Returns:
        Time value in seconds.

    Examples:
        >>> ticks_to_seconds(10_000_000)
        1.0
        >>> ticks_to_seconds(0)
        0.0
        >>> ticks_to_seconds(5_000_000)
        0.5
    """
    return ticks / EMBY_TICKS_PER_SECOND


def seconds_to_ticks(seconds: float) -> int:
    """Convert seconds to Emby ticks.

    Args:
        seconds: Time value in seconds.

    Returns:
        Time value in Emby ticks.

    Examples:
        >>> seconds_to_ticks(1.0)
        10000000
        >>> seconds_to_ticks(0.0)
        0
        >>> seconds_to_ticks(0.5)
        5000000
    """
    return int(seconds * EMBY_TICKS_PER_SECOND)
```

**Required Methods:**

| Method | Endpoint | Auth Required | Returns |
|--------|----------|---------------|---------|
| `async_validate_connection` | `/System/Info` | Yes | `bool` |
| `async_get_server_info` | `/System/Info` | Yes | `EmbyServerInfo` |
| `async_get_public_info` | `/System/Info/Public` | No | `EmbyPublicInfo` |
| `async_get_users` | `/Users` | Yes | `list[EmbyUser]` |

**Error Handling Requirements:**

| Exception Source | Target Exception |
|------------------|------------------|
| `aiohttp.ClientConnectorError` | `EmbyConnectionError` |
| `aiohttp.ClientSSLError` | `EmbySSLError` |
| `aiohttp.ClientResponseError` (401/403) | `EmbyAuthenticationError` |
| `aiohttp.ClientResponseError` (404) | `EmbyNotFoundError` |
| `aiohttp.ClientResponseError` (5xx) | `EmbyServerError` |
| `asyncio.TimeoutError` | `EmbyTimeoutError` |
| `aiohttp.ServerTimeoutError` | `EmbyTimeoutError` |
| `aiohttp.ClientPayloadError` | `EmbyConnectionError` |

**Acceptance Criteria:**
- [ ] Class uses async/await pattern
- [ ] Async context manager support (`async with`)
- [ ] Session management (create if not provided, don't close external sessions)
- [ ] Proper header injection (`X-Emby-Token`, `User-Agent`)
- [ ] SSL verification configurable
- [ ] Timeout configuration
- [ ] All methods have return type annotations
- [ ] No `Any` types (except where noted with `# type: ignore`)
- [ ] Comprehensive error handling with specific exception types
- [ ] Logging at appropriate levels (DEBUG for requests, ERROR for failures)
- [ ] API key never logged in full (use sanitize function)
- [ ] Docstrings with Args, Returns, Raises, and Examples

---

#### 1.2.3 Logging Level Guidelines

**Logging Level Usage:**

| Level | When to Use | Example |
|-------|-------------|---------|
| `DEBUG` | Every API request/response | `"Emby API request: GET /System/Info"` |
| `DEBUG` | Successful operations | `"Emby API response: 200 OK"` |
| `INFO` | Integration setup/unload | `"Emby integration loaded for {server}"` |
| `INFO` | New devices discovered | `"New Emby player discovered: {name}"` |
| `WARNING` | Recoverable errors, retries | `"Emby API request failed, retrying..."` |
| `WARNING` | Deprecation notices | `"This option is deprecated..."` |
| `ERROR` | Setup failures | `"Failed to connect to Emby server"` |
| `ERROR` | Unrecoverable errors | `"Authentication failed for Emby server"` |

**Sensitive Data Handling:**
- Never log full API keys (truncate with `sanitize_api_key()`)
- Never log passwords or tokens
- Sanitize user IDs in logs if they contain PII

**Acceptance Criteria:**
- [ ] All API requests logged at DEBUG level
- [ ] API key never appears in logs untruncated
- [ ] Errors include context (HTTP status, endpoint)
- [ ] Logging level guidelines documented and followed

---

## Task 1.3: Config Flow

### Overview

Implement the UI-based configuration flow for setting up the integration.

### Subtasks

#### 1.3.1 Implement User Step

**File:** `custom_components/emby/config_flow.py`

```python
"""Config flow for Emby integration."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EmbyClient
from .const import (
    CONF_API_KEY,
    CONF_VERIFY_SSL,
    DEFAULT_PORT,
    DEFAULT_SSL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    EMBY_MIN_VERSION,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    EmbyConfigFlowUserInput,
    normalize_host,
)
from .exceptions import (
    EmbyAuthenticationError,
    EmbyConnectionError,
    EmbySSLError,
    EmbyTimeoutError,
)

if TYPE_CHECKING:
    from homeassistant.data_entry_flow import FlowResult

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
        self._reauth_entry: ConfigEntry | None = None

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
                # Create the config entry
                return await self._async_create_entry(user_input)

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
            version = server_info.get("Version", "0.0.0")
            if not self._is_version_supported(version):
                errors["base"] = "unsupported_version"
                return errors

            # Set unique ID and check for duplicates
            server_id = server_info["Id"]
            await self.async_set_unique_id(server_id)

            if self._reauth_entry is None:
                self._abort_if_unique_id_configured()

            # Store server info for entry creation
            self._server_info = server_info

        except EmbyTimeoutError:
            errors["base"] = "timeout"
        except EmbySSLError:
            errors["base"] = "ssl_error"
        except EmbyConnectionError:
            errors["base"] = "cannot_connect"
        except EmbyAuthenticationError:
            errors["base"] = "invalid_auth"
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
        server_info = getattr(self, "_server_info", {})
        server_name = server_info.get("ServerName") or f"Emby ({user_input['host']})"

        if self._reauth_entry is not None:
            # Update existing entry for reauth
            self.hass.config_entries.async_update_entry(
                self._reauth_entry,
                data={
                    CONF_HOST: user_input["host"],
                    CONF_PORT: user_input["port"],
                    CONF_SSL: user_input.get("ssl", DEFAULT_SSL),
                    CONF_API_KEY: user_input["api_key"],
                    CONF_VERIFY_SSL: user_input.get("verify_ssl", DEFAULT_VERIFY_SSL),
                },
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
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: EmbyConfigFlowUserInput | None = None,
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
                "api_key": user_input["api_key"],
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
                "server_name": (
                    self._reauth_entry.title
                    if self._reauth_entry
                    else "Emby Server"
                ),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> EmbyOptionsFlowHandler:
        """Create the options flow.

        Args:
            config_entry: The config entry to configure.

        Returns:
            Options flow handler instance.
        """
        return EmbyOptionsFlowHandler(config_entry)


class EmbyOptionsFlowHandler(OptionsFlow):
    """Handle Emby options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow.

        Args:
            config_entry: The config entry being configured.
        """
        self.config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, int] | None = None,
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
                }
            ),
        )
```

**Acceptance Criteria:**
- [ ] Form displays all required fields
- [ ] Default values populated (port: 8096, SSL: false, Verify SSL: true)
- [ ] Input validation (host not empty, port in range, API key not empty)
- [ ] Host normalization (strip protocol, trailing slashes)
- [ ] Port validation uses `vol.Range(min=1, max=65535)`
- [ ] Validation attempts real connection
- [ ] Error messages shown for all failure types
- [ ] Unique ID set from server ID
- [ ] Duplicate server detection works
- [ ] Server version compatibility check
- [ ] Reauth flow implemented
- [ ] Options flow with scan interval setting

---

## Task 1.4: Integration Setup

### Overview

Implement the integration entry point and lifecycle management.

### Subtasks

#### 1.4.1 Implement `async_setup_entry`

**File:** `custom_components/emby/__init__.py`

```python
"""The Emby integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EmbyClient
from .const import (
    CONF_API_KEY,
    CONF_VERIFY_SSL,
    DEFAULT_SSL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    PLATFORMS,
    EmbyConfigEntry,
)
from .coordinator import EmbyDataUpdateCoordinator
from .exceptions import EmbyAuthenticationError, EmbyConnectionError

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: EmbyConfigEntry) -> bool:
    """Set up Emby from a config entry.

    Args:
        hass: Home Assistant instance.
        entry: Config entry to set up.

    Returns:
        True if setup was successful.

    Raises:
        ConfigEntryAuthFailed: If authentication fails.
        ConfigEntryNotReady: If server is temporarily unavailable.
    """
    session = async_get_clientsession(hass)

    client = EmbyClient(
        host=str(entry.data[CONF_HOST]),
        port=int(entry.data[CONF_PORT]),
        api_key=str(entry.data[CONF_API_KEY]),
        ssl=bool(entry.data.get(CONF_SSL, DEFAULT_SSL)),
        verify_ssl=bool(entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)),
        session=session,
    )

    try:
        await client.async_validate_connection()
        server_info = await client.async_get_server_info()
        _LOGGER.info(
            "Connected to Emby server: %s (version %s)",
            server_info.get("ServerName", "Unknown"),
            server_info.get("Version", "Unknown"),
        )
    except EmbyAuthenticationError as err:
        raise ConfigEntryAuthFailed(
            f"Invalid API key for Emby server at {entry.data[CONF_HOST]}"
        ) from err
    except EmbyConnectionError as err:
        raise ConfigEntryNotReady(
            f"Unable to connect to Emby server at {entry.data[CONF_HOST]}: {err}"
        ) from err

    # Create coordinator (Phase 2 - for now just store client)
    # In Phase 2, this becomes: coordinator = EmbyDataUpdateCoordinator(hass, client)
    # For Phase 1, we store the client directly but use the coordinator type alias
    # to ensure type compatibility when Phase 2 is implemented

    # Phase 1: Store client directly (temporary)
    # Phase 2: Will replace with coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = client

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register options update listener
    entry.async_on_unload(entry.add_update_listener(async_options_updated))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: EmbyConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass: Home Assistant instance.
        entry: Config entry to unload.

    Returns:
        True if unload was successful.
    """
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Clean up stored data
        hass.data[DOMAIN].pop(entry.entry_id, None)

        # Clean up domain dict if empty
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN, None)

        _LOGGER.info("Unloaded Emby integration for entry %s", entry.entry_id)

    return unload_ok


async def async_options_updated(hass: HomeAssistant, entry: EmbyConfigEntry) -> None:
    """Handle options update.

    Args:
        hass: Home Assistant instance.
        entry: Config entry with updated options.
    """
    _LOGGER.debug("Emby options updated, reloading integration")
    await hass.config_entries.async_reload(entry.entry_id)
```

**Acceptance Criteria:**
- [ ] Creates `EmbyClient` with config entry data
- [ ] Uses Home Assistant's shared aiohttp session
- [ ] Validates connection before setup
- [ ] Raises `ConfigEntryAuthFailed` for authentication errors
- [ ] Raises `ConfigEntryNotReady` for connection errors
- [ ] Stores data in `hass.data[DOMAIN][entry.entry_id]`
- [ ] Forwards setup to platforms
- [ ] Logs server connection info

---

#### 1.4.2 Implement `async_unload_entry`

**Acceptance Criteria:**
- [ ] Unloads all platforms
- [ ] Returns unload success status
- [ ] Cleans up `hass.data[DOMAIN]`
- [ ] Does not close shared aiohttp session
- [ ] Logs unload operation
- [ ] No memory leaks after unload

---

#### 1.4.3 Create Placeholder Platform File

**File:** `custom_components/emby/media_player.py`

```python
"""Media player platform for Emby."""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import EmbyConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EmbyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Emby media player from a config entry.

    Args:
        hass: Home Assistant instance.
        entry: Config entry for this platform.
        async_add_entities: Callback to add entities.
    """
    # Phase 2: Will add media player entities here
    _LOGGER.debug("Emby media player platform setup (placeholder)")
```

**Acceptance Criteria:**
- [ ] File exists and is syntactically valid
- [ ] Uses `EmbyConfigEntry` typed entry
- [ ] Platform setup function signature correct
- [ ] Integration loads without errors

---

## Task 1.5: Testing Infrastructure

### Overview

Create the test infrastructure and write comprehensive tests for all Phase 1 components.

### Subtasks

#### 1.5.1 Create Test Fixtures

**File:** `tests/conftest.py`

```python
"""Fixtures for Emby integration tests."""
from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientSession
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.emby.const import (
    CONF_API_KEY,
    CONF_VERIFY_SSL,
    DOMAIN,
)


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test Emby Server",
        data={
            CONF_HOST: "emby.local",
            CONF_PORT: 8096,
            CONF_SSL: False,
            CONF_API_KEY: "test-api-key-12345",
            CONF_VERIFY_SSL: True,
        },
        unique_id="test-server-id-12345",
        version=1,
    )


@pytest.fixture
def mock_server_info() -> dict[str, Any]:
    """Return mock server info response."""
    return {
        "Id": "test-server-id-12345",
        "ServerName": "Test Emby Server",
        "Version": "4.8.0.0",
        "OperatingSystem": "Linux",
        "HasPendingRestart": False,
        "IsShuttingDown": False,
        "LocalAddress": "http://192.168.1.100:8096",
    }


@pytest.fixture
def mock_public_info() -> dict[str, Any]:
    """Return mock public info response."""
    return {
        "Id": "test-server-id-12345",
        "ServerName": "Test Emby Server",
        "Version": "4.8.0.0",
        "LocalAddress": "http://192.168.1.100:8096",
    }


@pytest.fixture
def mock_users() -> list[dict[str, Any]]:
    """Return mock users response."""
    return [
        {
            "Id": "user-1",
            "Name": "TestUser",
            "ServerId": "test-server-id-12345",
            "HasPassword": True,
            "HasConfiguredPassword": True,
        }
    ]


@pytest.fixture
def mock_emby_client(
    mock_server_info: dict[str, Any],
    mock_public_info: dict[str, Any],
    mock_users: list[dict[str, Any]],
) -> Generator[MagicMock]:
    """Mock EmbyClient for testing."""
    with patch(
        "custom_components.emby.config_flow.EmbyClient", autospec=True
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.async_validate_connection = AsyncMock(return_value=True)
        client.async_get_server_info = AsyncMock(return_value=mock_server_info)
        client.async_get_public_info = AsyncMock(return_value=mock_public_info)
        client.async_get_users = AsyncMock(return_value=mock_users)
        client.close = AsyncMock()
        client.base_url = "http://emby.local:8096"
        yield client


@pytest.fixture
def mock_emby_client_init(
    mock_server_info: dict[str, Any],
    mock_public_info: dict[str, Any],
    mock_users: list[dict[str, Any]],
) -> Generator[MagicMock]:
    """Mock EmbyClient for __init__.py testing."""
    with patch(
        "custom_components.emby.EmbyClient", autospec=True
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.async_validate_connection = AsyncMock(return_value=True)
        client.async_get_server_info = AsyncMock(return_value=mock_server_info)
        client.async_get_public_info = AsyncMock(return_value=mock_public_info)
        client.async_get_users = AsyncMock(return_value=mock_users)
        client.close = AsyncMock()
        client.base_url = "http://emby.local:8096"
        yield client


@pytest.fixture
def mock_aiohttp_session() -> Generator[MagicMock]:
    """Mock aiohttp ClientSession."""
    with patch("aiohttp.ClientSession", autospec=True) as mock_session:
        session = mock_session.return_value
        session.closed = False
        session.close = AsyncMock()
        yield session


@pytest.fixture
async def mock_aiohttp_response() -> AsyncGenerator[MagicMock]:
    """Create a mock aiohttp response."""
    response = MagicMock()
    response.status = 200
    response.reason = "OK"
    response.json = AsyncMock(return_value={})
    response.raise_for_status = MagicMock()
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)
    yield response
```

**Acceptance Criteria:**
- [ ] Fixtures for mock config entry
- [ ] Fixtures for mock API responses (server info, public info, users)
- [ ] Fixtures for mock EmbyClient (config_flow and __init__)
- [ ] Fixtures for mock aiohttp session and response
- [ ] All fixtures properly typed
- [ ] Fixtures support both config flow and init testing

---

#### 1.5.2 Write API Client Tests

**File:** `tests/test_api.py`

**Required Test Cases:**
- [ ] `test_client_initialization` - Verify client stores parameters correctly
- [ ] `test_base_url_http` - Base URL generation without SSL
- [ ] `test_base_url_https` - Base URL generation with SSL
- [ ] `test_validate_connection_success` - Successful validation
- [ ] `test_validate_connection_auth_error` - 401 response raises `EmbyAuthenticationError`
- [ ] `test_validate_connection_403_error` - 403 response raises `EmbyAuthenticationError`
- [ ] `test_validate_connection_connection_error` - Connection failure raises `EmbyConnectionError`
- [ ] `test_validate_connection_timeout` - Timeout raises `EmbyTimeoutError`
- [ ] `test_validate_connection_ssl_error` - SSL error raises `EmbySSLError`
- [ ] `test_get_server_info_success` - Successful server info retrieval
- [ ] `test_get_server_info_caches_server_id` - Server ID is cached
- [ ] `test_get_public_info_success` - Successful public info retrieval
- [ ] `test_get_public_info_no_auth` - Public info doesn't include auth header
- [ ] `test_get_users_success` - Successful user list retrieval
- [ ] `test_get_users_empty` - Empty user list handled
- [ ] `test_ticks_to_seconds` - Tick conversion accuracy
- [ ] `test_ticks_to_seconds_zero` - Zero ticks returns zero
- [ ] `test_ticks_to_seconds_negative` - Negative ticks handled
- [ ] `test_seconds_to_ticks` - Reverse tick conversion accuracy
- [ ] `test_seconds_to_ticks_zero` - Zero seconds returns zero
- [ ] `test_seconds_to_ticks_fractional` - Fractional seconds handled
- [ ] `test_ticks_conversion_roundtrip` - Roundtrip conversion preserves value
- [ ] `test_session_not_closed_if_external` - External session not closed
- [ ] `test_session_closed_if_internal` - Internal session closed on `close()`
- [ ] `test_session_created_if_not_provided` - New session created when none provided
- [ ] `test_async_context_manager` - Context manager works correctly
- [ ] `test_invalid_json_response` - Invalid JSON handled gracefully
- [ ] `test_headers_include_auth` - Auth header included when required
- [ ] `test_headers_exclude_auth` - Auth header excluded when not required
- [ ] `test_user_agent_header` - User-Agent header is set
- [ ] `test_server_error_500` - 500 response raises `EmbyServerError`
- [ ] `test_not_found_404` - 404 response raises `EmbyNotFoundError`

**Acceptance Criteria:**
- [ ] All test cases pass
- [ ] 100% coverage of `api.py`
- [ ] Edge cases covered (empty responses, network errors, timeouts)
- [ ] Async tests use `pytest.mark.asyncio`
- [ ] SSL, timeout, and all exception types tested

---

#### 1.5.3 Write Config Flow Tests

**File:** `tests/test_config_flow.py`

**Required Test Cases:**
- [ ] `test_form_displayed` - Form shown on initial step
- [ ] `test_successful_config` - Full flow completes successfully
- [ ] `test_connection_error` - Connection error shows message
- [ ] `test_auth_error` - Auth error shows message
- [ ] `test_timeout_error` - Timeout error shows message
- [ ] `test_ssl_error` - SSL error shows message
- [ ] `test_unknown_error` - Unknown error handled gracefully
- [ ] `test_duplicate_server` - Duplicate server aborts
- [ ] `test_invalid_host_empty` - Empty host shows error
- [ ] `test_invalid_port_zero` - Port 0 shows error
- [ ] `test_invalid_port_negative` - Negative port shows error
- [ ] `test_invalid_port_too_high` - Port > 65535 shows error
- [ ] `test_host_normalization` - Protocol prefix removed from host
- [ ] `test_host_normalization_trailing_slash` - Trailing slash removed
- [ ] `test_version_check_supported` - Supported version accepted
- [ ] `test_version_check_unsupported` - Unsupported version rejected
- [ ] `test_options_flow` - Options can be modified
- [ ] `test_options_flow_default_values` - Default values populated
- [ ] `test_options_flow_validation` - Invalid values rejected
- [ ] `test_reauth_flow` - Reauth flow works
- [ ] `test_reauth_flow_success` - Successful reauth updates entry
- [ ] `test_user_input_preserved_on_error` - User input preserved (except API key)

**Acceptance Criteria:**
- [ ] All test cases pass
- [ ] 100% coverage of `config_flow.py`
- [ ] All error branches tested
- [ ] Options flow tested
- [ ] Reauth flow tested
- [ ] Input validation tested

---

#### 1.5.4 Write Integration Setup Tests

**File:** `tests/test_init.py`

**Required Test Cases:**
- [ ] `test_setup_entry_success` - Entry sets up correctly
- [ ] `test_setup_entry_connection_failure` - Setup raises ConfigEntryNotReady
- [ ] `test_setup_entry_auth_failure` - Setup raises ConfigEntryAuthFailed
- [ ] `test_unload_entry` - Entry unloads cleanly
- [ ] `test_unload_entry_cleans_data` - hass.data cleaned after unload
- [ ] `test_options_update_triggers_reload` - Options update reloads integration
- [ ] `test_multiple_entries` - Multiple config entries supported
- [ ] `test_rapid_setup_unload` - Rapid setup/unload cycles handled

**Acceptance Criteria:**
- [ ] All test cases pass
- [ ] 100% coverage of `__init__.py`
- [ ] Setup and teardown paths tested
- [ ] Exception handling tested

---

#### 1.5.5 Write Exception Tests

**File:** `tests/test_exceptions.py`

**Required Test Cases:**
- [ ] `test_exception_hierarchy_emby_error` - All exceptions inherit from `EmbyError`
- [ ] `test_exception_hierarchy_timeout` - `EmbyTimeoutError` inherits from `EmbyConnectionError`
- [ ] `test_exception_hierarchy_ssl` - `EmbySSLError` inherits from `EmbyConnectionError`
- [ ] `test_exception_messages` - Exceptions can contain messages
- [ ] `test_exception_chaining` - Exceptions can chain from cause

**Acceptance Criteria:**
- [ ] All test cases pass
- [ ] Exception inheritance verified
- [ ] 100% coverage of `exceptions.py`

---

#### 1.5.6 Write Constant Tests

**File:** `tests/test_const.py`

**Required Test Cases:**
- [ ] `test_sanitize_api_key_long` - Long key truncated correctly
- [ ] `test_sanitize_api_key_short` - Short key returns masked
- [ ] `test_sanitize_api_key_minimum` - Minimum length key handled
- [ ] `test_normalize_host_plain` - Plain host unchanged
- [ ] `test_normalize_host_http_prefix` - HTTP prefix removed
- [ ] `test_normalize_host_https_prefix` - HTTPS prefix removed
- [ ] `test_normalize_host_trailing_slash` - Trailing slash removed
- [ ] `test_normalize_host_whitespace` - Whitespace stripped
- [ ] `test_normalize_host_combined` - Multiple normalizations applied

**Acceptance Criteria:**
- [ ] All test cases pass
- [ ] Utility functions fully tested

---

## Task 1.6: HACS & Repository Setup

### Overview

Configure files required for HACS compatibility and open-source distribution.

### Subtasks

#### 1.6.1 Create `hacs.json`

**File:** `hacs.json` (project root)

```json
{
  "name": "Emby",
  "content_in_root": false,
  "filename": "emby",
  "render_readme": true,
  "homeassistant": "2024.1.0",
  "zip_release": true
}
```

**Acceptance Criteria:**
- [ ] Valid JSON syntax
- [ ] `homeassistant` version matches manifest
- [ ] HACS can discover the integration

---

#### 1.6.2 Create LICENSE File

**File:** `LICENSE` (project root)

Use Apache License 2.0 or MIT License (choose based on project preferences).

**Acceptance Criteria:**
- [ ] LICENSE file exists
- [ ] License is OSI-approved
- [ ] Matches project.license in pyproject.toml

---

#### 1.6.3 Create GitHub Actions CI

**File:** `.github/workflows/test.yml`

```yaml
name: Test

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements_test.txt
          pip install -e .

      - name: Run ruff
        run: ruff check custom_components/emby tests

      - name: Run mypy
        run: mypy custom_components/emby

      - name: Run tests
        run: pytest tests/ --cov=custom_components.emby --cov-report=xml --cov-fail-under=100

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          fail_ci_if_error: true
```

**Acceptance Criteria:**
- [ ] CI runs on push and PR to main
- [ ] Ruff linting included
- [ ] mypy type checking included
- [ ] Tests with coverage included
- [ ] Coverage uploaded to Codecov

---

## Acceptance Criteria

### Phase 1 Complete When:

1. **Project Structure**
   - [ ] All required files exist
   - [ ] Valid JSON in manifest, translations, hacs.json
   - [ ] Development tools configured (pyproject.toml, pre-commit)
   - [ ] Stub files for Phase 2 in place
   - [ ] GitHub Actions CI passing

2. **API Client**
   - [ ] Connects to Emby server
   - [ ] Authenticates with API key
   - [ ] Retrieves server info, public info, users
   - [ ] Handles all error cases (connection, auth, timeout, SSL, 404, 5xx)
   - [ ] Async context manager support
   - [ ] 100% test coverage

3. **Config Flow**
   - [ ] UI form works with all fields
   - [ ] Input validation (host, port, API key)
   - [ ] Host normalization
   - [ ] Validation connects to server
   - [ ] All error types display correctly
   - [ ] Duplicates prevented
   - [ ] Server version check
   - [ ] Options flow works
   - [ ] Reauth flow works
   - [ ] 100% test coverage

4. **Integration Setup**
   - [ ] `async_setup_entry` works
   - [ ] `async_unload_entry` works
   - [ ] `ConfigEntryAuthFailed` raised for auth errors
   - [ ] `ConfigEntryNotReady` raised for connection errors
   - [ ] Options update triggers reload
   - [ ] Data cleanup on unload
   - [ ] 100% test coverage

5. **Code Quality**
   - [ ] mypy strict passes
   - [ ] ruff passes
   - [ ] No `Any` types (except required HA overrides)
   - [ ] All functions have type annotations
   - [ ] Google-style docstrings on all public functions
   - [ ] Pre-commit hooks pass

6. **HACS Compatibility**
   - [ ] `hacs.json` present and valid
   - [ ] LICENSE file present
   - [ ] CI/CD pipeline passing

---

## Dependencies

### External Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `aiohttp` | `>=3.8.0,<4.0.0` | Async HTTP client |
| `homeassistant` | `>=2024.1.0` | Home Assistant core |

### Test Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | `>=7.0.0` | Test framework |
| `pytest-asyncio` | `>=0.23.0` | Async test support |
| `pytest-cov` | `>=4.0.0` | Coverage reporting |
| `pytest-homeassistant-custom-component` | `>=0.13.0` | HA test utilities |
| `mypy` | `>=1.0.0` | Type checking |
| `ruff` | `>=0.1.0` | Linting and formatting |
| `pre-commit` | `>=3.0.0` | Git hooks |

---

## Notes

### TDD Workflow Reminder

For every piece of code in this phase:

1. **RED** - Write a failing test first
2. **GREEN** - Write minimal code to pass
3. **REFACTOR** - Clean up while tests pass

No exceptions. See `ha-emby-tdd` skill for details.

### Type Safety Reminder

- Use TypedDicts for all API response types (external data)
- Use dataclasses for internal models (Phase 2)
- No `Any` types except where HA requires them
- All functions must have return type annotations
- Use `str | None` syntax (not `Optional[str]`)
- Use `Platform` enum, not strings

See `ha-emby-typing` skill for details.

### Two Failures Rule

If any implementation fails twice:

1. STOP coding
2. Research the problem
3. Read official documentation
4. Look at working examples in HA core
5. Understand before trying again

See `ha-emby-research` skill for details.

### Docstring Format

Use Google-style docstrings:

```python
def example_function(param1: str, param2: int) -> bool:
    """Short description of what the function does.

    Longer description if needed, explaining behavior,
    side effects, or important details.

    Args:
        param1: Description of first parameter.
        param2: Description of second parameter.

    Returns:
        Description of return value.

    Raises:
        ValueError: When param1 is empty.
        TypeError: When param2 is negative.

    Examples:
        >>> example_function("test", 42)
        True
    """
```

### Architecture Note

Phase 1 stores `EmbyClient` directly in `hass.data[DOMAIN][entry_id]`. In Phase 2, this will be replaced with `EmbyDataUpdateCoordinator` which wraps the client. The `EmbyConfigEntry` type alias already uses the coordinator type for forward compatibility.
