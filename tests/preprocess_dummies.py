"""Tiny registered pre-processors for the interface tests (``tests`` is on ``sys.path``)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pyarrow as pa

from scireport.preprocess import Context, Port, Preprocessor
from scireport.spec.kinds import Envelope

CALLS: list[str] = []
"""Names of the dummy pre-processors that actually ran, to tell a cache hit from a run."""


def make_figure(
  ctx: Context, *, table: pa.Table, column: str, scale: float = 1.0
) -> dict[str, Any]:
  """Table to figure: a bar per row, scaled."""
  CALLS.append('test.bars')
  values = np.asarray(table.column(column).to_pylist(), dtype=float) * scale
  figure, ax = ctx.figure(0.5, 2.0)
  with ctx.mplstyle():
    ax.bar(np.arange(values.size), values, color=ctx.look.series(0))
  data = pa.table({'index': np.arange(values.size), 'value': values})
  return {'figure': ctx.save_figure(figure, data=data, alt='Bars of the fixture column.')}


def make_table(ctx: Context, *, table: pa.Table, column: str, factor: int = 2) -> dict[str, Any]:
  """Table to table: one column multiplied."""
  CALLS.append('test.double')
  values = [None if v is None else v * factor for v in table.column(column).to_pylist()]
  return {'table': ctx.save_table(pa.table({column: values}), port='table')}


def explode(ctx: Context, *, table: pa.Table) -> dict[str, Any]:
  """Raise, whatever the input."""
  raise RuntimeError('boom')


def wrong_port(ctx: Context, *, table: pa.Table) -> dict[str, Any]:
  """Return a value for a port the pre-processor does not declare."""
  return {'figure': ctx.save_table(pa.table({'a': [1]}), port='figure')}


def returns_number(ctx: Context, *, table: pa.Table) -> dict[str, Any]:
  """Return a number where a figure is declared."""
  return {'figure': {'kind': 'number', 'value': 1}}


def forgets_output(ctx: Context, *, table: pa.Table) -> dict[str, Any]:
  """Return nothing."""
  return {}


def read_two(ctx: Context, *, left: pa.Table, right: Envelope | None) -> dict[str, Any]:
  """Two inputs, the second optional and untyped."""
  CALLS.append('test.two')
  return {'table': ctx.save_table(left, port='table')}


def entries() -> list[Preprocessor]:
  table_in = {'table': Port('table')}
  return [
    Preprocessor('test.bars', 1, make_figure, table_in, {'figure': Port('figure')}),
    Preprocessor('test.double', 1, make_table, table_in, {'table': Port('table')}),
    Preprocessor('test.explode', 1, explode, table_in, {'figure': Port('figure')}),
    Preprocessor('test.wrong_port', 1, wrong_port, table_in, {'figure': Port('figure')}),
    Preprocessor('test.returns_number', 1, returns_number, table_in, {'figure': Port('figure')}),
    Preprocessor('test.forgets', 1, forgets_output, table_in, {'figure': Port('figure')}),
    Preprocessor(
      'test.two',
      1,
      read_two,
      {'left': Port('table'), 'right': Port('any', optional=True)},
      {'table': Port('table')},
    ),
    Preprocessor('test.bars', 2, make_figure, table_in, {'figure': Port('figure')}),
  ]
