r"""Markdown prose to Markdown, HTML or LaTeX, through a replaceable converter (ADR-0003, ADR-0011).

Prose in templates and ``text`` values is Markdown. A :class:`MarkupConverter` turns it into the
target format. The default backend, :class:`MistletoeConverter`, is pure Python and understands a
**documented subset** of Markdown; anything outside it is shown as plain text and reported as
warning ``W701``, never silently dropped.

The subset
==========

Supported, and rendered alike in HTML and LaTeX:

* paragraphs, hard and soft line breaks, thematic breaks;
* emphasis, strong emphasis, ``~~strikethrough~~`` and inline code;
* links to ``http``, ``https`` and ``mailto`` addresses, and ``<autolinks>``;
* bullet and numbered lists, nested, and block quotes;
* fenced and indented code blocks;
* GFM tables with column alignment (header row required);
* inline ``$...$`` and display ``$$...$$`` math, written in LaTeX. A dollar sign that is not
  math is written ``\$``.

Outside the subset (shown as text, with ``W701``):

* headings (use the ``chapter`` and ``heading`` components, so that the table of contents and
  the numbering stay right);
* images (use the ``figure`` and ``image`` components);
* raw HTML, footnotes (``[^1]``), definition lists and task lists. mistletoe has no footnote
  syntax, so ``[^1]`` stays literal text.

Markdown output keeps the source as written (after removing the common indentation), so it can
be read by people and by language models exactly as authored.
"""

from __future__ import annotations

import html
import re
import textwrap
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, ClassVar
from urllib.parse import urlparse

from mistletoe import block_token
from mistletoe.block_token import Document
from mistletoe.html_renderer import HtmlRenderer
from mistletoe.latex_renderer import LaTeXRenderer
from mistletoe.latex_token import Math

from scireport.errors import Issue
from scireport.render.escape import tex_escape
from scireport.render.math import MathError
from scireport.render.numbers import Target
from scireport.render.safe import Safe

MathHook = Callable[[str, bool], str]
"""Draws math for HTML: ``(latex, display) -> html``; raises :class:`MathError` when it cannot."""

SAFE_SCHEMES = frozenset({'http', 'https', 'mailto'})
"""URL schemes a link may use; anything else is shown as text."""

_RAW_HTML_RE = re.compile(r'</?[A-Za-z][^<>]*>|<!--')
_FOOTNOTE_RE = re.compile(r'\[\^[^\]\s]+\]')
_TASK_RE = re.compile(r'^\[[ xX]\]\s')
_CODE_PARENTS = ('InlineCode', 'CodeFence', 'BlockCode')


@dataclass(frozen=True)
class Converted:
  """The result of converting a piece of prose.

  Parameters
  ----------
  text : Safe
      The prose in the target format.
  issues : tuple of Issue
      Warnings (``W601``, ``W701``); the caller adds the template location.
  """

  text: Safe
  issues: tuple[Issue, ...] = ()


class MarkupConverter(ABC):
  """Turns Markdown prose into the output format; subclass to add a backend."""

  name: ClassVar[str]
  """The engine name used in ``render.markup_engine``."""

  @abstractmethod
  def convert(
    self, source: str, target: Target, *, math: MathHook | None = None, inline: bool = False
  ) -> Converted:
    """Convert Markdown to a target format.

    Parameters
    ----------
    source : str
        Markdown; common indentation is removed first.
    target : {'md', 'html', 'tex'}
        The output format.
    math : callable or None, default=None
        Draws math for HTML (see :data:`MathHook`); without one, math stays as ``$...$``.
    inline : bool, default=False
        The prose is a phrase (a caption, a label): a single paragraph is returned without its
        paragraph wrapper.

    Returns
    -------
    Converted
        The converted prose and its warnings.
    """


class MistletoeConverter(MarkupConverter):
  """The default backend, built on mistletoe (pure Python)."""

  name = 'mistletoe'

  def convert(
    self, source: str, target: Target, *, math: MathHook | None = None, inline: bool = False
  ) -> Converted:
    """Convert Markdown with mistletoe; see :meth:`MarkupConverter.convert`."""
    text = textwrap.dedent(source.replace('\r\n', '\n').replace('\r', '\n')).strip('\n')
    issues: list[Issue] = []
    if target == 'md':
      with _CheckRenderer(issues) as renderer:
        renderer.render(Document(text))
      return Converted(Safe(text), tuple(issues))
    renderer_class = _HtmlRenderer if target == 'html' else _TexRenderer
    with renderer_class(issues, math) as renderer:
      document = Document(text)
      children = list(document.children or ())
      if inline and len(children) == 1 and isinstance(children[0], block_token.Paragraph):
        out = renderer.render_inner(children[0])
      else:
        if inline:
          issues.append(
            Issue('W701', 'only inline Markdown is allowed here; block content was kept as it is')
          )
        out = renderer.render(document)
    return Converted(Safe(out.strip('\n')), tuple(issues))


