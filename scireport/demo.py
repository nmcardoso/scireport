"""The kitchen-sink bundle: every component and one of every hard case, with no real data.

``kitchen_sink_report()`` builds the data file that the built-in ``kitchen-sink@1`` template
reads. It exists to look at a layout: it holds the five status levels, the six flow states, every
number format, a very long heading, a deeply nested path, a 900-word paragraph, a wide profile
table, a table with missing values, equations, figures at three widths, and so on. The figures are
drawn with :func:`scireport.mplstyle`, so they carry the style of the layout they are drawn for.
Everything is seeded: two calls give the same bytes.
"""

from __future__ import annotations

import base64

import numpy as np

from scireport.bundle import Bundle
from scireport.logging_utils import get_logger
from scireport.report import Report
from scireport.styles import figure, mplstyle

log = get_logger(__name__)

SEED = 20261009
LONG_TITLE = (
  'Detailed Cross-Match Reconciliation Between Legacy Sweep Catalogues and Euclid Q1 Spectra.'
)
"""Exactly 90 characters: the long-heading case."""
LONG_PATH = (
  'store/spec/euclid_q1_merged_objects/partition_0042/'
  'cell_03215_dec_-042.500_to_-042.417/shard_00007_of_00128/'
  'euclid_q1_merged_objects.spectra.rescue.lance'
)
"""A deeply nested artifact path: the long-path case."""
LONG_NAME = (
  'Sloan Digital Sky Survey Data Release 17 Spectroscopic Catalogue of '
  'Quasars, Emission-Line Galaxies and Standard Stars'
)
"""A long catalogue name."""
_PLACEHOLDER_PNG = base64.b64decode(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
)
"""A one-pixel PNG, for bundles that must not depend on matplotlib."""
_SENTENCES = (
  'The extraction phase resolves each candidate against the Legacy Survey DR11 sweep catalogues '
  'before any spectroscopic cross-match is attempted, because a photometric non-detection '
  'changes what a missing spectrum means. A cell that has already been fetched is never '
  're-requested: the ledger records success and failure independently of the rows themselves, '
  'so a crash part-way through a wide declination band costs only the cells still in flight '
  'when it happened, and a retry pass touches nothing that already succeeded. '
)


def kitchen_sink_report(layout: str = 'default', *, real_figures: bool = True) -> Report:
  """Build the kitchen-sink report.

  Parameters
  ----------
  layout : str, default='default'
      The layout whose matplotlib style draws the figures, and the layout the bundle names.
  real_figures : bool, default=True
      Draw the figures with matplotlib. False uses tiny fixed pictures, which makes the bundle
      independent of the matplotlib version.

  Returns
  -------
  Report
      A report with ``render.template`` set to ``kitchen-sink@1``.
  """
  rng = np.random.default_rng(SEED)
  report = Report(
    'Kitchen Sink: Every Component and Hard Case',
    subtitle='One of each component and the cases a layout has to survive',
    authors=['N. Cardoso', {'name': 'A. Reviewer', 'affiliation': 'Example Institute'}],
    date='2026-10-09',
    version='1.0.0',
    pipeline='scireport demo',
    footer='scireport kitchen sink · 2026-10-09',
    abstract=(
      'A synthetic report that exercises every component of a layout: **five** status levels, '
      'the flow states, tables with long paths and missing values, equations such as '
      '$\\chi^2_\\nu = 1.02$, and figures at three widths. It holds no real data.'
    ),
    keywords=['layout', 'regression', 'demo'],
  )
  _summary(report)
  _status_and_meta(report)
  _numbers_and_math(report)
  _prose(report)
  _figures(report, layout, rng, real=real_figures)
  _tables(report)
  report.set_render(template='kitchen-sink@1', layout=f'{layout}@1')
  return report


def kitchen_sink_bundle(layout: str = 'default', *, real_figures: bool = True) -> Bundle:
  """Build the kitchen-sink bundle in memory; see :func:`kitchen_sink_report`.

  Parameters
  ----------
  layout : str, default='default'
      The layout whose style draws the figures.
  real_figures : bool, default=True
      Draw the figures with matplotlib.

  Returns
  -------
  Bundle
      An in-memory bundle.
  """
  return kitchen_sink_report(layout, real_figures=real_figures).build()


def _summary(report: Report) -> None:
  """Add the headline metrics, including a missing one and a very large one."""
  report.add_metrics(
    'summary.metrics',
    [
      {
        'label': 'Smallest count',
        'value': {'kind': 'number', 'value': 1, 'format': 'int'},
        'detail': 'a single matched source',
      },
      {
        'label': 'Largest count',
        'value': {'kind': 'number', 'value': 481_239_772_105, 'format': 'int'},
        'detail': 'a deliberately implausible stress value',
      },
      {'label': 'Success rate', 'value': '99.72%', 'detail': 'successful operations'},
      {'label': 'Not recorded', 'value': '--', 'detail': 'a metric this run does not carry'},
    ],
  )
  report.add_status(
    'summary.status', 'success', 'COMPLETED SUCCESSFULLY', 'This is the report-level status.'
  )


