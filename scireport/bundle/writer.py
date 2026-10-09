"""Write a bundle as a directory, a byte-reproducible ZIP, or a single manifest file (ADR-0001).

Output is deterministic: the manifest is canonical JSON, ZIP entries are sorted with a fixed 1980
timestamp, fixed permissions and creator system, and media that is already compressed is STORED.
The compressed bytes of the DEFLATED entries depend on the zlib build, so identical bytes are
guaranteed for the same Python and zlib; the manifest's asset hashes do not depend on it. Files
are written to a temporary name and moved into place, so an interrupted write never leaves a
half-written bundle.
"""

from __future__ import annotations

import secrets
import shutil
import zipfile
from pathlib import Path
from typing import Literal

from scireport.bundle.backends import (
  DEFAULT_MAX_BYTES,
  MANIFEST_NAME,
  YAML_MANIFEST_NAMES,
)
from scireport.bundle.reader import Bundle
from scireport.errors import BundleError
from scireport.logging_utils import get_logger
from scireport.spec.manifest import manifest_to_json

log = get_logger(__name__)

WriteForm = Literal['directory', 'zip', 'file']

ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)
"""Timestamp of every ZIP entry (the earliest the format can store)."""

STORED_SUFFIXES = frozenset(
  ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.pdf', '.parquet', '.zip', '.gz', '.zst', '.xz']
)
"""Suffixes of already-compressed media, stored without deflating."""

_FILE_MODE = (0o100644) << 16
_UNIX = 3
_DEFLATE_LEVEL = 9


def infer_form(dest: Path) -> WriteForm:
  """Choose the storage form from a destination path.

  Parameters
  ----------
  dest : pathlib.Path
      ``*.zip`` gives a ZIP, ``*.json`` a single manifest file, anything else a directory.

  Returns
  -------
  {'directory', 'zip', 'file'}
      The form.
  """
  suffix = dest.suffix.lower()
  return 'zip' if suffix == '.zip' else 'file' if suffix == '.json' else 'directory'


def write_bundle(
  bundle: Bundle,
  dest: Path | str,
  *,
  form: WriteForm | None = None,
  overwrite: bool = False,
  max_bytes: int = DEFAULT_MAX_BYTES,
) -> Path:
  """Write a bundle to ``dest``, copying exactly the assets its manifest references.

  Every asset is read through :meth:`Bundle.read_asset`, so a bundle with a wrong hash or size
  is refused rather than copied. Files in the source that no value references are dropped.

  Parameters
  ----------
  bundle : Bundle
      The bundle to write (from :func:`~scireport.bundle.reader.open_bundle` or a ``Report``).
  dest : pathlib.Path or str
      Destination path.
  form : {'directory', 'zip', 'file'} or None, default=None
      Storage form; inferred from ``dest`` when None. ``file`` needs a bundle without assets.
  overwrite : bool, default=False
      Replace an existing destination. A directory is only replaced when it is empty or already
      looks like a bundle.
  max_bytes : int, default=DEFAULT_MAX_BYTES
      Cap on the total uncompressed size.

  Returns
  -------
  pathlib.Path
      ``dest``.

  Raises
  ------
  BundleError
      With code ``E410`` (destination exists or cannot be written), ``E405`` (over the cap),
      ``E409`` (single file with assets), ``E404`` (two assets differ only by case), or an
      asset error from reading the source.
  """
  dest = Path(dest)
  form = form or infer_form(dest)
  files = _collect(bundle)
  total = sum(len(data) for data in files.values())
  if total > max_bytes:
    raise BundleError(
      f'the bundle is {total:,} bytes uncompressed, over the cap of {max_bytes:,}', code='E405'
    )
  if form == 'file' and len(files) > 1:
    raise BundleError(
      'a single-file manifest cannot carry assets', code='E409', hint='Write a ZIP or a directory.'
    )
  _check_destination(dest, form, overwrite)
  dest.parent.mkdir(parents=True, exist_ok=True)
  if form == 'zip':
    _write_zip(files, dest)
  elif form == 'file':
    _write_file(files[MANIFEST_NAME], dest)
  else:
    _write_directory(files, dest)
  log.info('wrote %s bundle %s: %d files, %s bytes', form, dest, len(files), f'{total:,}')
  return dest


