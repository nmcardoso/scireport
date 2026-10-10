"""Read the text of a PDF and reduce it to what does not depend on layout or pagination."""

from __future__ import annotations

import io
import re
import unicodedata

from pypdf import PdfReader

_PAGE_NUMBER = re.compile(r'Page\s+\d+\s*/\s*\d+')
_WORD = re.compile(r'[^\W\d_]{4,}', re.UNICODE)


def pdf_text(data: bytes) -> str:
  """Return the text of every page of a PDF, in reading order, one page per paragraph.

  Parameters
  ----------
  data : bytes
      The PDF.

  Returns
  -------
  str
      The extracted text.
  """
  reader = PdfReader(io.BytesIO(data))
  return '\n\n'.join(page.extract_text() or '' for page in reader.pages)


def pages(data: bytes) -> int:
  """Return the number of pages of a PDF."""
  return len(PdfReader(io.BytesIO(data)).pages)


def letters(text: str) -> str:
  """Reduce text to its lower-case letters and digits.

  Line breaks, hyphenation, spacing, punctuation, ligatures and case all differ between engines
  and TeX Live versions without the content differing; the characters that remain do not.
  ``Page n / N`` is dropped first, because it depends on pagination.

  Parameters
  ----------
  text : str
      Extracted text.

  Returns
  -------
  str
      Letters and digits only, in order.
  """
  text = unicodedata.normalize('NFKC', _PAGE_NUMBER.sub('', text)).lower()
  return ''.join(char for char in text if char.isalnum())


def words(text: str) -> set[str]:
  """Return the distinct lower-case words of four letters or more of a text.

  Parameters
  ----------
  text : str
      Any text; Markdown syntax does not matter because only runs of letters are kept.

  Returns
  -------
  set of str
      The words.
  """
  return {word.lower() for word in _WORD.findall(unicodedata.normalize('NFKC', text))}


_COMMENT = re.compile(r'<!--.*?-->', re.DOTALL)
_IMAGE = re.compile(r'!\[[^\]]*\]\([^)]*\)')
_MATH = re.compile(r'\$\$.*?\$\$|\$[^$\n]+\$', re.DOTALL)


def markdown_words(markdown: str) -> set[str]:
  """Return the words of a Markdown output that a PDF must show.

  The generated-file comment, the alternative text of pictures and the source of math are left
  out: a PDF has the picture and the typeset formula instead.

  Parameters
  ----------
  markdown : str
      The Markdown output.

  Returns
  -------
  set of str
      Lower-case words of four letters or more.
  """
  return words(_MATH.sub(' ', _IMAGE.sub(' ', _COMMENT.sub(' ', markdown))))


def missing_words(markdown: str, pdf: bytes) -> list[str]:
  """List the words of the Markdown that are not in the text of the PDF.

  The PDF text is searched as one stream of letters, because an extractor may join the last word
  of a heading to the first of the next paragraph.

  Parameters
  ----------
  markdown : str
      The Markdown output.
  pdf : bytes
      The PDF.

  Returns
  -------
  list of str
      The missing words, sorted.
  """
  stream = letters(pdf_text(pdf))
  return sorted(word for word in markdown_words(markdown) if word not in stream)
