# Matplotlib style guide

Figures drawn by the code that feeds a report should look like the report (ADR-0007): the same colours, fonts and
line weights and, above all, the same **physical size**, so that 8 pt text is 8 pt on the page. A figure that is drawn
at 12 inches and shrunk to the page width has 4 pt text; a figure in the wrong blue looks pasted in. `scireport`
exposes the matplotlib style and the palette of every layout, so a project draws its figures in the look of the
report it will be part of.

This page is for the person who draws the figures. To make a style for a layout of your own, see
{doc}`layout-authoring`; the built-in looks are in {doc}`layouts`.

## A complete example

A histogram of separations, drawn in the look of `modern@1`, saved to disk and stored in a bundle together with the
small table it was drawn from, then rendered. The script was run as it is shown:

```python
import numpy as np

import scireport
from scireport import Report
from scireport.styles import figure_bytes, save_figure

LAYOUT = 'modern'  # the layout the report will be rendered with
PAPER = 'a4'

rng = np.random.default_rng(0)
separations = rng.normal(0.3, 0.1, 500)
counts, edges = np.histogram(separations, bins=40)

pal = scireport.palette(LAYOUT)
with scireport.mplstyle(LAYOUT):
  fig, ax = scireport.figure(0.8, 3.0, layout=LAYOUT, paper=PAPER)
  ax.stairs(counts, edges, fill=True)
  ax.axvline(0.5, color=pal.role_colors['failed'], linestyle='--', label='match radius')
  ax.set_xlabel(r'separation ($\mathrm{arcsec}$)')
  ax.set_ylabel('pairs')
  ax.legend()
  fig.set_layout_engine('constrained')  # keeps labels inside the physical size

print(f'figure size: {fig.get_figwidth():.2f} x {fig.get_figheight():.2f} in')
save_figure(fig, 'out/separations.png')
save_figure(fig, 'out/separations.pdf')
print('same bytes twice:', figure_bytes(fig, 'png') == figure_bytes(fig, 'png'))

report = Report('Cross-match check', authors=['N. Cardoso'], date='2026-10-09')
report.set_outline([{'title': 'Separations', 'children': ['xmatch.separations']}])
report.add_figure(
  'xmatch.separations',
  fig,
  alt='Histogram of the separations of the matched pairs; most are below 0.5 arcsec.',
  caption='Separation of the matched pairs.',
  width=0.8,
  data={'left': edges[:-1], 'right': edges[1:], 'count': counts},
)
report.write('bundle', overwrite=True)
```

```console
$ python separations.py
figure size: 5.61 x 3.00 in
same bytes twice: True
$ scireport validate bundle -l modern@1
valid: 0 error(s), 0 warning(s)
$ scireport render bundle -l modern@1 -o rendered -f md -f html
html/report.html
md/figures/xmatch.separations.png
md/report.md
render-manifest.json
```

The figure is 80 % of the page frame of `modern@1` on A4 (7.01 in between the margins, so 5.61 in) and 3 inches high.
`out/separations.png` and `.pdf` are files for any other use; the bundle holds the same figure as PNG and PDF, and a
`xmatch.separations.data.parquet` with the 40 rows it was drawn from. The Markdown output refers to
`figures/xmatch.separations.png`.

## The API

| Name | Does |
|---|---|
| `scireport.mplstyle(layout='default', *, rc=None)` | a context manager: registers the vendored fonts, applies the style of the layout, restores matplotlib's parameters on exit. `rc={...}` adds one-off overrides. Draw everything of a figure (axes, labels, legends) inside it |
| `scireport.mplstyle_path(layout='default')` | the `.mplstyle` file of a layout, a `pathlib.Path` |
| `scireport.palette(layout='default')` | colours, chart roles, status colours, the colour cycle, colour maps, fonts and page geometry, from the layout's `palette.yaml` |
| `scireport.figure(width=1.0, height=3.6, nrows=1, ncols=1, *, layout='default', paper='a4', subplot_kw=None)` | `(Figure, axes)` at the **final physical size** (below) |
| `scireport.styles.save_figure(fig, path, *, dpi=200, tight=True, close=False)` | writes PNG, PDF or SVG chosen by the suffix, with no run-varying bytes |
| `scireport.styles.figure_bytes(fig, format='png', *, dpi=200, tight=True)` | the same file as bytes |
| `scireport.styles.fonts.register()` | makes the vendored fonts known to matplotlib (`mplstyle()` does it for you) |

