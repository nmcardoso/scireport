"""Helpers that render a body template against a bundle, for the component and pipeline tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from render_fixtures import write_template

from scireport import Bundle
from scireport.errors import Issue, RenderError
from scireport.render import render_bundle
from scireport.render.pipeline import check_bundle

Format = Literal['md', 'html', 'tex']
MAIN = {'md': 'report.md', 'html': 'report.html', 'tex': 'report.tex'}


def render_body(
  bundle: Bundle, body: str, fmt: Format, tmp_path: Path, *, extra: str = '', **options: Any
) -> str:
  """Render a one-off template ``body`` and return the text of the main output file.

  Parameters
  ----------
  bundle : Bundle
      The bundle to render.
  body : str
      The content of ``report.j2`` (neutral Jinja).
  fmt : {'md', 'html', 'tex'}
      The format to write.
  tmp_path : pathlib.Path
      A scratch directory for the template.
  extra : str
      More lines for ``template.yaml``.
  **options : Any
      Forwarded to :func:`~scireport.render.render_bundle`.

  Returns
  -------
  str
      The main file of the format, decoded.
  """
  template = write_template(tmp_path / 'template', body=body, extra=extra)
  result = render_bundle(
    bundle, template=template, layout='minimal@1', formats=[fmt], flat=True, **options
  )
  return result.files[MAIN[fmt]].decode('utf-8')


def render_issues(
  bundle: Bundle, body: str, fmt: Format, tmp_path: Path, *, strict: bool = False
) -> list[Issue]:
  """Render a body template and return the issues (errors are returned, not raised)."""
  template = write_template(tmp_path / 'template', body=body)
  try:
    result = render_bundle(
      bundle,
      template=template,
      layout='minimal@1',
      formats=[fmt],
      flat=True,
      strict=strict,
    )
  except RenderError as exc:
    return exc.issues
  return list(result.issues)


def report_of(bundle: Bundle, body: str, fmt: Format, tmp_path: Path) -> list[str]:
  """Return the codes found by :func:`~scireport.render.pipeline.check_bundle` for a body."""
  template = write_template(tmp_path / 'template', body=body)
  report = check_bundle(bundle, template=template, layout='minimal@1', formats=[fmt])
  return [issue.code for issue in report.issues]
