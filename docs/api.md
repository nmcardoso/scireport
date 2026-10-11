# Python API

Everything below is importable from the top-level package: `from scireport import Report, render_bundle`. The heavier
names (`render_bundle`, `check_bundle`, `export_tex`, ...) load on first use, so `import scireport` stays fast. The API
follows semantic versioning; a name is removed only after at least one minor version of deprecation warnings
([Compatibility policy](compatibility.md)).

## Public names

Generated from `scireport.__all__`; a snapshot test fails when a name is added or removed without a release note.

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
| `__version__` | constant | `= '1.0.0'` |  |
| `check_bundle` | function | `(bundle: 'Bundle', *, template: 'str \| Path \| None' = None, layout: 'str \| Path \| None' = None, formats: 'Sequence[str] \| None' = None, options: 'Mapping[str, object] \| None' = None, markup_engine: 'str \| None' = None, math_renderer: 'str \| None' = None, pdf_engine: 'str \| None' = None, latex_engine: 'str \| None' = None, md_split: 'bool \| None' = None, strict: 'bool' = False, render: 'bool' = True, preprocess: 'bool' = True, allow_import: 'bool' = False, cache_dir: 'Path \| None' = None, office_source: 'str \| None' = None, reference_doc: 'Path \| None' = None) -> 'ValidationReport'` | Validate a bundle, and render it in memory to find what only a render can show. |
| `export_tex` | function | `(bundle: 'Bundle', keys: 'Sequence[str] \| None' = None, *, prefix: 'str' = '', bare: 'bool' = False, graphics_prefix: 'str' = '', max_rows: 'int \| None' = None) -> 'ExportResult'` | Export values of a bundle as LaTeX fragments. |
| `figure` | function | `(width: 'float' = 1.0, height: 'float' = 3.6, nrows: 'int' = 1, ncols: 'int' = 1, *, layout: 'str' = 'default', paper: 'str' = 'a4', subplot_kw: 'dict[str, Any] \| None' = None, constrained: 'bool' = True) -> 'tuple[Figure, Any]'` | Create a figure at its final size, as a fraction of the page frame, in the style of a layout. |
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

## The `Report` builder

`Report` builds a bundle from Python. Each `add_*` method creates one value under a semantic key and, optionally, puts
it in the outline.

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

## Docstrings

The complete docstrings of the main classes and functions, as the source states them.

```{eval-rst}
.. llms-txt-ignore-start
```

```{autoclass} scireport.Report
:members:
```

```{autofunction} scireport.render_bundle
```

```{autofunction} scireport.check_bundle
```

```{autofunction} scireport.open_bundle
```

```{autofunction} scireport.write_bundle
```

```{autofunction} scireport.parse_manifest
```

```{autofunction} scireport.preprocess_bundle
```

```{autofunction} scireport.export_tex
```

```{autofunction} scireport.write_export
```

```{autofunction} scireport.list_templates
```

```{autofunction} scireport.list_layouts
```

```{autoclass} scireport.RenderResult
:members:
```

```{autoclass} scireport.ValidationReport
:members:
```

```{autoclass} scireport.Issue
:members:
```

```{autoclass} scireport.Bundle
:members:
```

```{autoclass} scireport.ExportResult
```

```{eval-rst}
.. llms-txt-ignore-end
```

## Exceptions

Every exception derives from `ScireportError` and carries an error `code` ([Error codes](errors.md)).

```{eval-rst}
.. llms-txt-ignore-start
```

```{autoclass} scireport.ScireportError
:members:
```

```{eval-rst}
.. llms-txt-ignore-end
```

<!-- generated:exceptions -->
| Exception | Base class | Raised when |
|---|---|---|
| `BundleError` | `ScireportError` | A bundle cannot be read or written (E4xx). |
| `ExportError` | `ScireportError` | Values cannot be exported as LaTeX fragments (E807, E808, or E103 for an unknown key). |
| `KeyConflictError` | `ScireportError` | A key is added twice, or collides with another key, in a `Report` (E104, E102). |
| `MissingDependencyError` | `ScireportError` | A dependency is missing: pango, TeX Live (E901), pandoc (E506) or an extra (E607, E904). |
| `PandocError` | `ScireportError` | Pandoc ran and failed, or the converted content cannot be used (E507, E212). |
| `PdfError` | `ScireportError` | A PDF engine ran and failed; the issues carry the engine's own messages (E902). |
| `PreprocessError` | `ScireportError` | Pre-processing steps are invalid; carries every problem found before anything runs (E6xx). |
| `PreprocessRunError` | `ScireportError` | A pre-processor raised while it ran (E606); the data file itself is not at fault. |
| `RenderError` | `ScireportError` | Validation or rendering found problems; carries every one of them (ADR-0005). |
| `ScireportError` | `Exception` | Base class of every error scireport raises on purpose. |
| `SpecError` | `ScireportError` | A manifest does not match the data-file specification (E1xx to E3xx). |
| `SpecVersionError` | `ScireportError` | The spec version of a bundle cannot be read by this scireport (E5xx). |
| `TemplateError` | `ScireportError` | A template or layout cannot be found, loaded or used (E504, E505, E7xx). |
<!-- /generated -->
