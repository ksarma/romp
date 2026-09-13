#!/usr/bin/env python3
"""What the Slice 6 build note of plans/markdown-viewer.md says of the branch's history holds in the history.

The note's head describes the branch's base: cut from 4a3e18664 (Slice 8's head), rebased onto main 0bf0465b4, with
the fork's main while the build ran, 929ae86e1, differing from 4a3e18664 in six of the files the slice changes. The
build's records had said every file the slice changes is byte-identical at those two trees; the review's round 1
corrected that and wrote, in the correcting sentence, that the three commit messages claiming the identity claim it
for the files they touch and that none of the three touches the six. Both were false of 579fc2852, which changes
three of the six (feed.css, fileview-parity.test.ts and styles.css) and claims the identity for file-view.ts alone;
the review's round 2 corrected the sentence. This module reads the sentence and checks each claim it makes against
`git`: the six files that differ, the file each message names beside "byte-identical", the identity itself over the
files the note says a message claims it for, and what each commit changes among the six.

The history is read from the repository this file sits in, through `git -C`. The commits are the branch's own and
the trees are the fork's, so a clone that lacks one of them (a shallow checkout, which CI's default checkout is; a
repository the note was ported into) skips with the sha named, and a tree that is not a checkout skips too; every
other git failure is an error, never a skip. The premise test needs no history and fails first if the note's
phrasing changes so that the reader finds nothing. Synthetic: the repo's own text and history only.
"""
import os
import re
import subprocess
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
PLAN = os.path.join("plans", "markdown-viewer.md")
NOTE = "Slice 6"

# The trees the note's head names; the premise test checks the note against these constants.
MAIN_WHILE_BUILDING = "929ae86e1"  # the fork's main while the build ran
CUT_FROM = "4a3e18664"  # Slice 8's head, the head the branch was cut from
BASE = "0bf0465b4"  # main after PR 752, the branch's base since the rebase
CONSOLIDATION = "d91f0c19d"  # the build's consolidation commit; its diff from BASE is the files the slice changes

SENTENCE_LEAD = "commit messages that claim the identity"
SENTENCE_END = "The rebase re-minted every commit"
SIX_LEAD = re.compile(r"in six of them \(([^)]+)\)")
NONE_TOUCH = "none of them touching the six"
HEDGE = "byte-identical"
EVERY = "every file the commit touches"

SHA = r"(?=[0-9a-f]*\d)[0-9a-f]{7,40}"  # a short sha; at least one digit, so a word spelt in a to f is not one
SHA_LIST = r"%s(?:(?:, | and )%s)*" % (SHA, SHA)
FILE = r"[\w./-]+\.(?:ts|py|css|md|mjs)"
TOUCHED = r"(?:every file (?:it|they) touch(?:es)?|the files (?:it|they) (?:themselves )?touch(?:es)?)"
# `579fc2852 for file-view.ts`, `0f31a8759 and 9b1cf0d31 for every file they touch`
SCOPE_AFTER = re.compile(r"\b(%s)(?: claims? it)? for (%s|%s)" % (SHA_LIST, FILE, TOUCHED))
# `for the files they themselves touch (579fc2852, 0f31a8759 and 9b1cf0d31)`
SCOPE_BEFORE = re.compile(r"for (%s) \((%s)\)" % (TOUCHED, SHA_LIST))
# `579fc2852 for file-view.ts (the commit also changes feed.css, fileview-parity.test.ts and styles.css, three of
# the six`
AMONG_SIX = re.compile(r"\b(%s) for %s \((?:the commit|it) also changes ([^)]*?), \w+ of the six" % (SHA, FILE))
NOT_A_REPOSITORY = "not a git repository"


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _flat(text):
    """Collapse hard wraps so a reading survives a rewrap."""
    return re.sub(r"\s+", " ", text).strip()


def _section(md, name):
    """The `### <name>` section's body, flattened."""
    m = re.search(r"^### %s[^\n]*\n(.*?)(?=^#{2,3} |\Z)" % re.escape(name), md, re.S | re.M)
    assert m, "the plan has no %s section" % name
    return _flat(m.group(1))


def _path(name):
    """The repo path a note's mention names: `this plan`, a path, or a bare ui/webview file."""
    name = name.strip()
    if name == "this plan":
        return PLAN
    return name if "/" in name else "ui/webview/" + name


def _names(listing):
    """`a, b and c` as repo paths."""
    parts = listing.split(", ")
    parts[-1:] = parts[-1].split(" and ")
    return [_path(p) for p in parts if p.strip()]


def _six(section):
    m = SIX_LEAD.search(section)
    assert m, "the note does not name the six files in the form `in six of them (...)`"
    return set(_names(m.group(1)))


def _sentence(section):
    i = section.find(SENTENCE_LEAD)
    assert i >= 0, "the note has no sentence on the %s" % SENTENCE_LEAD
    j = section.find(SENTENCE_END, i)
    assert j > i, "the sentence on the commit messages is not followed by %r" % SENTENCE_END
    return section[i:j]


