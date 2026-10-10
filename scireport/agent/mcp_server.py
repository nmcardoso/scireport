"""The MCP server: scireport's catalogue, validation and rendering as tools for agents (ADR-0009).

``scireport mcp serve --root DIR`` speaks the Model Context Protocol over standard input and
output. Its tools describe what scireport offers (templates, layouts, pre-processors, the schema,
error codes) and work on bundles (inspect, validate, render). Its resources are the pages of the
packaged skill, so an agent that has the server also has the instructions.

**File access is restricted to ``--root``.** Every path an agent gives (a bundle, an output
directory, a template or layout directory) is resolved against the root and refused with
``E412`` when it leaves it, symbolic links included. Pre-processor references that import code
(``module:function``) are never allowed here. Problems in a bundle are returned as data
(``{"ok": false, "issues": [...]}``), never as a protocol error, so an agent can read the codes
and fix the file.

The SDK (``scireport[mcp]``, the official ``mcp`` package) is imported only when a server is
created. In SDK 2.x the class that SDK 1.x called ``FastMCP`` is ``MCPServer``.
"""

from __future__ import annotations

import functools
import threading
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from scireport.agent import catalogue
from scireport.agent.skill import SKILL_DIR, skill_files
from scireport.bundle import open_bundle
from scireport.bundle.summary import inspect_bundle as summarise_bundle
from scireport.errors import MissingDependencyError, ScireportError
from scireport.logging_utils import get_logger
from scireport.render.pipeline import check_bundle, render_bundle

if TYPE_CHECKING:
  from mcp.server import MCPServer

log = get_logger(__name__)

SERVER_NAME = 'scireport'
INSTRUCTIONS = (
  'scireport renders one data file (a report bundle) with a template and a layout to Markdown, '
  'HTML, LaTeX and PDF. Read the resource skill://scireport/SKILL.md first. Describe a template '
  'before writing a bundle for it, validate before rendering, and read the error codes with '
  'error_help. Paths are relative to the server root.'
)

_LOCK = threading.Lock()
"""Rendering changes process-wide state (matplotlib, SOURCE_DATE_EPOCH), so one at a time."""


def resolve_in_root(root: Path, name: str) -> Path:
  """Resolve a path an agent gave against the server root.

  Parameters
  ----------
  root : pathlib.Path
      The directory the server may use (already resolved).
  name : str
      A path relative to ``root``, or an absolute path inside it.

  Returns
  -------
  pathlib.Path
      The resolved path, symbolic links followed; it need not exist yet.

  Raises
  ------
  ScireportError
      With ``E412`` when the path leaves ``root``.
  """
  candidate = Path(name)
  path = (candidate if candidate.is_absolute() else root / candidate).resolve()
  if not path.is_relative_to(root):
    raise ScireportError(
      f'{name!r} is outside the directory this server may use',
      code='E412',
      hint='Give a path under the server root.',
    )
  return path


def create_server(root: Path) -> MCPServer:
  """Build the MCP server for a root directory.

  Parameters
  ----------
  root : pathlib.Path
      The only directory the tools may read and write.

  Returns
  -------
  mcp.server.MCPServer
      The server; call ``run()`` to serve over stdio, or connect an in-memory ``mcp.Client`` to
      it in a test.

  Raises
  ------
  MissingDependencyError
      With ``E904`` (exit code 3) when ``scireport[mcp]`` is not installed.
  """
  try:
    from mcp.server import MCPServer
  except ImportError:
    raise MissingDependencyError(
      'the MCP server needs the mcp package, and scireport[mcp] is not installed',
      code='E904',
      hint="Install the extra: uv add 'scireport[mcp]' (or pip install 'scireport[mcp]').",
    ) from None
  base = root.resolve()
  server = MCPServer(SERVER_NAME, instructions=INSTRUCTIONS)
  _add_catalogue_tools(server)
  _add_bundle_tools(server, base)
  _add_skill_resources(server)
  return server


