# Phase 10: Testing, CI/CD & HACS Compliance

## Overview

This phase ensures the integration is production-ready with comprehensive CI/CD pipelines, HACS compatibility, and quality assurance. Based on November 2025 best practices.

**Goals:**
- 100% test coverage with comprehensive test suite
- CI/CD pipeline with all required checks
- HACS default repository compliance
- Home Assistant brands integration
- Pre-commit hooks for code quality
- Type safety and linting compliance

## Dependencies

- Phases 1-9 complete
- GitHub repository with Actions enabled
- HACS validation requirements knowledge

---

## Task 10.1: GitHub Actions CI Pipeline

### 10.1.1 Core Test Workflow

**File:** `.github/workflows/test.yml`

Current workflow includes:
- ✅ Python 3.13 testing
- ✅ Ruff linting
- ✅ Mypy type checking
- ✅ Pytest with 100% coverage requirement
- ✅ Codecov upload

**Enhancements needed:**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: "0 0 * * *"  # Daily validation

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.13"]  # HA 2025.x requires Python 3.13+
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

      - name: Run ruff check
        run: ruff check custom_components/embymedia tests

      - name: Run ruff format check
        run: ruff format --check custom_components/embymedia tests

      - name: Run mypy
        run: mypy custom_components/embymedia

      - name: Run tests
        run: pytest tests/ --cov=custom_components.embymedia --cov-report=xml --cov-fail-under=100

      - name: Upload coverage
        uses: codecov/codecov-action@v5
        with:
          files: ./coverage.xml
          fail_ci_if_error: false
          token: ${{ secrets.CODECOV_TOKEN }}
```

**Acceptance Criteria:**
- [ ] Test Python 3.13 (HA 2025.x minimum)
- [ ] Ruff format check added
- [ ] Daily scheduled runs for validation
- [ ] Updated to codecov-action@v5

**Test Cases:**
- [ ] `test_ci_workflow_runs_on_pr`
- [ ] `test_ci_workflow_runs_on_push`

### 10.1.2 HACS Validation Workflow

**File:** `.github/workflows/hacs.yml` (new)

```yaml
name: HACS Validation

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: "0 0 * * *"

jobs:
  hacs:
    name: HACS Action
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: HACS Action
        uses: hacs/action@main
        with:
          category: integration
```

**Acceptance Criteria:**
- [ ] HACS action validates repository structure
- [ ] Action runs on every PR and push
- [ ] Daily scheduled validation

**Reference:** [HACS Action Documentation](https://www.hacs.xyz/docs/publish/action/)

### 10.1.3 Hassfest Validation Workflow

**File:** `.github/workflows/hassfest.yml` (new)

```yaml
name: Validate with hassfest

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: "0 0 * * *"

jobs:
  validate:
    name: Hassfest
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Hassfest
        uses: home-assistant/actions/hassfest@master
```

**Acceptance Criteria:**
- [ ] Hassfest validates manifest.json
- [ ] Validates integration structure
- [ ] Validates services.yaml if present

**Reference:** [Hassfest for Custom Components](https://developers.home-assistant.io/blog/2020/04/16/hassfest/)

### 10.1.4 Release Workflow

**File:** `.github/workflows/release.yml` (new)

```yaml
name: Release

on:
  release:
    types: [published]

jobs:
  release:
    name: Prepare release
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Update version in manifest
        run: |
          VERSION="${{ github.event.release.tag_name }}"
          VERSION="${VERSION#v}"  # Remove 'v' prefix if present
          jq --arg v "$VERSION" '.version = $v' \
            custom_components/embymedia/manifest.json > tmp.json
          mv tmp.json custom_components/embymedia/manifest.json

      - name: Create release zip
        run: |
          cd custom_components
          zip -r ../embymedia.zip embymedia

      - name: Upload release asset
        uses: softprops/action-gh-release@v2
        with:
          files: embymedia.zip
