#!/usr/bin/env python3
"""Tracking and comments key on the REAL file, not the spelling the viewer opened it under (the review
of plans/file-review.md Slice 1, 2026-09-06).

Everything that decides a file's project root is textual: the vendored store layer's findVaultRoot and
storePathFor walk the path string they are handed, and so do the guard and the CLIs on the path Claude
Code hands them — the session's own spelling, under its cwd. The kernel used to hand the host script
os.path.normpath of the spelled path. So with a vault (`.obsidian/`) holding a directory symlink
`proj -> /repo/docs`, where /repo has `.git`: the viewer opens vault/proj/x.md (the Files pane follows
directory links), the person turns Track changes on, and the host writes vault/.trackchanges/config.json.
The session works in /repo and Writes /repo/docs/x.md; the guard resolves /repo, finds no config there,
and lets the raw write land while the panel shows the file as tracked. A status on the real path answers
trackedBy null, and a comment made on one spelling is invisible from the other.

The fix is one helper, _file_comments_path, that resolves and REALPATHS the path for the fileComments
op, the fileCommentsSend op and the edit log — the same realpath _save_file already writes through, so
a direct edit is now logged in the .trackchanges/ the sidecar lives in. These tests drive the helper,
the two ops and the edit log through a symlinked spelling against a stub host that records the path it
was handed, and once against the REAL host script and the vendored store layer, where the toggle must
land in the real root and a status on the real path must see it. Synthetic paths in a temp dir only
(the notes-api demo world, TESTHOST's placeholder sid)."""
import json
import os
import shutil
import tempfile
import unittest
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
HOST = os.path.join(ROOT, "tools", "file-comments-host.mjs")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_filecomments_realpath", os.path.join(BIN, "romp-kernel"))
jd = km.jd

SID = "11111111-2222-3333-4444-555555555555"
NODE = shutil.which("node")

# A stub host: records the request it read from stdin, answers ok. ESM like the real script.
_STUB = """import fs from 'node:fs';
let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (d) => { raw += d; });
process.stdin.on('end', () => {
  fs.writeFileSync(%s, raw);
  process.stdout.write(JSON.stringify({ ok: true, verb: JSON.parse(raw).verb, logged: true }));
});
"""


@unittest.skipUnless(NODE, "node not installed on this machine")
class _LinkedWorld(unittest.TestCase):
    """vault/.obsidian and vault/proj -> repo/docs, where repo/.git and repo/docs/x.md exist. `link` is
    the spelling the viewer opened; `real` is the file. The consent is on and the kernel is pointed at
    the stub host unless a test asks for the real one."""

    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp())
        self.vault = os.path.join(self.tmp, "vault")
        self.repo = os.path.join(self.tmp, "repo")
        os.makedirs(os.path.join(self.vault, ".obsidian"))
        os.makedirs(os.path.join(self.repo, ".git"))
        os.makedirs(os.path.join(self.repo, "docs"))
        self.real = os.path.join(self.repo, "docs", "x.md")
        with open(self.real, "w") as f:
            f.write("# Findings\n\nThe api session cut p95 latency by 40%.\n")
        os.symlink(os.path.join(self.repo, "docs"), os.path.join(self.vault, "proj"))
        self.link = os.path.join(self.vault, "proj", "x.md")
        self.seen_path = os.path.join(self.tmp, "seen.json")
        self.stub_path = os.path.join(self.tmp, "stub-host.mjs")
        with open(self.stub_path, "w") as f:
            f.write(_STUB % json.dumps(self.seen_path))
        self._saved = (km._FILE_COMMENTS_HOST, km._cwd_of)
        km._FILE_COMMENTS_HOST = Path(self.stub_path)
        km._set_file_editing(True)

    def tearDown(self):
        km._FILE_COMMENTS_HOST, km._cwd_of = self._saved
        km._set_file_editing(False)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def seen(self):
        """The request the stub host was handed, or None when it never ran."""
        try:
            with open(self.seen_path) as f:
                return json.load(f)
        except OSError:
            return None


