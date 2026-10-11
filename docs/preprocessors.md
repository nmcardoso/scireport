# Pre-processors

A **pre-processor** is a registered function that turns data in a bundle into a figure or a table: a histogram
from a column, a sky map from positions, a profile of a table (ADR-0006). The data file lists *steps* by name;
`scireport` checks them, runs them in dependency order, caches the results and stores the figures **together
with the data they were drawn from**.

```yaml
# scireport.yaml (excerpt)
values:
  matches:
    kind: table
    asset: assets/tables/matches.csv
preprocess:
  - name: core.histogram
    id: separations
    inputs: {table: matches}
    outputs: {figure: fig.separations}
    params: {column: separation_arcsec, bins: 40, x_label: Separation (arcsec)}
outline:
  - title: Matches
    children: [fig.separations]
```

`scireport render report/ -o out/` runs the steps first; `scireport preprocess report/` runs only them.

## Ports

A pre-processor has typed **input ports** and **output ports**. A port names a value kind (`table`, `figure`,
`number`, ... or `any`). In a step, `inputs` maps each input port to the key of a value and `outputs` maps each
output port to the key the result is stored under. An input that is a `table` reaches the function as a pyarrow
table; any other kind arrives as the value model. A step may read the output of an earlier step.

`params` are the parameters of the function, validated with pydantic from its signature: a wrong type, an
unknown name or a missing required parameter is reported with the pointer into the data file
(`/preprocess/0/params/bins`), what was expected and a "did you mean" hint. `scireport preprocessors NAME` prints
the ports and parameters of one pre-processor (`--json` for agents).

## The plan is checked before anything runs

Every step is resolved and checked first, and **all** problems are reported together:

| Code | Problem |
|---|---|
| `E601` | the name or version is not registered (with a suggestion) |
| `E602` | a parameter is wrong |
| `E603` | an input or output does not fit: a port not wired, an unknown port, a key nobody provides, a value of the wrong kind, a column the table lacks |
| `E604` | two steps write the same key, or the steps depend on each other in a cycle |
| `E605` | the step names `module:function` and `--allow-import` was not given |

A step *owns* the keys it lists in `outputs`: if the data file already holds a value at that key (a bundle that was
written back after a run) the step replaces it. A key that is also the prefix of another key is `E102`, as always.

## Safety: by name, not by code

A data file refers to a pre-processor **by registered name only**. A name such as `my_package.steps:histogram`
imports and runs that code, so it is refused unless you pass `--allow-import` (`allow_import=True` in Python).
Only do that for files you trust. Pre-processors come from three places: the built-in catalogue, the entry-point
group `scireport.preprocessors` of installed packages, and `scireport.preprocess.register_preprocessor()`.

## Where results go

`scireport preprocess SOURCE` writes the new files (`assets/figures/...`, `assets/tables/...`) and a run record
`preprocess.json` to the **work directory** (`--work-dir`, default `scireport-work/`) and leaves SOURCE untouched.
`--output PATH` writes the pre-processed bundle as a new bundle, and `--write-back` replaces SOURCE with it (the
steps stay in the file; running again is a cache hit that replaces the same keys). The run record holds no times,
so two runs give the same record.

## The cache

A result is cached under the SHA-256 of: the pre-processor name and version, its validated parameters, the content
hashes of its inputs (the envelope of each value, which includes the hash of its asset), the keys it writes to, its
seed, the scireport version and the hash of the layout's style and palette files. The same inputs never run twice;
changing any of them is a miss. The cache directory is `--cache-dir`, else `$SCIREPORT_CACHE_DIR`, else
`$XDG_CACHE_HOME/scireport/preprocess`. `--no-cache` neither reads nor writes it. A damaged entry is a miss.

Randomness is seeded: each step gets a seed derived from `--seed` (default 0) and the step's id, and a
pre-processor draws random numbers only from `ctx.rng()`.

## Every figure carries its data

`ctx.save_figure(figure, data=...)` requires the data. A figure pre-processor is written as two pure functions and
the registered step:

* `compute_<name>(table, ...)` turns the input into a **small tidy table** (counts per bin, one row per bar, points
  per hexagon): this is the sidecar file of the figure. A bundle holds summaries, never raw catalogues (ADR-0001).
