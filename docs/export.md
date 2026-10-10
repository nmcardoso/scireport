# LaTeX fragments for manuscripts

`scireport export tex BUNDLE --keys 'crossmatch.*' -o paper/generated` writes files that a manuscript can
`\input`, so that the numbers and tables of a paper come from the data file (ADR-0010).

| File | From | Needs |
|---|---|---|
| `numbers.tex` | every selected `number` value: one `\newcommand` each | nothing |
| `tab_<key>.tex` | a `table`: a `table` float with caption and `\label{tab:<key>}`; over 40 rows a `longtable` | `booktabs` (and `longtable`) |
| `fig_<key>.tex` + `fig_<key>.pdf` (or `.png`) | a `figure`: a `figure` float with caption and `\label{fig:<key>}` | `graphicx` |

```latex
\input{generated/numbers}
We match \CrossmatchNPairs{} objects.
\input{generated/tab_crossmatch.pairs}
\input{generated/fig_crossmatch.separations}
```

**Macro names.** The key is split at `.`, `_` and `-`, each word gets a capital, and digits are spelled out
because LaTeX command names may only hold letters: `crossmatch.n_pairs` is `\CrossmatchNPairs`, `run2.count` is
`\RunTwoCount`. `--prefix Ds` puts letters in front (`\DsCrossmatchNPairs`); two keys that give one name are
`E807`, and a name that LaTeX already defines stops the compile at `\newcommand`, which a prefix avoids. The
macro holds the typeset value with its uncertainty or interval and unit (`3,061~pairs`).

**Options.** `--keys` takes keys or `*`/`?` patterns (repeat it, or separate with commas); a key that does not
exist is `E103`, a named key that has no fragment (a text, say) is `E808`. `--bare` writes a bare `tabular` and
`\includegraphics` without float, caption or label. `--graphics-prefix` is written before the figure file in
`\includegraphics` (default: the output directory's name and a slash, right for `paper/generated` when
the main file is in `paper/`). `--max-rows N` cuts tables. Row verdicts and cell emphasis are not exported.

The same is available from Python: `scireport.export_tex(bundle, keys, prefix=..., bare=...)` and
`write_export`. A test compiles a stub manuscript that inputs every fragment.
