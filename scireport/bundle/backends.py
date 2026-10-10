"""Storage backends of a bundle: a directory, a ZIP archive or memory.

A backend maps the relative POSIX names inside a bundle (``scireport.json``,
``assets/tables/x.parquet``) to bytes. It does no hashing and knows nothing about the manifest.
"""

from __future__ import annotations

import os
import stat
import zipfile
from pathlib import Path, PurePosixPath
from typing import IO, Protocol

from scireport.errors import BundleError
from scireport.hashing import sha256_file
from scireport.spec.assets import ASSET_ROOT, asset_path_problem

MANIFEST_NAME = 'scireport.json'
"""Name of the manifest inside a bundle."""

YAML_MANIFEST_NAMES = ('scireport.yaml', 'scireport.yml')
"""Names a hand-authored directory may use instead."""

DEFAULT_MAX_BYTES = 1 << 30
"""Default size cap of a bundle, in bytes (uncompressed): 1 GiB."""

MAX_ENTRIES = 10_000
"""Most files a ZIP bundle may hold."""

_SYMLINK_MODE = 0o120000


class Backend(Protocol):
  """What the reader and the writer need from a storage."""

  def names(self) -> list[str]:
    """Return every file name in the bundle, sorted."""

  def size(self, name: str) -> int:
    """Return the size in bytes of ``name``; raises ``FileNotFoundError`` when absent."""

  def read(self, name: str) -> bytes:
    """Return the content of ``name``; raises ``FileNotFoundError`` when absent."""

  def open(self, name: str) -> IO[bytes]:
    """Open ``name`` for streaming; raises ``FileNotFoundError`` when absent."""

  def close(self) -> None:
    """Release any file handle."""


class MemoryBackend:
  """A bundle held in memory, as a ``Report`` builds it.

  Parameters
  ----------
  files : dict
      Name to content.
  """

  def __init__(self, files: dict[str, bytes]) -> None:
    self._files = dict(files)

  def names(self) -> list[str]:
    """Return the file names, sorted."""
    return sorted(self._files)

  def size(self, name: str) -> int:
    """Return the size of ``name`` in bytes."""
    return len(self._get(name))

  def read(self, name: str) -> bytes:
    """Return the content of ``name``."""
    return self._get(name)

  def open(self, name: str) -> IO[bytes]:
    """Open ``name`` as an in-memory stream."""
    import io

    return io.BytesIO(self._get(name))

  def close(self) -> None:
    """Do nothing; there is no handle."""

  def _get(self, name: str) -> bytes:
    """Return the content of ``name`` or raise ``FileNotFoundError``."""
    try:
      return self._files[name]
    except KeyError:
      raise FileNotFoundError(name) from None


class OverlayBackend:
  """Files of one backend with another's files on top (a bundle plus what pre-processing added).

  A name found in ``top`` shadows the same name in ``base``. Closing the overlay closes both.

  Parameters
  ----------
  base : Backend
      The original files.
  top : Backend
      The added or replaced files.
  """

  def __init__(self, base: Backend, top: Backend) -> None:
    self._base = base
    self._top = top

  def names(self) -> list[str]:
    """Return the names of both backends, each once, sorted."""
    return sorted({*self._base.names(), *self._top.names()})

  def size(self, name: str) -> int:
    """Return the size of ``name``, from the top backend when it has it."""
    return self._pick(name).size(name)

  def read(self, name: str) -> bytes:
    """Return the content of ``name``, from the top backend when it has it."""
    return self._pick(name).read(name)

  def open(self, name: str) -> IO[bytes]:
    """Open ``name``, from the top backend when it has it."""
    return self._pick(name).open(name)

  def close(self) -> None:
    """Close both backends."""
    self._top.close()
    self._base.close()

  def _pick(self, name: str) -> Backend:
    """Return the backend that holds ``name``: the top one when it does."""
    return self._top if name in self._top.names() else self._base


class DirBackend:
  """A bundle laid out as a directory (or the directory of a single-file manifest).

  Symbolic links are refused: a name that resolves outside the root, or is itself a link, raises
  ``E404``. Only the manifest and ``assets/`` are listed.

  Parameters
  ----------
  root : pathlib.Path
      The bundle directory.
  """

  def __init__(self, root: Path) -> None:
    self.root = root
    self._real_root = root.resolve()

  def names(self) -> list[str]:
    """Return the manifest and asset file names found on disk, sorted."""
    found: list[str] = []
    for manifest in (MANIFEST_NAME, *YAML_MANIFEST_NAMES):
      if (self.root / manifest).is_file():
        found.append(manifest)
    assets = self.root / ASSET_ROOT
    if assets.is_dir():
      for dirpath, dirnames, filenames in os.walk(assets, followlinks=False):
        dirnames.sort()
        base = Path(dirpath).relative_to(self.root)
        found.extend((base / filename).as_posix() for filename in filenames)
    return sorted(found)

  def size(self, name: str) -> int:
    """Return the size of ``name`` in bytes."""
    return self._path(name).stat().st_size

  def read(self, name: str) -> bytes:
    """Return the content of ``name``."""
    return self._path(name).read_bytes()

  def open(self, name: str) -> IO[bytes]:
    """Open ``name`` for reading."""
    return self._path(name).open('rb')

  def stat_hash(self, name: str) -> tuple[str, int]:
    """Return ``(sha256, bytes)`` of ``name`` without reading it whole."""
    return sha256_file(self._path(name))

  def close(self) -> None:
    """Do nothing; files are opened per call."""

  def _path(self, name: str) -> Path:
    """Resolve ``name`` under the root, refusing links and escapes; raise if it is absent."""
    path = self.root.joinpath(*PurePosixPath(name).parts)
    if path.is_symlink() or not path.resolve().is_relative_to(self._real_root):
      raise BundleError(f'{name} is a symbolic link or leaves the bundle directory', code='E404')
    if not path.is_file():
      raise FileNotFoundError(name)
    return path


