# Markdown in reports

Prose in templates and `text` values is Markdown. A converter turns it into the target format. The default
backend is [mistletoe](https://github.com/miyuchina/mistletoe) (pure Python, no system dependency); the
converter interface (`scireport.render.markup.MarkupConverter`) lets another backend replace it. The Pandoc
backend is optional and arrives in a later phase (ADR-0011).

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
| Footnotes (`[^1]`) | mistletoe has no footnote syntax, so `[^1]` stays literal text | prose, or the Pandoc backend later |
| Raw HTML, definition lists, task lists | not portable to LaTeX | plain lists, `c.metadata` |
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
