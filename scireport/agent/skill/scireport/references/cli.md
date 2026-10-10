# Command line

`scireport` is a Typer program. Every command takes `--help`. A bundle (`SOURCE`) is a directory
holding `scireport.yaml`, a `.scireport.zip` archive, or a manifest file. Run it with
`uv run scireport ...` (or `scireport ...` where it is on the path).

## Command map

| Task | Command |
|---|---|
| start a data file that already validates | `scireport new DEST [--template T] [--layout L]` |
| check a bundle, change nothing | `scireport validate SOURCE [--json] [--strict]` |
| write md, html, tex, pdf, docx, odt, epub | `scireport render SOURCE -o OUT -f md -f html ...` |
| freeze a bundle into one reproducible ZIP | `scireport pack SOURCE -o x.scireport.zip` |
| unpack a ZIP, checking every hash | `scireport unpack SOURCE -o DIR` |
| see what a bundle holds (values, kinds, integrity) | `scireport inspect SOURCE [--json] [-k KEY]` |
| run the pre-processing steps of a bundle | `scireport preprocess SOURCE` |
| list or describe pre-processors | `scireport preprocessors [NAME] [--json]` |
| LaTeX tables, figures and `\newcommand` numbers for a paper | `scireport export tex SOURCE -o DIR` |
| list or describe templates, layouts | `scireport templates [REF] [--json]`, `scireport layouts [REF] [--json]` |
| the data-file specification | `scireport spec schema`, `spec kinds`, `spec errors`, `spec migrate`, `spec version` |
| matplotlib style of a layout | `scireport mplstyle path\|show\|palette [LAYOUT]` |
| install this skill, print the MCP snippet | `scireport agent install-skill -d DIR`, `scireport agent mcp-config` |
| serve the tools over MCP | `scireport mcp serve --root DIR` (needs `scireport[mcp]`) |

`scireport new /tmp/x/my-report` writes `my-report/scireport.yaml` with a summary text, a number and a
table; it validates and renders as is. Edit it instead of writing a data file from nothing.

## Global options

Written before the command: `scireport --log-level DEBUG render ...`.

| Option | Meaning |
|---|---|
| `--log-level` | `DEBUG`, `INFO` (default), `WARNING`, `ERROR`: the console level. |
| `--log-file PATH` | Also write a plain-text log to PATH. |
| `--version` | Print the version and exit. |

Logs go to **stderr**; a command's **result** goes to **stdout**. `scireport render ... 2>/dev/null` prints
only the written file names, `--json` prints only JSON. Use `--log-level WARNING` to silence the progress
lines (and the WeasyPrint step lines).

## `--json`

Most commands take `--json`: the result becomes one JSON document on stdout (indent 2). Errors become
`{"ok": false, "issues": [...]}` on stdout with the same exit code, so a script reads one stream.

`validate --json` on a valid bundle:

```json
{"ok": true, "strict": false, "exit_code": 0, "counts": {"errors": 0, "warnings": 0}, "issues": []}
```

(the real output is indented). On a bundle whose outline names a key that is not in `values`
(exit code 2; this shape, without `counts`, is the same for any failing command):

```json
{
  "ok": false,
  "issues": [
    {
      "code": "E103",
      "severity": "error",
      "message": "no value with key 'results.n_items'",
      "pointer": "/outline/1/children/0/key",
      "key": "results.n_items",
      "hint": "Did you mean 'results.n_itemz'?"
    }
  ]
}
```

Other fields of an issue, when they apply: `expected`, `found`, `file`, `line` (a template position).
Without `--json`, `validate` prints one line per issue and a verdict (`valid: 0 error(s), 1 warning(s)`).

`render --json` lists what was written (paths relative to the output directory) and the warnings:

```json
{
  "ok": true,
  "output": "out",
  "files": ["html/report.html", "md/report.md", "render-manifest.json", "tex/report.tex", "..."],
  "warnings": []
}
```

`inspect --json` (shortened):

