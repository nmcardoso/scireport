"""``agent`` and ``mcp``: the skill and the MCP server for coding agents (ADR-0009)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from scireport.agent.skill import check_skill, install_skill, skill_files
from scireport.cli._common import EXIT_RUNTIME, echo_json, reporting_errors
from scireport.logging_utils import get_logger

log = get_logger(__name__)

REPOSITORY_URL = 'https://github.com/nmcardoso/scireport'
"""Where consuming projects install scireport from (never a local path)."""

agent_app = typer.Typer(
  name='agent', help='The skill and MCP configuration for coding agents.', no_args_is_help=True
)
mcp_app = typer.Typer(name='mcp', help='The MCP server.', no_args_is_help=True)

AsJson = Annotated[bool, typer.Option('--json', help='Print the result as JSON.')]


@agent_app.command('install-skill')
def install_skill_command(
  dest: Annotated[
    Path,
    typer.Option(
      '--dest', '-d', help='The skills directory of the project (for example .claude/skills).'
    ),
  ],
  check: Annotated[
    bool,
    typer.Option(
      '--check', help='Only compare the installed copy with this version; exit 1 when it differs.'
    ),
  ] = False,
  as_json: AsJson = False,
) -> None:
  """Install the scireport skill into a project's skills directory.

  Writes DEST/scireport/SKILL.md and DEST/scireport/references/. The installed copy replaces an
  earlier one. With --check nothing is written: the exit code is 0 when the installed copy is
  identical to the skill of this version, and 1 when it is missing or differs.
  """
  with reporting_errors(as_json=as_json):
    if check:
      status = check_skill(dest)
      if as_json:
        echo_json(
          {
            'ok': status.current,
            'path': status.path.as_posix(),
            'missing': list(status.missing),
            'changed': list(status.changed),
            'extra': list(status.extra),
          }
        )
      elif status.current:
        typer.echo(f'{status.path.as_posix()}: up to date')
      else:
        for label, names in (
          ('missing', status.missing),
          ('changed', status.changed),
          ('extra', status.extra),
        ):
          for name in names:
            typer.echo(f'{label}: {name}')
      if not status.current:
        raise typer.Exit(EXIT_RUNTIME)
      return
    target = install_skill(dest)
    if as_json:
      echo_json({'ok': True, 'path': target.as_posix(), 'files': skill_files()})
    else:
      typer.echo(target.as_posix())


@agent_app.command('mcp-config')
def mcp_config(
  root: Annotated[
    str, typer.Option('--root', help='The directory the server may read and write.')
  ] = '.',
  uvx: Annotated[
    bool,
    typer.Option(
      '--uvx', help='Launch through uvx from the GitHub repository (nothing to install first).'
    ),
  ] = False,
  ref: Annotated[
    str, typer.Option('--ref', help='With --uvx: the git tag or branch to install.')
  ] = 'main',
) -> None:
  """Print a .mcp.json snippet that starts the scireport MCP server.

  Merge it into the project's .mcp.json yourself; scireport never writes that file, because a
  .mcp.json may hold tokens and must not be committed by a tool.
  """
  command = ['scireport', 'mcp', 'serve', '--root', root]
  if uvx:
    source = f'scireport[mcp] @ git+{REPOSITORY_URL}@{ref}'
    command = ['uvx', '--from', source, *command]
  snippet = {'mcpServers': {'scireport': {'command': command[0], 'args': command[1:]}}}
  typer.echo(json.dumps(snippet, indent=2))


@mcp_app.command('serve')
def serve(
  root: Annotated[
    Path,
    typer.Option(
      '--root', help='The only directory the server may read and write.', file_okay=False
    ),
  ] = Path(),
) -> None:
  """Serve the scireport tools over the Model Context Protocol (standard input and output).

  Needs scireport[mcp]. Logs go to standard error; standard output belongs to the protocol.
  """
  with reporting_errors():
    from scireport.agent.mcp_server import serve as run_server

    run_server(root)
