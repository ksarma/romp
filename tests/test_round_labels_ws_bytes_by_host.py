#!/usr/bin/env python3
"""Every review round the wsBytesByHost branch's lines name is one the maintainer held, named as the maintainer's (the author's
pass after the maintainer's round 5, 2026-09-21; the population re-derived and the fallbacks deleted in the pass after the
maintainer's round 6).

A PER-BRANCH GUARD over the lines this branch ADDS, and nothing wider: it is deleted at landing, its job done. THE RULE below
(the form space, what credits a round) will live once, in the shared helper of PR 857 (its eleventh pass; the maintainer's round
6 ruling of 03:04Z), after which this module becomes a few-line caller handing that helper the population derived here. Nothing
in this module is tree-wide: no manifest of files, no fact table of other work's lines, no fixture.

Two numberings meet in a reviewed branch's comments and test prose, and the PR body's convention paragraph tells them apart:
the MAINTAINER's rounds are the rulings the reviewer filed (on this PR: 1, its addendum, 3, 4, 5 and 6; the maintainer held no
second round), and the AUTHOR's passes are the builds between them (0, 0b, 1, 3, 4, the mirror-and-twins pass, the pass after
the maintainer's round 4, the pass after the maintainer's round 5, the pass after the maintainer's round 6, each with its verify
and fixer pass). The pushed commit labels count the author's passes, so a comment written under the label of the author's
fourth pass was written in that pass, which applied the maintainer's round 3; a bare fourth-round mention in such a comment
named one thing to its writer and another to a reader of the rulings. The maintainer ruled on the lazy-panes PR that the body's
convention is carried into the repo's own comments, and the same sweep was made here before the push after the
maintainer's round 5: every mention now names either the maintainer's round, by its number, or the author's pass, by the label
mapping, and a round of the earlier cut's review (2026-09-18) is named as that cut's review with no number.

THE RULE this module holds: in the branch's lines, the word "round" followed by a number is written only as "the maintainer's
round N" (a hyphen or a space before N) with N in REVIEWER_ROUNDS; a numbered round without the maintainer's name before it is
refused, as is one numbered past the rounds held, and so is a bare referential form (the word after an article, "the", "this" or
"that", or with a possessive and no number; a verify, a fixer pass, a build or a probe is the author's pass, and is named so:
"the author's pass 4", "the author's pass-1 verify"). The qualifier may end the line above the mention, as a wrapped comment has
it: the mention is then the first prose on its line, after the comment marker, and the previous non-blank line ends with the
qualifier (offences reads the previous line for that one shape, and for nothing else; the maintainer's round 6, B: the docstring
had stated this and the code had searched the mention's own line alone). "round-trip" and Math.round are not mentions.

REVIEWER_ROUNDS is a constant of this tree, derived from the maintainer's rulings on this PR (rounds 1, 3, 4, 5 and 6, the first
with an addendum; the sixth added 2026-09-21 when its ruling landed); the author raises it when a ruling lands. It is read from
nothing outside the repository: the reviewer's notes are on one machine, and a set sourced from a path the tree does not contain
would fail on every other clone for nobody's defect or pass with nothing to check.

THE POPULATION is the lines this branch ADDS, read from the COMMITTED tree and never from the working tree: the merge base of
origin/main and HEAD must be BASE, the merge base this branch was pushed from, and the lines are the added lines of
`git diff -U0 BASE HEAD`, by file and by line number in HEAD's version of the file. The branch's lines are told from the base's
by the DIFF, so a line of other work arriving through a later merge of main is not the branch's, and an uncommitted edit to any
tracked file is not read. Where the derivation is unavailable the population test SKIPS, its reason naming what was
unreachable: origin/main (a shallow CI clone, where this guard checks nothing and says so) or a merge base that is not BASE (a
merged head, where BASE is raised to the new merge base with the merge; or another branch, whose lines this guard is not
about). A guard that cannot derive its population substitutes no other (the maintainer's round 6, tests-2: the manifest this
module read where git could not answer made it a repo-wide gate over every later change's lines, in CI from its first run and
on main after landing). The form-space test runs everywhere: the rule needs no tree.

Exits, for a later change that reds here: a line that names an author's pass names it as the author's; a line that names a
maintainer's round of THIS PR names it as the maintainer's; a round of another PR's review in one of these files is written with
that review named ("the parked-pane change's review, its third round"), which the numbered form does not match; a new
maintainer's round on this PR is a new ruling, and REVIEWER_ROUNDS is raised with it; after a merge of main, BASE is raised to
the new merge base (until it is, the population test skips and says so).
"""
import re
import subprocess
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SELF = "tests/test_round_labels_ws_bytes_by_host.py"

