#!/usr/bin/env python3
"""_interrupt_marks on the pusher thread: the narrowing (P2 S1/S2, 2026-09-06) and the memo (P2).

The tick, build_feed and the user-todo floor each tallied a session's user atoms every cycle: a
flatten, a per-atom is_interrupt_record text join (most of the cost, and most user records are
tool_result-only harness lines that can never be an interrupt record or a human prompt), and the
floor's call was a second full scan over the very turns the card's badge had just read.

S1 drops the atoms the file adapter marked text-less (author None) before the text scan; exact,
because author_of returns None on no other shape. S2 hands build_feed's badge read into the floor.
The memo keys on the parse object's identity plus the machineCut stamp, per (sid, parse family).

Synthetic fixtures only: placeholder UUIDs, invented prompt text, hostname-free paths.
"""
import inspect
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
em = SourceFileLoader("romp_event_model_imm", os.path.join(BIN, "romp-event-model")).load_module()
SourceFileLoader("romp_judge_imm", os.path.join(BIN, "romp-judge")).load_module()
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
km = SourceFileLoader("romp_kernel_imm", os.path.join(BIN, "romp-kernel")).load_module()
sb = SourceFileLoader("romp_sdk_backend_imm", os.path.join(BIN, "romp_sdk_backend.py")).load_module()
jd = km.jd

NOW = 1781100000
# A sid of this module's own (the goal-store fixture rule, 2026-08-24): the override journal is
# per-sid and process-shared across every kernel test copy.
SID = "11111111-2222-3333-4444-777777777777"
T0 = NOW - 3600


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def uline(t, text, uuid, parent=None):
    return {"type": "user", "timestamp": iso(t), "uuid": uuid, "parentUuid": parent,
            "promptSource": "typed", "message": {"role": "user", "content": text}}


def aline(t, text, uuid, parent, stop):
    return {"type": "assistant", "timestamp": iso(t), "uuid": uuid, "parentUuid": parent,
            "message": {"role": "assistant", "content": [{"type": "text", "text": text}], "stop_reason": stop}}


def uatom(t, text, author="human"):
    return {"type": "user", "t": t, "author": author, "message": {"role": "user", "content": text}}


def intr(t):
    return uatom(t, "[Request interrupted by user]", author="human")


def tool_result_atom(t):
    """The file adapter's shape for a tool_result-only harness line: author None, no text block."""
    return {"type": "user", "t": t, "author": None,
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "tu1",
                                                     "content": "ok"}]}}


class _Counter:
    """Wrap a module attribute with a call counter; restore on close."""

    def __init__(self, mod, name):
        self.mod, self.name, self.orig, self.calls = mod, name, getattr(mod, name), []

        def wrapped(*a, **k):
            self.calls.append((a, k))
            return self.orig(*a, **k)
        setattr(mod, name, wrapped)

    def close(self):
        setattr(self.mod, self.name, self.orig)


