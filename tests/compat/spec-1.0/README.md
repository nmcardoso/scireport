# Compat corpus for spec 1.0

Frozen fixtures (ADR-0008). Every file listed in `FROZEN.sha256` must stay byte-identical: CI fails
when one changes, and a second check fails when a line of the list disappears or changes since the
base of a change or since the latest release (`tests/frozen.py`). A change in how a case loads is a
break of spec 1.0 and needs a new spec version.

Each case holds the bundle in the forms it supports plus `expected/`:

| Case | Forms | What it checks |
|---|---|---|
| `minimal` | directory, ZIP | The smallest bundle. |
| `text-only` | hand-authored YAML directory (`source/`), single JSON file, ZIP | Bare JSON shorthand, YAML typing rules, no assets. |
| `full-kinds` | directory, ZIP | The 16 kinds of the first draft, every asset type, render and outline blocks. Its outline lists four values, so only those reach the renders. |
| `bibliography` | directory, ZIP | The `bibliography` kind (added in S5, before the 1.0 release), `[@key]` citations, and the LaTeX render. |
| `every-kind` | directory, ZIP | The values of `full-kinds` plus a bibliography, with an outline that lists all 17 kinds, so every kind reaches every frozen render. |

`expected/manifest.json` is the canonical manifest a reader must produce; `expected/summary.json` is
what `scireport inspect --json` reports (without the path and form).

## Renders

`expected/render-generic-1-<layout>-1/<format>/` holds what `generic@1` and the layout write for
the case with the default markup engine (`mistletoe`), and `render-generic-1-<layout>-1-pandoc/`
what they write with `--markup-engine pandoc`. The layouts are `minimal`, `default` and `modern`,
the formats `md`, `html` and `tex`. The package version in the file headers is replaced by
`<version>`, `render-manifest.json` is left out (it records dependency versions) and the SVG
drawings of math in HTML are replaced by a marker. HTML is compared as a DOM, not as bytes.

For `default@1` and `modern@1` the folder also holds `pdf-text-weasyprint.sha256` and
`pdf-text-lualatex.sha256`: the SHA-256 of the letters of the PDF's text (PDFs are made without a
table of contents and running header, whose text depends on pagination). PDF bytes depend on the
pango, HarfBuzz and TeX Live versions, so they are not frozen.

`generic@1` renders what the outline lists, so the values a case's outline leaves out are not in
these files; `every-kind` lists all of them. `bibliography` has only the LaTeX render with
`mistletoe` (and the PDF text hash of LuaLaTeX): a citation in Markdown or HTML needs pandoc.

What pandoc writes depends on its version, so `pandoc-version.txt` records the version that made the
`-pandoc` folders (the one `uv.lock` pins through `pypandoc-binary`). With another version those
tests skip locally and fail in CI. A pandoc upgrade adds folders for the new version; it never
edits these files. The Word, OpenDocument and EPUB outputs are converted by pandoc from the frozen
Markdown and are not frozen themselves.

## Scripts

The corpus was created in steps, each by a script that only adds files, appends to
`FROZEN.sha256` and refuses to run again: `make_spec_1_0.py` (cases and manifests),
`make_render_1_0.py` (`minimal@1`), `make_render_layouts_1_0.py` (`default@1`, `modern@1`, PDF text
hashes), `make_bibliography_1_0.py`, and `make_every_kind_1_0.py` with `make_render_complete_1_0.py`
(the `every-kind` case, the pandoc renders and the bibliography renders of the designed layouts).
The built-in layouts, templates, fonts, styles and the JSON Schema are frozen by
`../FROZEN-builtins.sha256`.
