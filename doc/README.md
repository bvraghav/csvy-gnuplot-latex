# Documentation

For the CSVY → gnuplot → LaTeX pipeline described in the
[top-level README](../README.md).

| | |
|---|---|
| [Tutorials](#tutorials) | worked examples with pictures; read them in order |
| [REFERENCE.md](REFERENCE.md) | the complete rules: input format, generator, template contract, `\gnuplotfit`, the Gantt template, Makefiles |

```
doc/
├── README.md         this page
├── REFERENCE.md
├── tutorials/        101.md, sample-gantt-chart.md, advanced-gantt-chart.md
├── examples/         the inputs behind every figure in the tutorials
├── img/              the rendered figures (committed)
├── site/             the docs website's template, stylesheet and link filter
└── Makefile          examples/ -> img/; make site -> build/site/
```

## Tutorials

Each builds on the last.

| # | Tutorial | You will learn |
|---|---|---|
| 1 | [101: sizing a figure in LaTeX](tutorials/101.md) | `\gnuplotfit` vs `\includegraphics`; natural size; stretching width and height; one- and two-column layouts |
| 2 | [A sample Gantt chart](tutorials/sample-gantt-chart.md) | writing a `.csvy`; the template's defaults and the tested settings; writing labels; how editing the data changes the chart |
| 3 | [Advanced Gantt chart](tutorials/advanced-gantt-chart.md) | `vars` and `gnuplot` settings: bar thickness, margins (gutters), natural size, grid, title, y-axis label |

## Following along

Every figure in these pages is built from a file in [`examples/`](examples/),
with the same tools as the top folder:

```sh
make -C doc          # render doc/img/*.png from doc/examples/
make -C doc clean    # remove doc/build/ (the images are committed)
```

| In `examples/` | Becomes |
|---|---|
| `NAME.csvy` | `build/NAME.gp.tex`, and `img/NAME.png` (the figure at its natural size) |
| `NAME.img.tex` | `img/NAME.png`: a page that lays out one or more figures |
| `docimg.sty` | helpers for those pages: `\panel` (a captioned row) and `\figframe` (a dashed red frame at the figure's requested size) |

The `.csvy` files say `template: templates/gantt`, exactly as they would in
the top folder, so you can copy any of them there and run `make`. Each one
lists only what differs from the template's defaults
(`templates/gantt.csvy`).

## Conventions

- **Dashed red frame:** the area the figure was asked to fill (its `fig`
  size, or the size given to `\gnuplotfit`). Anything outside it is
  overflow.
- **Names:** `vars` settings are given by their YAML keys
  (`margin: {l: 2.0}`) and, where it helps, by the gnuplot variable they
  become (`margin_l`). `gnuplot` settings are given by the gnuplot setting
  they set (`xlabel`, `mxtics`).
- **Tested settings:** these are the values in the top folder's
  `project.csvy`, which the regression tests pin down; the tutorials start
  from them.
