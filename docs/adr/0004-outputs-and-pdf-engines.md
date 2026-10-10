# ADR-0004: Outputs and PDF engines

- Status: Accepted (HG-S0, 2026-10-09)
- Date: 2026-10-09

## Decision

| Format | Output |
|---|---|
| `md` | Single file or split, with `figures/*.png`; images carry alt text; math as `$...$`; a generated-file header. |
| `html` | One self-contained file: inlined CSS, fonts and images. |
| `tex` | A standalone, compilable LaTeX project (ADR-0010). |
| `pdf` | Two engines (below). |
| `docx`, `odt`, `epub` | Optional, through pandoc (`scireport[pandoc]`, ADR-0011). |

- **`weasyprint`** (default; extra `scireport[pdf]`) reproduces MOSAICS and keeps its WeasyPrint workarounds: no
  nested flex, a named cover page, no `break-inside` on tables.
- **`latex`**: `latexmk` with `lualatex` by default (`xelatex` and `pdflatex` selectable through
  `render.latex_engine`), fontspec loading the vendored fonts, `SOURCE_DATE_EPOCH`, log parsing.
- Both layouts support both engines.
- Math: mathtext SVG for HTML/WeasyPrint (port of MOSAICS `R/math.py`), native in LaTeX.
- Every render writes `render-manifest.json` (input and output hashes, versions).
- Optional dependencies are imported lazily. A missing system dependency exits with code 3 and an install hint.

## Consequences

md, html and tex are byte-deterministic; PDF determinism is verified per engine and recorded (best-effort).
WeasyPrint needs the pango system libraries; CI installs them on each OS.

## Notes from implementation (phase S3)

- PDF is made from another output, never from the template: `weasyprint` prints the HTML and `latex` compiles the LaTeX
  project in a scratch directory. `-f pdf` is never a default; `render.pdf_engine` and `render.latex_engine` choose the
  engines, and a layout lists the engines it supports (`E903`).
- Exit code 3 is `E901`: pango or TeX Live (or one TeX package) is missing, with an install hint for the platform.
- Reproducibility inputs: `SOURCE_DATE_EPOCH` (environment, else `meta.date`, else 1980-01-01), `FORCE_SOURCE_DATE=1`,
  and a trailer id derived from `report.tex` for LuaLaTeX. See `DECISIONS.md` for what was found while checking.
