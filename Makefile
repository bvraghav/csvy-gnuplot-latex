# Every NAME.csvy here becomes NAME.gp.tex (tikz), for \gnuplotfit{NAME.gp.tex}:
#
#   NAME.csvy --inp2gp--> NAME.gp, NAME.dat, NAME.d --gnuplot--> NAME.gp.tex
#
# NAME.d (written by inp2gp) adds the template named in the frontmatter as a
# dependency, so editing the template redraws the figures that use it.
#
# NAME.gp.tex is committed (LaTeX users need no gnuplot/Python), so it is
# made repeatable: the date line gnuplot writes is removed.  'make check'
# fails when a committed figure no longer matches its sources.

INPS := $(wildcard *.csvy)
FIGS := $(INPS:.csvy=.gp.tex)
MIDS := $(INPS:.csvy=.gp) $(INPS:.csvy=.dat) $(INPS:.csvy=.d)
DOC  ?= test-v6.tex

PYTHON  ?= python3
GNUPLOT ?= gnuplot
LATEXMK ?= latexmk
ENTR    ?= entr

.PHONY: all figs pdf check clean distclean test docs watch
.DELETE_ON_ERROR:

all: pdf

figs: $(FIGS)

pdf: $(FIGS)
	$(LATEXMK) $(DOC)

%.gp %.dat %.d: %.csvy inp2gp.py
	$(PYTHON) inp2gp.py $<

# The line after "%% generated with GNUPLOT ..." is the date: drop it.
%.gp.tex: %.gp %.dat
	cd $(dir $<) && $(GNUPLOT) $(notdir $<)
	sed '/^%% generated with GNUPLOT/{n;/^%%/d;}' $@ > $@.tmp && mv $@.tmp $@

-include $(INPS:.csvy=.d)

# Rebuild every figure from scratch in a temporary copy and compare.
check:
	@tmp=$$(mktemp -d) || exit 1; \
	trap 'rm -rf "$$tmp"' EXIT; \
	cp -R . "$$tmp" || exit 1; \
	(cd "$$tmp" && rm -f $(MIDS) $(FIGS)); \
	$(MAKE) -s -C "$$tmp" figs > /dev/null || { echo "check: build failed"; exit 1; }; \
	status=0; \
	for f in $(FIGS); do \
	  if [ ! -f "$$f" ]; then echo "check: $$f is missing; run 'make figs'"; status=1; \
	  elif ! cmp -s "$$tmp/$$f" "$$f"; then echo "check: $$f is out of date; run 'make figs'"; status=1; \
	  else echo "check: $$f ok"; fi; \
	done; \
	exit $$status

# clean keeps the committed figures; distclean removes them too.
clean:
	rm -f $(MIDS)
	$(LATEXMK) -c $(DOC)

distclean: clean
	rm -f $(FIGS)

test:
	$(MAKE) -C test

# Tutorial images: doc/img/*.png from doc/examples/.
docs:
	$(MAKE) -C doc

# Rebuild on every save (needs entr).  entr -d exits with status 2 when a
# file is added to a watched folder: list the files again and carry on.
WATCH_TARGET ?= all
watch:
	@command -v $(firstword $(ENTR)) > /dev/null || { echo "watch: needs entr"; exit 1; }
	@while :; do \
	  ls *.csvy templates/*.gp inp2gp.py gnuplotfit.sty $(DOC) 2> /dev/null \
	    | $(ENTR) -d $(MAKE) --no-print-directory $(WATCH_TARGET); \
	  [ $$? -eq 2 ] || break; \
	done
