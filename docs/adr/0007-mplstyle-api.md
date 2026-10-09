# ADR-0007: A shared matplotlib style, exposed as an API

- Status: Accepted (HG-S0, 2026-10-09)
- Date: 2026-10-09

## Decision

Shipped files: `styles/default.mplstyle` (port of `datex.mplstyle`: Inter, the MOSAICS palette, cividis) and
`styles/modern.mplstyle`.

Functions: `scireport.mplstyle(layout='default', *, rc=None)` is a context manager that registers the fonts and
restores the rcParams on exit; `scireport.mplstyle_path(layout)`; `scireport.palette(layout)`;
`scireport.figure(width=1.0, height=3.6, nrows, ncols)` gives frame-aware sizes (port of `Figures.grid`).

Saving strips PNG and PDF metadata so files are deterministic.

A consistency test ties `palette.yaml`, `tokens.css`, the mplstyle and the LaTeX colours together (port of
`test_report_theme`).

## Consequences

Figures made by consuming projects look like the report. Changing a colour is one edit, checked by the
consistency test.
