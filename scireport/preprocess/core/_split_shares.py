"""Shared by ``core.split_marginals`` and ``core.split_balance``: shares per bin for each group.

Both figures overlay, for several groups (data splits, or the arms of one split), the share of
the group that falls in each bin of one stratifier. They take the same long table, one row per
group and bin with a count, and draw the same step curves; only the vocabulary of the labels
differs. The sidecar table holds one row per group and bin: ``<group>``, ``position`` (the bin's
place on the axis), ``bin`` (its label), ``count`` and ``share`` (the count over the group's
total, or the count itself when the group is empty).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pyarrow as pa

from scireport.preprocess.plotting import empty_axes, labels, numbers, require_columns, values_of

if TYPE_CHECKING:
  from matplotlib.axes import Axes

  from scireport.preprocess.look import Look


def compute_shares(
  table: pa.Table,
  group_column: str,
  bin_column: str,
  count_column: str,
  *,
  group_name: str,
) -> pa.Table:
  """Turn a long table of counts into shares per group and bin.

  Parameters
  ----------
  table : pyarrow.Table
      One row per group and bin; repeated pairs are summed.
  group_column : str
      Column with the group of each row (a split name or an arm).
  bin_column : str
      Column with the bin: numbers are ordered by value, anything else in the order it first
      appears in the table.
  count_column : str
      Column with the count in that bin (a number; null counts as zero).
  group_name : str
      Name of the group column in the result (``'split'`` or ``'arm'``).

  Returns
  -------
  pyarrow.Table
      Columns ``<group_name>``, ``position``, ``bin``, ``count`` and ``share``: every group has
      a row for every bin (a bin it never lists has count 0); groups appear in the order they
      first appear in the table and bins in axis order.
  """
  require_columns(table, group_column, bin_column, count_column)
  groups = labels(table, group_column)
  bins = labels(table, bin_column)
  counts = np.nan_to_num(numbers(table, count_column), nan=0.0)
  kind = table.column(bin_column).type
  if pa.types.is_integer(kind) or pa.types.is_floating(kind):
    keys = numbers(table, bin_column)
    first = {bins[i]: float(keys[i]) for i in range(len(bins)) if np.isfinite(keys[i])}
    bin_order = sorted(first, key=lambda name: (first[name], name))
    bin_order += [name for name in dict.fromkeys(bins) if name not in first]
  else:
    bin_order = list(dict.fromkeys(bins))
  group_order = list(dict.fromkeys(groups))
  totals: dict[tuple[str, str], float] = {}
  for group, name, count in zip(groups, bins, counts, strict=True):
    totals[(group, name)] = totals.get((group, name), 0.0) + float(count)
  names: list[str] = []
  positions: list[int] = []
  bin_labels: list[str] = []
  values: list[float] = []
  shares: list[float] = []
  for group in group_order:
    row = [totals.get((group, name), 0.0) for name in bin_order]
    total = sum(row)
    for position, (name, value) in enumerate(zip(bin_order, row, strict=True)):
      names.append(group)
      positions.append(position)
      bin_labels.append(name)
      values.append(value)
      shares.append(value / total if total else value)
  return pa.table(
    {
      group_name: pa.array(names, pa.string()),
      'position': pa.array(positions, pa.int64()),
      'bin': pa.array(bin_labels, pa.string()),
      'count': pa.array(values, pa.float64()),
      'share': pa.array(shares, pa.float64()),
    }
  )


def draw_shares(
  ax: Axes,
  data: pa.Table,
  look: Look,
  *,
  group_name: str,
  stratifier: str,
  empty_message: str,
  y_label: str,
  title: str,
  reference: str | None = None,
) -> None:
  """Draw one step curve of shares per group, or a placeholder when there is nothing to compare.

  Parameters
  ----------
  ax : matplotlib.axes.Axes
      The axes to draw on.
  data : pyarrow.Table
      The table :func:`compute_shares` made.
  look : Look
      Series colours.
  group_name : str
      Name of the group column in ``data``.
  stratifier : str
      Name of the stratifier, for the axis label and the single-bin message.
  empty_message : str
      Placeholder when ``data`` has no rows.
  y_label : str
      Label of the share axis.
  title : str
      Axes title; nothing when empty.
  reference : str or None, default=None
      The group drawn heavier so the eye has a baseline, the others thinner and fainter; None
      draws every group alike.
  """
  from matplotlib.ticker import MaxNLocator

  if data.num_rows == 0:
    empty_axes(ax, empty_message)
    return
  group = np.asarray(data.column(group_name).to_pylist(), dtype=object)
  position = values_of(data, 'position')
  share = values_of(data, 'share')
  if int(position.max()) < 1:
    # One bin means the stratifier had no finite value to bin on, so every group's share is
    # the same single number. An empty step plot would read as a broken chart; this reads as
    # what it is.
    empty_axes(ax, f'{stratifier or "This stratifier"}: one bin, nothing to compare')
    return
  for index, name in enumerate(dict.fromkeys(group.tolist())):
    mine = group == name
    style: dict[str, Any] = {}
    if reference is not None:
      style = {
        'linewidth': 2.0 if name == reference else 1.0,
        'alpha': 1.0 if name == reference else 0.85,
      }
    ax.step(position[mine], share[mine], where='mid', label=name, color=look.series(index), **style)
  # The positions are bin numbers, so the ticks sit on whole numbers only.
  ax.xaxis.set_major_locator(MaxNLocator(integer=True))
  ax.set_xlabel(f'{stratifier} bin' if stratifier else 'bin')
  ax.set_ylabel(y_label)
  if title:
    ax.set_title(title, fontsize=11)
  ax.legend(fontsize=7)
