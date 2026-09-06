#!/usr/bin/env python3
"""An SDK input echo is the ONLY visible record of a send the transcript hasn't caught up on — since
queued sends forward into the CLI mid-turn (2026-07-17) there is a window where a message is neither
queued nor landed, and the echo must own it (the user 2026-07-20: a reply sat invisible in the chat,
and one message was silently LOST across a kernel restart with no trace anywhere). Four durability
guarantees, each pinned here:
  1. the live-tail overflow cap never evicts an echo (work atoms are disposable; echoes aren't),
  2. the genuine-human-turn floor retires only IMAGE-PATH-BEARING echoes (the image-extraction case
     whose text-match structurally fails: the CLI rewrites the path to "[Image #N]") — a plain-text
     echo prunes only by its own text landing, and a dropped send's echo PERSISTS so the loss shows
     (the tmux echo's semantics). Narrowed 2026-09-06 from "any absolute path": a quote chip's
     `path:line` label is not an extraction. And an echo whose text the session has FED to the CLI
     (fed_texts) outranks the floor entirely until it lands or the CLI dies holding it,
  3. unlanded echoes mirror to the registry (reg['echoes']) and reseed on backend construction, so a
     kernel restart cannot wipe the only evidence of an in-flight send,
  4. an echo that survives its holder is MARKED dropped at the event that orphaned it (boot reseed /
     fresh CLI spawn), so persistence reads as "never delivered", not as delivered history (the user
     2026-07-29: a two-day-old lost send kept resurfacing mid-chat, posing as an ordinary bubble) —
     unless the transcript already carries the text, as a native user record OR as the queued_command
     attachment a mid-turn splice leaves (the absorbed send's only record): that echo is neither
     re-delivered nor flagged, it just waits for the by-text prune (AbsorbedSendsCountAsLandedAtBoot).
SYNTHETIC fixtures only."""
import json
import os
import tempfile
import time
import unittest
from datetime import datetime, timezone
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
        # only what the CLI extracts: an image path (absolute or ~-rooted, a known image extension)
        self.assertTrue(sb._path_bearing("see /tmp/x.png"))
        self.assertTrue(sb._path_bearing("look at ~/Screenshots/shot-2.PNG please"))
        self.assertTrue(sb._path_bearing("(/tmp/notes-api/docs/fig.jpeg)"))
        self.assertFalse(sb._path_bearing("~/notes/todo.md is stale"),
                         "a non-image path is never rewritten out of the record — not extraction")
        self.assertFalse(sb._path_bearing("just a plain reply, and/or nothing else"))
        self.assertFalse(sb._path_bearing(""))

    def test_a_quote_chip_source_label_is_not_path_bearing(self):
        # the 2026-09-06 incident: a staged comment's quote chip leads with where the passage came from
        # (`path:line`), which the old any-path predicate called path-bearing — so the floor retired the
        # echo of a message the CLI still held. The text has no image in it; it must prune by text only.
        body = ("Replying to this highlighted code (/tmp/notes-api/notes/api.py:42):\n"
                "> def list_notes():\n\nrename this to fetch_notes")
        self.assertFalse(sb._path_bearing(body))
        be = self._backend()
        k, e = _echo(body, t=39)
        be._live[SID] = dict([(k, e)])
        be.prune_live(SID, tx_uuids=set(), tx_user_texts={"an earlier comment": 39}, human_floor=39)
        self.assertIn(k, be._live.get(SID, {}), "a quote-chip echo survives its sibling's landing")
        be.prune_live(SID, tx_uuids=set(), tx_user_texts={body: 69}, human_floor=69)
        self.assertNotIn(SID, be._live, "…and retires when its own text lands")