```

**Acceptance Criteria:**
- [ ] Version updated from release tag
- [ ] Zip file created for HACS
- [ ] Asset uploaded to GitHub release

---

## Task 10.2: HACS Default Repository Requirements

### 10.2.1 Repository Requirements

**Required for HACS default inclusion:**

1. **Public GitHub repository** ✅
2. **Repository description** - Clear, concise description
3. **At least one release** - Full GitHub release (not just tag)
4. **HACS action passing** - `.github/workflows/hacs.yml`
5. **Hassfest action passing** - `.github/workflows/hassfest.yml`
6. **home-assistant/brands entry** - Logo and icon submission

**Acceptance Criteria:**
- [ ] Repository has clear description
- [ ] At least one published release
- [ ] Both HACS and hassfest actions passing

**Reference:** [HACS Include Default Repositories](https://www.hacs.xyz/docs/publish/include/)

### 10.2.2 hacs.json Configuration

**File:** `hacs.json`

Current configuration:
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

**Required updates:**

```json
{
  "name": "Emby Media",
  "content_in_root": false,
  "render_readme": true,
  "homeassistant": "2024.4.0",
  "zip_release": true
}
```

**Key properties:**
| Property | Value | Description |
|----------|-------|-------------|
| `name` | `"Emby Media"` | Display name in HACS |
| `content_in_root` | `false` | Files in custom_components/ |
| `render_readme` | `true` | Show README in HACS |
| `homeassistant` | `"2024.4.0"` | Minimum HA version (HACS requirement) |
| `zip_release` | `true` | Create zip for releases |

**Acceptance Criteria:**
- [ ] `name` matches integration name
- [ ] `homeassistant` set to HACS minimum (2024.4.0+)
- [ ] Remove unused `filename` property

**Reference:** [HACS Integration Requirements](https://www.hacs.xyz/docs/publish/integration/)

### 10.2.3 manifest.json Requirements

**File:** `custom_components/embymedia/manifest.json`

**Required fields for HACS:**
```json
{
  "domain": "embymedia",
  "name": "Emby Media",
  "codeowners": ["@troykelly"],
  "config_flow": true,
  "dependencies": ["device_automation", "diagnostics", "media_source"],
  "documentation": "https://github.com/troykelly/homeassistant-emby",
  "integration_type": "hub",
  "iot_class": "local_push",
  "issue_tracker": "https://github.com/troykelly/homeassistant-emby/issues",
  "requirements": ["aiohttp>=3.8.0,<4.0.0"],
  "version": "0.1.0",
  "homeassistant": "2024.4.0"
}
```

**IoT Class options:**
| Class | Description |
|-------|-------------|
| `local_push` | Direct communication, push updates (WebSocket) |
| `local_polling` | Direct communication, polling updates |
| `cloud_push` | Cloud-based, push updates |
| `cloud_polling` | Cloud-based, polling updates |

**Update `iot_class` to `local_push`** since WebSocket provides push updates.

**Acceptance Criteria:**
- [ ] All required fields present
- [ ] `iot_class` reflects actual behavior (`local_push`)
- [ ] `homeassistant` minimum version set correctly
- [ ] `version` follows semver

**Reference:** [Integration Manifest](https://developers.home-assistant.io/docs/creating_integration_manifest/)

---

## Task 10.3: Home Assistant Brands

### 10.3.1 Submit to home-assistant/brands

**Required files for brands repository:**

```
brands/
└── custom_integrations/
    └── embymedia/
        ├── icon.png        # 256x256 square
        ├── icon@2x.png     # 512x512 square (hDPI)
        ├── logo.png        # Landscape, min 128px shortest side
        └── logo@2x.png     # Landscape, min 256px shortest side (hDPI)