`layout` is a layout reference like the one `scireport render -l` takes: a name (`default`, `modern`), `name@version`,
or the path of a layout directory. `mplstyle_path` and `palette` raise `E701` for a layout that does not exist and
`E703` for one that has no style or no palette (`minimal@1` has neither).

## Physical size

`scireport.figure(width, height)` makes the figure at the size it will have on the page. `width` is a **fraction of
the usable page width** (at most 1; a larger value is clamped), and `height` is in **inches** (clamped to the height of
the frame). The frame is the page minus the margins of the layout's palette, so it depends on the layout and on the
paper:

| Layout | Paper | Frame (width x height, inches) | `width=0.8` is |
|---|---|---|---|
| `default@1` | A4 | 7.56 x 10.28 | 6.05 in |
| `modern@1` | A4 | 7.01 x 9.80 | 5.61 in |
| `modern@1` | letter | 7.24 x 9.80 | 5.79 in |

With `nrows` and `ncols` the grid of axes shares the figure: the result is a single `Axes` for 1 x 1 and a NumPy array
otherwise. `subplot_kw` goes to every subplot (`{'projection': 'mollweide'}`). The `width` you pass to
`Report.add_figure(width=...)` is the width the layout draws the picture at, as a fraction of the text width; use the
same number for both, as the example does.

## Colours: the cycle, chart roles and status

Do not copy hex values out of the style. Ask the palette:

```python
pal = scireport.palette('modern')
pal.cycle_colors                  # ['#0072b2', '#f04e23', '#009e73', '#cc79a7', '#0a0a0a', '#5c5c5c']
pal.role_colors['failed']         # '#b3340f': what "failed" looks like in this report
pal.status_colors['warning']      # '#f04e23': the colour of the status component at that level
pal.colors['accent']              # any token, '#rrggbb'
pal.cmap.sequential               # 'cividis'
```

- The **cycle** is the series colours in order. The style already sets it as matplotlib's property cycle, so the second
  line you plot is in the second colour with no work on your side.
- A **role** is a colour with a fixed meaning in a chart (`failed`, `flagged`, `success`, `warning`, `neutral`,
  `annotation`). Use it for "the bad ones", so a chart colours them as the tables and the status banners of the report
  do. The role depends on the layout: `modern@1` has a single vermilion accent that means "needs attention".
- The **status** colours are those of the `status` component (`success`, `warning`, `partial`, `failed`, `running`).
- The **colour maps** are `cividis` and `RdBu_r` in both built-in layouts, which stay readable when printed in grey.

Never rely on colour alone to tell two things apart: the built-in layouts add a rule style or a tint to every status
level, and a figure that carries a verdict should add a marker or a label too. The fields of a palette:

<!-- generated:palette -->
| Field | Type | Meaning |
|---|---|---|
| `name` | `str` | The layout the palette belongs to. |
| `colors` | `dict[str, str]` | Token name (``navy-deep``) to ``#rrggbb``, lower case. These are the CSS custom properties. |
| `role` | `dict[str, str]` | Colour with a fixed meaning in a chart (``failed``, ``success`` ...) to a colour token. |
| `status` | `dict[str, str]` | Level of the status component to a colour token. |
| `cycle` | `list[str]` | Colour tokens that tell series apart, in order. |
| `cmap` | `Cmaps` | Sequential and diverging colour maps. |
| `fonts` | `Fonts` | Font stacks. |
| `spacing` | `list[int]` | The spacing scale in points. |
| `type_scale` | `dict[str, float]` | Point size per typographic rung. |
| `body_line_height` | `float` |  |
| `heading_line_height` | `float` |  |
| `page` | `Page` |  |
<!-- /generated -->