class ZipBackend:
  """A bundle stored as a ZIP archive, checked before use.

  Every entry name must be a safe relative path (no absolute path, ``..``, backslash, drive
  letter or NUL), entries may not be symbolic links, encrypted or duplicated, and the declared
  uncompressed sizes must stay under ``max_bytes`` and ``MAX_ENTRIES``.

  Parameters
  ----------
  path : pathlib.Path
      The ``.zip`` file.
  max_bytes : int, default=DEFAULT_MAX_BYTES
      Cap on the sum of uncompressed sizes.

  Raises
  ------
  BundleError
      With code ``E406`` for an unreadable archive, ``E407`` for a rejected entry or ``E405``
      for a bundle over the cap.
  """

  def __init__(self, path: Path, *, max_bytes: int = DEFAULT_MAX_BYTES) -> None:
    try:
      self._zip = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as exc:
      raise BundleError(f'{path} is not a readable ZIP archive: {exc}', code='E406') from exc
    try:
      self._index = _check_entries(self._zip.infolist(), max_bytes)
    except BundleError:
      self._zip.close()
      raise

  def names(self) -> list[str]:
    """Return the file names (not directories), sorted."""
    return sorted(self._index)

  def size(self, name: str) -> int:
    """Return the declared uncompressed size of ``name``."""
    return self._info(name).file_size

  def read(self, name: str) -> bytes:
    """Return the content of ``name``; the CRC is checked by ``zipfile``."""
    try:
      return self._zip.read(self._info(name))
    except zipfile.BadZipFile as exc:
      raise BundleError(f'{name} is corrupt in the archive: {exc}', code='E407') from exc

  def open(self, name: str) -> IO[bytes]:
    """Open ``name`` for streaming."""
    return self._zip.open(self._info(name))

  def close(self) -> None:
    """Close the archive."""
    self._zip.close()

  def _info(self, name: str) -> zipfile.ZipInfo:
    """Return the entry of ``name`` or raise ``FileNotFoundError``."""
    try:
      return self._index[name]
    except KeyError:
      raise FileNotFoundError(name) from None


def zip_name_problem(name: str) -> str | None:
  """Explain why an archive entry name is unsafe or unacceptable.

  Parameters
  ----------
  name : str
      An entry name as stored in the ZIP.

  Returns
  -------
  str or None
      A reason, or None when the name is a safe relative path that is either the manifest or
      under ``assets/`` with an acceptable asset path, or lies outside both (ignored).
  """
  if not name or '\x00' in name:
    return 'empty name or NUL character'
  if '\\' in name:
    return 'backslash in name'
  if name.startswith('/') or (len(name) > 1 and name[1] == ':'):
    return 'absolute path or drive letter'
  parts = name.rstrip('/').split('/')
  if any(part in ('', '.', '..') for part in parts):
    return 'empty, "." or ".." path segment (zip-slip)'
  if parts[0] == ASSET_ROOT and not name.endswith('/'):
    return asset_path_problem(name)
  return None


def _check_entries(infos: list[zipfile.ZipInfo], max_bytes: int) -> dict[str, zipfile.ZipInfo]:
  """Validate every entry of an archive and index the files by name."""
  if len(infos) > MAX_ENTRIES:
    raise BundleError(
      f'archive has {len(infos):,} entries, over the limit of {MAX_ENTRIES:,}', code='E405'
    )
  index: dict[str, zipfile.ZipInfo] = {}
  folded: set[str] = set()
  total = 0
  for info in infos:
    name = info.filename
    problem = zip_name_problem(name)
    if problem is not None:
      raise BundleError(f'archive entry {name!r} rejected: {problem}', code='E407')
    mode = info.external_attr >> 16
    if stat.S_IFMT(mode) == _SYMLINK_MODE:
      raise BundleError(f'archive entry {name!r} is a symbolic link', code='E407')
    if info.flag_bits & 0x1:
      raise BundleError(f'archive entry {name!r} is encrypted', code='E407')
    if info.is_dir():
      continue
    if name.casefold() in folded:
      raise BundleError(f'archive entry {name!r} is duplicated (case-insensitively)', code='E407')
    folded.add(name.casefold())
    total += info.file_size
    if total > max_bytes:
      raise BundleError(
        f'archive holds more than {max_bytes:,} bytes uncompressed (the size cap)',
        code='E405',
        hint='Raise the cap with --max-size, or aggregate the data before packing.',
      )
    index[name] = info
  return index
