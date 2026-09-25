# Advanced Gantt chart

The [sample tutorial](sample-gantt-chart.md) changed the data. This one keeps
the data and changes the template's settings: bar thickness, the gutters
(margins) around the plot, the natural size, the grid and the labels.

Every example is `sample-base.csvy` with only the lines shown changed. The
dashed red frame marks the size the figure was asked to fill; anything
outside it is overflow.

## Setting names: YAML keys and gnuplot variables

Each frontmatter key becomes a gnuplot variable of the same name, and nested
keys are joined with `_`. These two blocks give identical figures (checked
byte for byte):

```yaml
# nested                                  # flat: the gnuplot names
t: {start: 0.0, end: 24.0,                t_start: 0.0
    grid: 2.0, minor: 2}                  t_end: 24.0
fig: {w: 8.0, h: 4.0}                     t_grid: 2.0
margin: {l: 2.0, b: 1.2}                  t_minor: 2
                                          fig_w: 8.0
                                          fig_h: 4.0
                                          margin_l: 2.0
                                          margin_b: 1.2
```

[`examples/adv-flat.csvy`](examples/adv-flat.csvy) is the flat form. Use
whichever reads better; the rest of this page gives both names.

| YAML | gnuplot | Default | Unit |
|---|---|---|---|
| `bar_height` | `bar_height` | 0.6 | fraction of the row spacing |
| `margin: {l}` | `margin_l` | 2.0 | cm |
| `margin: {b}` | `margin_b` | 1.2 | cm |
| `fig: {w, h}` | `fig_w`, `fig_h` | 8.0, 4.0 | cm |
| `t: {start, end}` | `t_start`, `t_end` | 0, fit to the data | time |
| `t: {grid, minor}` | `t_grid`, `t_minor` | 1, 1 | time; minor tics per major |
| `plot_title`, `x_label`, `y_label` | same | `""`, `Time`, `""` | LaTeX text |
| `show_text` | `show_text` | true | 1 / 0 |

## Anatomy of the figure

With the tested settings, measured from the generated TikZ:

```
 ┌──────────────────────── fig_w = 8.0 cm ───────────────────────┐
 │            top gutter 0.31 cm (automatic)                      │
 │           ┌──────────── plot area 5.45 cm ─────────┐           │
 │  3D-AGM   │              ▆▆▆▆▆▆▆▆▆▆▆▆▆▆▒▒▒▒▒        │           │
 │  2D-AGM   │       ▆▆▆▆▆▆▆▒▒▒                 row    │  right    │  fig_h
 │  AAM      │▆▆▆▆▆▒                            pitch  │  gutter   │  = 4.0 cm
 │  EEM      │▆▆▆▒                              0.50cm │  0.55 cm  │
 │  KRA      │▆▆▒                                      │ (auto)    │
 │           └─────────────────────────────────────────┘           │
 │ margin_l    0  2  4  6 …                     24                 │
 │ = 2.0 cm          Time (months)          margin_b = 1.2 cm      │
 └────────────────────────────────────────────────────────────────┘
```

- **Plot area:** the figure minus the gutters. Here it's 8.0 − 2.0 − 0.55 =
  5.45 cm wide and 4.0 − 1.2 − 0.31 = 2.49 cm tall.
- **Row pitch:** the plot height divided by the number of rows. Here it's
  2.49 / 5 = 0.50 cm.
- **Bar thickness:** `bar_height` × the row pitch, here 0.6 × 0.50 = 0.30 cm.
  The gap between bars is the remaining 0.20 cm.

So the thickness of a bar depends on `bar_height`, `fig_h`, `margin_b` and
the number of rows. The left and bottom gutters are yours to set. gnuplot
sets the top and right ones itself, to fit the last tick label and the title.

## Bar thickness: `bar_height`

```diff
-bar_height: 0.6
+bar_height: 0.3        # or 0.9
```

[`adv-bar-03.csvy`](examples/adv-bar-03.csvy),
[`adv-bar-09.csvy`](examples/adv-bar-09.csvy)

![Three charts with bar_height 0.3, 0.6 and 0.9; at 0.3 the white duration numbers are taller than the bars and partly vanish](img/adv-bar-height.png)

| `bar_height` | Bar | Gap between bars |
|---|---|---|
| 0.3 | 0.15 cm | 0.35 cm |
| 0.6 | 0.30 cm | 0.20 cm |
| 0.9 | 0.45 cm | 0.05 cm |

Nothing else moves: the plot area and row pitch stay the same. The duration
numbers are white, and at 0.3 they're taller than the bars, so the parts
outside the bars disappear against the background. With thin bars, set
`show_text: false`.

## Left gutter: `margin: {l}` / `margin_l`

The left gutter holds the task names. gnuplot can't measure LaTeX text, so
this width is fixed rather than guessed. Longer names need more room.
Relabel the tasks:

```diff
-1,0.0,2.0,#29bb78,0.5,#69cfa1,KRA
+1,0.0,2.0,#29bb78,0.5,#69cfa1,Literature review
 ...                                              (and the other four)
```

[`adv-margin-l-20.csvy`](examples/adv-margin-l-20.csvy),
[`adv-margin-l-34.csvy`](examples/adv-margin-l-34.csvy),
[`adv-margin-l-34-w94.csvy`](examples/adv-margin-l-34-w94.csvy)

![Three charts with long task names: at margin l 2.0 "Literature review" sticks out past the left edge of the red frame; at 3.4 the names fit but the axis numbers run together; at 3.4 with width 9.4 everything fits](img/adv-margin-l.png)

1. **`margin: {l: 2.0}`:** "Literature review" is about 2.7 cm wide and
   sticks out of the figure. In a document, the figure would be wider than
   you asked for and could hit the page margin.
