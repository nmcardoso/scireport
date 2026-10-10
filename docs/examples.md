# Example gallery

Three small, seeded examples, each rendered with both layouts. The files below are the real output of the
`examples` job (`make examples`), published with the site: open the HTML in a browser, read the Markdown as a
language model would, or compare the two PDF routes (WeasyPrint prints the HTML; LuaLaTeX compiles the LaTeX
project).

| Example | Shows | Template |
|---|---|---|
| `dataset-report` | metrics, a status banner, a method section with math, a results table, two figures drawn with `scireport.mplstyle` | `generic@1`, from the outline |
| `metrics-dashboard` | six headline numbers, the pipeline flow, alerts, a table of checks with verdicts, a chart | its own template, `examples/templates/metrics-dashboard/` |
| `text-report` | prose, lists, an equation and code, with no data | `generic@1` |

## Gallery

| Example | Layout | Markdown | HTML | PDF (WeasyPrint) | PDF (LuaLaTeX) |
|---|---|---|---|---|---|
| `dataset-report` | `default@1` | [report.md](https://nmcardoso.github.io/scireport/gallery/dataset-report/default/report.md) | [report.html](https://nmcardoso.github.io/scireport/gallery/dataset-report/default/report.html) | [PDF](https://nmcardoso.github.io/scireport/gallery/dataset-report/default/weasyprint.pdf) | [PDF](https://nmcardoso.github.io/scireport/gallery/dataset-report/default/lualatex.pdf) |
| `dataset-report` | `modern@1` | [report.md](https://nmcardoso.github.io/scireport/gallery/dataset-report/modern/report.md) | [report.html](https://nmcardoso.github.io/scireport/gallery/dataset-report/modern/report.html) | [PDF](https://nmcardoso.github.io/scireport/gallery/dataset-report/modern/weasyprint.pdf) | [PDF](https://nmcardoso.github.io/scireport/gallery/dataset-report/modern/lualatex.pdf) |
| `metrics-dashboard` | `default@1` | [report.md](https://nmcardoso.github.io/scireport/gallery/metrics-dashboard/default/report.md) | [report.html](https://nmcardoso.github.io/scireport/gallery/metrics-dashboard/default/report.html) | [PDF](https://nmcardoso.github.io/scireport/gallery/metrics-dashboard/default/weasyprint.pdf) | [PDF](https://nmcardoso.github.io/scireport/gallery/metrics-dashboard/default/lualatex.pdf) |
| `metrics-dashboard` | `modern@1` | [report.md](https://nmcardoso.github.io/scireport/gallery/metrics-dashboard/modern/report.md) | [report.html](https://nmcardoso.github.io/scireport/gallery/metrics-dashboard/modern/report.html) | [PDF](https://nmcardoso.github.io/scireport/gallery/metrics-dashboard/modern/weasyprint.pdf) | [PDF](https://nmcardoso.github.io/scireport/gallery/metrics-dashboard/modern/lualatex.pdf) |
| `text-report` | `default@1` | [report.md](https://nmcardoso.github.io/scireport/gallery/text-report/default/report.md) | [report.html](https://nmcardoso.github.io/scireport/gallery/text-report/default/report.html) | [PDF](https://nmcardoso.github.io/scireport/gallery/text-report/default/weasyprint.pdf) | [PDF](https://nmcardoso.github.io/scireport/gallery/text-report/default/lualatex.pdf) |
| `text-report` | `modern@1` | [report.md](https://nmcardoso.github.io/scireport/gallery/text-report/modern/report.md) | [report.html](https://nmcardoso.github.io/scireport/gallery/text-report/modern/report.html) | [PDF](https://nmcardoso.github.io/scireport/gallery/text-report/modern/weasyprint.pdf) | [PDF](https://nmcardoso.github.io/scireport/gallery/text-report/modern/lualatex.pdf) |

The links work on the published site. In a local build they stay dead unless `make examples` has written
`examples/_out/` before `make docs`. The same run also produces the LaTeX project (`tex/`) and the PDFs of XeLaTeX and
pdfLaTeX; those are in the `examples` artifact of the CI run and are not published.

## Rendering the examples yourself

`make examples` writes `examples/_out/<example>/<layout>/` with `md/`, `html/`, `tex/` and a PDF from each engine:
`pdf-weasyprint/`, `pdf-lualatex/`, `pdf-xelatex/` and `pdf-pdflatex/`. Rendering needs pango and TeX Live;
`make examples EXAMPLES_ARGS=--no-pdf` makes only the text outputs. The folder is ignored by git.

The built-in template `kitchen-sink@1` draws every component once, plus the cases a layout has to survive
(five status levels, six flow states, a 90-character heading, a very long path, a 250-row table, missing
values). Its bundle is built by `scireport.demo.kitchen_sink_bundle()`:

```console
$ uv run python -c "from scireport.demo import kitchen_sink_bundle; from scireport.render import render_bundle; \
    r = render_bundle(kitchen_sink_bundle('modern'), template='kitchen-sink@1', layout='modern@1', formats=['pdf'], flat=True); \
    open('sink.pdf', 'wb').write(r.files['report.pdf'])"
```
