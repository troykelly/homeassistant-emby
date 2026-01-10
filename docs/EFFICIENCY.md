# Efficiency Best Practices

This document explains the efficiency architecture of the Emby Media integration and provides guidelines for contributors and users.

---

## Overview

The Emby Media integration is designed with efficiency as a core principle. It minimizes API calls to the Emby server through several strategies:

1. **WebSocket-first architecture** - Real-time updates without polling
2. **Multi-layer caching** - Reduce redundant API requests
3. **Request coalescing** - Deduplicate concurrent identical requests
4. **Adaptive polling** - Adjust intervals based on connection state
5. **Batch operations** - Consolidate multiple API calls

---

## Architecture

### Communication Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Home Assistant                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │ Session         │    │ Library         │    │ Discovery       │  │
│  │ Coordinator     │    │ Coordinator     │    │ Coordinator     │  │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘  │
│           │                      │                      │           │
│           ▼                      ▼                      ▼           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                       EmbyClient                             │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │    │
│  │  │ Browse      │  │ Request     │  │ Metrics             │  │    │
│  │  │ Cache       │  │ Coalescing  │  │ Collector           │  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────┘    │
│           │                                                         │
│           ▼                                                         │
│  ┌─────────────────┐                    ┌─────────────────────┐    │
│  │ HTTP API        │◄──────────────────►│ WebSocket           │    │
│  │ (REST)          │                    │ (Real-time)         │    │
│  └────────┬────────┘                    └──────────┬──────────┘    │
│           │                                        │                │
└───────────┼────────────────────────────────────────┼────────────────┘
            │                                        │
            ▼                                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Emby Server                                  │
└─────────────────────────────────────────────────────────────────────┘
```

### WebSocket-First Architecture

When WebSocket is enabled (default and recommended):

1. Session updates come via WebSocket subscription
2. Polling interval increases from 10s to 60s (fallback only)
3. Library changes trigger events instead of hourly polling
4. Reconnection is automatic with exponential backoff

**When WebSocket is unavailable:**
- Falls back to HTTP polling
- Uses configured scan interval (default 10s)
- Session updates are less responsive

### Polling Intervals

| Coordinator | Default | Configurable | With WebSocket |
|-------------|---------|--------------|----------------|
| Session | 10s | Yes (5-300s) | Extended to 60s |
| Library | 1 hour | Yes (1-24h) | On-demand via events |
| Server | 5 min | Yes (5m-1h) | N/A (always polls) |
| Discovery | 30 min | No | N/A |

---

## Caching Layers

### 1. Browse Cache

**Purpose:** Cache expensive media browsing API calls

| Property | Value |
|----------|-------|
| TTL | 5 minutes |
| Max Entries | 500 |
| Eviction | LRU (Least Recently Used) |

**Cached Operations:**
- Library item listings
- Genre/year/studio filters
- Media details

**Invalidation:**
- Manual refresh via UI
- LibraryChanged WebSocket event
- TTL expiration

### 2. Discovery Cache

**Purpose:** Cache user-specific library discovery data

| Property | Value |
|----------|-------|
| TTL | 30 minutes |
| Scope | Per user |

**Cached Operations:**
- Latest media items
- Resume points
- Favorites counts
- Library statistics

### 3. Request Coalescing

**Purpose:** Deduplicate concurrent identical requests

When multiple components request the same API call simultaneously (e.g., at startup), only one actual request is made and the result is shared.

**How it works:**
```python
# Without coalescing: 5 concurrent calls = 5 API requests
# With coalescing: 5 concurrent calls = 1 API request, 5 responses
```

---

## Configuration Options

### Polling Intervals (Options Flow)

Access via: **Settings** → **Devices & Services** → **Emby Media** → **Configure**

| Option | Default | Range | Impact |
|--------|---------|-------|--------|
| Scan Interval | 10s | 5-300s | Session update frequency |
| Library Scan Interval | 1h | 1-24h | Library count updates |
| Server Scan Interval | 5m | 5m-1h | Server status checks |

### Recommendations

**For typical use:**
- Keep defaults
- Enable WebSocket (reduces polling automatically)

**For low-power servers:**
```
Library Scan: 24h
Server Scan: 1h
WebSocket: Enabled
```

**For maximum responsiveness:**
```
Scan Interval: 5s
Library Scan: 1h
WebSocket: Enabled
```

---

## Diagnostics

The integration exposes efficiency metrics in the diagnostics download:

1. Go to **Settings** → **Devices & Services**
2. Click **Emby Media**
3. Click ⋮ (three dots) → **Download diagnostics**

### Metrics Available

```json
{
  "efficiency_metrics": {
    "api_calls": {
      "/Sessions": {"count": 1543, "avg_ms": 145, "errors": 2}
    },
    "websocket": {
      "messages_received": 4521,
      "uptime_hours": 168,
      "reconnections": 3
    },
    "coordinators": {
      "session": {"updates": 1543, "failures": 2, "avg_duration_ms": 180}
    }
  }
}
```

Use this to:
- Verify WebSocket is working (messages_received should increase)
- Check API call frequency
- Identify slow endpoints
- Diagnose performance issues

---

## Contributor Guidelines

### Adding New API Endpoints

1. **Evaluate caching needs**
   - Is data static or dynamic?
   - How often will it be called?
   - Can results be shared across users?

2. **Use request coalescing for high-frequency calls**
   - Session endpoints
   - Library browsing
   - Any endpoint called during startup

3. **Prefer WebSocket events over polling**
   - Check Emby's supported message types
   - Implement event handlers where available

4. **Add metrics instrumentation**
   - All new `_request*` methods should be timed
   - Record errors for diagnosis

### Code Example: Adding a Cached Endpoint

```python
async def async_get_my_data(self, user_id: str) -> dict:
    """Get data with caching and coalescing."""
    cache_key = f"my_data_{user_id}"

    # Check cache first
    cached = self._browse_cache.get(cache_key)
    if cached is not None:
        return cached

    # Use coalescing for the actual request
    async with self._request_lock:
        # Double-check after acquiring lock
        cached = self._browse_cache.get(cache_key)
        if cached is not None:
            return cached

        result = await self._request("GET", f"/MyEndpoint/{user_id}")
        self._browse_cache.set(cache_key, result)
        return result
