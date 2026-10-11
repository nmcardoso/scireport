# Compatibility policy

A report is data that outlives the program that wrote it. A bundle written today must still open, validate and render in
five years, and it must say the same thing. This page states what `scireport` promises about that, how the promise is
enforced by tests, what counts as breaking it, how a change is made without breaking it, and what is not promised. The
decisions behind it are ADR-0008 (backward compatibility) and ADR-0005 (stable error codes); the data format itself is
in [The data-file specification](spec.md).

```{note}
**Since 1.0.0** spec 1.0, the built-in templates (`generic@1`, `kitchen-sink@1`) and layouts (`minimal@1`, `default@1`,
`modern@1`) are frozen. Before the release, additions to the spec and visual changes were still made in place (the
`bibliography` kind arrived after the first draft; the designs of `default@1` and `modern@1` were redone at gate HG-S1);
the changelog ([changelog](changelog.md)) lists them. From 1.0.0 on, the same change is a new version.
```

## What is promised

### Data-file versions

The spec version is `MAJOR.MINOR` and is written into every bundle, template and layout (ADR-0008).

- **Minor versions are additive.** A new minor version may add optional fields, kinds and rules. It does not remove,
  rename or reinterpret anything that exists.
- **Every older minor is read natively.** This package reads every bundle of the major version it supports, whatever
  minor it was written with, without conversion or flags.
- **An old bundle renders identically.** Rendering a bundle with the same template and layout versions gives the same
  bytes in Markdown, LaTeX and HTML as it did before, and the same text in a PDF. This is what the compat corpus tests
  (see below). A change in how an old bundle renders is a bug, not a feature.
- **A newer minor is refused with a hint.** A bundle stamped with a newer minor than the installed package knows is
  `E501`, with the hint to upgrade scireport. It is never read "as well as possible".
- **A major version ships a migration.** A new major version comes with a pure function from the old manifest to the
  new one (`scireport spec migrate`). A major older than the oldest migration is `E503`.
- **The JSON Schema of a released version never changes.** `scireport/spec/schemas/data-1.0.schema.json` is generated
  from the pydantic models and frozen; a test fails when the models drift from it.

### Built-in templates and layouts

The built-in templates (`generic@1`, `kitchen-sink@1`) and layouts (`default@1`, `modern@1`, `minimal@1`) are **frozen per
version**.

- A visual or structural change is a new version directory (`layouts/default/2/`), never an edit of `default/1/`.
- A name without a version (`default`) means the newest version available. A bundle that says `default` therefore
  changes look when `default@2` ships. `scireport pack` writes the resolved `name@version` into the bundle, so a packed
  bundle renders the same after newer versions exist. Without a template or layout in the bundle or on the command line the
  defaults are the explicit `generic@1` and `default@1`, and those do not move.
- The palette and the matplotlib style of a layout belong to it: a change of either is a visual change.
- Pre-processors are versioned in the same way; a step that names `version: 1` keeps getting version 1
  ([Pre-processors](preprocessors.md)).

Templates and layouts declare the spec versions they support (`spec: ">=1.0,<2.0"`). A bundle outside that range is
`E505`.

### Error codes and exit codes

Errors are aggregated and coded (ADR-0005), and the codes are part of the public API (ADR-0008).

- A code never changes meaning once released. A retired code is never reused, and codes are never renumbered.
- The families are fixed by the first digit (`E1xx` keys, `E2xx` kinds, `E3xx` tables, `E4xx` assets, `E5xx` versions,
  and so on, see [Error codes](errors.md)). New codes take the next free number of their family.
- The exit codes of the command line are:

<!-- generated:exit-codes -->
| Code | Meaning |
|---|---|
| 0 | Success. |
| 1 | A failure that is not a problem in the data file (I/O error, pandoc or a PDF engine failed, `agent install-skill --check` found a difference). |
| 2 | The data file, template, layout or an export is invalid (errors; with `--strict` also warnings). |
| 3 | A system dependency or optional extra is missing (pango, TeX Live, `scireport[pandoc]`, `scireport[mcp]`); the message says how to install it. |
<!-- /generated -->

