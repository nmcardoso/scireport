# Python API

```python
import scireport
from scireport import Report, open_bundle, render_bundle, check_bundle, export_tex
```

**The import surface rule.** Only names listed in `scireport.__all__` are public and follow semantic
versioning (a test compares them with a committed snapshot). Import them from `scireport`. Everything
else, every `scireport.<module>` that is not re-exported, may change in a minor release: do not import
it, and do not reach into the private attributes of `Report` or `Bundle`. The heavier names (rendering,
export, pre-processing) load on first use, so `import scireport` stays fast. Docstrings are NumPy style:
`help(scireport.Report.add_table)` documents every argument.

## Public names

<!-- generated:api -->
| Name | Kind | Signature | What it does |
|---|---|---|---|
| `SPEC_VERSION` | constant | `= '1.0'` |  |
| `Bundle` | class | `(manifest: 'Manifest', backend: 'Backend', *, form: 'Form', source: 'Path \| None' = None) -> 'None'` | An opened report bundle: its manifest plus lazy access to its assets. |
| `BundleError` | class | `(message: 'str', *, code: 'str', hint: 'str \| None' = None, issues: 'list[Issue] \| None' = None) -> 'None'` | A bundle cannot be read or written (E4xx). |
| `ExportError` | class | `(message: 'str', *, code: 'str', hint: 'str \| None' = None, issues: 'list[Issue] \| None' = None) -> 'None'` | Values cannot be exported as LaTeX fragments (E807, E808, or E103 for an unknown key). |
| `ExportResult` | class | `(files: 'dict[str, bytes]', macros: 'dict[str, str]') -> None` | What an export produced. |
| `Issue` | class | `(code: 'str', message: 'str', pointer: 'str' = '', key: 'str \| None' = None, expected: 'str \| None' = None, found: 'str \| None' = None, hint: 'str \| None' = None, location: 'str \| None' = None) -> None` | One problem found in a manifest or bundle. |
| `KeyConflictError` | class | `(message: 'str', *, code: 'str', hint: 'str \| None' = None, issues: 'list[Issue] \| None' = None) -> 'None'` | A key is added twice, or collides with another key, in a `Report` (E104, E102). |
| `Manifest` | class | `(see its fields)` | The whole manifest (`scireport.json`). |
| `MissingDependencyError` | class | `(message: 'str', *, code: 'str', hint: 'str \| None' = None, issues: 'list[Issue] \| None' = None) -> 'None'` | A dependency is missing: pango, TeX Live (E901), pandoc (E506) or an extra (E607, E904). |
| `PandocError` | class | `(message: 'str', *, code: 'str', hint: 'str \| None' = None, issues: 'list[Issue] \| None' = None) -> 'None'` | Pandoc ran and failed, or the converted content cannot be used (E507, E212). |
| `PdfError` | class | `(message: 'str', *, code: 'str', hint: 'str \| None' = None, issues: 'list[Issue] \| None' = None) -> 'None'` | A PDF engine ran and failed; the issues carry the engine's own messages (E902). |
| `PreprocessError` | class | `(issues: 'list[Issue]') -> 'None'` | Pre-processing steps are invalid; carries every problem found before anything runs (E6xx). |
| `PreprocessRunError` | class | `(message: 'str', *, code: 'str', hint: 'str \| None' = None, issues: 'list[Issue] \| None' = None) -> 'None'` | A pre-processor raised while it ran (E606); the data file itself is not at fault. |
| `RenderError` | class | `(issues: 'list[Issue]') -> 'None'` | Validation or rendering found problems; carries every one of them (ADR-0005). |
| `RenderResult` | class | `(files: 'dict[str, bytes]', manifest: 'dict[str, Any]', issues: 'tuple[Issue, ...]', formats: 'tuple[str, ...]') -> None` | The outcome of a render: all files in memory, with what was found on the way. |
| `Report` | class | `(title: 'str', *, subtitle: 'str \| None' = None, authors: 'Iterable[str \| Mapping[str, Any] \| Author]' = (), date: 'str \| dt.date \| None' = None, version: 'str \| None' = None, pipeline: 'str \| None' = None, footer: 'str \| None' = None, abstract: 'str \| None' = None, keywords: 'Iterable[str]' = (), language: 'str' = 'en', generator: 'tuple[str, str] \| None' = None) -> 'None'` | Builds a report bundle in memory. |
| `ScireportError` | class | `(message: 'str', *, code: 'str', hint: 'str \| None' = None, issues: 'list[Issue] \| None' = None) -> 'None'` | Base class of every error scireport raises on purpose. |
| `SpecError` | class | `(issues: 'list[Issue]') -> 'None'` | A manifest does not match the data-file specification (E1xx to E3xx). |
| `SpecVersionError` | class | `(message: 'str', *, code: 'str', hint: 'str \| None' = None, issues: 'list[Issue] \| None' = None) -> 'None'` | The spec version of a bundle cannot be read by this scireport (E5xx). |
| `TemplateError` | class | `(message: 'str', *, code: 'str', hint: 'str \| None' = None, issues: 'list[Issue] \| None' = None) -> 'None'` | A template or layout cannot be found, loaded or used (E504, E505, E7xx). |
| `ValidationReport` | class | `(issues: 'tuple[Issue, ...]', strict: 'bool' = False) -> None` | Every problem found, aggregated, with the strictness that decides what counts as failure. |
| `__version__` | constant | `= '0.1.0.dev0'` |  |
| `check_bundle` | function | `(bundle: 'Bundle', *, template: 'str \| Path \| None' = None, layout: 'str \| Path \| None' = None, formats: 'Sequence[str] \| None' = None, options: 'Mapping[str, object] \| None' = None, markup_engine: 'str \| None' = None, math_renderer: 'str \| None' = None, pdf_engine: 'str \| None' = None, latex_engine: 'str \| None' = None, md_split: 'bool \| None' = None, strict: 'bool' = False, render: 'bool' = True, preprocess: 'bool' = True, allow_import: 'bool' = False, cache_dir: 'Path \| None' = None, office_source: 'str \| None' = None, reference_doc: 'Path \| None' = None) -> 'ValidationReport'` | Validate a bundle, and render it in memory to find what only a render can show. |
| `export_tex` | function | `(bundle: 'Bundle', keys: 'Sequence[str] \| None' = None, *, prefix: 'str' = '', bare: 'bool' = False, graphics_prefix: 'str' = '', max_rows: 'int \| None' = None) -> 'ExportResult'` | Export values of a bundle as LaTeX fragments. |
| `figure` | function | `(width: 'float' = 1.0, height: 'float' = 3.6, nrows: 'int' = 1, ncols: 'int' = 1, *, layout: 'str' = 'default', paper: 'str' = 'a4', subplot_kw: 'dict[str, Any] \| None' = None) -> 'tuple[Figure, Any]'` | Create a figure at its final size, as a fraction of the page frame, in the style of a layout. |
| `list_layouts` | function | `() -> 'list[Listing]'` | List every layout version available, built in or from entry points, sorted. |
| `list_templates` | function | `() -> 'list[Listing]'` | List every template version available, built in or from entry points, sorted. |
| `mplstyle` | function | `(layout: 'str' = 'default', *, rc: 'dict[str, Any] \| None' = None) -> 'Iterator[None]'` | Apply the matplotlib style of a layout for the duration of a `with` block. |
| `mplstyle_path` | function | `(layout: 'str' = 'default') -> 'Path'` | Return the matplotlib style file of a layout. |
| `open_bundle` | function | `(path: 'Path \| str', *, max_bytes: 'int' = 1073741824) -> 'Bundle'` | Open a bundle from a directory, a ZIP archive or a single manifest file. |
| `palette` | function | `(layout: 'str' = 'default') -> 'Palette'` | Return the palette of a layout: colours, chart roles, fonts and page geometry. |
| `parse_manifest` | function | `(raw: 'Any', *, resolver: 'Any' = None) -> 'Manifest'` | Parse and fully validate a manifest read from JSON or YAML. |
| `preprocess_bundle` | function | `(bundle: 'Bundle', *, work_dir: 'Path \| None' = None, cache_dir: 'Path \| None' = None, allow_import: 'bool' = False, layout: 'str \| None' = None, seed: 'int' = 0, use_cache: 'bool' = True) -> 'PreprocessResult'` | Run the `preprocess` steps of a bundle and return the bundle with their results. |
| `preprocessor` | function | `(name: 'str', *, version: 'int', inputs: 'Mapping[str, Port] \| None' = None, outputs: 'Mapping[str, Port] \| None' = None, render: 'Callable[..., Any] \| None' = None, requires: 'str \| None' = None) -> 'Callable[[Callable[..., dict[str, Any]]], Preprocessor]'` | Register a function as a pre-processor. |
| `render_bundle` | function | `(bundle: 'Bundle', *, template: 'str \| Path \| None' = None, layout: 'str \| Path \| None' = None, formats: 'Sequence[str] \| None' = None, options: 'Mapping[str, object] \| None' = None, markup_engine: 'str \| None' = None, math_renderer: 'str \| None' = None, pdf_engine: 'str \| None' = None, latex_engine: 'str \| None' = None, md_split: 'bool \| None' = None, flat: 'bool' = False, strict: 'bool' = False, preprocess: 'bool' = True, allow_import: 'bool' = False, cache_dir: 'Path \| None' = None, office_source: 'str \| None' = None, reference_doc: 'Path \| None' = None) -> 'RenderResult'` | Render a bundle to Markdown, HTML and/or a LaTeX project. |
| `write_bundle` | function | `(bundle: 'Bundle', dest: 'Path \| str', *, form: 'WriteForm \| None' = None, overwrite: 'bool' = False, max_bytes: 'int' = 1073741824) -> 'Path'` | Write a bundle to `dest`, copying exactly the assets its manifest references. |
| `write_export` | function | `(result: 'ExportResult', out_dir: 'Path \| str') -> 'list[Path]'` | Write the files of an export. |
<!-- /generated -->

