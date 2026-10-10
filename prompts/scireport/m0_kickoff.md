<!-- Kickoff prompt, Part B, Phase M0: preconditions, baseline and the parity tool. Source: prompts/scireport/scireport_plan.md. -->

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

Preconditions (verify, and stop if any fails): P2 gate HG5 is closed in 2_dataset/STATUS.md; scireport v1.0.0 is
tagged and public at https://github.com/nmcardoso/scireport (check with `git ls-remote --tags`); the working tree is
clean on main. Create branch p2/reports-scireport. Read plan Part B (M0) and the facts about the current reports. (1)
Snapshot the current docs/*.md (the 11 generated reports, method.md and data_model/*.md) into a git-ignored baseline folder
(record its path in DECISIONS.md and add it to .gitignore). (2) Build the content inventory of the baseline: for each file,
its H1 and heading list, every table (header and row count) and the count of numeric tokens; write it to
tests/fixtures/report_inventory.yaml (committed). (3) Implement `gzms report parity BASELINE NEW`: compares every baseline
table (header and rows, tolerant only to the documented column re-ordering and formatting) and every numeric token against
the new docs, and writes a parity report (counts of matched, changed, missing) to logs/; an unexplained loss is an error.
Run it against the baseline itself to prove it reports 0 losses. Add the tool as a Typer command and a make target, with
unit tests on small fixtures (a dropped row, a changed number, a re-formatted number, a renamed heading). Done when: make
check passes, STATUS.md and CHANGELOG.md updated. No gate.

Use cheaper models for subagents performing simple tasks (haiku: copying, docstring passes, fixture regeneration, parity summaries, link checks; sonnet: porting individual plot functions, CSS-to-LaTeX components, reference pages, later gzms section builders). Every subagent prompt names the files and the acceptance tests.
