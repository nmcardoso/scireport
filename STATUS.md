# STATUS

**Phase:** S0 (repository, tooling, CI, ADRs). **Gate HG-S0: open (waiting for the human).**

## Done in S0

- Local repository `/home/natan/repos/scireport` on branch `main`, remote `origin` =
  `git@github.com:nmcardoso/scireport.git` (the empty public repository already exists).
- `uv` project (GPL-3.0-only), dependencies and extras locked (`uv.lock`), ruff, mypy strict, pytest (coverage
  gate 90 %), pre-commit, Makefile.
- Agent files: `.agents/AGENTS.md`, copied subagents (`explore.md` adapted), `python-logging` skill copy,
  placeholder packaged `scireport` skill; symlinks `AGENTS.md`, `CLAUDE.md`, `.claude/agents`, `.claude/skills`.
- ADR-0001 to ADR-0011 (proposed), `docs/conventions.md`, Sphinx skeleton (HTML, `llms.txt`, per-page Markdown and
  linkcheck all build locally).
- CI: `ci.yml` (lint, test matrix, lowest, pdf-weasyprint, pdf-latex, pandoc, examples, docs), `docs.yml`,
  `release.yml`.
- Local verification: `make check` and `make docs` pass; the LaTeX and pandoc smoke tests pass here; the WeasyPrint
  smoke test passes with the HarfBuzz-Subset warning ignored.

## Not verified yet

- The GitHub Actions matrix has not run: nothing is pushed until the first push (see Next).
- Windows and macOS (no local access), WeasyPrint on Windows (MSYS2), Python 3.14/3.15, TeX Live package list.

## Next

1. Commit on `main`, push, read the first CI results, fix what the matrix reveals (TeX package list, MSYS2 paths,
   3.15 wheels) and record the outcome in `DECISIONS.md`.
2. In the repository settings: **Pages source = GitHub Actions**.
3. Answer the gate below. Then start S1 on branch `s1/spec-and-bundle`.

## HG-S0 (blocking): approve the architecture and the repository

**Purpose.** The ADRs fix the data-file format, the key structure, the template/layout split, the output engines,
validation, pre-processors, the plotting style, backward compatibility, the agent kit, LaTeX and pandoc. Every later
phase (S1 to S7) and the migration of the `2_dataset` reports are built on them; changing one later costs a
major spec version (ADR-0008). The gate also confirms that the infrastructure (public repository, CI, Pages) is ready.

**What I need from you**

1. Confirm the repository `https://github.com/nmcardoso/scireport` is public and set **Settings -> Pages ->
   Source = GitHub Actions**.
2. Review ADR-0001 to ADR-0011 in `docs/adr/` (status *Proposed*). The two choices with the largest downstream
   effect:
   - (a) **ZIP bundle with a JSON manifest** (ADR-0001) versus a single HDF5 file. Bundle: stdlib only, readable
     by agents and git, hashes for integrity; HDF5: efficient for large arrays that a report does not carry.
     *Recommendation: (a) bundle.*
   - (b) **Semantic keys with typed values** (ADR-0002) versus type-scoped keys such as `tables.*`. Semantic keys:
     a table can become a figure without renaming; type-scoped: simpler lookup, but renames break templates and
     stored bundles. *Recommendation: semantic keys.*
3. Decide the Python 3.15 policy (3.15 jobs are currently experimental because `pyyaml` has no cp315 wheel on
   PyPI as of 2026-10-09): (a) keep experimental until wheels exist, (b) make 3.15 required and build from source
   in CI, (c) drop 3.15 from the matrix. *Recommendation: (a); it keeps the signal without blocking releases.*

Approving the ADRs changes their status from *Proposed* to *Accepted* (I will do this edit after your answer).
