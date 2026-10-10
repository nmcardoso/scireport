"""A report whose figures come from pre-processing steps renders, twice, to the same bytes."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from scireport import Report, open_bundle
from scireport.cli import app
from scireport.render import render_bundle
from scireport.spec.kinds import FigureValue, MetricsValue, TableValue


def _catalogue(seed: int = 4) -> dict[str, list[float | str]]:
  rng = np.random.default_rng(seed)
  n = 400
  ra = rng.uniform(150.0, 210.0, n)
  dec = rng.uniform(-10.0, 20.0, n)
  g = rng.normal(21.0, 1.5, n)
  r = g - rng.normal(0.4, 0.2, n)
  return {
    'ra': list(np.round(ra, 5)),
    'dec': list(np.round(dec, 5)),
    'g': list(np.round(g, 4)),
    'r': list(np.round(r, 4)),
    'sep': list(np.round(np.abs(rng.normal(0.0, 0.4, n)), 4)),
    'survey': [('north', 'south')[i % 2] for i in range(n)],
  }


def _report() -> Report:
  report = Report(title='Pre-processed report', date='2026-10-10')
  report.add_table('cat', _catalogue())
  steps: list[tuple[str, str, dict[str, object]]] = [
    ('core.table_profile', 'profile', {}),
    ('core.histogram', 'fig.sep', {'column': 'sep', 'bins': 20, 'x_label': 'Separation'}),
    ('core.density_scatter', 'fig.gr', {'x_column': 'g', 'y_column': 'r'}),
    ('astro.color_magnitude', 'fig.cmd', {'color_column': 'g', 'magnitude_column': 'r'}),
    ('astro.sky_density', 'fig.sky', {'order': 3}),
    ('core.distribution', 'fig.dist', {'value_column': 'g', 'group_column': 'survey'}),
  ]
  for name, key, params in steps:
    if name == 'core.table_profile':
      report.add_preprocess(
        name, inputs={'table': 'cat'}, outputs={'profile': 'profile', 'summary': 'summary'}
      )
    else:
      report.add_preprocess(name, inputs={'table': 'cat'}, outputs={'figure': key}, params=params)
  report.set_outline(
    [
      {'title': 'Data', 'children': ['summary', 'profile']},
      {'title': 'Figures', 'children': ['fig.sep', 'fig.gr', 'fig.cmd', 'fig.sky', 'fig.dist']},
    ]
  )
  return report


@pytest.fixture
def source(tmp_path: Path) -> Path:
  return _report().write(tmp_path / 'report')


def test_the_steps_make_figures_tables_and_metrics(source: Path, tmp_path: Path) -> None:
  from scireport.preprocess import preprocess_bundle

  with open_bundle(source) as bundle:
    result = preprocess_bundle(bundle, cache_dir=tmp_path / 'cache')
  values = result.bundle.manifest.values
  assert isinstance(values['profile'], TableValue) and isinstance(values['summary'], MetricsValue)
  for key in ('fig.sep', 'fig.gr', 'fig.cmd', 'fig.sky', 'fig.dist'):
    assert isinstance(values[key], FigureValue), key
  assert result.bundle.verify() == []
  rows = result.bundle.read_table('profile')
  assert rows.column('name').to_pylist() == ['ra', 'dec', 'g', 'r', 'sep', 'survey']


@pytest.mark.parametrize('layout', ['default', 'modern'])
def test_the_report_renders_and_two_renders_are_byte_identical(
  source: Path, tmp_path: Path, layout: str
) -> None:
  outputs = []
  for run in ('a', 'b'):
    with open_bundle(source) as bundle:
      outputs.append(
        render_bundle(
          bundle,
          layout=layout,
          formats=['md', 'html', 'tex'],
          cache_dir=tmp_path / f'cache-{run}',
        )
      )
  first, second = outputs
  assert first.files == second.files
  figures = [name for name in first.files if name.endswith('.png')]
  assert len(figures) >= 5


def test_the_cli_renders_it(source: Path, tmp_path: Path) -> None:
  from typer.testing import CliRunner

  result = CliRunner().invoke(
    app,
    [
      'render',
      str(source),
      '-o',
      str(tmp_path / 'out'),
      '-f',
      'md',
      '--cache-dir',
      str(tmp_path / 'c'),
    ],
  )
  assert result.exit_code == 0, result.output
