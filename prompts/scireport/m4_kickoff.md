<!-- Kickoff prompt, Part B, Phase M4: the report CLI, make report and the PDF (gate HG-M1). Source: prompts/scireport/scireport_plan.md. -->

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

Read plan Part B (M4). Implement `gzms report` and `make report` to write docs/*.md (the 11 current files, same
names and H1s) plus docs/dataset_overview.md, docs/index.md, docs/figures/*.png and docs/gzms-report.pdf. PDF order: cover,
metrics, TOC, overview, method, registry and licences, ingest, cross-match and the RC3 study, splits, taxonomy, labels,
co-occurrence, QA and the divergence study, data-model appendix, CSV attachments. Choose the layout and PDF engine and record
them (WeasyPrint default; LaTeX as a fallback). Set seeds and SOURCE_DATE_EPOCH so a rebuild gives byte-identical md and PNG
files (the PDF is best-effort). Update README.md (make report, pango, the install-from-GitHub requirement), the CLI help and the
tests (unit, a full-fixture build, parity on the fixtures, a rebuild-determinism test). Run the real build on the full data and
the parity tool against the M0 baseline. Gate HG-M1 (blocking). Write it so that it can be answered in one reading: (1)
parity: counts of tables and numeric tokens matched, changed and missing out of the baseline totals, with every unexplained
loss listed and the file where to inspect it; (2) the figure set: the contact sheet path, the 18 figures with a one-line
purpose each, and which you recommend to drop or add; (3) the redshift sentinel policy with options (a), (b), (c) from M3 and
the counts (5,516 of the objects rows have z = 999); (4) the report figure style: scireport default vs modern vs astro.mplstyle,
with a recommendation; (5) the PDF engine and layout. Open a pull request and stop.

Use cheaper models for subagents performing simple tasks (haiku: copying, docstring passes, fixture regeneration, parity summaries, link checks; sonnet: porting individual plot functions, CSS-to-LaTeX components, reference pages, later gzms section builders). Every subagent prompt names the files and the acceptance tests.
