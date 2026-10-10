# STATUS

**Phase:** S3 (default and modern layouts, PDF engines, styles, examples). Implementation complete on branch
`s3/layouts-pdf` (stacked on `s2/templates-validation-writers`, see DECISIONS). **Blocked on gate HG-S1** (visual
sign-off, below). Next after the gate: S4 (`prompts/scireport/s4_kickoff.md` in the monorepo).

## Done in S3

- Layouts `default@1` (the MOSAICS look) and `modern@1` ("Signal"), each with Markdown, HTML and LaTeX components;
  `default@1` is the default layout.
- PDF engines: WeasyPrint and `latexmk` (LuaLaTeX default, XeLaTeX, pdfLaTeX with a `W901` fallback to TeX fonts);
  exit code 3 with an install hint for a missing system dependency; `SOURCE_DATE_EPOCH` honoured.
- Math: `mathtext` and `usetex` renderers, `W602`.
- Vendored Inter and IBM Plex Mono subsets with `OFL.txt`; the style API (`mplstyle()`, `mplstyle_path()`,
  `palette()`, `figure()`, deterministic PNG, PDF and SVG saving) and the palette, CSS, LaTeX and mplstyle
  consistency test.
- `kitchen-sink@1`, three examples, and a real `make examples`: 3 examples x 2 layouts x (md, html, tex, PDF via
  WeasyPrint, PDF via LuaLaTeX, XeLaTeX and pdfLaTeX) into `examples/_out/`.
- **CI is Linux only** (requested 2026-10-10): macOS and Windows jobs are removed from `ci.yml` and `release.yml`;
  both platforms are unsupported. This settles kickoff item 9 (Windows WeasyPrint status) by decision, not by
  evidence (DECISIONS, 2026-10-10).
- PDF determinism per engine is recorded in DECISIONS (2026-10-10).

## Verification (local, 2026-10-10)

| Check | Result |
|---|---|
| `make check` (ruff format and lint, mypy strict, pytest) | passes; 1048 tests, coverage 96.48 % (gate 90 %) |
| `pytest -m integration` with `SCIREPORT_REQUIRE_TOOLCHAIN=1` | 58 passed (PDF text against the Markdown output, double-build byte identity per engine, PDF text hashes of the compat cases, LaTeX error and missing-package paths) |
| `make examples` | exit 0 for 3 examples x 2 layouts; `W901` only for the pdfLaTeX runs, as designed |
| Toolchain | Debian TeX Live 2023 (`latexmk`, lualatex, xelatex, pdflatex); WeasyPrint 70.0 with fontTools (HarfBuzz-Subset absent locally, so WeasyPrint warns) |

## Not verified yet

- **GitHub Actions on the Linux-only matrix has not run.** Nothing was pushed before the CI change and `gh` is not
  logged in here. Until the first run is green, the CI edit (`ci.yml`, `release.yml`) is checked only as valid
  YAML.
- Python 3.13 to 3.15 and the `lowest` job run in CI only; local Python is 3.12.
- The TeX Live in CI is the current release from `.github/tl_packages`, not Debian 2023.
- The gate files in `examples/_out/hg-s1/` were built in the previous session (2026-10-09 23:41) from the same
  layout code as now. `make examples` does not rebuild them; `examples/gate_s1.py --mosaics <pdf>` does.

## Gate HG-S1: visual sign-off (blocking)

**What this is for.** `default@1` and `modern@1` are the two designs that every later phase (S4 to S8) and the
first consumer, the `2_dataset` report, build on. After release a layout is frozen (ADR-0008): a look change then
needs a new version (`default@2`), and old bundles keep the old look. Changing a look is cheapest now.

**Terms.** *Kitchen sink*: one test report that uses every component and hard case. *MOSAICS*: the report design
system in the datex repository that `default@1` ports. *Signal*: the working name of `modern@1` (black, white and
one vermilion accent, rule-only tables, giant chapter numerals). *WeasyPrint*: the engine that prints the HTML to
PDF. *LuaLaTeX*: the default LaTeX engine (XeLaTeX gives the same look; pdfLaTeX uses TeX fonts, `W901`).

