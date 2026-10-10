from __future__ import annotations

from typing import Any

import pytest

from scireport import Report
from scireport.errors import PreprocessError
from scireport.preprocess import plan_steps

pytestmark = pytest.mark.usefixtures('no_builtins')


def _manifest(*steps: dict[str, Any], values: dict[str, Any] | None = None) -> Any:
  report = Report(title='Fixture')
  for key, data in (values or {'data': {'a': [1, 2, 3], 'b': [0.5, 1.5, 2.5]}}).items():
    if isinstance(data, dict):
      report.add_table(key, data)
    else:
      report.add(key, data)
  for step in steps:
    report.add_preprocess(**step)
  return report.build().manifest


def _bars(**changes: Any) -> dict[str, Any]:
  step: dict[str, Any] = {
    'name': 'test.bars',
    'inputs': {'table': 'data'},
    'outputs': {'figure': 'fig'},
    'params': {'column': 'a'},
  }
  step.update(changes)
  return step


def _codes(error: PreprocessError) -> list[str]:
  return [issue.code for issue in error.issues]


def test_a_valid_step_is_resolved_with_its_defaults() -> None:
  (planned,) = plan_steps(_manifest(_bars(id='bars')))
  assert planned.label == 'bars'
  assert planned.entry.ref == 'test.bars@2'
  assert planned.params == {'column': 'a', 'scale': 1.0}
  assert planned.inputs == {'table': 'data'} and planned.outputs == {'figure': 'fig'}


def test_a_step_without_an_id_is_labelled_by_name_and_position() -> None:
  (planned,) = plan_steps(_manifest(_bars()))
  assert planned.label == 'test.bars#0'


def test_the_version_a_step_names_is_the_one_that_runs() -> None:
  (planned,) = plan_steps(_manifest(_bars(version=1)))
  assert planned.entry.version == 1


def test_all_problems_of_all_steps_come_back_together() -> None:
  steps = [
    _bars(name='test.bar'),
    _bars(outputs={'figur': 'fig2'}, params={'colum': 'a'}),
    _bars(inputs={'table': 'dta'}, outputs={'figure': 'fig3'}),
  ]
  with pytest.raises(PreprocessError) as caught:
    plan_steps(_manifest(*steps))
  error = caught.value
  assert 'E601' in _codes(error) and 'E602' in _codes(error) and 'E603' in _codes(error)
  assert len(error.issues) >= 5
  pointers = [issue.pointer for issue in error.issues]
  assert '/preprocess/0/name' in pointers
  assert any(p.startswith('/preprocess/1/params') for p in pointers)
  assert '/preprocess/2/inputs/table' in pointers
  missing = next(i for i in error.issues if i.pointer == '/preprocess/2/inputs/table')
  assert missing.hint == "Did you mean 'data'?"


def test_unwired_and_unknown_ports() -> None:
  with pytest.raises(PreprocessError) as caught:
    plan_steps(_manifest(_bars(inputs={}, outputs={})))
  messages = ' | '.join(issue.message for issue in caught.value.issues)
  assert 'input port' in messages and 'not wired' in messages
  assert 'output port' in messages and 'no key' in messages
  with pytest.raises(PreprocessError) as unknown:
    plan_steps(_manifest(_bars(inputs={'tabel': 'data'})))
  assert any(i.hint == "Did you mean 'table'?" for i in unknown.value.issues)


def test_optional_input_may_stay_unwired() -> None:
  step = {
    'name': 'test.two',
    'inputs': {'left': 'data'},
    'outputs': {'table': 'copy'},
  }
  (planned,) = plan_steps(_manifest(step))
  assert planned.inputs == {'left': 'data'}


def test_kind_of_the_wired_value_is_checked() -> None:
  step = _bars(inputs={'table': 'note'})
  with pytest.raises(PreprocessError) as caught:
    plan_steps(_manifest(step, values={'data': {'a': [1]}, 'note': 'text'}))
  issue = caught.value.issues[0]
  assert issue.code == 'E603' and issue.expected == 'table' and issue.found == 'text'


def test_steps_run_after_the_producers_of_their_inputs() -> None:
  second = _bars(id='second', inputs={'table': 'doubled'}, outputs={'figure': 'fig'})
  first = {
    'name': 'test.double',
    'id': 'first',
    'inputs': {'table': 'data'},
    'outputs': {'table': 'doubled'},
    'params': {'column': 'a'},
  }
  planned = plan_steps(_manifest(second, first))
  assert [p.label for p in planned] == ['first', 'second']


def test_independent_steps_keep_their_written_order() -> None:
  steps = [_bars(id=name, outputs={'figure': name}) for name in ('c', 'a', 'b')]
  assert [p.label for p in plan_steps(_manifest(*steps))] == ['c', 'a', 'b']


def test_the_kind_of_a_produced_key_is_checked_against_the_port() -> None:
  first = _bars(id='one', outputs={'figure': 'made'})
  second = _bars(id='two', inputs={'table': 'made'}, outputs={'figure': 'fig2'})
  with pytest.raises(PreprocessError) as caught:
    plan_steps(_manifest(first, second))
  assert caught.value.issues[0].found == 'figure'


def test_two_steps_may_not_write_the_same_key() -> None:
  with pytest.raises(PreprocessError) as caught:
    plan_steps(_manifest(_bars(id='one'), _bars(id='two')))
  issue = caught.value.issues[0]
  assert issue.code == 'E604' and issue.key == 'fig'
  assert "'one'" in issue.message and "'two'" in issue.message


def test_a_cycle_is_reported_with_its_steps() -> None:
  a = {
    'name': 'test.double',
    'id': 'a',
    'inputs': {'table': 'from_b'},
    'outputs': {'table': 'from_a'},
    'params': {'column': 'a'},
  }
  b = {**a, 'id': 'b', 'inputs': {'table': 'from_a'}, 'outputs': {'table': 'from_b'}}
  with pytest.raises(PreprocessError) as caught:
    plan_steps(_manifest(a, b))
  issue = caught.value.issues[0]
  assert issue.code == 'E604' and "'a'" in issue.message and "'b'" in issue.message


def test_a_step_may_not_read_its_own_output() -> None:
  step = {
    'name': 'test.double',
    'inputs': {'table': 'loop'},
    'outputs': {'table': 'loop'},
    'params': {'column': 'a'},
  }
  with pytest.raises(PreprocessError) as caught:
    plan_steps(_manifest(step))
  assert caught.value.code == 'E604'


def test_a_key_that_is_already_there_is_owned_by_the_step() -> None:
  manifest = _manifest(_bars(), values={'data': {'a': [1]}, 'fig': 'stale'})
  (planned,) = plan_steps(manifest)
  assert planned.outputs == {'figure': 'fig'}


def test_module_function_steps_need_allow_import() -> None:
  with pytest.raises(PreprocessError) as caught:
    plan_steps(_manifest(_bars(name='some.module:func')))
  assert caught.value.code == 'E605'


def test_an_invalid_output_key_is_e101() -> None:
  manifest_step = _bars(outputs={'figure': 'fig'})
  manifest = _manifest(manifest_step)
  step = manifest.preprocess[0].model_copy(update={'outputs': {'figure': 'Bad Key'}})
  broken = manifest.model_copy(update={'preprocess': [step]})
  with pytest.raises(PreprocessError) as caught:
    plan_steps(broken)
  assert caught.value.code == 'E101'
