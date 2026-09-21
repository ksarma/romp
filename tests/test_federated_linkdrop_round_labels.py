#!/usr/bin/env python3
"""The link-drop lab family's comments credit a maintainer round only where a ruling exists: this branch's guard, the first
caller of the shared rule (the author's pass 10, 2026-09-20; rewritten in pass 11, 2026-09-21, to read nothing outside the
repository, the maintainer's round 6, and then to call tests/review_round_labels_rule.py, the maintainer's ruling of 2026-09-21
on the three per-branch guards).

A PER-BRANCH GUARD, DELETED AT LANDING. Two numberings meet in the family's comments, docstrings and messages: the MAINTAINER's
rounds on PR 857 are the rulings the reviewer filed (the maintainer's rounds 1 to 6 at this writing); the AUTHOR's passes are
the build-and-verify passes before, between and after them, numbered 1 to 11 by the PR body's convention paragraph, which maps
the pipeline's commit labels to them. Before pass 10 the tree said "round N" in the author's pipeline's own numbering, which
matched neither, and 47 lines credited a sixth round no ruling then existed for; the sweep gave every mention its referent (the
maintainer's round N, or the author's pass P), and this module keeps it so over the lines this branch adds. Its job is done
when the branch lands (the lines it vetted are right by then, and the next branch's guard vets the next additions), so it is
deleted at landing. The RULE it applies, the form space of a numbered-round mention and what credits one, lives ONCE in
tests/review_round_labels_rule.py: three branches (PRs 821, 857 and 860) each wrote a guard and the three disagreed on the
spellings they read and on what credited one, so the maintainer ruled one helper holding the rule with each guard a caller,
riding this PR since it is likely to land first; 821's and 860's guards become callers of that helper in their next passes once
this lands. THE CALL is a few lines (test_no_mention_credits_a_round_the_maintainer_never_held): this module supplies the
POPULATION, its ROUNDS and its AUTHOR FORM, and asserts the helper returns no offence.

THE ROUNDS. MAINTAINER_ROUNDS is a constant of this TREE: the rulings the maintainer had filed on PR 857 when pass 11 began,
derived 2026-09-21, and the author raises it in the same change that first credits a new round, so a credit to a round no
ruling exists for reds on every machine until the ruling exists and the constant says so. It is read from NOTHING outside the
repository (the maintainer's round 6 found the earlier module reading the reviewer's notes directory for the set, so the same
committed tree got two verdicts). AUTHOR_FORM is how the PR body spells the author's own work ("pass P", "pass P's fixer pass",
"the pass-P head"), named in the helper's refusal so the writer knows what to write.

THE POPULATION is the family's files, each read WHOLE at HEAD: the modules the glob FAMILY_GLOB names under this directory
(the sibling pin's own spelling, tests/test_federated_linkdrop_driver_bound.py's ledger pin; a family module named otherwise
escapes both, so the population is spelling-keyed and says so) plus the ledger entry ENTRY. The two other files this branch
adds, the helper and its test, are outside the glob and so outside this population, and are held clean another way: the
helper's own test pins by execution that neither text spells a numbered-round form (the rule credits no PR's round), which
is all this guard would ask of them. Their TEXT is the COMMITTED one (_show: `git show HEAD:<path>` through _git), the same
commit the premise below is checked against, so the verdict is a function of the commit and the same committed tree gets one
verdict on every machine whatever its checkout holds (pass 11's closing fixer pass: the earlier module read the checkout's
text against HEAD's premise, so a mislabel committed at HEAD and removed in the working tree read clean); an uncommitted
edit is judged once committed, and a plant that reds this module is committed in a scratch repository. Every line of them is
the branch's own because every file of them is ADDED over the branch's merge base with origin/main, and setUpModule verifies
that premise by git before any cell runs (scope(): `git diff --name-status <merge base> HEAD` over the population, every
file `A`). Where git cannot answer (no repository under the root, GIT_DIR pointed elsewhere, origin/main not fetched or no
merge base, as in CI's shallow checkout) the derivation of "this branch's own lines" is unavailable and the module SKIPS
with a reason naming what was unreachable, never substituting another population (the maintainer's rule of 2026-09-21, from
PR 860's guard: a wider population reds work the guard was never about); where git answers and NO file of the population is
added over the merge base while every one is already in the tree there, the family has landed (on the target branch itself
after the merge the merge base is HEAD, and a branch cut from it inherits the family), nothing here is this branch's own to
vet, this guard's job is done, and the module SKIPS saying so (pass 11's closing fixer pass: the earlier module refused on
that shape, and CI's checkout of a push to the target branch is that shape until the follow-up that deletes this module
lands, since the checkout action writes origin/<branch> at the pushed commit; its checkout of a pull request writes
refs/remotes/pull/N/merge and no origin/main, which is the first skip); where git answers and a file of the population is
not added while another is, or a file is neither added nor at the merge base (an uncommitted one), the module REFUSES,
naming the files, since a whole-file read would then judge other work's lines or uncommitted text. family() REFUSES, with
the derivation named, a glob that reads no module, a file of the population that is not in the tree, and this module outside
its own population (its path the parameter `me`, this module's own by default), and every cell reads the population through
it, so a selected run of any one cell gets the one stated refusal; _read refuses a file that is not in the tree the same
way, _show one git does not answer for at HEAD, and sibling_glob returns the reason when the pin's file or function is not
found. A cell reads the sibling pin's glob from that pin's source and runs it, holding the two populations equal, so a
family module the sibling sees and this census does not is a red.

THE TREE-ONLY PIN, kept from the maintainer's round 6 and adapted to the call: test_the_module_reads_nothing_outside_the_tree
pins over this module's own source by RESOLUTION and not by a list of spellings (pass 11's fixer pass: the first pin refused
four attribute names and one absolute-path shape, and `from os import environ`, `getattr(os, "environ")`, `os.getcwd()`, a
`..` constant and a drive-letter constant passed it; pass 11's closing fixer pass: the second pin resolved os by its literal
name alone, so os reached as another table module's attribute, a primitive bound to another name, one reached through
`__builtins__`, a second glob.glob, and _read's own join handed an absolute path all read outside the tree with it green): the
import table is closed (IMPORTS, module-level `import x` alone, dotted for the helper, no from-import and no alias); every
attribute chain rooted at a module of the table resolves to the longest import that prefixes it and its remainder is in
MEMBERS for that import, and every entry of MEMBERS is read (both ways per import, so a member the module does not read today
is refused by construction, whichever module it hangs off); a module of the table is read only as the root of such a chain;
every callee is a name or an attribute chain; every name called is a definition of this module or one of BUILTINS (held equal
both ways); the dunder names read are exactly DUNDERS; no attribute read is a dunder or str.format; no reflective or file
primitive is called or read but the one open() in _read and the one glob.glob in _family_modules, both of whose paths pass
_under, which REFUSES at run time, over the value, a path that is absolute or leaves the root (pinned by execution in
test_every_path_the_module_reads_is_under_the_tree); the one subprocess.run is inside _git, its command git under `-C root`,
and the population's text is read through _show alone, a git show at HEAD through _git: the census cell's call-graph CLOSURE
over this module's own definitions (every name it calls that is a definition here, followed transitively, _closure) holds
_show and _git and not _read, and no definition in it calls open(), so the pin holds what the cell REACHES and not what it
names (pass 11's second closing fixer pass: the earlier pin read the cell's direct callees, and a wrapper on the way to _read
kept it green while the census read the checkout); and no string constant is an absolute path, a home path, a `..` step or a
drive letter. The helper this module imports is
pinned the same way, by its own test module (tests/test_review_round_labels_rule.py: `import re` alone, no file read at all).
What this pin does not check, stated: git's own reads (its configuration and the environment it inherits, GIT_DIR among them,
which is how the skip road is driven), the standard library's own reads, and a method called on a value the module bound
itself. This module is imported as a member of the tests package (`python -m pytest` or `python -m unittest` from the
repository root), which is how `import tests.review_round_labels_rule` resolves.

No probe is spelled with a digit after the word in this docstring, since the module is in its own population and reads itself;
the helper's form space is pinned in its own test module.
"""
import ast
import glob
import os
import re
import subprocess
import unittest

