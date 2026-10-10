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
for the ports and parameters of one, and see `docs/errors.md` for the codes. A test checks that this table lists
exactly the registered pre-processors.

| Name | Needs | Does |
|---|---|---|
| `astro.color_color` |  | Hybrid density colour-colour diagram. |
| `astro.color_magnitude` |  | Hybrid density colour-magnitude diagram. |
| `astro.footprint` | `scireport[astro]` | Coverage footprint of one or several catalogues on a Mollweide sky map. |
| `astro.magnitude_residual` |  | Draw a magnitude residual against magnitude as a hexagon density. |
| `astro.number_counts` |  | Differential number counts, log-scaled, against the Euclidean reference slope. |
| `astro.sky_density` | `scireport[astro]` | Mollweide sky map of source density on a HEALPix grid. |
| `astro.sky_grid` | `scireport[astro]` | Small multiples: one Mollweide sky-density panel per group, on one shared colour scale. |
| `astro.snr_magnitude` |  | Signal-to-noise against magnitude, with the 5-sigma depth marked. |
| `astro.zeropoint_offsets` |  | One band's cross-survey magnitude offset against colour, as a hexagon density. |
| `core.achieved_vs_target` |  | Paired horizontal bars of what was asked for and what came out. |
| `core.bar` |  | Horizontal bars of a table of labelled counts. |
| `core.corner` |  | Corner plot of two to eight numeric columns. |
| `core.density_scatter` |  | Scatter of two columns: hexagons where it is crowded, individual points where it is not. |
| `core.distribution` |  | Box or violin plot of a per-object value, one per group. |
| `core.duration_bars` |  | Wall-clock seconds per artifact, with the reused ones hatched. |
| `core.funnel` |  | Rows surviving each cumulative step, and rows removed by each step. |
| `core.heatmap` |  | Heatmap of a matrix given as a long table (one row per cell). |
| `core.histogram` |  | Histogram of a column of samples, or of counts tallied elsewhere. |
| `core.metric_scatter` |  | Compare a per-object metric of the left dataset with the right one, against ``y = x``. |
| `core.pp` |  | P-P plot of a sample against a normal distribution or a second sample. |
| `core.pvalue_strip` |  | Every p-value of a family of tests on one logarithmic axis, against its threshold. |
| `core.qq` |  | Q-Q plot of a sample against a normal distribution or a second sample. |
| `core.separation_histogram` |  | Histogram of match separations, with the match radius marked. |
| `core.split_balance` |  | One split's arms (train, validation, test) on one stratifier, normalised and overlaid. |
| `core.split_marginals` |  | Each split's marginal on one stratifier, normalised and overlaid. |
| `core.stacked_shares` |  | One stacked horizontal bar per group, each segment a label's share of the group. |
| `core.table_profile` |  | Per-column profile of a table, with its size. |

