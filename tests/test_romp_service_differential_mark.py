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
        n = len(self.m.mark_clauses())
        self.assertIn("; %d of %d mark clauses of compare() each told apart by a row" % (n, n), out.getvalue())

    # round 7 of fork PR #778 (extra6-1): the clause population is read from compare()'s source, and the table must tell every clause's
    # mutant apart; at round 6 three of eight clauses could be deleted with the check still reading 25 of 25
    CLAUSES = [
        "sd['fatal']",
        "b is not None",
        "len(orc_cmds) >= len(sd_cmds)",
        "any((c not in sd_cmds for c in orc_cmds))",
        "orc_cmds and orc_cmds[0] != sd_cmds[0]",
        "orc['execs'][0]['path'] != sd['path']",
        "len(orc['envfiles']) >= len(sd['envfiles'])",
        "any((f not in sd['envfiles'] for f in orc['envfiles']))",
    ]

    def test_the_clause_census_reads_the_eight_clauses_and_every_one_is_told_apart_by_exactly_the_rows_that_isolate_it(self):
        m = self.m
        clauses = m.mark_clauses()
        self.assertEqual([label for label, _ in clauses], self.CLAUSES)
        for label, mutant in clauses:
            flipped = [name for name, sd, orc, verdict, dangerous in m.MARK_CASES
                       if (mutant("X", sd, orc)[0], mutant("X", sd, orc)[2]) != (verdict, dangerous)]
            self.assertTrue(flipped, label)
            for name in flipped:   # a mutant flips a marked row to unmarked, never the other way and never an unmarked row
                row = next(c for c in m.MARK_CASES if c[0] == name)
                self.assertTrue(row[4], (label, name))
        # the three round-7 rows are the ONLY rows that tell their clause's mutant apart (the reason they were added)
        alone = {"len(orc_cmds) >= len(sd_cmds)": "argv more, every command one of systemd's",
                 "any((c not in sd_cmds for c in orc_cmds))": "argv fewer, the first kept, one systemd does not run",
                 "len(orc['envfiles']) >= len(sd['envfiles'])": "EnvironmentFile more, every path one systemd reads"}
        for label, mutant in clauses:
            if label in alone:
                flipped = [name for name, sd, orc, verdict, dangerous in m.MARK_CASES if mutant("X", sd, orc)[2] != dangerous]
                self.assertEqual(flipped, [alone[label]], label)

    def test_a_clause_added_without_a_row_fails_the_self_check_and_names_it(self):
        # the discriminating half of the census: a ninth disjunct no row flips must fail the check, which a written-down count could not do
        m = self.m
        with open(m.__file__, encoding="utf-8") as f:
            source = f.read()
        marker = "or (orc_cmds and orc_cmds[0] != sd_cmds[0]): dangerous = True"
        self.assertEqual(source.count(marker), 1)
        ninth = source.replace(marker, "or (orc_cmds and orc_cmds[0] != sd_cmds[0]) or (len(orc_cmds) == 99): dangerous = True")
        self.assertEqual([label for label, _ in m.mark_clauses(ninth)][:6], self.CLAUSES[:5] + ["len(orc_cmds) == 99"])
        out = io.StringIO()
        self.assertEqual(m.self_check(out, source=ninth), 1)
        self.assertIn("8 of 9 mark clauses of compare() each told apart by a row", out.getvalue())
        self.assertIn("mark self-check FAILED", out.getvalue())
        self.assertIn("  mark clause told apart by no row of MARK_CASES: len(orc_cmds) == 99", out.getvalue())
        # a census that finds nothing is a failure, not a pass
        hollow = source.replace("def compare(kind, sd, orc):", "def compare(kind, sd, orc):\n    return 'agree', '', False\ndef _compare_was(kind, sd, orc):")
        self.assertEqual(m.mark_clauses(hollow), [])
        out = io.StringIO()
        self.assertEqual(m.self_check(out, source=hollow), 1)
        self.assertIn("0 of 0 mark clauses", out.getvalue())
        self.assertIn("no mark clause found in compare()", out.getvalue())

    def test_the_four_surfaces_state_the_unmarked_half_in_one_phrase(self):
        # extra6-2 (round 7): the printed legend dropped the qualifier from the commands disjunct; the module docstring, compare()'s
        # docstring, the legend and tests/README.md carry the one phrase, whitespace folded (the README wraps it)
        m = self.m
        phrase = "or listing fewer commands every one among systemd's with the first command kept, or fewer files every one among systemd's"
        with open(os.path.join(HERE, "README.md"), encoding="utf-8") as f:
            readme = f.read()
        for surface, text in (("module docstring", m.__doc__), ("compare() docstring", m.compare.__doc__), ("LEGEND", m.LEGEND), ("tests/README.md", readme)):
            self.assertIn(phrase, " ".join(text.split()), surface)
        self.assertNotIn("fewer commands with the first command kept", m.LEGEND)

    # the round-7 addendum of fork PR #778 (the mark lens): the census's form space, the label of an and-tested clause, the vacuity row
    # and the README's counts

    def _source(self):
        with open(self.m.__file__, encoding="utf-8") as f:
            return f.read()

    ANCHOR = 'if len(orc["envfiles"]) >= len(sd["envfiles"]) or any(f not in sd["envfiles"] for f in orc["envfiles"]): dangerous = True'

    def _with(self, extra):
        # compare() with `extra` (one or more statements at the function's indent) placed after the EnvironmentFile block
        source = self._source()
        self.assertEqual(source.count(self.ANCHOR), 1)
        return source.replace(self.ANCHOR, self.ANCHOR + "\n" + "\n".join("    " + line for line in extra.split("\n")))

    def test_a_mark_set_in_a_form_the_census_does_not_read_fails_the_self_check_and_names_the_line(self):
        # red before: each of these passed the check at 8 of 8 with no row (the census read `dangerous = True` in an if's body alone)
        m = self.m
        self.assertEqual(m.unread_mark_forms(), [])
        cond = 'orc["execs"] and orc["execs"][0]["argv"][-1:] == ["ninth"]'
        for form in ('dangerous = dangerous or bool(%s)' % cond,
                     'if %s: dangerous = bool(1)' % cond,
                     'if %s: dangerous |= True' % cond,
                     'if not (%s): pass\nelse: dangerous = True' % cond,
                     'if %s: return "DISAGREE", "ninth", bool(1)' % cond,
                     'for dangerous in [True]: pass',
                     'if %s: dangerous = True; return marked(diffs)' % cond,
                     'dangerous = True'):
            with self.subTest(form):
                source = self._with(form)
                forms = m.unread_mark_forms(source)
                self.assertEqual(len(forms), 1, forms)
                out = io.StringIO()
                self.assertEqual(m.self_check(out, source=source), 1)
                self.assertIn("mark self-check FAILED", out.getvalue())
                self.assertIn("  mark set in a form the census does not read, at line %d: " % forms[0][0], out.getvalue())
        # the read form beside them is still a clause: with a row it passes, without one it fails on the clause, not the form
        source = self._with('if %s: dangerous = True' % cond)
        self.assertEqual(m.unread_mark_forms(source), [])
        out = io.StringIO()
        self.assertEqual(m.self_check(out, source=source), 1)
        self.assertIn("8 of 9 mark clauses", out.getvalue())
        self.assertNotIn("a form the census does not read", out.getvalue())

    def test_an_and_tested_clause_is_labelled_by_its_whole_test(self):
        # red before: the label was the first conjunct alone (`orc['execs']`), the mutant still the whole test off
        m = self.m
        source = self._with('if orc["execs"] and orc["execs"][0]["argv"][-1:] == ["ninth"]: dangerous = True')
        labels = [label for label, _ in m.mark_clauses(source)]
        self.assertEqual(labels[-1], "orc['execs'] and orc['execs'][0]['argv'][-1:] == ['ninth']")
        self.assertEqual(labels[:-1], self.CLAUSES)
        out = io.StringIO()
        self.assertEqual(m.self_check(out, source=source), 1)
        self.assertIn("  mark clause told apart by no row of MARK_CASES: orc['execs'] and orc['execs'][0]['argv'][-1:] == ['ninth']", out.getvalue())

    def test_an_empty_oracle_command_list_is_unmarked_by_vacuity_and_pins_the_first_command_clauses_guard(self):
        # the mark lens's unpinned item: no row had an empty oracle exec list beside a nonempty systemd list, so the `orc_cmds and` guard
        # inside the first-command clause was exercised by no row and its removal would have raised on none
        m = self.m
        row = next(c for c in m.MARK_CASES if c[0].startswith("argv: the oracle reports no command"))
        self.assertEqual(m.compare("X", row[1], row[2])[::2], ("DISAGREE", False))
        source = self._source()
        guard = "or (orc_cmds and orc_cmds[0] != sd_cmds[0])"
        self.assertEqual(source.count(guard), 1)
        unguarded = source.replace(guard, "or (orc_cmds[0] != sd_cmds[0])")
        tree = m.ast.parse(unguarded)
        fn = m._compare_def(tree)
        ns = dict(vars(m))
        exec(compile(m.ast.fix_missing_locations(m.ast.Module(body=[fn], type_ignores=[])), "<compare() without the guard>", "exec"), ns)
        with self.assertRaises(IndexError):
            ns["compare"]("X", row[1], row[2])

    def test_the_readme_states_the_tables_counts(self):
        # the mutation lens found the README's count unpinned (28 -> 27 changed no test); the counts there are the table's and the census's
        m = self.m
        with open(os.path.join(HERE, "README.md"), encoding="utf-8") as f:
            readme = " ".join(f.read().split())
        n, k = len(m.MARK_CASES), len(m.mark_clauses())
        self.assertIn("`MARK_CASES`, %d synthetic (systemd, oracle) pairs" % n, readme)
        self.assertIn("`mark self-check: %d of %d ...; %d of %d mark clauses of compare() each told apart by a row`" % (n, n, k, k), readme)

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
        # the round-6 addendum: the pair above is marked by the exec->path branch whether the argv branch's first-command clause exists or
        # not (systemd printed a path); the clause alone marks the shift where the path is uncompared, a first command under the - prefix
        unread = m._sd(cmds=[["/nx/bin/a"], ["/nx/bin/b"]], path=None)
        v, detail, dangerous = m.compare("X", unread, m._orc(execs=[m._ex("/nx/bin/b", "/nx/bin/b", ignore=True)]))
        self.assertEqual((v, dangerous), ("DISAGREE", True), detail)
        self.assertIn("exec->path uncompared", detail)       # the unread field is still said on a row a DISAGREE wins
        v, detail, dangerous = m.compare("X", unread, m._orc(execs=[m._ex("/nx/bin/a", "/nx/bin/a", ignore=True)]))
        self.assertEqual((v, dangerous), ("DISAGREE", False), detail)

    def test_the_exec_path_compare_is_positional(self):
        # the round-6 addendum: systemd's first command's path against the oracle's FIRST; an identity compare (any oracle command carrying
        # systemd's path) would read this pair as agree, and every other row of the table carries one oracle command, where the two coincide
        m = self.m
        sd = m._sd(cmds=[["/nx/bin/a"], ["/nx/bin/b"]], path="/nx/bin/b")
        v, detail, dangerous = m.compare("X", sd, m._orc(execs=[m._ex("/nx/bin/a"), m._ex("/nx/bin/b")]))
        self.assertEqual((v, dangerous), ("DISAGREE", True), detail)
        self.assertIn("exec->path: systemd '/nx/bin/b', oracle '/nx/bin/a'", detail)

    def test_the_per_key_env_guard(self):
        # the round-6 addendum: a key equal on both sides beside one systemd alone sets is the unmarked D4 class; a compare that marked every
        # key of a differing env would mark the equal one
        m = self.m
        v, detail, dangerous = m.compare("X", m._sd(env={"A": "1", "B": "2"}), m._orc(env={"A": "1"}))
        self.assertEqual((v, dangerous), ("DISAGREE", False), detail)
        self.assertEqual(detail, "B: systemd '2', oracle unset")
        self.assertEqual(m.compare("X", m._sd(env={"A": "1"}), m._orc(env={"A": "1"}))[0], "agree")

    def test_the_row_printer_lists_the_uncompared_rows_under_their_own_heading(self):
        # the round-6 addendum: main printed DISAGREE rows alone, so a REFUSES row with the uncompared reason reached no report; the printer
        # is factored (print_rows) and pinned here over rows made from the table, the way main makes them from the sweep
        m = self.m
        rows = [(name, v, detail, dangerous) for name, sd, orc, _, _ in m.MARK_CASES for v, detail, dangerous in [m.compare("X", sd, orc)]]
        out = io.StringIO()
        m.print_rows(rows, out)
        text = out.getvalue()
        self.assertIn("uncompared (REFUSES with the reason, never agree: systemd printed no exec->path for the row's first command):\n", text)
        block = text.split("uncompared (REFUSES", 1)[1]
        self.assertIn("  exec->path uncompared under the - prefix (the loud skip): exec->path uncompared: systemd printed no resolved path for its first command (its errors are downgraded by the - prefix, which skips the executable check that prints it), so the oracle's '/nx/bin/x' stands unchecked\n", block)
        self.assertNotIn("the oracle does not model the form", text)   # a not-modelled REFUSES row is counted, not listed
        self.assertIn("disagreements:\n", text)
        self.assertIn("  env both set and different [dangerous]: A: systemd '1', oracle '2'\n", text)
        self.assertIn("  exec->path uncompared, but a DISAGREE elsewhere on the row wins [dangerous]: A: systemd '1', oracle '2'; exec->path uncompared:", text)
        self.assertNotIn("exec->path equal", text)                         # an agree row is printed nowhere
        self.assertNotIn("both refuse", text)


if __name__ == "__main__":
    unittest.main()