def default_converter() -> MarkupConverter:
  """Return the converter for ``markup_engine: mistletoe``."""
  return MistletoeConverter()


@dataclass
class _Walker:
  """Visits an AST and reports what is outside the subset, once per construct."""

  issues: list[Issue]
  _seen: set[tuple[str, str]] = field(default_factory=set)

  def warn(self, kind: str, message: str, hint: str, line: int | None = None) -> None:
    """Record a ``W701`` unless the same construct was already reported in this prose."""
    if (kind, message) in self._seen:
      return
    self._seen.add((kind, message))
    where = f' (line {line} of the Markdown block)' if line else ''
    self.issues.append(Issue('W701', message + where, hint=hint))

  def check_text(self, content: str, line: int | None) -> None:
    """Warn about raw HTML, footnote references and task markers in a run of text."""
    if _RAW_HTML_RE.search(content):
      self.warn('html', 'raw HTML is not supported and is shown as text', 'Use Markdown.', line)
    if _FOOTNOTE_RE.search(content):
      self.warn('footnote', 'footnotes are not supported', 'Write the note in the text.', line)
    if _TASK_RE.match(content):
      self.warn('task', 'task lists are not supported', 'Use a plain bullet list.', line)


class _CheckRenderer(HtmlRenderer):
  """Parses like the HTML renderer and only collects warnings (used for Markdown output)."""

  def __init__(self, issues: list[Issue]) -> None:
    super().__init__(Math, process_html_tokens=False)
    self._walker = _Walker(issues)

  def render(self, token: Any) -> str:
    """Render ``token``, reporting the constructs outside the subset on the way."""
    name = type(token).__name__
    if name in ('Heading', 'SetextHeading'):
      self._walker.warn(
        'heading',
        'headings in prose are not supported',
        'Use the chapter and heading components.',
        getattr(token, 'line_number', None),
      )
    elif name == 'Image':
      self._walker.warn(
        'image', 'images in prose are not supported', 'Use a figure or image value.'
      )
    elif name == 'RawText':
      self._walker.check_text(token.content, getattr(token, 'line_number', None))
    elif name == 'Link' and not _safe_url(token.target):
      self._walker.warn('link', f'link to {token.target!r} is not allowed', 'Use http or https.')
    return super().render(token)

  def render_math(self, token: Any) -> str:
    """Math is part of the subset and needs no rendering here."""
    return token.content

  def render_raw_text(self, token: Any) -> str:
    """Return the text; escaping is irrelevant because nothing is written."""
    return str(token.content)


class _HtmlRenderer(_CheckRenderer):
  """HTML output with math drawn by the hook and the constructs outside the subset removed."""

  def __init__(self, issues: list[Issue], math: MathHook | None) -> None:
    super().__init__(issues)
    self._issues = issues
    self._math = math

  def render_raw_text(self, token: Any) -> str:
    """Escape text for HTML."""
    return self.escape_html_text(token.content)

  def render_math(self, token: Any) -> str:
    """Draw math through the hook; on failure show the source and warn (``W601``)."""
    display = token.content.startswith('$$')
    latex = token.content.strip('$').strip()
    if self._math is None:
      return html.escape(token.content)
    try:
      return self._math(latex, display)
    except MathError as exc:
      self._issues.append(Issue('W601', exc.message, hint=exc.hint))
      return f'<code>{html.escape(latex)}</code>'

  def render_heading(self, token: Any) -> str:
    """Show a heading as a bold run-in paragraph."""
    return f'<p class="h--run"><strong>{self.render_inner(token)}</strong></p>'

  def render_image(self, token: Any) -> str:
    """Show the alternative text of an image."""
    return self.render_to_plain(token)

  def render_link(self, token: Any) -> str:
    """Keep links to safe schemes; show the text of any other."""
    if not _safe_url(token.target):
      return self.render_inner(token)
    return super().render_link(token)

  def render_auto_link(self, token: Any) -> str:
    """Keep autolinks to safe schemes; show the text of any other."""
    if not token.mailto and not _safe_url(token.target):
      return self.render_inner(token)
    return super().render_auto_link(token)

  def render_table_cell(self, token: Any, in_header: bool = False) -> str:
    """Write a cell whose alignment is a class, not the obsolete ``align`` attribute."""
    tag = 'th' if in_header else 'td'
    align = 'center' if token.align == 0 else ('right' if token.align == 1 else 'left')
    return f'<{tag} class="align-{align}">{self.render_inner(token)}</{tag}>\n'