def _status_and_meta(report: Report) -> None:
  """Add the five status levels, the metadata, the alerts and the flow."""
  levels = [
    ('success', 'COMPLETED SUCCESSFULLY', 'Every stage finished within its thresholds.'),
    ('warning', 'COMPLETED WITH WARNINGS', 'One or more checks rejected at the chosen level.'),
    ('partial', 'PARTIALLY COMPLETE', 'A wider declination band was asked for than is cached.'),
    ('failed', 'RUN FAILED', 'An extraction step exhausted its retries against the archive.'),
    ('running', 'RUN IN PROGRESS', 'This report was made while the pipeline was running.'),
  ]
  for level, headline, detail in levels:
    report.add_status(f'qc.status.{level}', level, headline, detail)  # type: ignore[arg-type]
  report.add_mapping(
    'qc.meta',
    {
      'pipeline version': '2.4.1',
      'git commit': '7e91f2a3c8d0b1e4f5a6c7d8e9f0a1b2c3d4e5f6',
      'execution id': '2026-09-15T04:32:18',
      'host': 'cluster-node-042',
      'python': '3.12.3',
      'configuration hash': 'sha256:' + 'a1b2c3d4' * 4,
      'split seed': 'not recorded',
    },
  )
  report.add_alert('qc.alert.info', 'info', '99.97% of requested objects were extracted.')
  report.add_alert('qc.alert.warning', 'warning', '12 tiles exceeded the retry threshold.')
  report.add_alert('qc.alert.error', 'error', '3 extraction jobs failed after 5 retries.')
  report.add_flow(
    'qc.flow',
    [
      {'label': 'INGESTION', 'detail': ['12,483,921 objects'], 'state': 'done'},
      {'label': 'CATALOGUE QUERY', 'state': 'reused'},
      {
        'label': 'PHOTOMETRY EXTRACTION',
        'detail': ['8,021,433 rows', '99.8% success'],
        'state': 'done',
      },
      {'label': 'CROSS-MATCH / VIZIER', 'state': 'skipped'},
      {'label': 'CAST RECONCILIATION', 'state': 'running'},
      {'label': 'VALIDATION', 'detail': ['waiting on the archive'], 'state': 'pending'},
      {'label': 'PUBLISHED OUTPUT', 'detail': ['stage 5 failed once'], 'state': 'failed'},
    ],
  )


def _numbers_and_math(report: Report) -> None:
  """Add every number format, a missing number, and the equations."""
  report.add_number('qc.num.count', 12_483_921, format='int', unit='objects')
  report.add_number('qc.num.share', 0.9972, format='pct')
  report.add_number('qc.num.sep', 1.234, uncertainty=0.04, unit='arcsec', format=',.2f')
  report.add_number('qc.num.range', 1.5, interval=(1.1, 1.9), unit='mag')
  report.add_number('qc.num.flux', 3.21e8, format='sci', unit='Jy')
  report.add_number('qc.num.tiny', 1.42e-3, format='sci')
  report.add_number('qc.num.missing', None, missing='not recorded')
  report.add_math(
    'qc.eq.mag',
    r'm_{\rm AB} = -2.5\log_{10}\left(\frac{f_\nu}{3631\,{\rm Jy}}\right)',
    numbered=True,
    caption='The AB magnitude of a source from its flux density in janskys.',
  )
  report.add_math('qc.eq.chi', r'\chi^2 = \sum_i \frac{(O_i - E_i)^2}{\sigma_i^2}', numbered=True)


def _prose(report: Report) -> None:
  """Add the long paragraph, the lists and the code."""
  report.add_text('qc.long_paragraph', _SENTENCES * 8, format='plain')
  report.add_text(
    'qc.rich',
    'Inline **emphasis**, `code_with_underscores`, a [link](https://example.org), '
    'and math such as $f_\\nu \\propto \\nu^{-\\alpha}$ in a sentence.\n\n'
    '> A block quote, set apart from the body.\n\n'
    '| survey | n | note |\n|:--|--:|:--|\n| Legacy DR11 | 1,203 | sweeps |\n'
    '| Euclid Q1 | 87 | spectra |\n',
    format='markdown',
  )
  report.add_list(
    'qc.bullets',
    ['A bullet list item', 'One with `inline_code`', ['a', 'nested', 'list']],
  )
  report.add_list(
    'qc.steps', ['Fetch the cell', 'Match against sweeps', 'Rescue spectra'], ordered=True
  )
  report.add_text('qc.details', 'This text sits inside a collapsible block.')
  report.add_text('qc.note', 'A muted remark, such as the reason a value is missing.')
  report.add_code(
    'qc.code',
    'SELECT objid, ra, dec\nFROM legacy_dr11.sweep\nWHERE brick = :brick\n  AND mag_r < 21.5\n',
    language='sql',
  )


