# Markdown in reports

Prose in templates and `text` values is Markdown. A converter turns it into the target format. The default
backend is [mistletoe](https://github.com/miyuchina/mistletoe) (pure Python, no system dependency); the
converter interface (`scireport.render.markup.MarkupConverter`) lets another backend replace it. The
[pandoc](pandoc.md) backend (`--markup-engine pandoc`, `render.markup_engine: pandoc`) is optional and is never
chosen automatically, so the output does not depend on what is installed (ADR-0011).

The converter understands a **documented subset**. Anything outside it is shown as plain text and reported as
warning `W701`; nothing is dropped silently.

## Supported

- paragraphs, hard and soft line breaks, thematic breaks
- emphasis, strong emphasis, `~~strikethrough~~`, inline code
- links to `http`, `https` and `mailto` addresses, relative links, and `<autolinks>`
- bullet and numbered lists (nested) and block quotes
- fenced and indented code blocks
- GFM tables with column alignment (a header row is required)
- inline `$...$` and display `$$...$$` math, written in LaTeX; a dollar sign that is not math is `\$`

Markdown output keeps the source as written (common indentation removed), so people and language models read
exactly what was authored.

## Limits

| Not supported | Why | Use instead |
|---|---|---|
| Headings (`#`) | the table of contents and numbering must stay right | `c.chapter`, `c.heading` |
| Images (`![..](..)`) | assets are checked and hashed | `c.figure`, `c.image` |
| Footnotes (`[^1]`) | mistletoe has no footnote syntax, so `[^1]` stays literal text | prose, or `--markup-engine pandoc` |
| Raw HTML, definition lists, task lists | not portable to LaTeX | plain lists, `c.metadata`, or `--markup-engine pandoc` (definition and task lists) |
| Links to other schemes (`javascript:`, `file:`) | safety | `http`, `https`, `mailto` |

Math in HTML is drawn as SVG with matplotlib `mathtext` (`--math-renderer mathtext`). It covers the LaTeX
subset that `mathtext` understands; math it cannot draw is shown as its source and reported as `W601`. In
LaTeX output the math is passed through unchanged.

## Escaping

Plain text printed from a value (names, captions, cell contents) is escaped for the format rather than
converted: `scireport.render.escape.tex_escape` handles `# $ % & ~ _ ^ \ { }` plus `< > |` and Unicode
(Greek letters, `±`, `×`, `−`, `≤`, `°`, …) for pdfLaTeX, XeLaTeX and LuaLaTeX. `md_escape` backslash-escapes
whatever could open Markdown markup, including a leading `.` or `)` that mistletoe (unlike CommonMark) reads
as an empty list item. Property tests check both on arbitrary text.

## The two engines side by side

`tests/golden/markup/` holds the output of both engines for the same sample prose (one sample per topic), so a
diff of `mistletoe/` and `pandoc/` is the list below. Both engines apply the same rules for what is outside
the subset (headings, images, raw HTML, unsafe links: shown as text, `W701`), and Markdown output is the source
as written in both.

| Topic | mistletoe | pandoc |
|---|---|---|
| Footnotes, definition lists, task lists | not read; shown as text | read; HTML `<section class="footnotes">`, `<dl>`, checkboxes; LaTeX `\footnote`, `description`, `$\boxtimes$` |
| Soft line breaks | kept as a newline | joined with a space (the pandoc writer wraps nothing) |
| Hard line break in LaTeX | `\newline` | `\\` |
| Loose and nested lists in HTML | `<li><p>..</p></li>` | tight `<li>..</li>`; numbered lists carry `type="1"` |
| Code blocks in HTML | `<code class="language-python">` | `<pre class="python"><code>`, quotes as `&quot;` |
| Table alignment in HTML | `class="align-right"` (styled by the layout) | `style="text-align: right;"` |
| Tables in LaTeX | `center` + `tabular` | `longtable` (a table breaks across pages) |
| Strikethrough in LaTeX | `\sout` | `\st`, defined in the preamble as `\sout` |
| `^` in LaTeX | `\textasciicircum{}` | `\^{}` |
| Display math in LaTeX | `\[..\]` on one line | `\[` and `\]` on their own lines; inline math is `\(..\)` |
| Heading in prose (`W701`) | `<p class="h--run"><strong>` | `<p><strong>` |
| Raw HTML in prose (`W701`) | escaped text | inline code (`<code>&lt;b&gt;</code>`) |
| Footnote ids in HTML | n/a | `s<N>-fn1`, unique per fragment |

When pandoc writes LaTeX the writer adds a block to the preamble (`\tightlist`, `longtable`, `booktabs`, `ulem`,
`\st`) so that the project still compiles with plain `latexmk` and any layout. Math in HTML is drawn by the same
hook in both engines (SVG, `W601` when it cannot be drawn).

## Citations

`[@key]` in Markdown prose is handled by scireport, not by the markup engine; see [pandoc](pandoc.md).