class _TexRenderer(LaTeXRenderer):
  """LaTeX body output: escaped text, booktabs tables, verbatim code, native math."""

  def __init__(self, issues: list[Issue], math: MathHook | None) -> None:
    del math
    super().__init__(Math)
    self._walker = _Walker(issues)

  def render(self, token: Any) -> str:
    """Render ``token``, reporting the constructs outside the subset on the way."""
    name = type(token).__name__
    line = getattr(token, 'line_number', None)
    if name in ('Heading', 'SetextHeading'):
      self._walker.warn(
        'heading',
        'headings in prose are not supported',
        'Use the chapter and heading components.',
        line,
      )
    elif name == 'Image':
      self._walker.warn(
        'image', 'images in prose are not supported', 'Use a figure or image value.'
      )
    elif name == 'RawText':
      self._walker.check_text(token.content, line)
    elif name == 'Link' and not _safe_url(token.target):
      self._walker.warn('link', f'link to {token.target!r} is not allowed', 'Use http or https.')
    return super().render(token)

  def render_raw_text(self, token: Any, escape: bool = True) -> str:
    """Escape text for LaTeX."""
    return tex_escape(token.content) if escape else str(token.content)

  def render_inline_code(self, token: Any) -> str:
    """Typeset inline code in the typewriter font, escaped."""
    return rf'\texttt{{{tex_escape(token.children[0].content)}}}'

  def render_emphasis(self, token: Any) -> str:
    r"""Emphasise with ``\emph``, which nests correctly."""
    return rf'\emph{{{self.render_inner(token)}}}'

  def render_image(self, token: Any) -> str:
    """Show the alternative text of an image."""
    return ''.join(self.render(child) for child in token.children)

  def render_link(self, token: Any) -> str:
    """Keep links to safe schemes; show the text of any other."""
    if not _safe_url(token.target):
      return self.render_inner(token)
    return rf'\href{{{self.escape_url(token.target)}}}{{{self.render_inner(token)}}}'

  def render_auto_link(self, token: Any) -> str:
    """Keep autolinks to safe schemes; show the text of any other."""
    target = f'mailto:{token.target}' if token.mailto else token.target
    if not _safe_url(target):
      return tex_escape(token.target)
    return rf'\url{{{self.escape_url(target)}}}'

  def render_math(self, token: Any) -> str:
    r"""Write math natively: ``$...$`` inline and ``\[...\]`` for display."""
    if token.content.startswith('$$'):
      return '\n' + r'\[' + token.content.strip('$').strip() + r'\]' + '\n'
    return token.content

  def render_heading(self, token: Any) -> str:
    """Show a heading as a bold run-in paragraph."""
    return '\n' + r'\par\medskip\noindent\textbf{' + self.render_inner(token) + '}\\par\n'

  def render_quote(self, token: Any) -> str:
    """Write a block quote with the standard ``quote`` environment."""
    return '\\begin{quote}\n' + self.render_inner(token) + '\\end{quote}\n'

  def render_block_code(self, token: Any) -> str:
    """Write a code block as ``verbatim``."""
    code = str(token.children[0].content).replace('\\end{verbatim}', '\\end {verbatim}')
    if not code.endswith('\n'):
      code += '\n'
    return '\n\\begin{verbatim}\n' + code + '\\end{verbatim}\n'

  def render_list(self, token: Any) -> str:
    """Write a list with ``itemize`` or ``enumerate``."""
    tag = 'enumerate' if token.start is not None else 'itemize'
    return f'\\begin{{{tag}}}\n{self.render_inner(token)}\\end{{{tag}}}\n'

  def render_list_item(self, token: Any) -> str:
    r"""Write one ``\item`` with its content on the same line."""
    return f'\\item {self.render_inner(token).strip()}\n'

  def render_table(self, token: Any) -> str:
    """Write a GFM table with booktabs rules."""
    aligns = [{None: 'l', 0: 'c', 1: 'r'}[a] for a in token.column_align]
    rows = []
    if hasattr(token, 'header'):
      rows.append(self.render_table_row(token.header) + '\\midrule\n')
    rows.extend(self.render(child) for child in token.children)
    return (
      '\n\\begin{center}\n'
      f'\\begin{{tabular}}{{{"".join(aligns)}}}\n\\toprule\n'
      + ''.join(rows)
      + '\\bottomrule\n\\end{tabular}\n\\end{center}\n'
    )

  @staticmethod
  def render_thematic_break(token: Any) -> str:
    """Write a horizontal rule."""
    return '\n\\par\\noindent\\rule{\\linewidth}{0.4pt}\\par\n'

  @staticmethod
  def render_line_break(token: Any) -> str:
    r"""Write a soft break as a newline and a hard break as ``\newline``."""
    return '\n' if token.soft else '\\newline\n'

  def render_document(self, token: Any) -> str:
    """Return the body only; the layout owns the document skeleton."""
    return self.render_inner(token)


def _safe_url(target: str) -> bool:
  """Say whether a link target uses an allowed scheme (or none, for a relative link or anchor)."""
  scheme = urlparse(target.strip()).scheme.lower()
  return scheme == '' or scheme in SAFE_SCHEMES