BASE = "5b8df8f5c207f180d786b789abffd38b4a57376b"   # the branch's merge base with main at the push after the maintainer's round 5 (2026-09-21); raised with every merge of main

# the maintainer's rounds on this PR, derived from the rulings filed on it (1 with its addendum, 3, 4, 5, 6; no second)
REVIEWER_ROUNDS = frozenset({1, 3, 4, 5, 6})

# a mention: the word followed by a number (a hyphen or a space between: an identifier such as round1 is code, not prose), or
# the bare referential forms; "round-trip" in either spelling and a method named round are not mentions (the number group is
# empty for a bare form)
MENTION = re.compile(r"\bround[- ](\d+)\b|\b(?:the|this|that) round\b(?![- ]?trip)|\bround's\b", re.I)
QUALIFIER = re.compile(r"\bmaintainer's\s+$", re.I)   # what must stand immediately before a numbered mention: on its line, or ending the line above when the mention opens its line (THE RULE, the docstring)
MARKER = re.compile(r"^\s*(?:#|//|/\*|\*|<!--)?\s*")               # a comment marker and the whitespace around it, which a wrapped line begins with

# a doubled attribution in one run of prose (the maintainer's round 6, H): the same possessive's "pass after" twice in a row (the
# sweep's artefact, a qualifier inlined on a line whose line above already ended with it), or the same attribution twice adjacent
DOUBLED = re.compile(r"\b(the (?:author's|maintainer's))\s+(?:fixer\s+)?pass after\s+\1\s+(?:fixer\s+)?pass after\b"
                     r"|\b(the (?:author's|maintainer's) (?:fixer pass|pass|round)(?:[- ]\d+)?)\s+\2\b", re.I)

# a hunk header of a unified diff: the new side's first line number (and its count, absent for one line)
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def mention_lines(text):
    """(line number, line) for every line of `text` carrying a mention."""
    return [(i, line) for i, line in enumerate(text.split("\n"), 1) if MENTION.search(line)]


def qualified(line, m, prev):
    """Whether the numbered mention `m` in `line` has the qualifier immediately before it: on its own line, or ending `prev`, the
    previous non-blank line, when the mention is the first prose on its line after the comment marker (a wrapped comment)."""
    if QUALIFIER.search(line[:m.start()]):
        return True
    return prev is not None and MARKER.match(line).end() == m.start() and QUALIFIER.search(prev.rstrip() + " ") is not None


def offences(line, rounds=REVIEWER_ROUNDS, prev=None):
    """(the mention, why) for every mention in `line` the rule refuses; `prev` is the previous non-blank line, for the wrapped shape."""
    out = []
    for m in MENTION.finditer(line):
        n = m.group(1)
        if n is None:
            out.append((m.group(0), "a bare referential form: name the maintainer's round or the author's pass"))
        elif not qualified(line, m, prev):
            out.append((m.group(0), "a numbered round without the maintainer's name before it"))
        elif int(n) not in rounds:
            out.append((m.group(0), "the maintainer held rounds %s" % ", ".join(str(r) for r in sorted(rounds))))
    return out


def joined_runs(lines):
    """(first line number, last line number, the prose) for every run of consecutive added lines, each line's comment marker
    stripped and the lines joined by a space, whitespace collapsed: a comment read across its line breaks."""
    out, run = [], []
    for ln, line in lines:
        if run and ln != run[-1][0] + 1:
            out.append(run)
            run = []
        run.append((ln, line))
    if run:
        out.append(run)
    return [(r[0][0], r[-1][0], re.sub(r"\s+", " ", " ".join(MARKER.sub("", l.rstrip()) for _, l in r)).strip()) for r in out]


