from pathlib import Path

from scireport.validate.lint import lint_files, macro_names, suggest


def lint(tmp_path: Path, source: str, kind: str = 'neutral', name: str = 'a.j2'):  # type: ignore[no-untyped-def]
  (tmp_path / name).write_text(source, encoding='utf-8')
  return lint_files(tmp_path, [name], kind)  # type: ignore[arg-type]


def paths(result: object) -> list[tuple[str, ...]]:
  return [use.segments for use in result.uses]  # type: ignore[attr-defined]


def test_attribute_chains_and_item_access(tmp_path: Path) -> None:
  result = lint(tmp_path, "{{ data.a.b }}\n{{ data['c']['d'] }}\n{{ data.e['f'].value }}")
  assert paths(result) == [('a', 'b'), ('c', 'd'), ('e', 'f', 'value')]
  assert [use.location for use in result.uses] == ['a.j2:1', 'a.j2:2', 'a.j2:3']
  assert result.issues == ()


def test_key_functions(tmp_path: Path) -> None:
  result = lint(tmp_path, "{{ v('a.b') }}{{ has('c') }}{{ peek('d.e.f') }}")
  assert paths(result) == [('a', 'b'), ('c',), ('d', 'e', 'f')]


def test_computed_keys_warn_and_the_static_part_is_kept(tmp_path: Path) -> None:
  result = lint(tmp_path, "{{ v('a.' ~ n) }}{{ data.x[k].y }}{{ v(k) }}")
  assert [i.code for i in result.issues] == ['W403', 'W403', 'W403']
  assert paths(result) == [('x',)]
  assert result.uses[0].dynamic is True


def test_names_that_are_not_data_are_ignored(tmp_path: Path) -> None:
  result = lint(tmp_path, '{{ other.a.b }}{{ data }}{{ meta.title }}{{ c.table(data.t) }}')
  assert paths(result) == [('t',)]


def test_uses_inside_blocks_and_expressions(tmp_path: Path) -> None:
  source = (
    '{% for i in range(3) %}{% if data.a.flag.value %}{{ c.value(data.b) }}{% endif %}{% endfor %}'
    '{% set x = data.c %}'
  )
  assert paths(lint(tmp_path, source)) == [('a', 'flag', 'value'), ('b',), ('c',)]


def test_syntax_errors_have_a_file_and_line(tmp_path: Path) -> None:
  result = lint(tmp_path, 'ok\n{% if %}\n')
  assert [(i.code, i.location) for i in result.issues] == [('E704', 'a.j2:2')]


def test_included_files_are_followed_and_missing_ones_reported(tmp_path: Path) -> None:
  (tmp_path / 'part.j2').write_text('{{ data.inner }}', encoding='utf-8')
  result = lint(tmp_path, "{% include 'part.j2' %}{% import 'nope.j2' as n %}")
  assert paths(result) == [('inner',)]
  assert [(i.code, i.location) for i in result.issues] == [('E703', 'nope.j2')]


def test_latex_files_use_latex_delimiters(tmp_path: Path) -> None:
  result = lint(tmp_path, r'\textbf{(((data.a)))} {% not a block %}', kind='tex', name='a.tex.j2')
  assert paths(result) == [('a',)]


def test_macro_names(tmp_path: Path) -> None:
  (tmp_path / 'c.j2').write_text(
    '{% macro a() %}{% endmacro %}{% macro b(x) %}{% endmacro %}', encoding='utf-8'
  )
  assert macro_names(tmp_path, 'c.j2', 'md') == {'a', 'b'}
  (tmp_path / 'bad.j2').write_text('{% if %}', encoding='utf-8')
  assert macro_names(tmp_path, 'bad.j2', 'md') is None
  assert macro_names(tmp_path, 'missing.j2', 'md') is None


def test_suggest() -> None:
  assert (
    suggest('crossmatch.n_pair', ['crossmatch.n_pairs', 'x'])
    == "Did you mean 'crossmatch.n_pairs'?"
  )
  assert suggest('zzz', ['crossmatch.n_pairs']) is None
