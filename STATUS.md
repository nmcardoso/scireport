# STATUS

**Phase:** S7 (freeze and release 1.0.0) is done up to the gate. Branch `s7/release`, pull request
[#2](https://github.com/nmcardoso/scireport/pull/2), **not merged into `main` yet** (the merge was refused by the permission
system of the session: merge the pull request, all its checks are green). The package says `1.0.0`; the **tag `v1.0.0` is
not pushed**. **Blocked on gate HG-S2** (release sign-off), written below. Next phase after the tag: S8 (nothing started).

## Gate HG-S2: release sign-off for scireport 1.0.0

### Purpose: what each answer changes

Pushing the git tag `v1.0.0` (a named, permanent pointer to one commit) is what makes 1.0.0 a release. It builds the wheel
and source archive, creates the GitHub release that other projects install from (`...@v1.0.0`), and starts the promise of
ADR-0008: from then on specification 1.0, the layouts `minimal@1`, `default@1`, `modern@1`, the templates `generic@1`,
`kitchen-sink@1`, the error codes and the public Python API never change in a way that alters an old report; a visual change
becomes `default@2` instead of an edit. Before the tag any of them can still be edited (and the corpus regenerated); after
it only additions are allowed. So the answers below decide (1) whether the tag is pushed now or after changes that are still
cheap today, and (2) what is archived and cited.

Terms. **Freeze**: the files whose bytes must never change are listed with their SHA-256 hash (a 64-character fingerprint)
in two lists, and tests and CI fail when a file or a list line changes. **Compat corpus** (`tests/compat/spec-1.0/`): small
reports ("cases") together with the Markdown, HTML, LaTeX and PDF-text outputs they must keep producing. **Clean room**:
installing the package from the public GitHub URL into an empty virtual environment, outside the repository, and rendering
an example, to prove that a consumer gets a working package. **Zenodo**: a free archive that gives a software release a DOI
(a permanent citable identifier) when linked to the GitHub repository.

### Evidence (2026-10-11, head commit `ab14944` of `s7/release`)

| Check | Result |
|---|---|
| CI workflow `ci` on pull request #2 | **15 of 15 jobs succeeded**: `lint` (1), `test` (4: Python 3.12, 3.13, 3.14, 3.15), `lowest` (1), `pdf-weasyprint` (2: 3.12, 3.15), `pdf-latex` (2: 3.12, 3.15), `pandoc` (1), `mcp` (1), `examples` (1), `docs` (1), `compat` (1, new) |
| `main` before this branch (`0259ac5`) | 14 of 14 jobs succeeded (all of the above except `compat`) |
| Workflow `docs` on the pull request | build succeeded (the deploy runs on `main` only) |
| `release` workflow, started by hand against `s7/release` | `build` succeeded (the wheel and the source archive each hold all 64 frozen built-in files with the recorded hash, and the wheel holds the agent skill); `clean-room` succeeded (`scireport[pdf,astro]` installed from `git+https://github.com/nmcardoso/scireport@s7/release`, kitchen sink rendered to Markdown, HTML, LaTeX and PDF with `default` and `modern`) |
| Same clean room on this machine, Python 3.12, installed from a `file://` URL of the repository | passed |
| `make check` (ruff format and lint, mypy strict, pytest) | 1617 passed; coverage 95.25 % (gate 90 %) |
| `pytest -m integration` with `SCIREPORT_REQUIRE_TOOLCHAIN=1` (PDF engines, pandoc, MCP) | 242 passed, 0 skipped |
| `make docs` (`-W`, HTML and Markdown builds, site check) | pass; 34 pages |

The kickoff asked for the clean room "on all three operating systems"; that is superseded by the Linux-only decision of
2026-10-10 (DECISIONS), so it runs on Linux.

**Compat corpus** (`tests/compat/spec-1.0/`): 5 cases (`minimal`, `text-only`, `full-kinds`, `bibliography`, `every-kind`),
17.3 MB on disk, **488 frozen files** listed in `FROZEN.sha256`: 34 bundle fixtures (directory, ZIP and single-file forms),
10 expected manifests and summaries, 200 renders with the default markup engine `mistletoe`, 206 renders with `pandoc`, and 38
PDF-text hashes. Coverage of the promise: all 17 kinds (the new `every-kind` case lists every kind in its outline), 3 layouts
(`default@1`, `modern@1`, plus `minimal@1`), 3 formats (Markdown, HTML, LaTeX), PDF through the letters of the WeasyPrint and
LuaLaTeX output, 2 markup engines. A second list freezes the **64 built-in files** (`tests/compat/FROZEN-builtins.sha256`:
14 files of `default/1`, 15 of `modern/1`, 9 of `minimal/1`, 2 of `generic/1`, 2 of `kitchen-sink/1`, 19 in
`styles/fonts/` (17 fonts and 2 licence texts), 2 `.mplstyle` files and the JSON Schema `data-1.0.schema.json`).

