"""Escaping of plain text for LaTeX and Markdown.

HTML needs no function here: the HTML environment uses Jinja's autoescaping. Both functions are
total: whatever string they get, the result is safe to put in a document of that format, and a
hypothesis property test checks it (``tests/property/test_escape.py``).
"""

from __future__ import annotations

import re
from typing import Literal

TEX_SPECIALS: dict[str, str] = {
  '\\': r'\textbackslash{}',
  '{': r'\{',
  '}': r'\}',
  '#': r'\#',
  '$': r'\$',
  '%': r'\%',
  '&': r'\&',
  '_': r'\_',
  '~': r'\textasciitilde{}',
  '^': r'\textasciicircum{}',
  '<': r'\textless{}',
  '>': r'\textgreater{}',
  '|': r'\textbar{}',
}
"""ASCII characters with a meaning in LaTeX (or a different glyph in OT1) and their replacement."""

_GREEK = {
  'α': 'alpha',
  'β': 'beta',
  'γ': 'gamma',
  'δ': 'delta',
  'ε': 'epsilon',
  'ζ': 'zeta',
  'η': 'eta',
  'θ': 'theta',
  'ι': 'iota',
  'κ': 'kappa',
  'λ': 'lambda',
  'μ': 'mu',
  'ν': 'nu',
  'ξ': 'xi',
  'π': 'pi',
  'ρ': 'rho',
  'σ': 'sigma',
  'τ': 'tau',
  'υ': 'upsilon',
  'φ': 'phi',
  'χ': 'chi',
  'ψ': 'psi',
  'ω': 'omega',
  'Γ': 'Gamma',
  'Δ': 'Delta',
  'Θ': 'Theta',
  'Λ': 'Lambda',
  'Ξ': 'Xi',
  'Π': 'Pi',
  'Σ': 'Sigma',
  'Φ': 'Phi',
  'Ψ': 'Psi',
  'Ω': 'Omega',
}
_SYMBOLS = {
  '−': r'\ensuremath{-}',
  '×': r'\ensuremath{\times}',
  '±': r'\ensuremath{\pm}',
  'µ': r'\ensuremath{\mu}',
  '·': r'\ensuremath{\cdot}',
  '⋅': r'\ensuremath{\cdot}',
  '≤': r'\ensuremath{\leq}',
  '≥': r'\ensuremath{\geq}',
  '≈': r'\ensuremath{\approx}',
  '≠': r'\ensuremath{\neq}',
  '∼': r'\ensuremath{\sim}',
  '∞': r'\ensuremath{\infty}',
  '∝': r'\ensuremath{\propto}',
  '√': r'\ensuremath{\surd}',
  '→': r'\ensuremath{\rightarrow}',
  '←': r'\ensuremath{\leftarrow}',
  '′': r'\ensuremath{^{\prime}}',
  '″': r'\ensuremath{^{\prime\prime}}',
  '°': r'\textdegree{}',
  '•': r'\textbullet{}',
  '…': r'\ldots{}',
  '–': '--',
  '—': '---',
  '‘': '`',
  '’': "'",
  '“': '``',
  '”': "''",
  ' ': '~',
  ' ': r'\,',
  ' ': r'\,',
  '​': '',
}
TEX_UNICODE: dict[str, str] = {
  **{char: rf'\ensuremath{{\{name}}}' for char, name in _GREEK.items()},
  **_SYMBOLS,
}
"""Non-ASCII characters that need a macro under every engine, and the macro."""

_CONTROL_RE = re.compile(r'[\x00-\x08\x0b-\x1f\x7f]')
_SPACE_RE = re.compile(r'\s+')
TexUnicode = Literal['map', 'keep']


def tex_escape(text: str, *, unicode: TexUnicode = 'map', inline: bool = False) -> str:
  r"""Escape plain text so that LaTeX typesets it literally.

  Covers ``# $ % & ~ _ ^ \ { }`` and, because their glyph differs in the default font encoding,
  ``< > |``. A leading ``[`` or ``*`` is braced, because TeX would read it as the optional
  argument or star of a preceding ``\\``. Control characters are dropped.

  Parameters
  ----------
  text : str
      The text; any string.
  unicode : {'map', 'keep'}, default='map'
      ``map`` replaces Greek letters and common symbols (``×``, ``±``, ``−``, ``≤``, ``°`` ...) by
      macros that work under pdfLaTeX, XeLaTeX and LuaLaTeX; ``keep`` leaves every non-ASCII
      character to the font, for layouts that ship a font with the glyphs.
  inline : bool, default=False
      Collapse every run of whitespace, newlines included, to one space and strip the ends. Use
      it for table cells, headings and captions, where a blank line would end the paragraph.

  Returns
  -------
  str
      LaTeX source that typesets ``text``.
  """
  text = _CONTROL_RE.sub('', text)
  if inline:
    text = _SPACE_RE.sub(' ', text).strip()
  out: list[str] = []
  for char in text:
    if char in TEX_SPECIALS:
      out.append(TEX_SPECIALS[char])
    elif unicode == 'map' and char in TEX_UNICODE:
      out.append(TEX_UNICODE[char])
    else:
      out.append(char)
  result = ''.join(out)
  if result.startswith('['):
    result = '{[}' + result[1:]
  elif result.startswith('*'):
    result = '{*}' + result[1:]
  return result


_MD_ALWAYS = re.compile(r'[\\`*\[\]<>|$~&]')
_MD_UNDERSCORE = re.compile(r'(?<![A-Za-z0-9])_|_(?![A-Za-z0-9])')
_MD_LINE_START = re.compile(
  r'^(?:(#{1,6})(?=\s|$)|([-+])(?=\s|$)|(-)(?=--)|(\d{1,9})([.)])(?=\s|$)|(=+)(?=\s*$))'
)


def md_escape(text: str) -> str:
  """Escape plain text so that a Markdown reader shows it literally, on one line.

  Whitespace runs (newlines included) become one space and the ends are stripped. Every
  character that can open markup is backslash-escaped; an underscore inside a word
  (``n_sources``) is left alone, because CommonMark never reads it as emphasis.

  Parameters
  ----------
  text : str
      The text; any string.

  Returns
  -------
  str
      Markdown source that renders as ``text`` with its whitespace collapsed.
  """
  text = _SPACE_RE.sub(' ', _CONTROL_RE.sub('', text)).strip()
  text = _MD_ALWAYS.sub(lambda m: '\\' + m.group(0), text)
  text = _MD_UNDERSCORE.sub(r'\\_', text)
  return _MD_LINE_START.sub(_escape_line_start, text)


def md_code_span(text: str) -> str:
  r"""Wrap text in a Markdown code span, choosing a fence that the text cannot close.

  Parameters
  ----------
  text : str
      The code; newlines become spaces.

  Returns
  -------
  str
      For example ``\`a\``` or ``\`\` a`b \`\```.
  """
  text = _SPACE_RE.sub(' ', text)
  runs = [len(run) for run in re.findall(r'`+', text)]
  fence = '`' * next(n for n in range(1, len(runs) + 2) if n not in runs)
  pad = ' ' if text.startswith('`') or text.endswith('`') or text.strip() != text else ''
  return f'{fence}{pad}{text}{pad}{fence}' if text else f'{fence} {fence}'


def _escape_line_start(match: re.Match[str]) -> str:
  """Put a backslash before the marker that would start a heading, list or setext underline."""
  heading, bullet, rule, number, delimiter, underline = match.groups()
  if heading:
    return '\\' + heading
  if bullet or rule:
    return '\\' + (bullet or rule)
  if number:
    return f'{number}\\{delimiter}'
  return '\\' + underline
