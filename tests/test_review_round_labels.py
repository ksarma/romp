#!/usr/bin/env python3
"""Every round label in the lazy-panes branch's own lines credits a round the reviewer held (the author's pass 8, 2026-09-21).

THE PROPERTY. A label credits a round to someone. The REVIEWER's rounds on this PR are the rulings files in the review
notes, outside this repository; REVIEWER_ROUNDS below is their count at filing, a tree-resident constant the author
raises when a ruling lands. It is never a read of the notes directory: that is a path outside the tree, absent on CI
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
the working tree, every changed file (kernel/kernel.py whole, tagged or not; the `[fork]` tag is no longer a guard or
an input), plus every untracked file whole (a new test module before its first add). This module reads itself, so
every refused form it needs as a probe is assembled at run time and the prose above spells numbers as N. Three roads,
one of which runs, named in every assertion message:
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
is then a real round. When a listed file moves, regenerate the manifest: a missing file is a red, not a skip.
"""
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)

REVIEWER_ROUNDS = 6   # the reviewer's rounds ruled on the lazy-panes PR when this was written: six rulings files, the sixth of 2026-09-21
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

def _git(*args):
    try:
        r = subprocess.run(["git", "-C", ROOT] + list(args), capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout if r.returncode == 0 else None


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


def derive():
    """(road, files, candidate lines as (path, line, text), reason)."""
    head = _git("rev-parse", "--verify", "--quiet", "HEAD")
    main = _git("rev-parse", "--verify", "--quiet", "origin/main")
    if head is None or main is None:
        return "manifest", None, None, "git does not answer for HEAD or origin/main here (a shallow or remote-less checkout)"
    base = _git("merge-base", "HEAD", "origin/main")
    if base is None:
        return "manifest", None, None, "HEAD and origin/main have no merge base here (a shallow checkout)"
    base = base.strip()
    in_range = _git("rev-list", base + "..HEAD")
    if in_range is None:
        return "manifest", None, None, "git rev-list failed over %s..HEAD" % base[:9]
    if BRANCH_COMMIT not in in_range.split():
        return ("out-of-scope", [], [],
                "HEAD is not the lazy-panes branch: the range %s..HEAD does not carry the census's introducing commit %s "
                "(the fork's main after the merge, or another branch); the population is empty by scope" % (base[:9], BRANCH_COMMIT[:9]))
    names = _git("diff", "--name-only", base, "--", ".")
    untracked = _git("ls-files", "--others", "--exclude-standard")
    diff = _git("diff", "-U0", "--no-color", base, "--", ".")
    if names is None or untracked is None or diff is None:
        return "manifest", None, None, "git diff against the merge base %s failed" % base[:9]
    files = set(n for n in names.split("\n") if n)
    added = [(p, ln, t) for p, ln, t in _added_lines(diff) if p != MANIFEST]
    for rel in (u for u in untracked.split("\n") if u):
        files.add(rel)
        if rel == MANIFEST:
            continue
        try:
            with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        added.extend((rel, i, line) for i, line in enumerate(text.split("\n"), 1))
    cands = [(p, ln, t) for p, ln, t in added if TOKEN.search(t)]
    return "derived", sorted(files), sorted(cands), "the branch's added lines against the merge base %s" % base[:9]


def read_manifest():
    """(files, candidate lines as (path, 0, text)) from the committed manifest; raises when it is missing or malformed."""
    files, lines = [], []
    with open(os.path.join(ROOT, MANIFEST), encoding="utf-8") as f:
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


def write_manifest(files, cands, base_note):
    rows = ["# The lazy-panes census manifest (tests/test_review_round_labels.py): the branch's changed files and every added line",
            "# carrying a round token, written from the derivation by `python3 tests/test_review_round_labels.py --write-manifest`",
            "# (%s). Read on the manifest road (no git, or no origin/main: CI's depth-1 checkout); pinned equal to the" % base_note,
            "# derivation on the derived road. Regenerate it with every change that adds or rewords a candidate line."]
    rows += ["file\t%s" % f for f in files]
    rows += ["line\t%s\t%s" % (p, t) for p, t in sorted((p, t) for p, _, t in cands)]
    with open(os.path.join(ROOT, MANIFEST), "w", encoding="utf-8") as f:
        f.write("\n".join(rows) + "\n")


ROAD, FILES, LINES, REASON = derive()
if ROAD == "manifest":
    FILES, LINES = read_manifest()
FORM_SPACE = sorted({spelling(t) for _, _, text in LINES for t in tokens(text) if t.rule == "credit"})
sys.stderr.write("[review-round-labels] road: %s (%s); %d files, %d candidate lines, %d credit spellings\n"
                 % (ROAD, REASON, len(FILES), len(LINES), len(FORM_SPACE)))


class ReviewRoundLabels(unittest.TestCase):
    def _where(self):
        return "road %s: %s" % (ROAD, REASON)

    def test_every_listed_file_exists(self):
        missing = [f for f in FILES if not os.path.isfile(os.path.join(ROOT, f))]
        self.assertEqual(missing, [], "a listed file moved (%s): regenerate the manifest; a missing file must not read as clean" % self._where())

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
               "the author's %s 3" % R, "the fixer's %s-2" % R, "the reviewer's %ss 1 to %d" % (R, REVIEWER_ROUNDS + 1), "review %s 0" % R]
        green = [plant("review", "", REVIEWER_ROUNDS), "the reviewer's %s-%d finding kernel-1" % (R, REVIEWER_ROUNDS), plant("maintainer's", "", REVIEWER_ROUNDS),
                 "the %s-3 fixlist's extra9-1" % R, "%s 2's ruling" % R, "the %s-1 refuter's screenshot" % R, "the %s-4 verdict-1 case" % R,
                 "review %s 2 closeout" % R, "Review %s %d fixes:" % (R, REVIEWER_ROUNDS), "the reviewer's %ss 1 to %d" % (R, REVIEWER_ROUNDS),
                 "review %ss 5 and %d" % (R, REVIEWER_ROUNDS), "pass 5, the author's label", "the author's pass-5 %s" % V, "pass 4b",
                 "a%s 6" % R, "backg%s 6" % R, "%s-trip" % R, "REVIEWER_ROUNDS = %d" % REVIEWER_ROUNDS]
        self.assertEqual([s for s in red if not offences(s)], [], "a refused form read as clean")
        self.assertEqual([s for s in green if offences(s)], [], "an allowed form read as an offence")
        self.assertEqual([t.rule for t in tokens("review %s 5 %s and %s 4b and since %s 2 and the %s-3 fixlist" % (R, V, R, R, R))],
                         ["verify", "lettered", "bare", "credit"])
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
        write_manifest(FILES, LINES, REASON)
        print("wrote %s: %d files, %d candidate lines" % (MANIFEST, len(FILES), len(LINES)))
    else:
        unittest.main()
