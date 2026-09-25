# A sample Gantt chart

This tutorial builds a Gantt chart from a CSV table, first with only the
defaults and then with the tested settings. It then edits the data (never
the settings) to show how the chart follows.

Each task is drawn as a bar from `Start` to `End`, followed by a lighter
*buffer* bar of length `Buffer`: slack in case the task overruns.

## 1. The input file

A `.csvy` file is YAML settings between `---` lines, then a CSV table. The
smallest useful one names the template and gives the data:

```
---
template: templates/gantt.gp
---
Index,Start,End,Color,Buffer,BufferColor,Label
1,0.0,2.0,#29bb78,0.5,#69cfa1,KRA
2,0.0,3.0,#2972db,1.0,#699ce6,EEM
3,0.0,4.0,#eb6034,1.0,#f19071,AAM
4,5.0,10.0,#eb9c00,2.0,#f1ba4c,2D-AGM
5,9.0,20.0,#ee759e,3.0,#f39ebb,3D-AGM
```

[`examples/sample-minimal.csvy`](examples/sample-minimal.csvy)

| Column | Meaning |
|---|---|
| `Index` | the row: 1 at the bottom, counting up |
| `Start`, `End` | the task bar, in any time unit |
| `Color` | the task's colour, `#rrggbb` |
| `Buffer` | the buffer's length, drawn from `End` to `End + Buffer` |
| `BufferColor` | the buffer's colour, `#rrggbb` |
| `Label` | the task's name; LaTeX is allowed |

Save it as `schedule.csvy` in the top folder and build it:

```sh
make figs          # schedule.csvy -> schedule.gp.tex
```

Then, in LaTeX: `\gnuplotfit{schedule.gp.tex}` (see [101](101.md)).

With nothing but defaults, the chart looks like this:

![The chart with default settings: the time axis has a tick at every unit from 0 to 23 and the numbers run together](img/sample-minimal.png)

The bars are right, but the defaults need help:

- **The axis is crowded.** The default grid is 1, so there's a labelled tick
  at every unit from 0 to 23.
- **The axis label is generic:** "Time".
- **The axis stops at 23:** the end of the last buffer, rounded up to the
  grid.

## 2. The tested settings

The top folder's `project.csvy` adds settings that have been checked by the
regression tests. Use them as your starting point:

```
---
# Gantt chart: each task is followed by a buffer bar.
template: templates/gantt.gp
plot_title: ""
x_label: Time (months)
y_label: ""
t: {start: 0.0, end: 24.0, grid: 2.0, minor: 2}   # drop 'end' to fit the data
fig: {w: 8.0, h: 4.0}        # natural size in cm; LaTeX only stretches it
margin: {l: 2.0, b: 1.2}     # cm; room for task names / x-axis text
bar_height: 0.6
show_text: true
---
Index,Start,End,Color,Buffer,BufferColor,Label
1,0.0,2.0,#29bb78,0.5,#69cfa1,KRA
2,0.0,3.0,#2972db,1.0,#699ce6,EEM
3,0.0,4.0,#eb6034,1.0,#f19071,AAM
4,5.0,10.0,#eb9c00,2.0,#f1ba4c,2D-AGM
5,9.0,20.0,#ee759e,3.0,#f39ebb,3D-AGM
```

[`examples/sample-base.csvy`](examples/sample-base.csvy)

![The chart with the tested settings: ticks every 2 months up to 24 and a "Time (months)" axis label](img/sample-base.png)

| Setting | Tested value | Default | Effect |
|---|---|---|---|
| `x_label` | `Time (months)` | `Time` | x-axis label |
| `t: {start, end}` | `0`, `24` | `0`, fit to the data | x-axis range |
| `t: {grid, minor}` | `2`, `2` | `1`, `1` | a labelled tick every 2, with one minor tick between |
| `fig: {w, h}` | `8`, `4` | same | natural size in cm |
| `margin: {l, b}` | `2.0`, `1.2` | same | room for task names and x-axis text, in cm |
| `bar_height` | `0.6` | same | bar thickness as a fraction of the row spacing |
| `show_text` | `true` | same | durations (`End − Start`) printed inside task bars |
| `plot_title`, `y_label` | `""` | same | no title, no y-axis label |

The [advanced tutorial](advanced-gantt-chart.md) changes these settings. The
rest of this page keeps them fixed and changes only the data.

The data follows two rules of thumb:
- **Buffers** are about 30 % of each task's length, rounded to 0.5.
- **Buffer colours** are the task colour blended 30 % toward white.

You type both into the table yourself; the tools compute nothing.

