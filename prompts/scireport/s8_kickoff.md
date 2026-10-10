<!-- Kickoff prompt, Part A, Phase S8 (optional, after M5): the images extra. Source: prompts/scireport/scireport_plan.md. -->

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

Precondition: Part B is finished (HG-M2 answered) and scireport v1.0.0 is released. Read plan D6 (images) and
/home/natan/repos/datex/datex/report R/plot.py (the 15 compare_stamps plots) and the compare_stamps metrics module. Branch
s8/images-extra. Add the optional extra scireport[images] (declare it with `uv add --optional images ...`) with the
compare_stamps plots and metrics as pre-processors, following the S4 rules (pure functions, fixture smoke test,
determinism test, sidecar-data test) and the ADR-0006 interface. This is a minor release: bump to v1.1.0, keep spec 1.0
(only pre-processors are added), extend the compat corpus without touching frozen fixtures, update the docs and the skill
references, and run the clean-room install with the new extra. Do NOT push the tag: the human decides (gate HG-S3, release
sign-off, written like HG-S2).

Use cheaper models for subagents performing simple tasks (haiku: copying, docstring passes, fixture regeneration, parity summaries, link checks; sonnet: porting individual plot functions, CSS-to-LaTeX components, reference pages, later gzms section builders). Every subagent prompt names the files and the acceptance tests.