* `render_<name>(ctx, data, ...)` draws **only** from that table, inside the layout's matplotlib style, so a figure
  can be rebuilt from its sidecar file at any time. Each pre-processor has a test that proves it: the figure drawn
  again from the stored sidecar is byte-identical to the stored PNG.
* the `@preprocessor` function runs both and calls `ctx.save_figure`.

## Writing your own

```python
import pyarrow as pa
from scireport.preprocess import Context, Port, preprocessor


@preprocessor(
  'mypkg.row_count',
  version=1,
  inputs={'table': Port('table')},
  outputs={'count': Port('number')},
)
def row_count(ctx: Context, *, table: pa.Table, label: str = 'rows') -> dict[str, object]:
  """Count the rows of a table."""
  ctx.log.info('counting %d rows', table.num_rows)
  return {'count': {'kind': 'number', 'value': table.num_rows, 'unit': label}}
```

Register it from a package with the entry-point group:

```toml
[project.entry-points."scireport.preprocessors"]
row_count = "mypkg.steps:row_count"
```

A released version is frozen: a change that alters a figure or a number is a new version registered beside the old
one, and a step that names `version: 1` keeps getting version 1 (ADR-0008).

## Python API

| Name | Does |
|---|---|
| `scireport.preprocess.preprocess_bundle(bundle, *, work_dir, cache_dir, allow_import, layout, seed, use_cache)` | plan and run the steps; returns the bundle with the results and a record per step |
| `scireport.preprocess.write_back(result, destination)` | replace a bundle on disk with the pre-processed one |
| `scireport.preprocess.plan_steps(manifest, *, allow_import)` | resolve, check and order the steps without running them |
| `scireport.preprocess.get_preprocessor(name, version)` / `list_preprocessors()` | look one up, or list them |
| `scireport.preprocess.preprocessor(...)` / `register_preprocessor(entry)` | register a function |
| `Context` | `value`, `load_table`, `mplstyle`, `figure`, `save_figure`, `save_table`, `seed`, `rng`, `look`, `log` |

## Catalogue

Every entry has version 1. The `astro` plots that need no astropy (colour diagrams, number counts and the
photometry diagnostics) run in the core install; the sky maps need the `astro` extra (astropy and astropy-healpix;
no `mocpy`, no `hats`) and give `E607` with an install hint when it is missing. Run `scireport preprocessors NAME`
for the ports and parameters of one, and see [Error codes](errors.md) for the codes. Both tables are generated from the
registry; a test fails when this page is stale.

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

## Reference

Every figure pre-processor also takes `title` (default `''`), `width` (a fraction of the page frame, default `1.0`),
`height` (inches, default `3.6`), `alt` (alt text; generated from the data when not given) and `caption`. The tables
below list them only for the entries that change a default or require one. A parameter without a description is
named by its type and default alone; `scireport preprocessors NAME --json` gives the JSON Schema.

<!-- generated:preprocessor-reference -->
### `astro.color_color`

Hybrid density colour-colour diagram.

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | One row per object, with two colour columns |
| `figure` | outputs | figure | The colour-colour density diagram |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `color_x_column` | `str` | required | Columns with the two colours (magnitude differences such as g - r and r - i). |
| `color_y_column` | `str` | required | Columns with the two colours (magnitude differences such as g - r and r - i). |
| `gridsize` | `int` | `60` | Hexagons across the x range. |
| `threshold` | `int` | `3` | A hexagon with this many points or fewer is drawn as individual points. |
| `x_label` | `str \| None` | `None` | Axis labels; the column names when None. |
| `y_label` | `str \| None` | `None` | Axis labels; the column names when None. |

### `astro.color_magnitude`

Hybrid density colour-magnitude diagram.

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | One row per object, with a colour and a magnitude |
| `figure` | outputs | figure | The colour-magnitude density diagram |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `color_column` | `str` | required | Column with a colour (a magnitude difference such as g - r), on the x axis. |
| `magnitude_column` | `str` | required | Column with a single-band magnitude, on the inverted y axis. |
| `gridsize` | `int` | `60` | Hexagons across the colour range. |
| `threshold` | `int` | `3` | A hexagon with this many points or fewer is drawn as individual points. |
| `x_label` | `str \| None` | `None` | Axis labels; the column names when None. |
| `y_label` | `str \| None` | `None` | Axis labels; the column names when None. |

