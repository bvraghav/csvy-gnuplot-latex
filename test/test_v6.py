"""Regression tests for v6: inp2gp.py, templates/gantt.gp, Makefile, gnuplotfit.sty.

Every test works in a fresh temporary copy of the v6 sources, so nothing is
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
V6 = HERE.parent
CASES = HERE / "cases"
GOLDEN = HERE / "golden"
SOURCES = ["inp2gp.py", "templates", "Makefile", "gnuplotfit.sty", "project.csvy", "test-v6.tex"]
UPDATE_GOLDEN = os.environ.get("UPDATE_GOLDEN") == "1"

HAVE_GNUPLOT = shutil.which("gnuplot") is not None
HAVE_MAKE = shutil.which("make") is not None
HAVE_LATEXMK = shutil.which("latexmk") is not None

HEADER = "---\ntemplate: templates/gantt.gp\n---\n"


def strip_meta(text):
    """Drop tikz '%%' comment lines (date, gnuplot version)."""
    return "".join(l for l in text.splitlines(keepends=True) if not l.startswith("%%"))


class Sandbox(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="v6test-")
        self.dir = Path(self._tmp.name)
        for name in SOURCES:
            src = V6 / name
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
        self.write("v.csvy",
                   "---\n"
                   "template: templates/gantt.gp\n"
                   "fig: {w: 8, h: 4.5}\n"
                   "flag: true\n"
                   "unset_flag: false\n"
                   "s: 'it''s \\LaTeX'\n"
                   "day: 2026-09-25\n"
                   "xs: [1, 2.5, x]\n"
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
        self.assertEqual(gp[-1], "load 'templates/gantt.gp'")

    def test_data_rewrite(self):
        self.write("d.csvy", HEADER + 'A,B\n\n1,"x, y"\n2,\\textbf{z} \\& w\n\n')
        r = self.inp2gp("d.csvy")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.read("d.dat"),
                         "A\tB\n1\tx, y\n2\t\\\\textbf{z} \\\\& w\n")
        self.assertIn("N_rows = 2", self.read("d.gp"))

    def test_template_relative_to_input(self):
        (self.dir / "sub").mkdir()
        self.write("sub/r.csvy", "---\ntemplate: ../templates/gantt.gp\n---\nA\n1\n")
        r = self.inp2gp("sub/r.csvy")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.read("sub/r.gp").splitlines()[-1], "load '../templates/gantt.gp'")
        self.assertEqual(self.read("sub/r.d").splitlines()[0],
                         "sub/r.gp.tex: sub/r.gp sub/r.dat templates/gantt.gp")

    ERRORS = [
        ("no frontmatter", "Index,Label\n1,a\n", "e.csvy:1: expected '---'"),
        ("unclosed frontmatter", "---\ntemplate: x\n", "no closing '---'"),
        ("bad yaml", "---\na: [1\n---\nA\n1\n", "YAML frontmatter"),
        ("not a mapping", "---\n- 1\n---\nA\n1\n", "must be a mapping"),
        ("no template", "---\nx: 1\n---\nA\n1\n", "needs 'template:"),
        ("missing template", "---\ntemplate: nope.gp\n---\nA\n1\n", "template 'nope.gp' not found"),
        ("bad key", HEADER.replace("---\n", "---\nmy-key: 1\n", 1) + "A\n1\n",
         "e.csvy: key 'my-key' is not a valid gnuplot variable name"),
        ("reserved key", HEADER.replace("---\n", "---\nout_file: x\n", 1) + "A\n1\n",
         "key 'out_file' is reserved"),
        ("null value", HEADER.replace("---\n", "---\nx_label:\n", 1) + "A\n1\n",
         "key 'x_label': empty value"),
        ("multi-line string", HEADER.replace("---\n", "---\ns: \"a\\nb\"\n", 1) + "A\n1\n",
         "strings cannot span lines"),
        ("nested list", HEADER.replace("---\n", "---\nxs: [[1]]\n", 1) + "A\n1\n",
         "unsupported value"),
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
        self.assertIn("Usage:", r.stderr)


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
        for src in ("templates/gantt.gp", "project.csvy", "inp2gp.py"):
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
        self.write("project.csvy", csvy.replace("x_label: Time (months)", "x_label: Time (weeks)"))
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
