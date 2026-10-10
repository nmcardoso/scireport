<!-- Kickoff prompt, Part A, Phase S1: spec models and bundle I/O. Source: prompts/scireport/scireport_plan.md. -->

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

Precondition: STATUS.md shows HG-S0 answered. If it is still open, stop. Set the status of the approved ADRs to
Accepted. Re-run `uv pip compile pyproject.toml --all-extras --python-version 3.15 --only-binary :all:`; if Python 3.15
wheels now exist, remove continue-on-error from the 3.15 jobs and record it in DECISIONS.md.

Read plan D1, D2, D8 and ADR-0001, ADR-0002, ADR-0008. Branch s1/spec-and-bundle. Implement: (1) scireport/spec/:
pydantic models for the manifest blocks (scireport, meta, render, outline, values, preprocess, provenance), every v1.0
kind (text, number, bool, date, list, mapping, table, figure with required alt text, image, math, code, metrics,
status, alert, flow, attachment), key rules ([a-z0-9_-]+ dotted segments), and the canonicalisation of bare JSON
scalars, lists and objects into typed envelopes. (2) scireport/bundle/: reader and writer for the directory form, the
ZIP form and the single-file form; sha256 and bytes for every asset; byte-reproducible ZIPs (sorted entries, fixed 1980
timestamps, STORED for already-compressed media); zip-slip rejection and a size cap; lazy asset reads; YAML accepted
only for hand-authored directories. (3) the Report builder API (add values, tables from pyarrow or optional pandas,
figures with sidecar data, attachments; write to a bundle). (4) JSON Schemas generated from pydantic into
spec/schemas/data-1.0.schema.json with a drift test. (5) the migration framework (spec/migrations/, pure dict-to-dict,
a no-op 1.0 baseline) and the E5xx behaviour for a newer minor version. (6) CLI commands spec, pack, unpack, inspect.
Start the compat corpus: tests/compat/spec-1.0/<case>/ with at least a minimal, a full-kinds and a text-only bundle.
Tests: unit tests per kind; hypothesis property tests for key canonicalisation and pack/unpack round trips; ZIP
determinism (two writes give identical bytes); zip-slip and size-cap rejection; schema drift; Windows-safe paths and
newline='\n'. Done when: make check passes, CI is green on the matrix, STATUS.md and CHANGELOG.md are updated. No
gate; open a pull request and continue to S2 after merge.

Use cheaper models for subagents performing simple tasks (haiku: copying, docstring passes, fixture regeneration, parity summaries, link checks; sonnet: porting individual plot functions, CSS-to-LaTeX components, reference pages, later gzms section builders). Every subagent prompt names the files and the acceptance tests.
