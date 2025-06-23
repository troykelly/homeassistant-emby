"""The Emby custom component package placeholder.

This module is intentionally minimal - Home Assistant discovers the actual
platform code through the *manifest.json* file and via platform-specific
submodules (e.g. *media_player*).  The docstring exists primarily to satisfy
#
# It also imports the *pyemby* compatibility shim so that the integration
# functions on modern Python versions (3.12/3.13) where *async-timeout* ≥ 4 is
# bundled and the upstream *pyemby* library would otherwise raise
# `TypeError: 'Timeout' object does not support the context manager protocol`.
"""

# Apply runtime shim – safe no-op on older environments.
# Import solely for its side-effects (monkey-patching pyemby).  Suppress the
# *unused import* diagnostic for both Pyright and pylint/flake8.
#
# pyright: ignore[reportUnusedImport]
# noqa: F401
# pylint: disable=unused-import
from . import _pyemby_compat as _  # type: ignore
