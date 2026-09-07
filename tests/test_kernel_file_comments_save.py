#!/usr/bin/env python3
"""The `save` verb's kernel door and its trace (plans/file-review.md, Slice 5; the review of 2026-09-06).

Slice 5's editor Save goes through the comments host as the `save` verb, which writes the file and the
remapped sidecar together. The kernel is the door in front of that host, and four of its rules are
pinned here, all in kernel/kernel.py:

- a save on a NAME _is_text_path refuses is refused `not-text` before the host runs, with the phrase
  saveFile's Save uses, so the two save doors agree on what is a text file the viewer edits (the host's
  own checks are bytes, not names, so `authorized_keys` and `data.sqlite-journal` were written through
  here while the plain Save refused them);
- a save on a file with no .trackchanges/ at or above it is refused `not-tracked` before the host runs:
  the verb has no sidecar to write together with the file there, the panel never routes a save to such a
  file, and the host would have minted a .trackchanges/ holding a log for a file with nothing tracked;
- a save whose `content` is past _TEXT_MAX_BYTES is refused `too-large` before the request is
  serialized or node spawned — the host enforces the same cap, but last, after every byte was piped;
- a save whose decisions rejected N of the session's changes tells the owning session the count and that
  the sidecar changed (_save_trace_body); one that rejected none sends the direct-edit body, as before.

The stub-host worlds are tests/test_file_comments.py's and the real-host world is
tests/test_file_comments_e2e.py's, imported rather than copied. Synthetic only: the notes-api demo
world, a placeholder sid, temp dirs.
"""
import contextlib
import io
import json
import os
import re
import threading

import pytest

from tests import test_file_comments as tfc
from tests import test_file_comments_e2e as e2e
from tests import test_injected_voice as voice
from tests.test_file_comments_e2e import world  # noqa: F401  (the real-host fixture, discovered from this namespace)

km = tfc.km
SID = tfc.SID
CAP = km._TEXT_MAX_BYTES

# The editor's Save request as file-comments.ts builds it (saveArgs): the whole new text, the records as
# the editor's field holds them, and the decisions taken there.
CONTENT = "# Findings\n\nThe api session cut p95 latency by 45%.\n"
RECORD = {"id": "1781100000000-1", "author": "api", "ts": 1781100000000, "kind": "sub",
          "from": 30, "to": 33, "oldText": "40%", "newText": "45%"}
PLAIN = {"content": CONTENT, "suggestions": [RECORD], "accepted": [], "rejected": []}
REJECT_TWO = {"content": "# Findings\n\nThe api session reduced p95 latency by 40%.\n", "suggestions": [],
              "accepted": [],
              "rejected": [{"id": "1781100000000-1", "oldText": "40%", "newText": "45%"},
                           {"id": "1781100000000-2", "oldText": "reduced", "newText": "cut"}]}
FENCE = {"storeMtimeNs": "1781100000000000000", "configMtimeNs": "", "fileMtimeNs": "1"}
HOST_OK = {"fileMtimeNs": "1781100000000000123", "storeMtimeNs": "1781100000000000456", "logged": True,
           "store": {"v": 3, "path": "docs/report.md", "suggestions": [], "comments": []}, "hunks": []}


class _SaveWorld(tfc._TraceWorld):
    """The stub-host trace world with a save helper that takes the PATH: the door's rules are about
    names and trees, so most saves here are not on the harness's report.md."""

    def save(self, path, args=None, fence=None, reply=None):
        rep = {"ok": True, "verb": "save"}
        rep.update(HOST_OK if reply is None else reply)
        self.stub(reply=rep)
        before = set(threading.enumerate())
        r = self.send({"type": "fileComments", "reqId": 21, "sid": SID, "path": path, "verb": "save",
                       "args": PLAIN if args is None else args, "fence": FENCE if fence is None else fence})
        for t in set(threading.enumerate()) - before:
            t.join(20)
        return r

    def write(self, *parts, text="ssh-ed25519 AAAA one\n"):
        p = os.path.join(*parts)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        return p