def previous_line(lines, ln):
    """The previous non-blank line of a file (`lines` its lines, `ln` a 1-based line number), or None at the top."""
    for k in range(ln - 2, -1, -1):
        if lines[k].strip():
            return lines[k]
    return None


def _git(*args):
    """(git's stdout, None) run in ROOT, or (None, why) when git is absent or the command fails (a shallow checkout, a missing
    ref, no repository): the reason is the skip's, so it names the command and git's first line."""
    try:
        p = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, "git %s did not run: %s" % (" ".join(args), e.__class__.__name__)
    if p.returncode != 0:
        return None, "git %s exited %d: %s" % (" ".join(args), p.returncode, (p.stderr.strip() or "(nothing on stderr)").split("\n")[0])
    return p.stdout, None


def added_lines(diff):
    """{file: [(line number in the new side, line)]} for every line a unified diff with no context lines adds; a deleted or a
    binary file adds none, a renamed file's lines are under its new path, and a removed line moves the new side's numbering
    not at all. The header of a file is the `+++` line after its `---` line, so an added line that begins with two plus signs
    is a line and not a header."""
    out, rel, ln, after_old = {}, None, 0, False
    for raw in diff.split("\n"):
        if after_old and raw.startswith("+++ "):
            new = raw[4:]
            rel = None if new == "/dev/null" else (new[2:] if new.startswith("b/") else new)
            after_old = False
            continue
        after_old = raw.startswith("--- ")
        m = HUNK.match(raw)
        if m:
            ln = int(m.group(1))
            continue
        if rel is None or not raw.startswith("+"):
            continue
        out.setdefault(rel, []).append((ln, raw[1:]))
        ln += 1
    return out


def branch_population():
    """(the lines this branch adds, by file; how they were derived), from the committed tree, or a SkipTest whose reason names what
    was unreachable: this guard reads a population it derived or none."""
    mb, why = _git("merge-base", "origin/main", "HEAD")
    if mb is None:
        raise unittest.SkipTest("the merge base of origin/main and HEAD is not reachable in this checkout (%s; a shallow CI clone has no "
                                "origin/main), so the branch's added lines cannot be derived: this guard read nothing here and substitutes "
                                "no other population" % why)
    if mb.strip() != BASE:
        raise unittest.SkipTest("the merge base with origin/main is %s, not BASE %s: a merged head (raise BASE to the new merge base) or "
                                "another branch (this guard is that branch's); the branch's added lines are not derivable here, so nothing "
                                "was read" % (mb.strip()[:9], BASE[:9]))
    diff, why = _git("-c", "diff.noprefix=false", "-c", "diff.mnemonicPrefix=false", "diff", "--no-color", "--no-ext-diff", "-U0", BASE, "HEAD")
    if diff is None:
        raise unittest.SkipTest("the diff of BASE %s against HEAD could not be read (%s), so the branch's added lines cannot be derived: "
                                "nothing was read" % (BASE[:9], why))
    return added_lines(diff), "the added lines of `git diff -U0 %s HEAD`, the committed tree" % BASE[:9]


