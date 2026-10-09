# ADR-0009: Agent kit (skill + MCP server) and documentation site

- Status: Proposed (approval at HG-S0)
- Date: 2026-10-09

## Decision

**Skill** (package data `scireport/agent/skill/scireport/`): `SKILL.md` follows the monorepo frontmatter rules
(`name` equals the folder name; `description` at most 1024 characters) and `references/` holds `data-file.md`,
`python-api.md`, `cli.md`, `templates-and-layouts.md`, `preprocessors.md`, `mplstyle.md`, `errors.md`,
`recipes.md` (including "md for LLMs + one PDF for humans" and CI). Tables are generated from code by
`make skill` and drift-tested. `scireport agent install-skill --dest DIR [--check]` installs it.

**MCP server** (`scireport[mcp]`, official `mcp` SDK, FastMCP, stdio): tools `list_templates`,
`describe_template`, `list_layouts`, `list_preprocessors`, `describe_preprocessor`, `spec_schema`,
`inspect_bundle`, `validate_bundle`, `render_bundle`, `error_help`; resources are the skill pages; file access
is restricted to `--root`; `scireport agent mcp-config` prints a `.mcp.json` snippet. The SDK API is verified
(Context7) before coding.

**Docs:** Sphinx, MyST, furo, autodoc with napoleon, sphinxcontrib-typer for the CLI, generated spec, error-code
and pre-processor pages, an example gallery for both layouts. `sphinx-llms-txt` produces `llms.txt` and
`llms-full.txt`; `sphinx-markdown-builder` produces a `.md` file per page, published next to the HTML. Deployed
with GitHub Actions Pages to `https://nmcardoso.github.io/scireport/`.

## Consequences

Coding agents in consuming projects get instructions that cannot drift from the code.
