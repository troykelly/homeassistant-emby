---
name: ha-emby-research
description: Use when ANY code implementation fails twice - STOP coding immediately and research using official docs, source code, or web search. Prevents wasted cycles from guess-and-check coding. Two failures trigger mandatory research.
---

# Home Assistant Emby Research Protocol

## Overview

**Failed twice? STOP coding. Research.**

When code doesn't work after two attempts, continuing to guess wastes time. Switch to research mode: read docs, examine source code, search for examples.

## The Iron Law

```
TWO FAILURES = MANDATORY RESEARCH
```

After the second failure:
1. **STOP** writing code
2. **RESEARCH** the problem
3. **UNDERSTAND** before attempting again

## What Counts as a Failure

- Test fails
- Type check fails
- Runtime error
- Unexpected behavior
- Code doesn't do what you intended

Each distinct attempt to fix counts. Changing one thing and trying again = one attempt.

## Research Protocol

### Step 1: Identify the Problem

Write down explicitly:
- What you expected to happen
- What actually happened
- Error message (exact text)

### Step 2: Check Official Documentation

**Home Assistant Developer Docs:**
- https://developers.home-assistant.io/docs/
- https://developers.home-assistant.io/docs/core/entity/media-player/
- https://developers.home-assistant.io/docs/config_entries_config_flow_handler/

**Emby API Documentation:**
- https://dev.emby.media/doc/restapi/index.html
- https://github.com/MediaBrowser/Emby/wiki/

### Step 3: Examine Working Source Code

**Home Assistant Core Integrations (reference implementations):**
```bash
# Plex media player (similar architecture)
gh browse home-assistant/core -- homeassistant/components/plex/

# Jellyfin (Emby fork, very similar API)
gh browse home-assistant/core -- homeassistant/components/jellyfin/

# Kodi (another media player)
gh browse home-assistant/core -- homeassistant/components/kodi/
```

**Look for:**
- How similar problems are solved
- Patterns for the specific feature
- Test patterns for similar functionality

### Step 4: Search for Examples

```bash
# Search Home Assistant core for pattern
rg "pattern_you_need" ~/ha-core/homeassistant/components/

# Search GitHub for implementations
gh search code "MediaPlayerEntity async_play_media" --language=python

# Web search with specific terms
# "Home Assistant MediaPlayerEntity [specific method] example"
```

### Step 5: Understand Before Coding

Before writing any code:
- Explain the solution in plain English
- Identify what was wrong with previous attempts
- Write out the corrected approach

Only then return to coding.

## Common Research Scenarios

### Config Flow Not Working

**Research targets:**
1. HA dev docs: Config flow handler
2. Source: `homeassistant/components/*/config_flow.py` (pick similar integration)
3. Tests: `tests/components/*/test_config_flow.py`

### Entity State Not Updating

**Research targets:**
1. HA dev docs: Entity documentation
2. Source: How coordinators trigger updates
3. Check: Is `async_write_ha_state()` being called?

### API Authentication Failing

**Research targets:**
1. Emby API docs: Authentication section
2. Source: pyEmby or embyclient library code
3. Test: Use curl/httpie to verify API directly

### Type Errors

**Research targets:**
1. Home Assistant stubs: `homeassistant-stubs` package
2. Source: Base class type definitions
3. Mypy docs: Specific error code

### Test Fixtures Not Working

**Research targets:**
1. pytest-homeassistant-custom-component docs
2. Source: HA core test fixtures in `tests/conftest.py`
3. Examples: Tests in similar integrations

## Tracking Failures

Keep a mental or written count:

```
Attempt 1: Changed X → Still fails
Attempt 2: Changed Y → Still fails
→ STOP. Research required.
```

## Anti-Patterns (Don't Do These)

### Guess-and-Check Loop

```
❌ Try something → Fails → Try variation → Fails → Try another → Fails...
```

This wastes time and context. After 2 failures, research.

### Asking Without Research

```
❌ "What's wrong with this code?"
```

First research, then if still stuck, ask with:
- What you tried
- What you found in research
- Specific question

### Copying Without Understanding

```
❌ Copy code from Stack Overflow → Doesn't work → Copy different answer...
```

Understand WHY the solution works before using it.

## Research Results Format

After researching, document:

```markdown
## Problem
[What wasn't working]

## Root Cause
[Why it wasn't working]

## Solution
[How to fix it, with reference to source]

## Source
[Link to docs/code that explains the solution]
```

## When to Ask for Help

After research, if still stuck:
- You've read relevant docs
- You've examined working examples
- You've tried the documented approach
- You can articulate the specific confusion

Then ask, providing all the above context.

## Red Flags - You're Skipping Research

- "Let me just try one more thing"
- "Maybe if I change this..."
- "I think it should work if..."
- Attempt 3, 4, 5... without reading docs
- Same error appearing repeatedly

## The Bottom Line

**Two failures = research. No exceptions.**

The fastest path to working code is understanding, not guessing.

Stop. Read. Understand. Then code.
