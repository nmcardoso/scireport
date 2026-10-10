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
the choices is `E806`.

| Option | Default | Meaning |
|---|---|---|
| `toc` | `true` | write a table of contents |
| `cover` | `true` | a cover page (otherwise a plain title block) |
| `paper` | `a4` | `a4` or `letter` |
| `chapter_breaks` | `true` | start every chapter on a new page |
| `numbered_captions` | `true` | "Table 3." and "Figure 2." before captions |
| `header` | `true` | the running header and footer of a PDF |

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
