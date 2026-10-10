<!-- Kickoff prompt, Part B, Phase M3: new figures. Source: prompts/scireport/scireport_plan.md. -->

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

Read plan Part B (M3) and the New figures list (items 1-18), the scientific-plotting skill and the scireport
mplstyle API. Implement the 18 figures as scireport pre-processor steps or as gzms plotting functions, whichever the data
volume allows: summaries only in the bundle (HEALPix counts at order 7 instead of the 1.3 M positions; pre-tallied vote counts
streamed from reliability.parquet in row groups). The list: sky density of all objects (order 7, Mollweide, objects per
deg2, log scale); mean n_sources per pixel plus the multiplicity bars; per-source footprint small multiples for the 30
crowd and expert sources; the train/val/test split map with refined pixels marked; objects per source and rows attached;
the 21x21 crowd overlap heat map; the pair separation histograms (existing figure, restyled); redshift distribution stacked
by redshift_source; size_arcsec distribution; max_offset_arcsec and nearest_object_arcsec distributions; total votes per
question; grades A-D per question; JSD and q-value distributions plus the shift curves; the 28 questions x 16 flags heat map;
co-occurrence heat maps for the focus pairs (promised in plan section 8.7, never built); expert AUC and T-type Spearman
bars; split balance; ingest kept fractions per source. gzms plotting functions get a style= keyword: report figures use
scireport.mplstyle_path(), paper figures keep astro.mplstyle and their current output must stay byte-identical. Redshift
sentinel: the objects table has 999 in 5,516 rows; draw the histogram without z = 999 and z < 0, put the excluded counts in
the caption, and flag this as a gate item (HG-M1) with the options (a) exclude and report counts, (b) show a separate bar,
(c) exclude silently. Every figure has alt text, a caption that states the denominator, a saved PNG and sidecar data; the W&B
rule applies if the code logs runs. Tests: a smoke test per figure from small fixtures, determinism (identical PNG bytes),
and sidecar data checks. Collect a contact sheet of all figures under logs/ for the gate. Done when: make check passes,
STATUS.md and CHANGELOG.md updated. No gate here; the figures are reviewed at HG-M1.

Use cheaper models for subagents performing simple tasks (haiku: copying, docstring passes, fixture regeneration, parity summaries, link checks; sonnet: porting individual plot functions, CSS-to-LaTeX components, reference pages, later gzms section builders). Every subagent prompt names the files and the acceptance tests.