2. **`margin: {l: 3.4}`:** the names fit, but the gutter takes the extra
   1.4 cm from the plot area (5.45 → 4.05 cm), and the axis numbers run
   together.
3. **`margin: {l: 3.4}` + `fig: {w: 9.4}`:** add the same 1.4 cm to the
   width. The plot area is back to 5.45 cm.

```diff
-fig: {w: 8.0, h: 4.0}
-margin: {l: 2.0, b: 1.2}
+fig: {w: 9.4, h: 4.0}
+margin: {l: 3.4, b: 1.2}
```

`\gnuplotfit` can then stretch it to any width from 9.4 cm up.

## Bottom gutter: `margin: {b}` / `margin_b`

The bottom gutter holds the tick numbers and the x-axis label.

```diff
-margin: {l: 2.0, b: 1.2}
+margin: {l: 2.0, b: 0.6}        # or b: 2.0
```

[`adv-margin-b-06.csvy`](examples/adv-margin-b-06.csvy),
[`adv-margin-b-20.csvy`](examples/adv-margin-b-20.csvy)

![Three charts with bottom margin 0.6, 1.2 and 2.0: at 0.6 the axis label crosses the bottom of the red frame; at 2.0 the rows are squeezed and there is empty space below](img/adv-margin-b.png)

| `margin.b` | Plot height | Row pitch | Bar (at 0.6) | Result |
|---|---|---|---|---|
| 0.6 | 3.09 cm | 0.62 cm | 0.37 cm | "Time (months)" crosses the bottom edge |
| 1.2 | 2.49 cm | 0.50 cm | 0.30 cm | fits: the tested value |
| 2.0 | 1.69 cm | 0.34 cm | 0.20 cm | fits, with 0.8 cm of empty space |

The gutter takes its height from the plot, so a bigger bottom gutter also
means thinner bars. 1.2 cm fits one row of tick numbers plus a one-line label.

## Natural size: `fig: {w, h}` / `fig_w`, `fig_h`

`\gnuplotfit` stretches everything except the text, *including the gutters*.
Compare two ways to get a 12 cm × 6 cm figure:

```diff
-fig: {w: 8.0, h: 4.0}
+fig: {w: 12.0, h: 6.0}
```

[`adv-fig-12x6.csvy`](examples/adv-fig-12x6.csvy); both are placed with
`\gnuplotfit[12cm][6cm]`.

![Two 12 by 6 cm charts: the stretched 8 by 4 one has wide empty gutters; the natural 12 by 6 one has tighter gutters and a bigger plot area](img/adv-fig-size.png)

| | Natural 8 × 4, stretched ×1.5 | Natural 12 × 6 |
|---|---|---|
| Left / bottom gutter | 3.0 cm / 1.8 cm (stretched) | 2.0 cm / 1.2 cm (as set) |
| Plot area | 8.2 cm × 3.7 cm | 9.4 cm × 4.5 cm |
| Bar | 0.45 cm | 0.54 cm |

The gutters only need to hold text, and text doesn't grow when the figure
does. Stretching a small figure a lot therefore wastes space in the
gutters. For a figure that will always be large, raise `fig` to near that
size, and keep `\gnuplotfit` for small adjustments. The same goes for adding
many rows: raise `fig.h` rather than letting the bars get thin.

## Grid: `t: {grid, minor}` / `t_grid`, `t_minor`

```diff
-t: {start: 0.0, end: 24.0, grid: 2.0, minor: 2}
+t: {start: 0.0, end: 24.0, grid: 6.0, minor: 3}
```

[`adv-grid.csvy`](examples/adv-grid.csvy)

![Labelled ticks at 0, 6, 12, 18 and 24 with two lighter minor lines between each](img/adv-grid.png)

- **`grid`** is the spacing of the labelled ticks and the darker grid lines.
- **`minor`** is the number of *intervals* between them, so `minor: 3`
  draws two lighter lines, one every 2 months here, and `minor: 1` draws
  none.

Choose `grid` so that the numbers don't collide. At the natural width of
8 cm, about 13 labels fit.

## Labels: `plot_title`, `x_label`, `show_text`

```diff
-plot_title: ""
-x_label: Time (months)
+plot_title: Project plan
+x_label: Months from kick-off
 ...
-show_text: true
+show_text: false
```

[`adv-labels.csvy`](examples/adv-labels.csvy)

![A chart titled "Project plan" with the x-axis label "Months from kick-off" and no numbers inside the bars](img/adv-labels.png)

- **The title takes its height from the plot:** gnuplot enlarges the top
  gutter automatically, so the rows get thinner, as with `margin.b`: here
  the plot height drops from 2.49 cm to 1.88 cm. In a
  paper, the figure's `\caption` usually replaces the title, so the tested
  value is `""`.
- **Labels are LaTeX:** `x_label: 'Time ($t$, months)'` works. In YAML, quote
  a value that contains `: ` or starts with a special character.

### A known limit: `y_label`

`y_label` works, but gnuplot places it beside the task names using its own
estimate of their width, which is too narrow for LaTeX text, so the two
overlap. Widening `margin.l` doesn't help, because it moves both. The task
names already label the axis, so the tested value is `""`. If you need a
y-axis label, put it in the caption for now. Fixing this would need a new
template setting (an offset for the label).

## Summary

| To… | Change |
|---|---|
| make bars thicker or thinner | `bar_height` (0–1) |
| fit longer task names | `margin.l`, and `fig.w` by the same amount to keep the plot area |
| make room for bigger axis text | `margin.b` |
| keep gutters tight in a large figure | raise `fig: {w, h}` rather than stretching a lot |
| fit many rows | raise `fig.h` |
| thin out the axis numbers | `t.grid`, `t.minor` |
| let the axis follow the data | remove `t.end` |
