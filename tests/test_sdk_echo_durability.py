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


class AnswerEchoesKeepTheirId(unittest.TestCase):
    """A send that ANSWERS a user todo (SdkBackend.send's user_todo) stamps the id on its echo
    (`_todo`), mirrors it to the registry (`todo`) and gets it back at the boot reseed — the id
    rides the echo the way it rides the queue entry, so a loss detected later can be tied back to
    the ask. Every other echo mirrors exactly as before: the plain entry's keys are the pre-todo
    five, byte for byte."""

    PLAIN_KEYS = ["t", "text", "author", "rompAuto", "dropped"]

    def _backend(self, state):
        be = sb.SdkBackend(state, "/bin/true", lambda *a, **k: None)
        sb.write_reg(be.state_dir, SID, {"sid": SID, "alive": True})
        return be

    def test_send_stamps_the_id_on_the_echo_and_the_queue_entry(self):
        be = self._backend(tempfile.mkdtemp())
        fed = []
        be._ensure = lambda sid: type("S", (), {"enqueue": lambda self, t, todo="": fed.append((t, todo))})()
        self.assertTrue(be.send(SID, "Re: the staging port — 8443.", user_todo="ut-9f2c1a34"))
        self.assertTrue(be.send(SID, "plain words"))
        self.assertEqual(fed, [("Re: the staging port — 8443.", "ut-9f2c1a34"), ("plain words", "")],
                         "the id reaches the queue entry; a plain send hands an empty id")
        by_text = {a["_echo_text"]: a for a in be.live_atoms(SID) if a.get("_echo_text")}
        self.assertEqual(by_text["Re: the staging port — 8443."].get("_todo"), "ut-9f2c1a34")
        self.assertNotIn("_todo", by_text["plain words"], "a plain echo carries no id key at all")

    def test_the_mirror_carries_the_id_and_a_plain_entry_is_byte_identical(self):
        state = tempfile.mkdtemp()
        be = self._backend(state)
        k1, e1 = _echo("plain words", t=1000, key="echo:p")
        k2, e2 = _echo("Re: the staging port — 8443.", t=1001, key="echo:a")
        e2["_todo"] = "ut-9f2c1a34"
        be._live[SID] = {k1: e1, k2: e2}
        be._persist_echoes(SID)
        mirror = sb.read_reg(be.state_dir, SID).get("echoes")
        plain = next(x for x in mirror if x["text"] == "plain words")
        self.assertEqual(list(plain.keys()), self.PLAIN_KEYS, "the pre-todo shape, key for key, in order")
        self.assertEqual(plain, {"t": 1000, "text": "plain words", "author": "human",
                                 "rompAuto": False, "dropped": False})
        answer = next(x for x in mirror if x["text"] != "plain words")
        self.assertEqual(answer.get("todo"), "ut-9f2c1a34")
        # "kernel restart": the reseeded atom carries the id again; the plain one still has no key
        be2 = sb.SdkBackend(state, "/bin/true", lambda *a, **k: None)
        atoms = {a["_echo_text"]: a for a in be2.live_atoms(SID) if a.get("_echo_text")}
        self.assertEqual(atoms["Re: the staging port — 8443."].get("_todo"), "ut-9f2c1a34")
        self.assertNotIn("_todo", atoms["plain words"])

    def test_boot_reseed_spares_an_answer_still_queued_as_a_dict_entry(self):
        # the persisted queue holds the answer as {"text","todo"}: the reseed's "is it still queued?"
        # check must read the entry's text, or the answer's echo is flagged dropped (and re-delivered
        # a second time) while its message sits in the queue about to go out
        state = tempfile.mkdtemp()
        be = self._backend(state)
        sb.write_reg(be.state_dir, SID, {"sid": SID, "alive": True,
                                         "queue": [{"text": "Re: the staging port — 8443.",
                                                    "todo": "ut-9f2c1a34"}]})
        k, e = _echo("Re: the staging port — 8443.")
        e["_todo"] = "ut-9f2c1a34"
        be._live[SID] = dict([(k, e)])
        be._persist_echoes(SID)
        be2 = sb.SdkBackend(state, "/bin/true", lambda *a, **k: None)
        atoms = be2.live_atoms(SID)
        self.assertTrue(atoms and not atoms[0].get("dropped"),
                        "a queued answer is in flight, not lost")
        self.assertEqual(sb.read_reg(state, SID).get("queue"),
                         [{"text": "Re: the staging port — 8443.", "todo": "ut-9f2c1a34"}],
                         "and the reseed never rewrote the queue (no duplicate, id intact)")


