#!/usr/bin/env python3
"""The link-drop lab family's comments credit a maintainer round only where a ruling exists (the author's pass 10, 2026-09-20;
rewritten in pass 11, 2026-09-21, to read nothing outside the repository: the maintainer's round 6).

Two numberings meet in the family's comments, docstrings and messages. The MAINTAINER's rounds on PR 857 are the rulings the
reviewer filed (the maintainer's rounds 1 to 6 at this writing); the AUTHOR's passes are the build-and-verify passes before,
between and after them, numbered 1 to 11 by the PR body's convention paragraph. Before pass 10 the tree said "round N" in the
author's pipeline's own numbering, which matched neither: one number named two passes (the pipeline's fifth round was pass 6
in the served module's expired-wait comments and pass 9 in the mint and parsed modules), the pipeline's "round-N head" named
the pass-3 head in one module and the pass-7 head in another, and 47 lines credited a sixth round no ruling then existed for.
The sweep derived every mention from the line's commit and its sentence: a ruling, a refuter's probe or a ruled head is "the
maintainer's round N" with N the ruling's number; the author's own work is "pass P", "pass P's fixer pass" or "the pass-P
head", the head after the author's pass P.

This module is the ratchet. A numbered round ("round N", "round-N", "Round N's", "round N of PR 857", "round #N", "rounds N
and M") is a credit to the maintainer, so it is refused unless spelled "the maintainer's round N" (or "the maintainer's rounds
N and M", every number of the list judged) with N in MAINTAINER_ROUNDS. MAINTAINER_ROUNDS is a constant of this TREE: the
rulings the maintainer had filed on PR 857 when this pass began, derived 2026-09-21, and the author raises it in the same
change that first credits a new round, so a credit to a round no ruling exists for reds on every machine until the ruling
exists and the constant says so. It is read from NOTHING outside the repository. The maintainer's round 6 found the earlier
module reading the reviewer's notes directory for the set, so the same committed tree got two verdicts (the set widened on
the one machine that holds the rulings and stayed at the constant everywhere else), and a verdict that depends on the machine
is no property of the repository; test_the_module_reads_nothing_outside_the_tree pins that over this module's own source (no
environment read, no home or absolute path, every file read joined on ROOT).

THE POPULATION is derived from the tree: the modules the glob FAMILY_GLOB names under this directory (the sibling pin's own
spelling, tests/test_federated_linkdrop_driver_bound.py's ledger pin; a family module named otherwise escapes both, so the
population is spelling-keyed and says so) plus the ledger entry ENTRY, read whole, since every line of them is the branch's
own. A cell reads the sibling pin's glob from that pin's source and runs it, holding the two populations equal, so a family
module the sibling sees and this census does not is a red; a glob that reads nothing, a missing entry or this module outside
its own population is a stated refusal, never an empty census.

THE FORM SPACE. offences() reads the WHOLE text of each file, so a mention wrapped across a line break (the qualifier ending one
line and the number starting the next, a comment marker between) is one mention, reported at the line its number sits on (a
wrapped credit in the driver-bound module was invisible to the earlier module's line-by-line read). Between the word and the
number the separator may be nothing, spaces, hyphens, a newline, a comment marker (`#`, `//`) or a hash, and the plural takes
a list ("rounds N and M", "rounds N to M", each number judged). Every spelling of the word in the family is CLASSIFIED by
forms(): a numbered form by its plural and its separator, an unnumbered one (Python's round(), "rounds=40", "a typing round",
"the two-round convergence bound", "in its second round", "around") not read, and a form the classifier cannot place, a number
glued to a letter or an underscore, refused. The form-space cell enumerates the family's own forms and requires every numbered
form class it uses to be one of FORM_CLASSES, each of which has a red and a green probe assembled at run time from
MAINTAINER_ROUNDS (this module is in its own population and reads itself, so no probe is spelled). No file of the family quotes
a ruling sentence that carries a numbered round today, so the rule has no quotation exemption (an exemption nothing fires would
be untested); a quote added later takes the maintainer's form or is paraphrased.
"""
import ast
import glob
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)

