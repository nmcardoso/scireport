# Instructions for Agents: scireport

When working in this repository, prioritize readability and maintainability over clever solutions. Before an
architectural change, read the ADRs in `docs/adr/`. If a change would contradict one, stop and ask.

## About the project

`scireport` is a standalone, data-centric scientific report engine. One **data file** (a "report bundle"), one
**template** (structure) and one **layout** (look) go in; Markdown, HTML, LaTeX and PDF come out. It is inspired
by the MOSAICS report engine in `/home/natan/repos/datex/datex/report`, but it has no dependency on datex.

Consumers are other projects (first the `2_dataset` subproject of the TUPAN monorepo), installed from the public
GitHub repository `https://github.com/nmcardoso/scireport`. Never rely on local paths for installs.

Things worth knowing before changing anything:

- **The data file is the contract.** The spec version is stored in every bundle, template and layout, and the
  package must keep reading every older minor version natively (ADR-0008). A change that alters how an old bundle
  renders is a bug, not a feature.
- **Built-in layouts and templates are frozen per version** (`layouts/default/1/`). A visual change is a new
  version directory, never an edit.
- **Errors are aggregated and coded.** Validation reports every problem at once, each with a stable code
  (`E1xx`, `W4xx`, ...), the key, the JSON pointer, expected and found values, the template `file:line` and a
  "did you mean" hint (ADR-0005).
- **Output must be deterministic.** Same inputs and versions give byte-identical `.md`, `.html`, `.tex` and PNG.
  PDF determinism is best-effort and recorded per engine.
- **Optional dependencies are imported lazily.** A missing system dependency (pango, TeX Live) exits with code 3
  and an install hint; it never raises a raw `ImportError`/`OSError` at the user.
- **Bundles hold summaries, not raw catalogues** (ADR-0001).

## Repository map

Planned layout (`docs/conventions.md`). Phase S0 ships only the skeleton; the rest arrives per phase (see `STATUS.md`).

- `scireport/`: flat-layout package
  - `spec/` data model, kinds, manifest, migrations, JSON Schemas
  - `bundle/` reader and writer (directory, ZIP, single file), hashes
  - `validate/` template lint and bundle validation, error catalogue
  - `render/` Jinja environments, components, filters, outputs (`md`, `html`, `tex`), PDF engines
  - `layouts/{default,modern}/1/`, `templates/{generic,kitchen-sink}/1/`
  - `styles/` mplstyle files; `preprocess/{core,astro}/` registered pre-processors
  - `agent/` packaged skill and MCP server; `cli/` Typer commands
  - `logging_utils.py`: byte-identical copy of the monorepo `python-logging` skill (never edit, never reformat)
- `tests/{unit,property,golden,integration,compat,fixtures}`, `examples/`, `docs/`, `docs/adr/`
- `.agents/`: this file, `agents/` (subagent definitions), `skills/` (`python-logging` copy; `scireport` is a
  symlink to the packaged skill). `.claude/{agents,skills}`, `AGENTS.md` and `CLAUDE.md` are symlinks into
  `.agents/`. Edit only inside `.agents/`.
- `STATUS.md`, `DECISIONS.md`, `CHANGELOG.md`, `README.md`

## Golden rules

1. **Backward compatibility.** See ADR-0008. Frozen JSON Schemas, frozen compat corpus (`tests/compat/`),
   semver for the Python API, stable error codes.
2. **Reproducibility.** Deterministic seeds, sorted ZIP entries with fixed timestamps, no wall-clock time in
   outputs (honour `SOURCE_DATE_EPOCH`), no absolute paths in outputs.
3. **Safety.** Templates run in a `SandboxedEnvironment` with `StrictUndefined`. Data files refer to
   pre-processors by registered name only; `module:func` needs `--allow-import`. ZIP readers reject zip-slip paths
   and enforce a size cap. Pickle is never read.
