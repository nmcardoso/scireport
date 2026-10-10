# Recipes

Task-oriented, end to end. Every block here was run against this version. The commands assume the project
depends on scireport (`uv add "scireport[pdf,pandoc,mcp] @ git+https://github.com/nmcardoso/scireport"`) and are
prefixed with `uv run`; drop the prefix if `scireport` is already on the path. Pages: `data-file.md`,
`python-api.md`, `cli.md`, `templates-and-layouts.md`, `preprocessors.md`, `mplstyle.md`, `errors.md`.

Logs go to standard error; standard output holds the result (`--json` makes it machine-readable).

## Markdown for LLMs plus one PDF for humans

Use when a pipeline produces a report that a language model must read and a person must sign off. One bundle,
one command, two audiences.

```bash
uv run scireport render crossmatch.scireport.zip -o out -f md -f pdf
```

```text
out/md/index.md                       <- the LLM starts here (table of contents, links to the chapter files)
out/md/results.md                     <- one file per chapter that names an md_file in the outline
out/md/figures/crossmatch.sep_hist.png
out/pdf/report.pdf                    <- the human reads this
out/render-manifest.json              <- sha256 and size of every output, tool versions, options
```

- **Which Markdown file.** With `md_file` on outline chapters (`{'title': 'Results', 'md_file': 'results.md',
  'children': [...]}`, see recipe 7) the Markdown is split by chapter: `md/index.md` holds the front matter and
  the contents, each chapter its own file, so a model reads only the chapters it needs. Without `md_file`
  everything is in `md/report.md`. `--no-md-split` forces one file; `--flat` writes one format straight into
  the output directory instead of `md/`.
- **PDF engine.** The default is WeasyPrint (needs pango, see recipe 2). For real LaTeX math and typography add
  `--pdf-engine latex` (needs TeX Live: `latexmk`, `lualatex`); the Markdown is unchanged.
- **Why the Markdown is the source as written.** Nothing is flattened for the model: math stays `$...$` and
  `$$...$$` (LaTeX, as in the data file), tables are pipe tables with the number formats applied, figures are
  PNG files linked as `![alt text](figures/x.png)` (the alt text is required in the data file, so the model
  always gets a description), captions are `*Table 1. ...*` lines. The file starts with a comment naming the
  scireport, template and layout versions and the manifest hash.

```markdown
**Median sep:** 0.353 arcsec

*Table 1. Pairs per r-band magnitude bin.*

| r \[mag\] | Pairs | Median separation (arcsec) |
|:---|---:|---:|
| (14, 19\] | 512 | 0.349 |
| (19, 20\] | 1,147 | 0.353 |

![Histogram of match separations in arcsec.](figures/crossmatch.sep_hist.png)
```

- **Determinism.** The same bundle and the same scireport, template and layout versions give byte-identical
  `.md`, `.html`, `.tex` and PNG files on any machine (no wall-clock time, no absolute paths; the date is the
  `meta.date` you wrote, and `SOURCE_DATE_EPOCH` is honoured). Rendering twice and running `diff -r out1 out2`
  printed nothing here, PDF included. A PDF is guaranteed identical only on one machine with one set of
  library versions; compare the `sha256` entries of `render-manifest.json` to detect a change.
- **What goes wrong.** Nothing is written if validation fails (exit 2). A PDF without pango or TeX Live is exit 3
  with the install command. WeasyPrint prints `Using fontTools instead of HarfBuzz-Subset` warnings on stderr
  when `libharfbuzz-subset0` is missing; the PDF is still produced.

## CI

Use to fail a pull request when the report data file is invalid and to keep the rendered report as a build
artifact. Install from the GitHub repository, never from a local path.

`.github/workflows/report.yml` with uv (the project depends on scireport through `uv add`):

```yaml
name: report
on: [push, pull_request]
jobs:
  report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: astral-sh/setup-uv@v10.2.0
        with:
          python-version: "3.12"
          enable-cache: true
      # WeasyPrint PDFs (-f pdf):
      #   - run: sudo apt-get update && sudo apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0
      # LaTeX PDFs (--pdf-engine latex), citations also need biber:
      #   - run: sudo apt-get install -y latexmk texlive-luatex texlive-latex-extra texlive-fonts-recommended
      #                                  biber texlive-bibtex-extra
      - run: uv sync
      - name: Validate (warnings fail too)
        run: uv run scireport validate report --strict --json | tee validate.json
      - name: Render
        run: uv run scireport render report -o out -f md -f html --strict
      - uses: actions/upload-artifact@v7
        with:
          name: report
          path: out
          if-no-files-found: error
```

