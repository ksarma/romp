#!/usr/bin/env python3
"""Every copy in the kernel's queued group carries an identity. Upstream's T252c minted that identity in the
SDK backend (a kernel-side qid per copy, a fed ledger pairing each landing, queueMeta in the registry mirror);
the fork's #385 mints it at the client's press (send_id: the queue entry's, the echo's _send_id, the landed
record's sendIds). The upmerge4 fold kept the fork's send id as the ONE identity and did not take upstream's
backend mechanism beside it (R6; upmerge4-notes sdk-code.md DECISION 4 and the ui-code ruling), so this
module, upstream's, keeps what the resolved code still does:

  * the one T252c behaviour the fold re-expressed on the send id: by text alone, the second of two identical
    sends hid the loss of the first across a kernel death (it was neither re-delivered nor flagged); with ids
    on both sides the boot reseed sees the loss and re-delivers the lost copy under its own id
    (_echo_queued_in; upstream's test translated onto send ids);
  * a fed copy stranded by its client's death goes back to the head of the queue as the entry it was, id
    intact (_reconcile_stranded re-heads the popped entries themselves);
  * the tmux route: the CLI's queue-operation records carry timestamps but no ids, so each copy carries its
    enqueue stamp and no id, and the kernel ships the stamp on the queued copy on its own (the kernel's
    tmux-side _pending_queued_meta; the SDK backend has no such surface).

Every other test upstream's module carried pinned the mechanism the fold did not take (pending_queued_meta,
_pop_for_feed_locked, qid_for_landing, qids_for_landing, forget_fed, pending_meta, _fed_meta,
queue_meta_from_reg, qid/qids on chat events). Each is retired below with a one-line note naming the fork's
test that pins the same behaviour on the send id: tests/test_queued_sends_not_fused.py,
tests/test_queued_sends_kernel.py, tests/test_kernel_send_park.py, tests/test_sdk_echo_durability.py.

SYNTHETIC fixtures only: a private synthetic sid, the notes-api demo world, hostname-free.
"""
import json
import os
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
km = load_source("romp_kernel_qid", os.path.join(BIN, "romp-kernel"))
sb = load_source("romp_sdk_backend_qid", os.path.join(BIN, "romp_sdk_backend.py"))

SID = "5a6b7c8d-1e2f-4a3b-9c4d-5e6f7a8b9c0d"   # private synthetic sid (goal-store fixtures rule)
T0 = 1_800_000_000


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


