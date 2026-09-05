#!/usr/bin/env python3
"""Comment threads (the user 2026-08-13): highlight a passage in a session's chat, comment on it,
and a side conversation opens there — a popover backed by a FORK of the session cut at the anchored
message, kept OFF the board (reg threadOf, no names/ entry) until "Break out" promotes it.

Covered here: the inclusive cut-target resolution, the thread-fork's invisibility contract (no
names/, skipped by live_sessions, skipped by discover), the opening message's frame + its strip,
the transcript→popover projection, the create/reply/resolve/promote ops, and promotion's seeding
order. All fixtures SYNTHETIC: invented text, placeholder UUIDs.
"""
import json
import os
import shutil
import tempfile
import time
import unittest
from datetime import datetime, timezone
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ["ROMP_TMUX_AVAILABLE"] = "1"
os.environ["ROMP_SERVE_TOKEN"] = "testtok"
em = SourceFileLoader("romp_event_model", os.path.join(BIN, "romp-event-model")).load_module()
jd = SourceFileLoader("romp_judge", os.path.join(BIN, "romp-judge")).load_module()
km = SourceFileLoader("romp_kernel", os.path.join(BIN, "romp-kernel")).load_module()
sb = SourceFileLoader("romp_sdk_backend_ct", os.path.join(BIN, "romp_sdk_backend.py")).load_module()

km._limit_hold = lambda sid: None

PARENT = "11111111-2222-3333-4444-555555555555"
THREAD = "66666666-7777-8888-9999-aaaaaaaaaaaa"


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def uline(t, text, uuid, parent=None, meta=False):
    r = {"type": "user", "timestamp": iso(t), "uuid": uuid, "parentUuid": parent,
         "promptSource": "typed", "message": {"role": "user", "content": text}}
    if meta:
        r["isMeta"] = True
    return r


def aline(t, text, uuid, parent=None):
    return {"type": "assistant", "timestamp": iso(t), "uuid": uuid, "parentUuid": parent,
            "message": {"role": "assistant", "content": [{"type": "text", "text": text}],
                        "stop_reason": "end_turn"}}


def tline(t, uuid, parent):
    """A tool_use-only assistant record — a spine node that is not prose."""
    return {"type": "assistant", "timestamp": iso(t), "uuid": uuid, "parentUuid": parent,
            "message": {"role": "assistant",
                        "content": [{"type": "tool_use", "id": "tu_" + uuid, "name": "Read", "input": {}}]}}


def boundary(t, uuid, parent):
    return {"type": "system", "subtype": "compact_boundary", "timestamp": iso(t),
            "uuid": uuid, "parentUuid": parent}


class CommentBase(unittest.TestCase):
    """Temp state root shared by kernel + judge (km.jd IS the loaded jd module), synthetic
    transcripts under a temp projects/ dir — the test_sdk_clear_fork conventions."""

    def setUp(self):
        self._saved = jd.STATE
        self._saved_proj = jd.PROJECTS
        self._td = tempfile.mkdtemp()
        jd._rebind_state(Path(self._td))
        jd.PROJECTS = Path(self._td) / "projects"
        jd._discover_cache.clear()
        jd._PARSE_CACHE.clear()
        km._thread_msgs_cache.clear()
        self.now = int(time.time())
        self.cdir = str(Path(self._td) / "work")
        self.proj = jd._proj_dir(self.cdir)
        self.proj.mkdir(parents=True, exist_ok=True)
        jd.NAMES.mkdir(parents=True, exist_ok=True)
        jd.SDKDIR.mkdir(parents=True, exist_ok=True)
        # never build the real SDK backend in here — the frame reads state "" from a None backend
        self._saved_sdk = km._sdk
        km._sdk = lambda: None

    def tearDown(self):
        km._sdk = self._saved_sdk
        jd._rebind_state(self._saved)
        jd.PROJECTS = self._saved_proj
        shutil.rmtree(self._td, ignore_errors=True)

    def _write(self, stem, records):
        p = self.proj / (stem + ".jsonl")
        p.write_text("\n".join(json.dumps(r) for r in records) + "\n")
        return p

    def _parent_records(self):
        t = self.now - 600
        return [uline(t, "how should the retry loop back off?", "u1"),
                aline(t + 5, "Use exponential backoff with a jitter of ten percent.", "a1", parent="u1"),
                uline(t + 60, "and the cap?", "u2", parent="a1"),
                aline(t + 65, "Cap the delay at two minutes.", "a2", parent="u2")]


# ── the cut target: inclusive, guarded ────────────────────────────────────────────────────────────

class CutTarget(CommentBase):
    def test_an_assistant_anchor_cuts_at_itself_not_its_ancestor(self):
        p = self._write(PARENT, self._parent_records())
        cut, cut_t, err = km._comment_cut_target(str(p), PARENT, "a1")
        self.assertIsNone(err)
        self.assertEqual(cut, "a1", "the thread must HOLD the highlighted answer — inclusive cut")
        self.assertGreater(cut_t, 0, "the cut record's own time rides along for the timeline square")

    def test_a_tool_row_anchor_falls_to_its_nearest_prose_ancestor(self):
        # a tool_use record is type "assistant" but NOT a clean cut — including it would leave the
        # fork's history ending on a dangling tool call; the nearest prose record carries the anchor
        t = self.now - 300
        recs = self._parent_records() + [tline(t, "tu9", "a2")]
        p = self._write(PARENT, recs)
        cut, cut_t, err = km._comment_cut_target(str(p), PARENT, "tu9")
        self.assertIsNone(err)
        self.assertEqual(cut, "a2")

    def test_a_pre_compaction_anchor_is_refused_loudly(self):
        t = self.now - 600
        recs = [uline(t, "old ask", "u1"),
                aline(t + 5, "old answer", "a1", parent="u1"),
                boundary(t + 100, "b1", "a1"),
                uline(t + 200, "fresh ask", "u2", parent="b1")]
        p = self._write(PARENT, recs)
        cut, cut_t, err = km._comment_cut_target(str(p), PARENT, "a1")
        self.assertIsNone(cut)
        self.assertIn("compaction", err)

    def test_an_unknown_anchor_is_refused(self):
        p = self._write(PARENT, self._parent_records())
        cut, cut_t, err = km._comment_cut_target(str(p), PARENT, "nope")
        self.assertIsNone(cut)
        self.assertTrue(err)

    def _seamed_session(self):
        """A machine-cut resume that forked fresh-headed: old records in the resumed-from file,
        new ones in the current file, joined only by the states resumeFork lineage row — the shape
        that read every pre-seam message as 'not in the transcript' (the user 2026-08-15)."""
        old_fsid, new_fsid = PARENT, "cccccccc-dddd-eeee-ffff-000000000000"
        t = self.now - 900
        self._write(old_fsid, [uline(t, "the pre-seam ask", "u1"),
                               aline(t + 5, "the pre-seam answer, the one worth a comment", "a1", parent="u1")])
        p = self._write(new_fsid, [uline(t + 300, "the post-seam ask", "u9", parent=None),
                                   aline(t + 305, "the post-seam answer", "a9", parent="u9")])
        sdir = jd.STATE / "states"
        sdir.mkdir(parents=True, exist_ok=True)
        (sdir / (PARENT + ".jsonl")).write_text(
            json.dumps({"resumeFork": {"from": old_fsid, "to": new_fsid}, "t": t + 250}) + "\n")
        return p

    def test_a_pre_seam_anchor_is_found_and_falls_back_to_a_tip_fork(self):
        p = self._seamed_session()
        cut, cut_t, err = km._comment_cut_target(str(p), PARENT, "a1")
        self.assertIsNone(err, "the stitched chain must FIND the message the chat shows")
        self.assertEqual(cut, "", "behind the seam the CLI can't address it — tip fork instead")
        self.assertGreater(cut_t, 0, "the anchor's own time still stamps the row")

    def test_a_post_seam_anchor_still_cuts_at_itself(self):
        p = self._seamed_session()
        cut, cut_t, err = km._comment_cut_target(str(p), PARENT, "a9")
        self.assertIsNone(err)
        self.assertEqual(cut, "a9")

    def test_rewind_names_the_seam_instead_of_denying_the_message_exists(self):
        p = self._seamed_session()
        cut, err = km._rewind_target(str(p), PARENT, "u1")
        self.assertIsNone(cut)
        self.assertIn("restart seam", err)


