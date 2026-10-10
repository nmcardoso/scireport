# STATUS

**Phase:** S4 (pre-processors) implemented on branch `s4/preprocessors` (stacked on `s3/layouts-pdf`, see DECISIONS).
No gate. **Open: the HG-S1 layout changes are not applied yet** (see "Next"). Next phase: S5 (`prompts/scireport/s5_kickoff.md`
in the monorepo).

## Done in S4

- The pre-processor interface (ADR-0006): `@preprocessor` with typed ports, pydantic parameters from the signature, the
  registry (built-ins, entry points, `register_preprocessor()`), name-only references (`module:func` only with
  `--allow-import`), the DAG check before running (all problems at once, codes `E601`-`E605`), work-dir outputs, the
  content-hash cache, `Context`; `scireport preprocess` and `scireport preprocessors`; `render` and `validate` run the steps.
- The core catalogue (18) and the astro catalogue (9); the full list is in `docs/preprocessors.md` and is drift-tested.
  Each figure has the three tests of the kickoff (smoke, determinism, figure rebuilt from its sidecar data).
- Docs: `docs/preprocessors.md`; error page extended; CHANGELOG and DECISIONS updated (including the list of deliberate
  differences from MOSAICS, to be reviewed by you).

## Verification (local, 2026-10-10)

| Check | Result |
|---|---|
| `make check` (ruff format and lint, mypy strict, pytest) | passes; 1431 tests, coverage 97.37 % (gate 90 %) |
| `make docs` (`-W`) | builds |
| Rendered by eye | sky density (Mollweide, RA 0 at the centre, increasing to the left), heatmap, corner, histogram |
| Catalogue imports | registering the catalogue imports neither astropy, scipy, pandas nor mocpy (subprocess test) |

## Not verified yet

- **GitHub Actions has not run on this branch.** `ci.yml` triggers only on pull requests, pushes to `main` and manual
  dispatch, so pushing `s4/preprocessors` started nothing, and `gh` is not logged in here to dispatch it. The last CI run
  on `s3/layouts-pdf` (success, 6a10768) predates the Linux-only change (684996d), so that edit has never run either, and
  Python 3.13 to 3.15 and the `lowest` job are untested for S3 and S4. To get the first run: `gh auth login`, or open the
  pull requests (S3 into main, then S4 into S3) from the web.
- `pytest -m integration` (PDF engines) was not re-run after the S4 changes (they touch no PDF code).
- The sky maps and the 27 figures were checked by test and a few by eye, not all by eye.

## Next

1. **Apply the HG-S1 answer** (below) on `s3/layouts-pdf`: it is a visual loop (13 numbered defects of `default@1` and a
   redesign of `modern@1` after `/home/natan/Downloads/TUPAN_publication_plan.pdf`). It was not part of the S4 kickoff and
   is untouched. Tell me whether to do it before S5.
2. Review the deliberate differences from MOSAICS (DECISIONS, 2026-10-10 row "The catalogue is not a one-to-one copy").
3. Open the pull requests (the branches are pushed) and read the CI matrix.

## Record: HG-S1 (answered; its changes are pending, see Next)

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

**Answer:** Change the `modern@1` design to match as most as possible [this report](/home/natan/Downloads/TUPAN_publication_plan.pdf) ([tex source](/home/natan/Downloads/TUPAN_publication_plan.tex)), including the font. The `default@1` needs the following changes: (1) weasyprint: full width rule in the header (like the lualatex version); (2) both: increase the spacing between the header and the page content (e.g., the title or first paragraph); (3) lualatex: decrease the spacing between the H1 title and the horizontal rule; (4) lualatex: the spacings of the table of contents are completely misaligned, the vertical spacing between the entries is too high, the page numbers are not aligned to the right; (5) lualatex: in the metrics summary, increase the vertical spacing between the metric name/title and the metric value; (6) both: break page after the table of contents and the chapter titles; (7) both: the colored left rule/border of the aler boxes (such as those in "Status levels" section) should always be solid like in "COMPLETED SUCCESSFULLY", all other variants (e.g., dashed, dotted, double, etc) should be converted to simple solid line; (8) both: remove the dots of the timeline ("Pipeline flow" section), as neigther of versions redered it correctly; (9) both: remove the width cap of the text, the text should span full page width; (10) both: Use a serif font in text body and increase its size, keep the current font in the table body; (11) lualatex: fix the height of the table header, currently the height is more than the double of the correct size; (12) lualatex: always render the unit or type of the column in the next line of the table header, since the real reports with have tables with several columns; (13) lualatex: fix the bug in the page number 16 close to the "A 250-row profile table", a ghost table header is rendered on the top of the page.

## Blocked / questions

- Not blocked. One question: apply the HG-S1 layout changes (Next, item 1) before S5, or after? My recommendation is before:
  S5 adds pandoc output and the LaTeX fragment export on top of the layouts, and a look change after v1.0.0rc1 would need
  `default@2` (ADR-0008).
- The pull requests are not open: `gh` is not logged in on this machine (`gh auth login`), or open them from the web.

## Record: HG-S0 (answered, 2026-10-09)

- Repository public, Pages source = GitHub Actions: yes.
- ADR-0001 to ADR-0011: approve all, including (a) ZIP bundle with a JSON manifest and (b) semantic keys with
  typed values.
- Python 3.15: (a) keep experimental until wheels exist.

## Open items handed to later phases

1. **Pages:** the `docs` workflow failed on `main` at `configure-pages` before the Pages source was set to GitHub
   Actions; check whether it passes after the merge, otherwise it is S6 work.
2. `.github/tl_packages` was pruned in S3 (`siunitx`, `biblatex`, `biber` removed); S5 re-adds what it needs.