Without a project, run the tool from the repository with `uvx`; the extras go in brackets (`[pdf]`, `[pandoc]`):

```bash
uvx --from "scireport[pandoc] @ git+https://github.com/nmcardoso/scireport" \
  scireport validate report --strict --json
```

The same as a plain shell script (this ran, and failed with exit 2 on a broken file, printing the issues):

```bash
#!/usr/bin/env bash
set -euo pipefail

scireport() { uv run scireport "$@"; }

scireport validate report --strict --json > validate.json || {
  status=$?
  cat validate.json
  exit "$status"
}
scireport render report -o out -f md -f html --strict
```

Exit codes the job can rely on: `0` ok; `1` a runtime failure that is not the data file's fault (I/O, pandoc or
the PDF engine failed); `2` invalid (errors, or warnings with `--strict`; `validate --json` still prints the
issues on stdout); `3` a system dependency or extra is missing (pango, TeX Live, `scireport[pandoc]`,
`scireport[mcp]`). `validate` writes nothing; `render` writes nothing when it exits 2. Pin the dependency to a
tag or commit (`scireport @ git+https://github.com/nmcardoso/scireport@<tag>`) for a reproducible job.

## Numbers and tables in a paper

Use when a manuscript must quote numbers, tables and figures that come from the analysis, not from copy and
paste. `export tex` writes fragments; it does not render the report.

```bash
uv run scireport export tex crossmatch.scireport.zip -o paper/generated --keys 'crossmatch.*' --prefix Xm
```

```text
paper/generated/numbers.tex                  one \newcommand per number value
paper/generated/tab_crossmatch.by_mag.tex    a table float (booktabs)
paper/generated/fig_crossmatch.sep_hist.tex  a figure float
paper/generated/fig_crossmatch.sep_hist.pdf  the figure file (PDF preferred over PNG)
```

```latex
% numbers.tex
% crossmatch.median_sep
\newcommand{\XmCrossmatchMedianSep}{0.353~arcsec}
% crossmatch.n_pairs
\newcommand{\XmCrossmatchNPairs}{5,000~pairs}
```

`paper/main.tex` (compiled with `cd paper && latexmk -lualatex main.tex`, exit 0, `main.pdf` has the table, the
figure and the sentence):

```latex
\documentclass{article}
\usepackage{graphicx, booktabs, longtable}
\input{generated/numbers}
\begin{document}
We matched \XmCrossmatchNPairs{} and found a median separation of \XmCrossmatchMedianSep.
Table~\ref{tab:crossmatch.by_mag} and Figure~\ref{fig:crossmatch.sep_hist} show the details.
\input{generated/tab_crossmatch.by_mag}
\input{generated/fig_crossmatch.sep_hist}
\end{document}
```

- **Macro names.** `<Prefix>` + the key in CamelCase: `.`, `_` and `-` start a new capitalised word, and every
  digit becomes its English word (LaTeX macro names cannot hold digits): `crossmatch.n_pairs` is
  `\XmCrossmatchNPairs`, `fit.chi2` is `\FitChiTwo`, `fit.2d_count` is `\FitTwodCount`. The value carries its
  number format and unit (`5,000~pairs`).
- **Collisions are `E807`**, exit 2, and nothing is written: `fit.chi2` and `fit.chi_2` both give `\FitChiTwo`.
  Rename one key, export them separately (`--keys`), or use a different `--prefix`.
- **Options.** `--keys` takes `*` and `?` patterns, repeated or comma-separated (default: every number, table and
  figure); `--bare` writes a plain `tabular`/`\includegraphics` without float or caption; `--max-rows N` cuts
  tables; `--graphics-prefix` changes the path written in `\includegraphics` (default: the output directory name,
  here `generated/`, so run LaTeX in the directory that holds `generated/`).
- **Packages.** The first lines of each fragment say what it needs (`% Needs: booktabs, longtable`, `graphicx`);
  `numbers.tex` needs none.
