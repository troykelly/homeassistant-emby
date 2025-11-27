# Phase 20: Server Administration

## Overview

This phase implements server administration capabilities for the Emby integration, enabling automation of server maintenance tasks, control of server lifecycle, plugin monitoring, and storage information exposure.

Key features:
- **Scheduled Task Control** - Trigger library scans, metadata refresh, and other scheduled tasks on demand
- **Server Control** - Restart and shutdown server via Home Assistant services
- **Plugin Monitoring** - Sensors for installed plugins with update detection
- **Storage Information** - Expose library paths and storage configuration

## Implementation Status: PENDING

---

## Background Research

### Scheduled Tasks

Emby provides a comprehensive scheduled task system for maintenance operations. Common tasks include:

- **Library Scan** - Scan for new media files
- **Metadata Refresh** - Update metadata from providers
- **Clean Cache** - Remove temporary files
- **Extract Images** - Generate thumbnails and artwork
- **Activity Log Cleanup** - Purge old log entries

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/ScheduledTasks` | GET | Get all scheduled tasks with status (already implemented) |
| `/ScheduledTasks/{Id}/Trigger` | POST | Trigger a task immediately |
| `/System/Restart` | POST | Restart the Emby server |
| `/System/Shutdown` | POST | Shutdown the Emby server |
| `/Plugins` | GET | Get installed plugins |
| `/Library/VirtualFolders` | GET | Get library paths (already implemented) |

### Task States

Scheduled tasks have three possible states:
- **Idle** - Task is not running
- **Running** - Task is currently executing
- **Cancelling** - Task is being cancelled

---

## Task Breakdown

### Task 20.1: Scheduled Task Control API Methods

**Files:** `custom_components/embymedia/api.py`

Add API methods for triggering scheduled tasks.

#### Acceptance Criteria

- [ ] `async_run_scheduled_task(task_id: str)` method added
- [ ] Method calls `POST /ScheduledTasks/{Id}/Trigger`
- [ ] Method raises `EmbyNotFoundError` if task ID invalid
- [ ] Method raises `EmbyConnectionError` on connection failures
- [ ] All errors properly logged
- [ ] 100% test coverage

#### Implementation Pattern

Follow the existing pattern from `async_refresh_library()`:

```python
async def async_run_scheduled_task(
    self,
    task_id: str,
) -> None:
    """Trigger a scheduled task to run immediately.

    Args:
        task_id: The scheduled task ID to trigger.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
        EmbyNotFoundError: Task ID not found.
    """
    endpoint = f"/ScheduledTasks/{task_id}/Trigger"
    await self._request_post(endpoint)
```

#### Test Requirements

```python
# tests/test_api.py

async def test_run_scheduled_task(
    mock_client: EmbyClient,
    aresponses: ResponsesMockServer,
) -> None:
    """Test triggering a scheduled task."""
    # Add mock response for POST /ScheduledTasks/{id}/Trigger
    # Verify 204 No Content response handled correctly
    # Verify task_id passed in URL correctly

async def test_run_scheduled_task_not_found(
    mock_client: EmbyClient,
    aresponses: ResponsesMockServer,
) -> None:
    """Test triggering non-existent task raises EmbyNotFoundError."""
    # Mock 404 response
    # Verify EmbyNotFoundError raised

async def test_run_scheduled_task_connection_error(
    mock_client: EmbyClient,
    aresponses: ResponsesMockServer,
) -> None:
    """Test connection error during task trigger."""
    # Mock connection failure
    # Verify EmbyConnectionError raised
