# Home Assistant Emby Integration

A from-scratch Home Assistant integration for Emby Media Server.

## Project Overview

This is a custom Home Assistant integration that provides media player entities for Emby Media Server clients. It follows Home Assistant 2025 best practices and strict development standards.

## Mandatory Development Rules

### 1. Test-Driven Development (TDD)

**Every line of code MUST start with a failing test.**

```
RED → GREEN → REFACTOR
```

- Write test first
- Watch it fail (if it passes immediately, your test is wrong)
- Write minimal code to pass
- Refactor while keeping tests green
- No exceptions for "simple" code

See skill: `ha-emby-tdd`

### 2. No `Any` Type

**NEVER use `Any` in type annotations.**

- Use TypedDict for API response structures
- Use dataclasses for internal models
- Use Protocol for interfaces
- Use Generics for containers
- The only exception: `**kwargs: Any` when overriding HA base class methods that require it

See skill: `ha-emby-typing`

### 3. Two Failures = Research

**If code fails twice, STOP and research.**

- Don't guess-and-check
- Read official documentation
- Examine working implementations in HA core
- Understand before attempting again

See skill: `ha-emby-research`

## Project Structure

```
custom_components/embymedia/
├── __init__.py           # Integration setup, async_setup_entry
├── manifest.json         # Integration metadata
├── config_flow.py        # UI configuration flow
├── const.py              # Constants, types, TypedDicts
├── coordinator.py        # DataUpdateCoordinator
├── entity.py             # Base EmbyEntity class
├── api.py                # Emby API client wrapper
├── models.py             # Dataclasses for internal models
│
│   # Entity Platforms
├── media_player.py       # MediaPlayerEntity - playback control
├── remote.py             # RemoteEntity - navigation commands
├── notify.py             # NotifyEntity - on-screen messages
├── button.py             # ButtonEntity - server actions
│
│   # Media Features
├── media_source.py       # MediaSource provider
├── browse.py             # Media browser helpers
├── image.py              # Image proxy for album art
│
│   # Supporting
├── services.py           # Custom services
├── websocket.py          # WebSocket client
├── cache.py              # Response caching
├── exceptions.py         # Custom exceptions
├── diagnostics.py        # Diagnostic download
├── strings.json          # English translations
└── translations/
    └── en.json

tests/
├── conftest.py           # Pytest fixtures
├── test_init.py          # Setup/unload tests
├── test_config_flow.py   # Config flow tests
├── test_coordinator.py   # Coordinator tests
├── test_api.py           # API client tests
├── test_media_player.py  # Media player tests
├── test_remote.py        # Remote entity tests
├── test_notify.py        # Notify entity tests
├── test_button.py        # Button entity tests
└── ...                   # Additional test files
```

## Key Technologies

- **Python 3.12+** - Type hints with modern syntax (`X | None`, not `Optional[X]`)
- **Home Assistant 2025.x** - Latest patterns and APIs
- **pytest + pytest-homeassistant-custom-component** - Testing framework
- **mypy strict** - Type checking
- **aiohttp** - Async HTTP client
- **Emby REST API** - Server communication

## Environment Variables

### Live Server Testing

For testing against a live Emby server, set these environment variables in `.env`:

```bash
EMBY_URL=https://your-emby-server.example.com
EMBY_API_KEY=your-api-key-here
```

The devcontainer automatically loads `.env` into the container environment.

### Home Assistant Devcontainer Testing

For testing against the devcontainer's Home Assistant instance, use these environment variables:

```bash
HOMEASSISTANT_URL=http://localhost:8123
HOMEASSISTANT_TOKEN=your-long-lived-access-token
```

**Getting a Long-Lived Access Token:**

1. Open Home Assistant UI at `http://localhost:8123`
2. Go to your profile (click username in sidebar)
3. Scroll to "Long-Lived Access Tokens"
4. Click "Create Token" and copy the value

**Using the Home Assistant API:**

```python
import os
import aiohttp

async def test_ha_integration():
    """Test against running Home Assistant instance."""
    ha_url = os.environ.get("HOMEASSISTANT_URL", "http://localhost:8123")
    ha_token = os.environ.get("HOMEASSISTANT_TOKEN")

    if not ha_token:
        pytest.skip("HOMEASSISTANT_TOKEN required for HA integration tests")

    headers = {
        "Authorization": f"Bearer {ha_token}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        # Check integration is loaded
        async with session.get(
            f"{ha_url}/api/states", headers=headers
        ) as resp:
            states = await resp.json()
            emby_entities = [s for s in states if s["entity_id"].startswith("media_player.emby")]

        # Call a service
        async with session.post(
            f"{ha_url}/api/services/embymedia/refresh_library",
            headers=headers,
            json={"entity_id": "media_player.emby_living_room"},
        ) as resp:
            result = await resp.json()
```