### `astro.footprint`

Coverage footprint of one or several catalogues on a Mollweide sky map. Needs `scireport[astro]`.

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | Positions in degrees, or counts per HEALPix pixel |
| `figure` | outputs | figure | The Mollweide coverage map |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `order` | `int` | `5` | HEALPix level of the coverage mask, nested ordering; 0 to 10. |
| `ra_column` | `str` | `'ra'` | Right ascension and declination in degrees; ignored when ``ipix_column`` is given. |
| `dec_column` | `str` | `'dec'` | Right ascension and declination in degrees; ignored when ``ipix_column`` is given. |
| `ipix_column` | `str \| None` | `None` | Column of nested pixel indices at ``order``; makes the table a tally. |
| `counts_column` | `str \| None` | `None` | Column with the count (weight) of each row; one per row when None. |
| `group_column` | `str \| None` | `None` | One colour and legend entry per distinct value (at most 12). |
| `min_count` | `float` | `1.0` | A pixel is covered when it holds at least this many objects. |
| `height` | `float` | `3.2` | Figure height in inches. |

### `astro.magnitude_residual`

Draw a magnitude residual against magnitude as a hexagon density.

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | Catalogue with a magnitude and a residual column |
| `figure` | outputs | figure | Density of the residual against magnitude |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `magnitude_column` | `str` | required | Reference magnitude column (x axis). |
| `residual_column` | `str` | required | Residual column (y axis); the sign and meaning are the caller's. |
| `gridsize` | `int` | `60` | Hexagons across the magnitude range. |
| `threshold` | `int` | `3` | A hexagon with this many points or fewer is drawn as individual points. |
| `x_label` | `str` | `'Published magnitude'` | Axis labels. |
| `y_label` | `str` | `'Recovered - published (mag)'` | Axis labels. |
| `height` | `float` | `3.4` | Figure height in inches. |

### `astro.number_counts`

Differential number counts, log-scaled, against the Euclidean reference slope.

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | Sources per magnitude bin, one row per bin |
| `figure` | outputs | figure | The differential number counts |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `center_column` | `str` | required | Column with the magnitude bin centres. |
| `count_column` | `str` | required | Column with the sources per bin. |
| `group_column` | `str \| None` | `None` | Column with a series label (a survey, a band); one series when None. |
| `reference_slope` | `float` | `0.6` | The Euclidean slope per magnitude, anchored through the fullest bin of each series. |
| `x_label` | `str` | `'Magnitude'` | Label of the x axis. |
| `height` | `float` | `3.2` | Figure height in inches. |

### `astro.sky_density`

Mollweide sky map of source density on a HEALPix grid. Needs `scireport[astro]`.

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | Positions in degrees, or counts per HEALPix pixel |
| `figure` | outputs | figure | The Mollweide density map |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `order` | `int` | `7` | HEALPix level of the bins, or of the indices of a tally; 0 to 10. The sky has ``12 * 4**order`` pixels, nested ordering. |
| `ra_column` | `str` | `'ra'` | Right ascension and declination in degrees; ignored when ``ipix_column`` is given. |
| `dec_column` | `str` | `'dec'` | Right ascension and declination in degrees; ignored when ``ipix_column`` is given. |
| `ipix_column` | `str \| None` | `None` | Column of nested pixel indices at ``order``; makes the table a tally. |
| `counts_column` | `str \| None` | `None` | Column with the count (weight) of each row; one per row when None. |
| `log` | `bool` | `True` | Logarithmic colour scale. |
| `per_area` | `bool` | `True` | Colour by objects per square degree instead of objects per pixel. |
| `colorbar_label` | `str \| None` | `None` | Colour bar label; the unit when None. |
| `min_count` | `float` | `1.0` | Pixels with fewer objects stay blank. |

### `astro.sky_grid`

