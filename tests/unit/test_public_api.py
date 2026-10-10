"""The public API is ``scireport.__all__``; a snapshot makes any change deliberate (ADR-0008).

The snapshot lists every public name with its kind and signature, and for classes their public
methods (pydantic models: their fields). A change to the file is a change to the API: removing or
renaming a name, or changing a signature incompatibly, needs a new major version; adding is a
minor change. Regenerate with
``SCIREPORT_UPDATE_API=1 uv run pytest tests/unit/test_public_api.py``.
"""

from __future__ import annotations

import inspect
import os
from pathlib import Path
from typing import Any

import scireport

SNAPSHOT = Path(__file__).with_name('public_api.txt')


def plain(func: Any) -> str:
  """Render a signature without annotations, whose text differs between Python versions."""
  sig = inspect.signature(func)
  return str(
    sig.replace(
      parameters=[p.replace(annotation=inspect.Parameter.empty) for p in sig.parameters.values()],
      return_annotation=inspect.Signature.empty,
    )
  )


def describe(name: str, obj: Any) -> list[str]:
  if inspect.isclass(obj):
    lines = [f'class {name}']
    if hasattr(obj, 'model_fields'):
      lines += [f'  field {field}' for field in obj.model_fields]
    elif issubclass(obj, Exception):
      lines.append(f'  bases {", ".join(b.__name__ for b in obj.__bases__)}')
      lines.append(f'  exit_code {getattr(obj, "exit_code", None)}')
    for member_name, member in vars(obj).items():
      if member_name.startswith('_') and member_name != '__init__':
        continue
      if inspect.isfunction(member):
        lines.append(f'  def {member_name}{plain(member)}')
      elif isinstance(member, property):
        lines.append(f'  property {member_name}')
    return lines
  if callable(obj):
    return [f'def {name}{plain(obj)}']
  return [f'const {name} = {obj!r}']


def snapshot() -> str:
  lines: list[str] = []
  for name in sorted(scireport.__all__):
    lines += describe(name, getattr(scireport, name))
  return '\n'.join(lines) + '\n'


def test_the_snapshot_matches() -> None:
  current = snapshot()
  if os.environ.get('SCIREPORT_UPDATE_API') == '1':
    SNAPSHOT.write_text(current, encoding='utf-8', newline='\n')
  assert current == SNAPSHOT.read_text(encoding='utf-8'), 'the public API changed'


def test_every_public_name_resolves_and_is_listed_once() -> None:
  assert len(scireport.__all__) == len(set(scireport.__all__))
  for name in scireport.__all__:
    assert getattr(scireport, name) is not None
  assert sorted(dir(scireport)) == sorted(scireport.__all__)


def test_an_unknown_attribute_raises_attribute_error() -> None:
  import pytest

  with pytest.raises(AttributeError, match='no attribute'):
    scireport.nothing_here  # noqa: B018


def test_importing_the_package_does_not_load_the_renderer() -> None:
  import subprocess
  import sys

  code = (
    'import sys, scireport; '
    'assert "scireport.render.pipeline" not in sys.modules; '
    'scireport.render_bundle; '
    'assert "scireport.render.pipeline" in sys.modules'
  )
  subprocess.run([sys.executable, '-I', '-c', code], check=True, timeout=60)
