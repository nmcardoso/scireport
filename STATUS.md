# STATUS

**Phase:** S2 (templates, validation and the md, html and tex writers). Implementation complete on branch
`s2/templates-validation-writers` (pushed). **No human gate in S2.** S1 was merged into `main` (PR #1) before S2
started. Next: open and merge the S2 pull request, then S3 (`prompts/scireport/s3_kickoff.md` in the monorepo).

## Done in S2

- Template and layout models, loaded by name, `name@version`, path or entry point; `pack` pins the resolved versions.
- Sandboxed Jinja environments per format (strict undefined, format-aware escaping, `((* *))` delimiters for
  LaTeX files), the MOSAICS filters and 24 components with Markdown, HTML and LaTeX macros in the `minimal@1`
  layout. `generic@1` renders any bundle from its outline.
- Mistletoe converter with a documented Markdown subset (limits in `docs/markup.md`).
- Validation: aggregated coded issues, `--strict`, `--json`, Jinja AST lint, render-time usage tracking.
- Writers: Markdown (single and split), self-contained HTML, standalone LaTeX project, `render-manifest.json`.
- Commands `validate`, `render`, `templates`, `layouts`.
- Docs: templates and layouts, Markdown limits, outputs, error catalogue (drift-tested against the code).
- Choices the kickoff left open, and two bugs found on the way, are in `DECISIONS.md` and `CHANGELOG.md`:
  `md_escape` mishandled a bare `.` or `)` (found by a property test), and the CI TeX Live list lacked `ulem`.

## Verification

| Check | Result |
|---|---|
| `make check` (ruff format and lint, mypy strict, pytest) | passes; 906 tests, coverage 97.7 % (gate 90 %) |
| `make test-integration` | 9 passed: the golden LaTeX project and a bundle of hostile text compile with pdfLaTeX, XeLaTeX and LuaLaTeX (Debian's TeX Live 2023, `latexmk`) |
| Docs (`sphinx-build -W`) | builds without warnings |
| Clean install | the built wheel, installed in a fresh Python 3.12 venv, renders a corpus bundle to md, html and tex; it contains the built-in template and layout |
| Hypothesis | the Markdown escape property also ran once with 30,000 examples without a counterexample |
| GitHub Actions matrix | run 38012617081 (workflow_dispatch on `5c2ecee`): 31 of 31 jobs green, no failed step in any job (test on 3 OSes x Python 3.12 to 3.15 with 906 passed and 97.68 % coverage, lowest, lint, docs, examples, pandoc, pdf-weasyprint, pdf-latex). The `pdf-latex` jobs ran 7 tests each on Linux, macOS and Windows (6 compiles = 3 engines x 2 projects, plus the smoke test); they fail instead of skipping when TeX is missing |

## Not verified yet

- `ci.yml` runs only on pull requests and on pushes to `main`, so pushing the branch starts nothing. I started the run above with `gh workflow run ci.yml --ref s2/templates-validation-writers` and did not open a pull request; opening it will run the matrix again on the final commit.
- Local Python is 3.12 only; other Python versions, macOS and Windows run in CI only.
- The LaTeX compile tests ran here against Debian's TeX Live 2023. CI installs the current TeX Live from
  `.github/tl_packages`; each package name and collection was checked against `texlive.tlpdb`.
- The golden and compat HTML hide the SVG of drawn math (`<math-svg>`), because its bytes depend on the matplotlib
  build. The drawing itself is tested in `tests/unit/render/test_math.py`, not compared with a reference image.
- `generic@1` renders what the outline lists, so the expected renders of the compat cases leave out the values
  their outlines omit (19 in `full-kinds`). `tests/golden/` renders every kind.

## Open items handed to later phases

1. **S3:** designed layouts `default@1` and `modern@1`; PDF engines (WeasyPrint, LaTeX); exit code 3 for a missing
   system dependency; add `default@1` renders and the PDF text hash to the compat cases; re-check the Windows
   `pdf-weasyprint` jobs (`continue-on-error` until then).
2. **S3:** `minimal@1` is the default layout until `default@1` exists, so a bundle that names `default@1` needs an
   explicit `-l` today.
3. **Pages:** the `docs` workflow failed on `main` at `configure-pages` before the Pages source was set to GitHub
   Actions; check whether it passes after the S1 merge, otherwise it is S6 work.
4. `.github/tl_packages` still lists packages for later layouts (`siunitx`, `tcolorbox`, `biblatex`, ...); S3 should
   prune or confirm them.

## Next

1. Open the pull request for `s2/templates-validation-writers` (I do not merge) and review it.
2. Start S3 on a new branch from the updated `main`.

## Blocked / questions

None.

## Record: HG-S0 (answered, 2026-10-09)

- Repository public, Pages source = GitHub Actions: yes.
- ADR-0001 to ADR-0011: approve all, including (a) ZIP bundle with a JSON manifest and (b) semantic keys with
  typed values.
- Python 3.15: (a) keep experimental until wheels exist.