`pal.hex('accent')` is the same as `pal.colors['accent']`. `pal.page` gives the page geometry in millimetres, with
`frame_width_in` and `frame_height_in` in inches.

## Deterministic saving

`save_figure` and `figure_bytes` strip everything that varies between runs: the matplotlib version, the dates, random
ids. PDF fonts are embedded as TrueType, and SVG text becomes paths, so the same drawing gives the same bytes. The
example compares two calls; run twice on one machine and the SHA-256 of the PNG matches. That is what keeps the figure
files of a bundle reproducible, so use them rather than `fig.savefig` for a file that goes into a report.

`Report.add_figure(key, fig, alt=..., data=...)` renders a matplotlib figure the same way, to PNG and PDF by default
(`formats=('png', 'pdf', 'svg')` chooses, `dpi=200` is the PNG resolution). Three details differ from a plain
`save_figure`:

- `add_figure` keeps the **physical size** (it does not crop the figure to its content), while `save_figure` crops by
  default (`tight=True`). The same figure therefore gives a different PNG from the two. Pass `tight=False` to
  `save_figure` to match the bundle's file byte for byte.
- A figure that is not cropped needs its labels to fit inside it. The style does not choose a layout engine, so call
  `fig.set_layout_engine('constrained')` (or `fig.tight_layout()`) before you hand the figure to `add_figure`. Without
  it, an x label of the example is cut off at the bottom of the picture.
- `alt` is required, and a blank one is `E205`: the alternative text is what a reader of the Markdown output and of a
  screen reader sees.

## Give the figure its data

Give `data=` (the small table the figure was drawn from; anything `Report.add_table` takes) and the bundle stores it
next to the figure as a Parquet file. Anyone, a person or a program, can then rebuild or restyle the figure from the
bundle without the original analysis, and a language model can read the numbers behind a picture it cannot see. A
bundle holds summaries, not raw catalogues (ADR-0001): a histogram's bins and counts, the points of a curve, not the
millions of rows.

```python
import pyarrow.parquet as pq

table = pq.read_table('bundle/assets/figures/xmatch.separations.data.parquet')
table.column_names            # ['left', 'right', 'count']
table.num_rows                # 40
```

A bundle is rendered with the layout it names (`render.layout`) or the one on the command line, so draw with the
layout you will render with. Drawing for `modern` and rendering with `default` gives figures sized and coloured for
the wrong page.

## Use the style outside scireport

The shipped styles are ordinary `.mplstyle` files, so any matplotlib code can use them. Register the fonts first,
because `plt.style.use` does not:

```python
import matplotlib.pyplot as plt

import scireport
from scireport.styles import fonts

fonts.register()  # makes Inter and IBM Plex Mono known to matplotlib
plt.style.use(scireport.mplstyle_path('modern'))
fig, ax = plt.subplots(figsize=(4, 2.5))
ax.plot([1, 2, 3], [2, 1, 3])
fig.savefig('plot.png', dpi=150)
```

`plt.style.use` changes matplotlib's global state for the rest of the process; `with scireport.mplstyle(...)` does
not. The command line gives the same files and the palette, for scripts and for agents:

```console
$ scireport mplstyle path
/home/user/project/.venv/lib/python3.12/site-packages/scireport/styles/default.mplstyle
$ scireport mplstyle path modern --json
{
  "layout": "modern",
  "path": "/home/user/project/.venv/lib/python3.12/site-packages/scireport/styles/modern.mplstyle"
}
$ scireport mplstyle show modern          # print the file, one rcParam per line
$ scireport mplstyle palette modern       # colours, roles, status, cycle, colour maps, fonts, spacing, page
cycle: ['data-blue', 'accent', 'data-green', 'data-purple', 'ink', 'gray-500']
cmap: {'sequential': 'cividis', 'diverging': 'RdBu_r'}
page: {'width_mm': 210.0, 'height_mm': 297.0, 'margin_x_mm': 16.0, 'margin_y_mm': 24.0}
```

