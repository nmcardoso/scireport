# User guide

This page explains how `scireport` thinks and how you work with it day to day. If you have not built a report yet,
start with the [Quickstart](quickstart.md). Exact fields, options and codes are in the reference pages: [The data-file specification](spec.md), [Command line](cli.md),
[Python API](api.md) and [Error codes](errors.md).

## The mental model

Three inputs go in and several files come out:

```text
data file (bundle)    what the report says: numbers, tables, figures, text
template              which values appear, and in what order
layout                what it looks like: fonts, colours, cover, page
        |
        v   scireport render
Markdown (for language models)   HTML   LaTeX   PDF   Word / ODT / EPUB (through pandoc)
```

The data file is the contract. Your analysis code writes it; nothing else needs to know how the numbers were
computed. A template and a layout can change without touching the data, and the data can change without touching
either.

### The bundle

A **report bundle** is the data file. It is one manifest (structure, text, numbers, metadata) plus the binary files the
manifest points to (tables as Parquet or CSV, figures as PNG and PDF). It comes in three forms, and every command and
function that takes a bundle takes any of them:

| Form | What it is | Made by |
|---|---|---|
| directory | `scireport.json` (or a hand-written `scireport.yaml`) plus `assets/<folder>/<file>` | you, `scireport unpack`, `Report.write('x.scireport')` |
| ZIP | `x.scireport.zip`: the same layout in one file, byte-reproducible | `scireport pack`, `Report.write('x.scireport.zip')` |
| single file | one `.json` or `.yaml` manifest that needs no assets | you, `Report.write('x.json')` |

The folders under `assets/` are `tables`, `figures`, `images`, `text` and `attachments`. YAML is for hand-written
directories only; a ZIP always holds JSON. Opening a bundle never needs a template or a layout; `validate` and
`render` do. See [the data file](spec.md) for every field.

### Keys and typed values

Every value in a bundle has a **key**: a dotted name such as `crossmatch.n_pairs`. Each segment uses lowercase
letters, digits, `_` or `-`. A key says what the value means, so templates ask for meaning (`data.crossmatch.n_pairs`)
and not for a type. The **kind** of the value is stored in the value itself, so a table that later becomes a figure
keeps its key and no template breaks. A key may not be the dotted prefix of another (`a` and `a.b` together is
`E102`).

A value is a mapping with a `kind` and the fields of that kind. Plain JSON is a shortcut: a string is a `text`, a
number is a `number`, a list is a `list`. The kinds:

| Kind | Holds |
|---|---|
| `text` | prose or a short string; plain, Markdown or raw LaTeX; inline or a file in `assets/text/` |
| `number` | a value with unit, number format and an uncertainty or an interval; `null` means missing |
| `bool` | true or false |
| `date` | an ISO 8601 date or date-time |
| `list` | an ordered or bulleted list of values |
| `mapping` | labelled entries in a fixed order (a description list) |
| `table` | a Parquet or CSV file, or a small inline table; per-column label, unit and format; row verdicts |
| `figure` | PNG, PDF or SVG renditions, required alt text, caption, width, optional data behind it |
| `image` | a logo or photo that is not drawn from data |
| `math` | a LaTeX expression, optionally numbered |
| `code` | source code or preformatted text |
| `metrics` | a grid of headline numbers |
| `status` | an overall verdict banner (success, warning, partial, failed, running) |
| `alert` | a one-line call-out (info, warning, error) |
| `flow` | a pipeline drawn as numbered stages |
| `attachment` | a file offered next to the report, such as the full table behind a cut one |
| `bibliography` | a BibTeX file that `[@key]` citations in text refer to |

Fields, defaults and one example per kind are in [The data-file specification](spec.md). In Python you add values with `Report.add_number`,
`add_table`, `add_figure` and so on; `Report.add` takes any bare JSON or envelope.

### The outline

The built-in `generic` template draws a bundle from its **outline**: a list of keys (a key draws that value) and
headings with children. A heading can start a new Markdown file with `md_file`. A value that is in the bundle but not
in the outline gets warning `W401`, so a forgotten value does not go unnoticed. Templates of your own do not use the
outline; they name the keys they read, and `scireport templates NAME --json` lists those keys, their kinds and the
table columns they need. Build the bundle to match, then validate.

### Template and layout

