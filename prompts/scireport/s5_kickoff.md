<!-- Kickoff prompt, Part A, Phase S5: pandoc, LaTeX fragments, full CLI, MCP server and skill. Source: prompts/scireport/scireport_plan.md. -->

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

Read plan D9, D11 (item 2), D12, ADR-0009, ADR-0010, ADR-0011. Branch s5/cli-mcp-skill-pandoc. Implement:
(1) Pandoc (scireport[pandoc], pypandoc-binary, lazy import): render.markup_engine mistletoe|pandoc with no automatic
switching, pandoc version in render-manifest.json and a warning when it differs from the bundle's record; the bibliography
kind with [@key] (tex via biblatex/biber, md and html via citeproc with optional CSL; without pandoc, an E5xx with an
install hint); docx, odt and epub from the rendered html or md with an optional reference.docx; golden outputs for both
markup engines and a documented list of differences. (2) LaTeX fragment export: `scireport export tex BUNDLE --keys ...
-o DIR` writing tab_<key>.tex, fig_<key>.tex and numbers.tex (one \newcommand per number value, CamelCase with a configurable
prefix, a collision is an error); a test compiles a stub document that inputs every fragment. (3) The full Typer CLI: render,
validate, pack, unpack, inspect, new, preprocess, export tex, templates, layouts, preprocessors, spec, mplstyle, agent,
mcp serve; exit codes 0/1/2/3; --json on the commands agents use; public __all__ and an API snapshot test. (4) The MCP server
(scireport[mcp], official mcp SDK, FastMCP, stdio): tools list_templates, describe_template, list_layouts,
list_preprocessors, describe_preprocessor, spec_schema, inspect_bundle, validate_bundle, render_bundle, error_help;
resources are the skill pages; file access restricted to --root; `scireport agent mcp-config` prints a .mcp.json snippet.
Verify the SDK API with Context7 first; test with the SDK's in-memory client. (5) The skill in scireport/agent/skill/
scireport/: SKILL.md (frontmatter: name equals the folder, description at most 1024 characters) and references/ data-file.md,
python-api.md, cli.md, templates-and-layouts.md, preprocessors.md, mplstyle.md, errors.md, recipes.md (with the recipes
"Markdown for LLMs plus one PDF for humans" and "CI"); the tables are generated from code by `make skill` and drift-tested;
`scireport agent install-skill --dest DIR [--check]`. Keep the packaging test that the wheel and sdist contain the skill.
When done, tag and push v1.0.0rc1 (a pre-release; no gate, record it in STATUS.md). Done when: make check passes, CI is
green, the skill passes the monorepo frontmatter rules (run 1_review's `make check-skills` against it from the monorepo),
STATUS.md and CHANGELOG.md updated. No gate.

Use cheaper models for subagents performing simple tasks (haiku: copying, docstring passes, fixture regeneration, parity summaries, link checks; sonnet: porting individual plot functions, CSS-to-LaTeX components, reference pages, later gzms section builders). Every subagent prompt names the files and the acceptance tests.
