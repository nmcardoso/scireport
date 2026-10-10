<!-- Kickoff prompt, Part B, Phase M5: release gzms v1.1.0 (gate HG-M2). Source: prompts/scireport/scireport_plan.md. -->

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

Precondition: HG-M1 is answered in 2_dataset/STATUS.md and its decisions are implemented. Read plan Part B (M5). (1)
Bump pyproject.toml and CITATION.cff to 1.1.0 and write the CHANGELOG, DECISIONS and README updates. (2) Rebuild the release
(`make release`) and show that the data-product SHA256SUMS equal v1.0.0's (compare with the committed hashes; any difference is a
blocker to explain, not to hide). (3) Run `make check` (mypy strict, coverage at least 85 %), `make export-repo`, and a clean-room
check: extract the export into a fresh directory, `uv sync --locked` (scireport must come from GitHub), then `make report`, and
run the parity tool against the baseline. (4) Confirm CI is green on ubuntu and macOS. (5) Re-run `make check-skills` in 1_review.
Gate HG-M2 (blocking): v1.1.0 sign-off. Summarise: the checks above with counts, the changes since v1.0.0 (new report content,
figures, dependency), what is not changed (data hashes), and the files to inspect. The human pushes the tag; do not tag. Then
tell the user that scireport phase S8 (images extra) may start.

Use cheaper models for subagents performing simple tasks (haiku: copying, docstring passes, fixture regeneration, parity summaries, link checks; sonnet: porting individual plot functions, CSS-to-LaTeX components, reference pages, later gzms section builders). Every subagent prompt names the files and the acceptance tests.