import tests.review_round_labels_rule

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)

# the rulings the maintainer had filed on PR 857 when pass 11 began (the maintainer's rounds 1 to 6), derived 2026-09-21; the
# author raises it in the change that first credits a new round, and nothing outside the tree widens it
MAINTAINER_ROUNDS = frozenset({1, 2, 3, 4, 5, 6})
# how the PR body spells the author's own work, named in the helper's refusal of an uncredited round
AUTHOR_FORM = "the author's \"pass P\", \"pass P's fixer pass\" or \"the pass-P head\""
FAMILY_GLOB = "test_federated_linkdrop*.py"   # the sibling pin's spelling, held equal to it by test_the_population_is_the_trees_and_the_sibling_pins
ENTRY = "upstream/2026-09-19-tests-federated-linkdrop-served.md"
SIBLING_PIN = ("tests/test_federated_linkdrop_driver_bound.py", "test_the_ledger_entry_names_every_module_of_this_family")
MAIN = "origin/main"   # the branch's target: the fork's main, the merge base's other side
PACKAGE = "tests/__init__.py"   # a file of the tree at the merge base that this branch does not add: the partial road's probe in scope()
# the tree-only pin: the closed import table of this module (dotted for the helper); every attribute chain it reads on each
# import of the table (held equal both ways per import, so a read the module does not make today, os.environ, os.getcwd,
# glob.os, unittest.loader, is refused by construction, not by a list of the names to refuse); the builtins it calls and the
# module-level dunder names it reads, closed the same way; and the primitives it neither calls nor reads, but the one open()
# inside _read
IMPORTS = ("ast", "glob", "os", "re", "subprocess", "tests.review_round_labels_rule", "unittest")
MEMBERS = {"ast": ("Attribute", "Call", "ClassDef", "Constant", "FunctionDef", "Import", "ImportFrom", "Load", "Name", "iter_child_nodes", "parse", "unparse", "walk"),
           "glob": ("glob",),
           "os": ("pardir", "path.commonpath", "path.dirname", "path.isabs", "path.isfile", "path.join", "path.realpath", "path.relpath", "sep"),
           "re": ("match", "search"),
           "subprocess": ("TimeoutExpired", "run"),
           "tests.review_round_labels_rule": ("FORM_CLASSES", "form_class", "forms", "mentions", "offences"),
           "unittest": ("SkipTest", "TestCase", "main")}
