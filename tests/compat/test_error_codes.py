"""Error codes keep their meaning: none is removed or retitled (ADR-0005, ADR-0008).

``error-codes.json`` maps each released code to its title, written once from
``scireport.errors.CODES``. A code is never reused for another meaning, so a title can be
sharpened only in the help text (``scireport.error_help``), not here. A new code is appended to
the file in the commit that adds it; existing entries are never edited.
"""

from __future__ import annotations

import json
from pathlib import Path

from scireport.errors import CODES

FROZEN = json.loads(Path(__file__).with_name('error-codes.json').read_text(encoding='utf-8'))


def test_no_code_was_removed() -> None:
  assert sorted(set(FROZEN) - set(CODES)) == [], 'a released error code was removed (ADR-0005)'


def test_no_code_was_retitled() -> None:
  changed = {
    code: (title, CODES[code]) for code, title in FROZEN.items() if CODES.get(code) != title
  }
  assert changed == {}, 'a released error code changed its title: its meaning is frozen'


def test_every_code_is_recorded() -> None:
  missing = sorted(set(CODES) - set(FROZEN))
  assert missing == [], f'append the new code(s) to tests/compat/error-codes.json: {missing}'
