# Changelog

All notable changes are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/) and the
project uses [semantic versioning](https://semver.org/) for the Python API and `MAJOR.MINOR` for the data-file
specification (ADR-0008).

## [Unreleased]

## [1.0.0] - unreleased

The first release, prepared in phase S7 and pending sign-off (gate HG-S2); the date is set when the tag is pushed.
It freezes data-file specification 1.0, the built-in templates (`generic@1`, `kitchen-sink@1`) and layouts
(`minimal@1`, `default@1`, `modern@1`), the 17 value kinds, the error codes and the public Python API
(`scireport.__all__`, 37 names). Everything below, grouped by development phase, is part of this release.

### Added (phase S7: the 1.0 freeze)

- **The compat corpus `tests/compat/spec-1.0/` is complete** (ADR-0008): every one of the 17 kinds, both designed
  layouts (and `minimal@1`), Markdown, HTML and LaTeX, the text of the WeasyPrint and LuaLaTeX PDFs, and both markup
  engines. New case `every-kind` (the values of `full-kinds` plus a bibliography, with an outline that lists all 17
  kinds: the `generic@1` renders of `full-kinds` show only the four values its outline lists); the `-pandoc` render
  folders of every case and layout; the `bibliography` case rendered with `default@1` and `modern@1`; PDF text hashes
  for each of these. `pandoc-version.txt` records the pandoc that wrote the `-pandoc` files, and their tests compare
  only against it (skip locally, fail in CI with another version). Created by `make_every_kind_1_0.py` and
  `make_render_complete_1_0.py`, which only add files.
- **The built-ins are frozen by hash**: `tests/compat/FROZEN-builtins.sha256` lists every file of every
  `layouts/<name>/<n>/` and `templates/<name>/<n>/` directory, the vendored fonts, the `.mplstyle` files and the frozen JSON
  Schema; a test compares it with the files (`make_frozen_builtins.py` only appends lines for new versions).
- **Freeze lists only grow**: `tests/frozen.py BASE_REF` (`make compat-growth`) fails when a line of either freeze
  list disappeared or changed since a revision, so a fixture cannot be regenerated together with its hash. The new CI job
  `compat` runs `make compat` with pandoc and checks growth against the latest release tag (until the first tag exists,
  nothing is released and nothing is checked).
- `release.yml` can be started by hand against any ref (`workflow_dispatch`) for the sign-off; its build job runs
  `.github/check_dist.py` (the wheel and the sdist hold every frozen built-in file with its recorded hash, and the wheel
  holds the agent skill) and its clean-room job runs `.github/clean_room.sh`: a fresh virtual environment outside the
  checkout, `scireport[pdf,astro]` installed from the git URL, the kitchen sink rendered to Markdown, HTML, LaTeX and PDF
  with both designed layouts.
- `CITATION.cff`.

### Changed (phase S7)

- The package version is `1.0.0`. The README has a quickstart, the install lines for a consuming project and the system
  dependencies per feature; the support statement is Linux with Python 3.12 to 3.14 (3.15 stays experimental).
- The `pdf-weasyprint` CI job installs the `pandoc` extra: the frozen PDF text hashes include the pandoc renders.

### Changed (HG-S1 answer: the designs of `default@1` and `modern@1`; neither is released, so no new version)

- `default@1`: the WeasyPrint header rule spans the whole frame and the content starts 8 mm below it (LuaLaTeX: `headsep` 22 pt); the text is no longer capped at 68 characters (LaTeX: no right margin for the 52 mm overhang) and is set in **IBM Plex Serif** at 11 pt, while headings, tables and the dashboard components stay in Inter; the table of contents and every chapter opener are followed by a page break; the left border of the status and alert boxes is always solid (the level is told by its colour and its printed headline), the flow has no dots (the rail takes the colour of the state); LuaLaTeX: the rule under a heading follows it closely (the rule was a whole line high), the contents rows are tight and their page numbers flush right, the metric value sits further below its title, the unit of a table column is on its own line under the name, and a heading is no longer left alone at the foot of a page or followed by a ghost table header (`\Needspace` instead of `\needspace` after a longtable).
- `modern@1` is redone after the TUPAN publication plan ("Publication", replaces "Signal"): a steel-blue cover band with a gold stripe and the abstract in a titled box, numbered blue headings (`1`, `1.1`), justified **TeX Gyre Pagella** text, **TeX Gyre Heros** headings, **TeX Gyre Cursor** code, a table of contents with dot leaders, booktabs tables with the caption above, boxes with a coloured title bar and the state printed as a word. `chapter_breaks` defaults to false. Its matplotlib style and palette follow (`data-sky` is now `data-orange`). pdfLaTeX loads the TeX Gyre families from TeX Live and no longer needs the `W901` fallback for this layout.
- New vendored faces: IBM Plex Serif (Regular, Italic, SemiBold; OFL) and TeX Gyre Pagella, Heros, Cursor (GUST Font Licence, `fonts/GFL.txt`), subset with the Greek letters and `≤ ≥ ≈ ≠ √`. The LaTeX project copies the licence that matches the faces it ships. The palette may name a `fonts.serif` stack.
- The frozen compat renders (`tests/compat/spec-1.0/*/expected/render-generic-1-{default,modern}-1/`) and the golden files of the two layouts were regenerated: both layouts were still unreleased.

### Fixed (post-S6 review findings)

- `scireport pack` also pins an absent `render.template` and `render.layout` to the defaults a render uses (`generic@1`, `default@1`), so a packed bundle always names what it renders with. `inspect` counts the rows of a table that does not record `n_rows` (a hand-written one) from the Parquet footer or the CSV, instead of printing `? rows`; the stored spec is not changed.
- Piping a command into `head` no longer logs `[Errno 32] Broken pipe`: `reporting_errors` lets `BrokenPipeError` pass and the new console entry point `scireport.cli:run` exits quietly with status 1 (stdout is pointed at the null device first). `pyproject.toml` `[project.scripts]` now names `scireport.cli:run`; `scireport.cli.app` is unchanged.
- `scireport validate` reports the problems of the data file (spec stage) and of the template (template stage) the same way: plain lines on stdout, then the `valid:`/`invalid:` summary; `--json` is the same document for both (`ok`, `strict`, `exit_code`, `counts`, `issues`), where the spec stage used to print `{ok, issues}` and log lines on stderr. Exit codes are unchanged. The spec stage still stops the template checks that need the values.
- `E706` no longer ends in `(expected None, found tex)`: an issue prints only the parts it has (`(found tex)`), and `E706` now lists what is supported as `expected`. `E804` for a layout macro called with arguments it does not take (`TypeError: macro 'status' takes no keyword argument 'level'`) reports the macro in the layout's components file instead of the template line. No code or title changed.
- `scireport.figure()` uses matplotlib's constrained layout engine by default (`constrained=False` opts out), so axis labels are not clipped, and `Report.add_figure` renders exactly as `save_figure` does with its defaults (cropped to the content, `tight=True`; it was uncropped). A figure drawn the old way gives a different PNG when it is added again. Figures stay byte-reproducible.
- A number printed inside `{% filter md %}` keeps its LaTeX tie (`3.5~mag`) instead of `3.5\textasciitilde{}mag`; the output outside the filter is unchanged. The skill's `Report.write` examples carry `overwrite=True` (`E410`).
- `scireport.spec.schema.manifest_json_schema(version)` generates the schema of any older minor of the current major (fields added in a later minor are marked `json_schema_extra={'since': '1.N'}` and left out); the schema test regenerates every frozen `data-<version>.schema.json` byte for byte. `tests/compat/error-codes.json` freezes the title of every released error code, and a test fails when one is removed or retitled.
- The palette table of the docs and the skill spells out `cmap`, `fonts` and `page` as `cmap.sequential`, `fonts.sans`, `page.width_mm` ... with their meaning and default; the generator now also reads docstring entries that group names (`width, height : float`), which filled many empty cells of the pre-processor parameter tables.
- ADR-0005 lists the code families `E6xx` to `E9xx` and `W5xx`, `W7xx`, `W9xx`; ADR-0008 says that the latest version of a layout is reached by leaving the version out (`default` is a layout name, not an alias).

### Added (phase S6)

- **Documentation site** (ADR-0009) at <https://nmcardoso.github.io/scireport/>: quickstart, user guide, the data-file specification, the command line (generated tables plus the `sphinxcontrib-typer` help text), the Python API (generated tables plus autodoc), the error-code catalogue and the pre-processor reference (both generated from code and drift-tested), template, layout and matplotlib-style authoring guides, the example gallery (every example in both layouts as Markdown, HTML and two PDFs, built from `make examples`), the agent skill (ZIP download) and the MCP server pages, the ADRs, the compatibility policy and the changelog.
- **For language models**: `llms.txt` and `llms-full.txt` (`sphinx-llms-txt`), and a Markdown twin of every page next to its HTML (`sphinx-markdown-builder`), linked from the index; the frozen JSON Schemas are published under `/schemas/` (where their `$id` points) and the skill as `downloads/scireport-skill.zip`.
- `docs/check_site.py` (run by `make docs`) checks the built site; `make docs-linkcheck`.
- `scireport.agent.skillgen` also fills the generated blocks of the `docs/` pages; new generators `error-catalogue`, `preprocessor-reference`, `schema-files` and `exceptions`.

### Fixed (phase S6)

- CI: the `lint`, `test` and `lowest` jobs installed only the `dev` group, so mypy could not import `mcp` and the pre-processor end-to-end test lacked astropy; they now sync `--all-extras`.
- `minimal@1`: the description of the `accent` option was cut at its `#` (an unquoted YAML comment); it is quoted now. Only the listed description changes, not any output.
- `astro.snr_magnitude` and `astro.zeropoint_offsets` drew `σ` and `Δ` as Unicode text, which the vendored Inter subset lacks: on a machine without a system font that has them matplotlib warned, and the tests (warnings are errors) failed. They use mathtext (`$5\sigma$`, `$\Delta m$`) now; the default `y_label` of `astro.zeropoint_offsets` changes from `Δm (mag)` to `$\Delta m$ (mag)`.
- The skill and the docs said YAML anchors are rejected; only aliases (`*a`) are (`E408`).

### Added (phase S5)

- **pandoc** (ADR-0011, `scireport[pandoc]`, `pypandoc-binary`, imported lazily): `--markup-engine pandoc` / `render.markup_engine: pandoc` next to the default `mistletoe`, never chosen automatically; prose is read with pandoc's CommonMark (footnotes, definition lists, task lists) under `--sandbox`, with the same rules for what is outside the subset (`W701`); the pandoc version goes into `render-manifest.json` and `render.pandoc_version` (set by `pack`) warns with `W501` when it differs. The differences between the engines are listed in `docs/markup.md` and committed as golden files for both.
- **Citations**: the `bibliography` kind (BibTeX asset, optional CSL asset, optional biblatex style; at most one per bundle, `E211`), `Report.add_bibliography`, `[@key]` / `[see @a, p. 3; @b]` / `[-@key]` in Markdown text values, `c.references()`. Markdown and HTML go through pandoc's `citeproc`, run once over the whole document so numeric styles number consistently; LaTeX uses `biblatex` with `biber` and needs no pandoc. Unknown key: `E212`.
- **Word, OpenDocument and EPUB**: `-f docx`, `-f odt`, `-f epub`, converted from the unsplit Markdown or from the HTML (`--office-source`), with an optional `reference.docx` (`--reference-doc`, or `reference_docx:` in `layout.yaml`); archives are reproducible.
- **LaTeX fragments for manuscripts**: `scireport export tex BUNDLE --keys ... -o DIR` writes `tab_<key>.tex`, `fig_<key>.tex` (+ the figure file) and `numbers.tex` with one `\newcommand` per number (CamelCase, digits spelled out, `--prefix`, collision `E807`); `scireport.export_tex`, `write_export`. A test compiles a stub manuscript that inputs every fragment.
- **The full command line**: `new`, `export tex`, `mplstyle path|show|palette`, `agent install-skill [--check]`, `agent mcp-config`, `mcp serve`; `templates NAME` and `layouts NAME` describe one; `--json` on the commands agents use; `validate` takes `--markup-engine` and `--office-source`.
- **The MCP server** (`scireport[mcp]`, official `mcp` SDK 2.x, `MCPServer` over stdio): tools `list_templates`, `describe_template`, `list_layouts`, `list_preprocessors`, `describe_preprocessor`, `spec_schema`, `inspect_bundle`, `validate_bundle`, `render_bundle`, `error_help`; the skill pages are resources; paths are confined to `--root` (`E412`); problems come back as data.
- **The skill** (`scireport/agent/skill/scireport/`): `SKILL.md` and eight reference pages, with tables generated from the code by `make skill` and a drift test; `scireport.error_help.HELP` gives a usual cause and fix for every code.
- **Public API**: `scireport.__all__` (37 names; the heavier ones load on first use) and a snapshot test (`tests/unit/public_api.txt`).
- Error codes `E211`, `E212`, `E412`, `E506`, `E507`, `E807`, `E808`, `E904`, `W501`.
- The spec-1.0 compat corpus gains the `bibliography` case (appended to `FROZEN.sha256`; no existing line changed).

### Changed (phase S5)

- `.github/tl_packages` gains `biblatex` and `biber`; CI gains an `mcp` job and installs the pandoc extra in the `pdf-latex` job.
- `pandoc`-dependent and `mcp`-dependent tests are marked `integration` and skip when the extra is missing (they fail with `SCIREPORT_REQUIRE_TOOLCHAIN=1`).
- A format `docx`, `odt` or `epub` in a bundle's `render.formats` is now written (it was skipped with a log line).
- `scireport.preprocess` CLI listing code moved to `scireport.agent.catalogue` (shared with the MCP server).

### Added (phase S4)

- Pre-processors (ADR-0006): `@preprocessor(name, version, inputs, outputs)` with typed `Port`s, pydantic validation of the parameters from the function signature, the registry (built-ins, the entry-point group `scireport.preprocessors`, `register_preprocessor()`), name-only references in data files (`module:function` needs `--allow-import`), the DAG check before anything runs (every problem reported at once), outputs written to a work directory with the input bundle untouched unless `--write-back`, and a content-hash cache (name, version, parameters, input hashes, output keys, seed, scireport version, style hash). `Context` offers `value`, `load_table`, `mplstyle`, `figure`, `save_figure` (the sidecar data is required), `save_table`, `seed`, `rng`, `look` and `log`.
- Commands `scireport preprocess` (`--work-dir`, `--output`, `--write-back`, `--cache-dir`, `--no-cache`, `--allow-import`, `--seed`, `--json`) and `scireport preprocessors [NAME] [--json]`; `render` and `validate` run the steps first (`--preprocess/--no-preprocess`, `--allow-import`, `--cache-dir`).
- Core catalogue (18): `table_profile`, `bar`, `stacked_shares`, `histogram`, `separation_histogram`, `funnel`, `density_scatter`, `metric_scatter`, `distribution`, `corner`, `pvalue_strip`, `achieved_vs_target`, `duration_bars`, `split_marginals`, `split_balance`, `qq`, `pp`, `heatmap` (new).
- Astro catalogue (9): `sky_density`, `footprint`, `sky_grid` (HEALPix with astropy-healpix on matplotlib Mollweide axes; no mocpy, no hats), `color_color`, `color_magnitude`, `number_counts`, `snr_magnitude`, `magnitude_residual`, `zeropoint_offsets`. Only the three sky maps need `scireport[astro]`.
- Every figure is stored with the data it was drawn from, and a test per plot proves that the figure drawn again from the stored sidecar data is byte-identical to the stored PNG; a second test proves two runs give identical PNG, PDF and sidecar bytes.
- Error codes `E601`-`E608`; exit code 3 also for a missing extra (`E607`).
- `OverlayBackend` and `Bundle.with_files()`; `table_from_value()`; `docs/preprocessors.md`.

### Changed (phase S4)

- `check_manifest` no longer reports `E103` for an outline key that a `preprocess` step declares as an output.

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

- CI runs on Linux only: the macOS and Windows jobs and the MSYS2 and Homebrew steps are removed, and the release clean-room install runs on Linux. macOS and Windows are unsupported (DECISIONS, 2026-10-10).
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
- GitHub Actions: lint, test matrix (Python 3.12 to 3.15; originally also macOS and Windows, dropped in S3), lowest-direct bounds, WeasyPrint,
  LaTeX and pandoc toolchain jobs, docs, Pages deploy and release workflows.
- Sphinx documentation skeleton with `llms.txt` and per-page Markdown builders.
