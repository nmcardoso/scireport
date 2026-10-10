<!-- Kickoff prompt, Part A, Phase S7: freeze and release v1.0.0 (gate HG-S2). Source: prompts/scireport/scireport_plan.md. -->

You are working on the standalone package `scireport` in /home/natan/repos/scireport (GitHub:
https://github.com/nmcardoso/scireport), a data-centric scientific report engine built for the TUPAN monorepo.
The binding plan is prompts/scireport/scireport_plan.md in the monorepo (/home/natan/repos/phd); the architecture
decisions are docs/adr/ in the scireport repository (D1-D9, D11, D12 of the plan are ADR-0001 to ADR-0011; D10 and
D13 are in docs/conventions.md). Read .agents/AGENTS.md, STATUS.md and DECISIONS.md of the scireport repository
first, then the plan sections named below. Use the logging skill (scireport.logging_utils) for all code, never
print(). Code style is datex style (2-space indent, single quotes, ruff line length 100, numpy docstrings, mypy
strict). Add dependencies with `uv add` (latest versions become the lower bounds). Verify third-party APIs
(typer, pydantic, jinja2, mistletoe, weasyprint, mcp, ...) with Context7 before coding; never invent API calls,
CSS properties, tlmgr package names or error codes. Work on one branch per phase, small Conventional Commits with
the co-author trailer, push the branch, and check the CI matrix (gh is not logged in on this machine: ask the user
to run `gh auth login`, or poll the unauthenticated GitHub API sparingly, 60 requests/hour). Never copy or commit a
.mcp.json. Stop at human gates, writing each gate question in STATUS.md per monorepo golden rule 3 (purpose first,
terms defined, evidence with units and denominators, labelled options with consequences, a recommendation,
self-contained). Backward compatibility (ADR-0008) is a golden rule: anything that changes how a frozen spec,
template or layout renders needs a new version. End every session by updating STATUS.md (done, next, blocked,
questions), CHANGELOG.md and DECISIONS.md.

Read plan D8, D13 and ADR-0008. Branch s7/release. Freeze the compat corpus: make tests/compat/spec-1.0/ complete
(every kind, both layouts, every output format, both markup engines) with FROZEN.sha256, a `make compat` target and a CI
check that fails when a fixture or output drifts. Check the API snapshot, the frozen JSON Schema and the frozen layouts
(layouts/default/1, modern/1). Finish the CHANGELOG, README (install from GitHub, system dependencies, quickstart) and
CITATION.cff. Run the clean-room check: a fresh `uv venv`, then `uv pip install "scireport[pdf,astro] @
git+https://github.com/nmcardoso/scireport@<tag>"`, then render an example, on all three OSes through release.yml; fix
anything the matrix reveals. Confirm every job of the CI matrix is green on main, or is documented as experimental or
unsupported with a dated DECISIONS.md entry. Prepare the release but do NOT push the v1.0.0 tag. Gate HG-S2 (blocking):
release sign-off. Summarise in STATUS.md: matrix results with job counts, the compat corpus size and hashes, the known
limits (PDF determinism per engine, Windows WeasyPrint status, Python 3.15 status), the optional question whether to archive
the software with a Zenodo DOI (options: (a) yes, now; (b) after the 2_dataset migration; (c) no), and a recommendation. The
human pushes the tag.

Use cheaper models for subagents performing simple tasks (haiku: copying, docstring passes, fixture regeneration, parity summaries, link checks; sonnet: porting individual plot functions, CSS-to-LaTeX components, reference pages, later gzms section builders). Every subagent prompt names the files and the acceptance tests.