Small multiples: one Mollweide sky-density panel per group, on one shared colour scale. Needs `scireport[astro]`.

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | Positions in degrees, or counts per HEALPix pixel |
| `figure` | outputs | figure | One Mollweide density map per group |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `group_column` | `str` | required | Column whose distinct values become panels (at most 30), in sorted order. |
| `order` | `int` | `5` | HEALPix level of the bins, or of the indices of a tally; 0 to 10; nested ordering. |
| `ncols` | `int` | `3` | Panels per row; at least 1. |
| `ra_column` | `str` | `'ra'` | Right ascension and declination in degrees; ignored when ``ipix_column`` is given. |
| `dec_column` | `str` | `'dec'` | Right ascension and declination in degrees; ignored when ``ipix_column`` is given. |
| `ipix_column` | `str \| None` | `None` | Column of nested pixel indices at ``order``; makes the table a tally. |
| `counts_column` | `str \| None` | `None` | Column with the count (weight) of each row; one per row when None. |
| `log` | `bool` | `True` | Logarithmic shared colour scale. |
| `per_area` | `bool` | `True` | Colour by objects per square degree instead of objects per pixel. |
| `colorbar_label` | `str \| None` | `None` | Colour bar label; the unit when None. |
| `min_count` | `float` | `1.0` | Pixels with fewer objects stay blank. |
| `height` | `float \| None` | `None` | Figure height in inches; made from the number of rows when None. |

### `astro.snr_magnitude`

Signal-to-noise against magnitude, with the 5-sigma depth marked.

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | Catalogue with a magnitude and a signal-to-noise column |
| `figure` | outputs | figure | Density of S/N against magnitude |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `magnitude_column` | `str` | required | Magnitude column. |
| `snr_column` | `str` | required | Signal-to-noise column; rows with a value of zero or less are dropped. |
| `depth` | `float \| None` | `None` | The magnitude at which the S/N crosses 5, drawn as a vertical mark. |
| `estimate_depth` | `bool` | `True` | When ``depth`` is None, estimate it from the running median S/N; if that never crosses 5 no depth is drawn. |
| `gridsize` | `int` | `60` | Hexagons across the magnitude range. |
| `threshold` | `int` | `3` | A hexagon with this many points or fewer is drawn as individual points. |
| `x_label` | `str` | `'Magnitude'` | Axis labels. |
| `y_label` | `str` | `'$\\log_{10}$ S/N'` | Axis labels. |
| `height` | `float` | `3.4` | Figure height in inches. |

### `astro.zeropoint_offsets`

One band's cross-survey magnitude offset against colour, as a hexagon density.

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | Catalogue with a colour and a magnitude offset |
| `figure` | outputs | figure | Density of the offset against colour |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `color_column` | `str` | required | Colour column (x axis). |
| `delta_column` | `str` | required | Offset column (y axis). |
| `fit` | `bool` | `True` | Draw a least-squares line over the colour range; its slope is the colour term. |
| `gridsize` | `int` | `60` | Hexagons across the colour range. |
| `threshold` | `int` | `3` | A hexagon with this many points or fewer is drawn as individual points. |
| `x_label` | `str` | `'Colour (mag)'` | Axis labels. |
| `y_label` | `str` | `'$\\Delta m$ (mag)'` | Axis labels. |
| `height` | `float` | `3.4` | Figure height in inches. |

### `core.achieved_vs_target`

Paired horizontal bars of what was asked for and what came out.

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | One row per pair: label, achieved and target |
| `figure` | outputs | figure | Paired horizontal bars, achieved and requested |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `label_column` | `str` | required | Column with the name of each pair. |
| `achieved_column` | `str` | required | Column with what was measured. |
| `target_column` | `str` | required | Column with what was requested; null where nothing was requested. |
| `x_label` | `str` | `'Parts per million'` | Label of the value axis. |
| `height` | `float \| None` | `None` | Figure height in inches; from the number of pairs when None. |

### `core.bar`

Horizontal bars of a table of labelled counts.

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | One row per bar: a label and a count |
| `figure` | outputs | figure | The horizontal bar chart |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `label_column` | `str` | required | Column with the label of each bar. |
| `value_column` | `str` | required | Numeric column with the count of each bar; null counts as zero. |
| `highlight` | `list[str] \| None` | `None` | Labels to draw in the failure colour whatever their value. |
| `log` | `bool` | `False` | Symmetric-logarithmic value axis. |
| `x_label` | `str` | `'Rows'` | Label of the value axis. |
| `sort` | `'none' \| 'ascending' \| 'descending'` | `'none'` | Order of the bars; 'none' keeps the table order. |
| `height` | `float \| None` | `None` | Figure height in inches; computed from the number of bars when None. |

