# Command line

`scireport` is one command with subcommands. Every command exits with 0 (success), 1 (failure that is not a
validation problem), 2 (the data file, template or layout is invalid) or 3 (a system dependency or an extra is
missing); the codes are explained on [Error codes](errors.md). Logs go to standard error; a command's result goes to standard
output, and `--json` (on the commands agents use) prints it as JSON.

## Exit codes

<!-- generated:exit-codes -->
| Code | Meaning |
|---|---|
| 0 | Success. |
| 1 | A failure that is not a problem in the data file (I/O error, pandoc or a PDF engine failed, `agent install-skill --check` found a difference). |
| 2 | The data file, template, layout or an export is invalid (errors; with `--strict` also warnings). |
| 3 | A system dependency or optional extra is missing (pango, TeX Live, `scireport[pandoc]`, `scireport[mcp]`); the message says how to install it. |
<!-- /generated -->

## Choices a render can make

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

## Commands

Every command with its arguments and options, generated from the Typer application.

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

Print the error-code catalogue (the same codes the documentation site lists).

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

Reports every problem it can find at once, each with a stable code, the key, the template line
and a suggestion. A problem in the data file itself (the spec stage) stops the template checks
that need its values, so they appear after it is fixed. Both stages print on stdout in the same
form. Exit code 0: valid; 2: errors (with --strict also warnings).

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

## Help text as printed

The same commands as `scireport COMMAND --help` prints them.

```{eval-rst}
.. llms-txt-ignore-start
```

```{typer} scireport.cli:app
:prog: scireport
:make-sections:
:show-nested:
:width: 100
:preferred: text
```

```{eval-rst}
.. llms-txt-ignore-end
```
