<!-- Kickoff prompt, Part A, Phase S6: documentation site. Source: prompts/scireport/scireport_plan.md. -->

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

Read plan D9 (Docs) and ADR-0009. Branch s6/docs. Build the Sphinx site (MyST, furo,
autodoc with napoleon, sphinxcontrib-typer for the CLI) with: a user guide and quickstart; the data-file specification
generated from the pydantic models and the frozen schemas; the error-code catalogue and the pre-processor reference
generated from code (drift-tested); the template and layout authoring guides; the mplstyle guide; an example gallery that
shows every example in both layouts as md, html and pdf links (built from `make examples`); the agent kit (skill download
as a zip, MCP setup page); the ADRs; the compatibility policy. Produce llms.txt and llms-full.txt (sphinx-llms-txt) and a
.md file per page (sphinx-markdown-builder) published next to the HTML, and check that they are linked from the index.
Make the docs workflow build with -W and publish to https://nmcardoso.github.io/scireport/ (Pages source must be GitHub
Actions; if the site is not live, tell the user which setting to change). Linkcheck passes. Verify that an agent can use the
site: have a haiku subagent create a small bundle and render it using only llms-full.txt, and record what it missed as
documentation fixes. Done when: make docs passes with -W, the Pages site is live, the llms files and per-page md exist,
STATUS.md and CHANGELOG.md updated. No gate.

Use cheaper models for subagents performing simple tasks (haiku: copying, docstring passes, fixture regeneration, parity summaries, link checks; sonnet: porting individual plot functions, CSS-to-LaTeX components, reference pages, later gzms section builders). Every subagent prompt names the files and the acceptance tests.
