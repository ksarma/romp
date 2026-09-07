#!/usr/bin/env python3
"""The bound on ONE serialized request to the comments host (plans/file-review.md, Slice 5; the review of
2026-09-06, round 2), in kernel/kernel.py's _file_comments_call.

Round 1 bounded a save's `content` before the request is serialized. Its three record arrays —
`suggestions`, `accepted`, `rejected` — and every other verb's arguments (a comment's note, a reply's
turn) had no kernel-side bound short of the frame reader's 80 MB: a save carrying a million fake decision
entries (43 MB) was json.dumps'ed, piped to node, parsed and walked entry by entry at half a gigabyte, and
refused only by the host's own reply estimate after all of that, on the kernel that self-hosts the
sessions. Now the serialized request is measured once (json.dumps with ensure_ascii, so the string's
length is the byte count _run_bounded would pipe) and refused `too-large` past _FILE_COMMENTS_REPLY_MAX
before the spawn. The reply cap is the right number: what a request puts on disk comes back in the reply
(the sidecar as `store` and again as `hunks`, the decisions in the log's newest rows), so a request past it
asks for an answer the host refuses anyway (its checkReplyFits); the kernel's refusal is that verdict,
taken before the pipe.

Pinned here: each of the three arrays trips the bound alone; the boundary is the serialized request's
byte count, one byte over refuses and at the cap the request reaches the host; the measure is bytes on
the wire, not characters; every verb is bounded and the 2 MB text cap is not this bound; the finding's
own probe never spawns node, through the stub host and through the real one, with the disk untouched.
The stub-host world is tests/test_kernel_file_comments_save.py's and the real-host world is
tests/test_file_comments_e2e.py's, imported rather than copied. Synthetic only: the notes-api demo
world, a placeholder sid, temp dirs, invented decision ids.
"""
import json
import os
from pathlib import Path

import pytest

from tests import test_file_comments_e2e as e2e
from tests import test_kernel_file_comments_save as tks
from tests.test_file_comments_e2e import world  # noqa: F401  (the real-host fixture, discovered from this namespace)

km = tks.km
SID = tks.SID
PLAIN, FENCE = tks.PLAIN, tks.FENCE
REAL_CAP = km._FILE_COMMENTS_REPLY_MAX
# The finding's probe, scaled: ~41 bytes an entry serialized, so this many stand past the real 16 MB cap
# in about 17 MB — the same shape as the million-entry frame, at a size a test builds in a fraction of a second.
PROBE_ENTRIES = 420_000


def decisions(n, prefix="k"):
    """`n` decision entries in the decisions' shape, ids invented — the finding's probe."""
    return [{"id": "%s%d" % (prefix, i), "oldText": "", "newText": ""} for i in range(n)]


def request_bytes(path, verb, args, fence):
    """The bytes _file_comments_call pipes for this request: the same json.dumps of the same shape."""
    return len(json.dumps({"verb": verb, "path": path, "args": args, "fence": fence}))


class _NoSpawn:
    """_run_bounded swapped for a recorder: the argv and the payload of every spawn the kernel attempts,
    each answered ok. A test about the bound asserts the list stayed empty."""

    def __init__(self):
        self.calls = []

    def __call__(self, argv, stdin_text, *a, **k):
        self.calls.append((argv, stdin_text))
        return 0, b'{"ok":true}', b"", False


class _BoundWorld(tks._SaveWorld):
    """The save world with the reply cap lowered to 64 KB: the bound reads the module global at call time,
    and the stub's reply sits far under 64 KB (the same global is _run_bounded's stdout cap), so the
    boundary can be walked byte by byte without building 16 MB requests."""
    SMALL = 64 * 1024

    def setUp(self):
        super().setUp()
        km._FILE_COMMENTS_REPLY_MAX = self.SMALL
        self.real = os.path.realpath(self.fp)

    def tearDown(self):
        km._FILE_COMMENTS_REPLY_MAX = REAL_CAP
        super().tearDown()

    def sized(self, args, target):
        """`args` with its last `rejected` entry's newText padded (plain ASCII: one byte a character in
        JSON) so the SERIALIZED request comes to exactly `target` bytes, as the kernel measures it."""
        args = json.loads(json.dumps(args))
        args["rejected"][-1]["newText"] = ""
        pad = target - request_bytes(self.real, "save", args, FENCE)
        self.assertGreaterEqual(pad, 0, "the unpadded request must fit under the target")
        args["rejected"][-1]["newText"] = "p" * pad
        self.assertEqual(request_bytes(self.real, "save", args, FENCE), target)
        return args

    def assert_refused_at_the_kernel(self, r, size=None, lead="cannot save %s: the text, change records and decisions come to"):
        self.assertEqual((r["type"], r["code"]), ("fileCommentsFailed", "too-large"), r)
        self.assertIsNone(self.seen(), "node never ran: nothing piped, nothing parsed")
        self.assertIn(lead % km._tilde(self.real), r["error"])
        if size is not None:
            self.assertIn(" %s as one request" % km._human_bytes(size), r["error"])
        self.assertIn("past the %s the dashboard can carry back" % km._human_bytes(km._FILE_COMMENTS_REPLY_MAX), r["error"])
        self.assertNotIn("in one reply", r["error"], "the kernel's refusal, not the host's reply estimate")
        self.assertEqual(self.traced, [])
        self.assertEqual(self.reached, [], "nothing was written, so nothing is told")


