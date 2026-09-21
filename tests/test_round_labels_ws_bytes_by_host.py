#!/usr/bin/env python3
"""Every review round the wsBytesByHost branch's lines name is one the maintainer held, named as the maintainer's (the author's
pass after the maintainer's round 5, 2026-09-21).

Two numberings meet in a reviewed branch's comments and test prose, and the PR body's convention paragraph tells them apart:
the MAINTAINER's rounds are the rulings the reviewer filed (on this PR: 1, its addendum, 3, 4 and 5; the maintainer held no
second round), and the AUTHOR's passes are the builds between them (0, 0b, 1, 3, 4, the mirror-and-twins pass, the pass after
the maintainer's round 4, the pass after the maintainer's round 5, each with its verify and fixer pass). The pushed commit
labels count the author's passes, so a comment written under the label of the author's fourth pass was written in that pass,
which applied the maintainer's round 3; a bare fourth-round mention in such a comment named one thing to its writer and another
to a reader of the rulings. The maintainer ruled on the lazy-panes PR that the body's convention is carried into the repo's own
comments, and the same sweep was made here before the push after the maintainer's round 5: every mention now names either the
maintainer's round, by its number, or the author's pass, by the label mapping, and a round of the earlier cut's review
(2026-09-18) is named as that cut's review with no number.

THE RULE this module holds: in the branch's lines, the word "round" followed by a number is written only as "the maintainer's
round N" (a hyphen or a space before N) with N in REVIEWER_ROUNDS; a numbered round without the maintainer's name before it is
refused, as is one numbered past the rounds held, and so is a bare referential form (the word after an article, "the", "this" or
"that", or with a possessive and no number; a verify, a fixer pass, a build or a probe is the author's pass, and is named so:
"the author's pass 4", "the author's pass-3 fixer pass", "the author's pass-1 verify"). The qualifier may end the line above the
mention, as a wrapped comment has it. "round-trip" and Math.round are not mentions.

REVIEWER_ROUNDS is a constant of this tree, derived 2026-09-21 from the maintainer's rulings on this PR at filing (rounds 1, 3,
4 and 5, the first with an addendum); the author raises it when a ruling lands. It is read from nothing outside the repository:
the reviewer's notes are on one machine, and a set sourced from a path the tree does not contain would fail on every other
clone for nobody's defect or pass with nothing to check.

THE POPULATION is the branch's own lines, derived by content and not by blame (blame needs the history, which a CI checkout
does not have). The FILES are derived from git where git can: when the merge base of origin/main and HEAD is BASE, the merge
base this branch was pushed from, the files are `git diff --name-only BASE` (the tracked changes of this checkout against BASE,
staged additions included) and the committed manifest MANIFEST is pinned equal to that derivation; where it cannot (a shallow
CI clone has no origin/main; a merged head or another branch has a different merge base, and this branch's diff is not
derivable there) the manifest is read, and the assertion messages say so. A line of a listed file is the branch's when its
content is not a line of the merge base's version of the file: the merge base's version is held as a fixture, the hashes of the
lines of each file at BASE that carry a mention (the only lines this census reads, so the hashes are the whole content test for
them); a mention line whose hash is in that set is other work's, pre-existing at BASE, and is not read. Other work's round
mentions are many (kernel.py names its own reviews' rounds in some 370 lines; bin/romp, federation.ts and the two federation
delta tests name earlier changes' rounds), so a whole-file read is not available for these files; the hashes are the exact
complement. When the checkout has BASE, the fixture is re-derived from it and compared; when it does not, the fixture's shape is
checked and the message says it was not re-derived. Nothing in this module skips.

Exits, for a later change that reds here: a line that names an author's pass names it as the author's; a line that names a
maintainer's round of THIS PR names it as the maintainer's; a round of another PR's review in one of these files is written with
that review named ("the parked-pane change's review, its third round"), which the numbered form does not match; a new
maintainer's round on this PR is a new ruling, and REVIEWER_ROUNDS is raised with it; a file this branch adds later joins
MANIFEST with a fixture entry (test_the_manifest_is_the_derivation pins that while the branch is cut at BASE); a file that stops
being this branch's concern comes out of both with a note here. A missing listed file is a red, not a skip.
"""
import hashlib
import json
import os
import re
import subprocess
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)

