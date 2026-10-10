---
name: scireport
description: Generate scientific reports with the scireport engine. One data file (a report bundle with a manifest plus tables, figures and text) is rendered through a template and a layout to Markdown for language models, HTML, LaTeX and PDF for people, and with pandoc to Word, ODT and EPUB. Also exports LaTeX fragments (tables, figures, a numbers.tex of macros) for manuscripts. Use whenever a project must generate, validate or debug a report, write a report data file, add a pre-processor or figures in the shared matplotlib style, send numbers to a paper, or decode a scireport error code (E1xx to E9xx, W4xx to W9xx). Covers the CLI, the Python API, the MCP server, templates, layouts and recipes.
---

# scireport

scireport is a standalone report engine. **One data file** (a *report bundle*), **one template**
(structure) and **one layout** (look) go in; Markdown, HTML, LaTeX and PDF come out (Word, ODT and
EPUB through pandoc). The same bundle gives a Markdown file that a language model reads and a PDF
that people read. Output is deterministic: same inputs and versions, byte-identical files.

## Install

Install from the public repository, never from a local path:

```bash
uv add "scireport @ git+https://github.com/nmcardoso/scireport"
uv add "scireport[pdf,pandoc,mcp] @ git+https://github.com/nmcardoso/scireport"   # extras
```

Extras: `pdf` (WeasyPrint; needs pango on the system), `pandoc` (bundled pandoc binary), `astro`
(HEALPix sky maps), `mcp` (the MCP server). LaTeX PDFs need TeX Live (`latexmk`, `lualatex`,
`biber`). A missing system dependency exits with code 3 and prints how to install it.

## The workflow

1. **Write the data file.** From Python: `Report(...)` and its `add_*` methods, then
   `report.write('x.scireport.zip')`. By hand: a directory with `scireport.yaml`
   (`scireport new my-report` writes a starter that already validates).
2. **Validate.** `scireport validate x.scireport.zip --json` reports *every* problem at once, each
   with a stable code, the key, a JSON pointer, expected and found values and a hint. Fix, repeat.
3. **Render.** `scireport render x.scireport.zip -o out -f md -f html -f pdf`. Nothing is written
   when validation fails. `out/render-manifest.json` records hashes and tool versions.

Never edit generated output (`out/`); change the data file, the template or the layout and render
again.

## What to read next

| You need to ... | Read |
|---|---|
| write or read a data file: manifest blocks, keys, value kinds, assets, YAML rules | `references/data-file.md` |
| call scireport from Python: `Report`, `render_bundle`, `export_tex`, errors | `references/python-api.md` |
| run a command and know its options and exit codes | `references/cli.md` |
| pick or write a template or a layout, use components and filters | `references/templates-and-layouts.md` |
| turn a table into a figure or a summary table inside the bundle | `references/preprocessors.md` |
| draw matplotlib figures in the report's style | `references/mplstyle.md` |
| understand an error or warning code | `references/errors.md` |
| do a common job end to end (Markdown for LLMs plus one PDF, CI, citations, paper numbers) | `references/recipes.md` |

## Rules that save time

- **The data file is the contract.** Keys are semantic dotted paths (`crossmatch.n_pairs`); the
  *kind* of a value (`number`, `table`, `figure`, ...) lives in the value, not in the key.
  Bundles hold summaries, not raw catalogues.
- **Describe before you write.** `scireport templates NAME --json` lists the keys, kinds and
  table columns a template reads; build the bundle to match, then validate.
- **Use `--json` and exit codes in scripts.** 0 ok, 1 runtime failure, 2 invalid, 3 missing
  dependency. Look a code up with `scireport spec errors --json` or the MCP tool `error_help`.
- **Optional pieces never switch on by themselves.** pandoc is used only with
  `--markup-engine pandoc`, a `bibliography` value, or a `docx`/`odt`/`epub` format, so output
  does not depend on what happens to be installed.
- **Layouts and templates are versioned and frozen** (`default@1`). A look change is a new
  version, so a bundle that names `default@1` renders the same years later. `scireport pack`
  pins the versions it resolved.
- **Agents with MCP:** `scireport agent mcp-config` prints the `.mcp.json` snippet; the server
  reads and writes only under `--root`. The pages of this skill are its resources.

This page and the references are installed with `scireport agent install-skill --dest
.claude/skills` and are generated in part from the code, so they match the installed version.
