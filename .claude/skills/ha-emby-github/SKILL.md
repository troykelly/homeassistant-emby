---
name: ha-emby-github
description: Use for ALL GitHub operations on this project - covers project board queries, issue management, PR linking, commit formatting, and the VIOLATION rule. Required reading before any code changes.
---

# Home Assistant Emby GitHub Operations

## Overview

**All work on this repository MUST be tracked via GitHub Issues and the Project Board.**

This skill covers GitHub CLI operations, project board queries, issue lifecycle management, and the mandatory linking of all code changes to issues.

## The Iron Law

```
NO CODE CHANGES WITHOUT A LINKED GITHUB ISSUE
```

This is a **VIOLATION**. Every commit, every PR, every change must reference an issue.

**Before writing ANY code:**
1. Check if an issue exists for this work
2. If not, create one
3. Link all commits and PRs to the issue

## Project Details

| Item | Value |
|------|-------|
| Project URL | https://github.com/users/troykelly/projects/3 |
| Project Name | Home Assistant Emby Component |
| Repository | troykelly/homeassistant-emby |

## Label Reference

### Type Labels
| Label | Color | Use When |
|-------|-------|----------|
| `bug` | red | Something isn't working |
| `enhancement` | cyan | New feature or improvement |
| `question` | purple | Help or clarification needed |
| `connection` | peach | Setup/connection issues |
| `compatibility` | light blue | HA/HACS/version issues |

### Priority Labels
| Label | Color | Use When |
|-------|-------|----------|
| `priority: critical` | dark red | Integration unusable, affects all |
| `priority: high` | orange | Major functionality broken |
| `priority: medium` | yellow | Important but workaround exists |
| `priority: low` | green | Minor issue or nice-to-have |

### Component Labels
| Label | Description |
|-------|-------------|
| `component: media-player` | Playback, volume, media info |
| `component: remote` | Navigation commands |
| `component: sensor` | Library stats, server info |
| `component: button` | Action buttons |
| `component: config-flow` | Setup, authentication |
| `component: websocket` | Real-time updates |
| `component: api` | Emby server communication |
| `component: media-browse` | Media library browsing |

### Status Labels
| Label | Use When |
|-------|----------|
| `status: investigating` | Actively investigating |
| `status: in-progress` | Implementation started |
| `status: blocked` | Waiting on external factor |
| `status: wontfix` | Will not be addressed |
| `status: duplicate` | Already exists |

### Triage Labels
| Label | Meaning |
|-------|---------|
| `needs-triage` | New, awaiting review |
| `needs-info` | Waiting on reporter |
| `needs-reproduction` | Needs repro steps |
| `confirmed` | Bug reproduced |
| `ai-triaged` | Processed by CI |

### Special Labels
| Label | Use When |
|-------|----------|
| `upstream` | Emby server issue |
| `ha-core` | Home Assistant core issue |
| `breaking-change` | Introduces breaking change |
| `good first issue` | Good for newcomers |

## Common GitHub CLI Operations

### Query Issues

```bash
# List all triaged bugs ready for investigation
gh issue list --label "bug" --label "ai-triaged" --state open -L 20

# List confirmed bugs ready for fixing
gh issue list --label "bug" --label "confirmed" --state open -L 20

# List high-priority items
gh issue list --label "priority: high" --state open -L 20

# List issues in progress
gh issue list --label "status: in-progress" --state open -L 20

# View specific issue with full details
gh issue view 42

# View issue comments
gh issue view 42 --comments

# Search for related issues
gh issue list --search "websocket connection" --state all
```

### Update Issues

```bash
# Add labels
gh issue edit 42 --add-label "confirmed,priority: high"

# Remove labels
gh issue edit 42 --remove-label "needs-triage"

# Add comment
gh issue comment 42 --body "Investigation complete. See analysis below..."

# Assign to self
gh issue edit 42 --add-assignee @me

# Close issue
gh issue close 42 --reason completed
```

### Project Board

```bash
# List project items
gh project item-list 3 --owner troykelly --format json

# Get project field IDs (for status updates)
gh project field-list 3 --owner troykelly
```

