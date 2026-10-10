"""Render every example with every layout to every output: the body of ``make examples``.

For each example and layout it writes, under ``examples/_out/<example>/<layout>/``:

* ``md/``, ``html/`` and ``tex/``: the three text outputs (``tex`` is a project that ``latexmk``
  compiles);
* ``pdf-weasyprint/``: a PDF printed from the HTML;
* ``pdf-lualatex/``, ``pdf-xelatex/`` and ``pdf-pdflatex/``: the PDF compiled from the LaTeX
  project by each TeX engine.

The bundles are written to ``_out/<example>/<example>.scireport.zip`` first, so that what is
rendered is exactly what a user would ship. Nothing here is committed: ``_out/`` is ignored by git
and uploaded as an artifact by the ``examples`` CI job.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import typer

from scireport import Report, open_bundle
from scireport.errors import ScireportError
from scireport.logging_utils import get_logger, log_section, setup_logging
from scireport.render import render_bundle
from scireport.render.pdf import LATEX_ENGINES

try:  # run as a script (python examples/render_all.py) or as a module
  from examples import dataset_report, metrics_dashboard, text_report
except ImportError:  # pragma: no cover - script mode
  import dataset_report  # type: ignore[no-redef]
  import metrics_dashboard  # type: ignore[no-redef]
  import text_report  # type: ignore[no-redef]

log = get_logger(__name__)

HERE = Path(__file__).resolve().parent
EXAMPLES: dict[str, Callable[[str], Report]] = {
  'dataset-report': dataset_report.build,
  'metrics-dashboard': metrics_dashboard.build,
  'text-report': text_report.build,
}
TEMPLATES: dict[str, Path] = {'metrics-dashboard': metrics_dashboard.TEMPLATE}
"""Examples that bring their own template; the others use the generic one from the outline."""
LAYOUTS = ('default', 'modern')
app = typer.Typer(add_completion=False, help=__doc__)


@app.command()
def main(
  out: Annotated[Path, typer.Option('--out', '-o', help='Output directory.')] = HERE / '_out',
  layout: Annotated[
    list[str] | None, typer.Option('--layout', '-l', help='Layout name (repeat); default: all.')
  ] = None,
  example: Annotated[
    list[str] | None, typer.Option('--example', '-e', help='Example name (repeat); default: all.')
  ] = None,
  pdf: Annotated[
    bool, typer.Option('--pdf/--no-pdf', help='Also make the PDFs (needs pango and TeX Live).')
  ] = True,
  log_level: Annotated[str, typer.Option('--log-level')] = 'INFO',
) -> None:
  """Build the example bundles and render each with each layout."""
  setup_logging(level=log_level)
  layouts = layout or list(LAYOUTS)
  names = example or list(EXAMPLES)
  unknown = [name for name in names if name not in EXAMPLES]
  if unknown:
    raise typer.BadParameter(
      f'unknown example(s): {", ".join(unknown)}; have {", ".join(EXAMPLES)}'
    )
  try:
    for name in names:
      for lay in layouts:
        with log_section(log, f'{name} with {lay}'):
          render_example(name, lay, out, pdf=pdf)
  except ScireportError as exc:
    for issue in exc.issues:
      log.error('%s', issue.format())
    raise typer.Exit(exc.exit_code) from exc


def render_example(name: str, layout: str, out: Path, *, pdf: bool = True) -> list[Path]:
  """Render one example with one layout to every output.

  Parameters
  ----------
  name : str
      Key of :data:`EXAMPLES`.
  layout : str
      Layout name (``default`` or ``modern``).
  out : pathlib.Path
      The output directory; the example gets a folder in it.
  pdf : bool, default=True
      Also make the four PDFs.

  Returns
  -------
  list of pathlib.Path
      Every file written.
  """
  root = out / name
  bundle_path = root / f'{name}.scireport.zip'
  EXAMPLES[name](layout).write(bundle_path, overwrite=True)
  written: list[Path] = []
  template = TEMPLATES.get(name)
  with open_bundle(bundle_path) as bundle:
    target = root / layout
    written += render_bundle(bundle, template=template, formats=['md', 'html', 'tex']).write(target)
    if pdf:
      written += render_bundle(
        bundle, template=template, formats=['pdf'], pdf_engine='weasyprint', flat=True
      ).write(target / 'pdf-weasyprint')
      for engine in LATEX_ENGINES:
        written += render_bundle(
          bundle,
          template=template,
          formats=['pdf'],
          pdf_engine='latex',
          latex_engine=engine,
          flat=True,
        ).write(target / f'pdf-{engine}')
  log.info('%s with %s: %d files', name, layout, len(written))
  return written


if __name__ == '__main__':
  app()