def _figures(report: Report, layout: str, rng: np.random.Generator, *, real: bool) -> None:
  """Add figures at three widths and a density panel."""
  if not real:
    for key, width in (('qc.fig.wide', 1.0), ('qc.fig.half', 0.5), ('qc.fig.narrow', 0.33)):
      report.add_figure(key, {'png': _PLACEHOLDER_PNG}, alt='A placeholder', width=width)
    report.add_figure('qc.fig.density', {'png': _PLACEHOLDER_PNG}, alt='A placeholder', width=0.8)
    return
  x = np.linspace(0, 4 * np.pi, 200)
  with mplstyle(layout):
    for key, width, height, caption in (
      ('qc.fig.wide', 1.0, 2.6, 'A full-width figure.'),
      ('qc.fig.half', 0.5, 2.4, 'A half-width figure.'),
      ('qc.fig.narrow', 0.33, 2.2, 'A third-width figure.'),
    ):
      fig, ax = figure(width, height, layout=layout)
      ax.plot(x, np.sin(x), label='sin')
      ax.plot(x, 0.6 * np.cos(1.5 * x), label='cos')
      ax.set_xlabel('x')
      ax.set_ylabel('amplitude')
      ax.legend()
      report.add_figure(
        key,
        fig,
        alt=f'Two sine-like curves; {caption.lower()}',
        caption=caption,
        width=width,
        data={'x': x, 'sin': np.sin(x)},
      )
    px = rng.normal(0.0, 1.0, 4000)
    py = 0.8 * px + rng.normal(0.0, 0.5, 4000)
    fig, ax = figure(0.8, 3.4, layout=layout)
    image = ax.hexbin(px, py, gridsize=40, mincnt=1)
    fig.colorbar(image, ax=ax, label='count')
    ax.set_xlabel('x')
    ax.set_ylabel('y')
    ax.set_title('Dense core, sparse tails')
    report.add_figure(
      'qc.fig.density',
      fig,
      alt='A hexagonal density map of correlated points; the core is dense and the tails sparse.',
      caption='Hexagons where a bin holds more than a handful of points.',
      width=0.8,
    )


def _tables(report: Report) -> None:
  """Add the path table, the table with missing values and the wide profile table."""
  paths = [LONG_PATH, 'store/spec/short.lance', LONG_PATH.replace('0042', '0043')]
  report.add_table(
    'recon.paths',
    {
      'artifact': ['spectra', 'catalogue', 'rescue'],
      'path': paths,
      'size': [4.2e9, 8.1e6, 1.7e8],
    },
    columns=[
      {'name': 'artifact', 'label': 'Artifact', 'width': 0.15},
      {'name': 'path', 'label': 'Path', 'align': 'path', 'width': 0.65},
      {'name': 'size', 'label': 'Size', 'unit': 'bytes', 'format': 'sci', 'width': 0.2},
    ],
    caption='Deeply nested paths wrap at the separators instead of overflowing.',
    inline=False,
  )
  report.add_table(
    'recon.missing',
    {
      'source': [LONG_NAME, 'Gaia DR3', 'Legacy Survey DR11'],
      'redshift': [0.1234, None, 2.5],
      'flux': [1.5e-5, 2.25e3, None],
    },
    columns=[
      {'name': 'source', 'label': 'Source', 'width': 0.5},
      {'name': 'redshift', 'label': 'Redshift', 'format': '.4f', 'width': 0.2},
      {'name': 'flux', 'label': 'Flux', 'format': 'sci', 'unit': 'Jy', 'width': 0.3},
    ],
    caption='Missing values show as a dash.',
    inline=False,
  )
  n = 250
  # Integer arithmetic, not random draws: the bytes of the golden files must not depend on the
  # numpy version or the platform's libm.
  report.add_table(
    'recon.profile',
    {
      'column': [f'column_{i:03d}' for i in range(n)],
      'n_rows': [10_000 + (i * 7919) % 4_990_000 for i in range(n)],
      'null_fraction': [((i * 37) % 300) / 1000 for i in range(n)],
      'mean': [((i * 53) % 2000 - 1000) / 10 for i in range(n)],
      'std': [1 + ((i * 29) % 490) / 10 for i in range(n)],
      'minimum': [-300 + ((i * 17) % 60) - 30 for i in range(n)],
      'maximum': [300 + ((i * 13) % 60) - 30 for i in range(n)],
    },
    columns=[
      {'name': 'column', 'label': 'Column', 'align': 'path'},
      {'name': 'n_rows', 'label': 'Rows', 'format': ',d', 'align': 'right'},
      {'name': 'null_fraction', 'label': 'Null', 'format': '.1%', 'align': 'right'},
      {'name': 'mean', 'label': 'Mean', 'format': '.2f', 'align': 'right'},
      {'name': 'std', 'label': 'Std', 'format': '.2f', 'align': 'right'},
      {'name': 'minimum', 'label': 'Min', 'format': '.1f', 'align': 'right'},
      {'name': 'maximum', 'label': 'Max', 'format': '.1f', 'align': 'right'},
    ],
    caption='A 250-row table: the header repeats on every page.',
  )
  report.add_attachment(
    'recon.attachment',
    b'column,n_rows\n' + b''.join(f'column_{i:03d},{i}\n'.encode() for i in range(250)),
    filename='profile.csv',
    media_type='text/csv',
    description='The profile table as CSV',
  )
