# STATUS

**Phase:** S1 (spec models and bundle I/O). Implementation complete on branch `s1/spec-and-bundle`, pull request
<https://github.com/nmcardoso/scireport/pull/1> open. **No human gate in S1.** Next: merge the PR, then S2.

## Done in S1

- Precondition: HG-S0 answered (below). ADR-0001 to ADR-0011 set to *Accepted*. Python 3.15 re-checked:
  `pyyaml` 6.0.3 still has no cp315 wheel, so the 3.15 jobs stay `continue-on-error` (DECISIONS 2026-10-09).
- `scireport.spec`: manifest blocks and the 16 kinds, key grammar, canonicalisation of bare JSON, cross-reference
  checks, frozen `spec/schemas/data-1.0.schema.json` with a drift test, migration framework with the 1.0
  baseline, `E501` for a bundle from a newer spec.
- `scireport.bundle`: directory, ZIP and single-file forms; hashes; byte-reproducible ZIPs; zip-slip, symlink and
  size-cap rejection; lazy verified reads; strict YAML for hand-authored directories; atomic writes.
- `Report` builder, and the commands `spec (version|schema|kinds|migrate)`, `pack`, `unpack`, `inspect`.
- Compat corpus `tests/compat/spec-1.0/` (minimal, text-only, full-kinds) frozen by `FROZEN.sha256`.
- Choices the plan left open are in `DECISIONS.md` (all dated 2026-10-09, approver "S1").

## Verification

| Check | Result |
|---|---|
| `make check` (ruff format and lint, mypy strict, pytest) | passes; 353 tests, coverage 100 % (gate 90 %) |
| Lower bounds (`uv sync --resolution lowest-direct --group dev`, local copy) | 349 passed, 1 skipped (needs a git checkout) |
| Local Python | 3.12 only; 3.13 to 3.15 and macOS/Windows are covered by CI only |
| GitHub Actions matrix | see the PR checks (filled in below when the run finishes) |

## Not verified yet

- Windows and macOS runs of the new code (path handling, `newline='\n'`, the symlink test is skipped on Windows).
- Byte-identical ZIPs across platforms: guaranteed for one Python and zlib only (DECISIONS: DEFLATED entries).
  The compat fixtures are committed bytes that tests only read, so this does not affect them.

## Open items handed to later phases

1. **S2:** `pack` should pin the resolved layout and template versions into the bundle (ADR-0008); there is no
   registry to resolve against before S2.
2. **S2:** extend `scireport.errors.CODES` with the template, lint and render codes (E1xx missing key by template
   field, E3xx table schema against a template, W4xx unused key, W6xx math); the compat cases gain expected
   `.md`, canonical `.html`, `.tex` and PDF text hash.
3. **Pages:** the `docs` workflow failed on its two runs on `main` at the `configure-pages` step ("Get Pages
   site failed ... verify that the repository has Pages enabled"), before the Pages source was set to GitHub
   Actions. It runs again when this PR is merged to `main`; if it still fails, that is S6 work.

## Blocked / questions

None. (The earlier question about the uncommitted 3.15 edit in `ci.yml` was answered: restore the flags.)

## Record: HG-S0 (answered, 2026-10-09)

- Repository public, Pages source = GitHub Actions: yes.
- ADR-0001 to ADR-0011: approve all, including (a) ZIP bundle with a JSON manifest and (b) semantic keys with
  typed values.
- Python 3.15: (a) keep experimental until wheels exist.
