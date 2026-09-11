#!/usr/bin/env python3
"""The guide's commenting paragraph says what a person does about a comment whose copy the panel can only
guess (the recurring-passage tie-break, 2026-09-11, decision 51): saving the comment again from the right
copy, as the card asks, adds a NEW card on that copy with no tag, and the old card keeps its tag until the
person resolves it.

The slice first wrote that saving again "confirms it", which reads as a confirmation of the same comment.
The product has no such gesture: the host's `comment` verb always mints a new comment, `retarget` takes a
region, and a reply, a resolve or a file save leaves a tie's stale position where it is, so the tagged card
never becomes confirmed (review of the tie-break, 2026-09-11). This module pins the sentence as it now
reads and proves it against the real host as a child process, the tools/file-comments-host-tiebreak.test.mjs
way: a comment on the second of three tied copies, a raw write that leaves the host a guess, then the
person's second comment from the right copy, which lands on it by position with fields naming it and no
`placed` verdict, while the first comment's verdict stays a guess through a reply and until the person
resolves it. The card's words the guide defers to ("as the card asks") are looked up in the panel.

Skipped when node is missing. Synthetic: the notes-api demo world under a scratch directory, invented text.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
HOST = os.path.join(ROOT, "tools", "file-comments-host.mjs")
ENGINE = os.path.join(ROOT, "vendor", "track-changents", "engine.js")
NODE = shutil.which("node")

# The tie-break host test's world: one paragraph over a thousand characters long, three times, each under its own
# heading. The marker phrase in its middle has identical surroundings for more than the host's cap on both sides
# of every copy, so every anchor on it ties at the cap and only the position, the ordinal or the heading above
# tells the copies apart.
PARA = ("The quick brown fox jumps over the lazy dog. " * 12
        + "Here is the marker phrase to comment on. "
        + "Pack my box with five dozen liquor jugs. " * 12).strip()
MARKER = "the marker phrase"
OPENING = "# Report\n\nA short opening line that occurs once.\n\n"
TIED = "%s## First pass\n\n%s\n\n## Second pass\n\n%s\n\n## Third pass\n\n%s\n" % (OPENING, PARA, PARA, PARA)
# Scenario (c) of the host test: a short line above and a second copy under the SAME heading. The count of copies
# changed and two copies lie under the stored heading path, so the host falls back to the copy nearest the stale
# position, a guess: the state the guide's sentence is about.
TWIN = (OPENING + "One short line above.\n\n"
        + TIED[len(OPENING):TIED.index("## Third pass")] + PARA + "\n\n" + TIED[TIED.index("## Third pass"):])


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _flat(text):
    """Collapse hard wraps so an assertion survives a rewrap."""
    return re.sub(r"\s+", " ", text).strip()


def _nth(text, quote, n):
    i = -1
    for _ in range(n + 1):
        i = text.index(quote, i + 1)
    return i


class GuideConfirmSentence(unittest.TestCase):
    def test_the_guide_says_saving_again_adds_a_new_card_and_the_old_one_keeps_its_tag(self):
        guide = _flat(_read("docs", "guide.md"))
        self.assertIn("When none of those can tell which copy the comment meant, its highlight is dashed and the card "
                      "carries a **passage recurs** tag: the copy shown is a guess, and the card says so. Saving the "
                      "comment again from the right copy, as the card asks, adds a new card on that copy with no tag; "
                      "the old card keeps its tag, so resolve it once the new one is saved.", guide)
        # the earlier wording promised a confirmation of the same comment, which no verb performs
        self.assertNotIn("saving it again from the right copy confirms it", guide)
        # "as the card asks": the card's words for a guessed copy do ask for that
        panel = _read("ui", "webview", "file-comments.ts")
        m = re.search(r"function copyUnsureWords\(.*?\n\}", panel, re.S)
        self.assertIsNotNone(m, "the card's words for a guessed copy")
        self.assertIn("save again from the right copy", m.group(0))


@unittest.skipUnless(NODE, "node not installed on this machine")
class TheHostKeepsThePromise(unittest.TestCase):
    """The guide's sentence, walked on the real host: the second comment is a new one on the right copy, placed by its
    position with no verdict to paint, and the first stays a guess until resolved."""

    def setUp(self):
        self.scratch = tempfile.mkdtemp(prefix="romp-guide-confirm-")
        self.home = os.path.join(self.scratch, "home")
        root = os.path.join(self.home, "notes-api")
        os.makedirs(os.path.join(root, ".git"))
        os.makedirs(os.path.join(root, "docs"))
        self.file = os.path.join(root, "docs", "tied.md")
        with open(self.file, "w", encoding="utf-8") as f:
            f.write(TIED)

    def tearDown(self):
        shutil.rmtree(self.scratch, ignore_errors=True)

    def _env(self):
        env = dict(os.environ)
        env.pop("TRACKCHANGES_ROOT", None)
        env.pop("ROMP_SID", None)
        env.pop("ROMP_SESSION_NAME", None)
        env["FILE_COMMENTS_HOME"] = self.home
        return env

    def _host(self, req):
        r = subprocess.run([NODE, HOST], input=json.dumps(req), capture_output=True, text=True, timeout=30,
                           env=self._env())
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertTrue(out.get("ok"), r.stdout)
        return out

    def _status(self):
        return self._host({"verb": "status", "path": self.file, "args": {}})

    def _fence(self):
        st = self._status()
        ns = st.get("storeMtimeNs")
        return {"storeMtimeNs": "" if ns is None else ns}

    def _write(self, verb, args):
        return self._host({"verb": verb, "path": self.file, "args": args, "fence": self._fence()})

    def _anchor(self, text, at):
        """The engine's own anchor for the marker at `at`, what the browser's anchor-map builds when the person
        selects that copy."""
        src = ("const fs = (await import('fs')).default; const m = await import(process.argv[1]); const e = m.default || m;"
               " const [t, a, b] = JSON.parse(fs.readFileSync(0, 'utf8')); console.log(JSON.stringify(e.makeAnchor(t, a, b)));")
        r = subprocess.run([NODE, "--input-type=module", "-e", src, "--", Path(ENGINE).as_uri()],
                           input=json.dumps([text, at, at + len(MARKER)]), capture_output=True, text=True, timeout=30,
                           env=self._env())
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def _sidecar(self, path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def test_saving_again_from_the_right_copy_adds_a_new_card_and_the_old_one_stays_a_guess_until_resolved(self):
        # the comment, on the second of three tied copies
        first_at = _nth(TIED, MARKER, 1)
        r = self._write("comment", {"anchor": self._anchor(TIED, first_at), "note": "Say it once.", "hintOffset": first_at})
        store_path = r["storePath"]
        old = self._sidecar(store_path)["comments"][0]
        self.assertEqual([old["ordinal"], old["copies"], old["section"]], [2, 3, "Report > Second pass"])
        # a raw write nobody recorded: the position names no copy, the count changed, and two copies lie under the
        # stored heading, so the host's verdict is the nearest copy, a guess (the dashed highlight and the tag)
        with open(self.file, "w", encoding="utf-8") as f:
            f.write(TWIN)
        right_at = _nth(TWIN, MARKER, 1)
        guess = {"at": right_at, "confirmed": False, "by": "nearest"}
        self.assertEqual(self._status()["placed"], {old["id"]: guess})
        # "Saving the comment again from the right copy ... adds a new card on that copy with no tag": a second
        # comment, from the copy the person meant
        r2 = self._write("comment", {"anchor": self._anchor(TWIN, right_at), "note": "Say it once.", "hintOffset": right_at})
        comments = self._sidecar(store_path)["comments"]
        self.assertEqual(len(comments), 2, "a new comment, not the old one moved")
        kept, new = comments
        self.assertEqual(kept["id"], old["id"])
        self.assertNotEqual(new["id"], old["id"])
        self.assertEqual([kept["anchorAt"], kept["ordinal"], kept["copies"], kept["section"]],
                         [old["anchorAt"], 2, 3, "Report > Second pass"], "the old comment's record stands")
        self.assertEqual(new["anchorAt"], right_at, "the new comment's position names the copy it was saved from")
        self.assertTrue(TWIN.startswith(MARKER, new["anchorAt"]))
        self.assertEqual([new["ordinal"], new["copies"], new["section"]], [2, 4, "Report > Second pass"])
        placed = r2["placed"]
        self.assertNotIn(new["id"], placed, "no verdict to paint: the position places it, plainly")
        # "the old card keeps its tag": the verdict on the old comment is the same guess, on this reply and after one
        # more write the person can make on the card
        self.assertEqual(placed[old["id"]], guess)
        r3 = self._write("reply", {"commentId": old["id"], "note": "Which copy?"})
        self.assertEqual(r3["placed"], {old["id"]: guess})
        # "so resolve it once the new one is saved"
        r4 = self._write("resolve", {"commentId": old["id"], "on": True})
        by_id = {c["id"]: c for c in self._sidecar(store_path)["comments"]}
        self.assertTrue(by_id[old["id"]]["resolved"])
        self.assertFalse(by_id[new["id"]]["resolved"])
        self.assertNotIn(new["id"], r4["placed"], "the new card still paints plainly")


if __name__ == "__main__":
    unittest.main()