`--json` output carries the same codes, so a program can act on them without reading prose.

### Python API

The public Python API is `scireport.__all__` and follows semantic versioning (ADR-0008).

- Removing or renaming a public name, or changing a signature incompatibly, needs a new major version. Adding a name is
  a minor change.
- A name is removed only after **at least one minor version** in which using it gives a deprecation warning.
- The exception classes and their `exit_code` attributes are part of the API.

The snapshot test covers `scireport.__all__`, listed in [Python API](api.md). Other modules that a documentation page presents as
an extension point (writing a pre-processor with `scireport.preprocess`, the figure helpers of `scireport.styles`) are
documented where they are used ([Pre-processors](preprocessors.md), [Matplotlib style guide](styles.md)); ADR-0008 does not say whether they are covered by
the same promise, so treat anything outside `__all__` and the documentation as internal.

### Determinism

The same inputs and the same versions of scireport and its dependencies give the same bytes (ADR-0004, ADR-0001).

- `.md`, `.html` and `.tex` outputs and the PNG figures are byte-identical from one run to the next. No wall-clock time
  and no absolute path enters an output; the date comes from `SOURCE_DATE_EPOCH`, else `meta.date`, else 1980-01-01.
- A bundle written twice from the same content is the same ZIP: sorted entries, fixed timestamps. The compressed bytes of
  deflated entries depend on the zlib build, so identity is guaranteed for one Python and zlib; the hashes inside the
  manifest never depend on it.
- **PDF is best effort, and recorded per engine.** On one machine and one set of library versions, two builds give
  byte-identical PDFs for WeasyPrint, LuaLaTeX, XeLaTeX and pdfLaTeX (checked by `tests/integration/test_pdf.py`). The
  bytes still differ between pango, HarfBuzz or TeX Live versions. What the compat corpus freezes is the *letters* of
  the PDF text, not its bytes.

Every render writes `render-manifest.json` with the hashes of its inputs and outputs and the versions that produced them
([Outputs](outputs.md)), which is where to look when two renders differ.

## How it is enforced

A promise that is not tested is a wish. These are the mechanisms.

| Promise | Test | What fails |
|---|---|---|
| Old bundles load the same way | `tests/compat/test_spec_1_0.py` | Every form of every case loads to the expected canonical manifest and the expected `inspect` summary. |
| Old bundles render the same way | `tests/compat/test_render_1_0.py`, `tests/compat/test_render_layouts_1_0.py`, `tests/compat/test_render_pandoc_1_0.py` | Markdown, LaTeX and HTML of every case, with `generic@1`, each built-in layout and each markup engine, equal the committed files. HTML is compared as a canonical DOM. The pandoc files are compared only with the pandoc version that wrote them. |
| PDF text is the same | `tests/integration/test_pdf.py` | The letters of the PDF made by WeasyPrint and by LuaLaTeX hash to the committed value, for both markup engines. Needs the toolchains. |
| Fixtures were not touched | `test_fixtures_are_frozen` | A fixture was added, removed or changed. |
| The freeze lists only grow | `tests/frozen.py BASE_REF` (the CI `compat` job, `make compat-growth`) | A line of `FROZEN.sha256` or `FROZEN-builtins.sha256` disappeared or changed since the base of the change or since the latest release tag: a fixture cannot be regenerated together with its hash. |
| Built-in layouts and templates are untouched | `tests/compat/test_frozen_builtins.py` | A file of `layouts/NAME/N/` or `templates/NAME/N/`, a vendored font, a matplotlib style or a frozen JSON Schema changed or was added without being listed in `FROZEN-builtins.sha256`. |
| The release holds the frozen files | `.github/check_dist.py` (the release workflow) | The wheel or the sdist drops or rewrites a frozen built-in file. |
| The schema is frozen | `tests/unit/spec/test_schema.py` | The models no longer generate `data-1.0.schema.json`. |
| Bare JSON canonicalises stably | `tests/property/` | Key grammar, idempotent canonicalisation and manifest round trips, with generated inputs. |
| Built-in output is stable | `tests/golden/` | Markdown, HTML and LaTeX of `kitchen-sink` (every kind) and of each layout differ byte for byte. A second render is also compared with the first. |
| The Python API is stable | `tests/unit/test_public_api.py` against `tests/unit/public_api.txt` | A public name, signature or method changed. |
| Codes are documented and tested | `tests/unit/test_error_docs.py` | A code in the source is missing from the catalogue, the docs page is stale, or no test names a code. |