class _World:
    """A real SdkBackend bound as the kernel's backend, owning SID, with a thread-less SdkSession, plus the
    discovery a build_session needs (names/ + projects/<cdir>/<SID>.jsonl under a hermetic state root)."""

    def __init__(self):
        self.td = tempfile.TemporaryDirectory()
        root = Path(self.td.name)
        (root / "sdk").mkdir()
        self.cwd = root / "proj"; self.cwd.mkdir()
        os.environ["CLAUDE_CONFIG_DIR"] = str(root / "claude")
        self.tpath = Path(sb.transcript_path(str(self.cwd), SID))
        self.tpath.parent.mkdir(parents=True, exist_ok=True)
        self.tpath.write_text("")
        self.be = sb.SdkBackend(str(root), "/bin/true", lambda *a, **k: None)
        reg = {"sid": SID, "name": "web", "mode": "acceptEdits", "alive": True, "cwd": str(self.cwd), "lastSid": SID}
        sb.write_reg(self.be.state_dir, SID, reg)
        self.s = sb.SdkSession(self.be, dict(reg))
        # _ensure hands a send to THIS session only while its thread is alive (a dead one is respawned and
        # the spawn dies on the stand-in binary): park a daemon thread in its place for the test's life
        import threading
        self._park = threading.Event()
        self.s.thread = threading.Thread(target=self._park.wait, daemon=True)
        self.s.thread.start()
        self.be.sessions[SID] = self.s
        self.saved_sdk = km._sdk
        km._sdk = lambda: self.be
        proj = root / "projects"
        names = root / "names"; names.mkdir()
        (names / SID).write_text("web\t%s\t#abcdef\n" % str(self.cwd))
        self.saved = (km.jd.NAMES, km.jd.PROJECTS, km.jd.CAPDIR, km.jd.ARCHDIR, km.jd.GOALDIR, km.jd.STATE,
                      km.NAMES, km._tmux_sessions, km._GLOBAL_CLAUDE_MD)
        km.jd.NAMES, km.jd.PROJECTS = names, proj
        km.jd.CAPDIR, km.jd.ARCHDIR, km.jd.GOALDIR = root / "captions", root / "archive", root / "goals"
        km.jd.STATE = root
        km.NAMES = names
        km._GLOBAL_CLAUDE_MD = root / "no-global-claude.md"
        self.now = int(time.time())
        self.tm = {SID: {"state": "working", "since": self.now - 100, "model": "", "effort": "",
                         "context": None, "compactPct": None, "color": None}}
        km._tmux_sessions = lambda: self.tm
        km._chat_fold.clear(); km._parse_cache.clear()
        km._PATH_LINK_CACHE.clear(); km._SPACE_PATH_CACHE.clear()
        km._postal_index_memo[0] = None
        if isinstance(km.jd._discover_cache, dict):
            km.jd._discover_cache.clear()
        # the build_session transcript lives under the kernel's project dir for the cwd
        self.kpath = proj / km.jd._proj_dir(str(self.cwd)).name / (SID + ".jsonl")
        self.kpath.parent.mkdir(parents=True, exist_ok=True)

    def close(self):
        self._park.set()
        (km.jd.NAMES, km.jd.PROJECTS, km.jd.CAPDIR, km.jd.ARCHDIR, km.jd.GOALDIR, km.jd.STATE,
         km.NAMES, km._tmux_sessions, km._GLOBAL_CLAUDE_MD) = self.saved
        km._sdk = self.saved_sdk
        km._chat_fold.clear(); km._parse_cache.clear()
        os.environ.pop("CLAUDE_CONFIG_DIR", None)
        import shutil
        shutil.rmtree(self.td.name, ignore_errors=True)   # a backend writer (the echo mirror) may still be finishing

    def write(self, recs, shift=None):
        # discovery keys on the real clock: shift the fixture to "just now"; a landing that must pair with a
        # feed made during the test is written AT the clock (shift=now-T0), since the CLI's enqueue stamp is
        # never earlier than the feed that handed it the text
        shift = (self.now - 600) - T0 if shift is None else shift
        out = []
        for r in recs:
            r = dict(r)
            r["timestamp"] = iso(datetime.strptime(r["timestamp"], "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=timezone.utc).timestamp() + shift)
            out.append(r)
        self.kpath.write_text("".join(json.dumps(r) + "\n" for r in out))
        return shift

    def build(self):
        km._chat_fold.clear(); km._parse_cache.clear()
        return km.build_session(SID, self.now, self.tm)


def uline(t, text, uuid, parent=None):
    return {"type": "user", "timestamp": iso(t), "uuid": uuid, "parentUuid": parent, "promptSource": "sdk",
            "sessionId": SID, "message": {"role": "user", "content": text}}


def aline(t, text, uuid, parent, tools=(), stop="end_turn"):
    content = [{"type": "text", "text": text}] if text else []
    for i, n in enumerate(tools):
        content.append({"type": "tool_use", "id": "tu_%s_%d" % (uuid, i), "name": n, "input": {"command": "true"}})
    return {"type": "assistant", "timestamp": iso(t), "uuid": uuid, "parentUuid": parent, "sessionId": SID,
            "message": {"role": "assistant", "content": content, "stop_reason": stop}}


def trline(t, tool_use_id, uuid, parent):
    return {"type": "user", "timestamp": iso(t), "uuid": uuid, "parentUuid": parent, "sessionId": SID,
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_use_id, "content": "ok"}]}}


RUNNING = [uline(T0, "tighten the notes-api search", "u1"), aline(T0 + 10, "Done.", "a1", "u1"),
           uline(T0 + 39, "drop the unused import", "u2", "a1"),
           aline(T0 + 41, "Removing it.", "a2", "u2", tools=("Bash",), stop="tool_use"), trline(T0 + 50, "tu_a2_0", "tr1", "a2")]


def _ids(entries):
    """(text, send id) per queue entry: a _QueueText carries the client's id, a bare text carries none."""
    return [(str(q), getattr(q, "send_id", "")) for q in entries]


# TheSdkQueueCarriesIds (upstream's six tests) retired: every one read the backend mechanism the fold did not take
# (R6, sdk-code.md DECISION 4). The fork's send id pins the same behaviour in tests/test_queued_sends_not_fused.py:
#   - send mints the id before the enqueue and the echo shares it -> test_the_send_id_rides_the_queue_entry_its_mirror_and_the_echo
#     (the client mints the id at the press; send(send_id=) puts it on the entry and the echo);
#   - unqueue keeps the ids aligned -> test_a_cancel_removes_exactly_its_own_entry_of_two_wearing_the_same_words;
#   - a copy the backend queued itself carries no id, a restored queue keeps what its mirror carries ->
#     the mirror assertions of the same test and QueueEntryWire.test_round_trip_keeps_both_ids_and_the_bare_shapes;
#   - the feed's fed ledger and qid_for_landing / qids_for_landing / forget_fed: no fed ledger on the fork; the landed
#     record is paired by the echo's own id (kernel._note_send_landings) ->
#     TheKernelCarriesTheId.test_a_landed_record_is_stamped_with_the_ids_of_every_send_it_landed and
#     tests/test_queued_sends_kernel.py BuildSessionStampsTheIds.


