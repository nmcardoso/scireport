# Pre-processors

A **pre-processor** is a registered, typed, cached Python function that turns a table of the bundle into a
figure and/or a small summary table or number. The data file lists **steps** by name; scireport checks all
of them first, runs them in dependency order, caches the results by content and stores each figure with the
small table it was drawn from (a sidecar `.parquet`), because a bundle holds summaries, not raw catalogues.
Figures come out in the layout's matplotlib style (see `mplstyle.md`). Use one when a figure or a summary
is a standard operation on a table (histogram, sky map, Q-Q plot); otherwise draw the figure yourself and
`Report.add_figure` it.

## Steps in a data file

```yaml
values:
  matches:
    kind: table
    asset: assets/tables/matches.csv       # columns: id, separation_arcsec
preprocess:
  - name: core.histogram                   # a registered name (add @1 to pin a version)
    id: separations                        # optional: labels the step in logs; seeds its randomness
    inputs: {table: matches}               # input port -> key of an existing value (or of an earlier step)
    outputs: {figure: fig.separations}     # output port -> key the result is stored under
    params: {column: separation_arcsec, bins: 20, x_label: Separation (arcsec)}
outline:
  - title: Matches
    children: [fig.separations]
```

- `name` is a registered name only. `module:function` would import and run code from the data file, so it is
  refused (`E605`) unless you pass `--allow-import` (Python: `allow_import=True`). Do that only for files you
  trust.
- A step **owns** its `outputs` keys: if the bundle already holds a value there (a bundle written back after
  a run) the step replaces it. A step may read the output of an earlier step.
- `params` are validated from the function signature: a wrong type, an unknown name or a missing required one
  is `E602` with the pointer (`/preprocess/0/params/colum`) and a "did you mean" hint.
- Ports have kinds (`table`, `figure`, `number`, ..., `any`). A port that does not fit is `E603`; two steps
  writing one key, or a cycle, `E604`; an unknown name `E601`.

```console
$ scireport validate bad          # bins: many, colum: x, and a misspelt name
E602 /preprocess/0/params/colum: core.histogram@1: parameter colum: Extra inputs are not permitted. Did you mean 'column'?
E601 /preprocess/1/name: no pre-processor named 'core.histgram'. Did you mean 'core.histogram'?
```

`validate` and `render` run the steps themselves (`--no-preprocess` skips them, `--cache-dir` moves the cache).
The `scireport preprocess` command runs only the steps:

```console
$ scireport preprocess my-bundle --work-dir work
separations              core.histogram@1  miss  b7e497b57306
$ scireport preprocess my-bundle --work-dir work           # again: nothing runs
separations              core.histogram@1  hit   b7e497b57306
```

New files (`assets/figures/fig.separations.png`, `.pdf`, `.data.parquet`) and a run record `preprocess.json`
go to `--work-dir` (default `scireport-work/`); the source bundle is untouched. `-o PATH` writes the
pre-processed bundle (a directory or a `.zip`), `--write-back` replaces the source with it (the steps stay
in it, and running again is a cache hit). `--json` prints `{"ok", "work_dir", "steps": [{label, name,
version, cache, key, outputs}]}`.

## Cache and determinism

A result is cached under the SHA-256 of the pre-processor name and version, its validated parameters, the
content hashes of its inputs, the keys it writes, its seed, the scireport version and the layout's style.
Same inputs never run twice; changing any of them is a miss. The directory is `--cache-dir`, else
`$SCIREPORT_CACHE_DIR`, else `$XDG_CACHE_HOME/scireport/preprocess`; `--no-cache` neither reads nor writes it.

Randomness is seeded: each step's seed comes from `--seed` (default 0) and the step `id`; draw random numbers
only from `ctx.rng()`. The same inputs and versions give the same figure bytes. A released pre-processor
version is frozen: a change that alters a figure or number is a new version registered beside the old one.

## Describe before you use

```console
$ scireport preprocessors                       # name, extra needed, one line
$ scireport preprocessors core.histogram
core.histogram@1: Histogram of a column of samples, or of counts tallied elsewhere.
inputs:
  table: table  Samples, or a tally of counts per bin
outputs:
  figure: figure  The histogram
parameters:
  column (required)  string
  bins = 'auto'  [{'type': 'integer'}, {'enum': ['auto', 'fd', ...], 'type': 'string'}]
  counts_column = None  ...
  log = False  boolean
  ...
```

