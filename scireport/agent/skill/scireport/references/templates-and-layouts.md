# Templates and layouts

A **template** says what a report contains and in what order; a **layout** says what it looks like; the
data file holds the values. `render` joins the three. Most jobs need neither a new template nor a new
layout: `generic@1` renders any bundle from its `outline`, and `default@1` is the standard look. Write
your own only when the structure (a template) or the look (a layout) must differ.

Name one as `name` (the newest version), `name@version`, or a directory path (anything with a `/` or
starting with `.` or `~`): `-t generic@1 -l modern@1`, `-t ./templates/qa`.

## Built-in templates

Both support md, html and tex.

- `generic@1`: writes the cover, then every outline entry in order (a chapter for each top-level entry, a
  heading for each nested one, the right component for each value). It declares no `fields`.
- `kitchen-sink@1`: every component once, plus hard cases (long headings, a 250-row table). It needs a
  bundle with the keys it reads; it is for testing a layout. `scireport new DIR --template kitchen-sink@1`
  writes a starter with placeholders.

## Installed templates

<!-- generated:templates -->
| Template | Formats | Origin | Title |
|---|---|---|---|
| `generic@1` | md, html, tex | builtin | Generic report |
| `kitchen-sink@1` | md, html, tex | builtin | Kitchen sink |
<!-- /generated -->

## Built-in layouts

- `default@1`: the MOSAICS look: navy cover, chapter openers, table of contents with page numbers, running
  header and footer. The default layout.
- `modern@1`: white page, vermilion cover band, giant chapter numerals, heavy rules, rule-only tables.
- `minimal@1`: no design: plain Markdown, HTML and LaTeX. No PDF engine (`E903` if you ask for a PDF).
  Use it for tests and for language models.

Options are set with `-O name=value`, in the bundle's `render.options`, or in Python; see `cli.md`.

<!-- generated:layouts -->
### `default@1`

Default (MOSAICS look). Navy cover, chapter openers, a table of contents with page numbers, a running header and footer. Inter and IBM Plex Mono.

Formats: md, html, tex. PDF engines: weasyprint, latex.

| Option | Type | Default | Choices | Meaning |
|---|---|---|---|---|
| `toc` | bool | `True` |  | Write a table of contents. |
| `cover` | bool | `True` |  | Start with the navy cover page (otherwise a plain title block). |
| `paper` | str | `a4` | a4\|letter | Paper size of the PDF and of the LaTeX project. |
| `chapter_breaks` | bool | `True` |  | Start every chapter on a new page, below an opener band. |
| `numbered_captions` | bool | `True` |  | Prefix captions with "Table N." and "Figure N.". |
| `header` | bool | `True` |  | Print the running header and footer on the pages of a PDF. |

### `minimal@1`

Minimal. Plain reference layout for Markdown, self-contained HTML and a LaTeX project.

Formats: md, html, tex. PDF engines: .

| Option | Type | Default | Choices | Meaning |
|---|---|---|---|---|
| `toc` | bool | `True` |  | Write a table of contents. |
| `cover` | bool | `True` |  | Write the title block (subtitle, authors, date, version) under the title. |
| `accent` | str | `#1f4e79` |  | Accent colour as |
| `paper` | str | `a4` | a4\|letter | Paper size of the LaTeX project. |
| `numbered_captions` | bool | `True` |  | Prefix captions with "Table N." and "Figure N.". |

### `modern@1`

Modern (Signal). A white page with a vermilion cover band, giant chapter numerals, heavy rules and rule-only tables. Inter and IBM Plex Mono.

Formats: md, html, tex. PDF engines: weasyprint, latex.

| Option | Type | Default | Choices | Meaning |
|---|---|---|---|---|
| `toc` | bool | `True` |  | Write a table of contents. |
| `cover` | bool | `True` |  | Start with the cover page (otherwise a plain title block). |
| `paper` | str | `a4` | a4\|letter | Paper size of the PDF and of the LaTeX project. |
| `chapter_breaks` | bool | `True` |  | Start every chapter on a new page. |
| `numbered_captions` | bool | `True` |  | Prefix captions with "Table N." and "Figure N.". |
| `header` | bool | `True` |  | Print the running header and footer on the pages of a PDF. |
<!-- /generated -->

## Components and filters

A template turns values into output with components, `c.<name>(...)`. Each draws one kind of value in the
current format (Markdown, HTML or LaTeX), so the same template serves every format. `c.value(v('key'))`
picks the component from the value's kind. Components take a value (`data.a.b` or `v('a.b')`), not a key
string, except where the signature says `ref` (it accepts both).