```json
{
  "spec": "1.0", "form": "directory", "source": "my-report",
  "meta": {"title": "Untitled report", "authors": [{"name": "Your Name"}], "language": "en", "...": "..."},
  "render": {"template": "generic@1", "formats": ["md", "html"], "options": {}},
  "counts": {"number": 1, "table": 1, "text": 1},
  "values": [{"key": "results.n_items", "kind": "number", "summary": "3061 items", "assets": []}],
  "assets": {"count": 0, "bytes": 0},
  "verified": true, "issues": [], "ok": true
}
```

`inspect -k KEY` prints the canonical value stored at KEY (`{"kind": "number", "value": 3061, ...}`).

`templates generic@1 --json` (a template that reads any bundle has no `fields`; `dynamic_keys` says so):

```json
{
  "ref": "generic@1", "title": "Generic report", "spec": ">=1.0,<2.0", "origin": "builtin",
  "formats": ["md", "html", "tex"], "dynamic_keys": true, "fields": []
}
```

For `templates kitchen-sink@1 --json`, `fields` lists what to put in the bundle, one object per key
pattern (`*` is one key segment); `columns` and `renditions` are filled for tables and figures:

```json
{"key": "summary.metrics", "kinds": ["metrics"], "required": true, "description": "",
 "columns": [], "renditions": []}
```

`layouts NAME --json` gives `formats`, `pdf_engines` and `options` (name, type, default, choices,
description). `preprocessors NAME --json` is in `preprocessors.md`.

## How validation reports problems

`validate` (and `render`, which validates first and writes nothing on failure) reports **every** problem in
one pass, not the first. Each issue has a stable code (`E1xx`-`E3xx` the data file, `E4xx` bundles and assets,
`E5xx` versions and pandoc, `E6xx` pre-processing, `E7xx` templates and layouts, `E8xx` rendering and
exports, `E9xx` PDF engines; `Wxxx` are warnings; see `errors.md`), the key, the JSON pointer, expected
and found values, the template `file:line` and a "did you mean" hint. Errors give exit code 2. A warning
alone does not fail:

```console
$ scireport validate warn          # outline lists only a.one, but a.two is in values
W401 generic@1: /values/a.two: value 'a.two' is in the bundle but the template never renders it
valid: 0 error(s), 1 warning(s)    # exit 0
$ scireport validate warn --strict
invalid: 0 error(s), 1 warning(s)  # exit 2
```

`--strict` turns warnings into errors (in `validate` and `render`). `--no-render` skips the in-memory
render that finds what only a render shows (math the renderer cannot draw, a missing component).
Run `validate` with the formats you will render (`-f tex`) so that format's checks run too.

## What `render` writes

One folder per format next to `render-manifest.json` (hashes, versions and engines used):

```console
$ scireport render my-report -o out -f md -f html -f tex
out/
  render-manifest.json
  md/report.md            (index.md plus chapter files when the template names md_file)
  html/report.html        (one self-contained file)
  tex/report.tex          (a LaTeX project: .sty, latexmkrc, fonts/, figures/)
```

`-f pdf` adds `pdf/report.pdf`; `-f docx`, `-f odt`, `-f epub` add `docx/report.docx` and so on. With no
`-f` the formats are the bundle's `render.formats`, else every text format (md, html, tex) that the
template and layout support. `--flat` writes a single format straight into the
directory (`out/report.md` and `out/render-manifest.json`, no `md/` folder). Output is deterministic; do not
edit it, change the bundle, template or layout and render again.

Choose parts with `-t generic@1` (template) and `-l modern@1` (layout); a bare name means the newest
version. Both may be directories. Defaults come from the bundle's `render` block, then `generic@1` and
`default@1`.

### Layout options

`-O name=value`, repeatable; names and types are in `scireport layouts NAME`. Bools are `true`/`false`.
Priority: layout default, then the bundle's `render.options`, then `-O`. An unknown name or a value outside
the choices is `E806`:

