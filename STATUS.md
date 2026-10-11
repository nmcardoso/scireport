# STATUS

**Phase:** HG-S1 applied and the post-S6 review findings fixed, on branch `hg-s1/layouts` (not committed or pushed:
nothing in this session was committed). S6 (documentation site) is merged on `main`. Next phase: S7 (1.0 freeze). **Gate:
HG-S1 follow-up** (see "Questions"): please look at the two layouts before S7 freezes them.

## Done in this session

- **`default@1`** (all 13 points of the HG-S1 answer; both PDF engines checked by eye on the kitchen sink): (1) one full-width
  header rule in WeasyPrint; (2) 8 mm (WeasyPrint) and 22 pt (LuaLaTeX) between header and content; (3) the heading rule
  follows the H1 (the LaTeX rule was a whole line high: `\scrule` is now a box, no paragraph); (4) contents: tight rows, page
  numbers flush right, hanging titles; (5) 9 pt between a metric title and its value; (6) page break after the contents and
  after every chapter title (not when `chapter_breaks` is false); (7) status and alert boxes: always a solid left border;
  (8) no timeline dots (the rail is coloured by state); (9) no text cap (no `max-width`, LaTeX right margin 9 mm); (10) IBM
  Plex Serif 11 pt body, sans for headings and tables; (11) table header one line plus the unit; (12) the unit under the
  column name, always; (13) the ghost table header: `\needspace` after a longtable measures a stale page, so headings use
  `\Needspace` (reproduced, then verified gone).
- **`modern@1` "Publication"**, redone after the TUPAN publication plan (blue and gold, Palatino-like text, Helvetica-like
  headings, booktabs tables with the caption above, boxes with a title bar, numbered `1`/`1.1` headings, the abstract on the
  cover, TOC with dot leaders). Font: TeX Gyre Pagella, Heros and Cursor, the free clones of the plan's `mathpazo`,
  `helvet` and `courier` (see the licence question below). `chapter_breaks` defaults to false, as in the plan. All three
  LaTeX engines and WeasyPrint compile it.
- **Fonts**: IBM Plex Serif and the three TeX Gyre faces, subset with Greek letters and `≤ ≥ ≈ ≠ √`; `fonts.licence_files`
  copies `OFL.txt` or `GFL.txt` next to them in the LaTeX project; `Fonts.serif` is an optional palette field.