## Build a report

`Report(title, *, subtitle, authors, date, version, pipeline, footer, abstract, keywords, language,
generator)` collects values in memory. Every `add_*` method returns the report, so calls chain. Each call
checks its input at once and raises a coded error, so a mistake surfaces at the line that made it.

- **Keys** follow the key grammar (`references/data-file.md`): `E101` for a bad key (`SpecError`), `E104`
  for a key used twice and `E102` for a key that is the prefix of another (`KeyConflictError`).
  `report.keys` lists the keys so far.
- **Numbers.** `add_number(key, value, unit=, format=, uncertainty=, interval=, missing=)`. `NaN` and
  `None` become a missing number; an infinite value raises `ValueError`.
- **Tables.** `add_table(key, data, columns=, caption=, ...)` takes a pyarrow `Table`, a pandas
  `DataFrame` (the index is dropped; use `reset_index()` first if you need it), any object with an
  Arrow stream interface (polars), a dict of columns (`{'a': [1, 2]}`) or a list of row dicts. Anything
  else is a `TypeError`. It is stored as Parquet (zstd); `format='csv'` stores CSV; `inline=True` keeps
  the rows in the manifest and takes JSON scalars only (`E301`). `columns` names, orders and styles the
  columns (`['id', {'name': 'sep', 'label': 'Separation', 'unit': 'arcsec', 'format': '.2f'}]`).
