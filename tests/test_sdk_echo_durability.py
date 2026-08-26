#!/usr/bin/env python3
"""An SDK input echo is the ONLY visible record of a send the transcript hasn't caught up on — since
queued sends forward into the CLI mid-turn (2026-07-17) there is a window where a message is neither
queued nor landed, and the echo must own it (the user 2026-07-20: a reply sat invisible in the chat,
and one message was silently LOST across a kernel restart with no trace anywhere). Four durability
guarantees, each pinned here:
  1. the live-tail overflow cap never evicts an echo (work atoms are disposable; echoes aren't),
  2. the genuine-human-turn floor retires only PATH-BEARING echoes (the image-extraction case whose
     text-match structurally fails) — a plain-text echo prunes only by its own text landing, and a
     dropped send's echo PERSISTS so the loss shows (the tmux echo's semantics),
  3. unlanded echoes mirror to the registry (reg['echoes']) and reseed on backend construction, so a
     kernel restart cannot wipe the only evidence of an in-flight send,
  4. an echo that survives its holder is MARKED dropped at the event that orphaned it (boot reseed /
     fresh CLI spawn), so persistence reads as "never delivered", not as delivered history (the user
     2026-07-29: a two-day-old lost send kept resurfacing mid-chat, posing as an ordinary bubble).
SYNTHETIC fixtures only."""
import os
import tempfile
import time
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
sb = SourceFileLoader("romp_sdk_backend_echo", os.path.join(BIN, "romp_sdk_backend.py")).load_module()

SID = "11111111-2222-3333-4444-555555555555"


def _echo(text, t=1000, key="echo:k1"):
    return key, {"type": "user", "uuid": key, "session_id": SID, "t": t, "parentUuid": None,
                 "author": "human", "_echo_text": text,
                 "message": {"role": "user", "content": [{"type": "text", "text": text}]}}


def _work(i):
    return "w%d" % i, {"type": "assistant", "uuid": "w%d" % i, "session_id": SID, "t": 2000 + i,
                       "message": {"role": "assistant", "content": [{"type": "text", "text": "x"}]}}


class OverflowCapSparesEchoes(unittest.TestCase):
    def test_echo_survives_a_work_atom_flood(self):
        d = {}
        k, e = _echo("the in-flight reply")
        d[k] = e
        for i in range(sb.LIVE_TAIL_CAP + 60):
            wk, w = _work(i)
            d[wk] = w
            sb._evict_live_overflow(d)
        self.assertIn(k, d, "the echo must survive the cap — it is the send's only record")
        self.assertLessEqual(len(d), sb.LIVE_TAIL_CAP)

    def test_all_echo_pathology_still_bounds_memory(self):
        d = {}
        for i in range(sb.LIVE_TAIL_CAP + 20):
            k, e = _echo("msg %d" % i, t=1000 + i, key="echo:%d" % i)
            d[k] = e
        sb._evict_live_overflow(d)
        self.assertLessEqual(len(d), sb.LIVE_TAIL_CAP)


class FloorOnlyRetiresPathBearingEchoes(unittest.TestCase):
    def _backend(self):
        return sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)

    def test_plain_text_echo_survives_a_later_human_turn(self):
        be = self._backend()
        k, e = _echo("please refactor the parser")
        be._live[SID] = dict([(k, e)])
        be.prune_live(SID, tx_uuids=set(), tx_user_texts=set(), human_floor=e["t"] + 100)
        self.assertIn(k, be._live.get(SID, {}),
                      "a plain echo must not be floored away — its message may still be inside the CLI")

    def test_path_bearing_echo_retires_on_the_floor(self):
        # the image-extraction case: the landed record's text can never match, so the floor is the
        # only retire — exactly the 2026-06-25 screenshots-piling-up semantics, now scoped to it
        be = self._backend()
        k, e = _echo("look at ~/Screenshots/shot.png please")
        be._live[SID] = dict([(k, e)])
        be.prune_live(SID, tx_uuids=set(), tx_user_texts=set(), human_floor=e["t"] + 100)
        self.assertNotIn(SID, be._live, "path-bearing echo floors away once a human turn postdates it")

    def test_text_landing_still_prunes_any_echo(self):
        be = self._backend()
        k, e = _echo("please refactor the parser")
        be._live[SID] = dict([(k, e)])
        be.prune_live(SID, tx_uuids=set(), tx_user_texts={"please refactor the parser"}, human_floor=0)
        self.assertNotIn(SID, be._live)

    def test_path_bearing_predicate(self):
        self.assertTrue(sb._path_bearing("see /tmp/x.png"))
        self.assertTrue(sb._path_bearing("~/notes/todo.md is stale"))
        self.assertFalse(sb._path_bearing("just a plain reply, and/or nothing else"))
        self.assertFalse(sb._path_bearing(""))


