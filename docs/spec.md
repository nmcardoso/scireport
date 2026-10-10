# The data-file specification

The data file (a *report bundle*) is the one input that carries the content of a report: its metadata, its text, its
numbers and the files behind its tables and figures. A template and a layout decide how that content is laid out and
how it looks; they never change what it says. This page is the reference for anyone, person or program, who writes or
reads a bundle. For a guided tour see [User guide](guide.md); for the commands see [Command line](cli.md).

## Purpose and status

**The data file is the contract** (ADR-0008). The producer of a report and the engine that renders it agree on this
format and on nothing else. Because of that:

- The spec version is stored in every bundle, in the top-level `scireport` entry (`'1.0'`), and in every template
  and layout, as the range of spec versions it supports (`spec: ">=1.0,<2.0"` in `template.yaml` and `layout.yaml`).
- This package reads every older minor version of the major it supports natively. A change that alters how an old
  bundle renders is a bug, not a feature (see [Compatibility policy](compatibility.md)).
- A bundle holds **summaries, not raw catalogues** (ADR-0001). Aggregate first (a histogram, HEALPix counts, a
  per-bin table) and store the result. The size cap of a ZIP bundle (1 GiB by default) is a safety limit, not a target.

The newest version this package reads and writes is printed by `scireport spec version` and is
`scireport.spec.version.SPEC_VERSION`: **1.0**.

Spec 1.0 becomes frozen with the final 1.0.0 release. Until then it can still receive additions: the `bibliography`
kind was added after the first draft, as a new case of the compat corpus and not as a change of an existing one. The
policy that applies after the release is in [Compatibility policy](compatibility.md).

## The three physical forms

A bundle has one logical layout: a manifest and, optionally, an `assets/` folder. It can be stored in three ways.
Every command and function that takes a bundle takes any of them, and `scireport inspect` shows which one it found.

| Form | Name | Manifest | Written by |
|---|---|---|---|
| directory | `<name>.scireport/` | `scireport.json`, or `scireport.yaml` / `scireport.yml` when hand-authored | you, `scireport unpack`, `scireport new` |
| ZIP | `<name>.scireport.zip` | `scireport.json` only | `scireport pack`, `Report.write('x.scireport.zip')` |
| single file | any `.json` (or `.yaml`) file | the file itself | you, `scireport pack x.yaml -o x.json` |

The names are conventions. The reader does not look at them: a directory is a directory, a file that is a ZIP archive
is read as a ZIP whatever its extension, and any other `.json`, `.yaml` or `.yml` file is read as a single-file
manifest. Anything else is `E406`. When *writing*, the form comes from the destination: `.zip` gives a ZIP, `.json`
a single file and anything else a directory.

### Directory

```text
my-report.scireport/
  scireport.yaml            # or scireport.json; exactly one of the manifest names
  assets/
    tables/pairs.parquet    # folders: attachments, figures, images, tables, text
    figures/sep.png
    figures/sep.pdf
    text/refs.bib
```

- The manifest sits at the root. Two manifests in one directory (`scireport.json` and `scireport.yaml`) is `E409`; a
  directory with none is `E406`.
- Only the manifest and the files under `assets/` belong to the bundle. Other files are ignored.
- YAML is accepted **only** here (and for a single-file manifest). It exists so that a person or an agent can write
  a data file by hand. `scireport pack` turns it into the canonical form.