```

**Icon Requirements:**
- Aspect ratio: 1:1 (square)
- Size: 256x256 pixels (icon.png), 512x512 pixels (icon@2x.png)
- Format: PNG with transparency

**Logo Requirements:**
- Landscape preferred
- Shortest side: 128-256 pixels (logo.png), 256-512 pixels (logo@2x.png)
- Format: PNG

**IMPORTANT:** Custom integrations must NOT use Home Assistant branded images.

**Acceptance Criteria:**
- [ ] Icon files created (256x256, 512x512)
- [ ] Logo files created (landscape, proper dimensions)
- [ ] PR submitted to home-assistant/brands
- [ ] No Home Assistant branding in images

**Reference:** [Home Assistant Brands Repository](https://github.com/home-assistant/brands)

### 10.3.2 Image Resources

**Helpful resources for creating brand assets:**
- [RedKetchup Image Resizer](https://redketchup.io/image-resizer) - Resize SVG/images in browser
- [Worldvectorlogo](https://worldvectorlogo.com/) - SVG brand images
- [Wikimedia Commons](https://commons.wikimedia.org/) - High quality images
- Emby press kit (if available) - Official brand assets

---

## Task 10.4: Pre-commit Hooks

### 10.4.1 Create Pre-commit Configuration

**File:** `.pre-commit-config.yaml` (new)

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: detect-private-key

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
        files: ^custom_components/embymedia/
        additional_dependencies:
          - homeassistant-stubs
          - aiohttp
```

**Hooks included:**
| Hook | Purpose |
|------|---------|
| `trailing-whitespace` | Remove trailing whitespace |
| `end-of-file-fixer` | Ensure files end with newline |
| `check-yaml` | Validate YAML syntax |
| `check-json` | Validate JSON syntax |
| `check-added-large-files` | Prevent large file commits |
| `check-merge-conflict` | Detect merge conflict markers |
| `detect-private-key` | Prevent accidental key commits |
| `ruff` | Linting with auto-fix |
| `ruff-format` | Code formatting |
| `mypy` | Type checking |

**Acceptance Criteria:**
- [ ] Pre-commit config created
- [ ] Ruff linting and formatting hooks
- [ ] Mypy type checking hook
- [ ] Standard pre-commit hooks