BUILTINS = ("AssertionError", "all", "frozenset", "isinstance", "len", "list", "max", "next", "range", "reversed", "set", "sorted", "str")
DUNDERS = ("__file__", "__name__")
PRIMITIVES = ("open", "getattr", "setattr", "delattr", "hasattr", "__import__", "eval", "exec", "compile", "vars", "globals", "locals")


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


def _git(args, root):
    """git's stdout under `root` (the one subprocess.run of this module: git, `-C root`), or None when git is absent, times out
    or fails (no repository, a missing ref, a shallow checkout)."""
    try:
        p = subprocess.run(["git", "-C", root] + list(args), capture_output=True, text=True, encoding="utf-8", timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return p.stdout if p.returncode == 0 else None


def scope(files, root=ROOT, main=MAIN):
    """Whether every file of `files` is ADDED over the merge base of HEAD with `main`, so its whole text is the branch's own
    added lines: ("skip", what was unreachable) when git cannot answer for HEAD under `root`, for `main` or for the merge base
    (the derivation is unavailable: the caller skips, never reading another population); ("skip", why) when git answers, NO
    file of `files` is added over the merge base and every one is in the tree at the merge base (the family has landed: on
    `main` itself after the merge the merge base is HEAD, and a branch cut from it inherits the family; nothing there is this
    branch's own to vet, so the caller skips saying its job is done); ("refuse", the files) when git answers and a file of
    `files` is not added while another is, or a file is neither added nor at the merge base (other work's lines, or an
    uncommitted file, under a whole-file read: the caller refuses, naming them); ("ok", the derivation) otherwise."""
    if _git(["rev-parse", "--verify", "HEAD^{commit}"], root) is None:
        return "skip", "git does not answer for HEAD under the root (no repository there, or GIT_DIR points elsewhere), so this branch's own lines are not derivable"
    base = _git(["merge-base", main, "HEAD"], root)
    if base is None:
        return "skip", "no merge base of HEAD with %s is reachable (%s not fetched, as in a shallow checkout), so this branch's own lines are not derivable" % (main, main)
    base = base.strip()
    status = _git(["diff", "--name-status", "--no-renames", base, "HEAD", "--"] + list(files), root)
    there = _git(["ls-tree", "--name-only", "-r", base, "--"] + list(files), root)
    if status is None or there is None:
        return "skip", "git diff or git ls-tree against the merge base %s failed, so this branch's own lines are not derivable" % base[:9]
    added = set(line.split("\t", 1)[1] for line in status.splitlines() if line.startswith("A\t"))
    kept = [f for f in files if f not in added]
    if not added and all(f in set(there.splitlines()) for f in files):
        return "skip", ("no file of the population is added over the merge base %s of HEAD with %s and every one is in the tree there: the family has "
                        "landed (on %s itself the merge base is HEAD), so nothing here is this branch's own to vet and this guard's job is done" % (base[:9], main, main))
    if kept:
        return "refuse", ("a file of the population is not added over the merge base %s of HEAD with %s, so its whole text is not this branch's own lines "
                          "(other work's lines, or an uncommitted file, would be judged by a whole-file read): %r" % (base[:9], main, kept))
    return "ok", "every file of the population is added over the merge base %s of HEAD with %s (git diff --name-status)" % (base[:9], main)


def setUpModule():
    """The premise first: the population's files are this branch's own, by git. A skip names what was unreachable, or that the
    family has landed and this guard's job is done, and no cell runs; a refusal names the files that are not the branch's;
    nothing else is read in the derivation's place."""
    files, how = family()
    road, why = scope(files)
    if road == "skip":
        raise unittest.SkipTest("the round-labels guard skipped: %s (the population would have been %s)" % (why, how))
    if road == "refuse":
        raise AssertionError("the round-labels guard refuses to run: %s" % why)


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


def _show(rel, root=ROOT):
    """The COMMITTED text of a file of the population, `git show HEAD:<path>` through _git (its path relative to `root`, through
    _under's refusals of one that is absolute or leaves the root), so the text judged and the premise scope() checked are the
    same commit's; a stated refusal naming the file when git does not answer for it at HEAD (a file not committed there)."""
    _under(root, rel)
    text = _git(["show", "HEAD:" + rel], root)
    if text is None:
        raise AssertionError("%s is not readable at HEAD (git show under the repository root), so the committed text cannot be judged" % rel)
    return text


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


def _roots():
    """The first component of every import of the table: the names an attribute chain of this module may be rooted at."""
    return set(i.split(".")[0] for i in IMPORTS)


def _chains(tree):
    """Every attribute chain of `tree` rooted at a name of _roots(), outermost only, resolved to the longest import of IMPORTS
    that prefixes it: ({import: {its members read}}, the chains no import resolves, the imports read whole as a value), the
    reads the tree-only pin holds equal to MEMBERS, import by import."""
    parents = {c: p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}
    out, unresolved, whole = {m: set() for m in IMPORTS}, [], []
    for n in ast.walk(tree):
        if isinstance(n, ast.Attribute) and not (isinstance(parents.get(n), ast.Attribute) and parents[n].value is n):
            parts, q = [], n
            while isinstance(q, ast.Attribute):
                parts.append(q.attr)
                q = q.value
            if isinstance(q, ast.Name) and q.id in _roots():
                dotted = ".".join([q.id] + list(reversed(parts)))
                imp = max((i for i in IMPORTS if dotted == i or dotted.startswith(i + ".")), key=len, default=None)
                if imp is None:
                    unresolved.append((dotted, n.lineno))
                elif dotted == imp:
                    whole.append((dotted, n.lineno))
                else:
                    out[imp].add(dotted[len(imp) + 1:])
    return out, unresolved, whole


def _closure(fn, tree):
    """{name: its definition} for every definition of this module (a module-level def of `tree`) that `fn` reaches by a name call,
    transitively: the call graph's closure over the module's own definitions, so a pin over it holds what `fn` reaches and not
    what it names (a wrapper on the way to a reader is in it)."""
    defs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    out, todo = {}, [fn]
    while todo:
        for n in ast.walk(todo.pop()):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in defs and n.func.id not in out:
                out[n.func.id] = defs[n.func.id]
                todo.append(defs[n.func.id])
    return out


class RoundLabels(unittest.TestCase):
    maxDiff = None

    def test_the_ruled_rounds_are_tree_resident_and_contiguous_from_one(self):
        """MAINTAINER_ROUNDS is non-empty, contiguous from 1 and the only source of the legal set (the cells that take its
        bounds check it first, never max() over an empty set)."""
        self.assertTrue(MAINTAINER_ROUNDS, "MAINTAINER_ROUNDS is empty: the tree records no ruling at all")
        self.assertEqual(sorted(MAINTAINER_ROUNDS), list(range(1, max(MAINTAINER_ROUNDS) + 1)), "the rulings are numbered contiguously from 1: %r" % (sorted(MAINTAINER_ROUNDS),))

    def test_the_module_reads_nothing_outside_the_tree(self):
        """The same committed tree gets one verdict on every machine, pinned over this module's own source by RESOLUTION: every
        name the module reads is resolved to a binding the pin knows, and a read it cannot resolve is refused (the maintainer's
        round 6 found the earlier module reading the reviewer's notes directory; pass 11's fixer pass found the first pin keyed
        on four attribute names and one path shape; its closing fixer pass found the second resolving os by its literal name
        alone). The imports are exactly IMPORTS (module-level `import x`, dotted for the helper, no from-import, no alias, none
        inside a function or a class); every attribute chain rooted at a table root resolves to the longest import that
        prefixes it (a chain no import resolves, `tests.other`, is refused) and its remainder is in MEMBERS for that import,
        every entry of MEMBERS being read, both ways per import, so a member the module does not read today (os.environ,
        os.getcwd, glob.os, unittest.loader, subprocess.Popen, re.sre_compile) is refused by construction; a table module is
        read only as the root of such a chain, never handed on as a value, whole or by its import name; every callee is a name
        or an attribute chain (a subscript or a call as the callee is unresolved); every name called is a definition of this
        module or one of BUILTINS, held equal both ways; no primitive (PRIMITIVES) is called or read but exactly one open(),
        inside _read, whose argument is _under(root, rel), and the one glob.glob is inside _family_modules with its directory
        through _under; the one subprocess.run is inside _git and its command starts with git and `-C root`; the census cell's
        call-graph closure over this module's definitions (_closure: what the cell reaches by name calls, transitively) holds
        _show and _git and not _read, and no definition in it calls open() (pass 11's second closing fixer pass: the earlier
        pin read the cell's direct callees, so a wrapper over _read called from the cell read the checkout with it green);
        the dunder names read are exactly DUNDERS (so `__builtins__`, `__loader__` and `__spec__`, which reach the builtins and the file system,
        are refused); no attribute read is a dunder (`__class__`, `__globals__`, `__dict__`: reflection) or str.format or
        format_map, whose fields walk attributes by name inside a string the walk does not read; and no string constant is an
        absolute path, a home path, a `..` step or a drive letter. _under's refusals at run time are pinned by execution in
        test_every_path_the_module_reads_is_under_the_tree. What the pin does not check, stated: git's own reads (its
        configuration, the environment it inherits), the standard library's own reads (glob and re read no environment;
        os.path.realpath follows symlinks of the tree itself), a method called on a value the module bound itself (text.count,
        self.assertEqual: the values are made from the reads above), the helper's insides (its own test module pins them),
        and code that arrives by a road the table forbids, refused at the import, not read."""
        tree = ast.parse(_read(os.path.relpath(os.path.realpath(__file__), ROOT)))
        parents = {c: p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}
        imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        self.assertEqual([n.lineno for n in imports if isinstance(n, ast.ImportFrom)], [], "a from-import in the census module: a name bound past the import table is a road the pin cannot resolve")
        self.assertEqual([n.lineno for n in imports if n not in tree.body], [], "an import inside a function or a class: every import is module-level, so the table below is the whole table")
        self.assertEqual([a.asname for n in imports for a in n.names if a.asname], [], "an import under another name: the reads below resolve the module by its own name")
        self.assertEqual(sorted(a.name for n in imports for a in n.names), sorted(IMPORTS), "the census module's import table is exactly IMPORTS: a module outside it may read the environment, the home or the working directory")
        self.assertEqual(sorted(MEMBERS), sorted(IMPORTS), "MEMBERS holds one table per import of IMPORTS")
        chains, unresolved, whole = _chains(tree)
        self.assertEqual(unresolved, [], "an attribute chain rooted at a table root that no import of the table resolves: %r" % (unresolved,))
        self.assertEqual(whole, [], "an import of the table read whole as a value (assigned, passed, subscripted) is a name the pin cannot follow: %r" % (whole,))
        for m in IMPORTS:
            with self.subTest(module=m):
                self.assertEqual(sorted(chains[m] - set(MEMBERS[m])), [], "a read on %s this module does not make today (a member outside MEMBERS may reach the environment, the home or the working directory, os.environ and glob.os among them): %r" % (m, sorted(chains[m] - set(MEMBERS[m]))))
                self.assertEqual(sorted(set(MEMBERS[m]) - chains[m]), [], "a member of MEMBERS[%r] no longer read: the table is held equal to the module's reads both ways" % m)
        bare = [(n.id, n.lineno) for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id in _roots() and not (isinstance(parents.get(n), ast.Attribute) and parents[n].value is n)]
        self.assertEqual(bare, [], "a root of the table read as a value (assigned, passed, subscripted) is a name the pin cannot follow: %r" % (bare,))
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
        self.assertEqual([(ast.unparse(n.func), n.lineno) for n in calls if not isinstance(n.func, (ast.Name, ast.Attribute))], [], "a callee that is neither a name nor an attribute chain (a subscript, a call) is unresolved")
        defs = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        named = {n.func.id for n in calls if isinstance(n.func, ast.Name)}
        self.assertEqual(sorted(named - defs - set(BUILTINS) - {"open"}), [], "a name called that is neither a definition of this module nor one of BUILTINS is unresolved: %r" % (sorted(named - defs - set(BUILTINS) - {"open"}),))
        self.assertEqual(sorted(set(BUILTINS) - named), [], "a builtin in BUILTINS this module no longer calls: the tuple is held equal to the module's calls both ways")
        self.assertEqual(sorted(set(BUILTINS) & (defs | set(PRIMITIVES))), [], "BUILTINS names a definition of this module or a primitive")
        cells = [m for n in tree.body if isinstance(n, ast.ClassDef) for m in n.body if isinstance(m, ast.FunctionDef)]
        census = next(m for m in cells if m.name == "test_no_mention_credits_a_round_the_maintainer_never_held")
        closure = _closure(census, tree)
        self.assertNotIn("_read", closure, "the census cell reaches _read (the checkout's text) through its call graph %r: the population's text is read at HEAD "
                                           "alone, through _show, and a wrapper or a helper on the way to _read reads the checkout with a direct-callee pin green (pass "
                                           "11's second closing fixer pass); this pins WHERE the read is made, and the behaviour, a mislabel committed at HEAD read with "
                                           "the checkout restored, is driven by execution in a scratch repository outside the tree (the pass record), since driving "
                                           "it here would mean committing here" % (sorted(closure),))
        self.assertIn("_show", closure, "the census cell reaches no _show: the population's text is read through _show, git show at HEAD through _git with the path "
                                        "through _under's refusals, and through nothing else: %r" % (sorted(closure),))
        self.assertIn("_git", closure, "the census cell reaches no _git: the text it judges is not the committed one: %r" % (sorted(closure),))
        opened = [(d, n.lineno) for d in sorted(closure) for n in ast.walk(closure[d]) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "open"]
        self.assertEqual(opened, [], "a definition the census cell reaches calls open(): a file of the checkout read on the way to the verdict: %r" % (opened,))
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
        runs = [n for n in calls if isinstance(n.func, ast.Attribute) and ast.unparse(n.func) == "subprocess.run"]
        git = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_git")
        self.assertEqual([n.lineno for n in runs], [n.lineno for n in ast.walk(git) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and ast.unparse(n.func) == "subprocess.run"], "every subprocess.run is inside _git: at lines %r" % ([n.lineno for n in runs],))
        self.assertEqual(len(runs), 1, "_git holds exactly one subprocess.run")
        self.assertEqual(ast.unparse(runs[0].args[0]), "['git', '-C', root] + list(args)", "the one program this module runs is git under the root it was handed: %s" % ast.unparse(runs[0].args[0]))
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
        cell), _read over a file that is not there, _show over one not committed at HEAD (and the entry's committed text read
        through it), and sibling_glob over a pin whose file is missing, each a stated refusal
        naming what it could not read, never a bare exception or an empty census. Then scope()'s roads by execution over the
        tree: the population is added over the merge base (the road setUpModule took to reach this cell), a main that is no
        ref is a skip naming it, HEAD as the main (the merge base HEAD, nothing added over it, every file already there: the
        landed shape, CI's checkout of a push to the target branch) is a skip saying this guard's job is done, the population
        plus a file of the tree that predates the merge base (PACKAGE) is a refusal naming that file alone, a population of
        that file alone is the landed skip, and a file that is neither added nor at the merge base (an uncommitted one) is a
        refusal; the road where git does not answer at all is driven outside the tree (GIT_DIR pointed at nothing in a
        scratch copy), since driving it here would mean writing outside the tree."""
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
        with self.assertRaises(AssertionError) as unshown:
            _show("upstream/no-such-entry.md")
        self.assertEqual(str(unshown.exception), "upstream/no-such-entry.md is not readable at HEAD (git show under the repository root), so the committed text cannot be judged")
        self.assertTrue(_show(ENTRY).startswith("---"), "the entry's committed text is read at HEAD through git show")
        self.assertEqual(sibling_glob(pin=("tests/no_such_module.py", SIBLING_PIN[1])), (None, "tests/no_such_module.py is not in the tree (read relative to the repository root)"))
        self.assertEqual(sibling_glob(pin=(SIBLING_PIN[0], "no_such_function"))[0], None)
        road, why = scope(files)
        self.assertEqual(road, "ok", "setUpModule reached this cell, so the population is the branch's own: %s" % why)
        self.assertIn("added over the merge base", why)
        road, why = scope(files, main="refs/no-such-ref")
        self.assertEqual(road, "skip", why)
        self.assertIn("no merge base of HEAD with refs/no-such-ref is reachable", why)
        road, why = scope(files, main="HEAD")
        self.assertEqual(road, "skip", "the landed shape (the merge base HEAD, nothing added, every file there) is a skip, not a refusal: %s" % why)
        self.assertIn("no file of the population is added over the merge base", why)
        self.assertIn("this guard's job is done", why)
        road, why = scope(files + [PACKAGE])
        self.assertEqual(road, "refuse", why)
        self.assertIn(PACKAGE, why)
        self.assertTrue(all(f not in why for f in files), "the refusal names the file that is not added and none of the added ones: %s" % why)
        self.assertEqual(scope([PACKAGE])[0], "skip", "a population wholly at the merge base is the landed skip")
        road, why = scope(files + ["tests/no_such_census.py"])
        self.assertEqual(road, "refuse", why)
        self.assertIn("tests/no_such_census.py", why)
        self.assertEqual(scope(["tests/no_such_census.py"])[0], "refuse", "a file neither added nor at the merge base is not landed: refused")

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
        """THE CALL. Every numbered round of the family is, by the shared rule, a credit in the maintainer's form to a round in
        MAINTAINER_ROUNDS, and every form is classifiable; every numbered form the family uses is a class the rule's pin holds
        probes for (a spelling outside that enumeration is a refusal, not a silent read). The guard against a vacuous census
        counts the MODULES' mentions, not the entry's (the entry carries one credit, which is what satisfied the guard over an
        empty module population before family() refused it). Each file's text is the COMMITTED one, _show at HEAD."""
        files, how = family()
        bad, seen, counted, outside = [], 0, {}, {}
        for rel in files:
            text = _show(rel)
            counted[rel] = len(tests.review_round_labels_rule.mentions(text))
            if rel != ENTRY:
                seen += counted[rel]
            bad += ["%s:%d: %r (%s)" % o for o in tests.review_round_labels_rule.offences(text, MAINTAINER_ROUNDS, rel, AUTHOR_FORM)]
            for line, spelled, kind, _ in tests.review_round_labels_rule.forms(text):
                if kind == "numbered" and tests.review_round_labels_rule.form_class(spelled) not in tests.review_round_labels_rule.FORM_CLASSES:
                    outside.setdefault(tests.review_round_labels_rule.form_class(spelled), []).append("%s:%d %r" % (rel, line, spelled))
        self.assertGreater(seen, 0, "the census read no numbered round in any module over %s: the pattern or the population is broken (%r)" % (how, counted))
        self.assertEqual(outside, {}, "a numbered spelling the rule's form space does not enumerate (add its class to the helper's FORM_CLASSES with its probes): %r" % (outside,))
        self.assertEqual(bad, [], "a numbered round that is not a ruled maintainer round (the maintainer's rounds %s, from MAINTAINER_ROUNDS; the population from %s); write "
                                  "the author's pass (\"pass P\", \"pass P's fixer pass\", \"the pass-P head\") or \"the maintainer's round N\" for a round a ruling exists "
                                  "for, and raise MAINTAINER_ROUNDS in the change that first credits a new ruling:\n%s"
                                  % (", ".join(str(x) for x in sorted(MAINTAINER_ROUNDS)), how, "\n".join(bad)))


if __name__ == "__main__":
    unittest.main()
