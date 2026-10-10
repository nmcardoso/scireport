"""The LaTeX engine: a LaTeX project in, PDF bytes out, through ``latexmk`` (ADR-0004, ADR-0010).

The project the ``tex`` writer produces is written to a temporary directory and compiled there
with ``latexmk -interaction=nonstopmode -halt-on-error -file-line-error``, with the engine chosen
by ``--pdf``/``-pdflua``/``-pdfxe``. Two things make the PDF reproducible: ``SOURCE_DATE_EPOCH``
(with ``FORCE_SOURCE_DATE=1``) fixes the dates and the file id that TeX writes, and the project is
always compiled from a clean directory. The log is read afterwards: errors become ``E902``
issues with ``file:line``, missing characters ``W902`` and the layout's own fallback notice
``W901``.

``latexmk`` is a local program, so there is no remote service to rate-limit.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Mapping
from pathlib import Path

from scireport.errors import Issue, MissingDependencyError, PdfError
from scireport.logging_utils import get_logger
from scireport.render.pdf import EPOCH_DEFAULT, LATEX_ENGINES

log = get_logger(__name__)

MAIN = 'report'
TIMEOUT_SECONDS = 600
LATEXMK_FLAGS = {'pdflatex': '-pdf', 'lualatex': '-pdflua', 'xelatex': '-pdfxe'}
INSTALL_HINT = (
  'Install TeX Live (https://tug.org/texlive/): sudo apt install texlive-latex-extra '
  'texlive-luatex texlive-xetex latexmk texlive-fonts-recommended on Debian or Ubuntu; '
  'brew install --cask mactex-no-gui on macOS; the TeX Live installer on Windows.'
)
_ERROR_RE = re.compile(r'^(?P<file>[^\s:][^:]*):(?P<line>\d+): (?P<message>.+)$', re.MULTILINE)
_BANG_RE = re.compile(r'^! (?P<message>.+)$', re.MULTILINE)
_MISSING_FILE_RE = re.compile(r"File [`'](?P<name>[^']+)' not found")
_MISSING_CHAR_RE = re.compile(
  r'Missing character: There is no (?P<char>.) \(U\+(?P<code>[0-9A-F]+)\)'
)


def latex_available(engine: str = 'lualatex') -> bool:
  """Say whether ``latexmk`` and the TeX engine are on the path.

  Parameters
  ----------
  engine : str, default='lualatex'
      One of ``lualatex``, ``xelatex`` or ``pdflatex``.

  Returns
  -------
  bool
      True when both programs are found.
  """
  return shutil.which('latexmk') is not None and shutil.which(engine) is not None


def latex_version(engine: str) -> str:
  """Return the first line of ``<engine> --version``, or an empty string when it cannot run."""
  program = shutil.which(engine)
  if program is None:
    return ''
  try:
    done = subprocess.run(
      [program, '--version'], capture_output=True, text=True, timeout=30, check=False
    )
  except (OSError, subprocess.SubprocessError):
    return ''
  return done.stdout.splitlines()[0].strip() if done.stdout else ''


def source_date_epoch(date: str | None) -> int:
  """Choose the ``SOURCE_DATE_EPOCH`` of a build.

  Parameters
  ----------
  date : str or None
      The ``meta.date`` of the bundle (ISO 8601), or None.

  Returns
  -------
  int
      The environment's ``SOURCE_DATE_EPOCH`` when it is set; otherwise midnight UTC of ``date``;
      otherwise 1980-01-01. Never the wall clock.
  """
  given = os.environ.get('SOURCE_DATE_EPOCH', '')
  if given.isdecimal():
    return int(given)
  if date:
    from datetime import UTC, datetime

    try:
      stamp = datetime.fromisoformat(date.replace('Z', '+00:00'))
    except ValueError:
      return EPOCH_DEFAULT
    return int((stamp if stamp.tzinfo else stamp.replace(tzinfo=UTC)).timestamp())
  return EPOCH_DEFAULT


def compile_project(
  files: Mapping[str, bytes], *, engine: str, epoch: int
) -> tuple[bytes, list[Issue]]:
  """Compile a LaTeX project to PDF.

  Parameters
  ----------
  files : mapping
      The project: relative path to bytes, including ``report.tex``.
  engine : {'lualatex', 'xelatex', 'pdflatex'}
      The TeX engine.
  epoch : int
      The ``SOURCE_DATE_EPOCH`` of the build.

  Returns
  -------
  tuple
      The PDF bytes and the warnings found in the log (``W901``, ``W902``).

  Raises
  ------
  MissingDependencyError
      With ``E901`` when ``latexmk`` or the engine is not installed, or a TeX package is missing.
  PdfError
      With ``E902`` (carrying the errors of the log, each with ``file:line``) when the compile
      fails or times out.
  """
  if engine not in LATEX_ENGINES:
    raise PdfError(f'unknown TeX engine {engine!r}', code='E902')
  for program in ('latexmk', engine):
    if shutil.which(program) is None:
      raise MissingDependencyError(
        f'the LaTeX PDF engine needs {program}, which is not installed or not on the path',
        code='E901',
        hint=INSTALL_HINT,
      )
  with tempfile.TemporaryDirectory(prefix='scireport-tex-') as scratch:
    root = Path(scratch)
    for name, data in files.items():
      target = root / name
      target.parent.mkdir(parents=True, exist_ok=True)
      target.write_bytes(data)
    log_text = _run(root, engine, epoch)
    pdf = root / f'{MAIN}.pdf'
    if not pdf.is_file():
      raise _failure(log_text)
    issues = _warnings(log_text)
    return pdf.read_bytes(), issues


def parse_log(text: str) -> list[Issue]:
  """Read the errors of a TeX log.

  Parameters
  ----------
  text : str
      The contents of ``report.log``.

  Returns
  -------
  list of Issue
      One ``E902`` issue per error, with ``file:line`` as its location; a missing package or file
      is ``E901`` with the name in the message.
  """
  issues: list[Issue] = []
  seen: set[str] = set()
  for match in _ERROR_RE.finditer(text):
    message = match.group('message').strip()
    key = f'{match.group("file")}:{match.group("line")}:{message}'
    if key in seen:
      continue
    seen.add(key)
    code = 'E901' if _MISSING_FILE_RE.search(message) else 'E902'
    issues.append(Issue(code, message, location=f'{match.group("file")}:{match.group("line")}'))
  if not issues:
    for match in _BANG_RE.finditer(text):
      message = match.group('message').strip()
      code = 'E901' if _MISSING_FILE_RE.search(message) else 'E902'
      issues.append(Issue(code, message))
  return issues


def _run(root: Path, engine: str, epoch: int) -> str:
  """Run latexmk in ``root`` and return the text of the log, which may be empty."""
  env = {
    **os.environ,
    'SOURCE_DATE_EPOCH': str(epoch),
    'FORCE_SOURCE_DATE': '1',
    'TEXMFVAR': str(root / '.texmf-var'),
  }
  command = [
    'latexmk',
    LATEXMK_FLAGS[engine],
    '-interaction=nonstopmode',
    '-halt-on-error',
    '-file-line-error',
    f'{MAIN}.tex',
  ]
  log.info('compiling the LaTeX project with latexmk and %s', engine)
  try:
    done = subprocess.run(
      command,
      cwd=root,
      env=env,
      capture_output=True,
      text=True,
      encoding='utf-8',
      errors='replace',
      timeout=TIMEOUT_SECONDS,
      check=False,
    )
  except subprocess.TimeoutExpired as exc:
    raise PdfError(
      f'latexmk did not finish in {TIMEOUT_SECONDS} s', code='E902', hint='Check for a loop.'
    ) from exc
  except OSError as exc:
    raise MissingDependencyError(
      f'latexmk cannot be started: {exc}', code='E901', hint=INSTALL_HINT
    ) from exc
  log_file = root / f'{MAIN}.log'
  text = log_file.read_text(encoding='utf-8', errors='replace') if log_file.is_file() else ''
  log.debug('latexmk exit code %s', done.returncode)
  return text or done.stdout + done.stderr


def _failure(log_text: str) -> PdfError | MissingDependencyError:
  """Build the exception for a compile that produced no PDF."""
  issues = parse_log(log_text)
  missing = [i for i in issues if i.code == 'E901']
  if missing:
    names = ', '.join(
      sorted({m.group('name') for i in missing if (m := _MISSING_FILE_RE.search(i.message))})
    )
    return MissingDependencyError(
      f'LaTeX cannot find {names}',
      code='E901',
      hint=f'Install the TeX Live package that provides it (tlmgr install ...). {INSTALL_HINT}',
    )
  if not issues:
    issues = [Issue('E902', 'latexmk produced no PDF and the log has no error line')]
  return PdfError(f'LaTeX failed: {issues[0].describe()}', code='E902', issues=issues)


def _warnings(log_text: str) -> list[Issue]:
  """Collect the warnings of a successful compile."""
  issues: list[Issue] = []
  if 'W901:' in log_text:
    issues.append(
      Issue(
        'W901',
        'pdfLaTeX cannot load the OpenType fonts of the layout; it used TeX fonts instead',
        hint='Use LuaLaTeX or XeLaTeX (--latex-engine) for the designed look.',
      )
    )
  chars = sorted(
    {f'{m.group("char")} (U+{m.group("code")})' for m in _MISSING_CHAR_RE.finditer(log_text)}
  )
  if chars:
    issues.append(
      Issue(
        'W902',
        f'the font has no glyph for {len(chars)} character(s): {", ".join(chars[:8])}',
        hint='The characters are missing from the PDF.',
      )
    )
  return issues
