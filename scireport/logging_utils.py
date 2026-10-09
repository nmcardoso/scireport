"""Standardised, colour-coded logging for TUPAN subprojects (stdlib ``logging`` only).

Console line anatomy (colours are stable per module; icons/blocks give visual cues)::

    2026-11-03 14:22:05.123 │ ℹ INFO  │ ▌review.bibliometrics │ Fetched 1,234 records from ADS

Usage
-----
>>> from tupan_review.logging_utils import setup_logging, get_logger, log_rule, log_section, log_kv
>>> setup_logging(level="INFO", log_file="logs/run.log")
>>> log = get_logger(__name__)          # never "__main__": resolved to a readable name
>>> log_rule(log, "AN01 · Bibliometric trends")
>>> with log_section(log, "Querying ADS"):
...     log.info("Fetched %d records (query=%s)", 1234, "Q1")
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import os
import sys
import time
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

__all__ = [
  'setup_logging',
  'get_logger',
  'log_rule',
  'log_section',
  'log_kv',
  'module_display_name',
]

PROJECT_PACKAGES = ('tupan_review', 'tupan')  # package prefixes stripped/shortened for display
_RESET = '\033[0m'
_BOLD = '\033[1m'
_DIM = '\033[2m'
# 256-colour codes readable on both dark and light terminals (no near-black / near-white)
_MODULE_PALETTE = (
  33,
  39,
  45,
  69,
  75,
  99,
  105,
  135,
  141,
  166,
  172,
  178,
  37,
  43,
  71,
  107,
  113,
  169,
  175,
  203,
  209,
)
_LEVEL_STYLE = {  # level -> (icon, 256-colour code)
  logging.DEBUG: ('·', 244),
  logging.INFO: ('ℹ', 39),
  logging.WARNING: ('⚠', 214),
  logging.ERROR: ('✖', 196),
  logging.CRITICAL: ('‼', 201),
}
_RULE_CHAR = '─'
_SEP = ' │ '


def module_display_name(name: str) -> str:
  """Return a short, readable module name, e.g. ``tupan_review.analysis.an01_bibliometrics`` →
  ``review.an01_bibliometrics``. ``__main__`` is replaced by the running script's stem."""
  if name in ('__main__', '', None):
    script = Path(sys.argv[0]).stem if sys.argv and sys.argv[0] else 'main'
    name = script or 'main'
  parts = name.split('.')
  if parts[0] in PROJECT_PACKAGES:
    head = parts[0].replace('tupan_', '') if parts[0] != 'tupan' else 'tupan'
    tail = parts[-1] if len(parts) > 1 else ''
    return f'{head}.{tail}' if tail else head
  return '.'.join(parts[-2:]) if len(parts) > 2 else name


def _color_for(name: str) -> int:
  digest = hashlib.md5(name.encode('utf-8')).digest()  # stable across runs (unlike hash())
  return _MODULE_PALETTE[digest[0] % len(_MODULE_PALETTE)]


def _fg(code: int) -> str:
  return f'\033[38;5;{code}m'


def _use_color(stream: Any, color: bool | None) -> bool:
  if color is not None:
    return color
  if os.environ.get('NO_COLOR'):
    return False
  if os.environ.get('FORCE_COLOR'):
    return True
  return hasattr(stream, 'isatty') and stream.isatty()


class ColorFormatter(logging.Formatter):
  """Console formatter: timestamp │ icon LEVEL │ ▌module │ message (module-coloured)."""

  def __init__(self, color: bool = True, show_date: bool = True, name_width: int = 26) -> None:
    super().__init__()
    self.color = color
    self.show_date = show_date
    self.name_width = name_width

  def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:  # noqa: N802
    t = time.localtime(record.created)
    base = time.strftime('%Y-%m-%d %H:%M:%S' if self.show_date else '%H:%M:%S', t)
    return f'{base}.{int(record.msecs):03d}'

  def format(self, record: logging.LogRecord) -> str:
    ts = self.formatTime(record)
    icon, lcol = _LEVEL_STYLE.get(record.levelno, ('•', 250))
    level = f'{icon} {record.levelname:<8s}'
    mod = module_display_name(record.name)
    mod_txt = f'▌{mod:<{self.name_width}s}'
    msg = record.getMessage()
    if getattr(record, 'is_rule', False):  # horizontal rule records
      line = msg
      return f'{_BOLD}{_fg(_color_for(mod))}{line}{_RESET}' if self.color else line
    if record.exc_info:
      msg = f'{msg}\n{self.formatException(record.exc_info)}'
    if not self.color:
      return f'{ts}{_SEP}{level}{_SEP}{mod_txt}{_SEP}{msg}'
    mcol = _fg(_color_for(mod))
    return (
      f'{_DIM}{ts}{_RESET}{_SEP}{_fg(lcol)}{_BOLD}{level}{_RESET}{_SEP}'
      f'{mcol}{_BOLD}{mod_txt}{_RESET}{_SEP}{mcol}{msg}{_RESET}'
    )