class TheChatCarriesTheIds(unittest.TestCase):
    """The kernel's queued group, read through build_session. The fork's wire is `texts[].sendId` on a queued
    copy and `sendIds` on the echo and the landed record, pinned in tests/test_queued_sends_kernel.py
    (BuildSessionStampsTheIds); upstream's qid/qids tests are retired (R6, DECISION 4):
      - the queued group and the landed atom share the copy's id ->
        test_the_queued_chips_carry_the_id_of_the_entry_or_the_parked_op_they_stand_for and
        test_the_record_that_landed_the_send_carries_its_id_and_a_folded_record_every_id;
      - an intermediate build between the feed and the landing keeps the pairing -> the fork pairs by the echo's
        own send id, not a fed ledger: test_an_echo_still_in_flight_carries_its_send_id_on_its_user_event;
      - a two-block record carries both copies' ids -> the folded-record case of the landing test above;
      - ids ride only when each one sits beside its own text -> mechanism-less on the fork: the id rides the
        entry itself, so no second read of the queue can misalign it;
      - a parked copy carries no id until it reaches the backend -> the fork's parked op carries the send id as
        its fifth slot from the press (ParkedSendCarriesItsId), the opposite design.
    What stays is the tmux route's stamp, which the kernel ships whatever backend the copy came from."""

    def setUp(self):
        self.w = _World()

    def tearDown(self):
        self.w.close()
        km._pending_ops.pop(SID, None)

    def test_a_stamp_without_an_id_rides_the_queued_copy_too(self):
        # the tmux route's copies carry an enqueue stamp and no id (TheTmuxQueueCarriesStamps): the group ships the
        # stamp on its own (it rode only beside an id before upstream's third review). The read is the kernel's
        # hasattr-guarded pending_queued_meta (kept for the tmux route, fixer-rules decision f); a stand-in surface
        # on the SDK backend, which has none, exercises it
        self.w.write(RUNNING)
        self.w.s.enqueue("stamped only")
        self.w.be.pending_queued_meta = lambda sid: [{"md": "stamped only", "qid": None, "qts": 1_700_000_000_000}]
        m = self.w.build()
        q = [e for e in m["events"] if e.get("kind") == "queued"]
        self.assertEqual([(t["md"], t.get("qid"), t.get("qts")) for t in q[0]["texts"]], [("stamped only", None, 1_700_000_000_000)])


class TheTmuxQueueCarriesStamps(unittest.TestCase):
    def test_each_copy_carries_its_enqueue_stamp_and_no_id_since_nothing_on_this_route_could_share_one(self):
        td = tempfile.TemporaryDirectory()
        p = Path(td.name) / "t.jsonl"
        recs = [{"type": "queue-operation", "operation": "enqueue", "content": "one", "timestamp": iso(T0 + 5)},
                {"type": "queue-operation", "operation": "enqueue", "content": "two", "timestamp": iso(T0 + 9)},
                {"type": "queue-operation", "operation": "dequeue", "timestamp": iso(T0 + 12)}]
        p.write_text("".join(json.dumps(r) + "\n" for r in recs))
        km._queued_parse_cache.clear()
        self.assertEqual(km._pending_queued(str(p)), ["two"])
        meta = km._pending_queued_meta(str(p))
        self.assertEqual([m["md"] for m in meta], ["two"])
        self.assertEqual(meta[0]["qts"], (T0 + 9) * 1000)
        # no id: the tmux echo is minted before the CLI writes its enqueue record and the landing carries nothing,
        # so an id only the ledger copy wore would make the chat reject the echo as another send's (review)
        self.assertIsNone(meta[0]["qid"])
        td.cleanup()


