# Error and warning codes

Every problem scireport reports has a stable code, a one-line meaning and a "what to do" text. Look the
code up below, fix the cause, and run `scireport validate` again.

## How an issue looks

An issue has these parts (the JSON keys of `--json`; absent parts are left out):

| Part | Meaning |
|---|---|
| `code` | `E` plus three digits for an error, `W` plus three digits for a warning. |
| `severity` | `error` or `warning`. |
| `message` | What is wrong, in one sentence. |
| `pointer` | JSON pointer into the data file, for example `/outline/0/children/0/key`. |
| `key` | The value key involved, for example `run.count`. |
| `expected`, `found` | What was required and what is there, with units where they apply. |
| `hint` | A repair, often a "did you mean" spelling. |
| `location` | `file:line` of the template or layout that caused it. |

A real run on a hand-authored `scireport.yaml` whose outline names two keys that are not under `values`:

```console
$ scireport validate demo/ --json
{
  "ok": false,
  "issues": [
    {
      "code": "E103",
      "severity": "error",
      "message": "no value with key 'run.count'",
      "pointer": "/outline/0/children/0/key",
      "key": "run.count",
      "hint": "Did you mean 'run.n'?"
    },
    {
      "code": "E103",
      "severity": "error",
      "message": "no value with key 'run.nn'",
      "pointer": "/outline/0/children/1/key",
      "key": "run.nn",
      "hint": "Did you mean 'run.n'?"
    }
  ]
}
$ echo $?
2
```

Without `--json` each issue is one log line: `E103 /outline/0/children/0/key: no value with key
'run.count'. Did you mean 'run.n'?`.

## Aggregation, severity and exit codes

- Problems are collected, not raised one by one: one run reports every problem it can find. The manifest
  structure (E1xx to E4xx on the file itself) is checked first; the checks that need a template and a layout
  (E105 to E106, E207 to E210, E3xx, E7xx) follow once the file parses. So fix what is shown and run again:
  a second round may show issues that the first could not reach.
- `E` is an error: `validate` and `render` fail. `W` is a warning: the output is still written. With
  `--strict` a warning also fails.
- Exit codes: `0` success; `1` a failure that is not a problem in the data file (I/O, pandoc or a PDF engine
  failed); `2` the data file, template or layout is invalid (also a warning under `--strict`); `3` a system
  dependency or optional extra is missing (pango, TeX Live, `scireport[pandoc]`, `scireport[mcp]`).

## Looking a code up

- Here: the table at the end of this page has the meaning and the "what to do" of every code.
- `scireport spec errors --json` lists every code with its severity and title.
- MCP tool `error_help` (and `scireport.agent.catalogue.error_help(code)` in Python) returns the meaning,
  the family and the fix text for one code, and the codes of the same family for an unknown one.
- `scireport.errors.CODES` is the dictionary of codes and titles; `scireport.error_help.HELP` holds the fix
  texts.

Codes are stable: a code keeps its meaning in every later release, and a retired code is never reused for
something else. It is therefore safe to match on `code` in scripts and tests, never on `message`.

## Triage order

1. E1xx and E2xx: keys and value fields. They break the structure, and one wrong key can cause many others.
2. E3xx: table columns and rows, then E4xx assets and bundle files (hashes, paths, size cap).
3. E5xx (versions) and E6xx (pre-processing) next: a step that fails leaves its outputs missing, which then
   shows up as E103 or E105 downstream.
4. Template and layout: E7xx (definitions and syntax), then E8xx (rendering and export).
5. E9xx and E506 are environment problems (pango, TeX Live, `scireport[pandoc]`, `scireport[mcp]`), not
   problems in the data. Install what the hint names, or choose another engine.
6. Warnings last: W4xx and W7xx often only need tidying; W5xx, W6xx and W9xx say how the output may differ.

## Families

<!-- generated:families -->
| Prefix | About |
|---|---|
| `E1xx` | keys: the key grammar, and values the template reads |
| `E2xx` | kinds and value fields |
| `E3xx` | table schema |
| `E4xx` | assets and bundles |
| `E5xx` | versions of the spec, templates, layouts and pandoc |
| `E6xx` | pre-processing |
| `E7xx` | template and layout definitions |
| `E8xx` | rendering and export |
| `E9xx` | PDF engines and optional extras |
| `W4xx` | unused items |
| `W5xx` | versions |
| `W6xx` | math |
| `W7xx` | Markdown prose |
| `W9xx` | PDF engine warnings |
<!-- /generated -->