<!-- generated:components -->
| Component | Signature | What it does |
|---|---|---|
| `c.alert` | `(ref: 'Any') -> 'Safe'` | Draw an `alert` value: a one-line call-out. |
| `c.attachment` | `(ref: 'Any') -> 'Safe'` | Offer an `attachment` value as a link. |
| `c.bullets` | `(ref: 'Any') -> 'Safe'` | Draw a `list` value as a bullet or numbered list. |
| `c.chapter` | `(title: 'str', *, md_file: 'str \| None' = None, page_break: 'bool \| None' = None, in_contents: 'bool' = True) -> 'Safe'` | Start a chapter: the top level of the table of contents. |
| `c.code` | `(ref: 'Any') -> 'Safe'` | Draw a `code` value: source code or preformatted text. |
| `c.contents` | `() -> 'Safe'` | Write the table of contents from the headings rendered so far. |
| `c.cover` | `() -> 'Safe'` | Write the cover from the `meta` block of the bundle. |
| `c.details` | `(summary: 'str', caller: 'Callable[[], str]') -> 'Safe'` | Wrap content in a collapsible block (a call block: `{% call c.details('Title') %}`). |
| `c.equation` | `(ref: 'Any') -> 'Safe'` | Draw a `math` value. |
| `c.figure` | `(ref: 'Any', *, caption: 'str \| None' = None, width: 'float \| None' = None) -> 'Safe'` | Draw a `figure` value, choosing the best rendition for the format. |
| `c.flow` | `(ref: 'Any') -> 'Safe'` | Draw a `flow` value: a pipeline as numbered stages. |
| `c.heading` | `(text: 'str', level: 'int' = 1, *, page_break: 'bool \| None' = None, in_contents: 'bool' = True) -> 'Safe'` | Write a heading below the current chapter. |
| `c.image` | `(ref: 'Any', *, caption: 'str \| None' = None, width: 'float \| None' = None) -> 'Safe'` | Draw an `image` value (a logo, a photograph). |
| `c.math` | `(latex: 'str') -> 'Safe'` | Typeset an inline expression: `$...$` in TeX and Markdown, an image in HTML. |
| `c.metadata` | `(ref: 'Any') -> 'Safe'` | Draw a `mapping` value: labelled entries in a fixed order. |
| `c.metrics` | `(ref: 'Any') -> 'Safe'` | Draw a `metrics` value: a grid of headline numbers. |
| `c.note` | `(caller: 'Callable[[], str]') -> 'Safe'` | Write a muted remark (a call block: `{% call c.note() %}`). |
| `c.number` | `(ref: 'Any') -> 'Safe'` | Typeset a `number` value inline, with its unit and uncertainty. |
| `c.page_break` | `() -> 'Safe'` | Start a new page (PDF, LaTeX); no effect in Markdown. |
| `c.references` | `(ref: 'Any' = None, *, everything: 'bool' = False) -> 'Safe'` | Write the reference list of the bundle's bibliography. |
| `c.spacer` | `(height: 'float' = 8.0) -> 'Safe'` | Leave vertical space. |
| `c.status` | `(ref: 'Any') -> 'Safe'` | Draw a `status` value: the overall verdict banner. |
| `c.table` | `(ref: 'Any', *, caption: 'str \| None' = None, max_rows: 'int \| None' = None) -> 'Safe'` | Draw a `table` value. |
| `c.text` | `(ref: 'Any') -> 'Safe'` | Draw a `text` value: Markdown, plain paragraphs or raw LaTeX. |
| `c.value` | `(ref: 'Any', *, label: 'str \| None' = None) -> 'Safe'` | Draw any value with the component for its kind. |
<!-- /generated -->

Filters format numbers inside prose. The `fmt_` prefix exists because `int` and `float` are Jinja
built-ins. `{{ x | missing or (x | fmt_int) }}` shows a placeholder when `x` has no number. `{% filter md %}
...{% endfilter %}` converts a block of Markdown prose to the current format.