class IdentitySurvivesTheKernelsDeath(unittest.TestCase):
    """A kernel restart re-seeds the echo mirror and rebuilds the queue from the registry. On the fork the send
    id rides both mirrors (reg['queue'] entries as {"text","sendId"}, reg['echoes'] rows as sendId), so the
    restored entry and the reseeded echo still share the client's id (tests/test_queued_sends_kernel.py
    TheIdSurvivesTheRestartMirror). What this class keeps is the loss reading upstream's third review added
    and the fold re-expressed on the send id (_echo_queued_in): a fed copy the dead CLI was holding is seen
    lost even when a same-text copy survives in the queue, and comes back under its own id.

    Retired here (R6, DECISION 4), each pinned on the send id elsewhere:
      - the restored queue and the reseeded echo keep the copy's id, and the landing pairs with it ->
        TheIdSurvivesTheRestartMirror.test_the_reseeded_echo_and_the_re_queued_entry_carry_the_id and
        BuildSessionStampsTheIds (tests/test_queued_sends_kernel.py);
      - a fed copy the dead CLI was holding is re-delivered under its own id -> the same mirror test's re-queue
        assertion, and the identical-sends test below (its one-send case);
      - a re-delivered copy joins a surviving identified queue with both ids intact -> the identical-sends test
        below, whose survivor and re-delivered copy wear the same words;
      - a dead spawn's re-delivery into a LIVE session carries the id (and cleared upstream's fed ledger) ->
        tests/test_queued_sends_not_fused.py test_a_redelivered_send_keeps_its_id_on_the_live_arm_as_on_the_reg_arm;
        no fed ledger on the fork.
    """

    def setUp(self):
        self.w = _World()
        self.w.write(RUNNING, shift=self.w.now - T0)   # at the clock: a landing must follow the feed in time
        self._parks = []

    def tearDown(self):
        for park in self._parks:
            park.set()
        self.w.close()

    def _restart(self):
        """The kernel dies and boots: a fresh backend over the same state root re-seeds the echo mirror (its
        __init__), and the session is rebuilt from its registry record, the way the boot reconcile seeds it."""
        import threading
        self.w._park.set()
        self.w.be.sessions.pop(SID, None)
        be2 = sb.SdkBackend(self.w.be.state_dir, "/bin/true", lambda *a, **k: None)
        s2 = sb.SdkSession(be2, dict(sb.read_reg(be2.state_dir, SID)))
        park = threading.Event(); self._parks.append(park)
        s2.thread = threading.Thread(target=park.wait, daemon=True); s2.thread.start()
        be2.sessions[SID] = s2
        km._sdk = lambda: be2
        return be2, s2

    def test_the_lost_first_of_two_identical_sends_is_seen_lost_beside_the_queued_second(self):
        # upstream's T252c third-review case translated onto the fork's send id (sdk-code.md DECISION 4): two
        # sends of the same words under distinct client ids
        self.assertTrue(self.w.be.send(SID, "ok", send_id="a"))
        self.assertTrue(self.w.be.send(SID, "ok", send_id="b"))
        self.assertEqual(_ids(self.w.be.pending_queued(SID)), [("ok", "a"), ("ok", "b")])
        with self.w.s._lock:
            self.w.s._pending.pop(0)                  # the CLI took the first copy (the feed's pop in inputs())
        self.w.s._persist_queue()                     # the mirror holds the second, and both echoes
        be2, s2 = self._restart()                     # the first died with the CLI; by TEXT it looked queued
        self.assertEqual(_ids(be2.pending_queued(SID)), [("ok", "b"), ("ok", "a")],
                         "the survivor, then the lost copy re-delivered under its own id")
        self.assertEqual(sorted((a.get("_send_id"), bool(a.get("dropped"))) for a in be2.live_atoms(SID) if a.get("_echo_text")),
                         [("a", False), ("b", False)], "neither echo is flagged: one is queued, the other re-queued")

    def test_a_stranded_fed_copy_re_heads_the_queue_with_its_id(self):
        # translated from upstream's pending_meta / _fed_meta reading (DECISION 4): the fork re-heads the popped
        # entry itself (_reconcile_stranded), so the id it wore rides back to the head with it
        self.assertTrue(self.w.be.send(SID, "go on", send_id="a"))
        self.assertTrue(self.w.be.send(SID, "then this", send_id="b"))
        s = self.w.s
        with s._lock:
            item = s._pending.pop(0)                  # the feed's pop, by hand
            s._inflight_texts.append(item); s.inflight = 1   # fed to a client that is now gone
        s.resume_sid = None                           # no conversation materialised: the re-head branch
        s._reconcile_stranded()
        self.assertEqual(_ids(s.pending()), [("go on", "a"), ("then this", "b")],
                         "the fed copy is back at the head under its own id")
        self.assertEqual(s.inflight, 0)


# TheQueueMirrorAlignsByPosition (upstream's queue_meta_from_reg) retired: the fork's mirror carries the id ON each
# entry ({"text","sendId"}, _queue_wire / _queue_text), so a restore reads it off the entry and nothing aligns a
# side list by position (R6, DECISION 4). Pinned by tests/test_queued_sends_not_fused.py QueueEntryWire.


if __name__ == "__main__":
    unittest.main()