```

---

### Task 20.2: Server Control API Methods

**Files:** `custom_components/embymedia/api.py`

Add API methods for server restart and shutdown.

#### Acceptance Criteria

- [ ] `async_restart_server()` method added
- [ ] `async_shutdown_server()` method added
- [ ] Methods call appropriate endpoints
- [ ] Methods handle 204 No Content response
- [ ] All errors properly logged
- [ ] 100% test coverage

#### Implementation Pattern

```python
async def async_restart_server(self) -> None:
    """Restart the Emby server.

    This operation is asynchronous. The server will begin restarting
    but the API call returns immediately.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    endpoint = "/System/Restart"
    await self._request_post(endpoint)

async def async_shutdown_server(self) -> None:
    """Shutdown the Emby server.

    This operation is asynchronous. The server will begin shutting down
    but the API call returns immediately.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    endpoint = "/System/Shutdown"
    await self._request_post(endpoint)
```

#### Test Requirements

```python
# tests/test_api.py

async def test_restart_server(
    mock_client: EmbyClient,
    aresponses: ResponsesMockServer,
) -> None:
    """Test restarting server."""
    # Add mock response for POST /System/Restart
    # Verify 204 No Content response handled correctly

async def test_shutdown_server(
    mock_client: EmbyClient,
    aresponses: ResponsesMockServer,
) -> None:
    """Test shutting down server."""
    # Add mock response for POST /System/Shutdown
    # Verify 204 No Content response handled correctly

async def test_restart_server_auth_error(
    mock_client: EmbyClient,
    aresponses: ResponsesMockServer,
) -> None:
    """Test restart with auth error raises EmbyAuthenticationError."""
    # Mock 401 response
    # Verify EmbyAuthenticationError raised
```

---

### Task 20.3: Plugin TypedDict and API Method

**Files:** `custom_components/embymedia/const.py`, `custom_components/embymedia/api.py`

Add TypedDict for plugin API response and method to fetch plugins.

#### Acceptance Criteria

- [ ] `EmbyPlugin` TypedDict added to `const.py`
- [ ] `async_get_plugins()` method added to `api.py`
- [ ] Method calls `GET /Plugins`
- [ ] Response properly typed
- [ ] 100% test coverage

#### TypedDict Definition

```python
# custom_components/embymedia/const.py

class EmbyPlugin(TypedDict):
    """Response item from /Plugins endpoint.

    Represents an installed Emby plugin.
    """

    Id: str
    Name: str
    Version: str
    Description: NotRequired[str]
    ImageUrl: NotRequired[str]
    ConfigurationFileName: NotRequired[str]
```

#### API Method Implementation

```python
# custom_components/embymedia/api.py

async def async_get_plugins(self) -> list[EmbyPlugin]:
    """Get list of installed plugins.

    Returns:
        List of plugin objects with version information.

    Raises:
        EmbyConnectionError: Connection failed.
        EmbyAuthenticationError: API key is invalid.
    """
    response = await self._request(HTTP_GET, "/Plugins")
    return response  # type: ignore[return-value]
```

#### Test Requirements

```python
# tests/test_api.py

async def test_get_plugins(
    mock_client: EmbyClient,
    aresponses: ResponsesMockServer,
) -> None:
    """Test getting plugin list."""
    # Mock response with list of plugins
    # Verify correct endpoint called
    # Verify response properly parsed

async def test_get_plugins_empty(
    mock_client: EmbyClient,
    aresponses: ResponsesMockServer,
) -> None:
    """Test getting plugins when none installed."""
    # Mock empty array response
    # Verify empty list returned
```

---

### Task 20.4: Service - Run Scheduled Task

**Files:** `custom_components/embymedia/services.py`, `custom_components/embymedia/strings.json`

Create service to trigger scheduled tasks on demand.

#### Acceptance Criteria

- [ ] `embymedia.run_scheduled_task` service registered
- [ ] Service accepts `task_id` parameter
- [ ] Service validates task_id format
- [ ] Service calls `coordinator.client.async_run_scheduled_task()`
- [ ] Service handles errors with user-friendly messages
- [ ] Service schema added
- [ ] Translations added to `strings.json`
- [ ] 100% test coverage

#### Service Schema

```python
# custom_components/embymedia/services.py

SERVICE_RUN_SCHEDULED_TASK = "run_scheduled_task"
ATTR_TASK_ID = "task_id"