def _collect(bundle: Bundle) -> dict[str, bytes]:
  """Gather the manifest and the verified assets, keyed by bundle-relative name."""
  files: dict[str, bytes] = {MANIFEST_NAME: manifest_to_json(bundle.manifest).encode('utf-8')}
  for path in bundle.asset_paths:
    files[path] = bundle.read_asset(path)
  folded: dict[str, str] = {}
  for name in files:
    other = folded.setdefault(name.casefold(), name)
    if other != name:
      raise BundleError(
        f'assets {other!r} and {name!r} differ only by case; they would collide on some systems',
        code='E404',
      )
  return files


def _check_destination(dest: Path, form: WriteForm, overwrite: bool) -> None:
  """Refuse to clobber anything the caller did not ask to replace."""
  if not dest.exists():
    return
  if not overwrite:
    raise BundleError(
      f'{dest} already exists', code='E410', hint='Pass --force (or overwrite=True) to replace it.'
    )
  if form == 'directory':
    if not dest.is_dir():
      raise BundleError(f'{dest} exists and is not a directory', code='E410')
    looks_like_bundle = any(
      (dest / name).is_file() for name in (MANIFEST_NAME, *YAML_MANIFEST_NAMES)
    )
    if any(dest.iterdir()) and not looks_like_bundle:
      raise BundleError(
        f'{dest} is not empty and does not look like a bundle; refusing to replace it', code='E410'
      )
  elif dest.is_dir():
    raise BundleError(f'{dest} is a directory', code='E410')


def _write_zip(files: dict[str, bytes], dest: Path) -> None:
  """Write a deterministic ZIP and move it into place."""
  tmp = _temp_sibling(dest)
  try:
    with tmp.open('xb') as handle, zipfile.ZipFile(handle, 'w', allowZip64=True) as archive:
      for name in sorted(files):
        info = zipfile.ZipInfo(name, date_time=ZIP_EPOCH)
        info.create_system = _UNIX
        info.external_attr = _FILE_MODE
        info.compress_type = (
          zipfile.ZIP_STORED
          if Path(name).suffix.lower() in STORED_SUFFIXES
          else zipfile.ZIP_DEFLATED
        )
        archive.writestr(info, files[name], compresslevel=_DEFLATE_LEVEL)
    tmp.replace(dest)
  except BaseException:
    tmp.unlink(missing_ok=True)
    raise


def _write_file(data: bytes, dest: Path) -> None:
  """Write a single manifest file atomically."""
  tmp = _temp_sibling(dest)
  try:
    tmp.write_bytes(data)
    tmp.replace(dest)
  except BaseException:
    tmp.unlink(missing_ok=True)
    raise


def _write_directory(files: dict[str, bytes], dest: Path) -> None:
  """Write a bundle directory into a sibling temporary directory, then move it into place."""
  tmp = _temp_sibling(dest)
  tmp.mkdir()
  try:
    for name, data in files.items():
      target = tmp.joinpath(*name.split('/'))
      target.parent.mkdir(parents=True, exist_ok=True)
      target.write_bytes(data)
    if dest.exists():
      shutil.rmtree(dest)
    tmp.replace(dest)
  except BaseException:
    shutil.rmtree(tmp, ignore_errors=True)
    raise


def _temp_sibling(dest: Path) -> Path:
  """Return an unused hidden name next to ``dest``.

  Unlike ``tempfile.mkstemp`` this creates nothing, so the file or directory made under the name
  gets the permissions the user's umask gives any other output.
  """
  return dest.with_name(f'.{dest.name}.{secrets.token_hex(4)}.tmp')
