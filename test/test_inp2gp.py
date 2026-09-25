"""Regression tests: inp2gp.py, templates/gantt, Makefile, gnuplotfit.sty.

Every test works in a fresh temporary copy of the sources, so nothing is
written next to them.  Tests that need gnuplot, make or latexmk are skipped
when the tool is missing.

    make -C test          run all tests
    make -C test golden   refresh test/golden/ after an intended change
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CASES = HERE / "cases"
GOLDEN = HERE / "golden"
SOURCES = ["inp2gp.py", "templates", "Makefile", "gnuplotfit.sty", "project.csvy", "example.tex"]
UPDATE_GOLDEN = os.environ.get("UPDATE_GOLDEN") == "1"

HAVE_GNUPLOT = shutil.which("gnuplot") is not None
HAVE_MAKE = shutil.which("make") is not None
HAVE_LATEXMK = shutil.which("latexmk") is not None

HEADER = "---\ntemplate: templates/gantt\n---\n"


def strip_meta(text):
    """Drop tikz '%%' comment lines (date, gnuplot version)."""
    return "".join(l for l in text.splitlines(keepends=True) if not l.startswith("%%"))


class Sandbox(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="inp2gp-test-")
        self.dir = Path(self._tmp.name)
        for name in SOURCES:
            src = ROOT / name
            if src.is_dir():
                shutil.copytree(src, self.dir / name)
            else:
                shutil.copy2(src, self.dir / name)

    def tearDown(self):
        self._tmp.cleanup()

    def run_in(self, *args):
        return subprocess.run(args, cwd=self.dir, capture_output=True, text=True)

    def ok(self, *args):
        r = self.run_in(*args)
        self.assertEqual(r.returncode, 0, f"{' '.join(args)} failed:\n{r.stdout}\n{r.stderr}")
        return r

    def write(self, name, text):
        (self.dir / name).write_text(text)

    def read(self, name):
        return (self.dir / name).read_text()

    def inp2gp(self, name):
        return self.run_in(sys.executable, "inp2gp.py", name)

    def template(self, stem, defaults, gp="# test template\n"):
        """Write templates/<stem>.gp and templates/<stem>.csvy (header only)."""
        self.write(f"templates/{stem}.gp", gp)
        self.write(f"templates/{stem}.csvy", "---\n" + defaults + "---\n")

    def build_figure(self, name):
        self.ok(sys.executable, "inp2gp.py", f"{name}.csvy")
        self.ok("gnuplot", f"{name}.gp")
        return self.read(f"{name}.gp.tex")

    def check_golden(self, name, text):
        path = GOLDEN / name
        if UPDATE_GOLDEN:
            path.write_text(text)
            return
        self.assertTrue(path.exists(), f"missing {path}; run 'make -C test golden'")
        self.assertEqual(text, path.read_text(), f"differs from {path}")


# ------------------------------------------------------------------------------
class Generator(Sandbox):
    """inp2gp.py on its own (no gnuplot needed)."""

    def test_project_golden(self):
        r = self.inp2gp("project.csvy")
        self.assertEqual(r.returncode, 0, r.stderr)
        for ext in ("gp", "dat", "d"):
            with self.subTest(ext):
                self.check_golden(f"project.{ext}", self.read(f"project.{ext}"))

    def test_value_mapping(self):
        self.template("t", "vars:\n"
                           "  fig: {w: 1, h: 1}\n"
                           "  flag: false\n"
                           "  unset_flag: true\n"
                           "  s: x\n"
                           "  day: 2000-01-01\n"
                           "  xs: [0]\n")
        self.write("v.csvy",
                   "---\n"
                   "template: templates/t\n"
                   "vars:\n"
                   "  fig: {w: 8, h: 4.5}\n"
                   "  flag: true\n"
                   "  unset_flag: false\n"
                   "  s: 'it''s \\LaTeX'\n"
                   "  day: 2026-09-25\n"
                   "  xs: [1, 2.5, x]\n"
                   "---\n"
                   "A\n1\n")
        r = self.inp2gp("v.csvy")
        self.assertEqual(r.returncode, 0, r.stderr)
        gp = self.read("v.gp").splitlines()
        for line in ["data_file = 'v.dat'",
                     "out_file = 'v.gp.tex'",
                     "N_rows = 1",
                     "fig_w = 8",
                     "fig_h = 4.5",
                     "flag = 1",
                     "unset_flag = 0",
                     "s = 'it''s \\LaTeX'",
                     "day = '2026-09-25'",
                     "array xs[3] = [1, 2.5, 'x']"]:
            self.assertIn(line, gp)
        self.assertEqual(gp[-1], "load 'templates/t.gp'")

    def test_vars_merge_over_defaults(self):
        self.template("t", "vars:\n  a: 1\n  b: {c: 2, d: 3}\n",
                      gp='if (!exists("opt")) opt = 0\n')
        self.write("m.csvy", "---\ntemplate: templates/t\n"
                             "vars: {b: {d: 30}, opt: 5}\n---\nA\n1\n")
        r = self.inp2gp("m.csvy")
        self.assertEqual(r.returncode, 0, r.stderr)
        gp = self.read("m.gp")
        # defaults first, user values over them; 'opt' is allowed by exists()
        self.assertIn("a = 1\nb_c = 2\nb_d = 30\nopt = 5\n", gp)

    def test_gnuplot_values(self):
        self.template("t", "")
        self.write("g.csvy",
                   "---\ntemplate: templates/t\n"
                   "gnuplot:\n"
                   "  xlabel: \"'Time'\"\n"
                   "  border: 3\n"
                   "  xtics: 0.5\n"
                   "  grid: true\n"
                   "  mytics:\n"
                   "  key: false\n"
                   "  \"arrow  1\": from 1,0 to 1,1 nohead\n"
                   "  ylabel: >-\n"
                   "    'Rate (\\textit{per} $t$)'\n"
                   "---\nA\n1\n")
        r = self.inp2gp("g.csvy")
        self.assertEqual(r.returncode, 0, r.stderr)
        gp = self.read("g.gp")
        self.assertIn("set xlabel 'Time'\n"
                      "set border 3\n"
                      "set xtics 0.5\n"
                      "set grid\n"
                      "set mytics\n"
                      "unset key\n"
                      "set arrow 1 from 1,0 to 1,1 nohead\n"
                      "set ylabel 'Rate (\\textit{per} $t$)'\n"
                      "load 'templates/t.gp'\n", gp)

    def test_gnuplot_merge(self):
        self.template("t", "gnuplot:\n"
                           "  - xlabel: \"'A'\"\n"
                           "  - label: \"1 'x' at 0,0\"\n"
                           "  - label: \"2 'y' at 1,1\"\n"
                           "  - border: 3\n")
        self.write("g.csvy",
                   "---\ntemplate: templates/t\n"
                   "gnuplot:\n"
                   "  - label: \"3 'z' at 2,2\"\n"
                   "  - key: false\n"
                   "---\nA\n1\n")
        r = self.inp2gp("g.csvy")
        self.assertEqual(r.returncode, 0, r.stderr)
        # the user's 'label' entries replace both defaults, in their place;
        # new keys go at the end
        self.assertIn("set xlabel 'A'\n"
                      "set label 3 'z' at 2,2\n"
                      "set border 3\n"
                      "unset key\n"
                      "load", self.read("g.gp"))

    def test_header_list_form(self):
        body = "---\n" + "{}" + "---\nA\n1\n"
        self.write("a.csvy", body.format("template: templates/gantt\n"
                                         "vars: {bar_height: 0.5}\n"
                                         "gnuplot: {border: 15}\n"))
        self.write("b.csvy", body.format("- template: templates/gantt\n"
                                         "- vars: {bar_height: 0.5}\n"
                                         "- gnuplot: {border: 15}\n"))
        for name in ("a", "b"):
            r = self.inp2gp(f"{name}.csvy")
            self.assertEqual(r.returncode, 0, r.stderr)
        # same output apart from comments and the file names derived from NAME
        strip = lambda t, n: [l.replace(f"'{n}.", "'X.") for l in t.splitlines()
                              if not l.startswith("#")]
        self.assertEqual(strip(self.read("a.gp"), "a"), strip(self.read("b.gp"), "b"))

    def test_template_choice(self):
        self.template("t", "")
        self.write("c.csvy", HEADER + "A\n1\n")
        # the command line wins over the header; '.gp' is optional
        for arg in ("--template=templates/t", "--template=templates/t.gp"):
            r = self.run_in(sys.executable, "inp2gp.py", arg, "c.csvy")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(self.read("c.gp").splitlines()[-1], "load 'templates/t.gp'")
        self.write("n.csvy", "---\n---\nA\n1\n")
        r = self.run_in(sys.executable, "inp2gp.py", "--template", "templates/t", "n.csvy")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.write("p.csvy", "---\ntemplate: templates/gantt.gp\n---\nA\n1\n")
        r = self.inp2gp("p.csvy")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.read("p.gp").splitlines()[-1], "load 'templates/gantt.gp'")

    def test_template_errors(self):
        self.write("templates/nodefaults.gp", "# no .csvy next to me\n")
        self.template("withdata", "")
        with open(self.dir / "templates/withdata.csvy", "a") as f:
            f.write("A\n1\n")
        self.template("hastemplate", "template: x\n")
        for stem, message in [("nope", "template 'templates/nope': templates/nope.gp not found"),
                              ("nodefaults", "templates/nodefaults.csvy not found"),
                              ("withdata", "has a header only, no data"),
                              ("hastemplate", "unknown frontmatter key 'template'")]:
            with self.subTest(stem):
                self.write("e.csvy", f"---\ntemplate: templates/{stem}\n---\nA\n1\n")
                r = self.inp2gp("e.csvy")
                self.assertNotEqual(r.returncode, 0)
                self.assertIn(message, r.stderr)
                self.assertFalse((self.dir / "e.gp").exists())

    def test_data_rewrite(self):
        self.write("d.csvy", HEADER + 'A,B\n\n1,"x, y"\n2,\\textbf{z} \\& w\n\n')
        r = self.inp2gp("d.csvy")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.read("d.dat"),
                         "A\tB\n1\tx, y\n2\t\\\\textbf{z} \\\\& w\n")
        self.assertIn("N_rows = 2", self.read("d.gp"))

    def test_template_relative_to_input(self):
        (self.dir / "sub").mkdir()
        self.write("sub/r.csvy", "---\ntemplate: ../templates/gantt\n---\nA\n1\n")
        r = self.inp2gp("sub/r.csvy")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.read("sub/r.gp").splitlines()[-1], "load '../templates/gantt.gp'")
        self.assertEqual(self.read("sub/r.d").splitlines(),
                         ["sub/r.gp.tex: sub/r.gp sub/r.dat templates/gantt.gp",
                          "sub/r.gp sub/r.dat sub/r.d: templates/gantt.csvy",
                          "templates/gantt.gp: ;",
                          "templates/gantt.csvy: ;"])

    @staticmethod
    def H(body):
        """HEADER with extra frontmatter lines, and one data row."""
        return "---\ntemplate: templates/gantt\n" + body + "---\nA\n1\n"

    ERRORS = [
        ("no frontmatter", "Index,Label\n1,a\n", "e.csvy:1: expected '---'"),
        ("unclosed frontmatter", "---\ntemplate: x\n", "no closing '---'"),
        ("bad yaml", "---\na: [1\n---\nA\n1\n", "YAML frontmatter"),
        ("not a mapping", "---\n42\n---\nA\n1\n", "expected a mapping or a list of one-key mappings"),
        ("list item not one key", "---\n- template: a\n  vars: {}\n---\nA\n1\n", "one-key mappings"),
        ("key given twice", "---\n- template: a\n- template: b\n---\nA\n1\n", "key 'template' given twice"),
        ("unknown frontmatter key", "---\ntemplate: templates/gantt\nx_label: T\n---\nA\n1\n",
         "unknown frontmatter key 'x_label'"),
        ("no template", "---\nvars: {}\n---\nA\n1\n", "needs 'template:"),
        ("vars not a mapping", "---\ntemplate: templates/gantt\nvars: [1]\n---\nA\n1\n",
         "'vars' must be a mapping"),
        ("bad var name", "---\ntemplate: templates/gantt\nvars: {my-key: 1}\n---\nA\n1\n",
         "e.csvy: var 'my-key' is not a valid gnuplot variable name"),
        ("reserved var", "---\ntemplate: templates/gantt\nvars: {out_file: x}\n---\nA\n1\n",
         "var 'out_file' is reserved"),
        ("unknown var", "---\ntemplate: templates/gantt\nvars: {bar_hieght: 1}\n---\nA\n1\n",
         "unknown var(s) bar_hieght"),
        ("null var", "---\ntemplate: templates/gantt\nvars: {bar_height: }\n---\nA\n1\n",
         "var 'bar_height': empty value"),
        ("multi-line var", "---\ntemplate: templates/gantt\nvars: {bar_height: \"a\\nb\"}\n---\nA\n1\n",
         "strings cannot span lines"),
        ("nested list var", "---\ntemplate: templates/gantt\nvars: {bar_height: [[1]]}\n---\nA\n1\n",
         "unsupported value"),
        ("reserved: terminal", "---\ntemplate: templates/gantt\ngnuplot: {terminal: png}\n---\nA\n1\n",
         "gnuplot 'terminal' is reserved"),
        ("reserved: term", "---\ntemplate: templates/gantt\ngnuplot: {term: png}\n---\nA\n1\n",
         "gnuplot 'term' is reserved"),
        ("reserved: out", "---\ntemplate: templates/gantt\ngnuplot: {out: x.tex}\n---\nA\n1\n",
         "gnuplot 'out' is reserved"),
        ("reserved: datafile", "---\ntemplate: templates/gantt\ngnuplot: {datafile separator: comma}\n---\nA\n1\n",
         "gnuplot 'datafile separator' is reserved"),
        ("reserved: table", "---\ntemplate: templates/gantt\ngnuplot: {table: x}\n---\nA\n1\n",
         "gnuplot 'table' is reserved"),
        ("multi-line set", "---\ntemplate: templates/gantt\ngnuplot: {xlabel: \"a\\nb\"}\n---\nA\n1\n",
         "must be one line"),
        ("unsupported set", "---\ntemplate: templates/gantt\ngnuplot: {xlabel: [1]}\n---\nA\n1\n",
         "gnuplot 'xlabel': unsupported value"),
        ("no header", HEADER, "no CSV header row"),
        ("no rows", HEADER + "A,B\n", "no data rows"),
        ("empty column name", HEADER + "A,,C\n1,2,3\n", "e.csvy:4: empty column name"),
        ("duplicate column", HEADER + "A,A\n1,2\n", "e.csvy:4: duplicate column name(s): A"),
        ("field count", HEADER + "A,B\n1,a\n2\n", "e.csvy:6: 1 fields, but the header has 2"),
        ("double quote", HEADER + 'A,B\n1,"say ""hi"""\n', "e.csvy:5: a double quote"),
        ("tab", HEADER + "A,B\n1,a\tb\n", "e.csvy:5: a tab"),
        ("newline", HEADER + 'A,B\n1,"a\nb"\n', "a newline"),
        ("unterminated quote", HEADER + 'A,B\n1,"open\n', "unexpected end of data"),
    ]

    def test_errors(self):
        for name, text, message in self.ERRORS:
            with self.subTest(name):
                self.write("e.csvy", text)
                r = self.inp2gp("e.csvy")
                self.assertNotEqual(r.returncode, 0)
                self.assertIn(message, r.stderr)
                for ext in ("gp", "dat", "d"):
                    self.assertFalse((self.dir / f"e.{ext}").exists(),
                                     f"e.{ext} written despite the error")

    def test_usage(self):
        r = self.run_in(sys.executable, "inp2gp.py", "project.txt")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("usage:", r.stderr)
        self.assertIn("must be a .csvy file", r.stderr)


