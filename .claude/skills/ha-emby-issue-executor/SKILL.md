---
name: ha-emby-issue-executor
description: Use when implementing fixes or features from GitHub issues - autonomous execution with TDD, memory persistence, code review, and branch management. Works until issue complete or blocked.
---

# Home Assistant Emby Issue Executor

## Overview

**Autonomous implementation of GitHub issues using TDD, with proper branch management and PR linking.**

This skill orchestrates the complete implementation of a bug fix or feature from a GitHub issue, including TDD cycles, code review, and PR creation.

**CRITICAL: Work autonomously. Never go interactive unless you have a specific blocking question.**

## When to Use

- Issue has `confirmed` label (bug ready to fix)
- Issue has `enhancement` label (feature to implement)
- Routed here by `ha-emby-issue-selector`
- User asks to "fix", "implement", or "work on" an issue

## The Autonomous Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                   ISSUE EXECUTOR WORKFLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. CONTEXT RECOVERY ────────────────────────────────────────   │
│     Check memory, read issue, check for existing work          │
│                                                                 │
│  2. BRANCH CREATION ─────────────────────────────────────────   │
│     Create issue-{N}-{description} branch                      │
│                                                                 │
│  3. UPDATE ISSUE STATUS ─────────────────────────────────────   │
│     Add "status: in-progress" label                            │
│                                                                 │
│  4. TDD IMPLEMENTATION ──────────────────────────────────────   │
│     RED → GREEN → REFACTOR (use ha-emby-tdd skill)             │
│                                                                 │
│  5. CODE REVIEW ─────────────────────────────────────────────   │
│     Self-review all changes                                    │
│                                                                 │
│  6. FULL TEST SUITE ─────────────────────────────────────────   │
│     pytest, mypy, ruff - ALL must pass                         │
│                                                                 │
│  7. CREATE PR ───────────────────────────────────────────────   │
│     Link to issue with "Fixes #N"                              │
│                                                                 │
│  8. UPDATE MEMORY ───────────────────────────────────────────   │
│     Record completion for future sessions                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Step 1: Context Recovery

**ALWAYS start here - even if you think you know the context.**

### Check Episodic Memory

Search for prior work on this issue:
- Previous session progress?
- Decisions already made?
- Blockers encountered?

### Read the Issue

```bash
# Get full issue details
gh issue view {N} --json title,body,labels,comments,assignees

# Check for linked PRs
gh pr list --search "#{N}"
```

**Extract from issue:**
- Problem description
- Expected behavior
- Root cause (if from bug-triage)
- Recommended fix approach
- Files to change
- Test cases needed

### Check Git Status

```bash
# Current branch
git branch --show-current

# Any existing work?
git branch -a | grep "issue-{N}"

# Uncommitted changes?
git status
```

**If work already exists:** Resume from last checkpoint.

## Step 2: Branch Creation

```bash
# Ensure on main and up to date
git checkout main
git pull origin main

# Create issue branch
git checkout -b issue-{N}-{short-description}
```

**Branch naming:**
- `issue-42-websocket-reconnect`
- `issue-123-playlist-service`
- `issue-7-volume-bug`

## Step 3: Update Issue Status

```bash
# Add in-progress status
gh issue edit {N} --add-label "status: in-progress"

# Remove investigating if present
gh issue edit {N} --remove-label "status: investigating"

# Comment that work is starting
gh issue comment {N} --body "Starting implementation."
```

## Step 4: TDD Implementation

**Use `ha-emby-tdd` skill. No exceptions.**

### RED - Write Failing Test

```python
# tests/test_file.py
async def test_feature_behavior(
    hass: HomeAssistant,
    mock_emby_client: MagicMock,
) -> None:
    """Test description matching issue requirement."""
    # Arrange
    ...
    # Act
    result = await feature()
    # Assert
    assert result == expected
```

```bash
# Run test - MUST FAIL
pytest tests/test_file.py::test_feature_behavior -v
```

**Commit:**
```bash
git add tests/
git commit -m "test(scope): RED - add failing test for feature (#N)

- Test: test_feature_behavior
- Expected: [what test expects]
- Status: Failing (TDD RED phase)"
```

### GREEN - Write Implementation

Write **minimal** code to pass the test:

```python
# custom_components/embymedia/file.py
async def feature() -> Result:
    """Implementation."""
    return Result(...)
```

```bash
# Run test - MUST PASS
pytest tests/test_file.py::test_feature_behavior -v
```

**Commit:**
```bash
git add .
git commit -m "feat(scope): GREEN - implement feature (#N)

- Implementation: [brief description]
- Test: test_feature_behavior now passing"
```

### REFACTOR - Improve Code

Only refactor while tests pass. Keep them passing.

```bash
# Verify tests still pass
pytest tests/ -v
```