# ── the thread fork's invisibility contract ───────────────────────────────────────────────────────

class ThreadForkInvisibility(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.mkdtemp()
        self.be = sb.SdkBackend(Path(self.td), "/bin/true", lambda *a, **k: None)
        self.be.spawn("parent", self.td, sid=PARENT)

    def tearDown(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def test_fork_observability_stamps_the_source_size_for_the_spend_log(self):
        # T156, measured no-build: the tail-copy optimization died on evidence (~5s of a ~70s wall
        # was file size), so every fork records its resume-source size at mint; the spend site logs
        # size + create-to-spend duration, and a recurrence of 200s-class boots reopens the case
        # with data instead of speculation.
        import os as _os
        tp = sb.transcript_path(self.td, PARENT)
        _os.makedirs(_os.path.dirname(tp), exist_ok=True)
        with open(tp, "w") as f:
            f.write('{"type":"user","uuid":"a1"}\n' * 100)
        self.be.fork("thread-x", PARENT, "a1", sid=THREAD, thread_of=PARENT)
        reg = json.loads((Path(self.td) / "sdk" / (THREAD + ".json")).read_text())
        self.assertEqual(reg.get("forkSrcBytes"), _os.path.getsize(tp))
        self.assertGreater(reg.get("forkedFrom", {}).get("t", 0), 0, "the duration base is the mint stamp")
        # the spend site reads both back into one log line (source pin — the spend needs a live CLI)
        import inspect
        spend = inspect.getsource(sb.SdkSession._on_message)
        self.assertIn('self.backend._log("fork spent (%s): src %.1fMB, create->spend %ds"', spend)

    def test_a_thread_fork_writes_no_names_entry_and_carries_threadOf(self):
        self.be.fork("thread-x", PARENT, "a1", sid=THREAD, thread_of=PARENT)
        self.assertFalse((Path(self.td) / "names" / THREAD).exists(),
                         "names/ is the discoverability trigger — a thread must never write it")
        reg = json.loads((Path(self.td) / "sdk" / (THREAD + ".json")).read_text())
        self.assertEqual(reg.get("threadOf"), PARENT)
        self.assertEqual(reg.get("forkOf"), PARENT)
        self.assertEqual(reg.get("forkAt"), "a1")

    def test_fast_mode_rides_the_fork_like_model_and_effort(self):
        # the user 2026-08-25: a comment made from an Opus-high-FAST session came up slow — the fork
        # reg seeded mode/effort/model from the parent but never fast; fast_opt reads reg["fast"] at
        # connect, so inheriting it here makes the thread fast from its first frame
        preg_path = Path(self.td) / "sdk" / (PARENT + ".json")
        preg = json.loads(preg_path.read_text())
        preg["fast"] = True
        preg_path.write_text(json.dumps(preg))
        self.be.fork("thread-x", PARENT, "a1", sid=THREAD, thread_of=PARENT)
        reg = json.loads((Path(self.td) / "sdk" / (THREAD + ".json")).read_text())
        self.assertTrue(reg.get("fast"), "a fast parent's new thread is fast")

    def test_a_slow_parent_stays_slow(self):
        self.be.fork("thread-x", PARENT, "a1", sid=THREAD, thread_of=PARENT)
        reg = json.loads((Path(self.td) / "sdk" / (THREAD + ".json")).read_text())
        self.assertNotIn("fast", reg, "no inherited fast key when the parent never asked for it")

    def test_a_fork_fast_on_arms_the_ask_on_a_slow_parent(self):
        # the user 2026-08-29: the default-comment setting (or a dialog pick) can arm fast for the
        # thread regardless of the parent; the reg's `fast` is what fast_opt reads at connect
        self.be.fork("thread-x", PARENT, "a1", sid=THREAD, thread_of=PARENT, fast="on")
        reg = json.loads((Path(self.td) / "sdk" / (THREAD + ".json")).read_text())
        self.assertTrue(reg.get("fast"), "an explicit on arms the ask on a slow parent")

    def test_a_fork_fast_off_launches_plain_from_a_fast_parent(self):
        preg_path = Path(self.td) / "sdk" / (PARENT + ".json")
        preg = json.loads(preg_path.read_text())
        preg["fast"] = True
        preg_path.write_text(json.dumps(preg))
        self.be.fork("thread-x", PARENT, "a1", sid=THREAD, thread_of=PARENT, fast="off")
        reg = json.loads((Path(self.td) / "sdk" / (THREAD + ".json")).read_text())
        self.assertNotIn("fast", reg, "off launches plain; the parent keeps its own ask untouched")

    def test_the_fast_ask_reaches_the_clis_flag_settings(self):
        # the chain the reg key rides (source pins — the flag file needs a live CLI connect):
        # reg["fast"] → fast_opt at construct → _options hands it to flag_settings_path → the
        # CLI's documented fastMode opt-in key. A refusal clears the ask + toasts, same model.
        import inspect
        self.assertIn('self.fast_opt = bool(reg.get("fast"))', inspect.getsource(sb.SdkSession.__init__))
        self.assertIn("fast=sess.fast_opt", inspect.getsource(sb.SdkBackend._options))
        self.assertIn('keys["fastMode"] = True', inspect.getsource(sb.flag_settings_path))
        refusal = inspect.getsource(sb.SdkSession._adopt_fast_state)
        self.assertIn('refused_ask = bool(reason) and self.fast_opt and fast != "on"', refusal)
        self.assertIn('kw["fast"] = False', refusal, "a refused ask is cleared, never left armed")

    def test_a_plain_fork_still_writes_its_names_entry(self):
        self.be.fork("fork-x", PARENT, "a1", sid=THREAD)
        self.assertTrue((Path(self.td) / "names" / THREAD).exists())

    def test_live_sessions_skips_threads_so_no_tab_is_born(self):
        self.be.fork("thread-x", PARENT, "a1", sid=THREAD, thread_of=PARENT)
        self.assertIn(PARENT, self.be.live_sessions())
        self.assertNotIn(THREAD, self.be.live_sessions(),
                         "a thread's only surface is the parent chat's comment UI")

    def test_promote_writes_names_and_clears_threadOf(self):
        self.be.fork("thread-x", PARENT, "a1", sid=THREAD, thread_of=PARENT)
        self.assertTrue(self.be.promote_thread(THREAD, "sidework", "#123456", "#ffffff"))
        self.assertTrue((Path(self.td) / "names" / THREAD).exists())
        reg = json.loads((Path(self.td) / "sdk" / (THREAD + ".json")).read_text())
        self.assertNotIn("threadOf", reg)
        self.assertEqual(reg.get("name"), "sidework")
        self.assertIn(THREAD, self.be.live_sessions(), "a promoted thread is an ordinary session")

    def test_promote_refuses_a_non_thread(self):
        self.assertFalse(self.be.promote_thread(PARENT, "nope"))

    def test_session_state_reads_a_dormant_thread_as_empty(self):
        self.be.fork("thread-x", PARENT, "a1", sid=THREAD, thread_of=PARENT)
        self.assertEqual(self.be.session_state(THREAD), "")


class ThreadDiscoverBlindness(CommentBase):
    def test_discover_never_lists_a_thread(self):
        self._write(PARENT, self._parent_records())
        (jd.NAMES / PARENT).write_text("parent\t%s" % self.cdir)
        self._write(THREAD, self._parent_records())     # the fork's transcript exists on disk
        (jd.SDKDIR / (THREAD + ".json")).write_text(json.dumps(
            {"sid": THREAD, "name": "thread-x", "cwd": self.cdir,
             "lastSid": THREAD, "alive": True, "threadOf": PARENT}))
        sids = [r[0] for r in jd.discover(self.now)]
        self.assertIn(PARENT, sids)
        self.assertNotIn(THREAD, sids, "no names/ entry → no judge pass, no cards, no lane")


# ── the opening message: frame + strip ────────────────────────────────────────────────────────────

class OpeningMessage(unittest.TestCase):
    def test_frame_quotes_the_passage_and_carries_the_comment(self):
        body = km._comment_first_message("Cap the delay at two minutes.", "Why two minutes and not five?")
        self.assertIn("> Cap the delay at two minutes.", body)
        self.assertTrue(body.endswith("Why two minutes and not five?"))
        self.assertTrue(body.startswith(km._COMMENT_FRAME_HEAD))

    def test_strip_returns_exactly_the_comment(self):
        body = km._comment_first_message("line one\nline two", "The comment.\n\nWith two paragraphs.")
        self.assertEqual(km._comment_strip_frame(body), "The comment.\n\nWith two paragraphs.")

    def test_strip_leaves_an_unframed_message_alone(self):
        self.assertEqual(km._comment_strip_frame("plain reply"), "plain reply")


# ── the transcript → popover projection ───────────────────────────────────────────────────────────

class ThreadProjection(CommentBase):
    def _thread_records(self):
        """The fork copy (u1..a1, verbatim uuids) + the side conversation after the cut."""
        t = self.now - 500
        return [uline(t, "how should the retry loop back off?", "u1"),
                aline(t + 5, "Use exponential backoff with a jitter of ten percent.", "a1", parent="u1"),
                uline(t + 100, km._comment_first_message(
                    "exponential backoff", "Why jitter at all?"), "cu1", parent="a1"),
                aline(t + 110, "Jitter prevents thundering herds.", "ca1", parent="cu1"),
                aline(t + 111, "It also spreads retries across the window.", "ca2", parent="ca1")]

    def _seed_thread(self, records=None, seen=None):
        self._write(THREAD, records or self._thread_records())
        (jd.SDKDIR / (THREAD + ".json")).write_text(json.dumps(
            {"sid": THREAD, "name": "thread-x", "cwd": self.cdir,
             "lastSid": THREAD, "alive": True, "threadOf": PARENT}))
        km._save_comments(PARENT, {"threads": [
            {"tid": THREAD, "sid": THREAD, "anchorUuid": "a1", "cutUuid": "a1",
             "exact": "exponential backoff", "status": "open",
             "createdT": self.now - 400, "lastSeenT": seen if seen is not None else self.now}]})

    def test_projection_starts_after_the_cut_and_strips_the_frame(self):
        self._seed_thread()
        msgs = km._thread_messages(THREAD, "a1")
        self.assertEqual([m["who"] for m in msgs], ["you", "agent"])
        self.assertEqual(msgs[0]["text"], "Why jitter at all?",
                         "the popover shows the comment, not its quoting frame")
        self.assertNotIn("thundering", msgs[0]["text"])

    def test_consecutive_agent_records_merge_into_one_reply(self):
        self._seed_thread()
        msgs = km._thread_messages(THREAD, "a1")
        self.assertIn("thundering herds", msgs[1]["text"])
        self.assertIn("spreads retries", msgs[1]["text"])

    def test_frame_reports_unread_from_the_watermark(self):
        self._seed_thread(seen=self.now - 450)      # replies landed after the last look
        fr = km._comments_frame(PARENT)
        self.assertEqual(fr["type"], "comments")
        self.assertEqual(fr["id"], PARENT)
        self.assertTrue(fr["threads"][0]["unread"])
        km._comment_seen(PARENT, THREAD)
        km._thread_msgs_cache.clear()
        fr = km._comments_frame(PARENT)
        self.assertFalse(fr["threads"][0]["unread"])

    def test_no_store_no_frame(self):
        self.assertIsNone(km._comments_frame(PARENT))

    def test_a_promoted_thread_whose_session_ended_drops_off_the_frame(self):
        # the user 2026-08-13: broke a thread out, closed the resulting session, and the highlight
        # kept claiming "now its own session" — a dead promotion is done, not a stale pointer
        self._write(THREAD, self._thread_records())
        (jd.SDKDIR / (THREAD + ".json")).write_text(json.dumps(
            {"sid": THREAD, "name": "sidework", "cwd": self.cdir, "lastSid": THREAD, "alive": True}))
        km._save_comments(PARENT, {"threads": [
            {"tid": THREAD, "sid": THREAD, "anchorUuid": "a1", "cutUuid": "a1",
             "exact": "exponential backoff", "status": "promoted", "promotedName": "sidework",
             "createdT": self.now - 400, "lastSeenT": self.now}]})
        fr = km._comments_frame(PARENT)
        self.assertEqual(len(fr["threads"]), 1, "still alive — the mark and chip stay")
        (jd.SDKDIR / (THREAD + ".json")).write_text(json.dumps(
            {"sid": THREAD, "name": "sidework", "cwd": self.cdir, "lastSid": THREAD, "alive": False}))
        fr = km._comments_frame(PARENT)
        self.assertEqual(fr["threads"], [], "ended — no highlight, no badge, nothing on the message")
        # the row survives in the store: reviving the session from the Fleet should bring it back
        self.assertEqual(len(km._load_comments(PARENT)["threads"]), 1)

    def test_pre_fork_thread_reads_nothing_not_the_parent(self):
        # Until the CLI init spends forkOf, the thread reg's lastSid points at the PARENT
        # transcript — reading it would present the parent's post-anchor turns as the thread's own.
        self._write(PARENT, self._parent_records())
        (jd.SDKDIR / (THREAD + ".json")).write_text(json.dumps(
            {"sid": THREAD, "name": "thread-x", "cwd": self.cdir, "lastSid": PARENT,
             "alive": True, "threadOf": PARENT, "forkOf": PARENT, "forkAt": "a1"}))
        self.assertEqual(km._thread_messages(THREAD, "a1"), [])

    def test_an_injected_marker_message_is_not_the_users(self):
        recs = self._thread_records()
        recs.append({"type": "user", "timestamp": iso(self.now - 80), "uuid": "inj1",
                     "parentUuid": "ca2", "promptSource": "typed",
                     "message": {"role": "user",
                                 "content": "<!-- romp-injected -->Where does this stand?"}})
        self._seed_thread(records=recs)
        msgs = km._thread_messages(THREAD, "a1")
        self.assertNotIn("Where does this stand", json.dumps(msgs))

    def test_frame_surfaces_a_thread_launch_error(self):
        self._seed_thread()
        class _Stub:
            def session_state(self, sid):
                return ""
            def launch_error(self, sid):
                return {"text": "its process couldn't start (a synthetic reason)", "at": 0, "limit": False}
        km._sdk = lambda: _Stub()
        fr = km._comments_frame(PARENT)
        self.assertIn("couldn't start", fr["threads"][0]["error"])

    def test_a_compaction_summary_record_is_not_a_message(self):
        recs = self._thread_records()
        recs.append({"type": "user", "timestamp": iso(self.now - 90), "uuid": "cs1",
                     "parentUuid": "ca2", "isCompactSummary": True,
                     "message": {"role": "user", "content": "summary of the earlier exchange"}})
        self._seed_thread(records=recs)
        msgs = km._thread_messages(THREAD, "a1")
        self.assertNotIn("summary of the earlier exchange", json.dumps(msgs))

    def test_a_large_transcript_reads_from_the_tail_window(self):
        # the copied history can be huge; the side conversation sits at the END, so the projection
        # must come out of the tail window without a full reparse — and be IDENTICAL to it
        filler = [aline(self.now - 550 + i, "filler %d " % i + "x" * 4000, "f%d" % i,
                        parent=("u1" if i == 0 else "f%d" % (i - 1))) for i in range(120)]
        t = self.now - 500
        recs = ([uline(self.now - 600, "how should the retry loop back off?", "u1")] + filler +
                [aline(t + 5, "Use exponential backoff.", "a1", parent="f119"),
                 uline(t + 100, km._comment_first_message("exponential backoff", "Why jitter?"),
                       "cu1", parent="a1"),
                 aline(t + 110, "Jitter prevents thundering herds.", "ca1", parent="cu1")])
        self._seed_thread(records=recs)
        p = self.proj / (THREAD + ".jsonl")
        self.assertGreater(p.stat().st_size, km._THREAD_TAIL_BYTES,
                           "the fixture must actually overflow the tail window")
        msgs = km._thread_messages(THREAD, "a1")
        self.assertEqual([m["who"] for m in msgs], ["you", "agent"])
        self.assertEqual(msgs[0]["text"], "Why jitter?")
        self.assertIn("thundering herds", msgs[1]["text"])


# ── the ops: create / reply / resolve / promote ───────────────────────────────────────────────────

class FakeBackend:
    """Records calls; shaped like SdkBackend where the ops touch it."""

    def __init__(self):
        self.calls = []
        self.sent = []

    def fork(self, name, parent_sid, cut_uuid="", bg="", fg="", sid=None, thread_of="",
             model="", effort="", fast=""):
        self.calls.append(("fork", name, parent_sid, cut_uuid, sid, thread_of))
        self.forked_meta = (model, effort)
        self.forked_fast = fast
        self.forked_bg = bg
        return sid

    def connect(self, sid):
        self.calls.append(("connect", sid))
        return True

    def send(self, sid, text):
        self.calls.append(("send", sid))
        self.sent.append((sid, text))
        return True

    def resume(self, name, sid, cwd=None):
        self.calls.append(("resume", sid))
        return True

    def interrupt(self, sid):
        self.calls.append(("interrupt", sid))
        return True

    def kill(self, sid):
        self.calls.append(("kill", sid))
        return True

    def promote_thread(self, sid, name, bg="", fg=""):
        self.calls.append(("promote", sid, name))
        self.promoted_color = (bg, fg)
        return True


class CommentOps(CommentBase):
    def setUp(self):
        super().setUp()
        self.be = FakeBackend()
        self._saved_backend_for = km.Sessions.backend_for
        self._saved_ready = km._sdk_ready
        self._saved_sessions = km._sessions
        self._saved_reveal = km._reveal_chat_for
        self._saved_push_now = km._push_session_now
        km.Sessions.backend_for = staticmethod(lambda sid: self.be)
        km._sdk_ready = lambda: True
        p = self._write(PARENT, self._parent_records())
        km._sessions = lambda now, window=None, forks=True: [
            {"sid": PARENT, "name": "parent", "path": str(p), "mtime": self.now}]
        km._reveal_chat_for = lambda client, msg: None
        km._push_session_now = lambda sid: None

    def tearDown(self):
        km.Sessions.backend_for = self._saved_backend_for
        km._sdk_ready = self._saved_ready
        km._sessions = self._saved_sessions
        km._reveal_chat_for = self._saved_reveal
        km._push_session_now = self._saved_push_now
        self._clear_defaults()   # the module shares one hermetic STATE — never leak across tests
        super().tearDown()

    def _clear_defaults(self):
        for f in ("comment-model", "comment-effort", "comment-fast"):
            try:
                (km.jd.STATE / f).unlink()
            except OSError:
                pass
        km.jd._state_cache.clear()

    def _put_default(self, name, value):
        km.jd.STATE.mkdir(parents=True, exist_ok=True)
        (km.jd.STATE / name).write_text(value)
        km.jd._state_cache.clear()   # same-second writes share an mtime; the cache is not under test

    def test_create_forks_a_thread_and_sends_the_framed_opener(self):
        err, tid = km._comment_create(PARENT, "a1", "exponential backoff", "Why jitter at all?")
        self.assertIsNone(err)
        self.assertTrue(tid)
        kinds = [c[0] for c in self.be.calls]
        self.assertEqual(kinds, ["fork", "connect", "send"])
        fork = self.be.calls[0]
        self.assertEqual(fork[3], "a1", "inclusive cut — the thread holds the highlighted answer")
        self.assertEqual(fork[5], PARENT, "born as a threadOf fork, never a board session")
        self.assertTrue(self.be.sent[0][1].startswith(km._COMMENT_FRAME_HEAD))
        row = km._comment_thread(PARENT, tid)
        self.assertEqual(row["status"], "open")
        self.assertEqual(row["anchorUuid"], "a1")

    def test_threads_autoname_by_count_and_accept_an_edited_name(self):
        _, tid1 = km._comment_create(PARENT, "a1", "exponential backoff", "Why?")
        _, tid2 = km._comment_create(PARENT, "a1", "the cap", "And this?")
        self.assertEqual(km._comment_thread(PARENT, tid1)["name"], "parent-comment-1")
        self.assertEqual(km._comment_thread(PARENT, tid2)["name"], "parent-comment-2")
        self.assertEqual(self.be.calls[0][1], "parent-comment-1",
                         "the thread's reg wears the name — a break-out inherits it")
        _, tid3 = km._comment_create(PARENT, "a1", "jitter", "Named.", name="my.question")
        self.assertEqual(km._comment_thread(PARENT, tid3)["name"], "my.question")
        err, _ = km._comment_create(PARENT, "a1", "jitter", "Bad.", name="no spaces!")
        self.assertIn("letters, digits", err)
        fr = km._comments_frame(PARENT)
        self.assertEqual(fr["threads"][0]["name"], "parent-comment-1",
                         "the popover titles threads by name off the frame")

    def test_model_and_effort_picks_ride_the_fork_untouched_by_default(self):
        km._comment_create(PARENT, "a1", "exponential backoff", "Why?", model="haiku", effort="low")
        self.assertEqual(self.be.forked_meta, ("haiku", "low"))
        km._comment_create(PARENT, "a1", "the cap", "Plain.")
        self.assertEqual(self.be.forked_meta, ("", ""), "no pick = inherit; the parent is never touched")

    def test_the_comments_identity_color_rides_create_fork_row_and_frame(self):
        _, tid = km._comment_create(PARENT, "a1", "exponential backoff", "Why?", color="#a3be8c")
        self.assertEqual(self.be.forked_bg, "#a3be8c")
        self.assertEqual(km._comment_thread(PARENT, tid)["color"], "#a3be8c")
        self.assertEqual(km._comments_frame(PARENT)["threads"][0]["color"], "#a3be8c")
        _, tid2 = km._comment_create(PARENT, "a1", "the cap", "Junk color.", color="not-a-hex")
        self.assertEqual(self.be.forked_bg, "", "a non-hex color falls to the backend's own pick")
        self.assertNotIn("color", km._comment_thread(PARENT, tid2))

    def test_settings_defaults_ride_every_new_thread(self):
        # the user 2026-08-29, who wanted every new comment thread on one model/effort/fast pick
        # regardless of the session it branches from: the kernel-side default applies when the
        # dialog is left untouched
        self._put_default("comment-model", "claude-opus-5")
        self._put_default("comment-effort", "high")
        self._put_default("comment-fast", "on")
        err, _ = km._comment_create(PARENT, "a1", "exponential backoff", "Why?")
        self.assertIsNone(err)
        self.assertEqual(self.be.forked_meta, ("claude-opus-5", "high"))
        self.assertEqual(self.be.forked_fast, "on")

    def test_the_dialog_pick_beats_the_setting(self):
        self._put_default("comment-model", "haiku")
        self._put_default("comment-fast", "on")
        km._comment_create(PARENT, "a1", "exponential backoff", "Why?", model="fable", fast="off")
        self.assertEqual(self.be.forked_meta[0], "fable")
        self.assertEqual(self.be.forked_fast, "off", "a per-thread pick deviates BOTH ways")

    def test_the_session_sentinel_is_a_byte_identical_noop(self):
        # "session" (the shipped default) resolves to the empty override — exactly the fork()
        # arguments a create sent before the setting existed
        for f in ("comment-model", "comment-effort", "comment-fast"):
            self._put_default(f, "session")
        km._comment_create(PARENT, "a1", "exponential backoff", "Why?")
        self.assertEqual(self.be.forked_meta, ("", ""))
        self.assertEqual(self.be.forked_fast, "")

    def test_absent_files_resolve_the_same_as_the_sentinel(self):
        self.assertEqual(km._comment_launch_prefs(), ("", "", ""))

    def test_the_setters_validate_like_every_kernel_setting(self):
        km._set_comment_model("gpt-99")
        self.assertFalse((km.jd.STATE / "comment-model").exists(), "garbage never reaches the file")
        km._set_comment_model("claude-opus-5")
        self.assertEqual((km.jd.STATE / "comment-model").read_text(), "claude-opus-5")
        km._set_comment_effort("bogus")
        self.assertFalse((km.jd.STATE / "comment-effort").exists())
        km._set_comment_fast("true")
        self.assertFalse((km.jd.STATE / "comment-fast").exists(), '"on"/"session" only — never a bool word')
        km._set_comment_fast("on")
        self.assertEqual((km.jd.STATE / "comment-fast").read_text(), "on")

    def test_a_harness_task_notification_never_renders_as_the_users_words(self):
        recs = self._parent_records()
        t = self.now - 200
        recs += [uline(t, km._comment_first_message("exponential backoff", "Why?"), "cu1", parent="a2"),
                 uline(t + 5, "<task-notification>\n<task-id>b1</task-id>\n<status>stopped</status>"
                       "\n</task-notification>", "tn1", parent="cu1"),
                 aline(t + 10, "Because herds.", "ca1", parent="tn1")]
        self._write(THREAD, recs)
        (jd.SDKDIR / (THREAD + ".json")).write_text(json.dumps(
            {"sid": THREAD, "name": "t", "cwd": self.cdir, "lastSid": THREAD,
             "alive": True, "threadOf": PARENT}))
        msgs = km._thread_messages(THREAD, "a2")
        self.assertEqual([m["who"] for m in msgs], ["you", "agent"],
                         "the harness notice is for the AGENT, not a popover bubble")
        self.assertNotIn("task-notification", json.dumps(msgs))

    def test_a_refused_cut_leaves_no_thread_row_behind(self):
        err, tid = km._comment_create(PARENT, "missing-uuid", "text", "comment")
        self.assertTrue(err)
        self.assertIsNone(tid)
        self.assertEqual(km._load_comments(PARENT).get("threads", []), [])
        self.assertEqual(self.be.calls, [])

    def test_reply_reaches_an_open_thread(self):
        _, tid = km._comment_create(PARENT, "a1", "exponential backoff", "Why?")
        err = km._comment_reply(PARENT, tid, "one more question")
        self.assertIsNone(err)
        self.assertEqual(self.be.sent[-1], (tid, "one more question"))

    def test_a_closed_thread_never_reopens(self):
        # the user's standing rule (2026-09-01): a thread they closed stays on disk and is never
        # revived — replying is refused with the reason (this retires the 2026-08-22/T145
        # "replying IS the reopen gesture" arm, which resumed the CLI and flipped the row open)
        _, tid = km._comment_create(PARENT, "a1", "exponential backoff", "Why?")
        km._comment_resolve(PARENT, tid)
        self.assertEqual(km._comment_thread(PARENT, tid)["status"], "resolved")
        n_sent = len(self.be.sent)
        err = km._comment_reply(PARENT, tid, "one more question")
        self.assertTrue(err and "closed" in err, err)
        self.assertNotIn(("resume", tid), self.be.calls, "nothing wakes a closed thread")
        self.assertEqual(len(self.be.sent), n_sent, "nothing is delivered to it either")
        self.assertEqual(km._comment_thread(PARENT, tid)["status"], "resolved", "the row stays closed")

    def test_relaying_a_resolved_thread_keeps_it_closed(self):
        # resolved -> relay -> reply must not become the reopen door the direct reply refuses
        _, tid = km._comment_create(PARENT, "a1", "exponential backoff", "Why?")
        km._comment_resolve(PARENT, tid)
        saved = km._thread_messages
        km._thread_messages = lambda tsid, cut, floor_t=0: [{"who": "user", "text": "the ask", "t": 5},
                                                             {"who": "assistant", "text": "the answer", "t": 6}]
        try:
            self.assertIsNone(km._comment_merge(PARENT, tid))
        finally:
            km._thread_messages = saved
        self.assertEqual(km._comment_thread(PARENT, tid)["status"], "resolved", "sent back, still closed")
        err = km._comment_reply(PARENT, tid, "one more")
        self.assertTrue(err and "closed" in err, err)

    def test_a_relayed_thread_stays_talkable(self):
        # T145 (the user 2026-08-28): a relay is NOT a close — the explicit reply continues the
        # thread, so only RESOLVED threads fall under the never-reopen rule
        _, tid = km._comment_create(PARENT, "a1", "exponential backoff", "Why?")
        km._comment_update(PARENT, tid, status="merged")
        err = km._comment_reply(PARENT, tid, "afterthought")
        self.assertIsNone(err)
        self.assertIn(("resume", tid), self.be.calls, "the reply is the explicit gesture that wakes it")
        self.assertEqual(km._comment_thread(PARENT, tid)["status"], "open")

    def test_delete_interrupts_the_inflight_reply_before_the_kill(self):
        # deleting a thread mid-generation must STOP the work, not just its cue (the user 2026-08-17)
        _, tid = km._comment_create(PARENT, "a1", "exponential backoff", "Why?")
        km._comment_delete(PARENT, tid)
        kinds = [c[0] for c in self.be.calls if c[0] in ("interrupt", "kill")]
        self.assertEqual(kinds, ["interrupt", "kill"], "cut the turn first, then shut the CLI down")

    def test_delete_removes_the_row(self):
        _, tid = km._comment_create(PARENT, "a1", "exponential backoff", "Why?")
        km._comment_resolve(PARENT, tid)
        km._comment_delete(PARENT, tid)
        self.assertIsNone(km._comment_thread(PARENT, tid))

    def test_promote_seeds_before_names_and_floors_past_the_exchange(self):
        _, tid = km._comment_create(PARENT, "a1", "exponential backoff", "Why?")
        t = self.now - 200
        self._write(tid, [uline(self.now - 600, "how should the retry loop back off?", "u1"),
                          aline(self.now - 595, "Use exponential backoff.", "a1", parent="u1"),
                          uline(t, "opener", "cu1", parent="a1"),
                          aline(t + 10, "reply", "ca1", parent="cu1")])
        (jd.SDKDIR / (tid + ".json")).write_text(json.dumps(
            {"sid": tid, "name": "thread-x", "cwd": self.cdir,
             "lastSid": tid, "alive": True, "threadOf": PARENT}))
        order = []
        saved_seed = km._seed_fork_stores
        km._seed_fork_stores = lambda *a, **k: order.append("seed") or saved_seed(*a, **k)
        real_promote = self.be.promote_thread
        self.be.promote_thread = lambda *a, **k: order.append("names") or real_promote(*a, **k)
        try:
            err = km._comment_promote(PARENT, tid, "sidework")
        finally:
            km._seed_fork_stores = saved_seed
        self.assertIsNone(err)
        self.assertEqual(order, ["seed", "names"],
                         "judge seeds must land before the names/ write — the fork() contract")
        self.assertEqual(km._comment_thread(PARENT, tid)["status"], "promoted")
        self.assertEqual(km._comment_thread(PARENT, tid)["promotedName"], "sidework")
        floor = jd.episode_floor(tid)
        self.assertIsNotNone(floor)
        self.assertGreaterEqual(floor, t + 10,
                                "the floor sits at the thread's leaf — the popover exchange is settled history")

    def _promotable(self, tid):
        """The transcript + reg a thread needs before _comment_promote will touch it."""
        t = self.now - 200
        self._write(tid, [uline(t, "opener", "cu1"), aline(t + 10, "reply", "ca1", parent="cu1")])
        (jd.SDKDIR / (tid + ".json")).write_text(json.dumps(
            {"sid": tid, "name": "thread-x", "cwd": self.cdir,
             "lastSid": tid, "alive": True, "threadOf": PARENT}))

    def test_promote_keeps_the_threads_own_color(self):
        # the color the dialog suggested rides create → row → PROMOTE (the user 2026-08-19: it used
        # to be re-picked at break-out, so the session never matched the color the thread had worn)
        _, tid = km._comment_create(PARENT, "a1", "exponential backoff", "Why?", color="#F9D849")
        self._promotable(tid)
        self.assertIsNone(km._comment_promote(PARENT, tid, "sidework"))
        self.assertEqual(self.be.promoted_color, ("#F9D849", "black"),
                         "the row's color, with the palette's readable fg — never a fresh pick")

    def test_promote_picks_fresh_only_for_a_colorless_row(self):
        _, tid = km._comment_create(PARENT, "a1", "exponential backoff", "Why?")
        self._promotable(tid)
        self.assertIsNone(km._comment_promote(PARENT, tid, "sidework"))
        bg, fg = self.be.promoted_color
        self.assertTrue(bg.startswith("#") and fg in ("white", "black"),
                        "a pre-color row still gets a real identity")

    def test_promote_refuses_a_bad_name(self):
        _, tid = km._comment_create(PARENT, "a1", "exponential backoff", "Why?")
        err = km._comment_promote(PARENT, tid, "bad name!")
        self.assertIn("letters, digits", err)

    def _tag_members(self, name):
        km._flags_cache.clear()
        t = next((t for t in km._timeline_views()["tags"] if t["name"] == name), None)
        return sorted(m["sid"] for m in (t or {"members": []})["members"])

    def test_a_thread_inherits_no_tags_at_create_but_does_when_promoted(self):
        # tab groups on tags (the user 2026-09-04): a comment thread has no tab, so tagging its hidden
        # sid at create would only inflate the member lists — it inherits the parent's tags at the
        # moment it BECOMES a tab (promote), before the connect that precedes the direct push
        km._flags_cache.clear()
        km._set_timeline_views({"active": "all", "tags": [{"id": "g1", "name": "pool", "members": [PARENT]},
                                                          {"id": "g2", "name": "other", "members": ["x"]}]})
        _, tid = km._comment_create(PARENT, "a1", "exponential backoff", "Why?")
        self.assertEqual(self._tag_members("pool"), [PARENT], "the thread fork stays out of the parent's tags")
        self._promotable(tid)
        seen_at_connect = []
        real_connect = self.be.connect
        self.be.connect = lambda sid: (seen_at_connect.append(self._tag_members("pool")), real_connect(sid))[1]
        self.assertIsNone(km._comment_promote(PARENT, tid, "sidework"))
        self.assertEqual(self._tag_members("pool"), sorted([PARENT, tid]), "promoted = a tab now, in the parent's group")
        self.assertEqual(self._tag_members("other"), ["x"], "a tag the parent is not in is untouched")
        self.assertIn(tid, seen_at_connect[0], "membership landed before connect, ahead of the direct push")

    def test_a_session_spawned_from_inside_a_thread_inherits_the_threads_parents_tags(self):
        # a thread's CLI carries the THREAD's sid as ROMP_SID, so `romp new` run from its shell names
        # the thread as parent; the thread holds no tags (no tab), but it lives in the parent's chat —
        # _resolve_parent_sid walks up to the threadOf session, and the child lands in ITS group
        CHILD = "66666666-7777-8888-9999-000000000000"
        km._flags_cache.clear()
        km._set_timeline_views({"active": "all", "tags": [{"id": "g1", "name": "pool", "members": [PARENT]}]})
        _, tid = km._comment_create(PARENT, "a1", "exponential backoff", "Why?")
        self._promotable(tid)                       # the thread's reg, threadOf = PARENT
        reg = lambda sid: json.loads((jd.SDKDIR / (sid + ".json")).read_text()) if (jd.SDKDIR / (sid + ".json")).exists() else None
        self.be.owns = lambda sid: reg(sid) is not None                       # SdkBackend.owns: a reg exists
        self.be.thread_of = lambda sid: str((reg(sid) or {}).get("threadOf") or "")   # SdkBackend.thread_of
        self.assertEqual(km._resolve_parent_sid(tid, {}), (PARENT, None), "the thread resolves to the session it is of")
        names, err = km._tag_new_session(CHILD, km._resolve_parent_sid(tid, {})[0], [])
        self.assertIsNone(err)
        self.assertEqual(names, ["pool"], "the child inherits from the session the thread is of")
        self.assertEqual(self._tag_members("pool"), sorted([PARENT, CHILD]), "…and the thread itself still holds none")

    def test_the_promoting_latch_refuses_resolve_delete_and_reply(self):
        # promote seeds for seconds on a big transcript; ops landing in that window must refuse
        # THROUGH the CAS, or a racing resolve kills the just-promoted board session
        _, tid = km._comment_create(PARENT, "a1", "exponential backoff", "Why?")
        km._comment_update(PARENT, tid, status="promoting")
        calls_before = list(self.be.calls)
        for op in (km._comment_resolve, km._comment_delete):
            err = op(PARENT, tid)
            self.assertIn("becoming its own session", err)
        err = km._comment_reply(PARENT, tid, "hello?")
        self.assertIn("becoming its own session", err)
        self.assertEqual(km._comment_thread(PARENT, tid)["status"], "promoting")
        self.assertEqual(self.be.calls, calls_before, "no kill, no send — the latch holds")

    def test_a_failed_promote_reverts_the_latch(self):
        _, tid = km._comment_create(PARENT, "a1", "exponential backoff", "Why?")
        t = self.now - 200
        self._write(tid, [uline(t, "opener", "cu1"), aline(t + 10, "reply", "ca1", parent="cu1")])
        (jd.SDKDIR / (tid + ".json")).write_text(json.dumps(
            {"sid": tid, "name": "thread-x", "cwd": self.cdir,
             "lastSid": tid, "alive": True, "threadOf": PARENT}))
        saved = km._seed_fork_stores
        km._seed_fork_stores = lambda *a, **k: "seeding failed on purpose"
        try:
            err = km._comment_promote(PARENT, tid, "sidework")
        finally:
            km._seed_fork_stores = saved
        self.assertIn("seeding failed", err)
        self.assertEqual(km._comment_thread(PARENT, tid)["status"], "open",
                         "the latch must never stick on a failed promote")

    def test_seed_fork_stores_refuses_a_vanished_cut(self):
        p = self.proj / (PARENT + ".jsonl")
        err = km._seed_fork_stores(PARENT, THREAD, str(p), "gone-uuid")
        self.assertIn("isn't in the conversation anymore", err)

    def test_resolve_refuses_a_promoted_thread_so_delete_can_never_kill_its_session(self):
        _, tid = km._comment_create(PARENT, "a1", "exponential backoff", "Why?")
        km._comment_update(PARENT, tid, status="promoted", promotedName="sidework")
        err = km._comment_resolve(PARENT, tid)
        self.assertIn("its own session", err)
        self.assertEqual(km._comment_thread(PARENT, tid)["status"], "promoted",
                         "resolve must never overwrite promoted — that hands delete a session to kill")
        km._comment_delete(PARENT, tid)                 # removing the highlight row is fine…
        self.assertNotIn(("kill", tid), self.be.calls)  # …but the promoted session is never killed
        self.assertIsNone(km._comment_thread(PARENT, tid))

    def test_a_missing_cut_shows_nothing_never_the_copied_history(self):
        self._write(THREAD, self._parent_records())
        (jd.SDKDIR / (THREAD + ".json")).write_text(json.dumps(
            {"sid": THREAD, "name": "thread-x", "cwd": self.cdir,
             "lastSid": THREAD, "alive": True, "threadOf": PARENT}))
        self.assertEqual(km._thread_messages(THREAD, "not-in-transcript"), [])

    def test_ending_the_parent_sweeps_its_threads_clis(self):
        _, tid = km._comment_create(PARENT, "a1", "exponential backoff", "Why?")
        km._comment_update(PARENT, tid, status="promoted", promotedName="kept")
        _, tid2 = km._comment_create(PARENT, "a1", "exponential backoff", "And the cap?")
        km._comment_kill_all(PARENT, self.be)
        self.assertIn(("kill", tid2), self.be.calls, "open threads die with their only surface")
        self.assertNotIn(("kill", tid), self.be.calls, "a promoted thread is a board session — untouched")

    def test_a_failed_create_kills_the_half_born_reg(self):
        self.be.send = lambda sid, text: (_ for _ in ()).throw(RuntimeError("boom"))
        err, tid = km._comment_create(PARENT, "a1", "exponential backoff", "Why?")
        self.assertIn("boom", err)
        self.assertIsNone(tid)
        self.assertEqual(km._load_comments(PARENT).get("threads", []), [])
        self.assertIn(("kill",), {c[:1] for c in self.be.calls},
                      "the forked reg/CLI must not outlive the removed row")

    def test_drive_ops_are_registered(self):
        src = (Path(BIN) / "romp-kernel").resolve().read_text()
        for op in ("commentCreate", "commentReply", "commentResolve", "commentDelete",
                   "commentSeen", "commentPromote"):
            self.assertIn('"%s"' % op, src)


class ExchangeLatchReplacedThePushCount(unittest.TestCase):
    """T102 (the user 2026-08-26): the push-count settle (settledPushes / _comment_settle_step) is
    RETIRED — it was a proxy for the real ending event, and it broke both ends: the fork-birth
    frames read all-quiet so the create-window pulse died until the CLI booted, and any stall in
    the 0→1→2 stepping parked the pulse green forever. The client's pulse is exchange-scoped now —
    latched at the send gesture, cleared by the agent's reply RECORD arriving in msgs — so the
    frame carries the exchange's records (msgs) and no per-push counter."""

    def test_the_push_count_is_gone_root_and_branch(self):
        src = open(os.path.join(os.path.dirname(HERE), "kernel", "kernel.py")).read()
        self.assertNotIn("settledPushes", src.replace("settledPushes — is RETIRED", ""),
                         "no counter rides the frame (the tombstone comment is the one mention)")
        self.assertNotIn("_comment_settle_step", src)
        ui = open(os.path.join(os.path.dirname(HERE), "ui", "webview", "comments.ts")).read()
        self.assertNotIn("settledPushes", ui)
        self.assertNotIn("SETTLE_CONFIRM_PUSHES", ui)

    def test_the_frame_still_carries_the_exchange_records_and_epoch(self):
        src = open(os.path.join(os.path.dirname(HERE), "kernel", "kernel.py")).read()
        self.assertIn('"sinceEpoch": since_ms,', src)
        self.assertIn('"msgs": msgs, "events": events', src)


# ── the /fork-comment + /fork-promote route brains ───────────────────────────────────────────────
# Parallel review dispatch (the user 2026-08-31): an external local tool (the Obsidian track-changes
# plugin) POSTs /fork-comment to open a transcript-comment-STYLE thread on a session — TIP-anchored
# (no highlighted record exists on that door) with the caller's own text as the opening message,
# VERBATIM — and /fork-promote to break a thread out by forkId alone. The brains are factored from
# the routes (_compact_request precedent), so these run without HTTP.

class ForkCommentRoutes(CommentBase):
    def setUp(self):
        super().setUp()
        self.be = FakeBackend()
        self._saved_backend_for = km.Sessions.backend_for
        self._saved_live = km.Sessions.live
        self._saved_ready = km._sdk_ready
        self._saved_sessions = km._sessions
        self._saved_push_now = km._push_session_now
        km.Sessions.backend_for = staticmethod(lambda sid: self.be)
        km.Sessions.live = staticmethod(lambda: {})   # hermetic: never consult the box's real tmux
        km._sdk_ready = lambda: True
        # km.NAMES is bound at import (module-scope constant) — _rebind_state moves only jd's copy,
        # so _name_of would read the import-time root and miss the per-test registry entry
        self._saved_names = km.NAMES
        km.NAMES = jd.NAMES
        p = self._write(PARENT, self._parent_records())
        (jd.NAMES / PARENT).write_text("parent\t%s" % self.cdir)
        km._sessions = lambda now, window=None, forks=True: [
            {"sid": PARENT, "name": "parent", "path": str(p), "mtime": self.now}]
        km._push_session_now = lambda sid: None

    def tearDown(self):
        km.Sessions.backend_for = self._saved_backend_for
        km.Sessions.live = self._saved_live
        km.NAMES = self._saved_names
        km._sdk_ready = self._saved_ready
        km._sessions = self._saved_sessions
        km._push_session_now = self._saved_push_now
        for f in ("comment-model", "comment-effort", "comment-fast"):
            try:
                (km.jd.STATE / f).unlink()
            except OSError:
                pass
        km.jd._state_cache.clear()
        super().tearDown()

    OPENER = ("Please review the tracked edits in this note and reply in the review thread.\n\n"
              "Use the thread id t-123 with every reply.")

    def test_fork_comment_creates_a_tip_thread_with_the_text_verbatim(self):
        res = km._fork_comment_request({"id": PARENT, "text": self.OPENER,
                                        "meta": {"thread": "t-123", "note": "notes/demo.md"}})
        self.assertTrue(res.get("ok"), res)
        tid = res["forkId"]
        self.assertEqual([c[0] for c in self.be.calls], ["fork", "connect", "send"])
        self.assertEqual(self.be.calls[0][3], "", "TIP fork — no highlighted record on this door")
        self.assertEqual(self.be.calls[0][5], PARENT, "born as a threadOf fork, never a board session")
        self.assertEqual(self.be.sent[0][1], self.OPENER,
                         "the caller authored the whole prompt — sent verbatim, never re-framed")
        self.assertFalse(self.be.sent[0][1].startswith(km._COMMENT_FRAME_HEAD))
        row = km._comment_thread(PARENT, tid)
        self.assertEqual(row["status"], "open")
        self.assertEqual(row["cutUuid"], "")
        self.assertEqual(row["anchorUuid"], "")
        self.assertEqual(row["meta"], {"thread": "t-123", "note": "notes/demo.md"})
        self.assertEqual(row["exact"], "notes/demo.md",
                         "the popover's about-line names the note under review")
        self.assertEqual(row["name"], "parent-comment-1", "the standard autoname idiom")

    def test_fork_comment_thread_reaches_the_popover_frame(self):
        res = km._fork_comment_request({"id": PARENT, "text": self.OPENER, "meta": {"thread": "t-1"}})
        fr = km._comments_frame(PARENT)
        self.assertEqual([t["tid"] for t in fr["threads"]], [res["forkId"]],
                         "a dispatched review thread is a normal popover thread")

    def test_fork_comment_resolves_a_live_session_name(self):
        km.Sessions.live = staticmethod(lambda: {PARENT: {}})
        res = km._fork_comment_request({"name": "parent", "text": self.OPENER})
        self.assertTrue(res.get("ok"), res)

    def test_fork_comment_applies_the_default_comment_settings(self):
        km.jd.STATE.mkdir(parents=True, exist_ok=True)
        (km.jd.STATE / "comment-model").write_text("haiku")
        km.jd._state_cache.clear()
        km._fork_comment_request({"id": PARENT, "text": self.OPENER})
        self.assertEqual(self.be.forked_meta[0], "haiku",
                         "the gear trio governs these forks exactly like dialog-created threads")

    def test_fork_comment_refusals_are_honest(self):
        self.assertEqual(km._fork_comment_request(None)["_status"], 400)
        self.assertEqual(km._fork_comment_request({"id": PARENT})["_status"], 400)
        self.assertEqual(km._fork_comment_request({"id": PARENT, "text": "  "})["_status"], 400)
        res = km._fork_comment_request({"name": "no-such-session", "text": self.OPENER})
        self.assertEqual(res["_status"], 404)
        self.assertIn("no session named", res["error"])
        km.Sessions.backend_for = staticmethod(lambda sid: object())   # tmux: no fork machinery
        res = km._fork_comment_request({"id": PARENT, "text": self.OPENER})
        self.assertNotIn("_status", res)
        self.assertIn("tmux", res["error"])

    def test_fork_comment_holds_the_postal_isolation_gate(self):
        saved_shaped, saved_iso = km._postal_shaped, km._postal_isolated
        km._postal_shaped, km._postal_isolated = (lambda t: True), (lambda s: True)
        try:
            res = km._fork_comment_request({"id": PARENT, "text": self.OPENER})
        finally:
            km._postal_shaped, km._postal_isolated = saved_shaped, saved_iso
        self.assertFalse(res.get("ok"))
        self.assertIn("isolation", res["error"])
        self.assertEqual(self.be.calls, [], "refused before any fork")

    def test_fork_comment_forwards_a_remote_target_and_passes_the_forkId_through(self):
        saved_host, saved_fwd = km._host_for_sid, km._remote_forward
        sent = []
        km._host_for_sid = lambda sid: {"host": "TESTHOST", "local_port": 1, "token": ""}
        km._remote_forward = lambda r, path, body: sent.append((path, body)) or {"ok": True, "forkId": "far-tid"}
        try:
            res = km._fork_comment_request({"id": PARENT, "text": self.OPENER, "meta": {"note": "n.md"}})
            self.assertEqual(res, {"ok": True, "forkId": "far-tid"})
            self.assertEqual(sent, [("/fork-comment", {"id": PARENT, "text": self.OPENER,
                                                       "meta": {"note": "n.md"}})])
            km._remote_forward = lambda r, path, body: None   # the tunnel didn't answer — say so
            res = km._fork_comment_request({"id": PARENT, "text": self.OPENER})
            self.assertFalse(res.get("ok"))
            self.assertIn("TESTHOST", res["error"])
        finally:
            km._host_for_sid, km._remote_forward = saved_host, saved_fwd
        self.assertEqual(self.be.calls, [], "a remote target never forks locally")

    def _promotable(self, tid):
        t = self.now - 200
        self._write(tid, [uline(t, "opener", "cu1"), aline(t + 10, "reply", "ca1", parent="cu1")])
        (jd.SDKDIR / (tid + ".json")).write_text(json.dumps(
            {"sid": tid, "name": "thread-x", "cwd": self.cdir,
             "lastSid": tid, "alive": True, "threadOf": PARENT}))

    def test_fork_promote_materializes_under_the_threads_own_name(self):
        tid = km._fork_comment_request({"id": PARENT, "text": self.OPENER})["forkId"]
        self._promotable(tid)
        res = km._fork_promote_request({"forkId": tid})
        self.assertEqual(res, {"ok": True, "name": "parent-comment-1"})
        self.assertIn(("promote", tid, "parent-comment-1"), self.be.calls)
        self.assertEqual(km._comment_thread(PARENT, tid)["status"], "promoted")
        again = km._fork_promote_request({"forkId": tid})
        self.assertEqual(again, {"ok": True, "name": "parent-comment-1"},
                         "already promoted = idempotent success, never a refusal")

    def test_fork_promote_refusals_ride_non_2xx(self):
        # the shipped caller reads ANY 2xx JSON as success, so every refusal must carry a status
        self.assertEqual(km._fork_promote_request(None)["_status"], 400)
        self.assertEqual(km._fork_promote_request({})["_status"], 400)
        self.assertEqual(km._fork_promote_request({"forkId": "not-a-thread"})["_status"], 404)
        tid = km._fork_comment_request({"id": PARENT, "text": self.OPENER})["forkId"]
        res = km._fork_promote_request({"forkId": tid})   # no transcript yet → promote refuses
        self.assertEqual(res["_status"], 409)
        self.assertFalse(res.get("ok"))

    def test_fork_promote_scans_attached_remotes_for_an_unknown_forkId(self):
        saved_remotes, saved_fwd = km._remotes, km._remote_forward
        asked = []
        km._remotes = {"TESTHOST": {"host": "TESTHOST", "local_port": 1, "token": ""}}
        km._remote_forward = lambda r, path, body: asked.append((r["host"], path, body)) or {"ok": True, "name": "far-name"}
        try:
            res = km._fork_promote_request({"forkId": "far-tid"})
        finally:
            km._remotes, km._remote_forward = saved_remotes, saved_fwd
        self.assertEqual(res, {"ok": True, "name": "far-name"})
        self.assertEqual(asked, [("TESTHOST", "/fork-promote", {"forkId": "far-tid"})])

    def test_routes_are_wired_and_pop_the_status(self):
        src = open(os.path.join(os.path.dirname(HERE), "kernel", "kernel.py")).read()
        self.assertIn('if u.path in ("/fork-comment", "/fork-promote"):', src)
        self.assertIn('res = (_fork_comment_request(b) if u.path == "/fork-comment"', src)
        self.assertIn('return self._send(res.pop("_status", 200), json.dumps(res), "application/json")', src)


if __name__ == "__main__":
    unittest.main()