BASE = "5b8df8f5c207f180d786b789abffd38b4a57376b"   # the branch's merge base with main at the push after the maintainer's round 5 (2026-09-21)

# the maintainer's rounds on this PR, derived 2026-09-21 from the rulings filed on it (1 with its addendum, 3, 4, 5; no second)
REVIEWER_ROUNDS = frozenset({1, 3, 4, 5})

# the manifest: `git diff --name-only BASE..HEAD` at the push after the maintainer's round 5 (34 files), plus this module and
# its fixture; pinned equal to the live derivation while the branch is cut at BASE (test_the_manifest_is_the_derivation)
MANIFEST = [
    ".github/workflows/ci.yml",
    "bin/romp",
    "docs/read-side.md",
    "docs/reference.md",
    "kernel/kernel.py",
    "tests/fixtures/round_labels_ws_bytes_by_host_base_mentions.json",
    "tests/romp-perf-client.bats",
    "tests/test_client_diag_allowlist.py",
    "tests/test_federated_capability_corners_served.py",
    "tests/test_federated_dial_terms_served.py",
    "tests/test_federated_relay_redial_served.py",
    "tests/test_kernel.py",
    "tests/test_relay_dial_declares_held_pair.py",
    "tests/test_round_labels_ws_bytes_by_host.py",
    "tests/test_served_labs_under_ci.py",
    "ui/webview/css-census.test.ts",
    "ui/webview/federation-remote-feed-delta.test.ts",
    "ui/webview/federation-remote-view-delta.test.ts",
    "ui/webview/federation-ws-bytes-by-host.test.ts",
    "ui/webview/federation.ts",
    "ui/webview/feed-clock-anchor.test.ts",
    "ui/webview/feed-delta.test.ts",
    "ui/webview/feed-delta.ts",
    "ui/webview/file-view-perf.test.ts",
    "ui/webview/file-view-seam.test.ts",
    "ui/webview/gear-sub-focus-browser.test.ts",
    "ui/webview/gear-tabs.test.ts",
    "ui/webview/gear.css",
    "ui/webview/gear.js",
    "ui/webview/gear.test.ts",
    "ui/webview/perf-beacon-settings.test.ts",
    "ui/webview/perf-telemetry.test.ts",
    "ui/webview/perf-telemetry.ts",
    "ui/webview/view-deltas.ts",
    "upstream/2026-09-18-phone-beacon-extension.md",
    "upstream/2026-09-19-relay-dial-page-caps-ws-bytes-by-host.md",
]
# the hashes of the mention lines of each manifest file at BASE (base_mentions_from_git(), run 2026-09-21), one entry per file,
# a file the branch added with none; a fixture because kernel.py alone carries hundreds of other work's mention lines
FIXTURE = "tests/fixtures/round_labels_ws_bytes_by_host_base_mentions.json"

# a mention: the word followed by a number (a hyphen or a space between: an identifier such as round1 is code, not prose), or
# the bare referential forms; "round-trip" in either spelling and a method named round are not mentions (the number group is
# empty for a bare form)
MENTION = re.compile(r"\bround[- ](\d+)\b|\b(?:the|this|that) round\b(?![- ]?trip)|\bround's\b", re.I)
QUALIFIER = re.compile(r"\bmaintainer's\s+$", re.I)   # what must stand immediately before a numbered mention ("the" may end the line above)


def mention_lines(text):
    """(line number, line) for every line of `text` carrying a mention."""
    return [(i, line) for i, line in enumerate(text.split("\n"), 1) if MENTION.search(line)]


