# The data file (report bundle)

The data file is the contract between your code and the report. A *report bundle* holds one
manifest (structure, text, numbers, metadata) plus the binary files it points to (tables, figures,
images). Template and layout only decide how it looks. A bundle holds summaries, not raw
catalogues: aggregate first (a histogram, HEALPix counts), then store the result.

## The three forms

| Form | What it is | Written by |
|---|---|---|
| directory | `scireport.json` (or hand-authored `scireport.yaml`) plus `assets/<folder>/<file>` | you, `scireport unpack`, `Report.write('x.scireport')` |
| ZIP | `*.scireport.zip`: the same layout, entries sorted, fixed 1980 timestamps, byte-reproducible | `scireport pack`, `Report.write('x.scireport.zip')` |
| single file | one `.json` (or `.yaml`) manifest that needs no assets (or points at files next to it) | you, `Report.write('x.json')` |

```text
my-report/
  scireport.yaml            # or scireport.json; only one of them
  assets/
    tables/pairs.parquet    # folders: attachments, figures, images, tables, text
    figures/sep.png
    figures/sep.pdf
    text/refs.bib
```

- YAML is for hand-authored directories only. A ZIP always holds `scireport.json`; a ZIP with a YAML
  manifest is `E409`.
- Every command and function that takes a bundle takes any of the three forms.
- `scireport pack SRC` completes a hand-authored directory: it computes `sha256` and `bytes` of every
  asset, pins the template and layout to `name@version` (and records the pandoc version when pandoc is
  used), leaves out files no value references, and writes the canonical ZIP. `scireport unpack` reverses it
  into a directory, checking every hash. `scireport inspect SRC` lists the values and verifies the hashes;
  `inspect SRC --key a.b` prints one canonical value.
- Opening a bundle never needs a template or a layout; `validate` and `render` do.

## The manifest blocks

The manifest is a mapping with these top-level blocks (fields are in the reference below):

- `scireport` (required): the spec version as a string, `'1.0'`. Quote it, or YAML reads a number. A
  newer minor version than the installed package reads is `E501`; this package reads every older one.
- `meta` (required, `title` is the only required field): title, subtitle, `authors` (strings or
  `{name, affiliation, orcid}`), `date` (ISO 8601, never filled in for you), version, abstract, keywords,
  `language`. It feeds the cover and running heads.
- `render`: the choices that travel with the data: `template` and `layout` (`generic@1`, `default@1`;
  a bare name means the newest), `formats` (`md`, `html`, `tex`, `pdf`, `docx`, `odt`, `epub`), the engines,
  and layout `options` (scalars such as `paper: letter`). Command-line flags override it.
- `outline`: used only by the built-in `generic` template. A list of keys (a leaf: draws that value) and
  `{title, children}` headings. A value that no template draws and that is not in the outline gives `W401`.
- `values`: key to value. This is where the content is.
- `preprocess`: steps that make figures and tables from values at render time (see
  `references/preprocessors.md`).
- `provenance`: `generator` (`{name, version}` of your program), `inputs` (`{name, sha256, uri}` of what the
  numbers were computed from) and `writer` (set by `Report`). Informational; nothing renders it.

Minimal complete data file (hand-authored YAML; this validates and renders as it stands):

```yaml
scireport: '1.0'
meta:
  title: Cross-match report
  authors: [Ada Lovelace]
render:
  template: generic@1
  formats: [md, html]
outline:
  - crossmatch.n_pairs
values:
  crossmatch.n_pairs:
    kind: number
    value: 3061
    unit: pairs
    format: int
```

The same value in the JSON of a packed bundle (`scireport.json`, key by key):

```json
{"crossmatch.n_pairs": {"kind": "number", "value": 3061, "unit": "pairs", "format": "int"}}
```

## Manifest reference

<!-- generated:manifest -->
### `Manifest`

The whole manifest (`scireport.json`).

