"""The code of ``docs/quickstart.md`` runs as written and makes the files the page says it makes."""

from __future__ import annotations

import re
import shlex
import shutil
import zipfile
from pathlib import Path

import matplotlib
import pytest
from typer.testing import CliRunner

from scireport import check_bundle, open_bundle
from scireport.cli import app

PAGE = Path(__file__).resolve().parents[2] / 'docs' / 'quickstart.md'
FENCE = re.compile(r'^```(?P<info>[^\n`]*)\n(?P<body>.*?)^```$', re.MULTILINE | re.DOTALL)
YAML_PATH = re.compile(r'^# (?P<path>\S+)\n')


def page_blocks() -> list[tuple[str, str]]:
  """Return every fenced code block of the quickstart page, in order.

  Returns
  -------
  list of tuple of str
      The info string (``python``, ``console``, ...) and the body of each block.
  """
  text = PAGE.read_text(encoding='utf-8')
  return [(m['info'].strip(), m['body']) for m in FENCE.finditer(text)]


def run_console(body: str, runner: CliRunner) -> int:
  """Run the shell lines of a ``console`` block that this test can reproduce.

  Lines that start with ``$ scireport`` run through the Typer app, except the ones that make a
  PDF (they need pango or TeX Live). ``mkdir -p`` and ``cp`` are done in Python. Every other
  line, such as installing the package, is left alone.

  Parameters
  ----------
  body : str
      The text inside the fence.
  runner : CliRunner
      Runs the command line application in process.

  Returns
  -------
  int
      How many lines were run.

  Raises
  ------
  AssertionError
      When a ``scireport`` command exits with a code other than 0.
  """
  ran = 0
  for line in body.splitlines():
    if not line.startswith('$ '):
      continue
    words = shlex.split(line[2:])
    if words[0] == 'scireport' and 'pdf' not in words:
      result = runner.invoke(app, ['--log-level', 'WARNING', *words[1:]])
      assert result.exit_code == 0, f'{line}\n{result.output}'
    elif words[0] == 'mkdir':
      Path(words[-1]).mkdir(parents=True, exist_ok=True)
    elif words[0] == 'cp':
      shutil.copy(words[1], words[2])
    else:
      continue
    ran += 1
  return ran


def test_the_quickstart_runs_as_written(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
  monkeypatch.chdir(tmp_path)
  monkeypatch.setenv('MPLBACKEND', 'Agg')
  matplotlib.use('Agg')
  namespace: dict[str, object] = {'__name__': '__quickstart__'}
  runner = CliRunner()
  python_blocks = commands = yaml_files = 0
  for info, body in page_blocks():
    if info == 'python':
      exec(compile(body, str(PAGE), 'exec'), namespace)
      python_blocks += 1
    elif info == 'console':
      commands += run_console(body, runner)
    elif info == 'yaml' and (named := YAML_PATH.match(body)):
      target = Path(named['path'])
      target.write_text(body[named.end() :], encoding='utf-8', newline='\n')
      yaml_files += 1

  assert python_blocks >= 3
  assert commands >= 6
  assert yaml_files == 1

  # The files the page says appear.
  assert Path('crossmatch.scireport.zip').is_file()
  for name in ('md/report.md', 'md/figures/crossmatch.sep_hist.png', 'html/report.html'):
    assert (tmp_path / 'out' / name).is_file(), name
  assert (tmp_path / 'out' / 'render-manifest.json').is_file()
  assert (tmp_path / 'crossmatch.scireport' / 'scireport.json').is_file()
  assert (tmp_path / 'out-yaml' / 'md' / 'report.md').is_file()
  assert Path('my-report.scireport.zip').is_file()

  # The Markdown carries what the page shows.
  markdown = (tmp_path / 'out' / 'md' / 'report.md').read_text(encoding='utf-8')
  assert '**N pairs:** 8 pairs' in markdown
  assert '**Sep mean:** 0.46 ± 0.07 arcsec' in markdown
  assert '![Histogram of the separations of the matched pairs, in arcsec.]' in markdown

  # pack pins the template and the layout, as the page says.
  with zipfile.ZipFile('my-report.scireport.zip') as archive:
    assert archive.namelist() == ['assets/figures/sep_hist.png', 'scireport.json']
  with open_bundle('my-report.scireport.zip') as packed:
    assert packed.manifest.render.template == 'generic@1'
    assert packed.manifest.render.layout == 'default@1'
    assert check_bundle(packed).ok
