# Outputs

`scireport render` writes each format into its own folder of the output directory, next to
`render-manifest.json`; `--flat` writes a single format straight into the directory. Nothing is written when
validation or rendering finds an error.

| Format | Files |
|---|---|
| `md` | `index.md` (or `report.md` when not split), one file per chapter that names an `md_file`, `figures/`, `images/`, `attachments/` |
| `html` | `report.html`, self-contained: CSS inlined, figures, images and math embedded as data URIs (math as SVG) |
| `tex` | `report.tex`, the layout's `.sty`, `latexmkrc`, `figures/` (PDF preferred over PNG, SVG never), `images/`, `attachments/` |

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

## Not in this version

PDF (WeasyPrint and LaTeX engines) arrives in phase S3, DOCX, ODT and EPUB in S5. Asking for them is `E805`.