- Re-run the export whenever the data changes and commit the fragments, or generate them in the paper's build.

## Citations

Use when prose carries references. A bundle holds one `bibliography` value (a `.bib` file); text uses
`[@key]` and `[@key, p. 12]`.

```python
import scireport

report = scireport.Report('Citations demo', authors=['Ada Example'], date='2026-01-15')
report.add_text(
  'intro',
  'Pairs are matched within 1 arcsec [@marshall2006]. Errors follow [@wall2003, p. 12].',
  format='markdown',
)
report.add_bibliography('refs', 'refs.bib')   # style='authoryear' for biblatex; csl=... for pandoc
report.set_outline(['intro', {'title': 'References', 'children': ['refs']}])
report.set_render(template='generic@1', formats=['md', 'html', 'pdf'])
report.write('cite.scireport.zip', overwrite=True)
```

`refs.bib` is ordinary BibTeX/BibLaTeX (`@article{marshall2006, author = {Marshall, Phil and Treu, Tommaso}, ...}`).
In the `generic` template a `bibliography` key listed in the outline prints the reference list. In your own
template write `{{ c.references() }}` after a heading (`{{ c.references(everything=True) }}` lists uncited works
too); pass the template directory as `-t ./mytemplate` (the `./` matters, see `templates-and-layouts.md`).

```bash
uv run scireport validate cite.scireport.zip
uv run scireport render cite.scireport.zip -o out -f md -f html            # citations resolved by pandoc
uv run scireport render cite.scireport.zip -o out2 -f tex -f pdf --pdf-engine latex   # biblatex + biber
```

```markdown
Pairs are matched within 1 arcsec (Marshall and Treu 2006). Errors follow (Wall and Jenkins 2003, 12).

## References

Marshall, Phil, and Tommaso Treu. 2006. “Cross-Matching Catalogues of Sky Surveys.” *Astronomy & Astrophysics* 450: 123–30.
```

- **md, html, docx, odt, epub** use pandoc's citeproc and need `scireport[pandoc]` (without it: `E506`, exit 3). A
  `bibliography` value turns pandoc on by itself. `csl=` on `add_bibliography` picks the citation style.
- **tex and the LaTeX PDF** emit `\autocite{marshall2006}`, `\addbibresource{references.bib}` (the `.bib` is
  copied into `tex/`) and `\printbibliography`; the `latexmk` run in `--pdf-engine latex` calls `biber`, so the
  PDF shows `[1]` and `[2, p. 12]` (with `style='authoryear'`: `(Marshall and Treu 2006)`). It needs `biber` and
  the `biblatex` package. `latexmk report.tex` in `out/tex` rebuilds it by hand.
- **WeasyPrint PDF** printed the same author-year citations and reference list as the HTML (pandoc again).
- **`E212`**: a `[@key]` that the `.bib` does not hold, with the template line: `citation of 'nobody2020', which
  the bibliography does not have`. Only one bibliography per bundle (`E211`).

## Word, ODT and EPUB

Use for co-authors who edit in Word or LibreOffice, or to read on an e-reader. Needs `scireport[pandoc]`
(it bundles pandoc; without it `E506`, exit 3).

```bash
uv run scireport render crossmatch.scireport.zip -o office -f docx -f odt -f epub
uv run scireport render crossmatch.scireport.zip -o office -f docx --office-source html
```

```text
office/docx/report.docx   office/odt/report.odt   office/epub/report.epub   office/render-manifest.json
```

- **`--office-source md|html`**: what pandoc converts. `md` (default) keeps math as native Word equations,
  tables as Word tables and figures as embedded PNG. `html` converts the rendered HTML instead.
- **Styles.** The output is not templated and carries no CSS look: the navy cover, running header, chapter
  bands and fonts of the layout do not appear. Word styles come from a reference document:
  `--reference-doc styles.docx` (for `docx` and `odt`), or `reference_docx` in the layout's `layout.yaml`
  (the built-in layouts name none, so pandoc's own styles apply). Restyle once in Word and reuse it:

```bash
pandoc -o styles.docx --print-default-data-file reference.docx    # pandoc's default styles, to edit
uv run scireport render crossmatch.scireport.zip -o office -f docx --reference-doc styles.docx
```

  (`pandoc` here is the bundled binary: `python -c "import pypandoc; print(pypandoc.get_pandoc_path())"`.)
  Changing a font in the reference document's `word/styles.xml` showed up in `report.docx` here.
- `epub` has its own stylesheet; `--reference-doc` does not apply to it.
- Not carried over: the layout's page design (navy cover, running header and footer, chapter bands, colours,
  fonts). For a designed document hand out the PDF.

