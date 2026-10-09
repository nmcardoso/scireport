# Thin wrappers around uv; the pipeline also runs without make.
.PHONY: setup check lint format typecheck test test-integration docs examples clean

setup:            ; uv sync --locked --all-extras --group dev --group docs
check:            lint typecheck test
lint:             ; uv run ruff format --check . && uv run ruff check .
format:           ; uv run ruff format . && uv run ruff check --fix .
typecheck:        ; uv run mypy scireport tests
test:             ; uv run pytest -m "not integration" --cov=scireport --cov-report=term-missing
test-integration: ; uv run pytest -m integration
docs:             ; uv run sphinx-build -W --keep-going -b html docs docs/_build/html
# Phase S3 replaces this body with the example renders (3 examples x 2 layouts x all formats).
examples:         ; uv run scireport --version && echo "examples are added in phase S3"
clean:            ; rm -rf docs/_build examples/_out .coverage htmlcov dist build