class TheHelper(_LinkedWorld):
    def test_a_symlinked_spelling_becomes_the_real_file(self):
        self.assertEqual(km._file_comments_path(self.link, None), self.real)
        self.assertEqual(km._file_comments_path(self.real, None), self.real, "a real path is left as it is")

    def test_a_relative_spelling_resolves_against_the_sessions_cwd_then_the_link(self):
        km._cwd_of = lambda sid: self.vault if sid == SID else None
        self.assertEqual(km._file_comments_path("proj/x.md", SID), self.real)

    def test_nothing_absolute_is_empty(self):
        km._cwd_of = lambda sid: None
        self.assertEqual(km._file_comments_path("proj/x.md", SID), "", "no cwd: the path cannot become absolute")
        self.assertEqual(km._file_comments_path("", None), "")
        self.assertEqual(km._file_comments_path(None, None), "")
        self.assertEqual(km._file_comments_path({"bad": True}, None), "")

    def test_a_file_that_does_not_exist_yet_still_resolves_through_the_link(self):
        # folder tracking is turned on before a file exists (plans/file-review.md, set-tracked folder)
        self.assertEqual(km._file_comments_path(os.path.join(self.vault, "proj", "new.md"), None),
                         os.path.join(self.repo, "docs", "new.md"))


class TheDiskOpThroughTheLink(_LinkedWorld):
    def op(self, verb, **args):
        msg = {"type": "fileComments", "reqId": 7, "sid": SID, "path": self.link, "verb": verb}
        if args:
            msg["args"] = args
        return km._file_comments_op(msg)

    def test_status_asks_the_host_about_the_real_file(self):
        rep = self.op("status")
        self.assertEqual(rep["type"], "fileCommentsResult", rep)
        self.assertEqual(self.seen()["path"], self.real, "the host resolves the root from the path it is handed")

    def test_set_tracked_asks_the_host_about_the_real_file(self):
        rep = self.op("set-tracked", on=True, scope="file")
        self.assertEqual(rep["type"], "fileCommentsResult", rep)
        self.assertEqual(self.seen()["path"], self.real,
                         "config.json must land in the root the guard resolves for the session's own Write")

    def test_comment_asks_the_host_about_the_real_file(self):
        rep = self.op("comment", note="Tighten this paragraph.")
        self.assertEqual(rep["type"], "fileCommentsResult", rep)
        self.assertEqual(self.seen()["path"], self.real, "a comment made on one spelling is seen from the other")

    def test_a_refusal_before_the_host_still_names_a_path(self):
        km._cwd_of = lambda sid: None
        rep = km._file_comments_op({"type": "fileComments", "reqId": 8, "sid": SID, "path": "proj/x.md",
                                    "verb": "status"})
        self.assertEqual((rep["type"], rep["code"]), ("fileCommentsFailed", "unreadable"))
        self.assertIn("proj/x.md", rep["error"])
        self.assertIsNone(self.seen())


class TheEditLogThroughTheLink(_LinkedWorld):
    def test_the_edit_is_judged_and_logged_on_the_real_tree(self):
        os.makedirs(os.path.join(self.repo, ".trackchanges"))
        self.assertEqual(km._edit_log_before(self.link, None), {"path": self.real},
                         "the entry lands in the .trackchanges/ the sidecar lives in — where _save_file wrote")

    def test_a_trackchanges_beside_the_link_is_not_this_files(self):
        # the vault's own store (the Obsidian host's) is above the LINK, not above the real file: nothing
        # of this file can live there, so nothing is logged — the real tree is the one that counts
        os.makedirs(os.path.join(self.vault, ".trackchanges"))
        self.assertIsNone(km._edit_log_before(self.link, None))

    def test_a_save_through_the_link_logs_the_real_path(self):
        os.makedirs(os.path.join(self.repo, ".trackchanges"))
        ns = os.stat(self.link).st_mtime_ns
        pre = km._edit_log_before(self.link, None)
        prior = {}
        mt, err = km._save_file(self.link, None, "# Findings\n\nThe api session cut p95 latency by 45%.\n",
                                str(ns), prior=prior)
        self.assertIsNone(err)
        logged, warn = km._edit_log_after(pre, prior, "# Findings\n\nThe api session cut p95 latency by 45%.\n", mt)
        self.assertTrue(logged)
        self.assertIsNone(warn)
        req = self.seen()
        self.assertEqual((req["verb"], req["path"]), ("log-edit", self.real))
        self.assertTrue(os.path.islink(os.path.join(self.vault, "proj")), "the link itself is untouched")


