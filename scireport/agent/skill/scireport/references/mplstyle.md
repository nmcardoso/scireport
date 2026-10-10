# Matplotlib style

Figures drawn by the code that feeds a report should look like the report: same colours, fonts, line weights
and, above all, the same **physical size**, so 8 pt text is 8 pt on the page. Every layout owns a matplotlib
style file and a palette (`palette.yaml`); scireport exposes both. Pre-processors use them automatically;
use them yourself when you draw a figure to hand to `Report.add_figure`.

## The API

```python
import numpy as np
import scireport
from scireport import Report
from scireport.styles import figure_bytes, save_figure

LAYOUT = 'modern'                                   # the layout the report will use ('default' if unset)
separations = np.random.default_rng(0).normal(0.3, 0.1, 500)

with scireport.mplstyle(LAYOUT):                    # applies the style; restored on exit
  fig, ax = scireport.figure(0.8, 3.0, layout=LAYOUT)   # 80 % of the page frame wide, 3 inches high
  ax.hist(separations, bins=40)
  ax.set_xlabel(r'separation ($\mathrm{arcsec}$)')
  ax.set_ylabel('count')

save_figure(fig, 'out/separations.png')             # .pdf and .svg too, by the suffix
png = figure_bytes(fig, 'png')                      # the same bytes, in memory

counts, edges = np.histogram(separations, bins=40)
report = Report('Cross-match')
report.add_figure('crossmatch.separations', fig, alt='Histogram of separations', width=0.8,
                  data={'left': edges[:-1], 'right': edges[1:], 'count': counts})
```

| Name | Does |
|---|---|
| `scireport.mplstyle(layout='default', *, rc=None)` | context manager: registers the vendored fonts, applies the layout's style, restores matplotlib's parameters on exit. `rc={...}` adds one-off overrides. Draw **everything** (axes, labels, legends) inside it |
| `scireport.mplstyle_path(layout='default')` | the `.mplstyle` file (`pathlib.Path`), for `plt.style.use(path)` |
| `scireport.palette(layout='default')` | the layout's colours, chart roles, status colours, colour cycle, colour maps, fonts and page geometry (fields below) |
| `scireport.figure(width=1.0, height=3.6, nrows=1, ncols=1, *, layout='default', paper='a4', subplot_kw=None)` | `(Figure, axes)` at the **final physical size**: `width` is a fraction (at most 1) of the usable page width, `height` is in inches (clamped to the frame). One `Axes` for a 1x1 grid, an array otherwise. `paper='letter'` for US letter |
| `scireport.styles.save_figure(fig, path, *, dpi=200, tight=True, close=False)` | writes PNG, PDF or SVG chosen by the suffix |
| `scireport.styles.figure_bytes(fig, 'png'\|'pdf'\|'svg', *, dpi=200, tight=True)` | the same file as bytes |

Things to get right:

- **Pass the same `layout` to `mplstyle` and `figure`.** `figure()` takes the page frame from its own
  `layout` argument (default `'default'`), so `scireport.figure(0.8, 3.0)` under `mplstyle('modern')` is sized for
  the wrong page: `default@1` has 9 mm side margins, `modern@1` 16 mm.
- `figure()` returns a `matplotlib.figure.Figure`, not a pyplot figure: nothing to `plt.close`.
- `save_figure` and `figure_bytes` strip everything that varies between runs (matplotlib version, dates,
  random ids; PDF fonts are embedded as TrueType, SVG text becomes paths), so the same drawing gives the
  same bytes. Run on the same machine twice and the SHA-256 of the PNG matches.
- `Report.add_figure(key, fig, alt=..., data=...)` renders PNG and PDF (`formats=` to change) the same way.
  `alt` is required. Give `data` (the small table the figure was drawn from) so the figure can be rebuilt; a
  bundle holds summaries, not raw catalogues.
- A shipped style is applied to figures **only inside `with scireport.mplstyle(...)`**; it never changes
  global matplotlib state. Outside the block you get matplotlib's defaults.

## Shipped styles and the CLI

`default` (the style of `default@1`: blue and teal series on white, light grid) and `modern` (the style of
`modern@1`, with its vermilion accent in the colour cycle). A layout names its style in `layout.yaml` (`mplstyle:`) and
its palette (`palette:`); a layout directory of your own may carry both (see `templates-and-layouts.md`).

```console
$ scireport mplstyle path                 # the .mplstyle file of default@1
/.../scireport/styles/default.mplstyle
$ scireport mplstyle path modern --json
{"layout": "modern", "path": "/.../scireport/styles/modern.mplstyle"}
$ scireport mplstyle show modern          # print the file (rcParams, one per line)
$ scireport mplstyle palette modern       # colours, roles, status, cycle, cmap, fonts, spacing, page
cycle: ['data-blue', 'accent', 'data-green', 'data-purple', 'ink', 'gray-500']
cmap: {'sequential': 'cividis', 'diverging': 'RdBu_r'}
page: {'width_mm': 210.0, 'height_mm': 297.0, 'margin_x_mm': 16.0, 'margin_y_mm': 24.0}
```

`scireport mplstyle palette LAYOUT --json` prints every field. In Python, `palette.colors['accent']` is a
`#rrggbb` string, `palette.cycle` lists the tokens of the series colours in order, and `palette.role` maps
a chart meaning (`failed`, `success`, `warning`, ...) to a colour token, so a figure can colour "failed"
as the report does:

```python
pal = scireport.palette('modern')
failed_colour = pal.colors[pal.role['failed']]
```

The palette fields:

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

## Fonts

The style uses **Inter** (text) and **IBM Plex Mono** (code), vendored as six small OpenType subsets inside
the package (SIL Open Font License, `OFL.txt` next to them); `mplstyle()` registers them, so nothing has to
be installed on the machine. The subsets cover Basic Latin, Latin-1 and a few symbols (dashes, `×`, `·`,
`→`, `−`, `∞`). They have **no Greek letters and no `≤ ≥ ≈ √`**. In a figure write those as math text,
which matplotlib draws with its own bundled fonts: `r'$\alpha$'`, `r'$\leq$'`, `r'$\sqrt{n}$'`, and
`r'$\mathrm{arcsec}$'` for an upright unit. A bare `α` in a label falls back to whatever font the machine
has, which makes the figure depend on the machine.

## Style changes are new versions

A colour or font change is a visual change, so a released style is frozen with its layout
(`default@1`, `modern@1`); a changed look is a new layout version with its own palette. The colours are
repeated by hand in `palette.yaml`, the stylesheet, the LaTeX `.sty` and the `.mplstyle`, and a test fails if
they drift; do not edit one copy alone.