| Field | Type | Default | Meaning |
|---|---|---|---|
| `scireport` | `str` | required | Spec version, ``MAJOR.MINOR``. |
| `meta` | `Meta` | required | Document metadata. |
| `render` | `Render` | Render(template=None, layout=None, formats=[], pdf_engine=None, latex_engine=None, markup_engine=None, math_renderer=None, pandoc_version=None, options={}) | Rendering choices. |
| `outline` | `list[OutlineNode] \| None` | None | Outline for the ``generic`` template. |
| `values` | `dict[str, Value]` | {} | Key to value; keys follow the key grammar and may not be prefixes of one another. |
| `preprocess` | `list[PreprocessStep]` | [] | Pre-processing steps. |
| `provenance` | `Provenance` | Provenance(generator=None, writer=None, inputs=[]) | Origin of the content. |

### `Meta`

Document metadata (the cover and running heads).

| Field | Type | Default | Meaning |
|---|---|---|---|
| `title` | `str` | required | Report title. |
| `subtitle` | `str \| None` | None | Line under the title. |
| `authors` | `list[Author]` | [] | Authors in order; a bare string is a name. |
| `date` | `str \| None` | None | ISO 8601 date, never filled in automatically (outputs hold no wall-clock time). |
| `version` | `str \| None` | None | Version of the report or of the data it describes. |
| `pipeline` | `str \| None` | None | Name of the pipeline or software that produced the content. |
| `footer` | `str \| None` | None | Running footer text. |
| `abstract` | `str \| None` | None | Summary, Markdown. |
| `keywords` | `list[str]` | [] | Keywords. |
| `language` | `str` | 'en' | BCP 47 language tag of the text. |

### `Author`

A report author.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `name` | `str` | required | Full name. |
| `affiliation` | `str \| None` | None | Institution. |
| `orcid` | `str \| None` | None | ORCID iD such as ``0000-0002-1825-0097``. |

### `Render`

How to render: the template, the layout and the engines.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `template` | `str \| None` | None | Template name, for example ``generic@1``. |
| `layout` | `str \| None` | None | Layout name, for example ``default@1``. |
| `formats` | `list[Literal['md', 'html', 'tex', 'pdf', 'docx', 'odt', 'epub']]` | [] | Output formats wanted. |
| `pdf_engine` | `Literal['weasyprint', 'latex'] \| None` | None | PDF engine. |
| `latex_engine` | `Literal['lualatex', 'xelatex', 'pdflatex'] \| None` | None | TeX engine for ``pdf_engine: latex``. |
| `markup_engine` | `Literal['mistletoe', 'pandoc'] \| None` | None | Markdown converter. |
| `math_renderer` | `Literal['mathtext', 'usetex'] \| None` | None | How math becomes SVG for HTML and WeasyPrint. |
| `pandoc_version` | `str \| None` | None | The pandoc version the content was written and checked with (set by ``pack``); a render that uses pandoc with another version warns (``W501``). |
| `options` | `dict[str, str \| int \| float \| bool \| None]` | {} | Layout options (paper, cover, toc, accent, chapter breaks) as scalars. |

### `OutlineNode`

One entry of the outline used by the built-in `generic` template.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `title` | `str \| None` | None | Heading text. |
| `key` | `str \| None` | None | Key of the value to show. |
| `children` | `list[OutlineNode]` | [] | Entries under a heading. |
| `md_file` | `str \| None` | None | For a heading: write its chapter to this separate Markdown file. |
| `page_break` | `bool \| None` | None | Force or forbid a page break before the heading; None lets the layout decide. |
| `in_contents` | `bool` | True | List the heading in the table of contents. |

### `PreprocessStep`

One pre-processing step, declared by registered name (ADR-0006).

