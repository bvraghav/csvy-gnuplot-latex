# gnuplot figures for LaTeX from CSVY

Version 0.0.7

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
template: templates/gantt          # required (or --template); relative to this file
vars:                              # gnuplot variables the template computes with
  t: {end: 24.0, grid: 2.0}
gnuplot:                           # 'set <key> <value>', run before the template
  xlabel: "'Time (months)'"
  mxtics: 2
---
Index,Start,End,Color,Buffer,BufferColor,Label
1,0.0,2.0,#29bb78,0.5,#69cfa1,KRA
2,0.0,3.0,#2972db,1.0,#699ce6,"Label, with a comma"
```

The frontmatter is a mapping with up to three keys, or a list of one-key
mappings (`- template: …`, `- vars: …`), whichever you prefer:

| Key | Required | Meaning |
|---|---|---|
| `template` | yes | `path/to/STEM`: `STEM.gp` is the plot script, `STEM.csvy` its defaults. A trailing `.gp` is allowed. Relative to the `.csvy` |
| `vars` | no | values for the template's variables; applied over `STEM.csvy`'s |
| `gnuplot` | no | gnuplot settings; applied over `STEM.csvy`'s |

- **CSV rules**: a real CSV parser reads the table, so quote fields that
  contain commas. Blank lines are skipped. Every row must have as many fields
  as the header.
- **Labels** are gnuplot strings inside YAML strings: `xlabel: "'Time'"`.
  With LaTeX backslashes, use a `>-` block, because YAML's double quotes
  would turn `\t` into a TAB:
  ```yaml
  gnuplot:
    xlabel: >-
      'Time (\textit{months})'
  ```
- **Trust**: a `.csvy` file is code. `gnuplot:` entries run as written,
  and gnuplot can run shell commands (`` `…` ``, `set print "|…"`).
  Only build `.csvy` files you trust.

## 2. Generator: `inp2gp.py`

```sh
inp2gp.py [--template=STEM] NAME.csvy
```

It writes `NAME.gp`, `NAME.dat` and `NAME.d` next to the input.
`--template` overrides the frontmatter's `template`, and is relative to the
current folder. The generator checks everything before writing, so on any
error it writes nothing.

### Header → `NAME.gp`

```gnuplot
# Generated by inp2gp from NAME.csvy -- edit that file instead.
data_file = 'NAME.dat'                 # set by inp2gp (reserved)
out_file = 'NAME.gp.tex'
N_rows = 5
# vars: templates/gantt.csvy, then NAME.csvy
t_start = 0.0
...
# gnuplot: templates/gantt.csvy, then NAME.csvy
set xlabel 'Time (months)'
...
load 'templates/gantt.gp'
```

**Merging:** `STEM.csvy` supplies the defaults, and `NAME.csvy`'s entries
replace them key by key.
- **`vars`** are compared after flattening, so `margin: {l: 3.4}` replaces
  `margin_l` only.
- **`gnuplot`** entries with the same key replace *all* the defaults' entries
  for that key, in their place; new keys go at the end.

**`vars` → variables:**

| YAML | gnuplot |
|---|---|
| nested map `fig: {w: 8}` | flattened with `_`: `fig_w = 8` |
| integer / float | number as written (`2` stays an integer) |
| `true` / `false` | `1` / `0` |
| string, date | single-quoted, `'` doubled; backslashes kept as is |
| list of scalars | `array name[n] = [...]` |
| null, nested list, multi-line string | error |

- **Names:** each flattened name must be a valid gnuplot name
  (`[A-Za-z_][A-Za-z0-9_]*`), and must not be one of the reserved
  `data_file`, `out_file` or `N_rows`.
- **Known vars only:** a var must be in `STEM.csvy`, or tested with
  `exists("…")` in `STEM.gp`. Anything else is an error, which catches
  typos.

**`gnuplot` → `set` lines:**

