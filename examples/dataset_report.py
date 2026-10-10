"""Example 1, a small dataset report: a cross-match of two surveys, with figures and tables.

The data are synthetic and seeded. The report is rendered by the built-in ``generic@1`` template
from the outline, so no template has to be written for it.
"""

from __future__ import annotations

import numpy as np

from scireport import Report
from scireport.styles import figure, mplstyle

SEED = 7


def build(layout: str = 'default') -> Report:
  """Build the report.

  Parameters
  ----------
  layout : str, default='default'
      The layout whose style draws the figures.

  Returns
  -------
  Report
      The report, ready to ``build()`` or ``write()``.
  """
  rng = np.random.default_rng(SEED)
  n_a, n_b, n_match = 48_213, 61_870, 37_904
  separation = rng.rayleigh(0.32, n_match)
  mag_a = rng.normal(21.4, 1.3, n_match)
  mag_b = mag_a + rng.normal(0.05, 0.12, n_match)
  report = Report(
    'Cross-match of two imaging surveys',
    subtitle='Survey A (optical) against survey B (infrared), a 25 deg² field',
    authors=['N. Cardoso'],
    date='2026-10-09',
    version='1.0',
    pipeline='scireport examples',
    abstract=(
      f'We match **{n_a:,}** sources of survey A to **{n_b:,}** of survey B within '
      f'$1.5^{{\\prime\\prime}}$ and find **{n_match:,}** pairs. The median separation is '
      f'{np.median(separation):.2f} arcsec and the colour offset is consistent with zero.'
    ),
    keywords=['cross-match', 'surveys', 'example'],
  )
  report.add_metrics(
    'summary.metrics',
    [
      {
        'label': 'Survey A',
        'value': {'kind': 'number', 'value': n_a, 'format': 'int'},
        'detail': 'sources in the field',
      },
      {
        'label': 'Survey B',
        'value': {'kind': 'number', 'value': n_b, 'format': 'int'},
        'detail': 'sources in the field',
      },
      {
        'label': 'Pairs',
        'value': {'kind': 'number', 'value': n_match, 'format': 'int'},
        'detail': f'{n_match / n_a:.1%} of survey A',
      },
    ],
  )
  report.add_status('summary.status', 'success', 'MATCH COMPLETE', 'Every check passed.')
  report.add_text(
    'method.text',
    'Positions of both catalogues are projected on the tangent plane of the field centre. '
    'A pair is kept when the two sources are closer than $r_{\\max}=1.5^{\\prime\\prime}$ and '
    'each is the nearest neighbour of the other.\n\n'
    '- The search radius is set by the astrometric uncertainty of survey B.\n'
    '- Ties are broken by the brighter source of survey A.\n',
    format='markdown',
  )
  report.add_math(
    'method.radius',
    r'r_{\max} = 3\sqrt{\sigma_A^2 + \sigma_B^2}',
    numbered=True,
    caption='The search radius from the two astrometric uncertainties.',
  )
  report.add_table(
    'results.summary',
    {
      'quantity': ['Sources in survey A', 'Sources in survey B', 'Pairs', 'Unmatched in A'],
      'value': [n_a, n_b, n_match, n_a - n_match],
      'share': [1.0, n_b / n_a, n_match / n_a, (n_a - n_match) / n_a],
    },
    columns=[
      {'name': 'quantity', 'label': 'Quantity', 'width': 0.5},
      {'name': 'value', 'label': 'Count', 'format': ',d', 'align': 'right', 'width': 0.25},
      {'name': 'share', 'label': 'Share of A', 'format': '.1%', 'align': 'right', 'width': 0.25},
    ],
    caption='Counts of the cross-match.',
  )
  with mplstyle(layout):
    fig, ax = figure(0.8, 3.0, layout=layout)
    ax.hist(separation, bins=40, color=None)
    ax.axvline(1.5, linestyle='--', color='0.4')
    ax.set_xlabel('separation (arcsec)')
    ax.set_ylabel('pairs')
    report.add_figure(
      'results.separation',
      fig,
      alt='Histogram of pair separations, peaking near 0.3 arcsec with a tail towards the 1.5 '
      'arcsec search radius.',
      caption='Separation of the matched pairs; the dashed line is the search radius.',
      width=0.8,
      data={'separation_arcsec': separation},
    )
    fig, ax = figure(0.8, 3.4, layout=layout)
    image = ax.hexbin(mag_a, mag_b - mag_a, gridsize=36, mincnt=1)
    fig.colorbar(image, ax=ax, label='pairs')
    ax.set_xlabel('magnitude in A')
    ax.set_ylabel('colour offset B - A')
    report.add_figure(
      'results.colour',
      fig,
      alt='Hexagonal density map of the colour offset against magnitude; the offset is centred '
      'on zero at every magnitude.',
      caption='Colour offset against magnitude of the matched pairs.',
      width=0.8,
    )
  report.add_alert('results.note', 'info', 'Offsets are in the AB system.')
  report.set_outline(
    [
      'summary.status',
      'summary.metrics',
      {'title': 'Method', 'children': ['method.text', 'method.radius']},
      {
        'title': 'Results',
        'children': [
          {'title': 'Counts', 'children': ['results.summary']},
          {
            'title': 'Separations and colours',
            'children': ['results.separation', 'results.colour', 'results.note'],
          },
        ],
      },
    ]
  )
  report.set_render(template='generic@1', layout=f'{layout}@1')
  return report
