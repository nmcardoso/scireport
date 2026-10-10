# Thin wrappers around uv; the pipeline also runs without make.
.PHONY: setup check lint format typecheck test test-integration compat schema skill docs examples clean

setup:            ; uv sync --locked --all-extras --group dev --group docs
check:            lint typecheck test
lint:             ; uv run ruff format --check . && uv run ruff check .
format:           ; uv run ruff format . && uv run ruff check --fix .
typecheck:        ; uv run mypy scireport tests
test:             ; uv run pytest -m "not integration" --cov=scireport --cov-report=term-missing
test-integration: ; uv run pytest -m integration
# The frozen compat corpus (ADR-0008); also part of `make test`.
compat:           ; uv run pytest tests/compat
# Regenerates the schema of the CURRENT spec version. Never for a released version: its file is frozen.
schema:           ; uv run scireport spec schema -o scireport/spec/schemas/data-$$(uv run scireport spec version).schema.json
# Rewrites the generated tables of the packaged skill from the code (a test fails when they are stale).
skill:            ; uv run python -m scireport.agent.skillgen
docs:             ; uv run sphinx-build -W --keep-going -b html docs docs/_build/html
# 3 examples x 2 layouts x (md, html, tex, pdf via weasyprint, pdf via lualatex, xelatex and pdflatex)
# into examples/_out/. Needs pango and TeX Live; `make examples EXAMPLES_ARGS=--no-pdf` skips the PDFs.
examples:         ; uv run python examples/render_all.py $(EXAMPLES_ARGS)
clean:            ; rm -rf docs/_build examples/_out .coverage htmlcov dist build
