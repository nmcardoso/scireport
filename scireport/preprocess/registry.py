"""The pre-processor registry: the decorator, discovery and lookup by name (ADR-0006).

A pre-processor is a function ``f(ctx, *, <inputs>, <parameters>) -> {port: value}`` registered
under a dotted name (``core.histogram``) and an integer version. Data files refer to it by name
only; ``module:function`` is resolved only when the caller allows imports. Three sources fill
the registry: the built-ins (``scireport.preprocess.core`` and ``.astro``), the entry-point group
``scireport.preprocessors`` and :func:`register_preprocessor`.

A released version of a pre-processor is frozen: a change that alters a figure or a number is a
new version registered beside the old one, and a step that names ``version: 1`` keeps getting
version 1 (ADR-0008).
"""

from __future__ import annotations

import difflib
import importlib
import importlib.metadata
import inspect
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from scireport.errors import Issue, PreprocessError
from scireport.logging_utils import get_logger
from scireport.preprocess.ports import Port

log = get_logger(__name__)

ENTRY_POINT_GROUP = 'scireport.preprocessors'
"""The entry-point group plugins register their pre-processors under."""

_NAME_RE = re.compile(r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$')


@dataclass(frozen=True, eq=False)
class Preprocessor:
  """A registered pre-processor.

  Call it like the function it wraps: ``histogram(ctx, table=..., column='z')``.

  Parameters
  ----------
  name : str
      Dotted name such as ``core.histogram``.
  version : int
      Version of the behaviour; at least 1.
  func : callable
      ``f(ctx, *, <inputs>, <parameters>) -> dict[str, Value]``.
  inputs, outputs : dict
      Port name to :class:`~scireport.preprocess.ports.Port`. Input port names are keyword
      arguments of ``func``; ``func`` returns a value for every non-optional output port.
  render : callable or None, default=None
      For a pre-processor that draws: ``render(ctx, data, **style) -> Figure``, which rebuilds
      the figure from its sidecar data (used by the tests to prove that the data is enough).
  requires : str or None, default=None
      The extra (``'astro'``) whose packages ``func`` needs; None for the core install.
  summary : str, default=''
      First line of the docstring of ``func``.
  """

  name: str
  version: int
  func: Callable[..., dict[str, Any]]
  inputs: Mapping[str, Port] = field(default_factory=dict)
  outputs: Mapping[str, Port] = field(default_factory=dict)
  render: Callable[..., Any] | None = None
  requires: str | None = None
  summary: str = ''

  def __call__(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
    """Call the wrapped function."""
    return self.func(*args, **kwargs)

  @property
  def ref(self) -> str:
    """The name with its version, ``core.histogram@1``."""
    return f'{self.name}@{self.version}'


_REGISTRY: dict[tuple[str, int], Preprocessor] = {}
_STATE = {'builtins': False, 'plugins': False}


def preprocessor(
  name: str,
  *,
  version: int,
  inputs: Mapping[str, Port] | None = None,
  outputs: Mapping[str, Port] | None = None,
  render: Callable[..., Any] | None = None,
  requires: str | None = None,
) -> Callable[[Callable[..., dict[str, Any]]], Preprocessor]:
  """Register a function as a pre-processor.

  Parameters
  ----------
  name : str
      Dotted lower-case name, ``group.name`` (``core.histogram``).
  version : int
      Version of the behaviour, at least 1.
  inputs, outputs : dict or None
      Port name to :class:`~scireport.preprocess.ports.Port`.
  render : callable or None, default=None
      The drawing function of a figure pre-processor; see :class:`Preprocessor`.
  requires : str or None, default=None
      The extra the function needs, such as ``'astro'``.

  Returns
  -------
  callable
      A decorator that registers the function and returns the :class:`Preprocessor`.

  Raises
  ------
  ValueError
      When the name or version is malformed, an input port is not a parameter of the function,
      or the name and version are already registered.
  """

  def decorate(func: Callable[..., dict[str, Any]]) -> Preprocessor:
    doc = inspect.getdoc(func) or ''
    entry = Preprocessor(
      name=name,
      version=version,
      func=func,
      inputs=dict(inputs or {}),
      outputs=dict(outputs or {}),
      render=render,
      requires=requires,
      summary=doc.strip().splitlines()[0] if doc.strip() else '',
    )
    register_preprocessor(entry)
    return entry

  return decorate


def register_preprocessor(entry: Preprocessor, *, replace: bool = False) -> Preprocessor:
  """Add a pre-processor to the registry.

  Parameters
  ----------
  entry : Preprocessor
      What to register.
  replace : bool, default=False
      Replace an entry with the same name and version instead of raising.

  Returns
  -------
  Preprocessor
      ``entry``.

  Raises
  ------
  ValueError
      When the name is not dotted lower case, the version is below 1, an input port is not a
      keyword-only or named parameter of the function, or the name and version exist already.
  """
  if not _NAME_RE.fullmatch(entry.name):
    raise ValueError(f'pre-processor name must look like group.name, got {entry.name!r}')
  if entry.version < 1:
    raise ValueError(f'pre-processor version must be at least 1, got {entry.version}')
  parameters = inspect.signature(entry.func).parameters
  missing = [port for port in entry.inputs if port not in parameters]
  if missing:
    raise ValueError(f'{entry.ref}: input ports {missing} are not parameters of the function')
  slot = (entry.name, entry.version)
  if slot in _REGISTRY and not replace:
    raise ValueError(f'{entry.ref} is already registered')
  _REGISTRY[slot] = entry
  return entry


def unregister_preprocessor(name: str, version: int) -> None:
  """Remove a pre-processor from the registry (for tests and plugins that reload).

  Parameters
  ----------
  name : str
      The dotted name.
  version : int
      The version.
  """
  _REGISTRY.pop((name, version), None)


def list_preprocessors() -> list[Preprocessor]:
  """Return every registered pre-processor, sorted by name and version.

  Returns
  -------
  list of Preprocessor
      Built-ins, plugins and anything registered in code.
  """
  _discover()
  return [_REGISTRY[slot] for slot in sorted(_REGISTRY)]


def get_preprocessor(
  name: str, version: int | None = None, *, allow_import: bool = False, pointer: str = ''
) -> Preprocessor:
  """Look up a pre-processor by name and version.

  Parameters
  ----------
  name : str
      A registered dotted name, or ``module:function`` when ``allow_import`` is true.
  version : int or None, default=None
      The version a step was written for; None means the newest registered.
  allow_import : bool, default=False
      Let ``module:function`` import code. A data file can then run arbitrary code, so only a
      trusted caller sets it.
  pointer : str, default=''
      JSON pointer of the step, for the error.

  Returns
  -------
  Preprocessor
      The registered entry.

  Raises
  ------
  PreprocessError
      With ``E601`` when the name or version is unknown (with a suggestion), ``E605`` when the
      name needs ``allow_import``, and ``E608`` when the import fails.
  """
  if ':' in name:
    return _import_reference(name, version, allow_import, pointer)
  _discover()
  versions = sorted(v for (n, v) in _REGISTRY if n == name)
  if not versions:
    names = sorted({n for (n, _) in _REGISTRY})
    close = difflib.get_close_matches(name, names, n=1)
    hint = f'Did you mean {close[0]!r}?' if close else 'Run `scireport preprocessors` for the list.'
    raise PreprocessError([Issue('E601', f'no pre-processor named {name!r}', pointer, hint=hint)])
  chosen = versions[-1] if version is None else version
  if chosen not in versions:
    raise PreprocessError(
      [
        Issue(
          'E601',
          f'pre-processor {name!r} has no version {chosen}',
          pointer,
          expected=f'one of {versions}',
          found=str(chosen),
        )
      ]
    )
  return _REGISTRY[(name, chosen)]


def _import_reference(
  reference: str, version: int | None, allow_import: bool, pointer: str
) -> Preprocessor:
  """Resolve ``module:function`` to a registered pre-processor; the caller allowed imports."""
  if not allow_import:
    raise PreprocessError(
      [
        Issue(
          'E605',
          f'{reference!r} names code to import, and a data file may not run code by default',
          pointer,
          hint='Use a registered name, or pass --allow-import (allow_import=True) if you trust '
          'this file.',
        )
      ]
    )
  module_name, _, attribute = reference.partition(':')
  try:
    module = importlib.import_module(module_name)
    found = module
    for part in attribute.split('.'):
      found = getattr(found, part)
  except (ImportError, AttributeError) as exc:
    raise PreprocessError([Issue('E608', f'cannot import {reference!r}: {exc}', pointer)]) from exc
  if not isinstance(found, Preprocessor):
    raise PreprocessError(
      [
        Issue(
          'E601',
          f'{reference!r} is not a pre-processor',
          pointer,
          hint='Decorate the function with @preprocessor(...).',
        )
      ]
    )
  if version is not None and found.version != version:
    raise PreprocessError(
      [
        Issue(
          'E601',
          f'{reference!r} is version {found.version}, the step asks for {version}',
          pointer,
          expected=str(version),
          found=str(found.version),
        )
      ]
    )
  return found


def _discover() -> None:
  """Load the built-ins and the entry-point plugins, once each."""
  if not _STATE['builtins']:
    _STATE['builtins'] = True
    importlib.import_module('scireport.preprocess.core')
    importlib.import_module('scireport.preprocess.astro')
  if not _STATE['plugins']:
    _STATE['plugins'] = True
    for entry_point in importlib.metadata.entry_points(group=ENTRY_POINT_GROUP):
      try:
        loaded: Any = entry_point.load()
      except Exception as exc:
        log.warning('E608 cannot load the pre-processor plugin %s: %s', entry_point.name, exc)
        continue
      if isinstance(loaded, Preprocessor) and (loaded.name, loaded.version) not in _REGISTRY:
        register_preprocessor(loaded)
