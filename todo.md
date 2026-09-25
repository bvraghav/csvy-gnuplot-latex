# TODO

## 1. Version number in the site's nav bar, from `VERSION`

The version should appear in the nav bar on every page, taken from `VERSION`
at build time, so the version is still kept in one place.

- `doc/Makefile` already reads it (`VERSION := $(shell cat ../VERSION)`) and
  passes `-M version=…` to pandoc; today only the footer uses it.
- Add it next to the site name in `doc/site/template.html`, e.g.
  `csvy-gnuplot-latex v1.0.0`, perhaps as a link to the release notes
  (item 2) or to the GitHub release.
- Style it in `doc/site/site.css` as quieter than the site name (smaller,
  muted colour).
- Done when a `VERSION` change alone shows in the nav bar after
  `make site`: every page already depends on `../VERSION`.

## 2. `doc/RELEASE_notes.md`

Release notes for readers, kept in the repository and published on the site.
This is separate from `CHANGELOG.md`, which is the complete record for
maintainers.

- One section per release, newest first. Each has:
  - highlights and getting started (for the first release);
  - what's stable;
  - known limitations;
  - what changed, in a few lines, with a link to `CHANGELOG.md`.
- Start it with the v1.0.0 notes written for the GitHub release.
- The site: add `$(SITE)/RELEASE_notes.html` to `PAGES` in `doc/Makefile`
  (the existing `$(SITE)/%.html: %.md` rule builds it), a nav bar entry, and
  a link from `doc/README.md`.
- Link the nav bar's version number (item 1) to it.
- Release process: write the section before tagging, and paste it into the
  GitHub release form. Document this in `doc/REFERENCE.md` (Makefiles or a
  new *Releasing* section).
- Decide the file name: `RELEASE_notes.md`, as asked, or `RELEASE_NOTES.md`
  to match `CHANGELOG.md` and `REFERENCE.md`.

## 3. Use as a subfolder, or a git submodule, of a larger LaTeX project

Goal: a paper's repository contains this project, e.g. as
`figures/csvy-gnuplot-latex/`, preferably as a submodule. The paper's own
`.csvy` inputs and figures live *outside* the submodule, so updating the
submodule never touches them.

What already works:
- `NAME.gp.tex` is self-contained TikZ, with no paths inside it, so
  `\gnuplotfit{figures/NAME.gp.tex}` works from anywhere.
- `template:` is resolved relative to the `.csvy`, so an input can say
  `template: csvy-gnuplot-latex/templates/gantt`.
- `inp2gp.py` writes its outputs next to its input, and `NAME.d` lists
  paths relative to where make runs.

What needs work:
- **The Makefile only builds `*.csvy` in its own folder**, and `DOC`,
  `check`, `watch` and `overleaf` assume the paper is here too. Options:
  - a variable for the input folder, e.g.
    `make -C csvy-gnuplot-latex figs INPUTS=../figures`;
  - better, an includable `figures.mk` that the paper's Makefile uses:
    `include csvy-gnuplot-latex/figures.mk`, with `FIG_INPUTS := figures/*.csvy`,
    so the figure rules run in the paper's own make, with correct paths and
    dependencies. The current Makefile would then include it too.
- **Finding `gnuplotfit.sty`** from a paper in the parent folder. Options:
  - `\usepackage{csvy-gnuplot-latex/gnuplotfit}`: works, but LaTeX warns
    that the package name doesn't match;
  - `TEXINPUTS=./csvy-gnuplot-latex//:` in the paper's build (latexmk:
    `ensure_path('TEXINPUTS', …)` in `latexmkrc`);
  - `make overleaf`-style copying of `gnuplotfit.sty` next to the paper.
  Pick one and document it.
- **`.gitignore`:** the patterns are anchored to this repository's root
  (`/*.gp`), so they won't cover inputs in the parent. `figures.mk` users
  need matching rules in their own `.gitignore`, or `inp2gp` could write the
  intermediates into a `build/` folder instead of next to the input.
- **`make check`, `watch` and `overleaf`** each need to work on the paper's
  inputs, not this repository's example.
- **Submodule specifics:**
  - tell users to pin a release tag: `git submodule add …`, then
    `git -C csvy-gnuplot-latex checkout v1.0.0`;
  - updates are then an explicit `git submodule update --remote` plus a
    commit;
  - co-authors need `git clone --recurse-submodules`, or
    `git submodule update --init`.
- **Docs:** a tutorial or README section, *Using it as a submodule*, with a
  complete example: a paper's `Makefile`, `figures/NAME.csvy` and
  `\gnuplotfit{figures/NAME.gp.tex}`. Add a test that builds a figure from
  an input outside the repository.

This probably changes the Makefile's interface, so it's likely a 1.1.0
(additive) if the current targets keep working, or a 2.0.0 if they change.
