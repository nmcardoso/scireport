"""Every code has a "what to do" text, and no text outlives its code."""

from __future__ import annotations

import re

from scireport.error_help import HELP
from scireport.errors import CODES


def test_help_covers_exactly_the_catalogue() -> None:
  assert list(HELP) == list(CODES)


def test_each_text_is_one_to_three_plain_sentences() -> None:
  for code, text in HELP.items():
    assert 40 <= len(text) <= 330, code
    assert text == text.strip() and '\n' not in text, code
    assert 'TODO' not in text, code


def test_texts_only_mention_codes_that_exist() -> None:
  for code, text in HELP.items():
    assert set(re.findall(r'\b[EW]\d{3}\b', text)) <= set(CODES), code
