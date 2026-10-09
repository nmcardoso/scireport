# scireport

Data-centric scientific report engine. One **data file** (a report bundle), one **template** (structure) and one
**layout** (look) go in; **Markdown** (for LLMs), **HTML**, **LaTeX** and **PDF** (for humans) come out.

> **Status: pre-alpha (phase S0).** The repository skeleton, tooling, CI matrix and architecture decision records
> exist; the engine itself is built in phases S1 to S7. Nothing here is usable for reports yet.

Inspired by the MOSAICS report engine of `datex`, but standalone and data-centric.

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
| `pdf` extra (WeasyPrint) | pango and HarfBuzz: `apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0`, `brew install pango`, or MSYS2 `mingw-w64-ucrt-x86_64-pango` (Windows) |
| LaTeX PDF engine | TeX Live with `latexmk`, `lualatex` (see `.github/tl_packages`) |
| `pandoc` extra | nothing (pypandoc-binary bundles pandoc) |

## Develop

```bash
uv sync --all-extras --group dev --group docs
make check              # ruff format and lint, mypy --strict, pytest with coverage >= 90 %
make test-integration   # PDF engines and pandoc (need the toolchains above)
make docs               # Sphinx site in docs/_build/html
```

Design decisions are in [`docs/adr/`](docs/adr/); repository conventions are in
[`docs/conventions.md`](docs/conventions.md); work in progress is tracked in [`STATUS.md`](STATUS.md) and
[`DECISIONS.md`](DECISIONS.md). Agent instructions are in [`.agents/AGENTS.md`](.agents/AGENTS.md).

## Licence

GPL-3.0-only. Vendored fonts (added in phase S3) are under the SIL Open Font Licence.