A **template** is the structure: a `template.yaml` that says which keys it reads and of which kind, and a
format-neutral `report.j2` that calls components (`c.chapter`, `c.table`, `c.figure`, ...). The same template gives
Markdown, HTML and LaTeX. A **layout** is the look: the skeleton of each format, the CSS and LaTeX styles, the
fonts, the palette, the matplotlib style and a list of options. The two are separate directories, so a project
changes its look without touching its template, and the other way round (ADR-0003).

| Built in | Names |
|---|---|
| templates | `generic@1` (draws any bundle from its outline), `kitchen-sink@1` (one of every component; used to test layouts) |
| layouts | `default@1`, `modern@1`, `minimal@1` (no PDF engine of its own: `E903` if you ask for a PDF) |

`scireport templates` and `scireport layouts` list what is installed; add a name to describe one. The name after `@`
is a version. Built-in versions are frozen: a look change is a new version, so a bundle that names `default@1`
renders the same years from now. A bare name means the newest. Your own template or layout is a directory, passed as
`-t ./my-template` or `-l ./my-layout` (the `./` matters), see [Writing a template](templates.md), [Built-in layouts](layouts.md) and
[Writing a layout](layout-authoring.md).

### Formats and PDF engines

| Format | Made by |
|---|---|
| `md`, `html`, `tex` | the built-in renderer; `tex` is a standalone LaTeX project (`latexmk report.tex` compiles it) |
| `pdf` | WeasyPrint from the HTML (default), or `latexmk` from the LaTeX project (`--pdf-engine latex`) |
| `docx`, `odt`, `epub` | pandoc, from the Markdown (needs the `pandoc` extra) |

With no `-f`, a render writes the formats the bundle lists in `render.formats`, else `md`, `html` and `tex`. A PDF
is never a default; ask for it. What each format writes is in [Outputs](outputs.md); the prose dialect is in [Markdown in reports](markup.md);
Word, ODT, EPUB and citations are in [pandoc: markup engine, citations and office formats](pandoc.md).

### Pre-processors

A **pre-processor** turns data in the bundle into a figure or a table at render time: a histogram of a column, a
sky map, a funnel of cuts. The bundle lists *steps* by registered name, for example `core.histogram`; it never
contains code. Each step writes its figure together with the small table it was drawn from. Results are cached by
content, so rendering again does not redraw.

```python
from scireport import Report

report = Report('Pre-processing demo')
report.add_table('crossmatch.pairs', {'sep_arcsec': [0.21, 0.48, 0.77, 0.35, 0.52, 0.66]})
report.add_preprocess(
  'core.histogram',
  inputs={'table': 'crossmatch.pairs'},
  outputs={'figure': 'crossmatch.sep_hist'},
  params={'column': 'sep_arcsec', 'bins': 4},
)
report.set_outline(['crossmatch.pairs', 'crossmatch.sep_hist'])
report.write('pre.scireport.zip')
```

`scireport render pre.scireport.zip -o out -f md` runs the step first and then renders the table and the new figure.
`scireport preprocessors` lists the registered steps and `scireport preprocessors core.histogram` shows the ports and
parameters of one. A step that names `module:function` runs code from the data file, so it needs `--allow-import`;
use that only for files you trust. See [Pre-processors](preprocessors.md).

## The workflow

Author the data, validate it, render it, and pack it when it is final.

### 1. Author the data

**From Python**, with `Report`: it checks each call at once and raises a coded error at the line that made the
mistake, and `report.write(...)` produces a bundle. The [Quickstart](quickstart.md) shows the whole sequence. Two things
to remember: `add_figure` needs `alt`, and you draw figures inside `with scireport.mplstyle():` with
`scireport.figure(width, height)` so that they match the report (see [Matplotlib style guide](styles.md)).

**By hand**, with a directory and a `scireport.yaml`. `scireport new my-report` writes a starter that already
validates; edit it. The YAML reader is stricter than most: only `true` and `false` are booleans (`yes` and `on`
are strings), a date stays a string, aliases (`*a`) are rejected, and a duplicate key is an error. Quote the
spec version, `'1.0'`.

**For an agent**, `scireport agent install-skill -d .claude/skills` installs a skill that teaches a coding agent
all of this, and `scireport mcp serve` exposes the tools over MCP (see [The agent skill](agent.md) and [MCP server](mcp.md)).

### 2. Validate

```console
$ scireport validate my-report
valid: 0 error(s), 0 warning(s)
```

