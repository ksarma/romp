#!/usr/bin/env python3
"""WS heartbeat + client staleness watchdog (the user 2026-06-29). The pusher DEDUPS, so a quiet fleet sends
no view frames; a client whose socket goes SILENTLY half-open (TCP dead, no onclose) then receives nothing and
never recovers — the feed froze on stale cards (a 'blocked in picker' card that the session had long left)
until a manual reload. Fix: the kernel sends a tiny 'ka' keepalive to every client on a fixed cadence, and the
page shim stamps lastRecv on every frame + a watchdog force-reconnects (→ reload-resync) when it stops arriving.

Synthetic only — no real session data.
"""
import json
import os
import unittest
from romp_load import load_source
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))

KSRC = open(os.path.join(BIN, "romp-kernel"), encoding="utf-8").read()


class Keepalive(unittest.TestCase):
    def setUp(self):
        self._saved = list(km._clients)

    def tearDown(self):
        km._clients[:] = self._saved

    def test_keepalive_sends_a_ka_frame_to_every_client(self):
        got_a, got_b = [], []
        km._clients[:] = [
            {"app": "feed", "wid": "", "send": got_a.append, "alive": True},
            {"app": "timeline", "wid": "", "send": got_b.append, "alive": True},
        ]
        km._keepalive_all()
        dv = km._dist_ver()
        self.assertEqual([json.loads(x) for x in got_a], [{"type": "ka", "dv": dv}], "feed client got one keepalive")
        self.assertEqual([json.loads(x) for x in got_b], [{"type": "ka", "dv": dv}], "timeline client too — every app, not just one")

    def test_keepalive_marks_a_broken_client_not_alive(self):
        def boom(_s):
            raise OSError("broken pipe")
        c = {"app": "feed", "wid": "", "send": boom, "alive": True}
        km._clients[:] = [c]
        km._keepalive_all()                              # must not raise; a dead socket is flagged for reaping
        self.assertFalse(c["alive"], "a send failure marks the client dead (reaped by the pusher), not crash the loop")


