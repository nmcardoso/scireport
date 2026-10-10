"""``core.pvalue_strip``: every p-value of a family of tests on one logarithmic axis.

Ported from the MOSAICS panel ``plot_pvalue_strip``. A quality-assurance run does a few dozen
tests and a table of them is read by nobody; one strip with the threshold drawn on it answers the
only question that matters, whether anything is below it. Points below the threshold are drawn in
the failure colour, the others in the success colour. A test that could not be computed is not a
passing test, so it has no position on the axis and is written out as ``not computable``. P-values
below 1e-16 are drawn at 1e-16 (the sidecar keeps the real value).

Parameters of the step (see :func:`pvalue_strip`):

* ``label_column``: the name of each test. ``pvalue_column``: its p-value (null or NaN: the test
  was degenerate).
* ``alpha``: significance threshold, drawn as a vertical line.
* ``title``: text. ``width`` (fraction of the page frame) and ``height`` (inches; computed from
  the number of tests when omitted).
* ``alt`` and ``caption``: text of the figure value; ``alt`` is made from the data when omitted.

Outputs: ``figure`` (a ``figure`` value with PNG and PDF renditions and its sidecar data).
Sidecar columns: ``label``, ``pvalue`` (null when not computable) and ``significant`` (true when
the p-value is below ``alpha``, null when not computable), one row per test in table order. The
threshold itself is the ``alpha`` parameter of the draw function.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pyarrow as pa

from scireport.preprocess.context import Context
from scireport.preprocess.plotting import (
  empty_axes,
  labels,
  numbers,
  require_columns,
  values_of,
)
from scireport.preprocess.ports import Port
from scireport.preprocess.registry import preprocessor
from scireport.spec.kinds import Envelope

if TYPE_CHECKING:
  from matplotlib.figure import Figure

_FLOOR = 1e-16
_INCHES_PER_TEST = 0.26
_MARGIN_INCHES = 1.3


def compute_pvalue_strip(
  table: pa.Table, label_column: str, pvalue_column: str, *, alpha: float = 0.05
) -> pa.Table:
  """Turn a table of tests and p-values into one row per test with its verdict.

  Parameters
  ----------
  table : pyarrow.Table
      The input, one row per test.
  label_column : str
      Column with the name of each test.
  pvalue_column : str
      Numeric column with the p-value; null, NaN or infinite means not computable.
  alpha : float, default=0.05
      Significance threshold.

  Returns
  -------
  pyarrow.Table
      Columns ``label`` (string), ``pvalue`` (float64, null when not computable) and
      ``significant`` (bool, null when not computable).
  """
  require_columns(table, label_column, pvalue_column)
  names = labels(table, label_column)
  values = numbers(table, pvalue_column)
  computable = np.isfinite(values)
  return pa.table(
    {
      'label': pa.array(names, pa.string()),
      'pvalue': pa.array(
        [float(v) if ok else None for v, ok in zip(values, computable, strict=True)], pa.float64()
      ),
      'significant': pa.array(
        [bool(v < alpha) if ok else None for v, ok in zip(values, computable, strict=True)],
        pa.bool_(),
      ),
    }
  )


def default_height(n_tests: int) -> float:
  """Return a figure height in inches that gives each test a row.

  Parameters
  ----------
  n_tests : int
      Number of tests.

  Returns
  -------
  float
      Height in inches, at least 1.6.
  """
  return max(1.6, _INCHES_PER_TEST * n_tests + _MARGIN_INCHES)


def render_pvalue_strip(
  ctx: Context,
  data: pa.Table,
  *,
  alpha: float = 0.05,
  title: str = '',
  width: float = 1.0,
  height: float | None = None,
) -> Figure:
  """Draw the strip of :func:`compute_pvalue_strip` in the layout's style.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`compute_pvalue_strip` made (or read back from a bundle's sidecar file).
  alpha : float, default=0.05
      Significance threshold, drawn as a vertical line.
  title : str, default=''
      Title; nothing when empty.
  width : float, default=1.0
      Width as a fraction of the page frame.
  height : float or None, default=None
      Height in inches; computed from the number of tests when None.

  Returns
  -------
  matplotlib.figure.Figure
      The drawn figure.
  """
  from matplotlib.transforms import blended_transform_factory

  with ctx.mplstyle():
    figure, ax = ctx.figure(width, default_height(data.num_rows) if height is None else height)
    figure.set_layout_engine('constrained')
    if data.num_rows == 0:
      empty_axes(ax, 'No tests')
      return figure
    names = [str(name) for name in data.column('label').to_pylist()]
    pvalues = values_of(data, 'pvalue')
    significant = data.column('significant').to_pylist()
    positions = np.arange(len(names))
    # x in axes fractions, y in data: a note about a missing p-value has no position on the
    # p-value axis to be drawn at.
    anchored = blended_transform_factory(ax.transAxes, ax.transData)
    for position, (p_value, is_significant) in enumerate(zip(pvalues, significant, strict=True)):
      if not np.isfinite(p_value):
        ax.text(
          0.02,
          position,
          'not computable',
          va='center',
          fontsize=7,
          color=ctx.look.color('neutral'),
          transform=anchored,
        )
        continue
      ax.plot(
        max(float(p_value), _FLOOR),
        position,
        marker='o',
        markersize=6,
        color=ctx.look.color('failed' if is_significant else 'success'),
      )
    ax.axvline(alpha, color=ctx.look.color('annotation'), linestyle='--', linewidth=0.9)
    ax.text(alpha, -1.0, f' alpha = {alpha:g}', fontsize=7, va='bottom')
    ax.set_xscale('log')
    ax.set_xlim(_FLOOR, 2.0)
    ax.set_yticks(positions)
    ax.set_yticklabels(names, fontsize=7, family='monospace')
    # Explicit rather than inverted with margins: the first and last rows carry annotations that
    # would otherwise sit on the edges of the axes.
    ax.set_ylim(len(names) - 0.4, -1.6)
    ax.set_xlabel('p-value')
    if title:
      ax.set_title(title)
  return figure


@preprocessor(
  'core.pvalue_strip',
  version=1,
  inputs={'table': Port('table', description='One row per test: its name and p-value')},
  outputs={'figure': Port('figure', description='The p-values against the threshold')},
  render=render_pvalue_strip,
)
def pvalue_strip(
  ctx: Context,
  *,
  table: pa.Table,
  label_column: str,
  pvalue_column: str,
  alpha: float = 0.05,
  title: str = '',
  width: float = 1.0,
  height: float | None = None,
  alt: str | None = None,
  caption: str | None = None,
) -> dict[str, Envelope]:
  """Every p-value of a family of tests on one logarithmic axis, against its threshold.

  Parameters
  ----------
  ctx : Context
      The run context.
  table : pyarrow.Table
      One row per test.
  label_column : str
      Column with the name of each test.
  pvalue_column : str
      Numeric column with the p-value; null or NaN means the test was not computable.
  alpha : float, default=0.05
      Significance threshold, drawn as a vertical line.
  title : str, default=''
      Title; nothing when empty.
  width : float, default=1.0
      Figure width as a fraction of the page frame.
  height : float or None, default=None
      Figure height in inches; computed from the number of tests when None.
  alt : str or None, default=None
      Alternative text; built from the counts when None.
  caption : str or None, default=None
      Caption below the figure.

  Returns
  -------
  dict
      ``{'figure': FigureValue}``.
  """
  data = compute_pvalue_strip(table, label_column, pvalue_column, alpha=alpha)
  figure = render_pvalue_strip(ctx, data, alpha=alpha, title=title, width=width, height=height)
  if alt is None:
    verdicts = data.column('significant').to_pylist()
    n_below = sum(1 for item in verdicts if item is True)
    n_missing = sum(1 for item in verdicts if item is None)
    alt = (
      f'Strip of the {pvalue_column} of {data.num_rows} tests on a logarithmic axis, with the '
      f'threshold alpha = {alpha:g}: {n_below} below it, {n_missing} not computable.'
    )
  return {'figure': ctx.save_figure(figure, data=data, alt=alt, caption=caption, width=width)}