class EchoesSurviveARestart(unittest.TestCase):
    def test_persist_then_reseed_round_trip(self):
        state = tempfile.mkdtemp()
        be = sb.SdkBackend(state, "/bin/true", lambda *a, **k: None)
        sb.write_reg(be.state_dir, SID, {"sid": SID, "alive": True})
        k, e = _echo("message in flight across the restart")
        be._live[SID] = dict([(k, e)])
        be._persist_echoes(SID)
        reg = sb.read_reg(be.state_dir, SID)
        self.assertEqual([x["text"] for x in reg.get("echoes") or []],
                         ["message in flight across the restart"])
        # "kernel restart": a fresh backend over the same state dir reseeds the echo into its live tail
        be2 = sb.SdkBackend(state, "/bin/true", lambda *a, **k: None)
        atoms = be2.live_atoms(SID)
        self.assertEqual([a.get("_echo_text") for a in atoms],
                         ["message in flight across the restart"])
        self.assertEqual(atoms[0].get("author"), "human")

    def test_landing_empties_the_mirror(self):
        state = tempfile.mkdtemp()
        be = sb.SdkBackend(state, "/bin/true", lambda *a, **k: None)
        sb.write_reg(be.state_dir, SID, {"sid": SID, "alive": True})
        k, e = _echo("lands soon")
        be._live[SID] = dict([(k, e)])
        be._persist_echoes(SID)
        be.prune_live(SID, tx_uuids=set(), tx_user_texts={"lands soon"}, human_floor=0)
        self.assertEqual(sb.read_reg(be.state_dir, SID).get("echoes"), [],
                         "a landed echo leaves the restart mirror too")

    def test_command_feedback_is_never_mirrored(self):
        state = tempfile.mkdtemp()
        be = sb.SdkBackend(state, "/bin/true", lambda *a, **k: None)
        sb.write_reg(be.state_dir, SID, {"sid": SID, "alive": True})
        be._live[SID] = {"cmd:1": {"type": "user", "uuid": "cmd:1", "t": 5, "command": "/model",
                                   "_echo_text": "/model opus", "author": "human",
                                   "message": {"role": "user", "content": [{"type": "text", "text": "/model opus"}]}}}
        be._persist_echoes(SID)
        self.assertEqual(sb.read_reg(be.state_dir, SID).get("echoes"), [],
                         "a stale /model confirmation must not replay after a restart")


