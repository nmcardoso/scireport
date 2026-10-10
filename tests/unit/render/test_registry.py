import logging
from importlib import metadata
from pathlib import Path
from typing import Any

import pytest
from render_fixtures import kitchen_sink, write_layout, write_template

from scireport.errors import TemplateError
from scireport.render import registry
from scireport.render.registry import (
  list_layouts,
  list_templates,
  load_layout,
  load_template,
  pin,
  pin_manifest,
  split_ref,
)


class FakeEntryPoint:
  def __init__(self, name: str, target: Any) -> None:
    self.name = name
    self.value = f'fake:{name}'
    self._target = target

  def load(self) -> Any:
    if isinstance(self._target, Exception):
      raise self._target
    return self._target


def install(monkeypatch: pytest.MonkeyPatch, groups: dict[str, list[FakeEntryPoint]]) -> None:
  monkeypatch.setattr(
    metadata, 'entry_points', lambda *, group: groups.get(group, []), raising=True
  )


def test_split_ref() -> None:
  assert split_ref('generic') == ('generic', None)
  assert split_ref('generic@2') == ('generic', 2)


@pytest.mark.parametrize('ref', ['generic@x', 'generic@0', 'generic@1.5'])
def test_bad_versions_are_refused(ref: str) -> None:
  with pytest.raises(TemplateError) as caught:
    split_ref(ref)
  assert caught.value.code == 'E701'


def test_builtins_load_by_name_and_version() -> None:
  assert load_template('generic').ref == 'generic@1'
  assert load_template('generic@1').origin == 'builtin'
  assert load_layout('minimal@1').ref == 'minimal@1'


def test_unknown_names_list_what_exists() -> None:
  with pytest.raises(TemplateError) as caught:
    load_template('nope')
  assert caught.value.code == 'E701'
  assert 'generic' in str(caught.value.hint)


def test_unknown_versions_list_what_exists() -> None:
  with pytest.raises(TemplateError) as caught:
    load_layout('minimal@9')
  assert caught.value.code == 'E504'
  assert 'minimal@1' in str(caught.value.hint)


def test_directories_load_by_path(tmp_path: Path) -> None:
  root = write_template(tmp_path / 'mine' / '1', name='mine', version=1)
  write_template(tmp_path / 'mine' / '2', name='mine', version=2)
  assert load_template(root).ref == 'mine@1'
  assert load_template(str(root)).origin == 'path'
  assert load_template(tmp_path / 'mine').ref == 'mine@2'
  assert load_layout(write_layout(tmp_path / 'lay')).ref == 'mine@1'


def test_a_path_without_a_definition_is_refused(tmp_path: Path) -> None:
  with pytest.raises(TemplateError, match='not a template directory'):
    load_template(tmp_path)


def test_entry_points_provide_templates_and_layouts(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
  write_template(tmp_path / 't' / '1', name='plug', version=1)
  write_template(tmp_path / 't' / '3', name='plug', version=3)
  single = write_template(tmp_path / 'single', name='solo', version=2)
  layout = write_layout(tmp_path / 'lay', name='plug')
  install(
    monkeypatch,
    {
      registry.TEMPLATE_GROUP: [
        FakeEntryPoint('plug', tmp_path / 't'),
        FakeEntryPoint('solo', lambda: str(single)),
      ],
      registry.LAYOUT_GROUP: [FakeEntryPoint('plug', layout)],
    },
  )
  assert load_template('plug').ref == 'plug@3'
  assert load_template('plug@1').origin == 'entry-point:plug'
  assert load_template('solo').ref == 'solo@2'
  assert load_layout('plug').ref == 'plug@1'
  assert [item.ref for item in list_templates()] == [
    'generic@1',
    'kitchen-sink@1',
    'plug@1',
    'plug@3',
    'solo@2',
  ]
  assert [item.ref for item in list_layouts()] == ['default@1', 'minimal@1', 'modern@1', 'plug@1']


def test_a_broken_plugin_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
  install(monkeypatch, {registry.TEMPLATE_GROUP: [FakeEntryPoint('bad', ImportError('boom'))]})
  with pytest.raises(TemplateError) as caught:
    load_template('bad')
  assert caught.value.code == 'E705'
  assert 'boom' in caught.value.message


def test_a_plugin_cannot_replace_a_builtin(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
  root = write_template(tmp_path / 'g' / '1', name='generic', version=1)
  install(monkeypatch, {registry.TEMPLATE_GROUP: [FakeEntryPoint('generic', root.parent)]})
  with caplog.at_level(logging.WARNING):
    assert load_template('generic').origin == 'builtin'
    listing = list_templates()
  assert {item.origin for item in listing} == {'builtin'}
  assert [item.name for item in listing].count('generic') == 1
  assert 'ignored' in caplog.text


def test_pin_resolves_the_newest_version() -> None:
  assert pin('template', 'generic') == 'generic@1'
  assert pin('layout', 'minimal@1') == 'minimal@1'


def test_pin_manifest_pins_names_and_keeps_versions(caplog: pytest.LogCaptureFixture) -> None:
  manifest = kitchen_sink().manifest
  named = manifest.model_copy(
    update={
      'render': manifest.render.model_copy(update={'template': 'generic', 'layout': 'minimal@1'})
    }
  )
  pinned = pin_manifest(named)
  assert (pinned.render.template, pinned.render.layout) == ('generic@1', 'minimal@1')
  assert pin_manifest(pinned) is pinned
  unset = manifest.model_copy(
    update={'render': manifest.render.model_copy(update={'template': None, 'layout': None})}
  )
  assert pin_manifest(unset) is unset
  unknown = manifest.model_copy(
    update={'render': manifest.render.model_copy(update={'template': 'plugin-not-installed'})}
  )
  with caplog.at_level(logging.WARNING):
    assert pin_manifest(unknown).render.template == 'plugin-not-installed'
  assert 'cannot pin' in caplog.text


def test_listings_carry_titles_and_formats() -> None:
  generic = next(item for item in list_templates() if item.name == 'generic')
  assert generic.title == 'Generic report'
  assert generic.formats == ('md', 'html', 'tex')
  assert generic.origin == 'builtin'