| YAML value | Line |
|---|---|
| string or number | `set <key> <value>`, as written |
| `true`, or empty | `set <key>` |
| `false` | `unset <key>` |
| list, map, multi-line string | error |

- **Repeated keys:** use the list form, e.g. `- label: "1 'a' at 0,0"` and
  `- label: "2 'b' at 1,1"`.
- **Reserved:** a key whose first word is `terminal`, `output`, `datafile`
  or `table`, or an abbreviation of one (`term`, `out`, …), is an error.
  Those settings belong to the template and `inp2gp`.
- **Order and precedence:** the `set` lines run *before* the template. A
  setting the template makes from a var (e.g. the x range from `t_*`) wins;
  anything the template leaves alone keeps the `gnuplot:` value.

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
NAME.gp NAME.dat NAME.d: templates/gantt.csvy
templates/gantt.gp: ;
templates/gantt.csvy: ;
```

The Makefile includes these files. Editing a template's script redraws every
figure that uses it, and editing its defaults also regenerates their
`NAME.gp`. `STEM.gp` and `STEM.csvy` look like an output and its input to
make's `%.gp: %.csvy` rule; the empty recipes (`: ;`) mark them as sources,
so make never tries to build one from the other.

## 3. Template contract

A template is two files with the same stem.

**`STEM.gp`** is an ordinary gnuplot script that:

1. **reads the data** from `data_file` with
   ```gnuplot
   set datafile separator tab
   set datafile commentschars ""
   set datafile columnheaders
   ```
   and refers to columns by header name, e.g. `column("Start")` and
   `strcol("Label")`;
2. **writes** a `tikz` figure to `out_file`;
3. **uses its vars directly**, with no defaults of its own. The only
   exception is a default that has to be computed, guarded with
   `if (!exists("x"))`, such as the Gantt template's `t_end`;
4. **sets only what it must:** things computed from vars (terminal size,
   margins, ranges) and what the chart needs to be correct. Styling belongs
   in `STEM.csvy`'s `gnuplot:` section, where users can override it. A
   `set` in the script would silently overwrite theirs.

**`STEM.csvy`** holds the defaults: a header with `vars:` and `gnuplot:`
sections and no data. It lists every var the script uses. A var that has no
default (like `t_end`) can be left in as a comment, for documentation.

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

## 5. Template: `templates/gantt`

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

**`vars`** (defaults in `templates/gantt.csvy`):

| Key | Default | Meaning |
|---|---|---|
| `t: {start, end, grid}` | `0`, *fit*, `1` | x range and labelled-tick spacing; without `end`, the axis ends at the last buffer's end, rounded up to `grid` |
| `fig: {w, h}` | `8.0`, `4.0` | natural size in cm |
| `margin: {l, b}` | `2.0`, `1.2` | left / bottom margin in cm (room for task names / x-axis text) |
| `bar_height` | `0.6` | bar thickness as a fraction of the row spacing |
| `show_text` | `true` | print durations inside the task bars |

**`gnuplot`** defaults: `xlabel 'Time'`, `mxtics 1`, `ytics scale 0`, a
light vertical `grid`, `border 3`, `tics nomirror`, `unset key`. Any of them
can be overridden, and any other setting can be added, e.g. `title`, or
`ylabel "'Task' offset -1.5,0"`.

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
| `project.csvy` | example input |
| `test-v6.tex` | example document |
| `test/` | regression tests: `test_v6.py`, `Makefile`, `cases/`, `golden/` |
| `doc/` | tutorials (`*.md`), their inputs (`examples/`), images (`img/`, committed) and `Makefile` |
| `VERSION`, `LICENSE` | 0.0.7, MIT |

Generated files (don't edit them): `NAME.gp`, `NAME.dat`, `NAME.d` (all
ignored), and `NAME.gp.tex` (committed; regenerate it with `make figs`).

## License

MIT. See `LICENSE`.