One limit is worth knowing: the stability of an error code's *meaning* is kept by review. `tests/compat/error-codes.json`
freezes the title of every released code, so a removed or retitled code fails a test, but a reused code with the same title
and another cause would not.

### The compat corpus

`tests/compat/spec-1.0/` is the frozen corpus of spec 1.0. Each case is a directory:

```text
tests/compat/spec-1.0/
  FROZEN.sha256                  # sha256 of every file below, except this one and README.md
  minimal/
    bundle.scireport/            # the bundle as a directory
    bundle.scireport.zip         # the same bundle as a ZIP
    expected/
      manifest.json              # the canonical manifest a reader must produce
      summary.json               # what `scireport inspect --json` reports
      render-generic-1-minimal-1/{md,html,tex}/    # generic@1 with minimal@1
      render-generic-1-default-1/...               # generic@1 with default@1, plus pdf-text-*.sha256
      render-generic-1-modern-1/...
  text-only/                     # a hand-authored YAML directory, a single JSON file and a ZIP
  full-kinds/                    # 16 kinds of the first draft, every asset type (its outline lists four values)
  bibliography/                  # the bibliography kind, citations, and the LaTeX renders
  every-kind/                    # all 17 kinds in the outline, so every kind reaches every frozen render
  pandoc-version.txt             # the pandoc that wrote the render-*-pandoc folders
```

The folders `render-generic-1-<layout>-1/` hold the files written with the default markup engine (`mistletoe`),
`render-generic-1-<layout>-1-pandoc/` those written with `--markup-engine pandoc`; the layouts are `minimal`, `default` and
`modern`, the formats `md`, `html` and `tex`, and the designed layouts add the PDF text hashes of WeasyPrint and LuaLaTeX.
What pandoc writes depends on its version, so the pandoc tests compare only with `pandoc-version.txt` (they skip locally
with another version and fail in CI); a pandoc upgrade adds folders for the new version, it never edits these.

`FROZEN.sha256` lists a SHA-256 and a path per line. The test compares the list with the files on disk: a new file, a
missing file or a changed file fails it. The `make_*.py` scripts that created the corpus refuse to run again once their
output exists. A second check guards the list itself: CI runs `python tests/frozen.py BASE_REF` (`make compat-growth`), which
fails when a line disappeared or changed since the base of the change or since the latest release tag, so only new lines can
be added. `tests/compat/FROZEN-builtins.sha256` does the same for the built-in layouts, templates, fonts, matplotlib styles
and JSON Schemas.

**What a failure means.** A compat test that fails means the behaviour of spec 1.0 changed: either a bundle no longer
loads to the same manifest, or it no longer renders to the same output. It is almost never the fixture that is wrong.

**What to do.**

1. Never edit, regenerate or delete a frozen file, and never edit `FROZEN.sha256` to make a test pass.
2. Find the code change that altered the behaviour and undo it, or make it so that old bundles take the old path.
3. If the new behaviour is wanted, it is a new version: a new layout or template version, a new spec version, or a new
   pre-processor version (see the procedures below). The old fixtures stay and keep passing.