## Drive scireport from an agent with MCP

Use when an agent should write a bundle, check it and render it through tools instead of shell commands. Needs
`scireport[mcp]` (without it `E904`, exit 3). Print the configuration, merge it into the project's `.mcp.json`
yourself (scireport never writes that file, and a `.mcp.json` must not be committed if it holds tokens):

```bash
uv run scireport agent mcp-config                   # server is the installed `scireport`
uv run scireport agent mcp-config --uvx --ref main  # launched through uvx from the GitHub repository
```

```json
{
  "mcpServers": {
    "scireport": {
      "command": "scireport",
      "args": ["mcp", "serve", "--root", "."]
    }
  }
}
```

The server speaks MCP over stdio (`scireport mcp serve --root DIR`). Tools, in the order an agent should call them:

1. `list_templates`, `list_layouts` (and `list_preprocessors`, `describe_preprocessor`): what exists.
2. `describe_template(ref)`: the keys, kinds and table columns a template reads.
3. Write the bundle (a directory with `scireport.yaml`) with the agent's own file tools, under the root.
4. `validate_bundle(path)`: every problem at once, with code, key, JSON pointer, expected, found, hint.
5. `error_help(code)`: what a code means and how to fix it. Fix the file, go back to 4.
6. `render_bundle(path, output, formats=[...])`: writes under the root; nothing is written when invalid.
   (`inspect_bundle(path)` and `spec_schema()` complete the set.)

- **`--root` is the only directory the server reads or writes.** A path outside it, symbolic links followed, gives
  `E412`. Pre-processors that import code (`module:function`) are never allowed through MCP.
- **Problems come back as data, not as protocol errors**: `{"ok": false, "exit_code": 2, "issues": [...]}`, so the
  agent reads the codes and fixes the file. A missing PDF dependency is `exit_code` 3 in the result.
- The pages of this skill are served as resources (`skill://scireport/SKILL.md`, `skill://scireport/references/...`).

An in-memory test of the whole loop (`mcp` 2.x; this ran and printed the lines shown):

```python
import asyncio
from pathlib import Path

from mcp import Client
from scireport.agent.mcp_server import create_server

ROOT = Path('root').resolve()
BUNDLE = """\
scireport: '1.0'
meta: {title: Demo}
render: {template: generic@1, formats: [md]}
outline: [summary, results.n_items]
values:
  summary: Hello.
"""


async def call(client, tool, **arguments):
  return (await client.call_tool(tool, arguments)).structured_content


async def main():
  async with Client(create_server(ROOT)) as client:
    print([t.name for t in (await client.list_tools()).tools])
    print((await call(client, 'describe_template', ref='generic@1'))['title'])
    (ROOT / 'demo').mkdir()
    (ROOT / 'demo' / 'scireport.yaml').write_text(BUNDLE)
    checked = await call(client, 'validate_bundle', path='demo')
    print(checked['ok'], [(i['code'], i['pointer']) for i in checked['issues']])
    print((await call(client, 'error_help', code='E103'))['title'])
    fixed = BUNDLE + '  results.n_items: {kind: number, value: 3061, format: int}\n'
    (ROOT / 'demo' / 'scireport.yaml').write_text(fixed)
    print((await call(client, 'validate_bundle', path='demo'))['ok'])
    print(await call(client, 'render_bundle', path='demo', output='out', formats=['md']))
    print(await call(client, 'validate_bundle', path='../elsewhere'))


asyncio.run(main())
```

```text
['list_templates', 'describe_template', 'list_layouts', 'list_preprocessors', 'describe_preprocessor', 'spec_schema', 'error_help', 'inspect_bundle', 'validate_bundle', 'render_bundle']
Generic report
False [('E103', '/outline/1/key')]
Reference to a key that does not exist
True
{'ok': True, 'output': 'out', 'files': ['md/report.md', 'render-manifest.json'], 'warnings': []}
{'ok': False, 'exit_code': 2, 'issues': [{'code': 'E412', 'severity': 'error', 'message': "'../elsewhere' is outside the directory this server may use", 'hint': 'Give a path under the server root.'}]}
```