**Commit (if changes made):**
```bash
git add .
git commit -m "refactor(scope): improve implementation (#N)

- Changes: [what was improved]
- Tests: All passing"
```

### Repeat for Each Requirement

Multiple features? Multiple TDD cycles:
- RED → GREEN → REFACTOR for requirement 1
- RED → GREEN → REFACTOR for requirement 2
- ...

## Step 5: Code Review

### Self-Review Checklist

| Category | Check |
|----------|-------|
| **Types** | No `Any` (except required HA overrides) |
| **Docstrings** | Google-style on all public functions |
| **Error handling** | All exceptions caught and handled |
| **Logging** | Appropriate levels, no sensitive data |
| **Security** | No injection vulnerabilities |
| **Performance** | No obvious inefficiencies |
| **Style** | Passes ruff, follows conventions |

### Test Review Checklist

| Category | Check |
|----------|-------|
| **Coverage** | All code paths tested |
| **Assertions** | Meaningful, specific assertions |
| **Mocking** | Appropriate use, not over-mocked |
| **Edge cases** | Error conditions, boundaries |
| **Naming** | Descriptive test names |

**Implement ALL recommendations immediately.**

## Step 6: Full Test Suite

```bash
# Run complete test suite
pytest tests/ --cov=custom_components.embymedia --cov-report=term-missing --cov-fail-under=100

# Run type checking
mypy custom_components/embymedia/

# Run linting
ruff check custom_components/embymedia/ tests/
ruff format --check custom_components/embymedia/ tests/
```

**ALL tests must pass. ALL issues must be resolved.**

There is NO SUCH THING as an "unrelated" issue. If it's failing, fix it.

### If Tests Fail

1. Diagnose failure (use `ha-emby-research` skill if stuck after 2 attempts)
2. Fix the issue
3. Repeat code review for the fix
4. Re-run full test suite
5. Loop until all green

## Step 7: Create Pull Request

```bash
# Push branch
git push -u origin issue-{N}-{description}

# Create PR with issue link
gh pr create \
  --title "Fix: Brief description of fix" \
  --body "$(cat <<'EOF'
## Summary

Brief description of what this PR does.

Fixes #N

## Changes

- Change 1
- Change 2
- Change 3

## Test Plan

- [x] Unit tests added/updated
- [x] All tests passing
- [x] Manual testing completed (if applicable)

## Breaking Changes

None / List any breaking changes

---
🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

**Critical:** The `Fixes #N` line auto-closes the issue when PR merges.

## Step 8: Update Memory

Record for future sessions:
- Issue completed
- Approach taken
- Any decisions made
- Any issues encountered

## Commit Message Format

```
type(scope): description (#issue)

- Detail 1
- Detail 2

[optional body]
```

**Types:** `feat`, `fix`, `test`, `refactor`, `docs`, `chore`, `perf`

**Scopes:** `api`, `media-player`, `config-flow`, `websocket`, `sensor`, `services`, `browse`

**Examples:**
```
fix(websocket): handle reconnection on server restart (#42)

- Add session ID refresh on coordinator update
- Clear stale session references
- Add reconnection test

test(media-player): add volume control edge cases (#7)

- Test volume at 0%, 100%
- Test mute/unmute cycle
- Test invalid volume values
```

## Skills to Use

| Situation | Skill |
|-----------|-------|
| Writing ANY code | `ha-emby-tdd` |
| Type annotations | `ha-emby-typing` |
| Failed twice | `ha-emby-research` |
| HA patterns | `ha-emby-integration` |
| Media player | `ha-emby-media-player` |
| GitHub operations | `ha-emby-github` |

## Red Flags - STOP and Reassess

If you encounter any of these, pause and think:

- About to write code without a test → Use TDD
- Test passes on first run → Test is wrong
- Tempted to skip review → Review is mandatory
- "This is unrelated" → No such thing, fix it
- About to ask user a question → Is it truly blocking?
- Skipping a recommendation → ALL recommendations implemented
- No issue number in commit → VIOLATION

## Handling Blockers

If truly blocked:

```bash
# Update issue with blocker
gh issue comment {N} --body "Blocked: [description of blocker]"
gh issue edit {N} --add-label "status: blocked"

# Remove in-progress
gh issue edit {N} --remove-label "status: in-progress"
```

Then either:
- Ask user for guidance
- Switch to different issue

## The Bottom Line

**Work autonomously until blocked or issue complete.**

1. Check memory first
2. Read issue thoroughly
3. Create branch with issue number
4. TDD always - RED → GREEN → REFACTOR
5. Commit with issue reference (#N)
6. Review everything
7. Fix ALL issues
8. Create PR with `Fixes #N`
9. Update memory

No shortcuts. No skipping steps. No "I'll do it later."
