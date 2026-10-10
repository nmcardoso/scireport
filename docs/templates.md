# Templates and layouts

A **template** says what a report contains and in what order; a **layout** says what it looks like. The
data file holds the values. `scireport render` joins the three (ADR-0003).

```console
$ scireport templates          # name@version, formats, origin, title
$ scireport layouts --json
$ scireport render run.scireport.zip -o out -t generic@1 -l minimal@1
```

A template or layout is named `name`, `name@version` or given as a directory path. A bare name means the
newest version here. The built-ins are frozen per version (ADR-0008): a visual or structural change is a new
version directory, never an edit. `scireport pack` writes the resolved `name@version` into the bundle, so a
packed bundle renders the same after newer versions exist.

Other packages add their own through the entry-point groups `scireport.templates` and `scireport.layouts`.
The entry point's name is the template or layout name; it points to a directory (a `pathlib.Path`, a string
or a function returning one) that is either a version directory or a folder of numbered version directories.

## Template model

A template is a directory with two files, plus optional overrides.

| File | Content |
|---|---|
| `template.yaml` | name, version, supported spec range, formats, and the `fields` it reads |
| `report.j2` | the format-neutral body (Markdown prose, Jinja control flow) |
| `report.md.j2`, `report.html.j2`, `report.tex.j2` | optional body for one format (LaTeX files use `((* *))`, `((( )))`, `((= =))`) |

```yaml
spec: ">=1.0,<2.0"        # data-file spec versions it works with
name: dataset-qa
version: 1
formats: [md, html, tex]
dynamic_keys: false        # true when it walks the outline or loops over keys(...)
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

`dtype` is one of `any`, `int`, `float`, `number` (int or float), `string`, `bool`, `date`, `timestamp`.
`generic@1` renders any bundle from its outline: a chapter for each top-level entry, a heading for each nested
one and the matching component for each value. With no outline the values are grouped by the first segment of
their keys.

## Layout model

`layout.yaml` names the files for each format, and declares typed **options** with defaults.

```yaml
spec: ">=1.0,<2.0"
name: minimal
version: 1
formats:
  md:   {document: md/document.md.j2,   components: md/components.md.j2}
  html: {document: html/document.html.j2, components: html/components.html.j2, css: [html/minimal.css]}
  tex:  {document: latex/document.tex.j2, components: latex/components.tex.j2, style: latex/scireport-minimal.sty}
options:
  - {name: paper, type: str, default: a4, choices: [a4, letter]}
```

Option values come from, in increasing priority, the layout defaults, the bundle's `render.options` and
`-O name=value` on the command line. An unknown name or a value outside `choices` or `pattern` is `E806`.
`minimal@1` is the plain reference layout of the engine; the designed layouts arrive in phase S3.

## What a template can use

Templates run in a Jinja `SandboxedEnvironment` with `StrictUndefined` (ADR-0003, golden rule 3): no access to
Python internals, no imports, and a name that does not exist is an error (`E803`), not an empty string.

| Name | Meaning |
|---|---|
| `data.a.b` | the value with key `a.b`; reading it marks it as used |
| `v('a.b')` | the same by string, for computed keys (warns `W403`: it cannot be checked in advance) |
| `peek('a.b')` | read without marking as used |
| `keys('a')` | sorted keys under a prefix |
| `meta`, `options`, `outline` | the manifest's `meta`, the resolved layout options, the effective outline |
| `c.*` | the components, below |

**Components** turn a value into output for the current format: `c.chapter`, `c.heading`, `c.contents`,
`c.cover`, `c.table`, `c.figure`, `c.image`, `c.equation`, `c.math`, `c.metrics`, `c.status`, `c.alert`,
`c.flow`, `c.metadata`, `c.bullets`, `c.code`, `c.text`, `c.number`, `c.attachment`, `c.value` (picks the
component from the value's kind), `c.details`, `c.note` (both are `{% call %}` blocks), `c.spacer` and
`c.page_break`. Each has Markdown, HTML and LaTeX macros in the layout; a layout that lacks one is `E707`.

**Filters** (ported from the MOSAICS report engine; the `fmt_` prefix is kept because `int` and `float` are
Jinja built-ins): `fmt_int`, `fmt_float`, `share`, `fmt_bytes`, `duration`, `pct`, `ppm`, `sci`, `compact`,
`missing`, `breakable` and `slug`. `missing` returns the placeholder for a value that has no number, so
`{{ x | missing or (x | fmt_int) }}` is the gate used by the components.

Output is escaped for its format automatically (HTML autoescape; LaTeX special characters
`# $ % & ~ _ ^ \ { }` and Unicode; Markdown markup characters). Text a component returns is never escaped
twice.

## Checking a template

`scireport validate` checks a bundle against a template and layout without writing anything. It reports every
problem at once (see {doc}`errors`): a missing required field (`E105`), a key the template reads but the
bundle lacks (`E106`), a value of the wrong kind (`E207`), a table without a required column (`E303`), and a
value nothing renders (`W401`). Template problems carry `file:line` and a "did you mean" suggestion.

Two checks run together: a lint of the Jinja syntax tree finds the keys a template reads (and keys it
computes, `W403`), and a render in memory records which values were really used. `--strict` turns warnings
into errors; `--json` prints the report for agents. Exit codes: 0 valid, 2 invalid.