- **Figures.** `add_figure(key, fig, alt=..., caption=, width=, data=, formats=('png', 'pdf'), dpi=200)`.
  `alt` is required. `fig` is a matplotlib `Figure` (rendered to every format, with no clock or version
  inside, so the bytes repeat), a dict `{'png': path_or_bytes, 'pdf': ...}`, or one image path.
  `data=` takes anything `add_table` takes and is stored next to the figure.
- **Text and code** over 4096 bytes go to an asset file by themselves; `as_asset=True` or `False` decides.
  `add_text(key, text, format='plain' | 'markdown' | 'latex', alt={'html': ..., 'md': ...})`.
- **Files.** `add_image(key, path_or_bytes, suffix=, alt=, caption=, width=)`,
  `add_attachment(key, path_or_bytes, filename=, media_type=, description=)` (bytes need `suffix=` or
  `filename=`) and `add_bibliography(key, bib_path_or_bytes, csl=, style=)`.
- **Everything else:** `add_bool`, `add_date`, `add_list`, `add_mapping`, `add_math`, `add_code`,
  `add_metrics`, `add_status`, `add_alert`, `add_flow`. `add(key, value)` takes bare JSON, an envelope
  dict or a value model; it cannot add a value that refers to files.
- **Document choices.** `set_render(template=, layout=, formats=, pdf_engine=, latex_engine=,
  markup_engine=, math_renderer=, options={...})` fills the `render` block; unnamed fields keep their
  value. `set_outline([...])` takes keys and `{'title': ..., 'children': [...]}` headings (needed by
  `generic@1`). `add_preprocess(name, inputs=, outputs=, params=)` declares a pre-processing step (see
  `references/preprocessors.md`). `add_input(name, sha256=, uri=)` records an input in the provenance.