`scireport preprocessors NAME --json` gives `ref`, `name`, `version`, `summary`, `requires` (the extra, or
null), `inputs` and `outputs` (port -> `kind`, `optional`, `description`) and `params` (a JSON Schema with
`properties` and `required`). The MCP tool `describe_preprocessor` returns the same.

## Catalogue

Every entry is version 1. Sky maps need the `astro` extra (astropy and astropy-healpix:
`uv add "scireport[astro]"`); without it the step fails with `E607` and an install hint. The other `astro.*`
plots (colour diagrams, number counts, photometry diagnostics) run in the core install.

<!-- generated:preprocessors -->
| Name | Version | Extra | What it does |
|---|---|---|---|
| `astro.color_color` | 1 |  | Hybrid density colour-colour diagram. |
| `astro.color_magnitude` | 1 |  | Hybrid density colour-magnitude diagram. |
| `astro.footprint` | 1 | astro | Coverage footprint of one or several catalogues on a Mollweide sky map. |
| `astro.magnitude_residual` | 1 |  | Draw a magnitude residual against magnitude as a hexagon density. |
| `astro.number_counts` | 1 |  | Differential number counts, log-scaled, against the Euclidean reference slope. |
| `astro.sky_density` | 1 | astro | Mollweide sky map of source density on a HEALPix grid. |
| `astro.sky_grid` | 1 | astro | Small multiples: one Mollweide sky-density panel per group, on one shared colour scale. |
| `astro.snr_magnitude` | 1 |  | Signal-to-noise against magnitude, with the 5-sigma depth marked. |
| `astro.zeropoint_offsets` | 1 |  | One band's cross-survey magnitude offset against colour, as a hexagon density. |
| `core.achieved_vs_target` | 1 |  | Paired horizontal bars of what was asked for and what came out. |
| `core.bar` | 1 |  | Horizontal bars of a table of labelled counts. |
| `core.corner` | 1 |  | Corner plot of two to eight numeric columns. |
| `core.density_scatter` | 1 |  | Scatter of two columns: hexagons where it is crowded, individual points where it is not. |
| `core.distribution` | 1 |  | Box or violin plot of a per-object value, one per group. |
| `core.duration_bars` | 1 |  | Wall-clock seconds per artifact, with the reused ones hatched. |
| `core.funnel` | 1 |  | Rows surviving each cumulative step, and rows removed by each step. |
| `core.heatmap` | 1 |  | Heatmap of a matrix given as a long table (one row per cell). |
| `core.histogram` | 1 |  | Histogram of a column of samples, or of counts tallied elsewhere. |
| `core.metric_scatter` | 1 |  | Compare a per-object metric of the left dataset with the right one, against ``y = x``. |
| `core.pp` | 1 |  | P-P plot of a sample against a normal distribution or a second sample. |
| `core.pvalue_strip` | 1 |  | Every p-value of a family of tests on one logarithmic axis, against its threshold. |
| `core.qq` | 1 |  | Q-Q plot of a sample against a normal distribution or a second sample. |
| `core.separation_histogram` | 1 |  | Histogram of match separations, with the match radius marked. |
| `core.split_balance` | 1 |  | One split's arms (train, validation, test) on one stratifier, normalised and overlaid. |
| `core.split_marginals` | 1 |  | Each split's marginal on one stratifier, normalised and overlaid. |
| `core.stacked_shares` | 1 |  | One stacked horizontal bar per group, each segment a label's share of the group. |
| `core.table_profile` | 1 |  | Per-column profile of a table, with its size. |
<!-- /generated -->

## Write and register your own

A pre-processor is `f(ctx, *, <inputs>, <parameters>) -> {port: value}` under `@preprocessor`:

- The name is dotted (`mypkg.median_plot`) and `version` is an integer.
- `inputs` and `outputs` map port names to `Port(kind, optional=False, description='')`. Each input arrives as
  a keyword argument with the port's name (a `table` is a `pyarrow.Table`; other kinds are the value model).