# ------------------------------------------------------------------------------
@unittest.skipUnless(HAVE_GNUPLOT, "gnuplot not found")
class Gnuplot(Sandbox):
    """gnuplot's reader and the gantt template."""

    def test_strcol_returns_text_verbatim(self):
        # The .dat contract: tabs + doubled backslashes => strcol() gives the input back.
        labels = ["A, B \\& C", "\\textbf{x} \\\\ \\n", "it's # not a comment", "#hash first"]
        quote = lambda s: '"' + s + '"' if "," in s else s
        rows = "".join(f"{i},{quote(l)}\n" for i, l in enumerate(labels, 1))
        self.write("s.csvy", HEADER + "Index,Label\n" + rows)
        self.ok(sys.executable, "inp2gp.py", "s.csvy")
        self.write("s-read.gp",
                   "set datafile separator tab\n"
                   "set datafile commentschars ''\n"
                   "set datafile columnheaders\n"
                   "set print 's-out.txt'\n"
                   "do for [i=1:N] { stats 's.dat' every ::i-1::i-1 using (s = strcol('Label'), 0) nooutput; print s }\n")
        self.ok("gnuplot", "-e", f"N={len(labels)}", "s-read.gp")
        self.assertEqual(self.read("s-out.txt").splitlines(), labels)

    def test_project_figure_golden(self):
        self.check_golden("project.gp.tex", strip_meta(self.build_figure("project")))

    def test_tricky_labels(self):
        shutil.copy2(CASES / "tricky.csvy", self.dir)
        tex = self.build_figure("tricky")
        for node in [r"{A, B \& C}",
                     r"{\textbf{EEM}}",
                     r"{it's}",
                     r"{Time (\textit{months}, it's $t$)}",
                     r"{$6$}"]:  # t_end left out: last buffer end 5 -> grid 2 -> 6
            self.assertIn(node, tex)
        self.assertNotIn("$8$", tex)

    def test_gnuplot_entries_and_precedence(self):
        # gnuplot: entries reach the figure; a var the template uses wins over
        # a gnuplot: entry for the same setting (xrange comes from t_* vars).
        csvy = self.read("project.csvy").replace(
            "  mxtics: 2\n", "  mxtics: 2\n  border: 15\n  xrange: \"[0:5]\"\n")
        self.write("p2.csvy", csvy)
        tex = self.build_figure("p2")
        base = self.build_figure("project")
        self.assertNotEqual(strip_meta(tex), strip_meta(base))
        self.assertIn("{$24$}", tex)       # t_end = 24 won over xrange [0:5]
        # border 15 (all four sides) is drawn as a closed path; the default 3 is not
        closed = re.compile(r"^\\draw\[gp path\].*--cycle;$", re.M)
        self.assertTrue(closed.search(tex))
        self.assertFalse(closed.search(base))

    def test_template_needs_generated_inputs(self):
        r = self.run_in("gnuplot", "templates/gantt.gp")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("data_file and out_file must be set", r.stderr)