- **Regenerated** (both layouts are unreleased): `tests/golden/layouts/**` with `SCIREPORT_UPDATE_GOLDEN=1`, and the
  `render-generic-1-{default,modern}-1` folders of the compat corpus plus their lines in `FROZEN.sha256` (a one-off
  script; the repository's `make_render_layouts_1_0.py` refuses to overwrite). Review `git diff --stat tests/compat`.
- **Findings of S6, fixed** by a sonnet subagent (branch `worktree-agent-a81cab07de74db192`, 8 commits, applied here as a
  patch): `pack` pins an absent layout and template; `inspect` counts rows of hand-written tables; broken pipe is quiet
  (`scireport.cli:run`, run `uv sync`); `validate` reports both stages the same way; `E706` and `E804` messages;
  `figure()` uses the constrained layout engine and `add_figure` crops like `save_figure`; `c.number` in `{% filter md %}`
  keeps its LaTeX tie; the skill's `Report.write` examples carry `overwrite=True`; the schema of any older minor is
  generated and tested against the frozen files; the error-code titles are frozen in `tests/compat/error-codes.json`;
  ADR-0005 and ADR-0008 wording; the palette table prints `cmap.sequential`, `fonts.sans`, `page.width_mm` ...

## Verification (local, 2026-10-11)

| Check | Result |
|---|---|
| `make check` (ruff format and lint, mypy strict, pytest with coverage) | pass; 1583 passed, coverage 94.83 % (gate 90 %) |
| `pytest -m integration` (PDF engines, pandoc, MCP) | 117 passed after one test fix: the pdfLaTeX `W901` is expected for `default@1` only |
| `make docs` (`-W`, HTML and Markdown builds, site check) | pass; 34 pages (without the gallery; `make examples` not re-run) |
| Kitchen sink in both layouts, WeasyPrint, LuaLaTeX, XeLaTeX, pdfLaTeX | compile; WeasyPrint and LuaLaTeX pages looked at (default 21 pages each, modern 15 and 13) |
| Ghost table header, heading orphans | gone in `default@1` and `modern@1` LuaLaTeX; one heading above a figure that does not fit can still be left at a page foot (`default@1`, "Figures at three widths") |

## Not verified yet

- **GitHub Actions has not run** on `main` since the S6 CI fix, nor on this branch (`gh` is not logged in). The TeX Live
  package list of the CI (`.github/tl_packages`) was not checked for `tex-gyre` (needed by `modern@1`'s fonts only for
  pdfLaTeX, which loads `tgpagella`, `tgheros`, `tgcursor`) nor for `ragged2e`.
- Both layouts were judged by eye on the kitchen sink and on one pass over the three examples' page counts, not by a
  second reader. Page breaks differ per engine.
- The PDF-text hashes of the compat corpus were regenerated with the PDF toolchains of this machine.

## Next

1. You look at `default@1` and `modern@1` PDFs (`make examples`, then `examples/_out/*/{default,modern}/`) and answer the
   questions below; layouts freeze in S7.
2. S7: freeze (spec, layouts, compat corpus), final `v1.0.0`.
3. Commit this work (nothing is committed): one commit per theme is easiest (fonts, `default@1`, `modern@1`, corpus,
   S6 findings).

## Findings still open (decisions or out of scope; the rest of the S6 list is fixed above)

- **`minimal@1` `overflow-x` warning in WeasyPrint**: not fixed. Changing `minimal.css` alters three frozen compat files and
  four golden files of a layout that is released-in-spirit (ADR-0008); `minimal@1` declares no `pdf_engines`, so only an author
  who copies its CSS meets the warning (the layout guide says how to avoid it). Say if you want it fixed (regenerate the files).
- Path layouts in `render.layout` / `render.template` (`E205`), asset kind-versus-folder pairing, `assets` copied only by the
  LaTeX writer, layouts cannot ship fonts (`E703`), the semver scope questions, and the release-tag mismatch
  (`v1.0.0rc1` never tagged; the package says `0.1.0.dev0`): unchanged, they are decisions.
- Validation still stops at the spec stage: "every problem at once" holds per stage; a spec failure skips the checks that need
  the values (the data-independent template lint could still run: a separate change).
- Other component output inside `{% filter md %}` (LaTeX unit powers, scientific notation) still breaks in LaTeX.
- `docs/quickstart.md` and `docs/guide.md` show `report.write` without `overwrite=True`.
- `Report.add_figure` PNGs differ from before (cropped): a re-added figure changes bytes.

## Questions

- **Licence of the TeX Gyre subsets.** `modern@1` needs a Palatino-like face to match the TUPAN report. TeX Gyre Pagella
  (GUST Font Licence, an LPPL-like free licence) is the free clone and is in every TeX Live; the GFL asks that a *modified*
  font be renamed, and the subsets keep the family name (the same practice as the Inter and Plex subsets under the OFL, where
  the Reserved Font Name "Inter" is also kept). Options: (a) keep as is and record it (what I did; the licence text ships
  next to the fonts); (b) rename the subset families (e.g. "TeX Gyre Pagella Subset") in the files and in `fonts.py`, `.sty`
  and CSS, a mechanical change; (c) drop the vendored TeX Gyre files and rely on TeX Live for LaTeX and on a system font for
  HTML (breaks the one-file HTML). Recommendation: (b) before the 1.0 freeze, because renaming later changes frozen CSS.
  Also CLAUDE.md rule 6 speaks of OFL fonts only; it needs a sentence for the GFL.
- **Body text of `default@1` is Plex Serif 11 pt over full-width lines** (about 120 characters per line on A4 with 9 mm
  margins; as asked). Options: (a) keep; (b) widen the side margins to 15 mm (about 110 characters). I kept (a).
- **Table rows with a verdict** keep a dashed or double border in HTML only for `default@1` (answer 7 named the alert boxes);
  `modern@1` and LaTeX use a solid strip. Say if the `default@1` rows should be solid too.
- Review items from S5 (DECISIONS, rows of 2026-10-10) are unchanged: `numbers.tex` naming, citations read only in Markdown
  `text` values, a literal `has('x')` / `data.x` in a template counts as a read (E106).
- The subagent's worktree is still at `.claude/worktrees/agent-a81cab07de74db192` (branch
  `worktree-agent-a81cab07de74db192`); its changes are applied here. Remove it with `git worktree remove` when you have
  looked at the commits.
- The pull request is not opened (`gh auth login` is needed).

## Record: HG-S1 (answered 2026-10-10, applied 2026-10-11)

The answer asked: change the `modern@1` design to match the TUPAN publication plan report, including its font; and for
`default@1`: (1) WeasyPrint full-width header rule; (2) more space between header and content; (3) LuaLaTeX less space
between H1 and its rule; (4) LuaLaTeX table of contents spacing and right-aligned page numbers; (5) LuaLaTeX more space
between metric title and value; (6) page break after the table of contents and chapter titles; (7) alert box left border
always solid; (8) remove the dots of the timeline; (9) remove the text width cap; (10) serif body font, larger, table body
unchanged; (11) LuaLaTeX table header height; (12) LuaLaTeX unit or type of a column on the next header line; (13)
LuaLaTeX ghost table header near "A 250-row profile table". All applied; see "Done in this session".

## Record: HG-S0 (answered, 2026-10-09)

- Repository public, Pages source = GitHub Actions: yes.
- ADR-0001 to ADR-0011: approve all, including (a) ZIP bundle with a JSON manifest and (b) semantic keys with
  typed values.
- Python 3.15: (a) keep experimental until wheels exist.
