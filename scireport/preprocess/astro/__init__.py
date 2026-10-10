"""The astro catalogue (``scireport[astro]``): sky maps and photometric diagnostics.

Importing a module here never imports astropy: each function imports what it needs when it
runs, so the registry lists these pre-processors without the extra, and running one without it
is an ``E607`` error with an install hint.
"""

from __future__ import annotations

import importlib
import pkgutil

for _module in sorted(pkgutil.iter_modules(__path__), key=lambda found: found.name):
  if not _module.name.startswith('_'):
    importlib.import_module(f'{__name__}.{_module.name}')
