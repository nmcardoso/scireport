# Changelog

All notable changes are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/) and the
project uses [semantic versioning](https://semver.org/) for the Python API and `MAJOR.MINOR` for the data-file
specification (ADR-0008).

## [Unreleased]

### Added

- Phase S0: repository skeleton (`uv` project, GPL-3.0-only), ruff, mypy strict, pytest with coverage gate,
  pre-commit, Makefile.
- Agent files (`.agents/`, symlinks for Claude), copied subagents and the `python-logging` skill, a placeholder
  packaged `scireport` skill.
- Architecture decision records ADR-0001 to ADR-0011 (status: proposed) and repository conventions.
- GitHub Actions: lint, test matrix (Linux, macOS, Windows x Python 3.12 to 3.15), lowest-direct bounds, WeasyPrint,
  LaTeX and pandoc toolchain jobs, docs, Pages deploy and release workflows.
- Sphinx documentation skeleton with `llms.txt` and per-page Markdown builders.