def line_hash(line):
    return hashlib.sha1(line.strip().encode("utf-8")).hexdigest()[:12]


def offences(line, rounds=REVIEWER_ROUNDS):
    """(the mention, why) for every mention in `line` the rule refuses."""
    out = []
    for m in MENTION.finditer(line):
        n = m.group(1)
        if n is None:
            out.append((m.group(0), "a bare referential form: name the maintainer's round or the author's pass"))
        elif not QUALIFIER.search(line[:m.start()]):
            out.append((m.group(0), "a numbered round without the maintainer's name before it"))
        elif int(n) not in rounds:
            out.append((m.group(0), "the maintainer held rounds %s" % ", ".join(str(r) for r in sorted(rounds))))
    return out


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def _git(*args):
    """git's stdout in ROOT, or None when git is absent or the command fails (a shallow checkout, a missing ref)."""
    try:
        p = subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return p.stdout if p.returncode == 0 else None


def branch_files():
    """(the files, how they were derived): git's answer when this checkout is the branch cut at BASE, else the manifest."""
    mb = _git("merge-base", "origin/main", "HEAD")
    if mb is None:
        return list(MANIFEST), "the manifest (origin/main is not reachable in this checkout, as in a shallow CI clone)"
    if mb.strip() != BASE:
        return list(MANIFEST), ("the manifest (the merge base with origin/main is %s, not BASE: a merged head or another branch, "
                                "where this branch's diff is not derivable)" % mb.strip()[:9])
    names = (_git("diff", "--name-only", BASE) or "").split()
    return sorted(set(names) | {"tests/test_round_labels_ws_bytes_by_host.py", FIXTURE}), "git diff --name-only BASE, the live derivation"


def base_mentions():
    with open(os.path.join(ROOT, FIXTURE), encoding="utf-8") as f:
        return json.load(f)


def base_mentions_from_git(files):
    """{file: sorted hashes of its mention lines at BASE}, or None when BASE is not in this checkout."""
    if _git("cat-file", "-e", BASE + "^{commit}") is None:
        return None
    out = {}
    for rel in files:
        text = _git("show", "%s:%s" % (BASE, rel))
        out[rel] = sorted(line_hash(l) for _, l in mention_lines(text)) if text is not None else []
    return out


