# Tutorials

Worked examples for the CSVY → gnuplot → LaTeX pipeline described in the
[top-level README](../README.md). Read them in order; each builds on the last.

| # | Tutorial | You will learn |
|---|---|---|
| 1 | [101: sizing a figure in LaTeX](101.md) | `\gnuplotfit` vs `\includegraphics`; natural size; stretching width and height; one- and two-column layouts |
| 2 | [A sample Gantt chart](sample-gantt-chart.md) | writing a `.csvy`; the tested settings vs the bare defaults; how editing the data changes the chart |
| 3 | [Advanced Gantt chart](advanced-gantt-chart.md) | the template's settings by their gnuplot names: bar thickness, margins (gutters), natural size, grid, title |

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

The `.csvy` files say `template: templates/gantt.gp`, exactly as they would
in the top folder, so you can copy any of them there and run `make`.

## Conventions

- **Dashed red frame:** the area the figure was asked to fill (its `fig`
  size, or the size given to `\gnuplotfit`). Anything outside it is
  overflow.
- **Names:** settings are given by their YAML keys (`margin: {l: 2.0}`) and,
  where it helps, by the gnuplot variable they become (`margin_l`).
- **Tested settings:** these are the values in the top folder's
  `project.csvy`, which the regression tests pin down; the tutorials start
  from them.
