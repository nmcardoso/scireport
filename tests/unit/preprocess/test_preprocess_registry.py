from __future__ import annotations

import importlib.metadata
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from scireport.errors import PreprocessError
from scireport.preprocess import (
  Context,
  Port,
  Preprocessor,
  get_preprocessor,
  list_preprocessors,
  preprocessor,
  register_preprocessor,
)
from scireport.preprocess import registry as registry_module
from scireport.preprocess.registry import unregister_preprocessor

pytestmark = pytest.mark.usefixtures('no_builtins')


def _noop(ctx: Context, *, table: Any) -> dict[str, Any]:
  """Do nothing."""
  return {}


def test_decorator_registers_and_returns_a_callable_entry() -> None:
  @preprocessor('test.deco', version=1, inputs={'table': Port('table')})
  def deco(ctx: Context, *, table: Any) -> dict[str, Any]:
    """Say hello."""
    return {'hello': 1}

  try:
    assert isinstance(deco, Preprocessor)
    assert deco.ref == 'test.deco@1'
    assert deco.summary == 'Say hello.'
    assert deco(None, table=None) == {'hello': 1}
    assert get_preprocessor('test.deco') is deco
  finally:
    unregister_preprocessor('test.deco', 1)


def test_latest_version_is_the_default_and_an_older_one_stays_reachable() -> None:
  assert get_preprocessor('test.bars').version == 2
  assert get_preprocessor('test.bars', 1).version == 1


@pytest.mark.parametrize('name', ['histogram', 'Core.hist', 'core.', 'core.1x', 'core..x'])
def test_name_must_be_dotted_lower_case(name: str) -> None:
  with pytest.raises(ValueError, match=r'group\.name'):
    register_preprocessor(Preprocessor(name, 1, _noop))


def test_version_must_be_positive() -> None:
  with pytest.raises(ValueError, match='at least 1'):
    register_preprocessor(Preprocessor('test.v0', 0, _noop))


def test_input_ports_must_be_parameters() -> None:
  with pytest.raises(ValueError, match='not parameters'):
    register_preprocessor(Preprocessor('test.bad', 1, _noop, {'tabel': Port('table')}))


def test_duplicate_registration_needs_replace() -> None:
  with pytest.raises(ValueError, match='already registered'):
    register_preprocessor(Preprocessor('test.bars', 1, _noop, {'table': Port('table')}))
  replacement = Preprocessor('test.bars', 1, _noop, {'table': Port('table')})
  try:
    register_preprocessor(replacement, replace=True)
    assert get_preprocessor('test.bars', 1) is replacement
  finally:
    unregister_preprocessor('test.bars', 1)


def test_unknown_name_suggests_the_closest() -> None:
  with pytest.raises(PreprocessError) as caught:
    get_preprocessor('test.bar')
  issue = caught.value.issues[0]
  assert issue.code == 'E601'
  assert issue.hint is not None and 'test.bars' in issue.hint


def test_unknown_version_lists_the_available_ones() -> None:
  with pytest.raises(PreprocessError) as caught:
    get_preprocessor('test.bars', 7)
  issue = caught.value.issues[0]
  assert issue.code == 'E601' and issue.expected == 'one of [1, 2]'


def test_builtins_are_listed_sorted(monkeypatch: pytest.MonkeyPatch) -> None:
  monkeypatch.setitem(registry_module._STATE, 'builtins', False)
  names = [entry.ref for entry in list_preprocessors()]
  assert 'core.histogram@1' in names
  assert names == sorted(names, key=lambda ref: (ref.partition('@')[0], int(ref.partition('@')[2])))


def test_module_function_needs_allow_import() -> None:
  with pytest.raises(PreprocessError) as caught:
    get_preprocessor('os.path:join', pointer='/preprocess/0/name')
  issue = caught.value.issues[0]
  assert issue.code == 'E605' and issue.pointer == '/preprocess/0/name'
  assert '--allow-import' in (issue.hint or '')


def test_allowed_import_resolves_a_registered_function(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
  (tmp_path / 'my_steps.py').write_text(
    textwrap.dedent(
      """
      from scireport.preprocess import Port, preprocessor

      @preprocessor('test.mine', version=3, inputs={'table': Port('table')})
      def mine(ctx, *, table):
        return {}

      plain = len
      """
    ),
    encoding='utf-8',
  )
  monkeypatch.syspath_prepend(str(tmp_path))
  try:
    found = get_preprocessor('my_steps:mine', 3, allow_import=True)
    assert found.name == 'test.mine'
    with pytest.raises(PreprocessError) as wrong_version:
      get_preprocessor('my_steps:mine', 1, allow_import=True)
    assert wrong_version.value.code == 'E601'
    with pytest.raises(PreprocessError) as plain:
      get_preprocessor('my_steps:plain', allow_import=True)
    assert plain.value.code == 'E601' and 'not a pre-processor' in plain.value.message
  finally:
    unregister_preprocessor('test.mine', 3)
    sys.modules.pop('my_steps', None)


def test_failed_import_is_e608() -> None:
  with pytest.raises(PreprocessError) as missing_module:
    get_preprocessor('no_such_module_xyz:f', allow_import=True)
  with pytest.raises(PreprocessError) as missing_name:
    get_preprocessor('os.path:no_such_function', allow_import=True)
  assert missing_module.value.code == 'E608' and missing_name.value.code == 'E608'


def test_entry_point_plugins_register_and_a_broken_one_is_skipped(
  monkeypatch: pytest.MonkeyPatch, fresh_discovery: None, caplog: pytest.LogCaptureFixture
) -> None:
  plugin = Preprocessor('test.plugin', 1, _noop, {'table': Port('table')})

  def broken() -> Any:
    raise ImportError('plugin dependency is missing')

  points = [
    SimpleNamespace(name='good', load=lambda: plugin),
    SimpleNamespace(name='bad', load=broken),
    SimpleNamespace(name='odd', load=lambda: 42),
  ]
  monkeypatch.setattr(importlib.metadata, 'entry_points', lambda group: points)
  try:
    with caplog.at_level('WARNING'):
      assert get_preprocessor('test.plugin') is plugin
    assert 'E608' in caplog.text and 'bad' in caplog.text
  finally:
    unregister_preprocessor('test.plugin', 1)
