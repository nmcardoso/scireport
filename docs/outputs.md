# Outputs

`scireport render` writes each format into its own folder of the output directory, next to
`render-manifest.json`; `--flat` writes a single format straight into the directory. Nothing is written when
validation or rendering finds an error.

| Format | Files |
|---|---|
| `md` | `index.md` (or `report.md` when not split), one file per chapter that names an `md_file`, `figures/`, `images/`, `attachments/` |
| `html` | `report.html`, self-contained: CSS inlined, figures, images and math embedded as data URIs (math as SVG) |
| `tex` | `report.tex`, the layout's `.sty`, `latexmkrc`, `fonts/` (the vendored fonts the layout lists, with `OFL.txt`), `figures/` (PDF preferred over PNG, SVG never), `images/`, `attachments/` |
| `pdf` | `report.pdf`, made from the HTML (`--pdf-engine weasyprint`, the default) or from the LaTeX project (`--pdf-engine latex`); see below |

- **Markdown** starts every file with a generated-file notice (template, layout, manifest hash). Alt text comes
  from the data file. Math is `$...$` and `$$...$$`. A document is split when the outline names `md_file`
  chapters (`--md-split` / `--no-md-split` overrides).
- **LaTeX** is a standalone project: `latexmk report.tex` compiles it with no scireport installed. The
  `latexmkrc` selects the engine (`--latex-engine`, default `lualatex`; `pdflatex` and `xelatex` also work).
  Tables use `booktabs`, long ones `longtable`; quantities use `\ensuremath` macros, so no `siunitx` is needed
  by `minimal@1`. The packages a layout needs are listed in its `.sty`.
- **Engines and Unicode**: text is escaped and Greek letters and common symbols are mapped to macros, so
  all three engines typeset it. pdfLaTeX with Latin Modern cannot draw other scripts (for example CJK), and
  code blocks are literal, so any non-ASCII character in a code block also needs XeLaTeX or LuaLaTeX, the
  default.
- **Determinism**: the same bundle, template, layout and versions give byte-identical `.md`, `.html` and `.tex`.
  No clock is read and no absolute path is written.

## `render-manifest.json`

Records what produced the output so that it can be reproduced and audited: the scireport and spec versions,
the sha256 of the manifest and of every asset read, the resolved template and layout (reference and content
hash), the layout options, the formats, the engines and library versions (markup, math, matplotlib, jinja2,
LaTeX), every output file with sha256 and size, and the warnings. It records dependency versions, so it is not
part of the byte-for-byte comparisons in the golden tests.

## PDF

`scireport render -f pdf` makes a PDF; the format is never a default, because it needs system libraries.

| Engine | How | Needs | Choose it when |
|---|---|---|---|
| `weasyprint` (default) | prints the self-contained HTML with CSS Paged Media (running header and footer, a table of contents with page numbers through `target-counter`, a named cover page) | `pip install "scireport[pdf]"` and the pango libraries | you want the look of the HTML; it reproduces the MOSAICS reports |
| `latex` | writes the LaTeX project to a scratch directory and runs `latexmk` there; the TeX engine is `--latex-engine lualatex` (default), `xelatex` or `pdflatex` | TeX Live with the packages in `.github/tl_packages` | the PDF is part of a LaTeX workflow, or you need real LaTeX math |

`render.pdf_engine` and `render.latex_engine` of the data file set the same choices; the command line wins.
A PDF alone goes to `pdf/report.pdf` (or `report.pdf` with `--flat`); next to other formats it goes in
the `pdf/` folder. Both designed layouts support both engines; `minimal@1` has no PDF (`E903`).

**Missing system dependencies exit with code 3** and say what to install: pango (Linux: `apt install
libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0`; macOS: `brew install pango`; Windows: MSYS2, see
below) or TeX Live (a missing TeX package is named: `tcolorbox.sty not found`). A failed compile is
`E902` with the `file:line` of each error in the LaTeX log. Warnings of a build that still made a PDF
are `W901` (pdfLaTeX had to fall back to TeX fonts, because it cannot load OpenType fonts) and `W902`
(the font has no glyph for some character; the vendored subsets have no Greek letters or `≥ ≤ ≈ √`, which
the engine writes as math macros in LaTeX and which fall back to another font in HTML).

**Reproducibility.** Dates and file ids are fixed: `SOURCE_DATE_EPOCH` is taken from the environment,
else from `meta.date`, else 1980-01-01, and never from the clock. WeasyPrint is run with that variable set
(fontTools stamps the fonts it embeds) and the LaTeX build uses `FORCE_SOURCE_DATE=1`; LuaLaTeX also gets
a trailer id derived from the main file. On one machine and one set of library versions every engine gives
the same bytes for the same inputs (checked by `tests/integration/test_pdf.py`). The bytes still differ
between pango, HarfBuzz or TeX Live versions, so a PDF is best-effort deterministic: the text of the PDF,
reduced to its letters, is what the compat corpus freezes.

**Math.** Equations are LaTeX in the LaTeX project and in Markdown. For HTML (and so for WeasyPrint) they
are drawn as SVG paths by matplotlib: `render.math_renderer: mathtext` (default, pure Python, a subset of
LaTeX math) or `usetex` (a real LaTeX run, full LaTeX math, needs `latex`). A construct the renderer
cannot draw is shown as source with a warning (`W601` mathtext, `W602` usetex); `--strict` makes it an error.

**Windows.** WeasyPrint needs the pango libraries (GTK for Windows or MSYS2). See `DECISIONS.md` for the
status of the Windows CI jobs.