- **Output.** `report.write(dest, form=None, overwrite=False)` builds, checks and writes, and returns the
  path. `dest` ending in `.scireport.zip` gives a ZIP, ending in `.json` a single manifest file (only for
  a report without assets, else `E409`), anything else a directory. An existing destination is `E410`
  unless `overwrite=True`. `report.build()` returns an in-memory `Bundle` that `render_bundle`,
  `check_bundle` and `export_tex` accept directly; `report.manifest()` returns the checked `Manifest`.
  `write` does not pin versions: pass `set_render(template='generic@1', layout='default@1')`, or run
  `scireport pack` on the result.

Figures in the report's look: draw inside `with scireport.mplstyle():` and make the figure with
`fig, ax = scireport.figure(width, height)`. `width` is a fraction of the page frame (0.5 is half the
usable width, so 8 pt text is 8 pt on paper) and `height` is in inches; `nrows` and `ncols` give a grid
of axes. `scireport.palette()` returns the layout's colours. See `references/mplstyle.md`.

### Report methods

<!-- generated:report-methods -->
| Method | Signature | What it does |
|---|---|---|
| `add` | `(key: 'str', value: 'Any') -> 'Report'` | Add any value: a bare JSON shorthand, an envelope dict or a value model. |
| `add_alert` | `(key: 'str', level: "Literal['info', 'warning', 'error']", text: 'str') -> 'Report'` | Add a one-line call-out. |
| `add_attachment` | `(key: 'str', source: 'Path \| str \| bytes', *, filename: 'str \| None' = None, media_type: 'str \| None' = None, description: 'str \| None' = None) -> 'Report'` | Add a file offered alongside the report. |
| `add_bibliography` | `(key: 'str', source: 'Path \| str \| bytes', *, csl: 'Path \| str \| bytes \| None' = None, style: 'str \| None' = None) -> 'Report'` | Add the references that `[@key]` citations in prose refer to. |
| `add_bool` | `(key: 'str', value: 'bool') -> 'Report'` | Add a boolean. |
| `add_code` | `(key: 'str', source: 'str', *, language: 'str \| None' = None, caption: 'str \| None' = None, as_asset: 'bool \| None' = None) -> 'Report'` | Add source code or preformatted text. |
| `add_date` | `(key: 'str', value: 'str \| dt.date') -> 'Report'` | Add a date or date-time. |
| `add_figure` | `(key: 'str', figure: 'Any', *, alt: 'str', caption: 'str \| None' = None, width: 'float' = 1.0, data: 'Any' = None, formats: "Sequence[Literal['png', 'pdf', 'svg']]" = ('png', 'pdf'), dpi: 'float' = 200) -> 'Report'` | Add a figure with its sidecar data. |
| `add_flow` | `(key: 'str', stages: 'Iterable[FlowStage \| Mapping[str, Any] \| str]') -> 'Report'` | Add a pipeline drawn as numbered stages. |
| `add_image` | `(key: 'str', source: 'Path \| str \| bytes', *, suffix: 'str \| None' = None, alt: 'str \| None' = None, caption: 'str \| None' = None, width: 'float' = 1.0) -> 'Report'` | Add a picture that is not generated from data. |
| `add_input` | `(name: 'str', *, sha256: 'str \| None' = None, uri: 'str \| None' = None) -> 'Report'` | Record an input of the computation in the provenance block. |
| `add_list` | `(key: 'str', items: 'Iterable[Any]', *, ordered: 'bool' = False) -> 'Report'` | Add a list; items may be bare JSON, envelopes or value models. |
| `add_mapping` | `(key: 'str', entries: 'Mapping[str, Any] \| Iterable[tuple[str, Any]]') -> 'Report'` | Add labelled entries (a description list), in the order given. |
| `add_math` | `(key: 'str', latex: 'str', *, display: 'bool' = True, numbered: 'bool' = False, caption: 'str \| None' = None) -> 'Report'` | Add a LaTeX expression. |
| `add_metrics` | `(key: 'str', items: 'Iterable[MetricItem \| Mapping[str, Any] \| tuple[Any, ...]]') -> 'Report'` | Add a grid of headline numbers. |
| `add_number` | `(key: 'str', value: 'int \| float \| None', *, unit: 'str \| None' = None, format: 'str \| None' = None, uncertainty: 'float \| None' = None, interval: 'tuple[float, float] \| None' = None, missing: 'str \| None' = None) -> 'Report'` | Add a number. NaN is stored as a missing number; infinities are an error. |
| `add_preprocess` | `(name: 'str', *, inputs: 'Mapping[str, str] \| None' = None, outputs: 'Mapping[str, str] \| None' = None, params: 'Mapping[str, Any] \| None' = None, version: 'int \| None' = None, id: 'str \| None' = None) -> 'Report'` | Declare a pre-processing step to run when the report is rendered. |
| `add_status` | `(key: 'str', level: "Literal['success', 'warning', 'partial', 'failed', 'running']", headline: 'str', detail: 'str \| None' = None) -> 'Report'` | Add an overall verdict banner. |
| `add_table` | `(key: 'str', data: 'Any', *, columns: 'Iterable[str \| Mapping[str, Any] \| Column] \| None' = None, caption: 'str \| None' = None, format: "Literal['parquet', 'csv']" = 'parquet', inline: 'bool' = False, row_status: "Sequence[Literal['pass', 'warn', 'fail'] \| None] \| None" = None, row_status_column: 'str \| None' = None, emphasis: 'Iterable[CellEmphasis \| Mapping[str, Any]]' = (), max_rows: 'int \| None' = None, overflow_attachment: 'str \| None' = None) -> 'Report'` | Add a table. |
| `add_text` | `(key: 'str', text: 'str', *, format: "Literal['plain', 'markdown', 'latex']" = 'plain', alt: "Mapping[Literal['html', 'md'], str] \| None" = None, as_asset: 'bool \| None' = None) -> 'Report'` | Add prose or a short string. |
| `build` | `() -> 'Bundle'` | Assemble the report into an in-memory bundle. |
| `manifest` | `() -> 'Manifest'` | Assemble and fully check the manifest. |
| `set_outline` | `(nodes: 'Sequence[str \| Mapping[str, Any] \| OutlineNode]') -> 'Report'` | Set the outline used by the `generic` template. |
| `set_render` | `(**options: 'Any') -> 'Report'` | Set fields of the `render` block (template, layout, formats, engines, options). |
| `write` | `(dest: 'Path \| str', *, form: 'WriteForm \| None' = None, overwrite: 'bool' = False) -> 'Path'` | Build the report and write it. |
<!-- /generated -->