class EachRecordArrayIsBoundedAlone(_BoundWorld):
    """The three arrays round 1 left unbounded each trip the bound on their own — the content is tiny."""

    def test_suggestions_accepted_and_rejected_each_refuse_past_the_cap(self):
        for field in ("suggestions", "accepted", "rejected"):
            with self.subTest(field=field):
                args = dict(PLAIN, suggestions=[])
                args[field] = decisions(3000)
                size = request_bytes(self.real, "save", args, FENCE)
                self.assertGreater(size, self.SMALL)
                r = self.save(self.fp, args=args)
                self.assert_refused_at_the_kernel(r, size)

    def test_the_content_bound_still_comes_first_and_needs_no_serialization(self):
        # both over: the text cap's refusal, with its own phrase, and still no node
        big = "x" * (km._TEXT_MAX_BYTES + 1)
        r = self.save(self.fp, args=dict(PLAIN, content=big, rejected=decisions(3000)))
        self.assertEqual((r["type"], r["code"]), ("fileCommentsFailed", "too-large"))
        self.assertIn("past the 2.0 MB text cap the viewer edits", r["error"])
        self.assertNotIn("as one request", r["error"])
        self.assertIsNone(self.seen())


class TheBoundaryIsTheSerializedRequest(_BoundWorld):
    """`>` on the byte count of the request as piped: at the cap the request reaches the host whole; one
    byte over is refused before the spawn."""

    def test_at_the_cap_the_request_reaches_the_host_one_byte_over_does_not(self):
        at = self.sized(dict(PLAIN, rejected=decisions(2)), self.SMALL)
        r = self.save(self.fp, args=at)
        self.assertEqual(r["type"], "fileCommentsResult", r)
        seen = self.seen()["request"]
        self.assertEqual(seen["args"]["rejected"], at["rejected"], "all the decisions reached node")
        self.assertEqual(len(json.dumps(seen)), self.SMALL, "what node read is what the kernel measured")
        self.assertEqual([sid for sid, _ in self.reached], [SID], "that save landed, so its decisions' count was told")
        self.reached.clear(), self.traced.clear()
        over = self.sized(dict(PLAIN, rejected=decisions(2)), self.SMALL + 1)
        r = self.save(self.fp, args=over)
        self.assert_refused_at_the_kernel(r, self.SMALL + 1)

    def test_the_measure_is_bytes_on_the_wire_not_characters(self):
        # fewer characters than the cap, more bytes once serialized: ensure_ascii writes é as é, six bytes
        entry = {"id": "k0", "oldText": "", "newText": "é" * 12000}
        args = dict(PLAIN, rejected=[entry])
        self.assertLess(len(json.dumps(args, ensure_ascii=False)), self.SMALL, "under the cap counted in characters")
        size = request_bytes(self.real, "save", args, FENCE)
        self.assertGreater(size, self.SMALL, "over it counted in the bytes piped")
        r = self.save(self.fp, args=args)
        self.assert_refused_at_the_kernel(r, size)


class EveryVerbIsBoundedAndTheTextCapIsNotThisBound(_BoundWorld):
    """The bound is on the request, any verb: a comment's note or a status's arguments past the cap refuse
    with a lead naming what the verb does. And it is the REPLY cap, not the 2 MB text cap: a note past
    the text cap is the host's business and reaches it."""

    def test_a_comment_and_a_status_past_the_cap_refuse_with_their_own_leads(self):
        r = self.verb("comment", {"note": "n" * (self.SMALL + 1)})
        self.assert_refused_at_the_kernel(r, lead="cannot write the comments for %s: the request comes to")
        r = self.verb("status", {"baseline": False, "junk": "j" * (self.SMALL + 1)})
        self.assert_refused_at_the_kernel(r, lead="cannot open the comments for %s: the request comes to")

    def test_a_note_past_the_text_cap_but_under_the_reply_cap_reaches_the_host(self):
        km._FILE_COMMENTS_REPLY_MAX = REAL_CAP
        note = "n" * (km._TEXT_MAX_BYTES + 1)
        r = self.verb("comment", {"note": note})
        self.assertEqual(r["type"], "fileCommentsResult", r)
        self.assertEqual(len(self.seen()["request"]["args"]["note"]), len(note), "the whole note reached node")