RUN_SCHEDULED_TASK_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_TASK_ID): cv.string,
    }
)
```

#### Service Implementation Pattern

Follow the pattern from existing services like `async_refresh_library`:

```python
async def async_run_scheduled_task(call: ServiceCall) -> None:
    """Run a scheduled task immediately."""
    task_id: str = call.data[ATTR_TASK_ID]

    # Validate task_id
    _validate_emby_id(task_id, "task_id")

    # Get coordinator from hass.data (server-level service, no entity targeting)
    # For Phase 20, we'll target the first configured Emby server
    # Future: Add server selector if multiple servers configured

    try:
        await coordinator.client.async_run_scheduled_task(task_id=task_id)
    except EmbyNotFoundError as err:
        raise HomeAssistantError(
            f"Scheduled task {task_id} not found"
        ) from err
    except EmbyConnectionError as err:
        raise HomeAssistantError(
            "Failed to trigger scheduled task: Connection error"
        ) from err
    except EmbyError as err:
        raise HomeAssistantError(
            f"Failed to trigger scheduled task: {err}"
        ) from err
```

#### Translations

```json
// custom_components/embymedia/strings.json

{
  "services": {
    "run_scheduled_task": {
      "name": "Run scheduled task",
      "description": "Trigger a scheduled task to run immediately.",
      "fields": {
        "task_id": {
          "name": "Task ID",
          "description": "The ID of the scheduled task to run."
        }
      }
    }
  }
}
```

#### Test Requirements

```python
# tests/test_services.py