def _claims(sentence):
    """(scope, among, none_touch) read from the sentence: scope maps each sha to the repo path its message is said
    to claim the identity for, or to EVERY; among maps a sha to the files of the six the note says it changes;
    none_touch is the set of shas the note says touch none of the six."""
    scope = {}
    for m in SCOPE_AFTER.finditer(sentence):
        what = m.group(2)
        for sha in re.findall(SHA, m.group(1)):
            scope[sha] = _path(what) if re.fullmatch(FILE, what) else EVERY
    for m in SCOPE_BEFORE.finditer(sentence):
        for sha in re.findall(SHA, m.group(2)):
            scope[sha] = EVERY
    among = {m.group(1): set(_names(m.group(2))) for m in AMONG_SIX.finditer(sentence)}
    none_touch = set(scope) if NONE_TOUCH in sentence else set()
    return scope, among, none_touch


def _run(*args):
    """git at ROOT. Skips the caller only when git is not installed or ROOT is not in a repository."""
    try:
        proc = subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        raise unittest.SkipTest("git is not installed; the history the note names cannot be read")
    if proc.returncode != 0 and NOT_A_REPOSITORY in proc.stderr:
        raise unittest.SkipTest("not a git checkout (git exited %d: %s)" % (proc.returncode, proc.stderr.strip()))
    return proc


def _git(*args):
    proc = _run(*args)
    if proc.returncode != 0:
        raise AssertionError("git %s exited %d at %s:\n%s"
                             % (" ".join(args), proc.returncode, ROOT, proc.stderr.strip()))
    return proc.stdout


def _reachable(*shas):
    """Skips when a sha the note names is not in this clone: a shallow checkout, or a repository the note was
    ported into. Any other failure of git is an error."""
    for sha in shas:
        proc = _run("cat-file", "-e", sha + "^{commit}")
        if proc.returncode != 0:
            raise unittest.SkipTest("%s is not in this clone (shallow, or not the fork), so the note's account of it "
                                    "cannot be read: %s" % (sha, proc.stderr.strip()))


def _touched(sha):
    return set(_git("show", "--format=", "--name-only", sha).split())


def _differing(paths):
    """The files among `paths` whose bytes differ between the two trees the note compares."""
    if not paths:
        return set()
    return set(_git("diff", "--name-only", MAIN_WHILE_BUILDING, CUT_FROM, "--", *sorted(paths)).split())


def _hedge(sha):
    """The parenthetical of the commit's message that carries its byte-identity claim."""
    message = _flat(_git("log", "-1", "--format=%B", sha))
    m = re.search(r"\(([^()]*%s[^()]*)\)" % HEDGE, message)
    assert m, "%s's message has no parenthetical saying %r" % (sha, HEDGE)
    return m.group(1)


class TheNoteSaysEnough(unittest.TestCase):
    """The premise, read without git: the note names the trees this module reads and states the claims it holds."""

    def test_the_note_names_the_trees_the_six_and_a_scope_for_each_of_three_commits(self):
        section = _section(_read(PLAN), NOTE)
        for sha in (MAIN_WHILE_BUILDING, CUT_FROM, BASE, CONSOLIDATION):
            self.assertIn(sha, section, "the note names %s" % sha)
        self.assertEqual(len(_six(section)), 6)
        scope, among, none_touch = _claims(_sentence(section))
        self.assertEqual(len(scope), 3, "the sentence names three commits and the files each claims: %r" % scope)
        self.assertTrue(among or none_touch,
                        "the sentence says what each commit changes among the six, or that none does")


class TheHistoryAgrees(unittest.TestCase):
    """Each claim the sentence makes, checked against git."""

    @classmethod
    def setUpClass(cls):
        section = _section(_read(PLAN), NOTE)
        cls.six = _six(section)
        cls.scope, cls.among, cls.none_touch = _claims(_sentence(section))
        _reachable(MAIN_WHILE_BUILDING, CUT_FROM, BASE, CONSOLIDATION, *sorted(cls.scope))

    def test_the_six_files_the_note_names_are_the_ones_that_differ_between_the_two_trees(self):
        slice_files = set(_git("diff", "--name-only", BASE, CONSOLIDATION).split())
        self.assertEqual(_differing(slice_files), self.six)

    def test_each_message_hedges_its_identity_claim_to_the_files_the_note_says(self):
        for sha, what in sorted(self.scope.items()):
            hedge = _hedge(sha)
            if what == EVERY:
                self.assertIn("this commit touches", hedge,
                              "%s claims the identity for every file it touches: %r" % (sha, hedge))
            else:
                self.assertIn(os.path.basename(what), hedge, "%s claims the identity for %s: %r" % (sha, what, hedge))

    def test_the_files_the_note_says_a_message_claims_identical_are_identical(self):
        for sha, what in sorted(self.scope.items()):
            touched = _touched(sha)
            files = touched if what == EVERY else {what}
            self.assertLessEqual(files, touched, "%s changes the file it claims the identity for" % sha)
            self.assertEqual(_differing(files), set(),
                             "%s is said to claim the identity for %s, and those files differ between %s and %s"
                             % (sha, "every file it touches" if what == EVERY else what,
                                MAIN_WHILE_BUILDING, CUT_FROM))

    def test_what_the_note_says_a_commit_changes_among_the_six_is_what_it_changes(self):
        for sha in sorted(self.none_touch):
            self.assertEqual(_touched(sha) & self.six, set(), "%s is said to touch none of the six" % sha)
        for sha, said in sorted(self.among.items()):
            self.assertEqual(_touched(sha) & self.six, said,
                             "%s is said to change %r of the six" % (sha, sorted(said)))


if __name__ == "__main__":
    unittest.main()
