"""The component layer: ``c.chapter``, ``c.table``, ``c.figure`` and the rest (ADR-0003).

A template calls components; a component turns a bundle value into a plain-data spec (see
:mod:`scireport.render.specs`), asks the layout's macro of the same name to draw it, and returns
the result as a :class:`~scireport.render.safe.Safe` string. A template never writes a CSS class
or a LaTeX environment: only the layout's macro files do. A component that is given the wrong
kind of value, or a value that cannot be drawn in the current format, records an aggregated
issue (``E208``, ``E209``, ``E210``) and renders nothing, so one render reports every problem.
"""

from __future__ import annotations

import base64
import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from scireport.render.data import DataNamespace, MissingValue
from scireport.render.filters import fmt_bytes
from scireport.render.numbers import Target, escape_text, format_number_value
from scireport.render.safe import EMPTY, Safe
from scireport.render.specs import (
  CoverSpec,
  EquationSpec,
  FigureSpec,
  LinkSpec,
  MetricSpec,
  StageSpec,
)
from scireport.render.tables import build_table
from scireport.spec.kinds import (
  AlertValue,
  AttachmentValue,
  BoolValue,
  CodeValue,
  DateValue,
  Envelope,
  FigureValue,
  FlowValue,
  ImageValue,
  ListValue,
  MappingValue,
  MathValue,
  MetricsValue,
  NumberValue,
  StatusValue,
  TableValue,
  TextValue,
)

if TYPE_CHECKING:
  from scireport.render.session import RenderSession

EMBED_LIMIT_BYTES = 2 * 1024 * 1024
"""Largest attachment embedded in an HTML file as a ``data:`` link."""

COMPONENT_MACROS: tuple[str, ...] = (
  'chapter',
  'heading',
  'contents',
  'cover',
  'table',
  'figure',
  'image',
  'equation',
  'metrics',
  'status',
  'alert',
  'flow',
  'metadata',
  'bullets',
  'code',
  'details',
  'note',
  'paragraph',
  'fact',
  'attachment',
  'spacer',
  'page_break',
)
"""The macros every layout's components file must define for every format it supports."""

_MD_FILE_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]*\.md')
_FIGURE_ORDER = {'md': ('png', 'svg'), 'html': ('png', 'svg'), 'tex': ('pdf', 'png')}
_IMAGE_ORDER = {
  'md': ('png', 'jpg', 'jpeg', 'svg'),
  'html': ('png', 'jpg', 'jpeg', 'svg'),
  'tex': ('pdf', 'png', 'jpg', 'jpeg'),
}
_MEDIA = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'svg': 'image/svg+xml'}
FILE_MARKER = '<!-- scireport-file: {name} -->'
"""Line that starts a new Markdown file in a split document; the md writer removes it."""