# the rulings the maintainer had filed on PR 857 when pass 11 began (the maintainer's rounds 1 to 6), derived 2026-09-21; the
# author raises it in the change that first credits a new round, and nothing outside the tree widens it
MAINTAINER_ROUNDS = frozenset({1, 2, 3, 4, 5, 6})
FAMILY_GLOB = "test_federated_linkdrop*.py"   # the sibling pin's spelling, held equal to it by test_the_population_is_the_trees_and_the_sibling_pins
ENTRY = "upstream/2026-09-19-tests-federated-linkdrop-served.md"
SIBLING_PIN = ("tests/test_federated_linkdrop_driver_bound.py", "test_the_ledger_entry_names_every_module_of_this_family")

# the word, then what follows it: a separator (nothing, spaces, hyphens, a newline, a comment marker, a hash), a number, an
# optional list continuation, and the character after the last digit (a letter or an underscore glued to it makes the form
# unclassifiable); the qualifier's gaps take the same wrap
WORD = re.compile(r"\bround(?P<plural>s?)", re.I)
NUMBERED = re.compile(r"(?P<sep>[-\s#/]*)(?P<num>\d+)(?P<list>(?:\s*(?:,|and|to|or|&)\s*#?\d+)*)(?P<tail>[A-Za-z_]?)")
GAP = r"[\s#/]*"
CREDIT = re.compile(r"\bthe" + GAP + r"maintainer's" + GAP + r"round(?P<plural>s?)(?P<sep>[-\s#/]*)(?P<num>\d+)", re.I)
# the numbered form classes this census reads, by (plural, separator kind), each with the separator its probes are spelled
# with; the form-space cell requires every class the family uses to be one of these, and a red and a green probe per class
FORM_CLASSES = {(False, "none"): "", (False, "space"): " ", (False, "hyphen"): "-", (False, "hash"): " #",
                (False, "wrap"): "\n    # ", (True, "space"): " ", (True, "wrap"): "\n"}


def sep_kind(sep):
    """The class of a separator: a newline makes it a wrap whatever else it holds, a comment marker or a hash a hash, a hyphen a
    hyphen, spaces a space, nothing none."""
    if "\n" in sep:
        return "wrap"
    if "#" in sep or "/" in sep:
        return "hash"
    if "-" in sep:
        return "hyphen"
    return "space" if sep else "none"


def forms(text):
    """Every occurrence of the word in `text`, classified: (line, spelled, kind, numbers) with kind "numbered" (the numbers of
    the mention, a list's every number), "unnumbered" (no number follows: not read) or "unclassifiable" (a number glued to a
    letter or an underscore: refused, since the census cannot say whether it is a credit)."""
    out = []
    for w in WORD.finditer(text):
        n = NUMBERED.match(text, w.end())
        if n is None:
            out.append((text.count("\n", 0, w.start()) + 1, text[w.start():w.end()], "unnumbered", []))
        elif n.group("tail"):
            out.append((text.count("\n", 0, n.start("num")) + 1, text[w.start():n.end()], "unclassifiable", []))
        else:
            nums = [int(n.group("num"))] + [int(x) for x in re.findall(r"\d+", n.group("list"))]
            out.append((text.count("\n", 0, n.start("num")) + 1, text[w.start():n.end("list")], "numbered", nums))
    return out


def form_class(spelled):
    """The (plural, separator kind) class of a numbered form's spelling, from the word to its first digit."""
    w = WORD.match(spelled)
    n = NUMBERED.match(spelled, w.end())
    return (bool(w.group("plural")), sep_kind(n.group("sep")))


def mentions(text):
    """The numbered forms of `text`, as spelled."""
    return [spelled for _, spelled, kind, _ in forms(text) if kind == "numbered"]


