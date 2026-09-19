"""The pane loader that a WS drop puts up must be able to come back DOWN.

The user 2026-07-28: the dashboard announced it had lost the connection every few seconds, and after each
one the chat pane sat under the romp loader until a manual reload.

_pane_spin's loader has exactly two ways down, and on a RE-show — the one `romp:wsdown` triggers — neither
of them worked:

  MutationObserver   fires when the content container gains a child. render.ts's ensureView inserts one
                     `.thread` div per session ONCE and keeps it in a map for the life of the page, so
                     after the first load the container's direct children never change again. Every
                     post-reconnect push mutates nodes that are already there, and a childList observer
                     is deaf to that. Right on a cold load, unreachable on a reconnect.
  30s failsafe       was armed once at page load, so it only ever covered the FIRST show. By the time a
                     drop re-showed the loader, that timer had fired long ago.

So the loader went up on the drop with nothing left that could take it down — a pane frozen behind an
overlay while the socket underneath had already reconnected and was streaming fine.

The fix keeps both exits but makes them repeatable: the failsafe re-arms on every show, and the shim
fires `romp:wsup` on a reconnect, which hides the loader — the socket being back is precisely the event
that ends "romp is reconnecting". Staleness of what's on screen is the shell's reload prompt's job
(raiseStale, same onopen), not the loader's.

Source-pinning, like the other _pane_spin tests (this JS has no jsdom harness).
"""
import json
import os
import shutil
import subprocess
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


class PaneLoaderReconnect(unittest.TestCase):
    def setUp(self):
        self.js = km._pane_spin("content", "live-ask")

    def test_the_failsafe_is_armed_per_show_not_once_per_page_load(self):
        """The regression itself. A timer set in the load path cannot cover a show that happens minutes
        later, which is every show after the first one."""
        self.assertIn("function arm(){clearTimeout(fail);fail=setTimeout(hide,30000);}", self.js)
        self.assertIn("function show(){o.classList.remove('gone');arm();}", self.js,
                      "showing the loader must (re-)arm its own failsafe")
        self.assertNotIn("if(ready())hide();}setTimeout(hide,30000);", self.js,
                         "the old load-time-only arming is gone")

    def test_hiding_cancels_the_failsafe(self):
        """Otherwise a stale timer from an earlier show fires over a pane that is already live, and the
        next show inherits a shortened window."""
        self.assertIn("function hide(){clearTimeout(fail);o.classList.add('gone');}", self.js)

    def test_the_loader_comes_down_when_the_socket_comes_back(self):
        """The event-based exit for the re-show path. Without it the only way down is the failsafe, i.e.
        30 seconds of romp logo over a pane whose socket reconnected in under two."""
        self.assertIn("window.addEventListener('romp:wsup',function(){hide();});", self.js)
        # …while the corner BADGE (a pane that has content) waits for the first fresh frame instead
        # (2026-09-07; test_pane_shim_return.py owns that half)
        self.assertIn("window.addEventListener('romp:wsfresh',function(){badge(false);});", self.js)
        self.assertIn("window.addEventListener('romp:wsdown',function(){if(ready()){badge(true);}else{show();}});", self.js,
                      "the drop still raises SOMETHING — a matched pair; since T217 a pane with "
                      "content gets the translucent badge and only an empty pane the opaque sheet")

    def test_the_shim_fires_wsup_on_a_reconnect_only(self):
        """A first connect must NOT fire it: the loader is legitimately up during a cold load and has to
        stay there until real content lands (an 8s timer that hid it early was the 2026-07-03 bug)."""
        shim = km._shim("chat")
        self.assertIn('if(wasReconn){var ann=restartAnnounced&&Date.now()-restartAnnounced<30000;'
                      'restartAnnounced=0;', shim,
                      "the wasReconn gate stands; T217 spends the announced-restart latch inside it")
        self.assertIn('try{window.dispatchEvent(new Event("romp:wsup"));}catch(e){}\nenqueue({type:"wsup"});}', shim,
                      "wsup still rides the same wasReconn gate as the reload prompt")
        self.assertIn("var wasReconn=everConnected;everConnected=true;", shim,
                      "and wasReconn still means 'this socket had connected before'")

    def test_every_pane_that_carries_the_loader_gets_both_halves(self):
        """The chat is only where it was noticed: the same loader ships on the feed and fleet pages, and
        they drop and reconnect the same way. The timeline deliberately has no _pane_spin (it owns a
        bars-area loader instead, the user 2026-06-26) — it still carries the shim, so it gets the event
        whether or not anything listens today."""
        for page in (km._chat_page(), km._feed_page(), km._fleet_page()):
            self.assertIn("window.addEventListener('romp:wsup',function(){hide();});", page)
            self.assertIn("window.addEventListener('romp:wsfresh',function(){badge(false);});", page)
            self.assertIn('new Event("romp:wsup")', page)
        self.assertIn('new Event("romp:wsup")', km._timeline_page())
        self.assertNotIn("window.addEventListener('romp:wsup',function(){hide();});", km._timeline_page(),
                         "the timeline still owns no _pane_spin overlay")


