"""One render of one bundle into one output format.

A :class:`RenderSession` owns everything that changes during a render: the outline, the usage
tracker, the issues found so far, the files a format needs next to its main document (figures,
attachments) and the Jinja environments. The steps are those of ADR-0003: render the body (which
collects the outline and the table of contents in a single pass), then wrap it in the layout's
document skeleton, then let the output writer split and complete the result.
"""

from __future__ import annotations

import hashlib
import html
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from jinja2 import FileSystemLoader, TemplateSyntaxError
from jinja2.exceptions import SecurityError, TemplateRuntimeError, UndefinedError

from scireport._version import __version__
from scireport.bundle.reader import Bundle
from scireport.errors import Issue, MissingDependencyError, ScireportError, TemplateError
from scireport.logging_utils import get_logger
from scireport.render.components import COMPONENT_MACROS, Components
from scireport.render.data import DataNamespace, ValueStore
from scireport.render.definition import Format
from scireport.render.environment import make_environment
from scireport.render.layout import Layout, OptionValue
from scireport.render.locate import current_location, exception_location, syntax_location
from scireport.render.markup import MarkupConverter
from scireport.render.math import DEFAULT_COLOR, MathError, render_math
from scireport.render.outline import Outline
from scireport.render.safe import Safe
from scireport.render.template import Template
from scireport.spec.manifest import Manifest, OutlineNode, manifest_to_json

log = get_logger(__name__)


@dataclass(frozen=True)
class Info:
  """Facts about the render that templates and layouts may print.

  Parameters
  ----------
  scireport_version : str
      The version of scireport doing the render.
  template : str
      ``name@version`` of the template.
  layout : str
      ``name@version`` of the layout.
  format : str
      ``md``, ``html`` or ``tex``.
  manifest_sha256 : str
      SHA-256 of the canonical manifest, which identifies the content without a path or a date.
  generated : str
      The generated-file notice, plain text, for the header comment of every output.
  split : bool
      Whether the Markdown output is split into one file per chapter.
  latex_engine : str
      The TeX engine the project is meant for.
  """

  scireport_version: str
  template: str
  layout: str
  format: str
  manifest_sha256: str
  generated: str
  split: bool
  latex_engine: str


@dataclass(frozen=True)
class RenderedFormat:
  r"""What one render produced.

  Parameters
  ----------
  fmt : {'md', 'html', 'tex'}
      The format.
  files : dict
      Relative path to content. Text is UTF-8 with ``\n`` line endings.
  issues : tuple of Issue
      Everything found while rendering, warnings included.
  wants_split : bool
      Whether the body asked for a split Markdown document (a chapter with ``md_file``).
  """

  fmt: Format
  files: dict[str, bytes]
  issues: tuple[Issue, ...]
  wants_split: bool = False


