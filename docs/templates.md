# Writing a template

A **template** says what a report contains and in what order; a **layout** says what it looks like. The data file
holds the values. `scireport render` joins the three (ADR-0003). This page is about the first: how to write a
template of your own. For the look, see {doc}`layout-authoring`; for the built-in looks, {doc}`layouts`.

Most jobs need no template of your own. `generic@1` renders any bundle from its outline. Write one when a report must
have a fixed structure, with its own prose around the numbers, and when you want a missing value to be an error
with a name rather than a hole in the page.

```console
$ scireport templates
generic@1        md,html,tex  builtin    Generic report
kitchen-sink@1   md,html,tex  builtin    Kitchen sink
$ scireport templates ./tpl            # describe one: what it reads
$ scireport render run.scireport.zip -o out -t generic@1 -l minimal@1
```

A template or layout is named `name`, `name@version` or given as a directory path (anything with a `/`, or that
starts with `.` or `~`). A bare name means the newest version here. The built-ins are frozen per version
(ADR-0008): a visual or structural change is a new version directory, never an edit. `scireport pack` writes the
resolved `name@version` into the bundle, so a packed bundle renders the same after newer versions exist.

Other packages add their own through the entry-point groups `scireport.templates` and `scireport.layouts`. The entry
point's name is the template or layout name; it points to a directory (a `pathlib.Path`, a string or a function
returning one) that is either a version directory or a folder of numbered version directories (see
[Share a template](#share-a-template)).

## A first template

We will write a template for a small cross-match report: two counts, a median and a table, and an optional note. The
data comes first, because the template is a promise about it.

A bundle can be a directory with a `scireport.yaml` (or `scireport.json`) manifest, a ZIP or a single file; see
{doc}`spec`. This one is a directory, `bundle/scireport.yaml`:

```yaml
scireport: '1.0'
meta:
  title: Cross-match check
  authors: [N. Cardoso]
  date: '2026-10-09'
  language: en
values:
  stats.n_pairs:
    kind: number
    value: 3061
    format: int
    unit: pairs
  stats.n_sources:
    kind: number
    value: 3520
    format: int
  stats.median_sep:
    kind: number
    value: 0.31
    unit: arcsec
  tables.by_survey:
    kind: table
    caption: Pairs per survey.
    columns:
      - {name: survey, label: Survey}
      - {name: n, label: Pairs}
    rows:
      - [DES, 1804]
      - [SDSS, 1257]
  notes.caveat:
    kind: text
    format: markdown
    text: Sources within **0.5 arcsec** of two catalogue entries are counted once.
```

The same bundle from Python, if the numbers come from an analysis (`Report.write` refuses to replace a bundle unless
`overwrite=True`):

```python
from scireport import Report

report = Report('Cross-match check', authors=['N. Cardoso'], date='2026-10-09')
report.add_number('stats.n_pairs', 3061, format='int', unit='pairs')
report.add_number('stats.n_sources', 3520, format='int')
report.add_number('stats.median_sep', 0.31, unit='arcsec')
report.add_table(
  'tables.by_survey',
  {'survey': ['DES', 'SDSS'], 'n': [1804, 1257]},
  columns=[{'name': 'survey', 'label': 'Survey'}, {'name': 'n', 'label': 'Pairs'}],
  caption='Pairs per survey.',
  inline=True,
)
report.add_text(
  'notes.caveat',
  'Sources within **0.5 arcsec** of two catalogue entries are counted once.',
  format='markdown',
)
report.write('bundle', overwrite=True)
```

The template is a directory, `tpl/`, with two files. First `tpl/template.yaml`:

```yaml
spec: ">=1.0,<2.0"
name: xmatch-qa
version: 1
title: Cross-match check
description: Pair counts of a catalogue cross-match, by survey.
formats: [md, html, tex]
dynamic_keys: true          # the body loops over keys('notes'), which is computed
fields:
  - key: stats.n_pairs
    kind: number
    description: Number of matched pairs.
  - key: stats.n_sources
    kind: number
    description: Number of sources in the input catalogue.
  - key: stats.median_sep
    kind: number
    description: Median separation of the matched pairs.
  - key: tables.by_survey
    kind: table
    description: Pairs per survey.
    columns:
      - {name: survey, dtype: string}
      - {name: n, dtype: int}
  - key: notes.*
    kind: text
    required: false
    description: Free-text caveats, shown under a Notes heading when there are any.
```

And `tpl/report.j2`, the body:

```jinja
{{ c.chapter('Result') }}

{% filter md %}
We matched {{ data.stats.n_pairs.value | fmt_int }} of {{ data.stats.n_sources.value | fmt_int }}
sources ({{ data.stats.n_pairs.value | share(data.stats.n_sources.value) }}).
{% endfilter %}


{{ c.value(data.stats.median_sep, label='Median separation') }}

{{ c.table(data.tables.by_survey) }}

{% if keys('notes') %}
{{ c.heading('Notes', 1) }}

{% for key in keys('notes') %}
{{ c.text(v(key)) }}

{% endfor %}
{% endif %}
```

Check it, then render it. `minimal@1` is the plain layout; `-t ./tpl` and `-f` can be repeated.

```console
$ scireport validate bundle -t ./tpl -l minimal@1
valid: 0 error(s), 0 warning(s)
$ scireport render bundle -t ./tpl -l minimal@1 -o out -f md -f html -f tex
html/report.html
md/report.md
render-manifest.json
tex/latexmkrc
tex/report.tex
tex/scireport-minimal.sty
```

The command prints the files it wrote on standard output and logs on standard error. `out/md/report.md` reads:

```markdown
## Result

We matched 3,061 of 3,520
sources (86.96%).

**Median separation:** 0.31 arcsec

*Table 1. Pairs per survey.*

| Survey | Pairs |
|:---|---:|
| DES | 1804 |
| SDSS | 1257 |

### Notes

Sources within **0.5 arcsec** of two catalogue entries are counted once.
```

(The file also holds a generated-file notice, the title block and a table of contents, which the layout writes around
the body.) In `out/tex/report.tex` the same body is LaTeX: `\section{Result}`, `86.96\%`, a `booktabs` table and
`\subsection{Notes}`. The template did not change; the layout did the work for each format.

### What the template says

- `c.chapter('Result')` starts a chapter and enters it in the table of contents. `c.heading('Notes', 1)` is a heading
  below it.
- `data.stats.n_pairs.value` is the plain number of a `number` value (the unit and the format are on the value too:
  `.unit`, `.format`). The filters `fmt_int` and `share` turn it into text for prose.
- `c.value(data.stats.median_sep, label=...)` draws a value with the component for its kind. A number becomes a labelled
  line with its unit; `c.table(...)` draws a table; `c.text(...)` draws prose.
- `keys('notes')` lists the keys under a prefix, so the section appears only when the bundle has notes. This is why
  `notes.*` is optional in `template.yaml` and why the file says `dynamic_keys: true`.

## The fields: what the template promises

`fields` in `template.yaml` is the **contract** between the template and the bundle. Validation reads it before
anything is rendered, so a bundle that does not keep the promise fails with a message that names the field, instead of
failing half-way through a render.

```yaml
fields:
  - key: stats.n_pairs
    kind: number
    description: Number of matched pairs.
  - key: tables.summary
    kind: table
    columns:
      - {name: survey, dtype: string}
      - {name: n, dtype: int}
      - {name: note, dtype: string, required: false}
  - key: figures.*           # * is one key segment, ** is one or more
    kind: figure
    required: false
    renditions: [png, pdf]
```

| Field | Meaning |
|---|---|
| `key` | a value key, or a pattern: `*` is one key segment, `**` is one or more (`qa.*.summary`) |
| `kind` | one kind, or a list of the kinds it accepts: `text`, `number`, `bool`, `date`, `list`, `mapping`, `table`, `figure`, `image`, `math`, `code`, `metrics`, `status`, `alert`, `flow`, `attachment`, `bibliography` |
| `required` | default `true`: the bundle must have at least one value that matches |
| `description` | what the template uses it for; it appears in `scireport templates` and in error hints |
| `columns` | for a table: `name`, `dtype` and `required` of each column the table must have |
| `renditions` | for a figure: the file formats (`png`, `pdf`, `svg`) it must carry |

`dtype` is one of `any`, `int`, `float`, `number` (int or float), `string`, `bool`, `date`, `timestamp`. A bundle's
column has a name, a label, a unit and a format but no type: the type is read from the data, and `dtype` belongs to
the template only.

The top of `template.yaml` has the other keys:

| Key | Meaning |
|---|---|
| `spec` | the data-file spec versions it works with (`">=1.0,<2.0"`); another version is `E505` |
| `name`, `version` | the name and the integer version; a structural change is a new version |
| `title`, `description` | one line each, shown in listings |
| `formats` | the output formats it supports (`md`, `html`, `tex`); asking for another is `E706` |
| `entry` | the body file, `report.j2` by default |
| `dynamic_keys` | `true` when the body computes keys (`keys(...)`, `v('qa.' ~ name)`); it silences `W403` |

Two uses of `fields` beyond validation. `scireport templates ./tpl` prints what a template reads, and `scireport new`
writes a starter data file with a placeholder for every required field, which validates at once:

```console
$ scireport templates ./tpl
xmatch-qa@1: Cross-match check
formats: md, html, tex   spec: >=1.0,<2.0
  stats.n_pairs                number     required
    Number of matched pairs.
  stats.n_sources              number     required
    Number of sources in the input catalogue.
  stats.median_sep             number     required
    Median separation of the matched pairs.
  tables.by_survey             table      required
    Pairs per survey.
  notes.*                      text       optional
    Free-text caveats, shown under a Notes heading when there are any.
$ scireport new starter --template ./tpl
starter/scireport.yaml
$ scireport validate starter -t ./tpl -l minimal@1
valid: 0 error(s), 0 warning(s)
```

`scireport templates ./tpl --json` prints the same as data, for agents.

### Declared, read and rendered are three different things

It is easy to expect more from `fields` than it does, so here is what each check really looks at:

- A **required field the bundle lacks** is `E105`; a value of another kind than declared is `E207`; a table without a
  declared column is `E303` (or `E304` for a column of the wrong type); a figure without a declared rendition is `E210`.
  These check the bundle against `fields`.
- A key the template **reads** (`data.a.b`, `v('a.b')`) that the bundle does not have is `E106`, whether or not `fields`
  declares it. Declaring a key does not make reading it safe, and reading a key that exists but is not declared is not
  an error: it only means `scireport templates` does not tell the whole story. Declare everything you read.
- A value in the bundle that the template **never renders** is warning `W401` (an error with `--strict`). Pass it to a
  component, even `c.references(data.refs)` for a bibliography.

A guard does not help against `E106`. The lint reads the syntax tree and cannot know that you tested first, so
`{% if has('notes.caveat') %}`, `{% if peek('notes.caveat') %}` and `{% if data.notes.caveat %}` all report `E106` when
the bundle has no `notes.caveat`. A key read literally is therefore a required key. Optional content goes through
`keys('prefix')` and `v(key)`, with `dynamic_keys: true`, as the example does.

## What a template can use

| Name | Meaning |
|---|---|
| `data.a.b` | the value with key `a.b`; reading it marks it as used |
| `v('a.b')` | the same by string; with a computed key (`v('qa.' ~ name)`) it warns `W403` unless `dynamic_keys: true` |
| `has('a.b')` | whether the bundle has that key (a literal key is still checked: see above) |
| `peek('a.b')` | the value, or `None`, without marking it as used |
| `keys('a')` | the sorted keys under a prefix; `keys()` lists them all |
| `meta`, `options`, `outline`, `info` | the manifest's `meta`, the resolved layout options, the effective outline, and facts about the render (`info.layout`, `info.format`, ...) |
| `c.*` | the components, below |
| `md(text)`, `text \| md` | convert a Markdown string to the current format |

The values a template reads are bundle values, not plain Python objects: `data.stats.n_pairs.value` is the number and
`data.stats.median_sep.unit` its unit. A key that is a prefix (`data.stats`) gives a namespace; pass it to a component
and you get `E208`, because it holds several values.

Jinja control flow works as usual (`if`, `for`, `set`, `macro`, `{% do %}` and `{% break %}`/`{% continue %}`). Files
in the template directory can be shared with `{% from 'macros.j2' import shout %}` or `{% include %}`; the lint follows
them. Blocks swallow the newline that follows them (`trim_blocks`), which matters for [prose](#prose-and-markdown).

## Components

**Components** turn a value into output for the current format. They are the way to put anything on the page, and a
template that uses only components works in every format, because each layout draws each component in Markdown, HTML
and LaTeX. `c.value(x)` picks the component from the value's kind. A component takes a value (`data.a.b` or
`v('a.b')`) and, where the signature says `ref`, also a key string.

| Kind of value | Component |
|---|---|
| `text` | `c.text` |
| `number` | `c.number` (inline), or a labelled line through `c.value(x, label=...)` |
| `bool`, `date` | a labelled line through `c.value(x, label=...)` |
| `list`, `mapping` | `c.bullets`, `c.metadata` |
| `table` | `c.table` (`caption=`, `max_rows=`) |
| `figure`, `image` | `c.figure`, `c.image` (`caption=`, `width=` as a fraction of the page width) |
| `math` | `c.equation` (display), `c.math('x^2')` for an inline expression |
| `code` | `c.code` |
| `metrics`, `status`, `alert`, `flow` | `c.metrics`, `c.status`, `c.alert`, `c.flow` |
| `attachment` | `c.attachment` |
| `bibliography` | `c.references` |

A component given a value of the wrong kind is `E208`. Structure comes from `c.chapter`, `c.heading`, `c.contents`,
`c.cover`, `c.page_break` and `c.spacer`; `c.details` and `c.note` wrap content and are used as call blocks:

```jinja
{% call c.details('Method') %}
{{ 'Positions are matched within **0.5 arcsec**.' | md }}
{% endcall %}
```

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

A layout that lacks the macro for a component is `E707` ({doc}`layout-authoring`).

## Filters

Filters format numbers inside prose. They come from the MOSAICS report engine, with the `fmt_` prefix kept on two of
them because `int` and `float` are Jinja built-ins. `{{ x | missing or (x | fmt_int) }}` shows a placeholder when `x`
has no number; the components use that gate themselves. `slug` and `breakable` are for identifiers and long paths.

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

In a LaTeX file (see below) there are two more: `pdfstring`, for text that goes into a PDF string such as a bookmark,
and a `breakable` that escapes for TeX.

## Prose and Markdown

Prose is Markdown. Write it inside `{% filter md %}...{% endfilter %}`, or pass a string through `| md`, and the
converter turns it into the current format: bold, lists, links and `$math$` work in all three. The subset it reads, and
what is shown as plain text with `W701`, is in {doc}`markup`. Headings (`#`) and images (`![](...)`) are outside the
subset: use `c.chapter`, `c.heading` and `c.figure`, so that the table of contents and the numbering stay right and
every asset is checked.

Three things that are easy to miss:

- **Leave two blank lines after `{% endfilter %}`**, as the example does. The block tag swallows its own newline, so
  with one blank line the next component starts on the line right after the paragraph and glues to it (a table
  caption, in the example). Runs of blank lines are collapsed in the output, so extra ones cost nothing.
- **Write numbers into prose with filters, not with `c.number`.** `c.number` returns text already typeset for the
  format, which in LaTeX is raw TeX (`0.31~arcsec`); inside `{% filter md %}` that text is converted a second time and
  the tie shows up as `\textasciitilde{}`. `{{ data.stats.n_pairs.value | fmt_int }}` is plain text and safe. Use
  `c.number` and `c.value` on a line of their own.
- **Output is escaped for its format automatically** (HTML autoescape; the LaTeX special characters
  `# $ % & ~ _ ^ \ { }` and Unicode; Markdown markup characters). Text a component returns is never escaped twice, so
  do not escape by hand.

## Per-format bodies and LaTeX delimiters

`report.j2` is the format-neutral body. Next to it, `report.md.j2`, `report.html.j2` and `report.tex.j2` are optional
bodies for one format; when one exists it is used for that format instead of `report.j2`. You need one when a format
must differ in structure, for example a LaTeX-only appendix that uses a `\clearpage`.

A `.md.j2` or `.html.j2` file uses the same `{{ }}` and `{% %}` as `report.j2`. A `.tex.j2` file cannot: `{{` and `{%`
collide with TeX braces and `%` comments, so LaTeX files use other delimiters:

| Jinja | In a `.tex.j2` file |
|---|---|
| `{% if x %}` ... `{% endif %}` | `((* if x *))` ... `((* endif *))` |
| `{{ value }}` | `((( value )))` |
| `{# comment #}` | `((= comment =))` |

Here is the body of the example as `tpl/report.tex.j2`. It validates and renders, and it prints the same numbers
and table:

```text
((( c.chapter('Result') )))

We matched \textbf{(((data.stats.n_pairs.value | fmt_int)))} of (((data.stats.n_sources.value | fmt_int))) sources.

((( c.value(data.stats.median_sep, label='Median separation') )))

((( c.table(data.tables.by_survey) )))
((* for key in keys('notes') *))
((( c.text(v(key)) )))
((* endfor *))
```

Text printed with `(((...)))` is escaped for LaTeX, so a `%` in a value is safe; raw TeX goes in the file itself.
Mind that `(((` is a delimiter: a literal opening parenthesis next to it needs a variable (the minimal layout defines
`((* set lp = '(' *))` for this).

Which body a format uses decides which Jinja syntax the lint reads: all bodies are linted, and a key read in the
LaTeX one but missing in the bundle is `E106` too.

## Citations and the reference list

A bundle with a `bibliography` value (`Report.add_bibliography`) lets prose cite with `[@key]`. A template draws the
list with `c.references(data.refs)`; put a heading before it. Only cited works are listed, unless you pass
`everything=True`. LaTeX output uses `biblatex` and `biber`; Markdown and HTML are formatted by pandoc
(`scireport[pandoc]`, see {doc}`pandoc`). The bundle for this example is built with
`report.add_bibliography('refs', 'refs.bib')` and a text value `intro` with the citation `[@budavari2008]`:

```jinja
{{ c.chapter('Introduction') }}

{{ c.text(data.intro) }}

{{ c.heading('References', 1) }}

{{ c.references(data.refs) }}
```

With `-f tex` the citation becomes `\autocite{budavari2008}`, the writer adds `\usepackage[backend=biber]{biblatex}` and
`\addbibresource{references.bib}` to the preamble, and `\printbibliography` draws the list; with `-f md` the citation
is replaced by `(Budavári and Szalay 2008)` and the list is the formatted entry. `c.references()` on a bundle with no
bibliography is `E208`.

## The sandbox

Templates run in a Jinja `SandboxedEnvironment` with `StrictUndefined` (ADR-0003, golden rule 3). Two consequences:

- **A name that does not exist is an error, not an empty string** (`E803`): `{{ nothing_here }}` stops the render with
  the file and line. This also catches typos in attribute names (`data.stats.n_pairs.valeu`).
- **A template cannot reach Python internals** (`E802`): `{{ ''.__class__.__mro__ }}` is refused. There is no
  `import` of Python modules; `{% import %}` and `{% include %}` load files from the template directory only.

A template also cannot read files or the clock: everything it can show comes from the bundle, the options and `meta`.
That is what keeps the output deterministic: the same inputs and versions give byte-identical `.md`, `.html` and
`.tex`.

## Checking a template

`scireport validate` checks a bundle against a template and a layout without writing anything. It reports every
problem at once (see {doc}`errors`), each with a stable code, the key, the JSON pointer, the template `file:line` and a
"did you mean" suggestion where it has one. For a bundle with a missing source count and a renamed column:

```console
$ scireport validate bad -t ./tpl -l minimal@1
E106 report.j2:4: /values: the template reads key 'stats.n_sources', which the bundle does not have. Did you mean 'stats.n_pairs'?
E106 report.j2:5: /values: the template reads key 'stats.n_sources', which the bundle does not have. Did you mean 'stats.n_pairs'?
E105 template.yaml fields[1]: /values: the template needs a number value at 'stats.n_sources' (Number of sources in the input catalogue.) (expected number at stats.n_sources, found None). Did you mean 'stats.n_pairs'?
E303 template.yaml fields[3]: /values/tables.by_survey: table 'tables.by_survey' lacks the column 'n' (expected n, found survey, count)
invalid: 4 error(s), 0 warning(s)
```

Two checks run together. A **lint** of the Jinja syntax tree finds the keys a template reads (and keys it computes,
`W403`). A **render** in memory records which values were really used, so that `W401` and errors that only a render
shows (`E803`, `E208`) are found too. `--no-render` skips the second. `--strict` turns warnings into errors and
`--json` prints the report for agents. Exit codes: 0 valid, 2 invalid.

The codes you will meet while writing a template:

| Code | When |
|---|---|
| `E105` | a required field of `fields` has no value in the bundle |
| `E106` | the template reads a key the bundle does not have (literal reads, even when guarded) |
| `E207` | a value has another kind than the field declares |
| `E208` | a component was given a value it cannot draw (a number to `c.table`, a prefix to anything) |
| `E210` | a figure lacks a rendition the field asks for |
| `E303`, `E304` | a table lacks a declared column, or the column has another type |
| `E505` | the template's `spec` range does not include the bundle's spec version |
| `E702` | `template.yaml` is invalid (an unknown `kind`, a bad key pattern, ...) |
| `E703` | a file the template names, or imports, is missing |
| `E704` | Jinja syntax error, with `file:line` |
| `E706` | the template does not support a requested format |
| `E802`, `E803`, `E804` | the sandbox refused something; a name does not exist; a component or filter failed |
| `W401` | a value of the bundle is never rendered |
| `W403` | a key is computed at render time (silenced by `dynamic_keys: true`) |
| `W701` | Markdown outside the supported subset was shown as plain text |

`E804` also reports a layout macro that was called with arguments it does not take; see {doc}`layout-authoring`.

## Share a template

A template that only one project uses can live in the repository and be named by path (`-t ./templates/qa`). Put the
files in a numbered folder when there will be a second version: `templates/qa/1/template.yaml`, later
`templates/qa/2/`. A path to the folder `qa` resolves to its highest number; a path to `qa/1` pins one.
A path is a command-line choice: `render.template` in a data file takes a `name` or a `name@version` (a path there is
`E205`), so a bundle can name only a built-in template or a plugin.

A package can ship templates and layouts through the entry-point groups `scireport.templates` and
`scireport.layouts` (`scireport/render/registry.py` resolves them). The entry point's name is the template or layout
name. After installing the package, `scireport templates` lists the template with the origin `entry-point:<name>`:

```toml
# pyproject.toml of the plugin
[project.entry-points."scireport.templates"]
xmatch-qa = "labnotes:TEMPLATES"
```

```python
# labnotes/__init__.py
from pathlib import Path

TEMPLATES = Path(__file__).parent / 'templates'   # templates/1/template.yaml, templates/1/report.j2
```

```console
$ scireport templates
generic@1        md,html,tex  builtin    Generic report
kitchen-sink@1   md,html,tex  builtin    Kitchen sink
xmatch-qa@1      md,html,tex  entry-point:xmatch-qa Cross-match check
```

A built-in name always wins over a plugin with the same name, and a plugin that fails to load is `E705`.

## Reference

The templates installed here:

<!-- generated:templates -->
| Template | Formats | Origin | Title |
|---|---|---|---|
| `generic@1` | md, html, tex | builtin | Generic report |
| `kitchen-sink@1` | md, html, tex | builtin | Kitchen sink |
<!-- /generated -->

Everything a template may call is in {doc}`api` (the Python side) and {doc}`cli` (the commands); the layouts that draw
the components are in {doc}`layouts`.