## 3. Changing the data

Each example below is `sample-base.csvy` with only the lines shown changed.

### Move tasks

Start 2D-AGM a month later and make it a month longer; start 3D-AGM three
months later and finish it one month later:

```diff
-4,5.0,10.0,#eb9c00,2.0,#f1ba4c,2D-AGM
-5,9.0,20.0,#ee759e,3.0,#f39ebb,3D-AGM
+4,6.0,12.0,#eb9c00,2.0,#f1ba4c,2D-AGM
+5,12.0,21.0,#ee759e,3.0,#f39ebb,3D-AGM
```

[`examples/sample-shift.csvy`](examples/sample-shift.csvy)

![2D-AGM now runs from 6 to 12 and 3D-AGM from 12 to 21; their duration labels read 6 and 9](img/sample-shift.png)

The bars move, and the durations inside them update (6 and 9). The axis
stays at 0–24 because `t.end` is fixed. 3D-AGM's buffer now ends at exactly
24, the edge of the chart.

### Add a task

Append a row. `Index` 6 puts it on top:

```diff
 5,9.0,20.0,#ee759e,3.0,#f39ebb,3D-AGM
+6,20.0,22.0,#8e44ad,0.5,#b07cc6,Report
```

[`examples/sample-add.csvy`](examples/sample-add.csvy)

![A sixth row, Report, at the top from 20 to 22; all rows are a little thinner](img/sample-add.png)

The figure stays 8 cm × 4 cm, so the six rows share the height that five had
before, and every bar gets thinner. If you add many rows, raise `fig.h` (see
*Natural size* in the [advanced tutorial](advanced-gantt-chart.md)).

### Reorder the rows

`Index` decides each task's row, whatever order the lines are in. Reverse it
so the chart reads top-down, in time order:

```diff
-1,0.0,2.0,#29bb78,0.5,#69cfa1,KRA
-2,0.0,3.0,#2972db,1.0,#699ce6,EEM
-3,0.0,4.0,#eb6034,1.0,#f19071,AAM
-4,5.0,10.0,#eb9c00,2.0,#f1ba4c,2D-AGM
-5,9.0,20.0,#ee759e,3.0,#f39ebb,3D-AGM
+5,0.0,2.0,#29bb78,0.5,#69cfa1,KRA
+4,0.0,3.0,#2972db,1.0,#699ce6,EEM
+3,0.0,4.0,#eb6034,1.0,#f19071,AAM
+2,5.0,10.0,#eb9c00,2.0,#f1ba4c,2D-AGM
+1,9.0,20.0,#ee759e,3.0,#f39ebb,3D-AGM
```

[`examples/sample-reorder.csvy`](examples/sample-reorder.csvy)

![The same chart upside down: KRA at the top, 3D-AGM at the bottom](img/sample-reorder.png)

### Let the axis follow the data

Stretch 3D-AGM to month 27 with a 5.5-month buffer, so it ends at 32.5,
beyond the fixed axis. Remove `end` from `t` so that the axis fits the data,
and widen the grid to 4 so that the longer axis doesn't crowd:

```diff
-t: {start: 0.0, end: 24.0, grid: 2.0, minor: 2}   # drop 'end' to fit the data
+t: {start: 0.0, grid: 4.0, minor: 2}   # no 'end': the axis fits the data
 ...
-5,9.0,20.0,#ee759e,3.0,#f39ebb,3D-AGM
+5,9.0,27.0,#ee759e,5.5,#f39ebb,3D-AGM
```

[`examples/sample-autofit.csvy`](examples/sample-autofit.csvy)

![The axis now runs from 0 to 36 in steps of 4, and 3D-AGM ends at 27 with its buffer reaching 32.5](img/sample-autofit.png)

Without `end`, the axis ends at the last buffer's end, rounded up to the grid:
32.5 becomes 36. With a fixed `end: 24.0`, the bar would have been cut off at
24 without warning, so leave `end` out whenever the data may grow.

## Things to know about the data

- **Commas in labels:** quote the field: `"Design, phase 1"`.
- **LaTeX in labels:** `\textbf{EEM}` and `A \& B` reach LaTeX unchanged.
  So does `&`, so write `\&`.
- **Double quotes** (`"`) can't be used inside a field, because gnuplot
  can't read them there. Use ``` ``…'' ``` for quotes in text.
- **Errors:** if a row has too few fields, or a field contains `"`, `make`
  stops with the file and line number and writes nothing.

Next: [the advanced Gantt chart](advanced-gantt-chart.md), which changes the
settings instead of the data.
