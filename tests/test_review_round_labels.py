#!/usr/bin/env python3
"""Every round label in the lazy-panes branch's own lines credits a round the reviewer held (the author's pass 8, 2026-09-21).

TEMPORARY. This module is a per-branch guard over the mentions this branch adds over its merge base, deleted when the PR
lands, its job done (the lines it vetted are right by then; the next branch's guard vets the next additions). The rule it
implements, the form space of a numbered-round mention and what credits one, is to live once in a shared helper under tests/
that PR 857 lands; after that this module becomes a few-line caller of that helper with its own population and its own
rounds (the maintainer's ruling of 2026-09-21, which puts the sibling guards on PRs 857 and 860 on the same helper, so three
guards are one rule and not three requirements).

THE PROPERTY. A label credits a round to someone. The REVIEWER's rounds on this PR are numbered 1 to N in the review
notes, outside this repository; REVIEWER_ROUNDS below is the number of the highest ruling the reviewer has filed (the PR
body's convention paragraph lists the same rounds by head and date), a tree-resident constant the author raises when a
ruling lands. It is not a count of files (the notes hold an addendum beside one round's ruling and another round's
ruling in a sibling directory) and never a read of the notes directory: that is a path outside the tree, absent on CI
and on a contributor's clone, so such a read would fail for nobody's defect or pass over an empty set of legal rounds.
The AUTHOR's builds are passes ("pass N", "pass N's head", "the author's pass-N verify"), never rounds. Over the
branch's own lines, then, every token of the shape round-N is classified into one of five RULES:

- credit: a round credited to the reviewer or the maintainer, in ANY spelling the branch uses, "review round N" (the
  early convention), "the reviewer's round-N", "the maintainer's round N", "review round N closeout", or a bare round
  carrying a suffix that names the reviewer's artifact ("the round-N fixlist", "round N's ruling", "the round-N
  refuter", "the round-N verdict", "the round-N addendum"). Accepted when N is in 1..REVIEWER_ROUNDS, refused above it
  (a range of rounds, "from 1 to N", is judged by its largest number). The author's commit labels ("Review round N:", "Review
  round N fixes:") are the one accepted bare form, and only in commit subjects, which this module does not read (the
  subjects stand as pushed, the branch is never rebased, and the PR body maps each label family to its pass); in file
  text that spelling is a credit like any other.
- bare: a round with no credit and no artifact suffix ("since round N", "round N's head", "Round N showed"). Refused:
  the author's builds are passes, so a bare round credits no one and reads as a reviewer's round it may not be.
- lettered: a letter after the number (the spelling the author's pass 4b carried before pass 7). Refused: a pass.
- verify: a verify labelled as a round ("round N verify", "round N's verify", in any credit spelling). Refused: a
  verify is the author's verifier, never a review round.
- unclassifiable: a possessive before the round that names neither the reviewer nor the maintainer ("the author's
  round N", "the fixer's round-N"). Refused: an unknown credit is a credit to no one the census knows.

ROUNDS VERSUS PASSES, per form (the PR body's convention paragraph is the other copy of this gloss). "review round 1"
to "review round 4" in the branch's added lines are the author's passes 1 to 4 under the early convention (pass 3 took
the reviewer's round 2, pass 4 the reviewer's round 3, and the finding ids beside them are that round's fixlist's);
"review round 2 closeout" is pass 2, the closeout before the reviewer's round 2. A "verdict 1" beside such a label
numbered 4 (ui/webview/render.ts, skeleton-tabs.ts, skeleton-tabs.test.ts and skeleton-tabs-wiring.test.ts) names the
fourth-round section of the author's own review note (that note counts the author's verify rounds), the verify report
on pass 3 whose lift fix landed alone ahead of the reviewer's round 3, and "verdict 1" is that report's numbering, not
a reviewer's fixlist id; the body counts that report in pass 3. "the reviewer's round-N", "the maintainer's round N" and the artifact suffixes name the reviewer's
round N, the rulings file of that number. Since pass 8 the branch's own lines carry no bare round: every one was
reworded to "pass N" (or, where the sentence credited the reviewer, to "the reviewer's round N").

THE FORM SPACE is derived, not listed. FORM_SPACE is read off the population itself: every distinct (credit word,
suffix) spelling the branch's lines use around the word round. test_the_form_space plants a credit to
REVIEWER_ROUNDS + 1 in EACH spelling found, and in the five canonical spellings whether or not the branch uses them,
and asserts every plant is refused, so a spelling the census cannot read is a red and not a gap (the pass-7 module
refused the retired spelling "review round N" alone, and the spelling that same pass introduced, "the reviewer's
round-N", passed its numeric rule). The probes derive their number from REVIEWER_ROUNDS, so raising the constant when
a ruling lands keeps the module green (the rebind case executes that at two other values).

THE POPULATION is derived, not listed: the branch's ADDED lines, `git diff -U0 <merge base with origin/main> HEAD`, the
COMMITTED head, every changed file's added lines, kernel/kernel.py's like any other file's, tagged or not (the `[fork]`
tag is no longer a guard or an input; the file's pre-existing lines are the project's and unread). Nothing else is read:
an uncommitted edit and an untracked file are outside the population until they are committed, so a scratch note or an
edit in progress in the checkout moves nothing, and the plant that reds this module is committed first. A file the branch
deletes has no added lines and is outside the population (`--diff-filter=d`). The diff is read config-independently:
fixed prefixes (`--src-prefix=a/ --dst-prefix=b/`; a caller's diff.mnemonicPrefix or diff.noprefix would otherwise
rename or drop the `+++ b/` header the reader keys on), no external diff, rename detection on (`--find-renames`, so a
renamed file contributes its edited lines alone whatever diff.renames says). The read is per added line: a label wrapped
across two lines, a `round #N`, an ordinal (`Nth round`) or a spelled-out number is outside the token shape and unread; a
possessive written with a typographic apostrophe is read as its ASCII form. This module reads itself, so every refused
form it needs as a probe is assembled at run time and the prose above spells numbers as N.

THREE ROADS, one of which runs, the road named in every assertion message (test_the_three_roads drives each road's
derivation by execution from the derived road, the scratch-repository test the arm with no merge base, and
test_a_road_off_the_derived_one_is_a_skip the skip itself):
- derived: git answers for HEAD and origin/main, the merge base is derivable, and the range base..HEAD carries this
  module's introducing commit (BRANCH_COMMIT), so HEAD is the lazy-panes branch or a descendant of it that has not
  merged (a descendant's own added lines are read under this PR's count; a stacked change that needs its own count
  raises it here or writes its own census). The cases run over the derived population.
- unreachable, SKIPPED with its reason: git does not answer for HEAD, origin/main is unreachable, HEAD and origin/main
  have no merge base, or the diff fails. The pytest job's checkout in .github/workflows/ci.yml fetches depth 1 and no
  origin/main, so CI runs here. setUpModule raises unittest.SkipTest naming what was unreachable; no case runs, and no
  other population is read in the derivation's place.
- out of scope, SKIPPED with its reason: git answers and the range base..HEAD lacks BRANCH_COMMIT (the fork's main
  after the merge, where the merge base is HEAD and the range empty; an unrelated branch, whose lines are its own PR's
  to label). Nothing there is this branch's to label, and the skip says so.
The two skips follow the maintainer's ruling of 2026-09-21 (03:21Z, on PR 860's census, stated as the general lesson):
when a derivation is unavailable a guard skips or refuses with its reason and never substitutes a different population;
substituting a wider one is the unsafe direction, because it reds work the guard was never about. A checkout that cannot
derive this branch's added lines therefore reports a skip with the reason, never a pass over a stand-in and never an
exception.

THE GUARDS are per rule, never one count over a union: each rule either read at least one candidate line of the
population or refused a plant of its own form, and the credit rule must have read a line (a population with no credit
line means the token pattern or the population reader is broken). When the reviewer holds a further round on this PR,
raise REVIEWER_ROUNDS and rewrite this constant's comment; a label naming that round is then a real round.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)

REVIEWER_ROUNDS = 6   # the highest-numbered ruling the reviewer has filed on the lazy-panes PR when this was written: the reviewer's round 6, 2026-09-21
BRANCH_COMMIT = "9874612e59955d4bd1678b7fe1407d768383bfa6"   # the commit that added this module: the scope test of the derived road
RULES = ("credit", "bare", "lettered", "verify", "unclassifiable")
CREDIT_WORDS = {"review", "reviewer's", "reviewers'", "maintainer's", "maintainers'"}
ARTIFACTS = {"fixlist", "fixlists", "refuter", "refuters", "ruling", "rulings", "addendum", "verdict", "finding", "findings"}
VERIFY_WORDS = {"verify", "verify's", "verifier", "verifier's"}
DERIVED, UNREACHABLE, OUT_OF_SCOPE = "derived", "unreachable", "out-of-scope"   # the three roads

# a token: the word round (or rounds), a hyphen or a space or nothing, a number, then an optional letter, possessive and range
TOKEN = re.compile(r"\b(?P<word>rounds?)(?P<sep>[- ]?)(?P<n>\d+)(?P<letter>[a-z])?(?P<poss>'s)?(?P<range>\s+(?:to|and|through)\s+(?P<m>\d+))?\b", re.I)
PREV_WORD = re.compile(r"([A-Za-z][A-Za-z']*)[^A-Za-z0-9]*$")
NEXT_WORD = re.compile(r"^\s+([A-Za-z][A-Za-z']*(?:-\d+)?)")


class Token(object):
    __slots__ = ("text", "label", "n", "letter", "prev", "suffix", "rule")

    def __init__(self, line, m):
        self.text = m.group(0)
        self.n = max(int(m.group("n")), int(m.group("m")) if m.group("m") else 0)
        self.letter = m.group("letter") or ""
        pm = PREV_WORD.search(line[:m.start()])
        self.prev = (pm.group(1) if pm else "").lower()
        nm = NEXT_WORD.match(line[m.end():])
        self.suffix = (nm.group(1) if nm else "").lower()
        self.rule = classify(self)
        # the label as the report quotes it: the word before, the token, the word after (the property's evidence, not the token alone)
        self.label = " ".join(w for w in ((pm.group(1) if pm else ""), self.text, (nm.group(1) if nm else "")) if w)


def _artifact(suffix):
    base = suffix.split("-")[0]
    if base.endswith("'s"):
        base = base[:-2]
    return base in ARTIFACTS


def classify(tok):
    """One of RULES for a token: the property, not a spelling."""
    if tok.letter:
        return "lettered"
    if tok.suffix in VERIFY_WORDS:
        return "verify"
    if tok.prev in CREDIT_WORDS:
        return "credit"
    if tok.prev.endswith("'s") or tok.prev.endswith("s'"):
        return "unclassifiable"
    if _artifact(tok.suffix):
        return "credit"
    return "bare"


def refuse(tok):
    """Why the token is refused, or None when it is accepted."""
    if tok.rule == "lettered":
        return "a lettered round is an author's pass"
    if tok.rule == "verify":
        return "a verify is the author's verifier, never a review round"
    if tok.rule == "unclassifiable":
        return "a possessive that names neither the reviewer nor the maintainer credits no one the census knows"
    if tok.rule == "bare":
        return "a bare round credits no one: the author's builds are passes (pass N), the reviewer's rounds are named as the reviewer's"
    if not 1 <= tok.n <= REVIEWER_ROUNDS:
        return "the reviewer held %d rounds on this PR (REVIEWER_ROUNDS)" % REVIEWER_ROUNDS
    return None


def tokens(text):
    text = text.replace("’", "'")   # a typographic apostrophe reads as the ASCII one, so "the reviewer's" in either spelling is the credit it is
    return [Token(text, m) for m in TOKEN.finditer(text)]


def offences(text):
    """(line number, the token, why) for every refused token in `text`."""
    out = []
    for i, line in enumerate(text.split("\n"), 1):
        for tok in tokens(line):
            why = refuse(tok)
            if why:
                out.append((i, tok.label, why))
    return out


def spelling(tok):
    """The (credit word, suffix) shape of a credit token: the form-space key."""
    return (tok.prev if tok.prev in CREDIT_WORDS else "", tok.suffix if _artifact(tok.suffix) else "")


def plant(prev, suffix, n, sep=" "):
    """A credit to round `n` in the spelling (prev, suffix), assembled at run time."""
    head = {"": "the", "review": "review", "reviewer's": "the reviewer's", "reviewers'": "the reviewers'",
            "maintainer's": "the maintainer's", "maintainers'": "the maintainers'"}[prev]
    return "%s %s%s%d%s" % (head, "round", sep, n, (" " + suffix) if suffix else "")


# ── the population ──

def _git(*args, root=ROOT, env=None):
    try:
        r = subprocess.run(["git", "-C", root] + list(args), capture_output=True, text=True, timeout=180, env=env)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout if r.returncode == 0 else None


def _name_args(base):
    """The files changed from the merge base to the committed head and present at the head: a deleted file has no added
    lines and is outside the population."""
    return ("diff", "--name-only", "--diff-filter=d", "--find-renames", base, "HEAD", "--", ".")


def _diff_args(base):
    """The -U0 diff of the merge base against the committed head, whose added lines are the population, independent of the
    caller's git configuration: fixed prefixes (diff.mnemonicPrefix prints `+++ w/`, diff.noprefix `+++ path`, and
    _added_lines keys on `+++ b/`), no external diff, rename detection on (diff.renames may be false or `copies`)."""
    return ("diff", "-U0", "--no-color", "--no-ext-diff", "--find-renames", "--src-prefix=a/", "--dst-prefix=b/", base, "HEAD", "--", ".")


def _added_lines(diff):
    """(path, line number at the head, text) for every added line of a -U0 diff."""
    out, path, ln = [], None, 0
    for line in diff.split("\n"):
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            ln = int(m.group(1)) if m else 0
        elif line.startswith("+") and path is not None:
            out.append((path, ln, line[1:]))
            ln += 1
    return out


def _population(names, diff):
    """(files, candidate lines) from the derivation's git answers: `names` the changed files present at the head, `diff`
    the -U0 diff of the merge base against the committed head. Nothing else is read: an untracked file and an uncommitted
    edit are outside the population until they are committed."""
    files = sorted(n for n in names if n)
    cands = [(p, ln, t) for p, ln, t in _added_lines(diff) if TOKEN.search(t)]
    return files, sorted(cands)


def derive(root=ROOT, main="origin/main", scope=BRANCH_COMMIT, env=None):
    """(road, files, candidate lines as (path, line, text), reason, merge base). On the two skip roads files and lines are
    None: nothing is derived and nothing stands in for it, and the reason names what was unreachable. `root`, `main`,
    `scope` and `env` are the module's own values in the module's read; the tests hand in a scratch repository, a ref
    that does not exist, a foreign scope or a git that cannot answer to drive the other roads."""
    g = lambda *a: _git(*a, root=root, env=env)
    head = g("rev-parse", "--verify", "--quiet", "HEAD")
    if head is None:
        return UNREACHABLE, None, None, "git does not answer for HEAD here (no repository at the module's root, or no git to ask)", None
    mainsha = g("rev-parse", "--verify", "--quiet", main)
    if mainsha is None:
        return (UNREACHABLE, None, None,
                "%s is unreachable here: git does not answer for that ref (a checkout without the remote's main, CI's depth-1 checkout among them)" % main, None)
    base = g("merge-base", "HEAD", main)
    if base is None:
        return UNREACHABLE, None, None, "HEAD and %s have no merge base here (a shallow checkout, or unrelated histories)" % main, None
    base = base.strip()
    in_range = g("rev-list", base + "..HEAD")
    if in_range is None:
        return UNREACHABLE, None, None, "git rev-list failed over %s..HEAD" % base[:9], base
    if scope is not None and scope not in in_range.split():
        return (OUT_OF_SCOPE, None, None,
                "HEAD is not the lazy-panes branch: the range %s..HEAD does not carry the census's introducing commit %s "
                "(the fork's main after the merge, or another branch); nothing here is this branch's to label" % (base[:9], scope[:9]), base)
    names = g(*_name_args(base))
    diff = g(*_diff_args(base))
    if names is None or diff is None:
        return UNREACHABLE, None, None, "git diff of the merge base %s against HEAD failed" % base[:9], base
    files, cands = _population(names.split("\n"), diff)
    return DERIVED, files, cands, "the branch's added lines, the merge base %s against the committed head" % base[:9], base


ROAD, FILES, LINES, REASON, BASE = derive()
FORM_SPACE = sorted({spelling(t) for _, _, text in (LINES or []) for t in tokens(text) if t.rule == "credit"})
sys.stderr.write("[review-round-labels] road: %s (%s); %s\n"
                 % (ROAD, REASON, "%d files, %d candidate lines, %d credit spellings" % (len(FILES), len(LINES), len(FORM_SPACE))
                    if ROAD == DERIVED else "every case skipped"))


def setUpModule():
    """The skip: on a road other than the derived one no case runs, and the reason names what was unreachable (the ruling
    of 2026-09-21 in the docstring). unittest reports the module skipped; pytest skips each case with the message."""
    if ROAD != DERIVED:
        raise unittest.SkipTest("review-round-labels: every case skipped on the %s road: %s" % (ROAD, REASON))


class ReviewRoundLabels(unittest.TestCase):
    def _where(self):
        return "road %s: %s" % (ROAD, REASON)

    def test_a_road_off_the_derived_one_is_a_skip(self):
        """setUpModule by execution at each road: a skip with the road and the reason on the two roads that derive nothing,
        no raise on the derived one (a case that ran on a skip road would be the pass over a stand-in the ruling forbids)."""
        g = globals()
        held = g["ROAD"], g["REASON"]
        try:
            for road in (UNREACHABLE, OUT_OF_SCOPE):
                with self.subTest(road=road):
                    g["ROAD"], g["REASON"] = road, "the reason names what was unreachable"
                    with self.assertRaises(unittest.SkipTest) as cm:
                        setUpModule()
                    self.assertIn(road, str(cm.exception))
                    self.assertIn("the reason names what was unreachable", str(cm.exception))
            g["ROAD"], g["REASON"] = DERIVED, "derived"
            self.assertIsNone(setUpModule(), "the derived road is the one whose cases run")
        finally:
            g["ROAD"], g["REASON"] = held

    def test_the_three_roads(self):
        """Each road's derivation by execution, from the derived road (the one whose cases run): a git that cannot answer
        for HEAD, a ref that does not exist where origin/main is asked for (CI's depth-1 checkout has none), a scope
        commit the range lacks, and the derived road where this checkout is on it; each skip road returns no population
        (None, not an empty list) and a reason naming what was unreachable."""
        quiet = dict(os.environ, GIT_DIR="/nonexistent-git-dir")
        road, files, lines, reason, base = derive(env=quiet)
        self.assertEqual((road, files, lines, base), (UNREACHABLE, None, None, None), reason)
        self.assertIn("does not answer for HEAD", reason)
        gone = "refs/remotes/origin/no-such-main-for-the-census"
        road, files, lines, reason, base = derive(main=gone)
        self.assertEqual((road, files, lines, base), (UNREACHABLE, None, None, None), reason)
        self.assertIn("%s is unreachable" % gone, reason)
        road, files, lines, reason, base = derive(scope="0" * 40)
        self.assertEqual((road, files, lines), (OUT_OF_SCOPE, None, None), reason)
        self.assertIn("nothing here is this branch's to label", reason)
        self.assertEqual(base, BASE)
        road, files, lines, reason, base = derive()
        self.assertEqual((road, files, lines, base), (ROAD, FILES, LINES, BASE), reason)

    def test_the_derivation_over_a_scratch_repository(self):
        """The derivation's git reads driven against a repository built here, under a git configuration that would reshape
        an unpinned diff: a deleted file is outside the population, a renamed file contributes its edited lines alone, an
        untracked file and an uncommitted edit are outside the population whether or not they carry a token (the committed
        head is the population), two added lines in one hunk are numbered from the hunk's start, and a head with no merge
        base is the unreachable road, not a population."""
        R = "round"
        tmp = tempfile.mkdtemp(prefix="review-round-labels-")
        self.addCleanup(shutil.rmtree, tmp, True)
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}   # a caller's GIT_DIR (the unreachable road's drive) must not reach the scratch repository
        env.update(GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1",
                   GIT_CONFIG_PARAMETERS="'diff.mnemonicPrefix=true' 'diff.noprefix=true' 'diff.renames=false'",
                   GIT_AUTHOR_NAME="census", GIT_AUTHOR_EMAIL="census@example.invalid",
                   GIT_COMMITTER_NAME="census", GIT_COMMITTER_EMAIL="census@example.invalid")
        g = lambda *a: _git(*a, root=tmp, env=env)

        def put(rel, text):
            with open(os.path.join(tmp, rel), "w", encoding="utf-8") as f:
                f.write(text)
        self.assertEqual(subprocess.run(["git", "init", "--quiet", "-b", "base", tmp], env=env, capture_output=True).returncode, 0)
        put("gone.md", "a file the branch deletes\nthe reviewer's %s 2 finding\n" % R)
        put("kept.md", "line one\nthe reviewer's %s 1 ruling\nline three\n" % R)
        put("moved.md", "the reviewer's %s 2 ruling\nsecond line\n" % R)
        self.assertIsNotNone(g("add", "."))
        self.assertIsNotNone(g("commit", "--quiet", "-m", "base"))
        self.assertIsNotNone(g("checkout", "--quiet", "-b", "branch"))
        os.remove(os.path.join(tmp, "gone.md"))
        committed = "line one\nthe reviewer's %s 1 ruling\nline three\nsince %s 3 the park has a bound\nthe reviewer's %s 2 ruling closed it\n" % (R, R, R)
        put("kept.md", committed)
        self.assertIsNotNone(g("mv", "moved.md", "renamed.md"))
        put("renamed.md", "the reviewer's %s 2 ruling\nsecond line\nthe maintainer's %s 4 ruled it\n" % (R, R))
        self.assertIsNotNone(g("add", "-A"))
        self.assertIsNotNone(g("commit", "--quiet", "-m", "branch"))
        put("scratch.md", "a scratch note with no label in it\n")                              # untracked, token-free
        put("new_module.py", "# pass 2 reworded it\n# review %s 4b reworded it too\n" % R)     # untracked, with a token
        put("kept.md", committed + "the reviewer's %s 9 finding, an edit in progress\n" % R)    # tracked, an uncommitted edit with a token
        road, files, lines, reason, base = derive(root=tmp, main="base", scope=None, env=env)
        self.assertEqual(road, DERIVED, reason)
        self.assertEqual(files, ["kept.md", "renamed.md"],
                         "the deleted file and the two untracked files are outside the list; the renamed file is under its new path")
        self.assertEqual(sorted((p, t) for p, _, t in lines),
                         [("kept.md", "since %s 3 the park has a bound" % R), ("kept.md", "the reviewer's %s 2 ruling closed it" % R),
                          ("renamed.md", "the maintainer's %s 4 ruled it" % R)],
                         "the committed added lines alone (the uncommitted edit and the untracked module unread), under a git configuration "
                         "that renames the diff header, drops the prefix and disables rename detection")
        self.assertEqual([ln for p, ln, _ in lines if p == "kept.md"], [4, 5],
                         "the line numbers are the head's: the hunk's start for the first added line and the per-line advance for the second")
        self.assertIsNotNone(g("checkout", "--quiet", "--orphan", "island"))
        self.assertIsNotNone(g("commit", "--quiet", "-m", "island"))
        road, files, lines, reason, base = derive(root=tmp, main="base", scope=None, env=env)
        self.assertEqual((road, files, lines, base), (UNREACHABLE, None, None, None), reason)
        self.assertIn("no merge base", reason)

    def test_no_label_credits_a_round_the_reviewer_never_held(self):
        bad, read = [], dict((r, 0) for r in RULES)
        for path, ln, text in LINES:
            for tok in tokens(text):
                read[tok.rule] += 1
                why = refuse(tok)
                if why:
                    bad.append("%s:%d: %r (%s)" % (path, ln, tok.label, why))
        R = "round"
        plants = {"credit": plant("review", "", REVIEWER_ROUNDS + 1), "bare": "since %s 3" % R, "lettered": "review %s 4b" % R,
                  "verify": "%s 4's verify" % R, "unclassifiable": "the author's %s 3" % R}
        for rule in RULES:
            with self.subTest(rule=rule):
                if read[rule] == 0:
                    tok = tokens(plants[rule])[0]
                    self.assertEqual(tok.rule, rule, "the plant %r is not of the rule it stands for" % plants[rule])
                    self.assertTrue(refuse(tok), "rule %s read no candidate line and did not refuse its plant %r (%s)" % (rule, plants[rule], self._where()))
        self.assertGreater(read["credit"], 0, "the census read no credit line: the population reader or the token pattern is broken (%s)" % self._where())
        self.assertEqual(bad, [], "a label credits a round the reviewer never held on this PR, or credits no one (%s); write the author's pass "
                                  "(\"pass N\") with the reviewer's round named where a ruling exists, or raise REVIEWER_ROUNDS for a round the reviewer "
                                  "did hold:\n" % self._where() + "\n".join(bad))

    def test_the_form_space(self):
        """The classifier over every spelling the branch uses, so the census is known to read them; the probes are assembled
        at run time (this module is in the population and reads itself)."""
        R, V = "round", "verify"
        unclassified = [(p, t.label) for p, _, text in LINES for t in tokens(text) if t.rule not in RULES]
        self.assertEqual(unclassified, [], "a token outside the five rules (%s)" % self._where())
        canonical = [("review", ""), ("reviewer's", ""), ("maintainer's", ""), ("", "verdict"), ("", "ruling")]
        for prev, suffix in sorted(set(FORM_SPACE) | set(canonical)):
            for sep in (" ", "-"):
                with self.subTest(spelling=(prev, suffix, sep)):
                    over = plant(prev, suffix, REVIEWER_ROUNDS + 1, sep)
                    self.assertTrue(offences(over), "a credit above the reviewer's rounds read as clean in the spelling %r" % over)
                    held = plant(prev, suffix, REVIEWER_ROUNDS, sep)
                    self.assertEqual(offences(held), [], "a credit to the reviewer's last round read as an offence in the spelling %r" % held)
        red = ["since %s 3" % R, "%s 3's head" % R, "%s-3 armed them" % R, "%s 3 showed every" % R.title(),
               "review %s 4b" % R, "%s-4b" % R, "the reviewer's %s-4b" % R,
               "review %s 4 %s" % (R, V), "%s 4's %s" % (R, V), "the %s-5 %s" % (R, V), "the reviewer's %s 6 %s" % (R, V),
               "the author's %s 3" % R, "the fixer's %s-2" % R, "the reviewer's %ss 1 to %d" % (R, REVIEWER_ROUNDS + 1), "review %s 0" % R,
               "the reviewer’s %s %d" % (R, REVIEWER_ROUNDS + 1)]
        green = [plant("review", "", REVIEWER_ROUNDS), "the reviewer's %s-%d finding kernel-1" % (R, REVIEWER_ROUNDS), plant("maintainer's", "", REVIEWER_ROUNDS),
                 "the %s-3 fixlist's extra9-1" % R, "%s 2's ruling" % R, "the %s-1 refuter's screenshot" % R, "the %s-4 verdict-1 case" % R,
                 "review %s 2 closeout" % R, "Review %s %d fixes:" % (R, REVIEWER_ROUNDS), "the reviewer's %ss 1 to %d" % (R, REVIEWER_ROUNDS),
                 "review %ss 5 and %d" % (R, REVIEWER_ROUNDS), "pass 5, the author's label", "the author's pass-5 %s" % V, "pass 4b",
                 "a%s 6" % R, "backg%s 6" % R, "%s-trip" % R, "REVIEWER_ROUNDS = %d" % REVIEWER_ROUNDS,
                 "the reviewer’s %s %d" % (R, REVIEWER_ROUNDS), "the maintainer’s %s-1 finding" % R]
        self.assertEqual([s for s in red if not offences(s)], [], "a refused form read as clean")
        self.assertEqual([s for s in green if offences(s)], [], "an allowed form read as an offence")
        self.assertEqual([t.rule for t in tokens("review %s 5 %s and %s 4b and since %s 2 and the %s-3 fixlist" % (R, V, R, R, R))],
                         ["verify", "lettered", "bare", "credit"])
        self.assertEqual([t.rule for t in tokens("the reviewer’s %s 3 and the author’s %s 2" % (R, R))], ["credit", "unclassifiable"],
                         "a possessive with a typographic apostrophe is classified as its ASCII spelling, so a refusal states the right reason")
        # the rebind case (the reviewer's round-6 finding extra9-1): raising REVIEWER_ROUNDS as the docstring directs keeps the
        # probes coherent, since they derive their number from the constant
        g = globals()
        held = g["REVIEWER_ROUNDS"]
        try:
            for k in (held + 1, held + 3):
                g["REVIEWER_ROUNDS"] = k
                with self.subTest(rebound=k):
                    self.assertTrue(offences(plant("reviewer's", "", k + 1, "-")), "a credit above the rebound count read as clean")
                    self.assertEqual(offences(plant("reviewer's", "", k, "-")), [], "a credit to the rebound count read as an offence")
        finally:
            g["REVIEWER_ROUNDS"] = held


if __name__ == "__main__":
    unittest.main()