To talk to the real stdio server from Python use `StdioServerParameters(command='uv', args=['run', 'scireport',
'mcp', 'serve', '--root', 'root'])` as the argument of `Client(...)`.

## From a DataFrame and a matplotlib figure to a report

Use for the usual analysis script: a pandas summary, one plot, a few headline numbers. Bundles hold summaries,
not raw catalogues: aggregate first.

```python
import numpy as np
import pandas as pd

import scireport

rng = np.random.default_rng(0)
pairs = pd.DataFrame({
  'sep_arcsec': rng.rayleigh(0.3, 5000),
  'mag_r': rng.normal(20.5, 1.2, 5000),
})

bands = pairs.groupby(pd.cut(pairs['mag_r'], [14, 19, 20, 21, 22, 27]), observed=True).agg(
  n=('sep_arcsec', 'size'), median_sep=('sep_arcsec', 'median'),
).reset_index(names='mag_bin')
bands['mag_bin'] = bands['mag_bin'].astype(str)   # intervals are not a table type

with scireport.mplstyle():  # the matplotlib style of the report layout (default@1)
  fig, ax = scireport.figure(width=0.8, height=3.2)  # width: fraction of the page frame; height: inches
  ax.hist(pairs['sep_arcsec'], bins=50)
  ax.set_xlabel('separation [arcsec]')
  ax.set_ylabel('pairs')

report = scireport.Report('Cross-match report', authors=['Ada Example'], date='2026-01-15')
report.add_text('summary', 'Cross-match of **5000** pairs. The median separation is '
                '$\\tilde{s} \\approx 0.35$ arcsec.', format='markdown')
report.add_number('crossmatch.n_pairs', len(pairs), format='int', unit='pairs')
report.add_number('crossmatch.median_sep', float(pairs['sep_arcsec'].median()), format='.3f',
                  unit='arcsec')
report.add_table(
  'crossmatch.by_mag', bands, caption='Pairs per r-band magnitude bin.',
  columns=[
    {'name': 'mag_bin', 'label': 'r [mag]'},
    {'name': 'n', 'label': 'Pairs', 'format': 'int'},
    {'name': 'median_sep', 'label': 'Median separation', 'unit': 'arcsec', 'format': '.3f'},
  ],
)
report.add_figure('crossmatch.sep_hist', fig, alt='Histogram of match separations in arcsec.',
                  caption='Separation of matched pairs.')
report.set_outline([
  'summary',
  {'title': 'Results', 'md_file': 'results.md',
   'children': ['crossmatch.n_pairs', 'crossmatch.median_sep', 'crossmatch.by_mag',
                'crossmatch.sep_hist']},
])
report.set_render(template='generic@1', formats=['md', 'html'])
print(report.write('crossmatch.scireport.zip', overwrite=True))
```

```bash
uv run python make_report.py                                  # prints crossmatch.scireport.zip
uv run scireport validate crossmatch.scireport.zip            # valid: 0 error(s), 0 warning(s)
uv run scireport render crossmatch.scireport.zip -o out -f md -f html
```

- Keys are semantic dotted paths (`crossmatch.n_pairs`); a key cannot also be the prefix of another (`E102`) and
  cannot be added twice (`E104`). The `generic` template renders `outline` entries in order; a value that is
  not listed in the outline is `W401` (and `--strict` fails on it).
- `add_figure` stores PNG and PDF renditions and a sidecar of the data; `alt` is required. Draw inside
  `scireport.mplstyle()` and size with `scireport.figure()` so the plot matches the report (`mplstyle.md`).
- `add_table` takes a pandas DataFrame (the index is dropped), a pyarrow Table, a polars frame, a dict of columns
  or a list of row dicts; `columns` sets labels, units and number formats. NaN in `add_number` is stored as a
  missing number; infinity is an error.
- `report.write('x.scireport.zip')` writes one ZIP; any other name writes a directory bundle; `*.json` a single
  file. `data-file.md` lists every `add_*` method and value kind; `python-api.md` the signatures.

## A custom pre-processor in the consuming project