```console
$ scireport render my-report -o out -f md -f html -O toc=false -O cover=false
$ scireport render my-report -o out -f md -O paper=foo
E806 default@1: option paper must be one of a4, letter, got 'foo'          # exit 2
```

## Exit codes

<!-- generated:exit-codes -->
| Code | Meaning |
|---|---|
| 0 | Success. |
| 1 | A failure that is not a problem in the data file (I/O error, pandoc or a PDF engine failed, `agent install-skill --check` found a difference). |
| 2 | The data file, template, layout or an export is invalid (errors; with `--strict` also warnings). |
| 3 | A system dependency or optional extra is missing (pango, TeX Live, `scireport[pandoc]`, `scireport[mcp]`); the message says how to install it. |
<!-- /generated -->

## Choices: engines and formats

The values each `--*-engine` option accepts, first is the default. The same choices can be set in the
bundle's `render` block (`pdf_engine`, `latex_engine`, `markup_engine`, `math_renderer`); the command line
wins.

<!-- generated:engines -->
| Choice | Values (first is the default) |
|---|---|
| `--pdf-engine` | `weasyprint`, `latex` |
| `--latex-engine` | `lualatex`, `xelatex`, `pdflatex` |
| `--markup-engine` | `mistletoe`, `pandoc` |
| `--math-renderer` | `mathtext`, `usetex` |
| office formats | `docx`, `odt`, `epub` |
| `--office-source` | `md`, `html` |
<!-- /generated -->


## PDF engines

A PDF is never a default format: ask with `-f pdf`.

| Engine | How | Needs on the system |
|---|---|---|
| `weasyprint` (default) | prints the HTML | `scireport[pdf]` and pango (`apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0`; `brew install pango`) |
| `latex` | compiles the LaTeX project with `latexmk` | TeX Live: `latexmk` and the TeX engine (`lualatex` by default; `--latex-engine xelatex\|pdflatex`); `biber` when the bundle has a `bibliography` value |

```console
$ scireport render my-report -o out -f pdf                      # WeasyPrint
$ scireport render my-report -o out -f pdf --pdf-engine latex   # latexmk + lualatex
```

A missing dependency exits with code **3** and an install hint, never a traceback:

```console
$ scireport render my-report -o out -f pdf --pdf-engine latex     # latexmk not installed
E901 the LaTeX PDF engine needs latexmk, which is not installed or not on the path. Install TeX Live
(https://tug.org/texlive/): sudo apt install texlive-latex-extra texlive-luatex texlive-xetex latexmk
texlive-fonts-recommended on Debian or Ubuntu; brew install --cask mactex-no-gui on macOS; ...   # exit 3
```

A failed compile is `E902` (exit 1) and carries the `file:line` of each LaTeX error.
`minimal@1` has no PDF engine (`E903`, exit 2); use `default@1` or `modern@1`. Only the `md`, `html` and `tex`
outputs are byte-identical across machines; a PDF is deterministic on one machine and one set of library
versions.

## Word, ODT and EPUB (pandoc)

`-f docx`, `-f odt` and `-f epub` convert the rendered report with pandoc. They need `scireport[pandoc]`
(it bundles a pandoc binary; without it: `E506`, exit 3; a failed conversion: `E507`, exit 1).
They are not templated: the conversion reads
the Markdown render (default) or, with `--office-source html`, the HTML render.

```console
$ scireport render my-report -o out -f docx -f epub
$ scireport render my-report -o out -f docx --office-source html
$ scireport render my-report -o out -f docx --reference-doc styles.docx   # styles of docx and odt
```

`--reference-doc` is a `reference.docx` whose styles `docx` and `odt` use; a layout can also name one
(`reference_docx` in `layout.yaml`). The built-in layouts name none, so pandoc's own styles apply.

## Markdown engine

Prose in templates and `text` values is Markdown. The default converter, mistletoe, is pure Python and
understands a documented subset (no headings, footnotes or raw HTML inside prose: `W701`). To convert with
pandoc instead (footnotes, richer tables), and only then, pass `--markup-engine pandoc` (or set
`render.markup_engine`). pandoc never switches on by itself, so output does not depend on what is installed.

