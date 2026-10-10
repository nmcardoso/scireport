# MCP server

`scireport mcp serve` is a [Model Context Protocol](https://modelcontextprotocol.io/) server over standard input and
output. A coding agent that connects to it can look up what scireport offers (templates, layouts, pre-processors, the
JSON Schema of the data file, the meaning of an error code), and can inspect, validate and render bundles in a
directory you choose. Its resources are the pages of the packaged skill ([The agent skill](agent.md)), so an agent that has the
server also has the instructions.

## Install and start

The server is an optional extra and uses the official `mcp` SDK (2.x; the class that SDK 1.x called `FastMCP` is
`MCPServer`):

```console
$ uv add "scireport[mcp] @ git+https://github.com/nmcardoso/scireport"
$ scireport mcp serve --root .
```

Without the extra, the command exits with code 3 and error `E904` with the install line. Logs go to standard error;
standard output belongs to the protocol, so never print to it.

## Configure a client

`scireport agent mcp-config` prints the `.mcp.json` snippet that starts the server; `--root` sets the directory it may
use, and `--uvx` launches it through `uvx` from the GitHub repository, so nothing has to be installed first
(`--ref` picks a tag or branch):

```console
$ scireport agent mcp-config --root .
```

```json
{
  "mcpServers": {
    "scireport": {
      "command": "scireport",
      "args": ["mcp", "serve", "--root", "."]
    }
  }
}
```

```console
$ scireport agent mcp-config --uvx --ref main
```

```json
{
  "mcpServers": {
    "scireport": {
      "command": "uvx",
      "args": [
        "--from", "scireport[mcp] @ git+https://github.com/nmcardoso/scireport@main",
        "scireport", "mcp", "serve", "--root", "."
      ]
    }
  }
}
```

`scireport` never writes `.mcp.json` itself: merge the snippet into your project's file. That file may hold tokens for
other servers, so check before you commit it; the scireport entry holds none. With Claude Code the same server can be
added from the shell:

```console
$ claude mcp add scireport -- scireport mcp serve --root .
```

## Tools

| Tool | Arguments | Does |
|---|---|---|
| `list_templates` | none | the templates that can be used: name, version, formats, origin, title |
| `describe_template` | `ref` | the keys, kinds and table columns one template reads |
| `list_layouts` | none | layouts with their formats, PDF engines and options |
| `list_preprocessors` | none | the registered pre-processors |
| `describe_preprocessor` | `name` | ports and the JSON Schema of the parameters |
| `spec_schema` | none | the JSON Schema of the data file |
| `error_help` | `code` | severity, title, family and the usual fix of an error or warning code |
| `inspect_bundle` | `path`, `verify` | metadata, every value with its kind, asset sizes and the integrity check |
| `validate_bundle` | `path`, `template`, `layout`, `formats`, `strict`, `render` | every problem at once; nothing is written |
| `render_bundle` | `path`, `output`, `template`, `layout`, `formats`, `options`, `markup_engine`, `pdf_engine`, `latex_engine`, `strict` | writes one folder per format under `output`; nothing is written when the bundle is invalid |

`describe_template` before writing a bundle, `validate_bundle` before `render_bundle`, and `error_help` for any code in
an answer: that is the loop the server's instructions tell an agent to follow.

A problem in a bundle is returned as data, `{"ok": false, "issues": [...]}`, never as a protocol error, so the agent
can read the codes and fix the file. Each issue carries the code, the key, the JSON pointer, what was expected and what
was found, the template line and a hint ([Error codes](errors.md)). A successful `render_bundle` returns
`{"ok": true, "output": ..., "files": [...], "warnings": [...]}`.

## Resources

Every Markdown page of the skill is a resource with the URI `skill://scireport/<page>`, for example
`skill://scireport/SKILL.md` and `skill://scireport/references/data-file.md`. The same pages are served on this site
as one download ([The agent skill](agent.md)).

## What the server will not do

- **It stays inside `--root`.** Every path an agent gives (a bundle, an output directory, a template or layout
  directory) is resolved against the root and refused with `E412` when it leaves it, symbolic links included.
- **It never imports code.** A pre-processor written as `module:function` is refused; only registered names run.
- **It renders one bundle at a time**, because rendering changes process-wide state (matplotlib, `SOURCE_DATE_EPOCH`).
