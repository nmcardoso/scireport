"""Finding templates and layouts: built in, by path, or through entry points (ADR-0003).

A reference is ``name`` (the newest version), ``name@version`` or a path to a directory that holds
``template.yaml`` / ``layout.yaml``. Built-in templates and layouts live in ``scireport/templates/
<name>/<version>/`` and ``scireport/layouts/<name>/<version>/`` and are frozen per version
(ADR-0008). Other packages add their own through the entry-point groups ``scireport.templates``
and ``scireport.layouts``: the entry point's name is the template or layout name and it points to
a directory (as a :class:`pathlib.Path`, a string, or a function returning one) that is either a
version directory or a folder of numbered version directories.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Literal

from scireport.errors import TemplateError
from scireport.logging_utils import get_logger
from scireport.render.layout import LAYOUT_FILE, Layout, load_layout_dir
from scireport.render.template import TEMPLATE_FILE, Template, load_template_dir
from scireport.spec.manifest import Manifest

log = get_logger(__name__)

PACKAGE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_GROUP = 'scireport.templates'
LAYOUT_GROUP = 'scireport.layouts'
DEFAULT_TEMPLATE = 'generic@1'
"""Template used when neither the bundle nor the caller names one."""
DEFAULT_LAYOUT = 'minimal@1'
"""Layout used when neither the bundle nor the caller names one (``default@1`` from S3)."""

Kind = Literal['template', 'layout']


@dataclass(frozen=True)
class Listing:
  """One available template or layout version.

  Parameters
  ----------
  name : str
      Its name.
  version : int
      Its version.
  title : str
      One-line title.
  origin : str
      ``builtin`` or ``entry-point:<name>``.
  formats : tuple of str
      Output formats it supports.
  """

  name: str
  version: int
  title: str
  origin: str
  formats: tuple[str, ...]

  @property
  def ref(self) -> str:
    """``name@version``."""
    return f'{self.name}@{self.version}'


def split_ref(ref: str) -> tuple[str, int | None]:
  """Split ``name@version`` into its parts.

  Parameters
  ----------
  ref : str
      A reference such as ``generic@1`` or ``generic``.

  Returns
  -------
  tuple of (str, int or None)
      The name and the version (None when absent).

  Raises
  ------
  TemplateError
      With code ``E701`` when the version after ``@`` is not a positive integer.
  """
  name, _, version = ref.partition('@')
  if not version:
    return name, None
  if not version.isdecimal() or int(version) < 1:
    raise TemplateError(
      f'{ref!r} has a version that is not a positive integer',
      code='E701',
      hint='Write name@1, name@2 ... or just name for the newest.',
    )
  return name, int(version)


def load_template(ref: str | Path) -> Template:
  """Load a template by reference or from a directory.

  Parameters
  ----------
  ref : str or pathlib.Path
      ``name``, ``name@version`` or a path to a template directory (a string is a path when it
      has a path separator or starts with ``.`` or ``~``).

  Returns
  -------
  Template
      The template.

  Raises
  ------
  TemplateError
      With ``E701`` (not found), ``E504`` (version not found), ``E705`` (plugin failed) or the
      errors of :func:`~scireport.render.template.load_template_dir`.
  """
  return _load('template', ref, TEMPLATE_FILE, load_template_dir)


def load_layout(ref: str | Path) -> Layout:
  """Load a layout by reference or from a directory; see :func:`load_template`.

  Parameters
  ----------
  ref : str or pathlib.Path
      ``name``, ``name@version`` or a path to a layout directory.

  Returns
  -------
  Layout
      The layout.

  Raises
  ------
  TemplateError
      With ``E701``, ``E504``, ``E705`` or the errors of
      :func:`~scireport.render.layout.load_layout_dir`.
  """
  return _load('layout', ref, LAYOUT_FILE, load_layout_dir)


def pin(kind: Kind, ref: str) -> str:
  """Resolve a template or layout reference to ``name@version``.

  Parameters
  ----------
  kind : {'template', 'layout'}
      What the reference names.
  ref : str
      ``name`` or ``name@version``.

  Returns
  -------
  str
      The reference with an explicit version; the newest when ``ref`` had none.

  Raises
  ------
  TemplateError
      When the template or layout does not exist.
  """
  loaded = load_template(ref) if kind == 'template' else load_layout(ref)
  return loaded.ref


def pin_manifest(manifest: Manifest) -> Manifest:
  """Pin the template and layout named in a manifest to explicit versions (ADR-0008).

  ``name`` becomes ``name@version`` with the newest version available here, so that a later
  render of the packed bundle is identical even after newer versions exist. ``name@version``
  is kept as written, and a name that cannot be resolved here (a plugin that is not installed)
  is left alone with a warning. Nothing is pinned for a field the bundle leaves unset: the
  defaults are frozen per version too (``generic@1``).

  Parameters
  ----------
  manifest : Manifest
      The manifest to pin.

  Returns
  -------
  Manifest
      The manifest with pinned references; the same object when nothing changed.
  """
  changes: dict[str, str] = {}
  for kind in ('template', 'layout'):
    ref = getattr(manifest.render, kind)
    if ref is None or '@' in ref:
      continue
    try:
      changes[kind] = pin(kind, ref)
    except TemplateError as exc:
      log.warning('cannot pin the %s %r: %s', kind, ref, exc.message)
  if not changes:
    return manifest
  return manifest.model_copy(update={'render': manifest.render.model_copy(update=changes)})


def list_templates() -> list[Listing]:
  """List every template version available, built in or from entry points, sorted."""
  return _list('template', TEMPLATE_GROUP, TEMPLATE_FILE)


def list_layouts() -> list[Listing]:
  """List every layout version available, built in or from entry points, sorted."""
  return _list('layout', LAYOUT_GROUP, LAYOUT_FILE)


def _is_path(ref: str | Path) -> bool:
  """Decide whether a reference is a directory path rather than a name."""
  if isinstance(ref, Path):
    return True
  return os.sep in ref or '/' in ref or ref.startswith(('.', '~'))


def _load[T: (Template, Layout)](
  kind: Kind,
  ref: str | Path,
  filename: str,
  loader: Callable[..., T],
) -> T:
  """Resolve a reference to a directory and load it."""
  if _is_path(ref):
    root = Path(ref).expanduser()
    if not (root / filename).is_file():
      versions = _version_dirs(root, filename)
      if not versions:
        raise TemplateError(
          f'{root} is not a {kind} directory: it has no {filename}',
          code='E701',
          hint=f'Point to the folder that holds {filename}.',
        )
      root = versions[max(versions)]
    return loader(root, origin='path')
  name, version = split_ref(str(ref))
  candidates = _candidates(kind, name, filename)
  if not candidates:
    available = ', '.join(sorted({item.name for item in _list(kind, _group(kind), filename)}))
    raise TemplateError(
      f'no {kind} named {name!r}',
      code='E701',
      hint=f'Available: {available or "none"}. A path to a directory also works.',
    )
  if version is None:
    version = max(candidates)
  if version not in candidates:
    have = ', '.join(f'{name}@{v}' for v in sorted(candidates))
    raise TemplateError(
      f'{kind} {name!r} has no version {version}', code='E504', hint=f'Available: {have}.'
    )
  root, origin = candidates[version]
  return loader(root, origin=origin)


def _group(kind: Kind) -> str:
  """Return the entry-point group of a kind."""
  return TEMPLATE_GROUP if kind == 'template' else LAYOUT_GROUP


def _builtin_root(kind: Kind) -> Path:
  """Return the folder of built-in templates or layouts."""
  return PACKAGE_DIR / ('templates' if kind == 'template' else 'layouts')


def _version_dirs(root: Path, filename: str) -> dict[int, Path]:
  """Map version number to directory for the numbered folders under ``root`` that hold a file."""
  if not root.is_dir():
    return {}
  return {
    int(path.name): path
    for path in root.iterdir()
    if path.name.isdecimal() and (path / filename).is_file()
  }


def _entry_roots(kind: Kind, name: str | None = None) -> list[tuple[str, Path]]:
  """Resolve the entry points of a kind to ``(entry-point name, directory)`` pairs."""
  found = []
  for entry in metadata.entry_points(group=_group(kind)):
    if name is not None and entry.name != name:
      continue
    try:
      target = entry.load()
      path = Path(target() if callable(target) else target)
    except Exception as exc:  # a plugin can fail in any way
      raise TemplateError(
        f'the {kind} plugin {entry.name!r} ({entry.value}) cannot be loaded: {exc}',
        code='E705',
        hint='Check the package that provides it, or remove it from the environment.',
      ) from exc
    found.append((entry.name, path))
  return found


def _candidates(kind: Kind, name: str, filename: str) -> dict[int, tuple[Path, str]]:
  """Collect the versions of one name: built in first, then entry points that do not shadow it."""
  versions: dict[int, tuple[Path, str]] = {
    v: (path, 'builtin') for v, path in _version_dirs(_builtin_root(kind) / name, filename).items()
  }
  if versions:
    return versions
  for entry_name, root in _entry_roots(kind, name):
    if (root / filename).is_file():
      from scireport.render.definition import read_definition

      raw = read_definition(root / filename, kind=kind)
      version = raw.get('version')
      if isinstance(version, int):
        versions[version] = (root, f'entry-point:{entry_name}')
      continue
    for v, path in _version_dirs(root, filename).items():
      versions[v] = (path, f'entry-point:{entry_name}')
  return versions


def _list(kind: Kind, group: str, filename: str) -> list[Listing]:
  """List built-in and entry-point versions with their titles."""
  del group
  loader = load_template_dir if kind == 'template' else load_layout_dir
  listings: list[Listing] = []
  builtin = _builtin_root(kind)
  names = sorted(p.name for p in builtin.iterdir() if p.is_dir()) if builtin.is_dir() else []
  for name in names:
    for version, root in sorted(_version_dirs(builtin / name, filename).items()):
      listings.append(_listing(loader(root, origin='builtin'), 'builtin', version))
  for entry_name, root in _entry_roots(kind):
    if entry_name in names:
      log.warning(
        'the %s plugin %r is ignored: a built-in %s has that name', kind, entry_name, kind
      )
      continue
    roots = [root] if (root / filename).is_file() else list(_version_dirs(root, filename).values())
    for directory in roots:
      listings.append(
        _listing(loader(directory, origin='entry-point'), f'entry-point:{entry_name}')
      )
  return sorted(listings, key=lambda item: (item.name, item.version))


def _listing(loaded: Template | Layout, origin: str, version: int | None = None) -> Listing:
  """Build a listing row from a loaded template or layout."""
  definition = loaded.definition
  formats = (
    definition.formats if isinstance(definition.formats, list) else sorted(definition.formats)
  )
  return Listing(
    definition.name,
    version or definition.version,
    definition.title,
    origin,
    tuple(formats),
  )