### Create Issues

```bash
# Create bug issue
gh issue create \
  --title "Bug: Description" \
  --body "## Description\n\n## Steps to Reproduce\n\n## Expected Behavior\n\n## Actual Behavior" \
  --label "bug,needs-triage"

# Create feature issue
gh issue create \
  --title "Feature: Description" \
  --body "## Description\n\n## Use Case\n\n## Proposed Solution" \
  --label "enhancement,needs-triage"
```

## Branch Naming Convention

```
issue-{number}-{short-description}
```

**Examples:**
- `issue-42-fix-websocket-reconnect`
- `issue-123-add-playlist-service`
- `issue-7-media-player-volume-bug`

**Rules:**
- Always include issue number
- Use lowercase
- Use hyphens, not underscores
- Keep description short (3-5 words)

## Commit Message Format

```
type(scope): description (#issue)
```

**Types:**
| Type | Use For |
|------|---------|
| `feat` | New feature |
| `fix` | Bug fix |
| `test` | Adding/updating tests |
| `refactor` | Code restructuring |
| `docs` | Documentation only |
| `chore` | Maintenance tasks |
| `perf` | Performance improvement |

**Scopes:**
| Scope | Area |
|-------|------|
| `api` | Emby API client |
| `media-player` | Media player entity |
| `config-flow` | Setup/options flow |
| `websocket` | WebSocket client |
| `sensor` | Sensor entities |
| `services` | HA services |
| `browse` | Media browsing |

**Examples:**
```bash
git commit -m "fix(websocket): handle reconnection on server restart (#42)"
git commit -m "feat(services): add playlist creation service (#123)"
git commit -m "test(media-player): add volume control edge cases (#7)"
```

## Pull Request Format

```bash
gh pr create \
  --title "Fix: Websocket reconnection on server restart" \
  --body "$(cat <<'EOF'
## Summary

Brief description of changes.

Fixes #42

## Changes

- Change 1
- Change 2
- Change 3

## Test Plan

- [ ] Unit tests pass
- [ ] Manual testing completed
- [ ] Edge cases verified

## Breaking Changes

None / List any breaking changes

---
🤖 Generated with [Claude Code](https://claude.ai/code)
EOF
)"
```

**Critical:** Always include `Fixes #N` or `Closes #N` in the PR body to auto-close the issue on merge.

## Workflow Integration

### Before Starting Work

```bash
# 1. Check for existing issue
gh issue list --search "your topic"

# 2. If none exists, create one
gh issue create --title "..." --body "..."

# 3. Assign to yourself
gh issue edit {N} --add-assignee @me

# 4. Update status
gh issue edit {N} --add-label "status: in-progress"

# 5. Create branch
git checkout -b issue-{N}-description
```

### During Work

```bash
# Commit with issue reference
git commit -m "type(scope): message (#N)"

# Update issue with progress
gh issue comment {N} --body "Progress update: ..."
```

### After Work Complete

```bash
# Create PR linked to issue
gh pr create --title "..." --body "Fixes #N ..."

# Wait for CI and review
gh pr checks

# After merge, issue auto-closes
```

## Anti-Patterns

### VIOLATION: Code Without Issue

```bash
# WRONG - No issue reference
git commit -m "fix websocket bug"

# CORRECT - Always reference issue
git commit -m "fix(websocket): handle disconnect (#42)"
```

### VIOLATION: PR Without Issue Link

```bash
# WRONG - PR body missing issue link
gh pr create --body "Fixed the thing"

# CORRECT - Always link to issue
gh pr create --body "Fixes #42\n\nFixed the websocket disconnect issue"
```

### VIOLATION: Working Without Checking Project

```bash
# WRONG - Start coding immediately
vim custom_components/embymedia/websocket.py

# CORRECT - Check project first
gh issue list --label "status: in-progress" --assignee @me
gh issue view 42
# Then start coding
```

## The Bottom Line

**Every code change links to an issue. No exceptions.**

1. Issue exists before code
2. Branch named with issue number
3. Commits reference issue number
4. PR links to issue with `Fixes #N`
5. Issue auto-closes on merge
