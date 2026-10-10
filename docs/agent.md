# For coding agents: the skill and the MCP server

Both are generated from, or served by, the installed package, so they cannot describe another version.

## The skill

`scireport/agent/skill/scireport/` holds `SKILL.md` and `references/` (`data-file.md`, `python-api.md`, `cli.md`,
`templates-and-layouts.md`, `preprocessors.md`, `mplstyle.md`, `errors.md`, `recipes.md`). The tables in them
(commands and options, value kinds, manifest fields, public API, components, filters, layouts and their options,
pre-processors, error codes) are generated from the code by `make skill`; a test fails when a page is stale.

```bash
scireport agent install-skill --dest .claude/skills          # copy it into a project
scireport agent install-skill --dest .claude/skills --check  # exit 1 when the copy differs
```

`SKILL.md` follows the monorepo frontmatter rules: `name` equals the folder name and `description` has at most
1024 characters.

## The MCP server

`uv add 'scireport[mcp]'`, then `scireport mcp serve --root DIR` speaks the Model Context Protocol over standard
input and output (the official `mcp` SDK; in SDK 2.x the class once called `FastMCP` is `MCPServer`).
`scireport agent mcp-config` prints the `.mcp.json` snippet (`--uvx` launches through `uvx` from the GitHub
repository); scireport never writes that file.

| Tool | Does |
|---|---|
| `list_templates`, `describe_template` | what templates exist; the keys, kinds and table columns one reads |
| `list_layouts` | layouts with formats, PDF engines and options |
| `list_preprocessors`, `describe_preprocessor` | pre-processors; ports and the JSON Schema of the parameters |
| `spec_schema` | the JSON Schema of the data file |
| `inspect_bundle`, `validate_bundle`, `render_bundle` | work on a bundle under the root |
| `error_help` | severity, title, family and the usual fix of a code |

Problems come back as data (`{"ok": false, "issues": [...]}`), not as protocol errors. The pages of the skill are
the resources (`skill://scireport/SKILL.md`, ...). Every path is resolved against `--root` and refused with `E412`
when it leaves it, symbolic links included; a pre-processor that imports code (`module:function`) is never
allowed.
