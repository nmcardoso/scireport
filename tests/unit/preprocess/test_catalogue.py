"""The built-in catalogue as a whole: what is registered, documented and importable."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from scireport.preprocess import list_preprocessors, params_schema

DOC = Path(__file__).resolve().parents[3] / 'docs' / 'preprocessors.md'
CORE = {
  'table_profile', 'bar', 'stacked_shares', 'histogram', 'separation_histogram', 'funnel',
  'density_scatter', 'metric_scatter', 'distribution', 'corner', 'pvalue_strip',
  'achieved_vs_target', 'duration_bars', 'split_marginals', 'split_balance', 'qq', 'pp', 'heatmap',
}  # fmt: skip
ASTRO = {
  'sky_density', 'footprint', 'sky_grid', 'color_color', 'color_magnitude', 'number_counts',
  'snr_magnitude', 'magnitude_residual', 'zeropoint_offsets',
}  # fmt: skip
BUILTIN = [e for e in list_preprocessors() if e.name.startswith(('core.', 'astro.'))]


def test_the_catalogue_of_the_plan_is_registered_and_nothing_else() -> None:
  names = {e.name for e in BUILTIN}
  assert names == {f'core.{n}' for n in CORE} | {f'astro.{n}' for n in ASTRO}
  assert all(e.version == 1 for e in BUILTIN)


def test_the_docs_table_lists_exactly_the_registered_pre_processors() -> None:
  documented = set(re.findall(r'^\| `((?:core|astro)\.[a-z_]+)` \|', DOC.read_text('utf-8'), re.M))
  assert documented == {e.name for e in BUILTIN}


@pytest.mark.parametrize('entry', BUILTIN, ids=lambda e: e.name)
def test_every_entry_is_documented_and_has_a_parameter_schema(entry: object) -> None:
  from scireport.preprocess import Preprocessor

  assert isinstance(entry, Preprocessor)
  assert entry.summary and entry.summary.endswith('.')
  assert entry.inputs and entry.outputs
  schema = params_schema(entry)
  assert 'properties' in schema
  for forbidden in ('table', 'ctx'):
    assert forbidden not in schema['properties']
  if 'figure' in entry.outputs:
    assert entry.render is not None, 'a figure pre-processor must register its render function'
    assert {'width', 'alt', 'caption'} <= set(schema['properties'])


def test_only_the_sky_maps_need_the_astro_extra() -> None:
  needing = {e.name for e in BUILTIN if e.requires == 'astro'}
  assert needing == {'astro.sky_density', 'astro.footprint', 'astro.sky_grid'}


def test_registering_the_catalogue_imports_neither_astropy_nor_scipy_nor_pandas() -> None:
  code = (
    'import sys; from scireport.preprocess import list_preprocessors; list_preprocessors();'
    "banned = ('astropy', 'astropy_healpix', 'scipy', 'pandas', 'mocpy');"
    'bad = [m for m in banned if m in sys.modules];'
    'sys.exit(1 if bad else 0)'
  )
  done = subprocess.run([sys.executable, '-I', '-c', code], capture_output=True, text=True)
  assert done.returncode == 0, done.stderr