def offences(text, allowed=MAINTAINER_ROUNDS):
    """(line number, the mention, why) for every numbered round in `text` that is not "the maintainer's round N" (or a credited
    list) with every N in `allowed`, and for every form the classifier cannot place. Read over the whole text: a credit split
    by a line break is one credit."""
    credited = {m.start("num") for m in CREDIT.finditer(text)}
    out = []
    for w in WORD.finditer(text):
        n = NUMBERED.match(text, w.end())
        if n is None:
            continue
        line = text.count("\n", 0, n.start("num")) + 1
        spelled = text[w.start():n.end("list")]
        if n.group("tail"):
            out.append((line, text[w.start():n.end()], "a form the census cannot classify (a number glued to a letter): write \"the maintainer's round N\" or the author's \"pass P\""))
        elif n.start("num") not in credited:
            out.append((line, spelled, "a numbered round is a credit to the maintainer: write \"the maintainer's round N\" for a ruled "
                                       "round, or the author's \"pass P\" / \"the pass-P head\" for the author's own work"))
        else:
            unruled = [x for x in [int(n.group("num"))] + [int(x) for x in re.findall(r"\d+", n.group("list"))] if x not in allowed]
            if unruled:
                out.append((line, spelled, "no ruling exists for that maintainer round (%s); the rulings are the maintainer's rounds %s"
                            % (", ".join(str(x) for x in unruled), ", ".join(str(x) for x in sorted(allowed)))))
    return out


