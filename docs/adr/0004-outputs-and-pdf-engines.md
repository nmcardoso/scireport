# ADR-0004: Outputs and PDF engines

- Status: Proposed (approval at HG-S0)
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