def serve(root: Path) -> None:
  """Serve over standard input and output until the client disconnects.

  Parameters
  ----------
  root : pathlib.Path
      The only directory the tools may read and write.
  """
  server = create_server(root)
  log.info('serving scireport over stdio, root %s', root.resolve())
  server.run('stdio')


def _as_data[**P](func: Callable[P, dict[str, Any]]) -> Callable[P, dict[str, Any]]:
  """Return problems of a scireport call as ``{"ok": false, "issues": [...]}``."""

  @functools.wraps(func)
  def wrapper(*args: P.args, **kwargs: P.kwargs) -> dict[str, Any]:
    try:
      return func(*args, **kwargs)
    except ScireportError as exc:
      return {'ok': False, 'exit_code': exc.exit_code, 'issues': [i.to_dict() for i in exc.issues]}
    except OSError as exc:
      return {
        'ok': False,
        'exit_code': 1,
        'issues': [{'code': 'E410', 'severity': 'error', 'message': str(exc)}],
      }

  return wrapper


def _add_catalogue_tools(server: MCPServer) -> None:
  """Register the tools that describe scireport itself."""

  @server.tool()
  @_as_data
  def list_templates() -> dict[str, Any]:
    """List the report templates: reference (name@version), title, formats and origin."""
    return {'templates': catalogue.list_templates_data()}

  @server.tool()
  @_as_data
  def describe_template(ref: str) -> dict[str, Any]:
    """Describe a template: the values it reads (key pattern, kinds, required, table columns).

    Parameters
    ----------
    ref : str
        A template name (`generic`), name@version (`generic@1`) or a directory under the root.
    """
    return catalogue.describe_template(ref)

  @server.tool()
  @_as_data
  def list_layouts() -> dict[str, Any]:
    """List the layouts with their formats, PDF engines and options (name, type, default)."""
    rows = catalogue.list_layouts_data()
    for row in rows:
      detail = catalogue.describe_layout(row['ref'])
      row['pdf_engines'] = detail['pdf_engines']
      row['options'] = detail['options']
    return {'layouts': rows}

  @server.tool()
  @_as_data
  def list_preprocessors() -> dict[str, Any]:
    """List the registered pre-processors (steps that make figures and tables from tables)."""
    return {'preprocessors': catalogue.list_preprocessors_data()}

  @server.tool()
  @_as_data
  def describe_preprocessor(name: str) -> dict[str, Any]:
    """Describe a pre-processor: input and output ports and the JSON Schema of its parameters.

    Parameters
    ----------
    name : str
        For example `core.histogram` or `core.histogram@1`.
    """
    return catalogue.describe_preprocessor(name)

  @server.tool()
  @_as_data
  def spec_schema() -> dict[str, Any]:
    """Return the JSON Schema of the data file (the report bundle manifest) and its version."""
    return catalogue.spec_schema()

  @server.tool()
  @_as_data
  def error_help(code: str) -> dict[str, Any]:
    """Explain an error or warning code such as `E103` or `W401`: severity, title and family.

    Parameters
    ----------
    code : str
        The code as printed by validate or render.
    """
    return catalogue.error_help(code)


