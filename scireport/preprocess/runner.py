"""Run the pre-processing steps of a bundle (ADR-0006).

:func:`preprocess_bundle` plans the steps (nothing runs if the plan has a problem), runs them in
dependency order, reuses cached results, and returns a new bundle: the input's files plus what
the steps made, with the figures and tables at the keys the steps name. The input bundle is not
changed. The assets of a run go to a work directory when one is given;
:func:`write_back` replaces the input with the result.
"""

from __future__ import annotations

import importlib.util
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from scireport.bundle.reader import Bundle
from scireport.bundle.writer import write_bundle
from scireport.errors import (
  Issue,
  MissingDependencyError,
  PreprocessError,
  PreprocessRunError,
  ScireportError,
  SpecError,
)
from scireport.hashing import sha256_bytes
from scireport.logging_utils import get_logger, log_kv
from scireport.preprocess.cache import (
  Cache,
  CacheEntry,
  cache_key,
  default_cache_dir,
  value_hash,
)
from scireport.preprocess.context import Context, derive_seed
from scireport.preprocess.params import canonical_params
from scireport.preprocess.plan import PlannedStep, plan_steps
from scireport.spec.kinds import Envelope, Value
from scireport.spec.manifest import check_manifest

log = get_logger(__name__)

RECORD_NAME = 'preprocess.json'
"""Name of the run record written to the work directory."""

EXTRA_MODULES: dict[str, tuple[str, ...]] = {'astro': ('astropy', 'astropy_healpix')}
"""Extra name to the modules a pre-processor that ``requires`` it imports."""

_VALUE: TypeAdapter[Envelope] = TypeAdapter(Value)


@dataclass(frozen=True)
class StepRecord:
  """What happened to one step.

  Parameters
  ----------
  label : str
      The step's id, or its name and position.
  name : str
      Registered pre-processor name.
  version : int
      The version that ran.
  cache : {'hit', 'miss', 'off'}
      Whether the result came from the cache, was computed, or the cache was not used.
  key : str
      The cache key (hex SHA-256).
  outputs : dict
      Output port to the value key written.
  """

  label: str
  name: str
  version: int
  cache: str
  key: str
  outputs: dict[str, str]


@dataclass(frozen=True)
class PreprocessResult:
  """The outcome of :func:`preprocess_bundle`.

  Parameters
  ----------
  bundle : Bundle
      The input's files plus the steps' results. It shares the input's file handle.
  steps : list of StepRecord
      One record per step, in the order they ran.
  """

  bundle: Bundle
  steps: list[StepRecord]

  def to_dict(self) -> dict[str, Any]:
    """Return the run as JSON-ready data (no times, so two runs give the same record).

    Returns
    -------
    dict
        ``{'steps': [...]}`` with the label, name, version, cache status, key and outputs.
    """
    return {
      'steps': [
        {
          'label': step.label,
          'name': step.name,
          'version': step.version,
          'cache': step.cache,
          'key': step.key,
          'outputs': step.outputs,
        }
        for step in self.steps
      ]
    }


def preprocess_bundle(
  bundle: Bundle,
  *,
  work_dir: Path | None = None,
  cache_dir: Path | None = None,
  allow_import: bool = False,
  layout: str | None = None,
  seed: int = 0,
  use_cache: bool = True,
) -> PreprocessResult:
  """Run the ``preprocess`` steps of a bundle and return the bundle with their results.

  Parameters
  ----------
  bundle : Bundle
      The input bundle; it is not modified.
  work_dir : pathlib.Path or None, default=None
      Where the new asset files and the run record are written; None keeps them in memory.
  cache_dir : pathlib.Path or None, default=None
      The cache directory; see :func:`~scireport.preprocess.cache.default_cache_dir`.
  allow_import : bool, default=False
      Let steps name ``module:function`` (runs code from the importable module).
  layout : str or None, default=None
      The layout whose style the figures use; the manifest's ``render.layout``, else ``default``.
  seed : int, default=0
      The base seed; each step gets one derived from it and its label.
  use_cache : bool, default=True
      Reuse and store cached results.

  Returns
  -------
  PreprocessResult
      The bundle with the steps' values and the per-step record. A bundle with no steps is
      returned as it is.

  Raises
  ------
  PreprocessError
      With every problem of the plan (``E601`` to ``E605``), before anything runs.
  MissingDependencyError
      With ``E607`` when a step needs an extra that is not installed.
  PreprocessRunError
      With ``E606`` when a pre-processor raises while it runs.
  SpecError
      When the results make the manifest inconsistent (for example a key clash, ``E102``).
  """
  manifest = bundle.manifest
  if not manifest.preprocess:
    return PreprocessResult(bundle, [])
  plan = plan_steps(manifest, allow_import=allow_import)
  _check_extras(plan)
  chosen_layout = layout or manifest.render.layout or 'default'
  style = _style_hash(chosen_layout)
  cache = Cache(cache_dir or default_cache_dir()) if use_cache else None
  produced: dict[str, Envelope] = {}
  assets: dict[str, bytes] = {}
  records: list[StepRecord] = []
  for planned in plan:
    record = _run_step(planned, bundle, produced, assets, chosen_layout, seed, style, cache)
    records.append(record)
  merged = manifest.model_copy(update={'values': {**manifest.values, **produced}})
  problems = check_manifest(merged)
  if problems:
    raise SpecError(problems)
  result = PreprocessResult(bundle.with_files(merged, assets), records)
  if work_dir is not None:
    _write_work_dir(work_dir, assets, result)
  log_kv(
    log,
    'pre-processing done',
    {
      'steps': len(records),
      'cached': sum(r.cache == 'hit' for r in records),
      'assets': len(assets),
    },
  )
  return result