| Field | Type | Default | Meaning |
|---|---|---|---|
| `name` | `str` | required | Registered pre-processor name such as ``core.histogram``; ``module:func`` needs ``--allow-import``. |
| `version` | `int \| None` | None | The pre-processor version the step was written for. |
| `id` | `str \| None` | None | Identifier other steps and messages can use. |
| `inputs` | `dict[str, str]` | {} | Port name to value key. |
| `outputs` | `dict[str, str]` | {} | Port name to the value key the result is stored under. |
| `params` | `dict[str, JsonValue]` | {} | JSON parameters, validated by the pre-processor. |

### `Provenance`

Where the content came from.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `generator` | `Generator \| None` | None | The producing program. |
| `writer` | `str \| None` | None | ``scireport <version>`` of the writer, set by :class:`~scireport.report.Report`. |
| `inputs` | `list[InputRef]` | [] | The inputs, with hashes where they are files. |
<!-- /generated -->

## Keys

A key names a value by meaning: `crossmatch.n_pairs`, `quality.sep_hist`, `summary`.

- Dotted path; each segment matches `[a-z0-9_-]+`, segments joined by single dots. Anything else is
  `E101` (with a "did you mean" hint, for example `Bad_Key` to `bad_key`).
- The kind of a value lives in the value (`kind: table`), never in the key. Turning a table into a figure
  does not rename it, and templates never break.
- A key may not be the dotted prefix of another key: `a` and `a.b` together is `E102`. Group with the
  dots instead (`a.total`, `a.b`).
- Keys are unique (`E104` in `Report`; a duplicate YAML key is a parse error, `E408`).
- Templates read a value as `data.crossmatch.n_pairs`, or `v('crossmatch.n_pairs')` when the key is
  computed (that one cannot be checked in advance, so it warns `W403`). `scireport templates NAME --json`
  lists the keys, kinds and table columns a template reads; build the bundle to match.

## Bare JSON shorthand

Anywhere a value is expected you may write plain JSON. It is canonicalised on load, so
`scireport inspect SRC --key KEY` shows the envelope form:

| You write | It becomes |
|---|---|
| a string | `{kind: text, text: "...", format: plain}` |
| `true` / `false` | `{kind: bool, value: true}` |
| a number | `{kind: number, value: 3061}` |
| `null` | `{kind: number, value: null}` (a missing number) |
| a list | `{kind: list, items: [...]}` (members are canonicalised too) |
| a mapping without `kind` | `{kind: mapping, entries: [{key, value}, ...]}` in the order written |
| a mapping with a `kind` member | always an envelope of that kind; unknown kind is `E201` |

A string that looks like a date stays text: `when: 2026-10-09` is a text value. Write
`{kind: date, value: 2026-10-09}` for a date. Markdown, units, formats and files need the envelope form.

## Value kinds

Every value is an envelope: a mapping with a `kind` and the fields of that kind. Unknown fields are
`E204`, a missing required field `E203`, a bad value `E205`, giving both of two exclusive fields (for
example `text` and `asset`) `E206`.

### One example per kind

Each snippet goes under `values:` of a hand-authored `scireport.yaml`. They were validated together
(`scireport validate`). A file field (`asset`, `renditions`, `data`, `csl`) is a bare path string here;
`scireport pack` fills in `sha256` and `bytes`. In a packed bundle it is
`{path: assets/tables/pairs.parquet, sha256: ..., bytes: 718}`.