## `export tex`: numbers, tables and figures for a paper

`scireport export tex SOURCE -o paper/generated` writes files a manuscript `\input`s, so every number in the
paper comes from the data file. It does not render the report.

| File | Holds |
|---|---|
| `numbers.tex` | one `\newcommand{\Name}{value}` per `number` value |
| `tab_<key>.tex` | a `table` value as a `table` float with caption and `\label{tab:<key>}` (`booktabs`; over 40 rows `longtable`) |
| `fig_<key>.tex` and `fig_<key>.pdf` (or `.png`) | a `figure` value as a `figure` float with `\label{fig:<key>}` and the file it includes (PDF preferred) |

The macro name is the key in CamelCase with digits spelled out: `crossmatch.n_pairs` is `\CrossmatchNPairs`,
`run2.median_sep` is `\RunTwoMedianSep`. The value is typeset with unit and uncertainty. `--prefix Xm` puts
letters (only letters) in front: `\XmCrossmatchNPairs`. Two keys that give the same name are `E807` (exit 2;
rename one key, or export them separately with different prefixes).

```console
$ scireport export tex qa.scireport.zip -o paper/gen -k 'crossmatch.*' -k run2.median_sep
fig_crossmatch.separations.pdf
fig_crossmatch.separations.tex
numbers.tex
tab_crossmatch.summary.tex
```

`numbers.tex` from that run:

```tex
% crossmatch.n_pairs
\newcommand{\CrossmatchNPairs}{12,345~pairs}
% run2.median_sep
\newcommand{\RunTwoMedianSep}{0.31 \ensuremath{\pm} 0.02~arcsec}
```

- `-k/--keys`: keys to export; `*` and `?` match (`'crossmatch.*'`; quote it). Repeat the option or
  separate with commas. Default: every number, table and figure. A pattern that matches nothing is `E103`.
- `--bare`: a bare `tabular` and `\includegraphics`, with no float, caption or label, for your own wrapper.
- `--graphics-prefix`: the path written before the figure file, **from the directory LaTeX runs in**.
  Default: the output directory name and a slash (`gen/`), right when LaTeX runs in the parent (`paper/`).
- `--max-rows N` cuts every table. `--json` prints `{"ok", "output", "files", "macros"}`.

Use them in the paper (this compiles with plain `article`):

```tex
\usepackage{booktabs,longtable,graphicx}   % the "Needs:" line at the top of each fragment
\input{gen/numbers.tex}
We matched \CrossmatchNPairs, median separation \RunTwoMedianSep.
\input{gen/tab_crossmatch.summary.tex}
\input{gen/fig_crossmatch.separations.tex}
```

Regenerate after the bundle changes and commit the result; never edit the generated files.

## Every command and option

Generated from the code, so it matches the installed version.

<!-- generated:cli -->
### `scireport agent`

The skill and MCP configuration for coding agents.

### `scireport agent install-skill`

Install the scireport skill into a project's skills directory.

Writes DEST/scireport/SKILL.md and DEST/scireport/references/. The installed copy replaces an
earlier one. With --check nothing is written: the exit code is 0 when the installed copy is
identical to the skill of this version, and 1 when it is missing or differs.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `--dest` / `-d` | path |  | The skills directory of the project (for example .claude/skills). |
| `--check` | flag |  | Only compare the installed copy with this version; exit 1 when it differs. |
| `--json` | flag |  | Print the result as JSON. |

### `scireport agent mcp-config`

Print a .mcp.json snippet that starts the scireport MCP server.

Merge it into the project's .mcp.json yourself; scireport never writes that file, because a
.mcp.json may hold tokens and must not be committed by a tool.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `--root` | str | `.` | The directory the server may read and write. |
| `--uvx` | flag |  | Launch through uvx from the GitHub repository (nothing to install first). |
| `--ref` | str | `main` | With --uvx: the git tag or branch to install. |

