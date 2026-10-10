import pytest

from scireport.render.markup import MistletoeConverter, default_converter
from scireport.render.math import MathError
from scireport.render.safe import Safe

SOURCE = """\
    Some *emph*, **strong**, ~~gone~~ and `code_x` with a [link](https://example.org/a_b).

    - one
    - two
      1. nested

    > quoted

    | a | b |
    |:--|--:|
    | 1 & 2 | $\\alpha$ |

    ```python
    print('x')
    ```
"""
conv = MistletoeConverter()


def codes(converted: object) -> list[str]:
  return [issue.code for issue in converted.issues]  # type: ignore[attr-defined]


def fake_math(latex: str, display: bool) -> str:
  return f'<math display="{display}">{latex}</math>'


def test_default_converter_is_mistletoe() -> None:
  assert default_converter().name == 'mistletoe'


def test_markdown_output_is_the_dedented_source() -> None:
  converted = conv.convert(SOURCE, 'md')
  assert isinstance(converted.text, Safe)
  assert converted.text.startswith('Some *emph*')
  assert '| 1 & 2 | $\\alpha$ |' in converted.text
  assert converted.issues == ()


def test_html_output_covers_the_subset() -> None:
  html = conv.convert(SOURCE, 'html', math=fake_math).text
  for expected in (
    '<em>emph</em>',
    '<strong>strong</strong>',
    '<del>gone</del>',
    '<code>code_x</code>',
    '<a href="https://example.org/a_b">link</a>',
    '<ul>',
    '<ol>',
    '<blockquote>',
    '<th class="align-left">a</th>',
    '<th class="align-right">b</th>',
    '<td class="align-left">1 &amp; 2</td>',
    '<math display="False">\\alpha</math>',
    '<pre><code class="language-python">',
  ):
    assert expected in html


def test_tex_output_covers_the_subset() -> None:
  tex = conv.convert(SOURCE, 'tex').text
  for expected in (
    r'\emph{emph}',
    r'\textbf{strong}',
    r'\sout{gone}',
    r'\texttt{code\_x}',
    r'\href{https://example.org/a_b}{link}',
    r'\begin{itemize}',
    r'\begin{enumerate}',
    r'\begin{quote}',
    r'\toprule',
    r'1 \& 2 & $\alpha$ \\',
    r'\begin{verbatim}',
  ):
    assert expected in tex


def test_display_math_is_native_in_tex_and_drawn_in_html() -> None:
  assert r'\[\int f\]' in conv.convert('$$\\int f$$', 'tex').text
  html = conv.convert('$$\\int f$$', 'html', math=fake_math).text
  assert '<math display="True">\\int f</math>' in html


def test_html_without_a_math_hook_keeps_the_dollars() -> None:
  assert '$x$' in conv.convert('a $x$ b', 'html').text


def test_math_that_cannot_be_drawn_becomes_code_and_a_warning() -> None:
  def failing(latex: str, display: bool) -> str:
    raise MathError(latex, 'nope')

  converted = conv.convert('see $\\bad$', 'html', math=failing)
  assert '<code>\\bad</code>' in converted.text
  assert codes(converted) == ['W601']


@pytest.mark.parametrize('target', ['md', 'html', 'tex'])
@pytest.mark.parametrize(
  ('source', 'what'),
  [
    ('# Heading', 'headings'),
    ('![alt](a.png)', 'images'),
    ('raw <b>html</b>', 'raw HTML'),
    ('a note[^1]', 'footnotes'),
    ('[x](javascript:alert(1))', 'not allowed'),
    ('[ ] task', 'task lists'),
  ],
)
def test_constructs_outside_the_subset_warn_in_every_format(
  target: str, source: str, what: str
) -> None:
  converted = conv.convert(source, target)  # type: ignore[arg-type]
  assert codes(converted) == ['W701']
  assert what in converted.issues[0].message


def test_each_unsupported_construct_is_reported_once() -> None:
  converted = conv.convert('[^1] and again [^2]', 'html')
  assert codes(converted) == ['W701']


def test_headings_become_bold_paragraphs() -> None:
  assert '<p class="h--run"><strong>T</strong></p>' in conv.convert('# T', 'html').text
  assert r'\textbf{T}' in conv.convert('# T', 'tex').text


def test_dangerous_links_keep_their_text_only() -> None:
  assert 'javascript' not in conv.convert('[x](javascript:alert(1))', 'html').text
  assert 'javascript' not in conv.convert('[x](javascript:alert(1))', 'tex').text
  assert '<a href="#top">x</a>' in conv.convert('[x](#top)', 'html').text


def test_raw_html_is_escaped() -> None:
  assert '&lt;script&gt;' in conv.convert('<script>alert(1)</script>', 'html').text


def test_tex_special_characters_are_escaped() -> None:
  tex = conv.convert('50% of $5 & #1 _x_', 'tex').text
  assert r'50\% of ' in tex
  assert r'\#1' in tex


def test_inline_conversion_drops_the_paragraph_wrapper() -> None:
  assert conv.convert('A *phrase*', 'html', inline=True).text == 'A <em>phrase</em>'
  assert conv.convert('A *phrase*', 'tex', inline=True).text == r'A \emph{phrase}'


def test_inline_conversion_of_blocks_warns() -> None:
  converted = conv.convert('one\n\ntwo', 'html', inline=True)
  assert codes(converted) == ['W701']
  assert converted.text.count('<p>') == 2


def test_windows_line_endings_are_accepted() -> None:
  assert '<li>a</li>' in conv.convert('- a\r\n- b\r\n', 'html').text


def test_tokens_do_not_leak_between_conversions() -> None:
  conv.convert('$x$', 'tex')
  assert '$x$' in conv.convert('a $x$', 'html').text  # no hook: math token handled afresh