`validate` checks the bundle against the template and the layout and writes nothing. It reports **every** problem it
finds in a stage, not only the first. A problem is an **issue** with a stable code: `E` is an error, `W` is a
warning, and the hundreds digit says where it comes from (`E1xx`-`E3xx` the data file, `E4xx` bundles and assets,
`E5xx` versions and pandoc, `E6xx` pre-processing, `E7xx` templates and layouts, `E8xx` rendering and exports, `E9xx`
PDF engines). Add `--json` to get the issues as data. This bundle has a bad key and an out-of-range figure width:

```console
$ scireport validate bad --json
```

```json
{
  "ok": false,
  "issues": [
    {
      "code": "E101",
      "severity": "error",
      "message": "invalid key 'Crossmatch.N_pairs': segments must match [a-z0-9_-]+ and be joined by single dots",
      "pointer": "/values/Crossmatch.N_pairs",
      "key": "Crossmatch.N_pairs",
      "hint": "Did you mean 'crossmatch.n_pairs'?"
    },
    {
      "code": "E205",
      "severity": "error",
      "message": "Input should be less than or equal to 1",
      "pointer": "/values/crossmatch.sep_hist/width",
      "key": "crossmatch.sep_hist"
    }
  ]
}
```

Read an issue field by field:

| Field | Meaning |
|---|---|
| `code` | the stable identifier; look it up in [Error codes](errors.md), or with `scireport spec errors --json` |
| `severity` | `error` or `warning` |
| `message` | what is wrong, in a sentence |
| `pointer` | a JSON pointer into the manifest: `/values/crossmatch.sep_hist/width` is the `width` field of that value |
| `key` | the value key involved |
| `expected`, `found` | what was required and what was there, when that makes sense |
| `hint` | a suggestion, such as `Did you mean 'crossmatch.n_pairs'?` |
| `location` | for a problem raised by a template, the template file and line (`report.j2:15`) |

`expected` and `found` appear when you tamper with a file the manifest has hashed. After a byte is appended to the
figure of an unpacked bundle:

```text
E403 /values/crossmatch.sep_hist/renditions/0: asset assets/figures/crossmatch.sep_hist.png has the wrong size (expected 19436, found 19438)
invalid: 1 error(s), 0 warning(s)
```

And `location` appears when a template reads a key the bundle does not have. Here a bundle is checked against the
`kitchen-sink@1` template, which needs many keys:

```text
E106 report.j2:15: /values: the template reads key 'qc', which the bundle does not have
```

(The real run prints one `E106` line for every place the template reads a missing key.)

A warning does not fail the command. `--strict` turns warnings into errors, which is what you want in CI. Run
`validate` with the formats you will render (`-f tex`) so the checks of that format run too.

The exit code tells a script what happened:

<!-- generated:exit-codes -->
| Code | Meaning |
|---|---|
| 0 | Success. |
| 1 | A failure that is not a problem in the data file (I/O error, pandoc or a PDF engine failed, `agent install-skill --check` found a difference). |
| 2 | The data file, template, layout or an export is invalid (errors; with `--strict` also warnings). |
| 3 | A system dependency or optional extra is missing (pango, TeX Live, `scireport[pandoc]`, `scireport[mcp]`); the message says how to install it. |
<!-- /generated -->

### 3. Render

```console
$ scireport render my-report -o out -f md -f html
```

Each format goes to its own folder of the output directory, next to `render-manifest.json` (the hash of every input
and output, the template and layout versions, the engines). `--flat` writes a single format straight into the
directory. Nothing is written when validation fails. Choose the parts with `-t` and `-l`, and layout options with
`-O name=value`:

```console
$ scireport layouts default@1
$ scireport render my-report -o out -f html -l modern -O toc=false -O cover=false
```

Options come from the layout's defaults, then the bundle's `render.options`, then `-O`. An unknown option or a value
outside the choices is `E806`. Everything you can pass is in [Command line](cli.md); the same choices can be stored in the
bundle's `render` block (`template`, `layout`, `formats`, `pdf_engine`, `latex_engine`, `options`), and the command
line wins.

Never edit anything under `out/`. Change the data file, the template or the layout and render again.

### 4. Pack

```console
$ scireport pack my-report -o my-report.scireport.zip
```

`pack` seals a directory into the ZIP you keep, share or cite. It computes the hash and size of every asset, writes
canonical JSON, leaves out files that no value references, and **pins versions**: a bare `generic` or `default`
becomes `generic@1` or `default@1` (and the pandoc version is recorded when pandoc is used). A bundle written by
`Report.write` is already sealed, but it does not pin versions on its own; either name them in
`report.set_render(template='generic@1', layout='default@1')`, or run `pack` on the result. `unpack` reverses `pack`
and checks every hash, and `inspect` shows what a bundle holds and verifies its integrity (`inspect SOURCE -k KEY`
prints one value).