class ShimWatchdogSourcePins(unittest.TestCase):
    # Source-level pins: the shim JS is embedded in the kernel and not unit-runnable here, so assert the
    # heartbeat/watchdog wiring is present (mirrors the chat-compacting-icon source-pin style).
    def test_keepalive_lives_on_its_own_thread(self):
        # 2026-07-20: the beat moved OFF the pusher loop. Inline, a heavy _push_all under GIL contention
        # could stretch one pusher iteration past the shim's STALE_MS and the client force-closed a
        # healthy socket — the false "disconnected / reconnecting" banner. Pin the new wiring: a
        # dedicated _heartbeat thread, started at boot, and the pusher carrying NO inline beat.
        # (Behavior — beats on cadence with no pusher at all — is covered in test_heartbeat_thread.py.)
        self.assertIn("KEEPALIVE_S", KSRC)
        self.assertIn("def _heartbeat", KSRC)
        self.assertIn("threading.Thread(target=_heartbeat, daemon=True).start()", KSRC)
        pusher_src = KSRC.split("def _pusher(", 1)[1].split("\ndef ", 1)[0]   # the loop takes a clock and a wake for its tests
        self.assertNotIn("_keepalive_all", pusher_src, "the pusher must never grow the inline beat back")

    def test_the_one_shared_shim_stamps_lastrecv_and_watchdog_reconnects(self):
        # ONE shim serves every pane — the timeline's former hand-rolled copy (a second lastRecv/STALE_MS
        # watchdog) is gone; it now rides _shim("timeline") + federation like chat/feed/fleet. Pin the
        # watchdog wiring in the shared shim AND that no second copy has crept back in.
        self.assertEqual(KSRC.count("var lastRecv=0;var STALE_MS=30000;"), 1,
                         "still ONE shim — the anti-duplicate guard (no second hand-rolled copy)")
        # onopen + onmessage + the Page Lifecycle `resume` stamp (2026-09-07): a thawed tab's lastRecv only
        # said "JS did not run", so a healthy OPEN socket read as dead and was redialed on every return
        self.assertGreaterEqual(KSRC.count("lastRecv=Date.now()"), 3)
        self.assertIn('document.addEventListener("resume",function(){resumedAt=Date.now();', KSRC)
        self.assertIn("if(ws&&ws.readyState===1&&!(frozeAt&&frozeAt-lastRecv>STALE_MS)){lastRecv=Date.now();resumeProvisional=lastRecv;}});", KSRC,
                      "only an OPEN socket that was in time at the freeze earns the stamp, and only provisionally (review find, 2026-09-08)")
        # the staleness threshold is used TWICE within the one shim: the 5s interval watchdog AND the
        # visibilitychange fast-path (a foregrounded tab checks freshness at once — since 2026-09-07 it
        # names that verdict `stale` and files it as the return row's decision, still one test). Both live
        # in _shim, so the single-shim guard above still holds. Since 2026-09-08 the watchdog reads its bound
        # through `bound`: PROVISIONAL_MS (1.5 keepalive periods) while a resumed keep awaits a confirming frame,
        # STALE_MS otherwise, so the literal appears once and the watchdog's line once.
        self.assertEqual(KSRC.count("Date.now()-lastRecv>STALE_MS"), 1)
        self.assertEqual(KSRC.count("var bound=resumeProvisional?PROVISIONAL_MS:STALE_MS;if(everConnected&&Date.now()-lastRecv>bound)"), 1)
        self.assertEqual(KSRC.count("var PROVISIONAL_MS=15000,resumeProvisional=0;"), 1)
        self.assertNotIn("new WebSocket", km._TIMELINE_BOOT, "the timeline boot owns no socket of its own")

    def test_shim_ignores_the_keepalive_frame(self):
        # the ka frame never reaches the bundles: the shim consumes it (build-drift check, the stale rule,
        # then RETURN). Pinned as the exact branch text INCLUDING its return: a slice-to-the-next-`return;}`
        # pin would stay green with the return deleted (the slice runs on to the next branch's return) while
        # keepalives fell through to the resync retire and to the bundle. pane-shim-stale.test.ts RUNS the
        # same rule and asserts no ka reaches the bundle.
        head = ('if(msg&&msg.type==="ka"){if(LOADEDV&&msg.dv&&msg.dv>LOADEDV)raiseBuild(msg.dv);\n'
                'if(stalePending&&++staleKa>=2){var sw=stalePending;stalePending="";raiseStale(sw);}')
        i = KSRC.index(head)
        rest = KSRC[i + len(head):]
        nl = rest.index("\n")                              # the rule line's trailing comment
        third = rest[nl + 1:rest.index("\n", nl + 1)]
        self.assertTrue(third.startswith("return;}"), "the ka branch RETURNS: %r" % third)
        self.assertNotIn("dispatchEvent", head + rest[:nl + 1 + len(third)])