| File | SHA-256 |
|---|---|
| `tests/compat/spec-1.0/FROZEN.sha256` | `415197024488d5675245a38fa6a88f86b6ce4b12873227c69fc3a21c4fcb2ac3` |
| `tests/compat/FROZEN-builtins.sha256` | `760aecee01c1cda2772f15e6ee4f138e4133bcafe3600155357afdac13d73f03` |
| `scireport/spec/schemas/data-1.0.schema.json` | `edc111445e501e6fa153d03efe3dfd0e71b6788c990217af98e91c47f422c24e` |
| `tests/compat/spec-1.0/pandoc-version.txt` | `3ec15f7f82d24dbcd050ce11c3994d981499b029772da41c37a2cd0acce87f6e` (pandoc 3.9) |

CI fails when a fixture changes, when a built-in file changes or is added unlisted, and, from the first tag on, when a line of
either list disappears or changes since the latest release tag (`tests/frozen.py`, `make compat-growth BASE=<rev>`).

### Known limits (to be accepted with the release)

- **PDF determinism, per engine.** Two builds on one machine with the same library versions give identical bytes for
  WeasyPrint, LuaLaTeX, XeLaTeX and pdfLaTeX (tested, 2026-10-10). Across machines the bytes may differ (pango, HarfBuzz, TeX
  Live versions), so the corpus freezes the letters of the PDF text, for WeasyPrint and LuaLaTeX only; XeLaTeX and pdfLaTeX are
  tested for content, not frozen. pdfLaTeX needs the Latin Modern fallback for `default@1` (warning `W901`) and cannot typeset
  non-ASCII characters inside code blocks.
- **Windows and macOS: unsupported** by decision (Linux-only CI since 2026-10-10); no WeasyPrint-on-Windows evidence exists.
  The code stays portable (`pathlib`, LF files).
- **Python 3.15: experimental.** The 3.15 jobs pass but build `pyyaml` from source, because it has no cp315 wheel (checked
  again today); HG-S0 said to keep it experimental until wheels exist. README: Python 3.12 to 3.14 supported.
- **pandoc output depends on pandoc's version.** The `-pandoc` corpus files are compared only with pandoc 3.9 (the version
  `uv.lock` pins); another version skips the tests locally and fails them in CI, so an upgrade is a decision. Word, OpenDocument
  and EPUB files are converted by pandoc and are not frozen.
- **Layout defects that remain**: in `default@1` one heading above a figure that does not fit can be left at a page foot
  ("Figures at three widths" of the kitchen sink); `minimal@1` makes WeasyPrint warn about `overflow-x` if an author copies its
  CSS. Page breaks differ per engine.
- Open review findings, unchanged and not blocking (each is a decision or out of scope): paths in `render.layout` /
  `render.template` (`E205`), asset kind-versus-folder pairing, assets copied only by the LaTeX writer, layouts cannot ship
  fonts (`E703`), validation stops at the spec stage, other component output inside `{% filter md %}` still breaks in LaTeX,
  `docs/quickstart.md` and `docs/guide.md` show `report.write` without `overwrite=True`, `Report.add_figure` PNGs differ from
  before (cropped), `numbers.tex` naming, citations read only in Markdown `text` values, and a literal `has('x')` in a template
  counts as a read (`E106`).

### Questions (answer in one reply; (1) and (2) block the tag, the rest can be answered later)

**(1) Push the tag `v1.0.0`?** The default is that nothing is tagged until you say so.

- (a) **Approve as is.** Merge pull request #2, then the dates are updated (below) and `v1.0.0` is pushed from `main`. The two
  design questions under (2) stay as they are and a change later becomes a new layout version.
- (b) **Approve after the answers to (2).** Changes asked for in (2) are made first, the corpus folders of the affected layout
  and its lines in the two freeze lists are regenerated (allowed only until the tag), CI is re-run, then the tag.
- (c) **Hold**, with the changes you want listed.

Recommendation: **(b)**. Question (2a) is cheap now and expensive after the tag (it renames fonts in a frozen layout), so the
tag should wait for that one answer; it does not need to wait for anything else.

What happens at the tag (after (a) or (b)): I set the date in `CHANGELOG.md` (`[1.0.0] - unreleased`) and `date-released` in
`CITATION.cff`, commit, create the annotated tag `v1.0.0` and push it; the `release` workflow builds the wheel and source
archive, checks the frozen files in them, creates the GitHub release with generated notes and runs the clean room from the tag;
then the `docs` workflow publishes the site with the 1.0.0 page.

**(2) Design questions left over from gate HG-S1** (the layouts freeze at the tag):

- **(2a) Licence of the TeX Gyre subsets in `modern@1`.** `modern@1` uses TeX Gyre Pagella, Heros and Cursor (free clones of
  Palatino, Helvetica and Courier; GUST Font Licence, which resembles the LaTeX Project Public Licence). That licence asks that
  a *modified* font be renamed, and our files are subsets (the glyphs we need, Greek included) that keep the original family
  name, as the Inter and IBM Plex subsets do under the SIL Open Font Licence (which has the same "Reserved Font Name" idea). The
  licence text ships next to the fonts. Options: (a) keep and record it (current state); (b) rename the subset families in the
  font files, `fonts.py`, the `.sty` and CSS (for example "TeX Gyre Pagella Subset"), a mechanical change that alters the frozen
  CSS, `.sty` and fonts of `modern@1` and so regenerates its corpus folders now; (c) drop the vendored TeX Gyre files and use
  TeX Live's for LaTeX and a system font for HTML (breaks the one-file HTML). Recommendation: **(b) before the tag**, because
  after it the rename needs `modern@2`. `CLAUDE.md` rule 6 names only OFL fonts and needs one sentence for the GFL; I will
  add it with your answer.