def write_back(result: PreprocessResult, destination: Path) -> Path:
  """Replace a bundle on disk with the pre-processed one.

  The ``preprocess`` steps stay in the manifest: running them again is a cache hit and replaces
  the same keys.

  Parameters
  ----------
  result : PreprocessResult
      What :func:`preprocess_bundle` returned for the bundle at ``destination``.
  destination : pathlib.Path
      The bundle to overwrite (a directory, a ZIP archive, or a manifest file).

  Returns
  -------
  pathlib.Path
      ``destination``.
  """
  return write_bundle(result.bundle, destination, form=result.bundle.form, overwrite=True)


def _run_step(
  planned: PlannedStep,
  bundle: Bundle,
  produced: dict[str, Envelope],
  assets: dict[str, bytes],
  layout: str,
  seed: int,
  style: str,
  cache: Cache | None,
) -> StepRecord:
  """Run or restore one step and add its values and assets to ``produced`` and ``assets``."""
  entry = planned.entry
  step_seed = derive_seed(seed, planned.label)
  ctx = Context(
    bundle=bundle,
    produced=produced,
    produced_assets=assets,
    outputs=planned.outputs,
    layout=layout,
    seed=step_seed,
    name=entry.name,
  )
  hashes = {port: value_hash(ctx.value(key)) for port, key in planned.inputs.items()}
  key = cache_key(
    name=entry.name,
    version=entry.version,
    params=canonical_params(entry, planned.params),
    inputs=hashes,
    outputs=planned.outputs,
    seed=step_seed,
    style_hash=style,
  )
  status = 'off'
  hit = cache.load(key) if cache is not None else None
  if hit is not None:
    status = 'hit'
    values, files = hit.values, hit.assets
    log.info('%s: cached (%s)', planned.label, key[:12])
  else:
    status = 'miss' if cache is not None else 'off'
    values = _execute(planned, ctx)
    files = ctx.take_assets()
    if cache is not None:
      cache.store(key, CacheEntry(values=values, assets=files))
  produced.update(values)
  assets.update(files)
  return StepRecord(
    label=planned.label,
    name=entry.name,
    version=entry.version,
    cache=status,
    key=key,
    outputs=dict(planned.outputs),
  )


def _execute(planned: PlannedStep, ctx: Context) -> dict[str, Envelope]:
  """Call the pre-processor and return its values keyed by output key."""
  entry = planned.entry
  arguments: dict[str, Any] = {}
  for port, spec in entry.inputs.items():
    key = planned.inputs.get(port)
    if key is None:
      arguments[port] = None
    elif spec.kind == 'table':
      arguments[port] = ctx.load_table(key)
    else:
      arguments[port] = ctx.value(key)
  log.info('%s: running %s', planned.label, entry.ref)
  try:
    with ctx.mplstyle():
      result = entry.func(ctx, **arguments, **planned.params)
  except ScireportError:
    raise
  except Exception as exc:
    raise PreprocessRunError(
      f'{planned.label} ({entry.ref}) failed: {type(exc).__name__}: {exc}', code='E606'
    ) from exc
  return _collect(planned, result)


def _collect(planned: PlannedStep, result: Any) -> dict[str, Envelope]:
  """Check what a pre-processor returned against its output ports."""
  entry = planned.entry
  pointer = f'/preprocess/{planned.index}'
  if not isinstance(result, Mapping):
    raise PreprocessError(
      [Issue('E603', f'{entry.ref} must return a dict of values by output port', pointer)]
    )
  issues: list[Issue] = []
  values: dict[str, Envelope] = {}
  for port, raw in result.items():
    if port not in entry.outputs:
      issues.append(Issue('E603', f'{entry.ref} returned an undeclared port {port!r}', pointer))
      continue
    value = _VALUE.validate_python(raw)
    if not entry.outputs[port].accepts(value.kind):
      issues.append(
        Issue(
          'E603',
          f'{entry.ref}: port {port!r} must be a {entry.outputs[port].kind}, got a {value.kind}',
          pointer,
          expected=entry.outputs[port].kind,
          found=value.kind,
        )
      )
      continue
    values[planned.outputs[port]] = value
  for port, spec in entry.outputs.items():
    if port not in result and not spec.optional:
      issues.append(Issue('E603', f'{entry.ref} returned no value for port {port!r}', pointer))
  if issues:
    raise PreprocessError(issues)
  return values


def _check_extras(plan: list[PlannedStep]) -> None:
  """Raise ``E607`` when a step needs an extra whose packages are not installed."""
  for planned in plan:
    extra = planned.entry.requires
    if extra is None:
      continue
    missing = [m for m in EXTRA_MODULES.get(extra, ()) if importlib.util.find_spec(m) is None]
    if missing:
      raise MissingDependencyError(
        f'{planned.entry.ref} needs {", ".join(missing)}, which is not installed',
        code='E607',
        hint=f'Install the extra: pip install "scireport[{extra}]".',
      )


def _style_hash(layout: str) -> str:
  """Hash the style and palette files of a layout, which decide how a figure looks."""
  from scireport.render.registry import load_layout
  from scireport.styles import mplstyle_path

  loaded = load_layout(layout)
  parts = [mplstyle_path(layout).read_bytes()]
  if loaded.definition.palette:
    parts.append((loaded.root / loaded.definition.palette).read_bytes())
  return sha256_bytes(b'\0'.join(parts))


def _write_work_dir(work_dir: Path, assets: Mapping[str, bytes], result: PreprocessResult) -> None:
  """Write the assets of a run and its record under ``work_dir``."""
  for path, data in sorted(assets.items()):
    target = work_dir.joinpath(*path.split('/'))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
  work_dir.mkdir(parents=True, exist_ok=True)
  (work_dir / RECORD_NAME).write_text(
    json.dumps(result.to_dict(), indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n'
  )
