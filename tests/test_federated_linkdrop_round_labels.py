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
and M", "rounds N to M", "rounds N-M") is a credit to the maintainer, so it is refused unless spelled "the maintainer's round
N" (or "the maintainer's rounds N and M", "rounds N to M", every number of the list or range judged) with N in
MAINTAINER_ROUNDS. MAINTAINER_ROUNDS is a constant of this TREE: the rulings the maintainer had filed on PR 857 when this pass
began, derived 2026-09-21, and the author raises it in the same change that first credits a new round, so a credit to a round
no ruling exists for reds on every machine until the ruling exists and the constant says so. It is read from NOTHING outside
the repository. The maintainer's round 6 found the earlier module reading the reviewer's notes directory for the set, so the
same committed tree got two verdicts (the set widened on the one machine that holds the rulings and stayed at the constant
everywhere else), and a verdict that depends on the machine is no property of the repository;
test_the_module_reads_nothing_outside_the_tree pins that over this module's own source by RESOLUTION and not by a list of
spellings (pass 11's fixer pass: the earlier pin refused four attribute names and one absolute-path shape, and `from os import
environ`, `getattr(os, "environ")`, `os.getcwd()`, a `..` constant and a drive-letter constant passed it; pass 11's closing
fixer pass: the second pin resolved os by its literal name alone, so os reached as another table module's attribute
(`glob.os.environ`, `unittest.loader.os.getcwd()`), a primitive bound to another name (`_o = open`), one reached through
`__builtins__`, a second glob.glob, and _read's own join handed an absolute path all read outside the tree with it green): the
import table is closed (IMPORTS, module-level `import x` alone, no from-import and no alias); every attribute chain rooted at
a module of the table is in MEMBERS for that module and every entry of MEMBERS is read (both ways per module, so a member the
module does not read today is refused by construction, whichever module it hangs off); a module of the table is read only as
the root of such a chain; every callee is a name or an attribute chain; every name called is a definition of this module or
one of BUILTINS (held equal both ways); the dunder names read are exactly DUNDERS; no attribute read is a dunder or
str.format; no reflective or file primitive is called or read but the one open() in _read and the one glob.glob in
_family_modules, both of whose paths pass _under, which REFUSES at run time, over the value, a path that is absolute or leaves
the root (pinned by execution in test_every_path_the_module_reads_is_under_the_tree); and no string constant is an absolute
path, a home path, a `..` step or a drive letter.

THE POPULATION is derived from the tree: the modules the glob FAMILY_GLOB names under this directory (the sibling pin's own
spelling, tests/test_federated_linkdrop_driver_bound.py's ledger pin; a family module named otherwise escapes both, so the
population is spelling-keyed and says so) plus the ledger entry ENTRY, read whole, since every line of them is the branch's
own. family() REFUSES, with the derivation named, a glob that reads no module, a file of the population that is not in the
tree, and this module outside its own population (its path the parameter `me`, this module's own by default, so the
population cell executes that refusal too: pass 11's closing fixer pass found it reachable and run by no cell), and every
cell reads the population through it, so a selected run of any one cell gets the same stated refusal (pass 11's fixer pass:
the census cell over an empty module population passed on the entry's one credited mention, and a missing file was a bare
FileNotFoundError in two cells); _read refuses a file that is not
in the tree the same way, and sibling_glob returns the reason when the pin's file or function is not found. A cell reads the
sibling pin's glob from that pin's source and runs it, holding the two populations equal, so a family module the sibling sees
and this census does not is a red.

THE FORM SPACE. offences() reads the WHOLE text of each file, so a mention wrapped across a line break (the qualifier ending one
line and the number starting the next, a comment marker between) is one mention, reported at the line its number sits on (a
wrapped credit in the driver-bound module was invisible to the earlier module's line-by-line read). Between the word and the
number the separator may be nothing, spaces, hyphens, a newline, a comment marker (`#`, `//`) or a hash; the plural takes a
list or a range ("rounds N and M", "rounds N, M", "rounds N to M", "rounds N-M", an en dash, a slash, "through": each number
judged, and a range's endpoints stand for it, since MAINTAINER_ROUNDS is contiguous from 1); the singular takes the same
continuations but the comma, which is the plural's alone, so a count after a singular ("round N, M findings") is a
continuation the list did not consume and is refused as one (pass 11's closing fixer pass: the singular's list consumed the
comma, and a count after a credited round was refused as a credit to a round of the count's number, a binding the text does
not make). Every spelling of the word in the family is
CLASSIFIED by forms(): a numbered form by its plural and its separator; an unnumbered one (Python's round(), the
keyword-argument spelling "rounds=40", "a typing round", "the two-round convergence bound", "in its second round", "around",
a word between the word and a number as in "a round of 3 drives": the census reads spellings of the word, not sentences) not
read; and a form the classifier cannot place REFUSED, keyed on what it did not resolve (pass 11's fixer pass: a hyphenated
range "rounds N-M" was read as "rounds N" with M dropped, and a colon between the word and the number was read as unnumbered):
a number glued to a letter or an underscore, a further number after a run the list did not consume ("rounds N; M", "round
N, M"), a plural
that names one number ("rounds N"), and punctuation or markup between the word and a number ("round: N", "round (N)",
"round **N**", "round `N`"), the one exemption being the keyword-argument spelling, the word glued to `=` (the family's
`rounds=40` and `rounds=1`; no probe is spelled with a digit in this docstring, since the module reads itself). The `rN` path stems of the builder's scratch
directories outside the repository (`r6-margin/lab-head2.log`, `r10/lab-ci9.log`) name the author's pipeline's rounds and are
not the word, so they are not read (the record's "r4 unused by the family" was wrong: the served module carries them as
paths). The form-space cell enumerates the family's own forms and requires every numbered form class it uses to be one of
FORM_CLASSES, each of which has a red and a green probe assembled at run time from MAINTAINER_ROUNDS (this module is in its
own population and reads itself, so no probe is spelled). No file of the family quotes a ruling sentence that carries a
numbered round today, so the rule has no quotation exemption (an exemption nothing fires would be untested); a quote added
later takes the maintainer's form or is paraphrased.
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
# the tree-only pin: the closed import table of this module; every attribute chain it reads on each module of the table (held
# equal both ways per module, so a read the module does not make today, os.environ, os.getcwd, glob.os, unittest.loader, is
# refused by construction, not by a list of the names to refuse); the builtins it calls and the module-level dunder names it
# reads, closed the same way; and the primitives it neither calls nor reads, but the one open() inside _read
IMPORTS = ("ast", "glob", "os", "re", "unittest")
MEMBERS = {"ast": ("Attribute", "Call", "ClassDef", "Constant", "FunctionDef", "Import", "ImportFrom", "Load", "Name", "iter_child_nodes", "parse", "unparse", "walk"),
           "glob": ("glob",),
           "os": ("pardir", "path.commonpath", "path.dirname", "path.isabs", "path.isfile", "path.join", "path.realpath", "path.relpath", "sep"),
           "re": ("I", "compile", "findall", "match", "search"),
           "unittest": ("TestCase", "main")}
BUILTINS = ("AssertionError", "bool", "frozenset", "int", "isinstance", "len", "list", "max", "min", "next", "range", "reversed", "set", "sorted", "str")
DUNDERS = ("__file__", "__name__")
PRIMITIVES = ("open", "getattr", "setattr", "delattr", "hasattr", "__import__", "eval", "exec", "compile", "vars", "globals", "locals")

# the word, then what follows it: a separator (nothing, spaces, hyphens, a newline, a comment marker, a hash), a number, an
# optional list or range continuation (each number judged; the comma is the plural's alone, since a singular followed by a comma
# and a number is a count and the list would bind the count as a round), and the character after the last digit (a letter or an
# underscore glued to it makes the form unclassifiable); the qualifier's gaps take the same wrap
WORD = re.compile(r"\bround(?P<plural>s?)", re.I)
_NUMBERED = r"(?P<sep>[-\s#/]*)(?P<num>\d+)(?P<list>(?:\s*(?:%s)\s*#?\d+)*)(?P<tail>[A-Za-z_]?)"
NUMBERED = {False: re.compile(_NUMBERED % r"and|to|or|&|through|thru|[-–/]"), True: re.compile(_NUMBERED % r",|and|to|or|&|through|thru|[-–/]")}
# after the last digit the list consumed: a run of punctuation and spaces (no letter, no newline) and then a digit is a
# continuation the list did not resolve; after the word with no number read: the same run and then a digit is punctuation or
# markup between the word and a number, unclassifiable unless the run is the keyword-argument spelling's `=`
CONTINUATION = re.compile(r"[^\w\n]{1,6}\d")
GAP = r"[\s#/]*"
CREDIT = re.compile(r"\bthe" + GAP + r"maintainer's" + GAP + r"round(?P<plural>s?)(?P<sep>[-\s#/]*)(?P<num>\d+)", re.I)
# the numbered form classes this census reads, by (plural, separator kind), each with the separator its probes are spelled
# with; the form-space cell requires every class the family uses to be one of these, and a red and a green probe per class
FORM_CLASSES = {(False, "none"): "", (False, "space"): " ", (False, "hyphen"): "-", (False, "hash"): " #",
                (False, "wrap"): "\n    # ", (True, "space"): " ", (True, "wrap"): "\n"}
UNCLASSIFIABLE = "a form the census cannot classify (%s): write \"the maintainer's round N\" or the author's \"pass P\""


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


def _classify(text, w):
    """One occurrence `w` of the word in `text`: (kind, the match of NUMBERED or None, the numbers, why unclassifiable). Kind is
    "numbered" (every number of the list or range read), "unnumbered" (no number follows: not read) or "unclassifiable" (a
    number the census cannot place, refused with the reason)."""
    n = NUMBERED[bool(w.group("plural"))].match(text, w.end())
    if n is None:
        gap = CONTINUATION.match(text, w.end())
        if gap is not None and gap.group()[:-1] != "=":
            return "unclassifiable", None, [], "punctuation or markup between the word and a number: %r" % text[w.start():gap.end()]
        return "unnumbered", None, [], None
    nums = [int(n.group("num"))] + [int(x) for x in re.findall(r"\d+", n.group("list"))]
    if n.group("tail"):
        return "unclassifiable", n, nums, "a number glued to a letter or an underscore: %r" % text[w.start():n.end()]
    if CONTINUATION.match(text, n.end("list")) is not None:
        return "unclassifiable", n, nums, "a further number after a run the list did not consume: %r" % text[w.start():CONTINUATION.match(text, n.end("list")).end()]
    if w.group("plural") and len(nums) == 1:
        return "unclassifiable", n, nums, "a plural that names one number: %r" % text[w.start():n.end("list")]
    return "numbered", n, nums, None


def forms(text):
    """Every occurrence of the word in `text`, classified: (line, spelled, kind, numbers) with kind "numbered" (the numbers of
    the mention, a list's or a range's every number), "unnumbered" (no number follows: not read) or "unclassifiable" (a number
    the census cannot place: refused, since it cannot say whether the form is a credit or which rounds it names)."""
    out = []
    for w in WORD.finditer(text):
        kind, n, nums, _ = _classify(text, w)
        if kind == "unnumbered":
            out.append((text.count("\n", 0, w.start()) + 1, text[w.start():w.end()], kind, []))
        elif n is None:
            out.append((text.count("\n", 0, w.start()) + 1, text[w.start():w.end()], kind, []))
        elif kind == "unclassifiable":
            out.append((text.count("\n", 0, n.start("num")) + 1, text[w.start():n.end()], kind, []))
        else:
            out.append((text.count("\n", 0, n.start("num")) + 1, text[w.start():n.end("list")], kind, nums))
    return out


def form_class(spelled):
    """The (plural, separator kind) class of a numbered form's spelling, from the word to its first digit."""
    w = WORD.match(spelled)
    n = NUMBERED[bool(w.group("plural"))].match(spelled, w.end())
    return (bool(w.group("plural")), sep_kind(n.group("sep")))


def mentions(text):
    """The numbered forms of `text`, as spelled."""
    return [spelled for _, spelled, kind, _ in forms(text) if kind == "numbered"]


def offences(text, allowed=MAINTAINER_ROUNDS):
    """(line number, the mention, why) for every numbered round in `text` that is not "the maintainer's round N" (or a credited
    list or range) with every N in `allowed`, and for every form the classifier cannot place. Read over the whole text: a
    credit split by a line break is one credit."""
    credited = {m.start("num") for m in CREDIT.finditer(text)}
    out = []
    for w in WORD.finditer(text):
        kind, n, nums, why = _classify(text, w)
        if kind == "unnumbered":
            continue
        line = text.count("\n", 0, w.start() if n is None else n.start("num")) + 1
        if kind == "unclassifiable":
            out.append((line, text[w.start():n.end()] if n is not None else text[w.start():w.end()], UNCLASSIFIABLE % why))
            continue
        spelled = text[w.start():n.end("list")]
        if n.start("num") not in credited:
            out.append((line, spelled, "a numbered round is a credit to the maintainer: write \"the maintainer's round N\" for a ruled "
                                       "round, or the author's \"pass P\" / \"the pass-P head\" for the author's own work"))
        else:
            unruled = [x for x in nums if x not in allowed]
            if unruled:
                out.append((line, spelled, "no ruling exists for that maintainer round (%s); the rulings are the maintainer's rounds %s"
                            % (", ".join(str(x) for x in unruled), ", ".join(str(x) for x in sorted(allowed)))))
    return out


def family(here=HERE, root=ROOT, me=None):
    """(the family's files, relative to `root`; how they were derived): the tree glob over `here` plus the ledger entry. REFUSES
    (an AssertionError naming the derivation) a glob that reads no module, a file of the population that is not in the tree,
    and this module outside its own population, so every cell that reads the population gets the one stated refusal, a
    selected run of one cell included, and no cell judges an empty or a partial population (the census over the entry alone
    would pass on its one credited mention). `here`, `root` and `me` (this module's path relative to `root`, its own unless
    given) are parameters so each refusal is pinned by execution over the tree; the cells read the tree's own."""
    how = "the glob tests/%s over the tree, plus the ledger entry %s" % (FAMILY_GLOB, ENTRY)
    modules = _family_modules(here, root)
    if not modules:
        raise AssertionError("the glob read no module of the family (%s): a broken glob or a moved directory is not a clean tree" % how)
    files = modules + [ENTRY]
    missing = [f for f in files if not os.path.isfile(_under(root, f))]
    if missing:
        raise AssertionError("a file of the population is not in the tree (%s): %r" % (how, missing))
    me = os.path.relpath(os.path.realpath(__file__), root) if me is None else me
    if me not in modules:
        raise AssertionError("this module is outside its own population (%s), so its probes could not be assembled at run time: %r" % (how, modules))
    return files, how


def _under(root, rel):
    """The real path of `rel` under `root`, the one road to every file this module opens or globs: REFUSES (an AssertionError
    naming the path) a `rel` that is absolute and a joined path whose real path is not under `root`, at run time and over the
    value. os.path.join discards its root for an absolute second argument and a `..` step walks out of it, so a check over the
    constants' shapes alone left the module's own sanctioned read able to leave the tree (pass 11's closing fixer pass)."""
    if os.path.isabs(rel):
        raise AssertionError("%s is an absolute path: this module reads paths relative to the repository root alone" % rel)
    base = os.path.realpath(root)
    path = os.path.realpath(os.path.join(base, rel))
    if os.path.commonpath((base, path)) != base:
        raise AssertionError("%s leaves the tree (%s is not under %s)" % (rel, path, base))
    return path


def _read(rel, root=ROOT):
    """The text of a file of the tree by its path relative to `root` (the one open() of this module, its path through _under,
    which refuses one that is absolute or leaves the root), or a stated refusal naming the file when it is not there."""
    if not os.path.isfile(_under(root, rel)):
        raise AssertionError("%s is not in the tree (read relative to the repository root)" % rel)
    with open(_under(root, rel), encoding="utf-8") as f:
        return f.read()


def _family_modules(here, root, pattern=FAMILY_GLOB):
    """The family's modules under `here` by `pattern`, relative to `root`, sorted: the one glob.glob of this module, its directory
    through _under (a `here` outside the root is refused), its pattern a file name pattern (one holding a path separator names
    another directory, which the census does not resolve: refused), and every result under the root the same way."""
    if os.sep in pattern:
        raise AssertionError("%r is not a file name pattern under the family's directory: it holds a path separator" % pattern)
    found = glob.glob(os.path.join(_under(root, os.path.relpath(here, root)), pattern))
    modules = sorted(os.path.relpath(p, root) for p in found)
    for m in modules:
        _under(root, m)
    return modules


def sibling_glob(pin=SIBLING_PIN, root=ROOT):
    """The glob pattern the sibling pin passes to glob.glob(os.path.join(HERE, <pattern>)), read from its source by ast, or
    None with the reason when the pin's file, the function or its glob is not found (the cell refuses then, naming what it
    could not read)."""
    rel, name = pin
    try:
        tree = ast.parse(_read(rel, root))
    except AssertionError as e:
        return None, str(e)
    fn = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name), None)
    if fn is None:
        return None, "%s holds no function %s" % (rel, name)
    patterns = [a.value for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "glob"
                and isinstance(n.func.value, ast.Name) and n.func.value.id == "glob" and n.args and isinstance(n.args[0], ast.Call)
                for a in n.args[0].args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
    if len(patterns) != 1:
        return None, "%s.%s passes glob.glob %d string patterns, not one: %r" % (rel, name, len(patterns), patterns)
    return patterns[0], "read from %s.%s" % (rel, name)


def _chains(tree):
    """Every attribute chain of `tree` rooted at a name of IMPORTS, outermost only, by its root: {"os": {"path.join", ...}}, the
    reads the tree-only pin holds equal to MEMBERS, module by module."""
    parents = {c: p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}
    out = {m: set() for m in IMPORTS}
    for n in ast.walk(tree):
        if isinstance(n, ast.Attribute) and not (isinstance(parents.get(n), ast.Attribute) and parents[n].value is n):
            parts, q = [], n
            while isinstance(q, ast.Attribute):
                parts.append(q.attr)
                q = q.value
            if isinstance(q, ast.Name) and q.id in IMPORTS:
                out[q.id].add(".".join(reversed(parts)))
    return out


class RoundLabels(unittest.TestCase):
    maxDiff = None

    def test_the_ruled_rounds_are_tree_resident_and_contiguous_from_one(self):
        """MAINTAINER_ROUNDS is non-empty, contiguous from 1 and the only source of the legal set (the cells that take its
        bounds check it first, never max() over an empty set); a range's endpoints stand for the range because of this."""
        self.assertTrue(MAINTAINER_ROUNDS, "MAINTAINER_ROUNDS is empty: the tree records no ruling at all")
        self.assertEqual(sorted(MAINTAINER_ROUNDS), list(range(1, max(MAINTAINER_ROUNDS) + 1)), "the rulings are numbered contiguously from 1: %r" % (sorted(MAINTAINER_ROUNDS),))

    def test_the_module_reads_nothing_outside_the_tree(self):
        """The same committed tree gets one verdict on every machine, pinned over this module's own source by RESOLUTION: every
        name the module reads is resolved to a binding the pin knows, and a read it cannot resolve is refused (the maintainer's
        round 6 found the earlier module reading the reviewer's notes directory; pass 11's fixer pass found the first pin keyed
        on four attribute names and one path shape; its closing fixer pass found the second resolving os by its literal name
        alone, so os as another table module's attribute, a primitive under another name, `__builtins__`, a second glob.glob
        and _read's join handed an absolute path all read outside the tree with the pin green). The imports are exactly IMPORTS
        (module-level `import x`, no from-import, no alias, none inside a function or a class); every attribute chain rooted at
        a module of the table is in MEMBERS for that module and every entry of MEMBERS is read, both ways per module, so a
        member the module does not read today (os.environ, os.getcwd, glob.os, unittest.loader, re.sre_compile) is refused by
        construction; a module of the table is read only as the root of such a chain, never handed on as a value; every callee
        is a name or an attribute chain (a subscript or a call as the callee is unresolved); every name called is a definition
        of this module or one of BUILTINS, held equal both ways; no primitive (PRIMITIVES) is called or read but exactly one
        open(), inside _read, whose argument is _under(root, rel), and the one glob.glob is inside _family_modules with its
        directory through _under; the dunder names read are exactly DUNDERS (so `__builtins__`, `__loader__` and `__spec__`,
        which reach the builtins and the file system, are refused); no attribute read is a dunder (`__class__`, `__globals__`,
        `__dict__`: reflection) or str.format or format_map, whose fields walk attributes by name inside a string the walk does
        not read; and no string constant is an absolute path, a home path, a `..` step or a drive letter. _under's refusals at
        run time are pinned by execution in test_every_path_the_module_reads_is_under_the_tree. What the pin does not check,
        stated: the standard library's own reads (glob and re read no environment; os.path.realpath follows symlinks of the
        tree itself), a method called on a value the module bound itself (text.count, self.assertEqual: the values are made
        from the reads above), and code that arrives by a road the table forbids, refused at the import, not read."""
        tree = ast.parse(_read(os.path.relpath(os.path.realpath(__file__), ROOT)))
        parents = {c: p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}
        imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        self.assertEqual([n.lineno for n in imports if isinstance(n, ast.ImportFrom)], [], "a from-import in the census module: a name bound past the import table is a road the pin cannot resolve")
        self.assertEqual([n.lineno for n in imports if n not in tree.body], [], "an import inside a function or a class: every import is module-level, so the table below is the whole table")
        self.assertEqual([a.asname for n in imports for a in n.names if a.asname], [], "an import under another name: the reads below resolve the module by its own name")
        self.assertEqual(sorted(a.name for n in imports for a in n.names), sorted(IMPORTS), "the census module's import table is exactly IMPORTS: a module outside it may read the environment, the home or the working directory")
        self.assertEqual(sorted(MEMBERS), sorted(IMPORTS), "MEMBERS holds one table per module of IMPORTS")
        chains = _chains(tree)
        for m in IMPORTS:
            with self.subTest(module=m):
                self.assertEqual(sorted(chains[m] - set(MEMBERS[m])), [], "a read on %s this module does not make today (a member outside MEMBERS may reach the environment, the home or the working directory, os.environ and glob.os among them): %r" % (m, sorted(chains[m] - set(MEMBERS[m]))))
                self.assertEqual(sorted(set(MEMBERS[m]) - chains[m]), [], "a member of MEMBERS[%r] no longer read: the table is held equal to the module's reads both ways" % m)
        bare = [(n.id, n.lineno) for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id in IMPORTS and not (isinstance(parents.get(n), ast.Attribute) and parents[n].value is n)]
        self.assertEqual(bare, [], "a module of the table read as a value (assigned, passed, subscripted) is a name the pin cannot follow: %r" % (bare,))
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
        self.assertEqual([(ast.unparse(n.func), n.lineno) for n in calls if not isinstance(n.func, (ast.Name, ast.Attribute))], [], "a callee that is neither a name nor an attribute chain (a subscript, a call) is unresolved")
        defs = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        named = {n.func.id for n in calls if isinstance(n.func, ast.Name)}
        self.assertEqual(sorted(named - defs - set(BUILTINS) - {"open"}), [], "a name called that is neither a definition of this module nor one of BUILTINS is unresolved: %r" % (sorted(named - defs - set(BUILTINS) - {"open"}),))
        self.assertEqual(sorted(set(BUILTINS) - named), [], "a builtin in BUILTINS this module no longer calls: the tuple is held equal to the module's calls both ways")
        self.assertEqual(sorted(set(BUILTINS) & (defs | set(PRIMITIVES))), [], "BUILTINS names a definition of this module or a primitive")
        prim = [(n.id, n.lineno) for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id in PRIMITIVES]
        self.assertEqual([(i, ln) for i, ln in prim if i != "open"], [], "a reflective or file primitive read in the census module (a name reached by a string, a file opened outside _read) is a read the pin cannot resolve: %r" % ([(i, ln) for i, ln in prim if i != "open"],))
        read = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_read")
        inside = [n for n in ast.walk(read) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "open"]
        self.assertEqual([ln for i, ln in prim if i == "open"], [n.func.lineno for n in inside], "every read of the name open is the callee of the one open() inside _read (a bare `open` bound to another name, or one called elsewhere, is a file read the pin cannot follow): %r" % ([ln for i, ln in prim if i == "open"],))
        self.assertEqual(len(inside), 1, "_read holds exactly one open()")
        self.assertEqual(ast.unparse(inside[0].args[0]), "_under(root, rel)", "_read opens the path _under returns, which refuses one that is absolute or leaves the root: %s" % ast.unparse(inside[0].args[0]))
        default = read.args.defaults[-1] if read.args.defaults else None
        self.assertTrue(isinstance(default, ast.Name) and default.id == "ROOT", "_read's root defaults to ROOT: %s" % (ast.unparse(default) if default is not None else None))
        globs = [n for n in calls if isinstance(n.func, ast.Attribute) and ast.unparse(n.func) == "glob.glob"]
        fam = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_family_modules")
        self.assertEqual([n.lineno for n in globs], [n.lineno for n in ast.walk(fam) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and ast.unparse(n.func) == "glob.glob"], "every glob.glob is inside _family_modules: at lines %r" % ([n.lineno for n in globs],))
        self.assertEqual(len(globs), 1, "_family_modules holds exactly one glob.glob")
        self.assertEqual(ast.unparse(globs[0].args[0]), "os.path.join(_under(root, os.path.relpath(here, root)), pattern)", "the glob's directory passes _under: %s" % ast.unparse(globs[0].args[0]))
        dunders = sorted({n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id.startswith("__")})
        self.assertEqual(dunders, sorted(DUNDERS), "the module-level dunder names read are exactly DUNDERS (`__builtins__`, `__loader__` and `__spec__` reach the builtins and the file system): %r" % (dunders,))
        reflective = [(n.attr, n.lineno) for n in ast.walk(tree) if isinstance(n, ast.Attribute) and (n.attr.startswith("__") or n.attr in ("format", "format_map"))]
        self.assertEqual(reflective, [], "a dunder attribute (reflection) or str.format (its fields walk attributes by name inside a string) in the census module: %r" % (reflective,))
        home = os.sep + "home" + os.sep
        paths = sorted({n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value) > 1
                        and (n.value[0] in (os.sep, "~") or home in n.value or re.search(r"(^|[\\/])\.\.([\\/]|$)", n.value) or re.match(r"[A-Za-z]:[\\/]", n.value))})
        self.assertEqual(paths, [], "an absolute path, a home path, a `..` step or a drive letter in the census module: %r" % (paths,))

    def test_the_population_is_the_trees_and_the_sibling_pins(self):
        """The population is derived by FAMILY_GLOB plus the entry through family(), which refuses an empty or a partial one
        with the derivation named; the sibling ledger pin's glob, read from its source, is the same spelling and yields the
        same modules, so the two populations cannot disagree silently. Then the refusals themselves, by execution: family()
        over a directory of the tree that holds no family module, over a root under which the entry is missing, and with this
        module's path outside its own population (pass 11's closing fixer pass: that refusal was reachable and run by no
        cell), _read over a file that is not there, and sibling_glob over a pin whose file is missing, each a stated refusal
        naming what it could not read, never a bare exception or an empty census."""
        files, how = family()
        modules = [f for f in files if f != ENTRY]
        pattern, source = sibling_glob()
        self.assertIsNotNone(pattern, "the sibling pin's glob could not be read, so the two populations cannot be held equal: %s" % source)
        self.assertEqual(pattern, FAMILY_GLOB, "the sibling pin (%s) globs %r while this census globs %r: the two populations are keyed on different spellings" % (source, pattern, FAMILY_GLOB))
        sibling = _family_modules(HERE, ROOT, pattern)
        self.assertEqual(sibling, modules, "the sibling pin's glob and this census's population differ: %r" % (sorted(set(sibling) ^ set(modules)),))
        with self.assertRaises(AssertionError) as none:
            family(here=os.path.join(ROOT, "upstream"))
        self.assertIn("read no module of the family", str(none.exception))
        with self.assertRaises(AssertionError) as partial:
            family(here=HERE, root=HERE)
        self.assertIn("is not in the tree", str(partial.exception))
        self.assertIn(ENTRY, str(partial.exception))
        with self.assertRaises(AssertionError) as outside:
            family(me="tests/no_such_census.py")
        self.assertIn("this module is outside its own population", str(outside.exception))
        with self.assertRaises(AssertionError) as gone:
            _read("upstream/no-such-entry.md")
        self.assertEqual(str(gone.exception), "upstream/no-such-entry.md is not in the tree (read relative to the repository root)")
        self.assertEqual(sibling_glob(pin=("tests/no_such_module.py", SIBLING_PIN[1])), (None, "tests/no_such_module.py is not in the tree (read relative to the repository root)"))
        self.assertEqual(sibling_glob(pin=(SIBLING_PIN[0], "no_such_function"))[0], None)

    def test_every_path_the_module_reads_is_under_the_tree(self):
        """_under, the road every open() and glob.glob() of this module takes (the pin above holds them there), by execution:
        it refuses an absolute path, a path that steps out of the root, a directory outside the root handed to the glob and a
        pattern that names a directory, each with its reason, and it accepts the population's own reads (the entry's path,
        this module through the glob over its directory). Pass 11's closing fixer pass planted _read over an absolute path
        and read a file outside the tree with the earlier pin green, since os.path.join discards its root for an absolute
        second argument and the pin read the constants' shapes alone."""
        with self.assertRaises(AssertionError) as absolute:
            _read(os.sep + "etc" + os.sep + "os-release")
        self.assertIn("is an absolute path", str(absolute.exception))
        with self.assertRaises(AssertionError) as out:
            _read(os.path.join(os.pardir, "x"))
        self.assertIn("leaves the tree", str(out.exception))
        with self.assertRaises(AssertionError) as outside:
            _family_modules(os.path.join(ROOT, os.pardir), ROOT)
        self.assertIn("leaves the tree", str(outside.exception))
        with self.assertRaises(AssertionError) as directory:
            _family_modules(HERE, ROOT, os.path.join("tests", FAMILY_GLOB))
        self.assertIn("holds a path separator", str(directory.exception))
        self.assertEqual(_under(ROOT, ENTRY), os.path.join(os.path.realpath(ROOT), ENTRY))
        self.assertIn(os.path.relpath(os.path.realpath(__file__), ROOT), _family_modules(HERE, ROOT))

    def test_no_mention_credits_a_round_the_maintainer_never_held(self):
        """Every numbered round of the family is a credit in the maintainer's form to a round in MAINTAINER_ROUNDS, and every
        form is classifiable. The guard against a vacuous census counts the MODULES' mentions, not the entry's (the entry
        carries one credit, which is what satisfied the guard over an empty module population before family() refused it)."""
        files, how = family()
        bad, seen, counted = [], 0, {}
        for rel in files:
            text = _read(rel)
            counted[rel] = len(mentions(text))
            if rel != ENTRY:
                seen += counted[rel]
            bad += ["%s:%d: %r (%s)" % (rel, ln, label, why) for ln, label, why in offences(text)]
        self.assertGreater(seen, 0, "the census read no numbered round in any module over %s: the pattern or the population is broken (%r)" % (how, counted))
        self.assertEqual(bad, [], "a numbered round that is not a ruled maintainer round (the maintainer's rounds %s, from MAINTAINER_ROUNDS; the population from %s); write "
                                  "the author's pass (\"pass P\", \"pass P's fixer pass\", \"the pass-P head\") or \"the maintainer's round N\" for a round a ruling exists "
                                  "for, and raise MAINTAINER_ROUNDS in the change that first credits a new ruling:\n%s"
                                  % (", ".join(str(x) for x in sorted(MAINTAINER_ROUNDS)), how, "\n".join(bad)))

    def test_the_form_space(self):
        """The classifier over every spelling the family uses and every class this census reads: the family's own forms are
        enumerated by forms() and each numbered one is a FORM_CLASSES class (a spelling outside the enumeration is a refusal,
        not a silent read), no form is unclassifiable, and every class has red probes (uncredited at a ruled round, a credit one
        past the set) and green probes (a credit at the highest and the lowest ruled round), assembled at run time from
        MAINTAINER_ROUNDS because this module reads itself. Then the wrapped shapes, the plural list and the ranges (every
        number judged), the forms refused as unresolved (a continuation the list did not consume, a plural naming one number,
        punctuation between the word and a number), the unnumbered spellings, and the refusal reasons told apart."""
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
                # a plural probe carries a list (a plural naming one number is unclassifiable, refused below): after hi the list adds lo, after lo it adds hi
                tail, tail_lo = ((" and %d" % lo), (" and %d" % hi)) if plural else ("", "")
                red = ["%s%s%d%s" % (word, sep, hi + 1, tail), "%s %s%s%d%s" % (M, word, sep, hi + 1, tail), "the %s%s%d%s head" % (word, sep, hi, tail),
                       "(%s%s%d%s, tests-1)" % (word, sep, lo, tail_lo), "%s %s%s%d and %d" % (M, word, sep, lo, hi + 1)]
                green = ["%s %s%s%d%s" % (M, word, sep, hi, tail), "%s %s%s%d%s" % (M, word, sep, lo, tail_lo), "%s %s%s%d%s's tests-3" % (M, word, sep, lo, tail_lo),
                         "(%s %s%s%d%s)" % (M, word, sep, hi, tail), "The %s %s%s%d%s ruled" % (M[4:], word, sep, hi, tail)]
                self.assertEqual([s for s in red if not offences(s)], [], "a refused form read as clean")
                self.assertEqual([s for s in green if offences(s)], [], "an allowed form read as an offence")
        # the wrapped shapes: the qualifier and the number split by a line break, a comment marker on the next line
        self.assertEqual(offences("... (%s %s\n    %d, correctness-1: the bound deleted" % (M, R, lo)), [], "a credit wrapped at the number is one credit")
        self.assertEqual(offences("# ... (the\n    # maintainer's %s %d found it" % (R, hi)), [], "a credit wrapped at the qualifier, a comment marker between, is one credit")
        self.assertEqual([ln for ln, _, _ in offences("a\nb\n# the %s\n# %d head" % (R, hi + 1))], [4], "a wrapped uncredited round is an offence at the line its number sits on")
        self.assertEqual([ln for ln, _, _ in offences("%s %s\n%d\n" % (M, R, hi + 1))], [2], "a wrapped credit to an unruled round is an offence at the number's line")
        # the plural list and the ranges: every number judged, a range's endpoints standing for it
        self.assertEqual(len(offences("%s %ss %d and %d" % (M, R, lo, hi + 1))), 1, "a credited list with one unruled number is one offence")
        self.assertEqual(offences("%s %ss %d to %d" % (M, R, lo, hi)), [], "a credited range inside the set is clean")
        self.assertEqual(len(offences("%ss %d and %d were held" % (R, lo, hi))), 1, "an uncredited list is one offence, at the list")
        for rng in ("%d-%d", "%d–%d", "%d/%d", "%d through %d", "%d thru %d", "%d, %d"):
            with self.subTest(range=rng):
                self.assertIn("no ruling exists for that maintainer round (%d)" % (hi + 1), offences("%s %ss %s" % (M, R, rng % (lo, hi + 1)))[0][2],
                              "a credited range one past the set is an offence naming the number past it (pass 11's fixer pass: the range's second number was dropped unread)")
                self.assertEqual(offences("%s %ss %s" % (M, R, rng % (lo, hi))), [], "a credited range inside the set is clean")
                self.assertEqual(forms("%ss %s" % (R, rng % (lo, hi)))[0][3], [lo, hi], "every number of the range is read")
        # the forms refused as unresolved: a continuation the list did not consume, a plural naming one number, punctuation or markup before the number
        for s in ("%ss %d; %d" % (R, lo, hi + 1), "%s %d: %d findings" % (R, hi, hi + 1), "%s %s %d, %d findings" % (M, R, hi, hi + 1), "%s %d, %d" % (R, lo, hi),
                  "%s %ss %d" % (M, R, hi), "%ss %d" % (R, hi),
                  "%s: %d" % (R, hi + 1), "%s %s: %d" % (M, R, hi + 1), "%s (%d)" % (R, hi + 1), "%s **%d**" % (R, hi + 1), "%s `%d`" % (R, hi + 1), '%s "%d"' % (R, hi + 1), "%s.%d" % (R, hi)):
            with self.subTest(unresolved=s):
                self.assertEqual([k for _, _, k, _ in forms(s)], ["unclassifiable"], "a form the census did not resolve is unclassifiable, never numbered or unread: %r" % (s,))
                self.assertIn("cannot classify", offences(s)[0][2])
        # the comma is the plural's alone: a count after a credited singular is refused as the continuation the list did not consume, never
        # as a credit to a round of the count's number (pass 11's closing fixer pass), and the plural's comma list is still every number judged
        self.assertIn("a further number after a run the list did not consume", offences("%s %s %d, %d findings" % (M, R, hi, hi + 1))[0][2])
        self.assertEqual(forms("%s %ss %d, %d" % (M, R, lo, hi))[0][3], [lo, hi], "the plural's comma list is read whole")
        # the unnumbered spellings are not read (the keyword-argument spelling and the rN path stems among them, stated in the docstring)
        for s in ("%ss=40" % R, "%ss=1" % R, "in 1 %ss" % R, "a typing %s" % R, "the two-%s convergence bound" % R, "in its second %s" % R, "_commands_a%s_the_recorder" % R,
                  "%s(t_dead - t0, 2)" % R, "spaces-a%s-dots" % R, "rulings-r1.md", "the boot a%s it" % R, "each %s of planting" % R, "a typing %s\n# visits" % R,
                  "%s_labels" % R, "the %s-trip" % R, "the %s's own" % R, "a %s of 3 drives" % R, "r6-margin/lab-head2.log", "r10/lab-ci9.log", "%s_labels.py:66" % R):
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
