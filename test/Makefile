# Regression tests.  Each test runs in a temporary copy of the sources.
#
#   make          run all tests
#   make golden   refresh golden/ after an intended change (then review the diff)

PYTHON ?= python3
export PYTHONDONTWRITEBYTECODE = 1

.PHONY: test golden

test:
	$(PYTHON) -m unittest -v test_inp2gp

golden:
	UPDATE_GOLDEN=1 $(PYTHON) -m unittest test_inp2gp.Generator.test_project_golden test_inp2gp.Gnuplot.test_project_figure_golden
