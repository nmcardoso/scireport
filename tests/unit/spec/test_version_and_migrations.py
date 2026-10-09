from typing import Any

import pytest

import scireport.spec.migrations as migrations
from scireport.errors import SpecVersionError
from scireport.spec.version import SPEC_VERSION, check_readable, parse_version, read_version


@pytest.mark.parametrize(
  ('text', 'expected'), [('1.0', (1, 0)), ('0.9', (0, 9)), ('12.345', (12, 345))]
)
def test_parse_version(text: str, expected: tuple[int, int]) -> None:
  assert parse_version(text) == expected


@pytest.mark.parametrize('text', ['1', '1.0.0', 'v1.0', '01.0', '1.-1', '', 1.0, None])
def test_parse_version_rejects_malformed(text: object) -> None:
  with pytest.raises(SpecVersionError) as info:
    parse_version(text)  # type: ignore[arg-type]
  assert info.value.code == 'E502'


def test_read_version_needs_the_entry() -> None:
  assert read_version({'scireport': '1.0'}) == (1, 0)
  bad: list[object] = [{}, [], 'x', None]
  for raw in bad:
    with pytest.raises(SpecVersionError) as info:
      read_version(raw)
    assert info.value.code == 'E502'


def test_current_version_and_older_minors_are_readable() -> None:
  assert check_readable({'scireport': SPEC_VERSION}) == parse_version(SPEC_VERSION)
  assert check_readable({'scireport': '1.0'}, supported='1.4') == (1, 0)


@pytest.mark.parametrize('found', ['1.1', '1.9', '2.0', '10.0'])
def test_newer_versions_give_e501_with_upgrade_hint(found: str) -> None:
  with pytest.raises(SpecVersionError) as info:
    check_readable({'scireport': found})
  assert info.value.code == 'E501'
  assert info.value.hint is not None
  assert 'Upgrade scireport' in info.value.hint
  assert found in info.value.message


def test_older_major_gives_e503() -> None:
  with pytest.raises(SpecVersionError) as info:
    check_readable({'scireport': '1.0'}, supported='2.0')
  assert info.value.code == 'E503'


# ---- migrations -------------------------------------------------------------------------------


def test_baseline_migration_is_a_copy() -> None:
  raw: dict[str, Any] = {'scireport': '1.0', 'meta': {'title': 'T'}, 'values': {'a': [1, 2]}}
  out = migrations.migrate(raw)
  assert out == raw
  assert out is not raw
  assert out['values']['a'] is not raw['values']['a']


def test_migrate_restamps_older_minors(monkeypatch: pytest.MonkeyPatch) -> None:
  monkeypatch.setattr(migrations, 'SPEC_VERSION', '1.2')
  assert migrations.migrate({'scireport': '1.0'}, target='1.2')['scireport'] == '1.2'


def test_migrate_refuses_newer_targets_and_inputs() -> None:
  with pytest.raises(SpecVersionError) as info:
    migrations.migrate({'scireport': '1.0'}, target='2.0')
  assert info.value.code == 'E501'
  with pytest.raises(SpecVersionError) as info:
    migrations.migrate({'scireport': '1.5'}, target='1.0')
  assert info.value.code == 'E501'


def test_migrate_runs_registered_major_steps(monkeypatch: pytest.MonkeyPatch) -> None:
  monkeypatch.setattr(migrations, 'SPEC_VERSION', '3.0')
  monkeypatch.setattr(migrations, '_STEPS', {})

  @migrations.register_migration(1)
  def one_to_two(raw: dict[str, object]) -> dict[str, object]:
    return {**raw, 'scireport': '2.0', 'step1': True}

  @migrations.register_migration(2)
  def two_to_three(raw: dict[str, object]) -> dict[str, object]:
    return {**raw, 'scireport': '3.0', 'step2': raw['step1']}

  source = {'scireport': '1.0', 'meta': {}}
  out = migrations.migrate(source, target='3.0')
  assert out == {'scireport': '3.0', 'meta': {}, 'step1': True, 'step2': True}
  assert source == {'scireport': '1.0', 'meta': {}}


def test_migrate_without_a_step_gives_e503(monkeypatch: pytest.MonkeyPatch) -> None:
  monkeypatch.setattr(migrations, 'SPEC_VERSION', '2.0')
  monkeypatch.setattr(migrations, '_STEPS', {})
  with pytest.raises(SpecVersionError) as info:
    migrations.migrate({'scireport': '1.0'}, target='2.0')
  assert info.value.code == 'E503'