class DroppedSendsAnnounceThemselves(unittest.TestCase):
    """Guarantee 4 (the user 2026-07-29): an echo that survives its holder is marked `dropped` at the
    exact event that orphaned it — the boot reseed, or a fresh CLI spawning — so the chat can render
    "never delivered" instead of a sent-looking bubble posing as history. A two-day-old lost send kept
    resurfacing mid-chat, hopping turns as new ones landed, its stale timestamp reading as a glitch:
    durable BY DESIGN, but illegible. The marking is self-correcting (a landed text still prunes the
    echo, flag and all) and rides the registry mirror across further restarts."""

    def _backend(self, state=None):
        return sb.SdkBackend(state or tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)

    def test_boot_reseed_marks_an_unqueued_echo_dropped(self):
        state = tempfile.mkdtemp()
        be = self._backend(state)
        sb.write_reg(be.state_dir, SID, {"sid": SID, "alive": True})
        k, e = _echo("the send the dead CLI was holding")
        be._live[SID] = dict([(k, e)])
        be._persist_echoes(SID)
        be2 = self._backend(state)               # "kernel restart": nothing re-delivers this text
        atoms = be2.live_atoms(SID)
        self.assertTrue(atoms and atoms[0].get("dropped"),
                        "a reseeded echo with no queue entry has provably lost its message")
        self.assertTrue((sb.read_reg(state, SID).get("echoes") or [{}])[0].get("dropped"),
                        "the flag rides the mirror, so the NEXT restart keeps the verdict")

    def test_boot_reseed_spares_an_echo_still_in_the_queue(self):
        state = tempfile.mkdtemp()
        be = self._backend(state)
        sb.write_reg(be.state_dir, SID, {"sid": SID, "alive": True,
                                         "queue": ["still queued across the restart"]})
        k, e = _echo("still queued across the restart")
        be._live[SID] = dict([(k, e)])
        be._persist_echoes(SID)
        be2 = self._backend(state)               # boot reconcile will re-deliver the queue → not lost
        atoms = be2.live_atoms(SID)
        self.assertTrue(atoms and not atoms[0].get("dropped"),
                        "a queued send is in flight, not lost — it must not read as never-delivered")

    def test_spawn_marking_spares_the_pending_queue(self):
        be = self._backend()
        sb.write_reg(be.state_dir, SID, {"sid": SID, "alive": True})
        k1, e1 = _echo("orphaned by the respawn", key="echo:a")
        k2, e2 = _echo("delivered to the fresh CLI", t=1001, key="echo:b")
        be._live[SID] = {k1: e1, k2: e2}
        be._mark_dropped_echoes(SID, ["delivered to the fresh CLI"])
        d = be._live[SID]
        self.assertTrue(d[k1].get("dropped"))
        self.assertFalse(d[k2].get("dropped"))

    def test_spawn_marking_ignores_command_feedback(self):
        be = self._backend()
        sb.write_reg(be.state_dir, SID, {"sid": SID, "alive": True})
        be._live[SID] = {"cmd:1": {"type": "user", "uuid": "cmd:1", "t": 5, "command": "/model",
                                   "_echo_text": "/model opus", "author": "human",
                                   "message": {"role": "user", "content": [{"type": "text", "text": "/model opus"}]}}}
        be._mark_dropped_echoes(SID, [])
        self.assertFalse(be._live[SID]["cmd:1"].get("dropped"),
                         "command feedback is not a lost message; it retires via the command floor")

    def test_a_fresh_cli_spawn_runs_the_marking(self):
        # the spawn half is a call inside Session._run (spawning a real CLI in a unit test is not
        # practical) — pin it the way error-visibility's NoSilentSwallows pins handlers: read the source
        import ast
        import inspect
        run = next(n for n in ast.walk(ast.parse(inspect.getsource(sb)))
                   if isinstance(n, ast.FunctionDef) and n.name == "_run")
        calls = [n.func.attr for n in ast.walk(run)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
        self.assertIn("_mark_dropped_echoes", calls,
                      "_run no longer marks orphaned echoes when a fresh CLI spawns")

    def test_landing_still_prunes_a_dropped_echo(self):
        # the self-correcting guarantee: a premature mark can never stick to a delivered message
        state = tempfile.mkdtemp()
        be = self._backend(state)
        sb.write_reg(be.state_dir, SID, {"sid": SID, "alive": True})
        k, e = _echo("actually landed after all")
        e["dropped"] = True
        be._live[SID] = dict([(k, e)])
        be._persist_echoes(SID)
        be.prune_live(SID, tx_uuids=set(), tx_user_texts={"actually landed after all"}, human_floor=0)
        self.assertNotIn(SID, be._live)
        self.assertEqual(sb.read_reg(state, SID).get("echoes"), [])

    def test_dismiss_retires_by_key_and_by_send_time(self):
        state = tempfile.mkdtemp()
        be = self._backend(state)
        sb.write_reg(be.state_dir, SID, {"sid": SID, "alive": True})
        k, e = _echo("seen and dismissed")
        e["dropped"] = True
        be._live[SID] = dict([(k, e)])
        self.assertEqual(be.dismiss_echo(SID, uuid=k), "seen and dismissed")
        self.assertNotIn(SID, be._live)
        self.assertEqual(sb.read_reg(state, SID).get("echoes"), [], "dismissal empties the mirror")
        # by send time: the uuid regenerates at every boot reseed, but t survives it
        k2, e2 = _echo("dismissed after a restart", t=4242, key="echo:regen")
        e2["dropped"] = True
        be._live[SID] = dict([(k2, e2)])
        self.assertEqual(be.dismiss_echo(SID, uuid="echo:stale-painted-key", t=4242),
                         "dismissed after a restart")
        self.assertIsNone(be.dismiss_echo(SID, uuid="echo:stale-painted-key", t=4242),
                          "a second click is an idempotent miss, not an error")

    def test_dismiss_never_touches_a_pending_echo(self):
        be = self._backend()
        sb.write_reg(be.state_dir, SID, {"sid": SID, "alive": True})
        k, e = _echo("still in flight")
        be._live[SID] = dict([(k, e)])
        self.assertIsNone(be.dismiss_echo(SID, uuid=k, t=e["t"]),
                          "an undropped echo is the send's only record — undismissable")
        self.assertIn(k, be._live[SID])


class TodoAnswersAnnounceTheirLoss(unittest.TestCase):
    """Round-2 finding 2, backend half: the echo of a user-todo ANSWER carries the todo id
    (send(user_todo=...)), the id rides the reg mirror across restarts, and the drop-marking hands
    (sid, tid, text) to the constructor's todo_lost callback — the seam that returns a
    restart-lost answer to the asks the user still owes. Constructor-wired on purpose: the boot
    reseed fires drop marks from __init__, before any post-construction assignment could arm it."""

    ANSWER = "Re: need the staging port — 8443."
    TID = "ut-9f2c1a34"

    def _backend(self, state=None, lost=None):
        return sb.SdkBackend(state or tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None,
                             todo_lost=lost)

    def _todo_echo(self, dropped=False):
        k, e = _echo(self.ANSWER)
        e["_todo"] = self.TID
        if dropped:
            e["dropped"] = True
        return k, e

    def test_send_with_user_todo_stamps_entry_echo_and_mirror(self):
        state = tempfile.mkdtemp()
        be = self._backend(state=state)
        sb.write_reg(be.state_dir, SID, {"sid": SID, "alive": True})
        s = sb.SdkSession(be, sb.read_reg(be.state_dir, SID))
        be._ensure = lambda sid: s
        self.assertTrue(be.send(SID, self.ANSWER, user_todo=self.TID))
        self.assertEqual([getattr(t, "todo", "") for t in s.pending()], [self.TID],
                         "the queue entry carries the id")
        atoms = be.live_atoms(SID)
        self.assertEqual(atoms[0].get("_todo"), self.TID, "the echo carries it too")
        self.assertEqual((sb.read_reg(state, SID).get("echoes") or [{}])[0].get("todo"), self.TID,
                         "…and the id survives the restart mirror")

    def test_a_plain_send_mirrors_without_a_todo_key(self):
        # byte-compat: every non-answer echo keeps the exact pre-todo mirror shape
        state = tempfile.mkdtemp()
        be = self._backend(state=state)
        sb.write_reg(be.state_dir, SID, {"sid": SID, "alive": True})
        k, e = _echo("an ordinary message")
        be._live[SID] = dict([(k, e)])
        be._persist_echoes(SID)
        self.assertNotIn("todo", (sb.read_reg(state, SID).get("echoes") or [{}])[0])

    def test_the_drop_marking_hands_the_id_to_the_callback(self):
        calls = []
        be = self._backend(lost=lambda sid, tid, text: calls.append((sid, tid, text)))
        sb.write_reg(be.state_dir, SID, {"sid": SID, "alive": True})
        k, e = self._todo_echo()
        be._live[SID] = dict([(k, e)])
        be._mark_dropped_echoes(SID, [])
        self.assertEqual(calls, [(SID, self.TID, self.ANSWER)])
        self.assertTrue(be._live[SID][k].get("dropped"), "the visible marking still happens")

    def test_an_echo_still_queued_fires_nothing(self):
        calls = []
        be = self._backend(lost=lambda *a: calls.append(a))
        sb.write_reg(be.state_dir, SID, {"sid": SID, "alive": True})
        k, e = self._todo_echo()
        be._live[SID] = dict([(k, e)])
        be._mark_dropped_echoes(SID, [self.ANSWER])
        self.assertEqual(calls, [], "still in the surviving queue → in flight, not lost")

    def test_an_already_dropped_echo_never_refires(self):
        calls = []
        be = self._backend(lost=lambda *a: calls.append(a))
        sb.write_reg(be.state_dir, SID, {"sid": SID, "alive": True})
        k, e = self._todo_echo(dropped=True)
        be._live[SID] = dict([(k, e)])
        be._mark_dropped_echoes(SID, [])
        self.assertEqual(calls, [], "the loss was already announced — marking is one-shot")

    def test_a_plain_dropped_echo_fires_nothing(self):
        calls = []
        be = self._backend(lost=lambda *a: calls.append(a))
        sb.write_reg(be.state_dir, SID, {"sid": SID, "alive": True})
        k, e = _echo("an ordinary lost send")
        be._live[SID] = dict([(k, e)])
        be._mark_dropped_echoes(SID, [])
        self.assertEqual(calls, [], "no id on the echo → nothing to reopen")

    def test_the_id_reseeds_across_a_restart_and_the_boot_mark_fires(self):
        state = tempfile.mkdtemp()
        be = self._backend(state=state)
        sb.write_reg(be.state_dir, SID, {"sid": SID, "alive": True})
        k, e = self._todo_echo()
        be._live[SID] = dict([(k, e)])
        be._persist_echoes(SID)
        calls = []
        be2 = self._backend(state=state, lost=lambda sid, tid, text: calls.append((sid, tid)))
        self.assertEqual(calls, [(SID, self.TID)],
                         "the boot reseed hands the lost answer's id to the kernel")
        self.assertEqual(be2.live_atoms(SID)[0].get("_todo"), self.TID)

    def test_a_callback_error_never_breaks_the_marking(self):
        def boom(*a):
            raise RuntimeError("kernel side failed")

        be = self._backend(lost=boom)
        sb.write_reg(be.state_dir, SID, {"sid": SID, "alive": True})
        k, e = self._todo_echo()
        be._live[SID] = dict([(k, e)])
        be._mark_dropped_echoes(SID, [])
        self.assertTrue(be._live[SID][k].get("dropped"),
                        "the loss stays visible even when the reopen seam raises")


class RedeliveryFeedsTheAuthoritativeQueue(unittest.TestCase):
    """The redeliver arm of _mark_dropped_echoes (2026-08-23: a proven-lost HUMAN send goes back
    into the queue instead of just flagging) must write the queue that is AUTHORITATIVE for its
    caller, and must not lose what is already there (found 2026-08-26):
      - the reg rewrite is dict-aware like every other reg['queue'] RMW (round 2, 2026-08-22) —
        the strings-only filter it shipped with silently ERASED a persisted user-todo answer's
        {"text","todo"} entry: the todo stayed 'answered', the answer never delivered, and
        nothing could reopen the ask;
      - a redelivered answer KEEPS the id its echo carries, so recall/loss can still reopen;
      - on the LIVE-session callers (a fresh spawn's _run, a reconnect's _reconcile_stranded)
        the in-memory _pending is authoritative — a reg-only write is clobbered by the very next
        _persist_queue snapshot, leaving the recovered send in limbo until a future kernel boot.
    SYNTHETIC fixtures only."""

    ANSWER = "Re: pick a database - use sqlite"
    TID = "ut-2f7a9c11"
    STRAY = "unrelated typed message the dead CLI was holding"

    def setUp(self):
        self.state = tempfile.mkdtemp()
        # a real (empty) transcript, so _text_landed answers False (readable, nothing landed)
        # and the redeliver arm actually runs — unreadable fails safe toward the flag path
        os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(self.state, "claude")
        self.cwd = os.path.join(self.state, "proj")
        os.makedirs(self.cwd, exist_ok=True)
        tp = sb.transcript_path(self.cwd, SID)
        os.makedirs(os.path.dirname(tp), exist_ok=True)
        open(tp, "w").close()
        self.losses = []
        self.be = sb.SdkBackend(self.state, "/bin/true", lambda *a, **k: None,
                                todo_lost=lambda sid, tid, text: self.losses.append((sid, tid, text)))

    def _reg(self, **extra):
        reg = {"sid": SID, "name": "web", "mode": "acceptEdits",
               "alive": True, "cwd": self.cwd, "lastSid": SID}
        reg.update(extra)
        sb.write_reg(self.be.state_dir, SID, reg)
        return reg

    def _sess(self, reg):
        s = sb.SdkSession(self.be, dict(reg))
        self.be.sessions[SID] = s          # register WITHOUT starting the thread (no loop)
        return s

    def _stash_echo(self, text, t=100, todo=""):
        e = {"type": "user", "uuid": "echo:" + text[:10], "session_id": SID, "t": t,
             "parentUuid": None, "author": "human", "_echo_text": text,
             "message": {"role": "user", "content": [{"type": "text", "text": text}]}}
        if todo:
            e["_todo"] = todo
        self.be._live.setdefault(SID, {})[e["uuid"]] = e
        return e

    def _queue(self):
        return (sb.read_reg(self.be.state_dir, SID) or {}).get("queue") or []

    def test_the_reg_rewrite_preserves_a_persisted_todo_answer(self):
        # the two-part shape: a persisted ANSWER (dict entry, its echo still queued) plus one
        # stranded typed send whose redelivery triggers the rewrite that used to erase the dict
        answer = {"text": self.ANSWER, "todo": self.TID}
        self._reg(queue=[answer])
        self._stash_echo(self.ANSWER, t=100, todo=self.TID)
        self._stash_echo(self.STRAY, t=200)
        self.be._mark_dropped_echoes(SID, sb._queue_texts([answer]))   # the boot reseed's call shape
        q = self._queue()
        self.assertIn(answer, q, "the persisted user-todo answer must survive the re-delivery rewrite")
        self.assertEqual(q, [answer, self.STRAY],
                         "…and the recovered send queues BEHIND the surviving queue")
        self.assertEqual(self.losses, [], "nothing was lost — the reopen seam must stay quiet")

    def test_a_redelivered_answer_keeps_its_todo_id_in_the_reg(self):
        self._reg(queue=[])
        self._stash_echo(self.ANSWER, todo=self.TID)
        self.be._mark_dropped_echoes(SID, [])
        self.assertEqual(self._queue(), [{"text": self.ANSWER, "todo": self.TID}],
                         "the id rides the redelivered entry, so recall/loss can still reopen the ask")
        self.assertEqual(self.losses, [], "redelivered, not lost")

    def test_live_session_redelivery_reaches_pending_and_survives_the_next_persist(self):
        reg = self._reg(queue=[])
        s = self._sess(reg)
        e = self._stash_echo("typed while the old client was dying", t=300)
        self.be._mark_dropped_echoes(SID, s.pending())     # the spawn/reconnect-strand call shape
        self.assertEqual(s.pending(), ["typed while the old client was dying"],
                         "a live session's recovered send must enter _pending — a reg-only write "
                         "is overwritten by the very next queue mirror")
        s._persist_queue()          # the mirror snapshot a reg-only write could not survive
        self.assertEqual(self._queue(), ["typed while the old client was dying"])
        self.assertFalse(e.get("dropped"), "re-delivered → renders as queued, not never-delivered")

    def test_live_session_redelivery_keeps_the_answer_id_end_to_end(self):
        reg = self._reg(queue=[])
        s = self._sess(reg)
        self._stash_echo(self.ANSWER, todo=self.TID)
        self.be._mark_dropped_echoes(SID, s.pending())
        self.assertEqual([getattr(t, "todo", "") for t in s.pending()], [self.TID],
                         "the recovered answer carries its ask's id in the live queue")
        s._persist_queue()
        self.assertEqual(self._queue(), [{"text": self.ANSWER, "todo": self.TID}],
                         "…and the id survives the mirror round-trip")
        self.assertEqual(self.losses, [])

    def test_live_session_redelivery_never_duplicates_a_pending_text(self):
        reg = self._reg(queue=[])
        s = self._sess(reg)
        s.enqueue("already back in the queue")
        self._stash_echo("already back in the queue")
        # a caller's queued snapshot can predate the enqueue — the write-moment check must dedupe
        self.be._mark_dropped_echoes(SID, [])
        self.assertEqual(s.pending(), ["already back in the queue"], "one copy, not two")


if __name__ == "__main__":
    unittest.main()
