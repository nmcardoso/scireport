r"""Markdown prose to HTML or LaTeX through pandoc (ADR-0011).

:class:`PandocConverter` is the ``markup_engine: pandoc`` backend. It reads the prose with
pandoc's CommonMark reader (:data:`~scireport.render.pandoc.PROSE_READER`), edits the document
tree so that it follows the same rules as the default backend, and writes it with pandoc.

The rules that both backends share:

* headings and images in prose are shown as a bold paragraph and as their alternative text, and
  reported as ``W701``;
* raw HTML and raw LaTeX are shown as text (``W701``), never passed through;
* a link is kept only for ``http``, ``https`` and ``mailto`` addresses, or when it is relative;
* math is drawn by the hook for HTML and written natively for LaTeX.

What pandoc adds, and mistletoe does not read: footnotes (``[^1]``), definition lists, task
lists, and full GitHub-flavoured tables. ``docs/markup.md`` lists the differences in the output.

Markdown output is the source as written, like the default backend; pandoc only checks it.
"""

from __future__ import annotations

import textwrap
from typing import ClassVar

from scireport.errors import Issue
from scireport.render.markup import (
  Converted,
  MarkupConverter,
  MathHook,
  ProseWalker,
  safe_url,
)
from scireport.render.math import MathError
from scireport.render.numbers import Target
from scireport.render.pandoc import Node, read_ast, walk, write_ast
from scireport.render.safe import Safe

_TEX_SUPPORT = r"""% scireport: what the LaTeX written by pandoc needs (markup_engine: pandoc).
\makeatletter
\@ifpackageloaded{booktabs}{}{\usepackage{booktabs}}
\@ifpackageloaded{longtable}{}{\usepackage{longtable}}
\@ifpackageloaded{ulem}{}{\usepackage[normalem]{ulem}}
\@ifundefined{c@none}{\newcounter{none}}{}
\makeatother
\providecommand{\tightlist}{\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}
\providecommand{\st}[1]{\sout{#1}}
"""

_HTML_ARGS = ('--wrap=none', '--no-highlight')
_TEX_ARGS = ('--wrap=none', '--columns=100000', '--no-highlight')


class PandocConverter(MarkupConverter):
  """The ``pandoc`` backend: higher fidelity than mistletoe, needs ``scireport[pandoc]``."""

  name: ClassVar[str] = 'pandoc'

  def __init__(self) -> None:
    self._count = 0
    self._wrote_tex = False

  def convert(
    self, source: str, target: Target, *, math: MathHook | None = None, inline: bool = False
  ) -> Converted:
    """Convert Markdown with pandoc; see :meth:`MarkupConverter.convert`.

    Raises
    ------
    MissingDependencyError
        With ``E506`` when pandoc is not installed.
    PandocError
        With ``E507`` when pandoc fails.
    """
    text = textwrap.dedent(source.replace('\r\n', '\n').replace('\r', '\n')).strip('\n')
    issues: list[Issue] = []
    document = read_ast(text)
    blocks = _neutralise(document['blocks'], issues, target, math)
    if target == 'md':
      return Converted(Safe(text), tuple(issues))
    if inline:
      if len(blocks) == 1 and blocks[0]['t'] == 'Para':
        blocks = [{'t': 'Plain', 'c': blocks[0]['c']}]
      else:
        issues.append(
          Issue('W701', 'only inline Markdown is allowed here; block content was kept as it is')
        )
    self._count += 1
    edited = {**document, 'blocks': blocks}
    if target == 'html':
      out = write_ast(edited, 'html', [*_HTML_ARGS, f'--id-prefix=s{self._count}-'])
    else:
      self._wrote_tex = True
      out = write_ast(edited, 'latex', _TEX_ARGS)
    return Converted(Safe(out.strip('\n')), tuple(issues))

  def tex_preamble(self) -> str:
    """Return the definitions the LaTeX written so far needs, or '' when none was written."""
    return _TEX_SUPPORT if self._wrote_tex else ''


def _neutralise(
  blocks: list[Node], issues: list[Issue], target: Target, math: MathHook | None
) -> list[Node]:
  """Apply the shared rules to a document's blocks and return the edited blocks."""
  report = ProseWalker(issues)

  def visit(node: Node) -> Node | list[Node] | None:
    kind = node['t']
    if kind == 'Header':
      report.warn(
        'heading', 'headings in prose are not supported', 'Use the chapter and heading components.'
      )
      return {'t': 'Para', 'c': [{'t': 'Strong', 'c': node['c'][2]}]}
    if kind == 'Image':
      report.warn('image', 'images in prose are not supported', 'Use a figure or image value.')
      alt: list[Node] = node['c'][1]
      return alt
    if kind == 'Figure':
      content: list[Node] = node['c'][2]
      return content
    if kind == 'Link' and not safe_url(node['c'][2][0]):
      report.warn('link', f'link to {node["c"][2][0]!r} is not allowed', 'Use http or https.')
      text: list[Node] = node['c'][1]
      return text
    if kind == 'RawInline':
      report.warn('html', 'raw HTML is not supported and is shown as text', 'Use Markdown.')
      return {'t': 'Code', 'c': [['', [], []], node['c'][1]]}
    if kind == 'RawBlock':
      report.warn('html', 'raw HTML is not supported and is shown as text', 'Use Markdown.')
      return {
        't': 'CodeBlock',
        'c': [['', [], []], node['c'][1].rstrip('\n')],
      }
    if kind == 'Math' and target == 'html' and math is not None:
      return _draw(node, math, issues)
    return None

  edited: list[Node] = walk(blocks, visit)
  return edited


def _draw(node: Node, math: MathHook, issues: list[Issue]) -> Node:
  """Replace a math node by the HTML the hook draws; on failure show the source as code."""
  mode, latex = node['c'][0]['t'], node['c'][1].strip()
  try:
    return {'t': 'RawInline', 'c': ['html', math(latex, mode == 'DisplayMath')]}
  except MathError as exc:
    issues.append(Issue('W601', exc.message, hint=exc.hint))
    return {'t': 'Code', 'c': [['', [], []], latex]}
