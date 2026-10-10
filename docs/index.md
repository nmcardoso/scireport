# scireport

Data-centric scientific report engine. One **data file** (a report bundle), one **template** (the structure) and one
**layout** (the look) go in; Markdown, HTML, LaTeX and PDF come out, and with pandoc also Word, ODT and EPUB. The data
file is the contract: it is versioned, validated with coded errors, and every older minor version keeps rendering the
same ([Compatibility policy](compatibility.md)).

```console
$ uv add "scireport[pdf] @ git+https://github.com/nmcardoso/scireport"
$ scireport new report.scireport.yaml        # a starter data file
$ scireport render report.scireport.yaml -o out -f md -f html
```

Start with the [Quickstart](quickstart.md), read the [User guide](guide.md) for the model behind it, and look at the [Example gallery](examples.md) to
see the output of both layouts.

## For language models and coding agents

This site is written to be read by agents as well as by people. Everything below is served from the same address as
this page, and every page has a Markdown twin next to its HTML (replace `.html` by `.md`).

| What | Where |
|---|---|
| Index of the site, one line per page | [llms.txt](https://nmcardoso.github.io/scireport/llms.txt) |
| The whole site as one text file | [llms-full.txt](https://nmcardoso.github.io/scireport/llms-full.txt) |
| This page as Markdown (every other page likewise) | [index.md](https://nmcardoso.github.io/scireport/index.md) |
| The agent skill as a ZIP, to unpack into `.claude/skills/` | [scireport-skill.zip](https://nmcardoso.github.io/scireport/downloads/scireport-skill.zip) |
| The JSON Schema of the data file | [data-1.0.schema.json](https://nmcardoso.github.io/scireport/schemas/data-1.0.schema.json) |

`llms-full.txt` is built from the page sources, so the tables that are generated from the code (commands, value kinds,
error codes, pre-processors) are in it as plain text. See [The agent skill](agent.md) for the skill and [MCP server](mcp.md) for the MCP server.

```{toctree}
:caption: Getting started
:maxdepth: 1

quickstart
guide
examples
```

```{toctree}
:caption: Reference
:maxdepth: 1

spec
cli
api
errors
preprocessors
outputs
markup
pandoc
export
```

```{toctree}
:caption: Authoring
:maxdepth: 1

templates
layouts
layout-authoring
styles
```

```{toctree}
:caption: For coding agents
:maxdepth: 1

agent
mcp
```

```{toctree}
:caption: Project
:maxdepth: 1

compatibility
adr/index
conventions
changelog
```
