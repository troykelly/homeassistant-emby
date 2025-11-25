---
name: ha-emby-phase-executor
description: Use when implementing ANY phase of the Home Assistant Emby integration - autonomous execution of phase tasks with TDD, memory persistence, code review, and branch management. Invoke with phase number (e.g., "execute phase 1"). Works autonomously until phase complete or blocked.
---

# Phase Executor - Autonomous Development Workflow

## Overview

**Autonomous execution of roadmap phases for the HA Emby integration.**

This skill orchestrates the complete implementation of a development phase, including:
- Memory persistence across sessions
- Branch management
- Task documentation generation and review
- TDD implementation (RED-GREEN-REFACTOR)
- Code review
- Test suite execution
- PR creation

**CRITICAL: Work autonomously. Never go interactive unless you have a specific blocking question.**

## Invocation

```
Execute phase N
```

Where N is the phase number from `docs/roadmap.md`.

## The Autonomous Workflow

### Phase 0: Context Recovery

**ALWAYS start here - even if you think you know the context.**

```
1. Search episodic memory for:
   - Current phase progress
   - Current task/subtask
   - Branch name
   - Any blockers or notes
   - Previous session decisions

2. Check git status:
   - Current branch
   - Uncommitted changes
   - Recent commits

3. Read phase documentation:
   - docs/roadmap.md (for phase overview)
   - docs/phase-N-tasks.md (for detailed tasks)
```

**If memory shows work in progress:** Resume from last checkpoint.
**If no prior work:** Start fresh with Phase 1.

### Phase 1: Documentation Preparation

#### 1.1 Check Phase Task Documentation

```bash
# Check if phase tasks exist
cat docs/phase-N-tasks.md
```

**If documentation exists:** Proceed to Phase 2.
**If documentation missing:** Generate it.

#### 1.2 Generate Phase Task Documentation (if needed)

```
1. Read docs/roadmap.md for phase overview
2. Generate detailed task document following phase-1-tasks.md format:
   - Task overview
   - Subtasks with acceptance criteria
   - Code examples
   - Test requirements
   - Dependencies

3. Perform review for errors, omissions, blindspots
4. Implement ALL recommendations (no exceptions)
5. Save to docs/phase-N-tasks.md
```

#### 1.3 Create Working Branch

```bash
# Only if no branch exists for this phase
git checkout -b phase-N-implementation
```

**Branch naming:** `phase-N-implementation` or `phase-N-task-M` for large phases.

### Phase 2: Memory Update - Intent

**Before starting any work, record intent:**

```
Update episodic memory with:
- Phase number
- Task/subtask being worked on
- Current status: "Starting"
- Branch name
- Timestamp
```

### Phase 3: Task Review and Breakdown

#### 3.1 Assess Task Complexity

Read the task documentation and evaluate:

| Complexity | Criteria | Action |
|------------|----------|--------|
| Simple | Single function, <50 lines | Proceed directly |
| Medium | Multiple functions, <200 lines | Consider subtasks |
| Complex | Multiple files, >200 lines | Must break down |

#### 3.2 Break Down Complex Tasks

If task is complex:

```
1. Identify logical subtasks (each should be independently testable)
2. Add subtasks to documentation with:
   - Clear scope
   - Acceptance criteria
   - Test requirements
3. Review subtasks for errors/omissions/blindspots
4. Implement ALL review recommendations
5. Update docs/phase-N-tasks.md
6. Restart workflow with first subtask
```

### Phase 4: TDD Implementation

**Use ha-emby-tdd skill. No exceptions.**

#### 4.1 RED - Write Failing Test

```python
# Write test FIRST
async def test_feature_does_something() -> None:
    """Test description."""
    # Arrange
    ...
    # Act
    result = await feature()
    # Assert
    assert result == expected
```

```bash
# Run test - MUST FAIL
pytest tests/test_file.py::test_feature_does_something -v
```

**Update memory:** Status = "RED - Test written, failing as expected"

**Commit:**
```bash
git add tests/
git commit -m "test(phase-N): RED - add failing test for feature

- Test: test_feature_does_something
- Expected: [what test expects]
- Status: Failing (TDD RED phase)"
```

#### 4.2 GREEN - Write Implementation

```python
# Write MINIMAL code to pass test
def feature() -> Result:
    """Implementation."""
    return Result(...)
```

```bash
# Run test - MUST PASS
pytest tests/test_file.py::test_feature_does_something -v
```

**Update memory:** Status = "GREEN - Test passing"

**Commit:**
```bash
git add .
git commit -m "feat(phase-N): GREEN - implement feature

- Implementation: [brief description]
- Test: test_feature_does_something now passing"
```

#### 4.3 REFACTOR - Improve Code

Only refactor while tests pass. Keep them passing.

```bash
# Verify tests still pass after refactoring
pytest tests/ -v
```

**Update memory:** Status = "REFACTOR - Code improved, tests passing"