class AuthorNoneAtomsAreSkipped(unittest.TestCase):
    """S1: a user atom the file adapter marked author None (a text-less record) is dropped before the
    text scan. No tally changes; the per-atom text join is what goes."""

    def test_a_text_less_author_none_atom_never_changes_the_marks(self):
        base = [uatom(T0, "wire the thing"), intr(T0 + 60)]
        with_tr = [uatom(T0, "wire the thing"), tool_result_atom(T0 + 30), intr(T0 + 60),
                   tool_result_atom(T0 + 70), tool_result_atom(T0 + 80)]
        self.assertEqual(km._interrupt_marks_atoms(with_tr), km._interrupt_marks_atoms(base))
        # …and past the stop: a genuine stop with only harness lines after it is still the user's
        self.assertEqual(km._interrupt_marks_atoms(with_tr), (T0 + 60, T0))

    def test_a_text_less_atom_between_the_stop_and_the_notice_stays_wedge(self):
        # the forward scan read such an atom as wedge before; dropping it reads the same notice
        atoms = [uatom(T0, "wire the thing"), intr(T0 + 60), tool_result_atom(T0 + 61),
                 uatom(T0 + 62, sb.BOOT_RESUME_NUDGE, "romp")]
        self.assertEqual(km._interrupt_marks_atoms(atoms), (0, T0),
                         "the machine cut is still named by the notice past the harness line")
        atoms = [uatom(T0, "wire the thing"), intr(T0 + 60), tool_result_atom(T0 + 61)]
        self.assertEqual(km._interrupt_marks_atoms(atoms, cut_t=T0 + 64, cut_cause="restart"), (0, T0),
                         "the stamp still settles an inconclusive scan that ends in harness lines")

    def test_a_tool_result_only_atom_is_never_text_scanned(self):
        c = _Counter(km.em, "is_interrupt_record")
        try:
            atoms = [uatom(T0, "wire the thing")] + [tool_result_atom(T0 + i) for i in range(1, 40)] + \
                    [intr(T0 + 60), tool_result_atom(T0 + 61)]
            km._interrupt_marks_atoms(atoms)
            self.assertEqual(len(c.calls), 2, "only the two authored atoms reach is_interrupt_record")
        finally:
            c.close()

    def test_an_atom_without_an_author_key_is_still_classified(self):
        # an SDK live-tail atom (msg_to_atom) carries no author key at all; absence is not the
        # adapter's no-text marker, so the atom is examined exactly as before
        live_stop = {"type": "user", "t": T0 + 90,
                     "message": {"role": "user", "content": "[Request interrupted by user]"}}
        atoms = [uatom(T0, "wire the thing"), live_stop]
        self.assertEqual(km._interrupt_marks_atoms(atoms), (T0 + 90, T0))

    def test_author_none_means_no_text_in_the_file_adapter(self):
        # the exactness claim, checked against author_of itself: across every promptSource the
        # adapter sees, a None author is returned ONLY for a content list with no text block
        texty = [{"type": "text", "text": "hello there"}]
        stop = [{"type": "text", "text": "[Request interrupted by user]"}]
        tr_only = [{"type": "tool_result", "tool_use_id": "tu1", "content": "ok"}]
        for blocks in (texty, stop, tr_only, []):
            for ps in (None, "typed", "queued", "sdk", "system"):
                for sdk_human in (False, True):
                    a = em.author_of(blocks, ps, {}, sdk_human)
                    if a is None:
                        self.assertEqual(em._text_of(blocks), "",
                                         "author None with text present would make S1 inexact (%r %r)" % (blocks, ps))
                    if em._text_of(blocks):
                        self.assertIsNotNone(a, "every branch on a non-empty text returns an author (%r)" % ps)


class FloorReusesTheBadgeRead(unittest.TestCase):
    """S2: _user_todo_idle takes the caller's interrupt read instead of scanning the same turns again;
    an unknown (None) read still computes, and build_feed hands its badge value through."""

    def setUp(self):
        self.saved = (km._compacting_now, km._backend_queued, km._backend_rewind_pending, km._last_state,
                      dict(km._pending_ops))
        km._compacting_now = lambda sid, **k: False
        km._backend_queued = lambda sid: False
        km._backend_rewind_pending = lambda sid: False
        km._last_state = lambda sid: (None, 0)
        km._pending_ops.clear()
        self.ps = {"turns": [{"id": "t1", "t": T0, "end": T0 + 20, "ended": True, "trigger": None,
                              "atoms": [uatom(T0, "wire the thing"), intr(T0 + 60)]}]}

    def tearDown(self):
        (km._compacting_now, km._backend_queued, km._backend_rewind_pending, km._last_state, pend) = self.saved
        km._pending_ops.clear()
        km._pending_ops.update(pend)

    def _idle(self, **kw):
        return km._user_todo_idle(SID, self.ps, False, None, "", None, None, **kw)

    def test_a_known_read_is_not_recomputed(self):
        c = _Counter(km, "_interrupt_suppresses_nudge")
        try:
            self.assertTrue(self._idle(interrupted=False), "not interrupted, everything else quiet → idle")
            self.assertFalse(self._idle(interrupted=True), "the caller's own read gates the floor")
            self.assertEqual(c.calls, [], "a known read is never scanned again")
        finally:
            c.close()

    def test_an_unknown_read_is_computed_here(self):
        c = _Counter(km, "_interrupt_suppresses_nudge")
        try:
            self.assertFalse(self._idle(interrupted=None), "these turns end in a genuine stop → not idle")
            self.assertEqual(len(c.calls), 1)
            self.assertFalse(self._idle(), "the default is the unknown read")
        finally:
            c.close()

    def test_a_raising_read_still_reads_not_idle(self):
        saved = km._interrupt_suppresses_nudge
        km._interrupt_suppresses_nudge = lambda turns, sid="", **k: 1 / 0
        try:
            self.assertFalse(self._idle(interrupted=None), "an unreadable gate reads unknown, never idle")
        finally:
            km._interrupt_suppresses_nudge = saved

    def test_build_feed_hands_its_badge_read_to_the_floor(self):
        src = inspect.getsource(km.build_feed)
        self.assertIn("interrupted=_intr_read", src, "the floor call carries the badge's own read")
        self.assertIn("sess_interrupted, _intr_read = False, None", src,
                      "a raised badge read hands the floor None (compute), never False (idle)")