(The paths are the ones of the installation, shown here as an example; the palette output has more lines than the
three shown.) Each command takes a layout (a name, `name@version` or a directory) and uses `default` without one;
`path` and `palette` also take `--json`.

The shipped styles are `default` (blue and teal series on white, a light grid; the look of `default@1`) and `modern`
(the look of `modern@1`: Inter, spines on the left and bottom only, a hairline horizontal grid and one vermilion
accent in the colour cycle). A layout names its style in `layout.yaml` (`mplstyle:`) and its palette (`palette:`). A
layout directory of your own carries both, and then the whole API works with it by path or by name:

```python
with scireport.mplstyle('./layouts/lab-notes'):
  fig, ax = scireport.figure(1.0, 2.0, layout='./layouts/lab-notes')
```

The built-in `mplstyle: default` value names a style shipped in `scireport/styles/`; a value with a `/` or ending in
`.mplstyle` is a file inside the layout directory.

## Fonts

The style uses **Inter** (text) and **IBM Plex Mono** (code). Both ship inside the package as small OpenType subsets
under the SIL Open Font License, with `OFL.txt` next to them, and `mplstyle()` registers them, so nothing has to be
installed. The subsets cover Basic Latin, Latin-1 and a few symbols (dashes, `×`, `·`, `→`, `−`, `∞`, `°`, `±`). They
have **no Greek letters and no `≤ ≥ ≈ √`**. In a figure write those as math text, which matplotlib draws with its own
bundled fonts: `r'$\alpha$'`, `r'$\leq$'`, `r'$\sqrt{n}$'`, and `r'$\mathrm{arcsec}$'` for an upright unit. A bare
`α` in a label is drawn with whatever font the machine offers for it, so the figure depends on the machine: a computer
with the full Inter family installed may draw it and another may not.

## Pitfalls

- **Pass the same `layout` to `mplstyle` and `figure`.** `figure()` takes the page frame from its own `layout`
  argument (default `'default'`), so `scireport.figure(0.8, 3.0)` inside `mplstyle('modern')` is sized for the wrong
  page: 6.05 inches wide instead of 5.61, because `default@1` has 9 mm side margins and `modern@1` 16 mm. Pass the same
  `paper` that the report is rendered with, too.
- **Draw inside the `with` block.** A style is applied only inside `with scireport.mplstyle(...)`; it never changes
  global matplotlib state. Most parameters are read when an artist is created, so a label added after the block
  gets matplotlib's defaults. Before the block `font.size` was 10, inside it 8 and after it 10 again. `rc={'font.size':
  10}` overrides a parameter for the block.
- **`figure()` returns a `matplotlib.figure.Figure`, not a pyplot figure.** Nothing to `plt.close`, and `plt.show()`
  does not know it. `save_figure(..., close=True)` closes a pyplot figure only.
- **Add a layout engine** before `add_figure` (see above), or labels are clipped.
- **Keep Greek and `≤ ≥ ≈ √` in math text.**
- **Save with the helpers, not `fig.savefig`,** for any file that should be reproducible.
- **`Report.write` refuses to replace a bundle** (`E410`) unless `overwrite=True`.
- **Match `add_figure(width=...)` to the width you drew.** The layout scales the picture to that fraction of the text
  width.

## One source of truth

`palette.yaml`, in the layout directory, is the only place where a colour is a constant. `tokens.css`, the LaTeX
`.sty` file (`\definecolor{sc-ink}{HTML}{...}`) and the `.mplstyle` repeat the hex values by hand, so a reviewer can
read them in a diff. `tests/unit/styles/test_consistency.py` parses all four and fails when one drifts, when the CSS
uses a colour that is not a token, or when a layout lists a font that does not ship. Changing a colour is therefore
one edit in `palette.yaml` plus the three copies, and a test that tells you which one you forgot. Because a changed
colour is a changed look, a released layout gets a new version for it (ADR-0008, {doc}`layout-authoring`).
