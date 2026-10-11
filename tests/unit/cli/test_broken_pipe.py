"""A closed pipe (``scireport ... | head``) ends a command quietly."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import typer

from scireport.cli._common import reporting_errors


def test_a_broken_pipe_passes_through_the_error_reporter() -> None:
  with pytest.raises(BrokenPipeError), reporting_errors():
    raise BrokenPipeError(32, 'Broken pipe')


def test_other_os_errors_are_still_reported(caplog: pytest.LogCaptureFixture) -> None:
  with pytest.raises(typer.Exit) as caught, reporting_errors():
    raise PermissionError(13, 'denied')
  assert caught.value.exit_code == 1
  assert 'denied' in caplog.text


@pytest.mark.parametrize('command', ['layouts', 'preprocessors'])
def test_the_console_entry_point_exits_quietly_when_the_reader_is_gone(
  command: str, tmp_path: Path
) -> None:
  script = 'from scireport.cli import run; run()'
  proc = subprocess.Popen(
    [sys.executable, '-c', script, command],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd=tmp_path,
  )
  assert proc.stdout is not None
  proc.stdout.close()
  _, stderr = proc.communicate(timeout=120)
  assert stderr.decode() == ''
  assert proc.returncode == 1
