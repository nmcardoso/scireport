import pytest

from scireport.bundle.textio import MAX_MANIFEST_BYTES, parse_manifest_text
from scireport.errors import BundleError


def yaml_load(text: str) -> object:
  return parse_manifest_text(text.encode(), yaml_format=True, origin='t.yaml')


def json_load(text: str | bytes) -> object:
  data = text if isinstance(text, bytes) else text.encode()
  return parse_manifest_text(data, yaml_format=False, origin='t.json')


def test_json_basics_and_bom() -> None:
  assert json_load('{"a": [1, 2.5, null, true]}') == {'a': [1, 2.5, None, True]}
  assert json_load(b'\xef\xbb\xbf{"a": 1}') == {'a': 1}


@pytest.mark.parametrize(
  'text', ['{"a": 1, "a": 2}', '{"a": NaN}', '{"a": Infinity}', '{"a": ', '', b'\xff\xfe\x00']
)
def test_json_rejections(text: str | bytes) -> None:
  with pytest.raises(BundleError) as info:
    json_load(text)
  assert info.value.code == 'E408'


def test_yaml_follows_the_core_schema() -> None:
  doc = yaml_load(
    """
    a: yes
    b: no
    c: on
    d: 2026-10-09
    e: 12:30
    f: 007
    g: 1_000
    h: 1e3
    i: ~
    j: true
    k: False
    l: 0x1F
    m: 3
    n: -4.5
    o: .5
    p: 1.
    """
  )
  assert doc == {
    'a': 'yes',
    'b': 'no',
    'c': 'on',
    'd': '2026-10-09',
    'e': '12:30',
    'f': '007',
    'g': '1_000',
    'h': 1000.0,
    'i': None,
    'j': True,
    'k': False,
    'l': '0x1F',
    'm': 3,
    'n': -4.5,
    'o': 0.5,
    'p': 1.0,
  }


def test_yaml_rejects_duplicate_keys_and_aliases() -> None:
  with pytest.raises(BundleError, match='duplicate key'):
    yaml_load('a: 1\na: 2\n')
  with pytest.raises(BundleError, match='aliases'):
    yaml_load('a: &x [1]\nb: *x\n')


def test_yaml_syntax_error_is_e408() -> None:
  with pytest.raises(BundleError) as info:
    yaml_load('a: [1, 2\n')
  assert info.value.code == 'E408'


def test_oversized_manifest_is_refused() -> None:
  with pytest.raises(BundleError, match='limit'):
    parse_manifest_text(b' ' * (MAX_MANIFEST_BYTES + 1), yaml_format=False, origin='big')