class TheSaveDoorKeepsSaveFilesNameRule(_SaveWorld):
    """saveFile refuses a name outside _TEXT_EXT / _TEXT_NAMES with "not a text file the viewer edits";
    the save verb now refuses the same names with the same phrase, before node runs, and tells nothing."""

    NAMES = ("authorized_keys", "data.sqlite-journal", "notes")

    def test_names_savefile_refuses_are_refused_before_the_host_runs(self):
        for name in self.NAMES:
            with self.subTest(name=name):
                p = self.write(self.root, "docs", name)
                before = open(p, "rb").read()
                r = self.save(p, args=dict(PLAIN, content="ssh-ed25519 BBBB injected\n", suggestions=[]),
                              fence=dict(FENCE, storeMtimeNs=""))
                self.assertEqual((r["type"], r["code"]), ("fileCommentsFailed", "not-text"))
                self.assertEqual(r["error"], "cannot save %s: not a text file the viewer edits" % km._tilde(os.path.realpath(p)))
                self.assertIsNone(self.seen(), "the host never ran")
                self.assertEqual(open(p, "rb").read(), before, "the file is untouched")
        self.assertEqual(self.traced, [])
        self.assertEqual(self.reached, [], "a refusal wrote nothing, so there is nothing to tell")

    def test_the_two_save_doors_agree_name_by_name(self):
        # the same names through saveFile: refused with the same phrase — one rule, two doors
        for name in self.NAMES:
            p = self.write(self.root, "docs", name)
            r = self.send({"type": "saveFile", "sid": SID, "path": p, "reqId": 22, "baseMtimeNs": str(os.stat(p).st_mtime_ns),
                           "content": "ssh-ed25519 BBBB injected\n"}, wait=False)
            self.assertEqual(r["type"], "fileSaveFailed")
            self.assertIn("not a text file the viewer edits", r["error"])
        # and the names the viewer edits pass the door on both: an extension in _TEXT_EXT, a name in _TEXT_NAMES
        for name in ("report.md", "Makefile"):
            p = self.write(self.root, "docs", name, text="all:\n\ttrue\n")
            r = self.save(p, args=dict(PLAIN, content="all:\n\tfalse\n", suggestions=[]), fence=dict(FENCE, storeMtimeNs=""))
            self.assertEqual(r["type"], "fileCommentsResult", r)
            self.assertEqual(self.seen()["request"]["path"], os.path.realpath(p), "the host ran, on the real path")
            self.assertTrue(km._is_text_path(p))

    def test_the_name_rule_sits_behind_the_consent_and_before_the_node_probe(self):
        # consent first (the Security posture: checked before any content check) — the same order saveFile keeps
        km._set_file_editing(False)
        p = self.write(self.root, "docs", "authorized_keys")
        r = self.save(p, fence=dict(FENCE, storeMtimeNs=""))
        self.assertEqual((r["type"], r["code"]), ("fileCommentsFailed", "editing-off"))
        km._set_file_editing(True)
        # then the name, ahead of the node probe: a machine without node still says which rule refused
        saved = km._file_comments_node
        km._file_comments_node = lambda: None
        try:
            r = self.save(p, fence=dict(FENCE, storeMtimeNs=""))
        finally:
            km._file_comments_node = saved
        self.assertEqual((r["type"], r["code"]), ("fileCommentsFailed", "not-text"))
        # and only the save verb: a status on the same name still reaches the host (the viewer's panel may show it)
        self.stub()
        r = self.send({"type": "fileComments", "reqId": 23, "sid": SID, "path": p, "verb": "status", "args": {}})
        self.assertEqual(r["type"], "fileCommentsResult")


