# gnuplot figures for LaTeX from CSVY

Version 0.0.6

Write a figure once as a **CSVY** file (YAML settings + CSV data). The build
turns it into a gnuplot **TikZ** figure that LaTeX typesets in the document's
own fonts. In LaTeX you can still stretch it to any width and height.

```
NAME.csvy ──inp2gp.py──► NAME.gp    settings as gnuplot variables + load '<template>'
                     ├─► NAME.dat   data rows, re-written for gnuplot's reader
                     └─► NAME.d     make dependencies (includes the template)
gnuplot NAME.gp      ──► NAME.gp.tex (TikZ)
\gnuplotfit[w][h]{NAME.gp.tex}      ──► the figure, at the size LaTeX asks for
```

`inp2gp.py` knows nothing about any plot. The chart itself lives in a
template, e.g. `templates/gantt.gp`, and one template can serve any number
of inputs.

## Requirements

- Python 3 with PyYAML
- gnuplot 5.4+ with the `tikz` terminal (tested with 6.0)
- GNU make
- optional: `entr` for `make watch`
- LaTeX with TikZ and `gnuplot-lua-tikz.sty` (ships with gnuplot); any
  engine (tested with XeLaTeX via latexmk)

## Quick start

```sh
make            # build every *.csvy into *.gp.tex, then latexmk $(DOC)
make figs       # figures only
make check      # fail if a committed *.gp.tex no longer matches its sources
make clean      # remove intermediates and LaTeX auxiliaries; keep *.gp.tex
make distclean  # clean, and remove *.gp.tex too
make test       # run the regression tests (see Tests)
make watch      # rebuild on every save (needs entr); WATCH_TARGET=figs for figures only
make docs       # render the tutorial images in doc/img/
make DOC=paper.tex
```

New here? Start with the [tutorials](doc/README.md): sizing a figure in
LaTeX, a sample Gantt chart, and the template's settings.

In the document:

```latex
\usepackage{gnuplotfit}
...
\begin{figure}\centering
  \gnuplotfit[\linewidth][10\baselineskip]{project.gp.tex}
  \caption{...}
\end{figure}
```

`make watch` watches the `.csvy` files, the templates, `inp2gp.py`,
`gnuplotfit.sty` and `$(DOC)`, and runs `make` (or `make $(WATCH_TARGET)`)
whenever one is saved. It also notices new `.csvy` files. Stop it with
Ctrl-C.

