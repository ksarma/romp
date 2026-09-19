#!/usr/bin/env python3
"""The dangerous mark of tests/romp-service-differential.py, pinned in the suite: compare() over MARK_CASES, a table of synthetic
(systemd, oracle) pairs with one pair on each side of every shape the column marks, the fatal shapes, the not-modelled row and the
loud skip. Round 6 of fork PR #778 (tests-2): none of the recipe's real fixtures reaches the mark at an agreeing head (dangerous is
entailed by DISAGREE, and the head has none), so an edit that killed the mark printed the same table with the tag alone missing,
and nothing in the suite called compare() at all; the recipe's own self-check runs only when the recipe is run. This module
loads the recipe by path (it is import-side-effect free and needs no systemd) and asserts each pair, so a compare() edit is caught
in CI. Synthetic only: every path is under /nx, every value invented."""
import importlib.util
import io
import os
import tempfile
import unittest

os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()   # the suite's floor for a module that loads repo code: nothing here reads state
os.environ.pop("ROMP_STATE_DIR", None)

HERE = os.path.dirname(os.path.abspath(__file__))
RECIPE = os.path.join(HERE, "romp-service-differential.py")


def load_recipe():
    spec = importlib.util.spec_from_file_location("romp_service_differential", RECIPE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class MarkSelfCheck(unittest.TestCase):
    def setUp(self):
        self.m = load_recipe()

    def test_every_pair_of_the_table_scores_as_the_table_says(self):
        m = self.m
        for name, sd, orc, verdict, dangerous in m.MARK_CASES:
            with self.subTest(name):
                got = m.compare("X", sd, orc)
                self.assertEqual(got[0], verdict, (name, got))
                self.assertEqual(got[2], dangerous, (name, got))

    def test_the_table_has_both_sides_of_every_shape(self):
        # a table with a side missing pins half a boundary: each family below has a marked pair and an unmarked pair
        names = [c[0] for c in self.m.MARK_CASES]
        marked = {c[0] for c in self.m.MARK_CASES if c[4]}
        for family in ("env", "argv", "exec->path", "EnvironmentFile"):
            fam = [n for n in names if n.startswith(family)]
            self.assertTrue(any(n in marked for n in fam), family)
            self.assertTrue(any(n not in marked for n in fam), family)
        self.assertIn("systemd refuses, the oracle loads", marked)
        self.assertNotIn("the oracle refuses, systemd loads (a false refusal)", marked)

    def test_self_check_passes_and_prints_its_line(self):
        out = io.StringIO()
        self.assertEqual(self.m.self_check(out), 0)
        self.assertIn("mark self-check: %d of %d" % (len(self.m.MARK_CASES), len(self.m.MARK_CASES)), out.getvalue())

    def test_a_dead_mark_fails_the_self_check(self):
        # the discriminating half: compare() with every mark off must fail the check, which is what the recipe's real fixtures could not show
        m = self.m
        live = m.compare
        def dead(kind, sd, orc):
            v, d, _ = live(kind, sd, orc)
            return v, d, False
        m.compare = dead
        try:
            out = io.StringIO()
            self.assertEqual(m.self_check(out), 1)
            self.assertIn("mark self-check FAILED", out.getvalue())
        finally:
            m.compare = live

    def test_the_loud_skip_is_never_agree(self):
        # extra6-1: systemd prints no exec->path for a first command under the - prefix; the row says so instead of agreeing
        m = self.m
        sd = m._sd(path=None)
        orc = m._orc(execs=[m._ex("/nx/bin/x", "/nx/bin/x", ignore=True)])
        v, detail, dangerous = m.compare("X", sd, orc)
        self.assertEqual(v, "REFUSES")
        self.assertIn("exec->path uncompared", detail)
        self.assertIn("- prefix", detail)
        self.assertFalse(dangerous)

    def test_the_first_command_shift_is_marked_and_the_kept_first_is_not(self):
        # extra6-2: a shorter oracle list is unmarked only while it keeps systemd's first command
        m = self.m
        sd = m._sd(cmds=[["/nx/bin/a"], ["/nx/bin/b"]], path="/nx/bin/a")
        self.assertTrue(m.compare("X", sd, m._orc(execs=[m._ex("/nx/bin/b")]))[2])
        self.assertFalse(m.compare("X", sd, m._orc(execs=[m._ex("/nx/bin/a")]))[2])


if __name__ == "__main__":
    unittest.main()