class TodoAnswersAnnounceTheirLoss(unittest.TestCase):
    """The echo of a user-todo ANSWER carries the todo id (send(user_todo=...) — pinned above by
    AnswerEchoesKeepTheirId), and the drop-marking hands (sid, tid, text) to the constructor's
    todo_lost callback — the seam that returns a restart-lost answer to the asks the user still
    owes. Constructor-wired on purpose: the boot reseed fires drop marks from __init__, before any
    post-construction assignment could arm it. The rewind's dropped head takes the same seam."""

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

    def test_a_backend_built_without_the_seam_keeps_marking(self):
        # tests and older kernels: no callback → the drop marking is unchanged, nothing raised
        be = self._backend()
        sb.write_reg(be.state_dir, SID, {"sid": SID, "alive": True})
        k, e = self._todo_echo()
        be._live[SID] = dict([(k, e)])
        be._mark_dropped_echoes(SID, [])
        self.assertTrue(be._live[SID][k].get("dropped"))

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

    def test_a_rewind_dropped_answer_head_is_handed_to_the_callback(self):
        # the other loss event: the CLI refuses a rewind connect and the held edit turn is pulled
        # off the queue — when that head is an answer, its ask must visibly return too
        calls = []
        be = self._backend(lost=lambda sid, tid, text: calls.append((sid, tid, text)))
        sb.write_reg(be.state_dir, SID, {"sid": SID, "alive": True})
        s = sb.SdkSession(be, sb.read_reg(be.state_dir, SID))
        s.enqueue(self.ANSWER, todo=self.TID)
        s._rewind_bare = False
        s._rewind_failed(RuntimeError("refused"))
        self.assertEqual(calls, [(SID, self.TID, self.ANSWER)])
        self.assertEqual(s.pending(), [], "the head was dropped, as before")

    def test_a_bare_rollback_or_a_plain_head_hands_nothing_over(self):
        calls = []
        be = self._backend(lost=lambda *a: calls.append(a))
        sb.write_reg(be.state_dir, SID, {"sid": SID, "alive": True})
        s = sb.SdkSession(be, sb.read_reg(be.state_dir, SID))
        s.enqueue("an unrelated held message")
        s._rewind_bare = True
        s._rewind_failed(RuntimeError("refused"))
        self.assertEqual(s.pending(), ["an unrelated held message"], "a bare rollback drops no head")
        s._rewind_bare = False
        s._rewind_failed(RuntimeError("refused"))
        self.assertEqual(s.pending(), [])
        self.assertEqual(calls, [], "a plain head carries no id → nothing to reopen")


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


class RedeliveryFeedsTheAuthoritativeQueue(unittest.TestCase):
    """The redeliver arm of _mark_dropped_echoes (2026-08-23: a proven-lost HUMAN send goes back
    into the queue instead of just flagging) must write the queue that is AUTHORITATIVE for its
    caller (found 2026-08-26): on the LIVE-session caller (a fresh spawn's _run; the resumable
    reconnect is flag-only — ReconnectStrandIsFlagOnly below) the in-memory _pending is
    authoritative — a reg-only write is clobbered by the very next _persist_queue snapshot,
    leaving the recovered send in limbo until a future kernel boot. SYNTHETIC fixtures only."""

    def setUp(self):
        self.state = tempfile.mkdtemp()
        # an EMPTY reg listing, not a MISSING one: list_regs treats an absent sdk/ dir as a scan
        # fault and serves every cached row — earlier tests' regs would reseed into this boot
        os.makedirs(os.path.join(self.state, "sdk"))
        # a real (empty) transcript, so _text_landed answers False (readable, nothing landed)
        # and the redeliver arm actually runs — unreadable fails safe toward the flag path
        os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(self.state, "claude")
        self.cwd = os.path.join(self.state, "proj")
        os.makedirs(self.cwd, exist_ok=True)
        tp = sb.transcript_path(self.cwd, SID)
        os.makedirs(os.path.dirname(tp), exist_ok=True)
        open(tp, "w").close()
        self.be = sb.SdkBackend(self.state, "/bin/true", lambda *a, **k: None)

    def tearDown(self):
        os.environ.pop("CLAUDE_CONFIG_DIR", None)

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

    def _stash_echo(self, text, t=100):
        e = {"type": "user", "uuid": "echo:" + text[:10], "session_id": SID, "t": t,
             "parentUuid": None, "author": "human", "_echo_text": text,
             "message": {"role": "user", "content": [{"type": "text", "text": text}]}}
        self.be._live.setdefault(SID, {})[e["uuid"]] = e
        return e

    def _queue(self):
        return (sb.read_reg(self.be.state_dir, SID) or {}).get("queue") or []

    def test_live_session_redelivery_reaches_pending_and_survives_the_next_persist(self):
        reg = self._reg(queue=[])
        s = self._sess(reg)
        e = self._stash_echo("typed while the old client was dying", t=300)
        self.be._mark_dropped_echoes(SID, s.pending())     # the fresh-spawn (_run) call shape
        self.assertEqual(s.pending(), ["typed while the old client was dying"],
                         "a live session's recovered send must enter _pending — a reg-only write "
                         "is overwritten by the very next queue mirror")
        s._persist_queue()          # the mirror snapshot a reg-only write could not survive
        self.assertEqual(self._queue(), ["typed while the old client was dying"])
        self.assertFalse(e.get("dropped"), "re-delivered → renders as queued, not never-delivered")

    def test_live_session_redelivery_never_duplicates_a_pending_text(self):
        reg = self._reg(queue=[])
        s = self._sess(reg)
        s.enqueue("already back in the queue")
        self._stash_echo("already back in the queue")
        # a caller's queued snapshot can predate the enqueue — the write-moment check must dedupe
        self.be._mark_dropped_echoes(SID, [])
        self.assertEqual(s.pending(), ["already back in the queue"], "one copy, not two")