4. To cover something new, **add a case**: a new directory with its own script that only adds files and appends their
   hashes to `FROZEN.sha256` (`tests/compat/make_bibliography_1_0.py` is the model). Appending is allowed; changing an
   existing line is not.

Check the corpus any time with `make compat` (the pandoc files need the `pandoc` extra); without the integration tests it is also part of `make test`.

## What counts as breaking

| Change | Breaking? | Why / what to do instead |
|---|---|---|
| A new optional field on an existing kind | no | Additive: a new spec minor. The `bibliography` kind and `render.pandoc_version` were added this way. |
| A new kind | no | Additive: a new spec minor. Older readers refuse the newer stamp with `E501` rather than misread it. |
| Making an optional field required, or a default different | **yes** | Old bundles that omit it would load differently. The canonical manifest writes defaults for this reason. |
| Rejecting input that was accepted (a stricter key grammar, a new rule that old bundles break) | **yes** | A reader reads every older minor natively. |
| Renaming or removing a field, a kind or a key rule | **yes** | New major version with a migration. |
| Changing the markup of `default@1` (HTML, LaTeX, Markdown) or its palette | **yes** | New version directory: `default@2`. |
| A new layout or template, or a new version beside the old | no | Nothing that exists changes. |
| Changing the figure or number a released pre-processor version produces | **yes** | Register a new version beside the old one. |
| Removing or renaming a name in `scireport.__all__`, or an incompatible signature | **yes** | Deprecate for at least one minor version; remove in the next major. |
| Adding a public name or an optional parameter | no | Minor. |
| Changing the meaning of an error code, renumbering it or reusing a retired one | **yes** | Add a new code. |
| Adding an error or warning code | no | New codes take the next free number. See the note on `--strict` below. |
| Changing a frozen compat fixture | **yes** | Add a case instead. |
| PDF bytes differ after a pango, HarfBuzz or TeX Live upgrade | no | Best effort; the compat corpus compares the PDF text. |
| Output of pandoc differs after a pandoc upgrade | no | pandoc's version is recorded (`W501`); see [pandoc: markup engine, citations and office formats](pandoc.md). |

## How to make a change

These procedures are derived from ADR-0008, the `Makefile` and the tests; the repository has no separate checklist. Read
the ADRs in [Architecture decision records](adr/index.md) first: a change that contradicts one needs a new ADR, not a quiet edit.

**A new layout or template version.**

1. Copy `layouts/NAME/N/` to `layouts/NAME/N+1/` and set `version: N+1` in `layout.yaml` (templates: `templates/NAME/N/`
   and `template.yaml`). Change only the copy.
2. Add golden tests for the new version, and add its renders to the compat corpus as new files with a new script that
   appends to `FROZEN.sha256` (see `tests/compat/make_render_layouts_1_0.py`).
3. Leave version N as it is. A bundle that names `NAME@N` keeps rendering with it; a bare `NAME` now means `N+1`.
4. Append the new directory to the freeze list: `uv run python tests/compat/make_frozen_builtins.py` (it adds lines and refuses to change one).
5. Update [Built-in layouts](layouts.md) or [Writing a template](templates.md) and the changelog.

**A new spec minor.**

1. Make only additive changes to the models in `scireport/spec/`, and mark each new field (or model) with
   `json_schema_extra={'since': '1.N'}`: the schema of an older minor is generated from the newer models by leaving
   those out. Prove that nothing old changed: `make compat` and the schema test, which regenerates every frozen
   `data-<version>.schema.json` byte for byte, pass with no fixture edited.
2. Raise `SPEC_VERSION` in `scireport/spec/version.py`. Check the `spec:` range of every template and layout.
3. Write the new schema file with `make schema` (it writes `data-<version>.schema.json`). Never run it for a released
   version: that file is frozen.