### `scireport export`

Export values of a bundle for other documents.

### `scireport export tex SOURCE`

Write tab_<key>.tex, fig_<key>.tex and numbers.tex for a manuscript to \input.

numbers.tex holds one \newcommand per number value (CamelCase key, optional prefix); two keys
with the same macro name are an error. Figures are written next to their fragment.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `SOURCE` | argument |  | A bundle: directory, .zip archive or manifest file. |
| `--output` / `-o` | path |  | Directory for the fragments (for example paper/generated). |
| `--keys` / `-k` | str (repeat) |  | Keys to export; * and ? match several (crossmatch.*). Repeat, or separate with commas. Default: every number, table and figure. |
| `--prefix` | str | `` | Letters in front of every macro name in numbers.tex. |
| `--bare` | flag |  | Write a bare tabular and \includegraphics, without float or caption. |
| `--graphics-prefix` | str |  | Path written before a figure file in \includegraphics, from the directory LaTeX runs in (default: the name of the output directory and a slash). |
| `--max-rows` | int range |  | Cut every table to this many rows. |
| `--json` | flag |  | Print the result as JSON. |
| `--max-size` | int range | `1024` | Size cap of a ZIP bundle, in MiB (uncompressed). |

### `scireport inspect SOURCE`

Show what a bundle contains: metadata, every value and the integrity check.

Exit code 0 when the bundle is sound, 2 when it is invalid or fails verification.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `SOURCE` | argument |  | A bundle: directory, .zip archive or manifest file. |
| `--json` | flag |  | Print the result as JSON (for agents). |
| `--verify` / `--no-verify` | flag | `True` | Check every asset hash and size. |
| `--key` / `-k` | str |  | Print the canonical value stored at KEY. |
| `--max-size` | int range | `1024` | Size cap of a ZIP bundle, in MiB (uncompressed). |

### `scireport layouts [REF]`

List the layouts that can be used (built in and from plugins), or describe one.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `REF` | argument |  | Describe one layout (name, name@version or a directory). |
| `--json` | flag |  | Print the result as JSON (for agents). |

### `scireport mcp`

The MCP server.

### `scireport mcp serve`

Serve the scireport tools over the Model Context Protocol (standard input and output).

Needs scireport[mcp]. Logs go to standard error; standard output belongs to the protocol.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `--root` | directory | `.` | The only directory the server may read and write. |

### `scireport mplstyle`

The matplotlib style and palette of a layout (figures that look like the report).

### `scireport mplstyle palette [LAYOUT]`

Print the palette of a layout: colours, chart roles, fonts and page geometry.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `LAYOUT` | argument |  | A layout: name, name@version or a directory (default: default). |
| `--json` | flag |  | Print the result as JSON. |

### `scireport mplstyle path [LAYOUT]`

Print the path of the .mplstyle file of a layout (use it as plt.style.use(path)).

| Option | Type | Default | Meaning |
|---|---|---|---|
| `LAYOUT` | argument |  | A layout: name, name@version or a directory (default: default). |
| `--json` | flag |  | Print the result as JSON. |

### `scireport mplstyle show [LAYOUT]`

Print the contents of the .mplstyle file of a layout.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `LAYOUT` | argument |  | A layout: name, name@version or a directory (default: default). |

### `scireport new DEST`

Write a starter scireport.yaml that already reads as a valid data file.

With --template, every required field of that template gets a placeholder value; values that
need a file (figures, images, attachments) are listed so that you can add them.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `DEST` | argument |  | Directory to create (it becomes a directory bundle). |
| `--title` | str | `Untitled report` | The report title. |
| `--template` / `-t` | str |  | Template whose required fields get placeholders (default: generic). |
| `--layout` / `-l` | str |  | Layout to write into the render block. |
| `--force` | flag |  | Replace the scireport.yaml of an existing directory. |
| `--json` | flag |  | Print the result as JSON. |

### `scireport pack SOURCE`