**Commit (if changes made):**
```bash
git add .
git commit -m "refactor(phase-N): improve feature implementation

- Changes: [what was improved]
- Tests: All passing"
```

### Phase 5: Code Review

#### 5.1 Self-Review New Code

Review ALL new code for:

| Category | Check |
|----------|-------|
| Types | No `Any` (except required HA overrides) |
| Docstrings | Google-style on all public functions |
| Error handling | All exceptions caught and handled |
| Logging | Appropriate levels, no sensitive data |
| Security | No injection vulnerabilities |
| Performance | No obvious inefficiencies |
| Style | Passes ruff, follows conventions |

**Implement ALL recommendations immediately.**

#### 5.2 Test Review

Review ALL new tests for:

| Category | Check |
|----------|-------|
| Coverage | All code paths tested |
| Assertions | Meaningful, specific assertions |
| Mocking | Appropriate use, not over-mocked |
| Edge cases | Error conditions, boundaries |
| Naming | Descriptive test names |

**Implement ALL recommendations immediately.**

#### 5.3 Broader Impact Review (Major Changes)

If change affects multiple files or core architecture:

```
1. Identify all impacted code
2. Review integration points
3. Check for breaking changes
4. Verify backward compatibility
5. Update dependent tests
```

### Phase 6: Full Test Suite

```bash
# Run complete test suite
pytest tests/ --cov=custom_components.emby --cov-report=term-missing --cov-fail-under=100

# Run type checking
mypy custom_components/emby/

# Run linting
ruff check custom_components/emby/ tests/
```

**ALL tests must pass. ALL issues must be resolved.**

There is NO SUCH THING as an "unrelated" issue. If it's failing, fix it.

#### 6.1 If Tests Fail

```
1. Diagnose failure (use ha-emby-research skill if stuck)
2. Fix the issue
3. Repeat code review for the fix
4. Re-run full test suite
5. Loop until all green
```

### Phase 7: Documentation and Memory Update

#### 7.1 Update Documentation

```
1. Mark completed tasks in docs/phase-N-tasks.md
2. Add any notes or learnings
3. Update acceptance criteria checkboxes
```

#### 7.2 Update Memory

```
Update episodic memory with:
- Task completed
- Any issues encountered
- Decisions made
- Next task to work on
```

### Phase 8: Commit and Continue

```bash
git add .
git commit -m "docs(phase-N): update task progress

- Completed: [task name]
- Status: [next task or phase complete]"
```

### Phase 9: Next Step Decision

```
IF subtasks remain:
    → Go to next subtask (restart at Phase 4)

ELSE IF tasks remain:
    → Go to next task (restart at Phase 3)

ELSE IF phase complete:
    → Create PR (Phase 10)
```

### Phase 10: Create Pull Request

```bash
# Push branch
git push -u origin phase-N-implementation

# Create PR
gh pr create \
  --title "Phase N: [Phase Name]" \
  --body "## Summary
- [Key changes]

## Tasks Completed
- [x] Task 1.1
- [x] Task 1.2
...

## Test Coverage
- 100% coverage achieved
- All tests passing

## Breaking Changes
- None / [List any]

---
🤖 Generated with [Claude Code](https://claude.ai/code)"
```

**Update memory:** Status = "PR created, awaiting approval"

**STOP and await PR approval.**

## Memory Schema

Use consistent structure for episodic memory:

```yaml
phase_executor:
  phase: N
  status: "in_progress" | "blocked" | "pr_pending" | "complete"
  branch: "phase-N-implementation"
  current_task: "1.2.3"
  current_subtask: "1.2.3.a" | null
  tdd_stage: "red" | "green" | "refactor" | null
  last_commit: "abc123"
  notes:
    - "Decision: Used approach X because..."
    - "Issue: Had to fix Y"
  blockers: [] | ["Waiting for PR approval"]
```

## Skills to Use

| Situation | Skill |
|-----------|-------|
| Writing ANY code | ha-emby-tdd |
| Type annotations | ha-emby-typing |
| Failed twice | ha-emby-research |
| HA patterns | ha-emby-integration |
| Media player | ha-emby-media-player |

## Red Flags - STOP and Reassess

If you encounter any of these, pause and think:

- About to write code without a test → Use TDD
- Test passes on first run → Test is wrong
- Tempted to skip review → Review is mandatory
- "This is unrelated" → No such thing, fix it
- About to ask user a question → Is it truly blocking?
- Skipping a recommendation → ALL recommendations implemented

## Commit Message Format

```
type(scope): description

- Detail 1
- Detail 2

[optional body]
```

Types: `feat`, `fix`, `test`, `refactor`, `docs`, `chore`
Scope: `phase-N`, `api`, `config-flow`, `media-player`, etc.

## The Bottom Line

**Work autonomously until blocked or phase complete.**

- Check memory first
- Document everything
- TDD always
- Review everything
- Fix ALL issues
- Commit frequently
- Update memory constantly

No shortcuts. No skipping steps. No "I'll do it later."