def family():
    """(the family's files, relative to ROOT; how they were derived): the tree glob plus the ledger entry."""
    modules = sorted(os.path.relpath(p, ROOT) for p in glob.glob(os.path.join(HERE, FAMILY_GLOB)))
    return modules + [ENTRY], "the glob tests/%s over the tree, plus the ledger entry %s" % (FAMILY_GLOB, ENTRY)


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def sibling_glob():
    """The glob pattern the sibling pin passes to glob.glob(os.path.join(HERE, <pattern>)), read from its source by ast, or
    None with the reason when the pin or its glob is not found (the cell refuses then, naming what it could not read)."""
    rel, name = SIBLING_PIN
    tree = ast.parse(_read(rel))
    fn = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name), None)
    if fn is None:
        return None, "%s holds no function %s" % (rel, name)
    patterns = [a.value for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "glob"
                and isinstance(n.func.value, ast.Name) and n.func.value.id == "glob" and n.args and isinstance(n.args[0], ast.Call)
                for a in n.args[0].args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
    if len(patterns) != 1:
        return None, "%s.%s passes glob.glob %d string patterns, not one: %r" % (rel, name, len(patterns), patterns)
    return patterns[0], "read from %s.%s" % (rel, name)


class RoundLabels(unittest.TestCase):
    maxDiff = None

    def test_the_ruled_rounds_are_tree_resident_and_contiguous_from_one(self):
        """MAINTAINER_ROUNDS is non-empty, contiguous from 1 and the only source of the legal set (the cells that take its
        bounds check it first, never max() over an empty set)."""
        self.assertTrue(MAINTAINER_ROUNDS, "MAINTAINER_ROUNDS is empty: the tree records no ruling at all")
        self.assertEqual(sorted(MAINTAINER_ROUNDS), list(range(1, max(MAINTAINER_ROUNDS) + 1)), "the rulings are numbered contiguously from 1: %r" % (sorted(MAINTAINER_ROUNDS),))

    def test_the_module_reads_nothing_outside_the_tree(self):
        """The same committed tree gets one verdict on every machine: this module's own source, by ast, reads no environment
        variable, expands no home path, holds no constant that is an absolute or a home path, and opens files through _read alone,
        which joins on ROOT. The earlier module's notes-directory read (the maintainer's round 6) is what this refuses."""
        tree = ast.parse(_read(os.path.relpath(os.path.realpath(__file__), ROOT)))
        attrs = sorted({n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr in ("environ", "getenv", "expanduser", "expandvars")})
        self.assertEqual(attrs, [], "an environment or home-path read in the census module: the legal set and the population come from the tree alone: %r" % (attrs,))
        home = os.sep + "home" + os.sep
        paths = sorted({n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value) > 1
                        and (n.value[0] in (os.sep, "~") or home in n.value)})
        self.assertEqual(paths, [], "an absolute or home path in the census module: %r" % (paths,))
        opens = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "open"]
        self.assertEqual(len(opens), 1, "every file the census reads goes through _read, which joins on ROOT: open() at lines %r" % (opens,))

    def test_the_population_is_the_trees_and_the_sibling_pins(self):
        """The population is derived by FAMILY_GLOB plus the entry; every file exists; this module is in its own population; and
        the sibling ledger pin's glob, read from its source, is the same spelling and yields the same modules, so the two
        populations cannot disagree silently. A glob that reads no module is a refusal, never a clean census."""
        files, how = family()
        modules = [f for f in files if f != ENTRY]
        self.assertTrue(modules, "the glob read no module of the family (%s): a broken glob or a moved directory is not a clean tree" % how)
        missing = [f for f in files if not os.path.isfile(os.path.join(ROOT, f))]
        self.assertEqual(missing, [], "a file of the population is not in the tree (%s): %r" % (how, missing))
        self.assertIn(os.path.relpath(os.path.realpath(__file__), ROOT), modules, "this module is in its own population, so its probes must be assembled at run time: %r" % (modules,))
        pattern, source = sibling_glob()
        self.assertIsNotNone(pattern, "the sibling pin's glob could not be read, so the two populations cannot be held equal: %s" % source)
        self.assertEqual(pattern, FAMILY_GLOB, "the sibling pin (%s) globs %r while this census globs %r: the two populations are keyed on different spellings" % (source, pattern, FAMILY_GLOB))
        sibling = sorted(os.path.relpath(p, ROOT) for p in glob.glob(os.path.join(HERE, pattern)))
        self.assertEqual(sibling, modules, "the sibling pin's glob and this census's population differ: %r" % (sorted(set(sibling) ^ set(modules)),))

    def test_no_mention_credits_a_round_the_maintainer_never_held(self):
        files, how = family()
        bad, seen, counted = [], 0, {}
        for rel in files:
            text = _read(rel)
            counted[rel] = len(mentions(text))
            seen += counted[rel]
            bad += ["%s:%d: %r (%s)" % (rel, ln, label, why) for ln, label, why in offences(text)]
        self.assertGreater(seen, 0, "the census read no numbered round at all over %s: the pattern or the population is broken (%r)" % (how, counted))
        self.assertEqual(bad, [], "a numbered round that is not a ruled maintainer round (the maintainer's rounds %s, from MAINTAINER_ROUNDS; the population from %s); write "
                                  "the author's pass (\"pass P\", \"pass P's fixer pass\", \"the pass-P head\") or \"the maintainer's round N\" for a round a ruling exists "
                                  "for, and raise MAINTAINER_ROUNDS in the change that first credits a new ruling:\n%s"
                                  % (", ".join(str(x) for x in sorted(MAINTAINER_ROUNDS)), how, "\n".join(bad)))

    def test_the_form_space(self):
        """The classifier over every spelling the family uses and every class this census reads: the family's own forms are
        enumerated by forms() and each numbered one is a FORM_CLASSES class (a spelling outside the enumeration is a refusal,
        not a silent read), no form is unclassifiable, and every class has red probes (uncredited at a ruled round, a credit one
        past the set) and green probes (a credit at the highest and the lowest ruled round), assembled at run time from
        MAINTAINER_ROUNDS because this module reads itself. Then the wrapped shapes, the plural list, the unnumbered spellings,
        an unclassifiable form, and the refusal reasons told apart."""
        self.assertTrue(MAINTAINER_ROUNDS, "MAINTAINER_ROUNDS is empty: no probe can be assembled (the derivation cell states the cause)")
        hi, lo = max(MAINTAINER_ROUNDS), min(MAINTAINER_ROUNDS)
        R, M = "round", "the maintainer's"
        files, how = family()
        used, unclassifiable = {}, []
        for rel in files:
            for line, spelled, kind, nums in forms(_read(rel)):
                if kind == "numbered":
                    used.setdefault(form_class(spelled), []).append("%s:%d %r" % (rel, line, spelled))
                elif kind == "unclassifiable":
                    unclassifiable.append("%s:%d %r" % (rel, line, spelled))
        self.assertEqual(unclassifiable, [], "a spelling the census cannot classify in the family: %r" % (unclassifiable,))
        self.assertTrue(used, "the family carries no numbered form at all (%s): the enumeration is vacuous" % how)
        outside = {k: v[:3] for k, v in used.items() if k not in FORM_CLASSES}
        self.assertEqual(outside, {}, "a numbered spelling the form space does not enumerate (add its class to FORM_CLASSES with its probes): %r" % (outside,))
        for (plural, kind), sep in FORM_CLASSES.items():
            word = R + ("s" if plural else "")
            with self.subTest(form="%s%s<N>" % (word, sep.replace("\n", "<newline>"))):
                tail = (" and %d" % lo) if plural else ""
                red = ["%s%s%d%s" % (word, sep, hi + 1, tail), "%s %s%s%d%s" % (M, word, sep, hi + 1, tail), "the %s%s%d head" % (word, sep, hi),
                       "(%s%s%d, tests-1)" % (word, sep, lo), "%s %s%s%d and %d" % (M, word, sep, lo, hi + 1)]
                green = ["%s %s%s%d%s" % (M, word, sep, hi, tail), "%s %s%s%d%s" % (M, word, sep, lo, tail), "%s %s%s%d's tests-3" % (M, word, sep, lo),
                         "(%s %s%s%d)" % (M, word, sep, hi), "The %s %s%s%d ruled" % (M[4:], word, sep, hi)]
                self.assertEqual([s for s in red if not offences(s)], [], "a refused form read as clean")
                self.assertEqual([s for s in green if offences(s)], [], "an allowed form read as an offence")
        # the wrapped shapes: the qualifier and the number split by a line break, a comment marker on the next line
        self.assertEqual(offences("... (%s %s\n    %d, correctness-1: the bound deleted" % (M, R, lo)), [], "a credit wrapped at the number is one credit")
        self.assertEqual(offences("# ... (the\n    # maintainer's %s %d found it" % (R, hi)), [], "a credit wrapped at the qualifier, a comment marker between, is one credit")
        self.assertEqual([ln for ln, _, _ in offences("a\nb\n# the %s\n# %d head" % (R, hi + 1))], [4], "a wrapped uncredited round is an offence at the line its number sits on")
        self.assertEqual([ln for ln, _, _ in offences("%s %s\n%d\n" % (M, R, hi + 1))], [2], "a wrapped credit to an unruled round is an offence at the number's line")
        # the plural list: every number judged
        self.assertEqual(len(offences("%s %ss %d and %d" % (M, R, lo, hi + 1))), 1, "a credited list with one unruled number is one offence")
        self.assertEqual(offences("%s %ss %d to %d" % (M, R, lo, hi)), [], "a credited range inside the set is clean")
        self.assertEqual(len(offences("%ss %d and %d were held" % (R, lo, hi))), 1, "an uncredited list is one offence, at the list")
        # the unnumbered spellings are not read
        for s in ("%ss=40" % R, "in 1 %ss" % R, "a typing %s" % R, "the two-%s convergence bound" % R, "in its second %s" % R, "_commands_a%s_the_recorder" % R,
                  "%s(t_dead - t0, 2)" % R, "spaces-a%s-dots" % R, "rulings-r1.md", "the boot a%s it" % R, "each %s of planting" % R, "a typing %s\n# visits" % R,
                  "%s_labels" % R, "the %s-trip" % R, "the %s's own" % R):
            self.assertEqual(offences(s), [], "an unnumbered use read as an offence: %r" % (s,))
            self.assertEqual(mentions(s), [], "an unnumbered use read as a mention: %r" % (s,))
        # an unclassifiable form is refused, never silently unread
        self.assertIn("cannot classify", offences("%s %da" % (R, hi))[0][2])
        self.assertEqual([k for _, _, k, _ in forms("%s %dth" % (R, hi))], ["unclassifiable"])
        # the two refusals are told apart: an uncredited number, and a credit to a round with no ruling
        self.assertIn("credit to the maintainer", offences("%s %d" % (R, hi))[0][2])
        self.assertIn("no ruling exists", offences("%s %s %d" % (M, R, hi + 1))[0][2])
        self.assertEqual(mentions("%s %s %d and %s-%d and R%s %d's and %ss %d and %d" % (M, R, hi, R, lo, R[1:], lo, R, lo, hi)),
                         ["%s %d" % (R, hi), "%s-%d" % (R, lo), "R%s %d" % (R[1:], lo), "%ss %d and %d" % (R, lo, hi)])


if __name__ == "__main__":
    unittest.main()