- A hand-authored manifest may leave out the `sha256` and `bytes` of an asset, or write the reference as a bare path;
  the reader computes them from the files. See [References and hashes](#references-and-hashes).
- Symbolic links are refused (`E404`): a file that is a link, or that resolves outside the bundle directory, is not
  read.

### ZIP

The ZIP is the sealed, shareable form. `scireport pack` completes a hand-authored directory (it computes every hash,
writes the manifest as canonical JSON, pins the template and layout, and leaves out files that no value references)
and writes the archive. The archive is built so that packing the same content twice gives the same bytes:

- Entries are sorted by name, each with the timestamp 1980-01-01 00:00:00, creator system Unix and mode `0644`. There
  is no archive comment.
- Media that is already compressed (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.pdf`, `.parquet`, `.zip`, `.gz`,
  `.zst`, `.xz`) is stored without compression. Everything else is deflated at level 9.
- The compressed bytes of the deflated entries depend on the zlib build, so byte identity is guaranteed for one Python
  and zlib; the hashes inside the manifest never depend on it.
- The archive is written to a temporary name and moved into place, so an interrupted write never leaves half a file.

A ZIP is checked before anything is read from it. These are the real limits:

| Rule | Limit | Code |
|---|---|---|
| Entry name is a safe relative path: no leading `/` or drive letter, no `..`, `.` or empty segment, no backslash, no NUL (zip-slip) | every entry | `E407` |
| Entries under `assets/` follow the asset path rules | every entry | `E407` |
| No symbolic links, no encrypted entries, no two entries that differ only by case | every entry | `E407` |
| Number of entries | 10,000 | `E405` |
| Sum of the declared uncompressed sizes | 1 GiB by default; `--max-size` (MiB) on `pack`, `unpack` and `inspect`, `max_bytes` in Python | `E405` |
| Size of the manifest | 32 MiB | `E408` |
| A ZIP with `scireport.yaml` and no `scireport.json` | YAML is for directories | `E409` |
| No `scireport.json` at the root | | `E406` |

The writer enforces the same size cap on the content it is about to write, and refuses to overwrite an existing
destination unless `--force` (`overwrite=True`) is given (`E410`).

### Single file

A single file is one manifest, JSON or YAML. It is meant for text-only reports and for small examples. If it refers to
assets they are read from an `assets/` folder next to the file, like in a hand-authored directory. A single file
**written** by scireport cannot carry assets: asking for one is `E409`.

```json
{
  "scireport": "1.0",
  "meta": {"title": "Shorthand example"},
  "render": {"template": "generic@1"},
  "outline": ["summary", "n_pairs", "complete", "missing", "steps", "config", "when"],
  "values": {
    "summary": "Plain text is a text value.",
    "n_pairs": 3061,
    "complete": true,
    "missing": null,
    "steps": ["Load", "Match", 2],
    "config": {"radius": 1.0, "catalogue": "DR2"},
    "when": "2026-10-09"
  }
}
```

This file is valid as it stands (`scireport validate report.json`). Every value in it is bare JSON; the next sections
explain how each one is read.

### Moving between forms

| Command | What it does |
|---|---|
| `scireport pack SRC [-o DEST]` | Completes a hand-authored bundle and writes the canonical ZIP (default `<name>.scireport.zip` next to `SRC`). The destination form follows its suffix. |
| `scireport unpack SRC [-o DIR]` | Writes a directory with the manifest and the assets, checking every hash on the way. |
| `scireport inspect SRC [--key KEY]` | Lists the values and verifies every hash and size; with `--key` prints one value in its canonical form. |

Opening a bundle never needs a template or a layout. Validating and rendering do.

## The manifest

The manifest is a mapping with these top-level blocks. Unknown top-level entries are `E204`.

| Block | Required | What it holds |
|---|---|---|
| `scireport` | yes | The spec version as a string, `MAJOR.MINOR`. Quote it in YAML: `1.0` unquoted is a number and gives `E502`. |
| `meta` | yes | Title (the only required field), subtitle, authors, date, version, pipeline, footer, abstract, keywords, language. Feeds the cover and the running heads. |
| `render` | no | The choices that travel with the data: template, layout, output formats, engines, layout options. Command-line flags override them. |
| `outline` | no | The structure used by the built-in `generic` template: headings and the keys they show. |
| `values` | no (empty by default) | Key to value. This is where the content is. |
| `preprocess` | no | Steps that make figures and tables from values, by registered name (ADR-0006, [Pre-processors](preprocessors.md)). |
| `provenance` | no | Where the content came from. Informational: nothing renders it. |

A minimal data file that validates and renders as it stands (hand-authored YAML):

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

Points that the field tables below do not say:

- **`render.template` and `render.layout`** are `name` or `name@VERSION` (`generic@1`, `default@1`). A path to a
  directory is accepted on the command line, not in the manifest. A bare name means the newest version available, so
  `scireport pack` rewrites it to an explicit version; see [Compatibility policy](compatibility.md). Left unset, the defaults are
  `generic@1` and `default@1`.
- **`render.options`** holds scalar layout options (`paper: letter`, `toc: false`). Which ones exist is defined by the
  layout ([Built-in layouts](layouts.md)).
- **`outline`** is a list. A bare string is a leaf: the value at that key is drawn. A mapping with `title` is a heading,
  and its `children` are the entries below it. A node has exactly one of `title` and `key` (`E206`). Only the `generic`
  template reads the outline; a template of your own ignores it ([Writing a template](templates.md)). A value that no template draws and
  that the outline does not list is `W401`.
- **`meta.date`** is ISO 8601 and is never filled in for you (outputs hold no wall-clock time). A date is normalised on
  load (`20261009` becomes `2026-10-09`).
- **`meta.authors`** are strings or `{name, affiliation, orcid}` mappings.
- **`preprocess`** steps name registered pre-processors only; `module:function` needs `--allow-import`. A key that a
  step promises in `outputs` is not a dangling reference (`E103`) before the step has run.

### Canonical JSON

`scireport.json` is the canonical manifest. It is written as JSON with two-space indentation, non-ASCII characters
kept, a final newline, `values` sorted by key, absent optional fields left out and every other field written with its
value, defaults included. Writing defaults means that a later change of a default never changes how a stored bundle
reads. JSON manifests reject duplicate members, `NaN` and `Infinity` (`E408`).

### Manifest reference

Generated from the models in `scireport.spec.manifest`; a test fails when this block is stale.

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

A key names a value by what it means: `crossmatch.n_pairs`, `quality.sep_hist`, `summary`. The type is not part of
the name (ADR-0002). A table that later becomes a figure keeps its key, so no template and no stored bundle breaks.

**Grammar.** A key is one or more segments joined by single dots. Each segment is non-empty and matches
`[a-z0-9_-]+`: lowercase ASCII letters, digits, underscore and hyphen. As a regular expression the whole key is
`[a-z0-9_-]+(\.[a-z0-9_-]+)*`.

| Key | Valid | Why |
|---|---|---|
| `crossmatch.n_pairs` | yes | |
| `sep-hist` | yes | a hyphen is allowed |
| `Bad_Key` | no, `E101` | uppercase; the hint is `Did you mean 'bad_key'?` |
| `a..b` | no, `E101` | empty segment |
| `quality/sep hist` | no, `E101` | slash and space |

**Canonicalisation.** A valid key is its own canonical form. Keys are case-sensitive and never normalised behind your
back: an invalid key is an error with a suggestion (lowercase, whitespace, `/` and `:` turned into `-`, other
characters dropped), not a silent fix. In the canonical manifest `values` is sorted by key, so the order in which
values were added does not matter.

**Rules between keys.**

- A key may not be the dotted prefix of another key: `a` and `a.b` together is `E102`. Templates reach values through
  attribute chains (`data.a.b`), where `a` would have to be a value and a namespace at once. Group with the dots
  instead (`a.total`, `a.b`).
- A key is used once. A duplicate key in a YAML or JSON manifest is a parse error (`E408`); adding a key twice through
  the Python API is `E104`.
- A key that is referred to must exist: an outline leaf, `overflow_attachment` or a pre-processor input naming an
  absent key is `E103`, with a "did you mean" hint.

Keys appear in `values`, in the outline (`key`), in `preprocess` (`inputs` and `outputs`) and in
`overflow_attachment`; all of them follow the same grammar.

## Values and envelopes

Every entry of `values` is an **envelope**: a mapping with a `kind` and the fields of that kind. The kind tells every
reader, template and agent how to interpret the rest, so no external schema is needed to understand a bundle.

- An unknown kind is `E201`, with the closest kind as a hint.
- An unknown field is `E204`; a missing required field is `E203`; an invalid value is `E205`.
- Giving two fields of which exactly one is allowed (for example `text` and `asset`) is `E206`.

### Bare JSON shorthand

Anywhere a value is expected you may write plain JSON instead of an envelope. It is canonicalised on load, so
`scireport inspect SRC --key KEY` shows the envelope.

| You write | It becomes |
|---|---|
| a string | `{kind: text, text: "...", format: plain}` |
| `true` / `false` | `{kind: bool, value: true}` |
| a number | `{kind: number, value: 3061}` |
| `null` | `{kind: number, value: null}`: a missing number |
| a list | `{kind: list, items: [...]}`; the members are canonicalised too |
| a mapping without `kind` | `{kind: mapping, entries: [{key, value}, ...]}`, in the order written |
| a mapping with a `kind` member | always an envelope of that kind |

Two consequences. A mapping that has an entry called `kind` must be written as a full `mapping` envelope. And a string
that looks like a date stays text: `"2026-10-09"` is a `text` value, and `{kind: date, value: 2026-10-09}` is a date.
Markdown, units, number formats and files need the envelope form.

Numbers are integers or finite floats; `NaN` and infinities cannot be stored (use `null`, a missing number). A boolean
is not a number.

### The kinds

There are 17 kinds in spec 1.0 (`scireport spec kinds` lists them with their fields).

| Kind | What it is |
|---|---|
| `text` | Prose or a short string: inline, or a file for long content; plain, Markdown or raw LaTeX. |
| `number` | A number with unit, display format and an uncertainty or an interval; or a missing number. |
| `bool` | A truth value. |
| `date` | An ISO 8601 date or date-time. |
| `list` | An ordered or unordered list of values of any kind. |
| `mapping` | Labelled entries in a fixed order (a description list). |
| `table` | Rows and columns: a Parquet or CSV file, or a small inline table. Column labels, units and formats; row verdicts; cell emphasis; a row cap. |
| `figure` | One rendition per file format, required alternative text, a width, optional sidecar data. |
| `image` | A picture that is not generated from data: a logo, a photo. |
| `math` | A LaTeX expression. |
| `code` | Source code or preformatted text. |
| `metrics` | A grid of headline tiles. |
| `status` | An overall verdict banner. |
| `alert` | A one-line call-out. |
| `flow` | A pipeline drawn as numbered stages. |
| `attachment` | A file offered next to the report. |
| `bibliography` | The BibTeX file that `[@key]` citations in prose refer to; at most one per bundle (`E211`). See [Markdown in reports](markup.md) and [pandoc: markup engine, citations and office formats](pandoc.md). |

### An example with five kinds

This is a complete hand-authored directory, `scireport.yaml` plus the two asset folders it points at. It was checked
with `scireport validate`. The files `pairs.parquet`, `sep.png` and `sep.pdf` are bare paths here: the reader computes
their hash and size.

```yaml
scireport: '1.0'
meta:
  title: Cross-match report
  authors: [Ada Lovelace]
  date: 2026-10-10
render:
  template: generic@1
  formats: [md, html]
outline:
  - summary
  - crossmatch.n_pairs
  - crossmatch.sep_mean
  - crossmatch.pairs
  - crossmatch.sep_hist
  - headline
values:
  summary:
    kind: text
    format: markdown
    text: Pairs agree with the reference within **0.6 arcsec**.
  crossmatch.n_pairs:
    {kind: number, value: 3061, unit: pairs, format: int}
  crossmatch.sep_mean:
    {kind: number, value: 0.482, unit: arcsec, uncertainty: 0.013, format: .3f}
  crossmatch.pairs:
    kind: table
    caption: Matched pairs.
    columns:
      - {name: name, label: Name}
      - {name: sep, label: Separation, unit: arcsec, format: .2f, align: right}
    asset: assets/tables/pairs.parquet
  crossmatch.sep_hist:
    kind: figure
    alt: Histogram of pair separations in arcsec.
    caption: Separations.
    width: 0.8
    renditions:
      - assets/figures/sep.png
      - assets/figures/sep.pdf
  headline:
    kind: metrics
    items:
      - label: Pairs
        value: {kind: number, value: 3061, format: int}
        detail: after cuts
      - {label: Catalogue, value: DR2}
```

Reading it: `summary` is Markdown text; `crossmatch.sep_mean` is shown as `0.482 ± 0.013 arcsec`; the table is a Parquet
file whose columns are selected, labelled and formatted here; the figure has a PNG and a PDF rendition, with alt text,
which is required; the metrics tiles take a number or a text as their value.

### Kind reference

The defaults and exact types of every field, generated from the models in `scireport.spec.kinds`.

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

Binary files and long text live under `assets/` and are referenced from the manifest. An asset is never embedded in
the manifest.

| Folder | Convention |
|---|---|
| `tables` | `.parquet` (zstd) or `.csv` tables |
| `figures` | figure renditions (`.png`, `.pdf`, `.svg`) and their `.parquet` sidecar data |
| `images` | pictures: `.png`, `.jpg`, `.jpeg`, `.svg`, `.pdf` |
| `text` | long text and code (`.md`, `.txt`, `.tex`), and the `.bib` and `.csl` files of a bibliography |
| `attachments` | files offered with the report (`.csv`, ...) |

The reader checks that the folder is one of these five and that the file has the suffix its kind needs (a table
`.parquet` or `.csv`, a figure rendition `.png`, `.pdf` or `.svg` matching its `format`, an image one of its five
suffixes, a bibliography `.bib`). It does not check that a kind uses its conventional folder.

**Path rules.** A path that breaks any of these is `E404`. The rules are strict so that a bundle unpacks the same way
everywhere:

- relative to the bundle root, with `/` as the separator, starting with `assets/<folder>/` and at least one more segment;
- at most 180 characters;
- no empty, `.` or `..` segments; each segment matches `[A-Za-z0-9][A-Za-z0-9._-]*`;
- no segment ends with a dot, and none is a Windows reserved name (`con`, `prn`, `aux`, `nul`, `com1` to `com9`,
  `lpt1` to `lpt9`);
- two assets that differ only by case would collide on some systems and are refused when a bundle is written (`E404`).

### References and hashes

In a sealed bundle (a ZIP, or the JSON that `pack` writes) every asset is a mapping with its path, its SHA-256 and
its size in bytes. This is the `crossmatch.pairs` value of the example above after `scireport pack` (the hash is that of
the Parquet file used there, so yours differs):

```json
{
  "kind": "table",
  "columns": [
    {"name": "name", "label": "Name"},
    {"name": "sep", "label": "Separation", "unit": "arcsec", "format": ".2f", "align": "right"}
  ],
  "asset": {
    "path": "assets/tables/pairs.parquet",
    "sha256": "6939c7bf0a64397211df65f3bb20df35c63da5842b37d0cdf952014e540d2e37",
    "bytes": 762
  },
  "caption": "Matched pairs.",
  "emphasis": []
}
```

`sha256` is 64 lowercase hexadecimal characters and `bytes` is a non-negative integer. In a hand-authored directory
or single file both may be left out, or the whole reference written as the bare path string, as in the example above;
they are computed from the files, and `pack` writes them down. In a ZIP both are required.

Integrity is checked when an asset is read and by `scireport inspect` and `scireport validate`:

| Problem | Code |
|---|---|
| The manifest names a file that is not in the bundle | `E401` |
| The file does not hash to `sha256` | `E402` |
| The file's size differs from `bytes` (checked first, so a changed size is reported as `E403`) | `E403` |
| The same path is declared with two different hashes | `E411` |
| A file under `assets/` that no value references | `W402` |

The same figure or file may be referenced by several values, as long as every reference agrees on its hash.

## YAML rules

A hand-authored `scireport.yaml` is read more strictly than YAML usually is, so that it means what it looks like. The
reader follows the YAML 1.2 core schema where it matters:

- Only `true` and `false` are booleans. `yes`, `no`, `on`, `off` are strings, and `12:30` is a string.
- Numbers follow JSON rules: `1.0` is a float, so quote the spec version (`'1.0'`).
- A date such as `2026-10-09` is a string, never a date object. In a `meta.date` it is read as the ISO date; as a
  value it is text, unless the envelope is `kind: date`.
- Aliases (`*a`) are rejected, as are duplicate keys. Both are `E408`, like any syntax error.
- The file must be UTF-8 (a byte-order mark is ignored).

## Validation

Validation reports every problem at once, never the first one only (ADR-0005). Each problem has a stable code, the key,
the JSON pointer into the manifest, what was expected and what was found, the template `file:line` that read the key
(when a template did) and a "did you mean" hint where a close spelling exists. The codes are listed in [Error codes](errors.md).

Three layers apply to a data file.

1. **Opening the bundle** needs no template. It checks the form (`E406`, `E407`, `E409`), the size cap (`E405`), the
   parse (`E408`), the spec version (`E501` to `E503`), the structure of the manifest and of every value (`E1xx`,
   `E2xx` and the table checks `E301`, `E302`), and the references between values (`E102`, `E103`, `E202`, `E205` for
   a Markdown file used twice, `E211`, `E411`). In a hand-authored directory a missing asset is `E401` here.
2. **Verifying integrity** (`scireport inspect`, `Bundle.verify()`) checks every referenced asset against its hash and
   size (`E401` to `E403`) and reports unreferenced files (`W402`).
3. **Validating against a template and a layout** (`scireport validate`, also run by `render`) adds what depends on
   them: the keys the template reads and the values it requires (`E105`, `E106`, `E207`), the table columns it needs
   (`E303` to `E305`), unused values and keys computed at render time (`W401`, `W403`), the spec range and the formats
   they support (`E505`, `E706`), layout options (`E806`) and the content that an output cannot show (`E209`, `E210`).
   With `--strict` warnings fail too.

Families: `E1xx` keys, `E2xx` kinds and value fields, `E3xx` tables, `E4xx` assets and bundle files, `E5xx` versions
(and pandoc), `W4xx` unused or unchecked values. `scireport validate` exits 0 when valid and 2 when not; add `--json`
for a machine-readable report.

```json
{
  "ok": false,
  "issues": [
    {
      "code": "E102",
      "severity": "error",
      "message": "key 'a' holds a value and is also the prefix of 'a.b'",
      "pointer": "/values/a",
      "key": "a",
      "hint": "Rename one of them; templates reach values through data.a.b.c chains."
    }
  ]
}
```

That is the output of `scireport validate --json` for a manifest whose `values` hold both `a` and `a.b`. A problem
in the structure of the manifest stops the checks that need a well-formed manifest, so fix `E101`, `E201` and the like
first; the cross-reference checks then run.

## Versioning

The spec version is `MAJOR.MINOR` (ADR-0008).

- **A minor version is additive.** It may add optional fields and kinds but never changes the meaning of what
  exists. This package reads every older minor of its major natively: no conversion, no flag.
- **A newer minor than this package knows is `E501`**, with the hint to upgrade scireport. The check is on the version
  stamp, not on the content: a bundle stamped `1.1` is refused by a package that reads `1.0`, even if it happens to use
  nothing new. Do not edit the stamp by hand.
- **A major bump ships a migration.** A migration is a pure function from the manifest dict of one major version to
  the next, in `scireport/spec/migrations/`, and `scireport spec migrate` applies the chain. A major older than the
  oldest this package migrates is `E503`.
- A missing or malformed version is `E502`.
- Templates and layouts declare the range they support (`spec: ">=1.0,<2.0"`); a bundle outside it is `E505`.

`scireport spec migrate SRC [--to VERSION] [-o OUT]` reads a `.json` or `.yaml` manifest, never modifies it, and prints
or writes the migrated manifest as JSON. Version 1.0 is the baseline, so today the command returns the manifest
unchanged (re-stamped with the target); it asks for a version this package does not know with `E501`:

```text
$ scireport spec version
1.0
$ scireport spec migrate scireport.json -o migrated.json
$ scireport spec migrate scireport.json --to 2.0
E501 cannot migrate to spec 2.0; this scireport writes 1.0
```

## JSON Schema

The JSON Schema of the data file is generated from the same pydantic models the reader uses, frozen per spec version
and checked for drift by a test: if the models stop generating the frozen file, the test fails, and a released version
can then only change through a new one. The files ship in the package (`scireport/spec/schemas/`) and the documentation
site publishes them under `/schemas/`.

<!-- generated:schema-files -->
| File | Spec version | Status | Required top-level fields | Definitions |
|---|---|---|---|---|
| `data-1.0.schema.json` | 1.0 | current | `scireport`, `meta` | 34 |
<!-- /generated -->

Print the schema of the version this package writes, or save it to a file:

```bash
scireport spec schema
scireport spec schema -o data-1.0.schema.json
```

The schema is a JSON Schema draft 2020-12 document whose `$id` is
`https://nmcardoso.github.io/scireport/schemas/data-1.0.schema.json`. `scireport spec schema` prints exactly the frozen
file. Programs can load it with `scireport.spec.schema.load_frozen_schema()`.

**What it covers.** The schema describes the **canonical manifest**: the `scireport.json` of a packed bundle, in which
the version is exactly `"1.0"`, every value is an envelope with a `kind`, every asset reference has `path`, `sha256`
and `bytes`, and the keys of `values` follow the key grammar. A packed manifest validates against it:

```python
import json
from jsonschema import Draft202012Validator
from scireport.spec.schema import load_frozen_schema

validator = Draft202012Validator(load_frozen_schema('1.0'))
manifest = json.load(open('scireport.json'))
print(list(validator.iter_errors(manifest)))   # [] for a valid canonical manifest
```

**What it does not cover.** The loaders are more lenient than the schema, on purpose: a schema that admitted every
shorthand would accept almost anything and lose its value. So the schema does **not** describe bare-JSON shorthand, or
the asset references without `sha256` and `bytes` (or written as a bare path) that a hand-authored directory may use.
To check such a file against the schema, canonicalise it first with `scireport pack`, or just run `scireport validate`,
which accepts everything the loaders accept and reports problems with codes. The schema also does not express rules
that need more than one field (an exclusive pair such as `text` and `asset`, or the prefix rule of keys); the reader
enforces them.

## See also

- [User guide](guide.md): building a bundle step by step, in Python and by hand.
- [Error codes](errors.md): every error and warning code.
- [Writing a template](templates.md) and [Built-in layouts](layouts.md): what reads the values and how they look.
- [Compatibility policy](compatibility.md): what is promised about this format across versions.
- ADR-0001 (the format), ADR-0002 (keys and kinds), ADR-0005 (validation) and ADR-0008 (compatibility), in
  [Architecture decision records](adr/index.md).