## Open, validate and render

```python
with open_bundle('crossmatch.scireport.zip') as bundle:   # directory, ZIP or manifest file
  result = render_bundle(bundle, formats=['md', 'html'])
  result.write('out')
```

- `open_bundle(path, *, max_bytes=1 GiB)` returns a `Bundle`. Use it as a context manager so a ZIP handle
  is closed. A bad bundle raises `BundleError` (`E4xx`), `SpecVersionError` (`E5xx`) or `SpecError`
  carrying every manifest problem. Useful members: `bundle.manifest` (the validated `Manifest`, values
  are typed models: `bundle.manifest.values['a.b'].value`), `bundle.form` (`'directory'`, `'zip'`,
  `'file'`), `bundle.read_table(key)` (a pyarrow `Table`), `bundle.read_text(key)`, `bundle.read_asset(path)`
  (bytes), `bundle.asset_paths` and `bundle.verify()` (a list of `Issue`; empty when every hash and size
  matches). `write_bundle(bundle, dest, form=, overwrite=)` copies a bundle to another form.
- `render_bundle(bundle, *, template, layout, formats, options, markup_engine, math_renderer, pdf_engine,
  latex_engine, md_split, flat, strict, preprocess, allow_import, cache_dir, office_source,
  reference_doc)` returns a `RenderResult`. Whatever you leave out comes from the bundle's `render` block,
  then from the defaults (`generic@1`, `default@1`). Nothing is written to disk; the result holds:
  - `files`: path to bytes, sorted (`md/report.md`, `html/report.html`, `md/figures/...`,
    `render-manifest.json`). With one format and `flat=True` the format folder is dropped.
  - `manifest`: the dict that `render-manifest.json` holds (input hashes, versions, outputs).
  - `issues`: the warnings found (a tuple of `Issue`).
  - `formats`: the formats written. `result.write(out_dir)` writes `files` and returns the paths.
  - On any error nothing is returned: `RenderError` carries all the issues at once. `strict=True` makes
    warnings errors. `pdf`, `docx`, `odt`, `epub` are never defaults; a missing pango or TeX Live raises
    `MissingDependencyError` (exit code 3), a missing pandoc `E506`.
