# Repository conventions

These are conventions, not architecture decisions; they can change without a superseding ADR.

## Package layout

Flat layout `scireport/` with `spec/`, `bundle/`, `validate/`, `render/` (`outputs/`, `pdf/`),
`layouts/{default,modern}/1/`, `templates/{generic,kitchen-sink}/1/`, `styles/`, `preprocess/{core,astro}/`,
`agent/`, `cli/` and `logging_utils.py`. Other folders: `tests/{unit,property,golden,integration,compat,fixtures}`,
`examples/`, `docs/`, `.github/workflows/{ci,docs,release}.yml`.

## Agent files

`.agents/AGENTS.md` is the single instruction file; `AGENTS.md` and `CLAUDE.md` are symlinks to it.
`.agents/agents/` holds the subagent definitions (copied from datex; only `explore.md` is adapted), and
`.agents/skills/` holds a byte-identical copy of `python-logging` plus `scireport`, a symlink to the packaged skill.
`.claude/agents` and `.claude/skills` are symlinks into `.agents/`. A `.mcp.json` is never copied or committed.

## Style

`ruff` with `indent-width = 2`, `quote-style = 'single'`, line length 100; NumPy docstrings; `mypy --strict`;
coverage at least 90 %. `scireport/logging_utils.py` is a byte-identical copy of the monorepo skill and is excluded
from format and lint. Because it is byte-identical, its display-name shortening still lists the monorepo package
prefixes; scireport loggers therefore show their full dotted names.

## Dependencies

Core: jinja2, pydantic 2, pyyaml, typer, numpy, pyarrow, matplotlib, mistletoe. Extras: `pdf` (weasyprint),
`astro` (astropy, astropy-healpix), `pandoc` (pypandoc-binary), `mcp`; `images` arrives in phase S8. Groups: `dev`,
`docs`. pandas is optional. Dependencies are added with `uv add`, so the latest versions become the lower bounds.

## Fonts

The Inter and IBM Plex Mono subsets are copied from datex together with `OFL.txt`.

## Continuous integration

`ci.yml` runs on push and pull request with `fail-fast: false`:

| Job | Matrix | Runs |
|---|---|---|
| `lint` | ubuntu, Python 3.12 | `ruff format --check`, `ruff check`, `mypy --strict` |
| `test` | ubuntu x Python 3.12 to 3.15 | unit, property, golden and compat tests; coverage at least 90 % |
| `lowest` | ubuntu, 3.12 | `uv sync --resolution lowest-direct`, then the tests |
| `pdf-weasyprint` | ubuntu x 3.12, 3.15 | PDF integration tests (pango from apt) |
| `pdf-latex` | ubuntu x 3.12, 3.15 | TeX Live from `.github/tl_packages` |
| `pandoc` | ubuntu, 3.12 | `scireport[pandoc]` tests |
| `examples` | ubuntu | renders every example (from phase S3) |
| `docs` | ubuntu | Sphinx build with `-W` plus linkcheck |

`docs.yml` deploys GitHub Pages on `main`. `release.yml` builds the sdist and wheel on a tag, creates the GitHub
release, and runs a clean-room install from the `git+https://...@<tag>` URL on Linux.

Only Linux is built and tested (DECISIONS, 2026-10-09). The code stays portable (`pathlib`, `.gitattributes`
forces `eol=lf`, outputs are written with `newline='\n'`, tests never rely on the repository's symlinks), but
macOS and Windows are not checked by CI and are not supported.
