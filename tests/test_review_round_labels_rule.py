#!/usr/bin/env python3
"""The shared round-label rule's pin (tests/review_round_labels_rule.py; the author's pass 11 on PR 857, 2026-09-21): its form
space, its crediting rule, and that it holds no population, no round set and reads nothing at all.

The helper is the one text of the convention that a numbered round is a credit to the reviewer who held it (the maintainer's
ruling of 2026-09-21 on the three per-branch guards of PRs 821, 857 and 860, which disagreed on the spellings they read and on
what credited one). Each branch's guard calls it with its own population, its own rounds and its own author form, so what this
module pins is the RULE alone: every spelling the rule classifies (a red and a green probe per class of FORM_CLASSES, assembled
at run time from a synthetic round set, so raising a caller's set moves nothing here), the wrapped shapes (a comment marker or a
block comment's continuation line between the qualifier and the number), the plural's lists and ranges (every number judged, a
range expanded so a caller's set need not be contiguous), the forms refused as unresolved, the unnumbered spellings not read,
the two refusals told apart, the caller's author form named in the refusal, and the tree-only pin carried over from the 857
guard and adapted: the helper imports re alone and reads no file, no environment and no path, pinned by resolution over its
source and by the absence of any file or reflective primitive. A probe's set is synthetic (no PR's rounds live here or in the
helper: a cell holds that no integer constant is bound at the helper's module level and that the same text gets opposite
verdicts under two caller sets)."""
import ast
import os
import re
import unittest

import tests.review_round_labels_rule as rule

HERE = os.path.dirname(os.path.realpath(__file__))
HELPER = os.path.join(HERE, "review_round_labels_rule.py")
IMPORTS = ("re",)
MEMBERS = {"re": ("I", "compile")}
BUILTINS = ("bool", "int", "len", "list", "range", "sorted", "str")
PRIMITIVES = ("open", "getattr", "setattr", "delattr", "hasattr", "__import__", "eval", "exec", "compile", "vars", "globals", "locals")
R, M = "round", "the maintainer's"
SET = frozenset({1, 2, 3, 4, 5, 6})        # a synthetic contiguous set, the class probes' (hi and lo below)
GAPPED = frozenset({1, 3, 4, 5})           # a synthetic set with a hole, the range expansion's


def _helper_tree():
    with open(HELPER, encoding="utf-8") as f:
        return ast.parse(f.read())


