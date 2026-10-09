"""The Jinja environments: sandboxed, strict, and escaping for the format being written (ADR-0003).

Four kinds exist. ``neutral`` renders the format-neutral ``report.j2``; its text is Markdown
source, so the strings a template prints are Markdown-escaped. ``md``, ``html`` and ``tex``
render the files of a layout (and the optional per-format overrides of a template) and escape
for their own format. LaTeX files use the delimiters ``((* *))``, ``((( )))`` and ``((= =))``
because ``{%`` and ``{#`` clash with TeX; neutral templates never contain raw TeX, so they keep
the standard ones.

Every environment is a :class:`~jinja2.sandbox.SandboxedEnvironment` with
:class:`~jinja2.StrictUndefined`: a template cannot reach Python internals, import modules or
read a name that does not exist. A string a component or the ``md`` filter returns is a
:class:`~scireport.render.safe.Safe` and is never escaped again.
"""

from __future__ import annotations

from typing import Any, Literal

from jinja2 import BaseLoader, StrictUndefined
from jinja2.runtime import Context, Macro
from jinja2.sandbox import SandboxedEnvironment
from markupsafe import Markup

from scireport.render.data import MissingValue
from scireport.render.escape import md_escape, tex_escape
from scireport.render.filters import FILTERS, Scientific
from scireport.render.numbers import typeset_scientific
from scireport.render.safe import Safe

EnvKind = Literal['neutral', 'md', 'html', 'tex']

TEX_DELIMITERS = {
  'block_start_string': '((*',
  'block_end_string': '*))',
  'variable_start_string': '(((',
  'variable_end_string': ')))',
  'comment_start_string': '((=',
  'comment_end_string': '=))',
}
"""LaTeX-safe Jinja delimiters, used by ``tex`` environments only."""

_TEX_BREAK_AFTER = frozenset('/_-.')


class ReportEnvironment(SandboxedEnvironment):
  """A sandboxed environment whose macros return :class:`~scireport.render.safe.Safe` text.

  A macro writes already-escaped output. Without HTML autoescaping Jinja returns a plain string
  from a macro, and ``finalize`` would escape it a second time when another macro or template
  prints it. Marking the result of every macro (and of ``caller()``) as safe keeps composition
  of macros correct in all four kinds of environment.
  """

  def call(self, context: Context, obj: Any, /, *args: Any, **kwargs: Any) -> Any:
    """Call an object from a template; the output of a macro is marked safe."""
    result = super().call(context, obj, *args, **kwargs)
    if isinstance(obj, Macro) and isinstance(result, str) and not isinstance(result, Safe | Markup):
      return Safe(result)
    return result


def make_environment(kind: EnvKind, loader: BaseLoader | None = None) -> ReportEnvironment:
  """Create a sandboxed, strict environment for one kind of file.

  Parameters
  ----------
  kind : {'neutral', 'md', 'html', 'tex'}
      Which files the environment renders; it decides delimiters and escaping.
  loader : jinja2.BaseLoader or None, default=None
      Where templates are loaded from; None for an environment that only compiles strings.

  Returns
  -------
  ReportEnvironment
      The environment, with the number filters registered.
  """
  options: dict[str, Any] = {}
  if kind == 'tex':
    options.update(TEX_DELIMITERS)
  env = ReportEnvironment(
    loader=loader,
    undefined=StrictUndefined,
    autoescape=kind == 'html',
    finalize=_finalizer(kind),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
    extensions=['jinja2.ext.do', 'jinja2.ext.loopcontrols'],
    **options,
  )
  env.filters.update(FILTERS)
  env.globals['eol'] = Safe('')
  if kind == 'tex':
    env.filters['breakable'] = _tex_breakable
  return env


def _finalizer(kind: EnvKind) -> Any:
  """Build the function Jinja applies to every ``{{ expression }}`` before it is written."""

  def finalize(value: Any) -> Any:
    if isinstance(value, Safe | Markup):
      return value if kind == 'html' else str(value)
    if value is None or isinstance(value, MissingValue):
      return ''
    if isinstance(value, Scientific):
      return _scientific(value, kind)
    if isinstance(value, bool):
      return 'true' if value else 'false'
    if isinstance(value, int | float):
      return str(value)
    text = value if isinstance(value, str) else str(value)
    if kind == 'html':
      return text
    if kind == 'tex':
      return tex_escape(text)
    return md_escape(text)

  return finalize


def _scientific(value: Scientific, kind: EnvKind) -> Any:
  """Typeset scientific notation for the kind of file being written."""
  if kind == 'neutral':
    if value.mantissa == '0' and value.exponent == 0:
      return '0'
    return rf'${value.mantissa}\times10^{{{value.exponent}}}$'
  text = typeset_scientific(value, kind)
  return Safe(text) if kind in ('html', 'tex') else text


def _tex_breakable(text: Any) -> Safe:
  """Escape text for LaTeX and allow a line break after path separators."""
  if text is None:
    return Safe('')
  pieces = [
    tex_escape(char) + (r'\allowbreak{}' if char in _TEX_BREAK_AFTER else '') for char in str(text)
  ]
  return Safe(''.join(pieces))
