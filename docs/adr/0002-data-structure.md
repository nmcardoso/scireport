# ADR-0002: Semantic keys with typed envelopes

- Status: Proposed (approval at HG-S0)
- Date: 2026-10-09

## Context

The data file is a key-value mapping that a template consumes. Keys could be scoped by value type
(`tables.pairs`, `figures.sky`) or be purely semantic (`crossmatch.pairs`).

## Decision

**Manifest blocks:** `scireport` (spec version, e.g. `"1.0"`), `meta` (title, subtitle, authors, date, version,
pipeline, footer, abstract, keywords, language), `render` (template, layout such as `default@1`, formats,
`pdf_engine`, layout options), `outline` (optional; used only by the built-in `generic` template), `values`
(key to value), `preprocess` (list of steps), `provenance` (generator, input hashes).

**Keys** are semantic dotted paths (`crossmatch.pairs`); each segment matches `[a-z0-9_-]+`. The **type lives in
the value** (`"kind": "table"`), so changing a type never renames a key, templates address meaning, and one
namespace prevents collisions. The `assets/` folder is still organised by kind, for browsing.

**v1.0 kinds:** `text` (plain or markdown), `number` (value, unit, format, uncertainty or interval, missing),
`bool`, `date`, `list`, `mapping`, `table` (Parquet, CSV or inline; per-column label, unit, format, align,
width, description; `row_status` verdicts; cell emphasis; `max_rows` with an attachment fallback), `figure`
(renditions, caption, **required** alt text, width fraction, sidecar data), `image`, `math`, `code`, `metrics`,
`status`, `alert`, `flow`, `attachment`.

Bare JSON scalars, lists and objects are shorthand and are canonicalised on load.

## Alternatives considered

Type-scoped keys (`tables.*`, `figures.*`): rejected because a table that becomes a figure would rename its key,
breaking every template and every stored bundle, and because two kinds could not share a name.

## Consequences

Every value is self-describing, so validation, rendering and agents need no external schema to interpret a
bundle. The kind table is part of the frozen spec (ADR-0008).
