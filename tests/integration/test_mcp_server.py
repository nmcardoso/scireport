"""The MCP server, driven by the SDK's in-memory client (ADR-0009)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import pytest
from helpers import require_extra
from render_fixtures import kitchen_sink

from scireport import Report, write_bundle
from scireport.agent.mcp_server import resolve_in_root
from scireport.agent.skill import skill_files
from scireport.errors import ScireportError

pytestmark = [pytest.mark.integration, pytest.mark.mcp]

TOOLS = {
  'list_templates',
  'describe_template',
  'list_layouts',
  'list_preprocessors',
  'describe_preprocessor',
  'spec_schema',
  'inspect_bundle',
  'validate_bundle',
  'render_bundle',
  'error_help',
}


@pytest.fixture(autouse=True)
def _need_mcp() -> None:
  require_extra('mcp')


@pytest.fixture
def root(tmp_path: Path) -> Path:
  write_bundle(kitchen_sink(real=True), tmp_path / 'ks.scireport.zip')
  Report('Small').add_text('a.b', 'text').write(tmp_path / 'small.scireport.zip')
  return tmp_path


def run(root: Path, action: Callable[[Any], Awaitable[Any]]) -> Any:
  from mcp import Client

  from scireport.agent.mcp_server import create_server

  async def main() -> Any:
    async with Client(create_server(root)) as client:
      return await action(client)

  return asyncio.run(main())


def call(root: Path, tool: str, **arguments: object) -> dict[str, Any]:
  result = run(root, lambda client: client.call_tool(tool, arguments))
  assert result.structured_content is not None, result
  return dict(result.structured_content)


def test_the_server_offers_exactly_the_documented_tools(root: Path) -> None:
  tools = run(root, lambda client: client.list_tools()).tools
  assert {tool.name for tool in tools} == TOOLS
  assert all(tool.description for tool in tools)


def test_the_catalogue_tools_describe_scireport(root: Path) -> None:
  assert 'generic@1' in {t['ref'] for t in call(root, 'list_templates')['templates']}
  layout = call(root, 'list_layouts')['layouts'][0]
  assert layout['options'] and layout['pdf_engines']
  assert call(root, 'describe_template', ref='kitchen-sink@1')['fields']
  assert call(root, 'list_preprocessors')['preprocessors']
  assert call(root, 'describe_preprocessor', name='core.histogram')['params']
  assert call(root, 'spec_schema')['version'] == '1.0'
  info = call(root, 'error_help', code='E103')
  assert info['known'] and info['fix']


def test_unknown_names_come_back_as_data_not_as_protocol_errors(root: Path) -> None:
  result = call(root, 'describe_template', ref='nope')
  assert result['ok'] is False and result['exit_code'] == 2
  assert result['issues'][0]['code'] in {'E701', 'E504'}


def test_inspect_and_validate_a_bundle(root: Path) -> None:
  assert call(root, 'inspect_bundle', path='small.scireport.zip')['counts'] == {'text': 1}
  report = call(
    root, 'validate_bundle', path='ks.scireport.zip', template='generic@1', layout='minimal@1'
  )
  assert report['ok'] is True
  strict = call(root, 'validate_bundle', path='ks.scireport.zip', layout='minimal@1', strict=True)
  assert strict['strict'] is True


def test_render_writes_under_the_root(root: Path) -> None:
  result = call(
    root,
    'render_bundle',
    path='ks.scireport.zip',
    output='out',
    formats=['md', 'html'],
    layout='minimal@1',
    options={},
  )
  assert result['ok'] is True and result['output'] == 'out'
  assert 'html/report.html' in result['files'] and (root / 'out' / 'html' / 'report.html').is_file()


def test_an_invalid_bundle_is_not_written(root: Path) -> None:
  report = Report('T').add_text('a', 'x').set_outline(['a', 'missing.key'])
  with pytest.raises(ScireportError):
    report.build()
  broken = Report('T').add_text('a', 'x').set_render(template='nope@1')
  broken.write(root / 'broken.scireport.zip')
  result = call(root, 'render_bundle', path='broken.scireport.zip', output='o2')
  assert result['ok'] is False and not (root / 'o2').exists()


@pytest.mark.parametrize(
  ('tool', 'arguments'),
  [
    ('inspect_bundle', {'path': '../ks.scireport.zip'}),
    ('inspect_bundle', {'path': '/etc/passwd'}),
    ('render_bundle', {'path': 'small.scireport.zip', 'output': '../escaped'}),
    ('validate_bundle', {'path': 'small.scireport.zip', 'template': '../../etc/tpl'}),
    ('render_bundle', {'path': 'small.scireport.zip', 'output': 'o', 'layout': '/tmp/layout'}),
  ],
)
def test_paths_outside_the_root_are_refused(
  root: Path, tool: str, arguments: dict[str, object]
) -> None:
  result = call(root, tool, **arguments)
  assert result['ok'] is False and result['issues'][0]['code'] == 'E412'
  assert not (root.parent / 'escaped').exists()


def test_a_symlink_cannot_leave_the_root(
  root: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
  outside = tmp_path_factory.mktemp('outside')
  write_bundle(kitchen_sink(), outside / 'x.scireport.zip')
  (root / 'link').symlink_to(outside)
  result = call(root, 'inspect_bundle', path='link/x.scireport.zip')
  assert result['issues'][0]['code'] == 'E412'


def test_resolve_in_root_accepts_absolute_paths_inside(root: Path) -> None:
  base = root.resolve()
  assert resolve_in_root(base, str(base / 'a' / 'b')) == base / 'a' / 'b'
  assert resolve_in_root(base, '.') == base
  with pytest.raises(ScireportError):
    resolve_in_root(base, '..')


def test_preprocessor_imports_are_never_allowed(root: Path) -> None:
  report = Report('T').add_text('a', 'x')
  report.add_preprocess('os:getcwd')
  report.write(root / 'evil.scireport.zip')
  result = call(root, 'validate_bundle', path='evil.scireport.zip')
  assert result['ok'] is False
  assert any(i['code'] == 'E605' for i in result['issues'])


def test_the_skill_pages_are_resources(root: Path) -> None:
  listed = run(root, lambda client: client.list_resources()).resources
  uris = {str(resource.uri) for resource in listed}
  assert uris == {f'skill://scireport/{name}' for name in skill_files() if name.endswith('.md')}
  page = run(root, lambda client: client.read_resource('skill://scireport/SKILL.md'))
  assert 'name: scireport' in page.contents[0].text


def test_the_server_instructions_point_at_the_skill(root: Path) -> None:
  from scireport.agent.mcp_server import INSTRUCTIONS

  assert 'skill://scireport/SKILL.md' in INSTRUCTIONS
  assert json.dumps(INSTRUCTIONS)