**Reference:** [Ruff Pre-commit](https://github.com/astral-sh/ruff-pre-commit)

### 10.4.2 Install Pre-commit

Add to `requirements_dev.txt`:
```
pre-commit>=3.0.0
```

**Developer setup:**
```bash
pip install pre-commit
pre-commit install
```

---

## Task 10.5: Test Coverage Requirements

### 10.5.1 Current Test Status

- **Total tests:** 815+
- **Coverage:** 100%
- **Modules tested:** All

### 10.5.2 Test Categories

| Category | Files | Coverage |
|----------|-------|----------|
| API Client | `test_api.py` | 100% |
| Config Flow | `test_config_flow.py` | 100% |
| Coordinator | `test_coordinator.py` | 100% |
| Media Player | `test_media_player.py` | 100% |
| Media Source | `test_media_source.py` | 100% |
| WebSocket | `test_websocket.py` | 100% |
| Browsing | `test_browse.py` | 100% |
| Services | `test_services.py` | 100% |
| Diagnostics | `test_diagnostics.py` | 100% |
| Device Triggers | `test_device_trigger.py` | 100% |
| Notify | `test_notify.py` | 100% |
| Remote | `test_remote.py` | 100% |
| Button | `test_button.py` | 100% |
| Image | `test_image.py` | 100% |
| Cache | `test_cache.py` | 100% |
| YAML Config | `test_yaml_config.py` | 100% |

### 10.5.3 Live Server Tests

**Directory:** `tests/live/`

Optional tests requiring environment variables:
- `EMBY_URL` - Emby server URL
- `EMBY_API_KEY` - API key for authentication

```python
@pytest.fixture
def requires_live_server(live_emby_url, live_emby_api_key):
    """Skip test if live server not available."""
    if not live_emby_url or not live_emby_api_key:
        pytest.skip("Live server credentials required")
```

**Acceptance Criteria:**
- [ ] 100% coverage maintained
- [ ] All test categories passing
- [ ] Live tests work when credentials available

---

## Task 10.6: Type Safety

### 10.6.1 Mypy Configuration

**File:** `pyproject.toml` or `mypy.ini`

```toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = true
disallow_any_generics = true
no_implicit_optional = true
show_error_codes = true

[[tool.mypy.overrides]]
module = "homeassistant.*"
ignore_missing_imports = true
```

### 10.6.2 Type Safety Rules

**Project rules (from CLAUDE.md):**
- NEVER use `Any` in type annotations
- Exception: `**kwargs: Any` when overriding HA base class methods
- Use `TypedDict` for API response structures
- Use `dataclasses` for internal models
- Use `Protocol` for interfaces
- Modern syntax: `str | None` not `Optional[str]`

**Acceptance Criteria:**
- [ ] Mypy strict mode passing
- [ ] No `Any` types (except required overrides)
- [ ] All functions have return type annotations
- [ ] All class attributes typed

---

## Task 10.7: Documentation Requirements

### 10.7.1 README.md Requirements

**Required sections for HACS:**
- [ ] Integration description
- [ ] Installation instructions (HACS and manual)
- [ ] Configuration guide
- [ ] Feature list
- [ ] Screenshots/images (HACS renders README)
- [ ] Troubleshooting
- [ ] Contributing guidelines
- [ ] License

### 10.7.2 CHANGELOG.md

**Recommended format:**
```markdown
# Changelog

## [Unreleased]

## [1.0.0] - YYYY-MM-DD
### Added
- Initial release
- Media player entities for Emby clients
- Media browsing support
- WebSocket real-time updates
...
```

---

## Acceptance Criteria Summary

### Required for Phase 10 Complete

**CI/CD:**
- [ ] Test workflow tests Python 3.12 and 3.13
- [ ] HACS validation workflow added
- [ ] Hassfest validation workflow added
- [ ] Release workflow creates versioned zip
- [ ] All workflows passing

**HACS Compliance:**
- [ ] `hacs.json` properly configured
- [ ] `manifest.json` meets all requirements
- [ ] At least one GitHub release published
- [ ] Repository description set

**Brands:**
- [ ] Icon files created (256x256, 512x512)
- [ ] Logo files created
- [ ] PR submitted to home-assistant/brands

**Code Quality:**
- [ ] Pre-commit hooks configured
- [ ] 100% test coverage maintained
- [ ] Mypy strict mode passing
- [ ] Ruff linting and formatting passing

**Documentation:**
- [ ] README.md complete with all sections
- [ ] CHANGELOG.md created
- [ ] Installation guide accurate

### Definition of Done

1. ✅ All GitHub Actions workflows passing
2. ✅ HACS validation action passing
3. ✅ Hassfest validation action passing
4. ✅ Pre-commit hooks configured
5. ✅ Brands submission PR created
6. ✅ At least one GitHub release published
7. ✅ 100% test coverage maintained
8. ✅ Documentation complete

---

## HACS Default Submission Checklist

When ready to submit to HACS default repositories:

1. [ ] Read [HACS publishing documentation](https://www.hacs.xyz/docs/publish/start/)
2. [ ] HACS action added and passing
3. [ ] Hassfest action added and passing
4. [ ] At least one GitHub release published
5. [ ] Repository added to [home-assistant/brands](https://github.com/home-assistant/brands)
6. [ ] `hacs.json` contains at least `name`
7. [ ] Repository has description
8. [ ] Repository is not archived
9. [ ] Fork [hacs/default](https://github.com/hacs/default)
10. [ ] Create new branch from master
11. [ ] Add entry alphabetically to `integration` file
12. [ ] Submit PR with completed template
13. [ ] Wait for automated checks to pass
14. [ ] Wait for manual review (can take months)

**Reference:** [HACS Include Default Repositories](https://www.hacs.xyz/docs/publish/include/)

---

## Sources

- [HACS Integration Requirements](https://www.hacs.xyz/docs/publish/integration/)
- [HACS GitHub Action](https://github.com/hacs/action)
- [Hassfest for Custom Components](https://developers.home-assistant.io/blog/2020/04/16/hassfest/)
- [Home Assistant Brands Repository](https://github.com/home-assistant/brands)
- [Integration Manifest Documentation](https://developers.home-assistant.io/docs/creating_integration_manifest/)
- [Home Assistant Actions](https://github.com/home-assistant/actions)
- [Ruff Pre-commit Hook](https://github.com/astral-sh/ruff-pre-commit)
- [HACS Default Repository Inclusion](https://www.hacs.xyz/docs/publish/include/)