- `check_bundle(bundle, ...)` takes the same options plus `render=True` (also render in memory, which finds
  what only a render shows) and returns a `ValidationReport`; it does not raise for problems in the bundle.
  `report.ok`, `report.issues` (errors and warnings, in the order found), `report.errors`,
  `report.warnings`, `report.exit_code` (0 or 2), `report.to_dict()` (the `--json` payload of
  `scireport validate`) and `report.raise_for_errors()`. With `strict=True` a warning makes `ok` false.
- `export_tex(bundle, keys=None, *, prefix='', bare=False, graphics_prefix='', max_rows=None)` returns an
  `ExportResult` (`files`: name to bytes, `macros`: macro name to key). `keys` take `*` and `?`
  (`['crossmatch.*']`); `None` exports every number, table and figure. Numbers become macros in
  `numbers.tex` (key `crossmatch.n_pairs` with `prefix='x'` gives `\xCrossmatchNPairs`), tables `tab_<key>.tex`,
  figures `fig_<key>.tex` plus `fig_<key>.pdf` (or `.png`). `graphics_prefix` is the path LaTeX uses to
  reach the figures. `write_export(result, out_dir)` writes them. Errors: `ExportError` (`E103` unknown
  key, `E807` two keys give one macro name, `E808` a key that has no fragment, `E210`).
- `preprocess_bundle(bundle, *, work_dir, cache_dir, allow_import, layout, seed=0, use_cache=True)` runs
  the `preprocess` steps and returns a `PreprocessResult` (`.bundle` with the new figures and tables,
  `.steps`). `render_bundle` and `check_bundle` do it first by themselves (`preprocess=True`), so call it
  only to look at the results. `allow_import=True` lets a step name `module:function`, which runs code:
  use it only on files you trust.
- `parse_manifest(raw)` validates a manifest you parsed yourself; `list_templates()` and `list_layouts()`
  list what is installed; `SPEC_VERSION` is the spec version this package writes.

## Errors

Every error scireport raises on purpose is a `ScireportError` with `code`, `message`, `hint`, `issues`
(every problem found, never empty) and `exit_code` (what the CLI exits with). Catch the base class, or a
specific one.

| Class | Raised for | Codes | Exit code |
|---|---|---|---|
| `ScireportError` | base of all the others | | 2 |
| `SpecError` | manifest or value does not match the spec; also a bad key in `Report` | `E1xx`-`E3xx` | 2 |
| `SpecVersionError` | spec version missing, malformed, too new or too old | `E501`-`E503` | 2 |
| `BundleError` | bundle cannot be read or written, asset problems | `E4xx` | 2 |
| `KeyConflictError` | key used twice, or prefix of another key, in a `Report` | `E104`, `E102` | 2 |
| `TemplateError` | template or layout not found, invalid or unsupported | `E504`, `E505`, `E7xx` | 2 |
| `ExportError` | values cannot be exported as LaTeX | `E807`, `E808`, `E103`, `E210` | 2 |
| `PreprocessError` | the pre-processing plan is invalid (before anything runs) | `E601`-`E605` | 2 |
| `RenderError` | validation or rendering found problems | any | 2 |
| `MissingDependencyError` | pango, TeX Live, pandoc or an extra is missing | `E901`, `E506`, `E607`, `E904` | 3 |
| `PandocError` | pandoc ran and failed, or its result cannot be used | `E507`, `E212` | 1 |
| `PdfError` | a PDF engine ran and failed (issues hold its messages) | `E902` | 1 |
| `PreprocessRunError` | a pre-processor raised while it ran | `E606` | 1 |

