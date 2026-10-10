<!-- Kickoff prompt, Part A, Phase S2: templates, validation and the md, html and tex writers. Source: prompts/scireport/scireport_plan.md. -->

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

Read plan D3, D5, D11 (items 1, 3, 4 and 5 only; fragments are S5), ADR-0003, ADR-0005, ADR-0010 and the MOSAICS
engine in /home/natan/repos/datex/datex/report (components, filters, the single-pass outline and TOC, R/math.py,
tests/report_html.py). Branch s2/templates-validation-writers. Implement: (1) the template model (template.yaml with
fields, formats, compatible spec range; report.j2; optional per-format overrides) and the layout model (layout.yaml,
per-format document and components, options with defaults), loaded by name@version, by path, or through the entry-point
groups scireport.templates and scireport.layouts. (2) Jinja environments per format: SandboxedEnvironment,
StrictUndefined, format-aware escaping, the LaTeX-safe delimiters ((* *)), ((( ))), ((= =)) for LaTeX files only, and the
MOSAICS filters (int, float, share, bytes, duration, pct, ppm, sci, compact, missing, breakable). (3) the component
function layer (c.chapter, c.table, c.figure, c.metrics, c.details, ...) with Markdown, HTML and LaTeX component macros
for a minimal built-in test layout (the real layouts are S3). (4) the markup converter interface with the mistletoe
backend, restricted to a documented Markdown subset (GFM tables, math, footnotes as far as mistletoe supports them;
record the limits). (5) the validation engine: aggregated errors with stable codes (E1xx missing key, E2xx wrong kind,
E3xx table schema, E4xx asset or hash, E5xx version, W4xx unused key, W6xx math), key, JSON pointer, expected and found,
template file:line, difflib suggestions, --strict and --json, exit codes 0/1/2/3; the Jinja AST lint and the render-time
usage tracking (MOSAICS take/peek/leftovers). (6) writers: md (single file and the md_file= split plus index.md,
figures/*.png, alt text, generated-file header, math as $...$), self-contained html, and the standalone tex project
(report.tex, layout .sty, figures/ with PDF preferred over PNG, booktabs/longtable/siunitx tables), plus
render-manifest.json. (7) LaTeX escaping for # $ % & ~ _ ^ \ { } and Unicode. (8) the built-in generic@1 template that
renders any bundle from its outline. Tests: unit tests for every filter, component and error code (the error catalogue is
a table in code and in docs, drift-tested); a hypothesis property test on the escape function; golden md, html and tex for
a small bundle; byte-identical double renders; sandbox escape attempts rejected; a pdflatex/lualatex compile of the golden
tex marked integration. Done when: make check passes, the toolchain CI jobs are green, STATUS.md and CHANGELOG.md updated.
No gate.

Use cheaper models for subagents performing simple tasks (haiku: copying, docstring passes, fixture regeneration, parity summaries, link checks; sonnet: porting individual plot functions, CSS-to-LaTeX components, reference pages, later gzms section builders). Every subagent prompt names the files and the acceptance tests.
