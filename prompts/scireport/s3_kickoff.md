<!-- Kickoff prompt, Part A, Phase S3: the default and modern layouts, PDF engines, mplstyle, examples (gate HG-S1). Source: prompts/scireport/scireport_plan.md. -->

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

Read plan D3, D4, D7, D11, ADR-0004, ADR-0007, ADR-0010 and the MOSAICS design system in
/home/natan/repos/datex/datex/report/design (palette.py, css/tokens.css, base.css, components.css, print.css, fonts,
datex.mplstyle), its templates and tests (test_report_theme). Branch s3/layouts-pdf. Implement: (1) layouts/default/1/:
a faithful port of the MOSAICS look (design tokens, cover, chapter opener, TOC with target-counter, running header and
footer, all components) with HTML and LaTeX components; keep the WeasyPrint workarounds (no nested flex, a named cover
page, no break-inside on tables). (2) layouts/modern/1/: a more modern design, also with HTML and LaTeX components; use a
design-minded subagent pass and show alternatives rather than guessing. (3) The two PDF engines: weasyprint (lazy
import, exit code 3 with an install hint when pango is missing) and latex (latexmk with lualatex default, xelatex and
pdflatex selectable via render.latex_engine, fontspec with the vendored fonts, SOURCE_DATE_EPOCH, log parsing, pdflatex
falls back to TeX fonts with a warning). (4) Math: the mathtext SVG renderer (port of R/math.py) and the usetex option,
W6xx warnings. (5) Vendor the Inter and IBM Plex Mono subsets from datex with OFL.txt. (6) The mplstyle API: styles/
default.mplstyle and modern.mplstyle, scireport.mplstyle(), mplstyle_path(), palette(), figure(); font registration;
metadata-stripped deterministic PNG and PDF saving; the consistency test palette.yaml, tokens.css, mplstyle and LaTeX
colours. (7) kitchen-sink@1 and three examples under examples/ (a small dataset report, a metrics dashboard and a text-only
report), a real `make examples` rendering 3 examples x 2 layouts x (md, html, tex, pdf via weasyprint, pdf via latex with
lualatex, xelatex and pdflatex), uploaded as CI artifacts by the examples job. (8) Verify PDF byte determinism per engine
and record the result. (9) Decide the Windows WeasyPrint status from the CI evidence (green or documented as unsupported)
and record it in DECISIONS.md. Tests: golden html and tex per layout; canonical html comparison; compat corpus gains the
layout cases; PDF text-hash tests; plain-text extraction of each PDF checked against the md output. Gate HG-S1 (blocking,
visual sign-off): produce the MOSAICS demo PDF beside the scireport default PDF from both engines, and the modern design,
as files under examples/_out/ plus a short comparison table in STATUS.md. Options: (a) accept as is; (b) list defects to
fix before S4; (c) change the modern direction. Open a pull request and stop.

Use cheaper models for subagents performing simple tasks (haiku: copying, docstring passes, fixture regeneration, parity summaries, link checks; sonnet: porting individual plot functions, CSS-to-LaTeX components, reference pages, later gzms section builders). Every subagent prompt names the files and the acceptance tests.