class TheSendThroughTheLink(_LinkedWorld):
    """The message names the real file, so the session's command lines find the store; the log-send
    entry goes to the real root. The delivery is scripted the way tests/test_file_comments.py's send
    world scripts it: a known session `web` on the tmux backend, _send_or_park recording the body."""

    def setUp(self):
        super().setUp()
        self._saved2 = (km._name_of, km._sdk, km._send_or_park)
        km._name_of = lambda sid: "web" if sid == SID else None
        km._sdk = lambda: None
        self.injected = []

        def fake_send_or_park(be, sid, text, echo=None, user_todo=None):
            self.injected.append({"sid": sid, "text": text, "user_todo": user_todo})
            return True
        km._send_or_park = fake_send_or_park

    def tearDown(self):
        km._name_of, km._sdk, km._send_or_park = self._saved2
        super().tearDown()

    def test_the_message_and_the_log_entry_name_the_real_file(self):
        rep = km._file_comments_send_op({"type": "fileCommentsSend", "reqId": 9, "sid": SID, "path": self.link,
                                         "tracked": True, "accepted": 0, "rejected": 0, "watermark": None,
                                         "comments": [{"id": "1757145600000-0", "desc": "on this file",
                                                       "body": "Tighten the summary."}]})
        self.assertEqual(rep["type"], "fileCommentsSent", rep)
        self.assertNotIn("logWarning", rep)
        body = self.injected[0]["text"]
        self.assertIn("I left 1 comment on %s." % self.real, body)
        self.assertIn("--file %s --thread" % self.real, body, "track-reply resolves the store from --file")
        self.assertNotIn(self.link, body, "the spelling never reaches the session")
        req = self.seen()
        self.assertEqual((req["verb"], req["path"]), ("log-send", self.real))
        self.assertEqual(req["args"]["sessionName"], "web")


class WithTheRealHost(_LinkedWorld):
    """The finding's scenario against the real host script and the vendored store layer: a toggle through
    the link lands in the REPO's .trackchanges/, never the vault's, and a status on the real path — the
    spelling the guard judges the session's Write under — sees the file as tracked."""

    def setUp(self):
        super().setUp()
        km._FILE_COMMENTS_HOST = Path(HOST)

    def op(self, path, verb, args=None, fence=None):
        msg = {"type": "fileComments", "reqId": 10, "sid": SID, "path": path, "verb": verb}
        if args is not None:
            msg["args"] = args
        if fence is not None:
            msg["fence"] = fence
        rep = km._file_comments_op(msg)
        self.assertEqual(rep["type"], "fileCommentsResult", rep)
        return rep

    def test_the_toggle_through_the_link_lands_in_the_real_root(self):
        before = self.op(self.real, "status")
        self.assertIsNone(before["trackedBy"])
        on = self.op(self.link, "set-tracked", {"on": True, "scope": "file"},
                     {"storeMtimeNs": "", "configMtimeNs": ""})
        self.assertEqual(on["root"], self.repo)
        self.assertEqual(on["trackedBy"], {"kind": "file", "entry": "docs/x.md"})
        self.assertTrue(os.path.isfile(os.path.join(self.repo, ".trackchanges", "config.json")))
        self.assertFalse(os.path.exists(os.path.join(self.vault, ".trackchanges")),
                         "nothing under the link's root: the guard would never look there")
        after = self.op(self.real, "status")
        self.assertEqual(after["trackedBy"], {"kind": "file", "entry": "docs/x.md"},
                         "the real path — the session's spelling — sees the same verdict")
        via_link = self.op(self.link, "status")
        self.assertEqual(via_link["trackedBy"], after["trackedBy"], "both spellings agree")


if __name__ == "__main__":
    unittest.main()