## Choosing a layout, options and a PDF engine

`default@1` has a cover page and chapter openers; `modern@1` is a second look; `minimal@1` is plain and has no
PDF engine. Describe a layout with `scireport layouts NAME` to see its options. For `default@1` and `modern@1`
they are `toc`, `cover`, `paper` (`a4` or `letter`), `chapter_breaks`, `numbered_captions` and `header`.

| PDF engine | Choose it when | Needs |
|---|---|---|
| `weasyprint` (default) | you want a PDF that matches the HTML | the `pdf` extra and pango |
| `latex` | you want real LaTeX typography and math, or the same PDF a LaTeX user would compile | TeX Live: `latexmk` and a TeX engine; `biber` when the bundle has a bibliography |

```console
$ scireport render my-report -o out -f pdf
$ scireport render my-report -o out -f pdf --pdf-engine latex --latex-engine xelatex
```

The TeX engine is `lualatex` by default; `xelatex` and `pdflatex` also work. `pdflatex` cannot typeset scripts such
as CJK, nor non-ASCII characters in code blocks. A missing system dependency exits with code 3 and an install hint,
never a traceback. A LaTeX compile that fails is `E902`, exit code 1, with the `file:line` of each TeX error. If one
engine fails on your document, try the other.

## Reproducibility

The same inputs and the same versions give the same bytes in `.md`, `.html`, `.tex` and PNG files, on any
machine. This is a rule of the package:

- **No clock.** `meta.date` is only what you wrote; scireport never fills it in. The ZIP of a bundle has sorted
  entries and fixed 1980 timestamps. Matplotlib figures are saved without version or date metadata. Pre-processors
  are seeded (`--seed`, default 0).
- **No absolute paths** in any output.
- **PDF dates** come from `SOURCE_DATE_EPOCH` when it is set, else from `meta.date`, else 1980-01-01.
- **PDF bytes** are best-effort: they repeat on one machine with the same library and font versions (rendering the
  same bundle twice here gave identical files), but not guaranteed across machines. To detect a change, compare the
  `sha256` entries of `render-manifest.json`.

You can check it yourself: render twice and compare.

```console
$ scireport render my-report -o a -f md -f html -f tex
$ scireport render my-report -o b -f md -f html -f tex
$ diff -r a b && echo identical
identical
```

## Bundles hold summaries

A bundle holds the **summary** of an analysis, not the raw catalogue: aggregate first, then store the result. A
histogram of a million separations is twenty rows; a sky map is HEALPix counts. This keeps bundles small and
diffable, and the report honest about what it shows (ADR-0001).

```python
import numpy as np

from scireport import Report

rng = np.random.default_rng(0)
separations = rng.rayleigh(0.3, 1_000_000)  # a million rows: far too many to store

counts, edges = np.histogram(separations, bins=20, range=(0, 2))
report = Report('Cross-match report')
report.add_table(
  'crossmatch.sep_counts',
  {'bin_low': edges[:-1], 'bin_high': edges[1:], 'pairs': counts},
  columns=[
    {'name': 'bin_low', 'label': 'From', 'unit': 'arcsec', 'format': '.1f'},
    {'name': 'bin_high', 'label': 'To', 'unit': 'arcsec', 'format': '.1f'},
    {'name': 'pairs', 'label': 'Pairs', 'format': 'int'},
  ],
  caption='Pairs per separation bin.',
)
report.add_number('crossmatch.n_pairs', len(separations), format='int')
report.add_number('crossmatch.sep_median', float(np.median(separations)), unit='arcsec', format='.3f')
report.set_outline(['crossmatch.n_pairs', 'crossmatch.sep_median', 'crossmatch.sep_counts'])
report.write('summary.scireport.zip')
```

The ZIP is about 2 kB. `add_table` accepts numpy arrays inside a dict, and a table over `max_rows` can link to the
full data as an `attachment`. The pre-processors above do the aggregation for you.

## Recipes

### Markdown for language models, and one PDF for people

One bundle, one command, two audiences:

```console
$ scireport render crossmatch.scireport.zip -o out -f md -f pdf
```