class TheSaveDoorNeedsATrackchangesFolderAbove(_SaveWorld):
    """A save is the editor's Save over a file the panel holds state for — a tracked flag in
    <root>/.trackchanges/config.json or a sidecar beside it. With no .trackchanges/ at or above the
    file there is no such state and nothing to write together with the file, so the kernel refuses
    `not-tracked` before the host runs, and no .trackchanges/ is minted for a log on a file with nothing
    tracked. The plain Save (saveFile) is the door for that file, and still works."""

    def setUp(self):
        super().setUp()
        self.other = os.path.join(self.tmp, "other")
        os.makedirs(os.path.join(self.other, ".git"))              # a landmark the host's findVaultRoot accepts
        self.np = self.write(self.other, "notes.md", text="A note.\n")
        self.assertFalse(km._trackchanges_above(self.np), "the precondition this world is built for")

    def test_a_save_with_no_trackchanges_above_is_refused_before_the_host_and_mints_nothing(self):
        r = self.save(self.np, args=dict(PLAIN, content="A changed note.\n", suggestions=[]), fence=dict(FENCE, storeMtimeNs=""))
        self.assertEqual((r["type"], r["code"]), ("fileCommentsFailed", "not-tracked"))
        self.assertIn("no .trackchanges/ folder at or above it", r["error"])
        self.assertIn(km._tilde(os.path.realpath(self.np)), r["error"])
        self.assertIn("plain Save", r["error"], "the refusal names the door that writes such a file")
        self.assertIsNone(self.seen(), "the host never ran")
        self.assertEqual(open(self.np, encoding="utf-8").read(), "A note.\n")
        self.assertFalse(os.path.exists(os.path.join(self.other, ".trackchanges")), "no directory minted for a log")
        self.assertEqual(self.traced, [])
        self.assertEqual(self.reached, [])

    def test_the_plain_save_is_the_door_for_that_file(self):
        r = self.send({"type": "saveFile", "sid": SID, "path": self.np, "reqId": 24, "baseMtimeNs": str(os.stat(self.np).st_mtime_ns),
                       "content": "A changed note.\n"}, wait=False)
        self.assertEqual((r["type"], r["logged"]), ("fileSaved", False), "written, and nothing to log (log-edit's rule)")
        self.assertEqual(open(self.np, encoding="utf-8").read(), "A changed note.\n")
        self.assertFalse(os.path.exists(os.path.join(self.other, ".trackchanges")))
        self.assertEqual(len(self.traced), 1, "and the direct edit is told, as today")

    def test_a_trackchanges_folder_at_the_root_lets_the_save_through_with_or_without_a_sidecar(self):
        # the harness root holds .trackchanges/: a tracked file with no sidecar yet (storeMtimeNs "") and one with
        # a sidecar both reach the host, which decides the rest (the panel routes both)
        for fence in (dict(FENCE, storeMtimeNs=""), FENCE):
            r = self.save(self.fp, args=dict(PLAIN, suggestions=[]) if fence["storeMtimeNs"] == "" else PLAIN, fence=fence)
            self.assertEqual(r["type"], "fileCommentsResult", r)
            self.assertEqual(self.seen()["request"]["fence"], fence)
        # a .trackchanges/ higher than the file's own root still passes the door: the host is the authority there
        deep = self.write(self.root, "sub", "notes.md", text="deep\n")
        os.makedirs(os.path.join(self.root, "sub", ".git"))
        self.assertTrue(km._trackchanges_above(deep))
        r = self.save(deep, args=dict(PLAIN, content="deeper\n", suggestions=[]), fence=dict(FENCE, storeMtimeNs=""))
        self.assertEqual(r["type"], "fileCommentsResult")


