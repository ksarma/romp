#!/usr/bin/env python3
"""One flaky tmux read must not read as mass death for the CHAT TAB LIST (2026-08-18).

list_lines collapses any exec error/timeout to [] — deliberately (the primitive stays lossy; each
consumer applies its own doctrine, and other consumers have theirs). The death writers already
refuse to inherit that collapse: alive_sids returns None on a REAL probe failure and they stand
down. The tab list had no doctrine at all: one collapsed read flowed through the pusher's snapshot
into _chat_tab_sessions, the push omitted every tmux session, and the client — for which the
continuous tabOrder push is the authority on what exists — tore them all down. The next push
re-listed ids whose sessions the client no longer held: the permanent dead-swirl strip
(seen on a remote host's tabs, 2026-08-18).

_tab_list_tmux mirrors the death writers' refusal for the tab list only: an empty tmux half where
the previous push had sessions is corroborated with alive_sids — an authoritative zero (no server /
no romp sessions) is adopted, a real probe failure carries the PREVIOUS push's tmux entries, loudly
(one log per episode), until a read answers again.

Round two (2026-08-18, the adversarial review): the guard's own corners inherited the collapse.
 - The BOOT corner: carry state is process memory, so a restart mid-episode adopted a collapsed
   empty read uncorroborated and the first push mass-dismissed every window. Now the empty-prev
   case probes too: an answering zero (or a genuinely tmux-less box) is adopted; an answering
   NON-zero seeds the carry with stub rows; a failed probe with nothing to carry returns the None
   sentinel and the pushers SKIP the chat leg for the cycle rather than assert an empty board.
 - An ANSWERING probe is authoritative mid-episode: carried sids it no longer lists are dropped
   and pruned from prev (they really died), instead of riding as live-looking tabs all episode.
 - A corroborated kill prunes prev at the kill site (_tab_carry_forget, via _record_death and the
   corroborated closed broadcasts), so a post-kill collapse can't resurrect the ended tab.
 - The carry is maintained EVERY pusher cycle, clients or not, so "previous push" is at most one
   cycle stale — never the hours-old world from before the last browser closed.

Round three (2026-08-18, the re-verification):
 - Readers SNAPSHOT the carry: _tab_carry_forget pops from prev on WS/HTTP handler threads while
   the pusher iterates it, and a size-changing pop mid-comprehension was a RuntimeError that killed
   the clientless pusher thread permanently (the :21193 call was the only bare site). The call is
   also belted like every sibling pusher job.
 - The boot-corner None sentinel keys to the DESTRUCTIVE frame (tabOrder), not the whole chat leg:
   the SDK half is in-process truth and its session frames keep flowing through the wedge — standing
   the leg down re-minted the stuck-spinner for healthy SDK sessions.
 - An answering probe is authoritative in BOTH directions: its answer IS the carried world, so
   newcomers spawned mid-episode are seeded in, and total turnover can't stale-empty the carry into
   the no-probe adopt branch (which disarmed the guard and logged a false 'recovered').
 - A corroborated kill leaves a TOMBSTONE that survives a stale healthy read re-adding the sid to
   prev; only proven revival (an answering probe listing it, or _revive_session) clears it.

SYNTHETIC fixtures only: placeholder UUIDs, invented names, hermetic temp STATE.
"""
import contextlib
import io
import json
import os
import tempfile
import unittest
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
km = load_source("romp_kernel_tabcarry", os.path.join(BIN, "romp-kernel"))
jd = km.jd

SID = "11111111-2222-3333-4444-555555555555"
ROW = {"state": "waiting", "since": 0, "model": "", "effort": "", "context": None,
       "compactPct": None, "color": None, "mode": "", "backend": "tmux"}
SDK_SID = "99999999-8888-7777-6666-555555555555"
SDK_ROW = {"state": "working", "since": 0, "model": "", "effort": "", "context": None,
           "compactPct": None, "color": None, "mode": "", "backend": "sdk"}


def reset_carry():
    km._tab_tmux_carry["prev"] = {}
    km._tab_tmux_carry["collapsed"] = False
    km._tab_tmux_carry["seeded"] = False
    km._tab_tmux_carry["dead"] = set()