Exit code 2 means the data file or the request is at fault, 1 a failure outside the data file, 3 a missing
system dependency. Plain Python errors still occur for plain misuse: `TypeError` (data that is not a table),
`ValueError` (an infinite number, bytes without `filename=`).

An `Issue` (frozen dataclass, importable from `scireport`) has `code`, `message`, `pointer` (RFC 6901 JSON
pointer into the manifest, `''` for the whole document), `key`, `expected`, `found`, `hint` and `location`
(`file:line` of the template that caused it), plus `severity` (`'error'` for `E` codes, `'warning'` for `W`
codes), `format()` (one line starting with the code), `describe()` (the same without the code) and
`to_dict()` (JSON-ready, empty fields left out). Look a code up with `scireport spec errors --json` or
`references/errors.md`.

```python
try:
  render_bundle(bundle)
except ScireportError as exc:
  for issue in exc.issues:          # all of them, not just the first
    print(issue.format())           # E106 /values: the template reads key 'summary', which ...
  payload = [issue.to_dict() for issue in exc.issues]
  raise SystemExit(exc.exit_code)
```

## Determinism

The API never reads the clock or the environment while building or writing: the same calls give the same
bytes (ZIP entries are sorted with fixed timestamps; matplotlib figures are saved without version or date
metadata), and `meta.date` is only what you set. PDF dates come from `SOURCE_DATE_EPOCH`, else `meta.date`,
else 1980-01-01; a PDF is best-effort deterministic across machines (fonts and engine versions).

## Complete examples

Every example below was run as written with `uv run python`, in one directory, in this order.

### Build a report from pandas and matplotlib, render to Markdown and HTML

pandas is not a dependency of scireport (pyarrow and matplotlib are); install it to run this one (`add_table`
takes a dict of columns as well).

```python
import pandas as pd

import scireport
from scireport import Report, open_bundle, render_bundle

pairs = pd.DataFrame({'id': [1, 2, 3, 4], 'sep_arcsec': [0.21, 0.48, 0.77, 0.35]})

report = Report('Cross-match report', authors=['Ada Lovelace'], version='1.0.0')
report.add_text('summary', 'Pairs closer than **1 arcsec** are kept.', format='markdown')
report.add_number('crossmatch.n_pairs', len(pairs), unit='pairs', format='int')
report.add_number('crossmatch.sep_mean', pairs['sep_arcsec'].mean(), unit='arcsec', format='.2f')
report.add_table(
  'crossmatch.pairs',
  pairs,
  columns=['id', {'name': 'sep_arcsec', 'label': 'Separation', 'unit': 'arcsec', 'format': '.2f'}],
  caption='Matched pairs.',
)

with scireport.mplstyle():  # draw and save inside the block: the style applies to new artists
  fig, ax = scireport.figure(0.7)  # 70 % of the page width, in the report's style
  ax.hist(pairs['sep_arcsec'], bins=4)
  ax.set_xlabel('Separation [arcsec]')
  ax.set_ylabel('Pairs')
  report.add_figure(
    'crossmatch.sep_hist',
    fig,
    alt='Histogram of the separation of matched pairs, in arcsec.',
    caption='Separations.',
    width=0.7,
    data=pairs,  # optional: stored next to the figure as Parquet
  )

report.set_outline(
  [
    'summary',
    {
      'title': 'Results',
      'children': [
        'crossmatch.n_pairs',
        'crossmatch.sep_mean',
        'crossmatch.pairs',
        'crossmatch.sep_hist',
      ],
    },
  ]
)
report.set_render(template='generic@1', formats=['md', 'html'])
report.write('crossmatch.scireport.zip', overwrite=True)

with open_bundle('crossmatch.scireport.zip') as bundle:
  result = render_bundle(bundle, formats=['md', 'html'])
  for issue in result.issues:  # warnings only; errors raise RenderError
    print(issue.format())
  for path in result.write('out'):
    print(path)
```

This writes `crossmatch.scireport.zip` and `out/md/report.md`, `out/html/report.html`,
`out/render-manifest.json`. The Markdown file refers to `figures/crossmatch.sep_hist.png` next to it.