Pack a bundle into a byte-reproducible ZIP with a JSON manifest.

A hand-authored directory (YAML manifest, asset references without hashes) is completed:
hashes and sizes are computed and the manifest is written as canonical JSON. Files that no
value references are left out.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `SOURCE` | argument |  | A bundle: directory, .zip archive or manifest file. |
| `--output` / `-o` | path |  | Destination; default <name>.scireport.zip next to SOURCE. |
| `--force` | flag |  | Replace the destination if it exists. |
| `--max-size` | int range | `1024` | Size cap of a ZIP bundle, in MiB (uncompressed). |
| `--json` | flag |  | Print the result as JSON (for agents). |

### `scireport preprocess SOURCE`

Run the pre-processing steps of a bundle: figures and tables from its data.

The plan is checked first and every problem is reported at once; nothing runs if there is one.
New files go to the work directory; SOURCE is left untouched unless --write-back is given.
Results are cached by content, so running again is a no-op.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `SOURCE` | argument |  | A bundle: directory, .zip archive or manifest file. |
| `--output` / `-o` | path |  | Write the pre-processed bundle here (directory, .zip). |
| `--write-back` | flag |  | Replace SOURCE with the pre-processed bundle (steps stay in it). |
| `--work-dir` | path | `scireport-work` | Where the new figures and tables and the run record go. |
| `--layout` / `-l` | str |  | Layout whose style the figures use. |
| `--seed` | int |  | Base seed; each step derives its own. |
| `--cache-dir` | path |  | Pre-processor cache (default: $SCIREPORT_CACHE_DIR or the XDG cache). |
| `--no-cache` | flag |  | Neither read nor write the cache. |
| `--allow-import` | flag |  | Let a step name module:function (imports and runs that code). Only for files you trust. |
| `--json` | flag |  | Print the result as JSON (for agents). |
| `--max-size` | int range | `1024` | Size cap of a ZIP bundle, in MiB. |

### `scireport preprocessors [NAME]`

List the registered pre-processors, or describe one.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `NAME` | argument |  | Show one pre-processor: its ports and parameters. |
| `--json` | flag |  | Print the result as JSON (for agents). |

### `scireport render SOURCE`

Render a bundle to Markdown, HTML, a LaTeX project and/or a PDF.

