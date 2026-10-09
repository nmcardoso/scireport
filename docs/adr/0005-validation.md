# ADR-0005: Validation reports every problem, with codes

- Status: Proposed (approval at HG-S0)
- Date: 2026-10-09

## Decision

Errors are aggregated, never first-fail. Each has a stable **code** (`E1xx` missing key, `E2xx` wrong kind,
`E3xx` table schema, `E4xx` asset or hash, `E5xx` version, `W4xx` unused key, `W6xx` math), the key and its JSON
pointer in the manifest, the expected and the found value, the template `file:line` where the key is used, and a
"did you mean" suggestion (difflib).

Template lint walks the Jinja AST (`v("key")` and `data.a.b` chains). Dynamic keys are checked at render time
through usage tracking (the MOSAICS `take`/`peek`/`leftovers` idea).

Options: `--strict` (warnings become errors) and `--json` (for agents). Exit codes: 0 ok, 1 runtime error,
2 validation error, 3 missing system dependency.

## Consequences

Codes are part of the public API (ADR-0008): they are never renumbered or reused. Agents can act on `--json`
output without parsing prose.
