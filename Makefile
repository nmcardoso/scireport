# Thin wrappers around uv; the pipeline also runs without make.
.PHONY: setup check lint format typecheck test test-integration compat compat-growth schema skill docs docs-linkcheck examples clean

setup:            ; uv sync --locked --all-extras --group dev --group docs
check:            lint typecheck test
lint:             ; uv run ruff format --check . && uv run ruff check .
format:           ; uv run ruff format . && uv run ruff check --fix .
typecheck:        ; uv run mypy scireport tests
test:             ; uv run pytest -m "not integration" --cov=scireport --cov-report=term-missing
test-integration: ; uv run pytest -m integration
# The frozen compat corpus (ADR-0008); also part of `make test`.
compat:           ; uv run pytest tests/compat
# The freeze lists may only grow since BASE (the corpus and the built-in layouts, templates and schemas).
BASE ?= origin/main
compat-growth:    ; uv run python tests/frozen.py $(BASE)
# Regenerates the schema of the CURRENT spec version. Never for a released version: its file is frozen.
schema:           ; uv run scireport spec schema -o scireport/spec/schemas/data-$$(uv run scireport spec version).schema.json
# Rewrites the generated tables of the packaged skill and of the docs pages from the code (a test fails when they are stale).
skill:            ; uv run python -m scireport.agent.skillgen
# The site: HTML, then a Markdown twin of every page into the same directory (published together),
# then a check of the result. `make docs DOCS_ARGS=--require-gallery` after `make examples` checks the gallery too.
SITE ?= docs/_build/site
docs:
	uv run sphinx-build -W --keep-going -b html -d docs/_build/doctrees docs $(SITE)
	uv run sphinx-build -W --keep-going -b markdown -d docs/_build/doctrees docs $(SITE)
	uv run python docs/check_site.py $(SITE) $(DOCS_ARGS)
docs-linkcheck:   ; uv run sphinx-build -b linkcheck -d docs/_build/doctrees docs docs/_build/linkcheck
# 3 examples x 2 layouts x (md, html, tex, pdf via weasyprint, pdf via lualatex, xelatex and pdflatex)
# into examples/_out/. Needs pango and TeX Live; `make examples EXAMPLES_ARGS=--no-pdf` skips the PDFs.
examples:         ; uv run python examples/render_all.py $(EXAMPLES_ARGS)
clean:            ; rm -rf docs/_build examples/_out .coverage htmlcov dist build
