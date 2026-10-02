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
global.document = { visibilityState: 'visible', addEventListener: () => {},   // the reconnect cue's visibility listener (iOS item 4) needs the method; this harness drives no visibility
  getElementById: (id) => (id === 'pane-spin' ? SHEET : id === '__CID__' ? CONTENT : null) };
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
        self.assertEqual(o["boot"], {"live30": 1, "gone": False, "listeners": ["message", "romp:firstpaintheld", "romp:firstpaintreleased", "romp:parked", "romp:unpark", "romp:wsdown", "romp:wsfresh", "romp:wsup"]},
                         "at load the sheet is up with its 30 s failsafe armed, and the two hold events are listened for beside the socket's (wsdown and wsup each carry a second, fork listener since pass 3: the latch; the shell's link word, `message`, and two more socket listeners since iOS item 4: the badge's hold and failsafe latch; the shim's park and unpark since the parked-pane fix of 2026-10-02)")
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
        self.assertIn("window.addEventListener('romp:wsdown',function(){if(held)clearTimeout(fail);});", js, "the fork's wsdown listener (pass 3): the failsafe upstream's show() re-armed is cleared while held")
        self.assertIn("window.addEventListener('romp:wsup',function(){if(held)o.classList.remove('gone');});", js, "the fork's wsup listener: the sheet upstream's hide() faded is re-shown while held")
        # upstream's text stands: its own wsdown and wsup lines, unchanged, BEFORE ours (same-target listeners run in registration order, so the fork's arms run after upstream's)
        self.assertIn("window.addEventListener('romp:wsdown',function(){if(ready()){badge(true);}else{show();}});", js)
        self.assertIn("window.addEventListener('romp:wsup',function(){hide();});", js)
        self.assertLess(js.index("window.addEventListener('romp:wsup',function(){hide();});"), js.index("var held=false;"), "after the wsup line")
        self.assertLess(js.index("romp:firstpaintheld"), js.index("window.addEventListener('romp:wsdown',function(){if(held)"), "the hold word's listener, then the fork's two socket listeners")
        self.assertLess(js.index("window.addEventListener('romp:wsup',function(){if(held)"), js.index("window.addEventListener('romp:wsfresh'"), "before the wsfresh line: the upstream lines are inserted around, not changed")
        # four wsdown listeners and three wsup listeners since iOS item 4 (2026-10-02): upstream's, the sheet's held latch, and
        # the badge's hold (a wsdown before upstream's line and one after it) and failsafe latch (a wsup); ReconnectBadgeHold below
        self.assertEqual(js.count("addEventListener('romp:wsdown'"), 4); self.assertEqual(js.count("addEventListener('romp:wsup'"), 3)



