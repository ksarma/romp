#!/usr/bin/env python3
"""The link-drop lab family's comments credit a maintainer round only where a ruling exists (the author's pass 10, 2026-09-20).

Two numberings meet in the family's comments, docstrings and messages. The MAINTAINER's rounds on PR 857 are the rulings
files in the reviewer's notes outside the repo (rulings-r1.md to rulings-r5.md at filing); the AUTHOR's passes are the
build-and-verify passes before, between and after them, numbered 1 to 10 by the PR body's convention paragraph. Before this
pass the tree said "round N" in the author's pipeline's own numbering, which matched neither: one number named two passes
(the pipeline's fifth round was pass 6 in the served module's expired-wait comments and pass 9 in the mint and parsed
modules), the pipeline's "round-N head" named the pass-3 head in one module and the pass-7 head in another, and 47 lines credited a
sixth round no ruling exists for. The sweep derived every mention from the line's commit and its sentence: a ruling, a
refuter's probe or a ruled head is "the maintainer's round N" with N the notes' number; the author's own work is "pass P",
"pass P's fixer pass" or "the pass-P head", the head after the author's pass P.

This module is the ratchet. A numbered round ("round N", "round-N", "Round N's", "round N of PR 857") is a credit to the
maintainer, so it is refused unless spelled "the maintainer's round N" with N a round a ruling exists for. The allowed set is
DERIVED from the rulings files present in the reviewer's notes directory when it is on the machine (`rulings-r<N>.md`,
contiguous from 1; the directory is named by ROMP_REVIEW_NOTES_DIR, else the default below), so a new ruling widens it
without an edit here. Where the directory is absent (a contributor's clone, CI) the set is 1 to MAINTAINER_ROUNDS_AT_FILING,
the count when this module was written, so a mention of a later maintainer round reds there until the constant is raised
in the same change: the constant is the repo's own record of how many rounds were held, and the directory is the live
source. Unnumbered uses are not read: the parsed walk's fixpoint vocabulary ("rounds=40", "a typing round", "the two-round
convergence bound", "in its second round"), Python's round() and the substring "around" carry no credit. No file of the
family quotes a ruling sentence that carries a numbered round today, so the rule has no quotation exemption (an exemption
nothing fires would be untested); a quote added later takes the maintainer's form or is paraphrased.

FILES are the family's five files (the four modules and the ledger entry) and this module, read whole: the four modules and
the entry are new in the branch, so every line of them is the branch's own and the census is over the branch's added lines.
The probes in the form-space test are assembled at run time because this module reads itself.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)

MAINTAINER_ROUNDS_AT_FILING = 5   # rulings-r1.md to rulings-r5.md existed when this module was written (2026-09-19 to 2026-09-20)
NOTES_DIR = os.environ.get("ROMP_REVIEW_NOTES_DIR") or os.path.expanduser("~/romp-handoffs/romp-general-notes/iosperf857-notes")
RULINGS = re.compile(r"rulings-r(\d+)\.md")

FILES = [
    "tests/test_federated_linkdrop_served.py",
    "tests/test_federated_linkdrop_mint.py",
    "tests/test_federated_linkdrop_driver_bound.py",
    "tests/test_federated_linkdrop_driver_parsed_served.py",
    "tests/test_federated_linkdrop_round_labels.py",
    "upstream/2026-09-19-tests-federated-linkdrop-served.md",
]

# a numbered round, however spelled, and the one form that credits a ruled round
LABEL = re.compile(r"\bround[- ]?(\d+)\b", re.I)
CREDIT = re.compile(r"the maintainer's round[- ]?(\d+)\b", re.I)


def ruled_rounds():
    """(the rounds a ruling exists for, where that came from): the rulings files present in the notes directory when it is on
    this machine, else 1 to MAINTAINER_ROUNDS_AT_FILING."""
    if os.path.isdir(NOTES_DIR):
        found = sorted(int(m.group(1)) for f in os.listdir(NOTES_DIR) for m in [RULINGS.fullmatch(f)] if m)
        return found, "the rulings files under the notes directory"
    return list(range(1, MAINTAINER_ROUNDS_AT_FILING + 1)), "MAINTAINER_ROUNDS_AT_FILING (the notes directory is not on this machine)"


def offences(text, allowed):
    """(line number, the mention, why) for every numbered round in `text` that is not "the maintainer's round N" with N in
    `allowed`."""
    out = []
    for i, line in enumerate(text.split("\n"), 1):
        credited = {m.start(1) for m in CREDIT.finditer(line)}
        for m in LABEL.finditer(line):
            n = int(m.group(1))
            if m.start(1) not in credited:
                out.append((i, m.group(0), "a numbered round is a credit to the maintainer: write \"the maintainer's round N\" for a ruled "
                                           "round, or the author's \"pass P\" / \"the pass-P head\" for the author's own work"))
            elif n not in allowed:
                out.append((i, m.group(0), "no ruling exists for that maintainer round; the rulings are rounds %s" % (allowed,)))
    return out


def mentions(text):
    return [m.group(0) for m in LABEL.finditer(text)]


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


class RoundLabels(unittest.TestCase):
    def test_every_listed_file_exists(self):
        missing = [f for f in FILES if not os.path.isfile(os.path.join(ROOT, f))]
        self.assertEqual(missing, [], "a listed file moved: re-list it (a missing file must not read as clean)")

    def test_the_ruled_rounds_are_derived_and_contiguous_from_one(self):
        allowed, source = ruled_rounds()
        self.assertTrue(allowed, "no ruled round at all from %s: the derivation read nothing" % source)
        self.assertEqual(allowed, list(range(1, max(allowed) + 1)), "the rulings are numbered contiguously from 1 (%s): %r" % (source, allowed))
        self.assertGreaterEqual(max(allowed), MAINTAINER_ROUNDS_AT_FILING,
                                "a ruling that existed at filing is missing from %s: %r" % (source, allowed))

    def test_no_mention_credits_a_round_the_maintainer_never_held(self):
        allowed, source = ruled_rounds()
        bad, seen = [], 0
        for rel in FILES:
            text = _read(rel)
            seen += len(mentions(text))
            bad += ["%s:%d: %r (%s)" % (rel, ln, label, why) for ln, label, why in offences(text, allowed)]
        self.assertGreater(seen, 0, "the census read no numbered round at all: the pattern or the file list is broken")
        self.assertEqual(bad, [], "a numbered round that is not a ruled maintainer round (rounds %s, from %s); write the author's pass "
                                  "(\"pass P\", \"pass P's fixer pass\", \"the pass-P head\") or \"the maintainer's round N\" for a round a "
                                  "ruling exists for:\n%s" % (allowed, source, "\n".join(bad)))

    def test_the_form_space(self):
        """The classifier over the shapes the family wrote, so the census is known to read them; the probes are assembled at run
        time because this module is in FILES and reads itself."""
        allowed, _ = ruled_rounds()
        R, hi, lo = "round", max(allowed), min(allowed)
        red = ["%s %d" % (R, hi + 1), "the %s-%d head" % (R, hi + 1), "%s %d's fixer pass" % (R, hi + 1), "%s %d's review" % (R, lo),
               "R%s %d found the key" % (R[1:], lo), "(%s %d, tests-1)" % (R, lo), "%s %d's high" % (R, lo), "(2026-09-20, %s %d of PR 857)" % (R, hi),
               "the maintainer's %s %d" % (R, hi + 1), "the maintainer's %s-%d voters" % (R, hi + 1), "since %s %d" % (R, hi), "the %s's failing-before (%s %d)" % (R, R, lo)]
        green = ["the maintainer's %s %d" % (R, hi), "the maintainer's %s-%d voters" % (R, lo), "the maintainer's %s %d's tests-3" % (R, lo),
                 "the maintainer's %s %d (its addendum)" % (R, hi), "pass 9", "the pass-7 head", "pass 10's fixer pass", "the author's pass 3",
                 "%ss=40" % R, "in 1 %ss" % R, "a typing %s" % R, "the two-%s convergence bound" % R, "in its second %s" % R,
                 "_commands_a%s_the_recorder" % R, "%s(t_dead - t0, 2)" % R, "spaces-a%s-dots" % R, "rulings-r1.md", "the boot a%s it" % R,
                 "each %s of planting" % R]
        self.assertEqual([s for s in red if not offences(s, allowed)], [], "a refused form read as clean")
        self.assertEqual([s for s in green if offences(s, allowed)], [], "an allowed form read as an offence")
        self.assertEqual(mentions("the maintainer's %s %d and %s-%d and R%s %d's" % (R, hi, R, lo, R[1:], lo)),
                         ["%s %d" % (R, hi), "%s-%d" % (R, lo), "R%s %d" % (R[1:], lo)])
        # the two refusals are told apart: an uncredited number, and a credit to a round with no ruling
        self.assertIn("credit to the maintainer", offences("%s %d" % (R, hi), allowed)[0][2])
        self.assertIn("no ruling exists", offences("the maintainer's %s %d" % (R, hi + 1), allowed)[0][2])


if __name__ == "__main__":
    unittest.main()