class BuildDriftBanner(unittest.TestCase):
    """Build drift is noticed on every page (the user 2026-07-13): the keepalive carries the kernel's current
    dist token (dv); every kernel-served page bakes its own load-time token (LOADEDV) into the shim and acts
    when dv passes it — so a standalone pane (no dashboard shell, previously NO check at all) notices too,
    and within one heartbeat instead of a 30s poll. What the raise DOES changed on 2026-09-08 (T265: the reload
    core reloads the page itself, never mid-gesture, superseding the 2026-07-13 "prompt, never automatic" rule)
    and again on 2026-09-16: the raise hands the dv to the core, which OFFERS the reload (the shell's banner, or a
    standalone page's own bar, with Reload and Not now) and never takes it; the self-injected build bar stands
    only where the core is absent (tests/test_dashboard_auto_reload.py runs the core and the offer)."""

    def test_keepalive_frame_carries_the_dist_token(self):
        got = []
        km._clients[:] = [{"app": "feed", "wid": "", "send": got.append, "alive": True}]
        try:
            km._keepalive_all()
        finally:
            km._clients[:] = []
        self.assertIn("dv", json.loads(got[0]), "every keepalive carries the current dist build token")

    def test_shim_bakes_the_pages_loaded_version(self):
        self.assertIn("var LOADEDV=123;", km._shim("feed", 123))
        # default (no version passed) bakes 0, which DISABLES the check (the LOADEDV&& guard) — a page
        # that doesn't know its build can never false-positive
        self.assertIn("var LOADEDV=0;", km._shim("feed"))

    def test_shim_hands_build_drift_to_the_reload_core_with_the_bar_where_the_core_is_absent(self):
        # 2026-09-16: the raise hands the keepalive's dv to the reload core, which offers (deduped by build: every keepalive
        # may hand it in); the self-injected bar stands only where the core is absent, once per page life
        js = km._shim("chat", 7)
        self.assertIn('function raiseBuild(dv){var R=window.__rompReload;if(R){R.noteDv(dv);return;}', js,
                      "build drift is a proposal to the core, never a request")
        self.assertNotIn('R.request("build"', js); self.assertNotIn("R.refused=", js)
        self.assertNotIn('postMessage({romp:"wsStale",build:1}', js, "the hand-off to the shell banner is gone")
        self.assertIn('if(buildRaised)return;buildRaised=true;selfBar("A newer romp build is available.","build");}', js,
                      "standalone page self-injects the bar when the core is absent, once")
        self.assertIn("var buildRaised=false,freshPending=false,restartAnnounced=0;", js)   # the no-core bar's latch (T217 added the announced-restart latch to the line)
        #                                    (freshPending rides along: the CONN prompt's self-retire, 2026-08-01)

    def test_every_pane_page_passes_its_version_to_the_shim(self):
        for app in ("chat", "feed", "fleet", "timeline"):
            self.assertIn('_shim("%s", v' % app, KSRC, "%s page bakes its ?v token into the shim" % app)   # (the feed page also passes caps=)