<!-- generated:filters -->
| Filter | Signature | What it does |
|---|---|---|
| `fmt_int` | `(value: 'Any') -> 'str'` | Format a count with thousands separators. |
| `fmt_float` | `(value: 'Any', digits: 'int' = 4) -> 'str'` | Format a statistic to a number of significant figures. |
| `share` | `(part: 'Any', whole: 'Any') -> 'str'` | Format one number as a percentage of another. |
| `fmt_bytes` | `(value: 'Any') -> 'str'` | Format a byte count in the largest binary unit that keeps it readable. |
| `duration` | `(value: 'Any') -> 'str'` | Format seconds as `<h>h<m>m<s>s`, leaving out zero parts. |
| `pct` | `(value: 'Any', digits: 'int' = 2) -> 'str'` | Format a ratio that is already computed as a percentage. |
| `ppm` | `(value: 'Any') -> 'str'` | Format a parts-per-million value with thousands separators. |
| `sci` | `(value: 'Any', digits: 'int' = 3) -> 'Scientific \| str'` | Format a number in scientific notation. |
| `compact` | `(value: 'Any', digits: 'int' = 1) -> 'str'` | Abbreviate a large count with a magnitude suffix. |
| `missing` | `(value: 'Any') -> 'str \| None'` | Return the placeholder for a value that has no number, or None when it has one. |
| `breakable` | `(text: 'Any') -> 'str'` | Insert a zero-width space after every path separator so that long paths can wrap. |
| `slug` | `(text: 'Any') -> 'str'` | Turn text into a lowercase, hyphen-separated identifier. |
<!-- /generated -->

## Describe, then build the bundle

`scireport templates NAME --json` lists what a template reads: one object per key or key pattern (`*` is
one key segment, `**` one or more) with `kinds`, `required`, `description`, `columns` (name, `dtype`,
`required`) for tables and `renditions` for figures. Build the bundle to match, then `validate`.

```console
$ scireport templates ./tpl/pairs
pairs@1: Pair counts
formats: md, html, tex   spec: >=1.0,<2.0
  stats.n_pairs                number     required
    Number of matched pairs.
  tables.by_survey             table      required
  extras.*                     text       optional
```

`scireport new DEST --template ./tpl/pairs` writes a starter data file with a placeholder for every
required field, so it validates at once (values that need a file, such as figures, are listed for you to add).

## Write a template

A template is a directory with two files:

| File | Content |
|---|---|
| `template.yaml` | `spec` range, `name`, `version`, `title`, `formats`, `fields` (the contract), `dynamic_keys` |
| `report.j2` | the format-neutral body: Markdown prose and Jinja control flow around `c.*` calls |
| `report.md.j2`, `report.html.j2`, `report.tex.j2` | optional body for one format, replacing `report.j2` there |

Start from `scireport/templates/generic/1/` (installed with the package; find it with
`python -c "import scireport, pathlib; print(pathlib.Path(scireport.__file__).parent / 'templates')"`) and
read `docs/templates.md` and `docs/layouts.md` in the repository for the full contract. A minimal template
that reads one number, one table and any optional `extras.*` text (this validates and renders):

```yaml
# pairs/template.yaml
spec: ">=1.0,<2.0"
name: pairs
version: 1
title: Pair counts
formats: [md, html, tex]
dynamic_keys: true          # the body loops over keys('extras'), which is computed
fields:
  - key: stats.n_pairs
    kind: number
    description: Number of matched pairs.
  - key: tables.by_survey
    kind: table
    columns:
      - {name: survey, dtype: string}
      - {name: n, dtype: int}
  - key: extras.*
    kind: text
    required: false
```

```jinja
{# pairs/report.j2 #}
{{ c.chapter('Pairs') }}

We matched {{ c.number(data.stats.n_pairs) }} pairs.

{{ c.table(data.tables.by_survey, caption='Pairs per survey.') }}

{% for key in keys('extras') %}
{{ c.value(v(key)) }}

{% endfor %}
```

```console
$ scireport validate bundle -t ./pairs -l minimal@1
valid: 0 error(s), 0 warning(s)
$ scireport render bundle -t ./pairs -l minimal@1 -o out -f md
```

`dtype` is `any`, `int`, `float`, `number` (int or float), `string`, `bool`, `date` or `timestamp`.
A bundle's column has `name`, `label`, `unit`, `format`, `align`, `width`, `description` and no type: the
type is read from the data, and `dtype` belongs to the template only (see `data-file.md`).

### What a template can use

Templates run in a Jinja `SandboxedEnvironment` with `StrictUndefined`: no access to Python internals,
no imports, and a name that does not exist is an error (`E803`), not an empty string.

| Name | Meaning |
|---|---|
| `data.a.b` | the value with key `a.b`; reading it marks it as used |
| `v('a.b')` | the same by string; with a computed key (`v('qa.' ~ name)`) it warns `W403` unless `dynamic_keys: true` |
| `has('a.b')` | whether the bundle has that key |
| `peek('a.b')` | the value, or `None`, without marking it as used |
| `keys('a')` | the sorted keys under a prefix |
| `meta`, `options`, `outline` | the manifest's `meta`, the resolved layout options, the effective outline |
| `c.<component>` | the components above |

The checks that matter when you write one:

