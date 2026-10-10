# Figures in the style of a report

Figures made by the code that feeds a report should look like the report (ADR-0007). `scireport` exposes
the matplotlib style of each layout.

```python
import scireport

with scireport.mplstyle('default'):                  # or 'modern'
  fig, ax = scireport.figure(0.8, 3.0)               # 80 % of the page frame wide, 3 inches high
  ax.hist(values, bins=40)
  ax.set_xlabel('separation (arcsec)')
  report.add_figure('sep', fig, alt='Histogram of separations', width=0.8, data={'sep': values})
```

| Name | Does |
|---|---|
| `scireport.mplstyle(layout='default', *, rc=None)` | a context manager: registers the vendored fonts, applies the style of the layout, restores matplotlib's parameters on exit. Draw everything of a figure inside it |
| `scireport.mplstyle_path(layout)` | the `.mplstyle` file of a layout (`scireport/styles/<name>.mplstyle`) |
| `scireport.palette(layout)` | colours, chart roles, status colours, the colour cycle, fonts and page geometry, from the layout's `palette.yaml` |
| `scireport.figure(width=1.0, height=3.6, nrows=1, ncols=1, *, layout='default', paper='a4', subplot_kw=None)` | a figure at its **final physical size**: `width` is a fraction of the usable page width, `height` is in inches, both clamped to the frame |
| `scireport.styles.save_figure(fig, path)` / `figure_bytes(fig, 'png')` | PNG, PDF or SVG with no matplotlib version, date or random id inside, so the same drawing gives the same bytes |

`Report.add_figure` renders a matplotlib figure the same way, so figures stored in a bundle are
deterministic.

## One source of truth

`palette.yaml` (in the layout directory) is the only place where a colour is a constant. `tokens.css`, the
`.sty` file (`\definecolor{sc-ink}{HTML}{...}`) and the `.mplstyle` repeat the hex values by hand, so a
reviewer can read them in a diff. `tests/unit/styles/test_consistency.py` parses all four and fails when one
drifts, when the CSS uses a colour that is not a token, or when a layout lists a font that does not ship.
Changing a colour is therefore one edit in `palette.yaml` plus the three copies, and a test that tells you
which one you forgot. Because a changed colour is a changed look, it is a new layout version.
