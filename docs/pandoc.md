# pandoc: markup engine, citations and office formats

pandoc is optional (ADR-0011). `uv add 'scireport[pandoc]'` installs `pypandoc-binary`, whose wheel bundles the
pandoc executable, so no system pandoc is needed and every machine runs the same version. It is imported
lazily; without the extra, anything that needs pandoc stops with `E506` and exit code 3.

pandoc is used in three places, and **only** when asked for. Nothing switches on because pandoc happens to be
installed.

| Use | How you ask for it |
|---|---|
| Convert the Markdown prose | `--markup-engine pandoc` or `render.markup_engine: pandoc` |
| Format citations in Markdown and HTML | a `bibliography` value and `[@key]` in prose |
| Write Word, OpenDocument and EPUB | `-f docx`, `-f odt`, `-f epub` |

Every render that used pandoc records its version in `render-manifest.json` (`engines.pandoc`). A bundle may
record the version it was checked with in `render.pandoc_version` (`scireport pack` does it for bundles that
use pandoc); rendering with another version gives warning `W501`, an error with `--strict`.

## The markup engine

`mistletoe` (the default, pure Python) reads a documented subset. `pandoc` reads CommonMark with pipe tables,
footnotes, definition lists, task lists, strikethrough and `$...$` math, and writes HTML and LaTeX. The rules
for what is outside the subset are the same for both ([Markdown](markup.md)): headings and images in prose, raw
HTML or LaTeX and unsafe links are shown as text with `W701`. pandoc always runs with `--sandbox` and an empty
data directory, so prose cannot read files, run filters or use a user's templates. The differences in the
output are listed in [Markdown](markup.md).

## Citations

A bundle holds at most one `bibliography` value: a BibTeX file, an optional CSL style (`.csl`, for Markdown and
HTML) and an optional biblatex `style` (for LaTeX).

```python
report.add_text('intro', 'Agrees with [@doe2020, p. 3; @smith2018] and [-@doe2020].', format='markdown')
report.add_bibliography('refs', 'references.bib', csl='ieee.csl', style='numeric')
```

Only the bracketed form is read: `[@a]`, `[see @a, p. 3; @b]`, `[-@a]` (year only). A group that is not a
citation (`[me@example.org]`), code spans and code blocks are left alone, and a bundle without a bibliography
renders exactly as before. A key that the `.bib` file lacks is `E212` with a suggestion. Citations are read in
Markdown `text` values; captions and table cells are not scanned.

The reference list is drawn by `c.references()` in a template (`generic@1` draws it where the bibliography value
sits in the outline); only the works that are cited are listed, unless `c.references(everything=True)`.

- **Markdown and HTML**: scireport collects every citation of the finished document, in order, and runs pandoc's
  citation processor (`citeproc`) once, so numeric styles number consistently across chapters. Needs pandoc.
- **LaTeX**: citations become `\autocite` commands (`\autocites` for groups), the writer adds
  `\usepackage[backend=biber]{biblatex}` and `\addbibresource{references.bib}` to the preamble, and
  `references.bib` is written next to `report.tex`. `latexmk` runs `biber` by itself. Needs no pandoc, but the
  PDF needs `biber` (TeX Live package `biber`, plus `biblatex`).

## Word, OpenDocument and EPUB

`docx`, `odt` and `epub` are not templated. scireport renders the report to **unsplit Markdown** (with its
`figures/`), or to the HTML with `--office-source html`, and pandoc converts that; math becomes native Word
equations. The conversion is the one place pandoc runs without `--sandbox` (it must read the figures), so the
tree is cleaned first: raw content is dropped and an image survives only when it is a file of the render.

A layout may name a `reference_docx:` in `layout.yaml` (a Word file whose styles pandoc uses for `docx` and
`odt`); `--reference-doc FILE` overrides it. The look of the HTML or PDF layouts is *not* carried over.
Archive entries get the timestamp of `meta.date` (or `SOURCE_DATE_EPOCH`), and the EPUB identifier is a hash of
the manifest, so two renders give the same bytes.
