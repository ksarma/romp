#!/usr/bin/env python3
"""The shared round-label rule's pin (tests/review_round_labels_rule.py; the author's pass 11 on PR 857, 2026-09-21): its form
space, its crediting rule, that it keys on misattribution, and that it holds no population, no round set and reads nothing at all.

The helper is the one text of the convention that a numbered round is a credit to the reviewer who held it (the maintainer's ruling
of 2026-09-21 on the three per-branch guards of PRs 821, 857 and 860, which disagreed on the spellings they read and on what
credited one) and that the rule refuses MISATTRIBUTION, not the absence of a qualifier (the reviewer's further ruling of
2026-09-21: "the reviewer's round N" is a credit beside "the maintainer's round N"; a date after the round is correct prose; an
unqualified round is the reviewer's by the convention that rounds belong to the reviewer and the author's work between them is a
pass, a default the rule states with its reason; what is refused is a round the reviewer never held, a round credited to the
author, a pass credited to the reviewer or the maintainer, and every form the rule cannot resolve). Each branch's guard calls it
with its own population, its own rounds and its own author form, so what this module pins is the RULE alone: every spelling the
rule classifies (a red and a green probe per class of FORM_CLASSES, assembled at run time from a synthetic round set, so raising a
caller's set moves nothing here, each class in digits and in words but the one with no separator, in digits alone), the READ
direction the reader keeps (the coordinator's ruling of 2026-09-29 on PR 857's review: a number after the word in digits or as a
cardinal word, an ordinal before it in digits or as a word, credited or not, a list with or without a serial comma and the
singular's comma followed by "and" all read into numbers; each placement the rule's docstring states it refuses refused with its
reason, the short run's six characters probed on both sides of the bound (a run of six refused, and a run of seven or one across
a line break not read), and the unnumbered forms it names not read, among them a count before the word, a word between the word
and a number, a word other than "review" between an ordinal and the word, and a run of punctuation longer than six characters or
across a line break between the word and a number or between an ordinal and the word; and a number spelled in a way the reader
does not know, a
Roman numeral among them, one of those unnumbered forms; a spelling that docstring does not state is its stated outside, to which
the coordinator's ruling of 2026-09-30 restated the earlier ruling's refusal of every other placement, and no probe here claims
one), the wrapped shapes (a comment marker or a block comment's continuation line between the qualifier and the number, and the
wrap a list or a range takes between two of its numbers: read whole, a further number past it beside a link refused as on one
line, a line break with no link beside it joining nothing, a range mark opening the next line, a bullet, joining nothing while
one ending the first line joins, and each width and look-back that docstring states for the refusal runs and the date probed at
its bound), the plural's lists
and ranges (every number judged, a range expanded so a caller's set need not be contiguous), the date form, the forms refused as
unresolved, the unnumbered spellings not read, the credit's two names and the default with its stated reason, each misattribution
refused with its reason and the caller's author form named in it, and the tree-only pin carried over from the 857 guard and adapted:
the helper imports re alone and reads no file, no environment and no path, pinned by resolution over its source and by the absence
of any file or reflective primitive. A probe's set is synthetic (no PR's rounds live here or in the helper: a cell holds that no
round set lives in the helper by any shape it could take, an integer constant bound at module level by any assignment, in any
function's default, in any set, tuple, list or dict-key display or any range(), set() or frozenset() anywhere in the module, and by
execution that offences() takes its rounds with no default; that the same text gets opposite verdicts under two caller sets; and
that neither the helper's text nor this module's spells a numbered-round form or a misattributed pass, so a caller that censuses
either reads it clean and no credit to any PR's round lives in the rule's text)."""
import ast
import inspect
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
R, M, V, A = "round", "the maintainer's", "the reviewer's", "the author's"
D = "2026-09-15"                            # a date, the form the rule consumes after a round
SET = frozenset({1, 2, 3, 4, 5, 6})        # a synthetic contiguous set, the class probes' (hi and lo below)
GAPPED = frozenset({1, 3, 4, 5})           # a synthetic set with a hole, the range expansion's
# the probes' number words, spelled here and never read from the helper's tables, so a wrong table there cannot agree with its probe:
# zero to nineteen, the tens from twenty and the four large words, each as a cardinal and as an ordinal; card() and ordinal() compose
# every number from zero to ninety-nine from them, and test_every_number_word_the_reader_knows probes each of them
WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
         "fifteen", "sixteen", "seventeen", "eighteen", "nineteen")
NTH = ("zeroth", "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth",
       "thirteenth", "fourteenth", "fifteenth", "sixteenth", "seventeenth", "eighteenth", "nineteenth")
TENS_WORDS = ("twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")
TENS_NTH = ("twentieth", "thirtieth", "fortieth", "fiftieth", "sixtieth", "seventieth", "eightieth", "ninetieth")
BIG = ("hundred", "thousand", "million", "billion")
BIG_NTH = ("hundredth", "thousandth", "millionth", "billionth")


def nth(x):
    """x as a digit ordinal: 1st, 2nd, 3rd, 4th, ..., 11th, 12th, 13th, 21st."""
    return "%d%s" % (x, "th" if 10 <= x % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(x % 10, "th"))