If the outline gives chapters an `md_file`, the Markdown is split: `md/index.md` holds the front matter and the
contents, and each chapter has its own file, so a model reads only the chapters it needs.

```python
report.set_outline(
  [
    'summary',
    {'title': 'Results', 'md_file': 'results.md', 'children': ['crossmatch.n_pairs', 'crossmatch.pairs']},
  ]
)
```

```text
md/index.md
md/results.md
pdf/report.pdf
render-manifest.json
```

Without `md_file`, everything is in `md/report.md`; `--no-md-split` forces one file. Nothing is flattened for the
model: math stays `$...$` and `$$...$$`, tables are pipe tables with the number formats applied, figures are PNG files
linked with their alt text, and the first line of every file says which scireport, template and layout made it.

### Check in CI

Fail a pull request when the data file is invalid, and keep the render as a build artifact. The commands:

```console
$ scireport validate report --strict --json > validate.json
$ scireport render report -o out -f md -f html --strict
```

`validate` exits with 2 when anything is wrong (`--strict` includes warnings), and with `--json` it still prints the
issues on standard output, so the log shows them. As a GitHub Actions job (the project depends on scireport through
`uv add`):

```yaml
name: report
on: [push, pull_request]
jobs:
  report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: astral-sh/setup-uv@v10.2.0
      - run: uv sync
      - run: uv run scireport validate report --strict --json
      - run: uv run scireport render report -o out -f md -f html --strict
      - uses: actions/upload-artifact@v7
        with:
          name: report
          path: out
          if-no-files-found: error
```

For a PDF in CI, install the system packages first (pango for WeasyPrint, or TeX Live for `--pdf-engine latex`), see
the [Quickstart](quickstart.md). To keep an invalid file out of the repository, run the same `validate` as a pre-commit hook.
Pin scireport to a tag or commit so the job is reproducible.

### Numbers for a LaTeX paper

A manuscript should quote numbers, tables and figures that come from the analysis, not from copy and paste.
`export tex` writes LaTeX fragments from a bundle; it does not render the report.

```console
$ scireport export tex crossmatch.scireport.zip -o paper/generated -k 'crossmatch.*' --prefix Xm
```

```text
fig_crossmatch.sep_hist.pdf
fig_crossmatch.sep_hist.tex
numbers.tex
tab_crossmatch.pairs.tex
```

`numbers.tex` holds one `\newcommand` per `number` value. The macro name is the key in CamelCase with digits spelled
out, after the prefix (letters only):

```tex
% crossmatch.n_pairs
\newcommand{\XmCrossmatchNPairs}{8~pairs}
% crossmatch.sep_mean
\newcommand{\XmCrossmatchSepMean}{0.46 \ensuremath{\pm} 0.07~arcsec}
```

Use them in `paper/main.tex`, and compile with `cd paper && latexmk -lualatex main.tex`:

```tex
\documentclass{article}
\usepackage{graphicx, booktabs, longtable}
\input{generated/numbers}
\begin{document}
We matched \XmCrossmatchNPairs{} with a mean separation of \XmCrossmatchSepMean.
Table~\ref{tab:crossmatch.pairs} and Figure~\ref{fig:crossmatch.sep_hist} show the details.
\input{generated/tab_crossmatch.pairs}
\input{generated/fig_crossmatch.sep_hist}
\end{document}
```

The first lines of each fragment say which packages it needs. Two keys that give the same macro name are `E807`;
rename one or export them separately. `--bare` writes a plain `tabular` and `\includegraphics` without a float,
`--max-rows` cuts tables, and `--graphics-prefix` changes the path used for figures. Re-run the export whenever the
data changes and commit the fragments, or run it in the paper's build. The same function is available in Python as
`export_tex`. See [LaTeX fragments for manuscripts](export.md).

## Where to go next

- [The data-file specification](spec.md): the manifest blocks and every value kind.
- [Command line](cli.md): every command and option.
- [Python API](api.md): the public Python names.
- [Error codes](errors.md): every code, with what to do.
- [Writing a template](templates.md), [Built-in layouts](layouts.md) and [Writing a layout](layout-authoring.md): choose or write the structure and the look.
- [Pre-processors](preprocessors.md), [Outputs](outputs.md), [Markdown in reports](markup.md), [pandoc: markup engine, citations and office formats](pandoc.md) and [LaTeX fragments for manuscripts](export.md): the reference pages for each
  stage.
- [Compatibility policy](compatibility.md): what the package promises about reading old data files.
