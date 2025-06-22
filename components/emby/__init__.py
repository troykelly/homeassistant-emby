"""Compatibility alias forwarding to the new *custom_components.emby* package.

This stub allows legacy imports such as::

    from components.emby.api import EmbyAPI

which were used throughout the existing test-suite and developer tools.  The
actual implementation lives under *custom_components.emby* as required by HACS.
The forwarding logic below seamlessly maps the public sub-modules so that
existing code continues to work without modification.
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType
from typing import Final

_TARGET_ROOT: Final[str] = "custom_components.emby"

# Import the real integration package and register it under the *components*
# namespace so that ``import components.emby`` yields the correct module.
_target_pkg: ModuleType = importlib.import_module(_TARGET_ROOT)
sys.modules[__name__] = _target_pkg  # type: ignore[assignment]

# Expose the three public sub-modules as well – this ensures dotted imports
# like ``components.emby.api`` work out of the box.
for _sub in ("api", "media_player", "search_resolver"):
    sys.modules[f"{__name__}.{_sub}"] = importlib.import_module(f"{_TARGET_ROOT}.{_sub}")

del importlib, sys, ModuleType, Final, _TARGET_ROOT, _target_pkg, _sub  # clean-up
