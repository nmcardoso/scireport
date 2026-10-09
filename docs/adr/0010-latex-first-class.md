# ADR-0010: LaTeX is a first-class output

- Status: Accepted (HG-S0, 2026-10-09)
- Date: 2026-10-09

## Decision

1. **Standalone LaTeX output** (`-f tex`): `report.tex`, the layout's preamble or class (`scireport-<layout>.sty`)
   and `figures/` (PDF renditions preferred, then PNG; SVG never). Tables use `booktabs`/`longtable` and
   `siunitx`. The project compiles with plain `latexmk` outside scireport. Both layouts ship LaTeX components that
   match their HTML look (`tcolorbox`, `fancyhdr`, a TikZ cover). Under `pdflatex` the layouts fall back to TeX
   fonts with a warning.
2. **Fragments for manuscripts:** `scireport export tex BUNDLE --keys ... -o paper/generated/` writes `tab_<key>.tex`,
   `fig_<key>.tex` and **`numbers.tex`** with one `\newcommand` per `number` value (key to CamelCase macro, with a
   configurable prefix; a collision is an error). This matches the monorepo rule that paper numbers come from
   generated macros.
3. **LaTeX math everywhere:** the `math` kind and `$...$`/`$$...$$` in prose are native in tex, kept in md, and
   rendered to SVG in html and WeasyPrint. `render.math_renderer` selects `mathtext` (default, pure Python) or
   `usetex`. A construct mathtext cannot draw gives warning `W6xx` and shows the source as code; `--strict` makes
   it an error.
4. **Raw LaTeX passthrough:** `text` with `format: latex` is emitted verbatim in tex; other formats need an explicit
   `alt: {html, md}` or pandoc, otherwise `E2xx`.
5. **Safety and tests:** LaTeX-safe Jinja delimiters; the escape filter covers `# $ % & ~ _ ^ \ { }` and Unicode
   (through the font, or a mapping under pdflatex); a hypothesis property test on the escape function; a compile
   check marked `integration`; golden `.tex` for every example, both layouts and all three engines.

## Consequences

Manuscripts and reports share one pipeline for numbers and tables. The LaTeX toolchain is exercised in CI on all
three operating systems.
