from __future__ import annotations

import numpy as np
import pyarrow as pa
import pytest

from scireport import Report
from scireport.errors import PreprocessError
from scireport.preprocess import Context
from scireport.preprocess.context import derive_seed
from scireport.preprocess.look import Look, default_look
from scireport.spec.kinds import FigureValue, TableValue

pytestmark = pytest.mark.usefixtures('no_builtins')


def _context(outputs: dict[str, str] | None = None, seed: int = 7) -> Context:
  report = Report(title='T')
  report.add_table('data', {'a': [1, 2, 3]})
  report.add_text('note', 'hello')
  return Context(
    bundle=report.build(),
    produced={},
    produced_assets={},
    outputs=outputs or {'figure': 'fig', 'table': 'tab'},
    layout='default',
    seed=seed,
    name='test.ctx',
  )


def test_derive_seed_is_stable_and_depends_on_both_parts() -> None:
  assert derive_seed(0, 'a') == derive_seed(0, 'a')
  assert derive_seed(0, 'a') != derive_seed(1, 'a')
  assert derive_seed(0, 'a') != derive_seed(0, 'b')
  assert 0 <= derive_seed(0, 'a') < 2**63


def test_rng_gives_the_same_stream_every_time() -> None:
  ctx = _context()
  assert np.array_equal(ctx.rng().random(5), ctx.rng().random(5))
  assert not np.array_equal(ctx.rng().random(5), _context(seed=8).rng().random(5))


def test_value_and_load_table() -> None:
  ctx = _context()
  assert isinstance(ctx.value('data'), TableValue)
  assert ctx.load_table('data').column('a').to_pylist() == [1, 2, 3]
  with pytest.raises(PreprocessError) as missing:
    ctx.value('dta')
  assert missing.value.code == 'E603'
  with pytest.raises(PreprocessError) as wrong:
    ctx.load_table('note')
  assert wrong.value.code == 'E603' and 'not a table' in wrong.value.message


def test_save_figure_needs_data_and_a_key_for_the_port() -> None:
  ctx = _context()
  figure, ax = ctx.figure(0.5, 2.0)
  ax.plot([0, 1], [0, 1])
  value = ctx.save_figure(figure, data=pa.table({'x': [0, 1]}), alt='A line.', formats=('png',))
  assert isinstance(value, FigureValue) and [r.format for r in value.renditions] == ['png']
  assert set(ctx.take_assets()) == {'assets/figures/fig.png', 'assets/figures/fig.data.parquet'}
  assert ctx.take_assets() == {}
  with pytest.raises(TypeError):
    ctx.save_figure(figure, alt='no data')  # type: ignore[call-arg]
  with pytest.raises(PreprocessError) as unknown:
    ctx.save_figure(figure, data=pa.table({'x': [0]}), alt='x', port='other')
  assert unknown.value.code == 'E603' and 'other' in unknown.value.message


def test_save_figure_rejects_blank_alt_text() -> None:
  ctx = _context()
  figure, _ = ctx.figure()
  with pytest.raises(ValueError, match='alt'):
    ctx.save_figure(figure, data=pa.table({'x': [0]}), alt='  ')


def test_save_table_stores_a_parquet_asset_and_presentation() -> None:
  ctx = _context()
  value = ctx.save_table(
    pa.table({'name': ['a', 'b'], 'n': [1, 2]}),
    columns=['name', {'name': 'n', 'label': 'Count', 'align': 'right'}],
    caption='Two rows',
  )
  assert value.n_rows == 2 and value.caption == 'Two rows'
  assert [c.label for c in value.columns] == [None, 'Count']
  assert value.asset is not None and value.asset.path == 'assets/tables/tab.parquet'
  csv = ctx.save_table(pa.table({'a': [1]}), format='csv')
  assert csv.asset is not None and csv.asset.path == 'assets/tables/tab.csv'


def test_an_unsafe_asset_path_is_refused() -> None:
  ctx = _context({'figure': '../escape'})
  figure, _ = ctx.figure()
  with pytest.raises(PreprocessError) as caught:
    ctx.save_figure(figure, data=pa.table({'x': [0]}), alt='x')
  assert caught.value.code == 'E603'


def test_figure_is_sized_as_a_fraction_of_the_page_frame() -> None:
  ctx = _context()
  figure, _ = ctx.figure(0.5, 2.0)
  width, height = figure.get_size_inches()
  assert height == pytest.approx(2.0) and 3.0 < width < 4.5


def test_look_follows_the_layout() -> None:
  ctx = _context()
  assert ctx.look is ctx.look
  assert ctx.look == default_look()
  assert ctx.look.color('failed').startswith('#')
  assert ctx.look.color('no-such-role') == '#78838c'
  assert ctx.look.series(0) == ctx.look.series(len(ctx.look.cycle))
  assert Look().series(3) == '#78838c'