**Useful HA API Endpoints for Testing:**

| Endpoint                           | Method | Purpose                   |
| ---------------------------------- | ------ | ------------------------- |
| `/api/states`                      | GET    | List all entity states    |
| `/api/states/{entity_id}`          | GET    | Get specific entity state |
| `/api/services/{domain}/{service}` | POST   | Call a service            |
| `/api/events/{event_type}`         | POST   | Fire an event             |
| `/api/config`                      | GET    | Get HA configuration      |

### Accessing Environment Variables

**NEVER read `.env` files directly in code.** Always use `os.environ`:

```python
import os

# CORRECT - Read from environment
emby_url = os.environ.get("EMBY_URL")
emby_api_key = os.environ.get("EMBY_API_KEY")
ha_url = os.environ.get("HOMEASSISTANT_URL")
ha_token = os.environ.get("HOMEASSISTANT_TOKEN")

# WRONG - Never do this
# from dotenv import load_dotenv
# load_dotenv()
```

### Test Fixtures for Live Testing

```python
import os
import pytest

@pytest.fixture
def live_emby_url() -> str | None:
    """Get live Emby URL from environment."""
    return os.environ.get("EMBY_URL")

@pytest.fixture
def live_emby_api_key() -> str | None:
    """Get live Emby API key from environment."""
    return os.environ.get("EMBY_API_KEY")

@pytest.fixture
def requires_live_server(live_emby_url: str | None, live_emby_api_key: str | None):
    """Skip test if live server credentials not available."""
    if not live_emby_url or not live_emby_api_key:
        pytest.skip("EMBY_URL and EMBY_API_KEY required for live tests")

@pytest.fixture
def ha_url() -> str:
    """Get Home Assistant URL from environment."""
    return os.environ.get("HOMEASSISTANT_URL", "http://localhost:8123")

@pytest.fixture
def ha_token() -> str | None:
    """Get Home Assistant token from environment."""
    return os.environ.get("HOMEASSISTANT_TOKEN")

@pytest.fixture
def requires_ha_server(ha_token: str | None):
    """Skip test if HA token not available."""
    if not ha_token:
        pytest.skip("HOMEASSISTANT_TOKEN required for HA integration tests")
```

## Development Commands

```bash
# Run tests
pytest tests/

# Run tests with coverage
pytest tests/ --cov=custom_components.embymedia --cov-report=term-missing --cov-fail-under=100

# Run specific test
pytest tests/test_media_player.py::test_play_media -v

# Type checking
mypy custom_components/embymedia/

# Linting
ruff check custom_components/embymedia/
ruff format custom_components/embymedia/
```

## Testing Patterns

### Required Fixtures (conftest.py)

```python
@pytest.fixture
def mock_emby_client() -> Generator[MagicMock, None, None]:
    """Mock Emby API client."""
    with patch("custom_components.embymedia.EmbyClient", autospec=True) as mock:
        yield mock.return_value

@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "emby.local", CONF_PORT: 8096, CONF_API_KEY: "test"},
        unique_id="server-123",
    )
```

### Test Coverage Requirements

- 100% coverage for all code
- All config flow paths (success, errors, abort)
- All entity states
- All service methods
- Error handling paths

## Emby API Notes

### Authentication

Use API key authentication via `X-Emby-Token` header or `api_key` query parameter.

### Time Units

Emby uses "ticks" (100-nanosecond intervals):

- `10_000_000 ticks = 1 second`
- `position_ticks // 10_000_000 = position_seconds`

### Key Endpoints

- `GET /System/Info` - Server information
- `GET /Sessions` - Active sessions/players
- `POST /Sessions/{id}/Playing/{command}` - Playback control
- `GET /Users/{id}/Items` - Browse library
- `GET /Items/{id}/Images/{type}` - Get images

## Configuration

### Config Flow Steps

1. **User step** - Enter host, port, API key
2. Validate connection and authentication
3. Set unique ID from server ID
4. Create config entry

### Options Flow (if needed)

For optional settings that can be changed after setup.

## Entity Features

### MediaPlayerEntity Supported Features

- PLAY, PAUSE, STOP
- VOLUME_SET, VOLUME_MUTE
- NEXT_TRACK, PREVIOUS_TRACK
- SEEK
- PLAY_MEDIA
- BROWSE_MEDIA
- MEDIA_ENQUEUE
- SHUFFLE_SET, REPEAT_SET
- SEARCH_MEDIA (voice assistant support)

### Other Entity Platforms

| Platform        | Entities    | Purpose                                                                                                    |
| --------------- | ----------- | ---------------------------------------------------------------------------------------------------------- |
| `remote`        | Per-session | Navigation commands (Up, Down, Select, Back, Home)                                                         |
| `notify`        | Per-session | Send on-screen messages to clients                                                                         |
| `button`        | Per-server  | Refresh library button                                                                                     |
| `sensor`        | Per-server  | Library counts (movies, series, episodes, songs, albums, artists), active sessions, version, running tasks |
| `binary_sensor` | Per-server  | Connected, pending restart, update available, library scan active                                          |