# The reconnect cue's glance (iOS item 4, 2026-10-02): the pane's corner badge under the hold and the failsafe latch, executed.
# A fake clock whose timers carry their due time, a badge with a class list (its text and children are watched: nothing may write them), a pane
# with content (a drop raises the badge, not the sheet), a document with a visibility state and listeners, and a window whose
# dispatches run every listener in registration order as ONE task; after each task the harness records whether the badge is
# painted, which is what a frame would show (a class set and cleared inside one task never paints).
_BADGE_HARNESS = r"""
'use strict';
let NOW = 1000000;
const TIMERS = [], WIN = {}, DOCL = {}, SHEETCLS = new Set(), BADGECLS = new Set(), PAINTS = [], TEXTW = [];
let nextId = 1;
global.setTimeout = (fn, ms) => { const id = nextId++; TIMERS.push({ id, fn, ms, at: NOW + ms, live: true }); return id; };
global.clearTimeout = (id) => { for (const t of TIMERS) if (t.id === id) t.live = false; };
global.MutationObserver = class { constructor() {} observe() {} };
const cls = (S) => ({ add: (c) => S.add(c), remove: (c) => S.delete(c), contains: (c) => S.has(c),
  toggle: (c, on) => { if (on) S.add(c); else S.delete(c); return !!on; } });
const SHEET = { classList: cls(SHEETCLS) };
const BADGE = { classList: cls(BADGECLS) };
// the glance carries no count, so ANY write to the badge's text or children is recorded and every case asserts there was none:
// textContent, innerHTML, innerText or outerHTML set; a child added, moved, replaced or removed; a child node's value or text set
// (its swirl image and its text node, which a writer could reach as childNodes, firstChild or lastChild)
const trapNode = (name) => { const n = {}; for (const k of ['nodeValue', 'textContent', 'data', 'innerHTML']) Object.defineProperty(n, k, { get: () => 'reconnecting', set: (v) => TEXTW.push(name + '.' + k + '=' + String(v)) }); return n; };
const KIDS = [trapNode('img'), trapNode('text')];
for (const k of ['textContent', 'innerHTML', 'innerText', 'outerHTML']) Object.defineProperty(BADGE, k, { get: () => 'reconnecting', set: (v) => TEXTW.push(k + '=' + String(v)) });
for (const k of ['appendChild', 'append', 'prepend', 'insertBefore', 'replaceChild', 'replaceChildren', 'replaceWith', 'insertAdjacentHTML', 'insertAdjacentText', 'insertAdjacentElement', 'removeChild', 'remove', 'before', 'after']) BADGE[k] = (...a) => { TEXTW.push(k + '(' + a.map(String).join(',') + ')'); };
for (const [k, v] of [['childNodes', KIDS], ['children', [KIDS[0]]], ['firstChild', KIDS[0]], ['lastChild', KIDS[1]], ['firstElementChild', KIDS[0]], ['lastElementChild', KIDS[0]]]) Object.defineProperty(BADGE, k, { get: () => v });
const CONTENT = { children: [{ id: 'thread-1' }] };
global.document = { visibilityState: 'visible', addEventListener: (t, f) => { (DOCL[t] = DOCL[t] || []).push(f); },
  getElementById: (id) => (id === 'pane-spin' ? SHEET : id === 'pane-reconn' ? BADGE : id === 'content' ? CONTENT : null) };
global.window = global;
global.addEventListener = (t, f) => { (WIN[t] = WIN[t] || []).push(f); };
const painted = () => BADGECLS.has('on');
const task = (fn) => { fn(); PAINTS.push({ t: NOW, on: painted() }); };
const fire = (type) => task(() => (WIN[type] || []).forEach((f) => f({ type })));
const fires = (...types) => task(() => types.forEach((type) => (WIN[type] || []).forEach((f) => f({ type }))));   // several events in ONE task: the shim's park (romp:parked, then romp:wsdown) and its unpark (romp:unpark, then romp:wsdown)
const msg = (data) => task(() => (WIN.message || []).forEach((f) => f({ data })));
const vis = (s) => task(() => { document.visibilityState = s; (DOCL.visibilitychange || []).forEach((f) => f({ type: 'visibilitychange' })); });
// the clock walks to `to`, firing each live timer due by then in due order, each as its own task
const run = (to) => { for (;;) { const due = TIMERS.filter((t) => t.live && t.at <= to).sort((a, b) => a.at - b.at || a.id - b.id)[0]; if (!due) break; NOW = due.at; due.live = false; task(due.fn); } NOW = to; };
const after = (ms) => run(NOW + ms);
const live = (ms) => TIMERS.filter((t) => t.live && (ms === undefined || t.ms === ms)).length;
// the painted state's changes across tasks, from not painted: each {t, on}; [] means the badge never painted
const runs = () => { const r = []; let prev = false; for (const p of PAINTS) { if (p.on !== prev) { r.push({ t: p.t - 1000000, on: p.on }); prev = p.on; } } return r; };
const out = (o) => console.log(JSON.stringify(Object.assign(o, { textWrites: TEXTW })));
"""


