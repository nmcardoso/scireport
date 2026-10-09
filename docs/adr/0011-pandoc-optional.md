# ADR-0011: Pandoc is optional and used only where it adds value

- Status: Accepted (HG-S0, 2026-10-09)
- Date: 2026-10-09

## Decision

**Backend.** `scireport[pandoc]` installs `pypandoc-binary` (wheels bundle pandoc for Linux, macOS, Windows), so
no system pandoc is needed and runs are reproducible. It is imported lazily.

**Uses:**

1. **Markup converter backend.** `render.markup_engine: mistletoe | pandoc`, default `mistletoe` (pure Python).
   pandoc gives higher fidelity for GFM tables, footnotes, math and definition lists in Markdown to LaTeX and to
   HTML, and converts raw `format: latex` text to HTML or md. There is **no automatic switching**: output must not
   depend on what is installed. The pandoc version goes into `render-manifest.json`; a version that differs from the
   one recorded in the bundle gives a warning.
2. **Citations.** An optional `bibliography` kind (a BibTeX asset) and `[@key]` in prose: tex uses `biblatex` with
   `biber`; md and html use pandoc citeproc with an optional CSL asset; without pandoc the result is error `E5xx`
   with an install hint.
3. **Extra formats** `docx`, `odt`, `epub`, converted from the rendered HTML or md. A layout may supply a
   `reference.docx`.

**Tests:** golden outputs for both markup engines on the same examples; the documented differences are listed in
the docs.

## Consequences

Core installs stay light. Two markup engines can diverge, which is managed by tests rather than by hidden switching.