## Every code

<!-- generated:errors -->
| Code | Severity | Meaning | What to do |
|---|---|---|---|
| `E101` | error | Key does not follow the key grammar | A key has an uppercase letter, a space, an empty segment or another character outside [a-z0-9_-]. Rewrite it as lowercase segments joined by single dots (for example 'run.mean-mag'); the hint gives a close spelling. |
| `E102` | error | Key is both a value and the prefix of another key | One key holds a value and is also the start of a longer key ('a' and 'a.b'). Rename one of them so that no key is a prefix of another; templates reach values through data.a.b.c chains. |
| `E103` | error | Reference to a key that does not exist | The outline, an input of a pre-processing step, a requested export key or `inspect --key` names a key that is not under values. Fix the spelling (see the hint) or add the value; a key a preprocess step writes also counts. |
| `E104` | error | Key is already in use | A value was added twice under the same key. Choose a different key for the second value, or drop the first; keys must be unique within a bundle. |
| `E105` | error | Template requires a value that the bundle does not have | The template declares a required field (template.yaml fields) and no value matches its key or pattern. Add a value of the listed kind under that key, or pass a template whose fields match the bundle. |
| `E106` | error | Template reads a key that the bundle does not have | The template reads data.<key> (or a component is given a key) that the bundle lacks. Add the value under that key, or fix the key in the template; the hint names the closest existing key. |
| `E201` | error | Unknown kind | A value has a kind that scireport does not know (a typo in 'kind', or a kind from a newer spec). Use a kind from `scireport spec kinds`; the hint suggests the closest name. |
| `E202` | error | Value has the wrong kind for this use | A key points to a value of another kind than the place needs, such as a table where text is expected or an overflow_attachment that is not an attachment. Point to a value of the expected kind, or change the value. |
| `E203` | error | Required field is missing | A kind requires a field that the value does not give. Add the field at the JSON pointer; `scireport spec kinds` lists the fields of every kind. |
| `E204` | error | Unexpected field | A value or the manifest has a field that the kind does not define, usually a typo or a field from another kind. Remove it or correct its name; the schema forbids extra fields. |
| `E205` | error | Field has an invalid value | A field is present but its content is not acceptable, such as a bad number format, a path with the wrong suffix, a blank alt text, a repeated md_file or an interval whose lower bound exceeds the upper. Read the message and the expected value, then correct the field. |
| `E206` | error | Exactly one of several fields must be given | A value or outline node needs exactly one of several alternative fields (for example title or key in an outline node, uncertainty or interval in a number) and has none or more than one. Keep exactly one. |
| `E207` | error | Value kind differs from the kind the template declares | The template needs a different kind of value at this key than the bundle holds (a text where it needs a table, say). Store the data under that key as the expected kind, or use another template. |
| `E208` | error | Component cannot render this kind of value | A template passed a value to a component that cannot draw it, passed several values at once, or asked for a bibliography the bundle does not have. Pass a value of the kind the component accepts, or add the missing value. |
| `E209` | error | Raw LaTeX text has no replacement for this output format | A text value with format latex is raw LaTeX that only the tex output can use. Add alt: {html: ..., md: ...} to the value with a replacement for each other format you render, or render only tex. |
| `E210` | error | Figure has no rendition this output format can use | A figure has no file the format can use: HTML and Markdown need png or svg, LaTeX needs pdf or png, or the template asks for a rendition that is missing. Add that rendition to the figure value, or drop the format. |
| `E211` | error | A bundle holds more than one bibliography | The bundle has two or more bibliography values, but [@key] citations refer to exactly one. Merge the .bib files into one bibliography value and delete the others. |
| `E212` | error | Citation refers to a key that the bibliography does not have | Prose cites [@key] and the bibliography has no entry with that key. Add the entry to the .bib file or correct the citation key (the hint names the closest key). |
| `E301` | error | Inline table rows do not match its columns | An inline table has rows that do not fit its columns: a missing cell, a cell that is not a plain JSON value, or an n_rows or row_status that disagrees with the rows. Give one scalar cell per column per row, or move large data to a .parquet or .csv asset. |
| `E302` | error | Table column definitions are inconsistent | The table's column definitions disagree with each other or the data: repeated column names, emphasis or row_status_column naming a column that is not there, or a CSV that cannot be read. Make the names unique and consistent with the data file. |
| `E303` | error | Table lacks a column the template requires | A table lacks a column that the template requires. Add the column to the data file (the hint shows the closest existing name), or use a template that does not need it. |
| `E304` | error | Table column has a different type than the template requires | A table column exists but with a type the template does not accept (a string where it needs float, say). Convert the column in the data file before packing, or use another template. |
| `E305` | error | Table column declared in the manifest is not in the data file | The manifest lists a column that the .parquet or .csv file does not contain. Correct the column name in the table's columns, or add the column to the data file. |
| `E401` | error | Asset file is missing from the bundle | The manifest names an asset file that is not in the bundle directory or ZIP. Put the file at that path under assets/, or correct the path; `scireport pack` finds the file from the directory. |
| `E402` | error | Asset sha256 does not match its file | The sha256 in the manifest differs from the file's content, so the file was edited after packing or the hash is stale. Run `scireport pack` on the directory to recompute hashes, or restore the original file. |
| `E403` | error | Asset size does not match its file | The file's size differs from the 'bytes' recorded in the manifest, so it was changed or truncated after packing. Restore the original file, or run `scireport pack` again to record the new size. |
| `E404` | error | Asset path is invalid or unsafe | An asset path is absolute, has '..', uses a backslash or a symbolic link, leaves assets/, or differs from another asset only by letter case. Use a relative path inside assets/ with forward slashes and unique, case-insensitive names. |
| `E405` | error | Bundle is larger than the size cap | The bundle, or the ZIP with its number of entries, is over the size cap (1024 MiB uncompressed by default). Aggregate the data into summaries (bundles hold summaries, not catalogues), or raise the cap with --max-size. |
| `E406` | error | Not a scireport bundle | The path is not a bundle: it does not exist, or it is not a directory with scireport.yaml or scireport.json, a .zip with scireport.json at its root, or a .json/.yaml manifest. Check the path and the file names. |
| `E407` | error | Archive entry rejected | A ZIP entry is unsafe or damaged: it leaves the archive (zip-slip), is a symbolic link, is encrypted, is corrupt or repeats another name in different case. Rebuild the archive with `scireport pack` from a clean directory. |
| `E408` | error | Manifest cannot be parsed | The manifest is not valid JSON or YAML (a syntax error, a duplicate key, NaN or Infinity, or a wrong encoding). Fix the syntax at the line the message gives; save the file as UTF-8. |
| `E409` | error | Bundle form is not allowed here | The bundle form does not fit the use: both scireport.json and scireport.yaml exist, a ZIP holds a YAML manifest, or a single-file manifest has assets. Keep one manifest; use `scireport pack` to make a ZIP or write a directory. |
| `E410` | error | Destination cannot be written | The destination exists and would be overwritten, is not an empty or bundle directory, or is a directory where a file is wanted. Pick another destination, or pass --force when you mean to replace a bundle or scireport.yaml. |
| `E411` | error | One asset path is declared with different hashes | The same asset path is listed twice with a different sha256 or size, so the values disagree about one file. Make the entries identical or give the two files different paths. |
| `E412` | error | A path is outside the directory this server may use | A path given to an MCP tool is outside the server root, which is the only directory the server may read or write. Use a path under the root the server was started with (scireport mcp), or restart it with the right root. |
| `E501` | error | Bundle was written by a newer spec version | The data file or a request is for a newer spec than this scireport knows. Upgrade scireport (the hint shows the command); do not edit the version number by hand. |
| `E502` | error | Spec version is missing or malformed | The manifest has no 'scireport' entry or it is not MAJOR.MINOR. Add scireport: "1.0" at the top level, as a string, not a number. |
| `E503` | error | Spec version is too old and has no migration | The bundle's spec major version is older than anything this scireport can migrate. Run `scireport spec migrate` with a scireport release that still knows that version, or rewrite the manifest for the current spec. |
| `E504` | error | Template or layout version does not exist | The template or layout exists but not at this version (name@N). Use a version listed in the hint, or leave the version off to take the newest; `scireport templates` and `scireport layouts` list them. |
| `E505` | error | Template or layout does not support this spec version | The chosen template or layout was written for other spec versions than the bundle's. Choose a version that supports the bundle's spec (`scireport templates NAME` shows the range), or migrate the bundle. |
| `E506` | error | Pandoc is needed and scireport[pandoc] is not installed | Pandoc is needed (markup_engine pandoc, or docx, odt or epub output) but the extra is not installed, or pypandoc found no pandoc. Run `uv add 'scireport[pandoc]'` (or pip install 'scireport[pandoc]'), or use the default mistletoe engine. |
| `E507` | error | Pandoc failed | Pandoc ran and failed, or took longer than its time limit. Read the stderr text in the message; the usual causes are Markdown or raw LaTeX pandoc rejects, a bad reference document, or a missing resource. |
| `E601` | error | Pre-processor is not registered (or not in this version) | The step names a pre-processor or a version that is not registered. Use a name from `scireport preprocessors` (the hint suggests the closest), or correct 'version'; a module:function must be decorated with @preprocessor. |
| `E602` | error | Pre-processor parameters are invalid | A step's params are invalid for that pre-processor: an unknown name, a wrong type or a value out of range. Fix the params at the JSON pointer; `scireport preprocessors NAME` lists them. |
| `E603` | error | Pre-processor input or output does not fit its ports | A step's inputs or outputs do not fit its ports: a port is unwired or unknown, the input key is missing or of another kind, or the function returned the wrong ports. Match inputs and outputs to the ports in `scireport preprocessors NAME`. |
| `E604` | error | Pre-processing steps do not form a valid graph | The preprocess steps cannot be put in order: two steps write the same key, a step reads its own output, or they depend on each other in a cycle. Give each output a unique key and remove the circular wiring. |
| `E605` | error | Importing a pre-processor by module and function needs --allow-import | A step names code as module:function, which a data file may not run on its own. If you trust the file, pass --allow-import; otherwise use a registered name from `scireport preprocessors`. |
| `E606` | error | A pre-processor failed | The pre-processor raised an exception while running, so the cause is in its code or data, not in the manifest. Read the exception in the message, fix the input data or the params, and run again with --log-level DEBUG for details. |
| `E607` | error | A pre-processor needs an optional dependency that is not installed | The step needs an optional extra, such as astropy for the astro pre-processors, that is not installed. Install it with `uv add 'scireport[astro]'` (the hint names the extra), then run again. |
| `E608` | error | A pre-processor plugin cannot be loaded | A module:function reference or a pre-processor plugin could not be imported. Check that the package is installed in this environment and the name is spelled right, or remove the broken plugin. |
| `E701` | error | Template or layout not found | The template or layout name or path was not found, or the version after @ is not a positive integer. Run `scireport templates` or `scireport layouts` for the names, or give the directory that holds template.yaml or layout.yaml. |
| `E702` | error | template.yaml or layout.yaml is invalid | template.yaml or layout.yaml is not valid: bad YAML, not a mapping, or a field with a wrong value. Fix the field at the JSON pointer in the message, and check the file against the template and layout docs. |
| `E703` | error | Template or layout file is missing | template.yaml or layout.yaml lists a file (an entry, include, style or palette) that does not exist or leaves the directory. Add the file at that relative path, or correct the name in the definition. |
| `E704` | error | Template syntax error | A Jinja template has a syntax error, such as an unclosed block or a bad expression. Open the file at the file:line in the issue and fix the tag; `scireport validate` lints every template file. |
| `E705` | error | Template or layout plugin cannot be loaded | A template or layout plugin registered through an entry point raised while loading. Check or reinstall the package that provides it, or remove it from the environment; the message has the original error. |
| `E706` | error | Template or layout does not support the requested output format | The template or layout does not provide the requested output format (md, html or tex, or the one the PDF or office format is made from). Choose a format they support (the message lists them), or choose another template or layout, or --office-source. |
| `E707` | error | Layout does not define a component macro | The layout does not define one of the component macros for this format (the name is in the message). Add the macro to the layout's components file, or use a layout that defines all components. |
| `E801` | error | Component called with an invalid argument | A component got an argument it cannot use, such as a heading level other than 1 to 3 or an md_file that is not a plain .md name, or --format named a format this version does not write. Pass an accepted value. |
| `E802` | error | Template does something the sandbox forbids | The template did something the sandbox forbids, such as reaching a private or unsafe attribute or method. Templates may only use data, components and filters; move the logic into a pre-processor. |
| `E803` | error | Template uses a name that does not exist | The template uses a variable, filter or component that does not exist. Fix the spelling at the file:line of the issue; the data object holds the bundle's values, and `scireport templates NAME` shows the contract. |
| `E804` | error | Rendering failed | Rendering raised an unexpected error inside a template or component. Look at the file:line and the exception type in the message, and fix the template call (often a value of the wrong type or a missing field). |
| `E805` | error | Option is not supported by this scireport version | A render setting has a value this version does not support: the PDF engine (weasyprint or latex), TeX engine (lualatex, xelatex or pdflatex), markup engine, math renderer or office source. Choose one of the values in the hint. |
| `E806` | error | Layout option is unknown or has an invalid value | A layout option is unknown or its value has the wrong type or is outside its choices. Pass --option name=value (-O) or set render.options with a name and value that `scireport layouts NAME` lists. |
| `E807` | error | Two keys give the same LaTeX macro name | Two number keys give the same LaTeX macro name, for example 'a.b' and 'a-b'. Rename one key, or export them in separate runs of `scireport export tex --keys` with different --prefix values. |
| `E808` | error | Key cannot be exported as a LaTeX fragment | A key named in `scireport export tex --keys` is not a number, table or figure value, so it has no LaTeX fragment. Name a key of one of those kinds, or select keys with a pattern such as 'results.*'. |
| `E901` | error | A system dependency of a PDF engine is missing | A system dependency of a PDF engine is missing: pango for weasyprint (the pdf extra), or latexmk, the TeX engine or a TeX package for latex. Install it as the hint says (TeX Live, pango), or choose the other --pdf-engine. |
| `E902` | error | The PDF engine failed | The PDF engine ran and failed. For LaTeX read the file:line errors in the issues; for WeasyPrint read the message. Fix the content or layout option they point to, then render again. |
| `E903` | error | Layout does not support the requested PDF engine | The layout does not list the PDF engine in its pdf_engines. Choose an engine the layout supports (the message lists them) with --pdf-engine, or choose another layout. |
| `E904` | error | An optional extra (scireport[mcp]) is not installed | The MCP server needs the mcp package, which belongs to an optional extra. Run `uv add 'scireport[mcp]'` (or pip install 'scireport[mcp]'), then start `scireport mcp` again. |
| `W401` | warning | Value is never rendered by the template | The bundle has a value that the template never uses, so it will not appear in the report. Remove it, or add it to the outline or a template that renders it; the warning does not stop rendering. |
| `W402` | warning | Asset file is not referenced by the manifest | A file under assets/ is not referenced by any value and is left out of packed bundles. Delete the file or add a value that points to it. |
| `W403` | warning | Key is computed at render time and cannot be checked in advance | The template builds a key at render time (for example data[name]), so validation cannot check it in advance. No action is needed; any missing key is reported as E106 while rendering. |
| `W501` | warning | Pandoc version differs from the one recorded in the bundle | The pandoc that ran has another version than the one recorded in render.pandoc_version of the bundle, so the output may differ. Install the recorded pandoc version, or pack the bundle again to record the current one. |
| `W601` | warning | Math could not be drawn and is shown as source | Mathtext cannot draw the expression, so the LaTeX source is shown in HTML and PDF through WeasyPrint. Simplify the expression to the subset mathtext supports, or use --math-renderer usetex (needs LaTeX); tex output is not affected. |
| `W602` | warning | LaTeX could not typeset math and the source is shown instead | LaTeX rejected a math expression under the usetex renderer, so the source is shown instead. Correct the expression, or use --math-renderer mathtext. |
| `W701` | warning | Markdown construct is outside the supported subset | The Markdown uses a construct outside the supported subset (a block where only inline text is allowed, or raw HTML, say), and it was kept as it is. Rewrite it with the supported syntax, or use --markup-engine pandoc. |
| `W901` | warning | pdfLaTeX falls back to TeX fonts | pdfLaTeX cannot load the layout's OpenType fonts, so it used TeX fonts and the PDF looks different. Use --latex-engine lualatex or xelatex for the designed look. |
| `W902` | warning | The PDF engine reported characters the font does not have | The font has no glyph for some characters, which are missing from the PDF. Replace them in the text, or choose a layout or engine whose font covers them (--latex-engine lualatex or xelatex). |
<!-- /generated -->
