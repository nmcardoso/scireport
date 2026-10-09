# ADR-0006: Pre-processors are registered, typed, cached, name-addressed functions

- Status: Proposed (approval at HG-S0)
- Date: 2026-10-09

## Decision

A pre-processor is registered with a decorator giving a name, a version and typed input and output ports:

```python
@preprocessor('core.histogram', version=1,
              inputs={'table': Port('table')}, outputs={'figure': Port('figure')})
def histogram(ctx: Context, *, table, column, bins='auto', counts_column=None, log=False, ...) -> dict[str, Value]
```

`Context` offers `ctx.value`, `ctx.load_table` (pyarrow), `ctx.mplstyle()`, `ctx.figure()`,
`ctx.save_figure(fig, data=...)`, `ctx.save_table`, `ctx.seed`, `ctx.log`. Parameters are validated by pydantic
from the signature.

**Discovery:** built-ins, the entry-point group `scireport.preprocessors`, and `register_preprocessor()`. Data
files refer to pre-processors **by name only**; `module:func` needs `--allow-import`.

**Execution:** the DAG is checked before anything runs; outputs go to a work directory and the input bundle is
untouched unless `--write-back`; results are cached by a hash of name, version, parameters, input content hashes,
the scireport version and the style hash.

**Catalogue** (ported from MOSAICS `R/plot.py` and `R/tables.py`): `core` (table_profile, bar, stacked_shares,
histogram, separation_histogram, funnel, density_scatter, metric_scatter, distribution, corner, pvalue_strip,
achieved_vs_target, duration_bars, split_marginals, split_balance, qq, pp, heatmap), `astro`
(sky_density, footprint, sky_grid, color_color, color_magnitude, number_counts, snr_magnitude,
magnitude_residual, zeropoint_offsets; astropy and astropy-healpix with matplotlib Mollweide, **no hats or
mocpy**), `images` (phase S8). Datex runtime-specific plots are not ported.

## Consequences

A bundle cannot execute arbitrary code by default. Results are reproducible and cacheable.