class ShellLivenessMatchesTheShim(unittest.TestCase):
    """D3 (2026-09-18): the shell socket got the shim's liveness rules. romp-manager ruled the shell keeps its OWN copy
    rather than sharing a fragment inlined into the shim (the shim is upstream text the fold touches weekly, and the
    standing rule is to follow upstream there). This ONE test is that ruling's safety net: it reads the constants and
    the three watchdog arms out of BOTH copies and asserts they agree, so a drift between them fails a test, not a
    phone. The shim's anti-duplicate guard above still holds (the shell uses its own SH_* names, so the shim is still
    one), and the shell's connect cut is the design's named constant at today's 15 s."""

    def _shim_bounds(self):
        js = km._shim("chat")
        import re
        stale = int(re.search(r"var lastRecv=0;var STALE_MS=(\d+);", js).group(1))
        prov = int(re.search(r"var PROVISIONAL_MS=(\d+),resumeProvisional=0;", js).group(1))
        connect_cut = int(re.search(r"ws\.readyState===0&&Date\.now\(\)-connT>(\d+)", js).group(1))
        closed_redial = int(re.search(r"ws\.readyState===3&&Date\.now\(\)-connT>(\d+)\)\{connect\(\);\}\},(\d+)\)", js).group(1))
        tick = int(re.search(r"ws\.readyState===3&&Date\.now\(\)-connT>\d+\)\{connect\(\);\}\},(\d+)\)", js).group(1))
        return {"stale": stale, "prov": prov, "connect_cut": connect_cut, "closed_redial": closed_redial, "tick": tick}

    def _shell_bounds(self):
        mob = km._LANDING_MOBILE_JS
        import re
        line = re.search(r"var SH_STALE_MS=(\d+),SH_PROVISIONAL_MS=(\d+),SH_CONNECT_MS=(\d+),SH_REDIAL_MS=(\d+),SH_TICK_MS=(\d+),SH_BLIND_MS=(\d+),", mob)
        self.assertIsNotNone(line, "the shell declares its own copy of the liveness constants, and names its blind redial")
        return {"stale": int(line.group(1)), "prov": int(line.group(2)), "connect_cut": int(line.group(3)),
                "closed_redial": int(line.group(4)), "tick": int(line.group(5)), "blind": int(line.group(6))}

    def test_the_two_copies_agree_on_the_constants(self):
        shim, shell = self._shim_bounds(), self._shell_bounds()
        self.assertEqual(shim["stale"], shell["stale"], "STALE_MS")
        self.assertEqual(shim["prov"], shell["prov"], "PROVISIONAL_MS")
        self.assertEqual(shim["connect_cut"], shell["connect_cut"], "the 15 s CONNECTING cut")
        self.assertEqual(shim["closed_redial"], shell["closed_redial"], "the CLOSED redial bound")
        self.assertEqual(shim["tick"], shell["tick"], "the 5 s watchdog tick")
        self.assertEqual(shell["connect_cut"], 15000, "the connect cut is a named constant at today's 15 s (SH_CONNECT_MS)")

    def test_the_panes_link_backstop_covers_the_shells_whole_alive_cycle(self):
        # review round 1 (kernel-2, 2026-09-18): the pane's link backstop (kernel.py _shim) calls the shell's redial loop
        # dead once the shell's connT is stale past a bound, so the bound must cover the loop's whole ALIVE cycle on a
        # hung path, from the shell's own constants: the CONNECTING cut, the watchdog tick that performs it (up to one
        # tick late) and the blind redial that follows, rounded up to the next tick as a margin for late timers. The
        # 20 s bound this replaces omitted the redial and named an alive loop dead in its last two seconds.
        import re
        shim, shell = km._shim("chat"), self._shell_bounds()
        bound = int(re.search(r"L\.connT&&Date\.now\(\)-L\.connT>(\d+)\)", shim).group(1))
        self.assertIn("else shd=SH_BLIND_MS;", km._LANDING_MOBILE_JS, "the blind redial reads its named constant, so the derivation below reads the value the shell runs")
        cycle = shell["connect_cut"] + shell["tick"] + shell["blind"]
        self.assertGreater(bound, cycle, "the bound exceeds the alive cycle's worst case (cut + one tick + the blind redial = %d ms)" % cycle)
        self.assertEqual(bound, shell["connect_cut"] + 2 * shell["tick"], "...rounded up to the next tick: the cut plus two ticks")
        self.assertEqual(bound, 25000)

    def test_the_two_copies_agree_on_the_tick_semantics(self):
        # both watchdogs carry the same three arms with the same bounds: an OPEN socket quiet past a bound is put down
        # and redialed; a CONNECTING one past the 15 s cut is closed; a CLOSED one past the redial bound dials
        shim = km._shim("chat")
        mob = km._LANDING_MOBILE_JS
        self.assertIn("if(ws.readyState===1){var bound=resumeProvisional?PROVISIONAL_MS:STALE_MS;", shim)
        self.assertIn("if(shWs.readyState===1){var b=shResumeProvisional?SH_PROVISIONAL_MS:SH_STALE_MS;", mob)
        self.assertIn("if(ws.readyState===0&&Date.now()-connT>15000){try{ws.close();}catch(e){}return;}", shim)
        self.assertIn("if(shWs.readyState===0&&Date.now()-shConnT>SH_CONNECT_MS){try{shWs.close();}catch(e){}return;}", mob)
        self.assertIn("if(ws.readyState===3&&Date.now()-connT>8000){connect();}", shim)
        self.assertIn("if(shWs.readyState===3&&Date.now()-shConnT>SH_REDIAL_MS){shellWS();}", mob)

    def test_the_shim_anti_duplicate_guard_still_reads_one_shim(self):
        # the shell's copy uses SH_* names, so the shim's own line is still counted once (the guard above is untouched)
        self.assertEqual(KSRC.count("var lastRecv=0;var STALE_MS=30000;"), 1)
        self.assertEqual(KSRC.count("var SH_STALE_MS=30000,SH_PROVISIONAL_MS=15000,SH_CONNECT_MS=15000,SH_REDIAL_MS=8000,SH_TICK_MS=5000,"), 1,
                         "the shell keeps exactly one copy of its own constants")


if __name__ == "__main__":
    unittest.main()