async def test_run_scheduled_task_service(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test run_scheduled_task service."""
    # Call service with valid task_id
    # Verify API method called with correct task_id

async def test_run_scheduled_task_invalid_id(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test run_scheduled_task with invalid task_id raises error."""
    # Call service with invalid characters in task_id
    # Verify ServiceValidationError raised

async def test_run_scheduled_task_not_found(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test run_scheduled_task with non-existent task."""
    # Mock API to raise EmbyNotFoundError
    # Verify HomeAssistantError raised with appropriate message
```

---

### Task 20.5: Service - Restart Server

**Files:** `custom_components/embymedia/services.py`, `custom_components/embymedia/strings.json`

Create service to restart Emby server.

#### Acceptance Criteria

- [ ] `embymedia.restart_server` service registered
- [ ] Service is server-level (no entity targeting required)
- [ ] Service calls `coordinator.client.async_restart_server()`
- [ ] Service logs restart action
- [ ] Service handles errors gracefully
- [ ] Service schema added
- [ ] Translations added
- [ ] 100% test coverage

#### Service Schema

```python
# custom_components/embymedia/services.py

SERVICE_RESTART_SERVER = "restart_server"

RESTART_SERVER_SCHEMA = vol.Schema({})  # No parameters required
```

#### Service Implementation

```python
async def async_restart_server(call: ServiceCall) -> None:
    """Restart the Emby server."""
    # Get coordinator from hass.data
    # For Phase 20, target first configured server
    # Future: Add server selector

    try:
        await coordinator.client.async_restart_server()
        _LOGGER.info(
            "Server restart initiated on %s",
            coordinator.server_name,
        )
    except EmbyConnectionError as err:
        raise HomeAssistantError(
            "Failed to restart server: Connection error"
        ) from err
    except EmbyError as err:
        raise HomeAssistantError(
            f"Failed to restart server: {err}"
        ) from err
```

#### Translations

```json
{
  "services": {
    "restart_server": {
      "name": "Restart server",
      "description": "Restart the Emby server. The server will be unavailable for a few minutes."
    }
  }
}
```

#### Test Requirements

```python
# tests/test_services.py

async def test_restart_server_service(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test restart_server service."""
    # Call service
    # Verify API method called
    # Verify info log message

async def test_restart_server_connection_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test restart_server with connection error."""
    # Mock API to raise EmbyConnectionError
    # Verify HomeAssistantError raised
```

---

### Task 20.6: Service - Shutdown Server

**Files:** `custom_components/embymedia/services.py`, `custom_components/embymedia/strings.json`

Create service to shutdown Emby server.

#### Acceptance Criteria

- [ ] `embymedia.shutdown_server` service registered
- [ ] Service is server-level (no entity targeting required)
- [ ] Service calls `coordinator.client.async_shutdown_server()`
- [ ] Service logs shutdown action
- [ ] Service handles errors gracefully
- [ ] Service schema added
- [ ] Translations added
- [ ] 100% test coverage

#### Service Schema

```python
# custom_components/embymedia/services.py

SERVICE_SHUTDOWN_SERVER = "shutdown_server"

SHUTDOWN_SERVER_SCHEMA = vol.Schema({})  # No parameters required
```

#### Service Implementation

```python
async def async_shutdown_server(call: ServiceCall) -> None:
    """Shutdown the Emby server."""
    # Get coordinator from hass.data
    # For Phase 20, target first configured server
    # Future: Add server selector

    try:
        await coordinator.client.async_shutdown_server()
        _LOGGER.warning(
            "Server shutdown initiated on %s",
            coordinator.server_name,
        )
    except EmbyConnectionError as err:
        raise HomeAssistantError(
            "Failed to shutdown server: Connection error"
        ) from err
    except EmbyError as err:
        raise HomeAssistantError(
            f"Failed to shutdown server: {err}"
        ) from err
```

#### Translations

```json
{
  "services": {
    "shutdown_server": {
      "name": "Shutdown server",
      "description": "Shutdown the Emby server. The server will be powered off and must be manually restarted."
    }
  }
}
```

#### Test Requirements

```python
# tests/test_services.py

async def test_shutdown_server_service(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test shutdown_server service."""
    # Call service
    # Verify API method called
    # Verify warning log message

async def test_shutdown_server_connection_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test shutdown_server with connection error."""
    # Mock API to raise EmbyConnectionError
    # Verify HomeAssistantError raised
```

---

### Task 20.7: Button Entity - Run Library Scan

**Files:** `custom_components/embymedia/button.py`

Add button entity to trigger library scan task.

#### Acceptance Criteria

- [ ] `EmbyRunLibraryScanButton` class added
- [ ] Button uses IDENTIFY device class
- [ ] Button has name "Run Library Scan"
- [ ] Button calls `async_run_scheduled_task()` with library scan task ID
- [ ] Button finds library scan task ID from coordinator data
- [ ] Button handles task not found gracefully
- [ ] Button properly integrated with device info
- [ ] 100% test coverage

#### Implementation Pattern

Follow the existing `EmbyRefreshLibraryButton` pattern:

```python
# custom_components/embymedia/button.py

class EmbyRunLibraryScanButton(CoordinatorEntity["EmbyServerCoordinator"], ButtonEntity):
    """Button to trigger library scan scheduled task.

    This button finds the library scan scheduled task and triggers it
    to run immediately. This is different from refresh_library which
    uses a different API endpoint.

    Attributes:
        _attr_name: Entity name ("Run Library Scan").
        _attr_device_class: IDENTIFY class for action buttons.
        _attr_has_entity_name: Uses device name as prefix.
    """

    _attr_name = "Run Library Scan"
    _attr_device_class = ButtonDeviceClass.IDENTIFY
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EmbyServerCoordinator,
    ) -> None:
        """Initialize the run library scan button.

        Args:
            coordinator: Server data update coordinator.
        """
        super().__init__(coordinator)

    @property
    def unique_id(self) -> str:
        """Return unique ID for the entity."""
        return f"{self.coordinator.server_id}_run_library_scan"

    @property
    def suggested_object_id(self) -> str | None:
        """Return suggested object ID for entity ID generation."""
        use_prefix: bool = self.coordinator.config_entry.options.get(
            CONF_PREFIX_BUTTON, DEFAULT_PREFIX_BUTTON
        )
        server_name = self.coordinator.server_name
        device_name = f"Emby {server_name}" if use_prefix else server_name
        return f"{device_name} Run Library Scan"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the Emby server."""
        use_prefix: bool = self.coordinator.config_entry.options.get(
            CONF_PREFIX_BUTTON, DEFAULT_PREFIX_BUTTON
        )
        server_name = self.coordinator.server_name
        device_name = f"Emby {server_name}" if use_prefix else server_name

        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.server_id)},
            name=device_name,
            manufacturer="Emby",
        )

    async def async_press(self) -> None:
        """Handle button press - trigger library scan task."""
        try:
            # Get scheduled tasks to find library scan task ID
            tasks = await self.coordinator.client.async_get_scheduled_tasks()

            # Find library scan task (search by key)
            library_scan_task = None
            for task in tasks:
                if task.get("Key") == "RefreshLibrary":
                    library_scan_task = task
                    break

            if library_scan_task is None:
                _LOGGER.error("Library scan scheduled task not found")
                return

            task_id = library_scan_task["Id"]
            await self.coordinator.client.async_run_scheduled_task(task_id=task_id)

            _LOGGER.info(
                "Library scan triggered on %s",
                self.coordinator.server_name,
            )
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error(
                "Failed to trigger library scan on %s: %s",
                self.coordinator.server_name,
                err,
            )