class RoundLabels(unittest.TestCase):
    def test_every_listed_file_exists(self):
        files, how = branch_files()
        missing = [f for f in files if not os.path.isfile(os.path.join(ROOT, f))]
        self.assertEqual(missing, [], "a listed file moved: re-list it (a missing file must not read as clean); the files came from %s" % how)

    def test_the_manifest_is_the_derivation(self):
        files, how = branch_files()
        if how.startswith("git diff"):
            self.assertEqual(sorted(set(files) ^ set(MANIFEST)), [], "MANIFEST differs from the branch's files as git derives them "
                                                                    "(%s): list the new files, with a fixture entry each, or drop the gone ones" % how)
        else:
            self.assertEqual(files, list(MANIFEST), "the derivation was not reachable, so the manifest was read: %s" % how)
        self.assertEqual(sorted(base_mentions()), sorted(MANIFEST), "the fixture carries one entry per manifest file, no more")

    def test_no_branch_line_names_a_round_the_maintainer_did_not_hold_or_names_it_bare(self):
        files, how = branch_files()
        stored = base_mentions()
        bad, read, skipped = [], 0, 0
        for rel in files:
            base = set(stored.get(rel, ()))    # a file the manifest does not know has no base hashes: every mention line is read
            for ln, line in mention_lines(_read(rel)):
                if line_hash(line) in base:
                    skipped += 1      # other work's line, pre-existing at BASE
                    continue
                read += 1
                bad += ["%s:%d: %r (%s)" % (rel, ln, mention, why) for mention, why in offences(line)]
        self.assertGreater(read, 0, "the census read no branch line carrying a mention: the pattern, the files (%s) or the fixture is broken" % how)
        self.assertEqual(bad, [], "a branch line names a round the maintainer did not hold, or names one bare; write the "
                                  "maintainer's round by its number or the author's pass by the label mapping (the module "
                                  "docstring). REVIEWER_ROUNDS is %s; the files came from %s; %d branch lines read, %d pre-existing "
                                  "lines skipped by hash:\n%s" % (sorted(REVIEWER_ROUNDS), how, read, skipped, "\n".join(bad)))

    def test_the_fixture_is_the_merge_bases(self):
        files, how = branch_files()
        stored = base_mentions()
        live = base_mentions_from_git(files)
        if live is not None:
            self.assertEqual(live, {f: stored.get(f, []) for f in files}, "the fixture differs from the mention lines of the listed files at BASE: "
                                                                            "re-derive it with base_mentions_from_git() (a changed BASE, a changed MENTION "
                                                                            "pattern or a re-listed file); the files came from %s" % how)
        else:
            shape = [f for f, hs in stored.items() if not all(re.fullmatch(r"[0-9a-f]{12}", h) for h in hs)]
            self.assertEqual(shape, [], "BASE %s is not in this checkout (a shallow clone has no history), so the fixture was not re-derived "
                                        "in this run and stands as derived on 2026-09-21; its entries must still be 12-hex hashes" % BASE[:9])
            self.assertGreater(sum(len(hs) for hs in stored.values()), 0, "the fixture holds no hash at all")

    def test_the_form_space(self):
        """The classifier over the shapes the branch wrote and the shapes it refuses; the probes are assembled at run time
        because this module is in the manifest and reads itself."""
        R, M = "round", "the maintainer's"
        red = ["%s 6" % R, "review %s 2, 2026-09-18" % R, "the %s-3 find" % R, "since %s 4 of the review" % R, "the author's %s 5 prep" % R,
               "(%s 4, tests-2)" % R, "the clauses the %s asked for" % R, "this %s" % R, "the %s's fixer pass" % R, "%s 5's bounded refusal" % R,
               "%s %s 2" % (M, R), "%s %s 6" % (M, R), "The Maintainer's %s-7 ruling" % R, "the author's pass after %s 4" % R,
               "the reviewer's %s 4" % R, "%s %s 5 and %s 6" % (M, R, R)]
        green = ["%s %s 5" % (M, R), "%s %s-4 ruling" % (M, R), "The maintainer's %s 1 addendum, fresh-2" % R, "%s %s 3, extra8-2; sayDeltaOnce" % (M, R),
                 " *  maintainer's %s 5 on panel-3" % R, "the author's pass 4", "the author's pass-3 fixer pass", "the author's pass-1 verify",
                 "the author's pass after %s %s 5" % (M, R), "%s-trip" % R, "the %s-trip" % R, "the %s trip" % R, "Math.%s(x)" % R,
                 "%ss 1, 3, 4 and 5" % R, "a%s 6" % R, "backg%s 4" % R, "the earlier cut's review, 2026-09-18", "the ground floor",
                 "%s1 as an identifier" % R]
        self.assertEqual([s for s in red if not offences(s)], [], "a refused form read as clean")
        self.assertEqual([s for s in green if offences(s)], [], "an allowed form read as an offence")
        self.assertEqual(len(offences("%s %s 5 and %s 6" % (M, R, R))), 1, "one offence per refused mention, the allowed one beside it not counted")
        self.assertIsNone(MENTION.search("the %s-trip and the %s trip" % (R, R)), "neither spelling of round-trip is a mention")
        self.assertEqual(len(mention_lines("a\n%s 6\nb\nthe %s asked\n" % (R, R))), 2)
        self.assertEqual(offences("%s %s 6" % (M, R), rounds=frozenset({6})), [], "a raised REVIEWER_ROUNDS admits the new round")


if __name__ == "__main__":
    unittest.main()