- **(2b) Line length of `default@1`.** Body text is IBM Plex Serif 11 pt over the full width (about 120 characters per line on
  A4 with 9 mm side margins, as HG-S1 asked). Options: (a) keep; (b) widen the side margins to 15 mm (about 110 characters).
  Recommendation: (a), it is what you asked for; (b) is a one-number change in two files if the printed page reads badly.
- **(2c) Rows with a verdict in `default@1` HTML tables** keep a dashed or double border; `modern@1` and LaTeX use a solid
  strip. Options: (a) keep; (b) make `default@1` solid too. Recommendation: (a): the dashes are what tells a failed row from a
  passed one in grey print; answer 7 of HG-S1 named only the alert boxes.
- **(2d) `minimal@1` `overflow-x` warning in WeasyPrint** (affects only an author who copies its CSS). Options: (a) leave and
  document (current); (b) fix it, which changes three frozen compat files and four golden files of a layout that is only
  "released in spirit" today. Recommendation: (a); after the tag (b) would need `minimal@2`.

**(3) Archive the software on Zenodo with a DOI?** The DOI would let a paper cite "scireport 1.0.0" permanently; Zenodo keeps a
*concept DOI* that stays the same across all versions and gives each release its own *version DOI*. It needs you to link the
GitHub repository on zenodo.org (I cannot do that) before the release is created, and it archives every later release too.
Options: (a) **yes, now**: link before the tag; I then add the concept DOI to `CITATION.cff` and the README after the release;
(b) after the `2_dataset` migration, so the archived version is one that a real consumer has used (the DOI of 1.0.0 would still
exist if you link later, but only releases made after linking are archived automatically); (c) no. Recommendation: **(a)**:
the concept DOI is the same whichever version you cite, linking costs nothing, and waiting only means the first release is
not archived. It needs the answer to (4).

**(4) Citation metadata.** `CITATION.cff` has the author as "N. Cardoso" (as `pyproject.toml`), without a full given name, an
ORCID or an affiliation, and without a DOI. Give them (or say "as is") before the tag; a wrong author on a DOI cannot be
edited out of the archived version.

### Mechanics that you may want to know

- Until pull request #2 is merged, `main` still says `0.1.0.dev0` and has no freeze lists; the tag must be created on the
  merge commit. The freeze check in CI is skipped until the first tag exists, so a change requested at this gate is not blocked.
- To change a frozen layout before the tag: edit it, regenerate its corpus folders (a one-off script like
  `make_render_layouts_1_0.py`, which refuses to overwrite: remove the folder first), delete and rewrite its lines in
  `FROZEN.sha256` and `FROZEN-builtins.sha256`, and run `make check` and `make test-integration`.
- The leftover worktree of the S6-findings subagent is at `.claude/worktrees/agent-a81cab07de74db192` (branch
  `worktree-agent-a81cab07de74db192`, its changes were applied in an earlier session); remove it with `git worktree remove
  --force` when you no longer need its commits.

## Done in this session (S7)

- Corpus completed: `every-kind` case, `-pandoc` renders of every case and layout, `bibliography` with the designed layouts,
  PDF-text hashes for each, `pandoc-version.txt` (scripts `make_every_kind_1_0.py`, `make_render_complete_1_0.py`; tests
  `test_render_pandoc_1_0.py`, extended `test_render_layouts_1_0.py`, `test_render_1_0.py`, `test_spec_1_0.py`,
  `tests/integration/test_pdf.py`).
- Built-ins frozen by hash (`FROZEN-builtins.sha256`, `test_frozen_builtins.py`), the growth check (`tests/frozen.py`, `make
  compat-growth`), CI job `compat`, `check_dist.py` and `clean_room.sh` in `release.yml` (now startable by hand).
- API snapshot (`tests/unit/public_api.txt`: only `__version__` changed), frozen JSON Schema (drift test passes, file
  unchanged) and the layouts checked; version 1.0.0; `CITATION.cff`; README; `CHANGELOG.md`; `docs/compatibility.md`.
- Found and fixed on the way: `normalised()` replaced the package version everywhere, which collided with a report's own
  `version` metadata (DECISIONS); 19 golden files changed one line (the manifest hash, which depends on the generator version).

## Record: earlier gates

- **HG-S1** (answered 2026-10-10, applied 2026-10-11): `modern@1` redone after the TUPAN publication plan report, 13 defects of
  `default@1` fixed; the follow-up questions are (2) above.
- **HG-S0** (answered 2026-10-09): repository public and Pages from GitHub Actions; ADR-0001 to ADR-0011 approved; Python
  3.15 kept experimental until wheels exist.
