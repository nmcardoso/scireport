"""``core.stacked_shares``: one stacked horizontal bar per group, each segment a label's share.

Ported from the MOSAICS panel ``plot_stacked_shares``. It shows shares rather than counts because
the groups (the tiers of a train/validation/test split) can differ by orders of magnitude in
size: the question is whether every group apportions its rows the same way. A label missing from
a group counts as zero, so the segments line up across groups. An optional reference (the shares
that were asked for) is drawn as dashed verticals at the cumulative boundaries, so a group whose
segments do not reach them has drifted.

Parameters of the step (see :func:`stacked_shares`):

* ``group_column``: the group of each row (one bar per group, in order of first appearance).
* ``label_column``: the label (segment) of each row, in order of first appearance.
* ``count_column``: the count of the row; repeated (group, label) pairs are summed, null is zero.
* ``reference``: ``label -> share`` mapping (shares summing to one), drawn as dashed verticals.
* ``title``: text. ``width`` (fraction of the page frame) and ``height`` (inches; computed from
  the number of groups when omitted).
* ``alt`` and ``caption``: text of the figure value; ``alt`` is made from the data when omitted.

Outputs: ``figure`` (a ``figure`` value with PNG and PDF renditions and its sidecar data).
Sidecar columns: ``group``, ``label``, ``count`` (summed), ``share`` (the count over the group's
total, the total floored at one so an empty group gives zeros) and ``reference`` (the requested
share of the label, null when no reference was given or the label is not in it); one row per
(group, label) pair, groups and labels in order of first appearance.
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

_INCHES_PER_GROUP = 0.42
_MARGIN_INCHES = 1.5
_MIN_LABELLED_SHARE = 0.06


def compute_stacked_shares(
  table: pa.Table,
  group_column: str,
  label_column: str,
  count_column: str,
  *,
  reference: dict[str, float] | None = None,
) -> pa.Table:
  """Turn a long table of (group, label, count) into the share of each label within each group.

  Parameters
  ----------
  table : pyarrow.Table
      The input, one row per (group, label) with its count.
  group_column : str
      Column with the group of each row.
  label_column : str
      Column with the label of each row.
  count_column : str
      Numeric column with the count; null or NaN counts as zero.
  reference : dict or None, default=None
      Requested share of each label.

  Returns
  -------
  pyarrow.Table
      Columns ``group``, ``label`` (strings), ``count``, ``share`` and ``reference`` (float64),
      one row per (group, label) pair of the full grid.
  """
  require_columns(table, group_column, label_column, count_column)
  groups = labels(table, group_column)
  names = labels(table, label_column)
  counts = np.nan_to_num(numbers(table, count_column), nan=0.0)
  group_order = list(dict.fromkeys(groups))
  label_order = list(dict.fromkeys(names))
  totals: dict[tuple[str, str], float] = {}
  for group, name, count in zip(groups, names, counts, strict=True):
    totals[(group, name)] = totals.get((group, name), 0.0) + float(count)
  out_group: list[str] = []
  out_label: list[str] = []
  out_count: list[float] = []
  out_share: list[float] = []
  out_reference: list[float | None] = []
  for group in group_order:
    # Floored at one so an empty group divides cleanly to a row of zeros: a tier that came out
    # empty is a result worth drawing.
    group_total = max(1.0, sum(totals.get((group, name), 0.0) for name in label_order))
    for name in label_order:
      count = totals.get((group, name), 0.0)
      out_group.append(group)
      out_label.append(name)
      out_count.append(count)
      out_share.append(count / group_total)
      out_reference.append(
        float(reference[name] or 0.0) if reference is not None and name in reference else None
      )
  return pa.table(
    {
      'group': pa.array(out_group, pa.string()),
      'label': pa.array(out_label, pa.string()),
      'count': pa.array(out_count, pa.float64()),
      'share': pa.array(out_share, pa.float64()),
      'reference': pa.array(out_reference, pa.float64()),
    }
  )


def default_height(n_groups: int) -> float:
  """Return a figure height in inches that gives each group a bar and the legend a row.

  Parameters
  ----------
  n_groups : int
      Number of groups.

  Returns
  -------
  float
      Height in inches, at least 2.0.
  """
  return max(2.0, _INCHES_PER_GROUP * n_groups + _MARGIN_INCHES)


def render_stacked_shares(
  ctx: Context,
  data: pa.Table,
  *,
  title: str = '',
  width: float = 1.0,
  height: float | None = None,
) -> Figure:
  """Draw the stacked bars of :func:`compute_stacked_shares` in the layout's style.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`compute_stacked_shares` made (or read back from a bundle's sidecar file).
  title : str, default=''
      Title; nothing when empty.
  width : float, default=1.0
      Width as a fraction of the page frame.
  height : float or None, default=None
      Height in inches; computed from the number of groups when None.

  Returns
  -------
  matplotlib.figure.Figure
      The drawn figure.
  """
  groups = [str(item) for item in data.column('group').to_pylist()]
  names = list(dict.fromkeys(groups))
  with ctx.mplstyle():
    figure, ax = ctx.figure(width, default_height(len(names)) if height is None else height)
    figure.set_layout_engine('constrained')
    if not names:
      empty_axes(ax, 'No groups')
      return figure
    segments = [str(item) for item in data.column('label').to_pylist()]
    label_order = list(dict.fromkeys(segments))
    shares = values_of(data, 'share')
    requested = values_of(data, 'reference')
    positions = np.arange(len(names))
    row_of = {name: index for index, name in enumerate(names)}
    left = np.zeros(len(names))
    for index, label in enumerate(label_order):
      share = np.zeros(len(names))
      for group, segment, value in zip(groups, segments, shares, strict=True):
        if segment == label:
          share[row_of[group]] = value
      ax.barh(positions, share, left=left, label=label, color=ctx.look.series(index))
      for position, (value, start) in enumerate(zip(share, left, strict=True)):
        # Only where the segment is wide enough to hold the text without spilling into its
        # neighbour.
        if value > _MIN_LABELLED_SHARE:
          ax.text(
            start + value / 2,
            position,
            f'{value:.1%}',
            va='center',
            ha='center',
            fontsize=7,
            color='white',
          )
      left = left + share
    boundary = 0.0
    for label in label_order:
      wanted = requested[[segment == label for segment in segments]]
      wanted = wanted[np.isfinite(wanted)]
      boundary += float(wanted[0]) if wanted.size else 0.0
      if wanted.size and 0 < boundary < 1:
        ax.axvline(boundary, color=ctx.look.color('annotation'), linestyle='--', linewidth=0.8)
    ax.set_yticks(positions)
    ax.set_yticklabels(names, fontsize=8, family='monospace')
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.set_xlabel('Share of group')
    if title:
      ax.set_title(title)
    figure.legend(
      *ax.get_legend_handles_labels(),
      loc='outside lower center',
      fontsize=7,
      ncol=len(label_order),
      frameon=False,
    )
  return figure


@preprocessor(
  'core.stacked_shares',
  version=1,
  inputs={'table': Port('table', description='Long table: group, label and count of each row')},
  outputs={'figure': Port('figure', description='The stacked share bars')},
  render=render_stacked_shares,
)
def stacked_shares(
  ctx: Context,
  *,
  table: pa.Table,
  group_column: str,
  label_column: str,
  count_column: str,
  reference: dict[str, float] | None = None,
  title: str = '',
  width: float = 1.0,
  height: float | None = None,
  alt: str | None = None,
  caption: str | None = None,
) -> dict[str, Envelope]:
  """One stacked horizontal bar per group, each segment a label's share of the group.

  Parameters
  ----------
  ctx : Context
      The run context.
  table : pyarrow.Table
      Long table with one row per (group, label).
  group_column : str
      Column with the group of each row.
  label_column : str
      Column with the label (segment) of each row.
  count_column : str
      Numeric column with the count; null counts as zero, repeated pairs are summed.
  reference : dict or None, default=None
      Requested shares as ``label -> share`` (summing to one), drawn as dashed verticals at the
      cumulative boundaries.
  title : str, default=''
      Title; nothing when empty.
  width : float, default=1.0
      Figure width as a fraction of the page frame.
  height : float or None, default=None
      Figure height in inches; computed from the number of groups when None.
  alt : str or None, default=None
      Alternative text; built from the column names and the counts when None.
  caption : str or None, default=None
      Caption below the figure.

  Returns
  -------
  dict
      ``{'figure': FigureValue}``.
  """
  data = compute_stacked_shares(
    table, group_column, label_column, count_column, reference=reference
  )
  figure = render_stacked_shares(ctx, data, title=title, width=width, height=height)
  if alt is None:
    n_groups = len(set(data.column('group').to_pylist()))
    n_labels = len(set(data.column('label').to_pylist()))
    alt = (
      f'Stacked horizontal bars of the share of each {label_column} within each {group_column}: '
      f'{n_groups} groups, {n_labels} labels'
      + (', with the requested shares as dashed lines.' if reference else '.')
    )
  return {'figure': ctx.save_figure(figure, data=data, alt=alt, caption=caption, width=width)}