- Every other keyword argument is a **parameter**; its type annotation and default define the pydantic
  validation, so a missing default makes it required. Unknown params are rejected.
- Return a dict with one value per output port: a value model or an envelope dict (`{'kind': 'number',
  'value': ..., 'unit': ...}`). An optional port may be left out.

`ctx` helpers:

| Member | Does |
|---|---|
| `ctx.value(key)` / `ctx.load_table(key)` | any value of the bundle (or of an earlier step) / a table as `pyarrow.Table` |
| `ctx.mplstyle()` | context manager applying the layout's matplotlib style |
| `ctx.figure(width, height, nrows, ncols)` | a figure at final size (`width` is a fraction of the page frame) and its axes |
| `ctx.look.series(i)` | the i-th chart colour of the layout |
| `ctx.save_figure(fig, data=..., alt=..., caption=None, width=1.0, port='figure')` | stores PNG and PDF **and the data** drawn; returns the `figure` value. `data` and a non-blank `alt` are required |
| `ctx.save_table(data, port='table', columns=None, caption=None)` | stores a table (Parquet or CSV); returns the `table` value |
| `ctx.rng()` / `ctx.seed` | a seeded numpy generator / the step's seed |
| `ctx.log` | a logger (`ctx.log.info('...')`); never `print` |

A figure that is rebuilt from the saved data must draw **only from `data`**. The built-ins split the work into
`compute_x(table, ...)` (a small tidy table) and `render_x(ctx, data, ...)`; do the same if the figure must be
reproducible from the bundle alone.

A minimal complete example (this file was run against the `matches` bundle above):

```python
# mypkg/steps.py
import pyarrow as pa
import pyarrow.compute as pc

from scireport.preprocess import Context, Port, preprocessor


@preprocessor(
  'mypkg.median_plot',
  version=1,
  inputs={'table': Port('table', description='Table with a numeric column')},
  outputs={
    'figure': Port('figure', description='Sorted values with the median marked'),
    'median': Port('number', description='The median of the column'),
  },
)
def median_plot(ctx: Context, *, table: pa.Table, column: str, unit: str | None = None) -> dict:
  """Plot a column in sorted order and report its median."""
  order = pc.sort_indices(table[column])
  ordered = table[column].take(order).to_pylist()
  median = pc.approximate_median(table[column]).as_py()
  ctx.log.info('median of %s is %.4g', column, median)
  with ctx.mplstyle():
    figure, ax = ctx.figure(1.0, 3.0)
    ax.plot(range(len(ordered)), ordered, color=ctx.look.series(0))
    ax.axhline(median, color=ctx.look.series(1))
    ax.set_xlabel('Rank')
    ax.set_ylabel(column)
  data = {'rank': list(range(len(ordered))), 'value': ordered}
  return {
    'figure': ctx.save_figure(figure, data=data, alt=f'Sorted {column} with its median'),
    'median': {'kind': 'number', 'value': median, 'unit': unit, 'format': '.3f'},
  }
```

Use it in a data file like a built-in:

```yaml
preprocess:
  - name: mypkg.median_plot
    id: median
    inputs: {table: matches}
    outputs: {figure: fig.median, median: stats.median_sep}
    params: {column: separation_arcsec, unit: arcsec}
```

There are two ways to make the name resolve:

1. **Plugin (preferred).** Register it through the entry-point group `scireport.preprocessors` in the
   package's `pyproject.toml`, install the package, and the name works everywhere with no flag:

   ```toml
   [project.entry-points."scireport.preprocessors"]
   median_plot = "mypkg.steps:median_plot"
   ```

   `scireport preprocessors` then lists `mypkg.median_plot@1`. A plugin that fails to import is `E608`.
2. **In the same process.** The decorator registers the function when its module is imported, so import
   that module before `render_bundle` / `preprocess_bundle`. From the command line, name it `mysteps:median_plot` in the data file and pass
   `--allow-import` (with the module on `PYTHONPATH`); only for files you trust.

Rendering that bundle writes `md/figures/fig.median.png` and the line `**Median sep:** 0.313 arcsec`.
