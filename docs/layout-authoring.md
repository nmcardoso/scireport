# Writing a layout

A **layout** says what a report looks like; a template says what it contains ([Writing a template](templates.md)). The same template and
the same data file give a different report with another layout, and the layout never has to know which values it
draws. Write a layout when the built-in looks ([Built-in layouts](layouts.md)) do not fit: a house style, a journal template, a
simpler page for a language model.

A layout is a directory with one definition file, one palette and, for each output format, a document skeleton, a file
of component macros and the styling that goes with them. This page builds one from `minimal@1`, then lists what each
file must define, so that you can write another from scratch.

```text
lab-notes/1/
  layout.yaml                  formats, options, PDF engines, fonts, the names of the files below
  palette.yaml                 the colours (the single source of truth), fonts, page geometry
  md/document.md.j2            the Markdown skeleton and its components
  md/components.md.j2
  html/document.html.j2        the HTML skeleton, its components and its stylesheets
  html/components.html.j2
  html/tokens.css  html/base.css  html/lab-notes.css
  latex/document.tex.j2        the LaTeX skeleton, its components and its style file
  latex/components.tex.j2
  latex/scireport-lab-notes.sty
  styles/lab-notes.mplstyle    the matplotlib style of figures drawn in this look
```

The names are free: `layout.yaml` says which file is which. The `1` is the layout version, and it is a folder only
so that a second version can sit next to it ([Versions are frozen](#versions-are-frozen)).

## Make a layout from minimal@1

The steps use the bundle and the template of [Writing a template](templates.md) (`bundle/` and `tpl/`). Each ends with a command that
you can run, so a mistake shows up in the step that caused it.

### 1. Copy it

`minimal@1` is the smallest complete layout: no design, but every component in every format. Copy it into a folder of
your own. The version folder is the layout's root:

```console
$ mkdir -p layouts/lab-notes
$ cp -r "$(python -c "from scireport.render.registry import PACKAGE_DIR; print(PACKAGE_DIR / 'layouts' / 'minimal' / '1')")" layouts/lab-notes/1
$ scireport layouts ./layouts/lab-notes
minimal@1: Minimal
formats: md, html, tex   pdf engines: 
  toc                  bool  = True
    Write a table of contents.
  cover                bool  = True
    Write the title block (subtitle, authors, date, version) under the title.
  accent               str   = '#1f4e79'
    Accent colour as #rrggbb.
  paper                str   = 'a4' (a4|letter)
    Paper size of the LaTeX project.
  numbered_captions    bool  = True
    Prefix captions with "Table N." and "Figure N.".
```

`-l ./layouts/lab-notes` is a path, so it is a layout: the folder has no `layout.yaml` itself, and scireport takes the
highest numbered folder inside it. `-l ./layouts/lab-notes/1` would name that one version. A copy already renders
(`scireport render bundle -t ./tpl -l ./layouts/lab-notes -o out -f md`); it still says `minimal@1` in its header,
because the name is in `layout.yaml`.

### 2. Name it and say what it declares

Rewrite `layout.yaml`. These are the keys it has; the ones that matter here are the name, the version, the files, the
options and the palette:

```yaml
# lab-notes@1: minimal@1 with a palette, a ruled accent heading and a density option.
spec: ">=1.0,<2.0"
name: lab-notes
version: 1
title: Lab notes
description: Plain pages with one accent colour, for notes that are read on screen and on paper.
formats:
  md:
    document: md/document.md.j2
    components: md/components.md.j2
  html:
    document: html/document.html.j2
    components: html/components.html.j2
    css: [html/tokens.css, html/base.css, html/lab-notes.css]
  tex:
    document: latex/document.tex.j2
    components: latex/components.tex.j2
    style: latex/scireport-lab-notes.sty
options:
  - name: toc
    type: bool
    default: true
    description: Write a table of contents.
  - name: cover
    type: bool
    default: true
    description: Write the title block (subtitle, authors, date, version) under the title.
  - name: density
    type: str
    default: normal
    choices: [normal, compact]
    description: Line spacing and font size of the text.
  - name: paper
    type: str
    default: a4
    choices: [a4, letter]
    description: Paper size of the PDF and of the LaTeX project.
  - name: numbered_captions
    type: bool
    default: true
    description: Prefix captions with "Table N." and "Figure N.".
pdf_engines: [weasyprint, latex]
mplstyle: styles/lab-notes.mplstyle
palette: palette.yaml
fonts:
  - Inter-Regular.otf
  - Inter-SemiBold.otf
  - Inter-Italic.otf
  - IBMPlexMono-Regular.otf
```

Compared with `minimal@1`: a new name and title; the `accent` option is gone, and a `density` option is new (the next
steps use it); the stylesheet list has three files; and `pdf_engines`, `mplstyle`, `palette` and `fonts` are declared.
The keys, in full:

| Key | Meaning |
|---|---|
| `spec` | the data-file spec versions the layout works with; another is `E505` |
| `name`, `version` | the name (letters, digits, `-`, `_`) and the integer version |
| `title`, `description` | one line each, shown by `scireport layouts` |
| `formats` | for each format it supports (`md`, `html`, `tex`), the files below; asking for another is `E706` |
| `options` | the typed options, below |
| `pdf_engines` | the PDF engines it supports: `weasyprint` (from the HTML) and `latex` (from the LaTeX project). Empty means no PDF: `E903` |
| `mplstyle` | the matplotlib style of figures drawn in this look: a shipped name (`default`, `modern`) or a path inside the layout (a value with a `/` or ending in `.mplstyle`) |
| `palette` | the palette file, relative to the layout directory |
| `fonts` | file names of vendored fonts the layout uses ([Fonts](#fonts)) |
| `reference_docx` | a Word file, relative to the layout, whose styles pandoc uses for `docx` and `odt` output |

Under each format:

| Key | Meaning |
|---|---|
| `document` | the skeleton that wraps the rendered body (a Jinja file) |
| `components` | the file with one macro per component (a Jinja file) |
| `css` | HTML only: stylesheets inlined into the document, in order |
| `style` | LaTeX only: the style file written next to `report.tex` |
| `assets` | other files copied into the LaTeX project as they are (a logo, say). Markdown and HTML do not copy them |

Every file `layout.yaml` names must exist; a missing one is `E703` with its path, an invalid definition is `E702`
(carrying every problem), at load time and also from `scireport validate`.

### 3. The palette

The palette is the one place where a colour is a constant. Everything else repeats it by hand so that a reviewer can
read it in a diff, and a check catches the copies that drift ([One source of colour](#one-source-of-colour)). Write
`palette.yaml`:

```yaml
# The single source of truth of the look of lab-notes@1.
# html/tokens.css, latex/scireport-lab-notes.sty and styles/lab-notes.mplstyle repeat these values.
name: lab-notes
colors:
  ink: "#1a1a1a"
  ink-soft: "#555555"
  accent: "#1f4e79"
  accent-light: "#eef3f8"
  green: "#2e7d32"
  green-light: "#eaf6ec"
  amber: "#b26a00"
  amber-light: "#fff4e0"
  red: "#b3261e"
  red-light: "#fdeceb"
  paper: "#ffffff"
  gray-100: "#f3f4f6"
  gray-300: "#dddddd"
  gray-500: "#888888"
role:
  failed: red
  flagged: red
  success: green
  warning: amber
  neutral: gray-500
  annotation: ink
status:
  success: green
  warning: amber
  partial: amber
  failed: red
  running: accent
cycle: [accent, amber, green, red, gray-500]
cmap:
  sequential: cividis
  diverging: RdBu_r
fonts:
  sans: [Inter, Helvetica Neue, Arial, sans-serif]
  mono: [IBM Plex Mono, DejaVu Sans Mono, monospace]
spacing: [4, 8, 12, 16, 24, 32]
type_scale:
  title: 24.0
  section: 16.0
  body: 11.0
  table: 9.5
body_line_height: 1.55
heading_line_height: 1.25
page:
  width_mm: 210.0
  height_mm: 297.0
  margin_x_mm: 25.0
  margin_y_mm: 25.0
```

Colours are `#rrggbb` in lower case. `role`, `status` and `cycle` name colours by token, and a name that is not in
`colors` is `E702`. `page` gives the margins the figures are sized against, so it must match the margins of the
stylesheet and of the LaTeX style (`margin: 25mm`, `margin=2.5cm` below). The fields:

<!-- generated:palette -->
| Field | Type | Meaning |
|---|---|---|
| `name` | `str` | The layout the palette belongs to. |
| `colors` | `dict[str, str]` | Token name (``navy-deep``) to ``#rrggbb``, lower case. These are the CSS custom properties. |
| `role` | `dict[str, str]` | Colour with a fixed meaning in a chart (``failed``, ``success`` ...) to a colour token. |
| `status` | `dict[str, str]` | Level of the status component to a colour token. |
| `cycle` | `list[str]` | Colour tokens that tell series apart, in order. |
| `cmap` | `object` | Sequential and diverging colour maps. |
| `cmap.sequential` | `str` | matplotlib colour map names. |
| `cmap.diverging` | `str` | matplotlib colour map names. |
| `fonts` | `object` | Font stacks. |
| `fonts.sans` | `list[str]` | Family names in order of preference. |
| `fonts.mono` | `list[str]` | Family names in order of preference. |
| `fonts.serif` | `list[str]` | The same for the body text of a layout that sets it in a serif face; empty when the layout sets its body text in sans. Default PydanticUndefined. |
| `spacing` | `list[int]` | The spacing scale in points. |
| `type_scale` | `dict[str, float]` | Point size per typographic rung. |
| `body_line_height` | `float` | Line heights as multiples of the font size. |
| `heading_line_height` | `float` | Line heights as multiples of the font size. |
| `page` | `object` | Page geometry, A4 unless the file says otherwise. |
| `page.width_mm` | `float` | Paper size. Default 210.0. |
| `page.height_mm` | `float` | Paper size. Default 297.0. |
| `page.margin_x_mm` | `float` | Left and right, top and bottom margins; the frame is what remains. Default 9.0. |
| `page.margin_y_mm` | `float` | Left and right, top and bottom margins; the frame is what remains. Default 18.0. |
<!-- /generated -->

### 4. The HTML stylesheets

`html/tokens.css` holds the palette as CSS custom properties, `--<token>: #hex;`, and the type and spacing scales as
`--text-<rung>` and `--space-<n>` in points:

```css
/* Design tokens of lab-notes@1. palette.yaml is the source of truth; a test compares the two. */
:root {
  --ink: #1a1a1a;
  --ink-soft: #555555;
  --accent: #1f4e79;
  --accent-light: #eef3f8;
  --green: #2e7d32;
  --green-light: #eaf6ec;
  --amber: #b26a00;
  --amber-light: #fff4e0;
  --red: #b3261e;
  --red-light: #fdeceb;
  --paper: #ffffff;
  --gray-100: #f3f4f6;
  --gray-300: #dddddd;
  --gray-500: #888888;

  --font-sans: 'Inter', 'Helvetica Neue', Arial, sans-serif;
  --font-mono: 'IBM Plex Mono', 'DejaVu Sans Mono', monospace;

  --text-title: 24pt;
  --text-section: 16pt;
  --text-body: 11pt;
  --text-table: 9.5pt;

  --space-1: 4pt;
  --space-2: 8pt;
  --space-3: 12pt;
  --space-4: 16pt;
  --space-5: 24pt;
  --space-6: 32pt;
}
```

`minimal.css` becomes `html/base.css`, with every literal colour replaced by a token. One `sed` does the replacement
(the shades of grey fold into the three the palette has):

```console
$ cd layouts/lab-notes/1
$ mv html/minimal.css html/base.css
$ sed -i -E \
    -e 's/#1a1a1a/var(--ink)/g' -e 's/#fff4e0/var(--amber-light)/g' -e 's/#fff\b/var(--paper)/g' \
    -e 's/#(444|555|666|777)\b/var(--ink-soft)/g' -e 's/#(888|999)\b/var(--gray-500)/g' \
    -e 's/#(bbb|ddd)\b/var(--gray-300)/g' -e 's/#(f3f3f3|f6f7f9)\b/var(--gray-100)/g' \
    -e 's/#eaf6ec/var(--green-light)/g' -e 's/#fdeceb/var(--red-light)/g' \
    -e 's/#eef3f8/var(--accent-light)/g' -e 's/#2e7d32/var(--green)/g' \
    -e 's/#b26a00/var(--amber)/g' -e 's/#b3261e/var(--red)/g' html/base.css
```

Three lines of `base.css` are then edited by hand. The first comment becomes
`/* lab-notes@1 base styles: every colour is a token from tokens.css. */`. The `body` rule loses its font shorthand,
`body { margin: 0; line-height: 1.55; color: var(--ink); background: var(--paper); }`, because the fonts come from the
next file. And `overflow-x: auto` on `.code-block pre` moves into `@media screen { ... }`, because WeasyPrint warns
about a property it ignores ([PDF engines](#pdf-engines-and-their-pitfalls)).

If you rename a file and forget `layout.yaml`, the error names the file and the layout directory. (A command that
fails while loading logs the message with a timestamp and a level; the text after `cli._common` is what is shown in
this page.)

```console
$ scireport render bundle -t ./tpl -l ./layouts/lab-notes -o out -f md
E703 layout file 'html/minimal.css' is missing from layouts/lab-notes/1
```

The third stylesheet holds what is new in this look, `html/lab-notes.css`:

```css
/* What lab-notes@1 adds to the base: the font stacks, a ruled chapter heading and the density option. */
body { font-family: var(--font-sans); font-size: var(--text-body); }
code, pre, .align-path { font-family: var(--font-mono); }
h1.title { font-size: var(--text-title); }
.chapter h1 { font-size: var(--text-section); text-transform: uppercase; letter-spacing: 0.04em;
  border-bottom: 4px solid var(--accent); }
.density-compact { font-size: 0.9em; line-height: 1.35; }
.density-compact p { margin: 0.4em 0; }
```

Finally the HTML skeleton. Three changes to `html/document.html.j2`: print `fonts_css` (the `@font-face` rules of the
fonts the layout lists, inlined as `data:` URIs), set the PDF page from the `paper` option, and use the `density`
option as a class. The `--accent` line of `minimal@1` goes, because the colour now lives in `tokens.css`:

```diff
@@ -6,13 +6,14 @@
 <meta name="generator" content="scireport {{ info.scireport_version }}">
 <title>{{ meta.title }}</title>
 <style>
-:root { --accent: {{ options.accent }}; }
+{{ fonts_css }}
 {{ css }}
+@page { size: {{ 'A4' if options.paper == 'a4' else 'Letter' }}; margin: 25mm; }
 </style>
 </head>
 <body>
 <!-- {{ info.generated }} -->
-<main>
+<main class="density-{{ options.density }}">
 {{ c.cover() }}
 {% if meta.abstract %}
 <section class="abstract">
```

### 5. The LaTeX style and skeleton

The `.sty` file is where a LaTeX layout lives: the packages, the fonts, the colours and the heading style. Rename it
(`mv latex/scireport-minimal.sty latex/scireport-lab-notes.sty`) and write `latex/scireport-lab-notes.sty`. The name in
`\ProvidesPackage` must match the file name:

```latex
\NeedsTeXFormat{LaTeX2e}
\ProvidesPackage{scireport-lab-notes}[2026/10/10 scireport lab-notes layout, version 1]
% Works with LuaLaTeX (default), XeLaTeX and pdfLaTeX. Inter is loaded from the fonts/ folder of the
% project through fontspec; pdfLaTeX cannot read OpenType fonts and falls back to Latin Modern.
\RequirePackage{iftex}
\ifPDFTeX
  \RequirePackage[T1]{fontenc}
  \RequirePackage[utf8]{inputenc}
  \RequirePackage{lmodern}
  \RequirePackage{textcomp}
  \renewcommand{\familydefault}{\sfdefault}
\else
  \RequirePackage{fontspec}
  \setmainfont{Inter}[Path=./fonts/, Extension=.otf, UprightFont=*-Regular, ItalicFont=*-Italic,
    BoldFont=*-SemiBold, BoldItalicFont=*-Italic]
  \setmonofont{IBMPlexMono}[Path=./fonts/, Extension=.otf, Scale=MatchLowercase,
    UprightFont=*-Regular, ItalicFont=*-Regular, BoldFont=*-Regular, BoldItalicFont=*-Regular]
\fi
\RequirePackage[margin=2.5cm]{geometry}
\RequirePackage{parskip}
\RequirePackage{amsmath,amssymb}
\RequirePackage{graphicx}
\RequirePackage{array}
\RequirePackage{booktabs}
\RequirePackage{longtable}
\RequirePackage[table]{xcolor}
\RequirePackage{caption}
\RequirePackage[normalem]{ulem}
\RequirePackage[hidelinks]{hyperref}
\RequirePackage{titlesec}

% ---- palette: the hex values repeat palette.yaml ----------------------------------------------
\definecolor{sc-ink}{HTML}{1A1A1A}
\definecolor{sc-ink-soft}{HTML}{555555}
\definecolor{sc-accent}{HTML}{1F4E79}
\definecolor{sc-accent-light}{HTML}{EEF3F8}
\definecolor{sc-green}{HTML}{2E7D32}
\definecolor{sc-green-light}{HTML}{EAF6EC}
\definecolor{sc-amber}{HTML}{B26A00}
\definecolor{sc-amber-light}{HTML}{FFF4E0}
\definecolor{sc-red}{HTML}{B3261E}
\definecolor{sc-red-light}{HTML}{FDECEB}
\definecolor{sc-paper}{HTML}{FFFFFF}
\definecolor{sc-gray-100}{HTML}{F3F4F6}
\definecolor{sc-gray-300}{HTML}{DDDDDD}
\definecolor{sc-gray-500}{HTML}{888888}
% The components of the layout use these names; they point at the tokens above.
\colorlet{accent}{sc-accent}
\colorlet{pass}{sc-green}
\colorlet{warn}{sc-amber}
\colorlet{fail}{sc-red}
\colorlet{muted}{sc-ink-soft}

\color{sc-ink}
\titleformat{\section}{\Large\bfseries\color{accent}}{\thesection}{0.6em}{}[\color{accent}\titlerule]
\setlength{\emergencystretch}{3em}
\setcounter{secnumdepth}{3}
\setcounter{tocdepth}{2}
\captionsetup{font=small,labelfont=bf}
\endinput
```

Three things to keep from `minimal@1`. The package list is a contract: the components and the converted Markdown prose
use `\captionof`, `\rowcolor`, `\toprule`, `\href`, `\sout`, `longtable` and `\includegraphics`, so `caption`, `xcolor`
with `table`, `booktabs`, `hyperref`, `ulem`, `longtable`, `array` and `graphicx` must load. The colour names `accent`,
`pass`, `warn`, `fail` and `muted` are the ones the components use, so the style defines them: here as aliases of the
palette tokens, written once with an `sc-` prefix so that the consistency check can read them. And the style works with
all three TeX engines: `iftex` chooses the font setup, because pdfLaTeX cannot load OpenType fonts.

The skeleton `latex/document.tex.j2` loses the `\definecolor{accent}` line (the colour is in the style) and gains the
density option:

```diff
@@ -3,8 +3,12 @@
 ((* if style *))
 \usepackage{(((style | safe)))}
 ((* endif *))
-\definecolor{accent}{HTML}{(((options.accent | replace('#', '') | upper | safe)))}
-\hypersetup{pdftitle={(((meta.title)))},pdfcreator={scireport (((info.scireport_version)))}}
+((* if options.density == 'compact' *))
+\linespread{1.0}
+((* else *))
+\linespread{1.15}
+((* endif *))
+\hypersetup{pdftitle={(((meta.title | pdfstring)))},pdfcreator={scireport (((info.scireport_version | pdfstring)))}}
 \begin{document}
 ((( c.cover() )))
 ((* if meta.abstract *))
```

`style` is the name of the style file without its suffix, set by the engine. `pdfstring` is a filter for LaTeX files:
it drops the characters TeX gives a meaning to, so that a title with a `%` or a `_` does not break the PDF metadata.
The Markdown skeleton and all three `components` files stay as they are: the look comes from the stylesheet and the
style file, and the components emit the same structure.

### 6. The matplotlib style

Figures drawn for this report should look like it ([Matplotlib style guide](styles.md)). `styles/lab-notes.mplstyle` repeats the palette
colours in the cycle, the axes and the grid; it is applied only inside `scireport.mplstyle()`:

```text
# Matplotlib rcParams of every figure drawn in the lab-notes@1 look. Applied only inside
# scireport.mplstyle(). The colours repeat palette.yaml.
font.family: sans-serif
font.sans-serif: Inter, Helvetica Neue, Arial, sans-serif
font.monospace: IBM Plex Mono, DejaVu Sans Mono, monospace
font.size: 9.0

axes.facecolor: "#ffffff"
axes.edgecolor: "#888888"
axes.labelcolor: "#1a1a1a"
axes.titlecolor: "#1a1a1a"
axes.linewidth: 0.7
axes.grid: True
axes.axisbelow: True
axes.prop_cycle: cycler('color', ["#1f4e79", "#b26a00", "#2e7d32", "#b3261e", "#888888"])

grid.color: "#dddddd"
grid.linewidth: 0.5

xtick.color: "#555555"
ytick.color: "#555555"
text.color: "#1a1a1a"
legend.frameon: False

figure.facecolor: "#ffffff"
savefig.facecolor: "#ffffff"
image.cmap: cividis
lines.linewidth: 1.4
```

### 7. Check and render

```console
$ scireport layouts ./layouts/lab-notes
lab-notes@1: Lab notes
formats: md, html, tex   pdf engines: weasyprint, latex
  toc                  bool  = True
    Write a table of contents.
  cover                bool  = True
    Write the title block (subtitle, authors, date, version) under the title.
  density              str   = 'normal' (normal|compact)
    Line spacing and font size of the text.
  paper                str   = 'a4' (a4|letter)
    Paper size of the PDF and of the LaTeX project.
  numbered_captions    bool  = True
    Prefix captions with "Table N." and "Figure N.".
$ scireport validate bundle -t ./tpl -l ./layouts/lab-notes -f md -f html -f tex
valid: 0 error(s), 0 warning(s)
$ scireport render bundle -t ./tpl -l ./layouts/lab-notes -o out -f md -f html -f tex -O density=compact
html/report.html
md/report.md
render-manifest.json
tex/fonts/IBMPlexMono-Regular.otf
tex/fonts/Inter-Italic.otf
tex/fonts/Inter-Regular.otf
tex/fonts/Inter-SemiBold.otf
tex/fonts/OFL.txt
tex/latexmkrc
tex/report.tex
tex/scireport-lab-notes.sty
```

`-O density=compact` sets an option from the command line (the data file's `render.options` and Python do the same;
the command line wins). In `out/html/report.html` the page is `<main class="density-compact">`, and with the default
it is `class="density-normal"`. The HTML holds four `@font-face` rules with the fonts as data URIs, so it is one file.
`out/tex/` is a standalone project: `latexmk report.tex` there makes the PDF with no scireport installed. The
`fonts/` folder, with its licence `OFL.txt`, is there because `layout.yaml` lists fonts.

The PDF needs the system libraries ([Outputs](outputs.md)): pango for the WeasyPrint engine and TeX Live for the LaTeX engine.
Both were checked with this layout:

```console
$ scireport render bundle -t ./tpl -l ./layouts/lab-notes -o out -f pdf
pdf/report.pdf
render-manifest.json
$ scireport render bundle -t ./tpl -l ./layouts/lab-notes -o out -f pdf --pdf-engine latex
pdf/report.pdf
render-manifest.json
```

The first prints the HTML with WeasyPrint, the second compiles the LaTeX project with `latexmk` and LuaLaTeX. WeasyPrint
may log that it uses fontTools instead of HarfBuzz-Subset; that depends on the system and is harmless. `-O paper=letter`
gives a US letter page (`Page size: 612 x 792 pts (letter)` in `pdfinfo`). The same render twice gives byte-identical
`.md`, `.html` and `.tex` (the render manifest records the layout's content hash next to its name).

## What each file must define

### The options

Each option has a `name` (lower case, digits and `_`), a `type` (`bool`, `str`, `int` or `float`), a `default` of that
type and optionally `choices`, a `pattern` and a `description`. A `str` option that ends up in CSS or LaTeX should have
a `pattern` or `choices`, so that it is constrained rather than trusted. Macros and skeletons read them as
`options.name`.

Values come from, in increasing priority, the layout defaults, the bundle's `render.options` and `-O name=value`. A
string from the command line is converted to the declared type (`true`/`false`, `yes`/`no`, `on`/`off` and `1`/`0` for
a `bool`). A problem in `layout.yaml` itself (a default of the wrong type, a default outside the choices, a bad
regular expression, two options with one name) is `E702`; an unknown option or a value of the wrong type, outside the
choices or not matching the pattern is `E806`, reported for all of them at once, with a "did you mean":

```console
$ scireport validate bundle -t ./tpl -l ./layouts/lab-notes -O density=huge -O colour=red
E806 lab-notes@1: option density must be one of normal, compact, got 'huge'
E806 layout lab-notes@1 has no option 'colour' (it has: toc, cover, density, paper, numbered_captions)
invalid: 2 error(s), 0 warning(s)
```

Options are for features and choices (a cover, a density, a paper size), not for colours: a colour option would
override the palette, which is the single source of colour. `minimal@1` has one (`accent`) because it has no palette;
a layout with a palette should offer a choice of palette tokens or be a second layout instead. In `layout.yaml`, quote
a description that contains ` #`: YAML reads it as the start of a comment and cuts the text there.

### The document skeleton

`document` wraps the rendered body: it writes the header, the title block, the table of contents and the body. It is
rendered after the body, so that the table of contents knows every heading. It sees:

| Name | Meaning |
|---|---|
| `body` | the rendered body of the report |
| `toc` | the table of contents entries (also drawn by `c.contents()`) |
| `c` | the components; the skeleton calls `c.cover()` and `c.contents()` |
| `options`, `meta`, `info`, `outline`, `data`, `v`, `has`, `peek`, `keys` | as in a template |
| `css`, `fonts_css` | HTML only: the stylesheets and the `@font-face` rules, ready to print |
| `style` | LaTeX only: the style file's name without the suffix, or empty |
| `split`, `files` | Markdown only: whether the document is split by chapter, and the file names |

`meta` is the manifest's metadata (`title`, `subtitle`, `authors` with `name` and `affiliation`, `date`, `version`,
`pipeline`, `footer`, `abstract`, `keywords`, `language`). `info` holds `scireport_version`, `template`, `layout`,
`format`, `manifest_sha256`, `generated` (the generated-file notice: put it in a comment at the top of the output),
`split` and `latex_engine`. `meta.abstract` is Markdown: print it through the `md` filter, as the built-in skeletons do.

### The component macros

The `components` file defines one macro for each of the components below, **with exactly these parameter names**:
the engine calls every macro with keyword arguments. A missing macro is `E707` (and `scireport validate` finds it
without rendering); a macro with other parameter names fails when it is first used with `E804`
(`TypeError: macro 'status' takes no keyword argument 'level'`), and the location it reports is the macro in the
layout's components file (`file:line`, relative to the layout directory). The file may define helper macros too (`caption_text` in `minimal@1`).

| Macro | Parameters | What it draws |
|---|---|---|
| `chapter` | `title, entry, page_break` | the top level of the table of contents. `entry` has `number`, `anchor`, `slug`, `level`, `text`, `md_file`; `page_break` is `true`, `false` or none (the layout decides) |
| `heading` | `text, level, entry, page_break` | a heading, level 1 to 3 |
| `contents` | `entries` | the table of contents: a list of the same entries |
| `cover` | `cover` | the title block: `title`, `subtitle`, `authors` (strings), `date`, `version`, `pipeline` |
| `table` | `spec` | `columns` (`label`, `unit`, `align`, `width`, `width_given`), `rows` (`cells`, `verdict`, `emphasis`), `caption`, `number`, `total`, `truncated`, `overflow`, `headed`, `has_verdicts` |
| `figure`, `image` | `spec` | `src`, `alt`, `caption`, `width` (a fraction of the text width), `number`, `key` |
| `equation` | `spec` | `body` (already typeset), `latex`, `display`, `number`, `caption` |
| `metrics` | `entries` | headline numbers: `label`, `value`, `detail` |
| `status` | `level, headline, detail` | `level` is `success`, `warning`, `partial`, `failed` or `running` |
| `alert` | `level, text` | `level` is `info`, `warning` or `error` |
| `flow` | `stages` | `number`, `label`, `detail` (lines), `state` (`done`, `reused`, `skipped`, `failed`, `running`, `pending`) |
| `metadata` | `entries` | pairs of `(label, value)` |
| `bullets` | `items, ordered` | a list |
| `code` | `source, language, caption, fence, verbatim` | a code block; `fence` and `verbatim` are ready for Markdown and LaTeX |
| `details`, `note` | `summary, body`; `body` | a collapsible block; a muted remark |
| `paragraph` | `body` | a paragraph of text |
| `fact` | `label, value` | a labelled line (`Pairs: 3,061`) |
| `attachment` | `link` | a file offered next to the report: `filename`, `href`, `description`, `size` |
| `spacer`, `page_break` | `height`; none | vertical space (points); a new page |

These field names are part of the layout API (ADR-0008): they do not change within a major version. The macros see
`options`, `meta` and `info`, the filters, and nothing else: no `c`, no `data`. The engine has already turned values
into these plain descriptions, so a macro decides only how they look.

### Escaping

Each format escapes what it prints. In HTML files autoescape is on: a plain string is escaped, and a string the engine
marks safe is not. In Markdown and LaTeX files `{{ x }}` and `((( x )))` escape plain strings for the format (Markdown
markup characters, TeX special characters and Unicode). When a macro must print raw markup, as in
`{{ ('#' * level) | safe }}` for a Markdown heading, say so with `| safe`. A component's output is never escaped
twice.

Newlines: the environments use `trim_blocks` and `lstrip_blocks`, so a line that ends with a block tag loses its
newline and indentation before a tag is dropped. `{{ eol }}` puts a newline back; a macro that must write a line break
after a block uses it. `{% do %}` and `{% break %}` are available.

### Markup the engine writes itself

Some markup comes from the engine itself, not from a macro: prose converted from Markdown, and math. In HTML a layout
should style `.math-inline` and `.math-display` (the images of equations), `.align-left`, `.align-right` and
`.align-center` (cells of tables written in Markdown prose) and `.h--run` (a heading written in prose, shown as a
bold run-in line). In LaTeX the prose uses `\emph`, `\texttt`, `\href`, `quote`, `itemize`, `enumerate`, `verbatim` and
`booktabs`, which is why the style file loads those packages. A document that cites also gets a few lines of CSS for
the reference list.

## One source of colour

`palette.yaml` is the only place where a colour is a constant. The stylesheet (`tokens.css`), the LaTeX style
(`\definecolor{sc-...}`) and the matplotlib style repeat the hex values by hand, so a reviewer can read them in a diff.
The repository's `tests/unit/styles/test_consistency.py` parses all four for the built-in layouts and fails when one
drifts, when the CSS uses a colour that is not a token, or when a layout lists a font that does not ship. It reads
`html/tokens.css` and the layout's `.sty` by the names used above, so a layout of your own that follows them can be
checked the same way. A small standalone version, `check_palette.py`, for your own project (it takes a layout
reference):

```python
"""Check that the stylesheet, the LaTeX style and the matplotlib style repeat palette.yaml."""

import re
import sys
from pathlib import Path

import scireport
from scireport.render.registry import load_layout

layout_ref = sys.argv[1]
root = load_layout(layout_ref).root
pal = scireport.palette(layout_ref)
css = (root / 'html' / 'tokens.css').read_text(encoding='utf-8')
sty = next(root.glob('latex/*.sty')).read_text(encoding='utf-8')
mpl = scireport.mplstyle_path(layout_ref).read_text(encoding='utf-8')

css_colors = dict(re.findall(r'--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;', css))
sty_colors = dict(re.findall(r'\\definecolor\{sc-([a-z0-9-]+)\}\{HTML\}\{([0-9A-Fa-f]{6})\}', sty))
mpl_colors = {c.lower() for c in re.findall(r'"(#[0-9a-fA-F]{6})"', mpl)}

problems = []
for token, value in pal.colors.items():
  if css_colors.get(token, '').lower() != value:
    problems.append(f'tokens.css: --{token} is {css_colors.get(token)}, palette has {value}')
  if f'#{sty_colors.get(token, "")}'.lower() != value:
    problems.append(f'.sty: sc-{token} is #{sty_colors.get(token)}, palette has {value}')
for value in sorted(mpl_colors - set(pal.colors.values())):
  problems.append(f'mplstyle: {value} is not a palette colour')
stray = set(re.findall(r'#[0-9a-fA-F]{6}\b', (root / 'html' / 'base.css').read_text(encoding='utf-8')))
problems.extend(f'base.css: {value} is not a token' for value in sorted(stray))

print('\n'.join(problems) or 'palette, CSS, LaTeX and matplotlib style agree')
sys.exit(1 if problems else 0)
```

```console
$ python check_palette.py ./layouts/lab-notes
palette, CSS, LaTeX and matplotlib style agree
```

Change `--amber` in `tokens.css` by one digit and it says what drifted, and exits with 1:

```console
$ python check_palette.py ./layouts/lab-notes
tokens.css: --amber is #b26a01, palette has #b26a00
```

A changed colour is a changed look, so for a published layout it is a new version
([Versions are frozen](#versions-are-frozen)).

## Fonts

Layouts use the vendored fonts: **Inter**, **IBM Plex Serif** and **IBM Plex Mono** (SIL Open Font License,
`OFL.txt`) and **TeX Gyre Pagella**, **Heros** and **Cursor** (GUST Font Licence, `GFL.txt`), seventeen OpenType faces in
the package (`Inter-Regular.otf`, `IBMPlexSerif-Regular.otf`, `TeXGyrePagellaSubset-Regular.otf` and so on; the E703 message below
lists them all). The TeX Gyre faces are subsets and are renamed with the suffix `Subset`, as the GUST Font Licence asks; its manifest
`MANIFEST-TeXGyreSubset.txt` travels with `GFL.txt`. The licence texts sit next to them and are copied next to any LaTeX project that ships the faces they cover. Listing a face under `fonts:` has three effects: the HTML inlines it as a `data:` font
(`fonts_css`), and the LaTeX project gets a `fonts/` folder with the face and `OFL.txt` (the `.sty` loads it through
`fontspec` with `Path=./fonts/`). The names must be vendored files: any other name is `E703`,
and the message lists the faces there are:

```console
$ scireport validate bundle -t ./tpl -l ./lf -f md
E703 layout lab-notes@1 lists the font 'Fira-Regular.otf', which the package does not ship. The vendored faces are in fonts/: IBMPlexMono-Medium.otf, IBMPlexMono-Regular.otf, IBMPlexSerif-Italic.otf, IBMPlexSerif-Regular.otf, IBMPlexSerif-SemiBold.otf, Inter-Italic.otf, Inter-Medium.otf, Inter-Regular.otf, Inter-SemiBold.otf, TeXGyreCursorSubset-Regular.otf, TeXGyreHerosSubset-Bold.otf, TeXGyreHerosSubset-Italic.otf, TeXGyreHerosSubset-Regular.otf, TeXGyrePagellaSubset-Bold.otf, TeXGyrePagellaSubset-BoldItalic.otf, TeXGyrePagellaSubset-Italic.otf, TeXGyrePagellaSubset-Regular.otf.
```

A layout therefore cannot ship a font of its own through `fonts:`. To use another family, name it in the CSS stack and
in the style file and rely on it being installed, which makes the output depend on the machine; `assets` copies files
into the LaTeX project only. If a font you add is open-licensed, keep its `OFL.txt` (or the licence it came with) next
to it.

The Inter and IBM Plex Mono subsets cover Basic Latin, Latin-1 and a few symbols (dashes, `×`, `·`, `→`, `−`, `∞`, `°`,
`±`). They have no Greek letters and no `≤ ≥ ≈ √` (the IBM Plex Serif and TeX Gyre subsets have them): the LaTeX writer maps those to math macros, and HTML falls back to the next
family of the stack, so end every stack with a generic keyword (`sans-serif`, `monospace`).

## PDF engines and their pitfalls

`pdf_engines` lists what the layout supports. The PDF is made from another output, never from the template:
`weasyprint` prints the HTML, and `latex` compiles the LaTeX project in a scratch directory. A layout that lists neither
has no PDF (`E903`); one that lists only one refuses the other. A missing library (pango, TeX Live or one TeX package)
exits with code 3 (`E901`) and an install hint; a failed compile is `E902` with the `file:line` of each error in the
LaTeX log. [Outputs](outputs.md) has the details.

For the **WeasyPrint** engine, the HTML is printed with CSS Paged Media, so the stylesheet also decides the pages. The
built-in layouts record what they learned, in the comments of `html/components.css`, `html/print.css` and
`html/base.css`:

- Do not nest a flex container inside another one. WeasyPrint collapses the width of a fixed-size, empty flex item
  whose container is itself a flex item. Use `display: table` and `table-cell`, floats or absolute positioning for
  columns. One unnested `display: flex` is fine.
- Do not put `break-inside: avoid` on a box that wraps a table. A table taller than a page has nowhere to go and the
  box moves it whole to the next page, where it still does not fit. Let the table split, and give single rows
  `break-inside: avoid` with the header in `thead` so that it repeats.
- Give the cover its own named page (`@page cover { margin: 0 }`) rather than `@page :first`, which breaks silently
  when the cover runs to two pages. Set running strings on `<body>` itself, not on a leading sibling element: a box with
  `page: auto` before one with `page: cover` forces a blank page ahead of the cover.
- Set the page size from the `paper` option in the document skeleton, as the example does, so that the PDF and the
  LaTeX project agree.
- Properties WeasyPrint does not know are logged as warnings, such as `overflow-x: auto` ("Ignored `overflow-x: auto`
  ... unknown property"). Put screen-only rules inside `@media screen { ... }`, where the PDF does not read them.

For the **LaTeX** engine:

- The project is standalone: everything the document needs is in the `.sty`, the fonts folder and `assets`.
- Use `fontspec` only when the engine is LuaLaTeX or XeLaTeX (`\ifPDFTeX ... \else ... \fi` with `iftex`). pdfLaTeX
  cannot load OpenType fonts: `default@1` warns `W901` and falls back to Latin Modern (`modern@1` loads the TeX Gyre packages instead).
- The `latexmkrc` and the engine are chosen by `--latex-engine` (default `lualatex`; `xelatex` and `pdflatex` also
  work, and `lab-notes@1` compiles with all three).
- Characters the font lacks are reported as `W902`.

## Use a layout

By path, for one project: `-l ./layouts/lab-notes` (the newest numbered folder) or `-l ./layouts/lab-notes/1` (one
version). A path is a command-line (and Python) choice only: `render.layout` in a data file takes a `name` or a
`name@version`, and a path there is `E205`. A bundle can therefore name a layout only if it resolves by name wherever
the bundle is rendered, which is a built-in layout or a plugin. `scireport pack` pins `name` to the newest
`name@version` it finds, so that a later render of the packed bundle is identical. A layout shared between projects
belongs in a package.

By plugin, for a package that ships layouts: the entry-point group `scireport.layouts`. The entry point's name is the
layout name, and it points to a version directory or to a folder of numbered version directories:

```toml
# pyproject.toml
[project]
name = "labnotes"
version = "0.1.0"
dependencies = ["scireport"]

[project.entry-points."scireport.layouts"]
lab-notes = "labnotes:LAYOUTS"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/labnotes"]
```

```python
# src/labnotes/__init__.py
"""The lab-notes layout for scireport."""

from pathlib import Path

LAYOUTS = Path(__file__).parent / 'layouts'
"""A folder of numbered version directories (layouts/1/layout.yaml, layouts/2/ ...)."""
```

With the layout in `src/labnotes/layouts/1/` and the package installed, `scireport layouts` lists it, and
`-l lab-notes` and `scireport.mplstyle('lab-notes')` find it by name:

```console
$ scireport layouts
default@1        md,html,tex  builtin    Default (MOSAICS look)
lab-notes@1      md,html,tex  entry-point:lab-notes Lab notes
minimal@1        md,html,tex  builtin    Minimal
modern@1         md,html,tex  builtin    Modern (Signal)
```

A built-in name always wins over a plugin with the same name, and the plugin is ignored with a warning. A plugin that
fails to load is `E705`. The wheel must include the layout files; hatchling includes every file under the package
folder.

## Versions are frozen

A layout is **versioned and frozen** (ADR-0008). Once a version is published, its folder is never edited: a visual
change is a new version directory, never a changed `1/`. The reason is the data file: it stores `name@version`, a
bundle packed years ago must render the same today, and the render manifest records a content hash of the layout
directory, so a silent edit would show up as a different report under the same name.

To change the look of `lab-notes@1`, copy `1/` to `2/` and edit the copy: `version: 2` in `layout.yaml`, a new
`.sty` name or version line if you like, a new palette value. A bare name then means the newest version:

```console
$ cp -r layouts/lab-notes/1 layouts/lab-notes/2
$ sed -i 's/^version: 1/version: 2/' layouts/lab-notes/2/layout.yaml
$ scireport layouts ./layouts/lab-notes | head -1
lab-notes@2: Lab notes
$ scireport layouts ./layouts/lab-notes/1 | head -1
lab-notes@1: Lab notes
```

Fixing a bug that no output depends on (a typo in a comment) is not a visual change, but when in doubt make a new
version. The same holds for templates, and for the options of a layout: a new option with a default that keeps the old
look is additive; one that changes what an existing file prints is a new version.

## Errors you will meet

| Code | When |
|---|---|
| `E701` | the layout is not found: no layout of that name, or a path without `layout.yaml` |
| `E504` | the name exists but not that version (`minimal@3`: "has no version 3. Available: minimal@1") |
| `E702` | `layout.yaml` or `palette.yaml` is invalid: a bad key or type, an unknown palette token, an option default outside its choices |
| `E703` | a file the layout names is missing (a document, components, CSS, style, palette, `reference_docx`), or a listed font does not ship |
| `E705` | a layout plugin cannot be loaded |
| `E706` | the layout does not support the requested format |
| `E707` | a component macro is missing for a format the layout lists |
| `E804` | a macro was called with arguments it does not take, or failed while rendering |
| `E806` | an option is unknown, or its value has the wrong type, is outside the choices or does not match the pattern |
| `E903` | the layout does not support the requested PDF engine |
| `E901`, `E902` | a PDF engine's system dependency is missing; the engine failed |
| `W901`, `W902` | pdfLaTeX fell back to TeX fonts; a font lacks some characters |

With the `flow` macro deleted from `md/components.md.j2`:

```console
$ scireport validate bundle -t ./tpl -l ./layouts/lab-notes -f md
E707 md/components.md.j2: layout lab-notes@1 does not define the 'flow' component for md
invalid: 1 error(s), 0 warning(s)
$ scireport render bundle -t ./tpl -l minimal@1 -o out -f pdf
E903 layout minimal@1 does not support the weasyprint PDF engine (it supports none)
```

[Error codes](errors.md) has the full catalogue.
