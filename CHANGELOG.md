# Changelog

All notable changes are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/) and the
project uses [semantic versioning](https://semver.org/) for the Python API and `MAJOR.MINOR` for the data-file
specification (ADR-0008).

## [Unreleased]

### Added (phase S3)

- Layouts `default@1` (the MOSAICS look: navy cover with a grid and a circle, chapter opener, table of contents with `target-counter` page numbers, running header and footer, every component) and `modern@1` ("Signal": vermilion cover band, giant chapter numerals, heavy rules, rule-only tables), each with Markdown, HTML and LaTeX components, a `palette.yaml` and a matplotlib style. `default@1` is now the default layout.
- PDF output: `scireport render -f pdf` with the `weasyprint` engine (lazy import; WeasyPrint prints the self-contained HTML) or the `latex` engine (`latexmk` with LuaLaTeX, XeLaTeX or pdfLaTeX; fontspec with the vendored fonts; pdfLaTeX falls back to TeX fonts with `W901`). Options `--pdf-engine` and `--latex-engine`, and `render.pdf_engine` / `render.latex_engine` in the data file. A missing system dependency exits with code 3 (`E901`) and an install hint; LaTeX errors are `E902` with `file:line` from the log. Reproducible dates and ids (`SOURCE_DATE_EPOCH`).
- Math: the `usetex` renderer (real LaTeX through matplotlib) next to `mathtext`; `W602` when LaTeX rejects an expression.
- Vendored Inter and IBM Plex Mono subsets with `OFL.txt` (`scireport/styles/fonts/`), inlined in HTML and copied into the LaTeX project.
- Style API: `scireport.mplstyle()`, `mplstyle_path()`, `palette()`, `figure()`, `scireport.styles.save_figure()` and `figure_bytes()` (PNG, PDF and SVG with no run-varying bytes); a consistency test ties `palette.yaml`, `tokens.css`, the LaTeX colours and the matplotlib style together.
- Built-in template `kitchen-sink@1` and `scireport.demo.kitchen_sink_bundle()`; three examples under `examples/` and `make examples` (3 examples x 2 layouts x md, html, tex, a WeasyPrint PDF and a PDF from each of three TeX engines), uploaded as artifacts by the `examples` CI job; `examples/gate_s1.py` for the visual gate.
- Error codes `E901`-`E903`, `W602`, `W901`, `W902`.
- Documentation pages for layouts, styles and examples; the PDF section of the outputs page.
- Tests: golden HTML, TeX and Markdown per layout; the spec-1.0 compat corpus gains the renders of both layouts (HTML compared as canonical DOM); PDF integration tests for every engine (text against the Markdown output, reproducibility, frozen text hashes); unit tests for the style API, the log parser and every new error path.

### Changed (phase S3)

- `Report.add_figure` renders matplotlib figures with `scireport.styles.figure_bytes` (PDF with embedded TrueType fonts).
- `.github/tl_packages`: `siunitx`, `biblatex` and `biber` removed (unused before S5); `changepage`, `enumitem` and `needspace` added.
- Layout files may list `fonts` (vendored font files) and a `palette` that the loader checks (`E703`).

### Added (phase S2)

- Template model (`template.yaml`: fields with kinds, table columns and figure renditions, formats, compatible spec range; `report.j2`; optional per-format bodies) and layout model (`layout.yaml`: per-format document, components, CSS and style; typed options with defaults), loaded by `name`, `name@version`, by path, or through the entry-point groups `scireport.templates` and `scireport.layouts`. `pack` pins the resolved versions into the bundle.
- Jinja environments per format: `SandboxedEnvironment`, `StrictUndefined`, escaping for the format, LaTeX-safe delimiters `((* *))`, `((( )))`, `((= =))` for LaTeX files only, and the MOSAICS filters (`fmt_int`, `fmt_float`, `share`, `fmt_bytes`, `duration`, `pct`, `ppm`, `sci`, `compact`, `missing`, `breakable`, `slug`).
- Component layer (`c.chapter`, `c.table`, `c.figure`, `c.metrics`, `c.details`, ... 24 components) with Markdown, HTML and LaTeX macros in the built-in `minimal@1` layout; the single-pass outline and table of contents; math drawn with matplotlib `mathtext` for HTML.
- Markup converter interface with the mistletoe backend and a documented Markdown subset (`W701` outside it).
- Validation engine: aggregated, coded issues with key, JSON pointer, expected and found, template `file:line` and suggestions; `--strict`, `--json`; Jinja AST lint; render-time tracking of values used and left over. Commands `validate`, `render`, `templates`, `layouts`.
- Writers: Markdown (single file, or `index.md` plus one file per chapter with an `md_file`, `figures/`, alt text, generated-file header), self-contained HTML, standalone LaTeX project (`report.tex`, layout `.sty`, `latexmkrc`, PDF figures preferred, booktabs/longtable tables) and `render-manifest.json`. Same inputs give byte-identical files.
- LaTeX and Markdown escaping, with hypothesis property tests.
- Built-in `generic@1` template that renders any bundle from its outline; `minimal@1` layout.
- Error catalogue extended and documented in `docs/errors.md`, drift-tested; documentation pages for templates and layouts, Markdown limits and outputs.
- Tests: unit tests for every filter, component and error code; golden Markdown, HTML and LaTeX; byte-identical double renders; sandbox escape attempts; the expected renders of the frozen spec-1.0 corpus; integration tests that compile the golden LaTeX project and a bundle of hostile text with pdfLaTeX, XeLaTeX and LuaLaTeX.

### Fixed (phase S2)

- `md_escape` now escapes a leading `.` or `)` (mistletoe reads it as an empty list item).
- CI: `ulem` added to the TeX Live package list of the `pdf-latex` job; `longtable`, which is not a TeX Live package, removed.
- `scireport layouts` lists formats in the canonical order.

### Added (phase S1)

- Data-file specification 1.0 (`scireport.spec`): pydantic models for the manifest blocks and the 16 kinds
  (`text`, `number`, `bool`, `date`, `list`, `mapping`, `table`, `figure` with required alt text, `image`,
  `math`, `code`, `metrics`, `status`, `alert`, `flow`, `attachment`), the key grammar, canonicalisation of bare
  JSON into typed envelopes, cross-reference checks, and the frozen JSON Schema
  `scireport/spec/schemas/data-1.0.schema.json` with a drift test.
- Spec versions and migrations: `E501` for a bundle from a newer spec, `E503` for a version with no migration, a
  pure dict-to-dict migration framework with the 1.0 baseline.
- Report bundles (`scireport.bundle`): directory, ZIP and single-file forms; sha256 and size for every asset;
  byte-reproducible ZIPs (sorted entries, 1980 timestamps, fixed attributes, STORED for compressed media);
  zip-slip, symlink, encrypted-entry and size-cap rejection; lazy, verified asset reads; strict YAML (YAML 1.2
  scalars, no aliases, no duplicate keys) for hand-authored directories only; atomic writes.
- `Report` builder: values, tables from pyarrow, pandas or any Arrow-stream object, matplotlib figures with
  sidecar data and metadata stripped, images, attachments, outline, render options, pre-process steps.
- Commands `scireport spec (version|schema|kinds|migrate)`, `pack`, `unpack`, `inspect` (`--json`, `--key`,
  `--no-verify`, `--max-size`) and the global `--log-level` / `--log-file`.
- Error catalogue `scireport.errors.CODES` (E1xx to E5xx, W402) and the aggregated `Issue` / `SpecError`.
- Compat corpus `tests/compat/spec-1.0/` (minimal, text-only, full-kinds) with `FROZEN.sha256`; hypothesis
  property tests for keys, canonicalisation and pack/unpack round trips; `make compat` and `make schema`.

### Changed

- ADR-0001 to ADR-0011 are *Accepted* (gate HG-S0, 2026-10-09).
- Python 3.15 CI jobs stay experimental (`continue-on-error`) until wheels exist; the Windows MSYS2 location is
  read from the setup step's output.

### Added (phase S0)

- Phase S0: repository skeleton (`uv` project, GPL-3.0-only), ruff, mypy strict, pytest with coverage gate,
  pre-commit, Makefile.
- Agent files (`.agents/`, symlinks for Claude), copied subagents and the `python-logging` skill, a placeholder
  packaged `scireport` skill.
- Architecture decision records ADR-0001 to ADR-0011 (status: proposed) and repository conventions.
- GitHub Actions: lint, test matrix (Linux, macOS, Windows x Python 3.12 to 3.15), lowest-direct bounds, WeasyPrint,
  LaTeX and pandoc toolchain jobs, docs, Pages deploy and release workflows.
- Sphinx documentation skeleton with `llms.txt` and per-page Markdown builders.
