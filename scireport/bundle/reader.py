"""Open a report bundle in any of its three forms and read its assets lazily (ADR-0001).

The forms are a directory (``scireport.json`` or, hand-authored, ``scireport.yaml``), a ZIP
archive, and a single manifest file (``.json`` or ``.yaml``) whose assets, if any, sit next to it
under ``assets/``. Only the manifest is parsed on opening; assets are read, and checked against
their SHA-256 and size, when asked for.
"""

from __future__ import annotations

import zipfile
from collections.abc import Mapping
from pathlib import Path
from types import TracebackType
from typing import IO, TYPE_CHECKING, Literal

from scireport.bundle.backends import (
  DEFAULT_MAX_BYTES,
  MANIFEST_NAME,
  YAML_MANIFEST_NAMES,
  Backend,
  DirBackend,
  ZipBackend,
)
from scireport.bundle.textio import parse_manifest_text
from scireport.errors import BundleError, Issue
from scireport.hashing import CHUNK_BYTES, sha256_bytes
from scireport.logging_utils import get_logger
from scireport.spec.assets import ASSET_ROOT, AssetRef
from scireport.spec.kinds import Envelope, TableValue, TextValue
from scireport.spec.manifest import Manifest, parse_manifest
from scireport.spec.walk import iter_assets

if TYPE_CHECKING:
  import pyarrow as pa

log = get_logger(__name__)

Form = Literal['directory', 'zip', 'file']
_YAML_SUFFIXES = ('.yaml', '.yml')


