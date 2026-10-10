"""Example 2, a metrics dashboard: headline numbers, a verdict table, a flow and alerts.

It uses its own template (``templates/metrics-dashboard``) instead of the generic one, to show what
a template looks like.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from scireport import Report
from scireport.styles import figure, mplstyle

SEED = 11
TEMPLATE = Path(__file__).resolve().parent / 'templates' / 'metrics-dashboard'
"""The directory of the example's own template."""


def build(layout: str = 'default') -> Report:
  """Build the report.

  Parameters
  ----------
  layout : str, default='default'
      The layout whose style draws the figure.

  Returns
  -------
  Report
      The report. A data file never names a template by path, so it does not name one at all:
      pass :data:`TEMPLATE` to ``scireport render -t`` (``examples/render_all.py`` does).
  """
  rng = np.random.default_rng(SEED)
  report = Report(
    'Nightly pipeline dashboard',
    subtitle='Run 2026-10-09 · 14 stages · 3 surveys',
    authors=['pipeline-bot'],
    date='2026-10-09',
    version='run-0412',
    pipeline='nightly',
    footer='nightly · run-0412',
  )
  report.add_status(
    'dash.status',
    'warning',
    'COMPLETED WITH WARNINGS',
    'Two checks are over their threshold; no stage failed.',
  )
  report.add_metrics(
    'dash.metrics',
    [
      {
        'label': 'Objects in',
        'value': {'kind': 'number', 'value': 12_483_921, 'format': 'int'},
        'detail': 'after deduplication',
      },
      {
        'label': 'Objects out',
        'value': {'kind': 'number', 'value': 12_351_077, 'format': 'int'},
        'detail': '98.9% kept',
      },
      {'label': 'Wall time', 'value': '3 h 12 min', 'detail': 'on 64 cores'},
      {
        'label': 'Failures',
        'value': {'kind': 'number', 'value': 0, 'format': 'int'},
        'detail': 'retries: 17',
      },
      {'label': 'Peak memory', 'value': '41.2 GiB', 'detail': 'limit 64 GiB'},
      {'label': 'Output size', 'value': '8.7 GiB', 'detail': 'zstd Parquet'},
    ],
  )
  report.add_flow(
    'dash.flow',
    [
      {'label': 'Ingest', 'detail': ['12,483,921 objects'], 'state': 'done'},
      {'label': 'Deduplicate', 'detail': ['132,844 removed'], 'state': 'done'},
      {'label': 'Cross-match', 'detail': ['cached from run-0411'], 'state': 'reused'},
      {'label': 'Photometry', 'detail': ['skipped: no new tiles'], 'state': 'skipped'},
      {'label': 'Publish', 'state': 'done'},
    ],
  )
  report.add_alert('dash.alert.memory', 'warning', 'Peak memory reached 64% of the limit.')
  report.add_alert('dash.alert.info', 'info', 'Run 0411 was reused for the cross-match stage.')
  checks = {
    'check': [
      'Row count conserved',
      'No duplicate identifiers',
      'Coordinates inside the footprint',
      'Redshift sentinels removed',
      'Photometric zero point drift',
      'Astrometric RMS',
    ],
    'value': [1.0, 0.0, 0.9998, 0.97, 0.031, 0.083],
    'limit': [1.0, 0.0, 0.999, 0.99, 0.02, 0.1],
    'verdict': ['pass', 'pass', 'pass', 'warn', 'warn', 'pass'],
  }
  report.add_table(
    'dash.checks',
    checks,
    columns=[
      {'name': 'check', 'label': 'Check', 'width': 0.5},
      {'name': 'value', 'label': 'Value', 'format': '.4g', 'align': 'right', 'width': 0.2},
      {'name': 'limit', 'label': 'Limit', 'format': '.4g', 'align': 'right', 'width': 0.2},
      {'name': 'verdict', 'label': 'Verdict', 'width': 0.1},
    ],
    caption='Validation checks; a tinted row is a warning.',
    row_status_column='verdict',
  )
  stages = ['ingest', 'dedup', 'match', 'photometry', 'publish']
  seconds = rng.uniform(300, 4000, len(stages))
  with mplstyle(layout):
    fig, ax = figure(0.8, 2.6, layout=layout)
    ax.barh(stages[::-1], seconds[::-1] / 60)
    ax.set_xlabel('minutes')
    report.add_figure(
      'dash.durations',
      fig,
      alt='Horizontal bars of the minutes each of five stages took.',
      caption='Wall time per stage.',
      width=0.8,
      data={'stage': stages, 'seconds': seconds},
    )
  report.set_render(layout=f'{layout}@1')
  return report
