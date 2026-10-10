# STATUS

**Phase:** S6 (documentation site) implemented on `s6/docs` and merged into `main`. The site is at
<https://nmcardoso.github.io/scireport/> (the Pages source is already GitHub Actions). Next phase: S7 (1.0 freeze).
No gate. **Still open: the HG-S1 layout changes** (see "Questions").

## Done in S6

- **Site** (Sphinx, MyST, furo, autodoc + napoleon, sphinxcontrib-typer): quickstart, user guide, data-file
  specification, command line, Python API, error codes, pre-processor reference, outputs, markup, pandoc, export,
  template / layout / matplotlib-style authoring guides, example gallery, agent skill and MCP pages, compatibility
  policy, ADRs, conventions, changelog.
- **Generated from code and drift-tested**: `scireport.agent.skillgen` now also fills `<!-- generated:NAME -->` blocks in
  `docs/` pages (and its test fails when one is stale). New generators: `error-catalogue`, `preprocessor-reference`,
  `schema-files`, `exceptions`. `tests/unit/test_error_docs.py` and the MCP integration test check the error and
  tool tables; `tests/unit/test_docs_quickstart.py` runs the quickstart's code; `tests/unit/test_docs_site.py` checks
  the gallery page against `examples/render_all.py`, the skill zip and the check script.
- **For models**: `llms.txt` (links to the `.md` pages), `llms-full.txt` (built from the page sources, so reference
  content is literal text; autodoc and typer sections are fenced off with `llms-txt-ignore`), a Markdown twin of every
  page, `downloads/scireport-skill.zip` (reproducible), `schemas/data-1.0.schema.json` (the schema's `$id` now
  resolves). The index links all of them; `docs/check_site.py` (run by `make docs`) verifies the lot.
- **Workflow**: `docs.yml` builds the examples (pango + TeX Live), then `make docs SITE=_site
  DOCS_ARGS=--require-gallery`, and deploys from `main` only (pull requests just build). `ci.yml`'s `docs` job runs
  `make docs` and linkcheck.
- **CI fix** (found while checking the matrix): `lint`, `test` and `lowest` failed on `main` since S5 because they
  installed no extras; they now use `--all-extras`.

## Verification (local, 2026-10-10)

| Check | Result |
|---|---|
| `ruff format --check`, `ruff check`, `mypy --strict scireport tests` | pass |
| `pytest -m "not integration"` with coverage | 1558 passed, coverage 94.94 % (gate 90 %) |
| `make examples` then `make docs DOCS_ARGS=--require-gallery` (`-W`, HTML and Markdown builds, site check) | pass; 34 pages, 7.8 MB with the gallery |
| `make docs-linkcheck` | pass (one permanent redirect, `modelcontextprotocol.io`) |
| Usability test: a haiku subagent given only `llms-full.txt` | built a bundle (title, 3 numbers, math, table, styled figure) and rendered md and html; fixed a broken data file from the error codes. Its own gap list was empty, so it is weak evidence; my scan of the file found 96 unresolved MyST `{doc}` roles, now plain links, and one `{ref}`, fixed |

## Not verified yet

- **GitHub Actions has not run on `s6/docs` or on `main` since the CI fix**, so the `docs` workflow with TeX Live and
  the gallery, the corrected `lint`/`test`/`lowest` jobs, Python 3.13 to 3.15 and the new `docs` CI job are untested on
  GitHub. `gh` is not logged in here; results are read from the unauthenticated API after the push.
- The haiku test shows the site is sufficient for one small task, not for every feature; the PDF and pandoc pages were
  checked by the sonnet authors running their examples, not by a second reader.

## Next

1. S7: freeze (spec, layouts, compat corpus), final `v1.0.0`.
2. Apply the HG-S1 layout changes before S7 freezes the layouts (the gallery then shows the final look).
3. Triage the findings below.

## Findings from writing the docs (code or skill, not fixed: out of S6 scope)

- `scireport pack` pins a named layout but not an absent `render.layout`; `n_rows` is recorded only by
  `Report.add_table`, so `inspect` of a packed hand-written table prints `? rows`.
