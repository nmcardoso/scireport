# scireport

Data-centric scientific report engine. One **data file** (a report bundle), one **template** (structure) and one
**layout** (look) go in; **Markdown** (for LLMs), **HTML**, **LaTeX** and **PDF** (for humans) come out.

> **Status: pre-alpha (phase S3).** The data file, templates, the `default` and `modern` layouts, and the
> Markdown, HTML, LaTeX and PDF (WeasyPrint and LaTeX) outputs work. Pre-processors, pandoc and the agent kit
> arrive in phases S4 to S5.

Inspired by the MOSAICS report engine of `datex`, but standalone and data-centric.

## The data file in one minute

```python
from scireport import Report

report = Report('Cross-match report', authors=['N. Cardoso'], version='1.1.0')
report.add_number('crossmatch.n_pairs', 3061, format='int')
report.add_table('crossmatch.pairs', table)            # pyarrow, pandas or a dict of columns
report.add_figure('crossmatch.separations', fig, alt='Histogram of pair separations')
report.write('crossmatch.scireport.zip')              # byte-reproducible ZIP, JSON manifest
```

```bash
scireport inspect crossmatch.scireport.zip            # what is in it, and is it intact (--json for agents)
scireport unpack crossmatch.scireport.zip             # -> crossmatch.scireport/ (manifest + assets)
scireport pack my-report/ -o report.scireport.zip     # hand-authored YAML directory -> sealed ZIP
scireport spec schema                                 # JSON Schema of the manifest
```

```bash
scireport render crossmatch.scireport.zip -o out -l modern -f html -f pdf          # WeasyPrint PDF
scireport render crossmatch.scireport.zip -o out -f pdf --pdf-engine latex --latex-engine xelatex
```

Figures that look like the report: `with scireport.mplstyle('default'): fig, ax = scireport.figure(0.8, 3.0)`
(see `docs/styles.md`). `make examples` renders three examples with both layouts to every output.

Exit codes: 0 ok, 1 runtime error, 2 invalid input (every problem is listed, each with a stable code such as
`E101`), 3 missing system dependency.

## Install (from the public repository)

```bash
uv pip install "scireport @ git+https://github.com/nmcardoso/scireport"
# with extras: pdf (WeasyPrint), astro, pandoc, mcp
uv pip install "scireport[pdf,astro] @ git+https://github.com/nmcardoso/scireport@v1.0.0"
```

Projects that depend on scireport must install it from GitHub, never from a local path, so that a referee can
reproduce the environment. Tags are listed at <https://github.com/nmcardoso/scireport/tags>.

### System dependencies (only for the matching feature)

| Feature | Needs |
|---|---|
| `pdf` extra (WeasyPrint) | pango and HarfBuzz: `apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0` |
| LaTeX PDF engine | TeX Live with `latexmk`, `lualatex` (see `.github/tl_packages`) |
| `pandoc` extra | nothing (pypandoc-binary bundles pandoc) |

## Develop

```bash
uv sync --all-extras --group dev --group docs
make check              # ruff format and lint, mypy --strict, pytest with coverage >= 90 %
make compat             # the frozen compat corpus only (tests/compat/)
make test-integration   # PDF engines and pandoc (need the toolchains above)
make docs               # Sphinx site in docs/_build/html
```

Design decisions are in [`docs/adr/`](docs/adr/); repository conventions are in
[`docs/conventions.md`](docs/conventions.md); work in progress is tracked in [`STATUS.md`](STATUS.md) and
[`DECISIONS.md`](DECISIONS.md). Agent instructions are in [`.agents/AGENTS.md`](.agents/AGENTS.md).

## Licence

GPL-3.0-only. The vendored fonts (Inter and IBM Plex Mono, `scireport/styles/fonts/`) are under the SIL Open Font Licence 1.1.
