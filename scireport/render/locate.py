"""Find where in a template the code that is running right now was called from.

Jinja compiles every template to Python and keeps a table from Python lines to template lines.
While a component, a filter or the ``data`` namespace runs, the calling template frame is on the
Python stack; walking up to it gives the ``file:line`` that validation errors report (ADR-0005).
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path
from types import TracebackType
from typing import Any


def current_location(roots: list[Path]) -> str | None:
  """Return ``file:line`` of the innermost template frame on the stack.

  Parameters
  ----------
  roots : list of pathlib.Path
      Template and layout directories; the file name is reported relative to the one that
      contains it.

  Returns
  -------
  str or None
      For example ``report.j2:12``, or None when no template is running.
  """
  frame = sys._getframe(1)
  while frame is not None:
    template = frame.f_globals.get('__jinja_template__')
    if template is not None:
      return _format(template.filename, template.get_corresponding_lineno(frame.f_lineno), roots)
    frame = frame.f_back  # type: ignore[assignment]
  return None


def exception_location(exc: BaseException, roots: list[Path]) -> str | None:
  """Return ``file:line`` of the innermost template frame in an exception's traceback.

  Parameters
  ----------
  exc : BaseException
      An exception raised while a template was rendering.
  roots : list of pathlib.Path
      Template and layout directories (see :func:`current_location`).

  Returns
  -------
  str or None
      The location, or None when the traceback has no template frame.
  """
  found = None
  tb: TracebackType | None = exc.__traceback__
  for frame, lineno in traceback.walk_tb(tb):
    template = frame.f_globals.get('__jinja_template__')
    if template is not None:
      found = _format(template.filename, template.get_corresponding_lineno(lineno), roots)
    elif '__jinja_exception__' in frame.f_globals:
      found = _format(frame.f_code.co_filename, lineno, roots)
  return found


def syntax_location(exc: Any, roots: list[Path]) -> str:
  """Return ``file:line`` for a Jinja syntax error.

  Parameters
  ----------
  exc : jinja2.TemplateSyntaxError
      The error; it knows its file name and line.
  roots : list of pathlib.Path
      Template and layout directories (see :func:`current_location`).

  Returns
  -------
  str
      The location.
  """
  return _format(exc.filename or exc.name or '<template>', exc.lineno, roots)


def _format(filename: str | None, lineno: int, roots: list[Path]) -> str:
  """Make the file name relative to the first root that contains it."""
  if not filename:
    return f'<template>:{lineno}'
  path = Path(filename)
  for root in roots:
    try:
      return f'{path.resolve().relative_to(root.resolve()).as_posix()}:{lineno}'
    except ValueError:
      continue
  return f'{path.name}:{lineno}'