To debug a figure without make, run `gnuplot NAME.gp` from the input's folder.
(That output keeps gnuplot's date line; use `make figs` for the committed copy.)

## Version control

`.gitignore` lists what is committed and what isn't:

| Committed | Ignored |
|---|---|
| sources: `*.csvy`, `templates/`, `inp2gp.py`, `gnuplotfit.sty`, `Makefile`, `*.tex` documents, `test/` (including `test/golden/`), `doc/` (including `doc/img/`) | intermediates `NAME.gp`, `NAME.dat`, `NAME.d`; LaTeX auxiliaries; `test-v6.pdf`; `__pycache__/`; `doc/build/` |
| **figures: `NAME.gp.tex`** | |

Why the figures are committed:

- **The document builds without the toolchain.** Anyone who only compiles
  it (co-authors, Overleaf, arXiv) needs LaTeX with TikZ and
  `gnuplotfit.sty`, but not Python, PyYAML, gnuplot or make.
- **Rebuilds are repeatable.** gnuplot writes the date into every figure;
  the Makefile removes that line, so rebuilding an unchanged figure gives the
  same bytes and no diff. The gnuplot version line is kept.
- **Figures can't quietly go stale.** `make check` rebuilds every figure from
  scratch in a temporary copy and compares it with the one in the folder. It
  fails with `NAME.gp.tex is out of date` or `is missing`; `make figs` fixes
  either. Run it before committing, or as a pre-commit hook:
  ```sh
  printf '#!/bin/sh\nexec make -s check\n' > .git/hooks/pre-commit
  chmod +x .git/hooks/pre-commit
  ```
  `make check` compares against the working tree, not what is staged.

The ignore patterns start with `/` (`/*.gp`, not `*.gp`), so they apply to
the top folder only: `templates/*.gp` and `test/golden/*` are sources. A
hand-written `.gp` in the top folder would be ignored too, so keep those in
`templates/` or a subfolder.

## 1. Input: `NAME.csvy`

This is a YAML frontmatter block between `---` lines, followed by a standard
CSV table with a header row.

```
---
template: templates/gantt.gp   # required; relative to this file
x_label: Time (months)
t: {start: 0.0, end: 24.0, grid: 2.0, minor: 2}
fig: {w: 8.0, h: 4.0}
---
Index,Start,End,Color,Buffer,BufferColor,Label
1,0.0,2.0,#29bb78,0.5,#69cfa1,KRA
2,0.0,3.0,#2972db,1.0,#699ce6,"Label, with a comma"
```

- **`template`**: the only reserved key. It gives the path to the gnuplot
  template, relative to the `.csvy` file.
- **Other keys**: they are handed to the template unchanged (see §2).
- **CSV rules**: a real CSV parser reads the table, so quote fields that
  contain commas. Blank lines are skipped. Every row must have as many fields
  as the header.

## 2. Generator: `inp2gp.py`

`inp2gp.py NAME.csvy` writes `NAME.gp`, `NAME.dat` and `NAME.d` next to the
input. It checks everything before writing, so on any error it writes
nothing.

### Frontmatter → gnuplot variables (`NAME.gp`)

| YAML | gnuplot |
|---|---|
| nested map `fig: {w: 8}` | flattened with `_`: `fig_w = 8` |
| integer / float | number as written (`2` stays an integer) |
| `true` / `false` | `1` / `0` |
| string, date | single-quoted, `'` doubled; backslashes kept as is |
| list of scalars | `array name[n] = [...]` |
| null, nested list, multi-line string | error |

- **Key names**: after flattening, each key must be a valid gnuplot name
  (`[A-Za-z_][A-Za-z0-9_]*`).
- **Also set by `inp2gp`** (reserved): `data_file`, `out_file` (always
  `NAME.gp.tex`) and `N_rows` (the number of data rows).
- **Last line of `NAME.gp`**: `load '<template>'`.

### Data → `NAME.dat`

gnuplot's own CSV reader breaks on quoted commas, so `inp2gp.py` re-writes the
rows in a form gnuplot reads exactly:

- **Separator**: tabs, with no quoting.
- **Backslashes**: doubled. `strcol()` undoes backslash escapes once, so it
  then returns the text exactly as written in the `.csvy`.
- **Rejected characters**: a `"`, tab or newline inside a field is an error,
  because gnuplot's reader can't carry them. For quotes in LaTeX text, use
  ``` ``…'' ``` or `\textquotedbl`.

### Dependencies → `NAME.d`

```make
NAME.gp.tex: NAME.gp NAME.dat templates/gantt.gp
templates/gantt.gp:
```

The Makefile includes these files, so editing a template redraws every
figure that uses it. The empty rule keeps make working if a template is
renamed.

## 3. Template contract

A template is an ordinary gnuplot script that:

1. **reads the data** from `data_file` with
   ```gnuplot
   set datafile separator tab
   set datafile commentschars ""
   set datafile columnheaders
   ```
   and refers to columns by header name, e.g. `column("Start")` and
   `strcol("Label")`;
2. **writes** a `tikz` figure to `out_file`;
3. **gives every setting a default** in the form
   `if (!exists("x")) x = ...`.

Things to watch for:

- **Escaping in `with labels`**: `ytic(strcol(...))` passes text through
  unchanged, but `with labels` applies escapes once more. Wrap the text in
  `esc_bs()`:
  ```gnuplot
  bs = "\\"
  esc_bs(s) = (_i = strstrt(s, bs)) ? s[1:_i] . bs . esc_bs(s[_i+1:]) : s
  ```
- **Integer division**: YAML integers stay integers, so write `x / 2.0`
  rather than `x / 2`.
- **Size and margins**: set the terminal size in cm and fix the margins. For
  example, `set lmargin at screen margin_l / fig_w` stops the text sticking
  out, because gnuplot can only guess how wide LaTeX will make it.

## 4. LaTeX: `gnuplotfit.sty`

```latex
\gnuplotfit[<width>][<height>]{<file>}
```

- **Arguments**: `<width>` defaults to `\linewidth`; `<height>` defaults to
  the figure's natural height. Both take any length: `\columnwidth`,
  `0.9\textwidth`, `10\baselineskip`, `4cm`, …
- **How it works**: the macro measures the figure at its natural size, then
  sets `xscale`/`yscale` so the result is exactly the requested size. Text
  stays at the document's normal size.
- **Only stretch**: going below the natural size makes the fixed-size text
  overlap. Set the template's natural size (`fig_w`, `fig_h`) to about the
  smallest size you'll use.
- **Margins stretch too**: the gaps between axis, tick labels and axis
  label grow with the figure.

## 5. Template: `templates/gantt.gp`

A Gantt chart in which each task bar is followed by a lighter buffer bar.

**Columns** (by name; any order; extra columns are ignored):

| Column | Meaning |
|---|---|
| `Index` | row, 1 = bottom |
| `Start`, `End` | task bar |
| `Color` | task colour, `#rrggbb` |
| `Buffer` | buffer length, drawn from `End` to `End + Buffer` |
| `BufferColor` | buffer colour, `#rrggbb` |
| `Label` | task name (LaTeX) |

**Settings** (all optional):

| Key | Default | Meaning |
|---|---|---|
| `plot_title` | `""` | title |
| `x_label`, `y_label` | `"Time"`, `""` | axis labels |
| `t: {start, end, grid, minor}` | `0`, *fit*, `1`, `1` | x range, major tic spacing, minor tics per major; if `end` is omitted, it is the last buffer's end rounded up to the grid |
| `bar_height` | `0.6` | bar thickness as a fraction of the row spacing |
| `show_text` | `true` | print durations inside the task bars |
| `fig: {w, h}` | `8.0`, `4.0` | natural size in cm |
| `margin: {l, b}` | `2.0`, `1.2` | left / bottom margin in cm (room for task names / x-axis text) |

The example `project.csvy` uses buffers of ~30 % of each task's length,
rounded to 0.5, with each buffer colour blended 30 % toward white. These
values are typed into the data; the generator computes nothing.

## Tests

```sh
make test               # or: make -C test
make -C test golden     # refresh test/golden/ after an intended change
```

`test/test_v6.py` (Python `unittest`) runs each test in a temporary copy of
the sources, so it leaves no files behind. Tests that need gnuplot, make or
latexmk are skipped when the tool is missing.

| Group | Checks |
|---|---|
| `Generator` | `project.*` outputs match `test/golden/`; YAML → gnuplot mapping; CSV → `.dat` rewrite; template path relative to the input; 20 kinds of bad input each give a clear error and write nothing |
| `Gnuplot` | `strcol()` returns data text exactly (the `.dat` contract); the figure matches the golden copy; LaTeX labels and the automatic `t_end` (`test/cases/tricky.csvy`); the template refuses to run on its own |
| `Make` | a fresh build is up to date; editing the template, the `.csvy` or `inp2gp.py` triggers a rebuild; figures have no date line and rebuild to the same bytes; `make check` passes, then catches an out-of-date and a missing figure; `clean` keeps figures, `distclean` removes them; a failed figure leaves no output |
| `LaTeX` | `\gnuplotfit` hits the requested width and height to within 0.01 pt (`test/cases/fit.tex`) |

The golden figure leaves out the `%%` comment lines, which hold the gnuplot
version (and, outside make, the date). A different gnuplot version may still
change the coordinates slightly. If that happens, check the new output and
run `make -C test golden`. After a gnuplot upgrade, `make check` may flag
the committed figures for the same reason; `make figs` updates them.

## Files

| File | |
|---|---|
| `inp2gp.py` | generator: CSVY → `.gp` + `.dat` + `.d` |
| `templates/gantt.gp` | Gantt chart template |
| `gnuplotfit.sty` | `\gnuplotfit` |
| `Makefile` | build rules, `check`, `watch`, `docs`, `clean` / `distclean` |
| `.gitignore` | intermediates and LaTeX auxiliaries (see Version control) |
| `project.csvy` | example input |
| `test-v6.tex` | example document |
| `test/` | regression tests: `test_v6.py`, `Makefile`, `cases/`, `golden/` |
| `doc/` | tutorials (`*.md`), their inputs (`examples/`), images (`img/`, committed) and `Makefile` |
| `VERSION`, `LICENSE` | 0.0.6, MIT |

Generated files (don't edit them): `NAME.gp`, `NAME.dat`, `NAME.d` (all
ignored), and `NAME.gp.tex` (committed; regenerate it with `make figs`).

## License

MIT. See `LICENSE`.