```yaml
# text: inline, or a file in assets/text/ for long prose. format: plain | markdown | latex
summary:
  kind: text
  format: markdown
  text: |
    Pairs agree with earlier work [@doe2020, p. 3]; see also [-@doe2020].
method:
  kind: text
  format: markdown
  asset: assets/text/method.md
raw.latex:                # raw TeX; html and md outputs use the alt replacements
  kind: text
  format: latex
  text: '\textbf{Bold} in TeX'
  alt: {html: '<b>Bold</b> in HTML', md: '**Bold** in Markdown'}

# number: value (int or float, or null for missing), unit, format, uncertainty or interval
results.n_pairs:
  {kind: number, value: 3061, unit: pairs, format: int}
results.sep_mean:         # shown as 0.482 ± 0.013 arcsec
  {kind: number, value: 0.482, unit: arcsec, uncertainty: 0.013, format: .3f}
results.sep_range:        # asymmetric: interval instead of uncertainty (not both)
  {kind: number, value: 0.5, interval: [0.4, 0.7]}
results.missing_example:  # no value: shows the `missing` text, or the renderer's placeholder
  {kind: number, value: null, missing: n/a}

results.complete: {kind: bool, value: true}

run.date: {kind: date, value: 2026-10-09}    # ISO 8601 date or date-time

run.steps:                # list: members are bare JSON or envelopes
  kind: list
  ordered: true
  items:
    - Load catalogues
    - {kind: number, value: 2}

run.config:               # mapping: labelled entries in a fixed order (a description list)
  kind: mapping
  entries:
    - key: Radius
      value: {kind: number, value: 1.0, unit: arcsec}
    - key: Catalogue
      value: DR2

# table, inline: columns name and order the cells; rows are JSON scalars (small tables only)
results.small:
  kind: table
  caption: A small inline table.
  columns:
    - {name: name, label: Name}
    - {name: sep, label: Separation, unit: arcsec, format: .2f, align: right}
  rows:
    - [a, 0.5]
    - [b, 1.25]
# table, from a file: Parquet or CSV in assets/tables/; columns (optional) select and style them
results.pairs:
  kind: table
  caption: Matched pairs.
  columns:
    - {name: name}
    - {name: sep, unit: arcsec}
  asset: assets/tables/pairs.parquet
results.sources:
  kind: table
  asset: assets/tables/sources.csv
# table, with per-row verdicts, cell emphasis and a row cap
checks:
  kind: table
  columns: [{name: check}, {name: result}]
  rows: [[astrometry, ok], [photometry, bad]]
  row_status: [pass, fail]                 # pass | warn | fail | null, one per row
  emphasis: [{row: 1, column: result, style: fail}]   # strong | muted | pass | warn | fail
  max_rows: 10                             # the rest goes to `overflow_attachment: <attachment key>`

# figure: one rendition per format (png, pdf, svg); alt text is required; width is a fraction
results.sep_hist:
  kind: figure
  alt: Histogram of pair separations in arcsec.
  caption: Separations.
  width: 0.8
  renditions:
    - assets/figures/sep.png
    - assets/figures/sep.pdf
  data: assets/figures/sep.data.parquet    # optional sidecar: the data the figure was drawn from

# image: a logo or photo, not generated from data (png, jpg, jpeg, svg, pdf); alt omitted = decorative
logo:
  kind: image
  alt: Project logo
  width: 0.3
  asset: assets/images/logo.png

eq.match:                 # math: LaTeX without $ delimiters
  kind: math
  latex: 'd < r_{\mathrm{match}}'
  numbered: true

snippet:                  # code: inline source or a text asset; language is optional
  kind: code
  language: python
  source: print('hello')

headline:                 # metrics: a grid of tiles; each value is a number or a text
  kind: metrics
  items:
    - label: Pairs
      value: {kind: number, value: 3061, format: int}
      detail: after cuts
    - {label: Catalogue, value: DR2}

verdict:                  # status: success | warning | partial | failed | running
  {kind: status, level: success, headline: COMPLETED SUCCESSFULLY, detail: All checks passed.}

note:                     # alert: info | warning | error
  {kind: alert, level: warning, text: Photometry is preliminary.}

pipeline:                 # flow: numbered stages
  kind: flow
  stages:
    - {label: Load, detail: [2 catalogues]}
    - {label: Match, state: reused}   # done (default) | reused | skipped | failed | running | pending

full_table:               # attachment: a file offered next to the report (assets/attachments/)
  kind: attachment
  filename: pairs.csv
  media_type: text/csv
  description: Every matched pair.
  asset: assets/attachments/pairs.csv

references:               # bibliography: see "Citations" below
  kind: bibliography
  asset: assets/text/refs.bib
  style: authoryear
```

