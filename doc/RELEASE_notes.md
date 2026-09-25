# Release notes

Newest first. The complete record of changes is in
[CHANGELOG.md](../CHANGELOG.md).

## v1.0.0 — first stable release (2026-09-25)

Write a figure once as a **CSVY** file (YAML settings + CSV data); `make` turns
it into a gnuplot **TikZ** figure that LaTeX typesets in your document's own
fonts. In LaTeX, `\gnuplotfit` stretches it to any width and height while the
text keeps its size.

Docs: https://bvraghav.github.io/csvy-gnuplot-latex/

### Highlights

- **One input file per figure.** A `.csvy` names a template and lists only
  what differs from its defaults:

  ```yaml
  ---
  template: templates/gantt
  vars: {t: {end: 24.0, grid: 2.0}}
  gnuplot: {xlabel: "'Time (months)'"}
  ---
  Index,Start,End,Color,Buffer,BufferColor,Label
  1,0.0,2.0,#29bb78,0.5,#69cfa1,KRA
  ```

- **Plain gnuplot underneath.** Two kinds of setting:
  - `vars:` are the values the template calculates with;
  - `gnuplot:` entries become ordinary `set` commands, so any gnuplot setting
    works without editing the template.
- **Fits the page, keeps the text.**
  `\gnuplotfit[\linewidth][10\baselineskip]{fig.gp.tex}` stretches the drawing
  to exactly that size; labels stay at the document's font size, unlike
  `\includegraphics`.
- **A Gantt chart template** (`templates/gantt`): task bars with a lighter
  buffer bar after each, LaTeX task names, and an axis that fits the data.
- **Reliable builds.**
  - `make` rebuilds only what changed, including when a template changes.
  - Figures are repeatable, so they can be committed.
  - `make check` catches a committed figure that no longer matches its input.
  - `make watch` rebuilds on every save.
- **Overleaf-ready.** `make overleaf` collects everything a LaTeX project
  without gnuplot needs: gnuplot's TikZ style files, `gnuplotfit.sty` and the
  figures.
- **Documented and tested.**
  - three tutorials with rendered examples, and a complete reference;
  - 24 regression tests with golden outputs.

### Getting started

```sh
git clone https://github.com/bvraghav/csvy-gnuplot-latex
cd csvy-gnuplot-latex
make            # project.csvy -> project.gp.tex, then builds example.tex
```

Then read the [101 tutorial](tutorials/101.md) and
[Using it in your own paper](../README.md#using-it-in-your-own-paper).

**Requirements:**
- Python 3 with PyYAML;
- gnuplot 5.4+ (with the `tikz` terminal);
- GNU make;
- LaTeX with TikZ.

It has been tested with gnuplot 6.0, Python 3.14, TeX Live 2026 (XeLaTeX)
and GNU make 4.4.

### Stability

The interface documented in the [reference](REFERENCE.md) now follows semantic
versioning: breaking changes to it need a new major version. That covers:
- the `.csvy` format;
- `inp2gp.py`'s command line and outputs;
- the template contract;
- `\gnuplotfit`;
- the Gantt template;
- the Makefile targets.

### Known limitations

- **Stretch, don't shrink:** below a figure's natural size, its fixed-size
  text can overlap. Set the natural size (`vars: {fig: {w, h}}`) to about the
  smallest size you need.
- **Data fields can't contain `"`, tabs or newlines:** gnuplot's reader can't
  carry them. For quotes in text, use LaTeX's ``` ``…'' ```.
- **`gnuplot-lua-tikz.sty` isn't in TeX Live:** use `make overleaf` for
  Overleaf and similar setups.
- **A `.csvy` file is code:** `gnuplot:` entries run as written, so only
  build files you trust.

### Changes

Since 0.0.8: the docs website (with the README as its About page),
`make overleaf`, a guide to using the pipeline in your own paper, a changelog,
the tested-with versions, `test-v6.tex` renamed to `example.tex`, and a fix so
the site build doesn't re-render images. Full history:
[CHANGELOG.md](../CHANGELOG.md).
