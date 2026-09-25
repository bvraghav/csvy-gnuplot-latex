# Tutorial images: img/*.png, rendered from examples/.
#
#   examples/NAME.csvy     -> build/NAME.gp.tex   (the same pipeline as the top folder)
#   examples/NAME.img.tex  -> img/NAME.png        (a LaTeX page laying out figures)
#   examples/NAME.csvy     -> img/NAME.png        (no NAME.img.tex: the figure at natural size)
#
# The examples say 'template: templates/gantt.gp', exactly as in the top folder;
# build/templates links to the real templates.
#
#   make          render every image in IMGS
#   make clean    remove build/ (img/ is committed)

ROOT    := $(abspath ..)
PYTHON  ?= python3
GNUPLOT ?= gnuplot
LATEXMK ?= latexmk
RES     ?= 150

IMGS := 101-natural 101-compare 101-onecolumn 101-twocolumn \
        sample-minimal sample-base sample-shift sample-add sample-reorder sample-autofit \
        adv-bar-height adv-margin-l adv-margin-b adv-fig-size adv-grid adv-labels adv-ylabel

CSVYS := $(notdir $(wildcard examples/*.csvy))
FIGS  := $(addprefix build/,$(CSVYS:.csvy=.gp.tex))

export TEXINPUTS := $(ROOT):$(abspath examples):

.PHONY: all clean
.DELETE_ON_ERROR:
.SECONDARY:

all: $(addprefix img/,$(addsuffix .png,$(IMGS)))

build/templates:
	mkdir -p build && ln -sfn ../../templates $@

build/%.csvy: examples/%.csvy | build/templates
	cp $< $@

build/%.gp.tex: build/%.csvy $(ROOT)/inp2gp.py $(ROOT)/templates/gantt.gp $(ROOT)/templates/gantt.csvy
	cd build && $(PYTHON) $(ROOT)/inp2gp.py $*.csvy && $(GNUPLOT) $*.gp

# An explicit wrapper wins; otherwise show the figure at its natural size.
build/%.img.tex: examples/%.img.tex
	mkdir -p build && cp $< $@

build/%.img.tex: build/%.gp.tex
	printf '%s\n' '\documentclass[border=0pt]{standalone}' '\usepackage{gnuplotfit}' \
	  '\begin{document}' '\input{$*.gp.tex}\unskip' '\end{document}' > $@

# Every page depends on every figure (simpler than tracking which it uses).
# latexmk skips a page whose own inputs did not change, so touch the PDF to
# tell make it is current.
build/%.img.pdf: build/%.img.tex $(FIGS) examples/docimg.sty $(ROOT)/gnuplotfit.sty
	cd build && $(LATEXMK) -interaction=nonstopmode -halt-on-error $*.img.tex \
	  > $*.img.latexmk.out 2>&1 || { grep -A5 '^!' $*.img.log; exit 1; }
	touch $@

img/%.png: build/%.img.pdf
	mkdir -p img && pdftoppm -png -r $(RES) -singlefile -f 1 -l 1 $< img/$*

# Whole pages: lower resolution.
img/101-onecolumn.png: RES = 80
img/101-twocolumn.png: RES = 110

# \includegraphics uses the natural-size figure as a PDF.
build/101-compare.img.pdf: build/101-natural.img.pdf
build/101-twocolumn.img.pdf: build/101-twocolumn-doc.img.pdf

clean:
	rm -rf build
