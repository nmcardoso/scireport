# Quickstart

In about ten minutes you will build a small report in Python, check it, render it to Markdown and HTML (and to a
PDF), write the same report by hand as a YAML directory, and freeze that directory into one file.

A report in `scireport` is made of three things: a **data file** (a "report bundle" that holds your numbers, tables,
figures and text), a **template** (which values appear, in what order) and a **layout** (what it looks like). You
write the data file; the template and the layout have good built-in defaults.

## Install

Install from the public GitHub repository, never from a local path, so that a referee can rebuild your environment:

```console
$ uv add "scireport @ git+https://github.com/nmcardoso/scireport"
```

To fix the version, add a tag or a commit after the URL (`...scireport@<tag>`; tags are listed at
<https://github.com/nmcardoso/scireport/tags>). Optional features are extras:

| Extra | Adds | Also needs on the system |
|---|---|---|
| `pdf` | PDF through WeasyPrint (`-f pdf`, the default PDF engine) | the pango libraries |
| `pandoc` | Word, ODT and EPUB output, citations (it bundles a pandoc binary) | nothing |
| `astro` | HEALPix sky maps in the `astro.*` pre-processors | nothing |
| `mcp` | the MCP server for coding agents | nothing |

```console
$ uv add "scireport[pdf,pandoc] @ git+https://github.com/nmcardoso/scireport"
```

Markdown, HTML and LaTeX output need nothing beyond the base install. Two PDF routes need system software:

- **WeasyPrint** (the default PDF engine) needs pango. On Debian or Ubuntu:
  `sudo apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0`.
- **LaTeX** (`--pdf-engine latex`) needs TeX Live: `latexmk` and one TeX engine (`lualatex` by default, or `xelatex`,
  or `pdflatex`). On Debian or Ubuntu:
  `sudo apt install texlive-latex-extra texlive-luatex texlive-xetex latexmk texlive-fonts-recommended`.

If one of these is missing, `scireport render -f pdf` does not crash with a traceback. It prints the error `E901` with
the install command for your system and exits with code 3 (see {doc}`errors`).

Run the commands below with `uv run scireport ...`, or with plain `scireport ...` inside an activated environment.

## Build a report in Python

`Report` collects values under **keys**. A key is a dotted name that says what the value means
(`crossmatch.n_pairs`); the kind of value (number, table, figure, ...) is stored in the value, not in the key. Start
with the text, the numbers and a table:

```python
import math
import statistics

import scireport
from scireport import Report

separations = [0.21, 0.48, 0.77, 0.35, 0.52, 0.66, 0.30, 0.41]  # arcsec

report = Report('Cross-match report', authors=['Ada Lovelace'], date='2026-10-09', version='1.0.0')
report.add_text(
  'summary',
  r'''Pairs closer than **1 arcsec** are kept: a pair is accepted when $d < r_{\mathrm{match}}$, that is

$$d = \sqrt{(\Delta\alpha \cos\delta)^2 + \Delta\delta^2} < r_{\mathrm{match}}.$$''',
  format='markdown',
)
report.add_number('crossmatch.n_pairs', len(separations), unit='pairs', format='int')
report.add_number(
  'crossmatch.sep_mean',
  statistics.mean(separations),
  unit='arcsec',
  uncertainty=statistics.stdev(separations) / math.sqrt(len(separations)),
  format='.2f',
)
report.add_table(
  'crossmatch.pairs',
  {'id': list(range(1, 9)), 'sep_arcsec': separations},
  columns=['id', {'name': 'sep_arcsec', 'label': 'Separation', 'unit': 'arcsec', 'format': '.2f'}],
  caption='Matched pairs.',
)
```

Text is Markdown when you say `format='markdown'`, and `$...$` or `$$...$$` is LaTeX math. A table can be a dict of
columns, a list of row dicts, or a pandas, polars or pyarrow table; `columns` sets labels, units and number formats.
A number carries its unit, format and uncertainty, so the report prints `0.46 ± 0.07 arcsec`, not a bare float.

Now a figure. Draw it inside `scireport.mplstyle()` and create it with `scireport.figure(width, height)`: the style is
the one of the report, and `width` is a fraction of the page width, so the text in the figure has the size you chose
on paper. The `alt` text is required.

```python
with scireport.mplstyle():
  fig, ax = scireport.figure(0.7, 2.8)  # 70 % of the page width, 2.8 inches high
  ax.hist(separations, bins=4)
  ax.set_xlabel('Separation [arcsec]')
  ax.set_ylabel('Pairs')
  report.add_figure(
    'crossmatch.sep_hist',
    fig,
    alt='Histogram of the separations of the matched pairs, in arcsec.',
    caption='Separations.',
    width=0.7,
  )
```

Last, say which values the report shows and in what order (the `outline`, used by the built-in `generic` template),
which template and layout to use, and write the bundle:

```python
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
report.set_render(template='generic@1', layout='default@1', formats=['md', 'html'])
print(report.write('crossmatch.scireport.zip'))
```

```text
crossmatch.scireport.zip
```

`write` checks the report and refuses to overwrite an existing file (pass `overwrite=True` to replace it). A name that
ends in `.scireport.zip` gives one ZIP; any other name gives a directory. The ZIP is byte-reproducible: the same calls
give the same file.

## Validate and render

Look at what the bundle holds, then validate it. `validate` changes nothing; it checks the data file against the
template and the layout, and renders in memory to find what only a render shows.

```console
$ scireport inspect crossmatch.scireport.zip
$ scireport validate crossmatch.scireport.zip
```

```text
Cross-match report
  spec 1.0, zip bundle: crossmatch.scireport.zip
  authors: Ada Lovelace
  values: 5 (figure 1, number 2, table 1, text 1)
  assets: 3 files, 29,255 bytes
  integrity: ok

  crossmatch.n_pairs   number      8 pairs
  crossmatch.pairs     table       8 rows, 2 columns, parquet
  crossmatch.sep_hist  figure      png, pdf; Histogram of the separations of the matched pairs, in arcsec.
  crossmatch.sep_mean  number      0.4625 ± 0.07 arcsec
  summary              text        markdown: Pairs closer than **1 arcsec** are kept. The match radius i…
valid: 0 error(s), 0 warning(s)
```

Render to Markdown and HTML. The command prints the files it wrote, relative to the output directory; progress logs go
to standard error.

```console
$ scireport render crossmatch.scireport.zip -o out -f md -f html
```

```text
html/report.html
md/figures/crossmatch.sep_hist.png
md/report.md
render-manifest.json
```

`out/md/report.md` is the file for a language model: plain Markdown, math kept as LaTeX, the figure as a PNG linked
with its alt text. `out/html/report.html` is one self-contained file that you can mail or open in a browser.
`render-manifest.json` records the hash of every input and output and the tool versions. Nothing is written if
validation fails.

```markdown
# Cross-match report

Ada Lovelace

Date: 2026-10-09 · Version: 1.0.0

Pairs closer than **1 arcsec** are kept: a pair is accepted when $d < r_{\mathrm{match}}$, that is

## Results

**N pairs:** 8 pairs

**Sep mean:** 0.46 ± 0.07 arcsec

*Table 1. Matched pairs.*

| id | Separation (arcsec) |
|---:|---:|
| 1 | 0.21 |
...
![Histogram of the separations of the matched pairs, in arcsec.](figures/crossmatch.sep_hist.png)

*Figure 1. Separations.*
```

(The excerpt drops the generated-file comment, the contents list and some table rows.) The `generic` template labels
a number with its key ("N pairs", "Sep mean"); a template of your own chooses its own labels, see {doc}`templates`.

For a PDF, ask for it. A PDF is never a default format. This needs the `pdf` extra and pango (see above); on a machine
without them the command exits with code 3 and tells you what to install.

```console
$ scireport render crossmatch.scireport.zip -o out-pdf -f pdf
$ scireport render crossmatch.scireport.zip -o out-latex -f pdf --pdf-engine latex
```

```text
pdf/report.pdf
render-manifest.json
```

The first command prints the PDF with WeasyPrint. The second compiles the LaTeX project with `latexmk` and is slower
(about ten seconds for this report). WeasyPrint may log `Using fontTools instead of HarfBuzz-Subset` on standard
error when `libharfbuzz-subset0` is missing; the PDF is still produced. Use `-l modern` for the other built-in look.

## The same report as a YAML directory

You do not need Python to make a data file. A bundle can be a directory with a `scireport.yaml` and an `assets/`
folder. `scireport new my-report` writes a starter that already validates; here we write one by hand. Start from the
figure of the bundle you just made: `unpack` turns a ZIP back into a directory (checking every hash), and the figure
is copied next to the new file.

```console
$ scireport unpack crossmatch.scireport.zip
$ mkdir -p my-report/assets/figures
$ cp crossmatch.scireport/assets/figures/crossmatch.sep_hist.png my-report/assets/figures/sep_hist.png
```

```yaml
# my-report/scireport.yaml
scireport: '1.0'
meta:
  title: Cross-match report
  authors: [Ada Lovelace]
  date: '2026-10-09'
  version: 1.0.0
render:
  template: generic
  layout: default
  formats: [md, html]
outline:
  - summary
  - title: Results
    children: [crossmatch.n_pairs, crossmatch.pairs, crossmatch.sep_hist]
values:
  summary:
    kind: text
    format: markdown
    text: |
      Pairs closer than **1 arcsec** are kept: a pair is accepted when $d < r_{\mathrm{match}}$.
  crossmatch.n_pairs: {kind: number, value: 8, unit: pairs, format: int}
  crossmatch.pairs:
    kind: table
    caption: Matched pairs.
    columns:
      - {name: id}
      - {name: sep_arcsec, label: Separation, unit: arcsec, format: .2f}
    rows: [[1, 0.21], [2, 0.48], [3, 0.77], [4, 0.35]]
  crossmatch.sep_hist:
    kind: figure
    alt: Histogram of the separations of the matched pairs, in arcsec.
    caption: Separations.
    width: 0.7
    renditions: [assets/figures/sep_hist.png]
```

Every value is a mapping with a `kind`. Quote the version (`'1.0'`) and the date, because YAML would read them as
numbers or dates. Plain strings, numbers and lists are shortcuts for the common kinds ({doc}`spec`). A small table
can be written inline as above; a large one belongs in `assets/tables/` as a Parquet or CSV file.

Validate the directory, render it directly, then **pack** it:

```console
$ scireport validate my-report
$ scireport render my-report -o out-yaml -f md
$ scireport pack my-report -o my-report.scireport.zip
```

```text
valid: 0 error(s), 0 warning(s)
md/figures/crossmatch.sep_hist.png
md/report.md
render-manifest.json
my-report.scireport.zip
```

`pack` computes the SHA-256 and size of every asset, rewrites the manifest as canonical JSON, leaves out files that no
value uses, and **pins** the template and the layout to the versions it resolved: the bare names `generic` and
`default` above become `generic@1` and `default@1` in the ZIP. The ZIP is the file to keep, share and cite. Open it
with `scireport inspect`, or turn it back into a directory with `scireport unpack`.

## Where to go next

- {doc}`guide`: the mental model (bundle, keys, outline, template, layout) and the everyday workflow, with recipes
  for CI and for a LaTeX paper.
- {doc}`spec`: every manifest block and value kind, field by field.
- {doc}`cli`: every command and option, and the exit codes.
- {doc}`errors`: every error and warning code (`E1xx`, `W4xx`, ...) and what to do about it.
- {doc}`templates` and {doc}`layouts`: what the built-in templates read and how the layouts differ; to write your own,
  see {doc}`layout-authoring`.
- {doc}`examples`: three complete reports (a dataset report, a metrics dashboard, a text-only report).
- {doc}`agent`: the packaged skill and the MCP server, for coding agents that write and check data files.
