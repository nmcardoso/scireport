"""What to do about each error and warning code (shown by ``error_help`` and in the skill).

``scireport.errors.CODES`` says what a code means in one line; :data:`HELP` says what usually
causes it and how to fix it, in one or two sentences for a person or an agent that has the
message in front of it. A test checks that every code has an entry and that no entry is left
over when a code is removed.
"""

from __future__ import annotations

HELP: dict[str, str] = {
  'E101': (
    'A key has an uppercase letter, a space, an empty segment or another '
    'character outside [a-z0-9_-]. Rewrite it as lowercase segments joined by '
    "single dots (for example 'run.mean-mag'); the hint gives a close spelling."
  ),
  'E102': (
    "One key holds a value and is also the start of a longer key ('a' and 'a.b')."
    ' Rename one of them so that no key is a prefix of another; templates reach '
    'values through data.a.b.c chains.'
  ),
  'E103': (
    'The outline, an input of a pre-processing step, a requested export key or '
    '`inspect --key` names a key that is not under values. Fix the spelling (see '
    'the hint) or add the value; a key a preprocess step writes also counts.'
  ),
  'E104': (
    'A value was added twice under the same key. Choose a different key for the '
    'second value, or drop the first; keys must be unique within a bundle.'
  ),
  'E105': (
    'The template declares a required field (template.yaml fields) and no value '
    'matches its key or pattern. Add a value of the listed kind under that key, '
    'or pass a template whose fields match the bundle.'
  ),
  'E106': (
    'The template reads data.<key> (or a component is given a key) that the '
    'bundle lacks. Add the value under that key, or fix the key in the template; '
    'the hint names the closest existing key.'
  ),
  'E201': (
    "A value has a kind that scireport does not know (a typo in 'kind', or a kind"
    ' from a newer spec). Use a kind from `scireport spec kinds`; the hint '
    'suggests the closest name.'
  ),
  'E202': (
    'A key points to a value of another kind than the place needs, such as a '
    'table where text is expected or an overflow_attachment that is not an '
    'attachment. Point to a value of the expected kind, or change the value.'
  ),
  'E203': (
    'A kind requires a field that the value does not give. Add the field at the '
    'JSON pointer; `scireport spec kinds` lists the fields of every kind.'
  ),
  'E204': (
    'A value or the manifest has a field that the kind does not define, usually a'
    ' typo or a field from another kind. Remove it or correct its name; the '
    'schema forbids extra fields.'
  ),
  'E205': (
    'A field is present but its content is not acceptable, such as a bad number '
    'format, a path with the wrong suffix, a blank alt text, a repeated md_file '
    'or an interval whose lower bound exceeds the upper. Read the message and the'
    ' expected value, then correct the field.'
  ),
  'E206': (
    'A value or outline node needs exactly one of several alternative fields (for'
    ' example title or key in an outline node, uncertainty or interval in a '
    'number) and has none or more than one. Keep exactly one.'
  ),
  'E207': (
    'The template needs a different kind of value at this key than the bundle '
    'holds (a text where it needs a table, say). Store the data under that key as'
    ' the expected kind, or use another template.'
  ),
  'E208': (
    'A template passed a value to a component that cannot draw it, passed several'
    ' values at once, or asked for a bibliography the bundle does not have. Pass '
    'a value of the kind the component accepts, or add the missing value.'
  ),
  'E209': (
    'A text value with format latex is raw LaTeX that only the tex output can '
    'use. Add alt: {html: ..., md: ...} to the value with a replacement for each '
    'other format you render, or render only tex.'
  ),
  'E210': (
    'A figure has no file the format can use: HTML and Markdown need png or svg, '
    'LaTeX needs pdf or png, or the template asks for a rendition that is '
    'missing. Add that rendition to the figure value, or drop the format.'
  ),
  'E211': (
    'The bundle has two or more bibliography values, but [@key] citations refer '
    'to exactly one. Merge the .bib files into one bibliography value and delete '
    'the others.'
  ),
  'E212': (
    'Prose cites [@key] and the bibliography has no entry with that key. Add the '
    'entry to the .bib file or correct the citation key (the hint names the '
    'closest key).'
  ),
  'E301': (
    'An inline table has rows that do not fit its columns: a missing cell, a cell'
    ' that is not a plain JSON value, or an n_rows or row_status that disagrees '
    'with the rows. Give one scalar cell per column per row, or move large data '
    'to a .parquet or .csv asset.'
  ),
  'E302': (
    "The table's column definitions disagree with each other or the data: "
    'repeated column names, emphasis or row_status_column naming a column that is'
    ' not there, or a CSV that cannot be read. Make the names unique and '
    'consistent with the data file.'
  ),
  'E303': (
    'A table lacks a column that the template requires. Add the column to the '
    'data file (the hint shows the closest existing name), or use a template that'
    ' does not need it.'
  ),
  'E304': (
    'A table column exists but with a type the template does not accept (a string'
    ' where it needs float, say). Convert the column in the data file before '
    'packing, or use another template.'
  ),
  'E305': (
    'The manifest lists a column that the .parquet or .csv file does not contain.'
    " Correct the column name in the table's columns, or add the column to the "
    'data file.'
  ),
  'E401': (
    'The manifest names an asset file that is not in the bundle directory or ZIP.'
    ' Put the file at that path under assets/, or correct the path; `scireport '
    'pack` finds the file from the directory.'
  ),
  'E402': (
    "The sha256 in the manifest differs from the file's content, so the file was "
    'edited after packing or the hash is stale. Run `scireport pack` on the '
    'directory to recompute hashes, or restore the original file.'
  ),
  'E403': (
    "The file's size differs from the 'bytes' recorded in the manifest, so it was"
    ' changed or truncated after packing. Restore the original file, or run '
    '`scireport pack` again to record the new size.'
  ),
  'E404': (
    "An asset path is absolute, has '..', uses a backslash or a symbolic link, "
    'leaves assets/, or differs from another asset only by letter case. Use a '
    'relative path inside assets/ with forward slashes and unique, case-'
    'insensitive names.'
  ),
  'E405': (
    'The bundle, or the ZIP with its number of entries, is over the size cap '
    '(1024 MiB uncompressed by default). Aggregate the data into summaries '
    '(bundles hold summaries, not catalogues), or raise the cap with --max-size.'
  ),
  'E406': (
    'The path is not a bundle: it does not exist, or it is not a directory with '
    'scireport.yaml or scireport.json, a .zip with scireport.json at its root, or'
    ' a .json/.yaml manifest. Check the path and the file names.'
  ),
  'E407': (
    'A ZIP entry is unsafe or damaged: it leaves the archive (zip-slip), is a '
    'symbolic link, is encrypted, is corrupt or repeats another name in different'
    ' case. Rebuild the archive with `scireport pack` from a clean directory.'
  ),
  'E408': (
    'The manifest is not valid JSON or YAML (a syntax error, a duplicate key, NaN'
    ' or Infinity, or a wrong encoding). Fix the syntax at the line the message '
    'gives; save the file as UTF-8.'
  ),
  'E409': (
    'The bundle form does not fit the use: both scireport.json and scireport.yaml'
    ' exist, a ZIP holds a YAML manifest, or a single-file manifest has assets. '
    'Keep one manifest; use `scireport pack` to make a ZIP or write a directory.'
  ),
  'E410': (
    'The destination exists and would be overwritten, is not an empty or bundle '
    'directory, or is a directory where a file is wanted. Pick another '
    'destination, or pass --force when you mean to replace a bundle or '
    'scireport.yaml.'
  ),
  'E411': (
    'The same asset path is listed twice with a different sha256 or size, so the '
    'values disagree about one file. Make the entries identical or give the two '
    'files different paths.'
  ),
  'E412': (
    'A path given to an MCP tool is outside the server root, which is the only '
    'directory the server may read or write. Use a path under the root the server'
    ' was started with (scireport mcp), or restart it with the right root.'
  ),
  'E501': (
    'The data file or a request is for a newer spec than this scireport knows. '
    'Upgrade scireport (the hint shows the command); do not edit the version '
    'number by hand.'
  ),
  'E502': (
    "The manifest has no 'scireport' entry or it is not MAJOR.MINOR. Add "
    'scireport: "1.0" at the top level, as a string, not a number.'
  ),
  'E503': (
    "The bundle's spec major version is older than anything this scireport can "
    'migrate. Run `scireport spec migrate` with a scireport release that still '
    'knows that version, or rewrite the manifest for the current spec.'
  ),
  'E504': (
    'The template or layout exists but not at this version (name@N). Use a '
    'version listed in the hint, or leave the version off to take the newest; '
    '`scireport templates` and `scireport layouts` list them.'
  ),
  'E505': (
    'The chosen template or layout was written for other spec versions than the '
    "bundle's. Choose a version that supports the bundle's spec (`scireport "
    'templates NAME` shows the range), or migrate the bundle.'
  ),
  'E506': (
    'Pandoc is needed (markup_engine pandoc, or docx, odt or epub output) but the'
    ' extra is not installed, or pypandoc found no pandoc. Run `uv add '
    "'scireport[pandoc]'` (or pip install 'scireport[pandoc]'), or use the "
    'default mistletoe engine.'
  ),
  'E507': (
    'Pandoc ran and failed, or took longer than its time limit. Read the stderr '
    'text in the message; the usual causes are Markdown or raw LaTeX pandoc '
    'rejects, a bad reference document, or a missing resource.'
  ),
  'E601': (
    'The step names a pre-processor or a version that is not registered. Use a '
    'name from `scireport preprocessors` (the hint suggests the closest), or '
    "correct 'version'; a module:function must be decorated with @preprocessor."
  ),
  'E602': (
    "A step's params are invalid for that pre-processor: an unknown name, a wrong"
    ' type or a value out of range. Fix the params at the JSON pointer; '
    '`scireport preprocessors NAME` lists them.'
  ),
  'E603': (
    "A step's inputs or outputs do not fit its ports: a port is unwired or "
    'unknown, the input key is missing or of another kind, or the function '
    'returned the wrong ports. Match inputs and outputs to the ports in '
    '`scireport preprocessors NAME`.'
  ),
  'E604': (
    'The preprocess steps cannot be put in order: two steps write the same key, a'
    ' step reads its own output, or they depend on each other in a cycle. Give '
    'each output a unique key and remove the circular wiring.'
  ),
  'E605': (
    'A step names code as module:function, which a data file may not run on its '
    'own. If you trust the file, pass --allow-import; otherwise use a registered '
    'name from `scireport preprocessors`.'
  ),
  'E606': (
    'The pre-processor raised an exception while running, so the cause is in its '
    'code or data, not in the manifest. Read the exception in the message, fix '
    'the input data or the params, and run again with --log-level DEBUG for '
    'details.'
  ),
  'E607': (
    'The step needs an optional extra, such as astropy for the astro pre-'
    'processors, that is not installed. Install it with `uv add '
    "'scireport[astro]'` (the hint names the extra), then run again."
  ),
  'E608': (
    'A module:function reference or a pre-processor plugin could not be imported.'
    ' Check that the package is installed in this environment and the name is '
    'spelled right, or remove the broken plugin.'
  ),
  'E701': (
    'The template or layout name or path was not found, or the version after @ is'
    ' not a positive integer. Run `scireport templates` or `scireport layouts` '
    'for the names, or give the directory that holds template.yaml or '
    'layout.yaml.'
  ),
  'E702': (
    'template.yaml or layout.yaml is not valid: bad YAML, not a mapping, or a '
    'field with a wrong value. Fix the field at the JSON pointer in the message, '
    'and check the file against the template and layout docs.'
  ),
  'E703': (
    'template.yaml or layout.yaml lists a file (an entry, include, style or '
    'palette) that does not exist or leaves the directory. Add the file at that '
    'relative path, or correct the name in the definition.'
  ),
  'E704': (
    'A Jinja template has a syntax error, such as an unclosed block or a bad '
    'expression. Open the file at the file:line in the issue and fix the tag; '
    '`scireport validate` lints every template file.'
  ),
  'E705': (
    'A template or layout plugin registered through an entry point raised while '
    'loading. Check or reinstall the package that provides it, or remove it from '
    'the environment; the message has the original error.'
  ),
  'E706': (
    'The template or layout does not provide the requested output format (md, '
    'html or tex, or the one the PDF or office format is made from). Choose a '
    'format they support (the message lists them), or choose another template or '
    'layout, or --office-source.'
  ),
  'E707': (
    'The layout does not define one of the component macros for this format (the '
    "name is in the message). Add the macro to the layout's components file, or "
    'use a layout that defines all components.'
  ),
  'E801': (
    'A component got an argument it cannot use, such as a heading level other '
    'than 1 to 3 or an md_file that is not a plain .md name, or --format named a '
    'format this version does not write. Pass an accepted value.'
  ),
  'E802': (
    'The template did something the sandbox forbids, such as reaching a private '
    'or unsafe attribute or method. Templates may only use data, components and '
    'filters; move the logic into a pre-processor.'
  ),
  'E803': (
    'The template uses a variable, filter or component that does not exist. Fix '
    'the spelling at the file:line of the issue; the data object holds the '
    "bundle's values, and `scireport templates NAME` shows the contract."
  ),
  'E804': (
    'Rendering raised an unexpected error inside a template or component. Look at'
    ' the file:line and the exception type in the message, and fix the template '
    'call (often a value of the wrong type or a missing field).'
  ),
  'E805': (
    'A render setting has a value this version does not support: the PDF engine '
    '(weasyprint or latex), TeX engine (lualatex, xelatex or pdflatex), markup '
    'engine, math renderer or office source. Choose one of the values in the '
    'hint.'
  ),
  'E806': (
    'A layout option is unknown or its value has the wrong type or is outside its'
    ' choices. Pass --option name=value (-O) or set render.options with a name '
    'and value that `scireport layouts NAME` lists.'
  ),
  'E807': (
    "Two number keys give the same LaTeX macro name, for example 'a.b' and 'a-b'."
    ' Rename one key, or export them in separate runs of `scireport export tex '
    '--keys` with different --prefix values.'
  ),
  'E808': (
    'A key named in `scireport export tex --keys` is not a number, table or '
    'figure value, so it has no LaTeX fragment. Name a key of one of those kinds,'
    " or select keys with a pattern such as 'results.*'."
  ),
  'E901': (
    'A system dependency of a PDF engine is missing: pango for weasyprint (the '
    'pdf extra), or latexmk, the TeX engine or a TeX package for latex. Install '
    'it as the hint says (TeX Live, pango), or choose the other --pdf-engine.'
  ),
  'E902': (
    'The PDF engine ran and failed. For LaTeX read the file:line errors in the '
    'issues; for WeasyPrint read the message. Fix the content or layout option '
    'they point to, then render again.'
  ),
  'E903': (
    'The layout does not list the PDF engine in its pdf_engines. Choose an engine'
    ' the layout supports (the message lists them) with --pdf-engine, or choose '
    'another layout.'
  ),
  'E904': (
    'The MCP server needs the mcp package, which belongs to an optional extra. '
    "Run `uv add 'scireport[mcp]'` (or pip install 'scireport[mcp]'), then start "
    '`scireport mcp` again.'
  ),
  'W401': (
    'The bundle has a value that the template never uses, so it will not appear '
    'in the report. Remove it, or add it to the outline or a template that '
    'renders it; the warning does not stop rendering.'
  ),
  'W402': (
    'A file under assets/ is not referenced by any value and is left out of '
    'packed bundles. Delete the file or add a value that points to it.'
  ),
  'W403': (
    'The template builds a key at render time (for example data[name]), so '
    'validation cannot check it in advance. No action is needed; any missing key '
    'is reported as E106 while rendering.'
  ),
  'W501': (
    'The pandoc that ran has another version than the one recorded in '
    'render.pandoc_version of the bundle, so the output may differ. Install the '
    'recorded pandoc version, or pack the bundle again to record the current one.'
  ),
  'W601': (
    'Mathtext cannot draw the expression, so the LaTeX source is shown in HTML '
    'and PDF through WeasyPrint. Simplify the expression to the subset mathtext '
    'supports, or use --math-renderer usetex (needs LaTeX); tex output is not '
    'affected.'
  ),
  'W602': (
    'LaTeX rejected a math expression under the usetex renderer, so the source is'
    ' shown instead. Correct the expression, or use --math-renderer mathtext.'
  ),
  'W701': (
    'The Markdown uses a construct outside the supported subset (a block where '
    'only inline text is allowed, or raw HTML, say), and it was kept as it is. '
    'Rewrite it with the supported syntax, or use --markup-engine pandoc.'
  ),
  'W901': (
    "pdfLaTeX cannot load the layout's OpenType fonts, so it used TeX fonts and "
    'the PDF looks different. Use --latex-engine lualatex or xelatex for the '
    'designed look.'
  ),
  'W902': (
    'The font has no glyph for some characters, which are missing from the PDF. '
    'Replace them in the text, or choose a layout or engine whose font covers '
    'them (--latex-engine lualatex or xelatex).'
  ),
}
"""Code to one or two sentences: the usual cause, and the fix."""
