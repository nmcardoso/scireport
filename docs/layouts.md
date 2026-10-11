# Built-in layouts

A layout is the look of a report (ADR-0003). Three ship with scireport; each is **frozen per version**
(ADR-0008): a visual change is a new version directory, never an edit.

| Layout | For | Look |
|---|---|---|
| `default@1` | reports that should look like the MOSAICS reports | a navy cover with a grid and a circle, a chapter opener page with a large title and an index (`01 / 07`), a table of contents with page numbers, a running header and footer, a serif text over sans-serif headings and tables, boxed status and alert components with a solid coloured left border |
| `modern@1` | journal-style reports with many tables and figures | after the TUPAN publication plan: a steel-blue cover band with a gold stripe and the abstract in a titled box, numbered blue headings (`1`, `1.1`), justified Palatino-like text, a table of contents with dot leaders, booktabs tables with the caption above, and boxes with a coloured title bar |
| `minimal@1` | tests, language models and plain reading | no design: Markdown, plain HTML and a plain LaTeX article |

`default@1` and `modern@1` support Markdown, HTML, LaTeX and both PDF engines. Both ship their fonts as
subsets in `scireport/styles/fonts/`:

| Layout | Text | Headings, tables, labels | Code |
|---|---|---|---|
| `default@1` | **IBM Plex Serif** (OFL, `OFL.txt`) | **Inter** (OFL) | **IBM Plex Mono** (OFL) |
| `modern@1` | **TeX Gyre Pagella** (a Palatino clone; GUST Font Licence, `GFL.txt`) | **TeX Gyre Heros** (a Helvetica clone; GFL) | **TeX Gyre Cursor** (a Courier clone; GFL) |

The HTML inlines the fonts as `data:` URIs, so a report is one file; the LaTeX project gets a `fonts/`
folder that `fontspec` loads, with the licence files beside it. pdfLaTeX loads the TeX Gyre families of
`modern@1` from TeX Live (`tgpagella`, `tgheros`, `tgcursor`) and so needs no fallback there.

## Options

Options are set in the data file (`render.options`), with `-O name=value` or in Python; a value outside
the choices is `E806`. Generated from the layouts' `layout.yaml`.

<!-- generated:layouts -->
### `default@1`

Default (MOSAICS look). Navy cover, chapter openers, a table of contents with page numbers, a running header and footer. Inter, IBM Plex Serif and IBM Plex Mono.

Formats: md, html, tex. PDF engines: weasyprint, latex.

| Option | Type | Default | Choices | Meaning |
|---|---|---|---|---|
| `toc` | bool | `True` |  | Write a table of contents. |
| `cover` | bool | `True` |  | Start with the navy cover page (otherwise a plain title block). |
| `paper` | str | `a4` | a4\|letter | Paper size of the PDF and of the LaTeX project. |
| `chapter_breaks` | bool | `True` |  | Start every chapter on a new page, below an opener band. |
| `numbered_captions` | bool | `True` |  | Prefix captions with "Table N." and "Figure N.". |
| `header` | bool | `True` |  | Print the running header and footer on the pages of a PDF. |

### `minimal@1`

Minimal. Plain reference layout for Markdown, self-contained HTML and a LaTeX project.

Formats: md, html, tex. PDF engines: none.

| Option | Type | Default | Choices | Meaning |
|---|---|---|---|---|
| `toc` | bool | `True` |  | Write a table of contents. |
| `cover` | bool | `True` |  | Write the title block (subtitle, authors, date, version) under the title. |
| `accent` | str | `#1f4e79` |  | Accent colour as #rrggbb. |
| `paper` | str | `a4` | a4\|letter | Paper size of the LaTeX project. |
| `numbered_captions` | bool | `True` |  | Prefix captions with "Table N." and "Figure N.". |

### `modern@1`

Modern (Publication). A journal-style report. Steel-blue cover band with a gold stripe, numbered blue headings, justified Palatino-like text, booktabs tables and boxes with a coloured title bar. TeX Gyre Pagella, Heros and Cursor.

Formats: md, html, tex. PDF engines: weasyprint, latex.

| Option | Type | Default | Choices | Meaning |
|---|---|---|---|---|
| `toc` | bool | `True` |  | Write a table of contents. |
| `cover` | bool | `True` |  | Start with the cover page (otherwise a plain title block). |
| `paper` | str | `a4` | a4\|letter | Paper size of the PDF and of the LaTeX project. |
| `chapter_breaks` | bool | `False` |  | Start every chapter on a new page (by default chapters follow each other). |
| `numbered_captions` | bool | `True` |  | Prefix captions with "Table N." and "Figure N.". |
| `header` | bool | `True` |  | Print the running header and footer on the pages of a PDF. |
<!-- /generated -->

## Design rules both layouts keep

- **Grey-scale safe.** A status level or an alert is never told by colour alone: its headline or label is
  printed as a word (`COMPLETED WITH WARNINGS`, `ERROR`) and a flow stage carries its state word. Table rows
  with a verdict carry a tint and a coloured left strip.
- **WeasyPrint workarounds** from MOSAICS: no flex container inside another one, a named cover page
  (`@page cover`), no `break-inside: avoid` on tables (a table taller than a page would never fit).
- **One palette file** (`palette.yaml` in the layout) is the source of truth for the stylesheet, the
  LaTeX colours and the matplotlib style; a test fails when they drift (see [Matplotlib style guide](styles.md)).

## Known limits

- The Inter and IBM Plex Mono subsets have no Greek letters, `≥ ≤ ≈ √` or the bullet. LaTeX writes them as
  math macros; in HTML they fall back to the next family of the stack (DejaVu Sans, Arial). The IBM Plex
  Serif and TeX Gyre subsets have them.
- pdfLaTeX cannot load the OpenType fonts of `default@1`: it uses Latin Modern and warns (`W901`).
- In `default@1`, text set in `--gray-500` (the running header, footer and some labels) is 3.9:1 on white,
  below WCAG AA for small text.
- The LaTeX look follows the HTML look, not pixel for pixel.
- The body text of both layouts spans the full width between the page margins (no line-length cap): long
  paragraphs make long lines. Use the `paper` option or a narrower layout when that matters.
