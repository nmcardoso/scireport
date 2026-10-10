# Examples

`make examples` renders three small, seeded examples with both layouts into `examples/_out/` (ignored by
git; the `examples` CI job uploads it as an artifact):

| Example | Shows | Template |
|---|---|---|
| `dataset-report` | metrics, a status banner, a method section with math, a results table, two figures drawn with `scireport.mplstyle` | `generic@1`, from the outline |
| `metrics-dashboard` | six headline numbers, the pipeline flow, alerts, a table of checks with verdicts, a chart | its own template, `examples/templates/metrics-dashboard/` |
| `text-report` | prose, lists, an equation and code, with no data | `generic@1` |

For each example and layout the folder holds `md/`, `html/`, `tex/` and a PDF from each engine:
`pdf-weasyprint/`, `pdf-lualatex/`, `pdf-xelatex/` and `pdf-pdflatex/`. Rendering needs pango and TeX Live;
`make examples EXAMPLES_ARGS=--no-pdf` makes only the text outputs.

The built-in template `kitchen-sink@1` draws every component once, plus the cases a layout has to survive
(five status levels, six flow states, a 90-character heading, a very long path, a 250-row table, missing
values). Its bundle is built by `scireport.demo.kitchen_sink_bundle()`:

```console
$ uv run python -c "from scireport.demo import kitchen_sink_bundle; from scireport.render import render_bundle; \
    r = render_bundle(kitchen_sink_bundle('modern'), template='kitchen-sink@1', layout='modern@1', formats=['pdf'], flat=True); \
    open('sink.pdf', 'wb').write(r.files['report.pdf'])"
```