class TheFindingsProbeNeverSpawnsNode(tks._SaveWorld):
    """The finding's own frame at the REAL cap, through the real dispatcher: a small text, a real record,
    and hundreds of thousands of fake decisions. Refused by the kernel with no spawn attempted
    — _run_bounded is swapped for a recorder, so a spawn would be counted even if the stub never wrote."""

    def test_a_save_with_decisions_past_the_cap_is_refused_without_a_spawn(self):
        spawn = _NoSpawn()
        saved = km._run_bounded
        km._run_bounded = spawn
        try:
            args = dict(PLAIN, rejected=decisions(PROBE_ENTRIES))
            real = os.path.realpath(self.fp)
            size = request_bytes(real, "save", args, FENCE)
            self.assertGreater(size, REAL_CAP)
            r = self.save(self.fp, args=args)
            self.assertEqual((r["type"], r["code"]), ("fileCommentsFailed", "too-large"), r)
            self.assertEqual(spawn.calls, [], "no spawn, no pipe")
            self.assertIn("cannot save %s: the text, change records and decisions come to %s as one request, past the "
                          "16.0 MB the dashboard can carry back" % (km._tilde(real), km._human_bytes(size)), r["error"])
            self.assertEqual(self.reached, [])
            self.assertEqual(self.traced, [])
            # the same save with the editor's decisions goes through, and what is piped is what was measured
            r = self.save(self.fp, args=tks.REJECT_TWO)
            self.assertEqual(r["type"], "fileCommentsResult", r)
            self.assertEqual(len(spawn.calls), 1)
            argv, payload = spawn.calls[0]
            self.assertEqual(len(payload), request_bytes(real, "save", tks.REJECT_TWO, FENCE))
            self.assertLessEqual(len(payload), REAL_CAP)
        finally:
            km._run_bounded = saved

    def test_the_call_itself_refuses_and_kernel_verbs_are_unaffected(self):
        # the unit under the wire: (None, ("too-large", ...)) and no spawn; log-send's small entry spawns as before
        spawn = _NoSpawn()
        saved = km._run_bounded
        km._run_bounded = spawn
        try:
            out, err = km._file_comments_call(self.fp, "save", dict(PLAIN, accepted=decisions(PROBE_ENTRIES)), FENCE)
            self.assertIsNone(out)
            self.assertEqual(err[0], "too-large")
            self.assertEqual(spawn.calls, [])
            out, err = km._file_comments_call(self.fp, "log-send", {"comments": [], "watermark": 1})
            self.assertIsNone(err)
            self.assertEqual(len(spawn.calls), 1)
        finally:
            km._run_bounded = saved


# ── the real host (tests/test_file_comments_e2e.py's World) ────────────────────────────────────

pytestmark_e2e = pytest.mark.skipif(not e2e.NODE, reason="node not installed on this machine")


@pytestmark_e2e
def test_the_findings_save_is_refused_by_the_kernel_before_the_host_runs_and_the_disk_is_untouched(world):
    """End to end, the scenario the review verified against the host alone: a tracked file with a sidecar
    holding one pending change, the editor's text, its record, and hundreds of thousands of
    invented decisions. Before the fix the kernel piped it whole and the HOST refused from its reply
    estimate after parsing and walking every entry; now the kernel refuses before any spawn, in its own
    words, and the file, the sidecar and the log are as they were. The same save with no decisions
    then goes through the real host, so the bound admits the request the editor sends."""
    s0 = world.ok("status", world.fp)
    world.ok("set-tracked", world.fp, {"on": True, "scope": "file"}, world.fence_of(s0))
    world.track_edit("cut p95 latency by 40%", "cut p95 latency by 45%")
    s = world.ok("status", world.fp)
    assert len(s["hunks"]) == 1
    rec = s["store"]["suggestions"][0]
    text_before, sidecar_before = world.fp.read_bytes(), Path(s["storePath"]).read_bytes()
    log_before = world.log_lines(s)
    spawn = _NoSpawn()
    saved = km._run_bounded
    km._run_bounded = spawn
    try:
        args = {"content": e2e.EDITED, "suggestions": [rec], "accepted": [], "rejected": decisions(PROBE_ENTRIES)}
        size = request_bytes(os.path.realpath(str(world.fp)), "save", args, world.fence_of(s, file=True))
        assert size > REAL_CAP
        r = world.op("save", world.fp, args, world.fence_of(s, file=True))
    finally:
        km._run_bounded = saved
    assert (r["type"], r["code"]) == ("fileCommentsFailed", "too-large"), r
    assert spawn.calls == [], "the kernel refused before the host was spawned"
    assert "as one request, past the 16.0 MB the dashboard can carry back" in r["error"]
    assert "in one reply" not in r["error"], "the host's reply-estimate phrase: it never ran"
    assert km._human_bytes(size) in r["error"]
    assert world.fp.read_bytes() == text_before and Path(s["storePath"]).read_bytes() == sidecar_before
    assert world.log_lines(s) == log_before
    assert world.traced == [] and world.injected == []
    # the editor's own request — the same text and record, nothing decided — is under the bound and lands
    r = world.ok("save", world.fp, {"content": e2e.EDITED, "suggestions": [rec], "accepted": [], "rejected": []},
                 world.fence_of(s, file=True))
    assert world.fp.read_text() == e2e.EDITED
    assert [x["id"] for x in json.loads(Path(r["storePath"]).read_text())["suggestions"]] == [rec["id"]]
    assert [e["kind"] for e in world.log_lines(r)] == ["set-tracked", "edit"]