```

#### async_setup_entry Update

```python
# custom_components/embymedia/button.py

async def async_setup_entry(
    hass: HomeAssistant,
    entry: EmbyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Emby button platform."""
    coordinator: EmbyDataUpdateCoordinator = entry.runtime_data.session_coordinator
    server_coordinator: EmbyServerCoordinator = entry.runtime_data.server_coordinator

    entities: list[ButtonEntity] = [
        EmbyRefreshLibraryButton(coordinator),
        EmbyRunLibraryScanButton(server_coordinator),
    ]

    async_add_entities(entities)
```

#### Test Requirements

```python
# tests/test_button.py

async def test_run_library_scan_button_press(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test run library scan button press."""
    # Mock async_get_scheduled_tasks to return tasks with RefreshLibrary
    # Mock async_run_scheduled_task
    # Press button
    # Verify correct task ID used

async def test_run_library_scan_button_task_not_found(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test run library scan when task not found."""
    # Mock async_get_scheduled_tasks to return empty list
    # Press button
    # Verify error logged, no exception raised

async def test_run_library_scan_button_unique_id(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test run library scan button unique ID."""
    # Verify unique_id format
```

---

### Task 20.8: Sensor - Plugin Count

**Files:** `custom_components/embymedia/sensor.py`

Add sensor entity displaying plugin count with plugin list attribute.

#### Acceptance Criteria

- [ ] `EmbyPluginCountSensor` class added
- [ ] Sensor displays count of installed plugins
- [ ] Sensor has `plugins` attribute with plugin list
- [ ] Sensor has `MEASUREMENT` device class
- [ ] Sensor updates via `EmbyServerCoordinator`
- [ ] Sensor properly integrated with device info
- [ ] 100% test coverage

#### Coordinator Integration

First, update `EmbyServerCoordinator` to fetch plugin data:

```python
# custom_components/embymedia/coordinator_sensors.py

async def _async_update_data(self) -> EmbyServerData:
    """Fetch server data from Emby API."""
    try:
        server_info = await self.client.async_get_server_info()
        scheduled_tasks = await self.client.async_get_scheduled_tasks(
            include_hidden=False
        )
        plugins = await self.client.async_get_plugins()

        return EmbyServerData(
            server_info=server_info,
            scheduled_tasks=scheduled_tasks,
            plugins=plugins,  # Add this field
        )
    except EmbyConnectionError as err:
        raise UpdateFailed(f"Error communicating with Emby server: {err}") from err
```

Update `EmbyServerData` dataclass:

```python
# custom_components/embymedia/models.py

@dataclass(slots=True)
class EmbyServerData:
    """Data structure for server-level information."""

    server_info: EmbyServerInfo
    scheduled_tasks: list[EmbyScheduledTask]
    plugins: list[EmbyPlugin]  # Add this field
```

#### Sensor Implementation

```python
# custom_components/embymedia/sensor.py

class EmbyPluginCountSensor(CoordinatorEntity["EmbyServerCoordinator"], SensorEntity):
    """Sensor showing count of installed plugins.

    Attributes:
        _attr_name: Entity name ("Plugins").
        _attr_native_unit_of_measurement: Unit (plugins).
        _attr_state_class: MEASUREMENT for numeric data.
        _attr_has_entity_name: Uses device name as prefix.
    """

    _attr_name = "Plugins"
    _attr_native_unit_of_measurement = "plugins"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = True
    _attr_icon = "mdi:puzzle"

    def __init__(
        self,
        coordinator: EmbyServerCoordinator,
    ) -> None:
        """Initialize the plugin count sensor."""
        super().__init__(coordinator)

    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"{self.coordinator.server_id}_plugins"

    @property
    def native_value(self) -> int:
        """Return the number of installed plugins."""
        if self.coordinator.data is None:
            return 0
        return len(self.coordinator.data.plugins)

    @property
    def extra_state_attributes(self) -> dict[str, list[dict[str, str]]]:
        """Return plugin list as attribute."""
        if self.coordinator.data is None:
            return {"plugins": []}

        plugins = []
        for plugin in self.coordinator.data.plugins:
            plugins.append({
                "id": plugin["Id"],
                "name": plugin["Name"],
                "version": plugin["Version"],
                "description": plugin.get("Description", ""),
            })

        return {"plugins": plugins}

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.server_id)},
            name=self.coordinator.server_name,
            manufacturer="Emby",
        )
