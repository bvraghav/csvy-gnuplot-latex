# gnuplot figures for LaTeX from CSVY

Version 0.0.8

**Docs:** [Overview](doc/README.md) ·
Tutorials: [101: sizing in LaTeX](doc/tutorials/101.md),
[sample Gantt chart](doc/tutorials/sample-gantt-chart.md),
[advanced Gantt chart](doc/tutorials/advanced-gantt-chart.md) ·
[Reference](doc/REFERENCE.md)

Write a figure once as a **CSVY** file (YAML settings + CSV data). The build
turns it into a gnuplot **TikZ** figure that LaTeX typesets in the document's
own fonts. In LaTeX you can still stretch it to any width and height.

```
NAME.csvy ──inp2gp.py──► NAME.gp    vars as gnuplot variables, gnuplot entries as
    + STEM.csvy          │           'set' lines, then load 'STEM.gp'
      (defaults)         ├─► NAME.dat   data rows, re-written for gnuplot's reader
                         └─► NAME.d     make dependencies (includes both template files)
gnuplot NAME.gp      ──► NAME.gp.tex (TikZ)
\gnuplotfit[w][h]{NAME.gp.tex}      ──► the figure, at the size LaTeX asks for
```

`inp2gp.py` knows nothing about any plot. The chart itself lives in a
template, e.g. `templates/gantt`: the script `gantt.gp` plus its defaults
`gantt.csvy`. One template can serve any number of inputs, and each input
lists only what differs from the defaults.

## Requirements

- Python 3 with PyYAML
- gnuplot 5.4+ with the `tikz` terminal (tested with 6.0)
- GNU make
- optional: `entr` for `make watch`; `pandoc` (3.x) for `make site`
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
make site       # build the docs website into doc/build/site/ (needs pandoc)
make DOC=paper.tex
```

New here? Start with the [tutorials](doc/README.md): sizing a figure in
LaTeX, a sample Gantt chart, and the template's settings. The complete rules
(input format, generator, template contract, Makefiles) are in the
[reference](doc/REFERENCE.md).

In the document:

```latex
\usepackage{gnuplotfit}
...
\begin{figure}\centering
  \gnuplotfit[\linewidth][10\baselineskip]{project.gp.tex}
  \caption{...}
\end{figure}
```

A minimal input names a template and gives the data; see the
[sample tutorial](doc/tutorials/sample-gantt-chart.md):

```
---
template: templates/gantt
vars: {t: {end: 24.0, grid: 2.0}}
gnuplot: {xlabel: "'Time (months)'"}
---
Index,Start,End,Color,Buffer,BufferColor,Label
1,0.0,2.0,#29bb78,0.5,#69cfa1,KRA
```

A `.csvy` file is code: its `gnuplot:` entries run as written, and gnuplot
can run shell commands. Only build files you trust.

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

## Tests

```sh
make test               # or: make -C test
make -C test golden     # refresh test/golden/ after an intended change
```

`test/test_inp2gp.py` (Python `unittest`) runs each test in a temporary copy of
the sources, so it leaves no files behind. Tests that need gnuplot, make or
latexmk are skipped when the tool is missing.

| Group | Checks |
|---|---|
| `Generator` | `project.*` outputs match `test/golden/`; `vars` → variables, merged over the defaults (including `exists()`-only vars); `gnuplot` → `set`/`unset` lines and merging; mapping and list headers give the same output; `--template` and the optional `.gp`; template path relative to the input; CSV → `.dat` rewrite; 31 kinds of bad input and 4 kinds of bad template each give a clear error and write nothing |
| `Gnuplot` | `strcol()` returns data text exactly (the `.dat` contract); the figure matches the golden copy; LaTeX labels and the automatic `t_end` (`test/cases/tricky.csvy`); `gnuplot:` entries reach the figure while a var the template uses wins; the template refuses to run on its own |
| `Make` | a fresh build is up to date; editing the template's script or defaults, the `.csvy` or `inp2gp.py` triggers a rebuild; make never tries to build a template from its defaults; figures have no date line and rebuild to the same bytes; `make check` passes, then catches an out-of-date and a missing figure; `clean` keeps figures, `distclean` removes them; a failed figure leaves no output |
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
| `templates/gantt.gp`, `templates/gantt.csvy` | Gantt chart template: script and defaults |
| `gnuplotfit.sty` | `\gnuplotfit` |
| `Makefile` | build rules, `check`, `watch`, `docs`, `clean` / `distclean` |
| `.gitignore` | intermediates and LaTeX auxiliaries (see Version control) |
| `.github/workflows/docs.yml` | builds the docs website and publishes it to GitHub Pages |
| `project.csvy` | example input |
| `test-v6.tex` | example document |
| `test/` | regression tests: `test_inp2gp.py`, `Makefile`, `cases/`, `golden/` |
| `doc/` | `README.md` (contents), `REFERENCE.md`, `tutorials/`, their inputs (`examples/`), images (`img/`, committed) and `Makefile` |
| `VERSION`, `LICENSE` | 0.0.8, MIT |

Generated files (don't edit them): `NAME.gp`, `NAME.dat`, `NAME.d` (all
ignored), and `NAME.gp.tex` (committed; regenerate it with `make figs`).

## License

MIT. See `LICENSE`.