class CollapseCarryUnit(unittest.TestCase):
    """_tab_list_tmux in isolation: adopt / corroborate / carry / seed / prune / recover."""

    def setUp(self):
        reset_carry()
        self.probes = []
        km._TMUX.available = lambda: True   # hermetic: never read whether THIS box has tmux

    def tearDown(self):
        for nm in ("available", "alive_sids"):
            km._TMUX.__dict__.pop(nm, None)   # instance attrs shadow the class methods; drop them
        reset_carry()

    def _probe(self, answer):
        def alive_sids(t=3):
            self.probes.append(1)
            return answer
        km._TMUX.alive_sids = alive_sids

    def _guard(self, tmux):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            out = km._tab_list_tmux(tmux)
        return out, err.getvalue()

    def test_a_healthy_read_passes_through_and_never_probes(self):
        self._probe(None)
        out, err = self._guard({SID: ROW})
        self.assertIn(SID, out)
        self.assertEqual(self.probes, [], "a non-empty read needs no corroboration")
        self.assertEqual(err, "")

    def test_a_collapsed_read_carries_the_previous_push_loudly_once(self):
        self._guard({SID: ROW})                       # the previous push's world
        self._probe(None)                             # a REAL probe failure — the ambiguous case
        out, err = self._guard({})
        self.assertIn(SID, out, "the collapse is carried — never an empty tab list from a failed read")
        self.assertIn("tab-list", err, "loud: the carry is logged")
        out2, err2 = self._guard({})                  # the episode continues…
        self.assertIn(SID, out2)
        self.assertEqual(err2, "", "…but logs once per episode, not once per cycle")

    def test_a_probe_that_sees_sessions_proves_the_collapse_and_carries(self):
        self._guard({SID: ROW})
        self._probe({SID})                            # list_lines collapsed, the corroboration answered
        out, _err = self._guard({})
        self.assertIn(SID, out, "an empty snapshot the probe contradicts is a collapse, not a death")

    def test_an_authoritative_zero_is_adopted_not_carried(self):
        self._guard({SID: ROW})
        self._probe(set())                            # no server / no romp sessions — the reboot shape
        out, err = self._guard({})
        self.assertNotIn(SID, out, "a genuine mass death must reach the client — carrying would keep dead tabs")
        n = len(self.probes)
        out2, _e = self._guard({})                    # the empty world persists…
        self.assertNotIn(SID, out2)
        self.assertEqual(len(self.probes), n, "…with nothing left to carry, no more corroboration probes")
        self.assertNotIn("carrying", err)

    def test_recovery_resumes_live_reads_and_says_so(self):
        self._guard({SID: ROW})
        self._probe(None)
        self._guard({})                               # the collapse episode starts
        out, err = self._guard({SID: ROW})            # a read answers again
        self.assertIn(SID, out)
        self.assertIn("recovered", err, "the episode's end is logged too")
        out2, err2 = self._guard({})
        # prev was refreshed by the healthy read, so a NEW collapse is a NEW episode with a new log
        self.assertIn(SID, out2)
        self.assertIn("tab-list", err2)

    def test_sdk_sessions_ride_through_a_carry_untouched(self):
        self._guard({SID: ROW})
        self._probe(None)
        out, _err = self._guard({SDK_SID: SDK_ROW})
        # the SDK half of the snapshot answered; only the tmux half collapsed — carry must MERGE,
        # never replace, or a tmux flake would tear down every SDK tab instead
        self.assertIn(SDK_SID, out)
        self.assertIn(SID, out)

    # ── the boot/restart corner (2026-08-18 round two): the empty-prev case corroborates too ──

    def test_boot_collapse_stands_down_with_a_sentinel_not_an_empty_board(self):
        # A fresh process (nothing seeded yet) whose first read collapses while the probe fails has
        # NOTHING trustworthy to say: None means "skip the chat push this cycle" — never an empty
        # adoption, which mass-dismissed every surviving window's tabs after a restart mid-episode
        # (pages outlive kernel restarts by design, and dismissSession destroys their drafts).
        self._probe(None)
        out, err = self._guard({})
        self.assertIsNone(out, "no trustworthy tab list → the sentinel, not an empty board")
        self.assertEqual(len(self.probes), 1, "the boot corner is corroborated now")
        self.assertIn("nothing to carry", err, "loud, so the skipped cycles are explicable")
        out2, err2 = self._guard({})
        self.assertIsNone(out2)
        self.assertEqual(err2, "", "…but logged once per episode")

    def test_boot_authoritative_zero_is_adopted_and_stops_probing(self):
        self._probe(set())                            # list-sessions answered: genuinely nothing alive
        out, err = self._guard({})
        self.assertEqual(out, {}, "an answering zero at boot is the truth — adopt it")
        self.assertNotIn("tab-list", err)
        n = len(self.probes)
        out2, _e = self._guard({})                    # the empty world persists…
        self.assertEqual(out2, {})
        self.assertEqual(len(self.probes), n, "…and the corroborated-empty world stops probing (seeded)")

    def test_headless_boot_adopts_the_empty_world_with_no_probe(self):
        # no tmux on the box: alive_sids would return None here too, and that must never read as a
        # collapse — empty IS the truth on a headless (SDK-only) box, silently, forever
        km._TMUX.available = lambda: False
        self._probe(None)
        out, err = self._guard({})
        self.assertEqual(out, {})
        self.assertEqual(self.probes, [], "no tmux → no probe, no episode")
        self.assertEqual(err, "")

    def test_a_restart_mid_episode_seeds_the_carry_from_an_answering_probe(self):
        # fresh carry (the restart), list read still collapsed, probe ANSWERS: the answer seeds
        # minimal stub rows, so the strip survives the episode's remainder instead of blanking
        self._probe({SID})
        out, _err = self._guard({})
        self.assertIn(SID, out, "the probe's answer is the world — listed, not torn down")
        self.assertEqual((out[SID] or {}).get("backend"), "tmux")
        self._probe(None)                             # the probe fails later in the same episode…
        out2, _e = self._guard({})
        self.assertIn(SID, out2, "…and the seeded carry holds the tab up")

    # ── an answering probe is authoritative mid-episode (2026-08-18 round two) ──

    def test_an_answering_probe_prunes_carried_sids_it_no_longer_lists(self):
        # prev={A,B}, probe answers {A}: B really died mid-episode. It must drop from the carried
        # map NOW — and from prev, so a later probe failure in the same episode can't resurrect it
        # (the death writers ride this same probe: a carried B would be a live tab over a dead lane).
        B = "22222222-3333-4444-5555-666666666666"
        self._guard({SID: ROW, B: ROW})               # the previous push's world
        self._probe({SID})
        out, _err = self._guard({})
        self.assertIn(SID, out)
        self.assertNotIn(B, out, "the probe is the corroboration authority — a sid it dropped is dead")
        self._probe(None)
        out2, _e = self._guard({})
        self.assertIn(SID, out2)
        self.assertNotIn(B, out2, "pruned from prev: a later probe failure cannot resurrect it")

    # ── a corroborated kill outranks the carry (2026-08-18 round two) ──

    def test_a_corroborated_kill_prunes_the_carry_at_the_kill_site(self):
        # the kill sites just PROVED death (_confirmed_ended) — _tab_carry_forget drops the sid so a
        # collapse in the very next cycle can't re-list the ended session and resurrect its tab
        self._guard({SID: ROW})
        km._tab_carry_forget(SID)
        self._probe(None)
        out, _err = self._guard({})
        self.assertNotIn(SID, out)

    def test_record_death_prunes_the_carry(self):
        # every _record_death caller corroborated the death (endSession, /end, the sweep's
        # gone/boot stamps) — the prune rides there so no kill site can forget it
        self._guard({SID: ROW})
        with contextlib.redirect_stderr(io.StringIO()):
            km._record_death(SID, int(km.time.time()), "kill")
        self.assertNotIn(SID, km._tab_tmux_carry["prev"])

    # ── an answering probe is authoritative in BOTH directions (2026-08-18 round three) ──

    def test_an_answering_probe_widens_the_carry_with_newcomers(self):
        # prev={A}, probe answers {A,B}: B was created DURING the episode (spawns are independent
        # execs that can succeed while list-sessions times out). The probe is the corroboration
        # authority in both directions — B must be listed now, and be in prev so it survives a
        # later probe failure in the same episode. The old carry only PRUNED when non-empty, so a
        # newcomer's tab stayed invisible for the whole wedge.
        B = "22222222-3333-4444-5555-666666666666"
        self._guard({SID: ROW})                       # the previous push's world
        self._probe({SID, B})
        out, _err = self._guard({})
        self.assertIn(SID, out)
        self.assertIn(B, out, "a probe-listed newcomer is seeded, never dropped")
        self.assertIn(B, km._tab_tmux_carry["prev"], "…and lands in prev, not just this cycle's map")
        self.assertEqual((out[SID] or {}).get("state"), "waiting", "survivors keep carried metadata")
        self._probe(None)                             # the probe fails later in the same episode…
        out2, _e = self._guard({})
        self.assertIn(B, out2, "…and the widened carry holds the newcomer up")

    def test_total_turnover_keeps_the_guard_armed_and_the_log_honest(self):
        # prev={A}, probe answers {B} (A killed outside romp, B spawned, all mid-episode): the old
        # prune-only carry went stale-empty, the NEXT collapsed cycle took the no-probe
        # adopt-and-stand-down branch and falsely logged 'recovered' — the guard disarmed for the
        # rest of the wedge, every later spawn invisible until list_lines itself healed. The
        # probe's world must be adopted wholesale instead.
        B = "22222222-3333-4444-5555-666666666666"
        C = "33333333-4444-5555-6666-777777777777"
        self._guard({SID: ROW})
        self._probe({B})
        out, _err = self._guard({})
        self.assertNotIn(SID, out, "the probe dropped A — it really died")
        self.assertIn(B, out, "…and its full answer is the carried world")
        n = len(self.probes)
        out2, err2 = self._guard({})                  # the wedge continues
        self.assertGreater(len(self.probes), n, "still collapsed → still probing — never the "
                                                "no-probe adopt that disarmed the guard")
        self.assertNotIn("recovered", err2, "no false recovery log while the read is still failing")
        self.assertIn(B, out2)
        self._probe({B, C})                           # a later spawn during the same episode
        out3, _e = self._guard({})
        self.assertIn(C, out3, "later newcomers keep landing")

    # ── cross-thread safety: a kill landing mid-cycle must never blow up the reader (round three) ──

    def test_a_forget_landing_mid_comprehension_does_not_raise(self):
        # _tab_carry_forget pops from prev on WS/HTTP handler threads while the pusher's guard
        # iterates the carry. Deterministic interleave: the probe's answer runs _tab_carry_forget
        # from inside the very iteration that consumes it — each membership/iteration step is a
        # moment another thread's pop can land. Pre-fix (the reader iterated the live dict) this
        # raised RuntimeError('dictionary changed size during iteration'); on the clientless pusher
        # path nothing caught it and the pusher thread died permanently. Readers snapshot now.
        B = "22222222-3333-4444-5555-666666666666"
        C = "33333333-4444-5555-6666-777777777777"
        self._guard({SID: ROW, B: ROW, C: ROW})       # the previous push's world (three sids)

        class ForgetsMidIteration(set):               # a kill gate fires during the reader's pass
            def __contains__(inner, s):
                km._tab_carry_forget(C)
                return set.__contains__(inner, s)

            def __iter__(inner):
                km._tab_carry_forget(C)
                return set.__iter__(inner)

        km._TMUX.alive_sids = lambda t=3: ForgetsMidIteration({SID, B})
        out, _err = self._guard({})                   # must not raise
        self.assertIn(SID, out)
        self.assertIn(B, out)
        self.assertNotIn(C, out, "the concurrently-killed sid stays dead")

    def test_the_clientless_pusher_survives_a_guard_exception(self):
        # The clientless maintain call is the ONLY bare _tab_list_tmux site — an escape there rode
        # _pusher_cycle's try/finally into _pusher's while-True and killed the daemon thread: no
        # pushes, no death sweep, no auto-nudge, no awaiting-lift until a kernel restart, while
        # HTTP/WS kept serving. Belted like every sibling job, and loud.
        jobs = ["_lift_spent_awaiting", "_death_sweep_tick", "_deferral_sweep_tick",
                "_auto_nudge_tick", "_interrupt_block_tick", "_auto_pause_on_limit",
                "_auto_pause_on_spend_limit", "_auto_resume_retry", "_auto_resume_session_retry",
                "_auto_retry_tick", "_clear_done_working_notes"]
        saved = {nm: getattr(km, nm) for nm in jobs}
        saved_guard = km._tab_list_tmux

        def boom(tmux):
            raise RuntimeError("dictionary changed size during iteration")

        try:
            for nm in jobs:
                setattr(km, nm, lambda *a, **k: None)
            km._tab_list_tmux = boom
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                km._pusher_cycle_jobs(int(km.time.time()), {}, any_client=False)   # must not raise
            self.assertIn("tab-carry maintain", err.getvalue(), "caught loudly, never silently")
        finally:
            km._tab_list_tmux = saved_guard
            for nm, fn in saved.items():
                setattr(km, nm, fn)

    # ── the kill tombstone: a stale healthy read can't resurrect a corroborated kill (round three) ──

    def test_a_stale_healthy_read_cannot_resurrect_a_corroborated_kill(self):
        # Interleave: the pusher snapshots liveness BEFORE the kill lands, the kill gate
        # corroborates and forgets, THEN the in-flight cycle's healthy read assigns prev from the
        # stale snapshot that still lists the sid. The pop alone was lost — prev re-added the sid —
        # and the next collapse re-carried the just-killed session: the dismiss/resurrect flap the
        # forget exists to prevent. The tombstone survives the overwrite.
        B = "22222222-3333-4444-5555-666666666666"
        self._guard({SID: ROW, B: ROW})               # a healthy cycle
        km._tab_carry_forget(SID)                     # the kill gate proves death…
        self._guard({SID: ROW, B: ROW})               # …but a STALE healthy read still lists it
        self.assertIn(SID, km._tab_tmux_carry["prev"], "the stale read really did re-add it")
        self._probe(None)
        out, _err = self._guard({})                   # collapse, probe fails → the carry
        self.assertNotIn(SID, out, "the tombstone keeps the corroborated kill out of the carry")
        self.assertIn(B, out, "…without costing the genuinely-carried survivor")

    def test_an_answering_probe_clears_the_tombstone(self):
        # Revival proof #1: the probe lists the sid alive NOW — the corroboration authority
        # outranks whatever a kill gate proved earlier, so the sid may be carried again.
        B = "22222222-3333-4444-5555-666666666666"
        self._guard({SID: ROW, B: ROW})
        km._tab_carry_forget(SID)
        self._probe({SID, B})
        out, _err = self._guard({})
        self.assertIn(SID, out, "probe-listed → alive again, the tombstone is outranked")
        self.assertNotIn(SID, km._tab_tmux_carry["dead"])
        self._probe(None)
        out2, _e = self._guard({})
        self.assertIn(SID, out2, "…and later carries may list it again")

    def test_a_revive_clears_the_tombstone(self):
        # Revival proof #2: _revive_session respawns the sid — the tombstone must clear or the
        # revived session's tab vanishes again on the next collapse.
        km._tab_carry_forget(SID)
        self.assertIn(SID, km._tab_tmux_carry["dead"])
        saved = {nm: getattr(km, nm) for nm in
                 ("_sdk", "_commands_for_cwd", "_push_all", "_reveal_chat_for", "_name_of", "_cwd_of")}

        class FakeSdk:                                # a resume that succeeds, no real backend
            def owns(self, sid):
                return True

            def resume(self, name, sid):
                return True

            def connect(self, sid):
                return True

        try:
            km._sdk = lambda: FakeSdk()
            km._commands_for_cwd = lambda cwd: None
            km._push_all = lambda *a, **k: None
            km._reveal_chat_for = lambda *a, **k: None
            km._name_of = lambda sid: "web"
            km._cwd_of = lambda sid: None
            km._revive_session(SID)
        finally:
            for nm, fn in saved.items():
                setattr(km, nm, fn)
        self.assertNotIn(SID, km._tab_tmux_carry["dead"], "a proven revival clears the tombstone")

    # ── the carry is maintained on clientless cycles too (2026-08-18 round two) ──

    def test_a_clientless_cycle_still_maintains_the_carry(self):
        # With no client holding want_chat/want_fleet, prev used to freeze at the last chat push's
        # world — hours stale once every browser closed — and a reconnect during a collapse
        # re-listed long-dead sessions as live tabs. The pusher runs the guard every cycle now.
        jobs = ["_lift_spent_awaiting", "_death_sweep_tick", "_deferral_sweep_tick",
                "_auto_nudge_tick", "_interrupt_block_tick", "_auto_pause_on_limit",
                "_auto_pause_on_spend_limit", "_auto_resume_retry", "_auto_resume_session_retry",
                "_auto_retry_tick", "_clear_done_working_notes"]
        saved = {nm: getattr(km, nm) for nm in jobs}
        try:
            for nm in jobs:
                setattr(km, nm, lambda *a, **k: None)
            self._guard({SID: ROW})                   # the last push before every browser closed
            self._probe(set())                        # the session ends while nobody is connected…
            km._pusher_cycle_jobs(int(km.time.time()), {}, any_client=False)
            self._probe(None)                         # …then a client reconnects during a collapse
            out, _err = self._guard({})
            self.assertNotIn(SID, out,
                             "the clientless cycle refreshed prev — the dead sid must not come back")
        finally:
            for nm, fn in saved.items():
                setattr(km, nm, fn)