### `core.corner`

Corner plot of two to eight numeric columns.

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | One row per object, several numeric columns |
| `figure` | outputs | figure | The corner plot |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `columns` | `list[str]` | required | Two to eight distinct numeric columns, in grid order. |
| `bins` | `int` | `20` | Bins of each diagonal histogram. |
| `gridsize` | `int` | `12` | Hexagons across the x range of each pair. |
| `threshold` | `int` | `3` | A hexagon with this many points or fewer is drawn as individual points. |
| `title` | `str` | `'Corner plot'` | Title; nothing when empty. |
| `height` | `float` | `6.0` | Figure height in inches. |

### `core.density_scatter`

Scatter of two columns: hexagons where it is crowded, individual points where it is not.

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | One row per object, two numeric columns |
| `figure` | outputs | figure | The hybrid density scatter |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `x_column` | `str` | required | Numeric columns for the two axes. |
| `y_column` | `str` | required | Numeric columns for the two axes. |
| `gridsize` | `int` | `50` | Number of hexagons across the x range. |
| `threshold` | `int` | `3` | A hexagon with this many points or fewer is drawn as individual points. |
| `x_label` | `str \| None` | `None` | Axis labels; the column names when None. |
| `y_label` | `str \| None` | `None` | Axis labels; the column names when None. |

### `core.distribution`

Box or violin plot of a per-object value, one per group.

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | One row per object, a value and optionally a group |
| `figure` | outputs | figure | A box or violin per group |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `value_column` | `str` | required | Numeric column to summarise. |
| `group_column` | `str \| None` | `None` | Column naming the group of each row; a single group when None. |
| `kind` | `'box' \| 'violin'` | `'box'` | Box and whiskers, or a kernel density estimate. |
| `max_outliers` | `int` | `200` | The most outlying values stored per group (box). |
| `n_grid` | `int` | `100` | Points of the density curve per group (violin). |
| `y_label` | `str \| None` | `None` | Label of the value axis; the column name when None. |

### `core.duration_bars`

Wall-clock seconds per artifact, with the reused ones hatched.

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | One row per artifact: label, seconds, reused |
| `figure` | outputs | figure | Horizontal bars of wall-clock seconds |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `label_column` | `str` | required | Column with the artifact's name. |
| `seconds_column` | `str` | required | Column with the seconds spent. |
| `reused_column` | `str \| None` | `None` | Boolean column that is true where the artifact was reused; all built when None. |
| `height` | `float \| None` | `None` | Figure height in inches; from the number of bars when None. |

### `core.funnel`

Rows surviving each cumulative step, and rows removed by each step.

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | One row per step: its name and rows surviving |
| `figure` | outputs | figure | Rows surviving and rows removed by each step |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `label_column` | `str` | required | Column with the name of each step. |
| `count_column` | `str` | required | Numeric column with the rows surviving the step; null marks a step that failed. |
| `panels` | `'both' \| 'counts' \| 'drops'` | `'both'` | Running count on the left and rows removed on the right, or one of them alone. |
| `height` | `float \| None` | `None` | Figure height in inches; computed from the number of steps when None. |

### `core.heatmap`