class Components:
  """The ``c`` object templates call; one per render.

  Only public methods are reachable from a template (the sandbox blocks names that start with an
  underscore), and each is a component of the layout API.

  Parameters
  ----------
  session : RenderSession
      The render this belongs to.
  """

  def __init__(self, session: RenderSession) -> None:
    self._s = session
    self._target: Target = session.fmt

  # ---- structure ------------------------------------------------------------------------

  def chapter(
    self,
    title: str,
    *,
    md_file: str | None = None,
    page_break: bool | None = None,
    in_contents: bool = True,
  ) -> Safe:
    """Start a chapter: the top level of the table of contents.

    Parameters
    ----------
    title : str
        Chapter title, plain text.
    md_file : str or None, default=None
        In a split Markdown document, write this chapter (and what follows until the next
        chapter with a file) to this file. Ignored by the other formats.
    page_break : bool or None, default=None
        Force or forbid a page break before the chapter; None lets the layout decide.
    in_contents : bool, default=True
        List the chapter in the table of contents.

    Returns
    -------
    Safe
        The chapter opener.
    """
    if md_file is not None and not _MD_FILE_RE.fullmatch(md_file):
      self._s.report('E801', f'md_file {md_file!r} is not a plain .md file name', found=md_file)
      md_file = None
    entry = self._s.outline.chapter(str(title), md_file=md_file, in_contents=in_contents)
    out = self._call('chapter', title=title, entry=entry, page_break=page_break)
    if self._target == 'md' and self._s.md_split and md_file:
      out = Safe(FILE_MARKER.format(name=md_file) + '\n' + out)
    return out

  def heading(
    self,
    text: str,
    level: int = 1,
    *,
    page_break: bool | None = None,
    in_contents: bool = True,
  ) -> Safe:
    """Write a heading below the current chapter.

    Parameters
    ----------
    text : str
        Heading text, plain text.
    level : int, default=1
        1 (section) to 3; a different number records ``E801`` and is clamped.
    page_break : bool or None, default=None
        Force or forbid a page break before the heading; None lets the layout decide.
    in_contents : bool, default=True
        List the heading in the table of contents.

    Returns
    -------
    Safe
        The heading.
    """
    if level not in (1, 2, 3):
      self._s.report('E801', f'heading level must be 1, 2 or 3, got {level!r}', found=str(level))
      level = min(max(int(level), 1), 3)
    entry = self._s.outline.heading(str(text), level, in_contents=in_contents)
    return self._call('heading', text=text, level=level, entry=entry, page_break=page_break)

  def contents(self) -> Safe:
    """Write the table of contents from the headings rendered so far.

    Call it from the layout's document skeleton, which is rendered after the body.

    Returns
    -------
    Safe
        The table of contents, or nothing when there are no listed headings.
    """
    entries = self._s.outline.entries
    return self._call('contents', entries=entries) if entries else EMPTY

  def cover(self) -> Safe:
    """Write the cover from the ``meta`` block of the bundle.

    Returns
    -------
    Safe
        The cover.
    """
    meta = self._s.bundle.manifest.meta
    authors = tuple(
      f'{a.name} ({a.affiliation})' if a.affiliation else a.name for a in meta.authors
    )
    spec = CoverSpec(
      title=meta.title,
      subtitle=meta.subtitle or '',
      authors=authors,
      date=meta.date or '',
      version=meta.version or '',
      pipeline=meta.pipeline or '',
    )
    return self._call('cover', cover=spec)

  # ---- data -----------------------------------------------------------------------------

  def table(self, ref: Any, *, caption: str | None = None, max_rows: int | None = None) -> Safe:
    """Draw a ``table`` value.

    Parameters
    ----------
    ref : Any
        A table value (``data.x``) or its key.
    caption : str or None, default=None
        Overrides the value's caption.
    max_rows : int or None, default=None
        Overrides the value's row cap.

    Returns
    -------
    Safe
        The table.
    """
    value = self._value(ref, 'table', method='table')
    if not isinstance(value, TableValue):
      return EMPTY
    key = self._s.store.key_of(value) or ''
    spec = build_table(
      self._s.bundle,
      value,
      target=self._target,
      number=self._s.next_number('table'),
      caption=caption,
      max_rows=max_rows,
      report=self._s.report,
      key=key,
      overflow=self._overflow,
    )
    return self._call('table', spec=spec)

  def figure(self, ref: Any, *, caption: str | None = None, width: float | None = None) -> Safe:
    """Draw a ``figure`` value, choosing the best rendition for the format.

    HTML and Markdown use PNG, then SVG; LaTeX uses PDF, then PNG; SVG is never used in LaTeX.

    Parameters
    ----------
    ref : Any
        A figure value or its key.
    caption : str or None, default=None
        Overrides the value's caption.
    width : float or None, default=None
        Overrides the width fraction.

    Returns
    -------
    Safe
        The figure, or nothing (and ``E210``) when no rendition suits the format.
    """
    value = self._value(ref, 'figure', method='figure')
    if not isinstance(value, FigureValue):
      return EMPTY
    key = self._s.store.key_of(value) or ''
    chosen = self._pick(
      {r.format: r for r in value.renditions}, _FIGURE_ORDER[self._target], key, 'figure'
    )
    if chosen is None:
      return EMPTY
    fmt, rendition = chosen
    spec = FigureSpec(
      src=self._source(key, fmt, self._s.bundle.read_asset(rendition), 'figures'),
      alt=value.alt,
      caption=caption if caption is not None else (value.caption or ''),
      width=width if width is not None else value.width,
      number=self._s.next_number('figure'),
      key=key,
    )
    return self._call('figure', spec=spec)

  def image(self, ref: Any, *, caption: str | None = None, width: float | None = None) -> Safe:
    """Draw an ``image`` value (a logo, a photograph).

    Parameters
    ----------
    ref : Any
        An image value or its key.
    caption : str or None, default=None
        Overrides the value's caption.
    width : float or None, default=None
        Overrides the width fraction.

    Returns
    -------
    Safe
        The image, or nothing (and ``E210``) when its file type cannot be used in the format.
    """
    value = self._value(ref, 'image', method='image')
    if not isinstance(value, ImageValue):
      return EMPTY
    key = self._s.store.key_of(value) or ''
    suffix = value.asset.path.rpartition('.')[2].lower()
    chosen = self._pick({suffix: value.asset}, _IMAGE_ORDER[self._target], key, 'image')
    if chosen is None:
      return EMPTY
    spec = FigureSpec(
      src=self._source(key, suffix, self._s.bundle.read_asset(value.asset), 'images'),
      alt=value.alt or '',
      caption=caption if caption is not None else (value.caption or ''),
      width=width if width is not None else value.width,
      key=key,
    )
    return self._call('image', spec=spec)

  def equation(self, ref: Any) -> Safe:
    """Draw a ``math`` value.

    Parameters
    ----------
    ref : Any
        A math value or its key.

    Returns
    -------
    Safe
        The equation: an image in HTML, LaTeX math in TeX and Markdown.
    """
    value = self._value(ref, 'math', method='equation')
    if not isinstance(value, MathValue):
      return EMPTY
    spec = EquationSpec(
      body=self._math(value.latex, value.display),
      latex=value.latex,
      display=value.display,
      number=self._s.next_number('equation') if value.numbered else 0,
      caption=value.caption or '',
    )
    return self._call('equation', spec=spec)

  def math(self, latex: str) -> Safe:
    """Typeset an inline expression: ``$...$`` in TeX and Markdown, an image in HTML.

    Parameters
    ----------
    latex : str
        The expression without ``$`` delimiters.

    Returns
    -------
    Safe
        The inline math.
    """
    return Safe(self._math(latex, False, inline_delimiters=True))

  def metrics(self, ref: Any) -> Safe:
    """Draw a ``metrics`` value: a grid of headline numbers.

    Parameters
    ----------
    ref : Any
        A metrics value or its key.

    Returns
    -------
    Safe
        The grid.
    """
    value = self._value(ref, 'metrics', method='metrics')
    if not isinstance(value, MetricsValue):
      return EMPTY
    entries = [
      MetricSpec(item.label, self._inline(item.value), item.detail or '') for item in value.items
    ]
    return self._call('metrics', entries=entries)

  def status(self, ref: Any) -> Safe:
    """Draw a ``status`` value: the overall verdict banner.

    Parameters
    ----------
    ref : Any
        A status value or its key.

    Returns
    -------
    Safe
        The banner.
    """
    value = self._value(ref, 'status', method='status')
    if not isinstance(value, StatusValue):
      return EMPTY
    return self._call(
      'status', level=value.level, headline=value.headline, detail=value.detail or ''
    )

  def alert(self, ref: Any) -> Safe:
    """Draw an ``alert`` value: a one-line call-out.

    Parameters
    ----------
    ref : Any
        An alert value or its key.

    Returns
    -------
    Safe
        The call-out.
    """
    value = self._value(ref, 'alert', method='alert')
    if not isinstance(value, AlertValue):
      return EMPTY
    return self._call('alert', level=value.level, text=value.text)

  def flow(self, ref: Any) -> Safe:
    """Draw a ``flow`` value: a pipeline as numbered stages.

    Parameters
    ----------
    ref : Any
        A flow value or its key.

    Returns
    -------
    Safe
        The stages.
    """
    value = self._value(ref, 'flow', method='flow')
    if not isinstance(value, FlowValue):
      return EMPTY
    stages = [
      StageSpec(i, stage.label, tuple(stage.detail), stage.state)
      for i, stage in enumerate(value.stages, start=1)
    ]
    return self._call('flow', stages=stages)

  def metadata(self, ref: Any) -> Safe:
    """Draw a ``mapping`` value: labelled entries in a fixed order.

    Parameters
    ----------
    ref : Any
        A mapping value or its key.

    Returns
    -------
    Safe
        The description list.
    """
    value = self._value(ref, 'mapping', method='metadata')
    if not isinstance(value, MappingValue):
      return EMPTY
    entries = [(entry.key, self._inline(entry.value)) for entry in value.entries]
    return self._call('metadata', entries=entries)

  def bullets(self, ref: Any) -> Safe:
    """Draw a ``list`` value as a bullet or numbered list.

    Parameters
    ----------
    ref : Any
        A list value or its key.

    Returns
    -------
    Safe
        The list.
    """
    value = self._value(ref, 'list', method='bullets')
    if not isinstance(value, ListValue):
      return EMPTY
    items = [self._inline(item) for item in value.items]
    return self._call('bullets', items=items, ordered=value.ordered)

  def code(self, ref: Any) -> Safe:
    """Draw a ``code`` value: source code or preformatted text.

    Parameters
    ----------
    ref : Any
        A code value or its key.

    Returns
    -------
    Safe
        The code block.
    """
    value = self._value(ref, 'code', method='code')
    if not isinstance(value, CodeValue):
      return EMPTY
    source = value.source if value.source is not None else self._asset_text(value)
    source = source.rstrip('\n')
    longest = max((len(run) for run in re.findall(r'`+', source)), default=0)
    return self._call(
      'code',
      source=source,
      language=value.language or '',
      caption=value.caption or '',
      fence=Safe('`' * max(3, longest + 1)),
      verbatim=Safe(source.replace('\\end{verbatim}', '\\end {verbatim}')),
    )

  def text(self, ref: Any) -> Safe:
    """Draw a ``text`` value: Markdown, plain paragraphs or raw LaTeX.

    Parameters
    ----------
    ref : Any
        A text value or its key.

    Returns
    -------
    Safe
        The prose in the output format. Raw LaTeX (``format: latex``) is written as it is in TeX
        and replaced by the value's ``alt`` text elsewhere; without one, ``E209``.
    """
    value = self._value(ref, 'text', method='text')
    if not isinstance(value, TextValue):
      return EMPTY
    source = self._text_source(value)
    if value.format == 'latex':
      return self._raw_latex(value, source)
    if value.format == 'markdown':
      return self._prose(source)
    paragraphs = [' '.join(p.split()) for p in re.split(r'\n\s*\n', source.strip()) if p.strip()]
    return Safe(
      '\n'.join(
        self._call('paragraph', body=Safe(escape_text(p, self._target))) for p in paragraphs
      )
    )

  def number(self, ref: Any) -> Safe:
    """Typeset a ``number`` value inline, with its unit and uncertainty.

    Parameters
    ----------
    ref : Any
        A number value or its key.

    Returns
    -------
    Safe
        For example ``12,483,921 objects`` or ``0.9875 ± 0.0021``.
    """
    value = self._value(ref, 'number', method='number')
    if not isinstance(value, NumberValue):
      return EMPTY
    return format_number_value(value, self._target)

  def attachment(self, ref: Any) -> Safe:
    """Offer an ``attachment`` value as a link.

    Parameters
    ----------
    ref : Any
        An attachment value or its key.

    Returns
    -------
    Safe
        The link: a ``data:`` URI in HTML (up to 2 MiB), a file next to the document otherwise.
    """
    value = self._value(ref, 'attachment', method='attachment')
    if not isinstance(value, AttachmentValue):
      return EMPTY
    return self._call('attachment', link=self._link(value))

  def value(self, ref: Any, *, label: str | None = None) -> Safe:
    """Draw any value with the component for its kind.

    Parameters
    ----------
    ref : Any
        A value or its key.
    label : str or None, default=None
        For a number, bool or date: the label of the line (``Pairs: 3,061``).

    Returns
    -------
    Safe
        The drawn value.
    """
    value = self._value(ref, method='value')
    if value is None:
      return EMPTY
    handlers: dict[str, Callable[[Any], Safe]] = {
      'text': self.text,
      'list': self.bullets,
      'mapping': self.metadata,
      'table': self.table,
      'figure': self.figure,
      'image': self.image,
      'math': self.equation,
      'code': self.code,
      'metrics': self.metrics,
      'status': self.status,
      'alert': self.alert,
      'flow': self.flow,
      'attachment': self.attachment,
    }
    if value.kind in handlers:
      return handlers[value.kind](value)
    shown = self._inline(value)
    if label is None:
      return self._call('paragraph', body=Safe(shown))
    return self._call('fact', label=label, value=Safe(shown))

  def details(self, summary: str, caller: Callable[[], str]) -> Safe:
    """Wrap content in a collapsible block (a call block: ``{% call c.details('Title') %}``).

    Parameters
    ----------
    summary : str
        The visible title.
    caller : callable
        Supplied by Jinja; returns the content rendered between ``call`` and ``endcall``.

    Returns
    -------
    Safe
        The block.
    """
    return self._call('details', summary=summary, body=Safe(caller()))

  def note(self, caller: Callable[[], str]) -> Safe:
    """Write a muted remark (a call block: ``{% call c.note() %}``).

    Parameters
    ----------
    caller : callable
        Supplied by Jinja; returns the remark rendered between ``call`` and ``endcall``.

    Returns
    -------
    Safe
        The remark.
    """
    return self._call('note', body=Safe(caller()))

  def spacer(self, height: float = 8.0) -> Safe:
    """Leave vertical space.

    Parameters
    ----------
    height : float, default=8.0
        The height in points.

    Returns
    -------
    Safe
        The space.
    """
    return self._call('spacer', height=float(height))

  def page_break(self) -> Safe:
    """Start a new page (PDF, LaTeX); no effect in Markdown.

    Returns
    -------
    Safe
        The break.
    """
    return self._call('page_break')

  # ---- helpers --------------------------------------------------------------------------

  def _call(self, name: str, **kwargs: Any) -> Safe:
    """Draw with the layout macro called ``name``."""
    return Safe(str(self._s.macro(name)(**kwargs)))

  def _value(self, ref: Any, *kinds: str, method: str) -> Envelope | None:
    """Resolve a value or a key, check its kind and record a problem instead of raising."""
    if isinstance(ref, MissingValue):
      return None
    if isinstance(ref, str):
      ref = self._s.store.get(ref)
      if isinstance(ref, MissingValue):
        return None
    if isinstance(ref, DataNamespace):
      self._s.report(
        'E208',
        f'c.{method} was given {ref!r}, which holds several values, not one',
        found=repr(ref),
      )
      return None
    if not hasattr(ref, 'kind'):
      self._s.report('E208', f'c.{method} needs a bundle value, got {type(ref).__name__}')
      return None
    if kinds and ref.kind not in kinds:
      self._s.report(
        'E208',
        f'c.{method} draws a {" or ".join(kinds)} value, but this is a {ref.kind}',
        key=self._s.store.key_of(ref),
        expected=' or '.join(kinds),
        found=ref.kind,
      )
      return None
    value: Envelope = ref
    return value

  def _inline(self, value: Envelope) -> str:
    """Typeset a value for use inside a line, a list item or a metric tile."""
    target = self._target
    if isinstance(value, NumberValue):
      return format_number_value(value, target)
    if isinstance(value, BoolValue):
      return 'true' if value.value else 'false'
    if isinstance(value, DateValue):
      return value.value
    if isinstance(value, TextValue):
      source = self._text_source(value)
      if value.format == 'markdown':
        return self._prose(source, inline=True)
      if value.format == 'latex':
        return self._raw_latex(value, source)
      return Safe(escape_text(source, target))
    if isinstance(value, ListValue):
      return self.bullets(value)
    if isinstance(value, MappingValue):
      return self.metadata(value)
    self._s.report(
      'E208',
      f'a {value.kind} value cannot be shown inside a line, a list or a mapping',
      key=self._s.store.key_of(value),
      found=value.kind,
    )
    return ''

  def _prose(self, source: str, *, inline: bool = False) -> Safe:
    """Convert Markdown prose, recording its warnings."""
    return self._s.convert(source, inline=inline)

  def _raw_latex(self, value: TextValue, source: str) -> Safe:
    """Write raw LaTeX verbatim in TeX; elsewhere use the value's ``alt`` text."""
    if self._target == 'tex':
      return Safe(source)
    alt = (value.alt or {}).get(self._target)
    if alt is None:
      self._s.report(
        'E209',
        f'raw LaTeX text has no "{self._target}" replacement',
        key=self._s.store.key_of(value),
        hint='Add alt: {html: ..., md: ...} to the value.',
      )
      return EMPTY
    return Safe(alt)

  def _math(self, latex: str, display: bool, *, inline_delimiters: bool = False) -> str:
    """Typeset math for the target; HTML draws it, the others keep LaTeX."""
    if self._target == 'html':
      return self._s.math_html(latex, display)
    return f'${latex}$' if inline_delimiters else latex

  def _pick(
    self, available: dict[str, Any], order: tuple[str, ...], key: str, what: str
  ) -> tuple[str, Any] | None:
    """Choose the first usable file format, or record ``E210``."""
    for fmt in order:
      if fmt in available:
        return fmt, available[fmt]
    self._s.report(
      'E210',
      f'{what} {key!r} has no {" or ".join(order)} file, which the {self._target} format needs',
      key=key,
      expected=' or '.join(order),
      found=', '.join(sorted(available)),
    )
    return None

  def _source(self, key: str, suffix: str, data: bytes, folder: str) -> str:
    """Return the ``src`` of a picture: a ``data:`` URI in HTML, a file next to the document."""
    if self._target == 'html':
      media = _MEDIA.get(suffix, 'application/octet-stream')
      return f'data:{media};base64,{base64.b64encode(data).decode("ascii")}'
    path = f'{folder}/{key}.{suffix}'
    self._s.add_file(path, data)
    return path

  def _link(self, value: AttachmentValue) -> LinkSpec:
    """Build the link for an attachment, embedding small files in HTML."""
    data = self._s.bundle.read_asset(value.asset)
    media = value.media_type or ''
    size = fmt_bytes(len(data))
    if self._target == 'html':
      if len(data) <= EMBED_LIMIT_BYTES:
        encoded = base64.b64encode(data).decode('ascii')
        uri = f'data:{media or "application/octet-stream"};base64,{encoded}'
        return LinkSpec(value.filename, uri, media, value.description or '', size, True)
      return LinkSpec(value.filename, '', media, value.description or '', size, False)
    path = f'attachments/{value.filename}'
    self._s.add_file(path, data)
    return LinkSpec(value.filename, path, media, value.description or '', size, False)

  def _overflow(self, key: str) -> LinkSpec | None:
    """Return the link to the full table behind a cut one."""
    value = self._s.store.get(key)
    return self._link(value) if isinstance(value, AttachmentValue) else None

  def _asset_text(self, value: CodeValue) -> str:
    """Read the text of a code value stored as an asset."""
    assert value.asset is not None
    return self._s.bundle.read_asset(value.asset).decode('utf-8')

  def _text_source(self, value: TextValue) -> str:
    """Return the text of a text value, inline or from its asset."""
    if value.text is not None:
      return value.text
    assert value.asset is not None
    return self._s.bundle.read_asset(value.asset).decode('utf-8')