class RoundLabelRule(unittest.TestCase):
    maxDiff = None

    def test_the_helper_reads_nothing_at_all(self):
        """The 857 guard's tree-only pin, adapted to a module that opens no file: over the helper's source by RESOLUTION, the
        imports are exactly IMPORTS (`import re`, module-level, no from-import, no alias, none inside a function); every attribute
        chain rooted at re is in MEMBERS and every member is read (both ways); re is never read as a value; every callee is a
        name or an attribute chain; every name called is a definition of the helper or one of BUILTINS, held equal both ways; no
        primitive of PRIMITIVES is called or read anywhere (open among them: the helper reads no file); no module-level dunder
        name is read at all (no `__file__`, no `__name__`, no `__builtins__`); no attribute read is a dunder or str.format; no
        string constant is an absolute path, a home path, a `..` step or a drive letter; and by execution, the imported module
        binds no name of os, sys, subprocess, glob, pathlib or open."""
        tree = _helper_tree()
        parents = {c: p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}
        imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        self.assertEqual([n.lineno for n in imports if isinstance(n, ast.ImportFrom)], [], "a from-import in the helper")
        self.assertEqual([n.lineno for n in imports if n not in tree.body], [], "an import inside a function or a class in the helper")
        self.assertEqual([a.asname for n in imports for a in n.names if a.asname], [], "an import under another name in the helper")
        self.assertEqual(sorted(a.name for n in imports for a in n.names), sorted(IMPORTS), "the helper's import table is exactly IMPORTS: re alone")
        chains = {m: set() for m in IMPORTS}
        for n in ast.walk(tree):
            if isinstance(n, ast.Attribute) and not (isinstance(parents.get(n), ast.Attribute) and parents[n].value is n):
                parts, q = [], n
                while isinstance(q, ast.Attribute):
                    parts.append(q.attr)
                    q = q.value
                if isinstance(q, ast.Name) and q.id in IMPORTS:
                    chains[q.id].add(".".join(reversed(parts)))
        for m in IMPORTS:
            self.assertEqual(sorted(chains[m] ^ set(MEMBERS[m])), [], "the reads on %s are exactly MEMBERS[%r], both ways: %r" % (m, m, sorted(chains[m])))
        bare = [(n.id, n.lineno) for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id in IMPORTS and not (isinstance(parents.get(n), ast.Attribute) and parents[n].value is n)]
        self.assertEqual(bare, [], "a module of the table read as a value in the helper: %r" % (bare,))
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
        self.assertEqual([(ast.unparse(n.func), n.lineno) for n in calls if not isinstance(n.func, (ast.Name, ast.Attribute))], [], "a callee that is neither a name nor an attribute chain")
        defs = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        named = {n.func.id for n in calls if isinstance(n.func, ast.Name)}
        self.assertEqual(sorted(named - defs - set(BUILTINS)), [], "a name called that is neither a definition of the helper nor one of BUILTINS: %r" % (sorted(named - defs - set(BUILTINS)),))
        self.assertEqual(sorted(set(BUILTINS) - named), [], "a builtin in BUILTINS the helper no longer calls (held equal both ways)")
        prim = [(n.id, n.lineno) for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id in PRIMITIVES]
        self.assertEqual(prim, [], "a file or reflective primitive read in the helper, which opens no file and resolves no name by a string: %r" % (prim,))
        dunders = sorted({n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id.startswith("__")})
        self.assertEqual(dunders, [], "a module-level dunder name read in the helper (`__file__`, `__name__`, `__builtins__` reach the file system or the builtins): %r" % (dunders,))
        reflective = [(n.attr, n.lineno) for n in ast.walk(tree) if isinstance(n, ast.Attribute) and (n.attr.startswith("__") or n.attr in ("format", "format_map"))]
        self.assertEqual(reflective, [], "a dunder attribute or str.format in the helper: %r" % (reflective,))
        home = os.sep + "home" + os.sep
        paths = sorted({n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value) > 1
                        and (n.value[0] in (os.sep, "~") or home in n.value or re.search(r"(^|[\\/])\.\.([\\/]|$)", n.value) or re.match(r"[A-Za-z]:[\\/]", n.value))})
        self.assertEqual(paths, [], "a path-shaped constant in the helper: %r" % (paths,))
        bound = sorted(n for n in ("os", "sys", "subprocess", "glob", "pathlib", "open", "io", "shutil") if n in vars(rule))
        self.assertEqual(bound, [], "the imported helper binds a name that reaches the file system or the environment: %r" % (bound,))

    def test_no_round_set_lives_in_the_helper(self):
        """The rounds are the caller's: no integer constant is bound at the helper's module level (a set of a PR's rounds would
        be one), and the same text gets opposite verdicts under two caller sets, so the verdict is the caller's set's and nothing
        of the helper's."""
        ints = [(ast.unparse(n.targets[0]), n.lineno) for n in _helper_tree().body if isinstance(n, ast.Assign)
                for c in ast.walk(n.value) if isinstance(c, ast.Constant) and isinstance(c.value, int) and not isinstance(c.value, bool)]
        self.assertEqual(ints, [], "an integer constant bound at the helper's module level: a round set is the caller's, never the helper's: %r" % (ints,))
        text = "%s %s %d" % (M, R, 6)
        self.assertEqual(rule.offences(text, frozenset({6})), [], "a credit to a round of the caller's set is clean")
        self.assertEqual(len(rule.offences(text, frozenset({5}))), 1, "the same credit under a set lacking the round is refused")
        self.assertIn("the rulings the caller holds are numbered 5", rule.offences(text, frozenset({5}))[0][3])

    def test_the_form_space(self):
        """Every class the rule reads has red probes (uncredited at a ruled round, a credit one past the set, the author's head
        spelled as a round, a credited list with one number past the set) and green probes (a credit at the highest and the
        lowest ruled round, alone, possessive, parenthesised, capitalised), assembled at run time from SET; then the wrapped
        shapes (a `#` comment line and a block comment's ` * ` line between the qualifier and the number, an uncredited wrap
        reported at the number's line), the plural list and the ranges (every number judged; a range EXPANDED, so over GAPPED a
        credited range across the hole is refused naming the hole), a range that does not ascend, the forms refused as
        unresolved (a continuation the list did not consume, a plural naming one number, punctuation or markup before the
        number), the comma the plural's alone, the unnumbered spellings (the keyword-argument spelling, a bare referential form,
        the path stems rN), the typographic apostrophe in the qualifier, the caller's author form and the filename carried in
        the offence, and the two refusals told apart."""
        hi, lo = max(SET), min(SET)
        for (plural, kind), sep in rule.FORM_CLASSES.items():
            word = R + ("s" if plural else "")
            with self.subTest(form="%s%s<N>" % (word, sep.replace("\n", "<newline>"))):
                tail, tail_lo = ((" and %d" % lo), (" and %d" % hi)) if plural else ("", "")
                red = ["%s%s%d%s" % (word, sep, hi + 1, tail), "%s %s%s%d%s" % (M, word, sep, hi + 1, tail), "the %s%s%d%s head" % (word, sep, hi, tail),
                       "(%s%s%d%s, tests-1)" % (word, sep, lo, tail_lo), "%s %s%s%d and %d" % (M, word, sep, lo, hi + 1)]
                green = ["%s %s%s%d%s" % (M, word, sep, hi, tail), "%s %s%s%d%s" % (M, word, sep, lo, tail_lo), "%s %s%s%d%s's tests-3" % (M, word, sep, lo, tail_lo),
                         "(%s %s%s%d%s)" % (M, word, sep, hi, tail), "The %s %s%s%d%s ruled" % (M[4:], word, sep, hi, tail)]
                self.assertEqual([s for s in red if not rule.offences(s, SET)], [], "a refused form read as clean")
                self.assertEqual([s for s in green if rule.offences(s, SET)], [], "an allowed form read as an offence")
                self.assertEqual(rule.form_class(rule.mentions(green[0])[0]), (plural, kind), "the probe's spelling is classified as its own class")
        # the wrapped shapes: the qualifier and the number split by a line break, a comment marker or a block comment's line between
        self.assertEqual(rule.offences("... (%s %s\n    %d, correctness-1: the bound deleted" % (M, R, lo), SET), [], "a credit wrapped at the number is one credit")
        self.assertEqual(rule.offences("# ... (the\n    # maintainer's %s %d found it" % (R, hi), SET), [], "a credit wrapped at the qualifier, a comment marker between, is one credit")
        self.assertEqual(rule.offences("/* the\n * maintainer's %s %d on panel-3 */" % (R, hi), SET), [], "a credit wrapped at the qualifier inside a block comment is one credit")
        self.assertEqual(rule.offences(" * %s %s\n * %d ruled" % (M, R, hi), SET), [], "a credit wrapped at the number inside a block comment is one credit")
        self.assertEqual([o[1] for o in rule.offences("a\nb\n# the %s\n# %d head" % (R, hi + 1), SET)], [4], "a wrapped uncredited round is an offence at the line its number sits on")
        self.assertEqual([o[1] for o in rule.offences("a\n * the %s\n * %d head" % (R, hi), SET)], [3], "a wrapped uncredited round inside a block comment is an offence at the number's line")
        self.assertEqual([o[1] for o in rule.offences("%s %s\n%d\n" % (M, R, hi + 1), SET)], [2], "a wrapped credit to an unruled round is an offence at the number's line")
        # the plural list and the ranges: every number judged, a range expanded
        self.assertEqual(len(rule.offences("%s %ss %d and %d" % (M, R, lo, hi + 1), SET)), 1, "a credited list with one unruled number is one offence")
        self.assertEqual(rule.offences("%s %ss %d to %d" % (M, R, lo, hi), SET), [], "a credited range inside the set is clean")
        self.assertEqual(len(rule.offences("%ss %d and %d were held" % (R, lo, hi), SET)), 1, "an uncredited list is one offence, at the list")
        for rng in ("%d-%d", "%d–%d", "%d through %d", "%d thru %d", "%d to %d"):
            with self.subTest(range=rng):
                self.assertIn("no ruling exists for a maintainer round numbered %d" % (hi + 1), rule.offences("%s %ss %s" % (M, R, rng % (lo, hi + 1)), SET)[0][3],
                              "a credited range one past the set is an offence naming the number past it")
                self.assertEqual(rule.offences("%s %ss %s" % (M, R, rng % (lo, hi)), SET), [], "a credited range inside the set is clean")
                self.assertEqual(rule.forms("%ss %s" % (R, rng % (lo, hi)))[0][3], list(range(lo, hi + 1)), "every number of the range is read, the interior included")
                self.assertIn("no ruling exists for a maintainer round numbered 2", rule.offences("%s %ss %s" % (M, R, rng % (1, 5)), GAPPED)[0][3],
                              "a credited range across a hole in the caller's set is refused naming the hole: the endpoints do not stand for the range")
                self.assertEqual(rule.offences("%s %ss %s" % (M, R, rng % (3, 5)), GAPPED), [], "a credited range inside a gapped set is clean")
        for lst in ("%d/%d", "%d, %d", "%d and %d", "%d or %d", "%d & %d"):
            with self.subTest(list=lst):
                self.assertEqual(rule.forms("%ss %s" % (R, lst % (lo, hi)))[0][3], [lo, hi], "a list names its numbers alone, nothing between them")
                self.assertEqual(rule.offences("%s %ss %s" % (M, R, lst % (1, 5)), GAPPED), [], "a credited list over a gapped set judges its numbers alone")
        self.assertIn("a range that does not ascend", rule.offences("%s %ss %d-%d" % (M, R, hi, lo), SET)[0][3], "a range written backwards is unclassifiable")
        # the forms refused as unresolved: a continuation the list did not consume, a plural naming one number, punctuation or markup before the number
        for s in ("%ss %d; %d" % (R, lo, hi + 1), "%s %d: %d findings" % (R, hi, hi + 1), "%s %s %d, %d findings" % (M, R, hi, hi + 1), "%s %d, %d" % (R, lo, hi),
                  "%s %ss %d" % (M, R, hi), "%ss %d" % (R, hi), "%s %db" % (R, hi), "%s %d_x" % (R, hi),
                  "%s: %d" % (R, hi + 1), "%s %s: %d" % (M, R, hi + 1), "%s (%d)" % (R, hi + 1), "%s **%d**" % (R, hi + 1), "%s `%d`" % (R, hi + 1), '%s "%d"' % (R, hi + 1), "%s.%d" % (R, hi)):
            with self.subTest(unresolved=s):
                self.assertEqual([k for _, _, k, _ in rule.forms(s)], ["unclassifiable"], "a form the rule did not resolve is unclassifiable, never numbered or unread: %r" % (s,))
                self.assertIn("cannot classify", rule.offences(s, SET)[0][3])
        self.assertIn("a further number after a run the list did not consume", rule.offences("%s %s %d, %d findings" % (M, R, hi, hi + 1), SET)[0][3])
        self.assertEqual(rule.forms("%s %ss %d, %d" % (M, R, lo, hi))[0][3], [lo, hi], "the plural's comma list is read whole")
        # the unnumbered spellings are not read
        for s in ("%ss=40" % R, "%ss=1" % R, "in 1 %ss" % R, "a typing %s" % R, "the two-%s convergence bound" % R, "in its second %s" % R, "_commands_a%s_the_recorder" % R,
                  "%s(t_dead - t0, 2)" % R, "spaces-a%s-dots" % R, "rulings-r1.md", "the boot a%s it" % R, "each %s of planting" % R, "a typing %s\n# visits" % R,
                  "%s_labels" % R, "the %s-trip" % R, "the %s's own" % R, "this %s" % R, "a %s of 3 drives" % R, "r6-margin/lab-head2.log", "Math.%s(x)" % R, "%s_labels.py:66" % R):
            self.assertEqual(rule.offences(s, SET), [], "an unnumbered use read as an offence: %r" % (s,))
            self.assertEqual(rule.mentions(s), [], "an unnumbered use read as a mention: %r" % (s,))
        # the typographic apostrophe reads as the ASCII one; the filename and the caller's author form are carried
        self.assertEqual(rule.offences("the maintainer’s %s %d" % (R, hi), SET), [], "a typographic apostrophe in the qualifier is the credit it is")
        o = rule.offences("%s %d" % (R, hi), SET, "tests/x.py", "\"the author's pass P\"")
        self.assertEqual((o[0][0], o[0][1], o[0][2]), ("tests/x.py", 1, "%s %d" % (R, hi)))
        self.assertIn("\"the author's pass P\" for the author's own work", o[0][3], "the caller's author form is named in the refusal")
        self.assertIn("another review's round by that review and its date with no number", o[0][3], "the date form for another review is named")
        # the two refusals are told apart: an uncredited number, and a credit to a round with no ruling
        self.assertIn("credit to the maintainer", rule.offences("%s %d" % (R, hi), SET)[0][3])
        self.assertIn("no ruling exists", rule.offences("%s %s %d" % (M, R, hi + 1), SET)[0][3])
        self.assertEqual(rule.mentions("%s %s %d and %s-%d and R%s %d's and %ss %d and %d" % (M, R, hi, R, lo, R[1:], lo, R, lo, hi)),
                         ["%s %d" % (R, hi), "%s-%d" % (R, lo), "R%s %d" % (R[1:], lo), "%ss %d and %d" % (R, lo, hi)])
        self.assertEqual(sorted(rule.FORM_CLASSES), sorted({(p, k) for p in (False, True) for k in ("none", "space", "hyphen", "hash", "wrap", "star")} - {(True, "none"), (True, "hyphen"), (True, "hash")}),
                         "the classes with probes are every (plural, separator kind) pair but the three plural spellings no branch writes (roundsN, rounds-N, rounds #N), which the classifier still reads and a caller's population check names")


if __name__ == "__main__":
    unittest.main()
