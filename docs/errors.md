# Error codes

Every problem `scireport` reports has a stable code. A code never changes meaning once released
(ADR-0008); a retired code is never reused. `E` codes are errors and make `validate` and `render`
fail; `W` codes are warnings and fail only with `--strict`.

Validation reports **all** problems at once. Each carries the code, a message, the value key, the JSON
pointer into the data file, what was expected and what was found, the template `file:line` that caused it
(when a template did), and a "did you mean" hint where a close spelling exists. `--json` prints the same
as data.

## Exit codes

| Code | Meaning |
|---:|---|
| 0 | Success. |
| 1 | Failure that is not a validation problem (I/O error, bug). |
| 2 | The data file, template or layout is invalid (errors; with `--strict` also warnings). |
| 3 | A system dependency of a PDF engine is missing (pango, TeX Live, a TeX package). |

The table below is checked against `scireport.errors.CODES` by a test, so the two cannot drift.


## Keys

The key grammar and what the template reads.

| Code | Meaning |
|---|---|
| E101 | Key does not follow the key grammar |
| E102 | Key is both a value and the prefix of another key |
| E103 | Reference to a key that does not exist |
| E104 | Key is already in use |
| E105 | Template requires a value that the bundle does not have |
| E106 | Template reads a key that the bundle does not have |

## Kinds and value fields

A value has the wrong kind, or a field of it is wrong.

| Code | Meaning |
|---|---|
| E201 | Unknown kind |
| E202 | Value has the wrong kind for this use |
| E203 | Required field is missing |
| E204 | Unexpected field |
| E205 | Field has an invalid value |
| E206 | Exactly one of several fields must be given |
| E207 | Value kind differs from the kind the template declares |
| E208 | Component cannot render this kind of value |
| E209 | Raw LaTeX text has no replacement for this output format |
| E210 | Figure has no rendition this output format can use |

## Table schema

Table columns against the table and against the template.

| Code | Meaning |
|---|---|
| E301 | Inline table rows do not match its columns |
| E302 | Table column definitions are inconsistent |
| E303 | Table lacks a column the template requires |
| E304 | Table column has a different type than the template requires |
| E305 | Table column declared in the manifest is not in the data file |

## Assets and bundles

Files in a bundle, hashes, sizes, archive safety.

| Code | Meaning |
|---|---|
| E401 | Asset file is missing from the bundle |
| E402 | Asset sha256 does not match its file |
| E403 | Asset size does not match its file |
| E404 | Asset path is invalid or unsafe |
| E405 | Bundle is larger than the size cap |
| E406 | Not a scireport bundle |
| E407 | Archive entry rejected |
| E408 | Manifest cannot be parsed |
| E409 | Bundle form is not allowed here |
| E410 | Destination cannot be written |
| E411 | One asset path is declared with different hashes |

## Versions

Spec, template and layout versions.

| Code | Meaning |
|---|---|
| E501 | Bundle was written by a newer spec version |
| E502 | Spec version is missing or malformed |
| E503 | Spec version is too old and has no migration |
| E504 | Template or layout version does not exist |
| E505 | Template or layout does not support this spec version |

## Templates and layouts

Definition files, syntax and plugins.

| Code | Meaning |
|---|---|
| E701 | Template or layout not found |
| E702 | template.yaml or layout.yaml is invalid |
| E703 | Template or layout file is missing |
| E704 | Template syntax error |
| E705 | Template or layout plugin cannot be loaded |
| E706 | Template or layout does not support the requested output format |
| E707 | Layout does not define a component macro |

## Rendering

Component arguments, the sandbox, options.

| Code | Meaning |
|---|---|
| E801 | Component called with an invalid argument |
| E802 | Template does something the sandbox forbids |
| E803 | Template uses a name that does not exist |
| E804 | Rendering failed |
| E805 | Option is not supported by this scireport version |
| E806 | Layout option is unknown or has an invalid value |

## PDF engines

The WeasyPrint and LaTeX engines that turn the HTML or the LaTeX project into a PDF. `E901` exits with
code 3 and an install hint; `E902` is a failure of the engine itself, with the engine's own messages.

| Code | Meaning |
|---|---|
| E901 | A system dependency of a PDF engine is missing |
| E902 | The PDF engine failed |
| E903 | Layout does not support the requested PDF engine |

## Unused items (warnings)

Values and files nothing uses.

| Code | Meaning |
|---|---|
| W401 | Value is never rendered by the template |
| W402 | Asset file is not referenced by the manifest |
| W403 | Key is computed at render time and cannot be checked in advance |

## Math (warnings)

Math that could not be drawn.

| Code | Meaning |
|---|---|
| W601 | Math could not be drawn and is shown as source |
| W602 | LaTeX could not typeset math and the source is shown instead |

## Markdown (warnings)

Markdown outside the supported subset.

| Code | Meaning |
|---|---|
| W701 | Markdown construct is outside the supported subset |

## PDF engines (warnings)

Things a PDF engine reported on a build that still produced a PDF.

| Code | Meaning |
|---|---|
| W901 | pdfLaTeX falls back to TeX fonts |
| W902 | The PDF engine reported characters the font does not have |