Heatmap of a matrix given as a long table (one row per cell).

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | A long table: one row per cell of the matrix |
| `figure` | outputs | figure | The heatmap |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `row_column` | `str` | required | Columns naming the row and the column of each cell. |
| `column_column` | `str` | required | Columns naming the row and the column of each cell. |
| `value_column` | `str` | required | Numeric column with the cell's value; null cells are drawn blank. |
| `row_order` | `list[str] \| None` | `None` | Labels in drawing order (first appearance when None); may list labels the data lacks, and leaving one out drops its cells. |
| `column_order` | `list[str] \| None` | `None` | Labels in drawing order (first appearance when None); may list labels the data lacks, and leaving one out drops its cells. |
| `cmap` | `'sequential' \| 'diverging'` | `'sequential'` | Which colour map of the layout to use. |
| `vmin` | `float \| None` | `None` | Colour limits; the range of the values when None. |
| `vmax` | `float \| None` | `None` | Colour limits; the range of the values when None. |
| `symmetric` | `bool` | `False` | Colour limits ``-m`` to ``m``, centring a diverging scale on 0. |
| `log` | `bool` | `False` | Logarithmic colour scale (cells that are not positive are blank). |
| `annotate` | `bool \| 'auto'` | `'auto'` | Write each value in its cell; ``'auto'`` does so for at most 400 cells. |
| `value_format` | `str` | `'.2g'` | Python format specification of the cell text. |
| `colorbar_label` | `str` | `''` | Label of the colour bar. |
| `row_label` | `str` | `''` | Axis labels (rows on the left, columns on top). |
| `column_label` | `str` | `''` | Axis labels (rows on the left, columns on top). |
| `square` | `bool` | `False` | Square cells. |
| `height` | `float \| None` | `None` | Figure height in inches; from the number of rows when None. |

### `core.histogram`

Histogram of a column of samples, or of counts tallied elsewhere.

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | Samples, or a tally of counts per bin |
| `figure` | outputs | figure | The histogram |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `column` | `str` | required | Column of samples, or of bin centres (numbers) or labels (anything else) for a tally. |
| `bins` | `int \| 'auto' \| 'fd' \| 'doane' \| 'scott' \| 'stone' \| 'rice' \| 'sturges' \| 'sqrt'` | `'auto'` | Number of bins or a numpy bin rule (``'auto'``, ``'fd'``, ``'sturges'``, ...); ignored for a tally. |
| `counts_column` | `str \| None` | `None` | Column with the count of each row; makes the table a tally. |
| `categorical` | `bool` | `False` | One bar per distinct label rather than a continuous axis. |
| `log` | `bool` | `False` | Logarithmic count axis. |
| `x_label` | `str \| None` | `None` | Label of the x axis; the column name when None. |
| `y_label` | `str` | `'Count'` | Label of the y axis. |
| `height` | `float` | `3.2` | Figure height in inches. |

### `core.metric_scatter`

Compare a per-object metric of the left dataset with the right one, against ``y = x``.

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | One row per object, a left and a right metric |
| `figure` | outputs | figure | Left metric against right metric |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `x_column` | `str` | required | Numeric columns: the left metric (x axis) and the right metric (y axis). |
| `y_column` | `str` | required | Numeric columns: the left metric (x axis) and the right metric (y axis). |
| `x_label` | `str` | `'left'` | Axis labels. |
| `y_label` | `str` | `'right'` | Axis labels. |
| `title` | `str` | `'Metric comparison'` | Title; nothing when empty. |
| `gridsize` | `int` | `50` | Number of hexagons across the x range. |
| `threshold` | `int` | `3` | A hexagon with this many points or fewer is drawn as individual points. |

### `core.pp`

P-P plot of a sample against a normal distribution or a second sample.

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | A table with the sample column (and the reference) |
| `figure` | outputs | figure | The P-P plot |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `column` | `str` | required | The sample, drawn on the y axis. |
| `reference_column` | `str \| None` | `None` | A second sample for the x axis; without it the standard normal distribution, against which the standardised sample is drawn. |
| `max_points` | `int` | `2000` | The most points drawn (a deterministic grid, not every row). |
| `x_label` | `str \| None` | `None` | Axis labels; made from the column names when None. |
| `y_label` | `str \| None` | `None` | Axis labels; made from the column names when None. |
| `height` | `float` | `3.4` | Figure height in inches. |

### `core.pvalue_strip`

Every p-value of a family of tests on one logarithmic axis, against its threshold.

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | One row per test: its name and p-value |
| `figure` | outputs | figure | The p-values against the threshold |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `label_column` | `str` | required | Column with the name of each test. |
| `pvalue_column` | `str` | required | Numeric column with the p-value; null or NaN means the test was not computable. |
| `alpha` | `float` | `0.05` | Significance threshold, drawn as a vertical line. |
| `height` | `float \| None` | `None` | Figure height in inches; computed from the number of tests when None. |

### `core.qq`