class ReconnectBadgeHold(unittest.TestCase):
    """iOS item 4 (2026-10-02): the reconnect cue's glance is the pane's corner badge, 'reconnecting…', with no count. Two
    latches around upstream's badge lines, executed over the script _pane_spin returns. (1) The no-flash hold: a drop's badge
    paints only if no fresh frame has come _RECONN_BADGE_HOLD_MS after the later of the drop and the page turning visible, so a
    healthy return shows nothing (the lab measured a 386 ms flash on the phone at 919fde73b); the hold delays the first paint
    and never clears anything. (2) The failsafe latch: while the shell's link word says down and this pane's own socket is not
    open, the badge's 30 s failsafe stands down (romp is still dialing); the link word 'up' or the pane's own reopen restarts it.
    A page with no shell hears no link word and keeps upstream's failsafe. The hold reads the constant from the kernel when it
    has one and 1000 ms otherwise, so a run at a head without the hold fails on the behaviour, not on a missing name."""

    HOLD = getattr(km, "_RECONN_BADGE_HOLD_MS", 1000)

    def _run(self, scenario):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node not installed")
        js = km._pane_spin("content", "live-ask")
        script = js[js.index("<script>") + len("<script>"):js.index("</script>")]
        fx = tempfile.mkdtemp()
        path = os.path.join(fx, "badge.js")
        with open(path, "w") as f:
            f.write(_BADGE_HARNESS + "const RHOLD_T = %d;\n" % self.HOLD + script + "\n" + scenario)
        r = subprocess.run([node, path], capture_output=True, text=True, timeout=30)
        shutil.rmtree(fx, ignore_errors=True)
        self.assertEqual(r.returncode, 0, "the loader script threw: " + r.stderr[:800])
        o = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(o["textWrites"], [], "nothing writes the badge's text or children: the glance stays 'reconnecting…', no count, in every state")
        return o

    def test_the_constant_is_one_second_and_the_badge_markup_carries_no_count(self):
        self.assertEqual(self.HOLD, 1000, "the hold proposed for the user's word (1 s): healthy lab returns end at 386 ms (phone) and 620 ms (desktop)")
        js = km._pane_spin("content", "live-ask")
        self.assertIn("<div id=pane-reconn><img src=/media/romp-swirl-glyph.svg alt=''>reconnecting…</div>", js,
                      "the glance's one line, upstream's bytes: no count, no cause")

    def test_a_healthy_return_never_paints_the_badge(self):
        # S0: the drop, then the pane's first fresh frame 400 ms later, inside the hold. Before the hold the badge painted at the
        # drop and came down at the fresh frame: the flash.
        o = self._run(r"""
fire('romp:wsdown');
const atDrop = { painted: painted(), hold: live(RHOLD_T) };
after(400); fire('romp:wsfresh');
const atFresh = { painted: painted(), live: live() };
after(60000);
out({ atDrop, atFresh, runs: runs(), liveEnd: live() });""")
        self.assertEqual(o["atDrop"], {"painted": False, "hold": 1}, "the drop's badge is pulled back in the same task and one hold is armed")
        self.assertEqual(o["atFresh"], {"painted": False, "live": 0}, "the fresh frame ends the wait: no badge, no hold, no failsafe left")
        self.assertEqual(o["runs"], [], "the badge never painted across the healthy return")

    def test_the_first_try_past_the_hold_paints_the_badge_at_the_hold_and_the_fresh_frame_clears_it_with_no_timer(self):
        # S1 then S3: no fresh frame by the hold, the badge paints; the fresh frame clears it, an event, and nothing is left pending
        o = self._run(r"""
fire('romp:wsdown');
after(RHOLD_T - 1); const justBefore = painted();
after(1); const atHold = painted();
after(5000); fire('romp:wsfresh');
out({ justBefore, atHold, afterFresh: painted(), liveEnd: live(), runs: runs() });""")
        self.assertIs(o["justBefore"], False, "1 ms before the hold: nothing painted")
        self.assertIs(o["atHold"], True, "at the hold: painted (S1)")
        self.assertIs(o["afterFresh"], False, "the fresh frame clears it (S3)")
        self.assertEqual(o["liveEnd"], 0, "no timer left: the clearing was the event, not a timer")
        self.assertEqual(o["runs"], [{"t": self.HOLD, "on": True}, {"t": self.HOLD + 5000, "on": False}], "one paint, one clear")

    def test_the_badge_stays_past_30s_while_the_link_is_down_and_the_link_up_word_restarts_the_failsafe(self):
        # S2: a return into a down link. Before the latch the badge's 30 s failsafe hid it while romp was still dialing, and the
        # page sat stale with no cue until the link came up (the lab's 45 s hung leg at 919fde73b: hidden at +30.09 s, link at +45 s).
        o = self._run(r"""
msg({ romp: 'panes', on: {}, link: 'up' });                           // boot: the shell's link is up
vis('hidden'); fire('romp:wsdown');                                   // the socket dies in the background
msg({ romp: 'panes', on: {}, link: 'down' });                         // the shell's abandon at the return says down
vis('visible');                                                       // the return
const atReturn = painted();
after(RHOLD_T); const s1 = { painted: painted(), failsafe: live(30000) };
after(45000); const past30 = painted();                               // 46 s after the return, the link still down
msg({ romp: 'link', link: 'up' });                                    // the shell's socket opens (the link word, the other form)
const atLinkUp = { painted: painted(), failsafe: live(30000) };
fire('romp:wsup');                                                    // the pane's own socket opens: no second failsafe
const atOpen = live(30000);
fire('romp:wsfresh');
out({ atReturn, s1, past30, atLinkUp, atOpen, afterFresh: painted(), liveEnd: live(), runs: runs() });""")
        self.assertIs(o["atReturn"], False, "the return holds the badge")
        self.assertEqual(o["s1"], {"painted": True, "failsafe": 0}, "painted at the hold, with no failsafe while the link is down")
        self.assertIs(o["past30"], True, "still painted 46 s after the return: romp is still dialing (before the latch the failsafe hid it at 30 s)")
        self.assertEqual(o["atLinkUp"], {"painted": True, "failsafe": 1}, "the link-up word restarts the 30 s failsafe from that moment; the badge waits for fresh data")
        self.assertEqual(o["atOpen"], 1, "the pane's own reopen while the link is up arms no second failsafe")
        self.assertIs(o["afterFresh"], False)
        self.assertEqual(o["liveEnd"], 0)
        self.assertEqual([r["on"] for r in o["runs"]], [True, False], "one paint, one clear: no flap across the wait")

    def test_a_drop_while_hidden_paints_only_a_hold_after_the_page_turns_visible(self):
        o = self._run(r"""
vis('hidden'); fire('romp:wsdown');
const hidden = { painted: painted(), hold: live(RHOLD_T) };
after(5000); const stillHidden = painted();
vis('visible'); const atVisible = { painted: painted(), hold: live(RHOLD_T) };
after(RHOLD_T - 1); const justBefore = painted();
after(1);
out({ hidden, stillHidden, atVisible, justBefore, atHold: painted(), runs: runs() });""")
        self.assertEqual(o["hidden"], {"painted": False, "hold": 0}, "a drop while hidden arms nothing: the hold counts from the page turning visible")
        self.assertIs(o["stillHidden"], False)
        self.assertEqual(o["atVisible"], {"painted": False, "hold": 1}, "turning visible arms the hold")
        self.assertIs(o["justBefore"], False)
        self.assertIs(o["atHold"], True)
        self.assertEqual(o["runs"], [{"t": 5000 + self.HOLD, "on": True}], "painted once, a hold after the page turned visible")

    def test_a_badge_painted_before_the_page_hid_is_re_held_at_the_return_and_a_quick_fresh_frame_keeps_it_off(self):
        o = self._run(r"""
fire('romp:wsdown'); after(RHOLD_T); const before = painted();
vis('hidden'); const whileHidden = painted();
after(20000);                                                         // inside the badge's own 30 s failsafe (no shell here)
vis('visible'); const atReturn = { painted: painted(), hold: live(RHOLD_T) };
after(300); fire('romp:wsfresh');
out({ before, whileHidden, atReturn, afterFresh: painted(), runs: runs() });""")
        self.assertIs(o["before"], True)
        self.assertIs(o["whileHidden"], True, "hiding the page leaves a painted badge as it is (nobody sees it)")
        self.assertEqual(o["atReturn"], {"painted": False, "hold": 1}, "the return re-holds it")
        self.assertIs(o["afterFresh"], False)
        self.assertEqual([r["on"] for r in o["runs"]], [True, False], "no repaint after the return: the fresh frame came inside the hold")

    def test_hiding_the_page_cancels_a_pending_hold_and_the_return_holds_afresh(self):
        o = self._run(r"""
fire('romp:wsdown'); after(500);
vis('hidden'); const atHide = live(RHOLD_T);
after(5000); const whileHidden = painted();
vis('visible'); const atVisible = live(RHOLD_T);
after(RHOLD_T - 1); const justBefore = painted();
after(1);
out({ atHide, whileHidden, atVisible, justBefore, atHold: painted() });""")
        self.assertEqual(o["atHide"], 0, "hiding the page cancels the pending hold")
        self.assertIs(o["whileHidden"], False, "nothing paints while hidden")
        self.assertEqual(o["atVisible"], 1, "the return holds afresh")
        self.assertIs(o["justBefore"], False)
        self.assertIs(o["atHold"], True)

    def test_a_repeat_drop_while_painted_under_a_down_link_leaves_no_failsafe(self):
        # upstream's wsdown line re-arms the 30 s failsafe on every drop over content; under a down link the listener after it
        # stands it down again, so a pane that drops again while the shell is still dialing keeps its badge past 30 s
        o = self._run(r"""
msg({ romp: 'panes', on: {}, link: 'down' });
fire('romp:wsdown'); after(RHOLD_T);
fire('romp:wsup'); const opened = live(30000);                       // the pane's own socket opens: the failsafe runs
fire('romp:wsdown'); const redropped = live(30000);                  // and drops again with the link still down
after(45000);
out({ opened, redropped, after45: painted() });""")
        self.assertEqual(o["opened"], 1)
        self.assertEqual(o["redropped"], 0, "the repeat drop under a down link leaves no failsafe")
        self.assertIs(o["after45"], True)

    def test_repeat_drops_neither_flicker_a_painted_badge_nor_move_a_pending_hold(self):
        o = self._run(r"""
fire('romp:wsdown'); after(600); fire('romp:wsdown');                 // a second drop during the hold
const pending = { painted: painted(), holds: live(RHOLD_T) };
after(RHOLD_T - 600); const atFirstDeadline = painted();             // the FIRST drop's deadline
fire('romp:wsdown'); fire('romp:wsup'); fire('romp:wsdown');          // a redial opens and drops again while painted
const stays = painted();
fire('romp:wsfresh');
out({ pending, atFirstDeadline, stays, runs: runs() });""")
        self.assertEqual(o["pending"], {"painted": False, "holds": 1}, "a repeat drop keeps one hold")
        self.assertIs(o["atFirstDeadline"], True, "the hold counts from the first drop, so repeat drops cannot postpone it")
        self.assertIs(o["stays"], True)
        self.assertEqual([r["on"] for r in o["runs"]], [True, False], "painted once and cleared once: no flicker across the repeat drops")

    def test_a_page_with_no_shell_keeps_upstreams_failsafe_from_the_paint(self):
        # standalone: no link word ever arrives, so the failsafe is armed per show (the paint) and hides the badge 30 s on
        o = self._run(r"""
fire('romp:wsdown'); after(RHOLD_T);
const s1 = { painted: painted(), failsafe: live(30000) };
after(30000);
out({ s1, after30: painted(), runs: runs() });""")
        self.assertEqual(o["s1"], {"painted": True, "failsafe": 1}, "painted at the hold with upstream's 30 s failsafe")
        self.assertIs(o["after30"], False, "30 s after the paint the failsafe hides it, as upstream's does")

    def test_the_panes_own_reopen_under_a_down_link_restarts_the_failsafe(self):
        # a dead shell loop: the pane's 25 s link backstop dials on its own; once its own socket is open the badge waits for fresh
        # data under the failsafe again, so a socket that opens and never delivers cannot keep the badge up for good
        o = self._run(r"""
msg({ romp: 'panes', on: {}, link: 'down' });
fire('romp:wsdown'); after(RHOLD_T);
after(40000); const waiting = { painted: painted(), failsafe: live(30000) };
fire('romp:wsup'); const opened = live(30000);
after(30000);
out({ waiting, opened, after30: painted() });""")
        self.assertEqual(o["waiting"], {"painted": True, "failsafe": 0})
        self.assertEqual(o["opened"], 1, "the pane's own open restarts the failsafe")
        self.assertIs(o["after30"], False)

    def test_the_latch_reads_the_link_field_of_both_shell_words_and_nothing_else(self):
        o = self._run(r"""
msg({ romp: 'other', link: 'down' }); msg({ romp: 'panes', on: {} }); msg(null);
fire('romp:wsdown'); after(RHOLD_T);
const noWord = live(30000);
msg({ romp: 'panes', on: {}, link: 'down' }); const panesDown = live(30000);
msg({ romp: 'link', link: 'up' }); const linkUp = live(30000);
msg({ romp: 'link', link: 'down' }); const linkDown = live(30000);
out({ noWord, panesDown, linkUp, linkDown });""")
        self.assertEqual(o, {"noWord": 1, "panesDown": 0, "linkUp": 1, "linkDown": 0, "textWrites": []},
                         "only a panes or link word's link field moves the latch")

    # A parked pane (the shim's park: the phone's off-screen tabs at a return, D2) gets no fresh frame until its tap, so a hold run
    # there painted the badge off screen and the tap showed it until that pane's first frame, on a healthy link too (finding of
    # 2026-10-02, a 286 ms flash at a tap 2 s after a healthy return). The shim dispatches romp:parked before its park's wsdown and
    # romp:unpark before its tap's wsdown, each in one task with it; tests/test_pane_shim_return.py ParkedPaneBadge composes the shim.
    def test_a_parked_pane_holds_its_badge_with_no_timer_and_its_tap_on_a_healthy_link_paints_nothing(self):
        o = self._run(r"""
vis('hidden'); vis('visible');
fires('romp:parked', 'romp:wsdown');                                  // the return parks this off-screen pane
const atPark = { painted: painted(), live: live() };
after(60000); const parked60 = painted();                             // a minute on another tab: nothing paints, nothing is armed
vis('hidden'); vis('visible'); const reReturn = { painted: painted(), live: live() };   // a return while still parked arms nothing either
fires('romp:unpark', 'romp:wsdown');                                  // the tap: the hold starts here
const atTap = { painted: painted(), holds: live(RHOLD_T), live: live() };
after(300); fire('romp:wsup'); after(50); fire('romp:wsfresh');       // the pane's dial opens and its first frame lands inside the hold
after(60000);
out({ atPark, parked60, reReturn, atTap, runs: runs(), liveEnd: live() });""")
        self.assertEqual(o["atPark"], {"painted": False, "live": 0}, "parked: the badge is held with no timer (nobody sees the pane, and no frame can come)")
        self.assertIs(o["parked60"], False)
        self.assertEqual(o["reReturn"], {"painted": False, "live": 0})
        self.assertEqual(o["atTap"], {"painted": False, "holds": 1, "live": 1}, "the tap is this pane's return: one hold from the tap, nothing else")
        self.assertEqual(o["runs"], [], "the badge never painted: not off screen, not at the tap, not after its fresh frame")
        self.assertEqual(o["liveEnd"], 0)

    def test_a_badge_painted_before_the_park_is_pulled_back_and_a_tap_during_an_outage_paints_a_hold_after_the_tap(self):
        o = self._run(r"""
fire('romp:wsdown'); after(RHOLD_T); const before = painted();        // a drop on screen: painted at the hold
fires('romp:parked', 'romp:wsdown'); const atPark = { painted: painted(), live: live() };   // the user moved to another tab and the return parked this pane
msg({ romp: 'panes', on: {}, link: 'down' });                        // the shell's link goes down
after(20000);
fires('romp:unpark', 'romp:wsdown');                                  // the tap, with the link still down
after(RHOLD_T - 1); const justBefore = painted();
after(1); const atHold = { painted: painted(), live: live() };
after(45000); const waiting = { painted: painted(), live: live() };
msg({ romp: 'link', link: 'up' }); fire('romp:wsup'); fire('romp:wsfresh');
out({ before, atPark, justBefore, atHold, waiting, afterFresh: painted(), runs: runs() });""")
        self.assertIs(o["before"], True)
        self.assertEqual(o["atPark"], {"painted": False, "live": 0}, "the park pulls a painted badge back and drops its failsafe: no timer while parked")
        self.assertIs(o["justBefore"], False, "1 ms before a hold after the tap: nothing painted")
        self.assertEqual(o["atHold"], {"painted": True, "live": 0}, "a hold after the tap it paints, with no failsafe under the down link")
        self.assertEqual(o["waiting"], {"painted": True, "live": 0}, "and stays, with no timer of any length, while the link is down")
        self.assertIs(o["afterFresh"], False)
        self.assertEqual([r["on"] for r in o["runs"]], [True, False, True, False], "painted on screen, pulled back at the park, painted a hold after the tap, cleared at the fresh frame")
        self.assertEqual(o["runs"][2]["t"], 2 * self.HOLD + 20000, "the second paint is a hold after the tap, not after the park")

    def test_the_fork_lines_sit_around_upstreams_badge_lines_which_stay_byte_for_byte(self):
        js = km._pane_spin("content", "live-ask")
        up_badge = "function badge(on){if(rb)rb.classList.toggle('on',!!on);clearTimeout(bfail);if(on)bfail=setTimeout(function(){badge(false);},30000);}"
        up_down = "window.addEventListener('romp:wsdown',function(){if(ready()){badge(true);}else{show();}});"
        up_fresh = "window.addEventListener('romp:wsfresh',function(){badge(false);});})();"
        for line in (up_badge, up_down, up_fresh):
            self.assertEqual(js.count(line), 1, line)
        before = "window.addEventListener('romp:wsdown',function(){rpo=false;ron=!!(rb&&rb.classList.contains('on'));});"
        afterl = "window.addEventListener('romp:wsdown',function(){if(!rb||!rb.classList.contains('on'))return;if(ron){rfail();return;}"
        self.assertLess(js.index(up_badge), js.index(before), "the fork's state reads bfail and rb, declared on upstream's lines")
        self.assertLess(js.index(before), js.index(up_down), "the recording listener runs before upstream's wsdown line (registration order)")
        self.assertLess(js.index(up_down), js.index(afterl), "the hold's listener runs after it, so it sees the badge upstream raised")
        self.assertLess(js.index(afterl), js.index(up_fresh), "inserted before upstream's last line")


if __name__ == "__main__":
    unittest.main()