class TheSaveContentIsBoundedBeforeNodeRuns(_SaveWorld):
    """_file_comments_call refuses a save whose content is past the text cap before json.dumps, before
    the spawn, before a byte is piped — the baseline stat guard's twin. The host would refuse the same
    text `too-large`, but only after parsing the whole request, reading the file and scanning the text."""

    def test_content_past_the_cap_is_refused_too_large_without_the_host(self):
        big = "x" * (CAP + 1)
        r = self.save(self.fp, args=dict(PLAIN, content=big))
        self.assertEqual((r["type"], r["code"]), ("fileCommentsFailed", "too-large"))
        self.assertIsNone(self.seen(), "node never ran: nothing serialized, nothing piped")
        self.assertIn(km._tilde(os.path.realpath(self.fp)), r["error"])
        self.assertIn("at least 2.0 MB", r["error"], "the length alone settled it — no encode of the whole text")
        self.assertIn("past the 2.0 MB text cap", r["error"])
        self.assertEqual(self.traced, [])
        self.assertEqual(self.reached, [], "nothing was written, so nothing is told")

    def test_the_bound_is_bytes_not_characters(self):
        # fewer characters than the cap, more bytes: encoded exactly, then refused with the exact size
        two_byte = "é" * (CAP // 2 + 1)
        self.assertLessEqual(len(two_byte), CAP)
        r = self.save(self.fp, args=dict(PLAIN, content=two_byte))
        self.assertEqual((r["type"], r["code"]), ("fileCommentsFailed", "too-large"))
        self.assertNotIn("at least", r["error"])
        self.assertIn("the text is 2.0 MB", r["error"])
        self.assertIsNone(self.seen())

    def test_content_at_the_cap_reaches_the_host(self):
        exact = "y" * CAP
        r = self.save(self.fp, args=dict(PLAIN, content=exact, suggestions=[]))
        self.assertEqual(r["type"], "fileCommentsResult", r)
        self.assertEqual(len(self.seen()["request"]["args"]["content"]), CAP, "the whole text reached node")

    def test_a_lone_surrogate_is_not_this_bounds_business(self):
        # the count must never raise: a lone surrogate is the host's `not-text`, and it gets to say so
        r = self.save(self.fp, args=dict(PLAIN, content="\ud800 alone", suggestions=[]),
                      reply={"ok": False, "code": "not-text", "error": "cannot save ~/notes-api/docs/report.md: a lone surrogate"})
        self.assertEqual((r["type"], r["code"]), ("fileCommentsFailed", "not-text"))
        self.assertIsNotNone(self.seen(), "the host ran and refused")

    def test_the_call_itself_refuses_and_other_verbs_and_shapes_are_untouched(self):
        # the unit under the wire: no reply, the kernel's own code, and no subprocess
        spawned = []
        saved = km._run_bounded
        km._run_bounded = lambda *a, **k: spawned.append(a) or (0, b'{"ok":true}', b"", False)
        try:
            out, err = km._file_comments_call(self.fp, "save", {"content": "z" * (CAP + 1)}, FENCE)
            self.assertIsNone(out)
            self.assertEqual(err[0], "too-large")
            self.assertEqual(spawned, [])
            # a comment's note is not `content`; a save whose content is not a string is the host's BadRequest
            km._file_comments_call(self.fp, "comment", {"note": "n" * (CAP + 1)}, FENCE)
            km._file_comments_call(self.fp, "save", {"content": ["not", "a", "string"]}, FENCE)
            self.assertEqual(len(spawned), 2)
        finally:
            km._run_bounded = saved


class TheSaveTraceNamesTheRejectedCount(_SaveWorld):
    """Consent, trace, routing: a verb that changes the file's bytes tells the owning session what
    changed. A save that rejected none of the session's changes is a direct edit and keeps
    _edit_trace_body (pinned by tests/test_file_comments.py's SaveTellsTheSession); a save whose decisions
    rejected N of them says so, in _save_trace_body — the count the panel's Reject would have said,
    without which the session could not tell a rejection from an overwrite."""

    def test_a_save_that_rejected_two_changes_says_so_once_after_the_reply(self):
        r = self.save(self.fp, args=REJECT_TWO)
        self.assertEqual(r["type"], "fileCommentsResult")
        real = os.path.realpath(self.fp)
        self.assertEqual([sid for sid, _ in self.reached], [SID], "exactly one send, to the owning session")
        body = self.reached[0][1]
        self.assertEqual(body, km._save_trace_body(real, 2))
        self.assertIn("rejected 2 of your tracked changes", body)
        self.assertIn("the file and its sidecar both changed", body)
        self.assertIn("I just edited `%s` directly on disk" % km._tilde(real), body)
        self.assertIn("re-read it before writing", body)
        self.assertIn("romp-injected", body, "the trace renders as an injected (gray) message")
        self.assertEqual(self.traced, [], "not the plain direct-edit trace")
        self.assertEqual(self.reject_traced, [], "and not the panel Reject's trace either: the person edited too")
        self.assertEqual(self.order, ["reply", "trace"], "the fileCommentsResult is on the wire before the trace goes")
        self.assertEqual(self.parked, [], "straight to the backend, never through the todo-reply helper")

    def test_the_count_is_the_decisions_length_one_included(self):
        one = dict(REJECT_TWO, rejected=REJECT_TWO["rejected"][:1])
        self.save(self.fp, args=one)
        self.assertEqual(self.reached[0][1], km._save_trace_body(os.path.realpath(self.fp), 1))
        self.assertIn("rejected 1 of your tracked changes", self.reached[0][1])

    def test_a_save_that_rejected_nothing_keeps_the_direct_edit_body(self):
        real = os.path.realpath(self.fp)
        self.save(self.fp, args=PLAIN)                                          # no decisions
        self.save(self.fp, args=dict(PLAIN, accepted=[{"id": "1781100000000-2", "oldText": "reduced", "newText": "cut"}]))
        self.assertEqual(self.traced, [(real, SID), (real, SID)], "both through _edit_trace")
        self.assertEqual([b for _, b in self.reached], [km._edit_trace_body(real)] * 2,
                         "an accept in the editor is sidecar-only news, as the panel's Accept is: the Send carries it")

    def test_a_refused_save_with_decisions_tells_nothing(self):
        for code in ("store-moved", "file-moved", "desync", "too-large", "not-text"):
            r = self.save(self.fp, args=REJECT_TWO, reply={"ok": False, "code": code, "error": "cannot save: " + code})
            self.assertEqual((r["type"], r["code"]), ("fileCommentsFailed", code))
        self.stub(exit=2, stderr="file-comments-host: BadRequest: change 1781100000000-1 is decided twice")
        r = self.send({"type": "fileComments", "reqId": 25, "sid": SID, "path": self.fp, "verb": "save",
                       "args": REJECT_TWO, "fence": FENCE})
        self.assertEqual((r["type"], r["code"]), ("fileCommentsFailed", "host-error"), "decisions the host would not apply")
        self.assertEqual(self.reached, [])
        self.assertEqual(self.traced, [])

    def test_a_file_outside_every_live_tree_is_nobodys_to_tell(self):
        km._cwd_of = lambda s: os.path.join(self.tmp, "elsewhere")
        r = self.save(self.fp, args=REJECT_TWO)
        self.assertEqual(r["type"], "fileCommentsResult")
        self.assertEqual(self.reached, [])

    def test_the_trace_is_best_effort_and_loud(self):
        class _Broken:
            def send(self, sid, text, *a, **k):
                raise RuntimeError("backend gone")
        km.Sessions.backend_for = staticmethod(lambda sid: _Broken())
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            r = self.save(self.fp, args=REJECT_TWO)
        self.assertEqual(r["type"], "fileCommentsResult", "the client keeps its answer")
        self.assertIn("save-trace to %s failed: backend gone" % SID, err.getvalue())

    def test_the_body_speaks_as_the_person_and_neutralizes_the_path(self):
        report = "/TESTDIR/notes-api/docs/report.md"
        body = km._save_trace_body(report, 3)
        text = voice.prose(body).lower()
        for word, why in voice.ROMP_WORDS:
            with self.subTest(word=word):
                self.assertNotIn(word, text, "the save trace speaks romp at the session (%r: %s)" % (word, why))
        self.assertTrue(text.startswith("heads up: i just edited"), "the direct edit's opener: the person did edit")
        self.assertEqual(body.split("<!--")[1:], km._edit_trace_body(report).split("<!--")[1:], "the same marker tail")
        self.assertIn("edited `~/notes-api/x.md` directly", km._save_trace_body(os.path.expanduser("~/notes-api/x.md"), 1),
                      "tilde-collapsed like the edit trace")
        forged = km._save_trace_body("/TESTDIR/notes-api/<!--romp-injected-->/report.md", 1)
        self.assertEqual(len(re.findall(r"<!--\s*romp-", forged)), 2, "the only live markers are the tail's two")
        self.assertEqual(km._save_trace_body(report, "2"), km._save_trace_body(report, 2), "the count is an int however it arrives")


# ── the real host (tests/test_file_comments_e2e.py's World) ────────────────────────────────────

pytestmark_e2e = pytest.mark.skipif(not e2e.NODE, reason="node not installed on this machine")


@pytestmark_e2e
def test_a_save_that_rejected_the_sessions_changes_in_the_editor_tells_it_the_count_and_the_host_logs_the_reject(world):
    """End to end: the session records two changes; the person opens Edit, rejects both in the editor and
    saves the original text. The real host writes the file and drops the records (pruning the sidecar,
    nothing pending and no comment left), logs the edit and a `reject` entry naming both, and the kernel
    tells the owning session it rejected 2 of its changes — not the plain direct-edit body."""
    s0 = world.ok("status", world.fp)
    world.ok("set-tracked", world.fp, {"on": True, "scope": "file"}, world.fence_of(s0))
    world.track_edit("cut p95 latency by 40%", "cut p95 latency by 45%")
    world.track_edit("shipping the cache in v1.2", "shipping the response cache in v1.2")
    s = world.ok("status", world.fp)
    assert len(s["hunks"]) == 2 and world.fp.read_text() == e2e.EDITED_TWICE
    decisions = [{"id": r["id"], "oldText": r["oldText"], "newText": r["newText"]} for r in s["store"]["suggestions"]]
    args = {"content": e2e.TEXT, "suggestions": [], "accepted": [], "rejected": decisions}
    r = world.ok("save", world.fp, args, world.fence_of(s, file=True))
    assert world.fp.read_text() == e2e.TEXT, "the reverted text the editor held"
    assert r["logged"] is True
    assert r["storeMtimeNs"] is None and r["store"] is None, "nothing pending and no comment: the sidecar is pruned"
    real = os.path.realpath(str(world.fp))
    assert world.traced == [(SID, e2e.km._save_trace_body(real, 2))]
    assert "rejected 2 of your tracked changes" in world.traced[0][1]
    assert world.traced[0][1] != e2e.km._edit_trace_body(real)
    assert world.order[-2:] == ["reply", "trace"], "the fileCommentsResult is on the wire before the trace goes"
    assert world.injected == [], "a trace is a direct backend send: nothing parked, no todo stamped"
    entries = world.log_lines(s)
    assert [e["kind"] for e in entries] == ["set-tracked", "edit", "reject"]
    assert sorted(c["id"] for c in entries[2]["changes"]) == sorted(d["id"] for d in decisions), "the host's reject entry is the decisions"
    assert s["unsent"]["rejected"] == 0
    s2 = world.ok("status", world.fp)
    assert s2["unsent"]["rejected"] == 2, "and the next Send to session will count them"


@pytestmark_e2e
def test_a_save_on_a_project_with_no_trackchanges_folder_is_refused_at_the_kernel_and_mints_none(world):
    """The finding's scenario through the real dispatcher: a .git project, nothing tracked, no
    .trackchanges/. saveFile refuses `authorized_keys` by name; the save verb now refuses it the same way,
    refuses a text file with `not-tracked`, and neither run mints a .trackchanges/ or reaches the host."""
    keys = world.root / "authorized_keys"
    keys.write_text("ssh-ed25519 AAAA one\n")
    assert not (world.root / ".trackchanges").exists()
    args = {"content": "ssh-ed25519 BBBB injected\n", "suggestions": [], "accepted": [], "rejected": []}
    fence = {"storeMtimeNs": "", "configMtimeNs": "", "fileMtimeNs": str(keys.stat().st_mtime_ns)}
    r = world.op("save", keys, args, fence)
    assert (r["type"], r["code"]) == ("fileCommentsFailed", "not-text")
    assert keys.read_text() == "ssh-ed25519 AAAA one\n"
    rep = world.ws({"type": "saveFile", "sid": SID, "path": str(keys), "baseMtimeNs": fence["fileMtimeNs"], "content": args["content"]}, wait=False)
    assert rep["type"] == "fileSaveFailed" and "not a text file the viewer edits" in rep["error"]
    r = world.op("save", world.other, dict(args, content="# Other, edited\n"),
                 dict(fence, fileMtimeNs=str(world.other.stat().st_mtime_ns)))
    assert (r["type"], r["code"]) == ("fileCommentsFailed", "not-tracked")
    assert world.other.read_text() == "# Other\n"
    assert not (world.root / ".trackchanges").exists(), "no directory minted for a log on a file with nothing tracked"
    assert world.traced == []