- Piping a command into `head` logs `[Errno 32] Broken pipe` as an error.
- Spec-stage errors go to stderr as log lines, template-stage issues print as plain lines on stdout; validation stops at
  the spec stage, so "every problem at once" holds per stage.
- `render.layout` / `render.template` in a data file reject paths (`E205`); a path layout works only from the CLI.
- `E706` ends in "(expected None, found tex)"; `E804` reports the template line, not the layout file.
- `assets` in `layout.yaml` is copied only by the LaTeX writer; a layout cannot ship its own fonts (`E703`).
- `Report.add_figure` renders with `tight=False`, `save_figure` defaults to `tight=True`; `scireport.figure()` sets no layout
  engine, so axis labels can clip unless the author calls `fig.set_layout_engine('constrained')`. WeasyPrint warns about
  `overflow-x` in `minimal.css`.
- `c.number` inside `{% filter md %}` breaks LaTeX (the tie becomes `\textasciitilde{}`); the skill does not say so. The
  skill's `Report.write` example omits `overwrite=True` (`E410`).
- Kind and folder pairing of assets is not enforced (only the five folders and the suffix).
- `manifest_json_schema()` refuses any version but the current one, so after a bump nothing checks that the models still
  generate the frozen `data-1.0.schema.json`. Error-code meanings are protected by review only (no stored titles, no
  retired-code list). ADR-0008 says "the `default` alias points to the latest" while in code `default` is a layout name.
  ADR-0005 omits E6xx to E9xx. The palette table prints `Cmaps`, `Fonts`, `Page` as bare type names.
- Whether `scireport.preprocess` and `scireport.styles` are covered by the semver promise, whether CLI flags and `--json`
  shapes are part of the contract, and whether a release may add warnings that break `--strict` CI are undecided;
  `compatibility.md` says what it assumes.
- **Release state mismatch:** the previous STATUS said `v1.0.0rc1` was tagged, but `git ls-remote --tags origin` lists no tags
  and `scireport.__version__` / `pyproject.toml` still say `0.1.0.dev0`, so the site shows 0.1.0.dev0.

## Questions

- **HG-S1 layout changes are still not applied** (13 defects of `default@1`, redesign of `modern@1`). The S6 kickoff did
  not ask for them; layouts freeze at S7, so nothing is lost yet, but a look change after the final release needs
  `default@2`. Tell me when to do it; my recommendation is before S7.
- **Is `v1.0.0rc1` meant to exist?** See "Release state mismatch". I did not create a tag (release tags follow gate sign-off).
- Review items from S5 (DECISIONS, rows of 2026-10-10) are unchanged: `numbers.tex` naming, citations read only in Markdown
  `text` values, a literal `has('x')` / `data.x` in a template counts as a read (E106).
- The pull request is not opened (`gh auth login` is needed); the branch is merged locally.

## Record: HG-S1 (answered; its changes are pending)

The answer of 2026-10-10 asked: change the `modern@1` design to match the TUPAN publication plan report, including its
font; and for `default@1`: (1) WeasyPrint full-width header rule; (2) more space between header and content; (3) LuaLaTeX
less space between H1 and its rule; (4) LuaLaTeX table of contents spacing and right-aligned page numbers; (5) LuaLaTeX more
space between metric title and value; (6) page break after the table of contents and chapter titles; (7) alert box left
border always solid; (8) remove the dots of the timeline; (9) remove the text width cap; (10) serif body font, larger,
table body unchanged; (11) LuaLaTeX table header height; (12) LuaLaTeX unit or type of a column on the next header line;
(13) LuaLaTeX ghost table header near "A 250-row profile table". The full text is in git history of this file (S4).

## Record: HG-S0 (answered, 2026-10-09)

- Repository public, Pages source = GitHub Actions: yes.
- ADR-0001 to ADR-0011: approve all, including (a) ZIP bundle with a JSON manifest and (b) semantic keys with
  typed values.
- Python 3.15: (a) keep experimental until wheels exist.
