# ADR-0003: Templates (structure) and layouts (look) are separate directories

- Status: Proposed (approval at HG-S0)
- Date: 2026-10-09

## Decision

A **template** is a directory: `template.yaml` declares `fields` (key or wildcard to kind, required, table
columns and dtypes, figure renditions), the supported `formats` and a compatible spec range; `report.j2` is the
**format-neutral** body calling component functions (`c.chapter`, `c.table(data.x)`, `c.figure`, `c.metrics`,
`c.details`, ...) and writing prose inside `{% filter md %}`, which mistletoe converts to HTML or LaTeX.
Optional per-format overrides: `report.{md,html,tex}.j2`.

A **layout** is a directory: `layout.yaml` (formats, options with defaults, PDF engines, `mplstyle`,
`palette.yaml`, fonts) plus, per format, a `document` skeleton and a `components` macro file (`html/`,
`latex/`, `md/`) and CSS.

**Rendering:** the body is rendered first (outline and TOC collected in a single pass, as MOSAICS does), then the
layout skeleton wraps it. LaTeX files use LaTeX-safe Jinja delimiters (`((* *))`, `((( )))`, `((= =))`) because
`{%` and `{#` clash with TeX; neutral templates never contain raw TeX, so standard delimiters stay valid there.

**Environment:** `SandboxedEnvironment` with `StrictUndefined` and format-aware escaping. The MOSAICS number
filters are ported: `int`, `float`, `share`, `bytes`, `duration`, `pct`, `ppm`, `sci`, `compact`, `missing`,
`breakable`.

**Markdown split:** chapters with `md_file=` become separate `.md` files plus `index.md`.

**Built-ins:** templates `generic@1` (renders any bundle from its `outline`) and `kitchen-sink@1`; layouts
`default@1` and `modern@1`. Custom ones are loaded by path or through the entry-point groups
`scireport.templates` and `scireport.layouts`.

## Consequences

A project changes the look without touching its template, and the other way round. One neutral template yields
all formats. Components are the unit of porting from MOSAICS (see the plan's component catalogue).
