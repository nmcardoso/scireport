<!-- Kickoff prompt, Part A, Phase S4: pre-processors. Source: prompts/scireport/scireport_plan.md. -->

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

Precondition: HG-S1 is answered in STATUS.md. Read plan D6, ADR-0006, and in
/home/natan/repos/datex/datex/report: R/plot.py (45 plot functions) and R/tables.py. Branch s4/preprocessors.
Implement: (1) the interface: the @preprocessor decorator (name, version, typed Port inputs and outputs), Context
(value, load_table via pyarrow, mplstyle, figure, save_figure with data, save_table, seed, log), pydantic parameter
validation from the signature, the registry with entry-point group scireport.preprocessors and register_preprocessor(),
name-only references in data files (module:func only with --allow-import), the DAG check before running, work-dir
outputs (the input bundle untouched unless --write-back), and the content-hash cache (name, version, parameters, input
hashes, scireport version, style hash). (2) The core catalogue: table_profile, bar, stacked_shares, histogram (samples or
pre-tallied counts), separation_histogram, funnel, density_scatter, metric_scatter, distribution, corner, pvalue_strip,
achieved_vs_target, duration_bars, split_marginals, split_balance, qq, pp, heatmap (new). (3) The astro catalogue
(scireport[astro]; astropy and astropy-healpix with matplotlib Mollweide, no hats or mocpy): sky_density (HEALPix counts or
ra/dec points), footprint, sky_grid, color_color, color_magnitude, number_counts, snr_magnitude, magnitude_residual,
zeropoint_offsets. Do NOT port the node timeline, throughput and traffic graph, the HTTP/cast/error ledgers, db_constraints
or photometry.assess; the image-comparison plots are S8. Each pre-processor ports the MOSAICS plot as a pure function, with a
fixture smoke test, a determinism test (two runs give identical PNG bytes and sidecar data) and a sidecar-data test (the
figure can be rebuilt from its data). Sonnet subagents may port individual plots; each prompt names the source function,
the target file and the three tests. Docstrings list the parameters and the output kinds. Done when: make check passes,
coverage stays at least 90 %, CI is green, STATUS.md and CHANGELOG.md updated. No gate.

Use cheaper models for subagents performing simple tasks (haiku: copying, docstring passes, fixture regeneration, parity summaries, link checks; sonnet: porting individual plot functions, CSS-to-LaTeX components, reference pages, later gzms section builders). Every subagent prompt names the files and the acceptance tests.