4. **Human gates are blocking.** When a plan step says HG-*, stop and write the gate question in `STATUS.md`
   so that it can be answered in one reading: purpose first (what changes downstream with each answer), every
   non-common term defined, evidence with units and denominators, labelled options (a), (b), (c) with
   consequences, a recommendation and why, and self-contained wording.
5. **Never commit** `.env`, `.mcp.json`, tokens, `docs/_build/`, example outputs, or PDFs of papers. Never copy
   a `.mcp.json` from another repository (the monorepo one holds a token).
6. **Licences.** The package is GPL-3.0-only. Vendored fonts (Inter, IBM Plex Mono) are OFL: keep `OFL.txt` next
   to them.
7. **Scope discipline.** Port from MOSAICS only what the plan lists. Runtime-specific pieces of datex (node
   timeline, HTTP ledgers, `photometry.assess`, ...) are not ported.

## Python standards

- Python >= 3.12, `uv`: `uv add <pkg>` (latest versions become the lower bounds), `uv run <cmd>`. Commit
  `pyproject.toml` and `uv.lock`.
- Matrix: Python 3.12 to 3.15 on Linux only; macOS and Windows are not built, tested or supported. Keep the code
  portable anyway: use `pathlib`; write text with `newline='\n'`; never rely on symlinks in tests.
- `ruff` (line length 100, `indent-width = 2`, single quotes), `mypy --strict`, `pytest`, coverage >= 90 %.
- Logging: stdlib `logging` through `scireport.logging_utils` (see the `python-logging` skill). Configure it only
  in CLI entry points, never at import time. Never `print()`; `typer.echo` only for a command's result.
- Configuration and manifests are validated by pydantic models; paths resolve from the package, never from the
  working directory.

### General Programming Style Rules

- Two spaces for indentation. Single quotes wherever possible.
- Every function, class and method gets type hints and a NumPy-style docstring.
- Prefer small pure functions. Side effects (file system, subprocesses) live at the edges.
- Private functions and methods come after public ones.
- Errors are specific exception classes carrying an error code; never a bare `Exception`.
- No dead code, no commented-out code, no TODO without an issue or a STATUS entry.

### Docstring Style Rules

- NumPy style: summary line, blank line, optional description, `Parameters`, `Returns`, `Raises`.
- A multi-line docstring starts on the line *after* the opening `"""`.
- Say what the thing actually does, in plain language. Accuracy over formality.
- Document units, shapes and the meaning of `None`.

## Testing

Unit tests for parsers, validators and filters; property tests (hypothesis) for LaTeX escaping and key
canonicalisation; golden tests for every output format; a compat corpus per spec version; integration tests
(marker `integration`) for PDF engines and pandoc. Integration tests skip when a toolchain is missing, unless
`SCIREPORT_REQUIRE_TOOLCHAIN=1` (set by the dedicated CI jobs), in which case they fail.

## Git workflow

- One branch per phase (`s1/spec-and-bundle`), Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `ci:`,
  `chore:`), small commits, never rewrite published history. Open a pull request at every human gate.
- Release tags are pushed only after gate sign-off.
- Commits carry the co-author trailer given by the harness.

## Communication

- Update `STATUS.md` at the end of every session: phase, done, next, blocked, questions.
- Record decisions in `DECISIONS.md` (date, decision, rationale, gate or approver). Design decisions that shape the
  architecture are ADRs in `docs/adr/`.
- When uncertain about a design judgement, record both options and ask. Do not decide silently.

## Subagent and model policy

Use the cheapest model that can do the task. **haiku** (`explore`, `docstring`): copying files and fonts, docstring
passes, fixture regeneration, link checks. **sonnet**: porting individual plot functions, CSS-to-LaTeX components,
reference doc pages. **Main model**: spec, validation, render core, compatibility, layout design, MCP design, gate
write-ups. Every subagent prompt names the files and the acceptance tests.

## Definition of done (any task)

`make check` passes (ruff format and lint, mypy strict, pytest with coverage). Docs build with `-W`. `STATUS.md` and
`CHANGELOG.md` are updated. Any output format touched has a golden test.
