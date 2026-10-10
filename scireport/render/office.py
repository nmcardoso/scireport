"""Word, OpenDocument and EPUB output, converted by pandoc from the rendered Markdown or HTML.

``docx``, ``odt`` and ``epub`` are not templated: scireport renders the report as usual (an
unsplit Markdown document with its ``figures/``, or the self-contained HTML) and hands that to
pandoc (ADR-0011). A layout may supply a ``reference.docx`` whose styles pandoc uses for ``docx``
and ``odt``. The conversion is the only place pandoc runs without ``--sandbox``, because it must
read the figures next to the document; the document tree is therefore cleaned first: raw content
is dropped, and an image survives only when it is a file of the render itself.

Archives are written with ``SOURCE_DATE_EPOCH`` set, so their entries carry fixed timestamps.
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Literal

from scireport.render.markup import safe_url
from scireport.render.pandoc import Node, read_ast, run_pandoc, walk
from scireport.spec.manifest import Meta

OfficeFormat = Literal['docx', 'odt', 'epub']
OFFICE_FORMATS: tuple[OfficeFormat, ...] = ('docx', 'odt', 'epub')
"""The formats pandoc writes for scireport, in the canonical order."""
OfficeSource = Literal['md', 'html']
OFFICE_SOURCES: tuple[OfficeSource, ...] = ('md', 'html')
"""What the conversion reads: the Markdown (default) or the HTML output."""
OFFICE_NAME = 'report'
"""Base name of the file inside its folder (``docx/report.docx``)."""

_MD_READER = (
  'commonmark_x-alerts-attributes-bracketed_spans-emoji-fancy_lists-fenced_divs'
  '-implicit_header_references-raw_attribute-smart-subscript-superscript'
  '-yaml_metadata_block-gfm_auto_identifiers'
)
_REFERENCE = 'reference.docx'


def convert_office(
  fmt: OfficeFormat,
  files: Mapping[str, bytes],
  *,
  source: OfficeSource,
  meta: Meta,
  epoch: int,
  identifier: str,
  reference_doc: bytes | None = None,
) -> bytes:
  """Convert a rendered report to ``docx``, ``odt`` or ``epub``.

  Parameters
  ----------
  fmt : {'docx', 'odt', 'epub'}
      The target format.
  files : mapping
      The render of ``source``: path to content (``report.md`` and ``figures/...``, or
      ``report.html``).
  source : {'md', 'html'}
      Which render to convert.
  meta : Meta
      The report's metadata (language, keywords, subject and, for EPUB, title and authors).
  epoch : int
      ``SOURCE_DATE_EPOCH`` for the archive timestamps.
  identifier : str
      A stable identifier for the EPUB (a hash of the manifest), so that two builds agree.
  reference_doc : bytes or None, default=None
      The content of a ``reference.docx`` for ``docx`` and ``odt``.

  Returns
  -------
  bytes
      The file.

  Raises
  ------
  MissingDependencyError
      With ``E506`` when pandoc is missing.
  PandocError
      With ``E507`` when pandoc fails.
  """
  with tempfile.TemporaryDirectory(prefix='scireport-office-') as tmp:
    folder = Path(tmp)
    for name, data in files.items():
      path = folder / name
      path.parent.mkdir(parents=True, exist_ok=True)
      path.write_bytes(data)
    out = folder / f'{OFFICE_NAME}.{fmt}'
    args = ['-f', 'json' if source == 'md' else 'html', '-t', fmt, '-o', out.name]
    args.extend(_metadata_args(fmt, meta, identifier))
    if reference_doc is not None and fmt in ('docx', 'odt'):
      (folder / _REFERENCE).write_bytes(reference_doc)
      args.append(f'--reference-doc={_REFERENCE}')
    run_pandoc(args, _document(source, files), cwd=folder, epoch=epoch, sandbox=False)
    return out.read_bytes()


def _document(source: OfficeSource, files: Mapping[str, bytes]) -> bytes:
  """Return what pandoc reads on standard input: the cleaned tree, or the HTML."""
  if source == 'html':
    return files['report.html']
  document = read_ast(files['report.md'].decode('utf-8'), _MD_READER)
  document['blocks'] = _clean(document['blocks'], set(files))
  return json.dumps(document, ensure_ascii=False).encode('utf-8')


def _clean(blocks: list[Node], available: set[str]) -> list[Node]:
  """Drop raw content and keep only images that are files of the render."""

  def visit(node: Node) -> Node | list[Node] | None:
    kind = node['t']
    if kind in ('RawInline', 'RawBlock'):
      return []
    if kind == 'Link' and not safe_url(node['c'][2][0]):
      text: list[Node] = node['c'][1]
      return text
    if kind == 'Image' and not _is_local_file(node['c'][2][0], available):
      alt: list[Node] = node['c'][1]
      return alt
    return None

  cleaned: list[Node] = walk(blocks, visit)
  return cleaned


def _is_local_file(target: str, available: set[str]) -> bool:
  """Say whether an image target is a relative path to one of the render's files."""
  path = PurePosixPath(target)
  return not path.is_absolute() and '..' not in path.parts and target in available


def _metadata_args(fmt: OfficeFormat, meta: Meta, identifier: str) -> list[str]:
  """Return the ``--metadata`` arguments for a format."""
  args = ['-M', f'lang={meta.language}']
  if meta.keywords:
    args.extend(['-M', f'keywords={", ".join(meta.keywords)}'])
  if meta.subtitle:
    args.extend(['-M', f'subject={meta.subtitle}'])
  if fmt == 'epub':
    args.extend(['-M', f'title={meta.title}', '-M', f'identifier={identifier}'])
    for author in meta.authors:
      args.extend(['-M', f'author={author.name}'])
    if meta.date:
      args.extend(['-M', f'date={meta.date}'])
  return args