Q-Q plot of a sample against a normal distribution or a second sample.

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | A table with the sample column (and the reference) |
| `figure` | outputs | figure | The Q-Q plot |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `column` | `str` | required | The sample, drawn on the y axis. |
| `reference_column` | `str \| None` | `None` | A second sample for the x axis; without it the standard normal distribution, against which the standardised sample is drawn. |
| `max_points` | `int` | `2000` | The most points drawn (a deterministic quantile grid, not every row). |
| `x_label` | `str \| None` | `None` | Axis labels; made from the column names when None. |
| `y_label` | `str \| None` | `None` | Axis labels; made from the column names when None. |
| `height` | `float` | `3.4` | Figure height in inches. |

### `core.separation_histogram`

Histogram of match separations, with the match radius marked.

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | Separations, or a tally of matches per bin |
| `figure` | outputs | figure | The histogram of match separations |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `column` | `str` | required | Column of separations in arcseconds, or of bin centres (arcseconds) for a tally. |
| `counts_column` | `str \| None` | `None` | Column with the number of matches in each bin; makes the table a tally. |
| `radius` | `float \| None` | `None` | Match radius in arcseconds, drawn as a vertical rule; nothing when None. |
| `bins` | `int` | `40` | Number of bins for a sample; ignored for a tally. |
| `x_label` | `str` | `'Angular separation (arcsec)'` | Label of the separation axis. |
| `height` | `float` | `3.2` | Figure height in inches. |

### `core.split_balance`

One split's arms (train, validation, test) on one stratifier, normalised and overlaid.

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | One row per arm and bin: arm, bin, count |
| `figure` | outputs | figure | Overlaid, normalised marginals of the arms |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `arm_column` | `str` | required | Column with the arm of each row. |
| `bin_column` | `str` | required | Column with the bin of the stratifier (numbers are ordered by value). |
| `count_column` | `str` | required | Column with the count of the arm in that bin. |
| `stratifier` | `str` | `''` | Name of the stratified quantity, for the axis label and the title. |
| `split` | `str` | `''` | Name of the split the arms belong to, for the title. |
| `y_label` | `str` | `'Share of arm'` | Label of the share axis. |
| `title` | `str \| None` | `None` | Title; ``<split>: label balance on <stratifier>`` when None, nothing when empty. |
| `height` | `float` | `3.2` | Figure height in inches. |

### `core.split_marginals`

Each split's marginal on one stratifier, normalised and overlaid.

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | One row per split and bin: split, bin, count |
| `figure` | outputs | figure | Overlaid, normalised marginals of the splits |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `split_column` | `str` | required | Column with the split of each row. |
| `bin_column` | `str` | required | Column with the bin of the stratifier (numbers are ordered by value). |
| `count_column` | `str` | required | Column with the count of the split in that bin. |
| `stratifier` | `str` | `''` | Name of the stratified quantity, for the axis label and the title. |
| `reference` | `str` | `''` | The split drawn heavier so the eye has a baseline; none when empty. |
| `y_label` | `str` | `'Share of split'` | Label of the share axis. |
| `title` | `str \| None` | `None` | Title; ``Split marginals: <stratifier>`` when None, nothing when empty. |
| `height` | `float` | `3.2` | Figure height in inches. |

### `core.stacked_shares`

One stacked horizontal bar per group, each segment a label's share of the group.

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | Long table: group, label and count of each row |
| `figure` | outputs | figure | The stacked share bars |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `group_column` | `str` | required | Column with the group of each row. |
| `label_column` | `str` | required | Column with the label (segment) of each row. |
| `count_column` | `str` | required | Numeric column with the count; null counts as zero, repeated pairs are summed. |
| `reference` | `object \| None` | `None` | Requested shares as ``label -> share`` (summing to one), drawn as dashed verticals at the cumulative boundaries. |
| `height` | `float \| None` | `None` | Figure height in inches; computed from the number of groups when None. |

### `core.table_profile`

Per-column profile of a table, with its size.

| Port | Direction | Kind | Meaning |
|---|---|---|---|
| `table` | inputs | table | The table to profile |
| `profile` | outputs | table | One row per column: type, nulls, zeros and shape |
| `summary` | outputs | metrics | Rows, columns and size in memory |

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `caption` | `str \| None` | `None` | Caption below the profile table; a description of the columns when None. |
<!-- /generated -->
