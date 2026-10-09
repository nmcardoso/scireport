# Compat corpus for spec 1.0

Frozen fixtures (ADR-0008). Every file listed in `FROZEN.sha256` must stay byte-identical: CI fails
when one changes. A change in how a case loads is a break of spec 1.0 and needs a new spec version.

Each case holds the bundle in the forms it supports plus `expected/`:

| Case | Forms | What it checks |
|---|---|---|
| `minimal` | directory, ZIP | The smallest bundle. |
| `text-only` | hand-authored YAML directory (`source/`), single JSON file, ZIP | Bare JSON shorthand, YAML typing rules, no assets. |
| `full-kinds` | directory, ZIP | All 16 kinds, every asset type, render and outline blocks. |

`expected/manifest.json` is the canonical manifest a reader must produce; `expected/summary.json` is
what `scireport inspect --json` reports (without the path and form). Later phases add the expected
`.md`, canonical `.html`, `.tex` and PDF text hash per case.

`tests/compat/make_spec_1_0.py` created the corpus once and refuses to run again.