class Bundle:
  """An opened report bundle: its manifest plus lazy access to its assets.

  Use as a context manager, or call :meth:`close`, so that a ZIP file handle is released.

  Parameters
  ----------
  manifest : Manifest
      The validated manifest.
  backend : Backend
      Where the files live.
  form : {'directory', 'zip', 'file'}
      How the bundle is stored.
  source : pathlib.Path or None, default=None
      The path it was opened from; None for a bundle built in memory.
  """

  def __init__(
    self, manifest: Manifest, backend: Backend, *, form: Form, source: Path | None = None
  ) -> None:
    self.manifest = manifest
    self.form = form
    self.source = source
    self._backend = backend
    self._refs: dict[str, AssetRef] = {ref.path: ref for _, ref in iter_assets(manifest)}

  def __enter__(self) -> Bundle:
    """Return the bundle."""
    return self

  def __exit__(
    self,
    exc_type: type[BaseException] | None,
    exc: BaseException | None,
    tb: TracebackType | None,
  ) -> None:
    """Close the bundle."""
    self.close()

  def close(self) -> None:
    """Release the file handle of a ZIP bundle; safe to call twice."""
    self._backend.close()

  def with_manifest(self, manifest: Manifest) -> Bundle:
    """Return a bundle with another manifest over the same files (for example a pinned one).

    The result shares the file handle of this bundle: close only one of them.

    Parameters
    ----------
    manifest : Manifest
        The manifest; it must reference the same assets.

    Returns
    -------
    Bundle
        A bundle with ``manifest`` and this bundle's files.
    """
    return Bundle(manifest, self._backend, form=self.form, source=self.source)

  def with_files(self, manifest: Manifest, files: Mapping[str, bytes]) -> Bundle:
    """Return a bundle with another manifest and some added or replaced files on top of this one.

    Used by pre-processing: the result holds the input bundle's files plus the assets the
    pre-processors made. The result shares the file handle of this bundle: close only one of
    them.

    Parameters
    ----------
    manifest : Manifest
        The manifest; it must reference every asset, old and new.
    files : mapping
        Bundle-relative path to content of the files to add; they shadow files of the same name.

    Returns
    -------
    Bundle
        A bundle over this bundle's files and ``files``.
    """
    from scireport.bundle.backends import MemoryBackend, OverlayBackend

    backend = OverlayBackend(self._backend, MemoryBackend(dict(files)))
    return Bundle(manifest, backend, form=self.form, source=self.source)

  @property
  def asset_paths(self) -> list[str]:
    """Paths of the assets the manifest references, sorted, each once."""
    return sorted(self._refs)

  def asset_ref(self, path: str) -> AssetRef:
    """Return the manifest's reference for an asset path.

    Parameters
    ----------
    path : str
        An asset path such as ``assets/tables/x.parquet``.

    Returns
    -------
    AssetRef
        Its declared hash and size.

    Raises
    ------
    BundleError
        With code ``E401`` when the manifest does not reference ``path``.
    """
    try:
      return self._refs[path]
    except KeyError:
      raise BundleError(f'the manifest does not reference an asset {path!r}', code='E401') from None

  def read_asset(self, ref: AssetRef | str) -> bytes:
    """Read one asset and check it against its declared size and SHA-256.

    Parameters
    ----------
    ref : AssetRef or str
        The reference, or the asset path of a referenced asset.

    Returns
    -------
    bytes
        The file content.

    Raises
    ------
    BundleError
        With code ``E401`` (missing), ``E403`` (size differs) or ``E402`` (hash differs).
    """
    ref = self.asset_ref(ref) if isinstance(ref, str) else ref
    try:
      size = self._backend.size(ref.path)
    except FileNotFoundError:
      raise BundleError(f'asset {ref.path} is missing from the bundle', code='E401') from None
    if size != ref.bytes:
      raise BundleError(
        f'asset {ref.path} is {size:,} bytes, the manifest says {ref.bytes:,}', code='E403'
      )
    data = self._backend.read(ref.path)
    digest = sha256_bytes(data)
    if digest != ref.sha256:
      raise BundleError(
        f'asset {ref.path} has sha256 {digest[:12]}…, the manifest says {ref.sha256[:12]}…',
        code='E402',
      )
    return data

  def open_asset(self, ref: AssetRef | str) -> IO[bytes]:
    """Open one asset for streaming, without checking its hash.

    Parameters
    ----------
    ref : AssetRef or str
        The reference, or the asset path of a referenced asset.

    Returns
    -------
    IO of bytes
        A binary stream the caller must close.

    Raises
    ------
    BundleError
        With code ``E401`` when the asset is missing.
    """
    path = ref if isinstance(ref, str) else ref.path
    self.asset_ref(path)
    try:
      return self._backend.open(path)
    except FileNotFoundError:
      raise BundleError(f'asset {path} is missing from the bundle', code='E401') from None

  def read_text(self, key: str) -> str:
    """Return the text of a ``text`` value, inline or from its asset.

    Parameters
    ----------
    key : str
        Key of a ``text`` value.

    Returns
    -------
    str
        The content, decoded as UTF-8.

    Raises
    ------
    BundleError
        With code ``E103`` for an unknown key or ``E202`` when the value is not text.
    """
    value = self._value(key)
    if not isinstance(value, TextValue):
      raise BundleError(f'{key!r} is a {value.kind}, not text', code='E202')
    if value.text is not None:
      return value.text
    assert value.asset is not None
    return self.read_asset(value.asset).decode('utf-8')

  def read_table(self, key: str) -> pa.Table:
    """Return a ``table`` value as a pyarrow table.

    Parameters
    ----------
    key : str
        Key of a ``table`` value.

    Returns
    -------
    pyarrow.Table
        The data: Parquet and CSV files are read, an inline table is converted.

    Raises
    ------
    BundleError
        With code ``E103`` for an unknown key or ``E202`` when the value is not a table.
    """
    import pyarrow as pa
    import pyarrow.csv as pacsv
    import pyarrow.parquet as pq

    value = self._value(key)
    if not isinstance(value, TableValue):
      raise BundleError(f'{key!r} is a {value.kind}, not a table', code='E202')
    if value.rows is not None:
      names = [column.name for column in value.columns]
      return pa.table({name: [row[i] for row in value.rows] for i, name in enumerate(names)})
    assert value.asset is not None
    reader = pa.BufferReader(self.read_asset(value.asset))
    return pq.read_table(reader) if value.format == 'parquet' else pacsv.read_csv(reader)

  def verify(self) -> list[Issue]:
    """Check every referenced asset and report every problem at once.

    Returns
    -------
    list of Issue
        ``E401`` for a missing file, ``E403`` for a wrong size, ``E402`` for a wrong hash and
        ``W402`` for an asset file that no value references. Empty when the bundle is sound.
    """
    import hashlib

    issues: list[Issue] = []
    pointers = {ref.path: pointer for pointer, ref in iter_assets(self.manifest)}
    for path in self.asset_paths:
      ref, pointer = self._refs[path], pointers[path]
      try:
        actual = self._backend.size(path)
      except FileNotFoundError:
        issues.append(Issue('E401', f'asset {path} is missing from the bundle', pointer=pointer))
        continue
      except BundleError as exc:
        issues.append(Issue(exc.code, exc.message, pointer=pointer))
        continue
      if actual != ref.bytes:
        issues.append(
          Issue(
            'E403', f'asset {path} has the wrong size', pointer, None, str(ref.bytes), str(actual)
          )
        )
        continue
      digest = hashlib.sha256()
      with self._backend.open(path) as handle:
        while chunk := handle.read(CHUNK_BYTES):
          digest.update(chunk)
      if digest.hexdigest() != ref.sha256:
        issues.append(
          Issue(
            'E402',
            f'asset {path} does not match its sha256',
            pointer,
            None,
            ref.sha256[:12] + '…',
            digest.hexdigest()[:12] + '…',
          )
        )
    declared = set(self._refs)
    for name in self._backend.names():
      if name.startswith(f'{ASSET_ROOT}/') and name not in declared:
        issues.append(Issue('W402', f'file {name} is not referenced by any value'))
    return issues

  def _value(self, key: str) -> Envelope:
    """Return the value at ``key`` or raise ``E103``."""
    try:
      return self.manifest.values[key]
    except KeyError:
      raise BundleError(f'no value with key {key!r}', code='E103') from None