class PlainFormatter(logging.Formatter):
  """File formatter: ISO timestamp | LEVEL | module | message (no ANSI codes)."""

  def format(self, record: logging.LogRecord) -> str:
    ts = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(record.created))
    msg = record.getMessage()
    if record.exc_info:
      msg = f'{msg}\n{self.formatException(record.exc_info)}'
    mod = module_display_name(record.name)
    return f'{ts}.{int(record.msecs):03d} | {record.levelname:<8s} | {mod} | {msg}'


class JsonLinesFormatter(logging.Formatter):
  """Machine-readable JSON lines (one object per record); extra={'kv': {...}} is merged."""

  def format(self, record: logging.LogRecord) -> str:
    payload: dict[str, Any] = {
      'ts': time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(record.created))
      + f'.{int(record.msecs):03d}',
      'level': record.levelname,
      'module': module_display_name(record.name),
      'logger': record.name,
      'msg': record.getMessage(),
    }
    kv = getattr(record, 'kv', None)
    if isinstance(kv, Mapping):
      payload.update({str(k): v for k, v in kv.items()})
    if record.exc_info:
      payload['exc'] = self.formatException(record.exc_info)
    return json.dumps(payload, default=str, ensure_ascii=False)


def setup_logging(
  level: str | int | None = None,
  log_file: str | Path | None = None,
  jsonl_file: str | Path | None = None,
  color: bool | None = None,
  show_date: bool = True,
  quiet_libraries: tuple[str, ...] = (
    'matplotlib',
    'urllib3',
    'PIL',
    'fontTools',
    'asyncio',
    'wandb',
    'h5py',
  ),
) -> logging.Logger:
  """Configure the root logger once per process. Level defaults to $TUPAN_LOG_LEVEL or INFO."""
  level = level or os.environ.get('TUPAN_LOG_LEVEL', 'INFO')
  root = logging.getLogger()
  root.setLevel(level)
  for h in list(root.handlers):
    root.removeHandler(h)
  console = logging.StreamHandler(sys.stderr)
  console.setFormatter(ColorFormatter(color=_use_color(sys.stderr, color), show_date=show_date))
  root.addHandler(console)
  if log_file:
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setFormatter(PlainFormatter())
    root.addHandler(fh)
  if jsonl_file:
    Path(jsonl_file).parent.mkdir(parents=True, exist_ok=True)
    jh = logging.FileHandler(jsonl_file, encoding='utf-8')
    jh.setFormatter(JsonLinesFormatter())
    root.addHandler(jh)
  for lib in quiet_libraries:
    logging.getLogger(lib).setLevel(logging.WARNING)
  logging.captureWarnings(True)
  return root


def get_logger(name: str | None = None) -> logging.Logger:
  """Return a logger with a readable name. Pass ``__name__``; ``__main__`` is resolved
  to the dotted module path when the file lives inside a project package."""
  if name in (None, '__main__'):
    main = sys.modules.get('__main__')
    spec = getattr(main, '__spec__', None)
    if spec is not None and getattr(spec, 'name', None):
      name = spec.name  # e.g. 'python -m tupan_review.analysis.an01' -> real module path
    else:
      name = Path(sys.argv[0]).stem if sys.argv and sys.argv[0] else 'main'
  return logging.getLogger(name)


def log_rule(
  logger: logging.Logger, title: str = '', width: int = 100, char: str = _RULE_CHAR
) -> None:
  """Emit a coloured horizontal rule with an optional centred title (phase/section separator)."""
  text = f' {title} ' if title else ''
  pad = max(width - len(text), 4)
  line = f'{char * (pad // 2)}{text}{char * (pad - pad // 2)}'
  logger.info(line, extra={'is_rule': True})


@contextlib.contextmanager
def log_section(logger: logging.Logger, title: str, level: int = logging.INFO) -> Iterator[None]:
  """Context manager logging '▶ start' and '✔ done (elapsed)' or '✖ failed' around a block."""
  t0 = time.perf_counter()
  logger.log(level, '▶ %s', title)
  try:
    yield
  except Exception:
    logger.exception('✖ %s failed after %.2f s', title, time.perf_counter() - t0)
    raise
  else:
    logger.log(level, '✔ %s done in %.2f s', title, time.perf_counter() - t0)


def log_kv(
  logger: logging.Logger, title: str, mapping: Mapping[str, Any], level: int = logging.INFO
) -> None:
  """Log a titled, aligned key–value block (also attached as structured fields for JSON logs)."""
  width = max((len(str(k)) for k in mapping), default=0)
  body = '\n'.join(f'    {str(k):<{width}s} = {v}' for k, v in mapping.items())
  logger.log(level, '%s\n%s', title, body, extra={'kv': dict(mapping)})