def _add_bundle_tools(server: MCPServer, root: Path) -> None:
  """Register the tools that work on bundles under ``root``."""

  def reference(value: str | None) -> str | None:
    """Keep names; resolve a directory reference under the root."""
    if value is None or (
      not any(mark in value for mark in ('/', '\\')) and not value.startswith('.')
    ):
      return value
    return str(resolve_in_root(root, value))

  @server.tool()
  @_as_data
  def inspect_bundle(path: str, verify: bool = True) -> dict[str, Any]:
    """Summarise a bundle: metadata, every value with its kind, asset sizes and integrity.

    Parameters
    ----------
    path : str
        A bundle (directory, .zip or manifest file) under the server root.
    verify : bool
        Check every asset hash and size.
    """
    with open_bundle(resolve_in_root(root, path)) as bundle:
      return summarise_bundle(bundle, verify=verify)

  @server.tool()
  @_as_data
  def validate_bundle(
    path: str,
    template: str | None = None,
    layout: str | None = None,
    formats: list[str] | None = None,
    strict: bool = False,
    render: bool = True,
  ) -> dict[str, Any]:
    """Check a bundle against a template and layout; every problem is returned at once.

    Each issue has a code, the key, a JSON pointer, what was expected and found, the template
    line and a hint. Nothing is written.

    Parameters
    ----------
    path : str
        A bundle under the server root.
    template : str, optional
        Template reference; the bundle's own, else `generic@1`.
    layout : str, optional
        Layout reference; the bundle's own, else the default layout.
    formats : list of str, optional
        Formats to check (md, html, tex, pdf, docx, odt, epub); the bundle's, else all text.
    strict : bool
        Treat warnings as errors.
    render : bool
        Also render in memory to find what only a render shows.
    """
    with _LOCK, open_bundle(resolve_in_root(root, path)) as bundle:
      report = check_bundle(
        bundle,
        template=reference(template),
        layout=reference(layout),
        formats=formats,
        strict=strict,
        render=render,
        allow_import=False,
      )
    return report.to_dict()

  @server.tool(name='render_bundle')
  @_as_data
  def render_bundle_files(
    path: str,
    output: str,
    template: str | None = None,
    layout: str | None = None,
    formats: list[str] | None = None,
    options: dict[str, str] | None = None,
    markup_engine: str | None = None,
    pdf_engine: str | None = None,
    latex_engine: str | None = None,
    strict: bool = False,
  ) -> dict[str, Any]:
    """Render a bundle to files under the server root. Nothing is written when it is invalid.

    Each format goes to its own folder of `output` (md/, html/, tex/, pdf/, docx/, odt/, epub/).
    A PDF needs pango (weasyprint) or TeX Live (latex); a missing one is exit_code 3.

    Parameters
    ----------
    path : str
        A bundle under the server root.
    output : str
        A directory under the server root; created when missing.
    template : str, optional
        Template reference; the bundle's own, else `generic@1`.
    layout : str, optional
        Layout reference; the bundle's own, else the default layout.
    formats : list of str, optional
        Formats to write (md, html, tex, pdf, docx, odt, epub); the bundle's, else all text.
    options : dict, optional
        Layout options as name to value (`{"paper": "letter"}`).
    markup_engine : str, optional
        `mistletoe` (default) or `pandoc`.
    pdf_engine : str, optional
        `weasyprint` (default) or `latex`.
    latex_engine : str, optional
        `lualatex` (default), `xelatex` or `pdflatex`.
    strict : bool
        Treat warnings as errors.
    """
    target = resolve_in_root(root, output)
    with _LOCK, open_bundle(resolve_in_root(root, path)) as bundle:
      result = render_bundle(
        bundle,
        template=reference(template),
        layout=reference(layout),
        formats=formats,
        options=options,
        markup_engine=markup_engine,
        pdf_engine=pdf_engine,
        latex_engine=latex_engine,
        strict=strict,
        allow_import=False,
      )
      written = result.write(target)
    return {
      'ok': True,
      'output': target.relative_to(root).as_posix() or '.',
      'files': [p.relative_to(target).as_posix() for p in written],
      'warnings': [issue.to_dict() for issue in result.issues],
    }


def _add_skill_resources(server: MCPServer) -> None:
  """Register every page of the packaged skill as a Markdown resource."""
  for name in skill_files():
    if name.endswith('.md'):
      server.resource(
        f'skill://{SERVER_NAME}/{name}',
        name=name,
        description=f'scireport skill page {name}',
        mime_type='text/markdown',
      )(_page_reader(name))


def _page_reader(name: str) -> Callable[[], str]:
  """Return a function that reads one page of the skill when the resource is requested."""

  def read() -> str:
    return (SKILL_DIR / name).read_text(encoding='utf-8')

  return read
