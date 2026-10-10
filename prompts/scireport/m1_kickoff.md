<!-- Kickoff prompt, Part B, Phase M1: install scireport, skills, CI and ignore rules. Source: prompts/scireport/scireport_plan.md. -->

You are working in the TUPAN monorepo (/home/natan/repos/phd) on subproject 2_dataset/ (P2, package `gzms`),
migrating its generated reports to the `scireport` package. The binding plans are prompts/scireport/scireport_plan.md
(Part B and decisions D1-D13) and, for the existing pipeline, prompts/2_dataset_plan.md. Read .agents/AGENTS.md,
2_dataset/STATUS.md and 2_dataset/DECISIONS.md first, then the plan sections named below. Work on branch
p2/reports-scireport. Use the logging skill for all code and the scientific-plotting skill for every figure (draw
inside the style context; functions take ax=None, save_path=None, show=False and return ax; every figure is saved with
its data). Rules that bind this whole migration: scireport is installed only from the public GitHub repository (no
local path, file:// or editable entry in pyproject.toml or uv.lock); the data products of gzms 1.0.0 must stay
byte-identical (SHA256SUMS); reports read the tables the pipeline steps already write and recompute nothing
scientific; numbers shown in reports come from code; the Markdown figure PNGs (docs/figures/) and the PDF
(docs/*.pdf) are git-ignored. Never invent a number, column or citation. Stop at human gates, writing each gate
question in 2_dataset/STATUS.md per monorepo golden rule 3 (purpose first, terms defined, evidence with units and
denominators, labelled options with consequences, a recommendation, self-contained). End every session by updating
STATUS.md (done, next, blocked, questions), CHANGELOG.md and DECISIONS.md. Open a pull request at every gate.

Read plan Part B (M1) and D9. (1) Add the dependency with `uv add "scireport[pdf,astro] @
git+https://github.com/nmcardoso/scireport@v1.0.0"`, set [tool.hatch.metadata] allow-direct-references = true, run `uv
lock`, and verify with grep that pyproject.toml and uv.lock contain no `path =`, `file://` or editable entry. Local editable
installs are allowed only in a scratch venv. gzms requires Python <3.14: confirm scireport resolves there. (2) Install the
skill into the monorepo: `uv run scireport agent install-skill --dest ../.agents/skills`, then run `scireport agent
install-skill --check` as a drift test in 2_dataset's tests (skipped gracefully when the monorepo layout is absent, as in the
exported repository), run `make check-skills` in 1_review, and add a scireport entry to the skills list of
.agents/AGENTS.md (when to use it: any generated report; Markdown for LLMs plus one PDF for humans). (3) CI: add the apt
packages libpango-1.0-0, libpangoft2-1.0-0 and libharfbuzz-subset0 on ubuntu and `brew install pango` on macOS to both
2_dataset/.github/workflows/ci.yml and the monorepo mirror .github/workflows/p2-dataset.yml (keep them in step), and
verify that every action tag exists (astral-sh/setup-uv has no floating major tag: pin an exact release; the current
workflows use @v10, which does not exist). (4) .gitignore rules /docs/*.pdf and /docs/figures/ in 2_dataset. (5) A smoke
test that renders a tiny bundle with scireport to md and, when pango is present, to PDF. Done when: uv sync --locked works
from a clean venv, make check passes, CI is green on ubuntu and macOS, STATUS.md and CHANGELOG.md updated. No gate.

Use cheaper models for subagents performing simple tasks (haiku: copying, docstring passes, fixture regeneration, parity summaries, link checks; sonnet: porting individual plot functions, CSS-to-LaTeX components, reference pages, later gzms section builders). Every subagent prompt names the files and the acceptance tests.
