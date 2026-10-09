# ADR-0008: Backward compatibility is a golden rule

- Status: Accepted (HG-S0, 2026-10-09)
- Date: 2026-10-09

## Decision

**Versioning.** The spec version is `MAJOR.MINOR` and appears in every bundle, template and layout. Minor versions
are additive; a reader reads every older minor natively; a bundle from a newer minor gives `E5xx` plus an upgrade
hint. A major bump ships a pure dict-to-dict migration (`spec/migrations/`) and `scireport spec migrate`. Frozen
JSON Schemas (`spec/schemas/data-1.0.schema.json`, ...) are generated from pydantic and checked for drift.

**Built-in layouts and templates are versioned and frozen** (`layouts/default/1/`). A visual change means a new
version; the `default` alias points to the latest. `pack` pins the resolved version into the bundle, so a later
re-render is identical.

**Compat corpus.** `tests/compat/spec-<v>/<case>/` holds bundles and their expected md, canonical HTML (port of
`report_html.canonicalize`), tex and PDF text hash. Fixture hashes are listed in `FROZEN.sha256`. CI fails if a
fixture or an output drifts.

**Python API.** Semver, an API snapshot test, at least one minor version of deprecation warnings, stable error
codes.

## Consequences

Old reports keep rendering identically. Improvements ship as new versions, never as edits to frozen ones.