class OneScanPerSessionPerBuild(unittest.TestCase):
    """Through the real parse: with a user todo open, build_feed scans a session's user atoms ONCE —
    the badge's read; the floor reuses it."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        td = Path(self.td.name)
        cdir = td / "launchdir"; cdir.mkdir()
        proj = td / "projects"
        pdir = proj / jd.re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(str(cdir)))
        pdir.mkdir(parents=True)
        self.tpath = pdir / (SID + ".jsonl")
        names = td / "names"; names.mkdir()
        (names / SID).write_text("api\t%s\t#abcdef\n" % str(cdir))
        self.saved = (jd.STATE, jd.NAMES, jd.PROJECTS, jd.GOALDIR, jd.STATESDIR, km.NAMES, jd.CLOSER_ON)
        jd._rebind_state(td)
        jd.NAMES, jd.PROJECTS = names, proj
        km.NAMES = names
        jd.CLOSER_ON = False
        jd.GOALDIR.mkdir(parents=True)
        km._parse_cache.clear()
        km._machine_cut_cache.clear()
        km._pending_ops.clear()
        (td / km.USER_TODOS_SWITCH_FILE).write_text(json.dumps({"enabled": True, "gt": 1}))
        (td / "user-todos.json").write_text(json.dumps({SID: [
            {"id": "ut-aaaaaaaa", "text": "which host for prod?", "createdT": NOW - 100}]}))
        recs = [uline(T0, "wire up the reconnect banner", "u1"),
                aline(T0 + 20, "done, which host do you want for prod?", "a1", "u1", "end_turn")]
        self.tpath.write_text("\n".join(json.dumps(r) for r in recs) + "\n")
        g = {"id": SID + ":g1", "text": "Ship the reconnect banner", "parentId": None, "nodeComplete": False,
             "blocked": False, "cleared": False, "trail": [], "t": T0}
        (jd.GOALDIR / (SID + ".json")).write_text(json.dumps(
            {"rompUuid": SID, "seq": 1, "lastNode": g["id"], "closedTurns": [], "nodes": {g["id"]: g},
             "placements": {}, "status": {g["id"]: "working"}}))
        self.tmux = {SID: {"state": "idle", "since": NOW - 100, "model": "", "effort": "",
                           "context": None, "compactPct": None, "color": None}}

    def tearDown(self):
        state = self.saved[0]
        jd._rebind_state(state)
        (jd.STATE, jd.NAMES, jd.PROJECTS, jd.GOALDIR, jd.STATESDIR, km.NAMES, jd.CLOSER_ON) = self.saved
        km._parse_cache.clear()
        km._machine_cut_cache.clear()
        km._pending_ops.clear()
        self.td.cleanup()

    def test_the_floor_runs_and_the_scan_happens_once(self):
        km._parse(str(self.tpath), SID, NOW)                       # warm the cache (stands in for _warm_fleet_bg)
        floor = _Counter(km, "_user_todo_idle")
        scan = _Counter(km, "_interrupt_suppresses_nudge")
        try:
            feed = km.build_feed(NOW, self.tmux)
            self.assertTrue(any(a.get("sid") == SID for a in feed.get("asks") or []), "the session built")
            self.assertEqual(len(floor.calls), 1, "the floor ran for the session with an open todo")
            self.assertEqual(floor.calls[0][1].get("interrupted"), False, "…handed the badge's read")
            self.assertEqual(len(scan.calls), 1, "one user-atom scan per session per build")
        finally:
            scan.close(); floor.close()


if __name__ == "__main__":
    unittest.main()
