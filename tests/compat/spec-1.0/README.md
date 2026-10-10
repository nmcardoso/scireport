# Compat corpus for spec 1.0

Frozen fixtures (ADR-0008). Every file listed in `FROZEN.sha256` must stay byte-identical: CI fails
when one changes. A change in how a case loads is a break of spec 1.0 and needs a new spec version.

Each case holds the bundle in the forms it supports plus `expected/`:

| Case | Forms | What it checks |
|---|---|---|
| `minimal` | directory, ZIP | The smallest bundle. |
| `text-only` | hand-authored YAML directory (`source/`), single JSON file, ZIP | Bare JSON shorthand, YAML typing rules, no assets. |
| `full-kinds` | directory, ZIP | The 16 kinds of the first draft, every asset type, render and outline blocks. |
| `bibliography` | directory, ZIP | The `bibliography` kind (added in S5, before the 1.0 release), `[@key]` citations, and the LaTeX render. Added by `make_bibliography_1_0.py`. |

`expected/manifest.json` is the canonical manifest a reader must produce; `expected/summary.json` is
what `scireport inspect --json` reports (without the path and form). `expected/render-generic-1-minimal-1/{md,html,tex}/` holds the files that `generic@1` and `minimal@1` write for the
case (added in phase S2 by `make_render_1_0.py`; the package version in the file headers is replaced by
`<version>` and `render-manifest.json` is left out, because it records dependency versions). `generic@1` renders
what the outline lists, so the values a case's outline leaves out are not in these files; `tests/golden/` renders
every kind. Later phases add the PDF text hash and the renders of `default@1` and `modern@1`.

`tests/compat/make_spec_1_0.py` created the corpus once and refuses to run again.