```

#### Test Requirements

```python
# tests/test_sensor.py

async def test_plugin_count_sensor(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test plugin count sensor."""
    # Mock coordinator data with plugins
    # Verify native_value is correct count
    # Verify extra_state_attributes contains plugin list

async def test_plugin_count_sensor_no_plugins(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test plugin count sensor with no plugins."""
    # Mock coordinator data with empty plugin list
    # Verify native_value is 0
    # Verify extra_state_attributes is empty list

async def test_plugin_count_sensor_unique_id(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test plugin count sensor unique ID."""
    # Verify unique_id format
```

---

### Task 20.9: Integration Testing

**Files:** `tests/test_button.py`, `tests/test_services.py`, `tests/test_sensor.py`

Comprehensive integration tests for Phase 20 features.

#### Acceptance Criteria

- [ ] All services tested end-to-end
- [ ] All button entities tested
- [ ] All sensors tested
- [ ] Error handling paths tested
- [ ] 100% code coverage maintained
- [ ] All tests pass with strict mypy

#### Test Scenarios

```python
# tests/test_integration_phase_20.py

async def test_run_library_scan_button_service_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test library scan can be triggered via button and service."""
    # Test button press triggers task
    # Test service call triggers task
    # Verify same result

async def test_server_restart_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test server restart service."""
    # Call restart service
    # Verify coordinator handles server disconnection
    # Verify reconnection when server comes back

async def test_plugin_sensor_updates(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test plugin sensor updates when plugins change."""
    # Initial state with plugins
    # Mock coordinator update with different plugins
    # Verify sensor updates correctly
```

---

### Task 20.10: Documentation

**Files:** `README.md`, `custom_components/embymedia/services.yaml`

Update documentation with Phase 20 features.

#### Acceptance Criteria

- [ ] README updated with new services section
- [ ] `services.yaml` added with service descriptions
- [ ] Example automations provided
- [ ] Button entities documented
- [ ] Sensors documented

#### README Section

```markdown
## Server Administration

### Services

#### `embymedia.run_scheduled_task`

Trigger a scheduled task to run immediately.

**Parameters:**
- `task_id` (required): The ID of the scheduled task to run.

**Example:**
```yaml
service: embymedia.run_scheduled_task
data:
  task_id: "abc123"
```

#### `embymedia.restart_server`

Restart the Emby server. The server will be unavailable for a few minutes.

**Example:**
```yaml
service: embymedia.restart_server
```

#### `embymedia.shutdown_server`

Shutdown the Emby server. The server will be powered off and must be manually restarted.

**Example:**
```yaml
service: embymedia.shutdown_server
```

### Button Entities

#### Run Library Scan

Button to trigger the library scan scheduled task immediately. This is useful for
triggering a library refresh after adding new media files.

**Entity ID:** `button.emby_server_run_library_scan`

### Sensors

#### Plugins

Shows the count of installed Emby plugins. The `plugins` attribute contains a list
of installed plugins with their versions.

**Entity ID:** `sensor.emby_server_plugins`

**Attributes:**
- `plugins`: List of installed plugins

### Example Automations

#### Nightly Library Scan

Trigger a full library scan every night at 3 AM:

```yaml
automation:
  - alias: "Nightly Library Scan"
    trigger:
      - platform: time
        at: "03:00:00"
    action:
      - service: button.press
        target:
          entity_id: button.emby_server_run_library_scan
```

#### Restart Server on Pending Restart

Automatically restart the server when a restart is pending:

```yaml
automation:
  - alias: "Auto Restart Emby"
    trigger:
      - platform: state
        entity_id: binary_sensor.emby_server_pending_restart
        to: "on"
        for:
          minutes: 5
    action:
      - service: embymedia.restart_server
```
```

#### services.yaml

```yaml
# custom_components/embymedia/services.yaml

run_scheduled_task:
  name: Run scheduled task
  description: Trigger a scheduled task to run immediately.
  fields:
    task_id:
      name: Task ID
      description: The ID of the scheduled task to run.
      required: true
      example: "abc123"
      selector:
        text:

restart_server:
  name: Restart server
  description: Restart the Emby server. The server will be unavailable for a few minutes.

shutdown_server:
  name: Shutdown server
  description: Shutdown the Emby server. The server will be powered off and must be manually restarted.
```

---

## Success Criteria

### Phase 20 is complete when:

- [ ] All 10 tasks completed with 100% test coverage
- [ ] `embymedia.run_scheduled_task` service functional
- [ ] `embymedia.restart_server` service functional
- [ ] `embymedia.shutdown_server` service functional
- [ ] Run Library Scan button entity working
- [ ] Plugin count sensor displaying correctly
- [ ] All documentation updated
- [ ] No regressions in existing functionality
- [ ] Mypy strict compliance maintained
- [ ] All CI checks passing

---

## Dependencies

### Required Before Phase 20:
- Phase 12 complete (Sensor platform with `EmbyServerCoordinator`)
- `async_get_scheduled_tasks()` API method exists (already implemented)
- `EmbyScheduledTask` TypedDict exists (already implemented)

### Blocks Future Phases:
- None (Phase 20 is independent)

---

## Notes

### Server Control Safety

The restart and shutdown services are powerful administrative actions. Consider:

1. **No Confirmation Dialog**: Home Assistant services don't support confirmation dialogs. Users should be aware these actions are immediate.

2. **Logging**: Both services use appropriate log levels (INFO for restart, WARNING for shutdown).

3. **Future Enhancement**: Consider adding a config option to disable these services for production environments.

### Task ID Discovery

For the `run_scheduled_task` service, users need to know task IDs. Future enhancements could include:

1. A selector that lists available tasks
2. Helper methods to find tasks by name
3. Documentation of common task IDs

For Phase 20, we provide the button entity for the most common task (library scan) and document how to find other task IDs via diagnostics download.

### Plugin Updates

The plugin sensor shows installed plugins but doesn't detect available updates. This would require:

1. Additional API endpoint investigation
2. Parsing plugin repository data
3. Version comparison logic

This is deferred to a future phase.