# The loader's script, executed (review round 2 of the lazy panes, 2026-09-19): the sheet's failsafe timer under the pane
# bundle's two first-paint events. A fake document (the sheet with a class list, an empty content container), a fake
# MutationObserver, recording timers and a window that keeps its listeners; the script is the <script> body _pane_spin returns.
_SPIN_HARNESS = r"""
'use strict';
const TIMERS = [], LISTENERS = {}, CLS = new Set();
let nextId = 1;
global.setTimeout = (fn, ms) => { const id = nextId++; TIMERS.push({ id, fn, ms, live: true }); return id; };
global.clearTimeout = (id) => { for (const t of TIMERS) if (t.id === id) t.live = false; };
global.MutationObserver = class { constructor(cb) { this.cb = cb; } observe() {} };
const SHEET = { classList: { add: (c) => CLS.add(c), remove: (c) => CLS.delete(c), contains: (c) => CLS.has(c) } };
const CONTENT = { children: [] };
global.document = { getElementById: (id) => (id === 'pane-spin' ? SHEET : id === '__CID__' ? CONTENT : null) };
global.window = global;
global.addEventListener = (type, fn) => { (LISTENERS[type] = LISTENERS[type] || []).push(fn); };
const fire = (type) => (LISTENERS[type] || []).forEach((fn) => fn({ type }));
const live30 = () => TIMERS.filter((t) => t.live && t.ms === 30000).length;
"""
_SPIN_DRIVER = r"""
const out = {};
out.boot = { live30: live30(), gone: CLS.has('gone'), listeners: Object.keys(LISTENERS).sort() };
fire('romp:firstpaintheld');   // the bundle's first frame applied off screen: the first paint is held
out.held = { live30: live30(), gone: CLS.has('gone') };
TIMERS.forEach((t) => { if (t.live && t.ms === 30000) { t.live = false; t.fn(); } });   // 30 s pass: every LIVE 30 s timer fires (a cleared one never does)
out.after30 = { gone: CLS.has('gone') };
fire('romp:firstpaintreleased');   // the show's release render painted
out.released = { live30: live30(), gone: CLS.has('gone') };
fire('romp:firstpaintheld');
out.heldAgain = { live30: live30() };
// the latch (review round 3, fresh-2): a socket blip WHILE the hold stands. wsdown's show() re-arms the failsafe (upstream's listener,
// registered first); ours, after it, stands the timer down again. wsup's hide() fades the sheet; ours re-shows it.
fire('romp:wsdown');
out.heldDown = { live30: live30(), gone: CLS.has('gone') };
fire('romp:wsup');
out.heldUp = { live30: live30(), gone: CLS.has('gone') };
fire('romp:firstpaintreleased');
out.releasedAfterBlip = { live30: live30(), gone: CLS.has('gone') };
TIMERS.forEach((t) => { if (t.live && t.ms === 30000) { t.live = false; t.fn(); } });   // the release re-armed the failsafe: 30 s later it fires
out.after30Released = { gone: CLS.has('gone') };
// the blip BEFORE the hold word (the refuter's amendment): wsdown then wsup before any frame fades the sheet; the hold word re-shows it
const CLS2 = new Set(['gone']); CLS.clear(); CLS.add('x'); CLS.delete('x');   // a fresh sheet state for the second page: up
fire('romp:wsdown'); fire('romp:wsup');
out.blipBeforeHold = { gone: CLS.has('gone'), live30: live30() };
fire('romp:firstpaintheld');
out.heldAfterBlip = { gone: CLS.has('gone'), live30: live30() };
console.log(JSON.stringify(out));
"""


