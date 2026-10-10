<!-- Binding plan for the scireport package (Part A) and the 2_dataset report migration (Part B).
Copied from the approved planning session on 2026-10-09. Kickoff prompts: prompts/scireport/*_kickoff.md.
Status: Phase S0 is COMPLETE (scireport repo created and pushed; gate HG-S0 open in scireport/STATUS.md).
Deviations recorded after S0 (see scireport/DECISIONS.md, which wins over this file):
- The TeX Live action is TeX-Live/setup-texlive-action@v4 (teatimeguest/... no longer exists).
- astral-sh/setup-uv is pinned to the exact tag v10.2.0 (no floating major tag).
- Python 3.15 jobs and the Windows WeasyPrint jobs are continue-on-error until verified.
- Kickoff prompts live in prompts/scireport/ (not prompts/2.02_reports/). -->

# Plan: execution plan for `scireport` and the 2_dataset report migration

## Context

`prompts/2.02-reports.prompt.md` asks for a **phased, detailed execution plan** that another coding agent will follow:

1. Build **`scireport`**, a standalone, data-centric report engine (data file + Jinja2 template + layout, rendered to
   `.md`, `.html` and `.pdf`), in `/home/natan/repos/scireport/`. It is inspired by the MOSAICS engine in
   `/home/natan/repos/datex/datex/report` but decoupled from datex.
2. **Migrate the 2_dataset (gzms) reports** to it. All current content is kept, and sky distribution/concentration
   and statistics figures are added. scireport is installed from public GitHub. The reports are Markdown for LLMs
   plus one PDF for humans. The scireport skill is installed in this monorepo.

This session's deliverable is the plan, not the implementation.

**Facts established while exploring:**

- **MOSAICS engine**
  - Rendering path: Jinja2 → HTML → **WeasyPrint** → PDF. Matplotlib draws the figures (base64 PNG) and the
    equations (mathtext SVG).
  - About 20 components, a design system (`design/palette.py`, `css/tokens.css`, `base.css`, `components.css`,
    `print.css`, vendored Inter and IBM Plex Mono fonts under OFL, `datex.mplstyle`) and 45 pure `plot_*`
    functions (`R/plot.py`).
  - Golden-HTML tests (`tests/report_html.py`).
  - Coupling to remove: datex core imports, `constants.AUTHOR` and `PACKAGE_NAME`, `hats`/`mocpy` sky maps, and a
    custom sky-map encoding.
- **2_dataset (`gzms` 1.0.0, stopped at HG5 release sign-off)**
  - 11 generated Markdown reports in `docs/`. All are built from hand-joined f-strings (`_md_table`, `_md`,
    `_cell`); there is no HTML or PDF output and no sky plots.
  - `method.md` is hand-written. The `data_model/*.md` files are generated and kept in sync with the README; I14
    and CI check them.
  - Two figures exist (`separations.pdf` and the QA grades and shift curves). Their style is `astro.mplstyle`.
  - The objects table has `ra`, `dec`, `n_sources`, `redshift` (with a 999 sentinel in 5,516 rows) and
    `size_arcsec`. The members, splits and QA Parquet tables hold the rest.
- **Repo conventions**
  - Symlinks: `AGENTS.md` and `CLAUDE.md` → `.agents/AGENTS.md`; `.claude/skills` → `../.agents/skills`.
  - `.claude/agents/{docstring,explore,sql-probe}.md` are datex copies.
  - Skill frontmatter rule: `name` equals the folder name; `description` ≤ 1024 characters
    (`1_review/tupan_review/qa/compliance.py`).
  - Subprojects keep byte-identical copies of skill code.
- **Tooling on this machine:** TeX Live 2023 (lualatex, latexmk), no pandoc, no WeasyPrint installed, `gh` not
  logged in. The GitHub owner is `nmcardoso`.

**User decisions this session:**

- Layouts: `default` and `modern` only.
- Agent kit: skill plus MCP server (`scireport[mcp]`).
- scireport licence: **GPL-3.0-only**.
- Code style: **datex** (2-space indent, single quotes).
- gzms: **v1.1.0**, with a sign-off gate.
- The PDF goes to `docs/` and is **git-ignored** (`docs/*.pdf`). The Markdown figure PNGs are **git-ignored** too
  (`docs/figures/`).
- Added after the first draft:
  - The repository is **pushed to `https://github.com/nmcardoso/scireport`**.
  - **GitHub Actions matrix testing** across platforms and Python versions.
  - **First-class LaTeX rendering** (D11).
  - **Pandoc support** where it adds value (D12).

## What I write after approval

1. **`prompts/2.02_reports_plan.md`**: the self-contained execution plan, in the same format as
   `prompts/2_dataset_plan.md`:
   - header, then §0 "How to use this plan" with a rules table
   - one-page decision summary
   - design (ADRs)
   - phases S0–S8 and M0–M5, each with goals, tasks, commands, outputs, tests, a "done when" list and gates
   - testing strategy and risk register
   - appendices:
     - A: data-spec v1.0 draft (JSON example and kind table)
     - B: component catalogue mapped from MOSAICS macros
     - C: preprocessor catalogue with MOSAICS `file:line` sources
     - D: default-layout design tokens copied from MOSAICS CSS
     - E: gzms content inventory to preserve, per doc file, with row counts
     - F: new-figures list
     - G: kickoff prompts
     - H: sources consulted (sphinx-llms-txt, sphinxcontrib-typer, sphinx-markdown-builder, mistletoe,
       pypandoc-binary 1.17, teatimeguest/setup-texlive-action, PEP 790 on the Python 3.15 release)
2. **`prompts/2.02_reports/<phase>_kickoff.md`**: one short kickoff prompt per phase, in the same style as
   `prompts/2_dataset/phase*_kickoff.md`.

No code, commits or moves of the prompt file. I will tell the user what to commit.

---

## Design fixed by the plan (D1–D13 become ADR-0001…0011 in the scireport repo; D10 and D13 are conventions, not ADRs)

### D1. Data-file format: a "report bundle" (ZIP container, or the same tree as a directory)

The bundle is `<name>.scireport.zip`, or a `<name>.scireport/` directory with the identical layout:

- `scireport.json` is the manifest, the single source of truth. YAML (`scireport.yaml`) is accepted only for
  hand-authored directories; `pack` converts it to JSON.
- `assets/{tables,figures,images,text,attachments}/…` hold each artifact in its **native format**:
  - tables as Parquet (zstd) or CSV
  - figures as PNG, PDF and optional SVG, plus sidecar data in Parquet
  - long text as Markdown
  - attachments as CSV
- Every asset carries its `sha256` and `bytes` in the manifest.
- A bare `.json` or `.yaml` file with relative asset paths is also accepted, for text-only reports.

| Format | Verdict |
|---|---|
| YAML / JSON alone | Fine for structure, but binary data would need base64 (+33 %). YAML adds typing ambiguity. |
| Pickle | **Rejected.** It can execute arbitrary code and is tied to Python versions. |
| HDF5 | **Rejected.** It needs the heavy C library h5py, and figures (SVG/PDF) and tables become opaque blobs. Neither agents nor git diffs can read it, and it corrupts on interrupted writes. Its strength, large numeric arrays, is not what a report carries. |
| **ZIP + JSON manifest + native assets** (like OOXML, EPUB or Frictionless Data Package) | **Chosen.** Standard library only. Each asset in its best format. Inspectable by humans and agents. Lazy reads. The unpacked directory form diffs in git. Integrity comes from the hashes. |

**Rules:**

- A bundle holds **summaries, not raw catalogues**: aggregate first, for example HEALPix counts instead of 1.3 M
  positions.
- Zips are byte-reproducible: sorted entries, fixed 1980 timestamps, STORED for media already compressed.
- The reader rejects zip-slip paths and enforces a size cap.

### D2. Data structure: semantic keys with typed envelopes, not type-scoped keys

**Manifest blocks:**

- `scireport` (spec version, e.g. `"1.0"`)
- `meta`: title, subtitle, authors, date, version, pipeline, footer, abstract, keywords, language
- `render`: template, layout (`default@1`), formats, `pdf_engine`, layout options
- `outline`: optional, used only by the built-in `generic` template
- `values`: key → value
- `preprocess`: list of steps
- `provenance`: generator, input hashes

**Keys:**

- Keys are semantic dotted paths (`crossmatch.pairs`). Segments match `[a-z0-9_-]+`.
- The **type lives in the value** (`"kind": "table"`), so changing a type never renames a key, templates address
  meaning, and one namespace prevents collisions.
- The assets folder is still organised by kind, for browsing.

**v1.0 kinds** (MOSAICS components plus generic needs):

- text and numbers: `text` (plain or markdown), `number` (value, unit, format, uncertainty or interval, missing),
  `bool`, `date`
- lists and records: `list`, `mapping` (metadata list)
- data: `table` (Parquet, CSV or inline; per-column label, unit, format, align, width, description; `row_status`
  verdicts; cell emphasis; `max_rows` with an attachment fallback), `figure` (renditions, caption, **required**
  alt text, width fraction, sidecar data), `image`
- typeset content: `math`, `code`
- dashboard blocks: `metrics`, `status`, `alert`, `flow`
- files: `attachment`

Bare JSON scalars, lists and objects are shorthand. They are canonicalised on load.

### D3. Templates and layouts

**Template** (structure) is a directory:

- `template.yaml` declares `fields`: key or wildcard → kind, required, table columns and dtypes, figure
  renditions. It also lists `formats` and a compatible spec range.
- `report.j2` is the **format-neutral** body. It calls component functions (`c.chapter`, `c.table(data.x)`,
  `c.figure`, `c.metrics`, `c.details`, …) and writes prose inside `{% filter md %}`. mistletoe converts that prose
  to HTML or LaTeX; it is pure Python and ships HTML, LaTeX and Markdown renderers.
- Optional per-format overrides: `report.{md,html,tex}.j2`.

**Layout** (look) is a directory:

- `layout.yaml`: formats, options with defaults (paper, cover, toc, accent, chapter breaks), PDF engines,
  `mplstyle`, `palette.yaml`, fonts
- per format: a `document` skeleton plus a `components` macro file (`html/`, `latex/`, `md/`), plus CSS

**Rendering:**

1. The body is rendered first (outline and TOC are collected, as in the MOSAICS single-pass trick).
2. The layout skeleton wraps it.
3. LaTeX files use LaTeX-safe Jinja delimiters (`((* *))`, `((( )))`, `((= =))`) because `{%` and `{#` clash with
   TeX. Neutral templates never contain raw TeX, so standard delimiters stay valid there.

**Environment:** `SandboxedEnvironment` with `StrictUndefined` and format-aware escaping. The MOSAICS number
filters are ported: `int`, `float`, `share`, `bytes`, `duration`, `pct`, `ppm`, `sci`, `compact`, `missing`,
`breakable`.

**Markdown split:** chapters with `md_file=` become separate `.md` files, plus `index.md`. This keeps today's
gzms file names.

**Built-ins:**

- templates `generic@1` (renders any bundle from its `outline`, so a report needs no template) and
  `kitchen-sink@1` (demo)
- layouts `default@1` and `modern@1`
- custom templates and layouts come by path or through the entry-point groups `scireport.templates` and
  `scireport.layouts`

### D4. Outputs and PDF engines

| Format | Output |
|---|---|
| `md` | Single file or split, with `figures/*.png`. Images get alt text. Math as `$…$`. A generated-file header. |
| `html` | One self-contained file: inlined CSS, fonts and images. |
| `tex` | A standalone, compilable LaTeX project. See D11. |
| `pdf` | Two engines (below). |
| `docx`, `odt`, `epub` | Optional, through pandoc (`scireport[pandoc]`). See D12. |

- **`weasyprint`** (default; extra `scireport[pdf]`): reproduces MOSAICS. Keep the MOSAICS WeasyPrint workarounds:
  no nested flex, a named cover page, no `break-inside` on tables.
- **`latex`**: `latexmk` with `lualatex` by default (`xelatex` and `pdflatex` selectable through
  `render.latex_engine`), fontspec loading the vendored fonts, `SOURCE_DATE_EPOCH` and log parsing.
- Both layouts support both engines.
- Math: mathtext SVG for HTML/WeasyPrint (port `R/math.py`), native in LaTeX.
- Every render also writes `render-manifest.json` (input and output hashes, versions).
- Optional dependencies are imported lazily. A missing system dependency gives exit code 3 with an install hint.

### D5. Validation (fully descriptive errors)

Errors are aggregated, never first-fail. Each has:

- a stable **error code**, e.g.:
  - `E1xx` missing key
  - `E2xx` wrong kind
  - `E3xx` table schema
  - `E4xx` asset or hash
  - `E5xx` version
  - `W4xx` unused key
- the key and its JSON pointer in the manifest
- the expected and the found value
- the template `file:line` where the key is used
- a "did you mean" suggestion (difflib)

Template lint walks the Jinja AST (`v("key")` and `data.a.b` chains). Dynamic keys are checked at render time
through usage tracking (the MOSAICS `take`/`peek`/`leftovers` idea).

Options: `--strict` (warnings become errors) and `--json` (for agents). Exit codes: 0 ok, 1 runtime error,
2 validation error, 3 missing system dependency.

### D6. Pre-processors

**Interface.** Each pre-processor is registered with a decorator that takes a name, a version and typed input and
output ports:

```python
@preprocessor('core.histogram', version=1,
              inputs={'table': Port('table')}, outputs={'figure': Port('figure')})
def histogram(ctx: Context, *, table, column, bins='auto', counts_column=None, log=False, ...) -> dict[str, Value]
```

**Context.** `ctx.value`, `ctx.load_table` (pyarrow), `ctx.mplstyle()`, `ctx.figure()`,
`ctx.save_figure(fig, data=…)`, `ctx.save_table`, `ctx.seed`, `ctx.log`. Parameters are validated by pydantic from
the signature.

**Discovery.** Built-ins, the entry-point group `scireport.preprocessors`, and `register_preprocessor()`. Data files
refer to pre-processors **by name only**; `module:func` needs `--allow-import`.

**Execution.**

1. The DAG is checked before anything runs.
2. Outputs are written to a work dir; the input bundle is left untouched unless `--write-back`.
3. Results are cached by a hash of: name, version, parameters, input content hashes, scireport version and the
   style hash.

**Catalogue (from `R/plot.py` and `R/tables.py`):**

- **core:**
  - `table_profile`
  - `bar` (from `plot_category_counts`)
  - `stacked_shares`
  - `histogram` (samples or pre-tallied counts)
  - `separation_histogram`
  - `funnel` (constraint counts and drops)
  - `density_scatter` (hybrid hexbin and scatter)
  - `metric_scatter`
  - `distribution` (box or violin)
  - `corner`
  - `pvalue_strip`
  - `achieved_vs_target`
  - `duration_bars`
  - `split_marginals`, `split_balance`
  - `qq`, `pp`
  - `heatmap` (new; gzms needs it)
- **astro** (`scireport[astro]`, astropy and astropy-healpix with matplotlib Mollweide, **no hats or mocpy**):
  - `sky_density` (HEALPix counts or ra/dec points)
  - `footprint`
  - `sky_grid` (small multiples)
  - `color_color`, `color_magnitude`, `number_counts`, `snr_magnitude`, `magnitude_residual`, `zeropoint_offsets`
- **images** (`scireport[images]`, optional **Phase S8 after the migration**): the 15 `compare_stamps` plots plus
  `metrics.py`
- **Not ported** (datex runtime-specific): the node timeline, throughput and traffic graph; the HTTP, cast and error
  ledgers; db_constraints; `photometry.assess`.

### D7. mplstyle API

**Shipped files:** `styles/default.mplstyle` (port of `datex.mplstyle`: Inter, the MOSAICS palette, cividis) and
`styles/modern.mplstyle`.

**Functions:**

- `scireport.mplstyle(layout='default', *, rc=None)` is a context manager. It registers the fonts (port
  `fonts.register`/`probe`) and restores the rcParams on exit.
- `scireport.mplstyle_path(layout)`
- `scireport.palette(layout)`
- `scireport.figure(width=1.0, height=3.6, nrows, ncols)`: frame-aware sizes (port `Figures.grid`).

**Saving:** PNG and PDF metadata are stripped so files are deterministic.

**Consistency test:** `palette.yaml` ↔ `tokens.css` ↔ mplstyle ↔ LaTeX colours (port `test_report_theme`).

### D8. Backward compatibility (golden rule)

**Versioning:**

- The spec version is `MAJOR.MINOR` and appears in every bundle, template and layout.
- Minor versions are additive. A reader reads every older minor natively. A bundle from a newer minor gives E5xx
  plus an upgrade hint.
- A major bump ships a pure dict→dict migration (`spec/migrations/`) and `scireport spec migrate`.
- Frozen JSON Schemas (`spec/schemas/data-1.0.schema.json`, …) are generated from pydantic and checked for drift.

**Built-in layouts and templates:**

- They are **versioned and frozen** (`layouts/default/1/`). A visual change means a new version; the `default`
  alias points to the latest.
- `pack` pins the resolved version into the bundle, so a later re-render is identical.

**Compat corpus:** `tests/compat/spec-<v>/<case>/` holds the bundles and their expected md, canonical HTML (port
`report_html.canonicalize`), tex and PDF text hash. Fixture hashes are listed in `FROZEN.sha256`. CI fails if a
fixture or an output drifts.

**Python API:** semver, an API snapshot test, at least one minor version of deprecation warnings, and stable error
codes.

### D9. Agent kit and docs

**Skill** (package data `scireport/agent/skill/scireport/`):

- `SKILL.md` follows the monorepo frontmatter rules.
- `references/`: `data-file.md`, `python-api.md`, `cli.md`, `templates-and-layouts.md`, `preprocessors.md`,
  `mplstyle.md`, `errors.md`, `recipes.md`. `recipes.md` includes "md for LLMs + one PDF for humans" and CI.
- The tables are generated from code by `make skill` and drift-tested.
- `scireport agent install-skill --dest DIR [--check]` installs it.

**MCP server** (`scireport[mcp]`, official `mcp` SDK, FastMCP, stdio):

- Tools: `list_templates`, `describe_template`, `list_layouts`, `list_preprocessors`, `describe_preprocessor`,
  `spec_schema`, `inspect_bundle`, `validate_bundle`, `render_bundle`, `error_help`.
- Resources: the skill pages.
- File access is restricted to `--root`.
- `scireport agent mcp-config` prints a `.mcp.json` snippet.
- Before coding, verify the current SDK API through Context7.

**Docs:**

- Sphinx, MyST, furo, autodoc with napoleon, sphinxcontrib-typer (CLI), generated spec, error-code and
  preprocessor pages, and an example gallery for both layouts.
- **sphinx-llms-txt** produces `llms.txt` and `llms-full.txt`. **sphinx-markdown-builder** produces a `.md` file
  per page, published next to the HTML.
- Skill zip download, an MCP page, and the ADRs.
- Deployed with the GitHub Actions Pages workflow to `https://nmcardoso.github.io/scireport/`.

### D10. scireport repository layout and standards

- **Package:** flat layout `scireport/` with:
  - `spec/`, `bundle/`, `validate/`, `render/` (`outputs/`, `pdf/`)
  - `layouts/{default,modern}/1/`, `templates/{generic,kitchen-sink}/1/`
  - `styles/`, `preprocess/{core,astro}/`, `agent/`, `cli/`
  - `logging_utils.py`
- **Other folders:** `tests/{unit,property,golden,integration,compat,fixtures}`, `examples/`, `docs/`,
  `.github/workflows/{ci,docs,release}.yml`.
- **Agent files:**
  - `.agents/AGENTS.md` (new, scireport-specific)
  - `.agents/agents/{docstring,explore,sql-probe}.md` (copied; only `explore.md` is changed, from "datex" to
    scireport)
  - `.agents/skills/python-logging/` (byte-identical copy)
  - `.agents/skills/scireport` → symlink to the package skill
  - symlinks: `AGENTS.md` and `CLAUDE.md` → `.agents/AGENTS.md`; `.claude/agents` → `../.agents/agents`;
    `.claude/skills` → `../.agents/skills`
  - **Never copy `.mcp.json`.**
- **Style:**
  - ruff with `indent-width = 2`, `quote-style = 'single'`, line length 100
  - numpy docstrings, mypy strict
  - the `logging_utils.py` copy is excluded from format and lint, as gzms D0.4 does
  - coverage ≥ 90 %
- **Dependencies:**
  - core: jinja2, pydantic 2, pyyaml, typer, numpy, pyarrow, matplotlib, mistletoe
  - extras: `pdf` (weasyprint), `astro` (astropy, astropy-healpix), `pandoc` (pypandoc-binary 1.17, whose wheels
    bundle pandoc for Linux, macOS and Windows), `mcp`, `images`
  - groups: `dev`, `docs`
  - pandas is optional (DataFrames are accepted when it is installed)
  - use the latest versions as lower bounds when running `uv add`
- **Fonts:** the Inter and Plex Mono subsets are copied from datex together with `OFL.txt`.

### D11. LaTeX rendering (first-class)

1. **Standalone LaTeX output** (`-f tex`). It writes `report.tex`, the layout's preamble or class
   (`scireport-<layout>.sty`), and `figures/` (PDF renditions preferred, then PNG; SVG is never used in LaTeX).
   Tables use `booktabs`/`longtable` (repeated heads, as MOSAICS does), plus `siunitx` for units and number
   alignment. The project compiles with plain `latexmk` outside scireport.
   - Both layouts ship LaTeX components that match their HTML look: `tcolorbox` for status, alert and metrics;
     `fancyhdr` for running heads; a TikZ cover.
   - Under `pdflatex`, which cannot load OTF fonts, the layouts fall back to TeX fonts and emit a warning.
2. **LaTeX fragments for manuscripts.** `scireport export tex BUNDLE --keys … -o paper/generated/` writes files a
   manuscript can `\input`:
   - `tab_<key>.tex`, `fig_<key>.tex`
   - **`numbers.tex`** with one `\newcommand` per `number` value. Key → CamelCase macro, with a configurable prefix;
     a collision is an error.

   This matches monorepo golden rule 2 ("numbers in papers come from generated macros"). A test compiles a stub
   document that inputs every fragment.
3. **LaTeX math everywhere.**
   - The `math` kind and `$…$`/`$$…$$` in Markdown prose are native in tex, kept as `$…$` in md, and rendered to
     SVG in html and WeasyPrint.
   - `render.math_renderer` selects the SVG backend: `mathtext` (default, pure Python, port of `R/math.py`) or
     `usetex` (matplotlib through real LaTeX, full fidelity, needs TeX).
   - A construct mathtext cannot draw gives warning `W6xx` and shows the source as code; `--strict` makes it an
     error.
4. **Raw LaTeX passthrough.** `text` with `format: latex` is emitted verbatim in tex. Other formats need an
   explicit `alt: {html, md}` or the pandoc converter (D12); otherwise error `E2xx`.
5. **Safety and tests.**
   - LaTeX files use LaTeX-safe Jinja delimiters (D3).
   - The escape filter covers `# $ % & ~ _ ^ \ { }`, plus Unicode handled through the font, or a mapping under
     pdflatex.
   - A hypothesis property test runs the escape function, and a small compile-check sample is marked
     `integration`.
   - Golden `.tex` outputs for every example, both layouts and all three engines.

### D12. Pandoc support (optional; used only where it adds value)

**Backend.** `scireport[pandoc]` installs **pypandoc-binary**: no system pandoc is needed, so runs are
reproducible. It is imported lazily.

**Uses:**

1. **Markup converter backend.** `render.markup_engine: mistletoe | pandoc`, default `mistletoe` (pure Python).
   pandoc gives higher fidelity for GFM tables, footnotes, math and definition lists in Markdown → LaTeX and → HTML.
   - It also converts raw `format: latex` text to HTML or md.
   - There is **no automatic switching** (output must not depend on what is installed). The pandoc version goes
     into `render-manifest.json`, and a version that differs from the one recorded in the bundle gives a warning.
2. **Citations.** An optional `bibliography` kind (a BibTeX asset) and `[@key]` in prose:
   - tex: `biblatex` with `biber`
   - md and html: pandoc citeproc, with an optional CSL asset
   - without pandoc: error `E5xx` with an install hint
3. **Extra formats** `docx`, `odt` and `epub`, converted from the rendered HTML or md. The layout may supply a
   `reference.docx`.

**Tests:** golden outputs for both markup engines on the same examples. The documented differences are listed in
the docs.

### D13. GitHub repository and CI matrix

**Remote.**

- `origin` = `git@github.com:nmcardoso/scireport.git`; the public URL is `https://github.com/nmcardoso/scireport`.
- At S0: if `gh` is authenticated, run `gh repo create nmcardoso/scireport --public --source . --push`. Otherwise
  the human creates an **empty** public repository (no README or licence) and the agent pushes over SSH.
- `main` and the phase branches are pushed as work goes on, with a PR at each gate. Release tags are pushed only
  after gate sign-off.
- Pages source: GitHub Actions.

**`ci.yml`** (push and PR; `fail-fast: false`; uv cache):

| Job | Matrix | What it runs |
|---|---|---|
| `lint` | ubuntu × 3.12 | `ruff format --check`, `ruff check`, `mypy --strict` |
| `test` | {ubuntu, macos, windows}-latest × Python {3.12, 3.13, 3.14, 3.15} | unit, property, golden and compat tests (no system dependencies); coverage ≥ 90 % (ubuntu 3.12 uploads the report). 3.15 is marked experimental only if a dependency lacks wheels; decided at S0 and recorded in DECISIONS. |
| `lowest` | ubuntu × 3.12 | `uv sync --resolution lowest-direct`, then the tests (checks the lower bounds) |
| `pdf-weasyprint` | {ubuntu (apt pango), macos (brew pango), windows (MSYS2 pango per the WeasyPrint docs; if impractical, recorded as unsupported in CI and in the docs)} × {3.12, 3.15} | PDF integration tests |
| `pdf-latex` | {ubuntu, macos, windows} × {3.12, 3.15} | TeX Live through `teatimeguest/setup-texlive-action` with a pinned package list (latexmk, luatex, fontspec, booktabs, siunitx, tcolorbox, …) |
| `pandoc` | {ubuntu, macos, windows} × 3.12 | `scireport[pandoc]` tests |
| `examples` | ubuntu | renders every example × layout × format and uploads them as artifacts |
| `docs` | ubuntu | Sphinx build with `-W` plus linkcheck |

**Other workflows:**

- `docs.yml`: deploys Pages on `main`.
- `release.yml`: on a tag, builds the sdist and wheel, creates the GitHub release, and runs a **clean-room job**
  that installs from the `git+https://…@<tag>` URL on all three OSes.

**Windows care:**

- `.gitattributes` with `eol=lf` for golden fixtures; outputs written with `newline='\n'`; `pathlib` everywhere.
- Tests never rely on the repo's `.agents` symlinks: the package skill is real package data.

**Action versions** (setup-uv, checkout, setup-texlive, upload-pages-artifact, deploy-pages): pin to the current
major version, verified when the workflow is written.

**2_dataset** already has an ubuntu/macos × 3.12/3.13 matrix, and `gzms` requires `<3.14`. The plan keeps that
matrix, adds pango on ubuntu and a `make report` md-render smoke step, and leaves widening the OS or Python range
out of scope.

---

## Phases

### Part A: scireport (`/home/natan/repos/scireport`)

| Phase | Work | Gate |
|---|---|---|
| S0 | `git init`, uv project, pyproject (GPL-3.0-only), ruff, mypy, pytest, pre-commit, Makefile, agent files and symlinks, README, STATUS, DECISIONS, CHANGELOG, ADR-0001…0011. The full CI matrix of D13 (it starts green on a smoke test), with the Python 3.15 wheel check. **Push to `github.com/nmcardoso/scireport`** (D13). | **HG-S0**: the repository exists and is public, CI is green on the matrix, Pages is set to GitHub Actions, and the ADRs are approved. If `gh` is not logged in, the human creates the empty repository first. |
| S1 | Spec models (kinds, manifest, keys, shorthand), bundle reader and writer (dir, zip, file; hashes; zip-slip), `Report` builder API, JSON Schemas, migration framework, the `spec`, `pack`, `unpack` and `inspect` commands | — |
| S2 | Template and layout model, Jinja envs per format, components and filters (MOSAICS ports), markup-converter interface with mistletoe, outline and TOC, validation engine and lint with the error catalogue, md (single/split), html and **standalone tex** writers (D11.1), LaTeX escaping and math passthrough, `generic@1` | — |
| S3 | `default@1` layout (MOSAICS port: tokens, base, components, print, cover, chapter opener, TOC with `target-counter`, running header and footer) and `modern@1`, each with HTML **and** LaTeX components. WeasyPrint and LaTeX engines (lualatex, xelatex, pdflatex), math renderers (mathtext, usetex), mplstyle API and fonts, `kitchen-sink@1`, examples | **HG-S1**: visual sign-off. Show the MOSAICS demo PDF beside the scireport default PDF from **both** engines, plus the `modern` design. |
| S4 | Pre-processor interface, registry, cache and DAG. Port the core and astro catalogues, each with a fixture smoke test, a determinism check and a sidecar-data check. | — |
| S5 | **Pandoc integration** (D12: converter backend, `bibliography`/citeproc, docx/odt/epub) and **LaTeX fragment export** (D11.2, `numbers.tex`). Full Typer CLI (`render`, `validate`, `pack`, `unpack`, `inspect`, `new`, `preprocess`, `export tex`, `templates`, `layouts`, `preprocessors`, `spec`, `mplstyle`, `agent`, `mcp serve`), public `__all__`, MCP server, skill. Push tag `v1.0.0rc1` (pre-release; no gate needed, but recorded in STATUS). | — |
| S6 | Sphinx site, llms files, per-page md, gallery, Pages deploy workflow | — |
| S7 | Freeze the compat corpus, CHANGELOG, clean-room install from the git URL, `v1.0.0` release | **HG-S2**: release sign-off, plus the optional question of a Zenodo DOI for the software |
| S8 (after M5, optional) | `images` extra (`compare_stamps` plots and metrics) → v1.1.0 | — |

### Part B: migration (`phd/2_dataset`, branch `p2/reports-scireport`)

| Phase | Work | Gate |
|---|---|---|
| M0 | **Preconditions:** P2 HG5 is closed and the scireport tag is public. Snapshot the current `docs/*.md` as the baseline (git-ignored). Write the parity tool `gzms report parity`, which compares every baseline table (header and rows) and every numeric token with the new docs. | — |
| M1 | Add `"scireport[pdf,astro] @ git+https://github.com/nmcardoso/scireport@v1.0.0"` and `allow-direct-references`, then `uv lock`. **No local paths in pyproject or uv.lock**; local editable installs are allowed only in a scratch venv. Then: `scireport agent install-skill --dest ../.agents/skills`, a skill drift test, `make check-skills` in 1_review, an AGENTS.md skills entry, apt pango in CI, and the `.gitignore` rules `/docs/*.pdf` and `/docs/figures/`. | — |
| M2 | New `gzms/report/` package: section builders that read the tables the steps already write (no recomputation), the template `gzms/report/template/` (`md_file` keeps the 11 current file names and H1 headings), and the steps' f-string renderers replaced by `write_pages(...)`. The obsolete `_md_table`, `_md`, `_cell` and `_pct` helpers are removed. `docs data-model` (README sync, I14) and `method.md` are unchanged; the PDF includes them as chapters. | — |
| M3 | New figures (Appendix F; below). gzms plotting functions get a `style=` keyword: report figures use `scireport.mplstyle_path()`, paper figures keep `astro.mplstyle`. | — |
| M4 | `gzms report` CLI and `make report` write `docs/*.md` plus `docs/dataset_overview.md`, `docs/index.md`, `docs/figures/*.png` and `docs/gzms-report.pdf`. PDF order: cover, metrics, TOC, overview, method, registry and licences, ingest, cross-match and the RC3 study, splits, taxonomy, labels, co-occurrence, QA and the divergence study, data-model appendix, CSV attachments. Update the tests. | **HG-M1**: the parity report has 0 unexplained losses; figure set; redshift sentinel policy (exclude z = 999 and z < 0 from histograms, with counts in the caption); report-figure style |
| M5 | v1.1.0: bump `pyproject` and `CITATION.cff`, CHANGELOG, DECISIONS, README (`make report`, pango), release rebuild with the data-product SHA256SUMS equal to v1.0.0, `export-repo`, clean-room `make report` | **HG-M2**: v1.1.0 sign-off; the human tags it |

**New figures (M3).** The prompt requires spatial distribution, concentration and statistics.

1. Sky density of all objects: HEALPix order 7, Mollweide, objects per deg², log scale.
2. Mean `n_sources` per pixel (survey concentration and overlap), plus the `n_sources` multiplicity bars.
3. Per-source footprint small multiples for the 30 crowd and expert sources (members joined to objects).
4. Train/val/test split map, with the refined pixels marked.
5. Objects per source and rows attached (log bars).
6. 21×21 crowd overlap heat map.
7. Pair separation histograms: the existing figure, restyled.
8. Redshift distribution, stacked by `redshift_source`.
9. `size_arcsec` distribution.
10. `max_offset_arcsec` and `nearest_object_arcsec` distributions.
11. Total votes per question, from pre-tallied counts streamed from `reliability.parquet`.
12. Grades A–D per question (`plot_grades` and stacked shares).
13. JSD and q-value distributions, plus the existing shift curves.
14. Heat map of 28 questions × 16 flags.
15. Co-occurrence heat maps for the focus pairs (promised in plan §8.7, never built).
16. Expert AUC and T-type Spearman bars.
17. Split balance (per-source shares, redshift marginals per split).
18. Ingest kept fractions per source.

**Subagent and model policy** (prompt golden rule):

- **haiku** (the copied `explore` and `docstring` agents): copying files and fonts, docstring passes, fixture
  regeneration, parity summaries, link checks.
- **sonnet**: porting individual plot functions, CSS-to-LaTeX components, reference doc pages, and gzms section
  builders after the first one.
- **Main model:** spec, validation, render core, compatibility, layout design, the MCP design, the first gzms
  section, and gate write-ups.
- Every subagent prompt names the files and the acceptance tests.

**Gate write-ups** follow monorepo golden rule 3: purpose first, every term defined, evidence with units and
denominators, labelled options with their consequences, a recommendation, and self-contained wording. scireport
gates go in `scireport/STATUS.md`; migration gates go in `2_dataset/STATUS.md`.

## Key risks (go into the plan's risk register)

- **WeasyPrint needs the pango system libraries.** Import it lazily, skip PDF tests when it is missing, and add apt
  and brew steps in CI.
- **LaTeX/WeasyPrint visual drift.** The theme-consistency test, plus the HG-S1 side-by-side review.
- **PDF byte determinism.** Verify for each engine and record the result. The PDF is git-ignored, so this is
  best-effort; md and PNG must be byte-stable.
- **mistletoe's LaTeX output for GFM tables and math.** Wrap it in a restricted Markdown subset with tests.
- **Starting the migration before P2 HG5 closes** would change the code behind v1.0.0. M0 enforces the
  precondition.
- **Scope creep from porting all 45 MOSAICS plots.** The image-comparison set is deferred to S8.
- **`phd/.mcp.json` contains a committed W&B token.** Never copy it, and flag it to the user.
- **Windows CI.** WeasyPrint needs GTK/pango through MSYS2, TeX Live installs are slow, and line endings can break
  golden files. Mitigations: cache TeX Live (`setup-texlive-action` does by default), keep `eol=lf` fixtures, and
  if Windows WeasyPrint proves impractical, record it as unsupported rather than skipping silently.
- **Python 3.15 wheels.** pyarrow, matplotlib and weasyprint dependencies may lag. Check at S0, and mark the job
  experimental only with a dated DECISIONS entry.
- **Two markup engines can diverge.** Golden tests run on both, the differences are documented, and there is no
  automatic engine switching.
- **pdflatex lacks OTF fonts.** Fall back with a warning; lualatex is the default.

## Verification (written into the plan's "done when" lists)

**scireport:**

- `make check`: ruff format and lint, mypy strict, pytest with coverage ≥ 90 %.
- `make examples`: 3 examples × 2 layouts × (md, html, tex, pdf via weasyprint, pdf via latex with lualatex,
  xelatex and pdflatex), plus docx through pandoc.
- `scireport export tex`: the fragments and `numbers.tex` compile in a stub document.
- Golden tests pass for both markup engines (mistletoe and pandoc).
- GitHub Actions: every matrix job of D13 is green on `main` at `https://github.com/nmcardoso/scireport` (or
  documented as experimental or unsupported), and the Pages site is live.
- `make compat`: the frozen corpus.
- Two renders give byte-identical md, html and tex.
- `make docs`: `llms.txt`, `llms-full.txt` and the per-page `.md` files exist; linkcheck passes.
- MCP: a test with the SDK's in-memory client.
- `scireport agent install-skill --check`.
- Clean-room: `uv venv`, then `uv pip install "scireport[pdf,astro] @ git+https://github.com/nmcardoso/scireport@v1.0.0"`, then render an example.

**2_dataset:**

- `uv sync --locked` fetches scireport from GitHub; grep shows no `path =` or `file://` entries.
- `make report` writes the same 11 file names with the same H1 headings, plus the overview page, figures and PDF.
- Parity tool: 0 unexplained missing tables or numbers.
- A rebuild gives byte-identical md and PNG files.
- `make check` (mypy strict, coverage ≥ 85 %) passes, and CI is green on ubuntu and macos.
- The v1.1.0 data-product hashes equal v1.0.0's.
- `make export-repo` works, and so does a clean-room `make report`.
- `make check-skills` in 1_review passes.