def open_bundle(path: Path | str, *, max_bytes: int = DEFAULT_MAX_BYTES) -> Bundle:
  """Open a bundle from a directory, a ZIP archive or a single manifest file.

  A ZIP archive is sealed: every asset reference must carry its hash. A directory or single
  file is hand-authorable: a reference may omit ``sha256`` and ``bytes`` (or be a bare path) and
  they are computed from the files, and the manifest may be YAML.

  Parameters
  ----------
  path : pathlib.Path or str
      The bundle.
  max_bytes : int, default=DEFAULT_MAX_BYTES
      Cap on the total uncompressed size of a ZIP bundle.

  Returns
  -------
  Bundle
      The opened bundle; the caller closes it.

  Raises
  ------
  BundleError
      With an ``E4xx`` code when ``path`` is not a bundle or is unsafe or too large.
  SpecVersionError
      When the manifest's spec version cannot be read (``E501`` to ``E503``).
  SpecError
      Carrying every issue found when the manifest is invalid.
  """
  path = Path(path)
  if path.is_dir():
    root, manifest_path = path, _find_manifest(path)
    backend: Backend = DirBackend(root)
    form: Form = 'directory'
  elif path.is_file() and zipfile.is_zipfile(path):
    zip_backend = ZipBackend(path, max_bytes=max_bytes)
    try:
      return _open_zip(zip_backend, path)
    except BaseException:
      zip_backend.close()
      raise
  elif path.is_file() and path.suffix.lower() in ('.json', *_YAML_SUFFIXES):
    root, manifest_path = path.parent, path
    backend = DirBackend(root)
    form = 'file'
  elif not path.exists():
    raise BundleError(f'{path} does not exist', code='E406')
  else:
    raise BundleError(
      f'{path} is not a bundle: expected a directory, a .zip archive or a .json/.yaml manifest',
      code='E406',
    )
  data = manifest_path.read_bytes()
  raw = parse_manifest_text(
    data, yaml_format=manifest_path.suffix.lower() in _YAML_SUFFIXES, origin=str(manifest_path)
  )
  assert isinstance(backend, DirBackend)
  manifest = parse_manifest(raw, resolver=_dir_resolver(backend))
  log.debug('opened %s bundle %s with %d values', form, path, len(manifest.values))
  return Bundle(manifest, backend, form=form, source=path)


def _find_manifest(root: Path) -> Path:
  """Locate the manifest file in a bundle directory."""
  candidates = [root / name for name in (MANIFEST_NAME, *YAML_MANIFEST_NAMES)]
  present = [candidate for candidate in candidates if candidate.is_file()]
  if not present:
    raise BundleError(
      f'{root} has no {MANIFEST_NAME} (or scireport.yaml): not a bundle directory', code='E406'
    )
  if len(present) > 1:
    raise BundleError(
      f'{root} has more than one manifest ({", ".join(p.name for p in present)})',
      code='E409',
      hint='Keep one: the JSON manifest, or a YAML one for hand-authored directories.',
    )
  return present[0]


def _open_zip(backend: ZipBackend, path: Path) -> Bundle:
  """Parse the manifest of an opened ZIP backend and wrap it."""
  names = backend.names()
  if any(name in YAML_MANIFEST_NAMES for name in names) and MANIFEST_NAME not in names:
    raise BundleError(
      f'{path} holds a YAML manifest; YAML is accepted only in hand-authored directories',
      code='E409',
      hint='Run "scireport pack" on the directory to produce a ZIP with a JSON manifest.',
    )
  if MANIFEST_NAME not in names:
    raise BundleError(f'{path} has no {MANIFEST_NAME} at its root: not a bundle', code='E406')
  raw = parse_manifest_text(
    backend.read(MANIFEST_NAME), yaml_format=False, origin=f'{path}!{MANIFEST_NAME}'
  )
  manifest = parse_manifest(raw)
  log.debug('opened zip bundle %s with %d values', path, len(manifest.values))
  return Bundle(manifest, backend, form='zip', source=path)


def _dir_resolver(backend: DirBackend) -> object:
  """Return the asset resolver used to complete references in hand-authored directories."""
  return backend.stat_hash