```

### Coordinator Best Practices

1. **Set `always_update=False`** - Only update entities when data changes
2. **Add `PARALLEL_UPDATES`** - Control concurrent entity updates
3. **Batch related API calls** - Use `asyncio.gather()` for parallel requests
4. **Track metrics** - Call `metrics.record_coordinator_update()`

---

## Troubleshooting High API Usage

### Symptoms
- Emby server becoming sluggish
- High CPU usage on server
- Network congestion

### Diagnosis Steps

1. **Download diagnostics** (see above)
2. **Check api_calls counts** - Identify most-called endpoints
3. **Verify WebSocket is active** - messages_received should be non-zero
4. **Check for errors** - High error rates cause retries

### Common Causes

| Cause | Solution |
|-------|----------|
| WebSocket disabled | Enable WebSocket in options |
| Very short scan interval | Increase to 30s or higher |
| Many ignored devices | Consider filtering earlier |
| Multiple integrations | Use single integration per server |

### Quick Fixes

1. **Increase polling intervals** via Options
2. **Enable WebSocket** if disabled
3. **Check for integration loops** in automations
4. **Restart integration** to reset caches

---

## Memory Management

### Bounded Caches

All caches have size limits to prevent memory leaks:

| Cache | Max Entries |
|-------|-------------|
| Browse | 500 items |
| Discovery | Per user, refreshed on interval |

### Cleanup

- Stale cache entries are evicted on TTL expiration
- Request coalescing clears completed futures immediately
- Session coordinators clean up removed sessions

### Monitoring

Check memory usage in diagnostics:
```json
{
  "cache_stats": {
    "hits": 456,
    "misses": 78,
    "entries": 234
  }
}
```

If `entries` approaches 500, consider:
- Increasing TTL (fewer cache misses = slower growth)
- Reducing library browsing frequency

---

## See Also

- **[Configuration](CONFIGURATION.md)** - Detailed configuration options
- **[Troubleshooting](TROUBLESHOOTING.md)** - General problem solving
- **[CLAUDE.md](../CLAUDE.md)** - Development guidelines
