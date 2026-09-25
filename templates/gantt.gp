# ==============================================================================
# GANTT CHART TEMPLATE (tikz output, for \gnuplotfit)
# ==============================================================================
# Loaded by NAME.gp, which inp2gp generates from NAME.csvy.
#
# Set by inp2gp:
#   data_file   tab-separated data with a header row
#   out_file    tikz output, \input via \gnuplotfit{NAME.gp.tex}
#   N_rows      number of data rows
#
# Data columns, by header name (any order; extra columns are ignored):
#   Index        row position, 1 to N from bottom to top
#   Start, End   task bar
#   Color        task colour, "#rrggbb"
#   Buffer       buffer length, drawn from End to End+Buffer
#   BufferColor  buffer colour, "#rrggbb"
#   Label        task name (LaTeX)
#
# Vars (defaults and meanings in gantt.csvy, next to this file):
#   t_start, t_end, t_grid   x range and labelled-tic spacing; t_end is
#                            optional: without it the axis fits the data
#   fig_w, fig_h             natural size in cm
#   margin_l, margin_b       left / bottom margin in cm
#   bar_height, show_text    bar thickness (fraction of a row); durations
#
# Everything else (labels, grid, border, tics, key) is plain gnuplot, set in
# the 'gnuplot:' section of gantt.csvy / NAME.csvy before this file runs.

if (!exists("data_file") || !exists("out_file")) \
    exit error "gantt.gp: data_file and out_file must be set (run NAME.gp, not this file)"

# ==============================================================================
# DATA
# ==============================================================================
# inp2gp's format: tabs, no quoting, backslashes already doubled for strcol().
set datafile separator tab
set datafile commentschars ""
set datafile columnheaders

stats data_file using (column("Index")) nooutput
N = STATS_max

# t_end defaults to the end of the last buffer, rounded up to the grid.
if (!exists("t_end")) {
    stats data_file using (column("End") + column("Buffer")) nooutput
    t_end = t_start + t_grid * ceil((STATS_max - t_start) / t_grid)
}

# ==============================================================================
# PLOT
# ==============================================================================
# TikZ output: unitless coordinates, so LaTeX can stretch it without touching text.
eval sprintf('set terminal tikz latex size %gcm,%gcm', fig_w, fig_h)
set output out_file

# Fixed margins: gnuplot's automatic ones only guess the LaTeX text size.
set lmargin at screen margin_l / fig_w
set bmargin at screen margin_b / fig_h

# "#rrggbb" -> 0xrrggbb integer, for 'lc rgb variable'
hex2rgb(s) = int(("0x" . s[2:7]) + 0)
dur(a, b) = sprintf("%g", b - a)

set xrange [t_start:t_end]
set yrange [0.5:N + 0.5]
set xtics t_start, t_grid, t_end

h = bar_height / 2.0

# Task bar: Start..End.  Buffer bar: End..End+Buffer.
# ytic() takes strcol() as is; 'with labels' would need esc_bs() around text.
plot data_file \
       using ((column("Start") + column("End")) / 2.0):(column("Index")) \
            :((column("End") - column("Start")) / 2.0):(h) \
            :(hex2rgb(strcol("Color"))):ytic(strcol("Label")) \
       with boxxyerror fs solid 0.9 noborder lc rgb variable, \
     data_file \
       using (column("End") + column("Buffer") / 2.0):(column("Index")) \
            :(column("Buffer") / 2.0):(h) \
            :(hex2rgb(strcol("BufferColor"))) \
       with boxxyerror fs solid 0.9 noborder lc rgb variable, \
     data_file \
       using ((column("Start") + column("End")) / 2.0):(column("Index")) \
            :(show_text ? dur(column("Start"), column("End")) : "") \
       with labels tc rgb "white"