4. Add a compat case for what is new, update [The data-file specification](spec.md) and the changelog.

**A new spec major.** Do the same, and add the migration in `scireport/spec/migrations/` as a pure function from a manifest
dict of the old major to the new one, registered with `register_migration`. Test it against the old corpus. The old
corpus stays.

**Deprecating a public name.** Keep it working and make it emit a deprecation warning. Leave it for at least one minor
version, record it under "Deprecated" in the changelog, and remove it only in a major version. A change to the public API
shows in the diff of `tests/unit/public_api.txt`; regenerate it with
`SCIREPORT_UPDATE_API=1 uv run pytest tests/unit/test_public_api.py` and read the diff, because that diff is the API
change.

**Adding an error code.** Take the next free number of its family. Add it to `CODES` in `scireport/errors.py` with a
one-line title and to `HELP` in `scireport/error_help.py`, regenerate the docs tables with `make skill`, and write a test
that names the code. Never renumber a code and never reuse a retired one.

## What to do as a user

- **Pin the version.** Pin scireport in your project (a lock file, and for an install from the GitHub repository a tag or
  a commit) so that an upgrade is something you decide. Read [Changelog](changelog.md) before upgrading.
- **Pack your bundles.** `scireport pack` completes a data file, records the hash of every asset and pins the template
  and layout to `name@version` (and the pandoc version when pandoc is used). A packed ZIP is the form to archive.

  ```bash
  scireport pack report.scireport -o report.scireport.zip
  ```

- **Validate in CI.** `scireport validate` exits 0 when the bundle is valid and 2 when not. `--strict` makes warnings
  fail too.

  ```bash
  scireport validate report.scireport.zip --strict --json
  ```

  A new release can add warning codes, and the ADRs do not promise otherwise, so a strict check can start to fail after an
  upgrade. Another reason to pin the version and upgrade on purpose.
- **Keep the bundle, not the output.** Because an old bundle renders to the same text, the bundle is the archive and the
  PDF can be rebuilt. Keep the `render-manifest.json` of an important report: it records the versions that made it.
- **Write against the data file, not the output.** Depend on keys, kinds and error codes, which are stable, and not on the
  wording of a message or the exact layout of a page.

## What is not promised

- **Platforms other than Linux.** CI builds and tests on Linux only. macOS and Windows are not built, tested or supported,
  although the code stays portable. Python 3.12 to 3.14 are supported; 3.15 stays experimental until wheels exist for every
  dependency.
- **PDF bytes across library versions.** pango, HarfBuzz, WeasyPrint and TeX Live versions change the bytes. Only the
  PDF text is frozen, and only for the engines the corpus records (WeasyPrint and LuaLaTeX).
- **Output of pandoc across pandoc versions.** The pandoc golden files hold for the pinned pandoc. The Markdown, HTML and
  Word outputs that go through pandoc are not part of the frozen corpus. The pandoc version in a bundle is recorded so that
  a difference can be explained (`W501`).
- **ZIP bytes across zlib builds.** The ZIP of one content is the same on one Python and zlib; the hashes in the manifest
  do not depend on it.
- **The wording of messages and log lines.** Codes, keys and JSON pointers are stable; the text next to them can be
  improved.
- **Command-line flags and the shape of `--json` output beyond the codes.** No ADR makes them part of the contract, though
  [Command line](cli.md) documents them and the changelog records changes.
- **Third-party templates, layouts and pre-processors.** Those that come from plugins are as stable as their authors make
  them. Only the built-in ones are frozen by scireport.
- **Anything before the final `1.0.0`**, as described in the note at the top of this page.

## See also

- [The data-file specification](spec.md): the data-file format and its versioning.
- [Error codes](errors.md): every error and warning code.
- [Changelog](changelog.md): what changed in each release.
- ADR-0005 (validation and codes) and ADR-0008 (backward compatibility), in [Architecture decision records](adr/index.md).