class ReconnectStrandIsFlagOnly(unittest.TestCase):
    """_reconcile_stranded's RESUMABLE branch is documented flag-only — the fed atom may genuinely
    have landed, so re-feeding risks a REAL duplicate the user sees twice. The redeliver arm of
    _mark_dropped_echoes silently flipped that policy (found 2026-08-26): a missed _text_landed
    scan (a tail-window miss, an unusual content shape) re-fed the message into the resumed
    conversation. On the resumable branch the loss is SURFACED (the dropped flag) and never
    re-fed; the re-feed belongs only where the conversation is NOT resumable (the no-init re-head,
    the boot/spawn dead paths). SYNTHETIC fixtures only."""

    TEXT = "typed while the reconnect tore the client down"

    def setUp(self):
        self.state = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.state, "sdk"))   # an empty listing, not a missing one (see above)
        # a real (empty) transcript: _text_landed answers False — the exact "missed scan" shape,
        # since the resumable branch must not trust that answer with a re-feed
        os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(self.state, "claude")
        self.cwd = os.path.join(self.state, "proj")
        os.makedirs(self.cwd, exist_ok=True)
        tp = sb.transcript_path(self.cwd, SID)
        os.makedirs(os.path.dirname(tp), exist_ok=True)
        open(tp, "w").close()
        self.be = sb.SdkBackend(self.state, "/bin/true", lambda *a, **k: None)

    def tearDown(self):
        os.environ.pop("CLAUDE_CONFIG_DIR", None)

    def _sess(self, **extra):
        reg = {"sid": SID, "name": "web", "mode": "acceptEdits",
               "alive": True, "cwd": self.cwd, "lastSid": SID}
        reg.update(extra)
        sb.write_reg(self.be.state_dir, SID, reg)
        s = sb.SdkSession(self.be, dict(reg))
        self.be.sessions[SID] = s          # register WITHOUT starting the thread (no loop)
        return s

    def _stash_echo(self, text, t=100):
        e = {"type": "user", "uuid": "echo:" + text[:10], "session_id": SID, "t": t,
             "parentUuid": None, "author": "human", "_echo_text": text,
             "message": {"role": "user", "content": [{"type": "text", "text": text}]}}
        self.be._live.setdefault(SID, {})[e["uuid"]] = e
        return e

    def test_a_resumable_reconnect_flags_and_never_refeeds(self):
        s = self._sess()                                # lastSid set → the conversation is resumable
        self.assertEqual(s.resume_sid, SID)
        s.inflight = 1
        s._inflight_texts.append(self.TEXT)
        e = self._stash_echo(self.TEXT, t=300)
        s._reconcile_stranded()
        self.assertEqual(s.pending(), [],
                         "flag-only: a fed turn on a resumable conversation is never re-fed — "
                         "re-feeding risks a real duplicate")
        self.assertEqual((sb.read_reg(self.be.state_dir, SID) or {}).get("queue") or [], [],
                         "…and no reg-queue back door either")
        self.assertTrue(e.get("dropped"), "the loss surfaces NOW as never-delivered")

    def test_a_fresh_conversation_reconnect_still_reheads(self):
        # the documented other branch: no init ever streamed → nothing the user can see exists,
        # so re-feeding cannot duplicate — the queue re-head is the loss-proof path here
        s = self._sess(lastSid="")                      # never resumed → resume_sid None
        self.assertIsNone(s.resume_sid)
        s.inflight = 1
        s._inflight_texts.append(self.TEXT)
        s._reconcile_stranded()
        self.assertEqual(s.pending(), [self.TEXT],
                         "the not-yet-materialized conversation re-heads the queue, as documented")


if __name__ == "__main__":
    unittest.main()
