<!-- Kickoff prompt, Part B, Phase M2: the gzms report package. Source: prompts/scireport/scireport_plan.md. -->

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

Read plan Part B (M2), D3 and D6, the scireport skill, and the current report code in
2_dataset/gzms (the steps' f-string renderers built from _md_table, _md, _cell and _pct). Build the first section yourself
(use the main model), then use sonnet subagents for the others. (1) Create gzms/report/ with section builders that read the
tables the steps already write (Parquet/CSV under data/processed and the QA outputs) and return scireport values (tables with
column labels and units, numbers, text, metrics, status). They recompute nothing scientific. (2) Create the scireport
template gzms/report/template/ (template.yaml with fields, report.j2) whose md_file= chapters keep the 11 current file names
and H1 headings exactly, so `docs/` keeps its names. (3) Replace each step's f-string renderer with a call to
write_pages(...) and delete the obsolete helpers once nothing uses them. (4) docs data-model (README sync, check I14) and the
hand-written method.md stay unchanged; the PDF includes them as chapters through scireport text values. (5) The inventory
from M0 is the checklist: after each section, run `gzms report parity` and fix every loss. Use Appendix E of the plan (the
per-file content inventory) only as orientation; the committed inventory is authoritative. Tests: unit tests per section
builder on the small fixtures, a smoke test that builds all md pages from the fixtures, and the parity tool on the fixture
build. Done when: all 11 pages build from the pipeline tables with 0 parity losses on the fixtures, make check passes, the
data-product hashes are untouched, STATUS.md and CHANGELOG.md updated. No gate.

Use cheaper models for subagents performing simple tasks (haiku: copying, docstring passes, fixture regeneration, parity summaries, link checks; sonnet: porting individual plot functions, CSS-to-LaTeX components, reference pages, later gzms section builders). Every subagent prompt names the files and the acceptance tests.
