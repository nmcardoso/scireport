"""Render a bundle: resolve, validate, render each format, assemble the result (ADR-0003/0004).

:func:`render_bundle` is the one entry point the CLI, the MCP server and Python code share. It
works in memory and writes nothing: the result holds every output file, so a failed render
never leaves half an output behind and two renders can be compared byte for byte. Use
:meth:`RenderResult.write` to put the files on disk.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jinja2
import matplotlib

from scireport._version import __version__
from scireport.bundle.reader import Bundle
from scireport.errors import Issue, TemplateError
from scireport.hashing import sha256_bytes
from scireport.logging_utils import get_logger, log_kv
from scireport.render.definition import FORMATS, Format
from scireport.render.layout import Layout
from scireport.render.markup import default_converter
from scireport.render.outputs import assemble
from scireport.render.registry import DEFAULT_LAYOUT, DEFAULT_TEMPLATE, load_layout, load_template
from scireport.render.session import RenderSession
from scireport.render.template import Template
from scireport.spec.manifest import manifest_to_json
from scireport.spec.walk import iter_assets
from scireport.validate import validate_bundle
from scireport.validate.report import ValidationReport, dedupe

log = get_logger(__name__)

MANIFEST_NAME = 'render-manifest.json'
"""Name of the file that records the inputs, versions and outputs of a render."""
DEFAULT_LATEX_ENGINE = 'lualatex'
_DEFERRED_FORMATS = {'pdf': 'S3', 'docx': 'S5', 'odt': 'S5', 'epub': 'S5'}


@dataclass(frozen=True)
class RenderResult:
  """The outcome of a render: all files in memory, with what was found on the way.

  Parameters
  ----------
  files : dict
      Path (relative to the output directory) to content, sorted. With several formats the first
      path segment is the format (``md/report.md``); with ``flat`` it is not.
  manifest : dict
      The content of ``render-manifest.json``.
  issues : tuple of Issue
      The warnings found while validating and rendering; a render with errors raises instead.
  formats : tuple of str
      The formats that were written.
  """

  files: dict[str, bytes]
  manifest: dict[str, Any]
  issues: tuple[Issue, ...]
  formats: tuple[Format, ...]

  def write(self, out_dir: Path | str) -> list[Path]:
    """Write every file under ``out_dir`` and return their paths.

    Parameters
    ----------
    out_dir : pathlib.Path or str
        The directory; created when missing. Files of an earlier render with the same name are
        replaced, others are left alone.

    Returns
    -------
    list of pathlib.Path
        The written files, in path order.
    """
    root = Path(out_dir)
    written = []
    for name, data in self.files.items():
      path = root / name
      path.parent.mkdir(parents=True, exist_ok=True)
      path.write_bytes(data)
      written.append(path)
    log_kv(log, 'render written', {'directory': root, 'files': len(written)})
    return written


@dataclass(frozen=True)
class _Plan:
  """Everything a render needs once the bundle's choices and the caller's are merged."""

  template: Template
  layout: Layout
  formats: list[Format]
  options: dict[str, Any]
  latex_engine: str
  markup_engine: str
  math_renderer: str
  flat: bool
  md_split: bool | None


def render_bundle(
  bundle: Bundle,
  *,
  template: str | Path | None = None,
  layout: str | Path | None = None,
  formats: list[Format] | None = None,
  options: Mapping[str, object] | None = None,
  markup_engine: str | None = None,
  math_renderer: str | None = None,
  latex_engine: str | None = None,
  md_split: bool | None = None,
  flat: bool = False,
  strict: bool = False,
) -> RenderResult:
  """Render a bundle to Markdown, HTML and/or a LaTeX project.

  What is not given falls back to the bundle's ``render`` block, then to the built-in defaults
  (``generic@1`` and the default layout).

  Parameters
  ----------
  bundle : Bundle
      The opened bundle.
  template : str or pathlib.Path or None, default=None
      ``name``, ``name@version`` or a template directory.
  layout : str or pathlib.Path or None, default=None
      ``name``, ``name@version`` or a layout directory.
  formats : list of {'md', 'html', 'tex'} or None, default=None
      Formats to write; the bundle's, or all that the template and layout support.
  options : mapping or None, default=None
      Layout options; they override the bundle's ``render.options`` and the layout defaults.
  markup_engine : str or None, default=None
      ``mistletoe`` (the only engine in this version).
  math_renderer : str or None, default=None
      ``mathtext`` (the only renderer in this version).
  latex_engine : str or None, default=None
      ``lualatex``, ``xelatex`` or ``pdflatex``: the engine the LaTeX project is meant for.
  md_split : bool or None, default=None
      Split Markdown into one file per chapter with an ``md_file``; by default it splits when
      the template or outline names such files.
  flat : bool, default=False
      Do not put each format in its own folder; only for a single format.
  strict : bool, default=False
      Treat warnings as errors.

  Returns
  -------
  RenderResult
      The files and the render manifest.

  Raises
  ------
  RenderError
      Carrying every problem when validation or rendering found errors (or warnings, if strict).
  TemplateError
      When the template or layout cannot be found or loaded, or an option is unsupported.
  """
  plan = _plan(
    bundle,
    template,
    layout,
    formats,
    options,
    markup_engine,
    math_renderer,
    latex_engine,
    md_split,
    flat,
  )
  static = validate_bundle(
    bundle, plan.template, plan.layout, plan.formats, options=plan.options, strict=strict
  )
  static.raise_for_errors()
  files, found = _render_all(bundle, plan)
  final = ValidationReport(tuple(dedupe([*static.issues, *found])), strict)
  final.raise_for_errors()
  manifest = _render_manifest(bundle, plan, files, final)
  files[MANIFEST_NAME] = (json.dumps(manifest, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
  for issue in final.issues:
    log.warning('%s', issue.format())
  return RenderResult(dict(sorted(files.items())), manifest, final.issues, tuple(plan.formats))


def check_bundle(
  bundle: Bundle,
  *,
  template: str | Path | None = None,
  layout: str | Path | None = None,
  formats: list[Format] | None = None,
  options: Mapping[str, object] | None = None,
  markup_engine: str | None = None,
  math_renderer: str | None = None,
  latex_engine: str | None = None,
  md_split: bool | None = None,
  strict: bool = False,
  render: bool = True,
) -> ValidationReport:
  """Validate a bundle, and render it in memory to find what only a render can show.

  The static checks come first (see :func:`~scireport.validate.validate_bundle`). If they pass
  and ``render`` is true, every format is rendered without writing anything, which adds the
  problems of keys computed at render time (``E106``), values nobody renders (``W401``), Markdown
  outside the supported subset (``W701``) and math that cannot be drawn (``W601``).

  Parameters
  ----------
  bundle : Bundle
      The opened bundle.
  template, layout, formats, options, markup_engine, math_renderer, latex_engine, md_split
      As for :func:`render_bundle`.
  strict : bool, default=False
      Treat warnings as errors.
  render : bool, default=True
      Also render in memory; False runs only the static checks.

  Returns
  -------
  ValidationReport
      Every problem found; it never raises for problems in the bundle.
  """
  plan = _plan(
    bundle,
    template,
    layout,
    formats,
    options,
    markup_engine,
    math_renderer,
    latex_engine,
    md_split,
    False,
  )
  static = validate_bundle(
    bundle, plan.template, plan.layout, plan.formats, options=plan.options, strict=strict
  )
  if not static.ok or not render:
    return static
  _, found = _render_all(bundle, plan)
  return ValidationReport(tuple(dedupe([*static.issues, *found])), strict)


def _plan(
  bundle: Bundle,
  template: str | Path | None,
  layout: str | Path | None,
  formats: list[Format] | None,
  options: Mapping[str, object] | None,
  markup_engine: str | None,
  math_renderer: str | None,
  latex_engine: str | None,
  md_split: bool | None,
  flat: bool,
) -> _Plan:
  """Merge the caller's choices, the bundle's ``render`` block and the defaults."""
  spec = bundle.manifest.render
  chosen_template = load_template(template or spec.template or DEFAULT_TEMPLATE)
  chosen_layout = load_layout(layout or spec.layout or DEFAULT_LAYOUT)
  engine = markup_engine or spec.markup_engine or 'mistletoe'
  renderer = math_renderer or spec.math_renderer or 'mathtext'
  _check_supported(engine, renderer)
  wanted = _formats(formats, spec.formats, chosen_template, chosen_layout)
  if flat and len(wanted) != 1:
    raise TemplateError('flat output needs exactly one format', code='E801')
  return _Plan(
    template=chosen_template,
    layout=chosen_layout,
    formats=wanted,
    options={**spec.options, **dict(options or {})},
    latex_engine=latex_engine or spec.latex_engine or DEFAULT_LATEX_ENGINE,
    markup_engine=engine,
    math_renderer=renderer,
    flat=flat,
    md_split=md_split,
  )


def _render_all(bundle: Bundle, plan: _Plan) -> tuple[dict[str, bytes], list[Issue]]:
  """Render every format in memory; return the files and everything found on the way."""
  resolved = plan.layout.resolve_options(plan.options)
  files: dict[str, bytes] = {}
  issues: list[Issue] = []
  for fmt in plan.formats:
    rendered, found = _render_format(
      bundle, plan.template, plan.layout, fmt, resolved, plan.latex_engine, plan.md_split
    )
    issues.extend(found)
    files.update(
      {(name if plan.flat else f'{fmt}/{name}'): data for name, data in rendered.items()}
    )
  return files, issues


def _render_format(
  bundle: Bundle,
  template: Template,
  layout: Layout,
  fmt: Format,
  options: dict[str, Any],
  latex_engine: str,
  md_split: bool | None,
) -> tuple[dict[str, bytes], list[Issue]]:
  """Render one format; Markdown is rendered a second time when it turns out to be split."""
  split = bool(md_split) if fmt == 'md' else False

  def run(with_split: bool) -> tuple[RenderSession, str, str]:
    session = RenderSession(
      bundle,
      template,
      layout,
      fmt,
      options=options,
      converter=default_converter(),
      md_split=with_split,
      latex_engine=latex_engine,
    )
    body, document = session.render()
    return session, body, document

  session, body, document = run(split)
  if fmt == 'md' and md_split is None and not split and session.wants_split:
    log.debug('the template names Markdown files: rendering again as a split document')
    session, body, document = run(True)
  if any(issue.severity == 'error' for issue in session.issues):
    return {}, session.issues
  return assemble(session, body, document), session.issues


def _formats(
  requested: list[Format] | None,
  from_bundle: Sequence[str],
  template: Template,
  layout: Layout,
) -> list[Format]:
  """Choose the formats: the caller's, the bundle's, or everything both sides support."""
  if requested:
    return [fmt for fmt in FORMATS if fmt in requested]
  declared = [fmt for fmt in FORMATS if fmt in from_bundle]
  for name in from_bundle:
    if name not in FORMATS:
      log.info(
        'format %r is not written by this step (%s); skipping it',
        name,
        _DEFERRED_FORMATS.get(name, 'later'),
      )
  if declared:
    return declared
  return [
    fmt
    for fmt in FORMATS
    if fmt in template.definition.formats and fmt in layout.definition.formats
  ]


def _check_supported(engine: str, renderer: str) -> None:
  """Refuse the markup engine and math renderer that arrive in later phases."""
  if engine != 'mistletoe':
    raise TemplateError(
      f'markup engine {engine!r} is not available in this version',
      code='E805',
      hint='Only mistletoe is available; pandoc arrives in phase S5.',
    )
  if renderer != 'mathtext':
    raise TemplateError(
      f'math renderer {renderer!r} is not available in this version',
      code='E805',
      hint='Only mathtext is available; usetex arrives in phase S3.',
    )


def _render_manifest(
  bundle: Bundle, plan: _Plan, files: dict[str, bytes], report: ValidationReport
) -> dict[str, Any]:
  """Build the content of ``render-manifest.json``: no clock, no paths, only hashes and versions."""
  import mistletoe

  return {
    'scireport': __version__,
    'spec': bundle.manifest.scireport,
    'input': {
      'manifest_sha256': sha256_bytes(manifest_to_json(bundle.manifest).encode('utf-8')),
      'assets': {
        ref.path: ref.sha256
        for _, ref in sorted(iter_assets(bundle.manifest), key=lambda p: p[1].path)
      },
    },
    'template': {'ref': plan.template.ref, 'sha256': plan.template.sha256},
    'layout': {'ref': plan.layout.ref, 'sha256': plan.layout.sha256},
    'options': plan.layout.resolve_options(plan.options),
    'formats': list(plan.formats),
    'engines': {
      'markup': plan.markup_engine,
      'mistletoe': mistletoe.__version__,
      'math': plan.math_renderer,
      'matplotlib': matplotlib.__version__,
      'jinja2': jinja2.__version__,
      'latex': plan.latex_engine,
    },
    'outputs': {
      name: {'sha256': sha256_bytes(data), 'bytes': len(data)}
      for name, data in sorted(files.items())
    },
    'warnings': [issue.to_dict() for issue in report.issues if issue.severity == 'warning'],
  }
