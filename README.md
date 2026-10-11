# scireport

Data-centric scientific report engine. One **data file** (a report bundle), one **template** (structure) and one
**layout** (look) go in; **Markdown** (for LLMs), **HTML**, **LaTeX** and **PDF** (for humans) come out.

> **Version 1.0.0.** The data-file specification 1.0, the built-in templates (`generic@1`, `kitchen-sink@1`) and
> layouts (`minimal@1`, `default@1`, `modern@1`) are frozen: a report written today renders the same with every
> later 1.x release ([compatibility policy](https://nmcardoso.github.io/scireport/compatibility.html)). Supported:
> Linux, Python 3.12 to 3.14 (3.15 is experimental until `pyyaml` publishes wheels for it). macOS and Windows are
> not built or tested.

**Documentation:** <https://nmcardoso.github.io/scireport/>. For language models: [`llms.txt`](https://nmcardoso.github.io/scireport/llms.txt),
[`llms-full.txt`](https://nmcardoso.github.io/scireport/llms-full.txt), and a Markdown twin of every page (`.html` becomes `.md`).

Inspired by the MOSAICS report engine of `datex`, but standalone and data-centric.

## Quickstart

```bash
uv pip install "scireport[pdf] @ git+https://github.com/nmcardoso/scireport@v1.0.0"
```

Write a data file (a *report bundle*) from Python, or by hand as YAML (`scireport new my-report/`):

```python
from scireport import Report

report = Report('Cross-match report', authors=['N. Cardoso'], version='1.1.0')
report.add_number('crossmatch.n_pairs', 3061, format='int')
report.add_table('crossmatch.pairs', table)            # pyarrow, pandas or a dict of columns
report.add_figure('crossmatch.separations', fig, alt='Histogram of pair separations')
report.write('crossmatch.scireport.zip')              # byte-reproducible ZIP, JSON manifest
```

Look inside it, check it and render it:

```bash
scireport inspect crossmatch.scireport.zip            # what is in it, and is it intact (--json for agents)
scireport validate crossmatch.scireport.zip           # every problem at once, each with a stable code
scireport render crossmatch.scireport.zip -o out -f md -f html -f pdf    # PDF through WeasyPrint
scireport render crossmatch.scireport.zip -o out -l modern -f html -f pdf
scireport render crossmatch.scireport.zip -o out -f pdf --pdf-engine latex --latex-engine xelatex
```

Other commands: `unpack` (ZIP to a directory), `pack` (a hand-written YAML directory to a sealed ZIP), `spec schema`
(JSON Schema of the manifest), `export tex` (tables, figures and a `numbers.tex` for a manuscript), `mcp serve` and
`agent install-skill` (for language-model agents).

Figures that look like the report: `with scireport.mplstyle('default'): fig, ax = scireport.figure(0.8, 3.0)`
(see `docs/styles.md`). `make examples` renders three examples with both layouts to every output.

Exit codes: 0 ok, 1 runtime error, 2 invalid input (every problem is listed, each with a stable code such as
`E101`), 3 missing system dependency.

## Install (from the public repository)

```bash
uv pip install "scireport @ git+https://github.com/nmcardoso/scireport@v1.0.0"
# with extras: pdf (WeasyPrint), astro (HEALPix sky maps), pandoc (citations, Word/ODT/EPUB), mcp (agent server)
uv pip install "scireport[pdf,astro] @ git+https://github.com/nmcardoso/scireport@v1.0.0"
```

In a project's `pyproject.toml`: `scireport = { git = "https://github.com/nmcardoso/scireport", tag = "v1.0.0" }`
under `[tool.uv.sources]`, or the direct reference `scireport @ git+https://github.com/nmcardoso/scireport@v1.0.0`
in `dependencies`. Projects that depend on scireport install it from GitHub, never from a local path, so that a
referee can reproduce the environment. Tags are listed at <https://github.com/nmcardoso/scireport/tags>.

### System dependencies (only for the matching feature)

Markdown, HTML and LaTeX output need nothing beyond Python. A missing system dependency makes the command exit with
code 3 and print an install hint.

| Feature | Needs |
|---|---|
| `pdf` extra (WeasyPrint) | pango and HarfBuzz: `apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0` |
| LaTeX PDF engine (`--pdf-engine latex`) | TeX Live with `latexmk`, `lualatex` (or `xelatex`, `pdflatex`) and the packages in [`.github/tl_packages`](.github/tl_packages); `biber` for citations |
| `pandoc` extra | nothing (`pypandoc-binary` bundles pandoc) |
| `astro` extra, `mcp` extra | nothing (Python wheels) |

## Develop

```bash
uv sync --all-extras --group dev --group docs
make check              # ruff format and lint, mypy --strict, pytest with coverage >= 90 %
make compat             # the frozen compat corpus only (tests/compat/)
make test-integration   # PDF engines and pandoc (need the toolchains above)
make docs               # the site (HTML, a Markdown twin per page, llms files) in docs/_build/site
```

Design decisions are in [`docs/adr/`](docs/adr/); repository conventions are in
[`docs/conventions.md`](docs/conventions.md); work in progress is tracked in [`STATUS.md`](STATUS.md) and
[`DECISIONS.md`](DECISIONS.md). Agent instructions are in [`.agents/AGENTS.md`](.agents/AGENTS.md).

## Licence

GPL-3.0-only. The vendored fonts in `scireport/styles/fonts/` keep their own licences, shipped next to them: Inter,
IBM Plex Mono and IBM Plex Serif under the SIL Open Font Licence 1.1 (`OFL.txt`), and TeX Gyre Pagella, Heros and
Cursor under the GUST Font Licence (`GFL.txt`).

## Citing

If you use scireport in a publication, cite it as described in [`CITATION.cff`](CITATION.cff) (GitHub shows a
"Cite this repository" box).
