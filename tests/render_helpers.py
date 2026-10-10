"""Helpers that render a body template against a bundle, for the component and pipeline tests."""

from __future__ import annotations

import os
import re
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from render_fixtures import write_template

from scireport import Bundle
from scireport._version import __version__
from scireport.errors import Issue, RenderError
from scireport.render import render_bundle
from scireport.render.pipeline import MANIFEST_NAME, check_bundle

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


UPDATE_GOLDEN = os.environ.get('SCIREPORT_UPDATE_GOLDEN') == '1'


def check_golden(files: Mapping[str, bytes], directory: Path) -> None:
  """Compare rendered files with the committed copies; rewrite them when asked.

  Set ``SCIREPORT_UPDATE_GOLDEN=1`` to rewrite the directory. Review the diff before committing:
  a changed golden file is a changed output, which needs a new layout or template version
  (ADR-0008).

  Parameters
  ----------
  files : mapping
      Relative path to content, as in :attr:`~scireport.render.RenderResult.files`.
  directory : pathlib.Path
      The folder that holds the expected files.
  """
  if UPDATE_GOLDEN:
    if directory.exists():
      shutil.rmtree(directory)
    for name, data in files.items():
      target = directory / name
      target.parent.mkdir(parents=True, exist_ok=True)
      target.write_bytes(data)
    return
  expected = {
    path.relative_to(directory).as_posix(): path.read_bytes()
    for path in sorted(directory.rglob('*'))
    if path.is_file()
  }
  assert sorted(files) == sorted(expected), 'the set of output files changed'
  changed = [name for name, data in files.items() if data != expected[name]]
  assert changed == [], f'output differs from the golden files: {changed}'


TEXT_SUFFIXES = ('.md', '.html', '.tex', '.sty', 'latexmkrc')
SVG_PAYLOAD = re.compile(rb'data:image/svg\+xml;base64,[A-Za-z0-9+/=]+')


def normalised(files: Mapping[str, bytes]) -> dict[str, bytes]:
  """Hide what depends on the environment: the manifest, the package version and drawn math.

  The manifest records the versions of Jinja, mistletoe and matplotlib, so a byte comparison would
  fail on every dependency update; ``test_pipeline`` checks its content instead. Math in HTML is an
  SVG drawn by matplotlib, whose bytes depend on its version and its fonts; ``test_math`` checks
  the drawing and the render tests check that two renders agree byte for byte.

  Parameters
  ----------
  files : mapping
      Relative path to content, as in :attr:`~scireport.render.RenderResult.files`.

  Returns
  -------
  dict
      The files without ``render-manifest.json``, with the version replaced by ``<version>`` and
      every SVG data URI of an HTML file replaced by ``<math-svg>``.
  """
  version = __version__.encode()
  out = {}
  for name, data in files.items():
    if name == MANIFEST_NAME:
      continue
    if name.endswith(TEXT_SUFFIXES):
      data = data.replace(version, b'<version>')
    if name.endswith('.html'):
      data = SVG_PAYLOAD.sub(b'data:image/svg+xml;base64,<math-svg>', data)
    out[name] = data
  return out
