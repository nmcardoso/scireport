# Built-in layouts

A layout is the look of a report (ADR-0003). Three ship with scireport; each is **frozen per version**
(ADR-0008): a visual change is a new version directory, never an edit.

| Layout | For | Look |
|---|---|---|
| `default@1` | reports that should look like the MOSAICS reports | a navy cover with a grid and a circle, a chapter opener with a large title and an index (`01 / 07`), a table of contents with page numbers, a running header and footer, boxed status and alert components whose left border style also encodes the level |
| `modern@1` | data reports with many tables and figures | a white page with a vermilion cover band and a black disc, giant chapter numerals, heavy rules and rule-only (booktabs-like) tables; one accent colour that means "needs attention" |
| `minimal@1` | tests, language models and plain reading | no design: Markdown, plain HTML and a plain LaTeX article |

`default@1` and `modern@1` support Markdown, HTML, LaTeX and both PDF engines. Both use the vendored
**Inter** and **IBM Plex Mono** (SIL Open Font License; subsets in `scireport/styles/fonts/`, with
`OFL.txt`). The HTML inlines the fonts as `data:` URIs, so a report is one file; the LaTeX project gets a
`fonts/` folder that `fontspec` loads.

## Options

Options are set in the data file (`render.options`), with `-O name=value` or in Python; a value outside
the choices is `E806`. Generated from the layouts' `layout.yaml`.

<!-- generated:layouts -->
### `default@1`

Default (MOSAICS look). Navy cover, chapter openers, a table of contents with page numbers, a running header and footer. Inter and IBM Plex Mono.

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

Modern (Signal). A white page with a vermilion cover band, giant chapter numerals, heavy rules and rule-only tables. Inter and IBM Plex Mono.

Formats: md, html, tex. PDF engines: weasyprint, latex.

| Option | Type | Default | Choices | Meaning |
|---|---|---|---|---|
| `toc` | bool | `True` |  | Write a table of contents. |
| `cover` | bool | `True` |  | Start with the cover page (otherwise a plain title block). |
| `paper` | str | `a4` | a4\|letter | Paper size of the PDF and of the LaTeX project. |
| `chapter_breaks` | bool | `True` |  | Start every chapter on a new page. |
| `numbered_captions` | bool | `True` |  | Prefix captions with "Table N." and "Figure N.". |
| `header` | bool | `True` |  | Print the running header and footer on the pages of a PDF. |
<!-- /generated -->

## Design rules both layouts keep

- **Grey-scale safe.** A status level or a verdict is never told by colour alone: the left or top rule has
  its own style (solid, dashed, dotted, double) and the table rows carry a tint and a border style.
- **WeasyPrint workarounds** from MOSAICS: no flex container inside another one, a named cover page
  (`@page cover`), no `break-inside: avoid` on tables (a table taller than a page would never fit).
- **One palette file** (`palette.yaml` in the layout) is the source of truth for the stylesheet, the
  LaTeX colours and the matplotlib style; a test fails when they drift (see {doc}`styles`).

## Known limits

- The font subsets have no Greek letters, `≥ ≤ ≈ √` or the bullet. LaTeX writes them as math macros;
  in HTML they fall back to the next family of the stack (DejaVu Sans, Arial).
- pdfLaTeX cannot load OpenType fonts: it uses Latin Modern Sans and warns (`W901`).
- In `default@1`, text set in `--gray-500` (the running header, footer and some labels) is 3.9:1 on white,
  below WCAG AA for small text; `modern@1` uses darker greys.
- The LaTeX look follows the HTML look, not pixel for pixel: table rows are shaded and given a left strip
  of a width per verdict, not a dashed or double border.