class RenderSession:
  """Renders a bundle with a template and a layout into one format.

  Parameters
  ----------
  bundle : Bundle
      The opened, verified bundle.
  template : Template
      The template.
  layout : Layout
      The layout.
  fmt : {'md', 'html', 'tex'}
      The output format.
  options : dict
      The layout options, resolved (see :meth:`~scireport.render.layout.Layout.resolve_options`).
  converter : MarkupConverter
      Turns Markdown prose into the format.
  md_split : bool, default=False
      Write Markdown as an index plus one file per chapter that names a file.
  latex_engine : str, default='lualatex'
      The TeX engine the LaTeX project is meant for.
  math_color : str, default=DEFAULT_COLOR
      Colour of equations drawn for HTML.
  math_renderer : {'mathtext', 'usetex'}, default='mathtext'
      How equations are drawn for HTML.
  """

  def __init__(
    self,
    bundle: Bundle,
    template: Template,
    layout: Layout,
    fmt: Format,
    *,
    options: dict[str, OptionValue],
    converter: MarkupConverter,
    md_split: bool = False,
    latex_engine: str = 'lualatex',
    math_color: str = DEFAULT_COLOR,
    math_renderer: str = 'mathtext',
  ) -> None:
    self.bundle = bundle
    self.template = template
    self.layout = layout
    self.fmt = fmt
    self.options = options
    self.converter = converter
    self.md_split = md_split
    self.math_color = math_color
    self.math_renderer = math_renderer
    self.issues: list[Issue] = []
    self.files: dict[str, bytes] = {}
    self.outline = Outline()
    self.store = ValueStore(bundle.manifest.values, self._missing_key)
    self.c = Components(self)
    self._roots = [template.root, layout.root]
    self._counters: dict[str, int] = {}
    self._module: Any = None
    digest = hashlib.sha256(manifest_to_json(bundle.manifest).encode('utf-8')).hexdigest()
    self.info = Info(
      scireport_version=__version__,
      template=template.ref,
      layout=layout.ref,
      format=fmt,
      manifest_sha256=digest,
      generated=(
        f'Generated by scireport {__version__} (template {template.ref}, layout {layout.ref}) '
        f'from a bundle with manifest sha256 {digest[:12]}. Do not edit.'
      ),
      split=md_split,
      latex_engine=latex_engine,
    )
    self._wants_split = False

  # ---- the render -----------------------------------------------------------------------

  def render(self) -> tuple[str, str]:
    """Render the body and wrap it in the layout's document skeleton.

    Returns
    -------
    tuple of (str, str)
        The body and the finished document. Both are empty when rendering failed; the reason is
        in :attr:`issues`.
    """
    try:
      body = self._render_body()
      document = self._render_document(body)
    except (TemplateSyntaxError, UndefinedError, SecurityError, TemplateRuntimeError) as exc:
      self._record_exception(exc)
      return '', ''
    except MissingDependencyError:
      raise
    except ScireportError as exc:
      location = exception_location(exc, self._roots)
      self.issues.extend(_located(issue, location) for issue in exc.issues)
      return '', ''
    except Exception as exc:  # a template can make any component or filter fail
      self._record_exception(exc)
      return '', ''
    for key in self.store.tracker.leftovers():
      self.issues.append(
        Issue(
          'W401',
          f'value {key!r} is in the bundle but the template never renders it',
          pointer=f'/values/{key}',
          key=key,
          location=self.template.ref,
        )
      )
    return body, document

  @property
  def wants_split(self) -> bool:
    """Whether a chapter asked for its own Markdown file (``md_file``)."""
    return self._wants_split

  def next_number(self, kind: str) -> int:
    """Return the next number of a counter (``table``, ``figure``, ``equation``), from 1."""
    self._counters[kind] = self._counters.get(kind, 0) + 1
    return self._counters[kind]

  def macro(self, name: str) -> Callable[..., Any]:
    """Return the layout macro that draws a component.

    Parameters
    ----------
    name : str
        A component name from :data:`~scireport.render.components.COMPONENT_MACROS`.

    Returns
    -------
    callable
        The macro, called with keyword arguments.
    """
    if self._module is None:
      self._module = self._load_components()
    macro: Callable[..., Any] = getattr(self._module, name)
    return macro

  def convert(self, source: str, *, inline: bool = False) -> Safe:
    """Convert Markdown prose to the output format, recording its warnings.

    Parameters
    ----------
    source : str
        Markdown.
    inline : bool, default=False
        The prose is a phrase, not a block.

    Returns
    -------
    Safe
        The converted prose.
    """
    hook = self._draw_math if self.fmt == 'html' else None
    converted = self.converter.convert(source, self.fmt, math=hook, inline=inline)
    location = current_location(self._roots)
    self.issues.extend(_located(issue, location) for issue in converted.issues)
    return converted.text

  def math_html(self, latex: str, display: bool) -> str:
    """Draw math for HTML; on failure record ``W601`` and show the source."""
    try:
      return self._draw_math(latex, display)
    except MathError as exc:
      self.report(exc.code, exc.message, hint=exc.hint)
      return f'<code>{html.escape(latex)}</code>'

  def add_file(self, path: str, data: bytes) -> None:
    """Add a file the format needs next to its main document (a figure, an attachment)."""
    self.files[path] = data

  def report(
    self,
    code: str,
    message: str,
    *,
    key: str | None = None,
    hint: str | None = None,
    expected: str | None = None,
    found: str | None = None,
  ) -> None:
    """Record a problem found during rendering, with the template line that caused it."""
    self.issues.append(
      Issue(
        code,
        message,
        pointer=f'/values/{key}' if key else '',
        key=key,
        expected=expected,
        found=found,
        hint=hint,
        location=current_location(self._roots),
      )
    )

  # ---- internals ------------------------------------------------------------------------

  def _render_body(self) -> str:
    """Render the template body for this format."""
    neutral = self.template.is_neutral(self.fmt)
    env = make_environment(
      'neutral' if neutral else self.fmt, FileSystemLoader(str(self.template.root))
    )
    env.filters['md'] = lambda text: self.convert(str(text))
    env.globals.update(self._globals())
    template = env.get_template(self.template.entry_for(self.fmt))
    body = template.render()
    self._wants_split = len(self.outline.files) > 1
    return body

  def _render_document(self, body: str) -> str:
    """Wrap the body in the layout's document skeleton."""
    from scireport.render.outputs import skeleton_variables

    files = self.layout.files(self.fmt)
    env = make_environment(self.fmt, FileSystemLoader(str(self.layout.root)))
    env.filters['md'] = lambda text: self.convert(str(text))
    env.globals.update(self._globals())
    template = env.get_template(files.document)
    return template.render(**skeleton_variables(self, body))

  def _load_components(self) -> Any:
    """Compile the layout's component macros and check that every one exists."""
    files = self.layout.files(self.fmt)
    env = make_environment(self.fmt, FileSystemLoader(str(self.layout.root)))
    env.filters['md'] = lambda text: self.convert(str(text))
    env.globals.update(
      {'options': self.options, 'meta': self.bundle.manifest.meta, 'info': self.info}
    )
    module = env.get_template(files.components).make_module()
    missing = [name for name in COMPONENT_MACROS if not callable(getattr(module, name, None))]
    if missing:
      issues = [
        Issue(
          'E707',
          f'layout {self.layout.ref} does not define the {name!r} component for {self.fmt}',
          location=files.components,
        )
        for name in missing
      ]
      raise TemplateError(issues[0].describe(), code='E707', issues=issues)
    return module

  def _globals(self) -> dict[str, Any]:
    """Build the names a template can use."""
    return {
      'c': self.c,
      'data': DataNamespace(self.store),
      'v': self.store.get,
      'has': self.store.has,
      'peek': self.store.peek,
      'keys': self.store.keys,
      'md': lambda text, inline=True: self.convert(str(text), inline=inline),
      'meta': self.bundle.manifest.meta,
      'options': self.options,
      'info': self.info,
      'outline': effective_outline(self.bundle.manifest),
    }

  def _draw_math(self, latex: str, display: bool) -> str:
    """Draw math as an HTML image; raises :class:`MathError` when mathtext cannot."""
    svg = render_math(latex, display=display, color=self.math_color, renderer=self.math_renderer)
    alt = html.escape(latex, quote=True)
    if display:
      return f'<img class="math-display" src="{svg.data_uri}" alt="{alt}">'
    return (
      f'<img class="math-inline" src="{svg.data_uri}" alt="{alt}" '
      f'style="vertical-align: {-svg.depth_pt:.2f}pt;">'
    )

  def _missing_key(self, key: str, hint: str | None) -> None:
    """Record ``E106`` for a key the template reads and the bundle lacks."""
    self.report(
      'E106', f'the template reads key {key!r}, which the bundle does not have', key=key, hint=hint
    )

  def _record_exception(self, exc: BaseException) -> None:
    """Turn an exception from a template into an issue with its file and line."""
    if isinstance(exc, TemplateSyntaxError):
      self.issues.append(
        Issue('E704', exc.message or str(exc), location=syntax_location(exc, self._roots))
      )
      return
    location = exception_location(exc, self._roots)
    if isinstance(exc, SecurityError):
      code, message = 'E802', f'the sandbox forbids this: {exc}'
    elif isinstance(exc, UndefinedError):
      code, message = 'E803', str(exc)
    else:
      code, message = 'E804', f'{type(exc).__name__}: {exc}'
    self.issues.append(Issue(code, message, location=location))


def effective_outline(manifest: Manifest) -> list[OutlineNode]:
  """Return the outline the ``generic`` template renders.

  The manifest's own outline when it has one. Otherwise every value, grouped by the first segment
  of its key: values without a dot first, then one chapter per group, in key order.

  Parameters
  ----------
  manifest : Manifest
      The manifest.

  Returns
  -------
  list of OutlineNode
      The outline.
  """
  if manifest.outline is not None:
    return manifest.outline
  loose: list[OutlineNode] = []
  groups: dict[str, list[OutlineNode]] = {}
  for key in sorted(manifest.values):
    head, _, rest = key.partition('.')
    node = OutlineNode(key=key)
    if rest:
      groups.setdefault(head, []).append(node)
    else:
      loose.append(node)
  chapters = [
    OutlineNode(title=head.replace('-', ' ').replace('_', ' ').capitalize(), children=children)
    for head, children in groups.items()
  ]
  return loose + chapters


def _located(issue: Issue, location: str | None) -> Issue:
  """Add a template location to an issue that has none."""
  if issue.location or not location:
    return issue
  return Issue(
    issue.code,
    issue.message,
    issue.pointer,
    issue.key,
    issue.expected,
    issue.found,
    issue.hint,
    location,
  )