Each format goes to its own folder of the output directory (md/, html/, tex/, pdf/), next to
render-manifest.json. A PDF needs system libraries: pango for --pdf-engine weasyprint, TeX Live
for --pdf-engine latex (exit code 3 when they are missing). Nothing is written when validation
or rendering finds an error.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `SOURCE` | argument |  | A bundle: directory, .zip archive or manifest file. |
| `--output` / `-o` | path |  | Directory to write the outputs to. |
| `--template` / `-t` | str |  | Template: name, name@version or a directory. |
| `--layout` / `-l` | str |  | Layout: name, name@version or a directory. |
| `--format` / `-f` | str (repeat) |  | Output format: md, html, tex, pdf, docx, odt or epub (repeat for several). |
| `--option` / `-O` | str (repeat) |  | Layout option as name=value (repeat for several). |
| `--pdf-engine` | str |  | How a PDF is made: weasyprint, latex (default weasyprint). |
| `--latex-engine` | str |  | TeX engine of the LaTeX project and the PDF (default lualatex). |
| `--markup-engine` | str |  | Markdown converter: mistletoe (default) or pandoc (needs scireport[pandoc]). |
| `--office-source` | str |  | What docx, odt and epub are converted from: md (default) or html. |
| `--reference-doc` | path |  | A reference.docx whose styles docx and odt use (else the layout's). |
| `--math-renderer` | str |  | Math renderer for HTML: mathtext or usetex. |
| `--md-split` / `--no-md-split` | flag |  | Split Markdown by chapter md_file (default: when the template names files). |
| `--flat` | flag |  | Write one format straight into the directory. |
| `--strict` | flag |  | Treat warnings as errors. |
| `--json` | flag |  | Print the result as JSON (for agents). |
| `--preprocess` / `--no-preprocess` | flag | `True` | Run the bundle's pre-processing steps first (default). |
| `--allow-import` | flag |  | Let a step name module:function (imports and runs that code). Only for files you trust. |
| `--cache-dir` | path |  | Pre-processor cache directory. |
| `--max-size` | int range | `1024` | Size cap of a ZIP bundle, in MiB (uncompressed). |

### `scireport spec`

Inspect the data-file specification.

### `scireport spec errors`

Print the error-code catalogue (the page docs/errors.md is generated from it).

| Option | Type | Default | Meaning |
|---|---|---|---|
| `--output` / `-o` | path |  | Write the page here instead of stdout. |
| `--json` | flag |  | Print the codes as JSON. |

### `scireport spec kinds`

List the value kinds with their fields.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `--json` | flag |  | Print as JSON. |

### `scireport spec migrate SOURCE`

Migrate a manifest to a spec version (pure dict-to-dict; the input is not changed).

| Option | Type | Default | Meaning |
|---|---|---|---|
| `SOURCE` | argument |  | A manifest file (.json or .yaml). |
| `--output` / `-o` | path |  | Write the migrated manifest here. |
| `--to` | str | `1.0` | Target spec version. |

### `scireport spec schema`

Print the JSON Schema of the manifest (generated from the pydantic models).

| Option | Type | Default | Meaning |
|---|---|---|---|
| `--output` / `-o` | path |  | Write the schema here instead of stdout. |

### `scireport spec version`

Print the newest spec version this scireport reads and writes.

### `scireport templates [REF]`

List the templates that can be used (built in and from plugins), or describe one.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `REF` | argument |  | Describe one template (name, name@version or a directory). |
| `--json` | flag |  | Print the result as JSON (for agents). |

### `scireport unpack SOURCE`

Unpack a bundle into a directory (manifest plus assets), checking every hash on the way.

| Option | Type | Default | Meaning |
|---|---|---|---|
| `SOURCE` | argument |  | A bundle: directory, .zip archive or manifest file. |
| `--output` / `-o` | path |  | Destination directory; default <name>.scireport/. |
| `--force` | flag |  | Replace the destination if it exists. |
| `--max-size` | int range | `1024` | Size cap of a ZIP bundle, in MiB (uncompressed). |
| `--json` | flag |  | Print the result as JSON (for agents). |

### `scireport validate SOURCE`

Check a bundle against a template and a layout; nothing is written.

Reports every problem at once, each with a stable code, the key, the template line and a
suggestion. Exit code 0: valid; 2: errors (with --strict also warnings).

| Option | Type | Default | Meaning |
|---|---|---|---|
| `SOURCE` | argument |  | A bundle: directory, .zip archive or manifest file. |
| `--template` / `-t` | str |  | Template: name, name@version or a directory. |
| `--layout` / `-l` | str |  | Layout: name, name@version or a directory. |
| `--format` / `-f` | str (repeat) |  | Output format: md, html, tex, pdf, docx, odt or epub (repeat for several). |
| `--option` / `-O` | str (repeat) |  | Layout option as name=value (repeat for several). |
| `--markup-engine` | str |  | Markdown converter: mistletoe (default) or pandoc (needs scireport[pandoc]). |
| `--office-source` | str |  | What docx, odt and epub are converted from: md (default) or html. |
| `--strict` | flag |  | Treat warnings as errors. |
| `--json` | flag |  | Print the result as JSON (for agents). |
| `--render` / `--no-render` | flag | `True` | Also render in memory to find what only a render shows. |
| `--preprocess` / `--no-preprocess` | flag | `True` | Run the bundle's pre-processing steps first (default). |
| `--allow-import` | flag |  | Let a step name module:function (imports and runs that code). Only for files you trust. |
| `--cache-dir` | path |  | Pre-processor cache directory. |
| `--max-size` | int range | `1024` | Size cap of a ZIP bundle, in MiB (uncompressed). |
<!-- /generated -->