class FedEchoesOutliveTheFloor(unittest.TestCase):
    """An echo whose text the session has fed to the CLI (SdkSession._inflight_texts, the fed-turn twin
    of `inflight`) is in flight by construction — the CLI queues a mid-turn send behind the running turn
    and splices it at the next tool boundary — so no floor may retire it. It retires on its text landing
    (the absorbed atom's queued_command text) or on the CLI dying with it (the dropped marking clears the
    fed list). SYNTHETIC fixtures only; the session is registered without a thread."""

    IMG = "compare against /tmp/notes-api/docs/before.png please"

    def setUp(self):
        self.state = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.state, "sdk"))
        os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(self.state, "claude")
        self.cwd = os.path.join(self.state, "proj")
        os.makedirs(self.cwd, exist_ok=True)
        tp = sb.transcript_path(self.cwd, SID)
        os.makedirs(os.path.dirname(tp), exist_ok=True)
        open(tp, "w").close()
        self.be = sb.SdkBackend(self.state, "/bin/true", lambda *a, **k: None)
        reg = {"sid": SID, "name": "web", "mode": "acceptEdits", "alive": True, "cwd": self.cwd, "lastSid": SID}
        sb.write_reg(self.be.state_dir, SID, reg)
        self.s = sb.SdkSession(self.be, dict(reg))
        self.be.sessions[SID] = self.s

    def tearDown(self):
        os.environ.pop("CLAUDE_CONFIG_DIR", None)

    def _fed_echo(self, text, t=38):
        self.s.inflight = 1
        self.s._inflight_texts.append(text)
        k, e = _echo(text, t=t)
        self.be._live[SID] = dict([(k, e)])
        return k, e

    def test_a_fed_image_echo_survives_the_floor(self):
        # a human record at t=39 (the sibling's landing) postdates the fed echo at t=38; the old rule
        # retired an image-bearing echo here — the guard holds it, the CLI still has the message
        k, e = self._fed_echo(self.IMG, t=38)
        self.assertEqual(self.s.fed_texts(), [self.IMG])
        self.be.prune_live(SID, tx_uuids=set(), tx_user_texts={"the first comment": 39}, human_floor=39)
        self.assertIn(k, self.be._live.get(SID, {}), "a fed echo outranks the floor")

    def test_it_still_retires_when_its_text_lands(self):
        # the queued_command attachment lands the text (the kernel's _atom_user_texts covers that shape);
        # the by-text prune is untouched by the guard
        k, e = self._fed_echo(self.IMG, t=38)
        self.be.prune_live(SID, tx_uuids=set(), tx_user_texts={self.IMG: 69}, human_floor=69)
        self.assertNotIn(SID, self.be._live, "landing retires a fed echo as before")

    def test_the_unfed_image_echo_still_floors_as_before(self):
        # nothing fed → the image-extraction semantics are exactly the pre-change ones
        k, e = _echo(self.IMG, t=38)
        self.be._live[SID] = dict([(k, e)])
        self.assertEqual(self.s.fed_texts(), [])
        self.be.prune_live(SID, tx_uuids=set(), tx_user_texts=set(), human_floor=39)
        self.assertNotIn(SID, self.be._live)

    def test_the_cli_dying_lifts_the_guard_and_marks_the_loss(self):
        # the reconnect teardown (a resumable conversation): the fed list empties, the echo is flagged
        # dropped — the guard is gone, the loss is visible, and a floor now rules as it did before
        k, e = self._fed_echo(self.IMG, t=38)
        self.assertEqual(self.s.resume_sid, SID)
        self.s._reconcile_stranded()
        self.assertEqual(self.s.fed_texts(), [])
        self.assertTrue(e.get("dropped"), "the CLI died holding it → never delivered, shown as such")
        self.assertIn(k, self.be._live.get(SID, {}), "the flag path keeps the echo as the loss record")
        self.be.prune_live(SID, tx_uuids=set(), tx_user_texts=set(), human_floor=39)
        self.assertNotIn(SID, self.be._live, "a dropped image echo keeps the pre-change floor rule")

    def test_a_dropped_fed_echo_never_hides_behind_the_guard(self):
        # belt and braces: a stale fed entry (a crashed thread that never cleared it) must not shield an
        # echo the marking has already ruled lost
        k, e = self._fed_echo(self.IMG, t=38)
        e["dropped"] = True
        self.be.prune_live(SID, tx_uuids=set(), tx_user_texts=set(), human_floor=39)
        self.assertNotIn(SID, self.be._live)

    def test_fed_texts_is_a_snapshot(self):
        self.s._inflight_texts.append("one")
        snap = self.s.fed_texts()
        snap.append("two")
        self.assertEqual(self.s.fed_texts(), ["one"])


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
      - on the LIVE-session caller (a fresh spawn's _run; the resumable reconnect is flag-only —
        ReconnectStrandIsFlagOnly below) the in-memory _pending is authoritative — a reg-only
        write is clobbered by the very next _persist_queue snapshot, leaving the recovered send
        in limbo until a future kernel boot;
      - the reg rewrite is dict-aware like every other reg['queue'] RMW — the strings-only filter
        it shipped with silently ERASED a persisted user-todo answer's {"text","todo"} entry: the
        todo stayed 'answered', the answer never delivered, and nothing could reopen the ask;
      - a redelivered answer KEEPS the id its echo carries, so recall/loss can still reopen.
    SYNTHETIC fixtures only."""

    ANSWER = "Re: pick a database - use sqlite"
    TID = "ut-2f7a9c11"
    STRAY = "unrelated typed message the dead CLI was holding"

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
        self.losses = []
        self.be = sb.SdkBackend(self.state, "/bin/true", lambda *a, **k: None,
                                todo_lost=lambda sid, tid, text: self.losses.append((sid, tid, text)))

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
        self.be._mark_dropped_echoes(SID, s.pending())     # the fresh-spawn (_run) call shape
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




class ReconnectStrandIsFlagOnly(unittest.TestCase):
    """_reconcile_stranded's RESUMABLE branch is documented flag-only — the fed atom may genuinely
    have landed, so re-feeding risks a REAL duplicate the user sees twice. The redeliver arm of
    _mark_dropped_echoes silently flipped that policy (found 2026-08-26): a missed _text_landed
    scan (a tail-window miss, an unusual content shape) re-fed the message into the resumed
    conversation. On the resumable branch the loss is SURFACED (the dropped flag, the todo-reopen
    seam) and never re-fed; the re-feed belongs only where the conversation is NOT resumable (the
    no-init re-head, the boot/spawn dead paths). SYNTHETIC fixtures only."""

    TEXT = "typed while the reconnect tore the client down"
    TID = "ut-3a8b0c22"

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
        self.losses = []
        self.be = sb.SdkBackend(self.state, "/bin/true", lambda *a, **k: None,
                                todo_lost=lambda sid, tid, text: self.losses.append((sid, tid, text)))

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

    def _stash_echo(self, text, t=100, todo=""):
        e = {"type": "user", "uuid": "echo:" + text[:10], "session_id": SID, "t": t,
             "parentUuid": None, "author": "human", "_echo_text": text,
             "message": {"role": "user", "content": [{"type": "text", "text": text}]}}
        if todo:
            e["_todo"] = todo
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

    def test_the_resumable_branch_still_reopens_a_lost_todo_answer(self):
        s = self._sess()
        s.inflight = 1
        s._inflight_texts.append(self.TEXT)
        e = self._stash_echo(self.TEXT, t=300, todo=self.TID)
        s._reconcile_stranded()
        self.assertEqual(s.pending(), [])
        self.assertTrue(e.get("dropped"))
        self.assertEqual(self.losses, [(SID, self.TID, self.TEXT)],
                         "the todo-reopen seam fires on the flag path — the ask visibly returns")

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


class AbsorbedSendsCountAsLandedAtBoot(unittest.TestCase):
    """The boot/dead-spawn duplicate guard (_text_landed) must know the shape an ABSORBED send leaves. A
    message fed into a running turn is spliced in at the CLI's next tool boundary as a queued_command
    ATTACHMENT record — no native user line is ever written for it — and until 2026-09-06 the scan
    accepted user records alone (its raw-line prefilter even required the literal '"user"', which an
    attachment line lacks; it carries `userType`). So a kernel restart in the window between the splice
    and the next merged build reseeded the echo, read the send as never landed, re-queued the text, and
    the resumed CLI ran the same instruction a second time — the chat showed it twice.

    Now a found text is neither re-delivered nor flagged: it landed and is merely un-pruned, and the next
    build's by-text prune (the absorbed atom's text reaches _atom_user_texts) retires it. Two more scan
    rules ride along, both mirrored from prune_live's by-text rule: a record stamped BEFORE the send is
    not this send's landing ("ok" repeats), and the match is the whole collapsed text, never a substring.
    A PRIVATE synthetic sid (the shared placeholder is reserved for fixtures other modules journal
    against); the notes-api demo domain."""

    SID = "5a5a5a5a-6b6b-4c7c-8d8d-9e9e9e9e9e9e"
    SENT = ("Replying to this highlighted code (/tmp/notes-api/notes/api.py:42):\n"
            "> def list_notes():\n\nrename this to fetch_notes")
    T = 1_800_000_038          # the send (the echo's stamp)

    def setUp(self):
        self.state = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.state, "sdk"))
        os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(self.state, "claude")
        self.cwd = os.path.join(self.state, "proj")
        os.makedirs(self.cwd, exist_ok=True)
        self.tpath = sb.transcript_path(self.cwd, self.SID)
        os.makedirs(os.path.dirname(self.tpath), exist_ok=True)
        open(self.tpath, "w").close()

    def tearDown(self):
        os.environ.pop("CLAUDE_CONFIG_DIR", None)

    @staticmethod
    def _iso(t):
        return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def _user(self, t, text, uuid, parent):
        return {"type": "user", "timestamp": self._iso(t), "uuid": uuid, "parentUuid": parent,
                "promptSource": "sdk", "userType": "external", "isSidechain": False,
                "message": {"role": "user", "content": text}}

    def _att(self, t, prompt, uuid, parent):
        # the real record's key shape (keys only — content invented): no '"user"' literal anywhere,
        # `userType` is the near-miss; the prompt is a string or a content-block list
        return {"type": "attachment", "timestamp": self._iso(t), "uuid": uuid, "parentUuid": parent,
                "isSidechain": False, "userType": "external",
                "attachment": {"type": "queued_command", "prompt": prompt, "commandMode": "prompt",
                               "timestamp": int(t) * 1000}}

    def _qop(self, t, op, content=None):
        return {"type": "queue-operation", "timestamp": self._iso(t), "operation": op, "content": content}

    def _write(self, recs):
        with open(self.tpath, "w") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")

    def _running_turn(self):
        return [self._user(self.T - 38, "tighten the notes-api search", "u1", None),
                {"type": "assistant", "timestamp": self._iso(self.T - 28), "uuid": "a1", "parentUuid": "u1",
                 "message": {"role": "assistant", "content": [
                     {"type": "tool_use", "id": "tu_a1_0", "name": "Bash", "input": {"command": "true"}}],
                     "stop_reason": "tool_use"}}]

    def _splice(self, prompt=None, t=None):
        # the CLI's shape for a mid-turn splice: enqueue op (no uuid), the tool_result it waited for,
        # then the attachment stamped with the ENQUEUE time — and no user record for the text, ever
        return [self._qop(self.T, "enqueue", None),
                {"type": "user", "timestamp": self._iso(self.T + 12), "uuid": "tr1", "parentUuid": "a1",
                 "message": {"role": "user", "content": [
                     {"type": "tool_result", "tool_use_id": "tu_a1_0", "content": "ok"}]}},
                self._qop(self.T + 12, "remove"),
                self._att(t if t is not None else self.T, prompt if prompt is not None else self.SENT,
                          "att1", "tr1")]

    def _backend(self, echoes, queue=()):
        sb.write_reg(self.state, self.SID, {"sid": self.SID, "name": "web", "mode": "acceptEdits",
                                            "alive": True, "cwd": self.cwd, "lastSid": self.SID,
                                            "queue": list(queue), "echoes": echoes})
        return sb.SdkBackend(self.state, "/bin/true", lambda *a, **k: None)   # __init__ runs the reseed

    def _echo(self, text=None, t=None):
        return {"t": t if t is not None else self.T, "text": text if text is not None else self.SENT,
                "author": "human", "rompAuto": False, "dropped": False}

    def _queue(self):
        return (sb.read_reg(self.state, self.SID) or {}).get("queue") or []

    def _live(self, be):
        return list((be._live.get(self.SID) or {}).values())

    def test_the_attachment_only_transcript_counts_as_landed(self):
        self._write(self._running_turn() + self._splice())
        be = self._backend([])
        self.assertIs(be._text_landed(self.SID, self.SENT, self.T), True,
                      "the queued_command attachment IS the absorbed send's landing")

    def test_a_content_block_prompt_counts_too(self):
        # the SDK injection path writes the prompt as a content-block list, not a string
        self._write(self._running_turn() + self._splice(prompt=[{"type": "text", "text": self.SENT}]))
        be = self._backend([])
        self.assertIs(be._text_landed(self.SID, self.SENT, self.T), True)

    def test_boot_reseed_neither_refeeds_nor_flags_an_absorbed_send(self):
        # the F1 shape: the CLI spliced the message (attachment written), the kernel died before the
        # next merged build pruned the echo. Pre-fix: the echo was re-queued and the CLI ran it twice.
        self._write(self._running_turn() + self._splice())
        be = self._backend([self._echo()])
        self.assertEqual(self._queue(), [], "a landed send is never re-queued — the CLI would run it twice")
        live = self._live(be)
        self.assertEqual([a["_echo_text"] for a in live], [self.SENT], "the echo is reseeded, awaiting its prune")
        self.assertFalse(live[0].get("dropped"), "…and not flagged: it landed, it is merely un-pruned")
        self.assertFalse((sb.read_reg(self.state, self.SID).get("echoes") or [{}])[0].get("dropped"))
        # the next merged build lands the absorbed atom's text at the attachment's (enqueue) stamp
        be.prune_live(self.SID, tx_uuids=set(), tx_user_texts={self.SENT: self.T}, human_floor=self.T - 38)
        self.assertNotIn(self.SID, be._live, "the by-text prune retires it, exactly once")

    def test_a_multi_line_send_is_found_through_the_json_escaping(self):
        # the old raw-line prefilter looked for the collapsed text's first 60 chars in the raw JSON line,
        # where every newline is the two characters backslash-n — a quote chip's reply never matched
        self._write(self._running_turn() + [self._user(self.T + 3, self.SENT, "u2", "a1")])
        be = self._backend([])
        self.assertIs(be._text_landed(self.SID, self.SENT, self.T), True)

    def test_an_earlier_twin_of_the_text_is_not_this_sends_landing(self):
        # prune_live's T237b rule, mirrored: "ok" from an hour ago is not the landing of the "ok" the
        # dead CLI was holding — that send IS lost, and it goes back into the queue
        self._write([self._user(self.T - 3600, "ok", "u1", None)])
        be = self._backend([self._echo(text="ok")])
        self.assertIs(be._text_landed(self.SID, "ok", self.T), False)
        self.assertEqual(self._queue(), ["ok"], "re-delivered: the only record of the text predates the send")
        self.assertFalse(self._live(be)[0].get("dropped"))

    def test_a_record_at_the_send_second_counts(self):
        # the echo's stamp is minted before the CLI can see the text, so its record is at or after it —
        # the same second included (both stamps are whole seconds)
        self._write([self._user(self.T, "ok", "u1", None)])
        be = self._backend([])
        self.assertIs(be._text_landed(self.SID, "ok", self.T), True)

    def test_a_superstring_record_is_not_a_match(self):
        # the whole collapsed text, never a substring: a found echo is handed to the by-text prune, which
        # matches exactly — a substring "find" would leave an echo nothing ever prunes
        self._write([self._user(self.T + 2, "ok go ahead with the rename", "u1", None)])
        be = self._backend([])
        self.assertIs(be._text_landed(self.SID, "ok", self.T), False)

    def test_a_lost_send_with_only_its_enqueue_op_is_still_re_delivered(self):
        # the control: the CLI died holding the message — the enqueue op is on disk, no attachment, no
        # user record. Provably lost → back into the queue, as before.
        self._write(self._running_turn() + [self._qop(self.T, "enqueue", None)])
        be = self._backend([self._echo()])
        self.assertIs(be._text_landed(self.SID, self.SENT, self.T), False)
        self.assertEqual(self._queue(), [self.SENT])
        self.assertFalse(self._live(be)[0].get("dropped"), "re-queued renders as queued, never as lost")

    def test_an_unreadable_transcript_still_takes_the_flag_path(self):
        os.remove(self.tpath)
        be = self._backend([self._echo()])
        self.assertIsNone(be._text_landed(self.SID, self.SENT, self.T), "cannot read → no verdict")
        self.assertEqual(self._queue(), [], "never re-deliver on doubt")
        self.assertTrue(self._live(be)[0].get("dropped"), "…but the possible loss is shown, for a human call")

    def test_the_match_set_reads_both_record_shapes(self):
        # the helper _text_landed matches against: user text (string or blocks, joined AND per block —
        # romp bundles injected messages), and the queued_command prompt (string or blocks); nothing else
        self.assertEqual(sb._landed_texts({"type": "user", "message": {"content": " a  b "}}), {"a b"})
        self.assertEqual(sb._landed_texts({"type": "user", "message": {"content": [
            {"type": "text", "text": "one"}, {"type": "text", "text": "two"}]}}), {"one two", "one", "two"})
        self.assertEqual(sb._landed_texts({"type": "attachment", "attachment": {
            "type": "queued_command", "prompt": "x\ny"}}), {"x y"})
        self.assertEqual(sb._landed_texts({"type": "attachment", "attachment": {
            "type": "queued_command", "prompt": [{"type": "text", "text": "p"}]}}), {"p"})
        self.assertEqual(sb._landed_texts({"type": "attachment", "attachment": {"type": "total_tokens_reminder"}}), set())
        self.assertEqual(sb._landed_texts({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t", "content": "ok"}]}}), set())
        self.assertEqual(sb._landed_texts({"type": "assistant", "message": {"content": [{"type": "text", "text": "z"}]}}), set())


if __name__ == "__main__":
    unittest.main()
