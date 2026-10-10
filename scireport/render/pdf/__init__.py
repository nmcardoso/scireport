"""The PDF engines (ADR-0004): WeasyPrint prints the HTML output, LaTeX compiles the TeX project.

PDF is not rendered from the template: it is made from another output. The ``weasyprint`` engine
prints the self-contained HTML (CSS Paged Media, so it reproduces the MOSAICS look) and the
``latex`` engine runs ``latexmk`` on the LaTeX project. Both are optional dependencies, imported
or started only when a PDF is asked for; a missing system dependency (pango, TeX Live) is
:class:`~scireport.errors.MissingDependencyError` with an install hint and exit code 3.
"""

from __future__ import annotations

from typing import Literal

PdfEngine = Literal['weasyprint', 'latex']
PDF_ENGINES: tuple[PdfEngine, ...] = ('weasyprint', 'latex')
"""The PDF engines, WeasyPrint first (the default)."""
LatexEngine = Literal['lualatex', 'xelatex', 'pdflatex']
LATEX_ENGINES: tuple[LatexEngine, ...] = ('lualatex', 'xelatex', 'pdflatex')
"""The TeX engines ``latexmk`` can run, LuaLaTeX first (the default)."""
PDF_NAME = 'report.pdf'
"""Name of the PDF inside its output folder."""
EPOCH_DEFAULT = 315532800
"""1980-01-01T00:00:00Z: the ``SOURCE_DATE_EPOCH`` used when nothing better is known."""