class RoundLabels(unittest.TestCase):
    def test_no_branch_line_names_a_round_the_maintainer_did_not_hold_or_names_it_bare(self):
        added, how = branch_population()
        self.assertIn(SELF, added, "the rig: this module is a file the branch adds, so its own lines are in the population it derives (%s)" % how)
        bad, read, carrying = [], 0, set()
        for rel, lines in sorted(added.items()):
            if not any(MENTION.search(line) for _, line in lines):
                continue
            text, why = _git("show", "HEAD:" + rel)     # the committed file, for the line above a wrapped mention (a base line or an added one)
            self.assertIsNotNone(text, "the rig: HEAD's %s could not be read (%s)" % (rel, why))
            head_lines = text.split("\n")
            for ln, line in lines:
                if not MENTION.search(line):
                    continue
                self.assertEqual(head_lines[ln - 1], line, "the rig: the diff's line %d of %s is HEAD's line %d" % (ln, rel, ln))
                read += 1
                carrying.add(rel)
                bad += ["%s:%d: %r (%s)" % (rel, ln, mention, why) for mention, why in offences(line, prev=previous_line(head_lines, ln))]
        self.assertGreater(read, 0, "the census read no added line carrying a mention: the pattern or the derivation (%s) is broken" % how)
        self.assertEqual(bad, [], "a branch line names a round the maintainer did not hold, or names one bare; write the "
                                  "maintainer's round by its number or the author's pass by the label mapping (the module "
                                  "docstring). REVIEWER_ROUNDS is %s; the lines came from %s; %d added lines carrying a mention read "
                                  "in %d of the %d files the branch changes:\n%s"
                                  % (sorted(REVIEWER_ROUNDS), how, read, len(carrying), len(added), "\n".join(bad)))

    def test_no_added_comment_repeats_an_attribution_across_its_line_breaks(self):
        """A mechanical rewrite over prose owes a read-back (the maintainer's round 6, H): the sweep that reworded the mentions
        inlined the full qualifier on a continuation line whose line above already ended with it, and a per-line census cannot see
        a doubling that spans the break. So the added lines are read as prose, joined_runs, and a doubled attribution in one run is refused
        (DOUBLED). A list of distinct forms is not a repeat, and the probes below say so."""
        added, how = branch_population()
        bad = []
        for rel, lines in sorted(added.items()):
            for first, last, text in joined_runs(lines):
                bad += ["%s:%d-%d: %r" % (rel, first, last, text[max(0, m.start() - 40):m.end() + 30]) for m in DOUBLED.finditer(text)]
        self.assertEqual(bad, [], "an added comment repeats an attribution across its line breaks; the lines came from %s:\n%s" % (how, "\n".join(bad)))
        A, M, R = "the author's", "the maintainer's", "round"
        self.assertEqual(len(DOUBLED.findall("(%s fixer pass after %s fixer pass after %s %s 5, refusal-1: the census read)" % (A, A, M, R))), 1,
                         "the sweep's doubling, the qualifier inlined on a line whose line above ended with it")
        self.assertEqual(len(DOUBLED.findall("%s %s 5 %s %s 5 on panel-3" % (M, R, M, R))), 1, "the same attribution twice adjacent")
        self.assertEqual(len(DOUBLED.findall("%s pass 4 %s pass 4" % (A, A))), 1)
        for clean in ("the pass after %s %s 4, the pass after %s %s 5" % (M, R, M, R), "%s pass 4 and %s pass 5" % (A, A),
                      "(%s fixer pass after %s %s 5, refusal-1: the census read)" % (A, M, R), "%s %s 5 and %s %s-4 ruling" % (M, R, M, R)):
            self.assertEqual(DOUBLED.findall(clean), [], "a list of distinct forms is not a repeat: %r" % clean)
        self.assertEqual(joined_runs([(3, "# a"), (4, "#  b"), (7, "// c"), (8, " * d")]), [(3, 4, "a b"), (7, 8, "c d")], "runs by consecutive numbers, markers stripped")

    def test_the_diff_reader_numbers_added_lines_in_the_new_side(self):
        """The reader over `git diff -U0`: two files, a hunk after removed lines (the new side's numbering does not move for
        them), a second hunk, a deleted file (nothing added), a header-shaped added line, and a renamed file under its new path."""
        diff = "\n".join([
            "diff --git a/x.py b/x.py", "index 1..2 100644", "--- a/x.py", "+++ b/x.py",
            "@@ -3,2 +3 @@", "-gone one", "-gone two", "+kept three",
            "@@ -10 +9,3 @@", "+++ a line beginning with two plus signs", "+ten", "+eleven",
            "diff --git a/d.py b/d.py", "deleted file mode 100644", "index 3..0", "--- a/d.py", "+++ /dev/null",
            "@@ -1,2 +0,0 @@", "-was", "-here",
            "diff --git a/old.md b/new.md", "similarity index 90%", "rename from old.md", "rename to new.md", "index 4..5 100644",
            "--- a/old.md", "+++ b/new.md", "@@ -1 +1 @@", "-a", "+b", ""])
        self.assertEqual(added_lines(diff), {"x.py": [(3, "kept three"), (9, "++ a line beginning with two plus signs"), (10, "ten"), (11, "eleven")],
                                             "new.md": [(1, "b")]})

    def test_the_form_space(self):
        """The classifier over the shapes the branch wrote and the shapes it refuses; the probes are assembled at run time
        because this module is in the population and reads itself."""
        R, M = "round", "the maintainer's"
        red = ["%s 7" % R, "review %s 2, 2026-09-18" % R, "the %s-3 find" % R, "since %s 4 of the review" % R, "the author's %s 5 prep" % R,
               "(%s 4, tests-2)" % R, "the clauses the %s asked for" % R, "this %s" % R, "the %s's fixer pass" % R, "%s 5's bounded refusal" % R,
               "%s %s 2" % (M, R), "%s %s 7" % (M, R), "The Maintainer's %s-8 ruling" % R, "the author's pass after %s 4" % R,
               "the reviewer's %s 4" % R, "%s %s 5 and %s 6" % (M, R, R)]
        green = ["%s %s 5" % (M, R), "%s %s-4 ruling" % (M, R), "The maintainer's %s 1 addendum, fresh-2" % R, "%s %s 3, extra8-2; sayDeltaOnce" % (M, R),
                 " *  maintainer's %s 5 on panel-3" % R, "%s %s 6, tests-2" % (M, R), "the author's pass 4", "the author's pass-3 fixer pass", "the author's pass-1 verify",
                 "the author's pass after %s %s 5" % (M, R), "%s-trip" % R, "the %s-trip" % R, "the %s trip" % R, "Math.%s(x)" % R,
                 "%ss 1, 3, 4, 5 and 6" % R, "a%s 6" % R, "backg%s 4" % R, "the earlier cut's review, 2026-09-18", "the ground floor",
                 "%s1 as an identifier" % R]
        self.assertEqual([s for s in red if not offences(s)], [], "a refused form read as clean")
        self.assertEqual([s for s in green if offences(s)], [], "an allowed form read as an offence")
        self.assertEqual(len(offences("%s %s 5 and %s 6" % (M, R, R))), 1, "one offence per refused mention, the allowed one beside it not counted")
        self.assertIsNone(MENTION.search("the %s-trip and the %s trip" % (R, R)), "neither spelling of round-trip is a mention")
        self.assertEqual(len(mention_lines("a\n%s 7\nb\nthe %s asked\n" % (R, R))), 2)
        self.assertEqual(offences("%s %s 7" % (M, R), rounds=frozenset({7})), [], "a raised REVIEWER_ROUNDS admits the new round")
        # the wrapped shapes, two lines each (the maintainer's round 6, B): the qualifier ending the line above a mention that opens
        # its line is accepted, in every comment marker; a bare number opening a line whose line above ends otherwise is refused,
        # as is a mention the qualifier's line does not immediately precede (prose before it on its own line)
        for marker in ("// ", "# ", " *  ", "   ", "<!-- "):
            self.assertEqual(offences("%s%s 5, tests-1)" % (marker, R), prev="   (%s" % M), [], "a wrapped qualifier accepted under %r" % marker)
        self.assertEqual(len(offences("// %s 5" % R, prev="// the")), 1, "the article alone above a wrapped bare number: refused")
        self.assertEqual(len(offences(" * %s 5 on panel-3" % R, prev=" * ruled on")), 1, "a wrapped bare number under an unqualified line: refused")
        self.assertEqual(len(offences("// and %s 5" % R, prev="// %s" % M)), 1, "the qualifier above does not reach a mention that is not first on its line")
        self.assertEqual(len(offences("%s 5" % R, prev=None)), 1, "no line above: refused")
        self.assertEqual(previous_line(["a", "", "  ", "b"], 4), "a", "the previous non-blank line, blanks skipped")
        self.assertIsNone(previous_line(["a"], 1), "nothing above the first line")


if __name__ == "__main__":
    unittest.main()
