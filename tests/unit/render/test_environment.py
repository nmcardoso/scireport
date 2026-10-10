import pytest
from jinja2 import DictLoader, UndefinedError
from jinja2.exceptions import SecurityError

from scireport.render.environment import TEX_DELIMITERS, make_environment
from scireport.render.filters import Scientific
from scireport.render.safe import Safe


def render(kind: str, source: str, **context: object) -> str:
  return make_environment(kind).from_string(source).render(**context)  # type: ignore[arg-type]


def out(kind: str, expression: str = 'x') -> str:
  """Return the template source that prints ``expression`` in this kind of file."""
  return f'((( {expression} )))' if kind == 'tex' else '{{ ' + expression + ' }}'


def test_standard_delimiters_in_neutral_md_and_html() -> None:
  for kind in ('neutral', 'md', 'html'):
    assert render(kind, '{% if x %}{{ x }}{# gone #}{% endif %}', x='a') == 'a'


def test_latex_files_use_latex_safe_delimiters() -> None:
  source = (
    r'\emph{(((x)))}((* if x *)) \textbf{{braces}} {#not a comment#} {% not a block %}'
    r'((* endif *))((= gone =))'
  )
  out = render('tex', source, x='a')
  assert out == r'\emph{a} \textbf{{braces}} {#not a comment#} {% not a block %}'


def test_the_tex_delimiters_are_the_documented_ones() -> None:
  assert TEX_DELIMITERS['block_start_string'] == '((*'
  assert TEX_DELIMITERS['variable_start_string'] == '((('
  assert TEX_DELIMITERS['comment_start_string'] == '((='


@pytest.mark.parametrize(
  ('kind', 'expected'),
  [
    ('html', 'a &lt; b &amp; c'),
    ('tex', r'a \textless{} b \& c \_ d'),
    ('md', r'a \< b \& c \_ d'),
    ('neutral', r'a \< b \& c \_ d'),
  ],
)
def test_text_is_escaped_for_the_format(kind: str, expected: str) -> None:
  value = 'a < b & c _ d' if kind != 'html' else 'a < b & c'
  assert render(kind, out(kind), x=value) == expected


@pytest.mark.parametrize('kind', ['neutral', 'md', 'html', 'tex'])
def test_safe_text_is_never_escaped(kind: str) -> None:
  assert render(kind, out(kind), x=Safe('<b>_&</b>')) == '<b>_&</b>'


@pytest.mark.parametrize('kind', ['neutral', 'md', 'tex'])
def test_numbers_none_and_bools_print_plainly(kind: str) -> None:
  source = '|'.join(out(kind, name) for name in 'abcd')
  assert render(kind, source, a=3, b=None, c=True, d=1.5) == '3||true|1.5'


@pytest.mark.parametrize(
  ('kind', 'expected'),
  [
    ('html', '1.23×10<sup>5</sup>'),
    ('tex', r'\ensuremath{1.23\times10^{5}}'),
    ('md', '1.23×10⁵'),
    ('neutral', r'$1.23\times10^{5}$'),
  ],
)
def test_scientific_notation_is_typeset_per_format(kind: str, expected: str) -> None:
  assert render(kind, out(kind), x=Scientific('1.23', 5)) == expected


def test_the_number_filters_are_available() -> None:
  assert render(
    'html', '{{ n | fmt_int }} {{ p | pct }} {{ s | sci }}', n=1234, p=0.5, s=1500.0
  ) == ('1,234 50.00% 1.50×10<sup>3</sup>')


def test_macro_output_is_not_escaped_again() -> None:
  source = '{% macro m(x) %}<{{ x }}>{% endmacro %}{{ m("a&b") }}'
  assert render('neutral', source) == r'<a\&b>'
  assert (
    render('tex', '((* macro m(x) *))\\x{(((x)))}((* endmacro *))(((m("a&b"))))') == r'\x{a\&b}'
  )


def test_call_blocks_return_safe_content() -> None:
  env = make_environment('tex')
  template = env.from_string(
    '((* macro box() *))[(((caller())))]((* endmacro *))((* call box() *))a&b((* endcall *))'
  )
  assert template.render() == '[a&b]'


def test_undefined_names_are_errors() -> None:
  with pytest.raises(UndefinedError):
    render('neutral', '{{ nope }}')


def test_missing_attributes_are_errors() -> None:
  with pytest.raises(UndefinedError):
    render('neutral', '{{ x.nope }}', x={'a': 1})


@pytest.mark.parametrize(
  'source',
  [
    "{{ ''.__class__ }}",
    "{{ ''.__class__.__mro__[1].__subclasses__() }}",
    '{{ cycler.__init__.__globals__ }}',
    '{{ lipsum.__globals__ }}',
    '{{ x.__class__ }}',
    '{{ ().__class__.__bases__[0] }}',
    '{{ [].append.__self__ }}',
    '{{ range.__call__.__self__ }}',
    '{{ dict.mro() }}',
    "{{ joiner.__init__.__globals__['os'] }}",
    "{% for c in ''.__class__.__mro__ %}{{ c }}{% endfor %}",
    '{{ x.f.__globals__ }}',
    '{{ self._TemplateReference__context }}',
  ],
)
def test_sandbox_escape_attempts_are_rejected(source: str) -> None:
  def f() -> None:
    pass

  class Thing:
    def method(self) -> str:
      return 'x'

  with pytest.raises((SecurityError, UndefinedError)):
    render('neutral', source, x=Thing(), f=f) if '.f.' not in source else render(
      'neutral', source, x=type('Holder', (), {'f': staticmethod(f)})()
    )


def test_sandbox_blocks_calling_unsafe_callables() -> None:
  class Danger:
    def run(self) -> str:
      return 'ran'

    run.unsafe_callable = True  # type: ignore[attr-defined]

  with pytest.raises(SecurityError):
    render('neutral', '{{ d.run() }}', d=Danger())


def test_templates_cannot_import_python_modules() -> None:
  with pytest.raises(UndefinedError):
    render('neutral', "{{ __import__('os').system('true') }}")
  with pytest.raises(UndefinedError):
    render('neutral', '{{ os.system("true") }}')


def test_the_environment_can_load_templates() -> None:
  env = make_environment('md', DictLoader({'a.j2': '{{ x }}'}))
  assert env.get_template('a.j2').render(x='_') == r'\_'


def test_whitespace_around_block_tags_is_trimmed() -> None:
  assert render('md', 'a\n  {% if True %}\nb\n  {% endif %}\nc\n') == 'a\nb\nc\n'


def test_the_eol_global_keeps_a_newline_after_a_block_tag() -> None:
  assert render('md', '{% if True %}x{% endif %}{{ eol }}\ny') == 'x\ny'