class PaneLoaderFirstPaintHold(unittest.TestCase):
    """D3 (review round 2 of the lazy panes, 2026-09-19): on the phone an off-screen feed applies its first frame without painting
    (paint-gate.ts firstPaintHeld), so the sheet's 30 s failsafe used to fade it over the still-empty list and the tap revealed a
    blank pane. The bundle now tells the loader `romp:firstpaintheld` once per hold (the sheet stands with no timer: nobody can see
    it) and `romp:firstpaintreleased` once the release render has painted (the backstop resumes; the render's first child retires
    the sheet through the observer). Executed over the script _pane_spin returns."""

    def _run(self):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node not installed")
        js = km._pane_spin("feed-list")
        script = js[js.index("<script>") + len("<script>"):js.index("</script>")]
        fx = tempfile.mkdtemp()
        path = os.path.join(fx, "spin.js")
        with open(path, "w") as f:
            f.write(_SPIN_HARNESS.replace("__CID__", "feed-list") + script + "\n" + _SPIN_DRIVER)
        r = subprocess.run([node, path], capture_output=True, text=True, timeout=30)
        shutil.rmtree(fx, ignore_errors=True)
        self.assertEqual(r.returncode, 0, "the loader script threw: " + r.stderr[:800])
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_the_held_first_paint_stands_the_sheet_down_from_its_timer_and_the_release_re_arms_it(self):
        o = self._run()
        self.assertEqual(o["boot"], {"live30": 1, "gone": False, "listeners": ["romp:firstpaintheld", "romp:firstpaintreleased", "romp:wsdown", "romp:wsfresh", "romp:wsup"]},
                         "at load the sheet is up with its 30 s failsafe armed, and the two hold events are listened for beside the socket's (wsdown and wsup each carry a second, fork listener since round 3: the latch)")
        self.assertEqual(o["held"], {"live30": 0, "gone": False}, "the hold clears the failsafe: the sheet stands with no timer")
        self.assertFalse(o["after30"]["gone"], "30 s later the sheet is still up (before this the failsafe faded it over the empty list, and the tap revealed a blank pane)")
        self.assertEqual(o["released"], {"live30": 1, "gone": False}, "the release re-arms the 30 s backstop; the render's first child, not this event, retires the sheet (the observer)")
        self.assertEqual(o["heldAgain"]["live30"], 0, "a second hold word stands it down again (the bundle sends one per hold)")

    def test_a_socket_blip_under_the_hold_neither_re_arms_the_failsafe_nor_fades_the_sheet_and_the_hold_word_re_shows_a_faded_sheet(self):
        # fresh-2 (review round 3, 2026-09-19): the "stands with no timer" guarantee held only while the socket never blipped: romp:wsdown's
        # show() re-armed the 30 s failsafe and romp:wsup's hide() faded the sheet, while the bundle tells the loader once per hold, so a drop
        # and redial under the hold undid the mechanism extra6-2 was ruled to close. The latch: `held` set by the hold word (which also re-shows
        # a sheet a blip before it faded), cleared by the release; two fork listeners after upstream's stand the socket's arms down while held.
        o = self._run()
        self.assertEqual(o["heldDown"], {"live30": 0, "gone": False}, "wsdown under the hold: upstream's show() re-armed the failsafe, the fork listener after it stood it down again; the sheet stays up")
        self.assertEqual(o["heldUp"], {"live30": 0, "gone": False}, "wsup under the hold: upstream's hide() faded the sheet, the fork listener re-showed it; no timer")
        self.assertEqual(o["releasedAfterBlip"], {"live30": 1, "gone": False}, "the release clears the latch and re-arms the 30 s backstop")
        self.assertTrue(o["after30Released"]["gone"], "…which fades the sheet 30 s later as before (the latch is off)")
        self.assertEqual(o["blipBeforeHold"], {"gone": True, "live30": 0}, "a blip BEFORE the hold word (wsdown, wsup: hide() fades the sheet; the wsdown's re-arm was cleared by hide())")
        self.assertEqual(o["heldAfterBlip"], {"gone": False, "live30": 0}, "the hold word re-shows the faded sheet and stands it with no timer (the refuter's amendment: without the re-show the sheet stayed faded over the still-empty list)")

    def test_the_fork_listener_lines_are_inserted_beside_the_socket_ones(self):
        js = km._pane_spin("feed-list")
        self.assertIn("var held=false;window.addEventListener('romp:firstpaintheld',function(){held=true;clearTimeout(fail);o.classList.remove('gone');});", js)
        self.assertIn("window.addEventListener('romp:firstpaintreleased',function(){held=false;arm();});", js)
        self.assertIn("window.addEventListener('romp:wsdown',function(){if(held)clearTimeout(fail);});", js, "the fork's wsdown listener (round 3): the failsafe upstream's show() re-armed is cleared while held")
        self.assertIn("window.addEventListener('romp:wsup',function(){if(held)o.classList.remove('gone');});", js, "the fork's wsup listener: the sheet upstream's hide() faded is re-shown while held")
        # upstream's text stands: its own wsdown and wsup lines, unchanged, BEFORE ours (same-target listeners run in registration order, so the fork's arms run after upstream's)
        self.assertIn("window.addEventListener('romp:wsdown',function(){if(ready()){badge(true);}else{show();}});", js)
        self.assertIn("window.addEventListener('romp:wsup',function(){hide();});", js)
        self.assertLess(js.index("window.addEventListener('romp:wsup',function(){hide();});"), js.index("var held=false;"), "after the wsup line")
        self.assertLess(js.index("romp:firstpaintheld"), js.index("window.addEventListener('romp:wsdown',function(){if(held)"), "the hold word's listener, then the fork's two socket listeners")
        self.assertLess(js.index("window.addEventListener('romp:wsup',function(){if(held)"), js.index("window.addEventListener('romp:wsfresh'"), "before the wsfresh line: the upstream lines are inserted around, not changed")
        self.assertEqual(js.count("addEventListener('romp:wsdown'"), 2); self.assertEqual(js.count("addEventListener('romp:wsup'"), 2)


if __name__ == "__main__":
    unittest.main()
