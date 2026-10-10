"""The core catalogue: pre-processors that need nothing beyond the base install.

Every module of this package that does not start with an underscore is imported when the
registry is first used, and its ``@preprocessor`` functions register themselves.
"""

from __future__ import annotations

import importlib
import pkgutil

for _module in sorted(pkgutil.iter_modules(__path__), key=lambda found: found.name):
  if not _module.name.startswith('_'):
    importlib.import_module(f'{__name__}.{_module.name}')
