from __future__ import annotations

from typing import Annotated, Any, Literal

import pyarrow as pa
import pytest
from pydantic import Field

from scireport.preprocess import Context, Port, Preprocessor, params_schema
from scireport.preprocess.params import canonical_params, params_model, validate_params

pytestmark = pytest.mark.usefixtures('no_builtins')


def _typed(
  ctx: Context,
  *,
  table: pa.Table,
  column: str,
  bins: int | Literal['auto'] = 'auto',
  levels: Annotated[list[float], Field(min_length=1)] | None = None,
  log: bool = False,
) -> dict[str, Any]:
  """Typed parameters."""
  return {}


ENTRY = Preprocessor('test.typed', 1, _typed, {'table': Port('table')})


def test_defaults_are_filled_in() -> None:
  params, issues = validate_params(ENTRY, {'column': 'z'}, '/preprocess/0/params')
  assert issues == []
  assert params == {'column': 'z', 'bins': 'auto', 'levels': None, 'log': False}


def test_json_lists_and_unions_are_validated() -> None:
  params, issues = validate_params(ENTRY, {'column': 'z', 'bins': 12, 'levels': [0.5, 1]}, '/p')
  assert issues == [] and params['bins'] == 12 and params['levels'] == [0.5, 1.0]


def test_every_problem_is_reported_with_a_pointer() -> None:
  params, issues = validate_params(
    ENTRY, {'colum': 'z', 'bins': 'many', 'levels': [], 'log': 'sometimes'}, '/preprocess/2/params'
  )
  assert params == {}
  assert {issue.code for issue in issues} == {'E602'}
  pointers = {issue.pointer for issue in issues}
  assert '/preprocess/2/params/colum' in pointers
  assert '/preprocess/2/params/column' in pointers  # the required parameter that is missing
  assert '/preprocess/2/params/log' in pointers
  by_pointer = {issue.pointer: issue for issue in issues}
  assert by_pointer['/preprocess/2/params/colum'].hint == "Did you mean 'column'?"
  assert by_pointer['/preprocess/2/params/log'].found == "'sometimes'"


def test_unknown_parameter_without_a_close_match_lists_the_accepted_ones() -> None:
  _, issues = validate_params(ENTRY, {'column': 'z', 'zzzz': 1}, '/p')
  assert issues[0].hint == 'test.typed@1 takes: bins, column, levels, log.'


def test_input_ports_and_the_context_are_not_parameters() -> None:
  assert sorted(params_model(ENTRY).model_fields) == ['bins', 'column', 'levels', 'log']


def test_canonical_params_are_sorted_json() -> None:
  params, _ = validate_params(ENTRY, {'levels': [1, 2], 'column': 'z'}, '/p')
  assert list(canonical_params(ENTRY, params)) == ['bins', 'column', 'levels', 'log']


def test_schema_lists_required_parameters() -> None:
  schema = params_schema(ENTRY)
  assert schema['required'] == ['column']
  assert set(schema['properties']) == {'bins', 'column', 'levels', 'log'}


def test_positional_parameters_are_a_programming_error() -> None:
  def positional(ctx: Context, table: pa.Table, /, bad: int, *args: int) -> dict[str, Any]:
    return {}

  with pytest.raises(TypeError, match='named parameter'):
    params_model(Preprocessor('test.pos', 1, positional, {}))
