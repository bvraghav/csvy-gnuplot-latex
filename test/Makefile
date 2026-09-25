# Regression tests for v6.  Each test runs in a temporary copy of the sources.
#
#   make          run all tests
#   make golden   refresh golden/ after an intended change (then review the diff)

PYTHON ?= python3
export PYTHONDONTWRITEBYTECODE = 1

.PHONY: test golden

test:
	$(PYTHON) -m unittest -v test_v6

golden:
	UPDATE_GOLDEN=1 $(PYTHON) -m unittest test_v6.Generator.test_project_golden test_v6.Gnuplot.test_project_figure_golden