## Kind reference

Defaults and exact types of every field. The examples above are the quick way in.

<!-- generated:kinds -->
### `text`

Prose or a short string: inline `text` or a file in `assets/text/`.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `text` | `str \| None` | None | The content, inline. Exactly one of ``text`` and ``asset`` is given. |
| `asset` | `AssetRef \| None` | None | A Markdown, plain-text or LaTeX file, for long content. |
| `format` | `Literal['plain', 'markdown', 'latex']` | 'plain' | How the content is marked up. ``latex`` is emitted verbatim in TeX output. |
| `alt` | `dict[Literal['html', 'md'], str] \| None` | None | For ``latex`` text, the replacement used by other outputs: keys ``html`` and ``md``. |

### `number`

A number with its presentation and uncertainty.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `value` | `int \| float \| None` | None | The number; None means missing. Never NaN or infinite. |
| `unit` | `str \| None` | None | Unit, free text (``'arcsec'``, ``'deg^2'``). |
| `format` | `str \| None` | None | A name from the number filters (``'int'``, ``'pct'``, ``'sci'``, ...) or a Python format specification (``',.2f'``). Resolved by the renderer. |
| `uncertainty` | `float \| None` | None | Symmetric uncertainty, at least 0. Excludes ``interval``. |
| `interval` | `tuple[int \| float, int \| float] \| None` | None | Lower and upper bound of an asymmetric interval. Excludes ``uncertainty``. |
| `missing` | `str \| None` | None | Text shown when ``value`` is None; the renderer's placeholder when None. |

### `bool`

A boolean.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `value` | `bool` | required | The truth value. |

### `date`

A calendar date or date-time, stored in canonical ISO 8601 form.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `value` | `str` | required | ``YYYY-MM-DD`` or an ISO 8601 date-time. Normalised on load by :func:`canonical_date`. |

### `list`

An ordered list of values (any kind, nested).

| Field | Type | Default | Meaning |
|---|---|---|---|
| `items` | `list[Value]` | required | The members. Bare JSON members are canonicalised. |
| `ordered` | `bool` | False | Whether the list is numbered when rendered. |

### `mapping`

Labelled metadata entries in a fixed order (a description list).

| Field | Type | Default | Meaning |
|---|---|---|---|
| `entries` | `list[MappingEntry]` | required | The entries, in display order. |

### `table`

A table: a Parquet or CSV file in `assets/tables/`, or a small inline table.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `columns` | `list[Column]` | [] | Column presentation. For an inline table it also names the columns and fixes their order; for a file it is optional and selects and orders the columns shown. |
| `asset` | `AssetRef \| None` | None | A ``.parquet`` or ``.csv`` file. Exactly one of ``asset`` and ``rows`` is given. |
| `rows` | `list[list[str \| int \| float \| bool \| None]] \| None` | None | Inline rows of JSON scalars, one cell per column. |
| `caption` | `str \| None` | None | Caption below the table. |
| `n_rows` | `int \| None` | None | Number of rows in the data, recorded by the writer. |
| `row_status` | `list[Literal['pass', 'warn', 'fail'] \| None] \| None` | None | Per row ``pass``, ``warn``, ``fail`` or None (inline tables). Excludes ``row_status_column``. |
| `row_status_column` | `str \| None` | None | Name of a data column that holds the per-row verdicts. |
| `emphasis` | `list[CellEmphasis]` | [] | Cells to emphasise. |
| `max_rows` | `int \| None` | None | Show at most this many rows; the rest is available through ``overflow_attachment``. |
| `overflow_attachment` | `str \| None` | None | Key of an ``attachment`` value with the full table, linked when rows are cut. |

### `figure`