### Validate, and print every issue

```python
import json

from scireport import Report, ScireportError, check_bundle, render_bundle

# 1. Problems found while building: every issue of the failure is in exc.issues.
report = Report('Broken').add_number('a', 1).set_outline(['a', 'missing.key'])
try:
  report.build()
except ScireportError as exc:
  print(type(exc).__name__, 'exit code', exc.exit_code)
  for issue in exc.issues:
    print(issue.format())

# 2. Problems found while checking a bundle against a template: check_bundle never raises for them.
bundle = Report('Small').add_number('a', 1).add_number('unused', 2).set_outline(['a']).build()
check = check_bundle(bundle)
print(check.ok, [i.code for i in check.issues])  # True ['W401']: a warning
strict = check_bundle(bundle, strict=True)  # warnings now count as errors
print(strict.ok, strict.exit_code)  # False 2
print(json.dumps(check_bundle(bundle, template='kitchen-sink@1').to_dict()['counts']))

# 3. render_bundle raises RenderError with every issue instead.
try:
  render_bundle(bundle, template='kitchen-sink@1')
except ScireportError as exc:
  print(len(exc.issues), 'issues, first:', exc.issues[0].to_dict())
```

### Export numbers and tables for a paper

```python
from scireport import Report, export_tex, open_bundle, write_export

(
  Report('Paper numbers')
  .add_number('crossmatch.n_pairs', 3061, format='int')
  .add_number('crossmatch.sep_mean', 0.482, unit='arcsec', uncertainty=0.013, format='.3f')
  .add_table('crossmatch.summary', {'band': ['g', 'r'], 'n': [120, 98]}, caption='Sources per band.')
  .write('paper.scireport.zip', overwrite=True)
)

with open_bundle('paper.scireport.zip') as bundle:
  result = export_tex(bundle, ['crossmatch.*'], prefix='x', max_rows=10)
  print(result.macros)  # macro name (no backslash) -> key
  for path in write_export(result, 'generated'):
    print(path)
print(open('generated/numbers.tex').read())
```

`numbers.tex` holds lines such as `\newcommand{\xCrossmatchNPairs}{3,061}`. In the manuscript write
`\input{generated/numbers.tex}`, then `\xCrossmatchNPairs` wherever the number goes.

### Pre-process, then read a bundle back

```python
from scireport import Report, preprocess_bundle, render_bundle

report = (
  Report('Pre-processing')
  .add_table('crossmatch.pairs', {'sep_arcsec': [0.21, 0.48, 0.77, 0.35, 0.5, 0.66]})
  .add_preprocess(
    'core.histogram',
    inputs={'table': 'crossmatch.pairs'},
    outputs={'figure': 'crossmatch.sep_hist'},
    params={'column': 'sep_arcsec'},
  )
  .set_outline(['crossmatch.pairs', 'crossmatch.sep_hist'])
)
bundle = report.build()
done = preprocess_bundle(bundle)  # runs the steps; `bundle` itself is not modified
print(done.bundle.manifest.values['crossmatch.sep_hist'].kind, [s.name for s in done.steps])
# render_bundle(bundle) would run the steps first on its own (preprocess=True).
result = render_bundle(bundle, formats=['md'])
print(sorted(result.files))
```

```python
import scireport
from scireport import open_bundle, write_bundle

with open_bundle('crossmatch.scireport.zip') as bundle:
  print(bundle.form, bundle.manifest.meta.title, len(bundle.manifest.values), 'values')
  print(bundle.manifest.values['crossmatch.n_pairs'].value)  # a typed value model
  print(bundle.read_table('crossmatch.pairs').to_pandas().head(2))  # needs pandas
  print(bundle.read_text('summary'))
  print(bundle.verify())  # [] when every hash and size matches
  write_bundle(bundle, 'unpacked', form='directory', overwrite=True)  # convert to a directory
for item in scireport.list_templates() + scireport.list_layouts():
  print(item)
```

## Where to go next

- The data file itself: `references/data-file.md`.
- The same operations from the shell, with exit codes: `references/cli.md`.
- Which keys and columns a template reads: `references/templates-and-layouts.md`.
- A job end to end (Markdown plus PDF, citations, numbers for a paper): `references/recipes.md`.