### State Mapping

| Condition                | State   |
| ------------------------ | ------- |
| No session               | OFF     |
| Session, nothing playing | IDLE    |
| Playing, paused          | PAUSED  |
| Playing, not paused      | PLAYING |

## Code Style

- Use `from __future__ import annotations`
- Modern union syntax: `str | None` not `Optional[str]`
- Explicit return types on all functions
- Type all class attributes in `__init__`
- Use `_attr_*` pattern for entity attributes
- Never do I/O in properties

## Skills Reference

This project uses specialized skills for consistent, high-quality development. Skills are located in `.claude/skills/` and should be used as specified below.

### Skill Usage Matrix

| Situation                   | Required Skill           | Invocation                    |
| --------------------------- | ------------------------ | ----------------------------- |
| Implementing ANY phase      | `ha-emby-phase-executor` | "Execute phase N"             |
| Writing ANY code            | `ha-emby-tdd`            | Automatic with phase executor |
| Type annotations            | `ha-emby-typing`         | Automatic with phase executor |
| Failed implementation twice | `ha-emby-research`       | Manual trigger                |
| HA integration patterns     | `ha-emby-integration`    | Reference as needed           |
| Media player implementation | `ha-emby-media-player`   | Reference for Phase 3+        |

### Skill Descriptions

#### `ha-emby-phase-executor` (Primary Workflow)

**Use for:** Autonomous execution of roadmap phases.

**Invocation:** `Execute phase N`

**What it does:**

- Checks episodic memory for prior work
- Creates/reviews phase task documentation
- Manages git branches
- Orchestrates TDD implementation (RED-GREEN-REFACTOR)
- Performs code review
- Runs full test suite
- Creates PR when phase complete

**Key behaviors:**

- Works autonomously (no interactive prompts unless blocked)
- Commits at each TDD stage
- ALL issues must be resolved (no "unrelated" issues)
- ALL review recommendations implemented

#### `ha-emby-tdd` (Mandatory for All Code)

**Use for:** Writing any code in this project.

**The Iron Law:** No code without a failing test first.

**Workflow:**

1. **RED** - Write failing test
2. **GREEN** - Write minimal implementation
3. **REFACTOR** - Improve while tests pass

**No exceptions for:**

- "Simple" functions
- "Obvious" implementations
- Config flow steps
- Entity attributes

#### `ha-emby-typing` (Mandatory for All Code)

**Use for:** Type annotations throughout the codebase.

**Rules:**

- NEVER use `Any` (except `**kwargs: Any` for HA overrides)
- Use `TypedDict` for API responses
- Use `dataclasses` for internal models
- Use `Protocol` for interfaces
- Modern syntax: `str | None` not `Optional[str]`

#### `ha-emby-research` (Trigger on Failure)

**Use when:** Implementation fails twice.

**Protocol:**

1. STOP coding immediately
2. Read official documentation
3. Examine working HA core implementations
4. Understand the problem fully
5. Then attempt implementation

#### `ha-emby-integration` (Reference)

**Use for:** Home Assistant integration patterns and best practices.

**Covers:**

- Config flow patterns
- Coordinator usage
- Entity registration
- Service definitions
- Async patterns

#### `ha-emby-media-player` (Reference for Phase 3+)

**Use for:** MediaPlayerEntity implementation specifics.

**Covers:**

- Supported features
- State management
- Playback control
- Media browsing
- Image handling

### Workflow Example

```
User: "Execute phase 1"

Claude:
1. Uses ha-emby-phase-executor skill
2. Checks memory for prior work
3. Reads docs/phase-1-tasks.md
4. Creates branch: phase-1-implementation
5. For each task:
   a. Uses ha-emby-tdd for implementation
   b. Uses ha-emby-typing for type safety
   c. Uses ha-emby-research if stuck
   d. Commits at RED, GREEN, REFACTOR
   e. Code review
   f. Full test suite
6. Creates PR when complete
```

### Documentation

| Document                | Purpose                                 |
| ----------------------- | --------------------------------------- |
| `docs/roadmap.md`       | Overall project phases and milestones   |
| `docs/phase-N-tasks.md` | Detailed tasks for each phase (1-21)    |
| `CLAUDE.md`             | This file - project overview and skills |

## Resources

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [MediaPlayerEntity Docs](https://developers.home-assistant.io/docs/core/entity/media-player/)
- [Config Flow Docs](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/)
- [Emby REST API](https://dev.emby.media/doc/restapi/index.html)
- [pyEmby Library](https://github.com/mezz64/pyEmby)
