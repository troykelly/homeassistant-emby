---
name: ha-emby-typing
description: Use when writing ANY Python code for the HA Emby integration - enforces strict typing with ZERO Any usage, proper type annotations for all functions, TypedDicts for data structures, and mypy strict compliance.
---

# Home Assistant Emby Strict Typing

## Overview

**NEVER use `Any`. Every type must be explicit and correct.**

This integration follows Home Assistant's strict typing requirements. All code must pass mypy with `--strict` and be added to `.strict-typing`.

## The Iron Law

```
NO Any TYPE. EVER.
```

**Exceptions for `Any`:**
- None

**Not even for:**
- "Complex nested data"
- "Third-party library returns Any"
- "It's just kwargs"
- "The type is too complicated"

If you think you need `Any`, you need a TypedDict, Protocol, or Generic instead.

## Type Annotation Requirements

### Every Function Must Be Fully Typed

```python
# WRONG - Missing types
def process_media(data):
    return data["title"]

# WRONG - Uses Any
def process_media(data: Any) -> Any:
    return data["title"]

# CORRECT - Explicit types
def process_media(data: MediaItem) -> str:
    return data.title
```

### All Class Attributes Must Be Typed

```python
# WRONG - No type annotations
class EmbyMediaPlayer:
    def __init__(self, client, device):
        self._client = client
        self._device = device
        self._state = None

# CORRECT - All types explicit
class EmbyMediaPlayer(MediaPlayerEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        client: EmbyClient,
        device: EmbyDevice,
    ) -> None:
        self._client: EmbyClient = client
        self._device: EmbyDevice = device
        self._state: MediaPlayerState | None = None
```

## TypedDict for API Responses

When Emby API returns JSON dictionaries, define TypedDicts:

```python
from typing import TypedDict, NotRequired

class EmbySessionInfo(TypedDict):
    """Type for Emby session information."""
    Id: str
    DeviceId: str
    DeviceName: str
    UserName: str
    NowPlayingItem: NotRequired[EmbyNowPlayingItem]
    PlayState: NotRequired[EmbyPlayState]


class EmbyNowPlayingItem(TypedDict):
    """Type for currently playing item."""
    Id: str
    Name: str
    Type: str
    RunTimeTicks: int
    MediaType: str


class EmbyPlayState(TypedDict):
    """Type for playback state."""
    PositionTicks: int
    IsPaused: bool
    IsMuted: bool
    VolumeLevel: int
```

## Dataclasses for Internal Models

Convert API responses to typed dataclasses:

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class PlaybackState:
    """Internal representation of playback state."""
    position: timedelta
    is_paused: bool
    is_muted: bool
    volume_level: float  # 0.0 to 1.0

    @classmethod
    def from_api(cls, data: EmbyPlayState) -> PlaybackState:
        """Create from API response."""
        return cls(
            position=timedelta(microseconds=data["PositionTicks"] // 10),
            is_paused=data["IsPaused"],
            is_muted=data["IsMuted"],
            volume_level=data["VolumeLevel"] / 100,
        )
```

## Custom ConfigEntry Type

**Required** for runtime data:

```python
from homeassistant.config_entries import ConfigEntry

from .coordinator import EmbyDataUpdateCoordinator

type EmbyConfigEntry = ConfigEntry[EmbyDataUpdateCoordinator]
```

Use throughout the integration:

```python
async def async_setup_entry(
    hass: HomeAssistant,
    entry: EmbyConfigEntry,
) -> bool:
    """Set up Emby from a config entry."""
    coordinator = EmbyDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    # ...
```

## Handling Optional Values

Use `| None` syntax (not `Optional`):

```python
# WRONG - Old style
from typing import Optional
def get_title(self) -> Optional[str]:
    return self._title

# CORRECT - Modern union syntax
def get_title(self) -> str | None:
    return self._title
```

## Generic Types

Use generics for containers:

```python
# WRONG - Bare list/dict
def get_sessions() -> list:
    ...

def get_metadata() -> dict:
    ...

# CORRECT - Typed containers
def get_sessions() -> list[EmbySession]:
    ...

def get_metadata() -> dict[str, str]:
    ...
```

## Callback and Callable Types

```python
from collections.abc import Callable, Awaitable

# Sync callback
StateCallback = Callable[[MediaPlayerState], None]

# Async callback
AsyncStateCallback = Callable[[MediaPlayerState], Awaitable[None]]

# With optional args
UpdateCallback = Callable[[str, dict[str, str] | None], None]
```

## Protocol for Duck Typing

When you need interface-like behavior:

```python
from typing import Protocol

class SupportsPlayback(Protocol):
    """Protocol for objects that support playback."""

    async def async_play(self) -> None: ...
    async def async_pause(self) -> None: ...
    async def async_stop(self) -> None: ...


def control_playback(player: SupportsPlayback) -> None:
    """Control any object supporting playback."""
    ...
```

## Kwargs Handling

For methods requiring `**kwargs` (like HA interfaces):

```python
from typing import Unpack

class PlayMediaKwargs(TypedDict, total=False):
    """Kwargs for play_media."""
    extra_data: dict[str, str]
    thumb: str


async def async_play_media(
    self,
    media_type: MediaType,
    media_id: str,
    enqueue: MediaPlayerEnqueue | None = None,
    announce: bool | None = None,
    **kwargs: Unpack[PlayMediaKwargs],
) -> None:
    """Play media."""
    # Access typed kwargs
    extra = kwargs.get("extra_data", {})
```

If true Any kwargs are required by parent interface, use explicit comment:

```python
async def async_play_media(
    self,
    media_type: MediaType,
    media_id: str,
    enqueue: MediaPlayerEnqueue | None = None,
    announce: bool | None = None,
    **kwargs: Any,  # Required by MediaPlayerEntity interface
) -> None:
```

This is the **only** acceptable use of Any - when overriding a base class method that requires it.

## Mypy Configuration

In `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_unreachable = true
enable_error_code = [
    "ignore-without-code",
    "redundant-cast",
    "truthy-bool",
]

[[tool.mypy.overrides]]
module = "embypy.*"
ignore_missing_imports = true
```

## Common Type Errors and Fixes

### "has no attribute" on Union

```python
# ERROR: Item "None" has no attribute "title"
def get_title(item: MediaItem | None) -> str:
    return item.title  # Error!

# FIX: Guard the None case
def get_title(item: MediaItem | None) -> str | None:
    if item is None:
        return None
    return item.title
```

### "Incompatible return type"

```python
# ERROR: list[str] vs list[Any]
def get_sources(self) -> list[str]:
    return self._sources  # Error if _sources is list[Any]

# FIX: Type the attribute properly
self._sources: list[str] = []
```

### External Library Returns Any

```python
# BAD: Let Any propagate
result = external_lib.get_data()  # Returns Any
self._data = result  # Now _data is Any

# GOOD: Parse into typed structure immediately
raw = external_lib.get_data()
self._data = parse_to_typed(raw)  # Returns TypedDict or dataclass
```

## Red Flags - Type Violations

Stop and fix if you see ANY of these:

- `Any` in a type annotation
- `# type: ignore` without error code
- Untyped function or method
- `cast()` to bypass type checking
- `dict` or `list` without type parameters
- Variables without type annotations in class `__init__`

## The Bottom Line

**Every type explicit. Zero Any. Mypy strict passes.**

If the type is hard to express, that's a sign to create proper TypedDicts, dataclasses, or Protocols.

No shortcuts. No Any. No excuses.