Use when the bundle should hold a figure or number that the project computes from a table at render time.
Pre-processors are called by registered name from the bundle (`preprocess:` block) and never run arbitrary code
by default. See `preprocessors.md` for ports, parameters, the cache and the built-in `core.*`/`astro.*` catalogue.

`myproj/steps.py`:

```python
import pyarrow as pa

from scireport.preprocess import Context, Port, preprocessor


@preprocessor(
  'myproj.row_count',
  version=1,
  inputs={'table': Port('table')},
  outputs={'count': Port('number')},
)
def row_count(ctx: Context, *, table: pa.Table, label: str = 'rows') -> dict[str, object]:
  """Count the rows of a table."""
  return {'count': {'kind': 'number', 'value': table.num_rows, 'unit': label}}
```

`report/scireport.yaml` (with `assets/tables/matches.csv` next to it):

```yaml
scireport: '1.0'
meta: {title: Matches}
render: {template: generic@1, formats: [md]}
outline: [matches.n_rows, matches.table]
values:
  matches.table:
    kind: table
    asset: assets/tables/matches.csv
preprocess:
  - name: myproj.row_count
    inputs: {table: matches.table}
    outputs: {count: matches.n_rows}
    params: {label: matches}
```

Make the name resolvable by registering the function with an entry point in the project's `pyproject.toml`
(installed package, no flags needed):

```toml
[project.entry-points."scireport.preprocessors"]
row_count = "myproj.steps:row_count"
```

```bash
uv run scireport preprocessors | grep myproj      # myproj.row_count@1   Count the rows of a table.
uv run scireport preprocess report                # runs the step; new files go to scireport-work/
uv run scireport render report -o out             # runs the steps first, then renders
```

The output is `**N rows:** 4 matches`. Without installing the package, name the function as
`name: myproj.steps:row_count` and pass `--allow-import` (with `PYTHONPATH` set so Python can import it).
That runs code from the data file, so use it only for files you trust. Not installed and not allowed is `E601`
(unknown name, with a "did you mean") or `E605` (`module:function` without `--allow-import`).
A released version is frozen: a change of behaviour is `version=2` registered beside version 1.

## Validate in a pre-commit hook and before a render in a Makefile

Use to keep an invalid data file out of the repository and to render only what changed.

`.pre-commit-config.yaml` (a local hook; exit 2 blocks the commit and prints the codes):

```yaml
repos:
  - repo: local
    hooks:
      - id: scireport-validate
        name: validate the report data file
        entry: uv run scireport validate report --strict
        language: system
        files: ^report/
        pass_filenames: false
```

`Makefile` (recipe lines start with a tab):

```make
SCIREPORT = uv run scireport
REPORT_FILES := $(shell find report -type f)

.PHONY: report
report: out/md/report.md

out/md/report.md: $(REPORT_FILES)
	$(SCIREPORT) validate report --strict
	$(SCIREPORT) render report -o out -f md -f html
```

`make` validates, then renders; a second `make` finds nothing to do; an invalid file stops `make` with exit 2
before anything is written. Both were run: the hook printed `Passed`, then `Failed`
with `E204 /unknown: Extra inputs are not permitted` after a stray key was added.

## If something fails

1. **Read the exit code.** `0` ok, `1` runtime failure (I/O, pandoc or the PDF engine), `2` the data file,
   template, layout or export is invalid, `3` a system dependency or extra is missing (the message says how to
   install it: pango, TeX Live, `scireport[pandoc]`, `scireport[mcp]`). See `cli.md`.
2. **Get every problem at once:** `uv run scireport validate X --json`. Each issue has `code`, `key`, `pointer`
   (a JSON pointer into the data file), `expected`, `found`, `location` (template `file:line`) and `hint`.
   Fix them all, then validate again. `--strict` also fails on warnings (`W4xx`...).
3. **Look the code up:** `uv run scireport spec errors --json` (a list of `{code, severity, title, ...}`), the MCP
   tool `error_help`, or `errors.md`.
4. **Check the bundle itself:** `uv run scireport inspect X --verify` (asset hashes and sizes; `E40x`).
5. **PDF only:** retry with the other engine (`--pdf-engine latex` or `weasyprint`); an `E902` carries the
   engine's own messages and the LaTeX `file:line`.

Never edit files under `out/`; change the data file, the template or the layout, and render again.