class CollapseCarryThroughPush(unittest.TestCase):
    """The seam end-to-end: a collapsed cycle's PUSH must still list the previous cycle's tmux
    sessions in tabOrder (the frame the client treats as authoritative for teardown)."""

    def setUp(self):
        reset_carry()
        self.td = tempfile.TemporaryDirectory()
        td = Path(self.td.name)
        self.saved = (jd.NAMES, jd.PROJECTS, jd.CAPDIR, jd.ARCHDIR, jd.GOALDIR, jd.STATE,
                      km.NAMES, km._sdk, km._cached_feed, km._fleet_view_sig)
        names = td / "names"; names.mkdir()
        proj = td / "projects"; proj.mkdir()
        jd.NAMES, jd.PROJECTS = names, proj
        jd.CAPDIR, jd.ARCHDIR, jd.GOALDIR = td / "captions", td / "archive", td / "goals"
        for d in (jd.CAPDIR, jd.ARCHDIR, jd.GOALDIR):
            d.mkdir()
        jd.STATE = td
        km.NAMES = names
        km._sdk = lambda: None
        km._cached_feed = lambda *a, **k: None      # the feed leg is not under test
        km._fleet_view_sig = lambda *a, **k: None
        cdir = td / "work"; cdir.mkdir()
        pdir = proj / jd.re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(str(cdir)))
        pdir.mkdir(parents=True)
        rec = {"type": "user", "timestamp": "2026-06-11T00:00:00.000Z", "uuid": "u1",
               "parentUuid": None, "promptSource": "typed",
               "message": {"role": "user", "content": "hello there"}}
        (pdir / (SID + ".jsonl")).write_text(json.dumps(rec) + "\n")
        (names / SID).write_text("web\t%s\t#abcdef\n" % str(cdir))
        rec2 = {"type": "user", "timestamp": "2026-06-11T00:00:01.000Z", "uuid": "u2",
                "parentUuid": None, "promptSource": "typed",
                "message": {"role": "user", "content": "hello api"}}
        (pdir / (SDK_SID + ".jsonl")).write_text(json.dumps(rec2) + "\n")
        (names / SDK_SID).write_text("api\t%s\t#123456\n" % str(cdir))
        km._TMUX.available = lambda: True   # hermetic: never read whether THIS box has tmux

    def tearDown(self):
        (jd.NAMES, jd.PROJECTS, jd.CAPDIR, jd.ARCHDIR, jd.GOALDIR, jd.STATE,
         km.NAMES, km._sdk, km._cached_feed, km._fleet_view_sig) = self.saved
        for nm in ("available", "alive_sids"):
            km._TMUX.__dict__.pop(nm, None)
        reset_carry()
        self.td.cleanup()

    def _push_frames(self, tmux):
        frames = []
        client = {"app": "chat", "alive": True, "wid": "", "qbytes": 0,
                  "send": lambda s: frames.append(json.loads(s)), "sent": {}, "echat": {}}
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._push([client], tmux=tmux)
        return frames, err.getvalue()

    def _push_orders(self, tmux):
        frames, err = self._push_frames(tmux)
        return [f["order"] for f in frames if f.get("type") == "tabOrder"], err

    def test_one_collapsed_cycle_does_not_omit_the_board_and_recovery_resumes(self):
        orders, _e = self._push_orders({SID: ROW})              # a healthy cycle: the tab exists
        self.assertTrue(orders and SID in orders[-1], "healthy baseline lists the session")
        km._TMUX.alive_sids = lambda t=3: None                  # the next read collapses for real
        orders, err = self._push_orders({})
        self.assertTrue(orders and SID in orders[-1],
                        "the collapsed cycle's push carries the previous set — the client must never "
                        "see the one-push omission that tears every tab down")
        self.assertIn("tab-list", err, "and says so, once")
        km._TMUX.alive_sids = lambda t=3: set()                 # …later, an authoritative zero
        orders, _e = self._push_orders({})
        self.assertTrue(orders and SID not in orders[-1],
                        "a corroborated empty board flows through — dead sessions really do drop")

    def test_a_boot_collapse_cycle_emits_no_tab_order_frame(self):
        # restart-during-stall (2026-08-18 round two): fresh carry + collapsed read + failed probe.
        # The push must emit NO tabOrder frame at all — an EMPTY one is the mass teardown (every
        # surviving window's kernelListed ids get dismissed, drafts destroyed); no frame means
        # clients keep what they hold and a fresh page keeps its loading state until a read answers.
        km._TMUX.alive_sids = lambda t=3: None
        orders, err = self._push_orders({})
        self.assertEqual(orders, [], "an untrustworthy cycle pushes no tab list at all")
        self.assertIn("nothing to carry", err)
        km._TMUX.alive_sids = lambda t=3: {SID}                 # the probe recovers mid-episode…
        orders, _e = self._push_orders({})
        self.assertTrue(orders and SID in orders[-1],
                        "…and its answer seeds the carry: the next push lists the session again")

    # ── the sentinel keys to the destructive frame, never the whole leg (2026-08-18 round three) ──

    def test_a_boot_collapse_starves_only_the_tmux_half_never_sdk_sessions(self):
        # Restart-during-wedge with all real work in SDK sessions (the recommended backend): the
        # sentinel is ABOUT the tmux half — the SDK half is in-process truth and never inherits a
        # tmux collapse. Standing the whole chat leg down re-minted the stuck-spinner for healthy
        # SDK sessions: a fresh dashboard sat on its loading state for as long as the probe stayed
        # mute. Only the DESTRUCTIVE frame (tabOrder, whose omission tears down) stays keyed to
        # the sentinel; the SDK session's frames flow.
        km._TMUX.alive_sids = lambda t=3: None                  # fresh carry + collapsed read + mute probe
        frames, err = self._push_frames({SDK_SID: SDK_ROW})
        self.assertEqual([f for f in frames if f.get("type") == "tabOrder"], [],
                         "no tabOrder frame — an omitting one is the mass teardown")
        self.assertIn(SDK_SID, [f.get("id") for f in frames if f.get("type") == "session"],
                      "the SDK session's frame flows through the wedge")
        self.assertIn("nothing to carry", err)
        km._TMUX.alive_sids = lambda t=3: {SID}                 # the probe answers mid-episode…
        frames2, _e = self._push_frames({SDK_SID: SDK_ROW})
        orders = [f["order"] for f in frames2 if f.get("type") == "tabOrder"]
        self.assertTrue(orders and SID in orders[-1] and SDK_SID in orders[-1],
                        "…and the next push re-lists BOTH halves")

    def test_push_session_now_reaches_an_sdk_target_through_the_sentinel(self):
        # The `romp new` seam: a just-created SDK session's guaranteed targeted push used to be
        # swallowed whole by the boot-corner sentinel — the one tab the creator was staring at
        # never painted. A non-tmux target is in-process truth: it proceeds with the SDK-half map
        # and sends the session frame ONLY (no tabOrder — the destructive frame stays keyed to
        # the sentinel; the client's upsert paints the tab).
        km._TMUX.alive_sids = lambda t=3: None                  # the boot-corner sentinel is active
        saved_snap = km._tmux_sessions
        frames = []
        client = {"app": "chat", "alive": True, "wid": "", "qbytes": 0,
                  "send": lambda s: frames.append(json.loads(s)), "sent": {}, "echat": {}}
        try:
            km._tmux_sessions = lambda: {SDK_SID: SDK_ROW}
            with km._clients_lock:
                km._clients.append(client)
            with contextlib.redirect_stderr(io.StringIO()):
                km._push_session_now(SDK_SID)
        finally:
            km._tmux_sessions = saved_snap
            with km._clients_lock:
                km._clients[:] = [c for c in km._clients if c is not client]
        self.assertEqual([f for f in frames if f.get("type") == "tabOrder"], [],
                         "never a tabOrder from a sentinel cycle's partial list")
        self.assertIn(SDK_SID, [f.get("id") for f in frames if f.get("type") == "session"],
                      "the targeted push reaches the SDK session anyway")


if __name__ == "__main__":
    unittest.main()
