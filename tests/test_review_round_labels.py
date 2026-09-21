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

THE POPULATION is derived, not listed: the branch's ADDED lines, `git diff -U0 <merge base with origin/main>` against
the working tree, every changed file's added lines, kernel/kernel.py's like any other file's, tagged or not (the
`[fork]` tag is no longer a guard or an input; the file's pre-existing lines are the project's and unread), plus every
untracked file's lines (a new test module before its first add; such a file joins the FILE LIST only when it carries a
candidate line, so a token-free scratch file in the checkout moves nothing). A file the branch deletes has no added
lines and is outside the population (`--diff-filter=d`), so a deletion regenerates the manifest clean. The diff is read
config-independently: fixed prefixes (`--src-prefix=a/ --dst-prefix=b/`; a caller's diff.mnemonicPrefix or diff.noprefix
would otherwise rename or drop the `+++ b/` header the reader keys on), no external diff, rename detection on
(`--find-renames`, so a renamed file contributes its edited lines alone whatever diff.renames says), and the manifest
writer refuses an empty candidate list. The read is per added line: a label wrapped across two lines, a `round #N`, an
ordinal (`Nth round`) or a spelled-out number is outside the token shape and unread; a possessive written with a
typographic apostrophe is read as its ASCII form. This module reads itself, so every refused form it needs as a probe
is assembled at run time and the prose above spells numbers as N. Three roads, one of which runs, named in every
assertion message (test_the_three_roads drives each road's derivation by execution):
- derived: git answers for HEAD and origin/main, the merge base is derivable, and the range base..HEAD carries this
  module's introducing commit (BRANCH_COMMIT), so HEAD is the lazy-panes branch or a descendant of it that has not
  merged (a descendant's own added lines are read under this PR's count; a stacked change that needs its own count
  raises it here or writes its own census). The committed manifest is pinned equal to the derivation on this road.
- manifest: git does not answer, origin/main is unreachable or no merge base exists (the pytest job's checkout in
  .github/workflows/ci.yml fetches depth 1, so CI runs here), and the module reads the committed manifest, the
  derivation's last output, and applies every rule to it. A stale manifest passes here and reds on the derived road,
  where it is pinned; the manifest is committed with every change that adds a candidate line.
- out of scope: git answers and the range base..HEAD lacks BRANCH_COMMIT (the fork's main after the merge, where the
  merge base is HEAD and the range empty; an unrelated branch, whose lines are its own PR's to label). The population
  is empty by scope, the reason is stated, and the plants alone prove each rule.
The MANIFEST, tests/fixtures/review-round-labels-manifest.txt, holds the branch's changed files (the 821 ledger entry's
where-line population) and its candidate lines (every added line carrying a round token), written from the derivation
by `python3 tests/test_review_round_labels.py --write-manifest`. The manifest is excluded from the derivation: its lines
are copies of the population.

THE GUARDS are per rule, never one count over a union: each rule either read at least one candidate line of the
population or refused a plant of its own form; on the derived and manifest roads the credit rule must also have read a
line (a population with no credit line means the token pattern or the population reader is broken). When the reviewer
holds a further round on this PR, raise REVIEWER_ROUNDS and rewrite this constant's comment; a label naming that round
is then a real round. The file list is checked against the checkout on the derived road alone, where it is live (a
deleted file has left it, so a missing file there is one removed between the listing and the read); on the manifest and
out-of-scope roads the manifest is a FROZEN RECORD whose rows are read for the rules and checked for their own
consistency (non-empty, every line row under a file row), never against the tree: the out-of-scope road's record is
another branch's population, not this tree's; on the manifest road (CI's until the PR lands; this module leaves the tree
at landing, the first paragraph above) a check that each line row is a line of its file would catch that road's one
residual, a manifest the author left stale after a reword (pinned on the derived road), and is left as a shape question
for the ruler beside the convergence named above rather than added to a guard about to become a caller.
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
MANIFEST = "tests/fixtures/review-round-labels-manifest.txt"
RULES = ("credit", "bare", "lettered", "verify", "unclassifiable")
CREDIT_WORDS = {"review", "reviewer's", "reviewers'", "maintainer's", "maintainers'"}
ARTIFACTS = {"fixlist", "fixlists", "refuter", "refuters", "ruling", "rulings", "addendum", "verdict", "finding", "findings"}
VERIFY_WORDS = {"verify", "verify's", "verifier", "verifier's"}

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
    text = text.replace("\u2019", "'")   # a typographic apostrophe reads as the ASCII one, so "the reviewer's" in either spelling is the credit it is
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
    """The changed files present at the head: a deleted file has no added lines and is outside the population."""
    return ("diff", "--name-only", "--diff-filter=d", "--find-renames", base, "--", ".")


def _diff_args(base):
    """The -U0 diff whose added lines are the population, independent of the caller's git configuration: fixed prefixes
    (diff.mnemonicPrefix prints `+++ w/`, diff.noprefix `+++ path`, and _added_lines keys on `+++ b/`), no external diff,
    rename detection on (diff.renames may be false or `copies`)."""
    return ("diff", "-U0", "--no-color", "--no-ext-diff", "--find-renames", "--src-prefix=a/", "--dst-prefix=b/", base, "--", ".")


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


def _population(names, untracked, diff, read):
    """(files, candidate lines) from the derivation's git answers: `names` the changed files present at the head,
    `untracked` the untracked files, `diff` the -U0 diff, `read(rel)` a file's text or None. An untracked file's lines
    join the population, and the file joins the list only when one of them carries a token (a scratch note moves nothing)."""
    files = set(n for n in names if n)
    added = [(p, ln, t) for p, ln, t in _added_lines(diff) if p != MANIFEST]
    for rel in (u for u in untracked if u):
        if rel == MANIFEST:
            continue
        text = read(rel)
        if text is None:
            continue
        lines = [(rel, i, line) for i, line in enumerate(text.split("\n"), 1) if TOKEN.search(line)]
        if lines:
            files.add(rel)
            added.extend(lines)
    cands = [(p, ln, t) for p, ln, t in added if TOKEN.search(t)]
    return sorted(files), sorted(cands)


def derive(root=ROOT, main="origin/main", scope=BRANCH_COMMIT, env=None):
    """(road, files, candidate lines as (path, line, text), reason, merge base). `root`, `main`, `scope` and `env` are the
    module's own values in the module's read; the tests hand in a scratch repository, a foreign scope or a git that
    cannot answer to drive the other roads."""
    g = lambda *a: _git(*a, root=root, env=env)
    head = g("rev-parse", "--verify", "--quiet", "HEAD")
    mainsha = g("rev-parse", "--verify", "--quiet", main)
    if head is None or mainsha is None:
        return "manifest", None, None, "git does not answer for HEAD or %s here (a shallow or remote-less checkout)" % main, None
    base = g("merge-base", "HEAD", main)
    if base is None:
        return "manifest", None, None, "HEAD and %s have no merge base here (a shallow checkout)" % main, None
    base = base.strip()
    in_range = g("rev-list", base + "..HEAD")
    if in_range is None:
        return "manifest", None, None, "git rev-list failed over %s..HEAD" % base[:9], base
    if scope is not None and scope not in in_range.split():
        return ("out-of-scope", [], [],
                "HEAD is not the lazy-panes branch: the range %s..HEAD does not carry the census's introducing commit %s "
                "(the fork's main after the merge, or another branch); the population is empty by scope" % (base[:9], scope[:9]), base)
    names = g(*_name_args(base))
    untracked = g("ls-files", "--others", "--exclude-standard")
    diff = g(*_diff_args(base))
    if names is None or untracked is None or diff is None:
        return "manifest", None, None, "git diff against the merge base %s failed" % base[:9], base

    def read(rel):
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as f:
                return f.read()
        except (OSError, UnicodeDecodeError):
            return None
    files, cands = _population(names.split("\n"), untracked.split("\n"), diff, read)
    return "derived", files, cands, "the branch's added lines against the merge base %s" % base[:9], base


def read_manifest(path=None):
    """(files, candidate lines as (path, 0, text)) from the committed manifest; raises when it is missing or malformed."""
    files, lines = [], []
    with open(path or os.path.join(ROOT, MANIFEST), encoding="utf-8") as f:
        for raw in f.read().split("\n"):
            if not raw or raw.startswith("#"):
                continue
            kind, _, rest = raw.partition("\t")
            if kind == "file":
                files.append(rest)
            elif kind == "line":
                path, _, text = rest.partition("\t")
                lines.append((path, 0, text))
            else:
                raise ValueError("%s: a row that is neither file nor line: %r" % (MANIFEST, raw[:80]))
    return sorted(files), sorted(lines)


def write_manifest(files, cands, base_note, path=None):
    """Write the manifest from a derivation; refuses an empty candidate list (file rows with no line row is never the
    derivation's honest output: the diff reader or the token pattern is broken)."""
    if not cands:
        raise ValueError("the derivation read no candidate line (%s): the diff reader or the token pattern is broken; nothing written" % base_note)
    rows = ["# The lazy-panes census manifest (tests/test_review_round_labels.py): the branch's changed files and every added line",
            "# carrying a round token, written from the derivation by `python3 tests/test_review_round_labels.py --write-manifest`",
            "# (%s). Read on the manifest road (no git, or no origin/main: CI's depth-1 checkout); pinned equal to the" % base_note,
            "# derivation on the derived road. Regenerate it with every change that adds or rewords a candidate line."]
    rows += ["file\t%s" % f for f in files]
    rows += ["line\t%s\t%s" % (p, t) for p, t in sorted((p, t) for p, _, t in cands)]
    with open(path or os.path.join(ROOT, MANIFEST), "w", encoding="utf-8") as f:
        f.write("\n".join(rows) + "\n")


def _record_problems(files, lines):
    """The manifest's own consistency, the check the frozen record gets where the tree is not compared against it: a file
    row and a line row exist, and every line row's path is a file row."""
    out = []
    if not files:
        out.append("no file row")
    if not lines:
        out.append("no line row")
    known = set(files)
    out.extend("%s: a line row whose path is not a file row" % p for p in sorted({p for p, _, _ in lines if p not in known}))
    return out


ROAD, FILES, LINES, REASON, BASE = derive()
if ROAD == "manifest":
    FILES, LINES = read_manifest()
FORM_SPACE = sorted({spelling(t) for _, _, text in LINES for t in tokens(text) if t.rule == "credit"})
sys.stderr.write("[review-round-labels] road: %s (%s); %d files, %d candidate lines, %d credit spellings\n"
                 % (ROAD, REASON, len(FILES), len(LINES), len(FORM_SPACE)))


class ReviewRoundLabels(unittest.TestCase):
    def _where(self):
        return "road %s: %s" % (ROAD, REASON)

    def test_the_file_list_holds_on_its_road(self):
        """Derived road: every listed file exists (the list is live: tracked files present at the head, untracked files
        with a candidate line). Manifest and out-of-scope roads: the manifest is a frozen record, checked for its own
        consistency and never against the tree (the docstring's last paragraph says why)."""
        self.assertTrue(_record_problems(["a"], [("b", 0, "x")]), "the record check reads nothing: an inconsistent record read as consistent")
        self.assertEqual(_record_problems(*read_manifest()), [], "the committed manifest is not consistent with itself (%s)" % self._where())
        if ROAD == "derived":
            missing = [f for f in FILES if not os.path.isfile(os.path.join(ROOT, f))]
            self.assertEqual(missing, [], "a listed file is missing from the checkout (%s): the derivation lists files present at the "
                                          "head, so this one went between the listing and this read; re-run" % self._where())
        elif ROAD == "manifest":
            self.assertEqual(_record_problems(FILES, LINES), [], "the record read on this road is not consistent with itself (%s); "
                                                                 "the tree is not compared against it here" % self._where())
        else:
            self.assertEqual((FILES, LINES), ([], []), "the population is empty by scope on this road (%s); the committed manifest's "
                                                       "own consistency, checked above, is the record's check here" % self._where())

    def test_the_three_roads(self):
        """Each road's derivation by execution: a git that cannot answer (the manifest road), a scope commit the range lacks
        (out of scope), and the derived road where this checkout is on it."""
        quiet = dict(os.environ, GIT_DIR="/nonexistent-git-dir")
        road, files, lines, reason, base = derive(env=quiet)
        self.assertEqual((road, files, lines, base), ("manifest", None, None, None), reason)
        self.assertIn("does not answer", reason)
        if ROAD == "manifest":
            return   # git answers nothing here (the reason above says so): the two roads that need it cannot be driven
        road, files, lines, reason, base = derive(scope="0" * 40)
        self.assertEqual((road, files, lines), ("out-of-scope", [], []), reason)
        self.assertIn("empty by scope", reason)
        self.assertEqual(base, BASE)
        road, files, lines, reason, base = derive()
        self.assertEqual((road, files, lines, base), (ROAD, FILES, LINES, BASE), reason)

    def test_the_derivation_over_a_scratch_repository(self):
        """The derivation's git reads driven against a repository built here, under a git configuration that would reshape
        an unpinned diff: a deleted file is outside the population, a renamed file contributes its edited lines alone, a
        token-free untracked file joins nothing, an untracked file with a token joins the list and the population, two added
        lines in one hunk are numbered from the hunk's start, and the manifest writer refuses an empty derivation."""
        R = "round"
        tmp = tempfile.mkdtemp(prefix="review-round-labels-")
        self.addCleanup(shutil.rmtree, tmp, True)
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}   # a caller's GIT_DIR (the manifest road's drive) must not reach the scratch repository
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
        put("kept.md", "line one\nthe reviewer's %s 1 ruling\nline three\nsince %s 3 the park has a bound\nthe reviewer's %s 2 ruling closed it\n"
            % (R, R, R))
        self.assertIsNotNone(g("mv", "moved.md", "renamed.md"))
        put("renamed.md", "the reviewer's %s 2 ruling\nsecond line\nthe maintainer's %s 4 ruled it\n" % (R, R))
        self.assertIsNotNone(g("add", "-A"))
        self.assertIsNotNone(g("commit", "--quiet", "-m", "branch"))
        put("scratch.md", "a scratch note with no label in it\n")
        put("new_module.py", "# pass 2 reworded it\n# review %s 4b reworded it too\n" % R)
        road, files, lines, reason, base = derive(root=tmp, main="base", scope=None, env=env)
        self.assertEqual(road, "derived", reason)
        self.assertEqual(files, ["kept.md", "new_module.py", "renamed.md"],
                         "the deleted file and the token-free scratch file are outside the list; the renamed file is under its new path")
        self.assertEqual(sorted((p, t) for p, _, t in lines),
                         [("kept.md", "since %s 3 the park has a bound" % R), ("kept.md", "the reviewer's %s 2 ruling closed it" % R),
                          ("new_module.py", "# review %s 4b reworded it too" % R), ("renamed.md", "the maintainer's %s 4 ruled it" % R)],
                         "the added lines alone, under a git configuration that renames the diff header, drops the prefix and disables rename detection")
        self.assertEqual([ln for p, ln, _ in lines if p == "kept.md"], [4, 5],
                         "the line numbers are the head's: the hunk's start for the first added line and the per-line advance for the second")
        with self.assertRaises(ValueError):
            write_manifest(files, [], reason, path=os.path.join(tmp, "manifest.txt"))
        self.assertFalse(os.path.exists(os.path.join(tmp, "manifest.txt")), "nothing written for an empty derivation")
        write_manifest(files, lines, reason, path=os.path.join(tmp, "manifest.txt"))
        mfiles, mlines = read_manifest(os.path.join(tmp, "manifest.txt"))
        self.assertEqual((mfiles, sorted((p, t) for p, _, t in mlines)), (files, sorted((p, t) for p, _, t in lines)))
        self.assertEqual(_record_problems(mfiles, mlines), [])

    def test_the_manifest_matches_the_derivation(self):
        mfiles, mlines = read_manifest()
        self.assertTrue(mfiles and mlines, "the manifest is empty (%s)" % self._where())
        if ROAD != "derived":
            return   # the manifest is the population here (manifest road) or the population is empty by scope: nothing to compare
        self.assertEqual(mfiles, FILES, "the manifest's file list is not the derivation's: run `python3 tests/test_review_round_labels.py --write-manifest` (%s)" % self._where())
        self.assertEqual(sorted((p, t) for p, _, t in mlines), sorted((p, t) for p, _, t in LINES),
                         "the manifest's candidate lines are not the derivation's: run `python3 tests/test_review_round_labels.py --write-manifest` (%s)" % self._where())

    def test_no_label_credits_a_round_the_reviewer_never_held(self):
        bad, read = [], dict((r, 0) for r in RULES)
        for path, ln, text in LINES:
            for tok in tokens(text):
                read[tok.rule] += 1
                why = refuse(tok)
                if why:
                    bad.append("%s:%s: %r (%s)" % (path, ln or "manifest", tok.label, why))
        R = "round"
        plants = {"credit": plant("review", "", REVIEWER_ROUNDS + 1), "bare": "since %s 3" % R, "lettered": "review %s 4b" % R,
                  "verify": "%s 4's verify" % R, "unclassifiable": "the author's %s 3" % R}
        for rule in RULES:
            with self.subTest(rule=rule):
                if read[rule] == 0:
                    tok = tokens(plants[rule])[0]
                    self.assertEqual(tok.rule, rule, "the plant %r is not of the rule it stands for" % plants[rule])
                    self.assertTrue(refuse(tok), "rule %s read no candidate line and did not refuse its plant %r (%s)" % (rule, plants[rule], self._where()))
        if ROAD != "out-of-scope":
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
               "the reviewer\u2019s %s %d" % (R, REVIEWER_ROUNDS + 1)]
        green = [plant("review", "", REVIEWER_ROUNDS), "the reviewer's %s-%d finding kernel-1" % (R, REVIEWER_ROUNDS), plant("maintainer's", "", REVIEWER_ROUNDS),
                 "the %s-3 fixlist's extra9-1" % R, "%s 2's ruling" % R, "the %s-1 refuter's screenshot" % R, "the %s-4 verdict-1 case" % R,
                 "review %s 2 closeout" % R, "Review %s %d fixes:" % (R, REVIEWER_ROUNDS), "the reviewer's %ss 1 to %d" % (R, REVIEWER_ROUNDS),
                 "review %ss 5 and %d" % (R, REVIEWER_ROUNDS), "pass 5, the author's label", "the author's pass-5 %s" % V, "pass 4b",
                 "a%s 6" % R, "backg%s 6" % R, "%s-trip" % R, "REVIEWER_ROUNDS = %d" % REVIEWER_ROUNDS,
                 "the reviewer\u2019s %s %d" % (R, REVIEWER_ROUNDS), "the maintainer\u2019s %s-1 finding" % R]
        self.assertEqual([s for s in red if not offences(s)], [], "a refused form read as clean")
        self.assertEqual([s for s in green if offences(s)], [], "an allowed form read as an offence")
        self.assertEqual([t.rule for t in tokens("review %s 5 %s and %s 4b and since %s 2 and the %s-3 fixlist" % (R, V, R, R, R))],
                         ["verify", "lettered", "bare", "credit"])
        self.assertEqual([t.rule for t in tokens("the reviewer\u2019s %s 3 and the author\u2019s %s 2" % (R, R))], ["credit", "unclassifiable"],
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
    if "--write-manifest" in sys.argv:
        if ROAD != "derived":
            sys.exit("the manifest is written from the derivation alone; this checkout is on the %s road (%s)" % (ROAD, REASON))
        try:
            write_manifest(FILES, LINES, REASON)
        except ValueError as e:
            sys.exit(str(e))
        print("wrote %s: %d files, %d candidate lines" % (MANIFEST, len(FILES), len(LINES)))
    else:
        unittest.main()