**Files to inspect** (in `examples/_out/hg-s1/`, not committed; rebuild with `uv run python examples/gate_s1.py
--mosaics <datex demo pdf>`):

| File | Pages | What it is |
|---|---|---|
| `mosaics-kitchen-sink.pdf` | 17 | the MOSAICS demo |
| `default-weasyprint.pdf` | 19 | `default@1`, WeasyPrint |
| `default-lualatex.pdf` | 22 | `default@1`, LuaLaTeX |
| `modern-weasyprint.pdf` | 19 | `modern@1`, WeasyPrint |
| `modern-lualatex.pdf` | 20 | `modern@1`, LuaLaTeX |
| `compare-default.png` | | cover, contents, chapter opener, status levels, flow, table: MOSAICS, WeasyPrint and LuaLaTeX side by side |
| `compare-modern.png` | | the same pages for `modern@1`, both engines |

Also: `examples/_out/modern-alternatives/` (mock-ups of A Folio, B Gridline and C Signal) and the per-example
outputs for all engines in `examples/_out/<example>/<layout>/`. Page counts differ because each engine breaks
pages its own way.

**What I see in `compare-*.png`** (my reading of the images, not a measurement): `default@1` follows the MOSAICS
cover (navy, grid, circle), contents and chapter opener on both engines; the LuaLaTeX chapter title wraps earlier
and the circle on the cover is larger and lower than in WeasyPrint. `modern@1` has a vermilion cover band with a
black circle, a giant numeral (`01 / 02`) on chapter openers, and rules, shapes and a text word (not hue alone)
for the status levels, identically on both engines. Please check the table and flow pages yourself: I did not
verify pixel-level parity.

**Known limitations** waiting for your decision:

1. The vendored font subsets have no Greek letters or `≥ ≤ ≈ √`. LaTeX draws them with math macros and HTML falls
   back to another font. Widening the subsets costs about +10 KB per face (the fonts inlined in one HTML file are
   about 350 KB today).
2. The LuaLaTeX `default@1` PDF has 22 pages against 19 for WeasyPrint. I have not investigated why.

**Options.**

- (a) Accept as is. Consequence: both layouts are frozen as version 1 at release; S4 starts on them.
- (b) List defects to fix before S4. Consequence: I fix them inside `default/1` and `modern/1` (nothing is
  released, so no new version is needed), including limitations 1 and 2 if you want them.
- (c) Change the modern direction (Folio or Gridline from the alternatives, or a new round). Consequence:
  `modern/1` is redone with its HTML and LaTeX components, golden files and compat renders; `default@1` is
  untouched.

**Recommendation: (b), with limitation 1 fixed.** Missing Greek letters are a real limitation for scientific
reports and are cheap to fix now and impossible to fix inside a frozen version. The rest is your call after
looking at the PDFs.

## Blocked / questions

- HG-S1 above. I stopped and did not start S4.
- The pull request is not open yet: `gh` is not logged in on this machine (`gh auth login`), or push the branch
  and open it from the web. The first run of the Linux-only CI happens then.

## Record: HG-S0 (answered, 2026-10-09)

- Repository public, Pages source = GitHub Actions: yes.
- ADR-0001 to ADR-0011: approve all, including (a) ZIP bundle with a JSON manifest and (b) semantic keys with
  typed values.
- Python 3.15: (a) keep experimental until wheels exist.

## Open items handed to later phases

1. **Pages:** the `docs` workflow failed on `main` at `configure-pages` before the Pages source was set to GitHub
   Actions; check whether it passes after the merge, otherwise it is S6 work.
2. `.github/tl_packages` was pruned in S3 (`siunitx`, `biblatex`, `biber` removed); S5 re-adds what it needs.