# ------------------------------------------------------------------------------
@unittest.skipUnless(HAVE_GNUPLOT and HAVE_MAKE, "gnuplot or make not found")
class Make(Sandbox):
    """Makefile rules and the NAME.d dependencies."""

    def up_to_date(self):
        return self.run_in("make", "-q", "figs").returncode == 0

    def bump(self, name):
        """Make <name> newer than everything else, as if just edited.

        Everything is moved into the past rather than <name> into the future,
        so a rebuild really leaves the outputs newest."""
        past = time.time() - 600
        for p in self.dir.rglob("*"):
            os.utime(p, (past, past))
        os.utime(self.dir / name, (past + 60, past + 60))

    def test_dependencies(self):
        self.ok("make", "figs")
        self.assertTrue((self.dir / "project.gp.tex").exists())
        self.assertTrue(self.up_to_date(), "fresh build is not up to date")
        for src in ("templates/gantt.gp", "templates/gantt.csvy", "project.csvy", "inp2gp.py"):
            with self.subTest(src):
                self.bump(src)
                self.assertFalse(self.up_to_date(), f"editing {src} does not trigger a rebuild")
                self.ok("make", "figs")
                self.assertTrue(self.up_to_date())

    def test_figure_is_repeatable(self):
        # Committed figures must not change on a rebuild: no date line.
        self.ok("make", "figs")
        first = self.read("project.gp.tex")
        self.assertIsNone(re.search(r"^%% \w{3} \w{3} +\d+ \d\d:\d\d:\d\d", first, re.M),
                          "date line left in the figure")
        self.assertIn("%% generated with GNUPLOT", first)
        time.sleep(1.1)  # a date line would now differ
        (self.dir / "project.gp.tex").unlink()
        self.ok("make", "figs")
        self.assertEqual(self.read("project.gp.tex"), first)

    def test_check(self):
        self.ok("make", "figs")
        r = self.ok("make", "-s", "check")
        self.assertIn("check: project.gp.tex ok", r.stdout)

        csvy = self.read("project.csvy")
        edited = csvy.replace("'Time (months)'", "'Time (weeks)'")
        self.assertNotEqual(edited, csvy)
        self.write("project.csvy", edited)
        r = self.run_in("make", "-s", "check")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("project.gp.tex is out of date", r.stdout)

        self.write("project.csvy", csvy)
        (self.dir / "project.gp.tex").unlink()
        r = self.run_in("make", "-s", "check")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("project.gp.tex is missing", r.stdout)

    def test_clean_keeps_figures(self):
        self.ok("make", "figs")
        self.ok("make", "clean")
        self.assertTrue((self.dir / "project.gp.tex").exists(), "clean removed a committed figure")
        for ext in ("gp", "dat", "d"):
            self.assertFalse((self.dir / f"project.{ext}").exists())
        self.ok("make", "distclean")
        self.assertFalse((self.dir / "project.gp.tex").exists())

    def test_template_files_are_never_rebuilt(self):
        # STEM.gp / STEM.csvy look like a make target and its source: make must not
        # try to build the template from its defaults file.
        gp = self.read("templates/gantt.gp")
        self.ok("make", "figs")
        self.bump("templates/gantt.csvy")
        self.ok("make", "figs")
        self.assertEqual(self.read("templates/gantt.gp"), gp)

    def test_failed_figure_leaves_nothing(self):
        self.write("bad.csvy", HEADER + 'A,B\n1,"say ""hi"""\n')
        r = self.run_in("make", "figs")
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((self.dir / "bad.gp.tex").exists())


# ------------------------------------------------------------------------------
@unittest.skipUnless(HAVE_GNUPLOT and HAVE_LATEXMK, "gnuplot or latexmk not found")
class LaTeX(Sandbox):
    """gnuplotfit.sty stretches figures to exactly the requested size."""

    TOLERANCE_PT = 0.01

    def test_fit_sizes(self):
        self.build_figure("project")
        shutil.copy2(CASES / "fit.tex", self.dir)
        self.ok("latexmk", "-interaction=nonstopmode", "-halt-on-error", "fit.tex")
        found = re.findall(r"^FIT (\S+) ([\d.]+)pt ([\d.]+)pt ([\d.]+)pt ([\d.]+)pt",
                           self.read("fit.log"), re.M)
        self.assertEqual([f[0] for f in found], ["natural", "column", "wide", "fixed"])
        for case, gw, gh, ww, wh in found:
            with self.subTest(case):
                self.assertAlmostEqual(float(gw), float(ww), delta=self.TOLERANCE_PT)
                self.assertAlmostEqual(float(gh), float(wh), delta=self.TOLERANCE_PT)


if __name__ == "__main__":
    unittest.main()
