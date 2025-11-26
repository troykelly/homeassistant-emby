# Contributing to Emby Media for Home Assistant

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

Please be respectful and constructive in all interactions. We welcome contributors of all skill levels.

## Ways to Contribute

### Reporting Bugs

1. Check [existing issues](https://github.com/troykelly/homeassistant-emby/issues) first
2. Include:
   - Home Assistant version
   - Emby Server version
   - Integration version
   - Steps to reproduce
   - Expected vs actual behavior
   - Relevant logs
   - [Diagnostics file](docs/TROUBLESHOOTING.md#getting-diagnostics)

### Suggesting Features

Open an issue with:
- Clear description of the feature
- Use cases explaining why it's needed
- Any relevant examples from other integrations

### Improving Documentation

- Fix typos or unclear instructions
- Add examples
- Improve troubleshooting guides

### Code Contributions

## Development Setup

### Prerequisites

- Python 3.13+
- Home Assistant development environment
- Git

### Clone and Install

```bash
git clone https://github.com/troykelly/homeassistant-emby.git
cd homeassistant-emby

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements_test.txt
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=custom_components.embymedia --cov-report=term-missing

# Run specific test file
pytest tests/test_media_player.py -v

# Run specific test
pytest tests/test_media_player.py::test_play_media -v
```

### Type Checking

```bash
mypy custom_components/embymedia/
```

### Linting

```bash
ruff check custom_components/embymedia/
ruff format custom_components/embymedia/
```

## Development Guidelines

### Test-Driven Development (TDD)

This project follows strict TDD:

1. **Write a failing test first**
2. **Write minimal code to pass the test**
3. **Refactor while keeping tests green**

No code without a test. No exceptions.

### Type Safety

- **Never use `Any` type** (except `**kwargs: Any` when required by HA overrides)
- Use `TypedDict` for API responses
- Use `dataclasses` for internal models
- Modern syntax: `str | None` not `Optional[str]`

### Code Style

- Use `from __future__ import annotations`
- Explicit return types on all functions
- Type all class attributes
- Use `_attr_*` pattern for entity attributes
- Never do I/O in properties

### Research Before Implementing

If your implementation fails twice:

1. Stop coding
2. Read official documentation
3. Examine working implementations in HA core
4. Understand before trying again

## Pull Request Process

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/my-feature`
3. **Make your changes**
4. **Run the full test suite**: `pytest tests/ --cov`
5. **Run type checking**: `mypy custom_components/embymedia/`
6. **Run linting**: `ruff check . && ruff format --check .`
7. **Commit with a descriptive message**
8. **Push to your fork**
9. **Open a Pull Request**

### PR Requirements

- [ ] All tests pass
- [ ] 100% test coverage maintained
- [ ] Type checking passes
- [ ] Linting passes
- [ ] Documentation updated if needed
- [ ] Commit messages are clear

### Commit Message Format

```
type: short description

Longer description if needed.

Fixes #123
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

## Project Structure

```
custom_components/embymedia/
├── __init__.py           # Integration setup
├── manifest.json         # Integration metadata
├── config_flow.py        # UI configuration
├── const.py              # Constants, TypedDicts
├── coordinator.py        # DataUpdateCoordinator
├── entity.py             # Base entity class
├── api.py                # Emby API client
├── models.py             # Dataclasses
├── media_player.py       # Media player entity
├── remote.py             # Remote entity
├── notify.py             # Notify entity
├── button.py             # Button entity
├── media_source.py       # Media source provider
├── browse.py             # Media browser helpers
├── image.py              # Image proxy
├── services.py           # Custom services
├── websocket.py          # WebSocket client
├── cache.py              # Response caching
├── exceptions.py         # Custom exceptions
├── diagnostics.py        # Diagnostic download
└── device_trigger.py     # Automation triggers

tests/
├── conftest.py           # Pytest fixtures
├── test_*.py             # Test files
```

## Getting Help

- Open a [discussion](https://github.com/troykelly/homeassistant-emby/discussions)
- Ask in your PR if you're stuck
- Review existing code for patterns

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