- Every key read **literally** (`data.x.y`, `v('x.y')`, even inside `has('x.y')`) must exist in the bundle
  (`E106`); the lint cannot see that you guard it. A key a template reads literally is therefore required.
  Optional content goes through `keys('prefix')` and `v(key)` with `dynamic_keys: true`.
- A `required: true` field the bundle lacks is `E105`; a value of another kind than declared is `E207`; a
  missing table column is `E303`.
- A value the template never renders is warning `W401` (`--strict` makes it an error). Pass it to a
  component, even `c.references(data.refs)` for a bibliography.
- Use `c.chapter`, `c.heading` and `c.figure` for headings, images and figures. Raw `#` headings and
  `![..](..)` inside Markdown prose are not supported (`W701`).

### Per-format bodies and LaTeX delimiters

`report.tex.j2` and every `.tex.j2` file of a layout use LaTeX-safe Jinja delimiters, because `{{ }}`
and `{% %}` collide with TeX braces: `((* if x *))` for blocks, `((( value )))` for expressions and
`((= comment =))`. `report.j2`, `.md.j2` and `.html.j2` use the normal `{{ }}` and `{% %}`. Text printed
from a value is escaped for the format automatically (never escape twice).

## Citations and the reference list

A bundle with a `bibliography` value (`Report.add_bibliography`) lets prose cite with `[@key]`. A template
draws the list with `c.references(data.refs)` (put a heading before it; `everything=True` lists uncited works
too). LaTeX uses `biblatex` and `biber`; Markdown and HTML are formatted by pandoc (`scireport[pandoc]`).

```jinja
{{ c.chapter('Introduction') }}

{{ c.text(data.intro) }}

{{ c.heading('References', 1) }}

{{ c.references(data.refs) }}
```

With no bibliography value `c.references()` is `E208`.

## Write a layout

A layout is a directory with `layout.yaml` and, per format, a document skeleton and a components file.
Copy `scireport/layouts/minimal/1/`, rename it in `layout.yaml`, and edit; read `docs/layouts.md`.

```yaml
spec: ">=1.0,<2.0"
name: mine
version: 1
formats:
  md:   {document: md/document.md.j2,     components: md/components.md.j2}
  html: {document: html/document.html.j2, components: html/components.html.j2, css: [html/minimal.css]}
  tex:  {document: latex/document.tex.j2, components: latex/components.tex.j2,
         style: latex/scireport-minimal.sty}
options:
  - {name: paper, type: str, default: a4, choices: [a4, letter]}
```

- `document` wraps the body (`((( body )))` in LaTeX files); `components` holds one Jinja macro per component.
  A components file must define every component for every format the layout lists, or the render fails with
  `E707`. The macro names are `chapter heading contents cover table figure image equation metrics status alert
  flow metadata bullets code details note paragraph fact attachment spacer page_break`.
- `options` are typed (`bool`, `str`, `int`, `float`) with a `default`, optional `choices` or `pattern`; the
  macros read them as `options.name`.
- Optional keys: `pdf_engines` (`weasyprint`, `latex`), `fonts` (vendored font files), `palette` and
  `mplstyle` (the colours and matplotlib style that figures use, see `mplstyle.md`) and `reference_docx`
  (a Word file, relative to the layout, whose styles pandoc uses for `docx` and `odt`).

```console
$ scireport layouts ./lay/mine
mine@1: Minimal
formats: md, html, tex   pdf engines:
  toc                  bool  = True
  ...
$ scireport render bundle -l ./lay/mine -o out -f md
```

## Versions are frozen

`generic@1`, `kitchen-sink@1`, `default@1`, `modern@1` and `minimal@1` never change. A visual or structural
change is a new version directory (`.../2/`), never an edit of `.../1/`. `scireport pack` writes the
resolved `name@version` into the bundle, so a packed bundle renders the same after newer versions exist. Do
the same for your own: copy `1/` to `2/` and edit the copy.

## Plugins

A package can ship templates and layouts through the entry-point groups `scireport.templates` and
`scireport.layouts` (`scireport/render/registry.py` resolves them). The entry point's name is the template
or layout name; it points to a `pathlib.Path` or a function returning one, which is a version directory or
a folder of numbered version directories.

```toml
# pyproject.toml of the plugin
[project.entry-points."scireport.templates"]
pairs = "myreports:TEMPLATES"      # TEMPLATES = Path(__file__).parent / "tpl"   (tpl/1/template.yaml)
```

After installing it, `scireport templates` lists `pairs@1  ... entry-point:pairs`. A plugin that fails to load
is `E705`. A built-in name always wins over a plugin with the same name.