A figure with one or more renditions, required alt text and optional sidecar data.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `renditions` | `list[Rendition]` | required | At least one, at most one per format. LaTeX output prefers PDF, then PNG; SVG is never used in LaTeX. |
| `alt` | `str` | required | Alternative text. Required and not blank. |
| `caption` | `str \| None` | None | Caption below the figure. |
| `width` | `float` | 1.0 | Width as a fraction of the frame, in (0, 1]. |
| `data` | `AssetRef \| None` | None | A ``.parquet`` or ``.csv`` sidecar with the data the figure was drawn from. |

### `image`

A picture that is not generated from data (a logo, a photo, a diagram).

| Field | Type | Default | Meaning |
|---|---|---|---|
| `asset` | `AssetRef` | required | A ``.png``, ``.jpg``, ``.jpeg``, ``.svg`` or ``.pdf`` file in ``assets/images/``. |
| `alt` | `str \| None` | None | Alternative text; None marks a decorative image. |
| `caption` | `str \| None` | None | Caption below the image. |
| `width` | `float` | 1.0 | Width as a fraction of the frame, in (0, 1]. |

### `math`

A mathematical expression in LaTeX.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `latex` | `str` | required | The expression, without ``$`` delimiters. |
| `display` | `bool` | True | Display (own line) rather than inline style. |
| `numbered` | `bool` | False | Whether a display equation gets a number. |
| `caption` | `str \| None` | None | Text below the equation. |

### `code`

Source code or preformatted text: inline `source` or a file in `assets/text/`.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `source` | `str \| None` | None | The code, inline. Exactly one of ``source`` and ``asset`` is given. |
| `asset` | `AssetRef \| None` | None | A text file. |
| `language` | `str \| None` | None | Language name for highlighting (``'python'``, ``'sql'``); none means preformatted text. |
| `caption` | `str \| None` | None | Text below the block. |

### `metrics`

A grid of headline numbers.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `items` | `list[MetricItem]` | required | At least one tile, in display order. |

### `status`

An overall verdict banner.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `level` | `Literal['success', 'warning', 'partial', 'failed', 'running']` | required | The verdict. |
| `headline` | `str` | required | One line, for example ``COMPLETED SUCCESSFULLY``. |
| `detail` | `str \| None` | None | Explanation under the headline. |

### `alert`

A one-line call-out.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `level` | `Literal['info', 'warning', 'error']` | required | Severity. |
| `text` | `str` | required | The message. |

### `flow`

A pipeline drawn as numbered stages.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `stages` | `list[FlowStage]` | required | At least one stage, numbered from 1 in order. |

### `attachment`

A file offered alongside the report (for example the full table behind a cut one).

| Field | Type | Default | Meaning |
|---|---|---|---|
| `asset` | `AssetRef` | required | The file in ``assets/attachments/``. |
| `filename` | `str` | required | Name shown to the reader and used on download: no path separators. |
| `media_type` | `str \| None` | None | MIME type, for example ``text/csv``. |
| `description` | `str \| None` | None | What the file contains. |

### `bibliography`

The references that `[@key]` citations in prose refer to (ADR-0011).

| Field | Type | Default | Meaning |
|---|---|---|---|
| `asset` | `AssetRef` | required | A BibTeX (BibLaTeX) file, ``.bib``, in ``assets/text/``. |
| `csl` | `AssetRef \| None` | None | A Citation Style Language file, ``.csl``, in ``assets/text/``: how pandoc formats the citations of the Markdown and HTML outputs. None uses pandoc's default style. |
| `style` | `str \| None` | None | The ``biblatex`` style of the LaTeX output (``authoryear``, ``numeric``, ...); None uses the biblatex default. |
<!-- /generated -->

## Assets

Binary and long-text files live under `assets/<folder>/<file>` and are referenced by `path`:

| Folder | Holds |
|---|---|
| `tables` | `.parquet` (zstd) or `.csv` tables |
| `figures` | figure renditions (`.png`, `.pdf`, `.svg`) and their `.parquet` sidecar data |
| `images` | pictures: `.png`, `.jpg`, `.jpeg`, `.svg`, `.pdf` |
| `text` | long text and code (`.md`, `.txt`, `.tex`), the `.bib` and `.csl` files |
| `attachments` | files offered with the report (`.csv`, ...) |

- Path rules (`E404` otherwise): relative, `/` as separator, at most 180 characters, no `.` or `..`
  segments, each segment matches `[A-Za-z0-9][A-Za-z0-9._-]*`, does not end in a dot and is not a Windows
  reserved name (`con`, `nul`, `com1`, ...). The folder must be one of the five above.
- A sealed bundle (ZIP, or JSON after `pack`) gives every asset as `{path, sha256, bytes}`. In a
  hand-authored directory `sha256` and `bytes` may be left out, or the whole reference written as the bare
  path; they are computed from the files, and `pack` writes them down.
- `inspect SRC` verifies hashes and sizes: `E402` (hash differs), `E403` (size differs). `E401` is a file
  the manifest names that is not there, `E411` one path declared with two different hashes. Opening a ZIP
  rejects unsafe entries such as zip-slip paths (`E407`) and a bundle over the size cap (`E405`, default
  1 GiB, `--max-size` in MiB). A file in `assets/` that no value references is `W402`.

## YAML rules (hand-authored `scireport.yaml`)

The YAML reader follows the YAML 1.2 core schema and is stricter than most:

- Only `true` and `false` are booleans. `yes`, `no`, `on`, `off` are strings, and `12:30` is a string.
- A date such as `2026-10-09` is a string, never a date object. Quote the spec version (`'1.0'`).
- Anchors and aliases (`&a`, `*a`) are rejected. Duplicate keys are rejected. Both are `E408`, as is any
  syntax error.
- JSON manifests reject duplicate members, `NaN` and `Infinity` as well. A number that is not finite
  cannot be stored; use `null` (missing).

## Citations and the bibliography

A `bibliography` value holds a BibTeX file (`asset`, `.bib`), optionally a CSL style (`csl`, `.csl`, used
by the md and html outputs) and optionally a `biblatex` `style` (`authoryear`, `numeric`, ... used by the
tex output). A bundle holds at most one (`E211`); in Python use `Report.add_bibliography`.

- Cite inside Markdown text values (`kind: text`, `format: markdown`) with pandoc's bracketed form:
  `[@doe2020]`, `[@a, p. 3; @b]`, `[-@doe2020]` (year only, in author-date styles). Only the bracketed
  form is read; `@doe2020` alone is plain text. Citations inside code spans and code blocks are left
  alone. Captions are not Markdown: a citation there stays literal text.
- A cited key that the `.bib` file does not have is `E212`, with the closest key as a hint.
- md and html: citations are formatted by pandoc's citeproc (needs `scireport[pandoc]`, otherwise `E506`
  with an install hint). The bundle then records the pandoc version; a different one at render time is
  `W501`. tex: `biblatex` with `biber` (no pandoc needed); the project holds `references.bib`.
- The reference list is drawn by `c.references()` in a template. The built-in `generic` template draws it
  where the bibliography value is listed in the outline, so list its key last: `outline: [..., references]`.
- Without a bibliography value nothing is treated as a citation, so older bundles render as before.

## Where to go next

- Build the same data from Python: `references/python-api.md`.
- Validate and render from the shell, and the exit codes: `references/cli.md`.
- What a template reads from `data`, components and layouts: `references/templates-and-layouts.md`.
- Steps that make figures and summary tables at render time: `references/preprocessors.md`.
- Figures in the report's style: `references/mplstyle.md`.
- What an `E`/`W` code means and what to do: `references/errors.md`.
- End-to-end jobs (Markdown for a model plus one PDF, citations, numbers for a paper):
  `references/recipes.md`.