def card(x):
    """x from zero to ninety-nine as a cardinal word: WORDS below twenty, else a tens word, joined by a hyphen to the unit's word
    unless x is a multiple of ten."""
    return WORDS[x] if x < 20 else TENS_WORDS[x // 10 - 2] + ("-" + WORDS[x % 10] if x % 10 else "")


def ordinal(x):
    """x from zero to ninety-nine as an ordinal word: NTH below twenty, a tens ordinal for a multiple of ten, else a tens word joined
    by a hyphen to the unit's ordinal."""
    return NTH[x] if x < 20 else TENS_WORDS[x // 10 - 2] + "-" + NTH[x % 10] if x % 10 else TENS_NTH[x // 10 - 2]


# the two spellings each class is probed in: (the number after the word, the ordinal before it)
SPELLINGS = {"digits": (str, nth), "words": (lambda x: WORDS[x], lambda x: NTH[x])}


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
        """The rounds are the caller's, held over the helper's source by every shape a round set could take and once by execution
        (pass 11's second closing fixer pass: the first check read plain module-level assignments alone, so an annotated
        assignment, a function returning a set, an annotated range() and a default on offences() all passed it): no integer
        constant is bound at the helper's module level by any assignment (plain, annotated or augmented); no default of any
        function or lambda of the helper holds one (a caller could then omit its set); no set, tuple, list or dict-key display
        over integer constants and no range(), set() or frozenset() over integer constants anywhere in the module (a round set
        inside a function is one; the one range() the helper makes takes computed bounds); and, by execution, offences() takes
        `rounds` with no default. Then the same text gets opposite verdicts under two caller sets, so the verdict is the
        caller's set's and nothing of the helper's; and neither the helper's text nor this module's spells a numbered-round
        form, nor holds an offence under a synthetic set (a pass credited to the reviewer among the forms offences() reads, which
        forms() does not), the docstrings writing N and every probe assembled at run time, so no credit to any PR's round lives in
        the rule's text and a caller that censuses either file reads it clean (pass 11's closing fixer pass: the two files were
        added by the branch that carries the rule, outside its guard's population, and that guard is deleted before the branch
        lands, so this is what holds them)."""
        tree = _helper_tree()

        def ints(node):
            return [c for c in ast.walk(node) if isinstance(c, ast.Constant) and isinstance(c.value, int) and not isinstance(c.value, bool)]

        bound = [(ast.unparse(n.targets[0] if isinstance(n, ast.Assign) else n.target), n.lineno) for n in tree.body
                 if isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign)) and n.value is not None and ints(n.value)]
        self.assertEqual(bound, [], "an integer constant bound at the helper's module level (a plain, annotated or augmented assignment): a round set is the caller's, never the helper's: %r" % (bound,))
        defaults = [(fn.name if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) else "lambda", ast.unparse(d), d.lineno)
                    for fn in ast.walk(tree) if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
                    for d in list(fn.args.defaults) + [k for k in fn.args.kw_defaults if k is not None] if ints(d)]
        self.assertEqual(defaults, [], "an integer constant in a default of a helper function (a round set a caller could omit): %r" % (defaults,))
        displays = [(ast.unparse(n), n.lineno) for n in ast.walk(tree)
                    if (isinstance(n, (ast.Set, ast.Tuple, ast.List)) and any(isinstance(e, ast.Constant) and ints(e) for e in n.elts))
                    or (isinstance(n, ast.Dict) and any(isinstance(k, ast.Constant) and ints(k) for k in n.keys))]
        self.assertEqual(displays, [], "a set, tuple, list or dict-key display over integer constants anywhere in the helper (a round set inside a function is one): %r" % (displays,))
        calls = [(ast.unparse(n), n.lineno) for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id in ("range", "set", "frozenset") and any(isinstance(a, ast.Constant) and ints(a) for a in n.args)]
        self.assertEqual(calls, [], "a range(), set() or frozenset() over integer constants anywhere in the helper (the one range() it makes takes computed bounds): %r" % (calls,))
        self.assertIs(inspect.signature(rule.offences).parameters["rounds"].default, inspect.Parameter.empty, "offences() takes the caller's rounds with no default, so no caller can omit its set")
        for path in (HELPER, os.path.realpath(__file__)):
            with open(path, encoding="utf-8") as f:
                text = f.read()
            spelled = [(line, s, kind) for line, s, kind, _ in rule.forms(text) if kind != "unnumbered"]
            self.assertEqual(spelled, [], "%s spells a numbered-round form: the rule credits no PR's round, so no credit and no probe written with a digit belongs in its text "
                                          "(a probe is assembled at run time; the docstrings write N): %r" % (os.path.basename(path), spelled))
            self.assertEqual(rule.offences(text, SET), [], "%s holds an offence under a synthetic set (a numbered pass credited to the reviewer or the maintainer is one forms() does not read): "
                                                        "the rule's own text reads clean under the rule" % os.path.basename(path))
        text = "%s %s %d" % (M, R, 6)
        self.assertEqual(rule.offences(text, frozenset({6})), [], "a credit to a round of the caller's set is clean")
        self.assertEqual(len(rule.offences(text, frozenset({5}))), 1, "the same credit under a set lacking the round is refused")
        self.assertIn("the rulings the caller holds are numbered 5", rule.offences(text, frozenset({5}))[0][3])

    def test_the_form_space(self):
        """Every class the rule reads has red probes (an unqualified round past the set by one, which the default reads as the
        reviewer's and no ruling covers; the maintainer's and the reviewer's credit past the set; the author's round and the
        author's review round, a round credited to the author; a credited list with one number past the set) and green probes (a
        credit at the highest and the lowest ruled round, alone, possessive, parenthesised, capitalised; the reviewer's credit; the
        unqualified "review round N" and the bare round at a ruled round, the reviewer's by default; the author's head spelled as a
        round; a round followed by a count word; a dated round), assembled at run time from SET, each class in digits and in words
        (a class of a number after the word with the number in digits and as a cardinal word, the class with no separator in digits
        alone, since the word glued to a letter is another word; an ordinal class with the ordinal in digits and as a word, a list
        for a plural, "review" on either side of the ordinal among the author's reds, and "in its" before an unqualified one among
        the greens); then the wrapped shapes (a `#` comment line and a block comment's ` * ` line
        between the qualifier and the number, an unqualified wrap past the set reported at the number's line), the plural list and
        the ranges (every number judged; a range EXPANDED, so over GAPPED a credited range across the hole is refused naming the
        hole), a range that does not ascend, the forms refused as unresolved (a continuation the list did not consume, a plural
        naming one number, punctuation or markup before the number), the comma the plural's alone, the unnumbered spellings (the
        keyword-argument spelling, a bare referential form, a count before the word, a word between an ordinal and the word, an
        ordinal before another word the word begins, the word glued to a letter, a longer word a number word begins or an ordinal
        ends, a Roman numeral, the path stems rN), the typographic apostrophe in the qualifier, the caller's author form and the
        filename carried in the offence, and the refusals told apart by their reasons. Then the READ direction's own probes (the
        coordinator's ruling of 2026-09-29 on PR 857's review), each a red the reader would miss without the part it pins: the
        serial comma in the plural, a range before it among them, and the singular's comma followed by "and" read as lists, and the
        singular's other commas refused, and so is a number after "and/or", after the word and before it, in digits and in words,
        with a space on either side of its slash or on both among them; a
        number word after the word read into its value (a qualified, an author's and a plural word form refused, a range and a list
        in words, a tens word joined to a unit, a digit form beside a word elsewhere clean), a list and a range whose continuation
        is capitalised or in capitals read the same (a range over GAPPED naming the hole), and a number word the reader does not
        read, or does not place, refused; and an ordinal before the word read whether credited or not (the author's credit in words
        and in digits, the maintainer's and the reviewer's past the set, an unqualified one by the default), as a list and a range
        (the singular's list, its comma followed by "and" and its range each in words and in digits), a tens ordinal joined to a
        unit, and each ordinal shape the reader cannot place refused (a plural naming one ordinal, a number before the run it did
        not consume, a digit ordinal among them, a singular's range that does not ascend, a number both before the word and after
        it, a large ordinal, a number after the word of an ordinal form); and punctuation or markup between an ordinal
        and the word refused, the mirror of the same after the word, credited or not, a large ordinal and "review" after the run
        among them, while the same markup before another word the word begins, or after the end of another word, is not read; the
        short run's stated bound, six characters, probed at the bound in digits and in words, punctuation or markup of six characters
        refused between the word and a number, between an ordinal and the word, and after "review" there, each red when its bound is
        cut to five, and on its other side a run of seven characters, or a run within six across a line break, not read in each of
        those three places, each red when its run is widened to seven or allowed to cross a line break; and
        a number word glued to the list word or the range word before it, or a digit ordinal glued to the letter after it, read as
        no number, so a plural with one other number is refused as a plural naming one number and never read as a list or a range
        (a number word glued to "and", "or" or "to", qualified or not, and a digit ordinal glued to "and", "or" or "to", credited
        or not: the guard before a number word in a continuation and the whole-word guard on a digit ordinal each have these reds)."""
        hi, lo = max(SET), min(SET)
        for (plural, kind), sep in rule.FORM_CLASSES.items():
            word = R + ("s" if plural else "")
            for spell, (num, o) in SPELLINGS.items():
                if (kind, spell) == ("none", "words"):
                    continue   # the word glued to a letter is another word ("rounded"), so a number word needs a separator; the unnumbered probes hold it
                if not kind.startswith("ordinal "):
                    label = "%s%s<N>" % (word, sep.replace("\n", "<newline>"))
                    tail, tail_lo = ((" and %s" % num(lo)), (" and %s" % num(hi))) if plural else ("", "")
                    red = ["%s%s%s%s" % (word, sep, num(hi + 1), tail), "%s %s%s%s%s" % (M, word, sep, num(hi + 1), tail), "%s %s%s%s%s" % (V, word, sep, num(hi + 1), tail),
                           "%s %s%s%s%s" % (A, word, sep, num(hi), tail), "%s review %s%s%s%s" % (A, word, sep, num(lo), tail_lo), "%s %s%s%s and %s" % (M, word, sep, num(lo), num(hi + 1))]
                    green = ["%s %s%s%s%s" % (M, word, sep, num(hi), tail), "%s %s%s%s%s" % (M, word, sep, num(lo), tail_lo), "%s %s%s%s%s's tests-3" % (M, word, sep, num(lo), tail_lo),
                             "(%s %s%s%s%s)" % (M, word, sep, num(hi), tail), "The %s %s%s%s%s ruled" % (M[4:], word, sep, num(hi), tail), "%s %s%s%s%s" % (V, word, sep, num(hi), tail),
                             "review %s%s%s%s" % (word, sep, num(hi), tail), "%s%s%s%s" % (word, sep, num(lo), tail_lo), "the %s%s%s%s head" % (word, sep, num(hi), tail),
                             "(%s%s%s%s, tests-1)" % (word, sep, num(lo), tail_lo), "Review %s%s%s%s, %s" % (word, sep, num(hi), tail, D)]
                else:
                    label = "<N>%s%s" % (sep.replace("\n", "<newline>"), word)
                    run, run_lo = ((lambda x: "%s and %s" % (o(x), o(lo))), (lambda x: "%s and %s" % (o(x), o(hi)))) if plural else (o, o)
                    red = ["%s%s%s" % (run(hi + 1), sep, word), "%s %s%s%s" % (M, run(hi + 1), sep, word), "%s %s%s%s" % (V, run(hi + 1), sep, word),
                           "%s %s%s%s" % (A, run(hi), sep, word), "%s review %s%s%s" % (A, run_lo(lo), sep, word), "%s %s%s review %s" % (A, run_lo(lo), sep, word),
                           "%s %s and %s%s%s" % (M, o(lo), o(hi + 1), sep, word)]
                    green = ["%s %s%s%s" % (M, run(hi), sep, word), "%s %s%s%s" % (M, run_lo(lo), sep, word), "%s %s%s%s's tests-3" % (M, run_lo(lo), sep, word),
                             "(%s %s%s%s)" % (M, run(hi), sep, word), "The %s %s%s%s ruled" % (M[4:], run(hi), sep, word), "%s %s%s%s" % (V, run(hi), sep, word),
                             "%s %s%s review %s" % (M, run(hi), sep, word), "in its %s%s%s" % (run(hi), sep, word), "the %s%s%s head" % (run_lo(lo), sep, word),
                             "(%s%s%s, tests-1)" % (run_lo(lo), sep, word), "The %s%s%s, %s" % (run(hi), sep, word, D)]
                with self.subTest(form=label, spelling=spell):
                    self.assertEqual([s for s in red if not rule.offences(s, SET)], [], "a refused form read as clean")
                    self.assertEqual([s for s in green if rule.offences(s, SET)], [], "an allowed form read as an offence")
                    self.assertEqual(rule.form_class(rule.mentions(green[0])[0]), (plural, kind), "the probe's spelling is classified as its own class")
                    self.assertEqual([len(rule.mentions(s)) for s in green], [1] * len(green), "every green probe is one numbered mention, the dated one included")
        # the wrapped shapes: the qualifier and the number split by a line break, a comment marker or a block comment's line between
        self.assertEqual(rule.offences("... (%s %s\n    %d, correctness-1: the bound deleted" % (M, R, lo), SET), [], "a credit wrapped at the number is one credit")
        self.assertEqual(rule.offences("# ... (the\n    # maintainer's %s %d found it" % (R, hi), SET), [], "a credit wrapped at the qualifier, a comment marker between, is one credit")
        self.assertEqual(rule.offences("/* the\n * maintainer's %s %d on panel-3 */" % (R, hi), SET), [], "a credit wrapped at the qualifier inside a block comment is one credit")
        self.assertEqual(rule.offences("/* the\n * reviewer's %s %d on panel-3 */" % (R, hi), SET), [], "the reviewer's credit wrapped at the qualifier inside a block comment is one credit")
        self.assertEqual(rule.offences(" * %s %s\n * %d ruled" % (M, R, hi), SET), [], "a credit wrapped at the number inside a block comment is one credit")
        self.assertEqual([o[1] for o in rule.offences("a\nb\n# the %s\n# %d head" % (R, hi + 1), SET)], [4], "a wrapped unqualified round past the set is an offence at the line its number sits on")
        self.assertEqual([o[1] for o in rule.offences("a\n * the %s\n * %d head" % (R, hi + 1), SET)], [3], "a wrapped unqualified round past the set inside a block comment is an offence at the number's line")
        self.assertEqual(rule.offences("a\n * the %s\n * %d head" % (R, hi), SET), [], "a wrapped unqualified round at a ruled round is the reviewer's by default")
        self.assertEqual([o[1] for o in rule.offences("%s %s\n%d\n" % (M, R, hi + 1), SET)], [2], "a wrapped credit to an unruled round is an offence at the number's line")
        self.assertEqual([(o[1], o[3].split(":")[0]) for o in rule.offences("# the\n    # author's %s %d" % (R, hi), SET)], [(2, "a round credited to the author")], "the author's qualifier wrapped at a comment marker is read as the author's")
        # the plural list and the ranges: every number judged, a range expanded
        self.assertEqual(len(rule.offences("%s %ss %d and %d" % (M, R, lo, hi + 1), SET)), 1, "a credited list with one unruled number is one offence")
        self.assertEqual(rule.offences("%s %ss %d to %d" % (M, R, lo, hi), SET), [], "a credited range inside the set is clean")
        self.assertEqual(rule.offences("%ss %d and %d were held" % (R, lo, hi), SET), [], "an unqualified list inside the set is the reviewer's by default")
        self.assertEqual(len(rule.offences("%ss %d and %d were held" % (R, lo, hi + 1), SET)), 1, "an unqualified list with one number past the set is one offence, at the list")
        for rng in ("%d-%d", "%d–%d", "%d through %d", "%d thru %d", "%d to %d"):
            with self.subTest(range=rng):
                self.assertIn("no ruling exists for a round numbered %d" % (hi + 1), rule.offences("%s %ss %s" % (M, R, rng % (lo, hi + 1)), SET)[0][3],
                              "a credited range one past the set is an offence naming the number past it")
                self.assertEqual(rule.offences("%s %ss %s" % (M, R, rng % (lo, hi)), SET), [], "a credited range inside the set is clean")
                self.assertEqual(rule.forms("%ss %s" % (R, rng % (lo, hi)))[0][3], list(range(lo, hi + 1)), "every number of the range is read, the interior included")
                self.assertIn("no ruling exists for a round numbered 2", rule.offences("%s %ss %s" % (M, R, rng % (1, 5)), GAPPED)[0][3],
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
        for s in ("%ss=40" % R, "%ss=1" % R, "in 1 %ss" % R, "a typing %s" % R, "the two-%s convergence bound" % R, "_commands_a%s_the_recorder" % R,
                  "%s %ss" % (WORDS[hi], R), "the %s test %s" % (NTH[hi], R), "a %s %s-trip" % (NTH[hi], R), "the Nth %s" % R, "%s %s pass" % (M, NTH[hi]),
                  "%s%s" % (R, WORDS[hi + 2]), "%s%s" % (R, NTH[hi + 2]), "the %s %sed corner" % (NTH[hi + 1], R), "%s %sfold" % (R, WORDS[hi + 1]),
                  "a milli%s %s trip" % (NTH[2], R), "%s VII" % R, "%s(t_dead - t0, 2)" % R, "spaces-a%s-dots" % R, "rulings-r1.md", "the boot a%s it" % R,
                  "each %s of planting" % R, "a typing %s\n# visits" % R, "%s_labels" % R, "the %s-trip" % R, "the %s's own" % R, "this %s" % R, "a %s of 3 drives" % R,
                  "r6-margin/lab-head2.log", "Math.%s(x)" % R, "%s_labels.py:66" % R, "%s pass over the tree" % M, "%s pass N" % V):
            self.assertEqual(rule.offences(s, SET), [], "an unnumbered use read as an offence: %r" % (s,))
            self.assertEqual(rule.mentions(s), [], "an unnumbered use read as a mention: %r" % (s,))
        # the typographic apostrophe reads as the ASCII one; the filename and the caller's author form are carried
        self.assertEqual(rule.offences("the maintainer’s %s %d" % (R, hi), SET), [], "a typographic apostrophe in the qualifier is the credit it is")
        self.assertEqual(rule.offences("the reviewer’s %s %d" % (R, hi), SET), [], "a typographic apostrophe in the reviewer's qualifier is the credit it is")
        o = rule.offences("%s %d" % (R, hi + 1), SET, "tests/x.py", "\"the author's pass P\"")
        self.assertEqual((o[0][0], o[0][1], o[0][2]), ("tests/x.py", 1, "%s %d" % (R, hi + 1)))
        self.assertIn("\"the author's pass P\" for the author's own work", o[0][3], "the caller's author form is named in the refusal")
        self.assertIn("another review's round by that review and its date with no number", o[0][3], "the date form for another review is named")
        # the refusals are told apart by their reasons: no ruling, the author's round, a pass credited to the wrong party, unclassifiable
        self.assertIn("no ruling exists", rule.offences("%s %d" % (R, hi + 1), SET)[0][3])
        self.assertIn("no ruling exists", rule.offences("%s %s %d" % (M, R, hi + 1), SET)[0][3])
        self.assertIn("a round credited to the author", rule.offences("%s %s %d" % (A, R, hi), SET)[0][3])
        self.assertIn("a pass credited to the maintainer", rule.offences("%s pass %d" % (M, hi), SET)[0][3])
        self.assertIn("cannot classify", rule.offences("%s: %d" % (R, hi), SET)[0][3])
        self.assertEqual(rule.mentions("%s %s %d and %s-%d and R%s %d's and %ss %d and %d" % (M, R, hi, R, lo, R[1:], lo, R, lo, hi)),
                         ["%s %d" % (R, hi), "%s-%d" % (R, lo), "R%s %d" % (R[1:], lo), "%ss %d and %d" % (R, lo, hi)])
        after = {(p, k) for p in (False, True) for k in ("none", "space", "hyphen", "hash", "wrap", "star")} - {(True, "none"), (True, "hyphen"), (True, "hash")}
        ordinal = {(p, "ordinal " + k) for p in (False, True) for k in ("space", "hyphen", "wrap", "star")} - {(True, "ordinal hyphen")}
        self.assertEqual(sorted(rule.FORM_CLASSES), sorted(after | ordinal),
                         "the classes with probes are every (plural, separator kind) pair of a number after the word but the three plural spellings no branch writes "
                         "(roundsN, rounds-N, rounds #N), and every (plural, ordinal separator kind) pair of space, hyphen, wrap and star but the plural's hyphen: the "
                         "classifier still reads the rest, and a caller's population check names any it meets")
        # the READ direction, lists: the plural's serial comma (a range before it too) and the singular's comma followed by "and" are read
        for s in ("%s %ss %d, %d, and %d" % (M, R, lo, hi, hi + 1), "%ss %d, %d, or %d" % (R, lo, hi, hi + 1), "%s %ss %d-%d, and %d" % (M, R, lo, hi, hi + 1),
                  "%ss %d, %d, & %d" % (R, lo, hi, hi + 1), "%ss %d, %d, / %d" % (R, lo, hi, hi + 1), "%s %s %d, and %d" % (M, R, lo, hi + 1), "%s %d, and %d" % (R, hi, hi + 1)):
            with self.subTest(read_list=s):
                self.assertEqual([k for _, _, k, _ in rule.forms(s)], ["numbered"], "a serial-comma list, or the singular's comma and \"and\", is read: %r" % (s,))
                self.assertIn("no ruling exists for a round numbered %d" % (hi + 1), rule.offences(s, SET)[0][3], "every number of it is judged: %r" % (s,))
        self.assertEqual(rule.forms("%s %ss %d, %d, and %d" % (M, R, lo, lo + 1, hi))[0][3], [lo, lo + 1, hi], "a serial-comma list names its numbers alone")
        self.assertEqual(rule.offences("%s %ss %d, %d, and %d" % (M, R, lo, lo + 1, hi), SET), [], "a serial-comma list over ruled rounds is clean")
        self.assertEqual(rule.forms("%s %s %d, and %d" % (M, R, lo, hi))[0][3], [lo, hi], "the singular's comma and \"and\" is the list of both numbers")
        self.assertEqual(rule.offences("%s %s %d, and %d" % (M, R, lo, hi), SET), [], "and over ruled rounds it is clean")
        self.assertEqual(rule.offences("%s %s %d, and the next" % (M, R, hi), SET), [], "a comma and \"and\" with no number after it is prose, not a list")
        for s in ("%s %s %d, or %d" % (M, R, lo, hi), "%s %d, & %d" % (R, lo, hi), "%s %d, / %d" % (R, lo, hi), "%s %d; and %d" % (R, lo, hi)):
            with self.subTest(singular_comma=s):
                self.assertEqual([k for _, _, k, _ in rule.forms(s)], ["unclassifiable"], "a singular's comma followed by a list word but \"and\" is refused: %r" % (s,))
                self.assertIn("a further number after a run the list did not consume", rule.offences(s, SET)[0][3])
        # "and/or" between two numbers is no list word: the number after it is refused as one the list did not consume, after the
        # word and before it, in digits and in words, as the singular's comma followed by "or" is, never read in part or as a list;
        # the same with a space on either side of the slash or on both, each side with a probe of its own after the word and before it
        for s, why in (("%s %s %d and/or %d" % (M, R, lo, hi), "a further number after a run"), ("%s %s and/or %s" % (R, WORDS[lo], WORDS[hi]), "a further number after a run"),
                       ("%s %d or/and %d" % (R, lo, hi), "a further number after a run"), ("%ss %d and/or %d" % (R, lo, hi), "a further number after a run"),
                       ("the %s and/or %s %s" % (nth(hi), nth(lo), R), "a further number before the ordinals"),
                       ("%s %s and/or %s %s" % (M, NTH[hi], NTH[lo], R), "a further number before the ordinals"),
                       ("%s %s %d and / or %d" % (M, R, lo, hi), "a further number after a run"), ("%s %s and / or %s" % (R, WORDS[lo], WORDS[hi]), "a further number after a run"),
                       ("%s %d and/ or %d" % (R, lo, hi), "a further number after a run"), ("%s %s %s or /and %s" % (M, R, WORDS[lo], WORDS[hi]), "a further number after a run"),
                       ("the %s and / or %s %s" % (nth(hi), nth(lo), R), "a further number before the ordinals"),
                       ("%s %s and / or %s %s" % (M, NTH[hi], NTH[lo], R), "a further number before the ordinals"),
                       ("the %s and /or %s %s" % (nth(hi), nth(lo), R), "a further number before the ordinals"),
                       ("%s %s or/ and %s %s" % (M, NTH[hi], NTH[lo], R), "a further number before the ordinals")):
            with self.subTest(and_or=s):
                self.assertEqual([k for _, _, k, _ in rule.forms(s)], ["unclassifiable"], "a number after \"and/or\" is refused, never read in part or as a list: %r" % (s,))
                self.assertIn(why, rule.offences(s, SET)[0][3], s)
        # the READ direction, number words after the word: read into their values, or refused when the reader cannot place them
        for s, nums in (("%s %s %s" % (M, R, WORDS[hi + 1]), [hi + 1]), ("%s %s %s" % (V, R, WORDS[hi + 1]), [hi + 1]), ("%ss %s and %s" % (R, WORDS[lo], WORDS[hi + 1]), [lo, hi + 1]),
                        ("%s %ss %s to %s" % (M, R, WORDS[hi - 1], WORDS[hi + 1]), [hi - 1, hi, hi + 1]), ("%ss %s and %d" % (R, WORDS[lo], hi + 1), [lo, hi + 1]),
                        ("%s %s" % (R.capitalize(), WORDS[hi + 1].upper()), [hi + 1]), ("%s %s-%s" % (R, "twenty", WORDS[1]), [21]), ("%s %s" % (R, "ninety"), [90]),
                        ("%s %s, and %s" % (R, WORDS[lo], WORDS[hi + 1]), [lo, hi + 1])):
            with self.subTest(read_word=s):
                self.assertEqual([(k, n) for _, _, k, n in rule.forms(s)], [("numbered", nums)], "a number word after the word is read into its value: %r" % (s,))
                self.assertIn("no ruling exists for a round numbered %d" % max(nums), rule.offences(s, SET)[0][3], "and judged: %r" % (s,))
        self.assertIn("a round credited to the author", rule.offences("%s %s %s" % (A, R, WORDS[lo]), SET)[0][3], "the author's round in words is the author's")
        self.assertEqual([c[2] for c in rule.credits("%s %s %s" % (A, R, WORDS[lo]))], ["author"])
        self.assertEqual(rule.offences("%s %ss %s and %s" % (M, R, WORDS[lo], WORDS[hi]), SET), [], "a list in words over ruled rounds is clean")
        self.assertEqual(rule.offences("%s %s %d found %s defects" % (M, R, hi, WORDS[hi + 1]), SET), [], "a digit form beside a number word elsewhere is clean")
        self.assertEqual(rule.offences("the %s pass %s" % (M[4:], WORDS[hi]), SET)[0][3].split(":")[0], "a pass credited to the maintainer", "a pass numbered in words is read")
        # the continuation in any letter case: a number word, a list word and a range word capitalised or in capitals, a range still
        # expanded, so over GAPPED a capitalised range across the hole names the hole
        for s, nums in (("%s %ss %s and %s" % (M, R, WORDS[lo].capitalize(), WORDS[hi].capitalize()), [lo, hi]), ("%s %ss %d AND %d" % (M, R, lo, hi), [lo, hi]),
                        ("%s %ss %s, %s" % (M, R, WORDS[lo].capitalize(), WORDS[hi].upper()), [lo, hi])):
            with self.subTest(case_list=s):
                self.assertEqual([(k, n) for _, _, k, n in rule.forms(s)], [("numbered", nums)], "a list in any letter case is read: %r" % (s,))
                self.assertEqual(rule.offences(s, SET), [], "and over ruled rounds it is clean: %r" % (s,))
        for s in ("%s %ss %d Through %d" % (M, R, 1, 5), "%s %ss %s Through %s" % (M, R, WORDS[1].capitalize(), WORDS[5].capitalize()), "%s %ss %d TO %d" % (M, R, 1, 5),
                  "%s %ss %s Thru %s" % (M, R, WORDS[1].capitalize(), WORDS[5].capitalize())):
            with self.subTest(case_range=s):
                self.assertEqual([o[3].split(":")[0] for o in rule.offences(s, GAPPED)], ["no ruling exists for a round numbered 2"], "a range in any letter case is expanded, naming the hole: %r" % (s,))
        for s, why in (("%s %s %s" % (R, WORDS[lo], "hundred"), "a further number after a run"), ("%s %s" % (R, "thousand"), "a number word the rule does not read, after the word"),
                       ("%s %s" % (R, NTH[hi]), "a number word the rule does not read, after the word"), ("%s\n    # %s" % (R, NTH[hi]), "a number word the rule does not read, after the word"),
                       ("%s: %s" % (R, WORDS[hi]), "punctuation or markup between the word and a number"), ("%s (%s)" % (R, NTH[hi]), "punctuation or markup between the word and a number"),
                       ("%s %d, %s" % (R, hi, WORDS[lo]), "a further number after a run"), ("%s %s, %s" % (R, WORDS[lo], WORDS[hi]), "a further number after a run"),
                       ("%s %s %s" % (R, "twenty", WORDS[1]), "a further number after a run"), ("%s %s, or %s" % (R, WORDS[lo], WORDS[hi]), "a further number after a run"),
                       ("%s %s_x" % (R, WORDS[hi]), "a number glued to a letter or an underscore"), ("%ss %s" % (R, WORDS[hi]), "a plural that names one number"),
                       ("%ss %s-%s" % (R, WORDS[hi], WORDS[lo]), "a range that does not ascend")):
            with self.subTest(unplaced_word=s):
                self.assertEqual([k for _, _, k, _ in rule.forms(s)], ["unclassifiable"], "a number word the reader cannot place is refused: %r" % (s,))
                self.assertIn(why, rule.offences(s, SET)[0][3], s)
        # the READ direction, ordinals before the word: read whether credited or not, into lists and ranges (the singular's list, its
        # comma followed by "and" and its range among them, in words and in digits), or refused when unplaced
        for s, party, nums in (("%s %s %s fixed it" % (A, NTH[3], R), "author", [3]), ("%s %s %s" % (A, nth(3), R), "author", [3]),
                               ("%s %s %s found it" % (M, NTH[hi + 1], R), "reviewer", [hi + 1]), ("%s %s %s" % (V, nth(9), R), "reviewer", [9]),
                               ("in its %s %s" % (NTH[hi + 1], R), "reviewer", [hi + 1]), ("the %s and %s %ss" % (NTH[lo], NTH[hi + 1], R), "reviewer", [lo, hi + 1]),
                               ("%s %s, %s, and %s %ss" % (M, NTH[lo], NTH[hi], NTH[hi + 1], R), "reviewer", [lo, hi, hi + 1]),
                               ("the %s to %s %ss" % (nth(hi - 1), nth(hi + 1), R), "reviewer", [hi - 1, hi, hi + 1]), ("the %s-%s %s" % ("twenty", NTH[1], R), "reviewer", [21]),
                               ("the %s %s" % ("twentieth", R), "reviewer", [20]), ("%s %s" % (NTH[hi + 1].capitalize(), R.capitalize()), "reviewer", [hi + 1]), ("the %s and %s-%s %ss" % (NTH[lo], "twenty", NTH[1], R), "reviewer", [lo, 21]), ("%s review %s %s" % (A, NTH[lo], R), "author", [lo]), ("%s %s review %s" % (A, NTH[lo], R), "author", [lo]),
                               ("the %s and %s %s" % (NTH[lo], NTH[hi + 1], R), "reviewer", [lo, hi + 1]), ("the %s and %s %s" % (nth(lo), nth(hi + 1), R), "reviewer", [lo, hi + 1]),
                               ("the %s, and %s %s" % (NTH[lo], NTH[hi + 1], R), "reviewer", [lo, hi + 1]), ("the %s, and %s %s" % (nth(lo), nth(hi + 1), R), "reviewer", [lo, hi + 1]),
                               ("the %s to %s %s" % (NTH[hi - 1], NTH[hi + 1], R), "reviewer", [hi - 1, hi, hi + 1]),
                               ("the %s to %s %s" % (nth(hi - 1), nth(hi + 1), R), "reviewer", [hi - 1, hi, hi + 1])):
            with self.subTest(read_ordinal=s):
                self.assertEqual([(k, n) for _, _, k, n in rule.forms(s)], [("numbered", nums)], "an ordinal before the word is read into its value: %r" % (s,))
                self.assertEqual([c[2] for c in rule.credits(s)], [party], "and credited to the party its qualifier names, or the reviewer by default: %r" % (s,))
                self.assertIn("a round credited to the author" if party == "author" else "no ruling exists for a round numbered %d" % max(nums), rule.offences(s, SET)[0][3], s)
        self.assertIn(rule.DEFAULT, rule.offences("in its %s %s" % (NTH[hi + 1], R), SET)[0][3], "an unqualified ordinal past the set is refused under the default, which the reason states")
        for s in ("%s %s %s" % (M, NTH[hi], R), "%s %s %s" % (V, nth(lo), R), "in its %s %s" % (NTH[hi], R), "%s %s and %s %ss" % (M, NTH[lo], NTH[hi], R),
                  "%s review %s %s" % (M, NTH[hi], R), "%s %s %s, %s" % (M, NTH[hi], R, D), "%s %s %s %s" % (M, NTH[hi], R, D), "a %s %s of 3 drives" % (NTH[lo], R),
                  "often %s %s" % (NTH[hi], R)):
            with self.subTest(ruled_ordinal=s):
                self.assertEqual(rule.offences(s, SET), [], "an ordinal at a ruled round is clean: %r" % (s,))
                self.assertEqual(len(rule.mentions(s)), 1, s)
        for s, why in (("the %s %ss" % (NTH[hi], R), "a plural that names one number"), ("the %s, %s %s" % (NTH[lo], NTH[hi], R), "a further number before the ordinals"),
                       ("the %s, %s %s" % (nth(lo), nth(hi), R), "a further number before the ordinals"),
                       ("the %s to %s %s" % (NTH[hi], NTH[lo], R), "a range that does not ascend"), ("the %s to %s %s" % (nth(hi), nth(lo), R), "a range that does not ascend"),
                       ("the %s %s %s" % ("twenty", NTH[1], R), "a further number before the ordinals"), ("one %s and %s %s" % ("hundred", NTH[1], R), "a further number before the ordinals"),
                       ("pass %d, %s %s" % (hi, NTH[hi], R), "a further number before the ordinals"),
                       ("one %s-%s %s" % ("hundred", NTH[hi], R), "a further number before the ordinals"), ("the %s %s %d" % (NTH[hi], R, hi), "a number both before the word and after it"),
                       ("the %s %s" % ("hundredth", R), "a number word the rule does not read, before the word"),
                       ("the %s %s, %d findings" % (NTH[hi], R, hi), "a further number after a run"), ("the %s to %s %ss" % (NTH[hi], NTH[lo], R), "a range that does not ascend")):
            with self.subTest(unplaced_ordinal=s):
                self.assertEqual([k for _, _, k, _ in rule.forms(s)], ["unclassifiable"], "an ordinal the reader cannot place is refused: %r" % (s,))
                self.assertIn(why, rule.offences(s, SET)[0][3], s)
        # the READ direction, punctuation or markup between an ordinal and the word, the mirror of the same after the word: refused,
        # credited or not, a LARGE ordinal and "review" after the run among them; not read before another word the word begins, or after
        # the end of another word
        for s in ("%s *%s* %s" % (A, NTH[3], R), "%s `%s` %s" % (A, nth(3), R), "%s %s (review) %s" % (M, NTH[hi + 2], R), "%s **%s** %s" % (V, nth(lo), R),
                  "the %s, %s" % (NTH[hi], R), "the %s: %s" % (nth(hi), R), "in its (%s) %s" % (NTH[lo], R), "the *%s* %s" % ("hundredth", R), "the %s review* %s" % (NTH[hi], R),
                  "the %s *review* %s" % (NTH[hi], R), "the *%s* %ss" % (NTH[hi], R)):
            with self.subTest(markup_ordinal=s):
                self.assertEqual([k for _, _, k, _ in rule.forms(s)], ["unclassifiable"], "punctuation or markup between an ordinal and the word is refused: %r" % (s,))
                self.assertIn("punctuation or markup between an ordinal and the word", rule.offences(s, SET)[0][3], s)
        for s in ("a *%s* %s-trip" % (NTH[lo], R), "the `%s` %sed corner" % (NTH[hi], R), "the (%s) %ssman" % (NTH[hi], R), "a milli%s, %s trip" % (NTH[2], R)):
            with self.subTest(markup_not_read=s):
                self.assertEqual(rule.offences(s, SET), [], "markup before another word the word begins, or after the end of another word, is not read: %r" % (s,))
                self.assertEqual([k for _, _, k, _ in rule.forms(s)], ["unnumbered"], s)
        # the short run's stated bound, six characters, at the bound in digits and in words: punctuation or markup of six characters
        # between the word and a number, between an ordinal and the word, and after "review" between an ordinal and the word, each
        # refused, each label naming the mutant that cuts its bound to five characters
        run6 = " : ** "
        self.assertEqual(len(run6), 6, "the probes' run sits at the bound")
        for spell, (num, o) in SPELLINGS.items():
            for label, s, why in (("six characters between the word and a number (GAP_NUMBER's run cut from six characters)",
                                   "%s%s%s" % (R, run6, num(hi)), "punctuation or markup between the word and a number"),
                                  ("six characters between an ordinal and the word (MARKUP_BEFORE's run cut from six characters)",
                                   "the %s%s%s" % (o(hi), run6, R), "punctuation or markup between an ordinal and the word"),
                                  ("six characters after \"review\" between an ordinal and the word (MARKUP_BEFORE's run after \"review\" cut from six characters)",
                                   "the %s review%s%s" % (o(hi), run6, R), "punctuation or markup between an ordinal and the word")):
                with self.subTest(short_run_bound=label, spelling=spell):
                    self.assertEqual([k for _, _, k, _ in rule.forms(s)], ["unclassifiable"], "a run at the short run's bound is refused: %r" % (s,))
                    self.assertIn(why, rule.offences(s, SET)[0][3], s)
        # the other side of that bound, an unnumbered form the docstring names: a run of seven characters, or a run within six that
        # crosses a line break, in the same three places and in digits and in words, each not read, each label naming the mutant that
        # widens its run to seven characters or lets it cross a line break
        run7, run_nl = " : **  ", " :\n  "
        self.assertEqual(len(run7), 7, "the probes' run sits one past the bound")
        self.assertTrue("\n" in run_nl and len(run_nl) <= 6, "the run crosses a line break within six characters, so the line break alone keeps it unread")
        for spell, (num, o) in SPELLINGS.items():
            for run, past, mutant in ((run7, "seven characters", "widened to seven characters"), (run_nl, "a run across a line break", "allowed to cross a line break")):
                for label, s in (("%s between the word and a number, not read (GAP_NUMBER's run %s)" % (past, mutant), "%s%s%s" % (R, run, num(hi))),
                                 ("%s between an ordinal and the word, not read (MARKUP_BEFORE's run %s)" % (past, mutant), "the %s%s%s" % (o(hi), run, R)),
                                 ("%s after \"review\" between an ordinal and the word, not read (MARKUP_BEFORE's run after \"review\" %s)" % (past, mutant),
                                  "the %s review%s%s" % (o(hi), run, R))):
                    with self.subTest(short_run_unread=label, spelling=spell):
                        self.assertEqual([k for _, _, k, _ in rule.forms(s)], ["unnumbered"], "a run past the short run's bound is not read: %r" % (s,))
                        self.assertEqual(rule.offences(s, SET), [], "and it refuses nothing: %r" % (s,))
        # a number word glued to the list word or the range word before it, or a digit ordinal glued to the letter after it, is no
        # number: in a plural the one number left is refused as a plural that names one number, never read as a list or a range of two
        for s in ("%s %ss %d and%s" % (M, R, lo, WORDS[hi]), "%ss %d and%s" % (R, hi - 1, WORDS[hi + 1]), "%s %ss %d or%s" % (V, R, lo, WORDS[hi]),
                  "%ss %d to%s" % (R, lo, WORDS[hi]), "%s %ss %s and%s" % (M, R, WORDS[lo], WORDS[hi]),
                  "the %sand %s %ss" % (nth(lo), nth(lo + 1), R), "%s %sand %s %ss" % (A, nth(lo), nth(lo + 1), R), "%s %sor %s %ss" % (M, nth(lo), nth(hi), R),
                  "the %sto %s %ss" % (nth(lo), nth(lo + 2), R)):
            with self.subTest(glued=s):
                self.assertEqual([k for _, _, k, _ in rule.forms(s)], ["unclassifiable"], "a glued word is no number, so this plural names one number and is refused, never read as a list: %r" % (s,))
                self.assertIn("a plural that names one number", rule.offences(s, SET)[0][3], s)

    def test_every_number_word_the_reader_knows(self):
        """Every number from zero to ninety-nine, spelled by this module's own tables (card() and ordinal(), never the helper's):
        as a cardinal word after the word and as an ordinal word before it, alone and as the second number of a list, each read
        into its value; alone, clean under a caller set that holds it and refused naming it under one that does not; and the
        author's credit in either spelling refused as the author's. Then each large word (hundred, thousand, million and billion)
        and each of their ordinals, which the reader does not read, each refused with its reason: the word after the word, and
        after a number the reader read; the ordinal after the word, and before it with the separator or "review" between, credited
        or not; while a large cardinal before the word is a count and is not read."""
        wrong = []
        for x in range(100):
            for text, nums in (("%s %s" % (R, card(x)), [x]), ("%ss %s and %s" % (R, WORDS[1], card(x)), [1, x]), ("the %s %s" % (ordinal(x), R), [x]),
                               ("the %s and %s %ss" % (NTH[1], ordinal(x), R), [1, x])):
                got = [(k, n) for _, _, k, n in rule.forms(text)]
                if got != [("numbered", nums)]:
                    wrong.append((text, "read as %r" % (got,)))
            for text in ("%s %s" % (R, card(x)), "the %s %s" % (ordinal(x), R)):
                if rule.offences(text, frozenset({x})):
                    wrong.append((text, "refused under a set that holds %d" % x))
                why = [o[3].split(":")[0] for o in rule.offences(text, frozenset({x + 1}))]
                if why != ["no ruling exists for a round numbered %d" % x]:
                    wrong.append((text, "under a set without %d: %r" % (x, why)))
            for text in ("%s %s %s" % (A, R, card(x)), "%s %s %s" % (A, ordinal(x), R)):
                why = [o[3].split(":")[0] for o in rule.offences(text, frozenset({x}))]
                if why != ["a round credited to the author"]:
                    wrong.append((text, "the author's credit: %r" % (why,)))
        self.assertEqual(wrong, [], "a number word from zero to ninety-nine the reader does not read into its value, or does not judge")
        after, before = "a number word the rule does not read, after the word", "a number word the rule does not read, before the word"
        for big, big_nth in zip(BIG, BIG_NTH):
            for text, why in (("%s %s" % (R, big), after), ("%s %s %s" % (R, WORDS[1], big), "a further number after a run the list did not consume"),
                              ("%s %s" % (R, big_nth), after), ("the %s %s" % (big_nth, R), before), ("the %s review %s" % (big_nth, R), before),
                              ("%s %s %s" % (M, big_nth, R), before), ("%s %s review %s" % (A, big_nth, R), before)):
                with self.subTest(large=text):
                    self.assertEqual([k for _, _, k, _ in rule.forms(text)], ["unclassifiable"], "a large number word beside the word is refused: %r" % (text,))
                    self.assertIn(why, rule.offences(text, SET)[0][3], text)
            with self.subTest(large_count=big):
                self.assertEqual(rule.offences("a %s %ss" % (big, R), SET), [], "a large cardinal before the word is a count, not read")
                self.assertEqual([k for _, _, k, _ in rule.forms("a %s %ss" % (big, R))], ["unnumbered"])

    def test_a_list_wrapped_across_a_comment_line_break(self):
        """The WRAP a list or a range takes across a comment line break (the coordinator's ruling of 2026-09-30 on PR 857's review;
        the rule's docstring states it): spaces, one newline, then optional indentation and a comment marker, and spaces. Under
        each marker (`#`, `//` and a block comment's `*`), in digits and in words, a list or a range wrapped between two of its
        numbers is READ whole, after the word and before it, the wrap after the list word, the range word or the comma or before
        it, the plural's bare comma and the singular's comma and "and" among them; a further number past the wrap beside a LINK
        (a comma, "and/or", "or", "&", "/", a hyphen or an en dash) that the list did not consume is REFUSED as it is on one line,
        after the list and before an ordinal run, the link ending the first line (a second link, or up to three characters,
        starting the next) or starting the next (the links other than the comma and "and/or" after the word in words alone,
        since a digit ordinal there is read as a number glued to a letter; a range mark starting the next line is a bullet,
        below); a line break with no link beside it joins nothing and refuses nothing ("round N" then "M tests" on the next line
        reads N alone, and so does a number then an ordinal run on the next line), nor does a sentence's end before the wrap
        ("round N." then "- M items", or then "And M tests") or a comment opener after it ("/* M tests */", "// M tests"); a range
        mark, a hyphen or an en dash, opening the next line after the comment marker, or with no marker, is a BULLET and joins
        nothing: what follows it is neither read nor refused, after the word, after a plural list and before an ordinal run (after
        a number and after an ordinal), and a date after it is no date of the form, so a further number after that date is not
        refused either; a range mark that ends the first line still joins, the range read whole after the word and before it and a
        date after it the date form; a comma that ends the first line joins across a bullet on the next as it does across a bare
        wrap, and the number is refused; a date wrapped beside its comma is the date form, and a further number
        after it is refused; a CRLF line end reads as a newline (the rule's docstring counts a carriage return before a newline as a
        space). Then each width the rule's docstring states for the refusal runs and the date, probed at its bound in digits and in
        words: across the wrap, six characters before a link that ends the first line, three after it on its line, three after the
        wrap or after a second link (in punctuation or in letters), the spaces before a wrap that precedes the link, and three after
        that link (in punctuation or in letters), each refused after the word and before an ordinal run, and the date's own widths
        read as the date form; on one line, six characters between the two numbers or before a list word and three after it, refused,
        and six before a date, read as the date form; a date after a link spelled in letters is no date and its year is refused; and
        the two 400-character look-backs, the number before an ordinal run found 400 characters before it and an ordinal run that
        starts 400 characters before the word read whole. Each probe's label names the part it pins and the mutant that reds it: a
        join without the wrap (_NUMBERED's list group, CONTINUATION_TOKEN after the link, _ORDINAL_RUN, the comma joins of
        _CONTINUE); FURTHER or FORE without _WRAP_RUN, or _WRAP_RUN without one of its two arms or its second link; a marker dropped
        from _BREAK, a link from _MARK or the list words from _LINK; DATE without _DATE_WRAP; the run before a wrap that precedes the
        link widened past spaces; the slash guard dropped; _BREAK refusing a carriage return before its newline; a width of
        _WRAP_RUN, of _DATE_WRAP or of a one-line run cut by one character, or the spaces before a wrap that precedes the link
        removed; _DATE_WRAP taking the links spelled in letters; FORE's or before()'s window cut back from 400 characters; the
        bullet guard dropped from _NUMBERED's list, from _ORDINAL_RUN, from _WRAP_RUN's arm with the link second or from _DATE_WRAP's
        arm with the mark second, or widened to a range mark that ends the first line in _NUMBERED's list, in _ORDINAL_RUN, in
        _WRAP_RUN's arm with the link first or in _DATE_WRAP's arm with the mark first. A probe that must stay unread names the
        mutant that would read or refuse it."""
        hi, lo = max(SET), min(SET)
        marks = {"#": ("# ", "\n    # "), "//": ("// ", "\n    // "), "*": ("/* ", "\n * ")}
        after, before = "a further number after a run", "a further number before the ordinals"
        for mark, (lead, br) in marks.items():
            for spell, (num, o) in SPELLINGS.items():
                past = "no ruling exists for a round numbered %d" % (hi + 1)
                read = [("after the word, the wrap after the list word (_NUMBERED's list and CONTINUATION_TOKEN without the wrap after the link)",
                         "%s%s %s %s and%s%s found it" % (lead, M, R, num(lo), br, num(hi + 1)), [lo, hi + 1]),
                        ("after the word, the wrap before the list word (_NUMBERED's list without the wrap before the link)",
                         "%s%s %s%sand %s found it" % (lead, R, num(lo), br, num(hi + 1)), [lo, hi + 1]),
                        ("after the word, a range (_NUMBERED's list and CONTINUATION_TOKEN without the wrap after the link)",
                         "%s%s %s to%s%s" % (lead, R, num(hi - 1), br, num(hi + 1)), [hi - 1, hi, hi + 1]),
                        ("after the word, the plural (_NUMBERED's list and CONTINUATION_TOKEN without the wrap after the link)",
                         "%s%ss %s and%s%s" % (lead, R, num(lo), br, num(hi + 1)), [lo, hi + 1]),
                        ("after the word, the plural's bare comma (_NUMBERED's list and CONTINUATION_TOKEN without the wrap after the link)",
                         "%s%ss %s,%s%s" % (lead, R, num(lo), br, num(hi + 1)), [lo, hi + 1]),
                        ("after the word, the singular's comma and \"and\", the wrap between (_CONTINUE's singular comma join without the wrap)",
                         "%s%s %s,%sand %s" % (lead, R, num(lo), br, num(hi + 1)), [lo, hi + 1]),
                        ("after the word, the singular's comma and \"and\", the wrap after (_NUMBERED's list and CONTINUATION_TOKEN without the wrap after the link)",
                         "%s%s %s, and%s%s" % (lead, R, num(lo), br, num(hi + 1)), [lo, hi + 1]),
                        ("after the word, the plural's comma and a list word, the wrap between (_CONTINUE's plural comma join without the wrap)",
                         "%s%ss %s, %s,%sor %s" % (lead, R, num(lo), num(lo + 1), br, num(hi + 1)), [lo, lo + 1, hi + 1]),
                        ("before the word, the wrap after the list word (_ORDINAL_RUN and CONTINUATION_TOKEN without the wrap after the link)",
                         "%s%s %s and%s%s %s found it" % (lead, M, o(lo), br, o(hi + 1), R), [lo, hi + 1]),
                        ("before the word, the wrap before the list word (_ORDINAL_RUN without the wrap before the link)",
                         "%sthe %s%sand %s %s" % (lead, o(lo), br, o(hi + 1), R), [lo, hi + 1]),
                        ("before the word, a range (_ORDINAL_RUN and CONTINUATION_TOKEN without the wrap after the link)",
                         "%sthe %s to%s%s %s" % (lead, o(hi - 1), br, o(hi + 1), R), [hi - 1, hi, hi + 1]),
                        ("before the word, the plural's bare comma (_ORDINAL_RUN and CONTINUATION_TOKEN without the wrap after the link)",
                         "%sthe %s,%s%s %ss" % (lead, o(lo), br, o(hi + 1), R), [lo, hi + 1]),
                        ("before the word, the singular's comma and \"and\", the wrap between (_CONTINUE's singular comma join without the wrap)",
                         "%sthe %s,%sand %s %s" % (lead, o(lo), br, o(hi + 1), R), [lo, hi + 1])]
                for label, s, nums in read:
                    with self.subTest(wrap_read=label, mark=mark, spelling=spell):
                        self.assertEqual([(k, n) for _, _, k, n in rule.forms(s)], [("numbered", nums)], "a list or a range wrapped across a comment line break is read whole: %r" % (s,))
                        self.assertIn(past, rule.offences(s, SET)[0][3], "and every number of it judged: %r" % (s,))
                refused = [("after the word, the wrap after a bare comma (FURTHER without _WRAP_RUN, or without its arm with the link first)",
                            "%s%s %s,%s%s findings" % (lead, R, num(hi), br, num(hi + 1)), after),
                           ("after the word, the wrap before a bare comma (FURTHER without _WRAP_RUN, or without its arm with the link second)",
                            "%s%s %s%s, %s findings" % (lead, R, num(hi), br, num(hi + 1)), after),
                           ("after the word, the wrap after a bare comma and a mark starting the next line (the run after the wrap dropped from _WRAP_RUN's first arm)",
                            "%s%s %s,%s(%s findings" % (lead, R, num(hi), br, num(hi + 1)), after),
                           ("after the word, the wrap after \"and/or\" (FURTHER without _WRAP_RUN's arm with the link first, or _LINK without the list words)",
                            "%s%s %s and/or%s%s" % (lead, R, num(lo), br, num(hi)), after),
                           ("after the word, the wrap before \"and/or\" (FURTHER without _WRAP_RUN's arm with the link second, or _LINK without the list words)",
                            "%s%s %s%sand/or %s" % (lead, R, num(lo), br, num(hi)), after),
                           ("after the word, the singular's \", or\" then the wrap (FURTHER without _WRAP_RUN's arm with the link first, or _LINK without the list words)",
                            "%s%s %s, or%s%s" % (lead, R, num(lo), br, num(hi)), after),
                           ("after the word, the singular's comma, the wrap, then \"or\" (_WRAP_RUN without its second link)",
                            "%s%s %s,%sor %s" % (lead, R, num(lo), br, num(hi)), after),
                           ("before the word, the wrap after a bare comma (FORE without _WRAP_RUN, or without its arm with the link first)",
                            "%sthe %s,%s%s %s" % (lead, o(hi), br, o(lo), R), before),
                           ("before the word, the wrap before a bare comma (FORE without _WRAP_RUN, or without its arm with the link second)",
                            "%sthe %s%s, %s %s" % (lead, o(hi), br, o(lo), R), before),
                           ("before the word, the wrap after \"and/or\" (FORE without _WRAP_RUN's arm with the link first, or _LINK without the list words)",
                            "%sthe %s and/or%s%s %s" % (lead, o(hi), br, o(lo), R), before),
                           ("before the word, the wrap before \"and/or\" (FORE without _WRAP_RUN's arm with the link second, or _LINK without the list words)",
                            "%sthe %s%sand/or %s %s" % (lead, o(hi), br, o(lo), R), before),
                           ("before the word, a comma, the wrap, then \"or\" (_WRAP_RUN without its second link)",
                            "%sthe %s,%sor %s %s" % (lead, o(hi), br, o(lo), R), before),
                           ("a further number after a date wrapped after its comma, the refusal quoting past the date (DATE without _DATE_WRAP, or without its arm with the link first)",
                            "%s%s %s,%s%s, %s findings" % (lead, R, num(hi), br, D, num(hi + 1)), "%s, %s'" % (D, num(hi + 1)))]
                # the wrap after each link spelled in punctuation, and before "&" and a slash: a range mark (a hyphen or an en dash)
                # opening the next line is a bullet and joins nothing, so the wrap before a range mark is probed below as a bullet
                for m, name in (("&", "&"), ("/", "a slash"), ("-", "a hyphen"), ("\u2013", "an en dash")):
                    widened = ", or the bullet guard widened to a range mark that ends the first line" if m in "-\u2013" else ""
                    if spell == "words":
                        refused += [("after the word, the wrap after %s (FURTHER without _WRAP_RUN's arm with the link first, or _MARK without it%s)" % (name, widened),
                                     "%s%s %s %s%s%s" % (lead, R, num(lo), m, br, o(hi)), after)]
                        if not widened:
                            refused += [("after the word, the wrap before %s (FURTHER without _WRAP_RUN's arm with the link second, or _MARK without it)" % name,
                                         "%s%s %s%s%s %s" % (lead, R, num(lo), br, m, o(hi)), after)]
                    refused += [("before the word, the wrap after %s (FORE without _WRAP_RUN's arm with the link first, or _MARK without it%s)" % (name, widened),
                                 "%s%s %s%s%s %s" % (lead, num(lo), m, br, o(hi), R), before)]
                    if not widened:
                        refused += [("before the word, the wrap before %s (FORE without _WRAP_RUN's arm with the link second, or _MARK without it)" % name,
                                     "%s%s%s%s %s %s" % (lead, num(lo), br, m, o(hi), R), before)]
                refused += [("after the word, a comma that ends the first line, then a bullet: the comma joins (_WRAP_RUN without its arm with the link first)",
                             "%s%s %s,%s- %s findings" % (lead, R, num(hi), br, num(hi + 1)), after),
                            ("before the word, a comma that ends the first line, then a bullet: the comma joins (_WRAP_RUN without its arm with the link first)",
                             "%sthe %s,%s- %s %s" % (lead, o(hi), br, o(lo), R), before)]
                for label, s, why in refused:
                    with self.subTest(wrap_refused=label, mark=mark, spelling=spell):
                        self.assertEqual([k for _, _, k, _ in rule.forms(s)], ["unclassifiable"], "a further number past the wrap beside a link is refused as on one line: %r" % (s,))
                        self.assertIn(why, rule.offences(s, SET)[0][3], s)
                unread = [("after the word, a line break with no link (reds under a join taking a wrap with no link, or FURTHER taking a bare wrap)",
                           "%s%s %s%s%s tests" % (lead, R, num(hi), br, num(hi + 1)), [hi]),
                          ("before the word, a line break with no link (reds under FORE taking a bare wrap)",
                           "%swe ran %s%s%s %s" % (lead, num(hi + 1), br, o(hi), R), [hi]),
                          ("after the word, a date wrapped after its comma (DATE without _DATE_WRAP, or without its arm with the link first)",
                           "%s%s %s,%s%s" % (lead, R, num(hi), br, D), [hi]),
                          ("after the word, a date wrapped after its comma, a mark starting the next line (the run after the wrap dropped from _DATE_WRAP's first arm)",
                           "%s%s %s,%s(%s" % (lead, R, num(hi), br, D), [hi]),
                          ("after the word, a date wrapped before its comma (DATE without _DATE_WRAP, or without its arm with the link second)",
                           "%s%s %s%s, %s" % (lead, R, num(hi), br, D), [hi])]
                for label, s, nums in unread:
                    with self.subTest(wrap_unread=label, mark=mark, spelling=spell):
                        self.assertEqual([(k, n) for _, _, k, n in rule.forms(s)], [("numbered", nums)], "what follows a line break with no link beside it is not read: %r" % (s,))
                        self.assertEqual(rule.offences(s, SET), [], s)
                # a range mark, a hyphen or an en dash, opening the next line after the comment marker is a BULLET and joins nothing, as
                # a bare line break joins nothing: what follows it is neither read nor refused, after the word and before it, and a date
                # after it is no date of the form; a range mark that ends the first line still joins, the range read whole and the date
                # after it the date form
                for m, name in (("-", "a hyphen"), ("\u2013", "an en dash")):
                    bullets = [("after the word, a bullet, %s opening the next line (the bullet guard dropped from _NUMBERED's list, or from _WRAP_RUN's arm with the link second)" % name,
                                "%s%s %s%s%s %s items" % (lead, R, num(hi - 1), br, m, num(hi + 1)), [hi - 1]),
                               ("after a plural list, a bullet, %s opening the next line (the bullet guard dropped from _NUMBERED's list, or from _WRAP_RUN's arm with the link second)" % name,
                                "%s%ss %s and %s%s%s %s items" % (lead, R, num(lo), num(hi - 1), br, m, num(hi + 1)), [lo, hi - 1]),
                               ("before the word, a number, then a bullet, %s opening the next line (the bullet guard dropped from _WRAP_RUN's arm with the link second)" % name,
                                "%swe ran %s%s%s %s %s" % (lead, num(hi + 1), br, m, o(hi), R), [hi]),
                               ("before the word, an ordinal, then a bullet, %s opening the next line (the bullet guard dropped from _ORDINAL_RUN, or from _WRAP_RUN's arm with the link second)" % name,
                                "%sthe %s%s%s %s %s" % (lead, o(hi + 1), br, m, o(hi), R), [hi]),
                               ("after the word, a bullet, %s opening the next line, then a date and a number (the bullet guard dropped from _DATE_WRAP's arm with the mark second, or from _WRAP_RUN's arm with the link second)" % name,
                                "%s%s %s%s%s %s, %s findings" % (lead, R, num(hi), br, m, D, num(hi + 1)), [hi])]
                    for label, s, nums in bullets:
                        with self.subTest(wrap_bullet=label, mark=mark, spelling=spell):
                            self.assertEqual([(k, n) for _, _, k, n in rule.forms(s)], [("numbered", nums)], "a bullet joins nothing: %r" % (s,))
                            self.assertEqual(rule.offences(s, SET), [], s)
                    ending = [("after the word, %s that ends the first line, a range read whole (the bullet guard widened to a range mark that ends the first line, in _NUMBERED's list)" % name,
                               "%s%s %s %s%s%s found it" % (lead, R, num(hi - 1), m, br, num(hi + 1)), [hi - 1, hi, hi + 1]),
                              ("before the word, %s that ends the first line, a range read whole (the bullet guard widened to a range mark that ends the first line, in _ORDINAL_RUN)" % name,
                               "%sthe %s %s%s%s %s" % (lead, o(hi - 1), m, br, o(hi + 1), R), [hi - 1, hi, hi + 1])]
                    for label, s, nums in ending:
                        with self.subTest(wrap_read=label, mark=mark, spelling=spell):
                            self.assertEqual([(k, n) for _, _, k, n in rule.forms(s)], [("numbered", nums)], "a range mark that ends the first line joins: %r" % (s,))
                            self.assertIn(past, rule.offences(s, SET)[0][3], "and every number of it judged: %r" % (s,))
                    with self.subTest(wrap_unread="after the word, %s that ends the first line, then a date: the date form (the bullet guard widened to a range mark that ends the first line, in _DATE_WRAP)" % name,
                                      mark=mark, spelling=spell):
                        s = "%s%s %s %s%s%s" % (lead, R, num(hi), m, br, D)
                        self.assertEqual([(k, n) for _, _, k, n in rule.forms(s)], [("numbered", [hi])], s)
                        self.assertEqual(rule.offences(s, SET), [], s)
        # the stated wrap's edges, in digits and in words: a sentence's end before the wrap and a comment opener after it join nothing;
        # a CRLF line end is a newline
        for spell, (num, o) in SPELLINGS.items():
            for label, s, nums in (("a sentence's end, then a bullet (_WRAP_RUN's run before a wrap that precedes the link widened past spaces, with its bullet guard dropped)",
                                    "%s %s %s.\n- %s items" % (M, R, num(hi), num(hi + 1)), [hi]),
                                   ("a sentence's end, then \"And\" (_WRAP_RUN's run before a wrap that precedes the link widened past spaces)",
                                    "%s %s %s.\n    # And %s tests" % (M, R, num(hi), num(hi + 1)), [hi]),
                                   ("a sentence's end, then a bullet, before an ordinal run (_WRAP_RUN's run before a wrap that precedes the link widened past spaces, with its bullet guard dropped)",
                                    "we ran %s.\n- %s %s" % (num(hi + 1), o(hi), R), [hi]),
                                   ("a comment opener `/*` after the line break (_MARK's slash guard dropped)",
                                    "%s %s\n    /* %s tests */" % (R, num(hi), num(hi + 1)), [hi]),
                                   ("a comment opener `//` after the line break (_MARK's slash guard dropped)",
                                    "%s %s\n    // %s tests" % (R, num(hi), num(hi + 1)), [hi]),
                                   ("a bullet with no comment marker, a hyphen opening the next line (the bullet guard dropped from _NUMBERED's list, or from _WRAP_RUN's arm with the link second)",
                                    "%s %s %s\n- %s items" % (M, R, num(hi - 1), num(hi + 1)), [hi - 1]),
                                   ("a bullet with no comment marker, an en dash opening the next line, before an ordinal run (the bullet guard dropped from _ORDINAL_RUN, or from _WRAP_RUN's arm with the link second)",
                                    "the %s\n\u2013 %s %s" % (o(hi + 1), o(hi), R), [hi])):
                with self.subTest(wrap_edge=label, spelling=spell):
                    self.assertEqual([(k, n) for _, _, k, n in rule.forms(s)], [("numbered", nums)], s)
                    self.assertEqual(rule.offences(s, SET), [], s)
            with self.subTest(wrap_edge="a CRLF line end, read (_BREAK refusing a carriage return before its newline)", spelling=spell):
                s = "# %s %s and\r\n# %s" % (R, num(lo), num(hi + 1))
                self.assertEqual([(k, n) for _, _, k, n in rule.forms(s)], [("numbered", [lo, hi + 1])], s)
            with self.subTest(wrap_edge="a CRLF line end, refused (_BREAK refusing a carriage return before its newline)", spelling=spell):
                s = "# %s %s,\r\n# %s findings" % (R, num(hi), num(hi + 1))
                self.assertIn(after, rule.offences(s, SET)[0][3], s)
        # the widths the rule's docstring states for the refusal runs and the date, each probed at its bound, in digits and in words: a
        # number past a run at the bound is refused, after the word and before an ordinal run; a date past it is the date form; a date
        # after a link spelled in letters is no date; and the two 400-character look-backs, each probe placed at exactly 400. Each
        # label names the mutant that narrows its bound by one character (or removes the spaces a wrap before a link takes)
        run6 = " ) ); "                                   # six characters of punctuation and spaces, none of them a link
        for spell, (num, o) in SPELLINGS.items():
            bounds = [("across the wrap, six characters before a link that ends the first line (_WRAP_RUN's run before that link cut from six characters)",
                       "# %s %s%s,\n    # %s findings" % (R, num(hi), run6, num(hi + 1)), "# the %s%s,\n    # %s %s" % (o(hi), run6, o(lo), R)),
                      ("across the wrap, three characters after a link that ends the first line, on its line (_WRAP_RUN's run after that link cut from three characters)",
                       "# %s %s,   \n    # %s findings" % (R, num(hi), num(hi + 1)), "# the %s,   \n    # %s %s" % (o(hi), o(lo), R)),
                      ("across the wrap, three characters after the wrap and no second link (_WRAP_RUN's run after the wrap cut from three characters)",
                       "# %s %s,\n    # (((%s findings" % (R, num(hi), num(hi + 1)), "# the %s,\n    # (((%s %s" % (o(hi), o(lo), R)),
                      ("across the wrap, a second link and three characters after it (_WRAP_RUN's run after the wrap cut from three characters)",
                       "# %s %s,\n    # - ((%s findings" % (R, num(hi), num(hi + 1)), "# the %s,\n    # - ((%s %s" % (o(hi), o(lo), R)),
                      ("across the wrap, a second link spelled in letters and three characters after it (_WRAP_RUN's run after the wrap cut from three characters)",
                       "# %s %s,\n    # or ((%s findings" % (R, num(hi), num(hi + 1)), "# the %s,\n    # or ((%s %s" % (o(hi), o(lo), R)),
                      ("across the wrap, spaces before a wrap that precedes the link (_WRAP_RUN's spaces before that wrap removed, or bounded to six)",
                       "# %s %s        \n    # , %s findings" % (R, num(hi), num(hi + 1)), "# the %s        \n    # , %s %s" % (o(hi), o(lo), R)),
                      ("across the wrap, a link that starts the next line and three characters after it (_WRAP_RUN's run after that link cut from three characters)",
                       "# %s %s\n    # , ((%s findings" % (R, num(hi), num(hi + 1)), "# the %s\n    # , ((%s %s" % (o(hi), o(lo), R)),
                      ("across the wrap, a link spelled in letters that starts the next line and three characters after it (_WRAP_RUN's run after that link cut from three characters)",
                       "# %s %s\n    # and/or ((%s" % (R, num(hi), num(hi + 1)), "# the %s\n    # and/or ((%s %s" % (o(hi), o(lo), R)),
                      ("on one line, six characters between the two numbers (FURTHER's or FORE's one-line run cut from six characters)",
                       "%s %s%s%s findings" % (R, num(hi), run6, num(hi + 1)), "the %s%s%s %s" % (o(hi), run6, o(lo), R)),
                      ("on one line, six characters before a list word (FURTHER's or FORE's one-line run cut from six characters)",
                       "%s %s%sand/or %s" % (R, num(lo), run6, num(hi)), "the %s%sand/or %s %s" % (o(hi), run6, o(lo), R)),
                      ("on one line, three characters after a list word (FURTHER's or FORE's one-line run after the list word cut from three characters)",
                       "%s %s and/or   %s" % (R, num(lo), num(hi)), "the %s and/or   %s %s" % (o(hi), o(lo), R))]
            for label, s_after, s_before in bounds:
                for place, s, why in (("after the word", s_after, after), ("before an ordinal run", s_before, before)):
                    with self.subTest(wrap_bound="%s, %s" % (label, place), spelling=spell):
                        self.assertEqual([k for _, _, k, _ in rule.forms(s)], ["unclassifiable"], "a number past a refusal run at its stated bound is refused: %r" % (s,))
                        self.assertIn(why, rule.offences(s, SET)[0][3], s)
            dates = [("across the wrap, six characters before a mark that ends the first line, then a date (_DATE_WRAP's run before that mark cut from six characters)",
                      "# %s %s%s,\n    # %s" % (R, num(hi), run6, D)),
                     ("across the wrap, three characters after a mark that ends the first line, then a date (_DATE_WRAP's run after that mark cut from three characters)",
                      "# %s %s,   \n    # %s" % (R, num(hi), D)),
                     ("across the wrap, three characters after the wrap, then a date (_DATE_WRAP's run after the wrap cut from three characters)",
                      "# %s %s,\n    # (((%s" % (R, num(hi), D)),
                     ("across the wrap, spaces before a wrap that precedes the mark, then a date (_DATE_WRAP's spaces before that wrap removed)",
                      "# %s %s        \n    # , %s" % (R, num(hi), D)),
                     ("across the wrap, a mark that starts the next line and three characters after it, then a date (_DATE_WRAP's run after that mark cut from three characters)",
                      "# %s %s\n    # , ((%s" % (R, num(hi), D)),
                     ("on one line, six characters, then a date (DATE's one-line run cut from six characters)", "%s %s%s%s" % (R, num(hi), run6, D))]
            for label, s in dates:
                with self.subTest(wrap_bound=label, spelling=spell):
                    self.assertEqual([(k, n) for _, _, k, n in rule.forms(s)], [("numbered", [hi])], "a date past a run at its stated bound is the date form: %r" % (s,))
                    self.assertEqual(rule.offences(s, SET), [], s)
            with self.subTest(wrap_bound="a link spelled in letters, the wrap, then a date: no date, its year refused (_DATE_WRAP taking the links spelled in letters)", spelling=spell):
                s = "# %s %s and\n    # %s" % (R, num(hi), D)
                self.assertEqual([k for _, _, k, _ in rule.forms(s)], ["unclassifiable"], s)
                self.assertIn("a further number after a run the list did not consume, and not a date", rule.offences(s, SET)[0][3], s)
            with self.subTest(wrap_bound="a number 400 characters before an ordinal run, a deep indentation between (FORE's window cut back from 400 characters)", spelling=spell):
                s = "# the %s,\n%s# %s %s" % (o(hi), " " * (396 - len(o(hi))), o(lo), R)
                self.assertEqual(s.index(o(lo) + " " + R) - s.index(o(hi)), 400, "the probe sits at the bound")
                self.assertIn(before, rule.offences(s, SET)[0][3], s)
            with self.subTest(wrap_bound="an ordinal run that starts 400 characters before the word, read whole (before()'s window cut back from 400 characters)", spelling=spell):
                s = "# the %s and\n%s# %s %s" % (o(lo), " " * (392 - len(o(lo)) - len(o(hi + 1))), o(hi + 1), R)
                self.assertEqual(s.index(R) - s.index(o(lo)), 400, "the probe sits at the bound")
                self.assertEqual([(k, n) for _, _, k, n in rule.forms(s)], [("numbered", [lo, hi + 1])], s)
                self.assertIn("no ruling exists for a round numbered %d" % (hi + 1), rule.offences(s, SET)[0][3], s)

    def test_the_credit_keys_on_misattribution(self):
        """The reviewer's ruling of 2026-09-21, each clause by execution under a synthetic set: (a) "the reviewer's round N" is a
        credit beside "the maintainer's round N", the apostrophe either; (b) a date after the round (", YYYY-MM-DD", "
        (YYYY-MM-DD", "), YYYY-MM-DD", the date straight after the number) is part of the form, after a list too, a malformed date
        is not one, and a further number after the date is still refused; (c) the unqualified "review round N", "Review round N"
        and the bare round, an unqualified ordinal before the word and a round numbered in words are the reviewer's by DEFAULT,
        credits() saying so with the stated reason, which names the convention and calls itself a default with a stated reason, and
        which the refusal of an unqualified round past the set carries while an explicit credit's does not (an explicit ordinal
        credit among them, the maintainer's and the reviewer's, in digits and in words, "review" on either side of the ordinal and
        a list too, whose credits() reason is None); (d) a round outside the
        caller's set is refused naming the number, the two things it can be and the caller's set, qualified or not; (e) a pass
        credited to the reviewer or the maintainer is refused naming the wrong party and the caller's author form, a list too, the
        apostrophe either, at its own line among the round offences, while an unnumbered pass and the author's pass are not read;
        (f) a round credited to the author is refused, "review" between the qualifier and the word too, a list too, an ordinal
        between the qualifier and the word and a number in words too, and an ordinal list there, with a bare comma or a serial
        comma, in words and in digits, while the author's pass beside the maintainer's round is
        clean; (g) a number the form did not consume that is not a date is still refused; (h) every unresolvable form is still
        refused with its reason, never passed, the READ direction's among them (punctuation before a number word, an ordinal after
        the word, the singular's comma followed by "or", a number before an ordinal run, a plural naming one ordinal, markup
        between an ordinal and the word)."""
        hi, lo = max(SET), min(SET)
        with self.subTest(clause="a: the reviewer's round is a credit"):
            self.assertEqual(rule.offences("%s %s %d" % (V, R, hi), SET), [], "the reviewer's round at a ruled round is clean")
            self.assertEqual(rule.credits("%s %s %d" % (V, R, hi)), [(1, "%s %d" % (R, hi), "reviewer", None)], "an explicit credit carries no default reason")
            self.assertEqual(rule.offences("the reviewer’s %s %d" % (R, hi), SET), [], "the typographic apostrophe reads the same")
            self.assertEqual(rule.offences("%s review %s %d" % (V, R, hi), SET), [], "\"review\" between the qualifier and the word is the same credit")
        with self.subTest(clause="b: a date after the round is part of the form"):
            for shape in (", %s", " (%s", "), %s", " %s", ",%s"):
                text = "Review %s %d%s" % (R, hi, shape % D)
                self.assertEqual(rule.offences(text, SET), [], "a dated round read as an offence: %r" % (text,))
                self.assertEqual([k for _, _, k, _ in rule.forms(text)], ["numbered"], "a dated round is one numbered form: %r" % (text,))
            self.assertEqual(rule.offences("%s %ss %d and %d, %s" % (M, R, lo, hi, D), SET), [], "a date after a plural list is part of the form, its year no number of the list")
            self.assertEqual(rule.forms("%ss %d and %d, %s" % (R, lo, hi, D))[0][3], [lo, hi], "the list's numbers stop before the date")
            o = rule.offences("Review %s %d, %s, %d findings" % (R, hi, D, hi + 1), SET)
            self.assertIn("not a date", o[0][3], "a further number after the date is refused as one the form did not consume")
            self.assertIn("cannot classify", rule.offences("Review %s %d, 2026-9-15" % (R, hi), SET)[0][3], "a malformed date is a further number, not a date")
        with self.subTest(clause="c: an unqualified round is the reviewer's by default, with the stated reason"):
            for text in ("review %s %d" % (R, hi), "Review %s %d" % (R, hi), "%s %d" % (R, lo), "%ss %d and %d" % (R, lo, hi), "the %s-%d head" % (R, hi), "Review %s %d fixes: a subject" % (R, hi),
                         "in its %s %s" % (NTH[hi], R), "%s %s" % (R, WORDS[lo])):
                self.assertEqual(rule.offences(text, SET), [], "an unqualified round at a ruled round read as an offence: %r" % (text,))
                self.assertEqual([c[2:] for c in rule.credits(text)], [("reviewer", rule.DEFAULT)], "the default and its reason are returned: %r" % (text,))
            self.assertIn("default", rule.DEFAULT)
            self.assertIn("stated reason", rule.DEFAULT)
            self.assertIn("convention", rule.DEFAULT)
            self.assertIn("rounds belong to the reviewer", rule.DEFAULT)
            self.assertIn("the author's work between them is a pass", rule.DEFAULT)
            for phrase in ("BY DEFAULT", "rounds belong to the reviewer", "the author's work between them is a pass", "by that convention", "a default with this stated reason", "not a guess"):
                self.assertIn(phrase, rule.__doc__, "the docstring states the default and its reason in the rule's own text: %r" % (phrase,))
            self.assertIn(rule.DEFAULT, rule.offences("review %s %d" % (R, hi + 1), SET)[0][3], "the refusal of an unqualified round past the set states the default it was read under")
            self.assertNotIn(rule.DEFAULT, rule.offences("%s %s %d" % (M, R, hi + 1), SET)[0][3], "an explicit credit's refusal carries no default")
            for text in ("%s %s %s" % (M, NTH[hi + 2], R), "%s %s %s" % (M, nth(hi + 2), R), "%s %s %s" % (V, NTH[hi + 3], R), "%s %s %s" % (V, nth(hi + 3), R),
                         "%s review %s %s" % (M, NTH[hi + 1], R), "%s %s review %s" % (V, nth(hi + 1), R), "%s %s and %s %ss" % (M, NTH[lo], NTH[hi + 1], R)):
                self.assertEqual([c[2:] for c in rule.credits(text)], [("reviewer", None)], "an explicit ordinal credit is the qualifier's, with no default reason: %r" % (text,))
                self.assertNotIn(rule.DEFAULT, rule.offences(text, SET)[0][3], "an explicit ordinal credit's refusal past the set carries no default: %r" % (text,))
        with self.subTest(clause="d: a round outside the caller's set is refused"):
            for text in ("review %s %d" % (R, hi + 1), "%s %s %d" % (M, R, hi + 1), "%s %s %d" % (V, R, hi + 1), "%s %d" % (R, hi + 1)):
                o = rule.offences(text, SET)
                self.assertEqual(len(o), 1, text)
                self.assertIn("no ruling exists for a round numbered %d" % (hi + 1), o[0][3], text)
                self.assertIn("an author's pass labelled a round, or a round not yet held", o[0][3], text)
                self.assertIn("the rulings the caller holds are numbered %s" % ", ".join(str(x) for x in sorted(SET)), o[0][3], text)
            self.assertEqual([o[2] for o in rule.offences("%s %s %d" % (V, R, 2), GAPPED)], ["%s %d" % (R, 2)], "the reviewer's credit at a hole in the set is refused")
        with self.subTest(clause="e: a pass credited to the reviewer or the maintainer is refused"):
            for who in ("maintainer", "reviewer"):
                o = rule.offences("the %s's pass %d" % (who, hi), SET, "tests/x.py", "\"the author's pass P\"")
                self.assertEqual([(x[0], x[1], x[2]) for x in o], [("tests/x.py", 1, "the %s's pass %d" % (who, hi))], who)
                self.assertIn("a pass credited to the %s" % who, o[0][3], "the wrong party is named")
                self.assertIn("\"the author's pass P\" for the author's own work", o[0][3], "the caller's author form is named")
            self.assertEqual(len(rule.offences("the maintainer's passes %d and %d" % (lo, hi), SET)), 1, "a list of passes credited to the maintainer is one offence")
            self.assertEqual(len(rule.offences("the maintainer’s pass %d" % hi, SET)), 1, "the typographic apostrophe reads the same")
            self.assertEqual(len(rule.offences("the\n    # reviewer's pass %d" % hi, SET)), 1, "the qualifier wrapped at a comment marker reads the same")
            self.assertEqual(rule.offences("the maintainer's pass over the tree", SET), [], "an unnumbered pass is not read")
            self.assertEqual(rule.offences("%s pass %d" % (A, hi), SET), [], "the author's pass is the author's")
            self.assertEqual([x[1] for x in rule.offences("a\nthe maintainer's pass %d\nreview %s %d\n" % (hi, R, hi + 1), SET)], [2, 3],
                             "a wrong-party pass before a round offence in the text comes before it in the offences: text order, not the order the passes are read in")
            self.assertEqual([x[1] for x in rule.offences("a\nreview %s %d\nthe maintainer's pass %d\n" % (R, hi + 1, hi), SET)], [2, 3], "and after it in the text, after it in the offences")
        with self.subTest(clause="f: a round credited to the author is refused"):
            for text in ("%s %s %d" % (A, R, lo), "%s review %s %d" % (A, R, lo), "%s %ss %d and %d" % (A, R, lo, hi), "the author’s %s %d" % (R, hi), "%s %s %d" % (A, R, hi + 1),
                         "%s %s %s" % (A, NTH[lo], R), "%s review %s %s" % (A, nth(hi), R), "the author’s %s %s" % (NTH[hi], R), "%s %s %s" % (A, R, WORDS[hi]),
                         "%s %s, %s %ss" % (A, NTH[lo], NTH[lo + 1], R), "%s %s, %s, and %s %ss" % (A, NTH[lo], NTH[lo + 1], NTH[hi], R), "%s %s, %s %ss" % (A, nth(lo), nth(hi), R),
                         "%s %s, %s, or %s %ss" % (A, nth(lo), nth(lo + 1), nth(hi), R)):
                o = rule.offences(text, SET)
                self.assertEqual(len(o), 1, text)
                self.assertIn("a round credited to the author", o[0][3], text)
                self.assertIn(rule.AUTHOR_FORM, o[0][3], "the caller's author form is named")
                self.assertEqual([c[2] for c in rule.credits(text)], ["author"], text)
            self.assertEqual(rule.offences("%s pass %d after %s %s %d" % (A, hi, M, R, hi), SET), [], "the author's pass beside the maintainer's round is clean")
        with self.subTest(clause="g: a number the form did not consume that is not a date"):
            o = rule.offences("%s %d), %d and %d" % (R, hi, 52, 260), SET)
            self.assertEqual(len(o), 1)
            self.assertIn("cannot classify", o[0][3])
            self.assertIn("not a date", o[0][3])
        with self.subTest(clause="h: the unresolvable forms still refuse"):
            for s in ("%s: %d" % (R, hi), "%s (%d)" % (R, hi), "%s **%d**" % (R, hi), "%s `%d`" % (R, hi), "%s %db" % (R, hi), "%ss %d" % (R, hi), "%ss %d-%d" % (R, hi, lo),
                      "%s %d, %d" % (R, lo, hi), "%s %s: %d" % (V, R, hi), "%s %s %d, %d findings" % (V, R, hi, hi + 1),
                      "%s: %s" % (R, WORDS[hi]), "%s %s" % (R, NTH[hi]), "%s %d, or %d" % (R, lo, hi), "the %s, %s %s" % (NTH[lo], NTH[hi], R), "the %s %ss" % (NTH[hi], R),
                      "%s `%s` %s" % (A, nth(lo), R), "%s %s (review) %s" % (M, NTH[hi], R)):
                self.assertEqual([k for _, _, k, _ in rule.forms(s)], ["unclassifiable"], "an unresolvable form passed or went unread: %r" % (s,))
                self.assertIn("cannot classify", rule.offences(s, SET)[0][3], s)


if __name__ == "__main__":
    unittest.main()
